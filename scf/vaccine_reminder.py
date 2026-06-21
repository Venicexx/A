# -*- coding: utf-8 -*-
"""
腾讯云 SCF 疫苗提醒函数
每周一 8:00 检查免费疫苗 → 到期前推送企微
"""

import json
import urllib.request
import urllib.error
from datetime import date, timedelta

# ─── 配置 ─────────────────────────────────────
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0e0f59cb-0991-4898-b60e-6e99eb365d96"
BIRTH_DATE  = date(2025, 4, 12)          # 宝宝生日
REMIND_DAYS  = [7, 14, 30]               # 提前多少天提醒

# ─── 免费疫苗时间表（国家免疫规划）─────────────
# (月龄, 疫苗名称, 是否已接种)
# 1月龄内由医院完成，不在这里提醒
SCHEDULE = [
    # 1岁内（应已完成，仅作记录）
    (2,  "脊灰灭活 IPV 第1剂",       True),
    (3,  "脊灰灭活 IPV 第2剂 + 百白破 DTaP 第1剂", True),
    (4,  "脊灰减毒 bOPV 第3剂 + 百白破 DTaP 第2剂", True),
    (5,  "百白破 DTaP 第3剂",        True),
    (6,  "乙肝第3剂 + A群流脑多糖第1剂", True),
    (8,  "麻腮风 MMR 第1剂 + 乙脑减毒第1剂", True),
    (9,  "A群流脑多糖第2剂",          False),  # 未接种！
    # 待接种
    (18, "百白破 DTaP 第4剂 + 麻腮风 MMR 第2剂 + 甲肝灭活第1剂", False),
    (24, "乙脑减毒第2剂 + 甲肝灭活第2剂", False),
    (36, "A群C群流脑多糖第1剂",        False),
    (48, "脊灰减毒 bOPV 第4剂",        False),
    (72, "白破 DT + A群C群流脑多糖第2剂", False),
]

# ─── 接种点 ────────────────────────────────────
LOCATION = "增城区妇幼保健院（荔城街健生路1号）"
BRING    = "预防接种证、宝宝医保卡"


def get_due_vaccines(today: date) -> list[dict]:
    """返回需要在未来提醒的疫苗列表"""
    results = []
    for months, name, done in SCHEDULE:
        if done:
            continue
        target = date(BIRTH_DATE.year + (BIRTH_DATE.month + months - 1) // 12,
                      (BIRTH_DATE.month + months - 1) % 12 + 1,
                      BIRTH_DATE.day)
        days_left = (target - today).days
        if days_left < 0:
            results.append({"name": name, "target": target, "days": days_left, "overdue": True})
        elif days_left <= max(REMIND_DAYS):
            results.append({"name": name, "target": target, "days": days_left, "overdue": False})
    return results


def build_message(due: list[dict]) -> str:
    lines = ["💉 宝宝疫苗提醒", ""]
    age_months = (date.today() - BIRTH_DATE).days // 30
    lines.append(f"👶 月龄：{age_months} 个月 | 📍 {LOCATION}")
    lines.append("")

    overdue = [v for v in due if v["overdue"]]
    upcoming = [v for v in due if not v["overdue"]]

    if overdue:
        lines.append("⚠️ 已超期，请尽快预约：")
        for v in overdue:
            lines.append(f"　🔴 {v['name']}（应于 {v['target'].strftime('%Y-%m-%d')} 接种）")
        lines.append("")

    if upcoming:
        lines.append("📅 即将到期：")
        for v in upcoming:
            lines.append(f"　🟡 {v['name']} — {v['target'].strftime('%Y-%m-%d')}（{v['days']}天后）")
        lines.append("")

    if not overdue and not upcoming:
        next_v = None
        for months, name, done in SCHEDULE:
            if not done:
                next_v = (name, months)
                break
        if next_v:
            target = date(BIRTH_DATE.year + (BIRTH_DATE.month + next_v[1] - 1) // 12,
                          (BIRTH_DATE.month + next_v[1] - 1) % 12 + 1,
                          BIRTH_DATE.day)
            d = (target - date.today()).days
            lines.append(f"✅ 近期无到期疫苗")
            lines.append(f"📌 下一针：{next_v[0]} — {target.strftime('%Y-%m-%d')}（{d}天后）")
        lines.append("")

    lines.append(f"📋 携带：{BRING}")
    lines.append("💡 接种前确认宝宝无发热、无急性疾病")
    lines.append("")
    lines.append("科捷物流 · 育婴助手自动推送")
    return "\n".join(lines)


def push_wechat(content: str) -> bool:
    payload = {"msgtype": "text", "text": {"content": content}}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(WEBHOOK_URL, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")).get("errcode") == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main_handler(event, context):
    today = date.today()
    due = get_due_vaccines(today)
    msg = build_message(due)
    ok = push_wechat(msg)
    print("推送结果:", "成功" if ok else "失败")
    return {"status": "ok" if ok else "fail"}


if __name__ == "__main__":
    main_handler({}, {})
