# -*- coding: utf-8 -*-
"""
step6_extractor.py — 新增信息提取服务
"""
import json
import re
from typing import Dict, Any, List

from ..schemas import (
    Step6Output, NewInformation,
    InfoCategory, ImportanceLevel, ConfidenceLevel
)
from .. import prompts
from services.deepseek_service import call_deepseek


# Category 映射（LLM 输出 → Enum）
CATEGORY_MAP = {
    "收入": InfoCategory.REVENUE,
    "客户": InfoCategory.CUSTOMER,
    "技术": InfoCategory.TECH,
    "产品": InfoCategory.PRODUCT,
    "产能": InfoCategory.CAPACITY,
    "团队": InfoCategory.TEAM,
    "财务": InfoCategory.FINANCE,
    "战略": InfoCategory.STRATEGY,
    "市场": InfoCategory.MARKET,
}

IMPORTANCE_MAP = {
    "high": ImportanceLevel.HIGH,
    "medium": ImportanceLevel.MEDIUM,
    "low": ImportanceLevel.LOW,
}

CONFIDENCE_MAP = {
    "high": ConfidenceLevel.HIGH,
    "medium": ConfidenceLevel.MEDIUM,
    "low": ConfidenceLevel.LOW,
}

VALID_INFO_TYPES = {
    "fact", "claim", "number", "plan", "risk_signal", "correction"
}

VALID_NOVELTY_TYPES = {
    "new", "more_specific", "contradiction", "confirmation"
}


def _parse_confidence(s) -> ConfidenceLevel:
    if not s:
        return ConfidenceLevel.MEDIUM
    return CONFIDENCE_MAP.get(str(s).lower(), ConfidenceLevel.MEDIUM)


def _parse_info_type(s) -> str:
    if not s:
        return "claim"
    s = str(s).lower().strip()
    return s if s in VALID_INFO_TYPES else "claim"


def _parse_novelty_type(s) -> str:
    if not s:
        return "new"
    s = str(s).lower()
    return s if s in VALID_NOVELTY_TYPES else "new"


def _validate_new_information(items: list) -> list:
    """
    Step6 输出质检：
    1. content 不能为空
    2. evidence 不能为空
    3. 去重（按 content 文本）
    4. 没有 related_prior_judgement 时补默认值
    5. 没有 follow_up_hint 时补默认值
    """
    valid = []
    seen = set()

    for item in items:
        if not item.content:
            continue
        if not item.evidence:
            continue

        dedup_key = item.content.strip()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        if not item.related_prior_judgement:
            item.related_prior_judgement = "未匹配到明确会前判断"

        if not item.follow_up_hint:
            item.follow_up_hint = "后续需进一步核实该信息的真实性和影响。"

        valid.append(item)

    return valid


def _parse_new_information(raw: Dict[str, Any], idx: int) -> NewInformation:
    """解析 LLM 输出的单条 new_information"""
    cat_str = str(raw.get("category", "战略")).strip()
    cat = CATEGORY_MAP.get(cat_str, InfoCategory.STRATEGY)

    imp_str = str(raw.get("importance", "medium")).lower()
    imp = IMPORTANCE_MAP.get(imp_str, ImportanceLevel.MEDIUM)

    return NewInformation(
        id=str(raw.get("id", f"ni_{idx + 1:03d}")).strip(),
        content=str(raw.get("content", "")).strip(),
        category=cat,
        evidence=str(raw.get("evidence", "")).strip(),
        importance=imp,
        contradicts_bp=bool(raw.get("contradicts_bp", False)),
        is_critical=bool(raw.get("is_critical", False)),
        info_type=_parse_info_type(raw.get("info_type", "claim")),
        novelty_type=_parse_novelty_type(raw.get("novelty_type", "new")),
        confidence=_parse_confidence(raw.get("confidence", "medium")),
        affects_judgement=str(raw.get("affects_judgement", "")).strip(),
        related_prior_judgement=str(raw.get("related_prior_judgement", "")).strip(),
        follow_up_hint=str(raw.get("follow_up_hint", "")).strip(),
        # v2.2 新增：转写噪音标记
        transcript_noise=bool(raw.get("transcript_noise", False)),
    )


def extract(
    step5_summary: str,
    meeting_record: str,
    model: str = None
) -> Step6Output:
    """
    Step6：新增信息提取

    Args:
        step5_summary: 1.0 Step5 的会前判断摘要
        meeting_record: 原始会议记录
        model: DeepSeek 模型名

    Returns:
        Step6Output: 包含所有新增信息
    """
    system_prompt, user_prompt = prompts.build_step6_prompt(
        step5_summary=step5_summary,
        meeting_record=meeting_record
    )

    raw_response = call_deepseek(system_prompt, user_prompt, model=model)

    # 解析 JSON
    parsed = _parse_json_response(raw_response)

    if isinstance(parsed, dict) and "new_information" in parsed:
        items = parsed["new_information"]
    elif isinstance(parsed, list):
        items = parsed
    else:
        items = []

    # 构建输出
    new_info_list = [_parse_new_information(item, i) for i, item in enumerate(items)]
    # 质量过滤：没有 evidence 的信息直接丢弃，不污染后续判断
    new_info_list = _validate_new_information(new_info_list)

    meeting_summary = parsed.get("meeting_summary", "") if isinstance(parsed, dict) else ""

    return Step6Output(
        meeting_summary=meeting_summary,
        new_information=new_info_list
    )


def _repair_truncated_json(text: str) -> str:
    """
    尝试修复被截断的 JSON：
    1. 去掉 markdown 代码块
    2. 直接解析（通常够用）
    3. 逐行移除末尾，找最后一个有效位置
    4. 若行级也失败，用逐字二分找最后有效位置
    """
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # 策略1：直接解析
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 策略2：逐行移除
    lines = text.splitlines()
    for i in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:i])
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue

    # 策略3：逐字二分查找（10k 字符内最多 log2(10000)≈14 次）
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


def _parse_json_response(text: str) -> Any:
    """从 LLM 输出中提取 JSON（支持 markdown 代码块 + 截断修复）"""
    repaired = _repair_truncated_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        raise ValueError(f"无法解析 LLM JSON 输出：\n{text[:300]}")


def to_dict(output: Step6Output) -> Dict[str, Any]:
    """将 Step6Output 转为 dict（用于 JSON 持久化）"""
    infos = output.new_information

    return {
        "meeting_summary": output.meeting_summary,
        "quality_check": {
            "total_count": len(infos),
            "critical_count": sum(1 for ni in infos if ni.is_critical),
            "high_importance_count": sum(
                1 for ni in infos
                if ni.importance.value == "high"
            ),
            "contradiction_count": sum(1 for ni in infos if ni.contradicts_bp),
            "low_confidence_count": sum(
                1 for ni in infos
                if ni.confidence.value == "low"
            ),
            "claim_count": sum(1 for ni in infos if ni.info_type == "claim"),
            "fact_count": sum(1 for ni in infos if ni.info_type == "fact"),
            "number_count": sum(1 for ni in infos if ni.info_type == "number"),
            "plan_count": sum(1 for ni in infos if ni.info_type == "plan"),
        },
        "new_information": [
            {
                "id": ni.id,
                "content": ni.content,
                "category": ni.category.value if ni.category else "",
                "evidence": ni.evidence,
                "importance": ni.importance.value if ni.importance else "",
                "contradicts_bp": ni.contradicts_bp,
                "is_critical": ni.is_critical,
                "info_type": ni.info_type,
                "novelty_type": ni.novelty_type,
                "confidence": ni.confidence.value if ni.confidence else "medium",
                "affects_judgement": ni.affects_judgement,
                "related_prior_judgement": ni.related_prior_judgement,
                "follow_up_hint": ni.follow_up_hint,
                "transcript_noise": ni.transcript_noise,
            }
            for ni in infos
        ]
    }
