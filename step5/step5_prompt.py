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
    profile: Optional[Dict[str, Any]] = None,
) -> str:
    """
    构建 Step5 决策收敛 prompt

    Args:
        step1_text: Step1 业务理解文本
        step3_json: Step3 完整输出（含 project_structure）
        step3b_json: Step3B 完整输出（consistency_checks / tensions / packaging_signals）
        step4_output: Step4 完整输出（包含 internal_json 和 meeting_brief_md）
        investment_modules: 投资思维模块列表（可选）
        profile: 用户画像（可选，已注入 prompt 作为决策参考）

    Returns:
        完整的 prompt 字符串
    """
    # [DEBUG] Step5 阶段1B：验证 profile 已传到 prompt 层
    profile_id = profile.get('profile_id') if profile else None
    print(f"[DEBUG] Step5 prompt received profile: {profile_id}")

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

    # 格式化基金画像
    if profile:
        profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
        if len(profile_text) > 20000:
            profile_text = profile_text[:20000] + "\n...(已截断)"
    else:
        profile_text = "当前未提供特定基金画像，请按中性投资人视角判断。"

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

【基金画像使用规则】

如果提供了 Step0 / 基金画像，你必须把它作为"判断这个项目是否适合继续沟通"的重要视角。

但注意：
- profile 只能影响"是否适合该基金/投资人继续看"
- profile 不能改变项目事实
- 不要为了匹配 profile 而美化项目
- 如果 profile_id 是 neutral_investor，则按通用项目质量判断，不强行写基金匹配
- 如果 profile 中有 hard_constraints、preferences、avoid、fit_questions，需要明确判断本项目是否触碰这些条件

---

【1. 一句话判断（core_judgement）】

必须包含：
- 公司本质（是什么类型公司）
- 当前最大问题（最关键不确定性/矛盾）

要求：
- 不要空话
- 不要重复BP
- 必须体现 Step3 + Step3B 的综合理解

core_reason 必须同时回答：
1. 从项目本身看，为什么是 meet/pass/maybe
2. 从当前 profile 看，为什么这个决策成立

例如：
- "项目技术方向值得验证，但对政府基金而言，本地落地、真实客户和产线规划尚未验证，因此当前只能 maybe。"
- "项目本身有增长潜力，但对政府产业基金缺乏本地落地和反投可能，当前不适合推进。"

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

reasons_to_meet：
- 至少 1 条必须说明该项目对当前 profile 的潜在匹配点
- 如果没有明显匹配点，要明确写"当前尚未看到明显 profile 匹配点"，不要硬凑

reasons_to_pass：
- 至少 1 条必须说明该项目对当前 profile 的不匹配点或待验证点
- 对政府基金类 profile，重点检查：本地落地、反投、真实客户、产线/产能、就业/地方贡献
- 对 VC 类 profile，重点检查：市场天花板、可规模化、增长速度、资本效率、退出路径
- 对产业资本类 profile，重点检查：产业链协同、能力补充、客户/渠道/技术协同

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

如果 profile 中存在 fit_questions，must_ask_questions 必须优先覆盖其中最关键的 1-2 个问题：
- 如果 Step4 gaps 已经包含类似问题，则合并，不重复
- 如果 Step4 gaps 没有覆盖 profile 的硬约束问题，也允许从 profile.fit_questions 中补入
- 每个问题的 purpose 要说明它验证的是"项目逻辑"还是"profile 匹配度"
- 特别注意：这里允许 profile.fit_questions 补入 must_ask_questions，但不要生成泛泛问题

---

【6. 投资逻辑归因（investment_logic）】

请判断：
- primary_type：公司最核心的投资逻辑（如 制造 / 项目制 / 运营 / AI平台）
- secondary_types：次要逻辑
- risk_type：主要风险类型（如 重资产 / 非标项目 / 政策驱动）

---

【输入】

【Step0 / 基金画像】
---
{profile_text}
---

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
    "core_reason": "做这个决策的核心原因（一句话）。如果 profile_id 不是 neutral_investor，必须同时说明：项目本身为什么是这个决策 + 对当前基金/投资人为什么是这个决策。"
  }},

  "reasons_to_meet": [
    {{
      "point": "理由点（要具体）",
      "why_it_matters": "为什么影响决策。至少一条必须写明该项目对当前 profile 的潜在匹配点；如果没有匹配点，必须写：当前尚未看到明显匹配点。"
    }}
  ],

  "reasons_to_pass": [
    {{
      "point": "理由点（要具体）",
      "why_it_matters": "为什么影响决策。至少一条必须写明该项目对当前 profile 的不匹配点或未验证点。政府基金重点看：本地落地、反投、真实客户、产线/产能、地方贡献。"
    }}
  ],

  "key_risks": [
    {{
      "risk": "风险描述（必须具体到本项目）",
      "severity": "high | medium | low",
      "why_it_matters": "为什么这个风险重要"
    }}
  ],

  "fund_fit": {{
    "fit_summary": "一句话说明该项目与当前基金/Profile的匹配度",
    "matched_points": ["匹配点1", "匹配点2"],
    "mismatch_or_uncertain_points": ["不匹配或未验证点1", "不匹配或未验证点2"],
    "required_verifications": ["下一轮必须验证的基金匹配问题1", "下一轮必须验证的基金匹配问题2"]
  }},

  "must_ask_questions": [
    {{
      "question": "问题本身（必须来自 Step4 gaps，含 red_flag_question）",
      "purpose": "验证目的。如果 profile_id 不是 neutral_investor，至少一个问题必须验证 profile 匹配度。政府基金优先问：是否愿意本地落地、是否接受反投、是否有真实客户和产线规划。"
    }}
  ],

  "investment_logic": {{
    "primary_type": "公司最核心的投资逻辑",
    "secondary_types": ["次要逻辑1", "次要逻辑2"],
    "risk_type": ["主要风险类型1", "主要风险类型2"]
  }}
}}

---

【7. 基金/Profile匹配度（fund_fit）】

必须基于 Step0 / 基金画像判断该项目是否适合当前基金/Profile继续看。

要求：
- 如果 profile_id 是 neutral_investor：
  fit_summary 写"当前为中性投资人视角，不做特定基金匹配判断"
- 如果 profile_id 不是 neutral_investor：
  必须明确引用该 profile 的 hard_constraints / preferences / avoid / fit_questions
- matched_points 写已经看到的匹配点
- mismatch_or_uncertain_points 写不匹配或尚未验证的点
- required_verifications 写下一轮必须验证的 profile 匹配问题
- 不允许只写"匹配度较高/较低"这种空话

对政府基金类 profile，必须检查：
- 是否愿意本地落地
- 是否接受反投或地方经济贡献
- 是否有真实付费客户
- 是否有产线/产能建设可能
- 是否能带动地方产业或就业

---

【重要约束】:

1. 不要重复分析过程
2. 不要生成泛泛而谈内容
3. 一切围绕"是否继续推进"这个决策
4. 如果信息不足，可以降低 confidence，但不能胡乱补充
5. must_ask_questions 中的 question 字段必须直接来自 Step4 internal gaps 中的 opening / deepen / trap / red_flag_question 之一，不允许凭空发明
6. reasons_to_meet 和 reasons_to_pass 必须和 Step3B 的核心矛盾强相关，不是罗列一般性优缺点
7. 如果提供了非 neutral_investor 的 profile，输出必须能看出当前基金/投资人视角；不能只做通用项目判断。
如果输出中完全没有体现 profile 的 hard_constraints / preferences / avoid / fit_questions，视为不合格输出。
8. profile 相关内容必须落在现有字段中，其中基金匹配度必须写入 fund_fit 字段。
9. 如果 profile 的关键约束没有在 BP/Step4 中被验证，应在 fund_fit.mismatch_or_uncertain_points 或 must_ask_questions 中体现。
"""

    return prompt
