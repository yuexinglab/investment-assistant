# -*- coding: utf-8 -*-
"""
step8_updater.py — Step8 认知更新（v2.3 语义分离架构）

v2.3.1 修复（2026-04-26）：
- _fill_with_llm 增加 90s 超时（防止 LLM 响应慢卡死 step8）
- update() 增加 try/except 兜底，确保 step8 永不让 pipeline 卡死


核心设计：
- Step8 只看 Step5（会前假设）+ Step7（问题验证结果）
- 不再看 Step6 或会议原文
- change_type + confidence_change 由规则自动映射
- hypothesis_direction 由代码根据假设文本自动推断
- LLM 只负责生成 updated_view + why_changed

规则引擎：
  Step7 status + impact  →  Step8 change_type + confidence_change + risk
  假设文本               →  Step8 hypothesis_direction（正向/负向/中性）

语义分离原则：
  - hypothesis_direction: "原假设成立" 对项目意味着什么（独立于会议结果）
  - change_type:          会议后原假设是否被强化/削弱/推翻
  - 这两个字段必须组合才能判断项目好坏
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple

from ..schemas import (
    Step8Output, HypothesisUpdate, OverallChange, NewRisk,
    ChangeType, ImportanceLevel, HypothesisDirection
)
from .. import prompts
from services.deepseek_service import call_deepseek


# ============================================================
# 规则引擎：Step7 → Step8 映射
# ============================================================

def _find_related_validations(
    hypothesis: str,
    step7_validations: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], int]]:
    """
    根据 hypothesis 找到相关的 Step7 问题验证（按匹配分数排序）。

    匹配逻辑（优先级从高到低）：
    1. 核心实体匹配：AI平台/欧莱雅/新能源/千沐/专利 等实体词命中
    2. 有 matched_information_ids 的优先
    3. 关键词命中

    Returns:
        List of (validation_dict, score) sorted by score descending
    """
    hypothesis_lower = hypothesis.lower()

    # 核心实体词表（高权重词，必须精确匹配）
    CORE_ENTITIES = [
        "ai平台", "人工智能平台", "大客户", "欧莱雅", "宝洁",
        "新能源", "食品业务", "工厂改造",
        "千沐", "并购", "协同效应",
        "专利", "专利保护", "竞争壁垒",
        "分子结构", "超分子",
    ]

    candidates = []

    for v in step7_validations:
        question = v.get("original_question", "").lower()
        matched_ids = v.get("matched_information_ids", [])
        answer_summary = v.get("answer_summary", "").lower()

        score = 0
        hits = []

        # 核心实体命中
        for entity in CORE_ENTITIES:
            if entity in hypothesis_lower and entity in question:
                score += 10
                hits.append(entity)

        # 如果没有核心实体命中，再做关键词匹配
        if score == 0:
            # 提取假设中的有效词（>=2字，非停用词）
            stop_words = {"是否", "真的", "主要", "什么", "如何", "是否已", "有多大",
                          "明确", "是否真实", "构成", "保护", "可能", "真实", "明确",
                          "壁垒", "切换", "来源", "成本", "业务", "时间表", "延期", "风险"}
            words = set()
            for pattern in [r"[一-龥]{2,4}", r"\w{3,}"]:
                words.update(re.findall(pattern, hypothesis_lower))
            words = words - stop_words - {""}
            for w in words:
                if w in question or w in answer_summary:
                    score += 1
                    hits.append(w)

        # 有 matched_information_ids → 强加分
        if matched_ids:
            score += 3

        if score > 0:
            candidates.append((v, score))

    # 排序：分数优先
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates  # 返回 (validation, score) 列表


def _has_missing_evidence(validation: Dict[str, Any]) -> bool:
    """Step7 的 missing_evidence 是否有内容（视为硬约束触发条件）"""
    missing = validation.get("missing_evidence", [])
    return bool(missing and len(missing) > 0)


def _infer_hypothesis_direction(hypothesis: str) -> HypothesisDirection:
    """
    根据假设文本推断 hypothesis_direction。

    核心原则：
    - positive：原假设成立 → 对项目是正面信息
    - negative：原假设成立 → 对项目是负面信息/风险
    - neutral：原假设只是验证点，无明显正负倾向

    判断逻辑：
    1. 先检测负向标记词（"没有"/"无法"/"缺乏"等）→ 推断为正向假设
       （因为这些词描述的是"缺失的东西"，成立意味着"项目有缺口"）
    2. 再检测负向风险词（"风险"/"担忧"/"不成熟"等）→ 推断为负向假设
       （这些描述的是"对项目的担忧"）
    3. 再检测正向标记词 → 推断为正向假设
    4. 默认 neutral

    示例：
    - "AI平台可能构成核心壁垒" → positive（壁垒对项目好）
    - "新能源客户可能没有真实订单" → positive（没订单=项目风险）
    - "大客户粘性强" → positive
    - "技术是否成熟" → neutral（纯验证点）
    - "竞争壁垒不足" → negative（壁垒不足=项目不好）
    """
    text = hypothesis.strip()

    # ── 1. 检测"负向缺失"模式 → positive ──────────────────────────────
    # 这些模式描述"项目可能缺少 X"，若成立 = 项目有风险 = 正向假设
    negative_lack_patterns = [
        # 没有/缺乏/无（缺失关键要素）
        "没有", "无", "缺乏", "缺失", "尚未",
        # 无法/不能/不会（能力不足）
        "无法", "不能", "不会", "不够",
        # 未验证/未实现/未完成
        "未验证", "未实现", "未完成", "未进行",
        # 存疑/存风险（对项目的担忧）
        "可能没有", "可能无法", "可能不会", "是否有",
        "是否真实", "是否具备", "是否成立", "是否可靠",
        "存疑", "存风险", "不确定",
    ]

    for pattern in negative_lack_patterns:
        if pattern in text:
            return HypothesisDirection.POSITIVE

    # ── 2. 检测"风险描述"模式 → negative ───────────────────────────────
    # 这些模式描述"对项目的负面判断"，成立 = 项目不好 = 负向假设
    risk_description_patterns = [
        # 项目本身的负面特征
        "风险高", "风险大", "风险暴露",
        "不成熟", "不完善", "不充分",
        "竞争激烈", "壁垒低", "壁垒不足", "护城河浅",
        "客户流失", "依赖单一", "集中度高",
        "亏损", "烧钱", "资金链", "造血能力",
        "团队不稳", "团队弱", "创始人风险",
        "市场小", "空间有限", "天花板低",
        "技术落后", "技术存疑", "技术夸大",
        "专利风险", "IP风险",
        # 明确表达"项目不好"的词汇
        "劣质", "低质", "虚假", "水分大",
    ]

    for pattern in risk_description_patterns:
        if pattern in text:
            return HypothesisDirection.NEGATIVE

    # ── 3. 检测"正向增强"模式 → positive ────────────────────────────────
    positive_patterns = [
        # 核心能力/壁垒
        "壁垒", "护城河", "门槛", "竞争力", "优势",
        "专利", "IP", "技术壁垒", "核心优势",
        # 客户/商业化验证
        "客户", "收入", "营收", "订单", "商业化",
        "验证", "确认", "落地", "交付",
        "合作", "合同", "收入确认",
        # 团队
        "团队", "创始人", "CEO", "CTO", "背景",
        "经验", "履历",
        # 技术
        "技术", "研发", "产品", "创新", "突破",
        "准确率", "性能", "效果",
        # 市场/规模
        "市场", "规模", "空间", "TAM", "增速",
        "增长", "扩张",
        # 融资/估值
        "融资", "估值", "资本",
        # 正面定性词
        "强", "好", "扎实", "稳健", "清晰",
        "已验证", "已确认", "已落地",
        "真实", "可靠", "稳定",
    ]

    for pattern in positive_patterns:
        if pattern in text:
            return HypothesisDirection.POSITIVE

    # ── 4. 兜底 neutral ────────────────────────────────────────────────
    return HypothesisDirection.NEUTRAL


def _check_evidence_quality(
    validation: Dict[str, Any],
    step7_result: Dict[str, Any]
) -> Tuple[str, float]:
    """
    检查 matched_information_ids 的证据质量。

    Returns:
        (quality_summary, claim_ratio)
        quality_summary: "fact_heavy" | "claim_heavy" | "mixed" | "unknown"
        claim_ratio: 0.0~1.0，claim 类信息占比
    """
    matched_ids = validation.get("matched_information_ids", [])
    if not matched_ids:
        return "unknown", 1.0

    # 从 step7_result 的 step6 new_information 中查找 info_type
    step6_info = step7_result.get("_step6_new_information", [])
    type_map = {ni.get("id", ""): ni.get("info_type", "unknown") for ni in step6_info}

    claim_count = 0
    total = len(matched_ids)
    for mid in matched_ids:
        info_type = type_map.get(mid, "unknown")
        if info_type in ("claim", "plan"):
            claim_count += 1

    claim_ratio = claim_count / total if total > 0 else 1.0
    if claim_ratio == 0.0:
        return "fact_heavy", claim_ratio
    elif claim_ratio >= 0.7:
        return "claim_heavy", claim_ratio
    elif claim_ratio >= 0.3:
        return "mixed", claim_ratio
    else:
        return "fact_heavy", claim_ratio


def _map_status_impact(
    related_validations: List[Tuple[Dict[str, Any], int]],
    step7_result: Dict[str, Any]
) -> Tuple[ChangeType, str, bool, Dict[str, Any]]:
    """
    将相关验证列表映射为 Step8 的 change_type、confidence_change、新增风险。

    v2.2.2 新增约束（按优先级应用）：
    1. partially_answered + missing_evidence 不为空 → 不能 reinforced
    2. claim_heavy 证据 → 不能 reinforced，只能 slightly_reinforced/reframed/uncertain
    3. answered + no_change → reframed

    Returns:
        (change_type, confidence_change, adds_risk, best_validation)
    """
    if not related_validations:
        return ChangeType.REFRAMED, "unchanged", False, {}

    best_v, best_score = related_validations[0]

    status = str(best_v.get("status", "not_answered")).lower()
    impact = str(best_v.get("impact", "no_change")).lower()
    has_missing = _has_missing_evidence(best_v)
    quality, claim_ratio = _check_evidence_quality(best_v, step7_result)
    adds_risk = False

    # ---- 应用硬约束（按优先级）----
    def _apply_constraints(raw_type: ChangeType, delta: str) -> Tuple[ChangeType, str]:
        """
        按优先级应用约束，返回（最终change_type，最终confidence_change）。

        优先级：
        1. claim_heavy 证据 → reinforced/slightly_reinforced → uncertain（最高优先）
        2. partially_answered + missing_evidence → reinforced → slightly_reinforced
        3. partially_answered + missing_evidence → slightly_reinforced → reframed
        """
        # 约束2（优先）：claim_heavy 证据 → 不能 reinforced/slightly_reinforced
        if quality == "claim_heavy":
            if raw_type in (ChangeType.REINFORCED, ChangeType.SLIGHTLY_REINFORCED):
                return ChangeType.UNCERTAIN, "medium→medium(存疑)"

        # 约束1：partially_answered + missing_evidence → 不能 reinforced/slightly_reinforced
        if has_missing and status in ("partially_answered", "indirectly_answered"):
            if raw_type == ChangeType.REINFORCED:
                return ChangeType.SLIGHTLY_REINFORCED, "medium→medium(弱)"
            if raw_type == ChangeType.SLIGHTLY_REINFORCED:
                return ChangeType.REFRAMED, "unchanged"

        return raw_type, delta

    # ---- answered 路线 ----
    if status == "answered":
        if impact in ("strengthens", "slightly_strengthens"):
            raw_type = ChangeType.REINFORCED if impact == "strengthens" else ChangeType.SLIGHTLY_REINFORCED
            delta = "medium→high" if impact == "strengthens" else "low→medium"
            final_type, final_delta = _apply_constraints(raw_type, delta)
            return final_type, final_delta, False, best_v
        elif impact in ("weakens", "slightly_weakens"):
            return ChangeType.OVERTURNED, "medium→low", True, best_v
        elif impact == "no_change":
            return ChangeType.REFRAMED, "unchanged", False, best_v
        else:
            return ChangeType.REFRAMED, "unchanged", False, best_v

    # ---- partially_answered / indirectly_answered 路线 ----
    if status in ("partially_answered", "indirectly_answered"):
        if impact in ("strengthens", "slightly_strengthens"):
            raw_type = ChangeType.SLIGHTLY_REINFORCED
            delta = "medium→medium(弱)"
            final_type, final_delta = _apply_constraints(raw_type, delta)
            return final_type, final_delta, False, best_v
        elif impact in ("weakens", "slightly_weakens"):
            raw_type = ChangeType.SLIGHTLY_WEAKENED if impact == "slightly_weakens" else ChangeType.WEAKENED
            return raw_type, "medium→low", True, best_v
        elif impact == "no_change":
            return ChangeType.REFRAMED, "unchanged", False, best_v
        else:  # unclear
            return ChangeType.UNCERTAIN, "unchanged", False, best_v

    # ---- evaded / not_answered → 高风险 ----
    if status in ("evaded", "not_answered"):
        return ChangeType.WEAKENED, "medium→low", True, best_v

    # 默认兜底
    return ChangeType.REFRAMED, "unchanged", False, best_v


def compute_hypothesis_updates(
    step5_judgements: List[Dict[str, str]],
    step7_validations: List[Dict[str, Any]],
    step7_result: Dict[str, Any],
) -> Tuple[List[HypothesisUpdate], List[NewRisk], List[str]]:
    """
    规则引擎：根据 Step5 假设 + Step7 验证结果，自动计算所有假设的更新。

    v2.2.2 证据填充规则：
    - contradicting_evidence 总是填写，即使 reinforced 也要写"缺失证据/未验证"
    - partially_answered + missing_evidence → missing_evidence 全部进 contradicting
    - 证据分类：info_type=claim/plan 的信息，进 contradicting（未验证）

    Returns:
        (hypothesis_updates, new_risks, unchanged_hypotheses)
    """
    hypothesis_updates = []
    all_new_risks = []
    unchanged_hypotheses = []

    # 建立 ni_id → info_type 的映射（从 step7_result._step6_new_information 中取）
    type_map: Dict[str, str] = {}
    step6_info = step7_result.get("_step6_new_information", [])
    for ni in step6_info:
        type_map[ni.get("id", "")] = ni.get("info_type", "unknown")

    for i, h in enumerate(step5_judgements):
        hid = h.get("hypothesis_id", f"h_{i+1}")
        hypothesis_text = h.get("hypothesis", h.get("dimension", ""))

        # 找到相关的 Step7 验证（按匹配分数排序）
        related_validations = _find_related_validations(hypothesis_text, step7_validations)

        if not related_validations:
            # 没有相关问题 → unchanged
            unchanged_hypotheses.append(hypothesis_text)
            continue

        # 规则映射：传入 step7_result 以便获取 info_type
        change_type, confidence_change, adds_risk, best_v = _map_status_impact(
            related_validations, step7_result
        )

        status = best_v.get("status", "not_answered")
        impact = best_v.get("impact", "no_change")
        matched_ids = best_v.get("matched_information_ids", [])
        answer_summary = best_v.get("answer_summary", "")
        qid = best_v.get("question_id", "")
        missing_evidence = best_v.get("missing_evidence", [])

        # ---- 证据分类逻辑（v2.2.2 严格化）----
        supporting: List[str] = []
        contradicting: List[str] = []

        if status in ("evaded", "not_answered"):
            # 回避/未回答 → 全部归反对证据
            contradicting = list(matched_ids)
        else:
            for mid in matched_ids:
                info_type = type_map.get(mid, "unknown")
                if impact in ("strengthens", "slightly_strengthens"):
                    if info_type in ("fact", "number"):
                        # 只有 fact/number 才能进 supporting
                        supporting.append(mid)
                    else:
                        # claim/plan 类 → 进 contradicting（未验证）
                        contradicting.append(mid)
                elif impact in ("weakens", "slightly_weakens"):
                    contradicting.append(mid)

            # ---- 约束：partially_answered + missing_evidence → 全部进 contradicting ----
            if status in ("partially_answered", "indirectly_answered") and missing_evidence:
                for me in missing_evidence:
                    if me not in contradicting:
                        contradicting.append(me)

        update = HypothesisUpdate(
            hypothesis_direction=_infer_hypothesis_direction(hypothesis_text),  # v2.3：自动推断假设方向
            hypothesis_id=hid,
            hypothesis=hypothesis_text,
            source_question_id=qid,
            change_type=change_type,
            confidence_change=confidence_change,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            # updated_view 和 why_changed 后面由 LLM 填充
            updated_view="",
            why_changed="",
        )

        # 新增风险（仅从 weakened/overturned 生成）
        if adds_risk:
            risk_desc = _generate_risk_description(status, impact, hypothesis_text, answer_summary)
            all_new_risks.append(NewRisk(
                risk=risk_desc,
                source_question_id=qid,
                severity=ImportanceLevel.HIGH if status in ("evaded", "not_answered") else ImportanceLevel.MEDIUM
            ))

        # 如果完全没有变化 → unchanged
        if change_type in (ChangeType.REFRAMED, ChangeType.UNCERTAIN) and "unchanged" in confidence_change and not matched_ids:
            unchanged_hypotheses.append(hypothesis_text)
            continue

        hypothesis_updates.append(update)

    return hypothesis_updates, all_new_risks, unchanged_hypotheses


def _generate_risk_description(status: str, impact: str, hypothesis: str, answer_summary: str) -> str:
    """根据 status/impact 生成风险描述"""
    if status == "evaded":
        return f"关键问题「{hypothesis[:20]}...」被回避，需重点关注"
    if status == "not_answered":
        return f"关键问题「{hypothesis[:20]}...」未被回答，判断依据不足"
    if impact in ("weakens", "slightly_weakens"):
        return f"假设「{hypothesis[:20]}...」被会议信息削弱：{answer_summary[:30]}..."
    return f"假设「{hypothesis[:20]}...」存在不确定性"


# ============================================================
# LLM 辅助：生成 updated_view 和 why_changed
# ============================================================

def _repair_json(text: str) -> str:
    """JSON截断修复"""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    lines = text.splitlines()
    for i in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:i])
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    lo, hi = 0, len(text)
    best = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            json.loads(text[:mid])
            best = mid
            lo = mid
        except json.JSONDecodeError:
            hi = mid - 1
    return text[:best] if best > 0 else text


def _parse_json(text: str) -> Any:
    repaired = _repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        raise ValueError(f"无法解析 LLM JSON 输出：\n{text[:300]}")


def _fill_with_llm(
    hypothesis_updates: List[HypothesisUpdate],
    step5_judgements: List[Dict[str, str]],
    step7_result: Dict[str, Any],
    model: str = None
) -> List[HypothesisUpdate]:
    """
    调用 LLM 填充 updated_view 和 why_changed。

    如果 hypothesis_updates 为空，直接返回空列表。
    """
    if not hypothesis_updates:
        return []

    system_prompt, user_prompt = prompts.build_step8_prompt(
        step5_judgements=step5_judgements,
        step7_result=step7_result
    )

    # v2.3.1: 用 60s 超时（禁用重试），让 LLM 快速失败
    raw = call_deepseek(system_prompt, user_prompt, model=model,
                        max_retries=1, timeout=60)
    parsed = _parse_json(raw)

    raw_updates = parsed.get("hypothesis_updates", []) if isinstance(parsed, dict) else []
    if not isinstance(raw_updates, list):
        raw_updates = []

    # 建立 hypothesis_id → LLM结果的映射
    llm_results = {u.get("hypothesis_id", ""): u for u in raw_updates}

    result = []
    for h in hypothesis_updates:
        llm_result = llm_results.get(h.hypothesis_id, {})
        h.updated_view = llm_result.get("updated_view", _default_updated_view(h))
        h.why_changed = llm_result.get(
            "why_changed",
            _default_why_changed(h, step7_result)
        )
        # 也允许 LLM 补充 evidence
        if llm_result.get("supporting_evidence"):
            h.supporting_evidence = llm_result["supporting_evidence"]
        if llm_result.get("contradicting_evidence"):
            h.contradicting_evidence = llm_result["contradicting_evidence"]
        result.append(h)

    return result


def _default_updated_view(h: HypothesisUpdate) -> str:
    """兜底 updated_view"""
    ct = h.change_type.value
    if ct == "weakened":
        return f"该假设被削弱，需降低置信度"
    if ct == "overturned":
        return f"该假设被推翻，需要重新审视"
    if ct == "reinforced":
        return f"该假设得到会议支持，置信度上升"
    return h.hypothesis


def _default_why_changed(h: HypothesisUpdate, step7_result: Dict[str, Any]) -> str:
    """兜底 why_changed"""
    qid = h.source_question_id
    validations = step7_result.get("question_validation", [])
    for v in validations:
        if v.get("question_id") == qid:
            summary = v.get("answer_summary", "")
            if summary:
                return f"会议回答：{summary[:50]}..."
    return f"根据 Step7 验证结果（status={v.get('status')}, impact={v.get('impact')}）判断"


# ============================================================
# 主入口：update
# ============================================================

def update(
    step5_judgements: List[Dict[str, str]],
    step7_result: Dict[str, Any],
    model: str = None
) -> Step8Output:
    """
    Step8：认知更新（v2.2.1 规则驱动）

    不再读取 Step6 或会议原文，只看 Step5 + Step7。

    Args:
        step5_judgements: Step5 的假设列表（每项需含 hypothesis_id）
            例: [{"hypothesis_id": "h_001", "hypothesis": "AI平台可能构成壁垒", "view": "..."}]
        step7_result: Step7 完整输出（dict，含 question_validation 和 meeting_quality）
        model: DeepSeek 模型名

    Returns:
        Step8Output
    """
    # v2.3.1: 整体 try/except，确保任何异常都不让 pipeline 卡死
    try:
        # Step7 结构
        step7_validations = step7_result.get("question_validation", [])
        step7_quality = step7_result.get("meeting_quality", {})

        # 规则引擎：自动映射所有假设
        hypothesis_updates, new_risks, unchanged = compute_hypothesis_updates(
            step5_judgements=step5_judgements,
            step7_validations=step7_validations,
            step7_result=step7_result,
        )

        # LLM 辅助：填充 updated_view 和 why_changed（超时60s则规则兜底）
        if hypothesis_updates:
            try:
                hypothesis_updates = _fill_with_llm(
                    hypothesis_updates=hypothesis_updates,
                    step5_judgements=step5_judgements,
                    step7_result=step7_result,
                    model=model
                )
            except Exception as e:
                print(f"[Step8] LLM 填充失败，使用规则兜底：{e}")
                for h in hypothesis_updates:
                    if not h.updated_view:
                        h.updated_view = _default_updated_view(h)
                    if not h.why_changed:
                        h.why_changed = _default_why_changed(h, step7_result)

        # 综合判断是否显著变化
        has_significant = any(
            h.change_type in (ChangeType.WEAKENED, ChangeType.OVERTURNED)
            for h in hypothesis_updates
        ) or len(new_risks) >= 2

        if not has_significant and step7_quality.get("overall_confidence") in ("high", "medium"):
            has_significant = False
        else:
            has_significant = True

        overall_change = OverallChange(
            is_judgement_significantly_changed=has_significant,
            new_risks=new_risks,
            new_opportunity_added=None
        )

        return Step8Output(
            hypothesis_updates=hypothesis_updates,
            overall_change=overall_change,
            unchanged_hypotheses=unchanged
        )

    except Exception as e:
        import traceback
        print(f"[Step8] update() 异常，使用全量 unchanged 兜底：{e}")
        traceback.print_exc()
        unchanged = [h.get("hypothesis", h.get("dimension", "")) for h in step5_judgements]
        return Step8Output(
            hypothesis_updates=[],
            overall_change=OverallChange(
                is_judgement_significantly_changed=False,
                new_risks=[],
                new_opportunity_added=None
            ),
            unchanged_hypotheses=unchanged
        )


def to_dict(output: Step8Output) -> Dict[str, Any]:
    """将 Step8Output 转为 dict（用于 JSON 持久化）"""
    return {
        "hypothesis_updates": [
            {
                "hypothesis_direction": h.hypothesis_direction.value,  # v2.3 新增
                "hypothesis_id": h.hypothesis_id,
                "hypothesis": h.hypothesis,
                "updated_view": h.updated_view,
                "confidence_change": h.confidence_change,
                "change_type": h.change_type.value,
                "supporting_evidence": h.supporting_evidence,
                "contradicting_evidence": h.contradicting_evidence,
                "why_changed": h.why_changed,
                "source_question_id": h.source_question_id,
            }
            for h in output.hypothesis_updates
        ],
        "unchanged_hypotheses": output.unchanged_hypotheses,
        "overall_change": {
            "is_judgement_significantly_changed": output.overall_change.is_judgement_significantly_changed,
            "new_risks": [
                {
                    "risk": r.risk,
                    "source_question_id": r.source_question_id,
                    "severity": r.severity.value,
                }
                for r in output.overall_change.new_risks
            ],
            "new_opportunity_added": output.overall_change.new_opportunity_added,
        }
    }


def _truncate(s: str, max_len: int = 80) -> str:
    """截断字符串到最大长度"""
    if not s:
        return ""
    return s[:max_len] + "..." if len(s) > max_len else s


def _extract_conclusion_from_text(hypothesis: str, text: str, positive: bool = None) -> str:
    """
    从 hypothesis + text（通常是 updated_view）提取语义结论。

    核心逻辑：
    1. 从 hypothesis 提取主题
    2. 从 updated_view 提取判断词
    3. 输出语义结论
    """
    hyp = hypothesis.strip()
    view = text.strip() if text else ""

    # ============================================================
    # 规则1：从 hypothesis 提取主题（按优先级）
    # ============================================================
    topic_rules = [
        (["新能源客户", "新能源业务", "新能源"], "新能源"),
        (["美妆客户", "美妆业务", "美妆", "欧莱雅", "宝洁", "珀莱雅"], "美妆"),
        (["扭亏", "盈利", "营收", "收入", "商业化"], "商业化"),
        (["AI平台", "AI"], "AI"),
        (["大模型"], "AI"),
        (["客户"], "客户"),
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
    # 规则2：从 updated_view 提取判断词（负向优先）
    # ============================================================
    neg_kw = [
        ("并非", "非真正", "无法", "不成立"),
        ("未形成", "未实现", "未明确", "未进行"),
        ("无意向", "无订单", "无收入"),
        ("不足以", "尚未"),
        ("未验证", "未提供", "仍有", "不确定"),
        ("风险暴露", "失败", "不可替代"),
    ]

    for group in neg_kw:
        if any(kw in view for kw in group):
            if topic:
                if group[0] in ("并非", "非真正", "无法", "不成立", "未形成", "未实现", "未明确", "未进行", "无意向", "无订单", "无收入"):
                    return f"{topic}不成立"
                else:
                    return f"{topic}存疑"
            return "假设存疑"

    # 正向判断（无负向关键词时）
    if positive is True:
        if topic:
            return f"{topic}已验证"
        return "假设成立"

    # 中性
    if topic:
        return f"{topic}待深入"
    return "待验证"


def _hypothesis_to_conclusion(hypothesis: str, updated_view: str = "") -> str:
    """
    将 hypothesis + updated_view 转化为"结论句"（语义摘要，不是截断）。

    核心逻辑：
    1. 从 hypothesis 提取主题
    2. 从 updated_view 提取判断词（负向优先）
    3. 输出语义结论
    """
    hyp = hypothesis.strip()
    view = updated_view.strip() if updated_view else ""

    # 规则1：直接从 updated_view 提取（优先于 hypothesis）
    if view:
        conclusion = _extract_conclusion_from_text(hyp, view, positive=None)
        if conclusion and conclusion not in ("待验证", "需进一步验证"):
            return conclusion

    # 规则2：从 hypothesis 主题生成结论
    topic_rules = [
        (["新能源客户", "新能源业务", "新能源"], "新能源"),
        (["美妆客户", "美妆业务", "美妆", "欧莱雅", "宝洁", "珀莱雅"], "美妆"),
        (["扭亏", "盈利", "营收", "收入", "商业化"], "商业化"),
        (["AI平台", "AI", "大模型", "准确率", "算法"], "AI"),
        (["客户"], "客户"),
        (["壁垒", "护城河", "专利", "IP"], "壁垒"),
        (["团队", "创始人", "CEO", "CTO", "背景"], "团队"),
        (["技术", "研发", "产品", "Demo", "原型"], "技术"),
        (["市场", "规模", "TAM", "空间"], "市场"),
        (["融资", "估值"], "融资"),
        (["竞争", "竞争对手", "赛道", "格局"], "竞争"),
        (["供应链", "产能", "工厂", "制造"], "供应链"),
        (["芯片", "SiC", "功率器件"], "芯片"),
    ]

    for keywords, topic in topic_rules:
        if any(kw in hyp for kw in keywords):
            if any(kw in hyp for kw in ["不", "无", "缺乏", "未", "弱", "风险", "不足", "尚未", "担忧"]):
                return f"{topic}存疑"
            elif any(kw in hyp for kw in ["已", "强", "好", "验证", "确认", "达标", "已有"]):
                return f"{topic}已验证"
            else:
                return f"{topic}待验证"

    # 规则3：兜底——从假设中提取核心词
    skip_words = ["假设", "认为", "可能", "预计", "预期", "判断", "观点", "并非"]
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

    return clean_hyp[:27] + "..." if clean_hyp else "假设待验证"


def _classify_update_signal(update: Dict[str, Any]) -> str:
    """
    核心语义映射函数（Step8 v3 精修版）。

    核心原则：weakened ≠ 负面，weakened = 不确定

    组合规则：
      positive + reinforced        → validated_positive  （假设被证实）
      positive + slightly_reinforced → key_uncertainty   （部分证实但证据弱）
      positive + weakened          → key_uncertainty     （❗关键改动：不直接否定）
      positive + overturned        → confirmed_negative  （被推翻）
      positive + uncertain/reframed → key_uncertainty
      negative + reinforced        → confirmed_negative  （风险假设被确认）
      negative + weakened          → validated_positive  （风险假设被化解）
      negative + uncertain/reframed → key_uncertainty
      neutral + any               → key_uncertainty（中性假设总是不确定）

    Returns:
        "validated_positive" | "confirmed_negative" | "key_uncertainty"
    """
    direction = (update.get("hypothesis_direction") or "neutral").lower()
    change = (update.get("change_type") or "").lower()

    # uncertain/reframed/unchanged → 关键不确定性
    if change in {"uncertain", "reframed", "no_change", "unchanged"}:
        return "key_uncertainty"

    if direction == "positive":
        if change in {"reinforced"}:
            return "validated_positive"
        # ❗ 关键改动：weakened 不再是 confirmed_negative
        if change in {"weakened"}:
            return "key_uncertainty"
        if change in {"slightly_reinforced", "overturned"}:
            # slightly_reinforced: 部分强化但证据弱 → 不确定
            # overturned: 被推翻 → 负面
            return "confirmed_negative" if change == "overturned" else "key_uncertainty"

    if direction == "negative":
        if change in {"reinforced"}:
            return "confirmed_negative"
        if change in {"weakened"}:
            return "validated_positive"
        if change in {"overturned", "slightly_reinforced"}:
            return "key_uncertainty"

    if direction == "neutral":
        return "key_uncertainty"

    return "key_uncertainty"


def _normalize_change_type(update: Dict[str, Any]) -> Dict[str, Any]:
    """
    后处理：纠正 LLM 可能犯的 change_type 错误。

    v3 精修版新增约束：
    1. 语义一致性：change_type 必须与 updated_view 语义一致
    2. 美妆保护：美妆/客户/收入类假设不能 overturned
    3. reinforced 保护：reinforced 只能用于"updated_view 支持原假设"

    规则：
    1. 没有任何证据（supporting + contradicting 都为空）→ uncertain
    2. 只有 missing_evidence（contradicting 非空但都是短字符串）→ uncertain
    3. updated_view 包含否定关键词 + change_type=reinforced → weakened
    4. 美妆/客户/收入类假设 + updated_view 没有"证伪"证据 → 不能 overturned
    5. reinforced 只能是"updated_view 明确支持原假设"
    """
    supporting = update.get("supporting_evidence") or []
    contradicting = update.get("contradicting_evidence") or []
    change = update.get("change_type", "").lower()
    hypothesis = update.get("hypothesis", "")
    updated_view = update.get("updated_view", "") or ""

    # ── 规则0：reinforced 语义一致性检查 ──────────────────────────────
    # 如果 updated_view 包含否定/削弱关键词，不能是 reinforced
    reinforced_blocked_keywords = [
        "辅助工具", "非核心", "不构成", "未能", "未形成", "未实现",
        "无量化", "无数据", "缺乏", "仅作", "准确率低",
        "尚未", "无法", "未验证", "存疑", "不成立"
    ]
    if change == "reinforced":
        # 检查 updated_view 是否"支持原假设"
        # 如果 updated_view 否定/削弱了原假设，应该是 weakened
        if any(kw in updated_view for kw in reinforced_blocked_keywords):
            update["change_type"] = "weakened"
            return update

    # ── 规则1：没有任何证据 → uncertain ───────────────────────────────
    if not supporting and not contradicting:
        update["change_type"] = "uncertain"
        return update

    # ── 规则2：slightly_weakened 约束 ─────────────────────────────────
    # 如果 contradicting 存在但 supporting 不存在，且都是短字符串 → uncertain
    if change == "slightly_weakened" and contradicting and not supporting:
        if all(len(str(x)) < 30 for x in contradicting):
            update["change_type"] = "uncertain"

    # ── 规则3：只有 missing_evidence（没有真正的反证）→ uncertain ────
    if contradicting and not supporting:
        # 检查是否都是"缺失证据"而不是"反证"
        if all(len(str(x)) < 30 for x in contradicting):
            update["change_type"] = "uncertain"

    # ── 规则4：美妆/客户/收入类假设保护 ────────────────────────────────
    # 如果假设涉及美妆/欧莱雅/宝洁/客户/收入，不能 overturned
    beauty_commerce_keywords = [
        "美妆", "欧莱雅", "宝洁", "珀莱雅", "客户", "收入",
        "商业化", "放量", "食品"
    ]
    hypothesis_lower = hypothesis.lower()
    if any(kw in hypothesis_lower for kw in beauty_commerce_keywords):
        if change == "overturned":
            # 美妆有真实收入底盘（1.35亿），不能被 overturned
            # 最多是 uncertain 或 partially_weakened
            update["change_type"] = "uncertain"

    # ── 规则5：overturned 保护 ─────────────────────────────────────────
    # overturned 必须有明确的"证伪"证据，不能只是"没验证"
    if change == "overturned":
        overturned_required_keywords = [
            "造假", "虚假", "欺诈", "不存在", "已失败",
            "明确否认", "合同取消", "合作终止", "已被证伪"
        ]
        overturned_blocked_keywords = [
            "未验证", "未提供", "缺乏证据", "待验证", "未明确",
            "无量化", "无数据", "不确定"
        ]
        # 如果 updated_view 只是"没验证"而不是"证伪"，不能是 overturned
        if any(kw in updated_view for kw in overturned_blocked_keywords):
            if not any(kw in updated_view for kw in overturned_required_keywords):
                update["change_type"] = "uncertain"

    return update


def build_step8_summary(step8_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 Step8 完整输出生成 Step8_summary（v3 语义分离版）。

    核心原则：
    - hypothesis_direction + change_type → 决策信号（validated_positive / confirmed_negative / key_uncertainty）
    - 不再用 change_type 直接推断"好/坏"

    新结构：
    - executive_summary: 执行摘要（≥1句）
    - decision_signals: 三类信号（validated_positives / confirmed_negatives / key_uncertainties）
    - _counts: 统计数字（给 Step9 规则引擎用）
    - key_findings: 保留（给前端展示）
    """
    hypothesis_updates = step8_output.get("hypothesis_updates", [])
    overall_change = step8_output.get("overall_change", {})

    validated_positives: List[Dict[str, Any]] = []
    confirmed_negatives: List[Dict[str, Any]] = []
    key_uncertainties: List[Dict[str, Any]] = []

    # ── 统计（Step9 规则引擎用）───────────────────────────────────────
    counts = {
        "validated_positive": 0,
        "confirmed_negative": 0,
        "key_uncertainty": 0,
        "total": len(hypothesis_updates),
        # 保留 change_type 原始计数（用于兼容 Step9 旧逻辑兜底）
        "reinforced": 0,
        "uncertain": 0,
        "weakened": 0,
    }

    for h in hypothesis_updates:
        # ── 后处理：纠正 change_type 错误 ─────────────────────────────
        h = _normalize_change_type(h)

        ct = h.get("change_type", "")
        hyp = h.get("hypothesis", "")
        updated_view = h.get("updated_view", "")

        # 语义映射：direction × change_type → signal
        signal = _classify_update_signal(h)

        # 生成结论句
        conclusion = _hypothesis_to_conclusion(hyp, updated_view)

        # 提取 required_material（来自 contradicting_evidence）
        contradicting = h.get("contradicting_evidence", [])
        required_material = "；".join(str(x) for x in contradicting[:3]) if contradicting else ""

        item = {
            "hypothesis_id": h.get("hypothesis_id", ""),
            "point": conclusion,
            "source_hypothesis": _truncate(hyp, 80),
            "change_type": ct,
            "hypothesis_direction": h.get("hypothesis_direction", "neutral"),
            "required_material": required_material,
        }

        if signal == "validated_positive":
            validated_positives.append(item)
            counts["validated_positive"] += 1
            if ct in {"reinforced", "slightly_reinforced"}:
                counts["reinforced"] += 1

        elif signal == "confirmed_negative":
            confirmed_negatives.append(item)
            counts["confirmed_negative"] += 1
            if ct in {"weakened", "slightly_weakened", "overturned"}:
                counts["weakened"] += 1

        else:  # key_uncertainty
            key_uncertainties.append(item)
            counts["key_uncertainty"] += 1
            if ct in {"uncertain", "reframed"}:
                counts["uncertain"] += 1

    # 限制每类最多5条
    validated_positives = validated_positives[:5]
    confirmed_negatives = confirmed_negatives[:5]
    key_uncertainties = key_uncertainties[:5]

    # ── 执行摘要 ──────────────────────────────────────────────────────
    executive_summary = _make_executive_summary(
        validated_positives, confirmed_negatives, key_uncertainties
    )

    # ── 兼容旧字段（给旧代码兜底）─────────────────────────────────────
    validated_points = [item["point"] for item in validated_positives]
    invalidated_points = [item["point"] for item in confirmed_negatives]
    uncertain_points = [item["point"] for item in key_uncertainties]

    # ── key_findings（给前端展示）────────────────────────────────────
    key_findings = []
    if counts["confirmed_negative"] > 0:
        key_findings.append(f"⚠️ {counts['confirmed_negative']}项负面信号")
    if counts["key_uncertainty"] > 0:
        key_findings.append(f"❓ {counts['key_uncertainty']}项关键不确定性")
    if counts["validated_positive"] > 0:
        key_findings.append(f"✅ {counts['validated_positive']}项正面信号")

    new_risks = overall_change.get("new_risks", [])
    if new_risks:
        key_findings.append(f"🚨 {len(new_risks)}个新风险暴露")

    # 高优先级结论（confirmed_negative 优先）
    for item in confirmed_negatives[:2]:
        if len(key_findings) < 5 and item["point"] not in key_findings:
            key_findings.append(item["point"])

    key_findings = key_findings[:5]

    return {
        "executive_summary": executive_summary,
        "decision_signals": {
            "validated_positives": validated_positives,
            "confirmed_negatives": confirmed_negatives,
            "key_uncertainties": key_uncertainties,
        },
        # ── 兼容旧字段（Step9 兜底逻辑仍用这些）──────────────────────
        "key_findings": key_findings,
        "validated_points": validated_points,
        "invalidated_points": invalidated_points,
        "uncertain_points": uncertain_points,
        "_counts": counts,
    }


def _make_executive_summary(
    pos: List[Dict[str, Any]],
    neg: List[Dict[str, Any]],
    uncertain: List[Dict[str, Any]]
) -> str:
    """生成执行摘要"""
    parts = []
    if pos:
        parts.append(f"确认{len(pos)}项正面信号")
    if neg:
        parts.append(f"暴露{len(neg)}项负面信号")
    if uncertain:
        parts.append(f"仍有{len(uncertain)}项关键不确定性")

    if not parts:
        return "会议未提供显著改变原有判断的信息。"

    summary = "，".join(parts) + "。"
    if neg and pos:
        summary += "负面信号多于正面，项目判断趋于谨慎。"
    elif neg and not pos:
        summary += "建议暂停推进，待关键问题明确后再评估。"
    elif pos and not neg:
        summary += "项目存在积极信号，可继续尽调。"
    elif uncertain and not neg and not pos:
        summary += "当前信息不足以支撑明确判断，建议补充材料。"
    return summary
