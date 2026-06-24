#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每月首个周五 → 推送家庭出游推荐
数据由 Claude 在确认后更新至 data/next_trip.json
支持：天气适配、适幼度、行程（含美食）、出行清单、周边配套
"""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone, timedelta

# ─── 配置 ─────────────────────────────────────
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0e0f59cb-0991-4898-b60e-6e99eb365d96"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "next_trip.json")


def today_beijing() -> date:
    """获取北京时间日期"""
    utc_now = datetime.now(timezone.utc)
    beijing = utc_now + timedelta(hours=8)
    return beijing.date()


def send_wechat(content: str) -> bool:
    """推送文本消息到企微"""
    payload = {"msgtype": "text", "text": {"content": content}}
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


def safe_print(text: str):
    """兼容 Windows GBK 终端打印"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))


def render_recommendation(rec: dict, year_month: str) -> str:
    """将一条推荐渲染为富文本消息"""
    label = "主推荐" if rec["type"] == "main" else "备选"
    lines = [f"🚗 {year_month}出游推荐 · {label}"]
    lines.append("━" * 30)
    lines.append("")

    # 标题 + 地点 + 距离
    lines.append(rec["title"])
    loc = rec["destination"]
    commute = rec["commute"]
    lines.append(f"📍 {loc} | 🚗 {commute['from']}出发约{commute['drive_time']}")
    lines.append(f"📅 推荐：{rec['date_hint']}")
    lines.append("")

    # 推荐理由
    lines.append("🌟 推荐理由")
    lines.append(rec["reason"])
    lines.append("")

    # 天气适配
    w = rec["weather"]
    lines.append("🌤️ 天气适配")
    lines.append(w["forecast"])
    for a in w["advice"].split("；"):
        lines.append(f"→ {a.strip()}")
    lines.append("")

    # 适幼度
    bf = rec["baby_friendly"]
    lines.append(f"👶 适幼度：{bf['rating']}")
    for note in bf["notes"]:
        lines.append(note)
    lines.append("")

    # 行程安排
    lines.append("📋 行程安排")
    for s in rec["schedule"]:
        act = s["activity"]
        food = s.get("food", "")
        if food:
            lines.append(f"{s['time']}  {act}")
            lines.append(f"        推荐：{food}")
        else:
            lines.append(f"{s['time']}  {act}")
    lines.append("")

    # 出行清单
    lines.append("🎒 出行清单")
    items = rec["packing_list"]
    for i in range(0, len(items), 2):
        pair = items[i:i+2]
        lines.append(" | ".join(pair))
    lines.append("")

    # 周边配套
    lines.append("🍜 周边配套")
    for n in rec["nearby"]:
        lines.append(f"• {n}")

    lines.append("━" * 30)
    return "\n".join(lines)


def main():
    today = today_beijing()

    # ── 仅在周五执行 ──
    if today.weekday() != 4:
        safe_print(f"[SKIP] 今天不是周五 (weekday={today.weekday()})")
        return

    # ── 读取数据 ──
    if not os.path.exists(DATA_FILE):
        safe_print("[WARN] 数据文件不存在")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ── 月份校验 ──
    expected = f"{today.year}-{today.month:02d}"
    if data.get("year_month", "") != expected:
        safe_print(f"[SKIP] 月份不匹配: 期望={expected}, 实际={data.get('year_month')}")
        return

    # ── 已推送过则跳过 ──
    if data.get("pushed", False):
        safe_print("[SKIP] 本月已推送")
        return

    recommendations = data.get("recommendations", [])
    if not recommendations:
        safe_print("[SKIP] 推荐列表为空")
        return

    # ── 逐条推送 ──
    all_ok = True
    for i, rec in enumerate(recommendations):
        msg = render_recommendation(rec, expected)
        safe_print(f"\n--- 推送第{i+1}/{len(recommendations)}条 ---")
        safe_print(msg)
        ok = send_wechat(msg)
        safe_print(f"[{'OK' if ok else 'FAIL'}] 第{i+1}条")
        if not ok:
            all_ok = False

    # ── 全部成功则标记已推送 ──
    if all_ok:
        data["pushed"] = True
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        safe_print("[DONE] 全部推送成功，已标记已推送")


if __name__ == "__main__":
    main()
