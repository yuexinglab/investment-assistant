# -*- coding: utf-8 -*-
"""
Step5 Schema - 决策收敛版本

基于用户方案：
- CoreJudgement：核心判断（一句话 + decision）
- reasons_to_meet / reasons_to_pass：决策理由（非优点/缺点罗列）
- key_risks：核心风险（来源 Step3B tensions / packaging）
- must_ask_questions：必问问题（必须来自 Step4 gaps）
- investment_logic：投资逻辑归因（primary / secondary / risk_type）
"""

from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field


class CoreJudgement(BaseModel):
    """一句话核心判断"""
    one_liner: str = Field(
        description="一句话判断，必须包含公司本质 + 当前最大问题"
    )
    essence: str = Field(
        description="公司本质（是什么类型的公司）"
    )
    decision: Literal["meet", "pass", "maybe"] = Field(
        description="决策结论：meet=值得见面 / pass=核心逻辑不成立 / maybe=方向可以但信息不足"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="判断信心度"
    )
    core_reason: str = Field(
        description="做这个决策的核心原因（一句话）"
    )


class ReasonItem(BaseModel):
    """决策理由"""
    point: str = Field(description="理由点（要具体）")
    why_it_matters: str = Field(description="为什么影响决策")


class RiskItem(BaseModel):
    """核心风险"""
    risk: str = Field(description="风险描述（必须具体到本项目）")
    severity: Literal["high", "medium", "low"] = Field(description="风险等级")
    why_it_matters: str = Field(description="为什么这个风险重要")


class QuestionItem(BaseModel):
    """必问问题"""
    question: str = Field(description="问题本身")
    purpose: str = Field(description="这个问题是为了验证什么")


class InvestmentLogic(BaseModel):
    """投资逻辑归因"""
    primary_type: str = Field(description="公司最核心的投资逻辑，如 制造/项目制/运营/AI平台")
    secondary_types: List[str] = Field(description="次要投资逻辑")
    risk_type: List[str] = Field(description="主要风险类型，如 重资产/非标项目/政策驱动")


class FundFit(BaseModel):
    """项目与当前基金/Profile的匹配度判断"""
    fit_summary: str = Field(description="一句话说明该项目与当前基金/Profile的匹配度")
    matched_points: List[str] = Field(description="与当前基金/Profile匹配的点")
    mismatch_or_uncertain_points: List[str] = Field(description="不匹配或尚未验证的点")
    required_verifications: List[str] = Field(description="下一轮必须验证的基金匹配问题")


class Step5Output(BaseModel):
    """
    Step5 决策收敛输出

    核心原则：
    - 不是分析过程，而是决策收敛
    - 所有理由必须影响"是否继续推进"这个决策
    - must_ask_questions 必须来自 Step4 gaps，不允许重新发明
    """

    core_judgement: CoreJudgement = Field(
        description="一句话核心判断"
    )

    reasons_to_meet: List[ReasonItem] = Field(
        description="为什么值得继续看（必须影响决策，不是一般优点）"
    )

    reasons_to_pass: List[ReasonItem] = Field(
        description="为什么不投（必须影响决策，不是一般缺点）"
    )

    key_risks: List[RiskItem] = Field(
        description="核心风险，来源优先级：Step3B tensions > Step3B packaging > Step3 risk_buckets"
    )

    fund_fit: FundFit = Field(
        description="项目与当前基金/Profile的匹配度判断"
    )

    must_ask_questions: List[QuestionItem] = Field(
        description="必问问题，必须来自 Step4 gaps（含 red_flag_question），不允许重新发明"
    )

    investment_logic: InvestmentLogic = Field(
        description="投资逻辑归因"
    )

    def to_markdown(self) -> str:
        """转换为可读 Markdown"""
        lines = []
        j = self.core_judgement

        # 标题
        lines.append("# 会前初步判断\n")

        # 1. 我现在对公司的定性
        lines.append("## 1. 我现在对公司的定性\n")
        lines.append(f"**一句话判断**：{j.one_liner}\n")
        lines.append(f"**公司本质**：{j.essence}\n")
        lines.append(f"**决策**：`{j.decision}`（信心度：{j.confidence}）\n")
        lines.append(f"**核心原因**：{j.core_reason}\n")

        # 2. 为什么还值得继续看
        lines.append("\n## 2. 为什么还值得继续看（优势 & 相对确定性）\n")
        for i, r in enumerate(self.reasons_to_meet, 1):
            lines.append(f"{i}. **{r.point}**")
            lines.append(f"   → {r.why_it_matters}\n")

        # 3. 我最担心的几个问题
        lines.append("\n## 3. 我最担心的几个问题（核心不确定性）\n")
        for i, r in enumerate(self.reasons_to_pass, 1):
            lines.append(f"{i}. **{r.point}**")
            lines.append(f"   → {r.why_it_matters}\n")

        # 3 后半：主要风险（合并 key_risks）
        lines.append("\n### 主要风险\n")
        sev_emoji = {"high": "[P1]", "medium": "[P2]", "low": "[P3]"}
        for r in self.key_risks:
            lines.append(f"- {sev_emoji.get(r.severity, '')} **{r.risk}**")
            lines.append(f"  → {r.why_it_matters}\n")

        # 4. 和基金匹配度怎么看
        lines.append("\n## 4. 和基金匹配度怎么看\n")
        f = self.fund_fit
        lines.append(f"**匹配结论**：{f.fit_summary}\n")
        if f.matched_points:
            lines.append("**匹配点**：")
            for p in f.matched_points:
                lines.append(f"- {p}")
            lines.append("")
        if f.mismatch_or_uncertain_points:
            lines.append("**不匹配/未验证点**：")
            for p in f.mismatch_or_uncertain_points:
                lines.append(f"- {p}")
            lines.append("")
        if f.required_verifications:
            lines.append("**下一轮必须验证**：")
            for v in f.required_verifications:
                lines.append(f"- {v}")
            lines.append("")

        # 5. 下一轮必须验证的问题
        lines.append("\n## 5. 下一轮必须验证的问题\n")
        for i, q in enumerate(self.must_ask_questions, 1):
            lines.append(f"{i}. {q.question}")
            lines.append(f"   目的：{q.purpose}\n")

        # 6. 当前推进建议
        lines.append("\n## 6. 当前推进建议\n")
        lines.append(f"**决策**：`{j.decision}`（信心度：{j.confidence}）\n")
        lines.append(f"**核心原因**：{j.core_reason}\n")
        decision_explain = {
            "meet": "建议继续约第一轮交流",
            "maybe": "可以谨慎推进，但必须围绕关键问题验证",
            "pass": "当前不建议推进",
        }
        lines.append(f"**中文解释**：{decision_explain.get(j.decision, j.decision)}\n")

        return "\n".join(lines)
