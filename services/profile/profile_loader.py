# -*- coding: utf-8 -*-
"""
profile_loader.py — 投资人 / 基金画像加载器

核心原则：
1. 默认只能是 neutral_investor，不能默认 government_fund
2. Profile 用于 Step0 / Step3 / Step4 / Step5 / Step7 / Step10
3. Step6 禁止使用 profile（只做事实提取）
4. Profile 只影响"问什么"和"适不适合"，不污染"事实是什么"

使用强度：
- Step0: 强使用（选择/创建投资人画像）
- Step1: 弱使用（只辅助识别项目是否可能匹配）
- Step3/4/5: 中使用（生成 profile 相关问题和会前判断）
- Step6: 禁止使用（只提取事实）
- Step7: 中使用（检查 profile 相关问题是否被回答）
- Step8: 弱使用（可标注对 profile 的影响）
- Step9: 弱使用（项目层决策，最多给 fit_hint）
- Step10: 强使用（做最终 fit 判断）
"""

import json
import os
from typing import Dict, Any, List, Optional


# 默认 profile：必须是 neutral_investor
DEFAULT_PROFILE_ID = "neutral_investor"


def get_kb_root() -> str:
    """获取知识库根目录"""
    # services/profile/profile_loader.py → services/ → 项目根目录
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # current_dir 现在是 services/，需要再往上一级到项目根目录
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, "knowledge_base")


def list_fund_profiles() -> List[Dict[str, Any]]:
    """
    列出可选 fund profiles，用于前端选择。

    Returns:
        列表，每个元素包含 profile_id, name, description
    """
    kb_root = get_kb_root()
    profiles = []

    fund_dir = os.path.join(kb_root, "profiles", "fund_profiles")
    if not os.path.exists(fund_dir):
        return profiles

    for filename in os.listdir(fund_dir):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(fund_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            profiles.append({
                "profile_id": data.get("profile_id", ""),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "profile_type": "fund",
                "is_default": data.get("profile_id") == DEFAULT_PROFILE_ID
            })
        except Exception:
            continue

    # 按 is_default 排序（默认的放最前面）
    profiles.sort(key=lambda x: (not x.get("is_default", False), x.get("name", "")))

    return profiles


def load_profile(profile_id: str = None) -> Dict[str, Any]:
    """
    加载指定 profile。

    Args:
        profile_id: 画像ID，如 "neutral_investor", "government_fund", "vc_fund"
                   如果为 None 或空，默认使用 neutral_investor

    Returns:
        画像数据 dict
    """
    # 确保有默认值
    if not profile_id:
        profile_id = DEFAULT_PROFILE_ID

    # 安全化：只取基本名字符
    safe_profile_id = "".join(c for c in profile_id if c.isalnum() or c == "_")

    kb_root = get_kb_root()
    fund_path = os.path.join(kb_root, "profiles", "fund_profiles", f"{safe_profile_id}.json")

    if os.path.exists(fund_path):
        with open(fund_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 如果找不到，加载默认的 neutral_investor
    default_path = os.path.join(kb_root, "profiles", "fund_profiles", f"{DEFAULT_PROFILE_ID}.json")
    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 兜底：返回空 profile
    return {
        "profile_id": DEFAULT_PROFILE_ID,
        "profile_type": "fund",
        "name": "中性投资人",
        "description": "默认画像",
        "hard_constraints": [],
        "preferences": [],
        "avoid": [],
        "fit_questions": []
    }


def load_project_profile(project_dir: str) -> Dict[str, Any]:
    """
    从项目目录加载已保存的 profile。

    Args:
        project_dir: 项目工作目录

    Returns:
        项目保存的 profile，如果不存在则返回 neutral_investor
    """
    # 优先从 step0/ 目录加载
    step0_path = os.path.join(project_dir, "step0", "step0.json")
    if os.path.exists(step0_path):
        with open(step0_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 老项目没有 step0，默认 neutral
    return load_profile(DEFAULT_PROFILE_ID)


def save_project_profile(project_dir: str, profile: Dict[str, Any]) -> None:
    """
    保存项目 profile 到 step0/step0.json。

    Args:
        project_dir: 项目工作目录
        profile: profile dict
    """
    step0_dir = os.path.join(project_dir, "step0")
    os.makedirs(step0_dir, exist_ok=True)

    step0_path = os.path.join(step0_dir, "step0.json")
    with open(step0_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def get_profile_summary(profile: Dict[str, Any]) -> str:
    """
    获取 profile 的简要摘要（用于 UI 显示）。

    Args:
        profile: profile dict

    Returns:
        格式化的摘要字符串
    """
    name = profile.get("name", "")
    hard_count = len(profile.get("hard_constraints", []))
    pref_count = len(profile.get("preferences", []))
    avoid_count = len(profile.get("avoid", []))

    parts = [name]
    if hard_count > 0:
        parts.append(f"硬约束 {hard_count} 项")
    if pref_count > 0:
        parts.append(f"偏好 {pref_count} 项")
    if avoid_count > 0:
        parts.append(f"回避 {avoid_count} 项")

    return " | ".join(parts)


def get_fit_questions_for_profile(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从 profile 中提取 fit_questions，格式化为带 source 的列表。

    Args:
        profile: profile dict

    Returns:
        问题列表，每个元素包含 question, source, profile_id
    """
    fit_questions = profile.get("fit_questions", [])
    profile_id = profile.get("profile_id", "neutral_investor")

    return [
        {
            "question": q,
            "source": "profile",
            "profile_id": profile_id,
            "priority": "high"  # profile questions 默认高优先级
        }
        for q in fit_questions
    ]


def merge_base_and_profile_questions(
    base_questions: List[str],
    profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    合并基础问题和 profile 问题。

    Args:
        base_questions: 基础问题列表（字符串）
        profile: profile dict

    Returns:
        合并后的问题列表，每个元素包含 question_id, question, source, priority
    """
    questions = []

    # 基础问题
    for i, q in enumerate(base_questions):
        questions.append({
            "question_id": f"q_base_{i+1:03d}",
            "question": q,
            "source": "base",
            "profile_id": None,
            "priority": "medium"
        })

    # Profile 问题
    fit_questions = get_fit_questions_for_profile(profile)
    for i, item in enumerate(fit_questions):
        questions.append({
            "question_id": f"q_fit_{i+1:03d}",
            "question": item["question"],
            "source": "profile",
            "profile_id": item["profile_id"],
            "priority": item.get("priority", "high")
        })

    return questions


def extract_profile_constraints(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取 profile 的约束结构（用于 Step10）。

    Returns:
        包含 hard_constraints, preferences, avoid 的结构化 dict
    """
    return {
        "hard_constraints": profile.get("hard_constraints", []),
        "preferences": profile.get("preferences", []),
        "avoid": profile.get("avoid", []),
        "profile_id": profile.get("profile_id", ""),
        "name": profile.get("name", "")
    }
