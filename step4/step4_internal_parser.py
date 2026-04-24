from __future__ import annotations

import json
import re
from typing import Any

from step4.step4_internal_schema import Step4InternalOutput


def extract_json_block(text: str) -> str:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match:
        return match.group(1)

    match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if match:
        return match.group(1)

    raise ValueError("未能从 Step4 internal 模型输出中提取 JSON。")


def parse_step4_internal_output(raw_text: str) -> Step4InternalOutput:
    raw_json = extract_json_block(raw_text)
    data: Any = json.loads(raw_json)
    obj = Step4InternalOutput.model_validate(data)
    return obj
