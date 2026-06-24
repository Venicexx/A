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
    ("👩 岳母",        date(2026, 7, 14),  "六月初一"),
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


def safe_print(text: str):
    """兼容 Windows GBK 终端打印（替换无法显示的字符）"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))


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
    """组装推送消息 — 仅显示未过去的日期"""
    lines = []
    lines.append("📅 家庭重要日期提醒")
    lines.append("━" * 24)
    lines.append("")

    year = today.year
    upcoming = []
    MAX_DAYS = 30  # 仅提醒未来30天内的事件

    # ── 生日检查：今年未过且在30天内 ──
    for name, bd, lunar in BIRTHDAYS:
        target = bd.replace(year=year)
        if target < today:
            continue
        diff = (target - today).days
        if diff > MAX_DAYS:
            continue
        if diff == 0:
            upcoming.append(f"🎂 {name} 生日 **今天**！({lunar})")
        else:
            upcoming.append(f"🎂 {name} 生日 {target.month}月{target.day}日（{lunar}）— 还有 {diff} 天")

    # ── 纪念日：今年未过且在30天内 ──
    anniv = date(year, ANNIVERSARY[0], ANNIVERSARY[1])
    diff = (anniv - today).days
    if anniv >= today and diff <= MAX_DAYS:
        if diff == 0:
            upcoming.append("💍 结婚纪念日 **今天**！")
        else:
            upcoming.append(f"💍 结婚纪念日 {anniv.month}月{anniv.day}日 — 还有 {diff} 天")

    # ── 证件到期：30天内才显示 ──
    id_diff = (ID_EXPIRY - today).days
    if id_diff <= MAX_DAYS:
        upcoming.append(f"🆔 身份证到期 {ID_EXPIRY} — 还有 {id_diff} 天，请准备换证！")

    # ── 账单：仅当最近一期到期日在30天内 ──
    def days_until_next(target_day: int) -> int:
        """当月target_day还没过则算当月，否则算下月"""
        if today.day <= target_day:
            next_date = date(year, today.month, target_day)
        else:
            next_month = today.month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year = year + 1
            next_date = date(next_year, next_month, target_day)
        return (next_date - today).days

    rent_days = days_until_next(15)
    if rent_days <= MAX_DAYS:
        upcoming.append(f"💰 房租 — 还有 {rent_days} 天到期（每月15号）")

    util_days = days_until_next(3)
    if util_days <= MAX_DAYS:
        upcoming.append(f"💡 水电燃气 — 还有 {util_days} 天出账（每月3-5号）")

    # ── 组装 ──
    if upcoming:
        lines.append("🔥 近期提醒")
        for item in upcoming:
            lines.append(f"  {item}")
        lines.append("")

    if not upcoming:
        lines.append("✅ 未来30天暂无重要日期。")
        lines.append("")

    lines.append("━" * 24)
    lines.append("一键查看 · 每周一推送")
    return "\n".join(lines)


def main():
    today = today_beijing()
    safe_print(f"[INFO] 家庭日期提醒 — {today}")

    msg = build_message(today)
    safe_print(msg)

    ok = send_wechat(msg)
    safe_print(f"[{'OK' if ok else 'FAIL'}] 推送{'成功' if ok else '失败'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
