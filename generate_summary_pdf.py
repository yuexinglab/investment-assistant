"""
生成项目技术总结PDF文档
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os

# ===== 注册中文字体 =====
# 尝试多个常见字体路径
FONT_PATHS = [
    r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑 Regular
    r"C:\Windows\Fonts\msyhbd.ttc",     # 微软雅黑 Bold
    r"C:\Windows\Fonts\simsun.ttc",     # 宋体
    r"C:\Windows\Fonts\simhei.ttf",     # 黑体
]

font_name = "MicrosoftYaHei"
font_bold = "MicrosoftYaHei-Bold"

try:
    pdfmetrics.registerFont(TTFont(font_name, r"C:\Windows\Fonts\msyh.ttc", subfontIndex=0))
    pdfmetrics.registerFont(TTFont(font_bold, r"C:\Windows\Fonts\msyhbd.ttc", subfontIndex=0))
    print(f"[OK] 微软雅黑 loaded")
except Exception as e:
    print(f"[WARN] msyh failed: {e}, trying simsun...")
    try:
        pdfmetrics.registerFont(TTFont(font_name, r"C:\Windows\Fonts\simsun.ttc", subfontIndex=0))
        font_bold = font_name
        print(f"[OK] simsun loaded")
    except Exception as e2:
        print(f"[ERR] Font load failed: {e2}")
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"

# ===== 颜色定义 =====
DARK_BLUE = colors.HexColor("#1a237e")
LIGHT_BLUE = colors.HexColor("#3f51b5")
ACCENT = colors.HexColor("#5c6bc0")
BG_GRAY = colors.HexColor("#f5f5f5")
BG_LIGHT = colors.HexColor("#e8eaf6")
TEXT_DARK = colors.HexColor("#212121")
TEXT_GRAY = colors.HexColor("#757575")
GREEN = colors.HexColor("#2e7d32")
ORANGE = colors.HexColor("#e65100")
RED = colors.HexColor("#c62828")
TEAL = colors.HexColor("#00695c")
BORDER = colors.HexColor("#c5cae9")

# ===== 样式 =====
def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontName=font_bold, fontSize=26, leading=34,
        textColor=colors.white, alignment=TA_CENTER, spaceAfter=8
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", fontName=font_name, fontSize=13, leading=20,
        textColor=colors.HexColor("#c5cae9"), alignment=TA_CENTER, spaceAfter=4
    )
    styles["cover_date"] = ParagraphStyle(
        "cover_date", fontName=font_name, fontSize=11, leading=16,
        textColor=colors.HexColor("#9fa8da"), alignment=TA_CENTER
    )
    styles["h1"] = ParagraphStyle(
        "h1", fontName=font_bold, fontSize=16, leading=22,
        textColor=DARK_BLUE, spaceBefore=16, spaceAfter=6,
        borderPad=0
    )
    styles["h2"] = ParagraphStyle(
        "h2", fontName=font_bold, fontSize=13, leading=18,
        textColor=LIGHT_BLUE, spaceBefore=12, spaceAfter=4
    )
    styles["h3"] = ParagraphStyle(
        "h3", fontName=font_bold, fontSize=11, leading=16,
        textColor=ACCENT, spaceBefore=8, spaceAfter=3
    )
    styles["body"] = ParagraphStyle(
        "body", fontName=font_name, fontSize=10, leading=16,
        textColor=TEXT_DARK, spaceAfter=4, alignment=TA_JUSTIFY
    )
    styles["body_small"] = ParagraphStyle(
        "body_small", fontName=font_name, fontSize=9, leading=14,
        textColor=TEXT_GRAY, spaceAfter=3
    )
    styles["code"] = ParagraphStyle(
        "code", fontName="Courier", fontSize=8.5, leading=13,
        textColor=colors.HexColor("#263238"), backColor=colors.HexColor("#eceff1"),
        spaceAfter=2, leftIndent=8, rightIndent=8, borderPad=4
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", fontName=font_name, fontSize=10, leading=15,
        textColor=TEXT_DARK, leftIndent=16, spaceAfter=3,
        bulletIndent=6
    )
    styles["note"] = ParagraphStyle(
        "note", fontName=font_name, fontSize=9.5, leading=14,
        textColor=TEAL, backColor=colors.HexColor("#e0f2f1"),
        spaceAfter=4, leftIndent=8, borderPad=6
    )
    styles["warn"] = ParagraphStyle(
        "warn", fontName=font_name, fontSize=9.5, leading=14,
        textColor=ORANGE, backColor=colors.HexColor("#fff3e0"),
        spaceAfter=4, leftIndent=8, borderPad=6
    )
    return styles


def hr(color=BORDER, thickness=0.8):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6, spaceBefore=2)


def section_title(text, styles, level=1):
    icons = {1: "●", 2: "◆", 3: "▸"}
    icon = icons.get(level, "▸")
    key = f"h{level}"
    return Paragraph(f"{icon}  {text}", styles[key])


def bullet_item(text, styles):
    return Paragraph(f"• {text}", styles["bullet"])


def code_block(text, styles):
    # 转义XML特殊字符
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text, styles["code"])


def info_table(data, styles, col_widths=None):
    """两列键值表"""
    table_data = [[Paragraph(k, styles["body_small"]), Paragraph(v, styles["body"])] for k, v in data]
    t = Table(table_data, colWidths=col_widths or [5*cm, 11*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BG_LIGHT),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def header_table(title, subtitle, color=DARK_BLUE):
    """章节 header box"""
    data = [[Paragraph(f"<font color='white'><b>{title}</b></font>", ParagraphStyle("ht", fontName=font_bold, fontSize=11, leading=16, textColor=colors.white)),
             Paragraph(f"<font color='#c5cae9'>{subtitle}</font>", ParagraphStyle("hs", fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor("#c5cae9")))]]
    t = Table(data, colWidths=[8*cm, 9*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def pipeline_table(steps, styles):
    """Pipeline步骤表"""
    header = [
        Paragraph("<b>步骤</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>模块名</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>功能说明</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>输出类型</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
    ]
    rows = [header]
    for step in steps:
        rows.append([
            Paragraph(step[0], ParagraphStyle("td", fontName=font_bold, fontSize=9, textColor=ACCENT)),
            Paragraph(step[1], ParagraphStyle("td", fontName=font_bold, fontSize=9, textColor=DARK_BLUE)),
            Paragraph(step[2], ParagraphStyle("td", fontName=font_name, fontSize=9, leading=13, textColor=TEXT_DARK)),
            Paragraph(step[3], ParagraphStyle("td", fontName="Courier", fontSize=8, textColor=TEAL)),
        ])
    t = Table(rows, colWidths=[1.2*cm, 3.5*cm, 8.5*cm, 3.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ]))
    return t


def schema_table(schemas, styles):
    """Schema定义表"""
    header = [
        Paragraph("<b>类/枚举</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>字段/值</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>说明</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
    ]
    rows = [header]
    for row in schemas:
        rows.append([
            Paragraph(row[0], ParagraphStyle("td", fontName=font_bold, fontSize=9, textColor=DARK_BLUE)),
            Paragraph(row[1], ParagraphStyle("td", fontName="Courier", fontSize=8, textColor=TEAL)),
            Paragraph(row[2], ParagraphStyle("td", fontName=font_name, fontSize=9, leading=13, textColor=TEXT_DARK)),
        ])
    t = Table(rows, colWidths=[3.5*cm, 5*cm, 8.2*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title="AI项目判断工作台 - 技术总结",
        author="AI Assistant",
    )
    styles = build_styles()
    story = []

    # ============================================================
    # 封面
    # ============================================================
    cover_bg = Table(
        [[Paragraph("AI 项目判断工作台", styles["cover_title"])],
         [Paragraph("Technical Summary — 2026.04.22", styles["cover_sub"])],
         [Paragraph("架构全解 · 模块设计 · 代码路径 · 实现细节", styles["cover_sub"])],
         [Spacer(1, 0.3*cm)],
         [Paragraph("版本：v1.0 + v2.5 + v2.0  |  作者：AI Assistant  |  日期：2026-04-23", styles["cover_date"])],
         [Spacer(1, 0.2*cm)],
         [Paragraph("本文档面向接手此项目的AI或工程师，一看即懂", styles["cover_date"])],
        ],
        colWidths=[17*cm]
    )
    cover_bg.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(Spacer(1, 1.5*cm))
    story.append(cover_bg)
    story.append(Spacer(1, 0.8*cm))

    # 快速概览卡
    overview_data = [
        ["项目名称", "AI 项目判断工作台（投资助手）"],
        ["项目路径", "D:\\复旦文件\\Semester3-4\\搞事情\\论文产品化\\投资助手\\"],
        ["技术栈", "Flask 3.x / Python 3.13 / DeepSeek API / pdfplumber / python-docx"],
        ["当前版本", "三个并行版本：1.0 初判 + v2.5 模板驱动 + 2.0 尽调验证"],
        ["AI模型", "deepseek-chat（通过.env配置API Key）"],
        ["运行方式", "python app.py  或  双击 启动.bat"],
        ["访问地址", "http://localhost:5000"],
    ]
    story.append(info_table(overview_data, styles, col_widths=[4*cm, 12*cm]))
    story.append(Spacer(1, 0.5*cm))
    story.append(PageBreak())

    # ============================================================
    # 第一章：项目背景与核心目标
    # ============================================================
    story.append(section_title("项目背景与核心目标", styles, 1))
    story.append(hr())
    story.append(Paragraph(
        "本项目是一套面向早期投资机构的<b>AI辅助项目研判工作台</b>，帮助投资人用AI自动分析创业公司BP（商业计划书），"
        "生成结构化初判报告，并在后续沟通（会议/调研）后持续更新判断。核心目标是把投资人的经验和直觉"
        "固化成可执行的AI流程，而不是让AI替代判断。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("核心设计哲学", styles, 2))
    story.append(Paragraph(
        "架构演进的关键认知转变：从<b>「AI扮演投资人互检」</b>升级为<b>「模板驱动 + AI执行 + 规则约束」</b>。"
        "内置行业判断模板，让AI对标提问而非自由发挥，从而确保一致性和可重复性。",
        styles["body"]
    ))

    insights = [
        ("洞察1", "B角色强制结构化挑刺，模拟投委会里\"有人专门提反对意见\""),
        ("洞察2", "2.0也需要多角色，用户得到初判后会继续追问，AI辅助用户扮演专业投资人"),
        ("洞察3", "上下文沉淀是资产：原始资料/解析结果/各版本报告全部持久化到磁盘"),
        ("洞察4", "3.0接口已在架构设计中预留（行业打分/竞争对手抓取/估值），不会有技术债"),
    ]
    t = Table(
        [[Paragraph(f"<b>{k}</b>", ParagraphStyle("k", fontName=font_bold, fontSize=9.5, textColor=DARK_BLUE)),
          Paragraph(v, styles["body"])] for k, v in insights],
        colWidths=[2.5*cm, 13.8*cm]
    )
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第二章：整体架构
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("整体系统架构", styles, 1))
    story.append(hr())

    story.append(Paragraph(
        "系统包含<b>三条并行分析链路</b>，共用同一个项目存储层和前端框架。每条链路独立触发、独立输出报告，"
        "彼此之间通过context.json传递上下文。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    # 三版本对比表
    version_data = [
        [Paragraph("<b>维度</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
         Paragraph("<b>1.0 初判</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
         Paragraph("<b>v2.5 模板驱动</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
         Paragraph("<b>2.0 尽调验证</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white))],
        [Paragraph("触发时机", styles["body_small"]),
         Paragraph("上传BP后", styles["body_small"]),
         Paragraph("上传BP后（推荐）", styles["body_small"]),
         Paragraph("上传会议记录后", styles["body_small"])],
        [Paragraph("核心逻辑", styles["body_small"]),
         Paragraph("A→B→C三角色", styles["body_small"]),
         Paragraph("9步模板流程+Step9投资人判断", styles["body_small"]),
         Paragraph("7步Pipeline串行执行", styles["body_small"])],
        [Paragraph("AI调用次数", styles["body_small"]),
         Paragraph("3次", styles["body_small"]),
         Paragraph("8~9次", styles["body_small"]),
         Paragraph("10~15次（含逐题判断）", styles["body_small"])],
        [Paragraph("输出格式", styles["body_small"]),
         Paragraph("role_a/b/c + final_report（文本）", styles["body_small"]),
         Paragraph("step1~9输出 + final_report（文本）", styles["body_small"]),
         Paragraph("V2PipelineResult（结构化dataclass）", styles["body_small"])],
        [Paragraph("存储键名", styles["body_small"]),
         Paragraph("latest_v1_report", styles["body_small"]),
         Paragraph("latest_v2_5_report", styles["body_small"]),
         Paragraph("latest_v2_report", styles["body_small"])],
        [Paragraph("报告状态", styles["body_small"]),
         Paragraph("v1_done", styles["body_small"]),
         Paragraph("v2_5_done", styles["body_small"]),
         Paragraph("v2_done", styles["body_small"])],
        [Paragraph("查看路由", styles["body_small"]),
         Paragraph("/project/<id>/result", styles["code"]),
         Paragraph("/project/<id>/result25", styles["code"]),
         Paragraph("/project/<id>/result2", styles["code"])],
    ]
    t = Table(version_data, colWidths=[3*cm, 3.8*cm, 5.3*cm, 5.2*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("BACKGROUND", (0, 1), (0, -1), BG_LIGHT),
        ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(section_title("目录结构", styles, 2))
    dir_lines = [
        "投资助手/",
        "  app.py              ← Flask主入口，所有路由定义",
        "  config.py           ← 配置：路径/API/文件类型",
        "  requirements.txt    ← 依赖列表",
        "  启动.bat             ← 双击启动",
        "  advanced_materials_v2.5.json  ← 新材料行业模板",
        "  .env                ← DEEPSEEK_API_KEY（不提交git）",
        "  prompts/            ← 所有Prompt定义",
        "    role_a_analyzer.py    ← A角色：业务理解",
        "    role_b_critic.py     ← B角色：风险挑刺",
        "    role_c_integrator.py ← C角色：整合裁判",
        "    step1_prompt.py      ← v2.5 Step1通用理解",
        "    step9_prompt.py      ← v2.5 Step9投资人判断层",
        "    v2_prompt.py         ← v2.0 Prompt集合（已整合到services/v2/prompts.py）",
        "  services/",
        "    deepseek_service.py  ← DeepSeek API调用封装",
        "    file_parser.py       ← PDF/TXT/DOCX解析",
        "    project_manager.py   ← 项目存储管理",
        "    report_generator.py  ← 报告生成主逻辑（调度层）",
        "    template_flow.py     ← v2.5 9步流程执行引擎",
        "    template_loader.py   ← 行业模板加载器",
        "    v2/                  ← 2.0 Pipeline包",
        "      schemas.py         ← 所有数据结构（枚举+dataclass）",
        "      prompts.py         ← Prompt构建器（输出JSON）",
        "      pipeline.py        ← 真正串行执行链",
        "      renderer.py        ← Markdown报告渲染器",
        "  templates/             ← Jinja2 HTML模板",
        "    index.html           ← 首页",
        "    new_project.html     ← 新建项目",
        "    project_detail.html  ← 项目详情（触发分析/查看报告入口）",
        "    result_1_0.html      ← 1.0报告展示",
        "    result_2_5.html      ← v2.5报告展示",
        "    result_2_0.html      ← 2.0报告展示",
        "  static/style.css       ← 全局样式",
        "  workspace/             ← 运行时自动创建，存储每个项目数据",
        "    <公司名>_<时间戳>/",
        "      meta.json          ← 项目元数据（状态机）",
        "      context.json       ← 最新各版本报告缓存",
        "      materials/         ← 原始上传文件",
        "      parsed/bp_text.txt ← 解析后的BP文本",
        "      parsed/meeting_text.txt ← 解析后的会议文本",
        "      reports/           ← 各版本报告JSON归档",
        "      question_trees/    ← 问题树存储",
    ]
    for line in dir_lines:
        story.append(code_block(line, styles))
    story.append(Spacer(1, 0.3*cm))

    # ============================================================
    # 第三章：路由表
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("Flask 路由全表", styles, 1))
    story.append(hr())

    route_data = [
        [Paragraph("<b>Method</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
         Paragraph("<b>路由</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
         Paragraph("<b>函数名</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
         Paragraph("<b>功能</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white))],
        ["GET", "/", "index", "首页，显示所有项目列表"],
        ["GET", "/project/new", "new_project", "新建项目页面"],
        ["POST", "/project/create", "create_project_route", "创建项目+上传BP文件"],
        ["GET", "/project/&lt;id&gt;", "project_detail", "项目详情页（分析触发中心）"],
        ["POST", "/project/&lt;id&gt;/analyze", "analyze", "触发1.0初判（A→B→C）"],
        ["POST", "/project/&lt;id&gt;/analyze_v25", "analyze_v25", "触发v2.5模板分析（9步流程）"],
        ["POST", "/project/&lt;id&gt;/update", "update_v2", "上传会议记录，触发2.0更新"],
        ["GET", "/project/&lt;id&gt;/result", "result_v1", "查看1.0报告页面"],
        ["GET", "/project/&lt;id&gt;/result25", "result_v25", "查看v2.5报告页面"],
        ["GET", "/project/&lt;id&gt;/result2", "result_v2", "查看2.0报告页面"],
        ["GET", "/project/&lt;id&gt;/export", "export_report", "导出报告（默认最新版本）"],
        ["GET", "/project/&lt;id&gt;/export/&lt;version&gt;", "export_report", "导出指定版本（v1_0/v2_5/v2_0）"],
    ]

    t_rows = []
    for i, row in enumerate(route_data):
        if i == 0:
            t_rows.append(row)
        else:
            method_color = GREEN if row[0] == "GET" else ORANGE
            t_rows.append([
                Paragraph(row[0], ParagraphStyle("m", fontName=font_bold, fontSize=9, textColor=method_color)),
                Paragraph(row[1], ParagraphStyle("r", fontName="Courier", fontSize=8.5, textColor=TEAL)),
                Paragraph(row[2], ParagraphStyle("f", fontName="Courier", fontSize=8.5, textColor=DARK_BLUE)),
                Paragraph(row[3], styles["body_small"]),
            ])

    t = Table(t_rows, colWidths=[1.5*cm, 5.5*cm, 4.5*cm, 5.8*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第四章：1.0 初判流程
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("1.0 初判：三角色串行流程", styles, 1))
    story.append(hr())

    story.append(Paragraph(
        "1.0版本是系统的基础层，用三个独立角色串行调用DeepSeek，模拟投委会内部讨论机制。"
        "每个角色的输出作为下一个角色的输入，形成「理解→挑战→综合」的认知闭环。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    v1_steps = [
        ("A", "role_a_analyzer", "业务理解（Synthesizer）：读完BP后输出结构化商业模式理解，提取核心假设、业务底盘、收入逻辑。", "str (文本)"),
        ("B", "role_b_critic", "风险挑刺（Critic）：拿到A角色输出后，专门扮演「反对派」，强制输出5个以上质疑点。", "str (文本)"),
        ("C", "role_c_integrator", "整合裁判（Integrator）：综合A/B两角色，输出初判报告，包含6个模块（业务理解/风险/问题清单/初判建议等）。", "str (文本)"),
    ]
    story.append(pipeline_table(v1_steps, styles))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("输出数据结构", styles, 2))
    story.append(code_block('{ "version": "1.0", "company_name": "...", "role_a": "...", "role_b": "...", "role_c": "...", "final_report": "..." }', styles))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "存储到 context.json 的 <b>latest_v1_report</b> 键，并更新 meta.json 的 status 为 <b>v1_done</b>。"
        "C角色输出即为final_report，是前端展示的主体。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第五章：v2.5 模板驱动流程
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("v2.5 模板驱动流程（9步法）", styles, 1))
    story.append(hr())

    story.append(Paragraph(
        "v2.5是核心架构升级，引入了<b>行业判断模板</b>作为规则约束层。"
        "与1.0相比，不再依赖AI自由发挥，而是让AI对照行业维度表逐项评估，"
        "最终Step9生成「投资人内部讨论」风格的深度判断。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    v25_steps = [
        ("1", "通用理解（Step1）", "读BP，输出业务底盘、商业模式、核心假设的结构化理解（升级版One-liner）。", "str"),
        ("2", "模板注入（Step2）", "加载行业模板（如advanced_materials_v2.5.json），注入维度/字段/规则，无AI调用。", "dict"),
        ("3", "字段抽取（Step3）", "对照模板的29个核心字段，从BP中逐一提取填充情况（已知/缺失/模糊）。", "str"),
        ("4", "缺口识别（Step4）", "对比已有信息和模板要求，识别哪些关键字段缺失，为Step5生成问题做准备。", "str"),
        ("5", "问题生成（Step5）", "基于缺口识别，生成8~12个精准的尽调追问问题，每个问题附带问题意图。", "str"),
        ("6", "规则命中（Step6）", "遍历模板中的8条风险规则库，检查BP是否触发任何预设红黄绿信号。", "str"),
        ("7", "评分计算（Step7）", "对照5大维度×子维度的1-10分评分标准，输出各维度得分和理由。", "dict"),
        ("8", "结构化报告（Step8）", "综合前7步，生成包含：业务底盘/确定部分/不确定部分/叙事vs现实/下一步验证点的报告。", "str"),
        ("9", "投资人判断层（Step9）", "核心质变点：从\"高级秘书\"进化到\"投资人内部讨论\"。输出动机判断/阶段错配/认知差/性价比判断/反直觉洞察。", "str"),
    ]
    story.append(pipeline_table(v25_steps, styles))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("行业模板结构（advanced_materials_v2.5.json）", styles, 2))
    story.append(Paragraph(
        "模板文件路径：<b>D:\\复旦文件\\Semester3-4\\搞事情\\论文产品化\\投资助手\\advanced_materials_v2.5.json</b>",
        styles["body"]
    ))
    template_info = [
        ("5大核心维度", "市场质量 / 技术成熟与验证程度 / 团队 / 商业化与交付能力 / 资本适配度"),
        ("子维度数量", "共28个子维度，每个附有1-10分评分标准"),
        ("核心字段", "29个结构化字段（客户类型/MRR/技术壁垒/核心团队背景等）"),
        ("风险规则库", "8条预设规则（如：技术TRL<4且已有客户→标记高风险）"),
        ("来源", "50+篇投资研究文章提炼 + 商业航天模板对标设计"),
    ]
    story.append(info_table(template_info, styles, col_widths=[4.5*cm, 11.8*cm]))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("v2.5 输出数据结构", styles, 2))
    story.append(code_block('{ "version": "v2_5", "company_name": "...", "industry": "...",', styles))
    story.append(code_block('  "step1_one_liner": "...", "step5_questions": "...",', styles))
    story.append(code_block('  "step6_risk_tags": "...", "step7_scores": {...},', styles))
    story.append(code_block('  "step9_judgment": "...",  // 投资人深度判断（核心输出）', styles))
    story.append(code_block('  "all_steps": {...},       // 全部步骤原始输出', styles))
    story.append(code_block('  "final_report": "..."     // = step9_judgment', styles))
    story.append(code_block('}', styles))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "存储到 context.json 的 <b>latest_v2_5_report</b> 键，meta.json status 更新为 <b>v2_5_done</b>。"
        "导出时优先提取 step9_judgment 作为核心内容。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第六章：2.0 尽调验证 Pipeline
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("2.0 尽调验证 Pipeline（核心架构升级）", styles, 1))
    story.append(hr())

    story.append(Paragraph(
        "2.0是在1.0或v2.5初判完成后，用户上传<b>会议记录/尽调纪要</b>触发的更新流程。"
        "与旧版D→E→C三角色不同，新架构是<b>真正的串行执行链</b>：每个模块的结构化输出"
        "直接作为下一个模块的输入，确保数据流打通，避免信息截断。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    v2_steps = [
        ("0", "_build_v1_structured", "预处理：将1.0或v2.5报告转为标准V1StructuredOutput（调用LLM做结构化，兜底用启发式解析）。", "V1StructuredOutput"),
        ("1", "Extractor", "从会议记录中提取新增有效信息，按类别（业务/技术/团队/商务）分类输出。", "List[Dict]"),
        ("2", "Delta Engine", "对比V1字段状态和新增信息，分析哪些字段状态发生变化，评估变化价值和对决策的影响。", "List[DeltaResult]"),
        ("3", "QA Judge（逐题）", "对V1问题清单中的每个问题，在会议记录中逐题判断：有效回答/模糊回答/回避问题。", "List[QAResult]"),
        ("4", "QA汇总", "统计有效/模糊/回避比例，识别高频回避主题，输出一句话会议信号。", "QASummary"),
        ("5", "Risk Update", "结合Delta和QA结果，更新V1风险列表的状态（已缓解/部分缓解/未变/新增）。", "List[RiskUpdate]"),
        ("6", "Decision Updater", "综合所有上游输出，更新投资判断：立场是否改变/决策逻辑/暂不推进原因/改变判断的条件。", "DecisionUpdate"),
        ("7", "Alpha Layer", "输出「直觉卡片」：团队画像（讲故事的人/做业务的人）/风险信号灯/回避模式/会议质量评分。", "AlphaSignal"),
    ]
    story.append(pipeline_table(v2_steps, styles))
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第七章：数据结构 Schema
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("核心数据结构（services/v2/schemas.py）", styles, 1))
    story.append(hr())

    story.append(section_title("枚举定义", styles, 2))
    enum_data = [
        ("FieldStatus", "unknown/missing/weak/partial/verified/strong", "字段验证程度（从完全未知到充分验证）"),
        ("QAJudgment", "effective/fuzzy/evasive", "回答质量：有效/模糊/回避"),
        ("ValueAssessment", "high/medium/low", "信息价值评估"),
        ("RiskImpact", "risk_relieved/partially_relieved/no_relief/new_risk_signal", "新信息对风险的影响"),
        ("DecisionImpact", "positive_change/negative_change/no_change/uncertain", "信息对投资决策的影响方向"),
        ("RiskStatus", "unresolved/partially_resolved/resolved/new_risk/unverifiable", "风险当前状态"),
        ("Recommendation", "推进/暂不推进/继续跟进", "最终投资建议（中文枚举值）"),
        ("RiskSignal", "red/yellow/green", "直觉风险信号灯"),
    ]
    story.append(schema_table(enum_data, styles))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("核心数据类（dataclass）", styles, 2))
    class_data = [
        ("V1StructuredOutput", "summary/field_states/questions/risks/conclusion", "1.0报告的结构化表示，作为2.0的输入基础。包含from_dict/to_dict序列化方法"),
        ("DeltaResult", "field_id/old_status/new_status/change_summary/value_assessment/impact_on_risk/impact_on_decision", "单个字段的变化记录，带双维度影响评估"),
        ("QAResult", "qid/question/answer_summary/judgment/reason/evidence", "单题回答质量判断结果，含判断依据和原文证据"),
        ("QASummary", "total/effective/fuzzy/evasive/high_frequency_theme/one_line_signal", "整场会议的QA质量汇总"),
        ("RiskUpdate", "risk_id/risk_name/old_status/new_status/change_type/severity/reason/evidence", "单个风险的状态更新，含risk_id确保可追踪"),
        ("DecisionUpdate", "previous_stance/current_stance/changed/decision_logic/why_not_now/what_would_change_decision/recommendation/one_line_decision", "结构化的投资判断更新，含改变前后立场对比"),
        ("AlphaSignal", "team_profile_label/risk_signal/avoidance_pattern/avoidance_frequency/meeting_quality_score/one_line_insight", "投资人直觉卡片，非结构化洞察的结构化输出"),
        ("V2PipelineResult", "new_info/deltas/delta_summary/qa_results/qa_summary/risk_updates/risk_summary/decision/alpha", "2.0 Pipeline的完整输出，包含to_dict序列化方法"),
    ]
    story.append(schema_table(class_data, styles))
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第八章：项目存储层
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("项目存储层（services/project_manager.py）", styles, 1))
    story.append(hr())

    story.append(Paragraph(
        "每个项目独立目录，状态通过meta.json的status字段追踪，各版本报告通过context.json索引。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.2*cm))

    storage_info = [
        ("项目目录命名规则", "<公司名>_<时间戳> 如：杉海材料科技_20260422_143022"),
        ("meta.json.status字段", "created → v1_done → v2_5_done → v2_done（单向状态机）"),
        ("context.json键名", "latest_v1_report / latest_v2_5_report / latest_v2_report / question_tree_v1 / question_tree_v2"),
        ("报告归档", "reports/<version>_<时间戳>.json，每次生成都保留历史，context.json只存最新"),
        ("has_v2_5字段", "list_projects()动态读取context.json，注入has_v2_5到meta，供首页判断显示"),
        ("v2_5_available变量", "project_detail视图函数动态计算，传入模板用于条件渲染"),
    ]
    story.append(info_table(storage_info, styles, col_widths=[5*cm, 11.3*cm]))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("关键函数说明", styles, 2))
    func_data = [
        ("create_project(company_name)", "创建项目目录+4个子目录，初始化meta.json和空context.json"),
        ("save_report(project_dir, version, content)", "保存报告JSON到reports/，更新context.json对应键，更新meta.json状态"),
        ("list_projects()", "列出所有项目，动态读取context.json注入has_v2_5字段，按created_at倒序"),
        ("load_project_context(project_dir)", "读取context.json返回完整上下文dict"),
    ]
    t = Table(
        [[Paragraph(f"<b>{k}</b>", ParagraphStyle("k", fontName="Courier", fontSize=8.5, textColor=TEAL)),
          Paragraph(v, styles["body"])] for k, v in func_data],
        colWidths=[6*cm, 10.3*cm]
    )
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第九章：前端交互逻辑
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("前端交互逻辑（project_detail.html）", styles, 1))
    story.append(hr())

    story.append(Paragraph(
        "项目详情页是整个系统的操作中心，通过Ajax异步触发分析，完成后重定向到对应报告页。",
        styles["body"]
    ))
    story.append(Spacer(1, 0.2*cm))

    ui_info = [
        ("Step 1 区域", "触发1.0初判（ABC三角色）；触发v2.5模板分析；查看/导出1.0报告；查看/导出v2.5报告"),
        ("Step 2 区域", "上传会议记录，触发2.0尽调更新；查看/导出2.0报告"),
        ("按钮条件渲染", "1.0按钮：meta.status != 'created' / v2.5按钮：v2_5_available变量 / 2.0按钮：meta.status == 'v2_done'"),
        ("导出路由", "/export（默认最新）或 /export/v1_0 | /export/v2_5 | /export/v2_0（指定版本）"),
        ("分析触发方式", "Ajax POST请求，loading状态显示，成功后window.location跳转到报告页"),
    ]
    story.append(info_table(ui_info, styles, col_widths=[4*cm, 12.3*cm]))
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第十章：已修复的bug清单
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("昨日已修复的Bug清单", styles, 1))
    story.append(hr())

    bugs = [
        ("template_loader.py", "路径错误", "模板加载路径写成了workspace/advanced_materials... 应为直接从BASE_DIR找"),
        ("app.py", "HTML标签混入Python代码", "Jinja2模板片段错误粘贴进了app.py的Python函数体内"),
        ("template_flow.py", "字段名不匹配", "访问 d['name'] 但JSON模板中使用的是 d['dimension_name']"),
        ("project_manager.py", "v2.5报告未正确保存", "save_report函数中 version='v2_5' 的判断分支缺失，导致覆盖到latest_v2_report"),
        ("report_generator.py", "report_to_markdown v2.5", "导出时错误地读取了 final_report 而不是 step9_judgment，导致内容不完整"),
        ("export_report路由", "未检查v2.5报告", "export_report函数的默认逻辑跳过了latest_v2_5_report，只看v2和v1"),
        ("result_v25函数名", "路由名不一致", "模板里用 url_for('result_v25') 但Flask函数名叫 result_v25（有下划线），不一致导致404"),
        ("首页index.html", "按钮显示逻辑错误", "显示了多个版本查看按钮，用户体验混乱；改为只显示详情按钮"),
        ("project_detail.html", "Step1显示2.0按钮", "Step1区域不应该显示2.0的查看/导出按钮，2.0应在Step2区域展示"),
        ("result_2_0.html", "导出版本错误", "2.0报告页的导出按钮没有指定version参数，导出了最新版（v2.5）而非2.0"),
    ]

    bug_rows = [[
        Paragraph("<b>文件</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>Bug类型</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
        Paragraph("<b>修复方案</b>", ParagraphStyle("th", fontName=font_bold, fontSize=9.5, textColor=colors.white)),
    ]]
    for i, (file, bug, fix) in enumerate(bugs):
        bg = colors.white if i % 2 == 0 else BG_GRAY
        bug_rows.append([
            Paragraph(file, ParagraphStyle("f", fontName="Courier", fontSize=8.5, textColor=RED)),
            Paragraph(bug, ParagraphStyle("b", fontName=font_bold, fontSize=9, textColor=ORANGE)),
            Paragraph(fix, styles["body_small"]),
        ])

    t = Table(bug_rows, colWidths=[4*cm, 3.5*cm, 9.8*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b71c1c")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 第十一章：快速上手指南
    # ============================================================
    story.append(PageBreak())
    story.append(section_title("快速上手指南（接手方必读）", styles, 1))
    story.append(hr())

    story.append(section_title("环境搭建", styles, 2))
    setup_steps = [
        "确保 Python 3.13+ 已安装",
        "进入项目目录：cd D:\\复旦文件\\Semester3-4\\搞事情\\论文产品化\\投资助手",
        "安装依赖：pip install -r requirements.txt",
        "确认 .env 文件存在，包含 DEEPSEEK_API_KEY=sk-xxx",
        "启动：python app.py  或  双击 启动.bat",
        "浏览器访问 http://localhost:5000",
    ]
    for s in setup_steps:
        story.append(bullet_item(s, styles))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("典型使用流程", styles, 2))
    flow_steps = [
        "首页点击「新建项目」，输入公司名，上传BP（支持PDF/TXT/DOCX）",
        "进入项目详情页，Step 1 点击「启动初判 1.0」（约1-2分钟，3次AI调用）",
        "Step 1 点击「v2.5模板分析」（约5-8分钟，9次AI调用，输出更深度报告）",
        "获取更多信息后，Step 2 上传会议记录，触发「2.0尽调更新」（约8-12分钟）",
        "各步骤均可独立「查看」或「导出Markdown」，互不影响",
    ]
    for s in flow_steps:
        story.append(bullet_item(s, styles))
    story.append(Spacer(1, 0.3*cm))

    story.append(section_title("扩展开发指南", styles, 2))
    dev_tips = [
        ("新增行业模板", "按 advanced_materials_v2.5.json 格式新建JSON，放在项目根目录，generate_v1_template() 支持传入 template_path 参数"),
        ("新增路由", "在 app.py 中添加 @app.route 装饰器，HTML模板放 templates/ 目录"),
        ("修改Prompt", "各角色Prompt独立文件在 prompts/ 目录，格式：SYSTEM_PROMPT 常量 + build_user_prompt() 函数"),
        ("修改2.0 Pipeline", "先改 schemas.py 增减字段，再改 prompts.py 对应的Prompt构建器，最后改 pipeline.py 和 renderer.py"),
        ("新增报告版本", "在 project_manager.py 的 save_report() 增加版本判断，在 app.py 增加路由，在 report_generator.py 增加生成函数"),
        ("预留的3.0扩展点", "app.py 预留了 /project/<id>/analyze_v3 入口，可接入行业打分/竞争对手抓取/估值模型"),
    ]
    t = Table(
        [[Paragraph(f"<b>{k}</b>", ParagraphStyle("k", fontName=font_bold, fontSize=9.5, textColor=DARK_BLUE)),
          Paragraph(v, styles["body"])] for k, v in dev_tips],
        colWidths=[4*cm, 12.3*cm]
    )
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # ============================================================
    # 尾页
    # ============================================================
    story.append(PageBreak())
    footer = Table(
        [[Paragraph(
            "本文档由 AI Assistant 于 2026-04-23 自动生成，基于项目代码库全量分析。<br/>"
            "如有疑问，可直接查阅对应源码文件，路径均已在文中标注。<br/>"
            "项目持续演进中，本文档描述截止到 2026-04-22 末的状态。",
            ParagraphStyle("footer", fontName=font_name, fontSize=10, leading=16,
                           textColor=colors.white, alignment=TA_CENTER)
        )]],
        colWidths=[17*cm]
    )
    footer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(Spacer(1, 3*cm))
    story.append(footer)

    doc.build(story)
    print(f"[OK] PDF generated: {output_path}")


if __name__ == "__main__":
    output = r"D:\复旦文件\Semester3-4\搞事情\论文产品化\投资助手\AI项目判断工作台_技术总结_20260422.pdf"
    build_pdf(output)
    print(f"Done! File: {output}")
