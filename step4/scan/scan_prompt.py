"""
Step4 v6.1 - Scan Prompt
基础扫描层：会话式问题生成

每个维度生成：
- opening: 暖场/开口问题
- follow_up: 顺着追问
- best_question: 最值钱的一句（最尖锐/最有信息量）
"""

import json
import os
import yaml
from typing import Dict, List, Any


def load_scan_templates() -> Dict[str, List[Dict[str, Any]]]:
    """加载扫描模板库"""
    _dir = os.path.dirname(os.path.abspath(__file__))
    _path = os.path.join(_dir, "scan_templates.yaml")
    with open(_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


PROMPT_TEMPLATE = """你是一位资深投资人，现在要做「基础尽调扫描」。

目标：快速扫一遍公司基本面，覆盖关键维度。

【核心原则】

1. **必须像真实会议中的会话**：不是填表，是聊天中的自然追问
2. **必须有上下文**：引用具体数字、客户名、产品名来开口
3. **opening 要暖场**：给对方一个舒服的回答入口
4. **follow_up 要跟进**：顺着上一个回答继续追问
5. **best_question 要值钱**：这是整个维度最值得问的一句，最尖锐或信息量最大

【严禁】

- 泛泛而问（如"收入结构如何"、"行业情况如何"）
- 像 checklist 一样生硬
- 没有具体信息的空问法
- 问题之间没有逻辑关联

【上下文】

Step1 业务理解摘要：
{step1}

BP 核心信息：
{bp}

【模板库（参考方法论，不是复制原文）】

{templates}

【输出格式】

必须输出合法 JSON，每个维度包含 opening / follow_up / best_question：

{{
  "revenue": {{
    "opening": "开场问题，要暖场",
    "follow_up": "顺着追问",
    "best_question": "最值钱的一句"
  }},
  "customer": {{...}},
  "industry": {{...}},
  "production": {{...}},
  "tech": {{...}},
  "business_model": {{...}},
  "new_business": {{...}}
}}

【重要】

- 只需要生成这 7 个维度
- 每个维度 3 个字段都必须有
- best_question 是整个维度的核心问题，要尖锐、有信息量
- 不要解释，不要加引号，直接输出问题
"""


def build_scan_prompt(step1_text: str, bp_text: str) -> str:
    """
    构建 scan prompt

    Args:
        step1_text: Step1 业务理解的文本
        bp_text: BP 文本

    Returns:
        填充好的 prompt
    """
    templates = load_scan_templates()

    # 截取上下文（防止 token 过多）
    step1_truncated = step1_text[:2000] if step1_text else ""
    bp_truncated = bp_text[:3000] if bp_text else ""

    # 转换模板为可读格式
    templates_text = _format_templates_for_prompt(templates)

    return PROMPT_TEMPLATE.format(
        step1=step1_truncated,
        bp=bp_truncated,
        templates=templates_text
    )


def _format_templates_for_prompt(templates: Dict) -> str:
    """将模板库格式化为 prompt 中可读的格式"""
    lines = []
    for dimension, items in templates.items():
        lines.append(f"\n## {dimension}")
        for item in items:
            lines.append(f"\n- 意图: {item['intent']}")
            lines.append(f"  opening: {item['opening_pattern']}")
            lines.append(f"  follow_up: {item['follow_up_pattern']}")
            lines.append(f"  best_question: {item['best_question_pattern']}")
    return "\n".join(lines)
