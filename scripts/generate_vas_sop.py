from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import os

# 核心配置
IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

STEPS = [
    ("①", "用刀划开原装箱"),
    ("②", "取出一台销售包装"),
    ("③", "用小刀划开封口贴"),
    ("④", "取出旧手册和说明书"),
    ("⑤", "放入新手册和说明书"),
    ("⑥", "还原包装贴上封口贴"),
    ("⑦", "将货物装回箱中"),
]

# 工位分配: {人数: [(工位标签, 步数范围)]}
WORKER_ALLOCATION = {
    1: [("单人", [0, 1, 2, 3, 4, 5, 6])],
    2: [("A", [0, 1, 2, 3]), ("B", [4, 5, 6])],
    3: [("A", [0, 1, 2]), ("B", [3, 4]), ("C", [5, 6])],
    4: [("A", [0, 1]), ("B", [2, 3]), ("C", [4, 5]), ("D", [6])],
}

IMAGES = [
    ("割开封口.jpg", [2]),         # 步骤③
    ("合格证和设备下方的旧产品使用说明书.jpg", [3]),  # 步骤④
    ("设备上方的旧操作说明.jpg", [3]),               # 步骤④
    ("新的操作说明和产品使用说明书.jpg", [4]),       # 步骤⑤
]

QUALITY_NOTES = [
    "不得损坏销售包装",
    "勿遗失三角形合格证",
    "封口贴须贴正、贴牢",
    "新旧手册不得混淆",
]

TOOLS = ["美工刀（含备用刀片）", "封口贴", "新操作手册", "新产品使用说明书", "废料回收箱"]


def set_page_a4_landscape(doc):
    """设置文档为A4横向"""
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.top_margin = Cm(0.6)
    section.bottom_margin = Cm(0.6)
    section.left_margin = Cm(0.8)
    section.right_margin = Cm(0.8)


def _fill_matrix(table, allocation, worker_labels, num_workers):
    """填充矩阵表数据"""
    # 标题行
    hdr = table.rows[0]
    hdr.cells[0].text = ""
    run = hdr.cells[0].paragraphs[0].add_run("步骤")
    run.bold = True
    run.font.size = Pt(8)
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    for i, label in enumerate(worker_labels):
        cell = hdr.cells[i + 1]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(f"工位\n{label}")
        run.bold = True
        run.font.size = Pt(8)
        run.font.name = "微软雅黑"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    # 填充颜色函数
    def set_cell_shading(cell, color):
        shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
        cell._tc.get_or_add_tcPr().append(shading_elm)

    # 数据行 (步骤1-7)
    for step_idx, (step_num, step_desc) in enumerate(STEPS):
        row = table.rows[step_idx + 1]
        cell = row.cells[0]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(f"{step_num}  {step_desc}")
        run.font.size = Pt(7)
        run.font.name = "微软雅黑"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)

        for w_idx, (_, step_range) in enumerate(allocation):
            cell = row.cells[w_idx + 1]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if step_idx in step_range:
                run = p.add_run("✓")
                run.font.size = Pt(10)
                set_cell_shading(cell, "E8F5E9")
            else:
                run = p.add_run("—")
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(200, 200, 200)

        # 设置列宽（每行重复确保生效）
        row.cells[0].width = Cm(4.0)
        for ci in range(1, len(row.cells)):
            row.cells[ci].width = Cm(1.8)

    # 末行: 动作数统计
    last_row = table.rows[8]
    cell = last_row.cells[0]
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run("动作数")
    run.bold = True
    run.font.size = Pt(8)

    for w_idx, (_, step_range) in enumerate(allocation):
        cell = last_row.cells[w_idx + 1]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(len(step_range)))
        run.bold = True
        run.font.size = Pt(8)
        run.font.name = "微软雅黑"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")


def add_header(doc, num_workers):
    """添加顶栏标题"""
    title_text = f"增值服务 · 操作手册与说明书置换作业指导卡    {num_workers}人版"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title_text)
    run.bold = True
    run.font.size = Pt(14)
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    # 参数信息行
    info_text = f"客户：中移物流　　地点：广东仓库　　每箱：20台　　版本：{num_workers}人版"
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run(info_text)
    run2.font.size = Pt(8)
    run2.font.name = "微软雅黑"
    run2._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")


def generate_sop(num_workers, output_path):
    """生成指定人数版本的SOP"""
    if num_workers not in WORKER_ALLOCATION:
        raise ValueError(f"不支持 {num_workers}人版，仅支持 1/2/3/4")
    doc = Document()
    set_page_a4_landscape(doc)
    add_header(doc, num_workers)

    # 主体用一个 1行2列 的容器表: 左矩阵 | 右图片
    container = doc.add_table(rows=1, cols=2)
    container.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 容器表隐藏边框
    tbl = container._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}/>')
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'  <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

    # 设置列宽
    container.columns[0].width = Cm(15.0)
    container.columns[1].width = Cm(10.5)

    # 设置容器表所有单元格无内边距
    for row in container.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcMar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                f'  <w:top w:w="0" w:type="dxa"/>'
                f'  <w:left w:w="30" w:type="dxa"/>'
                f'  <w:bottom w:w="0" w:type="dxa"/>'
                f'  <w:right w:w="30" w:type="dxa"/>'
                f'</w:tcMar>'
            )
            tcPr.append(tcMar)

    # === 左侧单元格：直接在单元格内构建矩阵表（通过XML追加） ===
    left_cell = container.cell(0, 0)
    # 清空默认段落
    p_left = left_cell.paragraphs[0]
    p_left.text = ""
    p_left.paragraph_format.space_before = Pt(0)
    p_left.paragraph_format.space_after = Pt(0)

    # 构建矩阵表（直接添加到主文档，再移动到单元格）
    allocation = WORKER_ALLOCATION[num_workers]
    worker_labels = [w[0] for w in allocation]
    num_cols = 1 + len(worker_labels)
    m_table = doc.add_table(rows=9, cols=num_cols)
    m_table.style = 'Table Grid'
    m_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _fill_matrix(m_table, allocation, worker_labels, num_workers)
    # 将矩阵表移动到左单元格，并从body移除
    left_cell._tc.append(m_table._tbl)

    # === 右侧单元格：直接在单元格内构建图片网格 ===
    right_cell = container.cell(0, 1)
    p_right = right_cell.paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_right.paragraph_format.space_before = Pt(0)
    p_right.paragraph_format.space_after = Pt(0)

    # 在单元格中直接添加图片
    for idx, (img_filename, step_numbers) in enumerate(IMAGES):
        if idx > 0 and idx % 2 == 0:
            # 每2张图后新建段落（换行）
            p_right = right_cell.add_paragraph()
            p_right.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_right.paragraph_format.space_before = Pt(0)
            p_right.paragraph_format.space_after = Pt(0)

        img_path = os.path.join(IMAGE_DIR, img_filename)
        step_label = f"[步骤{'/'.join(str(s+1) for s in step_numbers)}]"

        # 添加步骤标签（与图片同行，先加标签）
        run = p_right.add_run(step_label)
        run.font.size = Pt(6)
        run.bold = True
        run.font.color.rgb = RGBColor(0x19, 0x76, 0xD2)

        if "合格证" in img_filename:
            run2 = p_right.add_run(" !勿遗失")
            run2.font.size = Pt(6)
            run2.bold = True
            run2.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)

        # 换行加入图片
        p_right.add_run("\n")
        if os.path.exists(img_path):
            run_img = p_right.add_run()
            run_img.add_picture(img_path, width=Cm(3.5))
        else:
            print(f"⚠️ 图片文件未找到: {img_path}")
        # 图片后加空隔
        if idx < len(IMAGES) - 1:
            p_right.add_run("  ")

    # === 脚注（在容器表下方） ===
    p_footer = doc.add_paragraph()
    p_footer.paragraph_format.space_before = Pt(2)
    p_footer.paragraph_format.space_after = Pt(0)
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    tool_text = "  ".join([f"□ {t}" for t in TOOLS])
    quality_text = "  |  ".join([f"• {n}" for n in QUALITY_NOTES])
    run = p_footer.add_run(f"作业准备: {tool_text}")
    run.font.size = Pt(7)
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    run = p_footer.add_run(f"　　质量标准: {quality_text}")
    run.font.size = Pt(7)
    run.font.name = "微软雅黑"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    p_ver = doc.add_paragraph()
    p_ver.paragraph_format.space_before = Pt(1)
    p_ver.paragraph_format.space_after = Pt(0)
    p_ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_ver.add_run("v1.0  编制日期：2026-06-24  编制：科捷物流")
    run.font.size = Pt(6)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    doc.save(output_path)
    print(f" SOP文档已生成: {output_path}")


def generate_all_versions():
    """生成1-4人版全部SOP"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for n in [1, 2, 3, 4]:
        output_path = os.path.join(OUTPUT_DIR, f"VAS_SOP_{n}人版.docx")
        generate_sop(n, output_path)
    print(f"\n 全部版本已生成到: {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all_versions()
