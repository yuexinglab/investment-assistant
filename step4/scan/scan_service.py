"""
Step4 基础扫描服务（v6 新增）
快速扫一遍公司基本面
"""

from __future__ import annotations

import json
import re
from typing import Callable

from step4.scan.scan_prompt import build_scan_prompt


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

    # 最后尝试整个文本
    match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if match:
        return match.group(1)

    raise ValueError("无法从扫描层输出中提取 JSON")


class ScanService:
    """基础扫描服务"""

    def __init__(self, call_llm: Callable[[str, str], str]):
        self.call_llm = call_llm

    def run(self, step1_text: str, bp_text: str) -> dict:
        """生成基础扫描问题

        Args:
            step1_text: Step1 业务理解输出
            bp_text: BP 文本

        Returns:
            扫描问题字典，结构为 {维度: [问题1, 问题2]}
        """
        prompt = build_scan_prompt(step1_text, bp_text)

        raw = self.call_llm(
            system_prompt=(
                "你是资深投资人，擅长尽调提问。"
                "你的任务是快速扫描公司基本面。"
                "只输出 JSON，不要有其他内容。"
            ),
            user_prompt=prompt,
        )

        try:
            raw_json = extract_json_block(raw)
            data = json.loads(raw_json)
            return data
        except Exception as e:
            # Fallback：返回错误信息
            return {
                "error": f"扫描层生成失败: {str(e)}",
                "raw_output": raw[:500] if len(raw) > 500 else raw
            }
