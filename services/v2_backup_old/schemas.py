"""
schemas.py — 2.0尽调更新系统数据结构定义

所有模块的输入/输出 schema，统一管理，确保结构化。

枚举值定义：
- FieldStatus: 字段状态 (unknown/missing/weak/partial/verified/strong)
- ValueAssessment: 价值评估 (high/medium/low)
- RiskImpact: 对风险影响 (risk_relieved/partially_relieved/no_relief/new_risk_signal)
- DecisionImpact: 对决策影响 (positive_change/negative_change/no_change/uncertain)
- RiskStatus: 风险状态 (unresolved/partially_resolved/resolved/new_risk/unverifiable)
- QAJudgment: 回答质量 (effective/fuzzy/evasive)
- Recommendation: 投资建议 (推进/暂不推进/继续跟进)
- RiskSignal: 风险信号 (red/yellow/green)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ===== 枚举定义 =====

class FieldStatus(str, Enum):
    """字段状态枚举"""
    UNKNOWN = "unknown"      # 完全未知
    MISSING = "missing"      # 1.0未提及
    WEAK = "weak"            # 提及但无数据支撑
    PARTIAL = "partial"      # 部分验证，有数据但不完整
    VERIFIED = "verified"    # 有效验证，有数据可核实
    STRONG = "strong"       # 充分验证，壁垒明显


class QAJudgment(str, Enum):
    """回答质量枚举"""
    EFFECTIVE = "effective"   # ✅ 有效回答
    FUZZY = "fuzzy"          # ⚠️ 模糊回答
    EVASIVE = "evasive"      # ❌ 回避问题


class ValueAssessment(str, Enum):
    """价值评估枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskImpact(str, Enum):
    """对风险影响枚举"""
    RISK_RELIEVED = "risk_relieved"
    PARTIALLY_RELIEVED = "partially_relieved"
    NO_RELIEF = "no_relief"
    NEW_RISK_SIGNAL = "new_risk_signal"


class DecisionImpact(str, Enum):
    """对决策影响枚举（用于DeltaResult）"""
    POSITIVE_CHANGE = "positive_change"
    NEGATIVE_CHANGE = "negative_change"
    NO_CHANGE = "no_change"
    UNCERTAIN = "uncertain"


class RiskStatus(str, Enum):
    """风险状态枚举"""
    UNRESOLVED = "unresolved"           # 未缓解
    PARTIALLY_RESOLVED = "partially_resolved"  # 部分缓解
    RESOLVED = "resolved"               # 已缓解
    NEW_RISK = "new_risk"               # 新增风险
    UNVERIFIABLE = "unverifiable"      # 仍无法判断


class Recommendation(str, Enum):
    """投资建议枚举"""
    PROCEED = "推进"        # ✅ 建议推进
    HOLD = "暂不推进"       # ❌ 暂不推进
    FOLLOW_UP = "继续跟进"   # ⚠️ 继续跟进


class RiskSignal(str, Enum):
    """风险信号枚举"""
    RED = "red"     # 🔴 高风险
    YELLOW = "yellow"  # 🟡 中风险
    GREEN = "green"  # 🟢 低风险


# ===== V1结构化输出（供2.0使用）=====

@dataclass
class FieldState:
    """单个字段状态"""
    field_id: str                      # 字段唯一标识
    field_name: str                    # 字段中文名
    status: FieldStatus               # 状态
    value: str = ""                   # 值/内容
    evidence: str = ""                # 证据
    confidence: float = 0.5           # 置信度 0-1


@dataclass
class Question:
    """问题清单中的单个问题"""
    qid: str                          # 问题唯一ID
    question: str                     # 问题内容
    why: str = ""                     # 为什么问这个问题
    priority: str = "medium"          # priority: high/medium/low
    topic: str = ""                   # 问题主题


@dataclass
class Risk:
    """单个风险项"""
    risk_id: str                      # 风险唯一ID
    name: str                         # 风险名称
    severity: str = "medium"           # severity: high/medium/low
    reason: str = ""                  # 风险原因
    evidence: List[str] = field(default_factory=list)  # 证据列表


@dataclass
class V1StructuredOutput:
    """1.0阶段结构化输出，供2.0使用"""
    summary: Dict[str, Any] = field(default_factory=dict)  # 一句话总结 + 核心摘要
    field_states: Dict[str, FieldState] = field(default_factory=dict)  # 字段状态字典
    questions: List[Question] = field(default_factory=list)  # 问题清单
    risks: List[Risk] = field(default_factory=list)  # 风险列表
    conclusion: Dict[str, Any] = field(default_factory=dict)  # 结论
    field_template: str = ""  # 字段模板原文

    def to_dict(self) -> dict:
        """转dict用于存储"""
        return {
            "summary": self.summary,
            "field_states": {
                k: {
                    "field_id": v.field_id,
                    "field_name": v.field_name,
                    "status": v.status.value,
                    "value": v.value,
                    "evidence": v.evidence,
                    "confidence": v.confidence
                }
                for k, v in self.field_states.items()
            },
            "questions": [
                {"qid": q.qid, "question": q.question, "why": q.why, "priority": q.priority, "topic": q.topic}
                for q in self.questions
            ],
            "risks": [
                {"risk_id": r.risk_id, "name": r.name, "severity": r.severity, "reason": r.reason, "evidence": r.evidence}
                for r in self.risks
            ],
            "conclusion": self.conclusion,
            "field_template": self.field_template
        }

    @classmethod
    def from_dict(cls, data: dict) -> "V1StructuredOutput":
        """从dict恢复"""
        obj = cls()
        obj.summary = data.get("summary", {})
        obj.field_template = data.get("field_template", "")
        
        obj.field_states = {}
        for k, v in data.get("field_states", {}).items():
            obj.field_states[k] = FieldState(
                field_id=v.get("field_id", k),
                field_name=v.get("field_name", k),
                status=FieldStatus(v.get("status", "unknown")),
                value=v.get("value", ""),
                evidence=v.get("evidence", ""),
                confidence=v.get("confidence", 0.5)
            )
        
        obj.questions = [
            Question(q["qid"], q["question"], q.get("why", ""), q.get("priority", "medium"), q.get("topic", ""))
            for q in data.get("questions", [])
        ]
        
        obj.risks = [
            Risk(r["risk_id"], r["name"], r.get("severity", "medium"), r.get("reason", ""), r.get("evidence", []))
            for r in data.get("risks", [])
        ]
        
        obj.conclusion = data.get("conclusion", {})
        return obj


# ===== 2.0 各模块输出Schema =====

@dataclass
class DeltaResult:
    """Delta Engine 输出"""
    field_id: str
    field_name: str
    old_status: FieldStatus
    new_status: FieldStatus
    change_summary: str
    value_assessment: ValueAssessment
    impact_on_risk: RiskImpact
    impact_on_decision: DecisionImpact  # 枚举类型


@dataclass
class QAResult:
    """单题QA判断结果"""
    qid: str
    question: str
    answer_summary: str
    judgment: QAJudgment
    reason: str
    evidence: str  # 原文片段


@dataclass
class QASummary:
    """QA汇总结果"""
    total: int
    effective: int
    fuzzy: int
    evasive: int
    high_frequency_theme: List[str]  # 高频回避主题
    one_line_signal: str  # 一句话会议信号


@dataclass
class RiskUpdate:
    """风险变化结果"""
    risk_id: str
    risk_name: str
    old_status: RiskStatus
    new_status: RiskStatus
    change_type: str  # unchanged/partially_resolved/resolved/new
    severity: str
    reason: str
    evidence: List[str]


@dataclass
class RiskUpdateSummary:
    """风险更新汇总"""
    updated_risks: List[RiskUpdate]
    new_risks: List[RiskUpdate]
    summary: str  # 一句话风险总结


@dataclass
class DecisionUpdate:
    """判断更新结果"""
    previous_stance: str
    current_stance: str
    changed: bool
    decision_logic: List[str]
    why_not_now: List[str]
    what_would_change_decision: List[str]
    recommendation: Recommendation
    one_line_decision: str


@dataclass
class AlphaSignal:
    """Alpha Layer直觉信号"""
    team_profile_label: str  # 讲故事的人/做业务的人/两者兼备/无法判断
    team_profile_evidence: str
    risk_signal: RiskSignal
    risk_signal_reason: str
    valuation_guidance_exists: bool
    valuation_guidance_evidence: str
    avoidance_pattern: str
    avoidance_frequency: str  # high/medium/low
    avoidance_example: str
    meeting_quality_score: int  # 0-10
    one_line_insight: str


@dataclass
class V2PipelineResult:
    """2.0 Pipeline完整输出"""
    new_info: List[Dict[str, str]]  # [{"category": "业务", "content": "..."}]
    deltas: List[DeltaResult]
    delta_summary: str
    qa_results: List[QAResult]
    qa_summary: QASummary
    risk_updates: List[RiskUpdate]
    risk_summary: RiskUpdateSummary
    decision: DecisionUpdate
    alpha: AlphaSignal
    
    def to_dict(self) -> dict:
        """转dict用于存储"""
        return {
            "new_info": self.new_info,
            "deltas": [
                {
                    "field_id": d.field_id,
                    "field_name": d.field_name,
                    "old_status": d.old_status.value,
                    "new_status": d.new_status.value,
                    "change_summary": d.change_summary,
                    "value_assessment": d.value_assessment.value,
                    "impact_on_risk": d.impact_on_risk.value,
                    "impact_on_decision": d.impact_on_decision.value if hasattr(d.impact_on_decision, 'value') else d.impact_on_decision
                }
                for d in self.deltas
            ],
            "delta_summary": self.delta_summary,
            "qa_results": [
                {
                    "qid": q.qid,
                    "question": q.question,
                    "answer_summary": q.answer_summary,
                    "judgment": q.judgment.value,
                    "reason": q.reason,
                    "evidence": q.evidence
                }
                for q in self.qa_results
            ],
            "qa_summary": {
                "total": self.qa_summary.total,
                "effective": self.qa_summary.effective,
                "fuzzy": self.qa_summary.fuzzy,
                "evasive": self.qa_summary.evasive,
                "high_frequency_theme": self.qa_summary.high_frequency_theme,
                "one_line_signal": self.qa_summary.one_line_signal
            },
            "risk_updates": [
                {
                    "risk_id": r.risk_id,
                    "risk_name": r.risk_name,
                    "old_status": r.old_status.value,
                    "new_status": r.new_status.value,
                    "change_type": r.change_type,
                    "severity": r.severity,
                    "reason": r.reason,
                    "evidence": r.evidence
                }
                for r in self.risk_updates
            ],
            "risk_summary": {
                "updated_risks": [
                    {
                        "risk_id": r.risk_id,
                        "risk_name": r.risk_name,
                        "old_status": r.old_status.value,
                        "new_status": r.new_status.value,
                        "change_type": r.change_type,
                        "severity": r.severity,
                        "reason": r.reason,
                        "evidence": r.evidence
                    }
                    for r in self.risk_summary.updated_risks
                ],
                "new_risks": [
                    {
                        "risk_id": r.risk_id,
                        "risk_name": r.risk_name,
                        "old_status": r.old_status.value,
                        "new_status": r.new_status.value,
                        "change_type": r.change_type,
                        "severity": r.severity,
                        "reason": r.reason,
                        "evidence": r.evidence
                    }
                    for r in self.risk_summary.new_risks
                ],
                "summary": self.risk_summary.summary
            },
            "decision": {
                "previous_stance": self.decision.previous_stance,
                "current_stance": self.decision.current_stance,
                "changed": self.decision.changed,
                "decision_logic": self.decision.decision_logic,
                "why_not_now": self.decision.why_not_now,
                "what_would_change_decision": self.decision.what_would_change_decision,
                "recommendation": self.decision.recommendation.value,
                "one_line_decision": self.decision.one_line_decision
            },
            "alpha": {
                "team_profile_label": self.alpha.team_profile_label,
                "team_profile_evidence": self.alpha.team_profile_evidence,
                "risk_signal": self.alpha.risk_signal.value,
                "risk_signal_reason": self.alpha.risk_signal_reason,
                "valuation_guidance_exists": self.alpha.valuation_guidance_exists,
                "valuation_guidance_evidence": self.alpha.valuation_guidance_evidence,
                "avoidance_pattern": self.alpha.avoidance_pattern,
                "avoidance_frequency": self.alpha.avoidance_frequency,
                "avoidance_example": self.alpha.avoidance_example,
                "meeting_quality_score": self.alpha.meeting_quality_score,
                "one_line_insight": self.alpha.one_line_insight
            }
        }
