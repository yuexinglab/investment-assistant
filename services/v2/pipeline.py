"""
pipeline.py — 2.0 真正串行的执行链

核心思想：每个模块的真实输出 → 传给下一个模块

执行顺序：
1. extract_new_info (Extractor)
2. analyze_field_deltas (Delta Engine)
3. judge_answers (QA Judge - 单题判断)
4. summarize_qa (QA汇总)
5. update_risks (Risk Update)
6. update_decision (Decision Updater)
7. alpha_insights (Alpha Layer)
"""

import json
from typing import List, Dict, Any, Optional
from .schemas import (
    V1StructuredOutput, V2PipelineResult,
    DeltaResult, QAResult, QASummary,
    RiskUpdate, RiskUpdateSummary,
    DecisionUpdate, AlphaSignal, FieldState, Question, Risk,
    FieldStatus, QAJudgment, ValueAssessment,
    RiskImpact, DecisionImpact,
    RiskStatus, Recommendation, RiskSignal
)
from .prompts import (
    build_extractor_prompt, build_delta_prompt,
    build_qa_single_prompt, build_qa_summary_prompt,
    build_risk_update_prompt, build_decision_updater_prompt,
    build_alpha_layer_prompt, build_v1_structured_prompt
)
from services.deepseek_service import call_deepseek


def _parse_json_response(response: str) -> dict:
    """解析JSON响应，处理可能的markdown代码块"""
    # 去掉可能的markdown代码块
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]
    
    # 尝试解析JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        # 尝试提取JSON部分
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except:
                pass
        return {}


def _build_v1_structured(v1_report: str, field_template: str = "") -> V1StructuredOutput:
    """从v1报告提取结构化数据（真正调用LLM）"""
    prompt = build_v1_structured_prompt(v1_report, field_template)
    
    try:
        # 调用 LLM 做结构化
        response = call_deepseek(
            system_prompt="你是一个分析结果结构化器。必须严格输出JSON格式。",
            user_prompt=prompt
        )
        
        result = _parse_json_response(response)
        
        if result and "summary" in result:
            # 从 LLM 输出重建 V1StructuredOutput
            output = V1StructuredOutput()
            output.summary = result.get("summary", {})
            output.field_template = field_template
            
            # 解析 field_states
            output.field_states = {}
            for fs_data in result.get("field_states", []):
                field_id = fs_data.get("field_id", f"field_{len(output.field_states)}")
                output.field_states[field_id] = FieldState(
                    field_id=field_id,
                    field_name=fs_data.get("field_name", field_id),
                    status=FieldStatus(fs_data.get("status", "unknown")),
                    value=fs_data.get("value", ""),
                    evidence=fs_data.get("evidence", ""),
                    confidence=fs_data.get("confidence", 0.5)
                )
            
            # 解析 questions
            output.questions = [
                Question(
                    qid=q.get("qid", f"q{i}"),
                    question=q.get("question", ""),
                    why=q.get("why", ""),
                    priority=q.get("priority", "medium"),
                    topic=q.get("topic", "")
                )
                for i, q in enumerate(result.get("questions", []))
            ]
            
            # 解析 risks
            output.risks = [
                Risk(
                    risk_id=r.get("risk_id", f"risk_{i}"),
                    name=r.get("name", ""),
                    severity=r.get("severity", "medium"),
                    reason=r.get("reason", ""),
                    evidence=r.get("evidence", [])
                )
                for i, r in enumerate(result.get("risks", []))
            ]
            
            # 解析 conclusion
            output.conclusion = result.get("conclusion", {
                "stance": "继续跟进",
                "reason": "",
                "must_verify": []
            })
            
            return output
    except Exception as e:
        print(f"[Pipeline] _build_v1_structured LLM调用失败: {e}，回退到启发式解析")
    
    # 回退：使用启发式解析（仅作为兜底）
    output = V1StructuredOutput()
    output.summary = {
        "one_liner": v1_report[:200] + "..." if len(v1_report) > 200 else v1_report,
        "business_model": "",
        "revenue_source": "",
        "stage": "",
        "core_capabilities": [],
        "initial_risk_scan": []
    }
    output.questions = _extract_questions_from_text(v1_report)
    output.risks = _extract_risks_from_text(v1_report)
    output.conclusion = {
        "stance": _extract_stance(v1_report),
        "reason": "",
        "must_verify": []
    }
    output.field_template = field_template
    return output


def _field_state_to_dict(fs: FieldState) -> dict:
    """将 FieldState 转为 dict 供 prompt 使用"""
    return {
        "field_id": fs.field_id,
        "field_name": fs.field_name,
        "status": fs.status.value if hasattr(fs.status, 'value') else str(fs.status),
        "value": fs.value,
        "evidence": fs.evidence,
        "confidence": fs.confidence
    }


def _question_to_dict(q: Question) -> dict:
    """将 Question 转为 dict"""
    return {
        "qid": q.qid,
        "question": q.question,
        "why": q.why,
        "priority": q.priority,
        "topic": q.topic
    }


def _risk_to_dict(r: Risk) -> dict:
    """将 Risk 转为 dict"""
    return {
        "risk_id": r.risk_id,
        "name": r.name,
        "severity": r.severity,
        "reason": r.reason,
        "evidence": r.evidence
    }


def _delta_to_dict(d: DeltaResult) -> dict:
    """将 DeltaResult 转为 dict"""
    return {
        "field_id": d.field_id,
        "field_name": d.field_name,
        "old_status": d.old_status.value if hasattr(d.old_status, 'value') else d.old_status,
        "new_status": d.new_status.value if hasattr(d.new_status, 'value') else d.new_status,
        "change_summary": d.change_summary,
        "value_assessment": d.value_assessment.value if hasattr(d.value_assessment, 'value') else d.value_assessment,
        "impact_on_risk": d.impact_on_risk.value if hasattr(d.impact_on_risk, 'value') else d.impact_on_risk,
        "impact_on_decision": d.impact_on_decision.value if hasattr(d.impact_on_decision, 'value') else d.impact_on_decision,
    }


def _extract_questions_from_text(text: str) -> List:
    """从文本中提取问题"""
    questions = []
    if "问题" in text or "追问" in text:
        # 简单的正则匹配
        import re
        q_matches = re.findall(r'[\d]+\.\s*["""](.+?)["""]', text)
        for i, q in enumerate(q_matches[:10]):
            questions.append({
                "qid": f"q{i+1}",
                "question": q.strip(),
                "why": "",
                "priority": "medium",
                "topic": ""
            })
    return questions


def _extract_risks_from_text(text: str) -> List:
    """从文本中提取风险"""
    risks = []
    if "风险" in text:
        import re
        # 简单匹配风险相关段落
        risk_keywords = ["风险", "隐患", "担忧", "问题"]
        for keyword in risk_keywords:
            if keyword in text:
                idx = text.find(keyword)
                snippet = text[max(0, idx-50):min(len(text), idx+100)]
                if len(snippet) > 20:
                    risks.append({
                        "risk_id": f"auto_risk_{len(risks)+1}",
                        "name": snippet[:30],
                        "severity": "medium",
                        "reason": snippet,
                        "evidence": []
                    })
    return risks


def _extract_stance(text: str) -> str:
    """从文本中提取立场"""
    positive_words = ["推进", "建议投资", "看好", "值得关注"]
    negative_words = ["暂缓", "不建议", "风险大", "观望"]
    
    for word in positive_words:
        if word in text:
            return "建议推进"
    for word in negative_words:
        if word in text:
            return "暂不推进"
    return "继续跟进"


def run_v2_pipeline(v1_data: Dict, meeting_text: str) -> V2PipelineResult:
    """
    2.0 Pipeline 真正串行执行
    
    :param v1_data: 1.0结构化输出 (dict格式)
    :param meeting_text: 会议纪要文本
    :return: V2PipelineResult 结构化结果
    """
    import traceback
    
    print("[Pipeline] 开始执行2.0流程...")
    
    try:
        # 转换为V1StructuredOutput
        if isinstance(v1_data, dict):
            v1_structured = V1StructuredOutput.from_dict(v1_data) if "field_states" in v1_data else _build_v1_structured(
                v1_data.get("final_report", v1_data.get("role_c", "")),
                v1_data.get("field_template", "")
            )
        else:
            v1_structured = _build_v1_structured(str(v1_data))
        
        print(f"[Pipeline] V1结构化完成: {len(v1_structured.questions)}个问题, {len(v1_structured.risks)}个风险")
        
        # ===== Step 1: Extractor =====
        print("[Pipeline] Step1: 提取新增信息...")
        new_info = _run_extractor(meeting_text, v1_structured.summary.get("one_liner", ""))
        print(f"[Pipeline] Step1完成: 提取到{len(new_info)}条新信息")
        
        # ===== Step 2: Delta Engine =====
        print("[Pipeline] Step2: 分析字段变化...")
        deltas, delta_summary = _run_delta(
            [_field_state_to_dict(fs) for fs in v1_structured.field_states.values()],
            new_info
        )
        print(f"[Pipeline] Step2完成: {len(deltas)}个字段变化")
        
        # ===== Step 3: QA Judge (逐题判断) =====
        print("[Pipeline] Step3: 逐题判断回答质量...")
        qa_results = _run_qa_judge(v1_structured.questions, meeting_text)
        print(f"[Pipeline] Step3完成: 判断了{len(qa_results)}个问题")
        
        # ===== Step 4: QA 汇总 =====
        print("[Pipeline] Step4: 汇总QA结果...")
        qa_summary = _run_qa_summary(qa_results)
        
        # ===== Step 5: Risk Update =====
        print("[Pipeline] Step5: 更新风险状态...")
        risk_updates, risk_summary = _run_risk_update(
            v1_structured.risks,
            deltas,
            qa_results
        )
        print(f"[Pipeline] Step5完成: 更新了{len(risk_updates)}个风险")
        
        # ===== Step 6: Decision Updater =====
        print("[Pipeline] Step6: 更新投资判断...")
        decision = _run_decision_updater(
            v1_structured.conclusion,
            risk_summary,
            qa_summary,
            new_info,
            [d for d in deltas if d.value_assessment == ValueAssessment.HIGH]
        )
        print(f"[Pipeline] Step6完成: {decision.recommendation}")
        
        # ===== Step 7: Alpha Layer =====
        print("[Pipeline] Step7: 输出直觉信号...")
        alpha = _run_alpha_layer(meeting_text, qa_results, new_info)
        print(f"[Pipeline] Step7完成: 风险信号={alpha.risk_signal}")
        
        print("[Pipeline] 2.0流程完成！")
        
        # 组装结果
        return V2PipelineResult(
            new_info=new_info,
            deltas=deltas,
            delta_summary=delta_summary,
            qa_results=qa_results,
            qa_summary=qa_summary,
            risk_updates=risk_updates,
            risk_summary=risk_summary,
            decision=decision,
            alpha=alpha
        )
    except Exception as e:
        print(f"[Pipeline] 发生错误: {e}")
        traceback.print_exc()
        raise


def _run_extractor(meeting_text: str, v1_summary: str) -> List[Dict]:
    """执行Extractor"""
    prompt = build_extractor_prompt(meeting_text, v1_summary)
    response = call_deepseek(
        system_prompt="你是一个专业的信息提取器。",
        user_prompt=prompt
    )
    
    result = _parse_json_response(response)
    return result.get("new_info", [])


def _run_delta(field_states: List[Dict], new_info: List[Dict]) -> tuple:
    """执行Delta Engine"""
    prompt = build_delta_prompt(field_states, new_info)
    response = call_deepseek(
        system_prompt="你是一个变化分析引擎。",
        user_prompt=prompt
    )
    
    result = _parse_json_response(response)
    
    # 解析deltas
    deltas = []
    for d in result.get("deltas", []):
        deltas.append(DeltaResult(
            field_id=d.get("field_id", ""),
            field_name=d.get("field_name", ""),
            old_status=FieldStatus(d.get("old_status", "unknown")),
            new_status=FieldStatus(d.get("new_status", "unknown")),
            change_summary=d.get("change_summary", ""),
            value_assessment=ValueAssessment(d.get("value_assessment", "low")),
            impact_on_risk=RiskImpact(d.get("impact_on_risk", "no_relief")),
            impact_on_decision=DecisionImpact(d.get("impact_on_decision", "no_change"))
        ))
    
    return deltas, result.get("delta_summary", "")


def _run_qa_judge(questions: List, meeting_text: str) -> List[QAResult]:
    """执行QA Judge (逐题判断)"""
    if not questions:
        # 如果没有结构化问题，从文本中推断
        return []
    
    results = []
    for q in questions[:10]:  # 限制最多10个问题
        # 转换为dict
        if isinstance(q, Question):
            q_dict = _question_to_dict(q)
        elif isinstance(q, dict):
            q_dict = q
        else:
            q_dict = {"qid": "unknown", "question": str(q), "why": "", "priority": "medium", "topic": ""}
        prompt = build_qa_single_prompt(q_dict, meeting_text)
        
        response = call_deepseek(
            system_prompt="你是回答质量判官。",
            user_prompt=prompt
        )
        
        result = _parse_json_response(response)
        if result:
            results.append(QAResult(
                qid=result.get("qid", q_dict.get("qid", "unknown")),
                question=result.get("question", q_dict.get("question", "")),
                answer_summary=result.get("answer_summary", ""),
                judgment=QAJudgment(result.get("judgment", "fuzzy")),
                reason=result.get("reason", ""),
                evidence=result.get("evidence", "")
            ))
    
    return results


def _run_qa_summary(qa_results: List[QAResult]) -> QASummary:
    """执行QA汇总"""
    if not qa_results:
        return QASummary(
            total=0, effective=0, fuzzy=0, evasive=0,
            high_frequency_theme=[], one_line_signal="无问题可评估"
        )
    
    # 统计
    effective = sum(1 for r in qa_results if r.judgment == QAJudgment.EFFECTIVE)
    fuzzy = sum(1 for r in qa_results if r.judgment == QAJudgment.FUZZY)
    evasive = sum(1 for r in qa_results if r.judgment == QAJudgment.EVASIVE)
    
    # 找高频回避主题
    evasive_questions = [r.question for r in qa_results if r.judgment == QAJudgment.EVASIVE]
    
    # 调用LLM做汇总
    prompt = build_qa_summary_prompt([
        {"qid": r.qid, "judgment": r.judgment.value, "reason": r.reason}
        for r in qa_results
    ])
    
    response = call_deepseek(
        system_prompt="你是回答质量汇总器。",
        user_prompt=prompt
    )
    
    result = _parse_json_response(response)
    
    return QASummary(
        total=len(qa_results),
        effective=effective,
        fuzzy=fuzzy,
        evasive=evasive,
        high_frequency_theme=result.get("high_frequency_theme", evasive_questions[:3]),
        one_line_signal=result.get("one_line_signal", f"有效{effective}/模糊{fuzzy}/回避{evasive}")
    )


def _run_risk_update(
    v1_risks: List, 
    deltas: List[DeltaResult],
    qa_results: List[QAResult]
) -> tuple:
    """执行Risk Update"""
    # 转换v1_risks为dict
    risks_dict = [_risk_to_dict(r) if isinstance(r, Risk) else (r if isinstance(r, dict) else {"risk_id": "unknown", "name": str(r), "severity": "medium", "reason": "", "evidence": []}) for r in v1_risks]
    
    prompt = build_risk_update_prompt(
        risks_dict,
        [_delta_to_dict(d) for d in deltas],
        [{"qid": r.qid, "judgment": r.judgment.value} for r in qa_results]
    )
    
    response = call_deepseek(
        system_prompt="你是风险更新引擎。",
        user_prompt=prompt
    )
    
    result = _parse_json_response(response)
    
    # 解析更新的风险
    updated_risks = []
    for r in result.get("updated_risks", []):
        updated_risks.append(RiskUpdate(
            risk_id=r.get("risk_id", ""),
            risk_name=r.get("risk_name", ""),
            old_status=RiskStatus(r.get("old_status", "unresolved")),
            new_status=RiskStatus(r.get("new_status", "unresolved")),
            change_type=r.get("change_type", "unchanged"),
            severity=r.get("severity", "medium"),
            reason=r.get("reason", ""),
            evidence=r.get("evidence", [])
        ))
    
    # 解析新增风险
    new_risks = []
    for r in result.get("new_risks", []):
        new_risks.append(RiskUpdate(
            risk_id=r.get("risk_id", f"new_{len(updated_risks) + len(new_risks)}"),
            risk_name=r.get("risk_name", ""),
            old_status=RiskStatus.UNVERIFIABLE,
            new_status=RiskStatus.NEW_RISK,
            change_type="new",
            severity=r.get("severity", "medium"),
            reason=r.get("reason", ""),
            evidence=r.get("evidence", [])
        ))
    
    summary = RiskUpdateSummary(
        updated_risks=updated_risks,
        new_risks=new_risks,
        summary=result.get("risk_summary", "")
    )
    
    return updated_risks + new_risks, summary


def _run_decision_updater(
    v1_conclusion: Dict,
    risk_summary: RiskUpdateSummary,
    qa_summary: QASummary,
    new_info: List[Dict],
    high_value_deltas: List[DeltaResult]
) -> DecisionUpdate:
    """执行Decision Updater"""
    # 找高价值变化
    hv_deltas = [_delta_to_dict(d) for d in high_value_deltas]
    
    prompt = build_decision_updater_prompt(
        v1_conclusion,
        risk_summary.summary,
        qa_summary,  # 传入完整的 QASummary 对象
        new_info,
        hv_deltas
    )
    
    response = call_deepseek(
        system_prompt="你是投资判断更新器。",
        user_prompt=prompt
    )
    
    result = _parse_json_response(response)
    
    # 映射recommendation
    rec_map = {
        "推进": Recommendation.PROCEED,
        "暂不推进": Recommendation.HOLD,
        "继续跟进": Recommendation.FOLLOW_UP
    }
    rec = rec_map.get(result.get("recommendation", "继续跟进"), Recommendation.FOLLOW_UP)
    
    return DecisionUpdate(
        previous_stance=result.get("previous_stance", "未知"),
        current_stance=result.get("current_stance", "未知"),
        changed=result.get("changed", False),
        decision_logic=result.get("decision_logic", []),
        why_not_now=result.get("why_not_now", []),
        what_would_change_decision=result.get("what_would_change_decision", []),
        recommendation=rec,
        one_line_decision=result.get("one_line_decision", "")
    )


def _run_alpha_layer(
    meeting_text: str,
    qa_results: List[QAResult],
    new_info: List[Dict]
) -> AlphaSignal:
    """执行Alpha Layer"""
    prompt = build_alpha_layer_prompt(
        meeting_text,
        [{"qid": r.qid, "judgment": r.judgment.value, "question": r.question} for r in qa_results],
        new_info
    )
    
    response = call_deepseek(
        system_prompt="你是投资人直觉层。",
        user_prompt=prompt
    )
    
    result = _parse_json_response(response)
    
    # 映射risk_signal
    signal_map = {
        "red": RiskSignal.RED,
        "yellow": RiskSignal.YELLOW,
        "green": RiskSignal.GREEN
    }
    
    return AlphaSignal(
        team_profile_label=result.get("team_profile_label", "无法判断"),
        team_profile_evidence=result.get("team_profile_evidence", ""),
        risk_signal=signal_map.get(result.get("risk_signal", "yellow"), RiskSignal.YELLOW),
        risk_signal_reason=result.get("risk_signal_reason", ""),
        valuation_guidance_exists=result.get("valuation_guidance_exists", False),
        valuation_guidance_evidence=result.get("valuation_guidance_evidence", ""),
        avoidance_pattern=result.get("avoidance_pattern", ""),
        avoidance_frequency=result.get("avoidance_frequency", "medium"),
        avoidance_example=result.get("avoidance_example", ""),
        meeting_quality_score=result.get("meeting_quality_score", 5),
        one_line_insight=result.get("one_line_insight", "")
    )
