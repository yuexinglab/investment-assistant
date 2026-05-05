# -*- coding: utf-8 -*-
"""
Step5 Service - 决策收敛服务

Step5 的定位：
- 不是分析层（那是 Step1/3/3B/4 的事）
- 而是"决策收敛层"：把看懂 + 拆穿 + 提问，收敛成"投不投"

输入：
- step1_text: Step1 业务理解
- step3_json: Step3 完整输出（含 project_structure）
- step3b_json: Step3B 完整输出
- step4_output: Step4 完整输出（包含 internal_json）

输出：
- Step5Output: 结构化的投资决策框架（meet/pass/maybe）
"""

from __future__ import annotations

import json
import re
from typing import Callable, Dict, Any, List, Optional

from step5.step5_prompt import build_step5_prompt
from step5.step5_schema import Step5Output


def extract_json_block(text: str) -> str:
    """从模型输出中提取 JSON"""
    text = text.strip()

    # 直接是 JSON
    if text.startswith("{") and text.endswith("}"):
        return text

    # 尝试从 markdown 代码块中提取
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match:
        return match.group(1)

    # 尝试直接找 JSON
    match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if match:
        return match.group(1)

    raise ValueError("无法从 Step5 模型输出中提取 JSON")


def parse_step5_output(raw_text: str) -> Step5Output:
    """解析 Step5 输出"""
    raw_json = extract_json_block(raw_text)
    data = json.loads(raw_json)
    return Step5Output.model_validate(data)


def run_step5(
    *,
    step1_text: str,
    step3_json: Dict[str, Any],
    step3b_json: Dict[str, Any],
    step4_output: Dict[str, Any],
    call_llm: Callable[[str, str], str],
    investment_modules: Optional[List[Dict[str, Any]]] = None,
    max_retries: int = 2,
) -> Step5Output:
    """
    运行 Step5 决策收敛

    Args:
        step1_text: Step1 业务理解文本
        step3_json: Step3 完整输出
        step3b_json: Step3B 完整输出（consistency_checks / tensions / packaging_signals）
        step4_output: Step4 完整输出（含 internal_json）
        call_llm: LLM 调用函数
        investment_modules: 投资思维模块列表（可选）
        max_retries: 最大重试次数

    Returns:
        Step5Output: 结构化的投资决策框架
    """
    last_error = None

    for attempt in range(max_retries):
        # 构建 prompt
        prompt = build_step5_prompt(
            step1_text=step1_text,
            step3_json=step3_json,
            step3b_json=step3b_json,
            step4_output=step4_output,
            investment_modules=investment_modules,
        )

        # System prompt
        system_prompt = (
            "你是一位顶级投资人，擅长做投资判断和决策收敛。"
            "你的任务是把分析和提问收敛成'可执行的投资判断框架'。"
            "不要总结，要判断。不要模糊，要明确条件。"
            "输出必须是合法 JSON。"
        )

        if attempt > 0:
            system_prompt += (
                " 上一次输出有问题（字段不完整或格式错误），"
                "这次必须严格按照 JSON 格式输出所有字段。"
            )

        # 调用 LLM
        raw = call_llm(
            system_prompt=system_prompt,
            user_prompt=prompt
        )

        try:
            obj = parse_step5_output(raw)
            return obj
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Step5 生成失败: {last_error}")


# ── 兼容旧接口 ──────────────────────────────────────────────────────────────

class Step5Service:
    """兼容旧调用方式的包装"""

    def __init__(self, call_llm: Callable[[str, str], str], max_retries: int = 2):
        self.call_llm = call_llm
        self.max_retries = max_retries

    def run(
        self,
        *,
        step1_text: str,
        step3_json: Dict[str, Any],
        step4_internal: Dict[str, Any],
        step3b_json: Dict[str, Any] = None,
    ) -> Step5Output:
        """
        兼容旧接口（step4_internal），内部会包装成 step4_output
        """
        step4_output = step4_internal  # 旧接口直接传 internal
        if step3b_json is None:
            step3b_json = {}

        return run_step5(
            step1_text=step1_text,
            step3_json=step3_json,
            step3b_json=step3b_json,
            step4_output={"internal_json": step4_output},
            call_llm=self.call_llm,
            max_retries=self.max_retries,
        )
