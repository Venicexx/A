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
