# -*- coding: utf-8 -*-
"""
Step5 Prompt - 决策收敛版本

核心变化：
- 决策型（meet/pass/maybe），不是探索型（hypothesis）
- 必须接入 step3b_json
- must_ask_questions 必须来自 Step4 gaps，不允许重新发明
- reasons_to_meet/pass 必须是影响决策的关键因素，不是优点/缺点罗列
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional


def build_step5_prompt(
    step1_text: str,
    step3_json: Dict[str, Any],
    step3b_json: Dict[str, Any],
    step4_output: Dict[str, Any],
    investment_modules: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    构建 Step5 决策收敛 prompt

    Args:
        step1_text: Step1 业务理解文本
        step3_json: Step3 完整输出（含 project_structure）
        step3b_json: Step3B 完整输出（consistency_checks / tensions / packaging_signals）
        step4_output: Step4 完整输出（包含 internal_json 和 meeting_brief_md）
        investment_modules: 投资思维模块列表（可选）

    Returns:
        完整的 prompt 字符串
    """

    # JSON 序列化
    step3_str = json.dumps(step3_json, ensure_ascii=False, indent=2)
    step3b_str = json.dumps(step3b_json, ensure_ascii=False, indent=2)
    step4_str = json.dumps(step4_output, ensure_ascii=False, indent=2)

    # 安全截断
    max_chars = 80000
    if len(step3_str) > max_chars:
        step3_str = step3_str[:max_chars] + "\n...(已截断)"
    if len(step3b_str) > max_chars:
        step3b_str = step3b_str[:max_chars] + "\n...(已截断)"
    if len(step4_str) > max_chars:
        step4_str = step4_str[:max_chars] + "\n...(已截断)"

    # 格式化投资思维模块（如果有）
    modules_text = ""
    if investment_modules:
        modules_text = """

【投资思维模块库】

以下模块是系统选出的、与本项目最相关的投资判断模块。
你需要使用这些模块辅助形成最终投资判断。

使用规则：
1. core_judgement 必须体现 company_essence 模块。
2. reasons_to_meet / reasons_to_pass 必须围绕模块中的核心判断，而不是泛泛优缺点。
3. key_risks 优先来自模块 red_flags 与 Step3B tensions 的交集。
4. investment_logic 需要结合 Step3 business_model_hypotheses 和模块判断，不要过早武断。
5. 如果某个模块指出"待验证"，不要直接写成事实。

"""
        for i, m in enumerate(investment_modules, 1):
            modules_text += f"""
## 模块{i}: {m['module_name']} ({m['module_id']})
定义: {m['definition']}
Step3B用途: {m['step3b_usage']}
Step5用途: {m['step5_usage']}
核心问题: {', '.join(m['core_questions'])}
"""
        # 特别提示 company_essence
        has_essence_module = any(m['module_id'] == 'company_essence' for m in investment_modules)
        if has_essence_module:
            modules_text += """

【特别注意 - company_essence 模块】
如果项目核心商业本质仍未验证，investment_logic.primary_type 不要强行单选。
应写成："待验证：XX型 vs YY型"
"""

    # 投资逻辑类型提示
    logic_hints = """
【投资逻辑参考】

primary_type 可选值：
- 制造/产品销售型
- 项目制交付型
- 重资产运营型
- 数据/AI模型驱动型
- 混合型（需说明）

如果公司本质不清晰，应写为"待验证：XX型 vs YY型"。
"""

    prompt = f"""你现在不是在分析项目，而是在做投资决策总结。

请基于以下信息：
- Step1：用户的直觉判断
- Step3：公司结构（业务线、商业模式、风险、不确定性）
- Step3B：一致性分析（claim/reality/gap）、关键矛盾（tensions）、包装信号
- Step4：决策缺口（P1/P2/P3 gaps）、deep dive 路径、red flag 问题
- 投资思维模块库（如有）{modules_text}{logic_hints}
完成一个"是否继续推进该项目"的决策输出。

---

【1. 一句话判断（core_judgement）】

必须包含：
- 公司本质（是什么类型公司）
- 当前最大问题（最关键不确定性/矛盾）

要求：
- 不要空话
- 不要重复BP
- 必须体现 Step3 + Step3B 的综合理解

---

【2. 决策（decision）】

给出：
- meet / pass / maybe

标准：
- meet：存在明确值得验证的关键变量
- pass：核心逻辑已经明显不成立或风险不可接受
- maybe：方向可以，但信息不足

---

【3. 决策理由】

生成：
- reasons_to_meet（为什么值得继续看）
- reasons_to_pass（为什么可能不投）

注意：
- 不是优点/缺点罗列
- 必须是"影响投资决策的关键因素"
- 优先使用 Step3B 的矛盾和 Step4 的 gaps

---

【4. 核心风险（key_risks）】

来源优先级：
1）Step3B tensions（优先）
2）Step3B overpackaging_signals
3）Step3 risk_buckets

要求：
- 不要泛化（如"市场竞争激烈"）
- 必须具体到本项目

---

【5. 必问问题（must_ask_questions）】

严格要求：
- 必须来自 Step4 gaps（含 red_flag_question）
- 不允许重新发明问题
- 每个问题必须说明"验证目的"

---

【6. 投资逻辑归因（investment_logic）】

请判断：
- primary_type：公司最核心的投资逻辑（如 制造 / 项目制 / 运营 / AI平台）
- secondary_types：次要逻辑
- risk_type：主要风险类型（如 重资产 / 非标项目 / 政策驱动）

---

【输入】

Step1（直觉判断）:
---
{step1_text}
---

Step3（公司结构）:
---
{step3_str}
---

Step3B（一致性 & 矛盾 & 包装）:
---
{step3b_str}
---

Step4（决策缺口 & 深挖路径）:
---
{step4_str}
---

---

【输出格式】

必须输出合法 JSON，结构如下：

{{
  "core_judgement": {{
    "one_liner": "一句话判断，必须包含公司本质 + 当前最大问题",
    "essence": "公司本质",
    "decision": "meet | pass | maybe",
    "confidence": "high | medium | low",
    "core_reason": "做这个决策的核心原因（一句话）"
  }},

  "reasons_to_meet": [
    {{
      "point": "理由点（要具体）",
      "why_it_matters": "为什么影响决策"
    }}
  ],

  "reasons_to_pass": [
    {{
      "point": "理由点（要具体）",
      "why_it_matters": "为什么影响决策"
    }}
  ],

  "key_risks": [
    {{
      "risk": "风险描述（必须具体到本项目）",
      "severity": "high | medium | low",
      "why_it_matters": "为什么这个风险重要"
    }}
  ],

  "must_ask_questions": [
    {{
      "question": "问题本身（必须来自 Step4 gaps，含 red_flag_question）",
      "purpose": "验证目的"
    }}
  ],

  "investment_logic": {{
    "primary_type": "公司最核心的投资逻辑",
    "secondary_types": ["次要逻辑1", "次要逻辑2"],
    "risk_type": ["主要风险类型1", "主要风险类型2"]
  }}
}}

---

【重要约束】

1. 不要重复分析过程
2. 不要生成泛泛而谈内容
3. 一切围绕"是否继续推进"这个决策
4. 如果信息不足，可以降低 confidence，但不能胡乱补充
5. must_ask_questions 中的 question 字段必须直接来自 Step4 internal gaps 中的 opening / deepen / trap / red_flag_question 之一，不允许凭空发明
6. reasons_to_meet 和 reasons_to_pass 必须和 Step3B 的核心矛盾强相关，不是罗列一般性优缺点
"""

    return prompt
