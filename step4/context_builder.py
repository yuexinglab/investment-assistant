from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def extract_section_by_keywords(text: str, keywords: List[str], window: int = 700) -> str:
    if not text:
        return ""

    hits: List[str] = []
    for kw in keywords:
        start_idx = 0
        while True:
            idx = text.find(kw, start_idx)
            if idx == -1:
                break
            start = max(0, idx - 120)
            end = min(len(text), idx + window)
            snippet = text[start:end].strip()
            if snippet:
                hits.append(snippet)
            start_idx = idx + len(kw)

    uniq: List[str] = []
    seen = set()
    for h in hits:
        if h not in seen:
            uniq.append(h)
            seen.add(h)

    return "\n\n".join(uniq[:3])


def _safe_load_json(raw: str | Dict[str, Any] | None) -> Dict[str, Any]:
    """安全加载 JSON，支持 dict 直接返回"""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def build_step4_context(
    *,
    step1_text: str,
    step3_json: str | Dict[str, Any],
    bp_text: str,
    step3b_json: Optional[str | Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建 Step4 的 context pack

    整合 Step1 + Step3 + Step3B 的输出，生成统一上下文供深挖层使用。

    新增 Step3B 整合逻辑：
    - 从 Step3B 的一致性检查、矛盾、包装信号中提取决策缺口候选
    - 合并 Step3 的 key_uncertainties，形成统一的 decision_gap_candidates
    """
    step3_obj = _safe_load_json(step3_json)
    step3b_obj = _safe_load_json(step3b_json)

    # ── 原有 Step3 字段 ──────────────────────────────────────────────
    still_unresolved = step3_obj.get("still_unresolved", [])
    tensions = step3_obj.get("tensions", [])
    adjustment_hints = step3_obj.get("step1_adjustment_hints", {})
    selected_buckets = step3_obj.get("selected_buckets", [])
    bucket_outputs = step3_obj.get("bucket_outputs", [])

    # ── 新增：Step3 新版 project_structure（key_uncertainties）───────────
    project_structure = step3_obj.get("project_structure", {})
    key_uncertainties = project_structure.get("key_uncertainties", [])

    # ── Step3B 字段 ────────────────────────────────────────────────
    step3b_summary = step3b_obj.get("summary", "")
    step3b_checks = step3b_obj.get("consistency_checks", [])
    step3b_tensions = step3b_obj.get("tensions", [])
    step3b_packaging = step3b_obj.get("overpackaging_signals", [])

    # ── 构建 decision_gap_candidates ─────────────────────────────────
    # 合并 Step3（结构不确定性）+ Step3B（BP包装缺口）
    decision_gap_candidates = []

    # 从 Step3 key_uncertainties 提取
    for u in key_uncertainties[:6]:
        decision_gap_candidates.append({
            "source": "step3_key_uncertainty",
            "issue": u.get("uncertainty", ""),
            "why_it_matters": u.get("why_it_matters", ""),
            "discriminating_questions": u.get("discriminating_questions", []),
            "related_dimensions": u.get("related_dimensions", []),
        })

    # 从 Step3B consistency_checks 提取（仅 contradictory / uncertain）
    for c in step3b_checks:
        judgement = c.get("judgement", "")
        if judgement in ("contradict", "uncertain"):
            decision_gap_candidates.append({
                "source": "step3b_consistency_check",
                "issue": c.get("topic", ""),
                "claim": c.get("claim", ""),
                "gap": c.get("gap", ""),
                "why_it_matters": c.get("gap", ""),
                "judgement": judgement,
            })

    # 从 Step3B tensions 提取
    for t in step3b_tensions:
        if t.get("severity") in ("high", "critical"):
            decision_gap_candidates.append({
                "source": "step3b_tension",
                "issue": t.get("tension", ""),
                "why_it_matters": t.get("why_it_matters", ""),
                "severity": t.get("severity", "medium"),
            })

    # 从 Step3B overpackaging_signals 提取
    for p in step3b_packaging:
        decision_gap_candidates.append({
            "source": "step3b_packaging_signal",
            "signal_type": p.get("signal_type", ""),
            "issue": p.get("description", ""),
            "why_it_matters": f"可能存在{p.get('signal_type', '')}，影响对核心业务的真实判断",
        })

    bp_signals = {
        "revenue_and_growth": extract_section_by_keywords(
            bp_text, ["营收", "收入", "增长", "毛利", "利润", "订单", "复购"]
        ),
        "customer_and_cooperation": extract_section_by_keywords(
            bp_text, ["客户", "欧莱雅", "华熙", "宝洁", "合作", "采购", "联合开发", "独家", "协议"]
        ),
        "ai_and_platform": extract_section_by_keywords(
            bp_text, ["AI", "平台", "建沐", "研发体系", "数据库", "筛选", "预测"]
        ),
        "new_business": extract_section_by_keywords(
            bp_text, ["食品", "新能源", "医药", "农业", "第二曲线", "跨行业", "千沐"]
        ),
        "production_and_capacity": extract_section_by_keywords(
            bp_text, ["产能", "量产", "工厂", "中试", "生产", "验证", "良率"]
        ),
        "technology_and_patents": extract_section_by_keywords(
            bp_text, ["专利", "共晶", "离子盐", "超分子", "技术壁垒", "工艺"]
        ),
    }

    compact_bucket_points = []
    for item in bucket_outputs[:8]:
        compact_bucket_points.append({
            "bucket_key": item.get("bucket_key"),
            "point": item.get("point"),
            "relation_to_step1": item.get("relation_to_step1"),
            "certainty": item.get("certainty"),
        })

    return {
        # ── 原有字段 ────────────────────────────────────────────────
        "step1_core": (step1_text or "")[:3000],
        "step3_selected_buckets": selected_buckets,
        "step3_key_unknowns": still_unresolved[:8],
        "step3_tensions": tensions[:6],
        "step3_hints": adjustment_hints,
        "step3_bucket_points": compact_bucket_points,
        "bp_signals": bp_signals,
        # ── 新增：Step3 新版结构 ──────────────────────────────────────
        "project_structure": project_structure,
        # ── 新增：Step3B 整合 ────────────────────────────────────────
        "step3b_summary": step3b_summary,
        "step3b_consistency_checks": step3b_checks,
        "step3b_tensions": step3b_tensions,
        "step3b_packaging_signals": step3b_packaging,
        # ── 新增：合并决策缺口候选 ───────────────────────────────────
        "decision_gap_candidates": decision_gap_candidates,
    }
