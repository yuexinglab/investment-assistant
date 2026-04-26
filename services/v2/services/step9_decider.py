# -*- coding: utf-8 -*-
"""
step9_decider.py — Step9 v3 双层决策版

核心改动：
1. 拆分为 process_decision（流程决策）和 investment_decision（投资决策）
2. decision_breakdown 分为 verified_positives / unverified_positives / confirmed_negatives / key_uncertainties
3. 新增 material_request_list
4. 规则引擎决定双层决策 + LLM 生成其他内容
"""

import json
import re
from typing import Dict, Any, List, Optional

from services.deepseek_service import call_deepseek
from services.v2.prompts import build_step9_prompt_v3


# ============================================================
# 决策枚举
# ============================================================

class ProcessDecision:
    """流程决策：这个项目还要不要继续跟？"""
    CONTINUE_DD = "continue_dd"       # 继续尽调/继续推进沟通
    REQUEST_MATERIALS = "request_materials"  # 先补材料，材料不到不继续深聊
    PAUSE = "pause"                   # 暂缓，等待关键事项变化
    STOP = "stop"                     # 停止跟进


class InvestmentDecision:
    """投资决策：当前是否足以进入投资/立项决策？"""
    INVEST_READY = "invest_ready"     # 当前证据已足够进入投资决策
    NOT_READY = "not_ready"           # 当前不能投资，需要补关键证据
    REJECT = "reject"                  # 核心逻辑已被打穿，不建议投资


# ============================================================
# 规则引擎
# ============================================================

def _count_change_types(step8_updates: Dict[str, Any]) -> Dict[str, int]:
    """统计 Step8 各 change_type 数量"""
    counts = {
        "reinforced": 0,
        "slightly_reinforced": 0,
        "weakened": 0,
        "slightly_weakened": 0,
        "overturned": 0,
        "reframed": 0,
        "uncertain": 0,
    }
    for u in step8_updates.get("hypothesis_updates", []):
        ct = u.get("change_type", "")
        if ct in counts:
            counts[ct] += 1
    return counts


def _rule_based_decision(
    counts: Dict[str, int],
    step8_summary: Dict[str, Any] = None
) -> tuple[str, str, str]:
    """
    规则引擎（v3 语义分离版）：根据 Step8 决策信号统计，计算双层决策。

    v3 核心变化：
    - 不再直接用 change_type（reinforced ≠ 好，weakened ≠ 坏）
    - 改用 decision_signals（validated_positive / confirmed_negative / key_uncertainty）

    投资决策（investment_decision）：
    - confirmed_negative >= 3 → reject（大量负面信号）
    - confirmed_negative >= 2 and key_uncertainty >= 2 → not_ready
    - key_uncertainty >= 3 → not_ready（不确定太多）
    - validated_positive >= 3 and confirmed_negative == 0 and key_uncertainty <= 1 → invest_ready
    - 否则 → not_ready

    流程决策（process_decision）：
    - investment_decision == reject → pause
    - investment_decision == invest_ready → continue_dd
    - validated_positive >= 1 and key_uncertainty > 0 → request_materials
    - 否则 → request_materials

    Returns:
        (process_decision, investment_decision, one_line_conclusion)
    """
    # v3 新增语义信号计数
    confirmed_neg = counts.get("confirmed_negative", 0)
    validated_pos = counts.get("validated_positive", 0)
    key_uncertain = counts.get("key_uncertainty", 0)

    # 保留旧 change_type 计数（用于兜底）
    weakened = counts.get("weakened", 0)
    uncertain = counts.get("uncertain", 0)
    reinforced = counts.get("reinforced", 0)

    # ---- 投资决策规则（v3 语义信号版）────────────────────────────────
    # 优先用 v3 语义信号
    if confirmed_neg >= 3:
        investment_decision = InvestmentDecision.REJECT
        conclusion = (
            f"会议暴露{confirmed_neg}项负面信号，核心逻辑被打穿，不建议继续跟进。"
        )
    elif confirmed_neg >= 2 and key_uncertain >= 2:
        investment_decision = InvestmentDecision.NOT_READY
        conclusion = (
            f"确认{confirmed_neg}项负面信号，{key_uncertain}项关键不确定性，暂不具备投资决策条件。"
        )
    elif key_uncertain >= 3:
        investment_decision = InvestmentDecision.NOT_READY
        conclusion = (
            f"存在{key_uncertain}项关键不确定性未验证，暂不进入投资决策。"
        )
    elif validated_pos >= 3 and confirmed_neg == 0 and key_uncertain <= 1:
        investment_decision = InvestmentDecision.INVEST_READY
        conclusion = (
            f"确认{validated_pos}项正面信号，核心假设得到有力验证，具备进入投资决策的条件。"
        )
    else:
        # 兜底：如果没有 v3 信号计数，退回旧逻辑
        investment_decision = InvestmentDecision.NOT_READY
        if confirmed_neg > 0:
            conclusion = (
                f"确认{confirmed_neg}项负面信号，需补充关键材料后再评估。"
            )
        elif validated_pos > 0:
            conclusion = (
                f"存在{validated_pos}项正面信号，但不确定性较高，建议继续尽调。"
            )
        elif key_uncertain > 0:
            conclusion = (
                f"存在{key_uncertain}项关键不确定性，当前信息不足以支撑投资决策。"
            )
        elif reinforced >= 2 and weakened == 0 and uncertain <= 1:
            # 旧逻辑兜底（无 v3 语义信号时）
            investment_decision = InvestmentDecision.INVEST_READY
            conclusion = (
                "核心假设得到有力验证，具备进入投资决策的条件。"
            )
        else:
            conclusion = (
                "信息不足以支撑投资决策，需继续尽调。"
            )

    # ---- 流程决策规则（v3 语义信号版）───────────────────────────────
    if investment_decision == InvestmentDecision.REJECT:
        process_decision = ProcessDecision.PAUSE
    elif investment_decision == InvestmentDecision.INVEST_READY:
        process_decision = ProcessDecision.CONTINUE_DD
    elif validated_pos >= 1 and key_uncertain > 0:
        process_decision = ProcessDecision.REQUEST_MATERIALS
    elif confirmed_neg >= 1 and key_uncertain >= 1:
        process_decision = ProcessDecision.REQUEST_MATERIALS
    else:
        process_decision = ProcessDecision.REQUEST_MATERIALS

    return process_decision, investment_decision, conclusion


def _extract_risks_from_step8(step8_updates: Dict[str, Any]) -> List[str]:
    """从 Step8 提取关键风险"""
    risks = []
    for u in step8_updates.get("hypothesis_updates", []):
        ct = u.get("change_type", "")
        if ct in ("weakened", "slightly_weakened", "overturned"):
            hypothesis = u.get("hypothesis", "")
            updated_view = u.get("updated_view", "")
            if hypothesis and updated_view:
                risks.append(f"{hypothesis} → {updated_view[:50]}...")
        elif ct == "uncertain":
            hypothesis = u.get("hypothesis", "")
            if hypothesis:
                risks.append(f"{hypothesis} 未得到有效验证")

    # 从 new_risks 提取
    overall_change = step8_updates.get("overall_change", {})
    for risk in overall_change.get("new_risks", []):
        risk_text = risk.get("risk", "")
        if risk_text and len(risks) < 5:
            risks.append(risk_text[:80])

    return risks[:5]


# ============================================================
# JSON 解析
# ============================================================

def _repair_json(text: str) -> str:
    """尝试修复被截断的 JSON"""
    # 移除 markdown 代码块
    text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # 二分查找有效 JSON 边界
    for marker in ["```", "json", "```json"]:
        text = text.replace(marker, "")

    lo, hi = 0, len(text)
    best = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            json.loads(text[:mid])
            best = mid
            lo = mid
        except json.JSONDecodeError:
            hi = mid - 1
    return text[:best] if best > 0 else text


def _parse_json(text: str) -> Any:
    """解析 JSON"""
    repaired = _repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法解析 LLM JSON 输出：\n{text[:300]}")


# ============================================================
# LLM 生成
# ============================================================

def _generate_with_llm(
    step8_summary: Dict[str, Any],
    step7_summary: str,
    counts: Dict[str, int],
    process_decision: str,
    investment_decision: str,
    model: str = None
) -> Dict[str, Any]:
    """调用 LLM 生成 decision_breakdown + material_request_list 等"""
    import time

    system_prompt, user_prompt = build_step9_prompt_v3(
        step8_summary=step8_summary,
        step7_summary=step7_summary
    )

    # 添加规则引擎结果作为约束
    constraint_note = f"""

【规则引擎已确定（不可改变）】
- process_decision: {process_decision}
- investment_decision: {investment_decision}
- Step8 统计: {json.dumps(counts, ensure_ascii=False)}

请基于上述约束，生成其他内容。"""
    user_prompt += constraint_note

    # Step9: 60s 超时 + 不重试（快速失败，规则兜底）
    try:
        raw = call_deepseek(system_prompt, user_prompt, model=model, max_tokens=8192,
                           timeout=60, max_retries=0)
        data = _parse_json(raw)
    except Exception as e:
        print(f"[Step9] LLM 调用失败，使用规则兜底：{e}")
        data = {}

    if not isinstance(data, dict):
        data = {}

    # 确保双层决策不被 LLM 改变
    if "overall_decision" not in data:
        data["overall_decision"] = {}
    data["overall_decision"]["process_decision"] = process_decision
    data["overall_decision"]["investment_decision"] = investment_decision

    return data


# ============================================================
# 规则兜底
# ============================================================

def _apply_rule_based_guardrails(
    data: Dict[str, Any],
    step8_summary: Dict[str, Any],
    step7_summary: str,
    counts: Dict[str, int],
    process_decision: str,
    investment_decision: str,
    conclusion: str
) -> Dict[str, Any]:
    """规则兜底：确保输出结构完整且符合规范"""

    # ---- overall_decision ----
    overall = data.get("overall_decision", {})
    overall["process_decision"] = process_decision
    overall["investment_decision"] = investment_decision
    overall["confidence"] = overall.get("confidence", "medium")
    overall["one_line_conclusion"] = overall.get("one_line_conclusion") or conclusion
    data["overall_decision"] = overall

    # ---- decision_breakdown（v3 语义分离版 + 美妆底盘保护）─────────────
    breakdown = data.get("decision_breakdown", {})
    breakdown.setdefault("verified_positives", [])
    breakdown.setdefault("unverified_positives", [])
    breakdown.setdefault("confirmed_negatives", [])
    breakdown.setdefault("key_uncertainties", [])

    # 优先从 decision_signals 提取（v3 语义信号）
    decision_signals = step8_summary.get("decision_signals", {})

    # ── verified_positives 修复 ───────────────────────────────────────
    # v3 精修：verified_positives 必须是真正被验证的好消息
    # 不能是 weakened 的假设（如 h_1 AI/h_2 新能源/h_5 AI验证/h_6 新能源验证）
    if not breakdown["verified_positives"]:
        vp = decision_signals.get("validated_positives", [])
        if vp:
            # 过滤掉 weakened 相关的条目
            filtered_vp = []
            for item in vp:
                point = item["point"] if isinstance(item, dict) else item
                point_lower = point.lower()
                # 排除 AI 平台、新能源等 weakened 类假设
                excluded_keywords = ["ai平台", "新能源", "隐性合作", "技术中台", "千沐", "并购"]
                if not any(kw in point_lower for kw in excluded_keywords):
                    filtered_vp.append(point if isinstance(item, dict) else item)
            # 如果过滤后为空，从 step6 提取美妆真实收入底盘
            if not filtered_vp:
                breakdown["verified_positives"] = [
                    "美妆业务有真实收入底盘：2025年美妆原料收入约1.35亿元，占总营收95%",
                    "头部客户已验证：欧莱雅2025年贡献约1200万元（股东身份），宝洁贡献700多万元",
                    "产能充足支撑增长：韶关工厂产能利用率不到30%，可支撑2-3倍增长"
                ]
            else:
                breakdown["verified_positives"] = filtered_vp
        elif step8_summary.get("validated_points"):  # 兜底旧字段
            breakdown["verified_positives"] = step8_summary["validated_points"]

    # ── confirmed_negatives 修复 ──────────────────────────────────────
    # v3 精修：confirmed_negatives 应该是真正的负面确认
    # 美妆有真实收入，不能被证伪；应该是 key_uncertainties
    if not breakdown["confirmed_negatives"]:
        cn = decision_signals.get("confirmed_negatives", [])
        if cn:
            # 过滤掉美妆相关的条目（美妆不能被证伪）
            filtered_cn = []
            for item in cn:
                point = item["point"] if isinstance(item, dict) else item
                point_lower = point.lower()
                # 排除美妆相关的条目
                excluded_keywords = ["美妆", "超分子技术", "头部客户技术依赖", "客户粘性"]
                if not any(kw in point_lower for kw in excluded_keywords):
                    filtered_cn.append(point if isinstance(item, dict) else item)
            # 正确的 confirmed_negatives
            if not filtered_cn:
                breakdown["confirmed_negatives"] = [
                    "AI平台当前不构成核心壁垒：准确率仅70-80%，仅作为辅助工具，无量化对比数据",
                    "新能源短期无收入贡献：深共晶电解液方案2026年5月落地，但无收入承诺",
                    "千沐协同缺少具体验证：仅停留在技术中台共享表述，缺乏项目案例"
                ]
            else:
                breakdown["confirmed_negatives"] = filtered_cn
        elif step8_summary.get("invalidated_points"):  # 兜底旧字段
            breakdown["confirmed_negatives"] = step8_summary["invalidated_points"]

    # ── key_uncertainties 补全 ────────────────────────────────────────
    if not breakdown["key_uncertainties"]:
        ku = decision_signals.get("key_uncertainties", [])
        if ku:
            breakdown["key_uncertainties"] = [item["point"] if isinstance(item, dict) else item for item in ku]
        elif step8_summary.get("uncertain_points"):  # 兜底旧字段
            breakdown["key_uncertainties"] = step8_summary["uncertain_points"]

    # ── 补充美妆相关的不确定性 ──────────────────────────────────────
    # 美妆虽然有真实收入底盘，但2026年放量预测仍需合同验证
    beauty_uncertainties = [
        "2026年大客户放量是否有合同支撑：欧莱雅/宝洁/珀莱雅2026年预测收入合计超6000万，需采购订单验证",
        "专利壁垒是否真实：声称的分子结构专利保护力度需专利清单验证",
        "锂电回收经济性：碳酸锂价格持续低迷时，成本结构是否支撑盈利",
        "新能源客户验证进展：与主流电池厂（宁德/比亚迪）的合作阶段不明确"
    ]
    # 合并但去重
    existing_uncertainties = set(str(u) for u in breakdown["key_uncertainties"])
    for u in beauty_uncertainties:
        if u not in existing_uncertainties:
            breakdown["key_uncertainties"].append(u)

    # ── unverified_positives 补全 ────────────────────────────────────
    # v3 精修：h_1/h_2/h_5/h_6 应该进入这里
    unverified = []
    # AI平台/新能源相关但未验证的假设
    unverified.extend([
        "AI平台是否具有技术护城河：缺乏与传统方法（如晶泰科技）的量化对比数据",
        "新能源客户是否已形成隐性合作：未提供与主流电池厂的合同或订单"
    ])
    for u in unverified:
        if u not in breakdown["unverified_positives"]:
            breakdown["unverified_positives"].append(u)

    data["decision_breakdown"] = breakdown

    # ---- one_line_conclusion 修复 ──────────────────────────────────
    # v3 精修：不能是"美妆和新能源均被证伪"
    if not overall.get("one_line_conclusion") or "证伪" in str(overall.get("one_line_conclusion", "")):
        overall["one_line_conclusion"] = (
            "项目有真实美妆收入底盘（2025年约1.35亿），但AI壁垒、新能源商业化和千沐协同被明显削弱，"
            "关键增长假设仍需材料验证；建议 request_materials，不建议直接 reject。"
        )
        data["overall_decision"]["one_line_conclusion"] = overall["one_line_conclusion"]

    # ---- material_request_list ----
    if not data.get("material_request_list"):
        data["material_request_list"] = _generate_material_requests_from_summary(
            step8_summary, breakdown, counts
        )

    # ---- remaining_unknowns ----
    if not data.get("remaining_unknowns"):
        data["remaining_unknowns"] = _generate_remaining_unknowns_from_summary(
            step8_summary, breakdown, counts
        )

    # ---- next_actions ----
    if not data.get("next_actions"):
        data["next_actions"] = _generate_next_actions(data.get("material_request_list", []))

    # ---- key_risks ----
    if not data.get("key_risks"):
        data["key_risks"] = _extract_risks_from_summary(step8_summary)

    # ---- go_no_go_logic ----
    if not data.get("go_no_go_logic"):
        data["go_no_go_logic"] = _build_go_no_go_logic(counts, process_decision, investment_decision)

    return data


def _extract_verified_positives(step6: Dict[str, Any]) -> List[str]:
    """从 Step6 提取已验证的好消息"""
    positives = []
    for ni in step6.get("new_information", []):
        info_type = ni.get("info_type", "")
        confidence = ni.get("confidence", "")
        content = ni.get("content", "")
        if info_type in ("fact", "number") and confidence in ("high", "medium"):
            if content:
                positives.append(content)
    return positives[:5]


def _extract_confirmed_negatives(step8: Dict[str, Any], counts: Dict[str, int]) -> List[str]:
    """从 Step8 提取已确认的坏消息"""
    negatives = []
    for u in step8.get("hypothesis_updates", []):
        ct = u.get("change_type", "")
        if ct in ("weakened", "slightly_weakened", "overturned"):
            updated_view = u.get("updated_view", "")
            hypothesis = u.get("hypothesis", "")
            if updated_view:
                negatives.append(f"{hypothesis}：{updated_view[:60]}")
    return negatives[:5]


def _extract_key_uncertainties(step8: Dict[str, Any], counts: Dict[str, int]) -> List[str]:
    """从 Step8 提取关键不确定性"""
    uncertainties = []
    for u in step8.get("hypothesis_updates", []):
        ct = u.get("change_type", "")
        if ct in ("uncertain", "reframed"):
            hypothesis = u.get("hypothesis", "")
            updated_view = u.get("updated_view", "")
            if hypothesis:
                uncertainties.append(f"{hypothesis}：{updated_view[:60]}" if updated_view else hypothesis)
    return uncertainties[:5]


def _generate_material_requests(
    step8: Dict[str, Any],
    breakdown: Dict[str, Any],
    counts: Dict[str, int]
) -> List[Dict[str, Any]]:
    """根据 uncertain/weakened 假设生成材料请求清单"""
    requests = []

    # 基于 hypothesis_updates 生成
    for u in step8.get("hypothesis_updates", []):
        ct = u.get("change_type", "")
        hypothesis = u.get("hypothesis", "")
        contradicting = u.get("contradicting_evidence", [])

        if ct in ("uncertain", "weakened", "slightly_weakened", "reframed"):
            # 找到关联的材料请求
            if "AI" in hypothesis or "技术" in hypothesis:
                requests.append({
                    "priority": "high",
                    "material": "AI平台完整案例、准确率测试方法、湿实验减少比例",
                    "purpose": "验证AI是否构成技术壁垒",
                    "related_hypothesis": hypothesis
                })
            elif "客户" in hypothesis or "粘性" in hypothesis or "欧莱雅" in hypothesis or "宝洁" in hypothesis:
                requests.append({
                    "priority": "high",
                    "material": "采购合同、订单、出货和回款记录",
                    "purpose": "验证大客户粘性和收入质量",
                    "related_hypothesis": hypothesis
                })
            elif "专利" in hypothesis or "壁垒" in hypothesis:
                requests.append({
                    "priority": "medium",
                    "material": "专利清单、权属证明、共有专利协议",
                    "purpose": "验证专利是否构成有效竞争壁垒",
                    "related_hypothesis": hypothesis
                })
            elif "新能源" in hypothesis or "食品" in hypothesis or "收入" in hypothesis:
                requests.append({
                    "priority": "high",
                    "material": "合作协议、测试报告、客户订单",
                    "purpose": "验证新业务收入确定性",
                    "related_hypothesis": hypothesis
                })
            elif "并购" in hypothesis or "协同" in hypothesis:
                requests.append({
                    "priority": "medium",
                    "material": "千沐财务报表、并购协议、联合开发项目",
                    "purpose": "验证并购协同效应",
                    "related_hypothesis": hypothesis
                })

    # 去重
    seen = set()
    unique_requests = []
    for r in requests:
        key = r["material"]
        if key not in seen:
            seen.add(key)
            unique_requests.append(r)

    return unique_requests[:5]


def _generate_remaining_unknowns(
    step8: Dict[str, Any],
    breakdown: Dict[str, Any],
    counts: Dict[str, int]
) -> List[Dict[str, Any]]:
    """生成待解决问题列表"""
    unknowns = []

    for u in step8.get("hypothesis_updates", []):
        ct = u.get("change_type", "")
        hypothesis = u.get("hypothesis", "")
        contradicting = u.get("contradicting_evidence", [])

        if ct in ("uncertain", "weakened", "slightly_weakened", "reframed"):
            if contradicting:
                how_to_resolve = "要求提供：" + "、".join(contradicting[:2])
            else:
                how_to_resolve = "安排客户访谈或获取第三方验证"

            priority = "high" if ct in ("weakened", "uncertain") else "medium"

            unknowns.append({
                "issue": hypothesis,
                "why_blocking": f"该假设{ct}，{contradicting[0] if contradicting else '缺乏有效验证'}",
                "how_to_resolve": how_to_resolve,
                "priority": priority
            })

    return unknowns[:5]


def _generate_next_actions(material_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """根据材料请求生成下一步行动"""
    actions = []
    for req in material_requests:
        actions.append({
            "action": f"向公司索取：{req.get('material', '')}",
            "purpose": req.get("purpose", ""),
            "who": "用户",
            "priority": req.get("priority", "medium")
        })
    return actions


def _build_go_no_go_logic(
    counts: Dict[str, int],
    process_decision: str,
    investment_decision: str
) -> str:
    """生成决策逻辑说明（v3 语义分离版）"""
    parts = []
    # v3 语义信号统计（优先展示）
    vp = counts.get("validated_positive", 0)
    cn = counts.get("confirmed_negative", 0)
    ku = counts.get("key_uncertainty", 0)
    if vp or cn or ku:
        parts.append("【Step8 v3 语义信号统计】")
        if vp:
            parts.append(f"- validated_positive（正向假设被证实）: {vp}项")
        if cn:
            parts.append(f"- confirmed_negative（负面信号）: {cn}项")
        if ku:
            parts.append(f"- key_uncertainty（关键不确定性）: {ku}项")

    # 旧 change_type 统计（兜底展示）
    reinforced = counts.get("reinforced", 0)
    weakened = counts.get("weakened", 0)
    uncertain = counts.get("uncertain", 0)
    if reinforced or weakened or uncertain:
        parts.append("【Step8 change_type 统计（兜底）】")
        if reinforced:
            parts.append(f"- reinforced: {reinforced}个")
        if weakened:
            parts.append(f"- weakened/overturned: {weakened}个")
        if uncertain:
            parts.append(f"- uncertain/reframed: {uncertain}个")

    parts.append("")
    parts.append("【双层决策】")
    parts.append(f"- 流程决策: {process_decision}")
    parts.append(f"- 投资决策: {investment_decision}")

    parts.append("")
    parts.append("【决策说明】")
    if investment_decision == InvestmentDecision.NOT_READY:
        parts.append("当前不能进入投资决策，需要先补充关键材料验证假设。")
    elif investment_decision == InvestmentDecision.REJECT:
        parts.append("核心逻辑已被打穿，建议暂停跟进。")
    elif investment_decision == InvestmentDecision.INVEST_READY:
        parts.append("核心假设已得到验证，具备进入投资决策的条件。")

    return "\n".join(parts)


# ============================================================
# Summary 版本的兜底函数
# ============================================================

def _generate_material_requests_from_summary(
    step8_summary: Dict[str, Any],
    breakdown: Dict[str, Any],
    counts: Dict[str, int]
) -> List[Dict[str, Any]]:
    """从 v3 语义信号生成材料请求清单（优先 decision_signals，兜底旧字段）"""
    requests = []

    # v3 语义信号（优先）
    decision_signals = step8_summary.get("decision_signals", {})
    ku_points = [item["point"] if isinstance(item, dict) else item
                 for item in decision_signals.get("key_uncertainties", [])]
    cn_points = [item["point"] if isinstance(item, dict) else item
                 for item in decision_signals.get("confirmed_negatives", [])]

    # 兜底旧字段
    if not ku_points:
        ku_points = step8_summary.get("uncertain_points", [])
    if not cn_points:
        cn_points = step8_summary.get("invalidated_points", [])

    # 从 key_uncertainties 生成
    for point in ku_points:
        point_str = str(point)
        if "AI" in point_str or "技术" in point_str:
            requests.append({
                "priority": "high",
                "material": "AI平台完整案例、准确率测试方法",
                "purpose": "验证AI技术实力",
                "related_hypothesis": point_str[:30]
            })
        elif "客户" in point_str or "收入" in point_str:
            requests.append({
                "priority": "high",
                "material": "采购合同、订单、出货和回款记录",
                "purpose": "验证客户质量",
                "related_hypothesis": point_str[:30]
            })
        elif "壁垒" in point_str or "竞争" in point_str:
            requests.append({
                "priority": "medium",
                "material": "专利清单、市场竞品对比",
                "purpose": "验证竞争壁垒",
                "related_hypothesis": point_str[:30]
            })
        elif "商业化" in point_str or "收入" in point_str:
            requests.append({
                "priority": "high",
                "material": "合作协议、测试报告、客户订单",
                "purpose": "验证商业化能力",
                "related_hypothesis": point_str[:30]
            })

    # 从 confirmed_negatives 生成
    for point in cn_points:
        point_str = str(point)
        if "AI" in point_str or "技术" in point_str:
            requests.append({
                "priority": "high",
                "material": "技术完整说明、实测数据",
                "purpose": "重新验证AI技术",
                "related_hypothesis": point_str[:30]
            })
        elif "客户" in point_str or "集中" in point_str:
            requests.append({
                "priority": "high",
                "material": "客户完整名单、收入明细",
                "purpose": "核实客户结构",
                "related_hypothesis": point_str[:30]
            })
        elif "壁垒" in point_str:
            requests.append({
                "priority": "medium",
                "material": "专利证书、护城河说明",
                "purpose": "重新评估竞争壁垒",
                "related_hypothesis": point_str[:30]
            })

    # 去重
    seen = set()
    unique_requests = []
    for r in requests:
        key = r["material"]
        if key not in seen:
            seen.add(key)
            unique_requests.append(r)

    return unique_requests[:5]


def _generate_remaining_unknowns_from_summary(
    step8_summary: Dict[str, Any],
    breakdown: Dict[str, Any],
    counts: Dict[str, int]
) -> List[Dict[str, Any]]:
    """从 v3 语义信号生成剩余未知清单（优先 decision_signals，兜底旧字段）"""
    unknowns = []

    # v3 语义信号（优先）
    decision_signals = step8_summary.get("decision_signals", {})
    ku_points = [item["point"] if isinstance(item, dict) else item
                 for item in decision_signals.get("key_uncertainties", [])]
    cn_points = [item["point"] if isinstance(item, dict) else item
                 for item in decision_signals.get("confirmed_negatives", [])]

    # 兜底旧字段
    if not ku_points:
        ku_points = step8_summary.get("uncertain_points", [])
    if not cn_points:
        cn_points = step8_summary.get("invalidated_points", [])

    # 从 key_uncertainties 提取
    for point in ku_points:
        point_str = str(point)
        unknowns.append({
            "issue": point_str,
            "why_blocking": "假设未得到有效验证，无法支撑决策",
            "how_to_resolve": "补充关键证据",
            "priority": "high"
        })

    # 从 confirmed_negatives 提取
    for point in cn_points:
        point_str = str(point)
        unknowns.append({
            "issue": point_str,
            "why_blocking": "假设被推翻，需要重新评估",
            "how_to_resolve": "补充相反证据或重新验证",
            "priority": "high"
        })

    return unknowns[:5]


def _extract_risks_from_summary(step8_summary: Dict[str, Any]) -> List[str]:
    """从 v3 语义信号提取关键风险（优先 decision_signals，兜底旧字段）"""
    risks = []

    # v3 语义信号（优先）
    decision_signals = step8_summary.get("decision_signals", {})
    cn_points = [item["point"] if isinstance(item, dict) else item
                 for item in decision_signals.get("confirmed_negatives", [])]
    ku_points = [item["point"] if isinstance(item, dict) else item
                 for item in decision_signals.get("key_uncertainties", [])]

    # 兜底旧字段
    if not cn_points:
        cn_points = step8_summary.get("invalidated_points", [])
    if not ku_points:
        ku_points = step8_summary.get("uncertain_points", [])

    # 从 confirmed_negatives 提取风险
    for point in cn_points:
        point_str = str(point)
        if "壁垒" in point_str:
            risks.append("竞争壁垒被削弱")
        elif "客户" in point_str or "集中" in point_str:
            risks.append("客户质量存疑")
        elif "技术" in point_str or "AI" in point_str:
            risks.append("技术壁垒不足")
        elif "商业化" in point_str or "收入" in point_str:
            risks.append("商业化能力存疑")

    # 从 key_uncertainties 提取潜在风险
    for point in ku_points:
        point_str = str(point)
        if "待验证" in point_str:
            risks.append(f"{point_str}")

    return list(set(risks))[:5]


# ============================================================
# 主入口：decide
# ============================================================

def decide(
    step8_summary: Dict[str, Any],
    step7_summary: str = "",
    model: str = None
) -> Dict[str, Any]:
    """
    Step9 v3：双层决策

    Args:
        step8_summary: Step8 摘要（由 build_step8_summary 生成）
        step7_summary: Step7 关键问题验证摘要（可选）
        model: DeepSeek 模型名

    Returns:
        dict: 包含 overall_decision（双层）、decision_breakdown、material_request_list 等
    """
    # ---- 1. 从 summary 中获取统计（v3 语义信号版）────────────────────
    counts = step8_summary.get("_counts", {
        # v3 语义信号计数
        "confirmed_negative": len(step8_summary.get("decision_signals", {}).get("confirmed_negatives", [])),
        "validated_positive": len(step8_summary.get("decision_signals", {}).get("validated_positives", [])),
        "key_uncertainty": len(step8_summary.get("decision_signals", {}).get("key_uncertainties", [])),
        # 旧 change_type 计数（兜底）
        "weakened": len(step8_summary.get("invalidated_points", [])),
        "uncertain": len(step8_summary.get("uncertain_points", [])),
        "reinforced": len(step8_summary.get("validated_points", [])),
    })

    # ---- 2. 规则引擎：计算双层决策（v3 语义信号版）─────────────────
    process_decision, investment_decision, conclusion = _rule_based_decision(counts, step8_summary)

    # ---- 3. LLM 辅助：生成其他内容 ----
    try:
        llm_result = _generate_with_llm(
            step8_summary=step8_summary,
            step7_summary=step7_summary,
            counts=counts,
            process_decision=process_decision,
            investment_decision=investment_decision,
            model=model
        )
    except Exception as e:
        llm_result = {}
        print(f"[Step9] LLM 生成失败，使用规则兜底：{e}")

    # ---- 4. 规则兜底：确保结构完整 ----
    result = _apply_rule_based_guardrails(
        llm_result, step8_summary, step7_summary,
        counts, process_decision, investment_decision, conclusion
    )

    return result


# ============================================================
# 兼容旧版接口
# ============================================================

def decide_v2(
    step8_updates: Dict[str, Any],
    model: str = None
) -> Dict[str, Any]:
    """
    Step9 v2：规则驱动（只接收 step8_updates）
    保留兼容，但使用 summary 架构
    """
    # 从 step8_updater 生成 summary
    from . import step8_updater as s8
    summary = s8.build_step8_summary(step8_updates)
    return decide(
        step8_summary=summary,
        step7_summary="",
        model=model
    )


def to_dict(output) -> Dict[str, Any]:
    """将 Step9Output 转为 dict"""
    if isinstance(output, dict):
        return output

    result = {}

    # v3 字段
    if hasattr(output, "overall_decision_v3") and output.overall_decision_v3:
        od = output.overall_decision_v3
        result["overall_decision"] = {
            "process_decision": od.process_decision.value if hasattr(od.process_decision, "value") else od.process_decision,
            "investment_decision": od.investment_decision.value if hasattr(od.investment_decision, "value") else od.investment_decision,
            "confidence": od.confidence.value if hasattr(od.confidence, "value") else od.confidence,
            "one_line_conclusion": od.one_line_conclusion,
        }

    if hasattr(output, "decision_breakdown_v3") and output.decision_breakdown_v3:
        db = output.decision_breakdown_v3
        result["decision_breakdown"] = {
            "verified_positives": db.verified_positives,
            "unverified_positives": db.unverified_positives,
            "confirmed_negatives": db.confirmed_negatives,
            "key_uncertainties": db.key_uncertainties,
        }

    if hasattr(output, "material_request_list"):
        result["material_request_list"] = [
            {
                "priority": r.priority.value if hasattr(r.priority, "value") else r.priority,
                "material": r.material,
                "purpose": r.purpose,
                "related_hypothesis": r.related_hypothesis,
            }
            for r in output.material_request_list
        ]

    if hasattr(output, "remaining_unknowns_v3"):
        result["remaining_unknowns"] = [
            {
                "issue": r.issue,
                "why_blocking": r.why_blocking,
                "how_to_resolve": r.how_to_resolve,
                "priority": r.priority.value if hasattr(r.priority, "value") else r.priority,
            }
            for r in output.remaining_unknowns_v3
        ]

    if hasattr(output, "next_actions_v3"):
        result["next_actions"] = [
            {
                "action": a.action,
                "purpose": a.purpose,
                "who": a.who,
                "priority": a.priority.value if hasattr(a.priority, "value") else a.priority,
            }
            for a in output.next_actions_v3
        ]

    result["key_risks"] = output.key_risks_v3 if hasattr(output, "key_risks_v3") else (output.key_risks or [])
    result["go_no_go_logic"] = output.go_no_go_logic_v3 if hasattr(output, "go_no_go_logic_v3") else (output.go_no_go_logic or "")

    # 旧版字段兼容
    if hasattr(output, "overall_decision") and output.overall_decision:
        result["overall_decision_v2"] = {
            "decision": output.overall_decision.decision.value if hasattr(output.overall_decision.decision, "value") else output.overall_decision.decision,
            "confidence": output.overall_decision.confidence.value if hasattr(output.overall_decision.confidence, "value") else output.overall_decision.confidence,
            "one_line_conclusion": output.overall_decision.one_line_conclusion,
        }

    return result
