# -*- coding: utf-8 -*-
"""
Step3B 服务：BP一致性 & 包装识别
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .step3b_prompt import build_step3b_prompt
from .step3b_schema import (
    ConsistencyCheck,
    Tension,
    PackagingSignal,
    Step3BOutput,
)
from services.deepseek_service import call_deepseek

logger = logging.getLogger(__name__)


def run_step3b(
    bp_text: str,
    project_structure: Dict[str, Any],
    user_input: Optional[Dict[str, Any]] = None,
    investment_modules: Optional[List[Dict[str, Any]]] = None,
    model: str = "deepseek-chat",
) -> Step3BOutput:
    """
    运行 Step3B：BP一致性 & 包装识别

    Args:
        bp_text: BP原文
        project_structure: Step3 项目结构识别结果
        user_input: Step1 用户输入（可选）
        investment_modules: 投资思维模块列表（可选）
        model: 使用的模型

    Returns:
        Step3BOutput: 一致性检查、关键矛盾、包装信号
    """

    # 构建 prompt
    prompt = build_step3b_prompt(
        bp_text=bp_text,
        project_structure=project_structure,
        user_input=user_input,
        investment_modules=investment_modules,
    )

    # 调用 LLM
    try:
        response = call_deepseek(
            system_prompt="你是一个专业的投资分析师，擅长发现BP中的逻辑漏洞和叙事包装。",
            user_prompt=prompt,
            model=model,
            temperature=0.3,  # 偏低，保持分析严谨
        )
    except Exception as e:
        logger.error(f"Step3B LLM 调用失败: {e}")
        return _fallback_output()

    # 解析结果
    try:
        result = _parse_response(response)
        return result
    except Exception as e:
        logger.error(f"Step3B 解析失败: {e}")
        # 尝试修复 JSON
        result = _try_fix_and_parse(response)
        if result:
            return result
        return _fallback_output()


def _parse_response(response: str) -> Step3BOutput:
    """解析 LLM 响应"""
    # 提取 JSON
    json_str = _extract_json(response)

    data = json.loads(json_str)

    # 构建输出
    consistency_checks = [
        ConsistencyCheck(**item) for item in data.get("consistency_checks", [])
    ]

    tensions = [
        Tension(**item) for item in data.get("tensions", [])
    ]

    overpackaging_signals = [
        PackagingSignal(**item) for item in data.get("overpackaging_signals", [])
    ]

    return Step3BOutput(
        consistency_checks=consistency_checks,
        tensions=tensions,
        overpackaging_signals=overpackaging_signals,
        summary=data.get("summary", ""),
    )


def _extract_json(text: str) -> str:
    """从文本中提取 JSON"""
    # 尝试直接解析
    try:
        json.loads(text)
        return text
    except:
        pass

    # 尝试提取 ```json ... ``` 块
    import re
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()

    # 尝试提取 { ... }
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        return match.group(1).strip()

    raise ValueError("无法从响应中提取 JSON")


def _try_fix_and_parse(response: str) -> Optional[Step3BOutput]:
    """尝试修复 JSON 后解析"""
    import re

    # 移除常见的 markdown 格式
    cleaned = response.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        return _parse_response(cleaned)
    except:
        pass

    # 尝试修复常见的 JSON 问题
    cleaned = response
    # 移除行首的空格
    cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))

    try:
        return _parse_response(cleaned)
    except:
        return None


def _fallback_output() -> Step3BOutput:
    """解析失败时的兜底输出"""
    return Step3BOutput(
        consistency_checks=[
            ConsistencyCheck(
                topic="系统解析",
                claim="Step3B 未能成功解析",
                reality="解析失败",
                gap="请检查 BP 内容或重试",
                judgement="uncertain",
                confidence="low",
            )
        ],
        tensions=[],
        overpackaging_signals=[],
        summary="Step3B 解析失败，请重试",
    )


def run_step3b_simple(
    bp_text: str,
    project_structure: Dict[str, Any],
    investment_modules: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    简单版本：返回字典而不是 Pydantic 模型

    用于 pipeline 集成
    """
    result = run_step3b(bp_text, project_structure, investment_modules=investment_modules)
    return {
        "consistency_checks": [c.model_dump() for c in result.consistency_checks],
        "tensions": [t.model_dump() for t in result.tensions],
        "overpackaging_signals": [p.model_dump() for p in result.overpackaging_signals],
        "summary": result.summary,
    }
