# -*- coding: utf-8 -*-
"""
storage.py — BP 反馈样本持久化

存储格式：JSONL（每行一个 JSON，便于追加读取）
存储位置：knowledge_base/feedback/bp_review_feedback.jsonl
"""

import json
import os
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List, Optional


def _get_project_root() -> str:
    # services/feedback/storage.py → services/ → 项目根目录
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


FEEDBACK_DIR = os.path.join(_get_project_root(), "knowledge_base", "feedback")
FEEDBACK_FILE = os.path.join(FEEDBACK_DIR, "bp_review_feedback.jsonl")
CANDIDATES_DIR = os.path.join(FEEDBACK_DIR, "candidates")


def ensure_dirs():
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    os.makedirs(CANDIDATES_DIR, exist_ok=True)


def generate_feedback_id() -> str:
    return f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"


def append_feedback_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    追加一条 feedback case 到 jsonl 文件。
    如果没有 feedback_id / created_at，自动补全。
    """
    ensure_dirs()

    if not case.get("feedback_id"):
        case["feedback_id"] = generate_feedback_id()

    if not case.get("created_at"):
        case["created_at"] = datetime.now().isoformat()

    # 每次追加完整的 case（不做 update，而是追加最新版）
    # 读取现有文件，如果已存在相同 feedback_id 则替换那一行
    existing_lines = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_cases = json.loads(line)
                    if existing_cases.get("feedback_id") != case["feedback_id"]:
                        existing_lines.append(line)

    # 写入：先写所有保留的旧记录，再追加新记录
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        for old_line in existing_lines:
            f.write(old_line)
        f.write(json.dumps(case, ensure_ascii=False) + "\n")

    return case


def load_feedback_cases(profile_id: Optional[str] = None,
                        review_status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    读取所有 feedback cases。
    可按 profile_id 或 review_status 过滤。
    """
    ensure_dirs()
    if not os.path.exists(FEEDBACK_FILE):
        return []

    cases = []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    if profile_id:
        cases = [c for c in cases if c.get("profile_id") == profile_id]

    if review_status:
        cases = [c for c in cases if c.get("review_status") == review_status]

    return cases


def find_feedback_case(feedback_id: str) -> Optional[Dict[str, Any]]:
    """根据 feedback_id 查找单条记录"""
    for case in load_feedback_cases():
        if case.get("feedback_id") == feedback_id:
            return case
    return None


def find_feedback_by_project(project_id: str) -> Optional[Dict[str, Any]]:
    """根据 project_id 查找最新一条记录"""
    for case in reversed(load_feedback_cases()):
        if case.get("project_id") == project_id:
            return case
    return None
