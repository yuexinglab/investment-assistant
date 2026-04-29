# -*- coding: utf-8 -*-
"""
Step3B Prompt 构建器
"""

import json
from typing import Any, Dict, List, Optional


PROMPT_TEMPLATE = """你现在的任务不是总结BP，而是从"投资人质疑"的角度分析该项目。

请基于以下信息：
1）BP内容
2）系统识别出的项目结构（业务线、商业模式、风险、不确定性）

完成以下三件事：

--------------------------------

【1. 一致性检查（consistency_checks）】

请针对关键维度（如商业模式、收入来源、技术壁垒、客户需求等）：

- 找出 BP 中的"说法（claim）"
- 判断现实是否支撑（reality）
- 指出缺失或问题（gap）
- 给出判断：
  - support：有证据支持
  - contradict：存在明显矛盾
  - uncertain：信息不足

重点不要复述BP内容，而是"拆解说法"并指出问题。

请输出 2-4 个最重要的一致性检查项。

--------------------------------

【2. 关键矛盾（tensions）】

请识别项目中的"结构性矛盾"，格式如下：

A vs B（例如：当前收入 vs 未来故事）

要求：
- 必须是"两个方向的冲突"，而不是单点风险
- 必须解释为什么这个矛盾重要（影响投资判断）

请输出 1-3 个最关键的矛盾。

--------------------------------

【3. 包装/叙事信号（overpackaging_signals）】

请识别是否存在以下情况：

- tech_overstatement：技术被过度强调（AI/全栈/平台）
- expansion_story：扩张故事大于当前业务
- team_overuse：团队/背书被过度使用
- vague_terms：使用模糊词（生态、平台、赋能）

请输出 1-3 个最明显的信号。

--------------------------------

【4. summary】

用一句话总结：
- 这个项目最大的"认知问题"是什么？

--------------------------------

请输出结构化JSON，格式如下：
{{
  "consistency_checks": [
    {{
      "topic": "维度名称",
      "claim": "BP的说法",
      "reality": "现实情况",
      "gap": "缺失或问题",
      "judgement": "support/contradict/uncertain",
      "confidence": "high/medium/low"
    }}
  ],
  "tensions": [
    {{
      "tension": "A vs B",
      "why_it_matters": "为什么重要",
      "severity": "high/medium/low"
    }}
  ],
  "overpackaging_signals": [
    {{
      "signal": "具体信号",
      "type": "tech_overstatement/expansion_story/team_overuse/vague_terms",
      "severity": "high/medium/low"
    }}
  ],
  "summary": "一句话总结最大认知问题"
}}

请只输出JSON，不要输出多余解释。
"""


def build_step3b_prompt(
    bp_text: str,
    project_structure: Dict[str, Any],
    user_input: Optional[Dict[str, Any]] = None,
    investment_modules: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    构建 Step3B prompt

    Args:
        bp_text: BP原文
        project_structure: Step3 项目结构识别结果
        user_input: Step1 用户输入（可选）
        investment_modules: 投资思维模块列表（可选）
    """

    # 格式化项目结构
    structure_text = _format_project_structure(project_structure)

    # 格式化用户输入（如果有）
    user_input_text = ""
    if user_input:
        user_input_text = f"""

【Step1 用户初步判断】
{user_input.get('initial_judgment', '无')}
{user_input.get('first_impression', '无')}
"""

    # 格式化投资思维模块（如果有）
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

    prompt = f"""你现在的任务不是总结BP，而是从"投资人质疑"的角度分析该项目。

请基于以下信息：
1）BP内容
2）系统识别出的项目结构（业务线、商业模式、风险、不确定性）
3）投资思维模块库（如有）
{user_input_text}{modules_text}
完成以下三件事：

--------------------------------

【1. 一致性检查（consistency_checks）】

请针对关键维度（如商业模式、收入来源、技术壁垒、客户需求等）：

- 找出 BP 中的"说法（claim）"
- 判断现实是否支撑（reality）
- 指出缺失或问题（gap）
- 给出判断：
  - support：有证据支持
  - contradict：存在明显矛盾
  - uncertain：信息不足

重点不要复述BP内容，而是"拆解说法"并指出问题。

请输出 2-4 个最重要的一致性检查项。

--------------------------------

【2. 关键矛盾（tensions）】

请识别项目中的"结构性矛盾"，格式如下：

A vs B（例如：当前收入 vs 未来故事）

要求：
- 必须是"两个方向的冲突"，而不是单点风险
- 必须解释为什么这个矛盾重要（影响投资判断）

请输出 1-3 个最关键的矛盾。

--------------------------------

【3. 包装/叙事信号（overpackaging_signals）】

请识别是否存在以下情况：

- tech_overstatement：技术被过度强调（AI/全栈/平台）
- expansion_story：扩张故事大于当前业务
- team_overuse：团队/背书被过度使用
- vague_terms：使用模糊词（生态、平台、赋能）

请输出 1-3 个最明显的信号。

--------------------------------

【4. summary】

用一句话总结：
- 这个项目最大的"认知问题"是什么？

--------------------------------

【BP内容】
{bp_text[:8000]}

【系统识别出的项目结构】
{structure_text}

--------------------------------

请输出结构化JSON，格式如下：
{{
  "consistency_checks": [
    {{
      "topic": "维度名称",
      "claim": "BP的说法",
      "reality": "现实情况",
      "gap": "缺失或问题",
      "judgement": "support/contradict/uncertain",
      "confidence": "high/medium/low"
    }}
  ],
  "tensions": [
    {{
      "tension": "A vs B",
      "why_it_matters": "为什么重要",
      "severity": "high/medium/low"
    }}
  ],
  "overpackaging_signals": [
    {{
      "signal": "具体信号",
      "type": "tech_overstatement/expansion_story/team_overuse/vague_terms",
      "severity": "high/medium/low"
    }}
  ],
  "summary": "一句话总结最大认知问题"
}}

请只输出JSON，不要输出多余解释。
"""

    return prompt


def _format_project_structure(ps: Dict[str, Any]) -> str:
    """格式化项目结构为可读文本"""
    lines = []

    # 行业标签
    if ps.get("industry_tags"):
        tags = [f"{x['label']}" for x in ps["industry_tags"]]
        lines.append(f"行业：{', '.join(tags)}")

    # 业务线
    if ps.get("business_lines"):
        lines.append("\n业务线：")
        for bl in ps["business_lines"]:
            lines.append(f"  - {bl['name']} ({bl['role']})")

    # 商业模式假设
    if ps.get("business_model_hypotheses"):
        lines.append("\n商业模式假设：")
        for bm in ps["business_model_hypotheses"][:5]:
            role = bm.get('role', '')
            lines.append(f"  - {bm['bucket_name']} ({role})")

    # 风险桶
    if ps.get("risk_buckets"):
        lines.append("\n风险点：")
        for r in ps["risk_buckets"][:5]:
            lines.append(f"  - {r['bucket_name']}")

    # 关键不确定性
    if ps.get("key_uncertainties"):
        lines.append("\n关键不确定性：")
        for u in ps["key_uncertainties"][:3]:
            lines.append(f"  - {u['uncertainty']}")

    return "\n".join(lines) if lines else "无"
