from __future__ import annotations

import importlib
from typing import Any, Dict


def load_industry_enhancements(industry: str) -> Dict[str, Any]:
    try:
        module = importlib.import_module(f"step3.industries.{industry}")
    except ModuleNotFoundError as e:
        raise ValueError(f"未找到行业插件: {industry}") from e

    if not hasattr(module, "ENHANCEMENTS"):
        raise ValueError(f"行业插件 {industry} 缺少 ENHANCEMENTS 定义")

    return getattr(module, "ENHANCEMENTS")
