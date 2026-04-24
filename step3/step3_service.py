from __future__ import annotations

from typing import Callable, List, Optional

from step3.step3_parser import parse_step3_output
from step3.step3_prompt import build_step3_prompt


DEFAULT_BUCKET_MAPPING = {
    "ai": "tech_barrier",
    "技术": "tech_barrier",
    "平台": "tech_barrier",
    "壁垒": "tech_barrier",
    "客户": "customer_value",
    "付钱": "customer_value",
    "收入": "commercialization",
    "订单": "commercialization",
    "商业化": "commercialization",
    "扩张": "expansion_story",
    "多行业": "expansion_story",
    "第二曲线": "expansion_story",
    "诺奖": "team_credibility",
    "院士": "team_credibility",
    "博士": "team_credibility",
    "团队": "team_credibility",
}


def simple_bucket_selector(step1_text: str, max_buckets: int = 3) -> List[str]:
    hits: List[str] = []
    lowered = step1_text.lower()

    for keyword, bucket in DEFAULT_BUCKET_MAPPING.items():
        if keyword in step1_text or keyword in lowered:
            if bucket not in hits:
                hits.append(bucket)

    if not hits:
        hits = ["tech_barrier", "commercialization", "customer_value"]

    return hits[:max_buckets]


class Step3Service:
    def __init__(self, call_llm: Callable[[str, str], str]):
        self.call_llm = call_llm

    def run(
        self,
        *,
        step1_text: str,
        bp_text: str,
        industry: str,
        external_context: Optional[str] = None,
        selected_buckets: Optional[List[str]] = None,
    ):
        if not selected_buckets:
            selected_buckets = simple_bucket_selector(step1_text)

        prompt = build_step3_prompt(
            step1_text=step1_text,
            bp_text=bp_text,
            industry=industry,
            selected_buckets=selected_buckets,
            external_context=external_context,
        )

        raw = self.call_llm(
            "你是一位严谨的投资研究员。请严格输出合法 JSON，不要输出多余解释。",
            prompt,
        )
        return parse_step3_output(raw)
