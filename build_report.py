#!/usr/bin/env python3
"""
BC端库存报表自动生成脚本。

用法：
    python build_report.py

流程：
    1. 扫描 data/input/ 下的 Excel 文件
    2. 按子表名识别数据类型（不依赖文件名）
    3. 从模板读取目标列清单，按表头名称匹配重排
    4. 打印校验报告，等待用户确认
    5. 写入模板副本，自动填充公式
    6. 输出到 data/output/，原始文件归档
"""

import openpyxl
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from collections import defaultdict

# ============================================================
# 常量
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "input"
TEMPLATE_PATH = BASE_DIR / "data" / "template" / "BC端库存报表模板.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "output"
ARCHIVE_DIR = BASE_DIR / "data" / "archive"

# 导出子表名 → 内部标识
SHEET_TYPE_MAP = {
    "收货记录表": "inbound",
    "库存汇总查询": "inventory",
    "出库全流程记录": "outbound",
}

# 每类数据的配置：模板中的(子表名, 目标列清单来源子表, 写入起始列, 公式列)
TYPE_CONFIG = {
    "inbound": {
        "target_sheet": "收货记录查询",
        "column_source_sheet": "收货记录查询高级筛选",
        "column_source_range": "A",       # 从 A 列开始读目标列名
        "write_start_col": 5,             # E 列 = 5
        "formula_cols": [1, 2, 3, 4],     # A-D 列
    },
    "inventory": {
        "target_sheet": "总库存",
        "column_source_sheet": "总库存",
        "column_source_range": "F",        # 从 F 列开始读目标列名
        "write_start_col": 6,              # F 列 = 6
        "formula_cols": [1, 2, 3, 4, 5],  # A-E 列
    },
    "outbound": {
        "target_sheet": "出库全流程",
        "column_source_sheet": "出库全流程高级筛选",
        "column_source_range": "A",
        "write_start_col": 5,              # E 列 = 5
        "formula_cols": [1, 2, 3, 4],     # A-D 列
    },
}


# ============================================================
# 扫描 & 识别
# ============================================================

def scan_input_files(input_dir: Path) -> list[Path]:
    """扫描 input 目录，返回所有 xlsx/xls 文件路径列表。"""
    files = []
    for pattern in ["*.xlsx", "*.xls"]:
        files.extend(input_dir.glob(pattern))
    # 排除临时文件（~$ 开头）
    files = [f for f in files if not f.name.startswith("~$")]
    return sorted(files)


def identify_data_type(wb: openpyxl.Workbook) -> str | None:
    """根据工作簿的子表名识别数据类型。

    遍历 SHEET_TYPE_MAP，只要工作簿中存在匹配的子表即返回对应类型。
    返回 None 表示无法识别。
    """
    sheet_names = set(wb.sheetnames)
    for sheet_name, dtype in SHEET_TYPE_MAP.items():
        if sheet_name in sheet_names:
            return dtype
    return None


# ============================================================
# 列映射 & 重排
# ============================================================

def read_target_columns(wb: openpyxl.Workbook, dtype: str) -> list[str]:
    """从模板读取目标列清单。

    读取规则：
    - inbound: 收货记录查询高级筛选 的 A-AG 列（读到第一个空列为止）
    - inventory: 总库存 的 F-W 列
    - outbound: 出库全流程高级筛选 的 A-BO 列（读到第一个空列为止）

    返回列名列表，顺序与模板一致。
    """
    config = TYPE_CONFIG[dtype]
    source_sheet = config["column_source_sheet"]
    source_range = config["column_source_range"]
    ws = wb[source_sheet]

    # 确定起始列号
    start_col = openpyxl.utils.column_index_from_string(source_range)

    columns = []
    for c in range(start_col, ws.max_column + 1):
        val = ws.cell(row=1, column=c).value
        if val is None:
            # 对于 A 列起始的，遇到空列停止；对于 F 列起始的，读到 W 列位置后如果为空也停止
            break
        columns.append(str(val).strip())

    return columns


def match_and_reorder(
    source_ws: openpyxl.worksheet.worksheet.Worksheet,
    target_columns: list[str],
) -> tuple[list[list], dict]:
    """将源子表列按目标列清单匹配并重排。

    参数:
        source_ws: 导出文件的数据子表
        target_columns: 目标列名清单（有序）

    返回:
        (reordered_data, match_report)
        reordered_data: list[list] 重排后的数据行（每行长度 = len(target_columns)）
        match_report: {
            "matched": int,       # 匹配成功列数
            "missing": list[str], # 目标有但导出无的列名
            "extra": list[str],   # 导出有但目标无的列名
        }
    """
    # 读取导出文件的表头（第1行）
    source_headers = []
    header_col_map = {}  # 列名 → 列号(1-based)
    for c in range(1, source_ws.max_column + 1):
        val = source_ws.cell(row=1, column=c).value
        if val is not None:
            name = str(val).strip()
            source_headers.append(name)
            header_col_map[name] = c

    # 建立映射：目标列名 → 源文件列号(None 表示缺失)
    col_mapping: list[int | None] = []
    missing = []
    for tc in target_columns:
        if tc in header_col_map:
            col_mapping.append(header_col_map[tc])
        else:
            col_mapping.append(None)
            missing.append(tc)

    # 导出中有但目标清单没有的列
    target_set = set(target_columns)
    extra = [h for h in source_headers if h not in target_set]

    # 重排数据行（跳过表头行 1）
    reordered_data = []
    for r in range(2, source_ws.max_row + 1):
        row = []
        has_data = False
        for src_col in col_mapping:
            if src_col is not None:
                val = source_ws.cell(row=r, column=src_col).value
                row.append(val)
                if val is not None:
                    has_data = True
            else:
                row.append(None)
        if has_data:  # 跳过全空行
            reordered_data.append(row)

    return reordered_data, {
        "matched": len(target_columns) - len(missing),
        "missing": missing,
        "extra": extra,
    }


# ============================================================
# 校验报告模块
# ============================================================

def generate_validation_report(results: dict) -> str:
    """根据收集的数据生成校验报告文本。

    参数:
        results: {
            dtype: {
                "files": [Path, ...],
                "total_rows": int,
                "match_report": dict,      # 来自 match_and_reorder
                "data": list[list],        # 重排后的数据
            }
        }

    返回: 格式化的中文校验报告字符串
    """
    lines = []
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    lines.append(f"{'='*50}")
    lines.append(f"  数据校验报告 ({yesterday})")
    lines.append(f"{'='*50}")

    type_names = {
        "inbound": "收货记录表",
        "inventory": "库存汇总查询",
        "outbound": "出库全流程记录",
    }

    for dtype in ["inbound", "inventory", "outbound"]:
        if dtype not in results:
            lines.append(f"\n【{type_names[dtype]}】❌ 未找到数据")
            continue

        r = results[dtype]
        files = r["files"]
        data = r["data"]
        mr = r["match_report"]
        name = type_names[dtype]

        lines.append(f"\n【{name}】({len(files)} 个文件，共 {len(data)} 行)")

        # 文件名列表
        for f in files:
            lines.append(f"  📄 {f.name}")

        # 列匹配结果
        total_target = mr["matched"] + len(mr["missing"])
        if mr["missing"]:
            lines.append(f"  列匹配: ✅ {mr['matched']}/{total_target}  ⚠️ 缺失: {', '.join(mr['missing'])}")
        else:
            lines.append(f"  列匹配: ✅ {total_target}/{total_target} 全部匹配")
        if mr["extra"]:
            lines.append(f"  ℹ️ 导出多出的列(已丢弃): {', '.join(mr['extra'])}")

        # 日期范围（尝试取第1列中的日期信息）
        if data:
            first_vals = [row[0] for row in data if row[0] is not None]
            if first_vals:
                lines.append(f"  首行时间: {str(first_vals[0])[:19]}")
                lines.append(f"  末行时间: {str(first_vals[-1])[:19]}")

        # 空值统计
        if data:
            null_cols = []
            for ci in range(len(data[0])):
                null_count = sum(1 for row in data if row[ci] is None or str(row[ci]).strip() == "")
                if null_count == len(data):
                    # 全列为空
                    col_name = mr.get("target_names", [f"列{ci}"])[ci] if ci < len(mr.get("target_names", [])) else f"列{ci}"
                    null_cols.append(f"{col_name}(全空)")
            if null_cols:
                lines.append(f"  空值: {', '.join(null_cols[:5])}")

    lines.append(f"\n{'='*50}")
    return "\n".join(lines)


def extract_date_range(data: list[list], col_idx: int = 0) -> tuple[str, str] | None:
    """尝试从数据中提取日期范围。"""
    first = None
    last = None
    for row in data:
        val = row[col_idx] if col_idx < len(row) else None
        if val is not None and str(val).strip():
            last = str(val).strip()[:19]
            if first is None:
                first = last
    if first:
        return (first, last)
    return None
