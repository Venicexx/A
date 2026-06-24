"""一次性脚本：基于 BC端库存报表22日.xlsx 生成模板文件。

模板规则：
- 收货记录查询、总库存、出库全流程：保留第1行(表头) + 第2行(公式)，删除第3行及之后所有数据
- 收货记录查询高级筛选、出库全流程高级筛选：保留第1行(表头，供列映射读取)，清空其余数据
- 匹配条件、广东省仓库存报表 等其余子表：原样保留
"""

import openpyxl
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "BC端库存报表22日.xlsx"
DST = BASE / "data" / "template" / "BC端库存报表模板.xlsx"

# 需要清理数据的子表及其保留行数
CLEAR_SHEETS = {
    "收货记录查询": 2,        # 保留前2行(表头+公式)
    "总库存": 2,
    "出库全流程": 2,
    "收货记录查询高级筛选": 1,  # 只保留表头
    "出库全流程高级筛选": 1,
}

wb = openpyxl.load_workbook(SRC)

for name, keep_rows in CLEAR_SHEETS.items():
    ws = wb[name]
    max_row = ws.max_row
    if max_row > keep_rows:
        # 删除 keep_rows+1 到 max_row 的所有行
        ws.delete_rows(keep_rows + 1, max_row - keep_rows)
        print(f"[{name}] 已清空 {max_row - keep_rows} 行数据，保留前 {keep_rows} 行")

wb.save(DST)
print(f"\n模板已生成: {DST}")
