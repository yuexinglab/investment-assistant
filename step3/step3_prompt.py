# -*- coding: utf-8 -*-
"""
Step3 Prompt 构建器（v3 增强版）

核心：使用 Step2 的外部约束审查 BP 的叙事
- Step2 中的每个 caution / decision_blocker 都要被检查
- 检查 BP 是否：明确回应 / 弱化 / 跳过 / 把未解决说成已解决
"""

import json
from typing import Any, Dict, List, Optional


def format_step2_for_prompt(step2_json: dict) -> str:
    """
    将 Step2 JSON 格式化为 prompt 片段
    重点：提取 caution 和 decision_blocker
    """
    sections = []

    # ── 1. Step2 外部逻辑（external_investment_logic）────────────────────────
    eil = step2_json.get("external_investment_logic", [])
    if eil:
        sections.append("[Step2 外部投资逻辑 — 必须逐条审查 BP]")

        for i, item in enumerate(eil, 1):
            related = item.get("related_to_step1", "")
            bucket = item.get("bucket_key", "")
            implication = item.get("implication", "")
            logic = item.get("logic_statement", "")
            why = item.get("why_it_matters", "")

            sections.append(f"\n--- 约束 {i} ---")
            sections.append(f"关联 Step1 字段: {related}")
            sections.append(f"约束类型: {bucket} | 判定: {implication}")
            sections.append(f"外部逻辑: {logic}")
            sections.append(f"为何重要: {why}")

    # ── 2. Step2 逐项检查结果（step1_external_check）─────────────────────────
    sec = step2_json.get("step1_external_check", {})
    checks = sec.get("checks", []) if isinstance(sec, dict) else []
    if checks:
        sections.append("\n\n[Step2 逐项验证结果]")

        for i, check in enumerate(checks, 1):
            verdict = check.get("verdict", "")
            field = check.get("step1_field", "")
            claim = check.get("step1_claim", "")
            bucket = check.get("bucket_key", "")
            reasoning = check.get("reasoning", "")

            sections.append(f"\n--- 验证 {i} [{verdict.upper()}] ---")
            sections.append(f"Step1 字段: {field}")
            sections.append(f"BP 说法: {claim}")
            sections.append(f"约束类型: {bucket}")
            sections.append(f"推理: {reasoning}")

    # ── 3. Step2 决策阻碍（decision_blockers）─────────────────────────────────
    ir = step2_json.get("information_resolution", {})
    blockers = ir.get("decision_blockers", []) if isinstance(ir, dict) else []
    if blockers:
        sections.append("\n\n[Step2 决策阻碍 — BP 必须正面回应]")

        for b in blockers:
            if isinstance(b, str):
                sections.append(f"- {b}")
            else:
                sections.append(f"- {b}")

    # ── 4. Step2 张力 ───────────────────────────────────────────────────────
    tensions = step2_json.get("tensions", [])
    if tensions:
        sections.append("\n\n[Step2 张力识别]")
        for t in tensions:
            sections.append(f"- {t}")

    return "\n".join(sections)


def format_project_structure(ps: Dict[str, Any]) -> str:
    """格式化项目结构为可读文本"""
    lines = []

    if ps.get("industry_tags"):
        tags = [f"{x['label']}" for x in ps["industry_tags"]]
        lines.append(f"行业：{', '.join(tags)}")

    if ps.get("business_lines"):
        lines.append("\n业务线：")
        for bl in ps["business_lines"]:
            lines.append(f"  - {bl['name']} ({bl.get('role', '')})")

    if ps.get("business_model_hypotheses"):
        lines.append("\n商业模式假设：")
        for bm in ps["business_model_hypotheses"][:5]:
            lines.append(f"  - {bm['bucket_name']} ({bm.get('role', '')})")

    if ps.get("risk_buckets"):
        lines.append("\n风险点：")
        for r in ps["risk_buckets"][:5]:
            lines.append(f"  - {r['bucket_name']}")

    if ps.get("key_uncertainties"):
        lines.append("\n关键不确定性：")
        for u in ps["key_uncertainties"][:3]:
            lines.append(f"  - {u['uncertainty']}")

    return "\n".join(lines) if lines else "无"


def build_step3_prompt(
    bp_text: str,
    project_structure: Dict[str, Any],
    step2_json: Optional[Dict[str, Any]] = None,
    user_input: Optional[Dict[str, Any]] = None,
    investment_modules: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    构建 Step3 v3 prompt

    核心变化：使用 Step2 外部约束审查 BP 叙事

    Args:
        bp_text: BP原文
        project_structure: Step3 项目结构识别结果
        step2_json: Step2 外部约束检查结果（新增必填）
        user_input: Step1 用户输入（可选）
        investment_modules: 投资思维模块列表（可选）
    """

    # ── Step2 格式化 ───────────────────────────────────────────────────────
    step2_text = ""
    if step2_json:
        step2_text = format_step2_for_prompt(step2_json)
    else:
        step2_text = "[警告：Step2 未提供，Step3 将仅基于 BP 内部一致性分析，无法引用外部约束]"

    # ── 项目结构 ───────────────────────────────────────────────────────────
    structure_text = format_project_structure(project_structure)

    # ── 用户输入 ───────────────────────────────────────────────────────────
    user_input_text = ""
    if user_input:
        user_input_text = f"""
【Step1 用户初步判断】
{user_input.get('initial_judgment', '无')}
{user_input.get('first_impression', '无')}
"""

    # ── 投资思维模块 ───────────────────────────────────────────────────────
    modules_text = ""
    if investment_modules:
        modules_text = """

【投资思维模块库】

以下模块是历史项目和投资人经验沉淀出来的判断框架。
你必须参考这些模块来识别：
- BP包装
- 结构矛盾
- 关键红旗
- 需要验证的核心问题

使用规则：
1. 模块不是结论，只是判断工具。不要机械套用所有模块。
2. 只使用和本项目相关的模块。
3. 如果模块中的 red_flags 与 BP 内容匹配，请体现在 consistency_checks / tensions / overpackaging_signals 中。
4. 如果模块中的 good_signals 已经被 BP 证明，也可以写为 support。
5. 不要让模块取代项目事实，必须结合 BP 和 project_structure。

"""
        for i, m in enumerate(investment_modules, 1):
            modules_text += f"""
## 模块{i}: {m['module_name']} ({m['module_id']})
定义: {m['definition']}
适用场景: {', '.join(m['applicable_when'])}
核心问题: {', '.join(m['core_questions'])}
红旗信号: {', '.join(m['red_flags'])}
正面信号: {', '.join(m['good_signals'])}
"""

    prompt = f"""你现在的任务不是总结BP，而是从"投资人质疑"的角度，用外部约束审查 BP 叙事。

【你的核心武器 = Step2 的外部约束】
Step2 已经用行业常识/投资逻辑/技术商业化规律，对 BP 做了外部验证。
你的任务是：对照 Step2，找 BP 的叙事漏洞。

========================================
任务：对 Step2 中的每个关键约束，检查 BP 是否：
1. 明确回应了这个约束（BP 提供了证据）
2. 弱化了这个约束（BP 轻描淡写）
3. 完全跳过了这个约束（BP 没提）
4. 把"未解决问题"说成"已解决能力"（叙事包装）
========================================

请基于以下信息：
1）BP内容
2）系统识别出的项目结构
3）Step2 外部约束（这是你的武器）
{user_input_text}{modules_text}

--------------------------------

【1. 一致性检查（consistency_checks）】

针对 Step2 的每个 caution/contradict 约束：
- BP 怎么说的？
- BP 的说法 vs 外部约束
- judgement: support / contradict / uncertain

⚠️ 必须引用 Step2 约束，不能只做语言判断

请输出 2-4 个最重要的一致性检查项。

【每条新增字段说明】
- related_step2_check: 引用哪条 Step2 验证（如 step1_field）
- external_constraint: 外部约束是什么（来自 Step2）
- bp_claim_checked: BP 中哪段话对应这个说法
- judgement: BP 的说法 vs 外部约束 → support / contradict / uncertain

--------------------------------

【2. 关键矛盾（tensions）】

请识别"结构性矛盾"，重点：
- BP 叙事 vs 外部约束
- Step1 判断 vs BP 说法

格式：A vs B
要求：必须是"两个方向的冲突"，不能是单点风险

【每条新增字段】
- related_step2_logic: 引用哪条 Step2 外部逻辑
- conflict_type: external_vs_bp / step1_vs_bp

请输出 1-3 个最关键的矛盾。

--------------------------------

【3. 包装/叙事信号（overpackaging_signals）】

重点识别以下包装类型：
- future_as_present：把未来计划说成现在能力
- cooperation_as_revenue：把合作意向说成收入
- tech_as_capability：把技术说成壁垒
- platform_narrative：平台化叙事
- tech_overstatement：技术被过度强调
- expansion_story：扩张故事大于当前业务
- team_overuse：团队/背书被过度使用
- vague_terms：使用模糊词

【每条新增字段】
- related_step2_constraint: 关联哪条 Step2 约束（如果有）
- packaging_type: 细分类型（见上方列表）

请输出 1-3 个最明显的信号。

--------------------------------

【4. summary】

用一句话总结：
- 这个项目最大的"认知问题"是什么？

⚠️ 重要限制：
- summary 不要写成新的公司本质定义（如"本质是XX"）
- 如果需要表达判断，请写成："从 Step1/Step2 判断看，该项目更应按X审查，而不是按Y叙事理解"
- 直接指出 BP 叙事与外部约束的错位，不要发明新定义

========================================

【BP内容】
{bp_text[:8000]}

【系统识别出的项目结构】
{structure_text}

========================================
【Step2 外部约束 — 这是你的武器，必须逐条对照 BP】
========================================
{step2_text}

========================================

请输出结构化JSON，格式如下：
{{
  "consistency_checks": [
    {{
      "topic": "维度名称",
      "claim": "BP的说法",
      "reality": "现实情况",
      "gap": "缺失或问题",
      "judgement": "support/contradict/uncertain",
      "confidence": "high/medium/low",
      "related_step2_check": "关联的Step1字段（如 company_essence）",
      "external_constraint": "外部约束是什么（来自Step2）",
      "bp_claim_checked": "BP中哪段话"
    }}
  ],
  "tensions": [
    {{
      "tension": "A vs B",
      "why_it_matters": "为什么重要",
      "severity": "high/medium/low",
      "related_step2_logic": "关联的Step2外部逻辑",
      "conflict_type": "external_vs_bp / step1_vs_bp"
    }}
  ],
  "overpackaging_signals": [
    {{
      "signal": "具体信号",
      "type": "tech_overstatement/expansion_story/team_overuse/vague_terms/future_as_present/cooperation_as_revenue/tech_as_capability/platform_narrative",
      "severity": "high/medium/low",
      "related_step2_constraint": "关联的Step2约束（如果有）",
      "packaging_type": "细分类型（如 future_as_present）"
    }}
  ],
  "summary": "一句话总结最大认知问题"
}}

请只输出JSON，不要输出多余解释。
"""

    return prompt
