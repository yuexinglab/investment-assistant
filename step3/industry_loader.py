from __future__ import annotations

import importlib
from typing import Any, Dict


def load_industry_enhancements(industry: str) -> Dict[str, Any]:
    # general 或空字符串使用通用框架（不做行业增强）
    if not industry or industry == "general":
        return {}

    try:
        module = importlib.import_module(f"step3.industries.{industry}")
    except ModuleNotFoundError as e:
        # 未找到行业插件，降级为通用框架
        return {}

    if not hasattr(module, "ENHANCEMENTS"):
        raise ValueError(f"行业插件 {industry} 缺少 ENHANCEMENTS 定义")

    return getattr(module, "ENHANCEMENTS")
