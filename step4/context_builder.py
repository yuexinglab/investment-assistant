from __future__ import annotations

import json
from typing import Any, Dict, List


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


def _safe_load_step3(step3_json: str | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(step3_json, dict):
        return step3_json
    try:
        return json.loads(step3_json)
    except Exception:
        return {}


def build_step4_context(
    *,
    step1_text: str,
    step3_json: str | Dict[str, Any],
    bp_text: str,
) -> Dict[str, Any]:
    step3_obj = _safe_load_step3(step3_json)

    still_unresolved = step3_obj.get("still_unresolved", [])
    tensions = step3_obj.get("tensions", [])
    adjustment_hints = step3_obj.get("step1_adjustment_hints", {})
    selected_buckets = step3_obj.get("selected_buckets", [])
    bucket_outputs = step3_obj.get("bucket_outputs", [])

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
        "step1_core": (step1_text or "")[:3000],
        "step3_selected_buckets": selected_buckets,
        "step3_key_unknowns": still_unresolved[:8],
        "step3_tensions": tensions[:6],
        "step3_hints": adjustment_hints,
        "step3_bucket_points": compact_bucket_points,
        "bp_signals": bp_signals,
    }
