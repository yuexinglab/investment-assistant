# -*- coding: utf-8 -*-
"""
Step5 Prompt - 探索型投资人版本 (v2)

核心变化：
- 从"下结论" → "提出假设 + 设计验证"
- 所有判断保留不确定性（可被推翻）
- 强调"会前验证逻辑"而非"最终结论"

参考 Step4 的深挖逻辑，生成可执行的会前验证框架。
"""

from __future__ import annotations

import json
from typing import Dict, Any


def build_step5_prompt(
    step1_text: str,
    step3_json: Dict[str, Any],
    step4_internal: Dict[str, Any]
) -> str:
    """
    构建 Step5 探索型 prompt

    Args:
        step1_text: Step1 业务理解文本
        step3_json: Step3 风险分桶结果
        step4_internal: Step4 internal 层输出（深挖逻辑）

    Returns:
        完整的 prompt 字符串
    """

    # JSON 序列化
    step3_str = json.dumps(step3_json, ensure_ascii=False, indent=2)
    step4_str = json.dumps(step4_internal, ensure_ascii=False, indent=2)

    # 计算截断点（如果需要）
    # DeepSeek 最大输入约 128k tokens，我们保留足够空间
    max_chars = 500000  # 安全上限

    if len(step3_str) > max_chars:
        step3_str = step3_str[:max_chars] + "\n...(内容已截断)"
    if len(step4_str) > max_chars:
        step4_str = step4_str[:max_chars] + "\n...(内容已截断)"

    prompt = f"""你是一位资深投资人，现在处于"会前第一轮判断阶段（1.0）"。

⚠️ 当前阶段定义（非常重要）：
这不是 IC 决策，而是"初步接触后的假设形成阶段"。
你的目标不是下结论，而是形成"可被验证的判断框架"。

---

【你的核心任务】

基于已有信息，输出一个"探索型判断框架"：

不是结论，而是：
- 当前假设是什么
- 可能错在哪里（防止自信过度）
- 需要验证的关键点是什么
- 会前行动策略

---

【重要原则】

❗ 不要下最终结论（如"建议投资/不投资"）
❗ 所有判断必须保留不确定性（用"可能/当前判断/需验证"等表达）
❗ 必须明确说明：哪些地方你可能是错的
❗ 输出必须能指导"下一步会议如何验证"
❗ 要像真实的谨慎投资人，而不是自信的分析师

---

【输入】

Step1（初始判断 - 团队是怎么看这个项目的）:
---
{step1_text}
---

Step3（背景信息 - 风险和业务细节）:
---
{step3_str}
---

Step4（深挖逻辑 - 关键缺口和验证路径，来自 Step4 internal）:
---
{step4_str}
---

---

【输出结构】

请严格按以下JSON格式输出（不要输出JSON以外的内容）：

{{
  "current_hypothesis": "当前假设（不是结论，是初步判断）。必须用'可能/当前判断/需验证'等表达，不能过于确定。例如：'当前假设公司更接近XX，但需要验证YY'",

  "why_this_might_be_wrong": [
    "列出2-4个'你可能是错的地方'，这是防止AI自信过度的关键模块",
    "例如：'AI可能比描述的更核心，只是BP没有充分体现'",
    "例如：'核心客户可能已经形成技术依赖，只是没有明说'"
  ],

  "investment_logic": {{
    "bull_case": [
      "如果XX成立，则支持投资的理由",
      "至少2条，要具体"
    ],
    "bear_case": [
      "如果XX成立，则不支持投资的理由",
      "至少2条，要具体"
    ]
  }},

  "key_validation_points": [
    {{
      "point": "验证点描述（要具体，来自Step4的核心问题）",
      "why_it_matters": "为什么这个点重要",
      "what_to_look_for": "会议上要观察/询问什么"
    }},
    {{
      "point": "...",
      "why_it_matters": "...",
      "what_to_look_for": "..."
    }}
  ],

  "deal_breaker_signals": [
    {{
      "signal": "一旦出现就放弃的信号（要具体、可观察）",
      "implication": "出现后的含义"
    }},
    {{
      "signal": "...",
      "implication": "..."
    }}
  ],

  "meeting_objective": "本次会议的核心目标（不是判断是否投资，而是验证假设）。应该明确说明要验证哪几个核心问题。",

  "next_step_strategy": {{
    "if_validated": "如果核心假设得到验证，下一步建议",
    "if_not_validated": "如果核心假设被证伪，下一步建议",
    "current_action": "当前阶段的行动建议（继续推进/暂停/带问题再看等）"
  }}
}}

---

【风格要求】

- 像一个谨慎但有经验的投资人
- 有判断，但不自信过度
- 重点在"验证逻辑"，而不是"表达观点"
- 要体现出"我现在是这么看的，但不一定对"

【数量要求】

- why_this_might_be_wrong: 至少2条，最多4条
- key_validation_points: 至少2条，最多4条
- deal_breaker_signals: 至少1条，最多3条
"""

    return prompt
