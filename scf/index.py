# -*- coding: utf-8 -*-
"""
GitHub Actions 天气提醒脚本
每天 7:30 (cron: 30 23 * * * UTC) → 获取广州天气 + 当日节日 → 推送到企微群
"""

import json
import urllib.request
import urllib.error
from typing import Optional
from datetime import date, timedelta, datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── 时区修复：GitHub Actions 跑在 UTC，推送给国内用户需用北京时间 ───
BEIJING_TZ = timezone(timedelta(hours=8))

def today_beijing() -> date:
    """返回北京时间今天的日期"""
    return datetime.now(BEIJING_TZ).date()


# ─── 企微 Webhook ──────────────────────────────
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35561d77-a386-4401-9d60-f4202c539cee"

# ─── 城市列表 ───────────────────────────────────
CITIES = [
    ("Guangzhou", "广州仓（增城）"),
]

# ─── 天气描述中英对照 ──────────────────────────
WEATHER_CN = {
    "Sunny":                              "☀️ 晴天",
    "Clear":                              "🌙 晴朗",
    "Partly cloudy":                      "⛅ 多云",
    "Cloudy":                             "☁️ 阴天",
    "Overcast":                           "☁️ 阴天",
    "Mist":                               "🌫️ 薄雾",
    "Fog":                                "🌫️ 大雾",
    "Light rain":                         "🌧️ 小雨",
    "Light drizzle":                      "🌧️ 毛毛雨",
    "Patchy rain possible":               "🌦️ 局部阵雨",
    "Patchy light rain":                  "🌦️ 局部小雨",
    "Moderate rain":                      "🌧️ 中雨",
    "Moderate rain at times":             "🌧️ 间歇中雨",
    "Heavy rain":                         "🌧️ 大雨",
    "Heavy rain at times":                "🌧️ 间歇大雨",
    "Light rain shower":                  "🌦️ 小阵雨",
    "Torrential rain shower":             "⛈️ 暴雨",
    "Thunderstorm":                       "⛈️ 雷暴",
    "Thundery outbreaks possible":        "⛈️ 可能有雷暴",
    "Patchy light rain with thunder":     "⛈️ 雷阵雨",
    "Moderate or heavy rain with thunder":"⛈️ 强雷雨",
}


# ═══════════════════════════════════════════════
#  天气获取
# ═══════════════════════════════════════════════

def fetch_weather(city_en: str) -> Optional[dict]:
    url = f"https://wttr.in/{city_en}?format=j1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WARN] 获取 {city_en} 天气失败: {e}")
        return None


# ═══════════════════════════════════════════════
#  节假日查询
# ═══════════════════════════════════════════════

# 固定日期的纪念日（月-日 → 名称/emoji）
FIXED_HOLIDAYS = {
    "01-01": "🎉 元旦",
    "02-14": "💕 情人节",
    "03-08": "🌸 妇女节",
    "03-12": "🌳 植树节",
    "04-01": "😜 愚人节",
    "05-01": "👷 劳动节",
    "05-04": "🔥 青年节",
    "06-01": "👶 儿童节",
    "07-01": "🚩 建党节",
    "08-01": "🎖️ 建军节",
    "09-10": "📚 教师节",
    "10-01": "🇨🇳 国庆节",
    "10-31": "🎃 万圣节",
    "11-11": "🛒 双十一",
    "12-24": "🎄 平安夜",
    "12-25": "🎅 圣诞节",
    "12-31": "🎆 跨年夜",
}


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """返回某年某月第 n 个星期几的日期（weekday: 0=周一..6=周日）"""
    first = date(year, month, 1)
    # 第一个目标星期几是几号
    days_until = (weekday - first.weekday()) % 7
    first_occurrence = first + timedelta(days=days_until)
    return first_occurrence + timedelta(weeks=n - 1)


def get_variable_holiday(today: date) -> Optional[str]:
    """计算可变日期的节日（每年星期几不同）"""
    y, m, d = today.year, today.month, today.day

    # 母亲节：5 月第 2 个周日
    if today == nth_weekday_of_month(y, 5, 6, 2):
        return "👩‍👧 母亲节"

    # 父亲节：6 月第 3 个周日
    if today == nth_weekday_of_month(y, 6, 6, 3):
        return "👨‍👧 父亲节"

    # 感恩节：11 月第 4 个周四
    if today == nth_weekday_of_month(y, 11, 3, 4):
        return "🦃 感恩节"

    return None


def fetch_chinese_holiday(year: int) -> dict:
    """从 chinese-days CDN 拉取当年中国法定节假日"""
    url = f"https://cdn.jsdelivr.net/npm/chinese-days/dist/years/{year}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WARN] 获取节假日数据失败: {e}")
        return {}


# 按年份缓存中国节假日数据（每年不变，避免每次调用都请求 CDN）
_yearly_holiday_cache: dict[int, dict] = {}


def get_cached_chinese_holiday(year: int) -> dict:
    """获取中国节假日数据，按年份缓存"""
    if year not in _yearly_holiday_cache:
        _yearly_holiday_cache[year] = fetch_chinese_holiday(year)
    return _yearly_holiday_cache[year]


def get_today_holidays() -> list[str]:
    """获取今天的节日/纪念日列表"""
    today = today_beijing()
    key = today.strftime("%Y-%m-%d")
    mmdd = today.strftime("%m-%d")
    found = []

    # ── 1. 固定日期纪念日 ──
    if mmdd in FIXED_HOLIDAYS:
        found.append(FIXED_HOLIDAYS[mmdd])

    # ── 2. 可变日期节日 ──
    vh = get_variable_holiday(today)
    if vh:
        found.append(vh)

    # ── 3. 中国法定节假日（农历）── 使用缓存
    data = get_cached_chinese_holiday(today.year)
    holidays = data.get("holidays", {})
    if key in holidays:
        # 格式: "Spring Festival,春节,4"
        parts = holidays[key].split(",")
        cn_name = parts[1] if len(parts) >= 2 else parts[0]
        found.append(f"🏮 {cn_name}")
    else:
        # 非节假日，检查是否是补班日
        workdays = data.get("workdays", {})
        if key in workdays:
            parts = workdays[key].split(",")
            found.append(f"📋 今日补班（{parts[1]}调休）")

    return found


# ═══════════════════════════════════════════════
#  工具
# ═══════════════════════════════════════════════

def fmt_temp(c: str) -> str:
    try:
        return f"{int(float(c))}°C"
    except (ValueError, TypeError):
        return f"{c}°C"


def translate_weather(desc: str) -> str:
    return WEATHER_CN.get(desc, desc)


# ═══════════════════════════════════════════════
#  穿衣推荐
# ═══════════════════════════════════════════════

# 温度 → 穿衣建议（从高到低匹配）
TEMP_ADVICE = [
    (35, "👕 短袖/背心，注意防暑"),
    (30, "👕 短袖"),
    (25, "👔 薄长袖或短袖+薄外套"),
    (20, "🧥 薄外套/卫衣"),
    (15, "🧥 夹克/风衣"),
]


def clothing_advice(lo_c: float, hi_c: float, max_rain: int, uv: int, desc_en: str) -> str:
    parts = []

    # 温度建议 — 数据驱动
    advice = "🧣 厚外套/羽绒服"
    for threshold, text in TEMP_ADVICE:
        if hi_c >= threshold:
            advice = text
            break
    parts.append(advice)

    diff = hi_c - lo_c
    if diff >= 10:
        parts.append(f"⚠️ 昼夜温差 {diff:.0f}°C，带件外套")

    rain_lower = desc_en.lower()
    if any(k in rain_lower for k in ("rain", "drizzle", "thunder", "shower")):
        parts.append("🌂 带雨伞")
    elif max_rain >= 50:
        parts.append("🌂 降雨概率高，建议带伞")

    if uv >= 8:
        parts.append("🧴 紫外线强，记得防晒")
    elif uv >= 5:
        parts.append("🧴 注意防晒")

    return " | ".join(parts) if parts else "👕 舒适出行"


# ═══════════════════════════════════════════════
#  消息构建
# ═══════════════════════════════════════════════

def build_city_card(city_cn: str, data: dict) -> str:
    cc = data["current_condition"][0]

    # 按北京时间匹配今日天气数据，而非 weather[0]（wttr.in 用 UTC 定"今天"）
    today_str = today_beijing().isoformat()
    wi = next(
        (w for w in data["weather"] if w.get("date") == today_str),
        data["weather"][0],
    )
    hourly = wi["hourly"]

    desc_en = cc["weatherDesc"][0]["value"]
    desc_cn = translate_weather(desc_en)
    temp    = fmt_temp(cc["temp_C"])
    feels   = fmt_temp(cc["FeelsLikeC"])
    hi_raw  = float(wi.get("maxtempC", 30))
    lo_raw  = float(wi.get("mintempC", 20))
    hi      = fmt_temp(str(hi_raw))
    lo      = fmt_temp(str(lo_raw))
    uv      = int(cc["uvIndex"])

    morning_rain = 0
    all_rain     = 0
    for h in hourly:
        try:
            hour_num = int(h.get("time", "0")) // 100
            rain     = int(h.get("chanceofrain", "0"))
            if 6 <= hour_num <= 12:
                morning_rain = max(morning_rain, rain)
            all_rain = max(all_rain, rain)
        except (ValueError, TypeError):
            pass

    wear = clothing_advice(lo_raw, hi_raw, all_rain, uv, desc_en)

    lines = []
    lines.append(f"📍 {city_cn}  |  {desc_cn}")
    lines.append(f"🌡️ 当前 {temp}（体感 {feels}） | 湿度 {cc['humidity']}% | UV {uv}")
    lines.append(f"📊 今日 {lo} ~ {hi}")
    lines.append(f"🌬️ {cc['winddir16Point']}风 {cc['windspeedKmph']}km/h")
    lines.append("")
    lines.append(f"🧥 穿衣建议：{wear}")

    if morning_rain >= 60:
        lines.append(f"⚠️ 上午降雨概率 {morning_rain}%，建议提前安排出货")
    elif morning_rain >= 30:
        lines.append(f"🌂 上午降雨概率 {morning_rain}%，建议备雨布")
    elif all_rain >= 60:
        lines.append(f"🌂 今日降雨概率 {all_rain}%，关注下午天气变化")

    return "\n".join(lines)


def build_message(results: list) -> str:
    today = today_beijing()
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]
    date_str = f"{today.year}年{today.month}月{today.day}日 {weekday_cn}"
    lines = [
        f"📅 {date_str} · 科捷物流仓库天气提醒",
        "",
    ]

    # ── 天气卡片 ──
    for city_cn, _, data in results:
        if data:
            lines.append(build_city_card(city_cn, data))
            lines.append("")

    # ── 节日/纪念日 ──
    holidays = get_today_holidays()
    if holidays:
        lines.append("🎊 今日节日：")
        for h in holidays:
            lines.append(f"　{h}")
        lines.append("")

    lines.append("—" * 16)
    lines.append("💡 雨天请关注仓库防潮、出货节奏调整")
    lines.append("科捷物流 · 自动推送")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  推送
# ═══════════════════════════════════════════════

def push_wechat(content: str) -> bool:
    payload = {
        "msgtype": "text",
        "text": {"content": content},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("errcode") == 0
    except Exception as e:
        print(f"[ERROR] 推送失败: {e}")
        return False


# ═══════════════════════════════════════════════
#  SCF 入口
# ═══════════════════════════════════════════════

def main_handler(event, context):
    # 并行获取所有城市天气
    results = []
    with ThreadPoolExecutor(max_workers=len(CITIES)) as executor:
        future_map = {executor.submit(fetch_weather, en): (cn, en) for en, cn in CITIES}
        for future in as_completed(future_map):
            cn, en = future_map[future]
            try:
                data = future.result()
            except Exception:
                data = None
            results.append((cn, en, data))

    if all(d is None for _, _, d in results):
        return {"status": "fail", "reason": "all cities failed"}

    msg = build_message(results)
    ok  = push_wechat(msg)

    print("推送结果:", "成功" if ok else "失败")
    return {"status": "ok" if ok else "fail"}


# ═══════════════════════════════════════════════
#  本地调试
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    main_handler({}, {})
