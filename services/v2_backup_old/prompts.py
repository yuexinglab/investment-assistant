"""
prompts.py — 2.0 Prompt构建器

每个模块的prompt builder，输出结构化JSON供后续模块消费。
"""

from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import QASummary
else:
    # 运行时也需要导入，否则类型注解无法工作
    from .schemas import QASummary  # noqa: F401


# ===== Extractor Prompt =====

EXTRACTOR_SYSTEM = """你是一个专业的信息提取器。

你的任务：从会议纪要中提取"新增的、对投资判断有价值的信息"。

要求：
- 不重复1.0已有信息
- 只写事实，不做分析
- 忽略空话（如"我们很领先""市场很大"）
- 每个信息点必须标注类别（业务/财务/客户/技术/战略）

输出：JSON数组，每项包含 category 和 content。"""


def build_extractor_prompt(meeting_text: str, v1_summary: str = "") -> str:
    return f"""【1.0阶段摘要】
{v1_summary if v1_summary else "（无摘要）"}

【本次会议纪要】
{meeting_text}

请提取所有新增的关键信息，输出JSON格式：
{{
  "new_info": [
    {{"category": "业务", "content": "..."}},
    {{"category": "财务", "content": "..."}},
    ...
  ]
}}

如果没有新增有效信息，输出：
{{"new_info": []}}"""


# ===== Delta Engine Prompt =====

DELTA_SYSTEM = """你是一个变化分析引擎。

你的任务是：
1. 对比1.0字段状态 vs 2.0新增信息
2. 判断每个字段是否发生变化
3. 评估这个变化"有没有用"

⚠️ 关键原则：变化 ≠ 价值，要判断变化是否真正缓解了核心风险。

输出：JSON数组"""


def build_delta_prompt(
    field_states: List[Dict], 
    new_info: List[Dict]
) -> str:
    # 格式化字段状态
    fields_text = "\n".join([
        f"- {f['field_name']} ({f['field_id']}): {f['status']} - {f.get('value', 'N/A')}"
        for f in field_states
    ]) if field_states else "（无结构化字段，请从新增信息推断字段变化）"
    
    # 格式化新增信息
    info_text = "\n".join([
        f"- [{i['category']}] {i['content']}"
        for i in new_info
    ]) if new_info else "（无新增信息）"
    
    return f"""【1.0字段状态】
{fields_text}

【本次新增信息】
{info_text}

请逐字段分析，输出JSON：
{{
  "deltas": [
    {{
      "field_id": "xxx",
      "field_name": "xxx",
      "old_status": "missing/weak/partial/verified/strong",
      "new_status": "missing/weak/partial/verified/strong", 
      "change_summary": "xxx",
      "value_assessment": "high/medium/low",
      "impact_on_risk": "risk_relieved/partially_relieved/no_relief/new_risk_signal",
      "impact_on_decision": "positive_change/negative_change/no_change/uncertain"
    }}
  ],
  "delta_summary": "一句话总结：哪些变化是真有价值的？"
}}"""


# ===== QA Judge Prompts =====

# 单题判断
QA_SINGLE_SYSTEM = """你是回答质量判官。

你的任务是：判断管理层对单个问题的回答质量。

⚠️ 核心：不是判断回答"对不对"，而是判断回答"有没有用"。

判断标准：
- effective: 给出具体数据/可核实信息
- fuzzy: 描述概念，但无数据支撑
- evasive: 未正面回答或转移话题

输出：JSON"""


def build_qa_single_prompt(question: Dict, meeting_text: str) -> str:
    return f"""【问题】
问题ID: {question.get('qid', 'unknown')}
问题: {question.get('question', '')}
为什么问: {question.get('why', '（未说明）')}
主题: {question.get('topic', '（未标注）')}

【会议回答】
{meeting_text}

请判断回答质量，输出JSON：
{{
  "qid": "{question.get('qid', '')}",
  "question": "{question.get('question', '')}",
  "answer_summary": "管理层回答的核心内容摘要",
  "judgment": "effective/fuzzy/evasive",
  "reason": "为什么这么判断",
  "evidence": "会议中相关的原话片段"
}}"""


# QA汇总
QA_SUMMARY_SYSTEM = """你是回答质量汇总器。

你的任务是：汇总所有单题判断结果，输出整体评估。"""


def build_qa_summary_prompt(qa_results: List[Dict]) -> str:
    # 格式化单题结果
    results_text = "\n".join([
        f"- {r['qid']}: {r['judgment']} - {r['reason']}"
        for r in qa_results
    ])
    
    return f"""【单题判断结果】
{results_text}

请汇总，输出JSON：
{{
  "total": {len(qa_results)},
  "effective": X,
  "fuzzy": X,
  "evasive": X,
  "high_frequency_theme": ["回避频率最高的主题1", "..."],
  "one_line_signal": "一句话总结这场会议的回答质量信号"
}}"""


# ===== Risk Update Prompt =====

RISK_UPDATE_SYSTEM = """你是风险更新引擎。

你的任务是：判断每个风险的状态是否变化。

⚠️ 基于Delta和QA结果，判断风险是缓解了、加剧了、还是新出现了。

输出：JSON数组"""


def build_risk_update_prompt(
    v1_risks: List[Dict],
    deltas: List[Dict],
    qa_results: List[Dict]
) -> str:
    # 格式化风险
    risks_text = "\n".join([
        f"- {r['risk_id']}: {r['name']} (severity: {r.get('severity', 'medium')})"
        for r in v1_risks
    ]) if v1_risks else "（无结构化风险，请从Delta推断）"
    
    # 格式化Delta
    delta_text = "\n".join([
        f"- {d['field_name']}: {d['old_status']} → {d['new_status']} ({d['impact_on_risk']})"
        for d in deltas
    ]) if deltas else "（无字段变化）"
    
    # 格式化QA
    evasive_count = sum(1 for r in qa_results if r.get('judgment') == 'evasive')
    qa_text = f"回避问题数: {evasive_count}/{len(qa_results)}"
    
    return f"""【1.0风险列表】
{risks_text}

【字段变化分析】
{delta_text}

【回答质量摘要】
{qa_text}

请更新每个风险的状态，输出JSON：
{{
  "updated_risks": [
    {{
      "risk_id": "xxx",
      "risk_name": "xxx",
      "old_status": "unresolved/partially_resolved/resolved/unverifiable",
      "new_status": "unresolved/partially_resolved/resolved/unverifiable",
      "change_type": "unchanged/partially_resolved/resolved/new",
      "severity": "high/medium/low",
      "reason": "为什么这样判断",
      "evidence": ["相关证据1", "..."]
    }}
  ],
  "new_risks": [
    {{
      "risk_id": "auto_xxx",
      "risk_name": "新发现的风险名称",
      "severity": "high/medium/low",
      "reason": "为什么会是新风险",
      "evidence": ["证据"]
    }}
  ],
  "risk_summary": "一句话总结：整体风险是加剧了还是缓解了？"
}}"""


# ===== Decision Updater Prompt =====

DECISION_UPDATER_SYSTEM = """你是投资判断更新器。

你的任务是：回答核心问题——"这场会议是否改变了投资判断？"

⚠️ 必须明确，不能含糊！要给出清晰的决策和理由。

输出：JSON"""


def build_decision_updater_prompt(
    v1_conclusion: Dict,
    risk_summary: str,
    qa_summary: QASummary,
    new_info: List[Dict],
    high_value_deltas: List[Dict] = None
) -> str:
    """构建 Decision Updater Prompt（结构化版本）"""
    
    # 结构化的1.0结论
    v1_text = f"""立场: {v1_conclusion.get('stance', '未知')}
理由: {v1_conclusion.get('reason', '未知')}
必须验证项: {', '.join(v1_conclusion.get('must_verify', []) or ['无'])}"""
    
    # 结构化的风险摘要
    risk_text = risk_summary if risk_summary else "暂无风险变化"
    
    # 结构化的QA摘要
    qa_text = f"""有效: {qa_summary.effective}个
模糊: {qa_summary.fuzzy}个
回避: {qa_summary.evasive}个
高频回避主题: {', '.join(qa_summary.high_frequency_theme) if qa_summary.high_frequency_theme else '无'}
整体信号: {qa_summary.one_line_signal}"""
    
    # 结构化的新增信息
    info_text = "\n".join([
        f"- [{i.get('category', '其他')}] {i.get('content', '')}"
        for i in new_info
    ]) if new_info else "（无新增信息）"
    
    # 结构化的高价值变化
    delta_text = "\n".join([
        f"- {d.get('field_name', '')}: {d.get('value_assessment', '')} 价值, 对决策{d.get('impact_on_decision', '')}"
        for d in (high_value_deltas or [])
    ]) if high_value_deltas else "（无高价值变化）"
    
    return f"""【1.0投资结论】
{v1_text}

【本次风险变化】
{risk_text}

【本次回答质量统计】
{qa_text}

【新增关键信息】
{info_text}

【有价值的字段变化】
{delta_text}

请更新投资判断，输出JSON：
{{
  "previous_stance": "1.0时的立场",
  "current_stance": "当前立场",
  "changed": true/false,
  "decision_logic": ["决定理由1", "理由2", "理由3"],
  "why_not_now": ["现在投的障碍1", "障碍2"],
  "what_would_change_decision": ["如果能拿到这个信息，判断会完全不同1", "..."],
  "recommendation": "推进/暂不推进/继续跟进",
  "one_line_decision": "一句话决策：如'客户集中度未验证前，不建议推进'"
}}"""


# ===== Alpha Layer Prompt =====

ALPHA_LAYER_SYSTEM = """你是投资人直觉层。

你的任务是：输出"非显性信号"——不是他们说了什么，而是他们的行为模式透露了什么。

⚠️ 要锋利，不要温和。要下判断，不要只描述。

输出：JSON"""


def build_alpha_layer_prompt(
    meeting_text: str,
    qa_results: List[Dict],
    new_info: List[Dict]
) -> str:
    # 统计回避情况
    evasive = [r for r in qa_results if r.get('judgment') == 'evasive']
    evasive_themes = [r.get('question', '')[:20] for r in evasive[:3]]
    
    info_count = len(new_info)
    
    return f"""【会议纪要】
{meeting_text[:2000]}...

【回答质量统计】
有效: {sum(1 for r in qa_results if r.get('judgment') == 'effective')}/{len(qa_results)}
模糊: {sum(1 for r in qa_results if r.get('judgment') == 'fuzzy')}/{len(qa_results)}
回避: {len(evasive)}/{len(qa_results)}

【高频回避主题】
{', '.join(evasive_themes) if evasive_themes else '无明显回避'}

【新增信息数量】
{info_count}条

请输出直觉信号，输出JSON：
{{
  "team_profile_label": "讲故事的人/做业务的人/两者兼备/无法判断",
  "team_profile_evidence": "具体证据",
  "risk_signal": "red/yellow/green",
  "risk_signal_reason": "原因",
  "valuation_guidance_exists": true/false,
  "valuation_guidance_evidence": "如果有，具体证据",
  "avoidance_pattern": "回避模式描述",
  "avoidance_frequency": "high/medium/low",
  "avoidance_example": "具体回避例子",
  "meeting_quality_score": 0-10,
  "one_line_insight": "一句话洞察"
}}"""


# ===== V1结构化提取 Prompt =====

V1_EXTRACT_SYSTEM = """你是一个分析结果结构化器。

你的任务：从1.0阶段的分析文本中提取结构化数据，供2.0阶段使用。

⚠️ 必须严格输出JSON格式。"""


def build_v1_structured_prompt(v1_report: str, field_template: str = "") -> str:
    return f"""【1.0分析报告原文】
{v1_report}

【字段模板】
{field_template if field_template else "请从报告中推断关键字段"}

请提取并输出JSON：
{{
  "summary": {{
    "one_liner": "一句话总结公司",
    "business_model": "商业模式",
    "revenue_source": "收入来源",
    "stage": "发展阶段",
    "core_capabilities": ["核心能力1", "..."],
    "initial_risk_scan": ["初步风险1", "..."]
  }},
  "field_states": [
    {{
      "field_id": "xxx",
      "field_name": "xxx",
      "status": "unknown/missing/weak/partial/verified/strong",
      "value": "具体值或内容",
      "evidence": "证据",
      "confidence": 0.0-1.0
    }}
  ],
  "questions": [
    {{
      "qid": "q1",
      "question": "问题内容",
      "why": "为什么问",
      "priority": "high/medium/low",
      "topic": "主题"
    }}
  ],
  "risks": [
    {{
      "risk_id": "xxx",
      "name": "风险名称",
      "severity": "high/medium/low",
      "reason": "为什么是风险",
      "evidence": ["证据1", "..."]
    }}
  ],
  "conclusion": {{
    "stance": "立场",
    "reason": "理由",
    "must_verify": ["必须验证项1", "..."]
  }}
}}"""
