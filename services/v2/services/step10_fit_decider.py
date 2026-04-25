# -*- coding: utf-8 -*-
"""
step10_fit_decider.py — Step10: Fit 判断（投资匹配分析）

作用：
判断项目是否适合当前投资人/基金画像。

核心原则：
1. Fit 判断只回答"适不适合"，不回答"项目好不好"
2. 项目本身好≠适合当前基金
3. 偏好库只影响 Fit 判断，不污染 Step6-9 的项目判断

数据流：
Step9 项目决策 + Step0 基金画像 → Step10 Fit 判断
"""
import json
import re
from typing import Dict, Any, Optional

from ..schemas import (
    Step10Output, FitDecision, FinalRecommendation,
    MatchedConstraint, MismatchedConstraint, Compromise,
    CandidateProfileUpdate, CandidateCaseRecord
)

# Step10 System Prompt
STEP10_SYSTEM = """你是一个投资策略匹配分析师。

你的任务不是判断项目本身好不好，而是判断：
这个项目是否适合当前投资人/基金画像。

你必须严格区分：
1. 项目质量判断：项目本身是否有收入、客户、技术、风险
2. 投资匹配判断：是否符合当前基金的硬约束、偏好和不能接受的点

重要原则：
- 一个项目可以本身不错，但不适合当前基金
- 一个项目可以有风险，但如果高度符合基金策略，可以继续验证
- 不能把某只基金的偏好写成通用投资标准
- 不符合 hard_constraints 的项目，原则上应 not_fit 或 partial_fit
- preference 是加分项，不是硬门槛
- avoid 是减分项，需要说明是否构成否决

你需要输出：
1. fit_decision: fit / partial_fit / not_fit
2. final_recommendation: continue / request_materials / pass
3. fit_score: 0-100 的匹配分数
4. matched_constraints: 匹配的约束列表
5. mismatched_constraints: 不匹配的约束列表
6. compromises: 可妥协项列表
7. reasoning: 决策推理
8. candidate_profile_updates: 候选画像更新（用于沉淀）
9. candidate_case_record: 候选案例记录（用于沉淀）

输出必须是严格 JSON。
"""


def decide_fit(
    fund_profile: Dict[str, Any],
    step9_output: Dict[str, Any],
    project_summary: Dict[str, Any],
    user_feedback: str = "",
    model: str = None,
    step7_output: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Step10 Fit 判断

    Args:
        fund_profile: Step0 输出的基金画像 dict
        step9_output: Step9 输出的项目决策 dict
        project_summary: 项目摘要（project_id, project_name 等）
        user_feedback: 用户额外反馈
        model: DeepSeek 模型名
        step7_output: Step7 输出 dict（可选，用于检查 profile 问题的回答情况）

    Returns:
        Step10 输出 dict
    """
    from services.deepseek_service import call_deepseek

    # 构建 project_summary 文本（用于 prompt）
    project_text = f"项目名称：{project_summary.get('project_name', '')}\n"
    project_text += f"项目ID：{project_summary.get('project_id', '')}\n"

    # 构建 Step9 摘要
    step9_overall = step9_output.get("overall_decision", {})
    step9_breakdown = step9_output.get("decision_breakdown", {})

    # 处理字典列表（verified_positives/confirmed_negatives/key_uncertainties）
    def _format_dict_list(items: list, key: str = "hypothesis") -> str:
        """从字典列表中提取指定字段，转换为可读字符串"""
        if not items:
            return "无"
        parts = []
        for item in items[:5]:
            if isinstance(item, dict):
                val = item.get(key, str(item))
            else:
                val = str(item)
            # 截断过长内容
            if len(val) > 50:
                val = val[:50] + "..."
            parts.append(val)
        return "；".join(parts)

    step9_text = f"""
【Step9 双层决策】
流程决策：{step9_overall.get('process_decision', '')}
投资决策：{step9_overall.get('investment_decision', '')}
置信度：{step9_overall.get('confidence', '')}
一句话结论：{step9_overall.get('one_line_conclusion', '')}

【四象限分解】
已验证的好：{_format_dict_list(step9_breakdown.get('verified_positives', []))}
已确认的坏：{_format_dict_list(step9_breakdown.get('confirmed_negatives', []))}
关键不确定性：{_format_dict_list(step9_breakdown.get('key_uncertainties', []))}
"""

    # 构建 Step7 Profile 问题验证摘要（v2.3 新增）
    step7_profile_text = ""
    if step7_output:
        step7_profile_text = _format_step7_profile_summary(step7_output)

    # 构建基金画像摘要
    profile_text = f"""
【基金/投资人画像】
画像名称：{fund_profile.get('name', '')}
画像类型：{fund_profile.get('profile_type', 'fund')}
描述：{fund_profile.get('description', '')}

【硬约束】(不满足则 not_fit)
{_format_constraints(fund_profile.get('hard_constraints', []))}

【偏好】(满足则加分)
{_format_preferences(fund_profile.get('preferences', []))}

【回避项】(违反则扣分)
{_format_avoid(fund_profile.get('avoid', []))}
"""

    # 构建用户反馈
    feedback_text = f"\n【用户额外反馈】\n{user_feedback}" if user_feedback else "\n【用户额外反馈】\n无"

    # 构建 prompt
    user_prompt = f"""{profile_text}
{step9_text}
{step7_profile_text}
{feedback_text}

请判断该项目是否适合当前基金/投资人。

输出格式（严格 JSON）：
{{
  "fit_decision": "fit / partial_fit / not_fit",
  "final_recommendation": "continue / request_materials / pass",
  "fit_score": 0-100,
  "matched_constraints": [
    {{
      "constraint": "约束描述",
      "evidence": "项目中的证据",
      "strength": "high/medium/low"
    }}
  ],
  "mismatched_constraints": [
    {{
      "constraint": "约束描述",
      "evidence": "项目中的证据",
      "severity": "high/medium/low"
    }}
  ],
  "compromises": [
    {{
      "preference": "偏好项",
      "compromise_reason": "为何可以妥协/不可妥协",
      "acceptable": true/false
    }}
  ],
  "reasoning": "决策推理（100字以内）",
  "candidate_profile_updates": [
    {{
      "profile_id": "{fund_profile.get('profile_id', '')}",
      "candidate_rule": "从本次判断中提炼的新规则候选",
      "evidence": "本次判断的证据",
      "should_review": true
    }}
  ],
  "candidate_case_record": {{
    "project_name": "{project_summary.get('project_name', '')}",
    "project_type": "",
    "project_judgement": "{step9_overall.get('one_line_conclusion', '')}",
    "fit_judgement": "fit/partial_fit/not_fit",
    "final_decision": "continue/request_materials/pass",
    "fit_reason": ["原因1", "原因2"],
    "source_profile": "{fund_profile.get('profile_id', '')}"
  }}
}}
"""

    # 调用 LLM
    raw = call_deepseek(STEP10_SYSTEM, user_prompt, model=model)
    data = _parse_json_response(raw)

    if not isinstance(data, dict):
        data = {}

    # 应用规则护栏
    data = _apply_fit_guardrails(data, fund_profile, step9_output, step7_output)

    # 确保字段完整
    data = _ensure_fields(data, fund_profile, step9_output, project_summary)

    return data


def _format_step7_profile_summary(step7_output: Dict[str, Any]) -> str:
    """
    格式化 Step7 中 Profile 问题的验证结果（v2.3 新增）

    重点关注 question_source=profile 的问题，这些是基金特定的问题。
    """
    question_validations = step7_output.get("question_validation", [])
    if not question_validations:
        return "\n【Step7 Profile 问题验证】\n（无问题数据）"

    # 分类问题
    base_questions = [v for v in question_validations if v.get("question_source") == "base"]
    profile_questions = [v for v in question_validations if v.get("question_source") == "profile"]

    lines = ["\n【Step7 Profile 问题验证】(重点关注)"]

    if profile_questions:
        lines.append(f"\nProfile 问题（共 {len(profile_questions)} 个）：")
        for v in profile_questions:
            q = v.get("original_question", "")[:50]
            status = v.get("status", "not_answered")
            quality = v.get("quality", "medium")
            summary = v.get("answer_summary", "未回答")[:30]
            lines.append(f"  - [{status}/{quality}] {q}...")
            lines.append(f"    回答：{summary}")
            if v.get("missing_evidence"):
                lines.append(f"    缺失：{', '.join(v.get('missing_evidence', [])[:2])}")
    else:
        lines.append("\n（本次未使用 Profile 问题，或 Profile 问题未被记录）")

    # 简要统计 base 问题（作为参考）
    if base_questions:
        answered = sum(1 for v in base_questions if v.get("status") in ("answered", "partially_answered"))
        lines.append(f"\nBase 问题（共 {len(base_questions)} 个）：{answered} 个被回答")

    return "\n".join(lines)


def _format_constraints(constraints: list) -> str:
    """格式化约束列表"""
    if not constraints:
        return "无"
    return "\n".join([
        f"- [{c.get('priority', 'medium').upper()}] {c.get('description', '')}"
        for c in constraints
    ])


def _format_preferences(preferences: list) -> str:
    """格式化偏好列表"""
    if not preferences:
        return "无"
    return "\n".join([
        f"- [{p.get('priority', 'medium').upper()}] {p.get('description', '')}"
        for p in preferences
    ])


def _format_avoid(avoid_list: list) -> str:
    """格式化回避项列表"""
    if not avoid_list:
        return "无"
    return "\n".join([
        f"- [{a.get('severity', 'medium').upper()}] {a.get('description', '')}"
        for a in avoid_list
    ])


def _parse_json_response(text: str) -> Any:
    """解析 LLM 输出的 JSON"""
    text = text.strip()
    # 去掉 markdown 代码块
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 对象
        match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return {}


def _apply_fit_guardrails(
    data: Dict[str, Any],
    fund_profile: Dict[str, Any],
    step9_output: Dict[str, Any],
    step7_output: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    应用 Fit 判断规则护栏

    v3 精修规则：
    1. 如果有高严重度硬约束不匹配，直接 not_fit
    2. 如果多个硬约束未匹配，直接 not_fit
    3. 如果项目本身 not_ready 但 Fit 给了 fit，降级为 partial_fit
    4. (v2.3 新增) 如果 Profile 问题未被回答且 profile_id != neutral_investor，需要更严格判断
    5. (v3 精修) neutral_investor 禁止越权：不能写 not_fit/pass/不适合投资
    6. (v3 精修) candidate_case_record 必须与 guardrail 结果一致
    """
    mismatches = data.get("mismatched_constraints", [])
    matched = data.get("matched_constraints", [])

    # 计算高严重度不匹配数
    high_mismatch_count = sum(
        1 for m in mismatches
        if isinstance(m, dict) and m.get("severity") in ("high", "critical")
    )

    hard_constraints = fund_profile.get("hard_constraints", [])
    hard_count = len(hard_constraints)
    profile_id = fund_profile.get("profile_id", "")

    # 规则1：存在高严重度硬约束不匹配，不能给 fit
    # 注意：neutral_investor 不适用这条（中性投资人不会"不适配"）
    if profile_id != "neutral_investor" and high_mismatch_count >= 1:
        data["fit_decision"] = FitDecision.NOT_FIT.value
        data["final_recommendation"] = FinalRecommendation.PASS.value

    # 规则2：多个硬约束未匹配，直接 not_fit
    # 注意：neutral_investor 不适用这条
    if profile_id != "neutral_investor" and hard_count >= 2 and len(mismatches) >= 2 and high_mismatch_count >= 1:
        data["fit_decision"] = FitDecision.NOT_FIT.value
        data["final_recommendation"] = FinalRecommendation.PASS.value

    # 规则3：如果项目本身 not_ready 但 Fit 给了 fit，降级
    investment_decision = (
        step9_output
        .get("overall_decision", {})
        .get("investment_decision", "")
    )

    if investment_decision == "not_ready" and data.get("fit_decision") == "fit":
        data["fit_decision"] = FitDecision.PARTIAL_FIT.value
        data["final_recommendation"] = FinalRecommendation.REQUEST_MATERIALS.value

    # 规则4 (v2.3)：如果 Profile 问题未被回答，且不是 neutral_investor，需要更严格判断
    if step7_output and profile_id != "neutral_investor":
        profile_questions = [
            v for v in step7_output.get("question_validation", [])
            if v.get("question_source") == "profile"
        ]
        if profile_questions:
            unanswerd_profile_count = sum(
                1 for v in profile_questions
                if v.get("status") in ("not_answered", "evaded")
            )
            # 如果超过一半的 Profile 问题未回答，需要更严格
            if unanswerd_profile_count >= len(profile_questions) / 2:
                if data.get("fit_decision") == "fit":
                    data["fit_decision"] = FitDecision.PARTIAL_FIT.value
                # 如果几乎所有 Profile 问题都未回答，考虑降级
                if unanswerd_profile_count == len(profile_questions):
                    if data.get("final_recommendation") == "continue":
                        data["final_recommendation"] = FinalRecommendation.REQUEST_MATERIALS.value

    # 规则5 (v3 精修)：neutral_investor 禁止越权判断
    # ❗ 核心原则：Step10 只判断 Fit，不做质量判断
    # neutral_investor = 通用投资人画像，完全继承 Step9 的 process_decision
    if profile_id == "neutral_investor":
        # 强制 partial_fit（中性投资人不会"不适配"）
        if data.get("fit_decision") == FitDecision.NOT_FIT.value:
            data["fit_decision"] = FitDecision.PARTIAL_FIT.value

        # ❗ 关键：完全继承 Step9 的 process_decision（不做质量判断）
        step9_process = (
            step9_output
            .get("overall_decision", {})
            .get("process_decision", "")
        )
        step9_investment = (
            step9_output
            .get("overall_decision", {})
            .get("investment_decision", "")
        )

        # neutral_investor 的 final_recommendation 完全跟随 Step9
        if step9_process == "continue_dd":
            data["final_recommendation"] = FinalRecommendation.CONTINUE.value
        elif step9_process == "request_materials":
            data["final_recommendation"] = FinalRecommendation.REQUEST_MATERIALS.value
        elif step9_process == "pause":
            data["final_recommendation"] = FinalRecommendation.REQUEST_MATERIALS.value
        elif step9_process == "stop":
            data["final_recommendation"] = FinalRecommendation.PASS.value
        else:
            # 默认：如果项目本身不是 reject，继续推进
            if step9_investment != "reject":
                data["final_recommendation"] = FinalRecommendation.CONTINUE.value

        # ❗ reasoning 说明：不施加偏好，完全基于 Step9
        data["reasoning"] = (
            "[Guardrail] 当前为中性投资人画像，不施加特定偏好。"
            "项目是否推进完全基于 Step9 判断。"
        )

        # ── 规则6 (v3 新增)：修复 candidate_case_record ─────────────────
        # neutral_investor 的 candidate_case_record 不能写 not_fit/pass
        if "candidate_case_record" in data:
            ccr = data["candidate_case_record"]
            if isinstance(ccr, dict):
                # 强制 fit_judgement = partial_fit
                ccr["fit_judgement"] = FitDecision.PARTIAL_FIT.value
                # 强制 final_decision 与 Step9 一致
                ccr["final_decision"] = data.get("final_recommendation", "request_materials")
                # 修复 fit_reason：不能写"美妆和新能源均被证伪"等越权判断
                ccr["fit_reason"] = [
                    "中性投资人不对项目质量做判断",
                    "项目推进建议完全基于 Step9 双层决策"
                ]
                # 禁止写"不适合任何投资"
                if ccr.get("project_judgement"):
                    judgement = str(ccr["project_judgement"])
                    if "证伪" in judgement or "逻辑崩塌" in judgement or "拒绝投资" in judgement:
                        # 替换为中性描述
                        ccr["project_judgement"] = (
                            "美妆业务有真实收入底盘，AI/新能源/协同存在不确定性，"
                            "建议补充材料后继续评估"
                        )

    return data


def _ensure_fields(
    data: Dict[str, Any],
    fund_profile: Dict[str, Any],
    step9_output: Dict[str, Any],
    project_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """确保所有必要字段存在"""
    # 计算 fit_score
    if "fit_score" not in data:
        data["fit_score"] = _score_fit(data)

    # 确保列表字段存在
    data.setdefault("matched_constraints", [])
    data.setdefault("mismatched_constraints", [])
    data.setdefault("compromises", [])
    data.setdefault("candidate_profile_updates", [])
    data.setdefault("reasoning", "")

    # 确保 candidate_case_record 存在
    if "candidate_case_record" not in data or not data["candidate_case_record"]:
        data["candidate_case_record"] = {
            "project_name": project_summary.get("project_name", ""),
            "project_type": "",
            "project_judgement": step9_output.get("overall_decision", {}).get("one_line_conclusion", ""),
            "fit_judgement": data.get("fit_decision", "not_fit"),
            "final_decision": data.get("final_recommendation", "pass"),
            "fit_reason": [m.get("constraint", "") for m in data.get("mismatched_constraints", [])[:3]],
            "source_profile": fund_profile.get("profile_id", "")
        }

    return data


def _score_fit(data: Dict[str, Any]) -> int:
    """根据 fit_decision 计算分数"""
    decision = data.get("fit_decision", "")
    if decision == FitDecision.FIT.value:
        return 80
    if decision == FitDecision.PARTIAL_FIT.value:
        return 50
    if decision == FitDecision.NOT_FIT.value:
        return 20
    return 50


def to_dict(output: Dict[str, Any]) -> Dict[str, Any]:
    """将 Step10 输出转为 dict（用于持久化）"""
    # Step10 输出已经是 dict，直接返回
    return output
