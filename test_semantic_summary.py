# -*- coding: utf-8 -*-
"""测试新的语义摘要函数"""

import re

def _extract_conclusion_from_text(hypothesis: str, text: str, positive: bool = None) -> str:
    """从 hypothesis + text 提取语义结论"""
    hyp = hypothesis.strip()
    topic_keywords = ["AI", "大模型", "客户", "壁垒", "专利", "团队", "商业化", "收入",
                      "技术", "市场", "融资", "产能", "供应链", "竞争", "产品", "芯片", "功率器件", "SiC"]
    topic = ""
    for kw in topic_keywords:
        if kw in hyp:
            topic = kw
            break
    if not topic:
        for kw in topic_keywords:
            if kw in text:
                topic = kw
                break

    # 正向：已验证/成立/达标
    if positive is True:
        if topic:
            return f"{topic}已验证"
        return "假设成立"

    # 负向/不确定：从 text 中提取关键词
    if positive is False:
        if topic:
            neg_kw = ["不足", "缺乏", "尚未", "未形成", "未实现", "失败", "非真正", "无法"]
            uncertain_kw = ["未验证", "待定", "不确定", "存疑"]
            reject_kw = ["无法", "否定", "推翻"]
            if any(kw in text for kw in reject_kw):
                return f"{topic}不成立"
            elif any(kw in text for kw in neg_kw):
                return f"{topic}不足"
            elif any(kw in text for kw in uncertain_kw):
                return f"{topic}存疑"
            else:
                return f"{topic}待验证"
        return "假设存疑"

    # 中性
    if topic:
        return f"{topic}待深入"
    return "待验证"


def _hypothesis_to_conclusion(hypothesis: str, updated_view: str = "") -> str:
    """将 hypothesis + updated_view 转化为结论句"""
    hyp = hypothesis.strip()
    view = updated_view.strip() if updated_view else ""

    # 规则1：从 updated_view 提取结论
    if view:
        # 正向判断
        if any(kw in view for kw in ["已验证", "已确认", "成立", "达标", "可实现", "已有", "完成"]):
            return _extract_conclusion_from_text(hyp, view, positive=True)
        # 负向/不确定判断
        elif any(kw in view for kw in ["未验证", "不确定", "待验证", "存疑", "不成立", "待定", "尚未", "不足"]):
            return _extract_conclusion_from_text(hyp, view, positive=False)
        elif any(kw in view for kw in ["非真正", "无法", "否定", "推翻", "失败"]):
            return _extract_conclusion_from_text(hyp, view, positive=False)
        # 中性：无法判断正负
        else:
            return _extract_conclusion_from_text(hyp, view, positive=None)

    # 规则2：从 hypothesis 主题生成结论
    theme_rules = [
        (["AI", "大模型", "准确率", "算法"], "AI技术已验证", "AI技术存疑", "AI技术待验证"),
        (["客户", "欧莱雅", "宝洁", "联合利华", "大客户"], "客户已验证", "客户质量存疑", "客户待验证"),
        (["壁垒", "护城河", "专利", "IP"], "壁垒存在", "壁垒不足", "壁垒待验证"),
        (["团队", "创始人", "CEO", "CTO", "背景"], "团队已验证", "团队存疑", "团队待深入验证"),
        (["商业化", "收入", "盈利", "营收", "变现"], "商业化已验证", "商业化存疑", "商业化待验证"),
        (["技术", "研发", "产品", "Demo", "原型"], "技术已验证", "技术存疑", "技术待验证"),
        (["市场", "规模", "TAM", "空间"], "市场已验证", "市场存疑", "市场待验证"),
        (["融资", "估值", "估值偏高", "估值合理"], "融资条款待核实", "融资条款存疑", "融资待核实"),
        (["竞争", "竞争对手", "赛道", "格局"], "竞争格局已摸清", "竞争格局待深入", "竞争待验证"),
        (["产能", "工厂", "供应链", "制造"], "供应链已验证", "供应链存疑", "供应链待验证"),
        (["芯片", "SiC", "功率器件"], "芯片技术已验证", "芯片技术存疑", "芯片待验证"),
    ]

    for keywords, positive, negative, uncertain in theme_rules:
        if any(kw in hyp for kw in keywords):
            if any(kw in hyp for kw in ["不", "无", "缺乏", "未", "弱", "风险", "问题", "担忧", "不足", "尚未"]):
                return negative
            elif any(kw in hyp for kw in ["强", "已", "好", "验证", "确认", "达标", "已有"]):
                return positive
            else:
                return uncertain

    # 规则3：提取核心词组成结论
    skip_words = ["假设", "认为", "可能", "预计", "预期", "判断", "观点"]
    clean_hyp = hyp
    for sw in skip_words:
        clean_hyp = clean_hyp.replace(sw, "")

    words = clean_hyp.replace("的", " ").replace("是", " ").replace("有", " ").replace("为", " ").split()
    if len(words) >= 2:
        key_parts = [w for w in words if len(w) >= 2 and w not in ["不是", "可能", "风险"]][-2:]
        conclusion = "".join(key_parts)
        if len(conclusion) <= 30:
            return conclusion
        else:
            return conclusion[:27] + "..."

    return clean_hyp[:27] + "..."


# 测试
print("=== 语义摘要测试 ===\n")
test_cases = [
    # (假设, updated_view)
    ("AI平台准确率70-80%，数据几千条...", "AI平台数据量和准确率基本符合预期，已有一定规模化应用"),
    ("客户集中度风险存在", "大客户验证中，未明确签署合同"),
    ("专利壁垒", "专利已注册，但未形成真正技术护城河"),
    ("新能源业务尚未商业化", ""),
    ("假设公司有核心技术竞争力", "核心技术竞争力待深入验证"),
    ("团队背景", "创始团队有成功创业经验"),
    ("商业化能力", "已有初步收入，但尚未盈利"),
]

for hyp, view in test_cases:
    result = _hypothesis_to_conclusion(hyp, view)
    print(f"假设: {hyp[:35]}")
    print(f"  View: {view[:35] if view else '(无)'}")
    print(f"  结论: {result}")
    print()
