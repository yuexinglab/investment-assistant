# -*- coding: utf-8 -*-
"""
2.0 会后分析层 - 数据结构定义

数据流: Step6 → Step7 → Step8 → Step9
沉淀: 问题库候选 + 行业认知候选 + 对话历史 + 用户画像候选
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    PARTIALLY_ANSWERED = "partially_answered"
    INDIRECTLY_ANSWERED = "indirectly_answered"  # v2.2 新增：侧面回答
    EVADED = "evaded"
    NOT_ANSWERED = "not_answered"


class AnswerImpact(str, Enum):
    """Step7 回答对原判断的影响（独立枚举，与 Step8 ImpactType 区分）"""
    STRENGTHENS = "strengthens"        # 强化
    WEAKENS = "weakens"               # 削弱
    SLIGHTLY_STRENGTHENS = "slightly_strengthens"  # 轻度强化
    SLIGHTLY_WEAKENS = "slightly_weakens"          # 轻度削弱
    NO_CHANGE = "no_change"            # 无变化
    UNCLEAR = "unclear"                # 不明确


class QualityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImpactType(str, Enum):
    SUPPORTS = "supports"
    WEAKENS = "weakens"
    OVERTURNS = "overturns"
    NEUTRAL = "neutral"


class ChangeType(str, Enum):
    REINFORCED = "reinforced"         # 被有力证据强化
    SLIGHTLY_REINFORCED = "slightly_reinforced"  # v2.2.2：证据偏弱/claim为主，轻微强化
    WEAKENED = "weakened"            # 被削弱（但非推翻）
    SLIGHTLY_WEAKENED = "slightly_weakened"      # v2.2.2：轻微削弱
    OVERTURNED = "overturned"        # 被有力证据推翻
    REFRAMED = "reframed"           # 框架重构（证据模糊或矛盾）
    UNCERTAIN = "uncertain"         # v2.2.2：证据主要来自 claim，有效性未验证


class HypothesisDirection(str, Enum):
    """
    Step8 v3 新增：假设的方向（独立于 change_type）。

    hypothesis_direction 描述"原假设如果成立，对项目意味着什么"。
    change_type 只描述"原假设在会议后是否被强化/削弱/推翻"。

    这两个字段必须组合使用，才能判断项目好坏：
      - positive + reinforced   → validated_positive
      - positive + weakened    → confirmed_negative
      - negative + reinforced   → confirmed_negative（风险被确认）
      - negative + weakened     → validated_positive（风险被化解）
    """
    POSITIVE = "positive"   # 原假设成立 → 对项目是正面信息（如：AI壁垒/客户验证）
    NEGATIVE = "negative"   # 原假设成立 → 对项目是负面信息/风险（如：无客户/无壁垒）
    NEUTRAL = "neutral"     # 原假设只是验证点，无明显正负倾向


class Recommendation(str, Enum):
    CONTINUE = "continue"
    HOLD = "hold"
    STOP = "stop"
    REQUEST_MORE_INFO = "request_more_info"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InfoCategory(str, Enum):
    REVENUE = "收入"
    CUSTOMER = "客户"
    TECH = "技术"
    PRODUCT = "产品"
    CAPACITY = "产能"
    TEAM = "团队"
    FINANCE = "财务"
    STRATEGY = "战略"
    MARKET = "市场"


class ImportanceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============ Step6: 新增信息提取 ============

@dataclass
class NewInformation:
    id: str                          # ni_001, ni_002 ...
    content: str                     # 信息内容摘要
    category: InfoCategory           # 分类
    evidence: str                    # 原文证据片段
    importance: ImportanceLevel       # 重要性
    contradicts_bp: bool             # 是否与BP矛盾
    is_critical: bool                # 是否为关键信息（特别提醒用户）

    # v2.1 新增字段
    info_type: str = "claim"          # 信息类型：fact/claim/number/plan/risk_signal/correction
    novelty_type: str = "new"         # 新增类型：new/more_specific/contradiction/confirmation
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM  # 可信度
    affects_judgement: str = ""       # 影响哪个判断方向
    related_prior_judgement: str = "" # 对应的会前判断
    follow_up_hint: str = ""          # 后续验证建议
    # v2.2 新增字段
    transcript_noise: bool = False    # evidence 是否有转写错误，content 是否做了纠正


@dataclass
class Step6Output:
    meeting_summary: str             # 一句话总结会议得到了什么
    new_information: List[NewInformation] = field(default_factory=list)


# ============ Step7: 问题对齐 + 会议质量 ============

@dataclass
class QuestionValidation:
    # 核心字段
    question_id: str = ""              # q_001, q_002 ...
    original_question: str = ""         # 原始问题原文
    matched_information_ids: List[str] = field(default_factory=list)  # 匹配的ni_xxx列表
    matched_information_summary: List[str] = field(default_factory=list)  # v2.2.1 匹配信息内容列表
    answer_summary: str = ""           # 回答内容总结（必填，1-3句）
    status: AnswerStatus = AnswerStatus.NOT_ANSWERED   # 回答状态
    quality: QualityLevel = QualityLevel.MEDIUM          # 回答质量
    impact: AnswerImpact = AnswerImpact.NO_CHANGE        # 对原判断的影响（v2.2 新枚举）
    # v2.2 新增字段
    missing_evidence: List[str] = field(default_factory=list)  # 缺失证据列表
    follow_up_question: str = ""       # 下一轮追问
    # Profile 接入：区分问题来源
    question_source: str = "base"      # base / profile（v2.3 新增）
    profile_id: str = ""                # 如果是 profile 问题，记录来源画像 ID（v2.3 新增）


@dataclass
class MeetingQuality:
    answer_directness: ConfidenceLevel = ConfidenceLevel.MEDIUM   # 回答直接性
    evidence_strength: ConfidenceLevel = ConfidenceLevel.MEDIUM   # 证据强度（v2.2 新增）
    evasion_level: ConfidenceLevel = ConfidenceLevel.MEDIUM       # 回避程度（v2.2 新增）
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM   # 整体可信度
    consistency: ConfidenceLevel = ConfidenceLevel.MEDIUM          # 与BP一致性
    evasion_signals: List[str] = field(default_factory=list)      # 回避信号列表
    # v2.2.1 规则计算原始计数
    answered_count: int = 0
    partially_count: int = 0
    weak_count: int = 0  # evaded + not_answered
    missing_evidence_count: int = 0


@dataclass
class Step7Output:
    meeting_quality: MeetingQuality
    question_validation: List[QuestionValidation] = field(default_factory=list)


# ============ Step8: 认知更新（对抗式） ============

@dataclass
class HypothesisUpdate:
    # v2.3 新增
    hypothesis_direction: HypothesisDirection = HypothesisDirection.NEUTRAL  # 假设方向（正向/负向/中性）
    # v2.2.1 新增
    hypothesis_id: str = ""            # 对应 Step5 的 hypothesis_id（h_001 等）
    # 原有
    hypothesis: str = ""              # 原始假设（来自Step5）
    updated_view: str = ""             # v2.2.1 更新后的判断（取代 final_view）
    confidence_change: str = ""       # v2.2.1 信心变化，如 "medium → low" / "unchanged"
    change_type: ChangeType = ChangeType.REINFORCED  # 变化类型
    supporting_evidence: List[str] = field(default_factory=list)    # 支持证据（ni_xxx 列表）
    contradicting_evidence: List[str] = field(default_factory=list) # 反对证据（ni_xxx 列表）
    why_changed: str = ""             # 为什么改变（LLM 辅助生成）
    # v2.2.1 新增
    source_question_id: str = ""      # 来源问题 ID（q_xxx）


@dataclass
class NewRisk:
    risk: str                          # 风险描述
    source_question_id: str = ""       # 来源问题 ID（q_xxx）
    severity: ImportanceLevel = ImportanceLevel.MEDIUM  # 严重程度


@dataclass
class OverallChange:
    is_judgement_significantly_changed: bool
    new_risks: List[NewRisk] = field(default_factory=list)   # v2.2.1 替换 new_risk_added
    new_opportunity_added: Optional[str] = None


@dataclass
class Step8Output:
    overall_change: OverallChange
    hypothesis_updates: List[HypothesisUpdate] = field(default_factory=list)
    unchanged_hypotheses: List[str] = field(default_factory=list)  # v2.2.1 新增：未变化的假设列表


# ============ Step9: 决策与行动（v3 双层决策架构）============

class RiskLevel(str, Enum):
    """风险等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProcessDecision(str, Enum):
    """流程决策：这个项目还要不要继续跟？"""
    CONTINUE_DD = "continue_dd"       # 继续尽调/继续推进沟通
    REQUEST_MATERIALS = "request_materials"  # 先补材料，材料不到不继续深聊
    PAUSE = "pause"                   # 暂缓，等待关键事项变化
    STOP = "stop"                     # 停止跟进


class InvestmentDecision(str, Enum):
    """投资决策：当前是否足以进入投资/立项决策？"""
    INVEST_READY = "invest_ready"     # 当前证据已足够进入投资决策
    NOT_READY = "not_ready"           # 当前不能投资，需要补关键证据
    REJECT = "reject"                 # 核心逻辑已被打穿，不建议投资


@dataclass
class OverallDecisionV3:
    """双层决策（v3）"""
    process_decision: ProcessDecision  # 流程决策
    investment_decision: InvestmentDecision  # 投资决策
    confidence: ConfidenceLevel        # high / medium / low
    one_line_conclusion: str          # 一句话结论


@dataclass
class DecisionBreakdownV3:
    """决策分解（v3）：四象限结构"""
    verified_positives: List[str] = field(default_factory=list)      # 已验证的好
    unverified_positives: List[str] = field(default_factory=list)    # 未验证但可能成立的好
    confirmed_negatives: List[str] = field(default_factory=list)     # 已确认的坏
    key_uncertainties: List[str] = field(default_factory=list)       # 决定判断但未验证


@dataclass
class MaterialRequest:
    """材料请求清单"""
    priority: RiskLevel
    material: str                      # 具体材料名称
    purpose: str                       # 验证目的
    related_hypothesis: str = ""       # 关联假设


@dataclass
class RemainingUnknownV3:
    """待解决问题"""
    issue: str                         # 未解决问题
    why_blocking: str                  # 为什么阻碍判断
    how_to_resolve: str                # 如何解决
    priority: RiskLevel                # high / medium / low


@dataclass
class NextActionV3:
    """下一步行动"""
    action: str                        # 具体行动
    purpose: str                       # 目的
    who: str = "用户"                  # 谁来做
    priority: RiskLevel = RiskLevel.MEDIUM


@dataclass
class Step9OutputV3:
    """Step9 v3 完整输出（双层决策）"""
    overall_decision: OverallDecisionV3
    decision_breakdown: DecisionBreakdownV3 = field(default_factory=DecisionBreakdownV3)
    material_request_list: List[MaterialRequest] = field(default_factory=list)
    remaining_unknowns: List[RemainingUnknownV3] = field(default_factory=list)
    next_actions: List[NextActionV3] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    go_no_go_logic: str = ""          # 决策逻辑说明


# ============ Step9: 决策与行动（旧版 v2，保留兼容）============

class DecisionType(str, Enum):
    """核心决策类型（旧版）"""
    GO = "go"
    CAUTIOUS_GO = "cautious_go"
    HOLD = "hold"
    PASS = "pass"


@dataclass
class OverallDecision:
    """最终决策（旧版）"""
    decision: DecisionType
    confidence: ConfidenceLevel
    one_line_conclusion: str


@dataclass
class DecisionBreakdown:
    """决策分解（旧版）"""
    positives: List[str] = field(default_factory=list)
    negatives: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)


@dataclass
class ActionPlan:
    """行动计划项（旧版）"""
    priority: RiskLevel
    action: str
    reason: str
    linked_risk: str = ""


# ============ Step9: 决策与行动（旧版，保留兼容）============

@dataclass
class RemainingUnknown:
    issue: str
    why_blocking: str
    how_to_resolve: str
    priority: ImportanceLevel


@dataclass
class NextAction:
    action: str
    purpose: str
    who: str = "用户"
    priority: ImportanceLevel = ImportanceLevel.MEDIUM


@dataclass
class Step9Output:
    """Step9 输出（兼容旧版）"""
    # 新版 v3 字段
    overall_decision_v3: OverallDecisionV3 = None
    decision_breakdown_v3: DecisionBreakdownV3 = None
    material_request_list: List[MaterialRequest] = field(default_factory=list)
    remaining_unknowns_v3: List[RemainingUnknownV3] = field(default_factory=list)
    next_actions_v3: List[NextActionV3] = field(default_factory=list)
    key_risks_v3: List[str] = field(default_factory=list)
    go_no_go_logic_v3: str = ""
    # 旧版 v2 字段（兼容）
    overall_decision: OverallDecision = None
    decision_breakdown: DecisionBreakdown = None
    action_plan: List[ActionPlan] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    go_no_go_logic: str = ""
    # 最旧版字段（兼容）
    next_decision: dict = field(default_factory=dict)
    remaining_unknowns: List[RemainingUnknown] = field(default_factory=list)
    next_actions: List[NextAction] = field(default_factory=list)


# ============ 沉淀层 ============

@dataclass
class QuestionCandidate:
    question: str                       # 问题原文
    use_case: str                       # 使用场景
    why_effective: str                  # 为什么有效
    triggered_at: str = "Step7"         # 触发步骤
    trigger_reason: str = ""            # 触发原因


@dataclass
class IndustryInsightCandidate:
    industry: str                       # 行业
    insight: str                        # 认知内容
    core_question: str                  # 核心问题
    bucket_target: str                  # 目标桶（tech_barrier/commercialization/customer_value...）
    triggered_at: str = "Step7/8"      # 触发步骤
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    note: str = ""                      # 备注（需交叉验证等）


# ============ 对话历史 ============

@dataclass
class DialogueTurn:
    turn_id: int                        # 第几轮
    role: str                           # user / assistant
    content: str                        # 内容
    timestamp: str = ""                 # 时间戳


@dataclass
class UserProfileCandidate:
    dimension: str                      # 关注的维度（客户/技术/团队...）
    pattern: str                        # 模式描述（追问深度/容忍边界/决策风格...）
    evidence: str = ""                  # 证据片段
    triggered_at: str = ""               # 触发时间


# ============ 完整 2.0 输出 ============

@dataclass
class V2Output:
    """完整的 2.0 输出"""
    step6: Step6Output
    step7: Step7Output
    step8: Step8Output
    step9: Step9Output
    question_candidates: List[QuestionCandidate] = field(default_factory=list)
    industry_insight_candidates: List[IndustryInsightCandidate] = field(default_factory=list)
    user_profile_candidates: List[UserProfileCandidate] = field(default_factory=list)


# ============ 会议记录输入 ============

@dataclass
class MeetingInput:
    project_id: str
    content: str                         # 原始会议内容
    source: str = "text"                # text / txt / docx / doc
    dialogue_history: List[DialogueTurn] = field(default_factory=list)  # 对话记录


# ============ Step0: 投资人/基金画像 ============

class ProfileType(str, Enum):
    """画像类型"""
    USER = "user"
    FUND = "fund"


@dataclass
class HardConstraint:
    """硬约束"""
    key: str                       # 约束键
    description: str                # 约束描述
    priority: str = "high"         # high / medium / low
    examples: List[str] = field(default_factory=list)  # 符合的例子


@dataclass
class Preference:
    """偏好"""
    key: str                       # 偏好键
    description: str               # 偏好描述
    priority: str = "medium"       # high / medium / low
    weight: float = 0.2            # 权重


@dataclass
class Avoidance:
    """不偏好项"""
    key: str                       # 回避键
    description: str               # 回避描述
    priority: str = "medium"       # high / medium / low
    severity: str = "medium"       # critical / high / medium / low


@dataclass
class Step0ProfileOutput:
    """Step0 基金画像输出"""
    profile_id: str                # 画像ID
    profile_type: ProfileType      # 画像类型
    name: str                      # 画像名称
    description: str = ""          # 画像描述
    hard_constraints: List[HardConstraint] = field(default_factory=list)
    preferences: List[Preference] = field(default_factory=list)
    avoid: List[Avoidance] = field(default_factory=list)
    fit_questions: List[str] = field(default_factory=list)  # 用于反哺 Step7 的问题


# ============ Step10: Fit 判断 ============

class FitDecision(str, Enum):
    """Fit 决策"""
    FIT = "fit"                   # 高度匹配
    PARTIAL_FIT = "partial_fit"   # 部分匹配
    NOT_FIT = "not_fit"           # 不匹配


class FinalRecommendation(str, Enum):
    """最终建议"""
    CONTINUE = "continue"         # 继续推进
    REQUEST_MATERIALS = "request_materials"  # 补充材料
    PASS = "pass"                 # 放弃


@dataclass
class MatchedConstraint:
    """匹配的约束"""
    constraint: str                # 约束描述
    evidence: str                  # 证据
    strength: str = "medium"       # high / medium / low


@dataclass
class MismatchedConstraint:
    """不匹配的约束"""
    constraint: str                # 约束描述
    evidence: str                  # 证据
    severity: str = "medium"       # high / medium / low


@dataclass
class Compromise:
    """可妥协项"""
    preference: str               # 偏好项
    compromise_reason: str         # 妥协原因
    acceptable: bool = False       # 是否可接受


@dataclass
class CandidateProfileUpdate:
    """候选画像更新"""
    profile_id: str                # 画像ID
    candidate_rule: str           # 候选规则
    evidence: str                 # 证据
    should_review: bool = True     # 是否需要审核


@dataclass
class CandidateCaseRecord:
    """候选案例记录"""
    project_name: str             # 项目名称
    project_type: str = ""        # 项目类型
    project_judgement: str = ""   # 项目判断摘要
    fit_judgement: FitDecision = FitDecision.NOT_FIT  # Fit判断
    final_decision: FinalRecommendation = FinalRecommendation.PASS  # 最终决策
    fit_reason: List[str] = field(default_factory=list)  # Fit原因
    source_profile: str = ""      # 来源画像


@dataclass
class Step10Output:
    """Step10 Fit 判断输出"""
    fit_decision: FitDecision                    # fit / partial_fit / not_fit
    final_recommendation: FinalRecommendation    # continue / request_materials / pass
    fit_score: int = 50                          # 0-100
    matched_constraints: List[MatchedConstraint] = field(default_factory=list)
    mismatched_constraints: List[MismatchedConstraint] = field(default_factory=list)
    compromises: List[Compromise] = field(default_factory=list)
    reasoning: str = ""                          # 决策推理
    candidate_profile_updates: List[CandidateProfileUpdate] = field(default_factory=list)
    candidate_case_record: CandidateCaseRecord = None
