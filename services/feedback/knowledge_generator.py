# -*- coding: utf-8 -*-
"""
knowledge_generator.py — 从反馈 case 生成候选知识

不是自动入库，而是生成候选，待人工审核后入库。
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime


KNOWLEDGE_CANDIDATE_PROMPT = """
你是投资判断系统的知识沉淀助手。

你会看到一个 BP 的人工初判、AI 1.0 输出、人机反馈和错误归因。

你的任务不是重新分析项目，而是从这次反馈中提炼可以沉淀的候选知识。
注意：
1. 只能生成候选知识，不能直接认定为永久规则。
2. 候选知识必须来自本次反馈的明确证据。
3. 不要过度泛化，不要写放之四海而皆准的大道理。
4. 如果只是个案，请标记 scope = "case_specific"。
5. 如果可能适用于同类项目，请标记 scope = "reusable_candidate"。

请输出以下几类候选知识：

industry_rules：可能适用于该行业的判断规则
risk_rules：常见风险或包装叙事识别规则
question_templates：以后遇到类似情况时应该问的问题模板
decision_rules：影响是否约第一轮交流的规则
profile_updates：对当前投资人画像的候选更新

输入数据：
{feedback_case}

只输出 JSON，不要有任何额外文字：
{{
  "industry_rules": [
    {{
      "rule": "",
      "scope": "case_specific | reusable_candidate",
      "source_reason": "这条规则来自反馈中的哪句话/哪个判断"
    }}
  ],
  "risk_rules": [
    {{
      "rule": "",
      "scope": "case_specific | reusable_candidate",
      "source_reason": ""
    }}
  ],
  "question_templates": [
    {{
      "template": "",
      "when_to_use": "",
      "scope": "case_specific | reusable_candidate",
      "source_reason": ""
    }}
  ],
  "decision_rules": [
    {{
      "rule": "",
      "scope": "case_specific | reusable_candidate",
      "source_reason": ""
    }}
  ],
  "profile_updates": [
    {{
      "profile_id": "",
      "candidate_update": "",
      "evidence": "",
      "confidence": "high | medium | low"
    }}
  ]
}}
"""


def _safe_json_loads(text: str) -> Dict[str, Any]:
    import re
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
    raise ValueError(f"无法解析 JSON: {text[:200]}")


class KnowledgeCandidateGenerator:
    def __init__(self, call_llm_func):
        self.call_llm = call_llm_func

    def generate(self, feedback_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        从一条 feedback case 生成候选知识。
        """
        prompt = KNOWLEDGE_CANDIDATE_PROMPT.format(feedback_case=json.dumps(feedback_case, ensure_ascii=False, indent=2))
        response = self.call_llm(prompt)
        data = _safe_json_loads(response)

        # 补全默认值
        return {
            "industry_rules": data.get("industry_rules") or [],
            "risk_rules": data.get("risk_rules") or [],
            "question_templates": data.get("question_templates") or [],
            "decision_rules": data.get("decision_rules") or [],
            "profile_updates": data.get("profile_updates") or [],
        }
