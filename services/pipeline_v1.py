# -*- coding: utf-8 -*-
"""
pipeline_v1.py — 1.0 会前分析新流程

Step1 → Step3 → Step4 → Step5 串行执行
支持步骤级回调（用于 SSE 进度推送）

依赖关系：
  Step3 ← Step1
  Step4 ← Step1 + Step3
  Step5 ← Step1 + Step3 + Step4(internal)
"""

from __future__ import annotations

import json
import os
from typing import Callable, Optional

from services.deepseek_service import call_deepseek


# ─── Step1 服务（inline，不需要独立模块）────────────────────────────────────────

STEP1_SYSTEM = (
    "你是一位资深投资人兼业务理解专家。"
    "你现在的任务是：读完一份 BP，输出一份清晰的初步判断。"
    "风格：有观点、有逻辑、不废话。不要大量引用原文，要形成判断。"
)

STEP1_USER_TEMPLATE = """
请对以下BP进行初步判断，输出：

一、【这家公司本质上是什么 / 不是什么】
- 一句话定位
- 2-3条关键判断

二、【初步看法】
- 这个方向靠谱吗？
- 最值得关注的亮点是什么？
- 最大的疑问是什么？

三、【需要重点了解的问题】
- 3-5个关键问题（会前就想知道的）

---

BP 全文：

{bp_text}
"""


def run_step1(bp_text: str) -> str:
    """运行 Step1 初步判断"""
    prompt = STEP1_USER_TEMPLATE.format(bp_text=bp_text)
    return call_deepseek(
        system_prompt=STEP1_SYSTEM,
        user_prompt=prompt,
        max_retries=2
    )


# ─── 行业检测 ──────────────────────────────────────────────────────────────

INDUSTRY_KEYWORDS = {
    "commercial_space": [
        "航天", "卫星", "火箭", "发射", "太空", "轨道", "火箭箭体",
        "运载火箭", "低轨", "LEO", "GEO", "航天器", "SpaceX", "Starlink",
        "星际荣耀", "蓝箭", "星河动力", "天兵科技", "东方空间",
    ],
    "advanced_materials": [
        "材料", "化学", "分子", "超分子", "美妆", "原料", "配方",
        "生物基", "降解", "日化", "香精", "香料", "表面活性剂",
        "纳米", "聚合物", "合成", "催化剂", "制剂", "功能性材料",
    ],
}


def detect_industry(text: str) -> str:
    """
    根据文本关键词推断行业。
    优先匹配 commercial_space（更细分），否则默认 advanced_materials。
    """
    text_lower = text.lower()
    scores = {}
    for ind, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[ind] = score
    best = max(scores, key=lambda k: scores[k])
    # 只有得分 >= 2 才认定，否则用默认
    if scores[best] >= 2:
        return best
    return "advanced_materials"


# ─── Step3 服务 ─────────────────────────────────────────────────────────────

def run_step3(bp_text: str, step1_text: str) -> dict:
    """运行 Step3 背景分析，返回 dict"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from step3.step3_service import Step3Service

    # 自动检测行业（兜底 advanced_materials）
    industry = detect_industry(bp_text + step1_text)

    def _call_llm(system_prompt: str, user_prompt: str) -> str:
        return call_deepseek(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_retries=2
        )

    service = Step3Service(call_llm=_call_llm)
    result = service.run(
        step1_text=step1_text,
        bp_text=bp_text,
        industry=industry,
    )

    # 返回 dict
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)


# ─── Step4 服务 ─────────────────────────────────────────────────────────────

def run_step4(bp_text: str, step1_text: str, step3_json: dict) -> dict:
    """
    运行 Step4，返回 dict 包含：
      - internal: Step4 internal 原始 dict
      - meeting_brief_md: 会前提纲 Markdown 字符串
      - scan_questions: 基础扫描 dict
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from step4.step4_service import Step4Service

    def _call_llm(system_prompt: str, user_prompt: str) -> str:
        return call_deepseek(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_retries=2
        )

    service = Step4Service(call_llm=_call_llm)
    # Step4 期望 step3_json 为 JSON 字符串
    step3_str = json.dumps(step3_json, ensure_ascii=False) if isinstance(step3_json, dict) else step3_json
    result = service.run(
        bp_text=bp_text,
        step1_text=step1_text,
        step3_json=step3_str
    )

    # result 是 Step4Service 的统一输出
    # 返回结构化 dict
    output = {}

    # 会前提纲（meeting_brief_md）
    if hasattr(result, "meeting_brief_md"):
        output["meeting_brief_md"] = result.meeting_brief_md
    elif isinstance(result, dict) and "meeting_brief_md" in result:
        output["meeting_brief_md"] = result["meeting_brief_md"]
    else:
        output["meeting_brief_md"] = str(result)

    # internal JSON
    if hasattr(result, "internal"):
        internal = result.internal
        if hasattr(internal, "model_dump"):
            output["internal"] = internal.model_dump()
        else:
            output["internal"] = dict(internal) if internal else {}
    elif isinstance(result, dict) and "internal" in result:
        output["internal"] = result["internal"]
    else:
        output["internal"] = {}

    # scan_questions
    if hasattr(result, "scan_questions"):
        sq = result.scan_questions
        output["scan_questions"] = dict(sq) if sq else {}
    elif isinstance(result, dict) and "scan_questions" in result:
        output["scan_questions"] = result["scan_questions"]
    else:
        output["scan_questions"] = {}

    return output


# ─── Step5 服务 ─────────────────────────────────────────────────────────────

def run_step5(step1_text: str, step3_json: dict, step4_internal: dict) -> dict:
    """运行 Step5，返回 dict"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from step5.step5_service import Step5Service

    def _call_llm(system_prompt: str, user_prompt: str) -> str:
        return call_deepseek(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_retries=2
        )

    service = Step5Service(call_llm=_call_llm)
    result = service.run(
        step1_text=step1_text,
        step3_json=step3_json,
        step4_internal=step4_internal
    )

    if hasattr(result, "model_dump"):
        data = result.model_dump()
    else:
        data = dict(result)

    # 同时生成 Markdown 版本
    if hasattr(result, "to_markdown"):
        data["decision_md"] = result.to_markdown()

    return data


# ─── 主流程编排 ──────────────────────────────────────────────────────────────

def run_pipeline_v1(
    bp_text: str,
    project_dir: str,
    on_progress: Optional[Callable[[str, str, int], None]] = None
) -> dict:
    """
    完整 1.0 会前分析流程：Step1 → Step3 → Step4 → Step5

    Args:
        bp_text: BP 原文
        project_dir: 项目目录（用于保存中间文件）
        on_progress: 进度回调 fn(step_name: str, status: str, percent: int)
                     status: "running" | "done" | "error"

    Returns:
        完整结果 dict，包含 step1/step3/step4/step5
    """

    def emit(step: str, status: str, percent: int, msg: str = ""):
        if on_progress:
            on_progress(step, status, percent, msg)

    results = {}

    # ── Step1 ────────────────────────────────────────────────
    emit("step1", "running", 5, "正在理解公司业务...")
    try:
        step1_text = run_step1(bp_text)
        results["step1"] = step1_text
        _save_step(project_dir, "step1", "step1.txt", step1_text)
        emit("step1", "done", 25, "初步判断完成")
    except Exception as e:
        emit("step1", "error", 25, f"Step1 失败: {e}")
        raise RuntimeError(f"Step1 失败: {e}")

    # ── Step3 ────────────────────────────────────────────────
    emit("step3", "running", 30, "正在分析行业背景...")
    try:
        step3_json = run_step3(bp_text, step1_text)
        results["step3"] = step3_json
        _save_step(project_dir, "step3", "step3.json", json.dumps(step3_json, ensure_ascii=False, indent=2))
        emit("step3", "done", 50, "背景分析完成")
    except Exception as e:
        emit("step3", "error", 50, f"Step3 失败: {e}")
        raise RuntimeError(f"Step3 失败: {e}")

    # ── Step4 ────────────────────────────────────────────────
    emit("step4", "running", 55, "正在生成开会问题...")
    try:
        step4_result = run_step4(bp_text, step1_text, step3_json)
        results["step4"] = step4_result
        _save_step(project_dir, "step4", "step4_meeting_brief.md", step4_result.get("meeting_brief_md", ""))
        _save_step(project_dir, "step4", "step4_internal.json",
                   json.dumps(step4_result.get("internal", {}), ensure_ascii=False, indent=2))
        _save_step(project_dir, "step4", "step4_scan_questions.json",
                   json.dumps(step4_result.get("scan_questions", {}), ensure_ascii=False, indent=2))
        emit("step4", "done", 75, "开会问题生成完成")
    except Exception as e:
        emit("step4", "error", 75, f"Step4 失败: {e}")
        raise RuntimeError(f"Step4 失败: {e}")

    # ── Step5 ────────────────────────────────────────────────
    emit("step5", "running", 80, "正在整理判断逻辑...")
    try:
        step4_internal = step4_result.get("internal", {})
        step5_result = run_step5(step1_text, step3_json, step4_internal)
        results["step5"] = step5_result
        _save_step(project_dir, "step5", "step5_decision.md", step5_result.get("decision_md", ""))
        _save_step(project_dir, "step5", "step5_output.json",
                   json.dumps(step5_result, ensure_ascii=False, indent=2))
        emit("step5", "done", 100, "会前判断生成完成")
    except Exception as e:
        emit("step5", "error", 100, f"Step5 失败: {e}")
        raise RuntimeError(f"Step5 失败: {e}")

    return results


# ─── 单步运行（用于分步调试）────────────────────────────────────────────────

def run_single_step(step_name: str, project_dir: str) -> dict:
    """
    单独运行某一步骤（要求前置步骤已经完成）

    Args:
        step_name: "step1" | "step3" | "step4" | "step5"
        project_dir: 项目目录

    Returns:
        该步骤的输出 dict
    """
    bp_text_path = os.path.join(project_dir, "parsed", "bp_text.txt")
    if not os.path.exists(bp_text_path):
        raise FileNotFoundError("未找到 bp_text.txt，请先上传 BP")

    with open(bp_text_path, "r", encoding="utf-8") as f:
        bp_text = f.read()

    if step_name == "step1":
        result = run_step1(bp_text)
        _save_step(project_dir, "step1", "step1.txt", result)
        return {"step1": result}

    # 后续步骤需要前置结果
    step1_text = _load_step_text(project_dir, "step1", "step1.txt")
    if not step1_text:
        raise FileNotFoundError("未找到 Step1 结果，请先运行 Step1")

    if step_name == "step3":
        result = run_step3(bp_text, step1_text)
        _save_step(project_dir, "step3", "step3.json", json.dumps(result, ensure_ascii=False, indent=2))
        return {"step3": result}

    step3_json = _load_step_json(project_dir, "step3", "step3.json")
    if not step3_json:
        raise FileNotFoundError("未找到 Step3 结果，请先运行 Step3")

    if step_name == "step4":
        result = run_step4(bp_text, step1_text, step3_json)
        _save_step(project_dir, "step4", "step4_meeting_brief.md", result.get("meeting_brief_md", ""))
        _save_step(project_dir, "step4", "step4_internal.json",
                   json.dumps(result.get("internal", {}), ensure_ascii=False, indent=2))
        _save_step(project_dir, "step4", "step4_scan_questions.json",
                   json.dumps(result.get("scan_questions", {}), ensure_ascii=False, indent=2))
        return {"step4": result}

    step4_internal = _load_step_json(project_dir, "step4", "step4_internal.json")
    if not step4_internal:
        raise FileNotFoundError("未找到 Step4 internal，请先运行 Step4")

    if step_name == "step5":
        result = run_step5(step1_text, step3_json, step4_internal)
        _save_step(project_dir, "step5", "step5_decision.md", result.get("decision_md", ""))
        _save_step(project_dir, "step5", "step5_output.json",
                   json.dumps(result, ensure_ascii=False, indent=2))
        return {"step5": result}

    raise ValueError(f"未知步骤: {step_name}")


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def _save_step(project_dir: str, step: str, filename: str, content: str):
    """保存步骤输出到项目目录"""
    step_dir = os.path.join(project_dir, step)
    os.makedirs(step_dir, exist_ok=True)
    path = os.path.join(step_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _load_step_text(project_dir: str, step: str, filename: str) -> Optional[str]:
    """加载步骤文本文件"""
    path = os.path.join(project_dir, step, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_step_json(project_dir: str, step: str, filename: str) -> Optional[dict]:
    """加载步骤 JSON 文件"""
    path = os.path.join(project_dir, step, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_pipeline_results(project_dir: str) -> dict:
    """
    从已保存的文件加载 pipeline 结果（用于展示页面）

    Returns:
        {
          step1: str | None,
          step3: dict | None,
          step4: {meeting_brief_md, internal, scan_questions} | None,
          step5: {decision_md, ...} | None,
          completed_steps: [step names]
        }
    """
    results = {
        "step1": None,
        "step3": None,
        "step4": None,
        "step5": None,
        "completed_steps": []
    }

    step1 = _load_step_text(project_dir, "step1", "step1.txt")
    if step1:
        results["step1"] = step1
        results["completed_steps"].append("step1")

    step3 = _load_step_json(project_dir, "step3", "step3.json")
    if step3:
        results["step3"] = step3
        results["completed_steps"].append("step3")

    step4_brief = _load_step_text(project_dir, "step4", "step4_meeting_brief.md")
    step4_internal = _load_step_json(project_dir, "step4", "step4_internal.json")
    step4_scan = _load_step_json(project_dir, "step4", "step4_scan_questions.json")
    if step4_brief or step4_internal:
        results["step4"] = {
            "meeting_brief_md": step4_brief or "",
            "internal": step4_internal or {},
            "scan_questions": step4_scan or {}
        }
        results["completed_steps"].append("step4")

    step5_md = _load_step_text(project_dir, "step5", "step5_decision.md")
    step5_json = _load_step_json(project_dir, "step5", "step5_output.json")
    if step5_md or step5_json:
        data = step5_json or {}
        data["decision_md"] = step5_md or ""
        results["step5"] = data
        results["completed_steps"].append("step5")

    return results
