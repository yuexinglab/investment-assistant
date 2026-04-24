"""
project_manager.py — 项目存储管理
负责：创建项目目录、保存/加载各类文件、维护项目上下文
"""

import os
import json
from datetime import datetime
from config import WORKSPACE_DIR


def _slugify(name: str) -> str:
    """把中文公司名 + 时间戳组合成目录名"""
    import re
    # 保留中文、字母、数字，其他换成下划线
    clean = re.sub(r"[^\w\u4e00-\u9fff]", "_", name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{clean}_{ts}"


def create_project(company_name: str) -> str:
    """
    创建项目目录，初始化 meta.json 和子目录
    返回：项目目录的绝对路径
    """
    dir_name = _slugify(company_name)
    project_dir = os.path.join(WORKSPACE_DIR, dir_name)

    for sub in ["materials", "parsed", "reports", "question_trees"]:
        os.makedirs(os.path.join(project_dir, sub), exist_ok=True)

    meta = {
        "company_name": company_name,
        "created_at": datetime.now().isoformat(),
        "status": "created",   # created → v1_done → v2_done
        "reports": [],
        "question_trees": [],
    }
    _write_json(os.path.join(project_dir, "meta.json"), meta)

    # 初始化空的上下文文件
    _write_json(os.path.join(project_dir, "context.json"), {
        "latest_v1_report": None,
        "latest_v2_report": None,
        "question_tree_v1": None,
        "question_tree_v2": None,
    })

    return project_dir


def list_projects() -> list:
    """列出所有项目（按创建时间倒序）"""
    if not os.path.exists(WORKSPACE_DIR):
        return []

    projects = []
    for dir_name in os.listdir(WORKSPACE_DIR):
        project_dir = os.path.join(WORKSPACE_DIR, dir_name)
        meta_path = os.path.join(project_dir, "meta.json")
        if os.path.isdir(project_dir) and os.path.exists(meta_path):
            meta = _read_json(meta_path)
            meta["project_id"] = dir_name
            # 检查是否有 v2.5 报告
            context_path = os.path.join(project_dir, "context.json")
            if os.path.exists(context_path):
                ctx = _read_json(context_path)
                meta["has_v2_5"] = ctx.get("latest_v2_5_report") is not None
            else:
                meta["has_v2_5"] = False
            projects.append(meta)

    projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return projects


def get_project_meta(project_dir: str) -> dict:
    """读取项目 meta.json"""
    return _read_json(os.path.join(project_dir, "meta.json"))


def save_report(project_dir: str, version: str, report_content: dict):
    """
    保存报告到 reports/ 目录，并更新 context.json
    version: "v1_0" | "v2_0" | "v2_5" 等
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{version}_{ts}.json"
    report_path = os.path.join(project_dir, "reports", filename)
    _write_json(report_path, report_content)

    # 更新 context.json
    context = load_project_context(project_dir)
    if version.startswith("v1"):
        context["latest_v1_report"] = report_content
    elif version == "v2_5":
        context["latest_v2_5_report"] = report_content
    elif version.startswith("v2"):
        context["latest_v2_report"] = report_content
    _write_json(os.path.join(project_dir, "context.json"), context)

    # 更新 meta.json 的报告列表
    meta = get_project_meta(project_dir)
    meta.setdefault("reports", []).append({"version": version, "filename": filename, "saved_at": ts})
    if version == "v1_0":
        meta["status"] = "v1_done"
    elif version == "v2_5":
        meta["status"] = "v2_5_done"
    elif version.startswith("v2"):
        meta["status"] = "v2_done"
    _write_json(os.path.join(project_dir, "meta.json"), meta)


def save_question_tree(project_dir: str, version: str, questions: list):
    """保存问题树到 question_trees/ 目录"""
    filename = f"questions_{version}.json"
    path = os.path.join(project_dir, "question_trees", filename)
    _write_json(path, questions)

    # 同步到 context
    context = load_project_context(project_dir)
    if version == "v1":
        context["question_tree_v1"] = questions
    elif version == "v2":
        context["question_tree_v2"] = questions
    _write_json(os.path.join(project_dir, "context.json"), context)


def load_project_context(project_dir: str) -> dict:
    """加载完整上下文（含最新报告和问题树）"""
    ctx_path = os.path.join(project_dir, "context.json")
    if not os.path.exists(ctx_path):
        return {}
    return _read_json(ctx_path)


# ---- 内部工具 ----

def _write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
