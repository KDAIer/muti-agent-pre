"""
多智能体辩论课程答辩 PPT v3
- 图文混排：每张图旁边有文字解释
- 每个图下方有图注
- 修复所有丢失的文字
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pathlib import Path

FIG = Path("/home/madai/ai-pre/figures")

GREEN    = RGBColor(0x01, 0x47, 0x23)
GREEN2   = RGBColor(0x02, 0x70, 0x35)
GREEN3   = RGBColor(0x04, 0xA0, 0x50)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
OFFWHITE = RGBColor(0xF5, 0xF9, 0xF6)
DARKTEXT = RGBColor(0x1A, 0x1A, 0x1A)
MUTED    = RGBColor(0x44, 0x55, 0x4A)
ACCENT   = RGBColor(0xE8, 0xF4, 0xEC)
ACCENT2  = RGBColor(0xE0, 0xF0, 0xE6)
YELLOW   = RGBColor(0xFF, 0xF0, 0xCC)
HEADGRAY = RGBColor(0xF0, 0xF4, 0xF1)

W = Inches(13.333)
H = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H


def blank():
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(s, x, y, w, h, fill=GREEN, lc=None, lw=0):
    sh = s.shapes.add_shape(1, x, y, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if lc:
        sh.line.color.rgb = lc
        sh.line.width = Pt(lw)
    else:
        sh.line.fill.background()
    return sh


def tb(s, text, x, y, w, h, sz=13, bold=False, color=DARKTEXT,
       align=PP_ALIGN.LEFT, italic=False, wrap=True):
    box = s.shapes.add_textbox(x, y, w, h)
    box.word_wrap = wrap
    tf = box.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(sz)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = "Microsoft YaHei"
    return box


def bullets(s, lines, x, y, w, h, sz=12, bullet="•  ", color=DARKTEXT,
            spacing=3, bold_first=False):
    box = s.shapes.add_textbox(x, y, w, h)
    box.word_wrap = True
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.space_before = Pt(spacing)
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = bullet + line
        r.font.size = Pt(sz)
        r.font.color.rgb = color
        r.font.name = "Microsoft YaHei"
        r.font.bold = (bold_first and i == 0)
    return box


def img(s, name, x, y, w, h):
    path = str(FIG / name)
    pic = s.shapes.add_picture(path, x, y, width=w)
    if pic.height > h:
        scale = h / pic.height
        pic.width  = int(pic.width  * scale)
        pic.height = int(pic.height * scale)
        pic.left   = int(x + (w - pic.width) / 2)
    return pic


def cap(s, text, x, y, w, color=MUTED, sz=10):
    """图注：居中，斜体，小号"""
    tb(s, text, x, y, w, Inches(0.32), sz=sz, italic=True,
       color=color, align=PP_ALIGN.CENTER)


def top_bar(s, chapter=""):
    rect(s, 0, 0, W, Inches(0.55), fill=GREEN)
    tb(s, "LLM 多智能体辩论  |  计算机学院", Inches(0.25), Inches(0.07),
       Inches(7), Inches(0.4), sz=12, color=WHITE)
    if chapter:
        tb(s, chapter, W - Inches(5.2), Inches(0.07), Inches(5.0), Inches(0.4),
           sz=12, color=WHITE, align=PP_ALIGN.RIGHT)


def bot_bar(s, pg):
    rect(s, 0, H - Inches(0.32), W, Inches(0.32), fill=GREEN)
    tb(s, pg, W - Inches(1.2), H - Inches(0.3), Inches(1.1), Inches(0.27),
       sz=11, color=WHITE, align=PP_ALIGN.RIGHT)


def sec_mark(s, num, title):
    rect(s, Inches(0.3), Inches(0.66), Inches(0.07), Inches(0.54), fill=GREEN)
    tb(s, f"{num}  {title}", Inches(0.45), Inches(0.64), Inches(12.5), Inches(0.56),
       sz=19, bold=True, color=GREEN)


def card(s, x, y, w, h, hdr, body_lines, sz_h=13, sz_b=11):
    rect(s, x, y, w, Inches(0.36), fill=GREEN)
    tb(s, hdr, x + Inches(0.1), y + Inches(0.04), w - Inches(0.2), Inches(0.3),
       sz=sz_h, bold=True, color=WHITE)
    rect(s, x, y + Inches(0.36), w, h - Inches(0.36), fill=ACCENT, lc=GREEN2, lw=0.5)
    bullets(s, body_lines, x + Inches(0.12), y + Inches(0.44),
            w - Inches(0.24), h - Inches(0.54), sz=sz_b, bullet="")


def section_cover(s, part, zh, en, pg):
    rect(s, 0, 0, W, H, fill=GREEN)
    rect(s, 0, 0, Inches(0.5), H, fill=GREEN2)
    tb(s, f"Part  {part}", Inches(0.7), Inches(2.2), Inches(9), Inches(0.6),
       sz=16, color=RGBColor(0xB8, 0xE0, 0xC4))
    tb(s, zh, Inches(0.7), Inches(2.85), Inches(11), Inches(1.1),
       sz=44, bold=True, color=WHITE)
    tb(s, en, Inches(0.7), Inches(3.95), Inches(11), Inches(0.5),
       sz=18, color=RGBColor(0xB8, 0xE0, 0xC4))
    bot_bar(s, pg)


def table_rows(s, rows, col_xs, col_ws, row_h, start_y, hi_row=None, font=12):
    for ri, row in enumerate(rows):
        y = start_y + ri * row_h
        bg = GREEN if ri == 0 else (YELLOW if ri == hi_row else
                                    (ACCENT if ri % 2 == 0 else WHITE))
        fc = WHITE if ri == 0 else DARKTEXT
        for ci, (cell, cx, cw) in enumerate(zip(row, col_xs, col_ws)):
            rect(s, cx, y, cw, row_h, fill=bg,
                 lc=RGBColor(0xCC, 0xDD, 0xCC), lw=0.5)
            tb(s, cell, cx + Inches(0.06), y + Inches(0.07),
               cw - Inches(0.12), row_h - Inches(0.1),
               sz=font, bold=(ri == 0 or ri == hi_row), color=fc,
               align=PP_ALIGN.CENTER)


# ===================================================================
# Slide 01 — 封面
# ===================================================================
s = blank()
rect(s, 0, 0, Inches(8.2), H, fill=GREEN)
rect(s, Inches(8.2), 0, Inches(0.06), H, fill=GREEN2)
rect(s, Inches(8.26), 0, W - Inches(8.26), H, fill=OFFWHITE)

tb(s, "计算机学院  AI/Agent 课程小组报告",
   Inches(0.4), Inches(0.55), Inches(7.5), Inches(0.45),
   sz=13, color=RGBColor(0xB8, 0xE0, 0xC4))
tb(s, "LLM 多智能体辩论",
   Inches(0.4), Inches(1.3), Inches(7.5), Inches(1.0),
   sz=38, bold=True, color=WHITE)
tb(s, "Multi-Agent Debate",
   Inches(0.4), Inches(2.35), Inches(7.5), Inches(0.65),
   sz=24, color=RGBColor(0xB8, 0xE0, 0xC4))
tb(s, "提升推理能力与事实性：复现、对比与改进",
   Inches(0.4), Inches(3.1), Inches(7.5), Inches(0.5),
   sz=14, color=RGBColor(0xD4, 0xEE, 0xDB))
rect(s, Inches(0.4), Inches(3.72), Inches(6.8), Inches(0.04),
     fill=RGBColor(0x4A, 0xA8, 0x6A))
tb(s, "模型：Qwen3.8-27B（自部署 vLLM）  |  数据集：GSM8K · MATH · MMLU",
   Inches(0.4), Inches(3.86), Inches(7.5), Inches(0.4),
   sz=11, color=RGBColor(0xB8, 0xE0, 0xC4))

for i, (k, v) in enumerate([
    ("小组成员", "A · B · C · D · E（5 人）"),
    ("指导老师", "—"),
    ("汇报日期", "2026 年 10 月"),
]):
    yy = Inches(2.2 + i * 1.0)
    tb(s, k, Inches(8.45), yy, Inches(1.5), Inches(0.35), sz=10, color=MUTED)
    tb(s, v, Inches(8.45), yy + Inches(0.3), Inches(4.6), Inches(0.5),
       sz=15, bold=True, color=DARKTEXT)

bot_bar(s, "1")

# ===================================================================
# Slide 02 — 目录
# ===================================================================
s = blank()
top_bar(s, "目录")
rect(s, 0, Inches(0.55), Inches(0.06), H - Inches(0.87), fill=GREEN)
tb(s, "C O N T E N T S", Inches(0.35), Inches(0.68), Inches(5), Inches(0.5),
   sz=22, bold=True, color=GREEN)
tb(s, "目  录", Inches(0.35), Inches(1.18), Inches(4), Inches(0.38),
   sz=13, color=MUTED)

items = [
    ("01", "背景与动机",  "单模型的局限  ·  辩论的直觉  ·  本实验目标"),
    ("02", "方法综述",    "Single / CoT / SC / 原版辩论框架"),
    ("03", "模型与方法",  "辩论机制详解  ·  四项改进  ·  实验设置"),
    ("04", "实验结果",    "截断偏差发现  ·  GSM8K / MATH / MMLU  ·  成本分析"),
    ("05", "结论",        "主要发现  ·  局限  ·  未来方向  ·  分工"),
]
for i, (num, title, sub) in enumerate(items):
    y = Inches(1.72 + i * 0.98)
    rect(s, Inches(0.35), y, Inches(0.62), Inches(0.62), fill=GREEN)
    tb(s, num, Inches(0.35), y, Inches(0.62), Inches(0.62),
       sz=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    tb(s, title, Inches(1.08), y + Inches(0.04), Inches(3.5), Inches(0.36),
       sz=15, bold=True, color=DARKTEXT)
    tb(s, sub, Inches(1.08), y + Inches(0.38), Inches(12.0), Inches(0.26),
       sz=10, color=MUTED)
    rect(s, Inches(0.35), y + Inches(0.65), Inches(12.7), Inches(0.015),
         fill=RGBColor(0xCC, 0xE5, 0xD4))

bot_bar(s, "2")

# ===================================================================
# Slides 03–05: 背景与动机
# ===================================================================
s = blank(); section_cover(s, "01", "背景与动机", "Background & Motivation", "3")

s = blank()
top_bar(s, "01  背景与动机")
sec_mark(s, "1.1", "单模型推理的主要失败模式")

problems = [
    ("推理失误",
     ["复杂数学题上的计算错误和逻辑跳步", "一旦第一步走错，后续会在错误方向自我强化"]),
    ("幻觉问题",
     ["知识类问题倾向于编造细节而非承认未知", "无法判断自身置信度的边界"]),
    ("确认偏差",
     ["采样多次时仍偏向相似的错误解题路径", "缺乏外部视角来打破已有思路"]),
    ("知识盲区",
     ["专业领域、长尾事实超出单次采样覆盖范围", "三个 Agent 知识同质，讨论无法凭空创造知识"]),
]
for i, (title, body) in enumerate(problems):
    col, row = i % 2, i // 2
    x = Inches(0.3 + col * 6.52)
    y = Inches(1.45 + row * 2.15)
    card(s, x, y, Inches(6.15), Inches(1.95), title, body, sz_b=12)

tb(s, "直觉：让多个模型各自独立作答，互相看到对方答案后讨论修正，能否像集体讨论一样提升准确率？",
   Inches(0.3), Inches(5.85), Inches(12.7), Inches(0.5),
   sz=13, bold=True, color=GREEN)
bot_bar(s, "4")

s = blank()
top_bar(s, "01  背景与动机")
sec_mark(s, "1.2", "多智能体辩论的核心流程")

for ii, (rname, short, detail) in enumerate([
    ("Round 1\n第1轮", "各自独立作答",
     "N 个 Agent 同时接到同一道题\n各自推理，互不知晓他人答案\n效果等价于 N 次独立采样"),
    ("Round 2\n第2轮", "互阅后更新",
     "每个 Agent 读到其他所有 Agent\n的上一轮完整回答后更新自己\n的答案（可以接受或反驳）"),
    ("Round 3\n第3轮", "收敛共识",
     "再次互阅、更新；跑满 R 轮后\n多数投票决定最终答案\nDynStop: 全员一致即提前终止"),
]):
    x = Inches(0.5 + ii * 4.1)
    rect(s, x, Inches(1.48), Inches(3.7), Inches(0.42), fill=GREEN)
    tb(s, rname.split("\n")[0], x, Inches(1.48), Inches(3.7), Inches(0.42),
       sz=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    tb(s, rname.split("\n")[1], x + Inches(2.3), Inches(1.52), Inches(1.3), Inches(0.35),
       sz=10, color=RGBColor(0xB8, 0xE0, 0xC4))
    for j in range(3):
        ay = Inches(2.05 + j * 0.9)
        rect(s, x + Inches(0.12), ay, Inches(3.46), Inches(0.75),
             fill=ACCENT if ii == 0 else ACCENT2, lc=GREEN2, lw=0.5)
        label = f"Agent {j+1}" if ii == 0 else ("更新" if ii < 2 else "最终答案")
        tb(s, f"Agent {j+1}  {short}", x + Inches(0.22), ay + Inches(0.08),
           Inches(3.26), Inches(0.55), sz=11, color=DARKTEXT)
    tb(s, detail, x + Inches(0.1), Inches(4.84), Inches(3.5), Inches(0.9),
       sz=10, color=MUTED)
    if ii < 2:
        tb(s, "=>", Inches(4.0 + ii * 4.1), Inches(2.65), Inches(0.4), Inches(0.4),
           sz=22, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

rect(s, Inches(0.3), Inches(5.87), Inches(12.7), Inches(0.72), fill=ACCENT, lc=GREEN2, lw=0.5)
tb(s, "原论文 (Du et al., 2023)：在 GPT-3.5 上，辩论相比单模型在 GSM8K / MMLU 等任务上取得了明显提升。"
   "本实验目标：用自部署 Qwen3.8-27B 复现该框架，与 CoT / Self-Consistency 系统对比，"
   "测试 4 项改进，并定量回答辩论的收益究竟来自哪里。",
   Inches(0.45), Inches(5.94), Inches(12.3), Inches(0.58), sz=11, color=MUTED)
bot_bar(s, "5")

# ===================================================================
# Slides 06–07: 方法综述
# ===================================================================
s = blank(); section_cover(s, "02", "方法综述", "Method Overview", "6")

s = blank()
top_bar(s, "02  方法综述")
sec_mark(s, "2.1", "五种对比方法")

mlist = [
    ("Single（直答基线）",
     "预填充答案开头（如 \\boxed{），迫使模型跳过推理直接给出答案。"
     "纯精度下界基线，用于判断推理对任务的贡献。",
     "1 次调用"),
    ("CoT（思维链）",
     "提示模型逐步推理，temperature=0，输出上限 16 384 token。"
     "消除了原论文中 2048 token 上限导致的截断偏差（见结果章节）。",
     "1 次调用"),
    ("SC@k（自洽投票）",
     "采样 k 条 CoT（temperature=0.7），多数投票。"
     "SC@3 与 Debate Round-1 的调用次数完全相同，构成最直接的成本对比基准。",
     "k 次调用"),
    ("Debate（多智能体辩论）",
     "N=3 个 Agent，R=3 轮互相阅读对方答案后更新，最终多数投票。"
     "每轮 prompt 包含所有他人上轮完整回答，导致 prompt token 随轮次迅速增长。",
     "9 次调用"),
    ("改进方法（我们的贡献）",
     "异质角色（Roles）/ 裁判（Judge）/ 置信度投票（ConfVote）/ "
     "动态提前终止（DynStop）。其中 DynStop 是最有价值的改进，见实验结果。",
     "9+1 次"),
]
for i, (title, desc, cost) in enumerate(mlist):
    y = Inches(1.42 + i * 1.06)
    rect(s, Inches(0.3), y, Inches(0.07), Inches(0.9), fill=GREEN)
    tb(s, title, Inches(0.45), y + Inches(0.03), Inches(10.5), Inches(0.38),
       sz=13, bold=True, color=GREEN)
    tb(s, desc, Inches(0.45), y + Inches(0.42), Inches(10.5), Inches(0.5), sz=11, color=DARKTEXT)
    rect(s, Inches(11.1), y + Inches(0.08), Inches(2.0), Inches(0.4), fill=ACCENT)
    tb(s, cost, Inches(11.1), y + Inches(0.08), Inches(2.0), Inches(0.4),
       sz=11, color=GREEN, align=PP_ALIGN.CENTER, bold=True)

bot_bar(s, "7")

# ===================================================================
# Slides 08–11: 模型与方法
# ===================================================================
s = blank(); section_cover(s, "03", "模型与方法", "Model & Method Details", "8")

s = blank()
top_bar(s, "03  模型与方法")
sec_mark(s, "3.1", "辩论机制详解（原版同质辩论）")

for ri, (rname, desc) in enumerate([
    ("Round 1：各自独立作答",
     "3 个 Agent 接到同一道题，各自独立推理。"
     "Prompt: 仅含题目，无任何他人信息。"
     "等价于 3 次独立 CoT 采样（与 SC@3 调用数相同）。"),
    ("Round 2：互阅、更新",
     "每个 Agent 的 prompt 末尾追加其他 2 人上一轮的完整回答。"
     "prompt 长度大幅增加（MATH 均 prompt 约 27 k token）。"
     "Agent 可以接受他人结论、指出错误、或坚持己见。"),
    ("Round 3：再次互阅、汇总",
     "同 Round 2，再次追加其他 Agent 当轮回答。"
     "Round 3 结束后多数投票；若启用 DynStop，某轮全员一致即提前停止。"
     "完整 3 轮：共 9 次 API 调用，prompt token 约为 CoT 的 30 倍。"),
]):
    y = Inches(1.42 + ri * 1.5)
    rect(s, Inches(0.3), y, Inches(0.5), Inches(1.3), fill=GREEN)
    tb(s, str(ri + 1), Inches(0.3), y + Inches(0.4), Inches(0.5), Inches(0.5),
       sz=22, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    rect(s, Inches(0.85), y, Inches(12.15), Inches(1.3), fill=ACCENT, lc=GREEN2, lw=0.5)
    tb(s, rname, Inches(1.0), y + Inches(0.06), Inches(12.0), Inches(0.38),
       sz=13, bold=True, color=GREEN)
    tb(s, desc, Inches(1.0), y + Inches(0.46), Inches(12.0), Inches(0.78), sz=11, color=DARKTEXT)

bot_bar(s, "9")

s = blank()
top_bar(s, "03  模型与方法")
sec_mark(s, "3.2", "四项改进（本组原创贡献）")

imprs = [
    ("A  异质角色 (Roles)",
     ["三个 Agent 分配不同 system prompt：",
      "  求解者：步骤严谨，逐步推理",
      "  质疑者：专找逻辑漏洞和计算错误",
      "  验证者：用不同方法复核结果",
      "每人额外在末行输出 Confidence: N（0-100）"]),
    ("B  裁判 Agent (+Judge)",
     ["辩论 3 轮结束后追加 1 次调用",
      "裁判读完所有辩手最终发言后独立裁决",
      "提示中明确：不要按票数决定，多数可能是错的",
      "若所有 Agent 都错，裁判可独立解题",
      "实验结果：效果与多数投票相当，不显著"]),
    ("C  置信度加权投票 (ConfVote)",
     ["Roles / AntiConf 版本中 Agent 输出置信度分",
      "按置信度加权投票，替代简单多数",
      "权重 = Agent 自报的 0-100 分",
      "实验结果：与简单多数投票无显著差异",
      "原因：Agent 自报置信度校准性差"]),
    ("D  动态提前终止 (DynStop)",
     ["某轮全员答案一致即提前停止，不浪费后续轮次",
      "离线精确模拟，不重新调 API",
      "GSM8K：97-99% 的题第 1 轮全员一致",
      "实测节省 82-88% token，准确率与完整辩论相同",
      "=> 本组最有价值的改进"]),
]
for i, (title, body) in enumerate(imprs):
    col, row = i % 2, i // 2
    x = Inches(0.3 + col * 6.52)
    y = Inches(1.45 + row * 2.35)
    card(s, x, y, Inches(6.15), Inches(2.15), title, body, sz_b=11)

bot_bar(s, "10")

s = blank()
top_bar(s, "03  模型与方法")
sec_mark(s, "3.3", "实验设置")

tb(s, "数据集", Inches(0.3), Inches(1.44), Inches(4), Inches(0.36),
   sz=14, bold=True, color=GREEN)
datasets = [
    ("GSM8K",      "100 题", "小学数学应用题，整数答案，自动判分",          "Qwen 在此近乎饱和 (93%)"),
    ("MATH-hard",  "156 题", "MATH-500 中 Level 4-5 且答案为整数的全部题",  "主要实验数据集，难度适中"),
    ("MMLU",       "100 题", "多领域四选一，测试事实性知识",                  "覆盖 57 个学科领域"),
]
for i, (ds, n, desc, note) in enumerate(datasets):
    y = Inches(1.84 + i * 0.72)
    rect(s, Inches(0.3), y, Inches(2.0), Inches(0.58), fill=GREEN)
    tb(s, ds, Inches(0.3), y, Inches(2.0), Inches(0.58),
       sz=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    tb(s, n, Inches(2.35), y + Inches(0.1), Inches(1.0), Inches(0.38),
       sz=13, bold=True, color=GREEN)
    tb(s, desc, Inches(3.45), y + Inches(0.1), Inches(5.5), Inches(0.38), sz=12, color=DARKTEXT)
    tb(s, note, Inches(9.0), y + Inches(0.1), Inches(4.0), Inches(0.38), sz=11, color=MUTED)

rect(s, Inches(0.3), Inches(4.25), Inches(0.07), Inches(1.95), fill=GREEN)
tb(s, "关键设置", Inches(0.5), Inches(4.25), Inches(5), Inches(0.36),
   sz=14, bold=True, color=GREEN)
settings = [
    "模型：Qwen3.8-27B（自部署 vLLM，关闭内置思考模式，temperature=0.7，top_p=0.8）",
    "输出上限：MAX_TOKENS = 16 384（关键！原论文用 2048 会造成截断偏差，见结果章节）",
    "对比方式：所有方法在相同一批题目上评估；方法间差异用精确 McNemar 检验（双侧）",
    "Agent 数量：N=3（默认），消融实验含 N=1/3/5；轮数：R=3；固定随机种子可复现",
]
bullets(s, settings, Inches(0.5), Inches(4.65), Inches(12.5), Inches(1.6), sz=11)
bot_bar(s, "11")

# ===================================================================
# Slides 12–13: 实验过渡 + 截断偏差
# ===================================================================
s = blank(); section_cover(s, "04", "实验结果及分析", "Experimental Results & Analysis", "12")

s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.1", "关键发现：截断偏差（v1 vs v2）")

# 左：v1
rect(s, Inches(0.3), Inches(1.44), Inches(5.9), Inches(4.0), fill=ACCENT, lc=GREEN2, lw=0.5)
tb(s, "v1  输出上限 2 048 token（与原论文一致）",
   Inches(0.42), Inches(1.5), Inches(5.6), Inches(0.36),
   sz=12, bold=True, color=GREEN)
v1r = [
    ("Debate 3x3", "95.5%", "截断率  8.8%"),
    ("CoT",        "76.3%", "截断率 21.2%"),
    ("SC@6",       "81.4%", "截断率 24.1%"),
]
cxs = [Inches(0.42), Inches(2.45), Inches(3.9)]
cws = [Inches(2.0), Inches(1.4), Inches(1.9)]
for ri, row in enumerate(v1r):
    y = Inches(2.0 + ri * 0.62)
    for ci, (cell, cx, cw) in enumerate(zip(row, cxs, cws)):
        rect(s, cx, y, cw, Inches(0.55),
             fill=(RGBColor(0xE0,0xF0,0xE8) if ri == 0 else WHITE), lc=GREEN2, lw=0.4)
        tb(s, cell, cx + Inches(0.05), y + Inches(0.08), cw - Inches(0.1), Inches(0.38),
           sz=12, bold=(ri == 0), color=(GREEN if ri == 0 else DARKTEXT),
           align=PP_ALIGN.CENTER)

rect(s, Inches(0.42), Inches(3.9), Inches(5.6), Inches(0.9), fill=YELLOW, lc=GREEN2, lw=0.4)
tb(s, "表面结论：辩论 vs CoT 差距 +19 pp，看似辩论大幅领先",
   Inches(0.52), Inches(3.97), Inches(5.3), Inches(0.35), sz=11, bold=True, color=DARKTEXT)
tb(s, "真实原因：CoT 有 21% 的调用被截断（答案未写完被判错）；"
   "辩论后续轮次每次只需核对他人解答，回复更短，截断率仅 8.8%",
   Inches(0.52), Inches(4.35), Inches(5.3), Inches(0.45), sz=10, color=MUTED)

tb(s, "=>", Inches(6.0), Inches(2.8), Inches(0.45), Inches(0.5),
   sz=26, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

# 右：v2
rect(s, Inches(6.55), Inches(1.44), Inches(6.4), Inches(4.0),
     fill=RGBColor(0xE8,0xF8,0xEE), lc=GREEN2, lw=0.5)
tb(s, "v2  输出上限 16 384 token（消除截断）",
   Inches(6.65), Inches(1.5), Inches(6.1), Inches(0.36),
   sz=12, bold=True, color=GREEN)
v2r = [
    ("Debate 3x3", "100.0%", "截断率  0%"),
    ("CoT",        " 98.7%", "截断率  0%"),
    ("SC@6",       "100.0%", "截断率  0%"),
]
cxs2 = [Inches(6.65), Inches(8.65), Inches(10.1)]
for ri, row in enumerate(v2r):
    y = Inches(2.0 + ri * 0.62)
    for ci, (cell, cx, cw) in enumerate(zip(row, cxs2, cws)):
        rect(s, cx, y, cw, Inches(0.55),
             fill=(RGBColor(0xD8,0xF0,0xE0) if ri == 0 else WHITE), lc=GREEN2, lw=0.4)
        tb(s, cell, cx + Inches(0.05), y + Inches(0.08), cw - Inches(0.1), Inches(0.38),
           sz=12, bold=(ri == 0), color=(GREEN if ri == 0 else DARKTEXT),
           align=PP_ALIGN.CENTER)

rect(s, Inches(6.65), Inches(3.9), Inches(6.1), Inches(0.9),
     fill=RGBColor(0xD8,0xF0,0xE0), lc=GREEN2, lw=0.4)
tb(s, "消除截断后：辩论 vs CoT 差距仅 +1.3 pp（p=0.5），无统计显著差异",
   Inches(6.75), Inches(3.97), Inches(5.8), Inches(0.35), sz=11, bold=True, color=GREEN)
tb(s, "33 道被截断的 CoT 题用 16k 上限重跑：30 道答对，最长需 11.7k token。"
   "本实验统一使用 16 384 token 上限。",
   Inches(6.75), Inches(4.35), Inches(5.8), Inches(0.45), sz=10, color=MUTED)

rect(s, Inches(0.3), Inches(5.6), Inches(12.7), Inches(0.68), fill=GREEN)
tb(s, "核心发现：辩论在低 token 预算下的优势很大程度来自对截断的鲁棒性——被截断的 Agent 可从他人完整解答里借到答案。"
   "消除截断后，差距消失。这是方法对比研究中一个容易忽视的系统性偏差。",
   Inches(0.45), Inches(5.66), Inches(12.3), Inches(0.56), sz=12, color=WHITE)
bot_bar(s, "13")

# ===================================================================
# Slide 14 — GSM8K 结果（表 + 图）
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.2", "GSM8K：所有推理方法均触及上限，无显著差异")

# 左侧：精简表
rows = [
    ("方法",        "准确率",  "token/题"),
    ("Single",      "45.0%",  "112"),
    ("CoT",         "93.0%",  "583"),
    ("SC@3",        "92.0%",  "1 836"),
    ("SC@6",        "95.0%",  "3 669"),
    ("Debate 3x3",  "95.0%",  "19 128"),
    ("DynStop",     "95.0%",  "2 627 *"),
]
cxs = [Inches(0.3), Inches(2.5), Inches(3.8)]
cws = [Inches(2.15), Inches(1.25), Inches(2.0)]
table_rows(s, rows, cxs, cws, Inches(0.6), Inches(1.46), hi_row=6, font=11)

bullets(s, [
    "DynStop (*) 节省 86% token，精度不变",
    "所有对比 p >= 0.5 (McNemar)，无显著差异",
    "99% 的题在第 1 轮三个 Agent 就全票一致",
    "辩论的价值：成本控制，而非提升精度",
], Inches(0.3), Inches(5.6), Inches(6.1), Inches(1.55), sz=10, bullet="  ")

# 右侧：图 + 图注
img(s, "gsm8k_tradeoff.png", Inches(6.45), Inches(0.68), Inches(6.7), Inches(5.5))
cap(s, "图1  GSM8K 准确率 vs token 成本（log 轴）。各方法精度聚集在 92-95%，DynStop 成本最低。",
    Inches(6.45), Inches(6.2), Inches(6.7))
bot_bar(s, "14")

# ===================================================================
# Slide 15 — GSM8K 辩论动态图
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.2b", "GSM8K：辩论轮数 & 纠错/从众分析")

# 左图 + 注
img(s, "gsm8k_rounds.png", Inches(0.2), Inches(0.72), Inches(6.5), Inches(5.5))
cap(s, "图2  准确率随辩论轮数的变化。所有变体第 1 轮就与 SC@6 持平，后续轮次几乎无变化。",
    Inches(0.2), Inches(6.25), Inches(6.5))

# 右图 + 注
img(s, "gsm8k_transitions.png", Inches(6.9), Inches(0.72), Inches(6.2), Inches(5.5))
cap(s, "图3  辩论中答案迁移次数（所有轮次累计）。错->对 6 次，对->错 4 次，净收益极小。",
    Inches(6.9), Inches(6.25), Inches(6.2))

# 图解说明
rect(s, Inches(0.2), Inches(5.85), Inches(12.9), Inches(0.32), fill=ACCENT)
tb(s, "结论：GSM8K 上辩论几乎不改变答案（每 Agent 每轮改变率仅 1.7%），模型已接近该任务的精度上限，辩论无提升空间。",
   Inches(0.35), Inches(5.9), Inches(12.6), Inches(0.25), sz=11, color=MUTED)
bot_bar(s, "15")

# ===================================================================
# Slide 16 — MATH-hard 结果（表 + 图）
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.3", "MATH-hard：成本效益分析（156 题，Level 4-5）")

rows = [
    ("方法",           "准确率",  "token（相对CoT）"),
    ("CoT",            "98.7%",  "1 861  (1x)"),
    ("SC@3",           "100%",   "5 619  (3x)"),
    ("DynStop",        "100%",   "6 893  (3.7x) *"),
    ("SC@6",           "100%",   "11 246 (6x)"),
    ("Debate 3x2",     "100%",   "24 741 (13x)"),
    ("Debate 3x3",     "100%",   "54 508 (29x)"),
]
cxs = [Inches(0.3), Inches(2.5), Inches(3.9)]
cws = [Inches(2.15), Inches(1.35), Inches(2.7)]
table_rows(s, rows, cxs, cws, Inches(0.6), Inches(1.46), hi_row=3, font=11)

bullets(s, [
    "CoT 达 98.7%，Qwen3.8 在此已接近上限",
    "SC@3、DynStop、SC@6 均达 100%",
    "DynStop (*) 只用 3.7x CoT 成本，最优",
    "Debate 3x3 耗 29x 但无额外精度提升",
    "全部对比 p=1.0，无统计显著差异",
], Inches(0.3), Inches(5.6), Inches(6.1), Inches(1.6), sz=10, bullet="  ")

img(s, "math_tradeoff.png", Inches(6.45), Inches(0.68), Inches(6.7), Inches(5.5))
cap(s, "图4  MATH-hard 准确率 vs token 成本。DynStop 是绿色改进点，以 3.7x 成本达到 100%。",
    Inches(6.45), Inches(6.2), Inches(6.7))
bot_bar(s, "16")

# ===================================================================
# Slide 17 — MATH 辩论轮数 & Agent 数量消融
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.3b", "MATH-hard：辩论轮数 & Agent 数量消融（80 题）")

img(s, "math_rounds.png",  Inches(0.2),  Inches(0.72), Inches(6.5), Inches(5.3))
cap(s, "图5  准确率随轮数变化。第 2 轮已几乎达到峰值（100%），第 3 轮无额外收益。三种辩论变体曲线基本重合。",
    Inches(0.2), Inches(6.05), Inches(6.5))

img(s, "math_agents.png",  Inches(6.9),  Inches(0.72), Inches(6.2), Inches(5.3))
cap(s, "图6  Agent 数量消融（1/3/5 个）。1 Agent 自我反思达 98.8%，3 Agent 达 100%。5 Agent 成本是 3 Agent 的 2.4 倍，精度无差异。",
    Inches(6.9), Inches(6.05), Inches(6.2))

rect(s, Inches(0.2), Inches(6.45), Inches(12.9), Inches(0.3), fill=ACCENT)
tb(s, "结论：对于 Qwen3.8，3 个 Agent 已是性价比最优配置；1 个 Agent 自我反思已能达到 98.8%，说明多视角对该任务帮助有限。",
   Inches(0.35), Inches(6.49), Inches(12.6), Inches(0.24), sz=10, color=MUTED)
bot_bar(s, "17")

# ===================================================================
# Slide 18 — MATH 纠错/从众图
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.3c", "MATH-hard：辩论中的纠错与从众")

img(s, "math_transitions.png", Inches(2.0), Inches(0.72), Inches(9.0), Inches(5.3))
cap(s, "图7  所有轮次累计的答案迁移次数。Debate: 错->对 8 次，对->错 1 次，净正向；Roles 和 AntiConf 类似。",
    Inches(2.0), Inches(6.05), Inches(9.0))

bullets(s, [
    "MATH-hard 上辩论净效果为正（错->对 >> 对->错），说明在该难度下辩论确实有助于纠错",
    "Roles 异质角色和 AntiConf 防从众提示的纠错效果与原版 Debate 无显著差异",
    "全票一致后仍出错的情况几乎没有（0-1 题），说明 MATH 上 Agent 之间的一致性质量较高",
], Inches(0.3), Inches(6.55), Inches(12.7), Inches(0.9), sz=11, bullet="  ")
bot_bar(s, "18")

# ===================================================================
# Slide 19 — MMLU 结果（图文混排）
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.4", "MMLU：知识测试，辩论无法弥补知识盲区（100 题）")

rows = [
    ("方法",        "准确率",  "token/题"),
    ("Single",      "85.0%",  "162"),
    ("CoT",         "91.0%",  "890"),
    ("SC@6",        "93.0%",  "5 490"),
    ("Debate 3x3",  "91.0%",  "26 940"),
    ("DynStop",     "91.0%",  "4 114 *"),
    ("Roles 3x3",   "92.0%",  "32 994"),
]
cxs = [Inches(0.3), Inches(2.5), Inches(3.8)]
cws = [Inches(2.15), Inches(1.25), Inches(2.0)]
table_rows(s, rows, cxs, cws, Inches(0.6), Inches(1.46), hi_row=4, font=11)

bullets(s, [
    "Debate (91%) 略低于 SC@6 (93%)，不显著 (p=0.6)",
    "7 道题全票一致但仍全错（知识盲区）",
    "讨论无法凭空产生模型没有的知识",
    "Single 截断率 60%（仅因直答格式，不影响精度）",
], Inches(0.3), Inches(5.6), Inches(6.1), Inches(1.55), sz=10, bullet="  ")

img(s, "mmlu_tradeoff.png", Inches(6.45), Inches(0.68), Inches(6.7), Inches(5.5))
cap(s, "图8  MMLU 准确率 vs 成本。Debate 高成本但精度反而略低于 SC@6，知识类任务辩论性价比不如 Self-Consistency。",
    Inches(6.45), Inches(6.2), Inches(6.7))
bot_bar(s, "19")

# ===================================================================
# Slide 20 — MMLU 辩论动态 & 从众图
# ===================================================================
s = blank()
top_bar(s, "04  实验结果")
sec_mark(s, "4.4b", "MMLU：辩论轮数 & 纠错/从众分析")

img(s, "mmlu_rounds.png",      Inches(0.2), Inches(0.72), Inches(6.5), Inches(5.3))
cap(s, "图9  MMLU 准确率随轮数变化。各版本与 CoT/SC 基线持平，无随轮次提升，与 MATH 截然不同。",
    Inches(0.2), Inches(6.05), Inches(6.5))

img(s, "mmlu_transitions.png", Inches(6.9), Inches(0.72), Inches(6.2), Inches(5.3))
cap(s, "图10  MMLU 答案迁移。错->对 ≈ 对->错（各约 9:7），净收益近零。7 题全票一致但全错（知识盲区）。",
    Inches(6.9), Inches(6.05), Inches(6.2))

rect(s, Inches(0.2), Inches(6.45), Inches(12.9), Inches(0.3), fill=ACCENT)
tb(s, "防从众提示（AntiConf）对->错仍有 6 次，与原版 Debate 相当——根源是知识不确定性，而非从众意愿，提示工程无法弥补。",
   Inches(0.35), Inches(6.49), Inches(12.6), Inches(0.24), sz=10, color=MUTED)
bot_bar(s, "20")

# ===================================================================
# Slides 21–23: 结论
# ===================================================================
s = blank(); section_cover(s, "05", "结论", "Conclusion", "21")

s = blank()
top_bar(s, "05  结论")
sec_mark(s, "5.1", "四条主要结论")

concl = [
    ("结论 1：能力边界决定上限",
     ["在 Qwen3.8 已接近任务天花板时（CoT 93-99%），辩论不带来统计显著提升",
      "所有数据集的辩论 vs CoT/SC 对比均 p >= 0.5，无显著差异",
      "辩论有效性的前提：任务对多视角推理敏感且模型有提升空间"]),
    ("结论 2：截断偏差是核心陷阱",
     ["2048 token 限制使 MATH 上辩论看似领先 CoT 达 +19 pp",
      "消除截断后差距归零——这是低 token 预算下辩论的系统性偏差",
      "建议：方法对比研究中应统一并验证输出长度上限的影响"]),
    ("结论 3：DynStop 是最佳改进",
     ["全员一致即提前终止，节省 82-88% token，精度不变",
      "原因：97-100% 的题在第 1 轮就已全员一致",
      "以 SC@3 相当的成本，匹配完整 3 轮辩论的精度"]),
    ("结论 4：知识类任务的根本局限",
     ["裁判、角色分工、置信度投票、防从众提示均无显著效果",
      "MMLU 上 7 题全票错误：Agent 之间知识盲区高度重叠",
      "讨论不能创造模型没有的知识；多样化模型才是根本出路"]),
]
for i, (title, body) in enumerate(concl):
    col, row = i % 2, i // 2
    x = Inches(0.3 + col * 6.52)
    y = Inches(1.45 + row * 2.4)
    card(s, x, y, Inches(6.15), Inches(2.2), title, body, sz_b=11)

bot_bar(s, "22")

s = blank()
top_bar(s, "05  结论")
sec_mark(s, "5.2", "局限与未来方向")

tb(s, "局限", Inches(0.3), Inches(1.44), Inches(4), Inches(0.35), sz=14, bold=True, color=GREEN)
bullets(s, [
    "模型能力过强：Qwen3.8 在所选数据集上接近饱和，缺乏辩论发挥的空间",
    "Agent 同质：三个 Agent 是同一模型的独立采样，知识层面高度重叠",
    "成本膨胀：Debate 3x3 的 74% token 消耗是 prompt（他人历史回答），而非生成",
    "AIME 数据不足：测试集因服务器限制未能全部完成，无法作为难题证据",
], Inches(0.3), Inches(1.84), Inches(12.7), Inches(1.6), sz=12)

tb(s, "未来方向", Inches(0.3), Inches(3.65), Inches(4), Inches(0.35), sz=14, bold=True, color=GREEN)
bullets(s, [
    "在弱模型或更难任务上验证（竞赛级数学、专业医学/法律问答）",
    "引入真正异质的 Agent（不同模型、不同参数），打破知识同质性",
    "摘要压缩机制：将他人历史回答压缩为摘要，降低后续轮次的 prompt 膨胀",
    "自适应轮次：根据当前分歧程度动态决定是否继续辩论，融合 DynStop 思路",
], Inches(0.3), Inches(4.05), Inches(12.7), Inches(1.6), sz=12)

bot_bar(s, "23")

s = blank()
top_bar(s, "05  结论")
sec_mark(s, "5.3", "小组分工")

members = [
    ("A", "环境 & 接口",
     "Qwen API 对接（绕过本机代理 7890，流式输出、超时重试）· chat() 封装 · 数据准备（GSM8K / MATH / MMLU）与答案解析"),
    ("B", "基线 & 原版辩论",
     "single / cot / sc / debate 方法实现 · 截断偏差发现与 v1->v2 修复工具（repair.py，续写截断处而非重跑）"),
    ("C", "改进方法实现",
     "roles / anticonf / judge / 置信度投票 · add_judge.py（完整版裁判，实验性） · 防从众提示工程"),
    ("D", "实验 & 分析",
     "并发跑全套实验（16 workers）· McNemar 检验 · 动态终止分析 · agent 消融 · 从众分析 · 图表生成（analyze.py）"),
    ("E", "报告 & 展示",
     "报告撰写 · 架构图 · 统稿 · PPT 制作"),
]
for i, (mem, role, detail) in enumerate(members):
    y = Inches(1.44 + i * 1.02)
    rect(s, Inches(0.3), y, Inches(0.65), Inches(0.65), fill=GREEN)
    tb(s, mem, Inches(0.3), y, Inches(0.65), Inches(0.65),
       sz=22, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    tb(s, role, Inches(1.05), y + Inches(0.02), Inches(2.5), Inches(0.36),
       sz=13, bold=True, color=GREEN)
    tb(s, detail, Inches(3.65), y + Inches(0.04), Inches(9.3), Inches(0.58),
       sz=10, color=MUTED)
    rect(s, Inches(0.3), y + Inches(0.72), Inches(12.7), Inches(0.015),
         fill=RGBColor(0xCC, 0xE5, 0xD4))
bot_bar(s, "24")

# ===================================================================
# Slide final — 致谢
# ===================================================================
s = blank()
rect(s, 0, 0, W, H, fill=GREEN)
rect(s, 0, 0, Inches(0.5), H, fill=GREEN2)
tb(s, "感谢聆听！", Inches(0.7), Inches(1.8), Inches(9), Inches(1.1),
   sz=48, bold=True, color=WHITE)
tb(s, "Q & A", Inches(0.7), Inches(3.0), Inches(4), Inches(0.65),
   sz=30, color=RGBColor(0xB8, 0xE0, 0xC4))

refs = [
    "Du et al. (2023). Improving Factuality and Reasoning in LLMs through Multiagent Debate. arXiv:2305.14325.",
    "Wei et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in LLMs. arXiv:2201.11903.",
    "Wang et al. (2022). Self-Consistency Improves Chain of Thought Reasoning. arXiv:2203.11171.",
    "Liang et al. (2023). Encouraging Divergent Thinking via Multi-Agent Debate. arXiv:2305.19118.",
    "Chan et al. (2023). ChatEval: Better LLM-based Evaluators through Multi-Agent Debate. arXiv:2308.07201.",
]
for i, ref in enumerate(refs):
    tb(s, ref, Inches(0.7), Inches(4.1 + i * 0.5),
       Inches(12.0), Inches(0.45), sz=10,
       color=RGBColor(0xB8, 0xE0, 0xC4))
bot_bar(s, "25")

prs.save("/home/madai/ai-pre/答辩PPT_多智能体辩论.pptx")
print(f"Done: {len(prs.slides)} slides")
