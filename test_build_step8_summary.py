# -*- coding: utf-8 -*-
"""测试新的 build_step8_summary 函数"""

import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/services/v2/services')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/services/v2')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/services')

# 复制 step8_updater.py 中的函数过来测试（避免 import 问题）
def _extract_conclusion_from_text(hypothesis: str, text: str, positive: bool = None) -> str:
    hyp = hypothesis.strip()
    topic_keywords = ["AI", "大模型", "客户", "壁垒", "专利", "团队", "商业化", "收入",
                      "技术", "市场", "融资", "产能", "供应链", "竞争", "产品",
                      "芯片", "SiC", "功率器件"]
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

    if positive is True:
        if topic:
            return f"{topic}已验证"
        return "假设成立"

    if positive is False:
        if topic:
            neg_kw = ["不足", "缺乏", "尚未", "未形成", "未实现", "失败", "非真正", "无法", "未明确"]
            uncertain_kw = ["未验证", "待定", "不确定", "存疑", "待深入", "待验证"]
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

    if topic:
        return f"{topic}待深入"
    return "待验证"


def _hypothesis_to_conclusion(hypothesis: str, updated_view: str = "", change_type: str = "") -> str:
    """
    将 hypothesis + updated_view + change_type 转化为结论句。

    核心逻辑：
    1. 从 hypothesis 提取"主题"（what we're talking about）
    2. 从 updated_view 提取"判断词"（what we found out）
    3. 结合 change_type（参考方向）
    4. 输出语义结论

    主题判断规则：
    - "假设X: Y是核心" + "Y并非核心" → "Y非核心"
    - "假设X: Y已验证" + "Y存疑" → "Y待验证"
    """
    hyp = hypothesis.strip()
    view = updated_view.strip() if updated_view else ""

    # ============================================================
    # 规则1：从 hypothesis 提取主题（按优先级）
    # ============================================================
    # 优先级：越具体的词越先匹配
    # 规则：新能源/美妆/AI 要优先于"扭亏/盈利"，商业化类要优先于具体行业
    topic_rules = [
        # 核心业务方向
        (["扭亏", "盈利", "营收", "收入", "商业化"], "商业化"),
        # 具体行业/客户
        (["新能源客户", "新能源业务", "新能源"], "新能源"),
        (["美妆客户", "美妆业务", "美妆", "欧莱雅", "宝洁", "珀莱雅"], "美妆"),
        (["AI平台", "AI"], "AI"),
        (["客户"], "客户"),
        # 其他
        (["壁垒", "护城河", "专利"], "壁垒"),
        (["团队", "创始人"], "团队"),
        (["技术"], "技术"),
        (["市场"], "市场"),
        (["融资", "估值"], "融资"),
        (["竞争"], "竞争"),
        (["供应链", "产能"], "供应链"),
    ]

    topic = ""
    for keywords, topic_name in topic_rules:
        for kw in keywords:
            if kw in hyp:
                topic = topic_name
                break
        if topic:
            break

    # 从 view 提取主题（备用）
    if not topic:
        for keywords, topic_name in topic_rules:
            for kw in keywords:
                if kw in view:
                    topic = topic_name
                    break
            if topic:
                break

    # ============================================================
    # 规则2：从 updated_view 提取判断词
    # ============================================================
    # 负向判断（最优先）
    # overthrow → "不成立"（假设被推翻）
    # weakened → "存疑"（假设被削弱）
    neg_kw = [
        ("并非", "非真正", "无法", "不成立"),  # 强否定 → 不成立
        ("未形成", "未实现", "未明确", "未进行"),  # 未+动词 → 不成立（假设被推翻）
        ("无意向", "无订单", "无收入"),  # 无+名词 → 不成立
        ("不足以", "尚未", "待验证"),  # 不足/尚未/待验证 → 存疑（假设被削弱）
        ("风险暴露", "失败", "不可替代"),  # 风险/失败 → 存疑
        ("未验证", "未提供", "仍有", "不确定"),  # 未验证/未提供/仍有 → 存疑
    ]

    for group in neg_kw:
        if any(kw in view for kw in group):
            if topic:
                if group[0] in ("并非", "非真正", "无法", "不成立", "未形成", "未实现", "未明确", "未进行", "无意向", "无订单", "无收入"):
                    return f"{topic}不成立"
                else:
                    return f"{topic}存疑"
            return "假设存疑"

    # 正向判断（只有在没有负向关键词时才使用）
    pos_kw = [
        ("已验证", "已确认", "成立", "达标"),  # 已验证
        ("已有", "完成", "强"),  # 已有
    ]

    # 正向判断
    pos_kw = [
        ("已验证", "已确认", "成立", "达标"),  # 已验证
        ("已有", "完成", "强"),  # 已有
    ]
    for group in pos_kw:
        if any(kw in view for kw in group):
            if topic:
                return f"{topic}已验证"
            return "假设成立"

    # 中性判断
    neutral_kw = [
        ("待深入", "待验证", "验证中", "待定"),  # 待验证
        ("不确定", "假设可靠性存疑", "未提供"),  # 不确定/未提供
        ("仍需", "仍待"),  # 仍需
    ]
    for group in neutral_kw:
        if any(kw in view for kw in group):
            if topic:
                return f"{topic}待深入"
            return "待验证"

    # ============================================================
    # 规则3：如果 view 为空，从 hypothesis 主题判断
    # ============================================================
    if topic:
        # 从 hypothesis 语气判断
        if any(kw in hyp for kw in ["不", "无", "缺乏", "尚未", "弱", "风险", "不足"]):
            return f"{topic}存疑"
        elif any(kw in hyp for kw in ["已", "强", "好", "验证", "达标"]):
            return f"{topic}已验证"
        else:
            return f"{topic}待验证"

    # ============================================================
    # 规则4：兜底
    # ============================================================
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


def build_step8_summary(step8_output):
    """简化版 build_step8_summary 用于测试"""
    hypothesis_updates = step8_output.get("hypothesis_updates", [])
    overall_change = step8_output.get("overall_change", {})

    validated_points = []
    invalidated_points = []
    uncertain_points = []

    counts = {
        "reinforced": 0,
        "uncertain": 0,
        "weakened": 0,
        "total": len(hypothesis_updates),
    }

    for h in hypothesis_updates:
        ct = h.get("change_type", "")
        hyp = h.get("hypothesis", "")
        updated_view = h.get("updated_view", "")

        conclusion = _hypothesis_to_conclusion(hyp, updated_view, change_type=ct)

        if ct in ("weakened", "overturned", "slightly_weakened"):
            invalidated_points.append(conclusion)
            counts["weakened"] += 1
        elif ct in ("reinforced", "slightly_reinforced"):
            validated_points.append(conclusion)
            counts["reinforced"] += 1
        elif ct in ("uncertain", "reframed"):
            uncertain_points.append(conclusion)
            counts["uncertain"] += 1

    validated_points = validated_points[:5]
    invalidated_points = invalidated_points[:5]
    uncertain_points = uncertain_points[:5]

    key_findings = []
    if counts["weakened"] > 0:
        key_findings.append(f"{counts['weakened']}个假设被削弱/推翻")
    if counts["uncertain"] > 0:
        key_findings.append(f"{counts['uncertain']}个假设待验证")
    if counts["reinforced"] > 0:
        key_findings.append(f"{counts['reinforced']}个假设得到支持")

    new_risks = overall_change.get("new_risks", [])
    if new_risks:
        key_findings.append(f"{len(new_risks)}个新风险暴露")

    key_findings = key_findings[:5]

    return {
        "key_findings": key_findings,
        "validated_points": validated_points,
        "invalidated_points": invalidated_points,
        "uncertain_points": uncertain_points,
        "_counts": counts,
    }


def main():
    # 读取真实 step8 数据
    step8_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "workspace/杉海创新科技中性投资人测试1_20260425_162019/step8/step8_v2_2_007.json"
    )

    with open(step8_path, 'r', encoding='utf-8') as f:
        step8_data = json.load(f)

    print("=" * 60)
    print("Step8 原始数据统计")
    print("=" * 60)
    print(f"假设数量: {len(step8_data['hypothesis_updates'])}")

    # 原始 hypothesis 长度
    total_hyp_len = sum(len(h['hypothesis']) for h in step8_data['hypothesis_updates'])
    total_view_len = sum(len(h['updated_view']) for h in step8_data['hypothesis_updates'])
    print(f"原始 hypothesis 总字数: {total_hyp_len}")
    print(f"原始 updated_view 总字数: {total_view_len}")

    print("\n" + "=" * 60)
    print("新的 build_step8_summary 输出")
    print("=" * 60)

    summary = build_step8_summary(step8_data)
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    summary_size = len(summary_json)

    print(f"\n结论数量统计:")
    print(f"  key_findings: {len(summary['key_findings'])} 条")
    print(f"  validated_points: {len(summary['validated_points'])} 条")
    print(f"  invalidated_points: {len(summary['invalidated_points'])} 条")
    print(f"  uncertain_points: {len(summary['uncertain_points'])} 条")

    print(f"\n摘要 JSON 总字数: {summary_size} 字")
    print(f"压缩比: {(total_hyp_len + total_view_len) / summary_size:.1f}x")

    print("\n--- key_findings ---")
    for f in summary['key_findings']:
        print(f"  {f}")

    print("\n--- validated_points (强化) ---")
    for p in summary['validated_points']:
        print(f"  [+] {p}")

    print("\n--- invalidated_points (削弱/推翻) ---")
    for p in summary['invalidated_points']:
        print(f"  [-] {p}")

    print("\n--- uncertain_points (不确定) ---")
    for p in summary['uncertain_points']:
        print(f"  [?] {p}")

    print("\n--- _counts ---")
    print(f"  {summary['_counts']}")


if __name__ == "__main__":
    main()
