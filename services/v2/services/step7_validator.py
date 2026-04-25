# -*- coding: utf-8 -*-
"""
step7_validator.py — 问题对齐 & 回答质量判断（v2.2：两步架构）

Step7A: 问题 → Step6信息 匹配（只输出 ni_xxx 列表）
Step7B: 基于匹配结果，判断回答状态/质量/影响

核心原则：Step7 不读 meeting_record，只消费 Step6.new_information
"""
import json
import re
from typing import Dict, Any, List

from ..schemas import (
    Step7Output, QuestionValidation, MeetingQuality,
    AnswerStatus, QualityLevel, AnswerImpact, ConfidenceLevel
)
from .. import prompts
from services.deepseek_service import call_deepseek


# ---- Enum 映射 ----
STATUS_MAP = {
    "answered": AnswerStatus.ANSWERED,
    "partially_answered": AnswerStatus.PARTIALLY_ANSWERED,
    "indirectly_answered": AnswerStatus.INDIRECTLY_ANSWERED,
    "evaded": AnswerStatus.EVADED,
    "not_answered": AnswerStatus.NOT_ANSWERED,
}

QUALITY_MAP = {
    "high": QualityLevel.HIGH,
    "medium": QualityLevel.MEDIUM,
    "low": QualityLevel.LOW,
}

IMPACT_MAP = {
    "strengthens": AnswerImpact.STRENGTHENS,
    "weakens": AnswerImpact.WEAKENS,
    "slightly_strengthens": AnswerImpact.SLIGHTLY_STRENGTHENS,
    "slightly_weakens": AnswerImpact.SLIGHTLY_WEAKENS,
    "no_change": AnswerImpact.NO_CHANGE,
    "unclear": AnswerImpact.UNCLEAR,
}

CONFIDENCE_MAP = {
    "high": ConfidenceLevel.HIGH,
    "medium": ConfidenceLevel.MEDIUM,
    "low": ConfidenceLevel.LOW,
}


def _parse_status(s: str) -> AnswerStatus:
    return STATUS_MAP.get(str(s).lower(), AnswerStatus.NOT_ANSWERED)


def _parse_quality(s: str) -> QualityLevel:
    return QUALITY_MAP.get(str(s).lower(), QualityLevel.MEDIUM)


def _parse_impact(s: str) -> AnswerImpact:
    return IMPACT_MAP.get(str(s).lower(), AnswerImpact.NO_CHANGE)


def _parse_confidence(s: str) -> ConfidenceLevel:
    return CONFIDENCE_MAP.get(str(s).lower(), ConfidenceLevel.MEDIUM)


def _repair_json(text: str) -> str:
    """JSON截断修复（同step6_extractor）"""
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


# ============================================================
# Step7A：问题-信息匹配
# ============================================================

def _format_questions_for_matching(questions: List[str]) -> str:
    """格式化问题列表供 Step7A 使用（支持带 source 的问题）"""
    lines = []
    for i, q in enumerate(questions):
        if isinstance(q, dict):
            # 新的 dict 格式：包含 question_id, source, profile_id
            qid = q.get("question_id", f"q_{i+1}")
            source = q.get("source", "base")
            lines.append(f"{qid} [{source}]: {q.get('question', '')}")
        else:
            # 旧的字符串格式
            lines.append(f"q_{i+1}: {q}")
    return "\n".join(lines)


def _normalize_questions(questions: List[str]) -> List[Dict[str, Any]]:
    """
    标准化问题列表为 dict 格式。

    兼容：
    - 旧格式：["问题1", "问题2"]
    - 新格式：[{"question_id": "q_001", "question": "问题1", "source": "base", ...}]
    """
    result = []
    for i, q in enumerate(questions):
        if isinstance(q, dict):
            result.append({
                "question_id": q.get("question_id", f"q_{i+1:03d}"),
                "question": q.get("question", ""),
                "source": q.get("source", "base"),
                "profile_id": q.get("profile_id", ""),
                "priority": q.get("priority", "medium")
            })
        else:
            # 字符串格式，默认为 base
            result.append({
                "question_id": f"q_{i+1:03d}",
                "question": q,
                "source": "base",
                "profile_id": "",
                "priority": "medium"
            })
    return result


def _format_info_for_matching(new_information: List[Dict[str, Any]]) -> str:
    """格式化 Step6 输出供 Step7A 使用"""
    lines = []
    for ni in new_information:
        lines.append(
            f"{ni['id']}: {ni['content']} (type={ni.get('info_type', 'unknown')})"
        )
    return "\n".join(lines)


def run_step7a(
    questions: List[Dict[str, Any]],
    new_information: List[Dict[str, Any]],
    model: str = None
) -> List[Dict[str, Any]]:
    """
    Step7A：问题-信息匹配

    Args:
        questions: 标准化的会前问题列表（dict 格式）
        new_information: Step6.new_information 列表
        model: DeepSeek 模型名

    Returns:
        question_matches: List[Dict]，每项含 question_id/question/matched_information_ids/reason/source/profile_id
    """
    # 提取纯问题文本用于 prompt
    question_texts = [q.get("question", "") if isinstance(q, dict) else q for q in questions]

    system_prompt, user_prompt = prompts.build_step7a_prompt(
        questions=question_texts,
        new_information=new_information
    )
    raw = call_deepseek(system_prompt, user_prompt, model=model)
    parsed = _parse_json(raw)

    raw_matches = parsed.get("question_matches", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
    if not isinstance(raw_matches, list):
        raw_matches = []

    # 建立 LLM 返回 qid -> 原始问题信息的映射
    # LLM 可能只返回纯问题文本，我们需要匹配回原始的 question_id/source/profile_id
    qid_to_meta = {}
    for i, q in enumerate(questions):
        q_meta = {
            "question_id": q.get("question_id", f"q_{i+1:03d}"),
            "source": q.get("source", "base"),
            "profile_id": q.get("profile_id", ""),
            "priority": q.get("priority", "medium")
        }
        # 同时用 question_id 和 question 文本做映射
        if isinstance(q, dict):
            qid_to_meta[q.get("question_id", f"q_{i+1:03d}")] = q_meta
            qid_to_meta[q.get("question", "")] = q_meta

    # 标准化输出：确保每条有 question_id 和 matched_information_ids
    # 兼容：LLM 可能把 ID 写在 reason 里而不是 matched_information_ids 里
    ni_pattern = re.compile(r"ni_\d+")
    result = []
    for i, m in enumerate(raw_matches):
        qid = m.get("question_id", f"q_{i+1:03d}")
        if not qid:
            qid = f"q_{i+1:03d}"
        question_text = m.get("question", question_texts[i] if i < len(question_texts) else "")

        # 从映射中获取 source/profile_id
        meta = qid_to_meta.get(qid) or qid_to_meta.get(question_text) or {
            "source": "base",
            "profile_id": "",
            "priority": "medium"
        }

        ids = m.get("matched_information_ids", [])
        # 如果列表为空，尝试从 reason 字段提取 ni_xxx
        if not ids or not any(ids):
            reason_text = m.get("reason", "")
            ids = list(dict.fromkeys(ni_pattern.findall(reason_text)))
        result.append({
            "question_id": qid,
            "question": question_text,
            "matched_information_ids": ids if isinstance(ids, list) else [],
            "reason": m.get("reason", ""),
            "source": meta.get("source", "base"),
            "profile_id": meta.get("profile_id", ""),
            "priority": meta.get("priority", "medium")
        })
    return result


# ============================================================
# Step7B：回答质量判断
# ============================================================

def run_step7b(
    question_matches: List[Dict[str, Any]],
    new_information: List[Dict[str, Any]],
    model: str = None
) -> List[Dict[str, Any]]:
    """
    Step7B：基于匹配结果，判断回答状态/质量/影响

    Args:
        question_matches: Step7A 输出（已包含 source/profile_id）
        new_information: Step6.new_information 列表
        model: DeepSeek 模型名

    Returns:
        question_validations: List[Dict]，每项含 QuestionValidation 所有字段（包含 question_source/profile_id）
    """
    system_prompt, user_prompt = prompts.build_step7b_prompt(
        question_matches=question_matches,
        new_information=new_information
    )
    raw = call_deepseek(system_prompt, user_prompt, model=model)
    parsed = _parse_json(raw)

    raw_validations = parsed.get("question_validation", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
    if not isinstance(raw_validations, list):
        raw_validations = []

    # 建立 ni_id -> content 的映射（用于 matched_information_summary）
    ni_id_to_content = {ni.get("id", ""): ni.get("content", "") for ni in new_information}

    result = []
    for i, v in enumerate(raw_validations):
        qid = v.get("question_id", question_matches[i].get("question_id", f"q_{i+1:03d}"))
        if not qid:
            qid = f"q_{i+1:03d}"

        # matched_information_ids 优先用 Step7B 返回的，其次用 Step7A 的
        matched_ids = v.get("matched_information_ids", question_matches[i].get("matched_information_ids", []))
        if isinstance(matched_ids, str):
            matched_ids = [matched_ids]

        # matched_information_summary：根据 ID 提取 content
        matched_summaries = [ni_id_to_content.get(mid, "") for mid in matched_ids if ni_id_to_content.get(mid)]
        matched_summaries = [s for s in matched_summaries if s]  # 去空

        missing = v.get("missing_evidence", [])
        if isinstance(missing, str):
            missing = [missing]

        # answer_summary 必填兜底
        raw_summary = v.get("answer_summary", "").strip()
        if not raw_summary:
            raw_summary = "（会议记录中未找到该问题的明确回答）"

        # 获取 source/profile_id（来自 Step7A）
        source = question_matches[i].get("source", "base")
        profile_id = question_matches[i].get("profile_id", "")

        result.append({
            "question_id": qid,
            "original_question": v.get("question", question_matches[i].get("question", "")),
            "matched_information_ids": matched_ids,
            "matched_information_summary": matched_summaries,
            "answer_summary": raw_summary,
            "status": v.get("status", "not_answered"),
            "quality": v.get("quality", "medium"),
            "impact": v.get("impact", "no_change"),
            "missing_evidence": missing,
            "follow_up_question": v.get("follow_up_question", ""),
            "question_source": source,  # v2.3 新增
            "profile_id": profile_id,  # v2.3 新增
        })
    return result


# ============================================================
# 会议质量综合评估
# ============================================================

def _compute_meeting_quality(
    question_validations: List[Dict[str, Any]],
    new_information: List[Dict[str, Any]]
) -> MeetingQuality:
    """
    基于问题验证结果，综合评估会议整体质量（规则计算，不依赖 LLM）

    规则：
    - answered_count / partially_count / weak_count（evaded+not_answered）/ missing_evidence_count
    - answer_directness: answered率 > 70% = high, > 40% = medium, else low
    - evidence_strength: high confidence信息占比高 = high
    - evasion_level: evaded率高 = high（高回避）
    - evasion_signals: 收集所有 evaded/not_answered 的问题
    - overall_confidence: 综合上面四项计数判断
    """
    if not question_validations:
        return MeetingQuality(
            answer_directness=ConfidenceLevel.MEDIUM,
            evidence_strength=ConfidenceLevel.MEDIUM,
            evasion_level=ConfidenceLevel.LOW,
            overall_confidence=ConfidenceLevel.MEDIUM,
            evasion_signals=[],
            answered_count=0,
            partially_count=0,
            weak_count=0,
            missing_evidence_count=0,
        )

    total = len(question_validations)
    answered_count = sum(1 for q in question_validations if q["status"] == "answered")
    partially_count = sum(1 for q in question_validations if q["status"] in ("partially_answered", "indirectly_answered"))
    weak_count = sum(1 for q in question_validations if q["status"] in ("evaded", "not_answered"))
    missing_evidence_count = sum(
        len(q.get("missing_evidence", []))
        for q in question_validations
    )

    ratio = answered_count / total

    # answer_directness
    if ratio > 0.7:
        answer_directness = ConfidenceLevel.HIGH
    elif ratio > 0.4:
        answer_directness = ConfidenceLevel.MEDIUM
    else:
        answer_directness = ConfidenceLevel.LOW

    # evidence_strength: 基于 Step6 中 high confidence 信息占比
    if new_information:
        high_conf_count = sum(
            1 for ni in new_information
            if ni.get("confidence") in ("high", "HIGH")
        )
        evidence_ratio = high_conf_count / len(new_information)
        if evidence_ratio > 0.6:
            evidence_strength = ConfidenceLevel.HIGH
        elif evidence_ratio > 0.3:
            evidence_strength = ConfidenceLevel.MEDIUM
        else:
            evidence_strength = ConfidenceLevel.LOW
    else:
        evidence_strength = ConfidenceLevel.LOW

    # evasion_level
    evasion_ratio = weak_count / total
    if evasion_ratio > 0.5:
        evasion_level = ConfidenceLevel.HIGH
    elif evasion_ratio > 0.2:
        evasion_level = ConfidenceLevel.MEDIUM
    else:
        evasion_level = ConfidenceLevel.LOW

    # overall_confidence: answered + high quality 占比
    good = sum(1 for q in question_validations
               if q["status"] in ("answered", "partially_answered", "indirectly_answered")
               and q["quality"] in ("high", "HIGH"))
    if good / total > 0.6:
        overall_confidence = ConfidenceLevel.HIGH
    elif good / total > 0.3:
        overall_confidence = ConfidenceLevel.MEDIUM
    else:
        overall_confidence = ConfidenceLevel.LOW

    # evasion_signals
    evasion_signals = [
        f"问题「{q['original_question'][:30]}...」未得到有效回答"
        for q in question_validations
        if q["status"] in ("evaded", "not_answered")
    ]

    return MeetingQuality(
        answer_directness=answer_directness,
        evidence_strength=evidence_strength,
        evasion_level=evasion_level,
        overall_confidence=overall_confidence,
        consistency=ConfidenceLevel.MEDIUM,
        evasion_signals=evasion_signals,
        answered_count=answered_count,
        partially_count=partially_count,
        weak_count=weak_count,
        missing_evidence_count=missing_evidence_count,
    )


# ============================================================
# 主入口：validate（兼容旧签名 + 新两步架构）
# ============================================================

def validate(
    step4_questions: List[str],
    meeting_record: str = None,
    step6_summary: str = None,
    step6_new_information: List[Dict[str, Any]] = None,
    model: str = None
) -> Step7Output:
    """
    Step7：问题对齐 & 回答质量判断

    优先使用新的两步架构（Step7A + Step7B），需要传入 step6_new_information。
    兼容旧签名（用 meeting_record + step6_summary），但不推荐。

    Args:
        step4_questions: 会前问题列表（支持两种格式）：
                        - 旧格式：["问题1", "问题2"]（字符串列表）
                        - 新格式：[{"question_id": "q_001", "question": "问题1", "source": "base/profile", ...}]
        meeting_record: 原始会议记录（旧参数，v2.2 不再使用）
        step6_summary: Step6摘要（旧参数，v2.2 不再使用）
        step6_new_information: Step6.new_information（推荐参数）
        model: DeepSeek 模型名
    """
    # ---- 优先走新两步架构 ----
    if step6_new_information is not None:
        # 标准化问题格式
        normalized_questions = _normalize_questions(step4_questions)

        # Step7A: 问题-信息匹配
        question_matches = run_step7a(
            questions=normalized_questions,
            new_information=step6_new_information,
            model=model
        )
        # Step7B: 回答质量判断
        question_validations_raw = run_step7b(
            question_matches=question_matches,
            new_information=step6_new_information,
            model=model
        )
        # 构建 QuestionValidation 对象
        question_validations = [
            QuestionValidation(
                question_id=v["question_id"],
                original_question=v["original_question"],
                matched_information_ids=v["matched_information_ids"],
                matched_information_summary=v["matched_information_summary"],
                answer_summary=v["answer_summary"],
                status=_parse_status(v["status"]),
                quality=_parse_quality(v["quality"]),
                impact=_parse_impact(v["impact"]),
                missing_evidence=v["missing_evidence"],
                follow_up_question=v["follow_up_question"],
                question_source=v.get("question_source", "base"),  # v2.3 新增
                profile_id=v.get("profile_id", ""),  # v2.3 新增
            )
            for v in question_validations_raw
        ]
        # 综合会议质量
        meeting_quality = _compute_meeting_quality(
            question_validations_raw,
            step6_new_information
        )
        return Step7Output(
            question_validation=question_validations,
            meeting_quality=meeting_quality
        )

    # ---- 兼容旧签名（直接读 meeting_record，不推荐） ----
    system_prompt, user_prompt = prompts.build_step7_prompt(
        step4_questions=step4_questions,
        meeting_record=meeting_record or "",
        step6_summary=step6_summary or ""
    )
    raw = call_deepseek(system_prompt, user_prompt, model=model)
    parsed = _parse_json(raw)

    if not isinstance(parsed, dict):
        parsed = {}

    # 旧格式兼容（已确保是dict）
    raw_validations = parsed.get("question_validation", [])
    if not isinstance(raw_validations, list):
        raw_validations = []

    question_validations = [
        QuestionValidation(
            question_id=f"q_{i+1}",
            original_question=r.get("original_question", ""),
            matched_information_ids=[],
            answer_summary=r.get("answer_summary", ""),
            status=_parse_status(r.get("status", "")),
            quality=_parse_quality(r.get("quality", "")),
            impact=AnswerImpact.NO_CHANGE,
            missing_evidence=r.get("missing_evidence", []),
            follow_up_question=r.get("follow_up_question", ""),
        )
        for i, r in enumerate(raw_validations)
    ]

    raw_quality = parsed.get("meeting_quality", {})
    meeting_quality = MeetingQuality(
        answer_directness=_parse_confidence(raw_quality.get("answer_directness", "medium")),
        evidence_strength=_parse_confidence(raw_quality.get("evidence_strength", "medium")),
        evasion_level=_parse_confidence(raw_quality.get("evasion_level", "medium")),
        overall_confidence=_parse_confidence(raw_quality.get("overall_confidence", "medium")),
        consistency=_parse_confidence(raw_quality.get("consistency", "medium")),
        evasion_signals=raw_quality.get("evasion_signals", []),
    )

    return Step7Output(
        question_validation=question_validations,
        meeting_quality=meeting_quality
    )


def to_dict(output: Step7Output) -> Dict[str, Any]:
    """将 Step7Output 转为 dict（用于 JSON 持久化）"""
    mq = output.meeting_quality
    return {
        "meeting_quality": {
            "answer_directness": mq.answer_directness.value,
            "evidence_strength": mq.evidence_strength.value,
            "evasion_level": mq.evasion_level.value,
            "overall_confidence": mq.overall_confidence.value,
            "consistency": mq.consistency.value,
            "evasion_signals": mq.evasion_signals,
            # v2.2.1 规则计算原始计数
            "answered_count": mq.answered_count,
            "partially_count": mq.partially_count,
            "weak_count": mq.weak_count,
            "missing_evidence_count": mq.missing_evidence_count,
        },
        "question_validation": [
            {
                "question_id": v.question_id,
                "original_question": v.original_question,
                "matched_information_ids": v.matched_information_ids,
                "matched_information_summary": v.matched_information_summary,  # v2.2.1
                "answer_summary": v.answer_summary,
                "status": v.status.value,
                "quality": v.quality.value,
                "impact": v.impact.value,
                "missing_evidence": v.missing_evidence,
                "follow_up_question": v.follow_up_question,
                "question_source": v.question_source,  # v2.3 新增
                "profile_id": v.profile_id,  # v2.3 新增
            }
            for v in output.question_validation
        ]
    }
