from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Relation = Literal["support", "contradict", "neutral"]
Certainty = Literal["high", "medium", "low"]
SourceType = Literal["common_sense", "bp", "external_context", "unknown"]


class Step3EvidenceItem(BaseModel):
    bucket_key: str
    bucket_label: str
    point: str
    explanation: str
    relation_to_step1: Relation
    certainty: Certainty
    source_type: SourceType


class Step3PublicInfoItem(BaseModel):
    bucket_key: str
    item: str
    current_conclusion: str
    confidence: Certainty


class Step3UnresolvedItem(BaseModel):
    bucket_key: str
    question: str
    why_unresolved: str
    impact_level: Literal["high", "medium", "low"]


class Step3AdjustmentHints(BaseModel):
    supported: List[str] = Field(default_factory=list)
    caution: List[str] = Field(default_factory=list)
    to_step4: List[str] = Field(default_factory=list)


class Step3Output(BaseModel):
    selected_buckets: List[str]
    bucket_outputs: List[Step3EvidenceItem]
    publicly_resolvable: List[Step3PublicInfoItem]
    still_unresolved: List[Step3UnresolvedItem] = Field(default_factory=list)
    tensions: List[str] = Field(default_factory=list)
    step1_adjustment_hints: Step3AdjustmentHints
    raw_text: Optional[str] = None
