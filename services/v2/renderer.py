"""
renderer.py — 2.0报告渲染器

把结构化的V2PipelineResult渲染成：
1. Markdown报告（用于导出）
2. 页面展示数据（用于UI）
"""

from typing import Dict, Any
from .schemas import V2PipelineResult, Recommendation, RiskSignal


def render_markdown(result: V2PipelineResult, company_name: str = "") -> str:
    """渲染Markdown格式报告"""
    
    # 一句话决策
    rec_emoji = {
        "推进": "✅",
        "暂不推进": "❌",
        "继续跟进": "⚠️"
    }
    rec = result.decision.recommendation.value if result.decision else "继续跟进"
    emoji = rec_emoji.get(rec, "📋")
    
    lines = [
        f"# {company_name} — 2.0尽调更新报告",
        f"",
        f"## 📌 一句话决策",
        f"",
        f"{emoji} **{rec}**：{result.decision.one_line_decision}",
        f"",
        f"---",
        f"",
        f"## 一、新增关键信息",
        f"",
    ]
    
    # 新增信息
    if result.new_info:
        for info in result.new_info:
            lines.append(f"- **[{info.get('category', '其他')}]** {info.get('content', '')}")
    else:
        lines.append("*无新增关键信息*")
    
    lines.extend([
        f"",
        f"---",
        f"",
        f"## 二、字段变化分析",
        f"",
    ])
    
    # Delta
    if result.deltas:
        for d in result.deltas:
            impact_emoji = "✅" if d.value_assessment.value == "high" else ("⚠️" if d.value_assessment.value == "medium" else "❌")
            lines.extend([
                f"### {d.field_name}",
                f"- 状态变化：{d.old_status.value} → {d.new_status.value}",
                f"- 变化内容：{d.change_summary}",
                f"- 价值评估：{impact_emoji} {d.value_assessment.value}",
                f"- 对决策影响：{d.impact_on_decision.value if hasattr(d.impact_on_decision, 'value') else d.impact_on_decision}",
                f"",
            ])
    else:
        lines.append("*无字段变化*")
    
    lines.extend([
        f"",
        f"> 💡 **{result.delta_summary}**",
        f"",
        f"---",
        f"",
        f"## 三、回答质量评估",
        f"",
        f"| 类型 | 数量 |",
        f"|------|------|",
        f"| ✅ 有效回答 | {result.qa_summary.effective} |",
        f"| ⚠️ 模糊回答 | {result.qa_summary.fuzzy} |",
        f"| ❌ 回避问题 | {result.qa_summary.evasive} |",
        f"",
        f"**高频回避主题**：{', '.join(result.qa_summary.high_frequency_theme) if result.qa_summary.high_frequency_theme else '无'}",
        f"",
        f"> 💬 **{result.qa_summary.one_line_signal}**",
        f"",
    ])
    
    # 详细QA结果
    if result.qa_results:
        lines.extend([
            f"### 逐题判断详情",
            f"",
        ])
        for qa in result.qa_results:
            judge_emoji = {"effective": "✅", "fuzzy": "⚠️", "evasive": "❌"}.get(qa.judgment.value, "❓")
            lines.extend([
                f"**问题**：{qa.question}",
                f"- 回答摘要：{qa.answer_summary}",
                f"- 判断：{judge_emoji} {qa.judgment.value}",
                f"- 理由：{qa.reason}",
                f"- 证据：{qa.evidence}",
                f"",
            ])
    
    lines.extend([
        f"---",
        f"",
        f"## 四、风险变化",
        f"",
    ])
    
    # 风险更新
    if result.risk_updates:
        for r in result.risk_updates:
            status_emoji = {
                "resolved": "✅",
                "partially_resolved": "⚠️",
                "unresolved": "❌",
                "new_risk": "🆕",
                "unverifiable": "❓"
            }.get(r.new_status.value, "❓")
            
            lines.extend([
                f"### {r.risk_name} {status_emoji}",
                f"- 状态变化：{r.old_status.value} → {r.new_status.value}",
                f"- 严重程度：{r.severity}",
                f"- 理由：{r.reason}",
                f"",
            ])
    else:
        lines.append("*无风险更新*")
    
    if result.risk_summary.summary:
        lines.extend([
            f"> ⚠️ **{result.risk_summary.summary}**",
            f"",
        ])
    
    lines.extend([
        f"---",
        f"",
        f"## 五、判断更新",
        f"",
        f"| 项目 | 内容 |",
        f"|------|------|",
        f"| 之前立场 | {result.decision.previous_stance} |",
        f"| 当前立场 | {result.decision.current_stance} |",
        f"| 是否改变 | {'是' if result.decision.changed else '否'} |",
        f"| 投资建议 | {emoji} {rec} |",
        f"",
        f"### 决策逻辑",
    ])
    
    for i, logic in enumerate(result.decision.decision_logic or [], 1):
        lines.append(f"{i}. {logic}")
    
    if not result.decision.decision_logic:
        lines.append("*暂无足够信息支撑决策逻辑*")
    
    if result.decision.why_not_now:
        lines.extend([
            "",
            "### 为什么不是'以后再看'?",
        ])
        for reason in result.decision.why_not_now:
            lines.append(f"- {reason}")
    
    if result.decision.what_would_change_decision:
        lines.extend([
            f"",
            f"### 如果能拿到这些信息，判断会完全不同",
        ])
        for item in result.decision.what_would_change_decision:
            lines.append(f"- {item}")
    
    lines.extend([
        f"",
        f"---",
        f"",
        f"## 六、会议信号洞察（Alpha Layer）",
        f"",
        f"### 团队画像",
        f"- 类型：{result.alpha.team_profile_label}",
        f"- 证据：{result.alpha.team_profile_evidence}",
        f"",
        f"### 风险信号",
        f"- 信号灯：{'🔴' if result.alpha.risk_signal == RiskSignal.RED else ('🟡' if result.alpha.risk_signal == RiskSignal.YELLOW else '🟢')} {result.alpha.risk_signal.value.upper()}",
        f"- 原因：{result.alpha.risk_signal_reason}",
        f"",
        f"### 回避模式",
        f"- 模式：{result.alpha.avoidance_pattern or '无明显模式'}",
        f"- 频率：{result.alpha.avoidance_frequency}",
        f"- 例子：{result.alpha.avoidance_example or 'N/A'}",
        f"",
        f"### 估值引导信号",
        f"- 是否存在：{'是' if result.alpha.valuation_guidance_exists else '否'}",
        f"- 证据：{result.alpha.valuation_guidance_evidence or 'N/A'}",
        f"",
        f"### 会议质量评分",
        f"- 评分：{result.alpha.meeting_quality_score}/10",
        f"",
        f"> 🧠 **{result.alpha.one_line_insight or '未形成稳定直觉信号'}**",
        f"",
        f"---",
        f"",
        f"*本报告由AI项目判断工作台2.0生成*",
    ])
    
    return "\n".join(lines)


def render_ui_card(result: V2PipelineResult) -> Dict[str, Any]:
    """渲染UI展示用的卡片数据"""
    
    rec = result.decision.recommendation.value
    rec_color = {
        "推进": "green",
        "暂不推进": "red",
        "继续跟进": "yellow"
    }.get(rec, "gray")
    
    return {
        # 决策卡片
        "decision_card": {
            "recommendation": rec,
            "recommendation_color": rec_color,
            "one_liner": result.decision.one_line_decision,
            "changed": result.decision.changed,
            "previous_stance": result.decision.previous_stance,
            "current_stance": result.decision.current_stance,
        },
        
        # 决策逻辑（用于折叠展示）
        "decision_logic": result.decision.decision_logic,
        "why_not_now": result.decision.why_not_now,
        "what_would_change": result.decision.what_would_change_decision,
        
        # QA摘要
        "qa_summary": {
            "total": result.qa_summary.total,
            "effective": result.qa_summary.effective,
            "fuzzy": result.qa_summary.fuzzy,
            "evasive": result.qa_summary.evasive,
            "high_frequency_theme": result.qa_summary.high_frequency_theme,
            "one_line_signal": result.qa_summary.one_line_signal,
        },
        
        # 风险摘要
        "risk_summary": {
            "resolved": sum(1 for r in result.risk_updates if r.new_status.value == "resolved"),
            "partially_resolved": sum(1 for r in result.risk_updates if r.new_status.value == "partially_resolved"),
            "unresolved": sum(1 for r in result.risk_updates if r.new_status.value == "unresolved"),
            "new_risks": len(result.risk_summary.new_risks),
            "one_liner": result.risk_summary.summary,
        },
        
        # Alpha信号
        "alpha_signals": {
            "team_profile": {
                "label": result.alpha.team_profile_label,
                "evidence": result.alpha.team_profile_evidence,
            },
            "risk_signal": {
                "level": result.alpha.risk_signal.value,
                "reason": result.alpha.risk_signal_reason,
            },
            "avoidance": {
                "pattern": result.alpha.avoidance_pattern,
                "frequency": result.alpha.avoidance_frequency,
                "example": result.alpha.avoidance_example,
            },
            "valuation_guidance": {
                "exists": result.alpha.valuation_guidance_exists,
                "evidence": result.alpha.valuation_guidance_evidence,
            },
            "meeting_score": result.alpha.meeting_quality_score,
            "one_liner": result.alpha.one_line_insight,
        },
        
        # Delta高价值变化
        "high_value_deltas": [
            {
                "field": d.field_name,
                "change": f"{d.old_status.value} → {d.new_status.value}",
                "assessment": d.value_assessment.value,
                "impact": d.impact_on_decision.value if hasattr(d.impact_on_decision, 'value') else d.impact_on_decision,
            }
            for d in result.deltas
            if d.value_assessment.value == "high"
        ][:5],  # 最多5条
        
        # 新增信息
        "new_info": result.new_info[:10],  # 最多10条
    }
