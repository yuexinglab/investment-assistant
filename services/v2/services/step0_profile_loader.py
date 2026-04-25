# -*- coding: utf-8 -*-
"""
step0_profile_loader.py — Step0: 投资人/基金画像加载

作用：
1. 加载预设的基金/用户画像
2. 支持用户自定义画像
3. 输出 fit_questions 用于反哺 Step7

原则：
- 画像只用于 Step10 Fit 判断，不影响 Step6-9 的项目判断
- 画像不影响事实提取，只影响"适不适合我"的判断
"""
import json
import os
from typing import Dict, Any, Optional

from ..schemas import (
    Step0ProfileOutput, ProfileType,
    HardConstraint, Preference, Avoidance
)


def get_kb_root() -> str:
    """获取知识库根目录"""
    # services/v2/services/step0_profile_loader.py → 项目根目录
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(current_dir, "knowledge_base")


def list_available_profiles() -> list:
    """列出可用的基金/用户画像"""
    kb_root = get_kb_root()
    profiles = []

    # 基金画像
    fund_dir = os.path.join(kb_root, "profiles", "fund_profiles")
    if os.path.exists(fund_dir):
        for f in os.listdir(fund_dir):
            if f.endswith(".json"):
                with open(os.path.join(fund_dir, f), "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    profiles.append({
                        "profile_id": data.get("profile_id", ""),
                        "profile_type": "fund",
                        "name": data.get("name", ""),
                        "description": data.get("description", "")
                    })

    # 用户画像
    user_dir = os.path.join(kb_root, "profiles", "user_profiles")
    if os.path.exists(user_dir):
        for f in os.listdir(user_dir):
            if f.endswith(".json"):
                with open(os.path.join(user_dir, f), "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    profiles.append({
                        "profile_id": data.get("profile_id", ""),
                        "profile_type": "user",
                        "name": data.get("name", ""),
                        "description": data.get("description", "")
                    })

    return profiles


def load_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """
    加载指定画像

    Args:
        profile_id: 画像ID，如 "government_fund", "vc_fund"

    Returns:
        画像数据 dict，或 None（未找到）
    """
    kb_root = get_kb_root()

    # 尝试加载基金画像
    fund_path = os.path.join(kb_root, "profiles", "fund_profiles", f"{profile_id}.json")
    if os.path.exists(fund_path):
        with open(fund_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 尝试加载用户画像
    user_path = os.path.join(kb_root, "profiles", "user_profiles", f"{profile_id}.json")
    if os.path.exists(user_path):
        with open(user_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None


def load_or_create_profile(
    profile_id: Optional[str] = None,
    user_description: str = ""
) -> Step0ProfileOutput:
    """
    加载或创建画像

    Args:
        profile_id: 已有画像ID，若为 None 则根据 user_description 匹配或创建
        user_description: 用户描述（用于生成新画像）

    Returns:
        Step0ProfileOutput 对象
    """
    # 如果指定了 profile_id，尝试加载
    if profile_id:
        data = load_profile(profile_id)
        if data:
            return _dict_to_profile(data)

    # 如果没有指定，检查用户描述是否暗示了某种基金类型
    if user_description:
        # 简单规则匹配
        desc_lower = user_description.lower()
        if "政府" in user_description or "引导基金" in user_description or "产业基金" in user_description:
            data = load_profile("government_fund")
            if data:
                return _dict_to_profile(data)
        elif "vc" in desc_lower or "风险投资" in user_description or "风投" in user_description:
            data = load_profile("vc_fund")
            if data:
                return _dict_to_profile(data)

    # 默认返回政府基金画像（根据用户当前项目）
    data = load_profile("government_fund")
    if data:
        return _dict_to_profile(data)

    # 如果连默认画像都没有，创建一个空的
    return Step0ProfileOutput(
        profile_id="unknown",
        profile_type=ProfileType.FUND,
        name="未定义基金",
        description="请在 knowledge_base 中配置基金画像"
    )


def _dict_to_profile(data: Dict[str, Any]) -> Step0ProfileOutput:
    """将 dict 转为 Step0ProfileOutput"""
    profile_type_str = data.get("profile_type", "fund")
    profile_type = ProfileType.USER if profile_type_str == "user" else ProfileType.FUND

    # 解析硬约束
    hard_constraints = []
    for hc in data.get("hard_constraints", []):
        hard_constraints.append(HardConstraint(
            key=hc.get("key", ""),
            description=hc.get("description", ""),
            priority=hc.get("priority", "high"),
            examples=hc.get("examples", [])
        ))

    # 解析偏好
    preferences = []
    for p in data.get("preferences", []):
        preferences.append(Preference(
            key=p.get("key", ""),
            description=p.get("description", ""),
            priority=p.get("priority", "medium"),
            weight=p.get("weight", 0.2)
        ))

    # 解析回避项
    avoid_list = []
    for a in data.get("avoid", []):
        avoid_list.append(Avoidance(
            key=a.get("key", ""),
            description=a.get("description", ""),
            priority=a.get("priority", "medium"),
            severity=a.get("severity", "medium")
        ))

    return Step0ProfileOutput(
        profile_id=data.get("profile_id", ""),
        profile_type=profile_type,
        name=data.get("name", ""),
        description=data.get("description", ""),
        hard_constraints=hard_constraints,
        preferences=preferences,
        avoid=avoid_list,
        fit_questions=data.get("fit_questions", [])
    )


def to_dict(output: Step0ProfileOutput) -> Dict[str, Any]:
    """将 Step0ProfileOutput 转为 dict（用于持久化）"""
    return {
        "profile_id": output.profile_id,
        "profile_type": output.profile_type.value if output.profile_type else "fund",
        "name": output.name,
        "description": output.description,
        "hard_constraints": [
            {
                "key": hc.key,
                "description": hc.description,
                "priority": hc.priority,
                "examples": hc.examples
            }
            for hc in output.hard_constraints
        ],
        "preferences": [
            {
                "key": p.key,
                "description": p.description,
                "priority": p.priority,
                "weight": p.weight
            }
            for p in output.preferences
        ],
        "avoid": [
            {
                "key": a.key,
                "description": a.description,
                "priority": a.priority,
                "severity": a.severity
            }
            for a in output.avoid
        ],
        "fit_questions": output.fit_questions
    }
