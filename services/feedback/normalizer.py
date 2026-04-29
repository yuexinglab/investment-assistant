# -*- coding: utf-8 -*-
"""
normalizer.py — 自由输入自动整理器

将用户口语化、混乱的初判文字，AI整理成结构化字段。
"""

import json
import re
from typing import Dict, Any, List


HUMAN_NOTE_NORMALIZER_PROMPT = """
你是一个投资项目标注助手。

用户会输入一段非常自由、口语化、可能混乱的 BP 初步判断。
你的任务是把它整理成结构化字段。

注意：
1. 不要新增用户没有表达过的实质判断。
2. 如果用户没说清楚，字段可以写"不确定"。
3. 不要替用户做投资判断，只整理用户已经表达的意思。
4. 输出必须是严格 JSON，不要有任何额外文字。

字段说明：

one_liner：一句话描述这家公司是干什么的。不要照抄 BP，用朴素的话。
current_business：当前真正已经在做、已经能产生收入或接近收入的业务。只写当前，不写远期故事。
future_story：BP 里讲的未来故事、包装叙事或你觉得需要谨慎的部分。
real_customer：谁可能真的付钱，为什么付钱。如果没说，写"不确定"。
market_view：对市场空间、行业价值、政策价值、产业价值的粗略判断。可以很主观。
decision：用户是否建议约第一轮交流。只能是 meet / maybe_meet / request_materials / pass 四选一。
  - meet：明确建议约
  - maybe_meet：犹豫但愿意了解
  - request_materials：先要补充材料，暂不约
  - pass：明确不看
priority：high / medium / low，约的优先级。
confidence：high / medium / low，判断的信心程度。
reasons_to_meet：支持约交流的理由列表，字符串数组。
reasons_to_pass：不支持约交流的理由列表，字符串数组。
key_unknowns：BP 里没写清楚、会影响判断的关键信息，字符串数组。
must_ask_questions：如果约第一轮交流想问的问题列表，每项包含 question 和 why_important。

用户原始输入：
{raw_note}

请只输出 JSON：
{{
  "one_liner": "",
  "current_business": "",
  "future_story": "",
  "real_customer": "",
  "market_view": "",
  "decision": "",
  "priority": "",
  "confidence": "",
  "reasons_to_meet": [],
  "reasons_to_pass": [],
  "key_unknowns": [],
  "must_ask_questions": [
    {{"question": "", "why_important": ""}}
  ]
}}
"""


def _safe_json_loads(text: str) -> Dict[str, Any]:
    """从 LLM 输出中安全提取 JSON"""
    text = text.strip()

    # 去除 markdown 代码块
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text.strip())

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试找到 JSON 块
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法解析 JSON: {text[:200]}")


class HumanNoteNormalizer:
    def __init__(self, call_llm_func):
        """
        Args:
            call_llm_func: 接受一个 prompt str，返回 LLM 响应 str
                          示例：call_deepseek
        """
        self.call_llm = call_llm_func

    def normalize(self, raw_note: str) -> Dict[str, Any]:
        """
        将自由输入整理为结构化字段。
        """
        prompt = HUMAN_NOTE_NORMALIZER_PROMPT.format(raw_note=raw_note)
        response = self.call_llm(prompt)
        data = _safe_json_loads(response)

        # 字段名映射（规范化）
        return {
            "one_liner": data.get("one_liner", "不确定"),
            "current_business": data.get("current_business", "不确定"),
            "future_story": data.get("future_story", ""),
            "real_customer": data.get("real_customer", "不确定"),
            "market_view": data.get("market_view", ""),
            "decision": data.get("decision", "maybe_meet"),
            "priority": data.get("priority", "medium"),
            "confidence": data.get("confidence", "medium"),
            "reasons_to_meet": data.get("reasons_to_meet") or [],
            "reasons_to_pass": data.get("reasons_to_pass") or [],
            "key_unknowns": data.get("key_unknowns") or [],
            "must_ask_questions": data.get("must_ask_questions") or [],
        }
