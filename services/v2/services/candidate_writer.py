# -*- coding: utf-8 -*-
"""
candidate_writer.py — 知识沉淀候选写入服务

作用：
将所有沉淀内容写入 candidates/ 目录，等待人工审核后入库。

原则：
1. 所有沉淀都先进入 candidates，不自动入正式库
2. 每个候选条目都标注来源和时间
3. 支持增量追加（不去重，由人工判断是否重复）
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List


def get_kb_root() -> str:
    """获取知识库根目录"""
    # services/v2/services/candidate_writer.py → 项目根目录
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(current_dir, "knowledge_base")


class CandidateWriter:
    """
    知识沉淀候选写入器

    使用方式：
    writer = CandidateWriter()
    writer.append_candidate("profile_candidates", item)
    """

    def __init__(self, kb_root: str = None):
        self.kb_root = kb_root or get_kb_root()
        self.candidates_dir = os.path.join(self.kb_root, "candidates")
        os.makedirs(self.candidates_dir, exist_ok=True)

    def append_candidate(self, bucket: str, item: Dict[str, Any]):
        """
        追加候选条目到指定 bucket

        Args:
            bucket: 候选类型，如 "profile_candidates", "question_candidates"
            item: 候选条目 dict
        """
        path = os.path.join(self.candidates_dir, f"{bucket}.json")

        # 读取现有数据
        data = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                data = []

        # 添加元数据
        item.setdefault("status", "pending_review")
        item.setdefault("created_at", datetime.now().isoformat())
        item.setdefault("created_by", "Step10")

        # 追加
        data.append(item)

        # 写入
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def append_fit_feedback(
        self,
        project_name: str,
        fit_decision: str,
        final_decision: str,
        fit_reason: List[str],
        project_judgement: str = "",
        source_profile: str = ""
    ):
        """
        追加 Fit 反馈候选

        Args:
            project_name: 项目名称
            fit_decision: fit/partial_fit/not_fit
            final_decision: continue/request_materials/pass
            fit_reason: Fit 原因列表
            project_judgement: 项目判断摘要
            source_profile: 来源画像 ID
        """
        item = {
            "project_name": project_name,
            "project_judgement": project_judgement,
            "fit_judgement": fit_decision,
            "final_decision": final_decision,
            "fit_reason": fit_reason,
            "source_profile": source_profile,
            "status": "pending_review",
            "created_at": datetime.now().isoformat(),
            "created_by": "Step10"
        }
        self.append_candidate("fit_feedback_candidates", item)

    def append_profile_update(
        self,
        profile_id: str,
        candidate_rule: str,
        evidence: str
    ):
        """
        追加画像更新候选

        Args:
            profile_id: 画像 ID
            candidate_rule: 候选规则
            evidence: 证据
        """
        item = {
            "profile_id": profile_id,
            "candidate_rule": candidate_rule,
            "evidence": evidence,
            "should_review": True,
            "status": "pending_review",
            "created_at": datetime.now().isoformat(),
            "created_by": "Step10"
        }
        self.append_candidate("profile_candidates", item)

    def get_candidates(self, bucket: str) -> List[Dict[str, Any]]:
        """
        读取候选列表

        Args:
            bucket: 候选类型

        Returns:
            候选列表
        """
        path = os.path.join(self.candidates_dir, f"{bucket}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def list_buckets(self) -> List[str]:
        """列出所有候选 bucket"""
        if os.path.exists(self.candidates_dir):
            return [
                f.replace(".json", "")
                for f in os.listdir(self.candidates_dir)
                if f.endswith(".json")
            ]
        return []


# 全局实例（懒加载）
_writer = None


def get_writer() -> CandidateWriter:
    """获取全局 CandidateWriter 实例"""
    global _writer
    if _writer is None:
        _writer = CandidateWriter()
    return _writer
