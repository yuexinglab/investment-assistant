# -*- coding: utf-8 -*-
"""
investment_modules - 投资思维模块库

用于在 Step3B 和 Step5 中加载和使用投资思维模块。
"""

from .module_loader import load_investment_modules, select_relevant_modules, format_modules_for_prompt

__all__ = [
    "load_investment_modules",
    "select_relevant_modules",
    "format_modules_for_prompt",
]
