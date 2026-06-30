#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科捷物流每日天气提醒脚本
- 主数据源：高德地图天气 API（实况 + 预报）
- 降雨补充：wttr.in（逐小时降雨概率，用于出货提醒决策）
- 目标仓库：广州增城（adcode: 440118）
- 推送渠道：企业微信群机器人
- 包含：天气信息 + 穿衣建议 + 通勤出行建议（电动车/汽车）
"""

import json
import urllib.request
import urllib.error
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows GBK 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── 配置 ────────────────────────────────────────────────
AMAP_KEY = "7f8f03f4c0400ea203d7f8b1c0e3c0cb"
AMAP_CITY = "440118"       # 广州增城
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35561d77-a386-4401-9d60-f4202c539cee"

# ─── 星期映射（高德 week: 1=周一 .. 7=周日）─────────────
WEEKDAY_CN = {
    "1": "周一", "2": "周二", "3": "周三", "4": "周四",
    "5": "周五", "6": "周六", "7": "周日",
}

# ─── 高德天气现象 → emoji 映射 ──────────────────────────
WEATHER_EMOJI = {
    "晴": "☀️",
    "少云": "🌤️",
    "晴间多云": "🌤️",
    "多云": "⛅",
    "阴": "☁️",
    "小雨": "🌧️",
    "中雨": "🌧️",
    "大雨": "🌧️",
    "暴雨": "⛈️",
    "大暴雨": "⛈️",
    "特大暴雨": "⛈️",
    "雷阵雨": "⛈️",
    "雷阵雨伴有冰雹": "⛈️",
    "雨夹雪": "🌨️",
    "小雪": "🌨️",
    "中雪": "🌨️",
    "大雪": "🌨️",
    "暴雪": "🌨️",
    "阵雨": "🌦️",
    "冻雨": "🌧️",
    "浮尘": "🌫️",
    "扬沙": "🌫️",
    "沙尘暴": "🌫️",
    "雾": "🌫️",
    "霾": "🌫️",
    "风": "💨",
}


# ══════════════════════════════════════════════════════════
# 高德天气 API（主数据源）
# ══════════════════════════════════════════════════════════

def fetch_amap_current() -> dict | None:
    """获取高德实况天气（extensions=base）。

    返回字段：weather, temperature, humidity, winddirection, windpower, reporttime
    文档：https://developer.amap.com/api/webservice/guide/api/weatherinfo/
    """
    url = (
        f"https://restapi.amap.com/v3/weather/weatherInfo"
        f"?city={AMAP_CITY}&key={AMAP_KEY}&extensions=base"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"获取高德实况天气失败: {e}", file=sys.stderr)
        return None

    if data.get("status") == "1" and data.get("lives"):
        return data["lives"][0]

    print(f"高德实况天气返回异常: {data}", file=sys.stderr)
    return None


def fetch_amap_forecast() -> dict | None:
    """获取高德预报天气（extensions=all），返回今日预报。

    返回字段：dayweather, nightweather, daytemp, nighttemp, daywind, nightwind,
             daypower, nightpower, date, week
    """
    url = (
        f"https://restapi.amap.com/v3/weather/weatherInfo"
        f"?city={AMAP_CITY}&key={AMAP_KEY}&extensions=all"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"获取高德预报天气失败: {e}", file=sys.stderr)
        return None

    if data.get("status") == "1" and data.get("forecasts"):
        casts = data["forecasts"][0].get("casts", [])
        if casts:
            return casts[0]

    print(f"高德预报天气返回异常: {data}", file=sys.stderr)
    return None


# ══════════════════════════════════════════════════════════
# wttr.in（补充数据源 — 仅降雨概率）
# ══════════════════════════════════════════════════════════

def fetch_rain_probability() -> dict | None:
    """从 wttr.in 获取逐小时降雨概率，仅用于出货提醒决策。

    返回：morning_rain (6-12时最大概率), afternoon_rain (13-18时最大概率),
          all_rain (全天最大概率)
    失败或无数据时返回 None，不影响主流程。
    """
    url = "https://wttr.in/Guangzhou?format=j1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"wttr.in 降雨数据获取失败（不影响主流程）: {e}", file=sys.stderr)
        return None

    hourly = data.get("weather", [{}])[0].get("hourly", [])
    if not hourly:
        return None

    morning_rain = 0
    afternoon_rain = 0
    all_rain = 0

    for h in hourly:
        try:
            hour_num = int(h.get("time", "0")) // 100
            rain = int(h.get("chanceofrain", "0"))
        except (ValueError, TypeError):
            continue

        all_rain = max(all_rain, rain)
        if 6 <= hour_num <= 12:
            morning_rain = max(morning_rain, rain)
        elif 13 <= hour_num <= 18:
            afternoon_rain = max(afternoon_rain, rain)

    return {
        "morning_rain": morning_rain,
        "afternoon_rain": afternoon_rain,
        "all_rain": all_rain,
    }


# ══════════════════════════════════════════════════════════
# 消息构建
# ══════════════════════════════════════════════════════════

def weather_with_emoji(desc: str) -> str:
    """给高德天气描述配 emoji。"""
    for keyword, emoji in WEATHER_EMOJI.items():
        if keyword in desc:
            return f"{emoji} {desc}"
    return desc


def has_rain_keyword(weather_text: str) -> bool:
    """判断天气预报文本中是否包含降雨关键词。"""
    rain_keywords = ["雨", "暴雨", "雷暴", "雷阵", "雪"]
    return any(kw in weather_text for kw in rain_keywords)


def get_clothing_advice(day_temp_str: str) -> str:
    """根据最高温返回穿衣建议。"""
    try:
        t = int(float(day_temp_str))
    except (ValueError, TypeError):
        return ""
    if t >= 35:
        return "注意防暑降温、避免户外长时间作业"
    elif t >= 30:
        return "建议轻薄透气、注意防晒"
    elif t >= 20:
        return "温度舒适"
    elif t >= 10:
        return "建议薄外套"
    elif t >= 5:
        return "建议厚外套"
    else:
        return "注意保暖"


def get_travel_advice(day_temp_str: str, forecast: dict | None,
                       rain_data: dict | None) -> str:
    """根据天气条件返回出行建议（电动车 / 汽车）。

    优先级：降雨 > 极端温度 > 默认电动车
    """
    # 降雨判断
    rainy = False
    if rain_data and rain_data.get("all_rain", 0) >= 50:
        rainy = True
    if forecast and has_rain_keyword(forecast.get("dayweather", "")):
        rainy = True

    if rainy:
        return "🚗 出行建议：汽车（有降雨）"

    # 温度判断
    try:
        t = int(float(day_temp_str))
    except (ValueError, TypeError):
        return "🛵 出行建议：电动车"
    if t >= 35:
        return "🚗 出行建议：汽车（高温炎热）"
    elif t < 5:
        return "🚗 出行建议：汽车（低温寒冷）"

    return "🛵 出行建议：电动车"


def build_weather_message(current: dict | None, forecast: dict | None,
                          rain_data: dict | None) -> str:
    """构建完整的天气推送消息（纯文本格式）。"""
    lines = []

    # ── 标题行 ──
    lines.append("📅 每日天气提醒 — 广州增城仓")
    lines.append("")

    # ── 日期行（高德预报日期 + 星期）──
    day_temp_str = "--"
    if forecast:
        date_str = forecast.get("date", "")
        week_num = forecast.get("week", "")
        week_cn = WEEKDAY_CN.get(week_num, week_num)
        day_temp_str = forecast.get("daytemp", "--")
        if date_str:
            # 高德日期格式: 2026-06-25 → 2026年6月25日
            parts = date_str.split("-")
            if len(parts) == 3:
                date_fmt = f"{int(parts[0])}年{int(parts[1])}月{int(parts[2])}日"
                lines.append(f"📅 {date_fmt} {week_cn}")
            else:
                lines.append(f"📅 {date_str} {week_cn}")

    # ── 实况天气（高德 base）──
    if current:
        weather = current.get("weather", "--")
        temp = current.get("temperature", "--")
        humidity = current.get("humidity", "--")
        wind_dir = current.get("winddirection", "--")
        wind_power = current.get("windpower", "--")

        lines.append(f"📍 增城  |  {weather_with_emoji(weather)}")
        lines.append(f"🌡️ 当前 {temp}°C  |  湿度 {humidity}%  |  {wind_dir}风 {wind_power}级")

        if forecast:
            night_temp = forecast.get("nighttemp", "--")
            day_temp = forecast.get("daytemp", "--")
            lines.append(f"📊 {night_temp}°C ~ {day_temp}°C")
    else:
        lines.append("⚠️ 实况天气数据获取失败")

    lines.append("")

    # ── 预报详情（高德 all）──
    if forecast:
        day_weather = forecast.get("dayweather", "--")
        night_weather = forecast.get("nightweather", "--")
        day_wind = forecast.get("daywind", "--")
        day_power = forecast.get("daypower", "--")

        lines.append(f"☀️ 白天：{weather_with_emoji(day_weather)}  |  {day_wind}风 {day_power}级")
        lines.append(f"🌙 夜间：{weather_with_emoji(night_weather)}")

    # ── 降雨提醒 ──
    rain_warnings = []

    if rain_data:
        morning = rain_data["morning_rain"]
        afternoon = rain_data["afternoon_rain"]

        if morning >= 60:
            rain_warnings.append(f"⚠️ 上午降雨概率 {morning}%，建议提前安排出货")
        elif morning >= 30:
            rain_warnings.append(f"🌂 上午降雨概率 {morning}%，建议备雨布")

        if afternoon >= 60:
            rain_warnings.append(f"⚠️ 下午降雨概率 {afternoon}%，关注出货节奏")
        elif afternoon >= 30:
            rain_warnings.append(f"🌂 下午降雨概率 {afternoon}%，建议备雨布")

    elif forecast:
        day_w = forecast.get("dayweather", "")
        if has_rain_keyword(day_w):
            rain_warnings.append(f"🌂 今日预报 {day_w}，请关注仓库防潮与出货安排")

    if rain_warnings:
        lines.append("")
        lines.extend(rain_warnings)

    # ── 穿衣建议 ──
    clothing = get_clothing_advice(day_temp_str)
    if clothing:
        lines.append(f"👔 {clothing}")

    # ── 出行建议 ──
    travel = get_travel_advice(day_temp_str, forecast, rain_data)
    lines.append(travel)

    lines.append("")
    lines.append("—" * 20)
    lines.append("💡 雨天请关注仓库防潮、出货节奏调整。")
    lines.append("科捷物流 · 自动推送")
    lines.append("")

    # 实际推送时间戳（北京时间）
    from datetime import datetime, timezone, timedelta
    now_bj = datetime.now(timezone.utc) + timedelta(hours=8)
    lines.append(f"⏰ {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# 企微推送
# ══════════════════════════════════════════════════════════

def push_to_wechat(content: str) -> bool:
    """推送文本消息到企业微信群机器人。"""
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
        print(f"推送失败: {e}", file=sys.stderr)
        return False


# ══════════════════════════════════════════════════════════
# SCF 入口 / 主入口
# ══════════════════════════════════════════════════════════

def main_handler(event, context):
    """SCF 入口（兼容旧版腾讯云函数调用签名）。"""
    return main()


def main():
    # 并行获取三路数据（高德实况 + 高德预报 + wttr 降雨概率）
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_current = executor.submit(fetch_amap_current)
        fut_forecast = executor.submit(fetch_amap_forecast)
        fut_rain = executor.submit(fetch_rain_probability)

        current = fut_current.result()
        forecast = fut_forecast.result()
        rain_data = fut_rain.result()

    # 高德两路全失败才退出（wttr 失败不影响主流程）
    if current is None and forecast is None:
        print("高德天气 API 全部失败，跳过推送", file=sys.stderr)
        return {"status": "fail", "reason": "all amap APIs failed"}

    # 构建消息并推送
    message = build_weather_message(current, forecast, rain_data)
    success = push_to_wechat(message)

    if success:
        print(f"✅ 天气提醒推送成功\n\n{message}")
        return {"status": "ok"}
    else:
        print("❌ 推送失败", file=sys.stderr)
        return {"status": "fail", "reason": "push failed"}


# ══════════════════════════════════════════════════════════
# 本地调试
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
