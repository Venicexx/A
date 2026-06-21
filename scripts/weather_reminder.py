#!/usr/bin/env python3
"""
科捷物流每日天气提醒脚本
获取广州、佛山天气，推送到企业微信群
"""

import json
import urllib.request
import urllib.error
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows GBK 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── 天气描述中英对照 ────────────────────────────
WEATHER_CN = {
    "Sunny": "☀️ 晴天",
    "Clear": "🌙 晴朗",
    "Partly cloudy": "⛅ 多云",
    "Cloudy": "☁️ 阴天",
    "Overcast": "☁️ 阴天",
    "Mist": "🌫️ 薄雾",
    "Fog": "🌫️ 大雾",
    "Light rain": "🌧️ 小雨",
    "Light drizzle": "🌧️ 毛毛雨",
    "Patchy rain possible": "🌦️ 局部阵雨",
    "Patchy light rain": "🌦️ 局部小雨",
    "Moderate rain": "🌧️ 中雨",
    "Moderate rain at times": "🌧️ 间歇中雨",
    "Heavy rain": "🌧️ 大雨",
    "Heavy rain at times": "🌧️ 间歇大雨",
    "Light rain shower": "🌦️ 小阵雨",
    "Torrential rain shower": "⛈️ 暴雨",
    "Thunderstorm": "⛈️ 雷暴",
    "Thundery outbreaks possible": "⛈️ 可能有雷暴",
    "Patchy light rain with thunder": "⛈️ 雷阵雨",
    "Moderate or heavy rain with thunder": "⛈️ 强雷雨",
}

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35561d77-a386-4401-9d60-f4202c539cee"


def fetch_weather(city_en: str) -> dict | None:
    """从 wttr.in 获取天气数据"""
    url = f"https://wttr.in/{city_en}?format=j1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"获取 {city_en} 天气失败: {e}", file=sys.stderr)
        return None


def format_temp(c: str) -> str:
    """格式化温度"""
    try:
        t = int(float(c))
        return f"{t}°C"
    except (ValueError, TypeError):
        return f"{c}°C"


def translate_weather(desc: str) -> str:
    """翻译天气描述为中文"""
    return WEATHER_CN.get(desc, desc)


def build_weather_card(city_cn: str, data: dict) -> str:
    """根据天气数据构建一段城市天气文本"""
    cc = data["current_condition"][0]
    weather_info = data["weather"][0]
    hourly = weather_info["hourly"]

    desc_en = cc["weatherDesc"][0]["value"]
    desc_cn = translate_weather(desc_en)
    temp = format_temp(cc["temp_C"])
    feels = format_temp(cc["FeelsLikeC"])
    humidity = cc["humidity"]
    wind = cc["windspeedKmph"]
    wind_dir = cc["winddir16Point"]
    uv = cc["uvIndex"]

    # 当天最高/最低温
    hi = format_temp(weather_info.get("maxtempC", "--"))
    lo = format_temp(weather_info.get("mintempC", "--"))

    # 单次遍历计算上午雨概率和全天最高雨概率
    morning_rain = 0
    all_rain = 0
    for h in hourly:
        try:
            hour_num = int(h.get("time", "0")) // 100
            rain = int(h.get("chanceofrain", "0"))
            if 6 <= hour_num <= 12:
                morning_rain = max(morning_rain, rain)
            all_rain = max(all_rain, rain)
        except (ValueError, TypeError):
            pass

    lines = []
    lines.append(f"📍 **{city_cn}**  |  {desc_cn}")
    lines.append(f"🌡️ 当前 {temp}（体感 {feels}） | 湿度 {humidity}% | UV {uv}")
    lines.append(f"📊 今日 {lo} ~ {hi}")
    lines.append(f"🌬️ {wind_dir}风 {wind}km/h")

    if morning_rain >= 60:
        lines.append(f"⚠️ 上午降雨概率 {morning_rain}%，建议提前安排出货")
    elif morning_rain >= 30:
        lines.append(f"🌂 上午降雨概率 {morning_rain}%，建议备雨布")
    elif all_rain >= 60:
        lines.append(f"🌂 今日降雨概率 {all_rain}%，关注下午天气变化")

    return "\n".join(lines)


def build_full_message(cities_data: list[tuple[str, str, dict]]) -> str:
    """构建完整的推送消息"""
    lines = []
    lines.append("📅 **每日天气提醒**")
    lines.append("")

    for city_cn, _, data in cities_data:
        if data:
            lines.append(build_weather_card(city_cn, data))
            lines.append("")

    lines.append("—" * 20)
    lines.append("💡 雨天请关注仓库防潮、出货节奏调整。")
    lines.append("科捷物流 · 自动推送")

    return "\n".join(lines)


def push_to_wechat(content: str) -> bool:
    """推送消息到企业微信"""
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
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


def main():
    # 城市列表：英文名、中文名
    cities = [
        ("Guangzhou", "广州仓（花都/黄埔）"),
        ("Foshan", "佛山仓（禅城/顺德）"),
    ]

    # 并行获取所有城市天气
    results = []
    with ThreadPoolExecutor(max_workers=len(cities)) as executor:
        future_map = {executor.submit(fetch_weather, en): (cn, en) for en, cn in cities}
        for future in as_completed(future_map):
            cn, en = future_map[future]
            try:
                data = future.result()
            except Exception:
                data = None
            results.append((cn, en, data))

    if all(d is None for _, _, d in results):
        print("所有城市天气获取失败，跳过推送", file=sys.stderr)
        sys.exit(1)

    message = build_full_message(results)
    success = push_to_wechat(message)

    if success:
        print("✅ 天气提醒推送成功")
    else:
        print("❌ 推送失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
