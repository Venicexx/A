#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每月首个周五 → 推送家庭出游推荐（珠三角一日游 / 省内两日游）
数据由 Claude 在确认后更新至 data/next_trip.json
"""

import json
import os
import sys
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
    import urllib.request
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


def main():
    today = today_beijing()

    # ── 仅在周五执行 ──
    if today.weekday() != 4:
        print(f"[SKIP] 今天不是周五 (weekday={today.weekday()})")
        return

    # ── 读取数据 ──
    if not os.path.exists(DATA_FILE):
        print(f"[WARN] 数据文件不存在: {DATA_FILE}")
        send_wechat("🚗 本月出游推荐暂未更新，等待下月吧~")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    expected = f"{today.year}-{today.month:02d}"
    actual = data.get("year_month", "")
    if actual != expected:
        print(f"[SKIP] 月份不匹配: 期望={expected}, 实际={actual}")
        return

    messages = data.get("messages", [])
    if not messages:
        print(f"[SKIP] 消息列表为空")
        return

    # ── 逐条推送（每条独立消息） ──
    all_ok = True
    for i, msg in enumerate(messages):
        if not msg.strip():
            continue
        ok = send_wechat(msg.strip())
        status = "OK" if ok else "FAIL"
        print(f"[{status}] 推送第{i+1}/{len(messages)}条 {'成功' if ok else '失败'}")
        if not ok:
            all_ok = False

    # 推送成功后清空，避免重复发送
    if all_ok:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"year_month": expected, "messages": []}, f, ensure_ascii=False, indent=2)
        print("[CLEAN] 数据已清空")


if __name__ == "__main__":
    main()
