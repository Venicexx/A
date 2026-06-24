#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
家庭重要日期提醒
每周一 12:00（北京时间）推送 → 企微

生日数据基于农历每年更新阳历日期。
"""

import json
import os
import sys
import urllib.request
from datetime import date, timedelta

# ─── 配置 ─────────────────────────────────────
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0e0f59cb-0991-4898-b60e-6e99eb365d96"

# ─── 家庭重要日期数据 ─────────────────────────
# 生日（农历 → 当前年份阳历，每年手动更新）
# 农历: 用户六月初六, 妈妈二月初四, 柳清二月十五,
#       钰宁三月十五, 爸爸三月十七
BIRTHDAYS = [
    ("👨 你（自己）",  date(2026, 7, 19),  "六月初六"),
    ("👩 妈妈",        date(2026, 3, 22),  "二月初四"),
    ("💑 柳清",        date(2026, 4, 2),   "二月十五"),
    ("👶 钰宁",        date(2026, 5, 1),   "三月十五"),
    ("👨 爸爸",        date(2026, 5, 3),   "三月十七"),
]

# 纪念日（阳历）
ANNIVERSARY = (8, 28)   # 结婚纪念日 8月28日

# 证件到期
ID_EXPIRY = date(2027, 7, 14)   # 身份证到期日


def today_beijing() -> date:
    """获取北京时间日期"""
    from datetime import timezone, datetime
    utc_now = datetime.now(timezone.utc)
    beijing = utc_now + timedelta(hours=8)
    return beijing.date()


def send_wechat(content: str) -> bool:
    """推送消息到企微"""
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


def build_message(today: date) -> str:
    """组装推送消息"""
    lines = []
    lines.append("📅 家庭重要日期提醒")
    lines.append("━" * 24)
    lines.append("")

    year = today.year
    upcoming = []      # 30天内的日期
    general_info = []  # 一般备忘

    # ── 生日检查 ──
    for name, bd, lunar in BIRTHDAYS:
        # 如果今年生日已过，检查明年
        target = bd.replace(year=year)
        if target < today:
            target = target.replace(year=year + 1)
        diff = (target - today).days

        if diff <= 30:
            if diff == 0:
                upcoming.append(f"🎂 {name} 生日 **今天**！({lunar})")
            else:
                upcoming.append(f"🎂 {name} 生日 {target}（{lunar}）— 还有 {diff} 天")
        else:
            general_info.append(f"🎂 {name}：{bd}（{lunar}）")

    # ── 纪念日检查 ──
    anniv = date(year, ANNIVERSARY[0], ANNIVERSARY[1])
    if anniv < today:
        anniv = anniv.replace(year=year + 1)
    diff = (anniv - today).days
    if diff <= 30:
        if diff == 0:
            upcoming.append("💍 结婚纪念日 **今天**！")
        else:
            upcoming.append(f"💍 结婚纪念日 {anniv} — 还有 {diff} 天")
    else:
        general_info.append(f"💍 结婚纪念日：{anniv.month}月{anniv.day}日")

    # ── 证件到期检查 ──
    id_diff = (ID_EXPIRY - today).days
    if id_diff <= 90:
        upcoming.append(f"🆔 身份证到期 {ID_EXPIRY} — 还有 {id_diff} 天，请准备换证！")
    else:
        general_info.append(f"🆔 身份证 {ID_EXPIRY} 到期（还有 {id_diff} 天）")

    # ── 月度账单提醒 ──
    rent_day = 15
    util_start, util_end = 3, 5

    # 房租：当月15号前提醒
    if today.day <= rent_day:
        upcoming.append(f"💰 房租 — 每月{rent_day}号（本月{today.year}年{today.month}月{rent_day}日）")
    else:
        # 下月提醒
        general_info.append(f"💰 房租：每月{rent_day}号")

    # 水电：每月3-5号出账
    if today.day <= util_end or today.day >= 28:
        upcoming.append(f"💡 水电燃气 — 每月{util_start}-{util_end}号出账")
    else:
        general_info.append(f"💡 水电燃气：每月{util_start}-{util_end}号出账")

    # ── 组装 ──
    if upcoming:
        lines.append("🔥 近期提醒")
        for item in upcoming:
            lines.append(f"  {item}")
        lines.append("")

    if general_info:
        lines.append("📋 其他备忘")
        for item in general_info:
            lines.append(f"  {item}")
        lines.append("")

    if not upcoming:
        lines.append("✅ 本月暂无临近的重要日期。")
        lines.append("")

    lines.append("━" * 24)
    return "\n".join(lines)


def main():
    today = today_beijing()
    print(f"[INFO] 家庭日期提醒 — {today}")

    msg = build_message(today)
    print(msg)

    ok = send_wechat(msg)
    print(f"[{'OK' if ok else 'FAIL'}] 推送{'成功' if ok else '失败'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
