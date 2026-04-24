# -*- coding: utf-8 -*-
"""
Step5 Service - 决策收敛服务

Step5 的定位：
- 在"开会前"，形成一个可执行的投资判断框架
- 不做分析（那是 Step1/3/4 的事）
- 只做收敛：把信息变成决策

输入：
- step1_text: Step1 业务理解
- step3_json: Step3 风险分桶
- step4_internal: Step4 internal 层输出

输出：
- Step5Output: 结构化的投资决策框架
"""

from __future__ import annotations

import json
import re
from typing import Callable, Dict, Any

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


class Step5Service:
    def __init__(self, call_llm: Callable[[str, str], str], max_retries: int = 2):
        self.call_llm = call_llm
        self.max_retries = max_retries

    def run(
        self,
        *,
        step1_text: str,
        step3_json: Dict[str, Any],
        step4_internal: Dict[str, Any]
    ) -> Step5Output:
        """
        运行 Step5 决策收敛

        Args:
            step1_text: Step1 业务理解的文本
            step3_json: Step3 风险分桶的结果
            step4_internal: Step4 internal 层的输出

        Returns:
            Step5Output: 结构化的投资决策框架
        """
        last_error = None

        for attempt in range(self.max_retries):
            # 构建 prompt
            prompt = build_step5_prompt(
                step1_text=step1_text,
                step3_json=step3_json,
                step4_internal=step4_internal
            )

            # System prompt
            system_prompt = (
                "你是一位顶级投资人，擅长做投资判断和决策收敛。"
                "你的任务是把分析和提问收敛成'可执行的投资判断框架'。"
                "不要总结，要判断。"
                "不要模糊，要明确条件。"
                "输出必须是合法 JSON。"
            )

            if attempt > 0:
                system_prompt += (
                    " 上一次输出有问题（字段不完整或格式错误），"
                    "这次必须严格按照 JSON 格式输出所有字段。"
                )

            # 调用 LLM
            raw = self.call_llm(
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
