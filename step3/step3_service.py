# -*- coding: utf-8 -*-
"""
Step3 服务：基于 Step2 外部约束的 BP 叙事审查

从"BP 内部一致性检查"升级为"用外部约束审查 BP 叙事"
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .step3_prompt import build_step3_prompt
from .step3_schema import (
    ConsistencyCheck,
    Tension,
    PackagingSignal,
    Step3Output,
)
from services.deepseek_service import call_deepseek

logger = logging.getLogger(__name__)


def run_step3(
    bp_text: str,
    project_structure: Dict[str, Any],
    step2_json: Optional[Dict[str, Any]] = None,
    user_input: Optional[Dict[str, Any]] = None,
    investment_modules: Optional[List[Dict[str, Any]]] = None,
    model: str = "deepseek-chat",
) -> Step3Output:
    """
    运行 Step3：基于 Step2 外部约束的 BP 叙事审查

    Args:
        bp_text: BP原文
        project_structure: Step3 项目结构识别结果
        step2_json: Step2 外部约束检查结果（新增必填）
        user_input: Step1 用户输入（可选）
        investment_modules: 投资思维模块列表（可选）
        model: 使用的模型

    Returns:
        Step3Output: 一致性检查、关键矛盾、包装信号（均含 Step2 引用）
    """

    # 构建 prompt
    prompt = build_step3_prompt(
        bp_text=bp_text,
        project_structure=project_structure,
        step2_json=step2_json,
        user_input=user_input,
        investment_modules=investment_modules,
    )

    # 调用 LLM
    try:
        response = call_deepseek(
            system_prompt="你是一个专业的投资分析师，擅长用外部行业逻辑审查 BP 叙事，发现包装和叙事漏洞。",
            user_prompt=prompt,
            model=model,
            temperature=0.3,
        )
    except Exception as e:
        logger.error(f"Step3 LLM 调用失败: {e}")
        return _fallback_output(step2_json)

    # 解析结果
    try:
        result = _parse_response(response)
        # 补充 Step2 引用统计
        result = _add_step2_stats(result, step2_json)
        return result
    except Exception as e:
        logger.error(f"Step3 解析失败: {e}")
        result = _try_fix_and_parse(response)
        if result:
            result = _add_step2_stats(result, step2_json)
            return result
        return _fallback_output(step2_json)


def _parse_response(response: str) -> Step3Output:
    """解析 LLM 响应"""
    json_str = _extract_json(response)
    data = json.loads(json_str)

    consistency_checks = [
        ConsistencyCheck(**item) for item in data.get("consistency_checks", [])
    ]
    tensions = [
        Tension(**item) for item in data.get("tensions", [])
    ]
    overpackaging_signals = [
        PackagingSignal(**item) for item in data.get("overpackaging_signals", [])
    ]

    return Step3Output(
        consistency_checks=consistency_checks,
        tensions=tensions,
        overpackaging_signals=overpackaging_signals,
        summary=data.get("summary", ""),
    )


def _extract_json(text: str) -> str:
    """从文本中提取 JSON"""
    try:
        json.loads(text)
        return text
    except:
        pass

    import re
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()

    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        return match.group(1).strip()

    raise ValueError("无法从响应中提取 JSON")


def _try_fix_and_parse(response: str) -> Optional[Step3Output]:
    """尝试修复 JSON 后解析"""
    import re

    cleaned = response.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        return _parse_response(cleaned)
    except:
        pass

    cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))

    try:
        return _parse_response(cleaned)
    except:
        return None


def _add_step2_stats(output: Step3Output, step2_json: Optional[dict]) -> Step3Output:
    """补充 Step2 引用统计"""
    if not step2_json:
        return output

    # 统计 consistency_checks 中引用了 Step2 的条目
    caution_refs = 0
    contradict_refs = 0
    total_refs = 0

    for check in output.consistency_checks:
        if check.related_step2_check:
            total_refs += 1
        if check.judgement in ("contradict", "contradict"):
            contradict_refs += 1
        elif check.judgement == "uncertain":
            caution_refs += 1

    # 统计包装信号中引用了 Step2 的条目
    for signal in output.overpackaging_signals:
        if signal.related_step2_constraint:
            caution_refs += 1

    output.step2_constraints_used = total_refs
    output.step2_caution_references = caution_refs
    output.step2_contradict_references = contradict_refs
    output.step2_version = step2_json.get("schema_version", "")

    return output


def _fallback_output(step2_json: Optional[dict] = None) -> Step3Output:
    """解析失败时的兜底输出"""
    output = Step3Output(
        consistency_checks=[
            ConsistencyCheck(
                topic="系统解析",
                claim="Step3 未能成功解析",
                reality="解析失败",
                gap="请检查 BP 内容或重试",
                judgement="uncertain",
                confidence="low",
                related_step2_check="",
                external_constraint="",
                bp_claim_checked="",
            )
        ],
        tensions=[],
        overpackaging_signals=[],
        summary="Step3 解析失败，请重试",
    )

    if step2_json:
        output.step2_version = step2_json.get("schema_version", "")

    return output


def run_step3_simple(
    bp_text: str,
    project_structure: Dict[str, Any],
    step2_json: Optional[Dict[str, Any]] = None,
    investment_modules: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    简单版本：返回字典而不是 Pydantic 模型

    用于 pipeline 集成
    """
    result = run_step3(
        bp_text,
        project_structure,
        step2_json=step2_json,
        investment_modules=investment_modules,
    )

    return {
        "consistency_checks": [c.model_dump() for c in result.consistency_checks],
        "tensions": [t.model_dump() for t in result.tensions],
        "overpackaging_signals": [p.model_dump() for p in result.overpackaging_signals],
        "summary": result.summary,
        "step2_constraints_used": result.step2_constraints_used,
        "step2_caution_references": result.step2_caution_references,
        "step2_contradict_references": result.step2_contradict_references,
        "step2_version": result.step2_version,
    }
