"""
PPT 封面图生成 — 物流仓库主题 × 5月6日物流节
尺寸：1920×1080 (16:9) | DPI：300
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon, Arc, Rectangle
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# ── 中文字体 ──
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans SC']
plt.rcParams['axes.unicode_minus'] = False

# ── 配色 ──
DARK_BLUE    = '#0a1f3f'   # 深蓝底色
MID_BLUE     = '#1a3a6e'   # 中蓝
ACCENT_BLUE  = '#2B579A'   # 商务蓝
LOGISTICS_GREEN = '#007A4D'  # 中移绿
LIGHT_GREEN  = '#00a86b'   # 亮绿点缀
GOLD         = '#d4a843'   # 金色高光
WHITE        = '#ffffff'
LIGHT_GRAY   = '#e8edf2'

# ── 创建 16:9 画布 ──
W, H = 1920/300, 1080/300  # inches at 300 DPI
fig, ax = plt.subplots(figsize=(W, H), dpi=300)
ax.set_xlim(0, 1920)
ax.set_ylim(0, 1080)
ax.set_aspect('equal')
ax.axis('off')
fig.patch.set_facecolor(DARK_BLUE)

# ═══════════════════════════════════════════
# 1. 背景渐变网格（模拟仓库地面）
# ═══════════════════════════════════════════
for i in range(0, 1920, 60):
    alpha = 0.04 + 0.02 * np.sin(i / 200)
    ax.axvline(x=i, ymin=0, ymax=0.55, color=WHITE, alpha=alpha, linewidth=0.5)
for j in range(0, 580, 60):
    alpha = 0.04 + 0.02 * np.cos(j / 200)
    ax.axhline(y=j, xmin=0, xmax=1, color=WHITE, alpha=alpha, linewidth=0.5)

# ── 透视效果：从中心向外发散 ──
cx, cy = 960, 400
for angle in np.linspace(0, np.pi, 20):
    dx = np.cos(angle) * 1500
    dy = np.sin(angle) * 800
    ax.plot([cx, cx + dx], [cy, cy - dy], color=WHITE, alpha=0.03, linewidth=0.8)

# ═══════════════════════════════════════════
# 2. 底部弧形（仓库轮廓 / 地球弧线）
# ═══════════════════════════════════════════
theta = np.linspace(-0.3, np.pi + 0.3, 300)
r = 2200
earth_x = 960 - r * np.cos(theta)
earth_y = -800 + r * np.sin(theta)
ax.fill_between(earth_x, earth_y, -800, color=ACCENT_BLUE, alpha=0.15)

# 第二条弧线
r2 = 2000
earth_x2 = 960 - r2 * np.cos(theta)
earth_y2 = -750 + r2 * np.sin(theta)
ax.fill_between(earth_x2, earth_y2, -800, color=MID_BLUE, alpha=0.25)

# ═══════════════════════════════════════════
# 3. SVG 启发的几何图形 — 仓库/物流元素
# ═══════════════════════════════════════════

# ── 3a. 大型仓库轮廓（左侧） ──
warehouse_x, warehouse_y = 80, 340
# 主体
wh = Rectangle((warehouse_x, warehouse_y), 280, 200,
               facecolor=MID_BLUE, edgecolor=ACCENT_BLUE, linewidth=1.2, alpha=0.5, zorder=2)
ax.add_patch(wh)
# 屋顶三角形
roof = Polygon([(warehouse_x - 15, warehouse_y + 200),
                (warehouse_x + 140, warehouse_y + 280),
                (warehouse_x + 295, warehouse_y + 200)],
               facecolor=MID_BLUE, edgecolor=ACCENT_BLUE, linewidth=1.2, alpha=0.5, zorder=2)
ax.add_patch(roof)
# 仓库门
door = Rectangle((warehouse_x + 90, warehouse_y), 80, 80,
                 facecolor=DARK_BLUE, edgecolor=ACCENT_BLUE, linewidth=0.8, alpha=0.7, zorder=3)
ax.add_patch(door)
# 门内十字线
ax.plot([warehouse_x + 130, warehouse_x + 130], [warehouse_y, warehouse_y + 80],
        color=ACCENT_BLUE, alpha=0.3, linewidth=0.6, zorder=4)
ax.plot([warehouse_x + 90, warehouse_x + 170], [warehouse_y + 40, warehouse_y + 40],
        color=ACCENT_BLUE, alpha=0.3, linewidth=0.6, zorder=4)

# ── 3b. 右侧小型仓库 ──
wh2 = Rectangle((1380, 320), 200, 150,
                facecolor=MID_BLUE, edgecolor=ACCENT_BLUE, linewidth=1, alpha=0.4, zorder=2)
ax.add_patch(wh2)
roof2 = Polygon([(1360, 470), (1480, 540), (1600, 470)],
                facecolor=MID_BLUE, edgecolor=ACCENT_BLUE, linewidth=1, alpha=0.4, zorder=2)
ax.add_patch(roof2)

# ── 3c. 叉车/运输箭头（动态线条）──
# 从左到右的物流流动线
flow_y_positions = [550, 500, 450, 400]
for idx, y in enumerate(flow_y_positions):
    alpha_f = 0.12 + idx * 0.03
    lw = 1.5 + idx * 0.5
    x_start = 420 + idx * 30
    ax.plot([x_start, 1280 + idx * 20], [y, y - idx * 15],
            color=LIGHT_GREEN, alpha=alpha_f, linewidth=lw, zorder=2,
            linestyle='--' if idx % 2 == 0 else '-')
    # 箭头端点
    ax.scatter([1280 + idx * 20], [y - idx * 15], s=40 + idx * 10,
               color=LIGHT_GREEN, alpha=alpha_f + 0.05, zorder=3)

# ── 3d. 右侧连接节点（数据/自动化） ──
node_positions = [(1500, 620), (1600, 590), (1700, 570), (1550, 550)]
for px, py in node_positions:
    c = plt.Circle((px, py), 8, color=ACCENT_BLUE, alpha=0.5, zorder=3)
    ax.add_patch(c)
# 连线
for i in range(len(node_positions) - 1):
    ax.plot([node_positions[i][0], node_positions[i+1][0]],
            [node_positions[i][1], node_positions[i+1][1]],
            color=ACCENT_BLUE, alpha=0.25, linewidth=1, zorder=2)

# 扫描线
for y_scan in np.linspace(300, 700, 8):
    ax.plot([800, 1120], [y_scan, y_scan], color=GOLD, alpha=0.08, linewidth=1.5, zorder=2)

# ═══════════════════════════════════════════
# 4. 左侧竖条装饰（现代感）
# ═══════════════════════════════════════════
bar_data = [(40, 300, 4, 180, LOGISTICS_GREEN, 0.7),
            (54, 320, 4, 140, LIGHT_GREEN, 0.5),
            (68, 350, 4, 100, GOLD, 0.4),
            (35, 200, 3, 80, ACCENT_BLUE, 0.5)]

for x, y, w, h, color, alpha in bar_data:
    rect = Rectangle((x, y), w, h, facecolor=color, alpha=alpha, zorder=5)
    ax.add_patch(rect)

# ── 底部横条 ──
ax.axhline(y=180, xmin=0.042, xmax=0.085, color=LOGISTICS_GREEN, linewidth=2.5, zorder=5)

# ═══════════════════════════════════════════
# 5. 装饰圆点 / 粒子
# ═══════════════════════════════════════════
np.random.seed(42)
for _ in range(40):
    px = np.random.uniform(500, 1900)
    py = np.random.uniform(200, 950)
    size = np.random.uniform(1, 5)
    color = np.random.choice([ACCENT_BLUE, LIGHT_GREEN, GOLD, LIGHT_GRAY])
    alpha = np.random.uniform(0.1, 0.35)
    c = plt.Circle((px, py), size, facecolor=color, alpha=alpha, zorder=1)
    ax.add_patch(c)

# ═══════════════════════════════════════════
# 6. 主标题文字
# ═══════════════════════════════════════════
# 物流节
ax.text(960, 780, '物流节', fontsize=76, fontweight='bold',
        ha='center', va='center', color=WHITE, zorder=10)

# 5月6日
ax.text(960, 680, '5月6日', fontsize=42, fontweight='normal',
        ha='center', va='center', color=GOLD, zorder=10,
        style='italic')

# 副标题
ax.text(960, 590, '致敬每一位物流人', fontsize=28,
        ha='center', va='center', color=LIGHT_GRAY, alpha=0.9, zorder=10)

# ── 标题装饰线 ──
line_w = 200
ax.plot([960 - line_w, 960 + line_w], [640, 640],
        color=GOLD, alpha=0.5, linewidth=1.5, zorder=10)
c_dot = plt.Circle((960, 640), 5, facecolor=GOLD, alpha=0.7, zorder=10)
ax.add_patch(c_dot)

# ═══════════════════════════════════════════
# 7. 顶部/底部 信息条
# ═══════════════════════════════════════════
# 顶部公司名
ax.text(100, 1000, '中移物流 · 科捷物流', fontsize=16,
        ha='left', va='center', color=LIGHT_GRAY, alpha=0.7, zorder=10)

# 左上角金色小方块
square = Rectangle((72, 993), 18, 18, facecolor=LOGISTICS_GREEN, alpha=0.8, zorder=10)
ax.add_patch(square)

# 底部日期
ax.text(960, 100, '2026年5月 · 月度运营汇报', fontsize=15,
        ha='center', va='center', color=LIGHT_GRAY, alpha=0.6, zorder=10)

# ── 底部装饰线 ──
ax.plot([860, 1060], [140, 140], color=GOLD, alpha=0.3, linewidth=1, zorder=10)
ax.plot([890, 1030], [130, 130], color=GOLD, alpha=0.2, linewidth=0.8, zorder=10)

# ═══════════════════════════════════════════
# 8. 右下角 LOGO 占位区
# ═══════════════════════════════════════════
logo_rect = Rectangle((1680, 140), 140, 70,
                       facecolor='none', edgecolor=LIGHT_GRAY, alpha=0.25,
                       linewidth=1, linestyle='--', zorder=10)
ax.add_patch(logo_rect)
ax.text(1750, 175, 'LOGO', fontsize=12, ha='center', va='center',
        color=LIGHT_GRAY, alpha=0.35, zorder=10)

# ═══════════════════════════════════════════
# 保存
# ═══════════════════════════════════════════
output_path = 'E:/Claude Code(cursor)/output/images/cover_logistics_day.png'
plt.tight_layout(pad=0)
plt.savefig(output_path, dpi=300, bbox_inches='tight',
            facecolor=DARK_BLUE, edgecolor='none', pad_inches=0)
plt.close(fig)

print(f'✅ 封面图已生成: {output_path}')
print(f'   尺寸: 1920×1080 (16:9)')
print(f'   DPI: 300')
