# -*- coding: utf-8 -*-
"""
renderer.py — 2.0 会后分析报告渲染器
"""
from typing import Dict, Any

from .schemas import (
    Step6Output, Step7Output, Step8Output, Step9Output
)


def _to_str_enum(value) -> str:
    """将枚举或字符串转为字符串"""
    if value is None:
        return ""
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _get_new_information_items(step6_input) -> list:
    """兼容 dataclass 和 dict 格式的新增信息列表"""
    ni_list = step6_input.get("new_information", []) if isinstance(step6_input, dict) else step6_input.new_information
    # 统一转换为字典格式
    result = []
    for ni in ni_list:
        if isinstance(ni, dict):
            result.append(ni)
        else:
            # dataclass -> dict
            result.append({
                "content": getattr(ni, "content", ""),
                "category": _to_str_enum(getattr(ni, "category", None)),
                "importance": _to_str_enum(getattr(ni, "importance", None)),
                "evidence": getattr(ni, "evidence", ""),
                "contradicts_bp": getattr(ni, "contradicts_bp", False),
                "is_critical": getattr(ni, "is_critical", False),
                "info_type": getattr(ni, "info_type", "claim"),
                "novelty_type": getattr(ni, "novelty_type", "new"),
                "confidence": _to_str_enum(getattr(ni, "confidence", None)) or "medium",
                "affects_judgement": getattr(ni, "affects_judgement", ""),
                "related_prior_judgement": getattr(ni, "related_prior_judgement", ""),
                "follow_up_hint": getattr(ni, "follow_up_hint", ""),
                "transcript_noise": getattr(ni, "transcript_noise", False),
            })
    return result


def render_v2_report(
    project_name: str,
    step6,
    step7,
    step8,
    step9,
    question_candidates: list = None,
    industry_insight_candidates: list = None,
    user_profile_candidates: list = None,
) -> str:
    """
    渲染 2.0 完整报告为 Markdown

    Args:
        project_name: 项目名称
        step6~9: 各步骤输出（支持 dataclass 或 dict 格式）
        question_candidates: 问题库候选列表
        industry_insight_candidates: 行业认知候选列表
        user_profile_candidates: 用户画像候选列表

    Returns:
        Markdown 格式的报告字符串
    """
    lines = []
    lines.append(f"# 📋 会后分析报告：{project_name}")
    lines.append("")
    lines.append("> 生成时间：自动生成 | 架构版本：2.0")
    lines.append("")
    lines.append("---\n")

    # 统一获取字段（兼容 dataclass 和 dict）
    step6_data = step6.to_dict() if hasattr(step6, "to_dict") else step6
    step7_data = step7.to_dict() if hasattr(step7, "to_dict") else step7
    step8_data = step8.to_dict() if hasattr(step8, "to_dict") else step8
    step9_data = step9.to_dict() if hasattr(step9, "to_dict") else step9

    # ===== Step6: 新增信息提取 =====
    lines.append("## Step6：会议新增信息\n")
    meeting_summary = step6_data.get("meeting_summary", "") if isinstance(step6_data, dict) else ""
    if meeting_summary:
        lines.append(f"**会议摘要：** {meeting_summary}\n")
    ni_items = _get_new_information_items(step6_data)
    lines.append(f"共提取 {len(ni_items)} 条新增信息：\n")

    if ni_items:
        # 扩展表格：包含所有 v2.1 新字段
        lines.append("| # | 类别 | 信息内容 | 类型 | 新增 | 重要 | 可信 | 影响判断 | BP矛盾 |")
        lines.append("|---|------|----------|------|------|------|------|----------|--------|")
        for i, ni in enumerate(ni_items, 1):
            cat = ni.get("category", "") if isinstance(ni, dict) else ""
            imp = ni.get("importance", "") if isinstance(ni, dict) else ""
            info_type = ni.get("info_type", "fact") if isinstance(ni, dict) else "fact"
            novelty_type = ni.get("novelty_type", "new") if isinstance(ni, dict) else "new"
            confidence = ni.get("confidence", "medium") if isinstance(ni, dict) else "medium"
            contradicts = ni.get("contradicts_bp", False) if isinstance(ni, dict) else False
            is_critical = ni.get("is_critical", False) if isinstance(ni, dict) else False
            content = ni.get("content", "") if isinstance(ni, dict) else ""
            affects = ni.get("affects_judgement", "") if isinstance(ni, dict) else ""

            # 颜色标签
            imp_tag = f"🔴{imp}" if imp == "high" else ("🟡" if imp == "medium" else f"🟢{imp}")
            type_tag = f"claim" if info_type == "claim" else info_type
            novelty_tag = novelty_type
            conf_tag = f"🔴{confidence}" if confidence == "low" else ("🟡" if confidence == "medium" else f"🟢{confidence}")
            contradict_tag = "⚠️ 是" if contradicts else "否"
            critical_flag = " 🔥" if is_critical else ""

            lines.append(
                f"| {i} | {cat} | {content}{critical_flag} | {type_tag} | {novelty_tag} | {imp_tag} | {conf_tag} | {affects} | {contradict_tag} |"
            )
        lines.append("")
        # 关键信息详情（高重要性 + 与BP矛盾）
        highlight_items = [
            ni for ni in ni_items
            if ni.get("is_critical", False) or ni.get("contradicts_bp", False)
        ]
        if highlight_items:
            lines.append("### 🔥 关键信息详情\n")
            for ni in highlight_items:
                content = ni.get("content", "")
                evidence = ni.get("evidence", "")
                info_type = ni.get("info_type", "claim")
                novelty_type = ni.get("novelty_type", "new")
                confidence = ni.get("confidence", "medium")
                affects = ni.get("affects_judgement", "")
                contradicts_bp = ni.get("contradicts_bp", False)
                related_prior = ni.get("related_prior_judgement", "")
                follow_up = ni.get("follow_up_hint", "")
                tags = []
                if ni.get("is_critical", False):
                    tags.append("关键")
                if contradicts_bp:
                    tags.append("⚠️与BP矛盾")
                if ni.get("transcript_noise", False):
                    tags.append("🔊原文转写有误")
                tags.append(f"类型:{info_type}")
                tags.append(f"可信:{confidence}")
                tag_str = " | ".join(tags)
                lines.append(f"**{content}**")
                lines.append(f"> 【{tag_str}】【影响:{affects}】")
                if related_prior:
                    lines.append(f"> **关联会前判断：** {related_prior}")
                if follow_up:
                    lines.append(f"> **后续验证建议：** {follow_up}")
                lines.append(f"> 【原文】{evidence}\n")
    else:
        lines.append("*（暂无新增信息）*\n")

    lines.append("---\n")

    # ===== Step7: 问题对齐 + 会议质量 =====
    lines.append("## Step7：问题对齐与回答质量\n")

    # 会议质量评估
    mq = step7_data.get("meeting_quality", {}) if isinstance(step7_data, dict) else {}
    confidence_emoji = {
        "high": "🟢",
        "medium": "🟡",
        "low": "🔴"
    }
    eva_emoji = {
        "high": "🔴",  # 高回避 = 危险
        "medium": "🟡",
        "low": "🟢"
    }
    mq_emoji = lambda k: eva_emoji.get(mq.get(k, "medium"), "🟡") if isinstance(mq, dict) else "🟡"
    cd_emoji = confidence_emoji.get(mq.get("answer_directness", "medium"), "🟡") if isinstance(mq, dict) else "🟡"
    es_emoji = confidence_emoji.get(mq.get("evidence_strength", "medium"), "🟡") if isinstance(mq, dict) else "🟡"
    oc_emoji = confidence_emoji.get(mq.get("overall_confidence", "medium"), "🟡") if isinstance(mq, dict) else "🟡"
    el_emoji = mq_emoji("evasion_level")
    lines.append("### 会议整体评估\n")
    answered_c = mq.get('answered_count', 0) if isinstance(mq, dict) else 0
    partially_c = mq.get('partially_count', 0) if isinstance(mq, dict) else 0
    weak_c = mq.get('weak_count', 0) if isinstance(mq, dict) else 0
    missing_c = mq.get('missing_evidence_count', 0) if isinstance(mq, dict) else 0
    total_q = answered_c + partially_c + weak_c
    lines.append(f"- 回答直接性：{cd_emoji} {mq.get('answer_directness', 'medium')}（✅answered {answered_c} / 🟡partial {partially_c} / ❌weak {weak_c}）")
    lines.append(f"- 证据强度：{es_emoji} {mq.get('evidence_strength', 'medium')}")
    lines.append(f"- 回避程度：{el_emoji} {mq.get('evasion_level', 'medium')}")
    lines.append(f"- 整体可信度：{oc_emoji} {mq.get('overall_confidence', 'medium')}（缺失证据 ×{missing_c}）")
    lines.append(f"- 与BP一致性：{confidence_emoji.get(mq.get('consistency', 'medium'), '🟡')} {mq.get('consistency', 'medium')}")
    evasion_signals = mq.get("evasion_signals", []) if isinstance(mq, dict) else []
    if evasion_signals:
        lines.append("\n**⚠️ 回避信号：**\n")
        for sig in evasion_signals:
            lines.append(f"- {sig}\n")
    lines.append("")

    # 问题验证表格
    question_validation = step7_data.get("question_validation", []) if isinstance(step7_data, dict) else []
    lines.append("### 问题验证详情\n")
    if question_validation:
        lines.append("| # | 问题摘要 | 状态 | 质量 | 影响 | 追问 |")
        lines.append("|---|----------|------|------|------|------|")
        # 状态颜色：✅ answered / 🟡 partially+indirectly / ❌ evaded / ➖ not_answered
        status_color = {
            "answered": "✅",
            "partially_answered": "🟡",
            "indirectly_answered": "🟡",
            "evaded": "❌",
            "not_answered": "➖",
        }
        # 影响：⬆️ strengthens / ↗️ slightly_strengthens / ⬇️ weakens / ↘️ slightly_weakens / ➡️ no_change / ❓ unclear
        impact_emoji = {
            "strengthens": "⬆️",
            "slightly_strengthens": "↗️",
            "weakens": "⬇️",
            "slightly_weakens": "↘️",
            "no_change": "➡️",
            "unclear": "❓",
        }
        for i, v in enumerate(question_validation, 1):
            status = v.get("status", "not_answered") if isinstance(v, dict) else "not_answered"
            quality = v.get("quality", "medium") if isinstance(v, dict) else "medium"
            impact = v.get("impact", "no_change") if isinstance(v, dict) else "no_change"
            question = v.get("original_question", "") if isinstance(v, dict) else ""
            follow_up = v.get("follow_up_question", "") if isinstance(v, dict) else ""
            se = status_color.get(status, "➖")
            ie = impact_emoji.get(impact, "❓")
            q_short = question[:35] + "..." if len(question) > 35 else question
            fu_short = follow_up[:25] + "..." if len(follow_up) > 25 else follow_up
            matched_ids = v.get("matched_information_ids", []) if isinstance(v, dict) else []
            matched_str = ", ".join(matched_ids) if matched_ids else "—"
            lines.append(
                f"| {i} | {q_short} | {se} {status} | {quality} | {ie} {impact} | {fu_short} |"
            )
        lines.append("")
        # 详细视图
        for i, v in enumerate(question_validation, 1):
            status = v.get("status", "not_answered") if isinstance(v, dict) else "not_answered"
            question = v.get("original_question", "") if isinstance(v, dict) else ""
            matched_ids = v.get("matched_information_ids", []) if isinstance(v, dict) else []
            matched_summaries = v.get("matched_information_summary", []) if isinstance(v, dict) else []
            answer_summary = v.get("answer_summary", "") if isinstance(v, dict) else ""
            missing = v.get("missing_evidence", []) if isinstance(v, dict) else []
            follow_up = v.get("follow_up_question", "") if isinstance(v, dict) else ""
            se = status_color.get(status, "➖")
            lines.append(f"**{i}. {se} {question}**\n")
            lines.append(f"> 匹配信息：{', '.join(matched_ids) if matched_ids else '—'}")
            if matched_summaries:
                lines.append(f"> 匹配内容：")
                for sm in matched_summaries:
                    lines.append(f"> - {sm}")
            lines.append(f"> 总结：{answer_summary}")
            if missing:
                lines.append(f"> 缺失证据：")
                for ev in missing:
                    lines.append(f"> - {ev}")
            if follow_up:
                lines.append(f"> 追问：{follow_up}")
            lines.append("")
    else:
        lines.append("*（暂无问题验证数据）*\n")

    lines.append("---\n")

    # ===== Step8: 认知更新 =====
    lines.append("## Step8：会后认知更新\n")
    hypothesis_updates = step8_data.get("hypothesis_updates", []) if isinstance(step8_data, dict) else []
    unchanged_hypotheses = step8_data.get("unchanged_hypotheses", []) if isinstance(step8_data, dict) else []
    if hypothesis_updates:
        change_emoji = {
            "reinforced": "⬆️",
            "weakened": "⬇️",
            "overturned": "🔄",
            "reframed": "🔁"
        }
        for h in hypothesis_updates:
            change_type = h.get("change_type", "neutral") if isinstance(h, dict) else "neutral"
            hid = h.get("hypothesis_id", "") if isinstance(h, dict) else ""
            hypothesis = h.get("hypothesis", "") if isinstance(h, dict) else ""
            updated_view = h.get("updated_view", "") if isinstance(h, dict) else ""
            confidence_change = h.get("confidence_change", "") if isinstance(h, dict) else ""
            why_changed = h.get("why_changed", "") if isinstance(h, dict) else ""
            supporting_evidence = h.get("supporting_evidence", []) if isinstance(h, dict) else []
            contradicting_evidence = h.get("contradicting_evidence", []) if isinstance(h, dict) else []
            qid = h.get("source_question_id", "") if isinstance(h, dict) else ""
            ce = change_emoji.get(change_type, "➡️")
            conf_tag = f"({confidence_change})" if confidence_change else ""
            lines.append(f"### {ce} [{hid}] {hypothesis} {conf_tag}\n")
            if qid:
                lines.append(f"> 来源问题：{qid}\n")
            if updated_view:
                lines.append(f"> **更新后判断：** {updated_view}\n")
            if why_changed:
                lines.append(f"> **原因：** {why_changed}\n")

            if supporting_evidence:
                ev_str = ", ".join(supporting_evidence) if supporting_evidence else "—"
                lines.append(f"> ✅ 支持证据：{ev_str}\n")

            if contradicting_evidence:
                ev_str = ", ".join(contradicting_evidence) if contradicting_evidence else "—"
                lines.append(f"> ❌ 反对证据：{ev_str}\n")

            lines.append("")
    else:
        lines.append("*（暂无认知更新数据）*\n")

    if unchanged_hypotheses:
        lines.append("### ➡️ 未变化假设\n")
        for u in unchanged_hypotheses:
            lines.append(f"- {u}\n")
        lines.append("")

    overall_change = step8_data.get("overall_change", {}) if isinstance(step8_data, dict) else {}
    is_significantly_changed = overall_change.get("is_judgement_significantly_changed", False) if isinstance(overall_change, dict) else False
    if is_significantly_changed:
        lines.append("### ⚡ 整体判断显著变化\n")
        lines.append("**⚠️ 判断发生了显著变化！**\n")
        new_risks = overall_change.get("new_risks", []) if isinstance(overall_change, dict) else []
        new_opportunity = overall_change.get("new_opportunity_added", "") if isinstance(overall_change, dict) else ""
        if new_risks:
            lines.append("**⚠️ 新增风险：**\n")
            for r in new_risks:
                sev = r.get("severity", "medium") if isinstance(r, dict) else "medium"
                sev_tag = "🔴" if sev == "high" else "🟡"
                lines.append(f"- {sev_tag} {r.get('risk', '')} (来源: {r.get('source_question_id', '')} )\n")
        if new_opportunity:
            lines.append(f"- ✨ 新增机会：{new_opportunity}\n")
    lines.append("")

    lines.append("---\n")

    # ===== Step9: 决策与行动（v3 双层决策）=====
    lines.append("## Step9：决策与行动\n")

    # ---- 双层决策模块 ----
    overall_decision = step9_data.get("overall_decision", {}) if isinstance(step9_data, dict) else {}

    process_decision = overall_decision.get("process_decision", "request_materials") if isinstance(overall_decision, dict) else "request_materials"
    investment_decision = overall_decision.get("investment_decision", "not_ready") if isinstance(overall_decision, dict) else "not_ready"
    confidence = overall_decision.get("confidence", "medium") if isinstance(overall_decision, dict) else "medium"
    one_line = overall_decision.get("one_line_conclusion", "暂无") if isinstance(overall_decision, dict) else "暂无"

    process_emoji = {
        "continue_dd": "✅",
        "request_materials": "📋",
        "pause": "⏸️",
        "stop": "⛔"
    }
    investment_emoji = {
        "invest_ready": "✅",
        "not_ready": "⚠️",
        "reject": "⛔"
    }
    process_display = {
        "continue_dd": "继续尽调",
        "request_materials": "补充材料",
        "pause": "暂缓",
        "stop": "停止跟进"
    }
    investment_display = {
        "invest_ready": "可投资",
        "not_ready": "待验证",
        "reject": "不投资"
    }

    pe = process_emoji.get(process_decision, "📋")
    ie = investment_emoji.get(investment_decision, "⚠️")

    lines.append("### 双层决策\n")
    lines.append("| 流程决策 | 投资决策 | 置信度 |\n")
    lines.append("|----------|---------|--------|\n")
    lines.append(f"| {pe} **{process_display.get(process_decision, process_decision)}** | {ie} **{investment_display.get(investment_decision, investment_decision)}** | {confidence} |\n")
    lines.append(f"\n**一句话结论：** {one_line}\n")

    # ---- 四象限决策分解 ----
    decision_breakdown = step9_data.get("decision_breakdown", {}) if isinstance(step9_data, dict) else {}
    verified_positives = decision_breakdown.get("verified_positives", []) if isinstance(decision_breakdown, dict) else []
    unverified_positives = decision_breakdown.get("unverified_positives", []) if isinstance(decision_breakdown, dict) else []
    confirmed_negatives = decision_breakdown.get("confirmed_negatives", []) if isinstance(decision_breakdown, dict) else []
    key_uncertainties = decision_breakdown.get("key_uncertainties", []) if isinstance(decision_breakdown, dict) else []

    lines.append("### 决策分解\n")
    lines.append("| ✅ 已验证的好 | ❌ 已确认的坏 | ⚠️ 关键不确定性 |\n")
    lines.append("|--------------|-------------|----------------|\n")

    max_rows = max(len(verified_positives), len(confirmed_negatives), len(key_uncertainties))
    for i in range(max_rows):
        pos = verified_positives[i] if i < len(verified_positives) else ""
        neg = confirmed_negatives[i] if i < len(confirmed_negatives) else ""
        unc = key_uncertainties[i] if i < len(key_uncertainties) else ""
        lines.append(f"| {pos} | {neg} | {unc} |\n")

    # ---- 未验证的好消息 ----
    if unverified_positives:
        lines.append("\n**⚡ 未验证但可能成立的好**\n")
        for p in unverified_positives:
            lines.append(f"- {p}\n")

    # ---- 材料请求清单 ----
    material_requests = step9_data.get("material_request_list", []) if isinstance(step9_data, dict) else []
    if material_requests:
        lines.append("\n### 材料请求清单\n")
        lines.append("| 优先级 | 材料 | 目的 |\n")
        lines.append("|--------|------|------|\n")
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for req in material_requests:
            prio = req.get("priority", "medium") if isinstance(req, dict) else "medium"
            material = req.get("material", "") if isinstance(req, dict) else ""
            purpose = req.get("purpose", "") if isinstance(req, dict) else ""
            pe = priority_emoji.get(prio, "🟡")
            lines.append(f"| {pe} {prio} | {material} | {purpose} |\n")

    # ---- 待解决问题 ----
    remaining_unknowns = step9_data.get("remaining_unknowns", []) if isinstance(step9_data, dict) else []
    if remaining_unknowns:
        lines.append("\n### 待解决问题\n")
        for i, u in enumerate(remaining_unknowns, 1):
            priority = u.get("priority", "medium") if isinstance(u, dict) else "medium"
            issue = u.get("issue", "") if isinstance(u, dict) else ""
            why_blocking = u.get("why_blocking", "") if isinstance(u, dict) else ""
            how_to_resolve = u.get("how_to_resolve", "") if isinstance(u, dict) else ""
            prio = "🔴" if priority == "high" else ("🟡" if priority == "medium" else "🟢")
            lines.append(f"{prio} **{i}. {issue}**\n")
            lines.append(f"- 为什么阻碍：{why_blocking}\n")
            lines.append(f"- 解决方式：{how_to_resolve}\n")

    # ---- 下一步行动 ----
    next_actions = step9_data.get("next_actions", []) if isinstance(step9_data, dict) else []
    if next_actions:
        lines.append("\n### 下一步行动\n")
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for i, a in enumerate(next_actions, 1):
            priority = a.get("priority", "medium") if isinstance(a, dict) else "medium"
            action = a.get("action", "") if isinstance(a, dict) else ""
            who = a.get("who", "") if isinstance(a, dict) else ""
            purpose = a.get("purpose", "") if isinstance(a, dict) else ""
            prio = "🔴" if priority == "high" else ("🟡" if priority == "medium" else "🟢")
            lines.append(f"{prio} **{i}. {action}**（{who}）\n")
            lines.append(f"- 目的：{purpose}\n")

    # ---- 关键风险 ----
    key_risks = step9_data.get("key_risks", []) if isinstance(step9_data, dict) else []
    if key_risks:
        lines.append("\n### 关键风险\n")
        for risk in key_risks:
            lines.append(f"- {risk}\n")

    # ---- 决策逻辑 ----
    go_no_go_logic = step9_data.get("go_no_go_logic", "") if isinstance(step9_data, dict) else ""
    if go_no_go_logic:
        lines.append("\n### 决策逻辑\n")
        lines.append(f"```\n{go_no_go_logic}\n```\n")

    lines.append("---\n")

    # ===== 沉淀层 =====
    if question_candidates:
        lines.append("## 💎 问题库候选\n")
        lines.append("| 问题 | 用途 | 为什么有效 |")
        lines.append("|------|------|------------|")
        for q in question_candidates:
            lines.append(f"| {q.get('question', '')} | {q.get('use_case', '')} | {q.get('why_effective', '')} |")
        lines.append("")
        lines.append("> 💡 可将优质问题手动添加到问题模板库\n")
        lines.append("")

    if industry_insight_candidates:
        lines.append("## 🏭 行业认知候选\n")
        for ins in industry_insight_candidates:
            lines.append(f"**行业：** {ins.get('industry', '')}\n")
            lines.append(f"**洞察：** {ins.get('insight', '')}\n")
            lines.append(f"**核心问题：** {ins.get('core_question', '')}\n")
            if ins.get("note"):
                lines.append(f"> 备注：{ins.get('note')}\n")
            lines.append("")

    if user_profile_candidates:
        lines.append("## 👤 用户画像候选\n")
        for p in user_profile_candidates:
            lines.append(f"- **{p.get('dimension', '')}**：{p.get('pattern', '')}\n")
        lines.append("")
        lines.append("> 💡 这些是从对话中提炼的投资人画像特征，待 Step0 阶段使用\n")
        lines.append("")

    lines.append("---\n")
    lines.append("*报告由 AI 项目判断工作台 2.0 自动生成*\n")

    return "\n".join(lines)


def render_v2_context_summary(
    question_candidates: list = None,
    industry_insight_candidates: list = None,
    user_profile_candidates: list = None
) -> str:
    """渲染沉淀层摘要（轻量版，用于概览页）"""
    lines = []
    lines.append("### 沉淀层概览\n")
    if question_candidates:
        lines.append(f"- 💎 {len(question_candidates)} 条问题库候选")
    if industry_insight_candidates:
        lines.append(f"- 🏭 {len(industry_insight_candidates)} 条行业认知候选")
    if user_profile_candidates:
        lines.append(f"- 👤 {len(user_profile_candidates)} 条用户画像候选")
    if not any([question_candidates, industry_insight_candidates, user_profile_candidates]):
        lines.append("*（暂无沉淀数据）*")
    return "\n".join(lines)
