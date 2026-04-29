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
from services.project_manager import update_project_status


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
    优先匹配 commercial_space（更细分），否则默认 general。
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
    return "general"


# ─── Step3 服务 ─────────────────────────────────────────────────────────────

def run_step3(bp_text: str, step1_text: str) -> dict:
    """运行 Step3 背景分析，返回 dict"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from step3.project_structure_detector import detect_project_structure
    from step3.step3_service import Step3Service

    # 自动检测行业（兜底 general）
    industry = detect_industry(bp_text + step1_text)

    # 识别项目结构
    project_structure = detect_project_structure(bp_text + step1_text)

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
        project_structure=project_structure.to_dict(),
    )

    # 返回 dict，附加 project_structure
    output = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    output["project_structure"] = project_structure.to_dict()
    return output


# ─── Step3B 服务 ───────────────────────────────────────────────────────────

def run_step3b(
    bp_text: str,
    step3_json: dict,
    user_input: dict = None,
    investment_modules: list = None,
) -> dict:
    """
    运行 Step3B：BP一致性 & 包装识别

    基于 Step3 的 project_structure 做一致性检查、矛盾识别、包装信号识别

    Args:
        bp_text: BP原文
        step3_json: Step3 完整输出（包含 project_structure）
        user_input: Step1 用户输入（可选）
        investment_modules: 投资思维模块列表（可选）

    Returns:
        dict: Step3B 输出
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from step3b.step3b_service import run_step3b_simple

    project_structure = step3_json.get("project_structure", {})

    result = run_step3b_simple(
        bp_text=bp_text,
        project_structure=project_structure,
        investment_modules=investment_modules,
    )

    return result


# ─── Step4 服务 ─────────────────────────────────────────────────────────────

def run_step4(bp_text: str, step1_text: str, step3_json: dict, step3b_json: dict = None) -> dict:
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
    # Step3B 也需要转为字符串（如果传入的是 dict）
    step3b_str = json.dumps(step3b_json, ensure_ascii=False) if isinstance(step3b_json, dict) else step3b_json
    result = service.run(
        bp_text=bp_text,
        step1_text=step1_text,
        step3_json=step3_str,
        step3b_json=step3b_str,
    )

    # DEBUG: 检查 result 类型和内容
    print(f"[DEBUG] run_step4 result type: {type(result)}")
    if isinstance(result, dict):
        print(f"[DEBUG] result keys: {list(result.keys())}")
        if "internal" in result:
            ij = result["internal"]
            print(f"[DEBUG] internal type: {type(ij)}, len: {len(str(ij))}")

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

    # internal JSON（Step4Service 返回 internal_json）
    if hasattr(result, "internal_json"):
        internal = result.internal_json
        if hasattr(internal, "model_dump"):
            output["internal"] = internal.model_dump()
        else:
            output["internal"] = dict(internal) if internal else {}
    elif isinstance(result, dict) and "internal_json" in result:
        output["internal"] = result["internal_json"]
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

def run_step5(
    step1_text: str,
    step3_json: dict,
    step4_internal: dict,
    step3b_json: dict = None,
    step4_output_full: dict = None,
    investment_modules: list = None,
) -> dict:
    """运行 Step5，返回 dict"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from step5.step5_service import run_step5 as _run_step5

    def _call_llm(system_prompt: str, user_prompt: str) -> str:
        return call_deepseek(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_retries=2
        )

    # 使用完整 step4_output（包含 meeting_brief_md）传给 Step5
    step4_out = step4_output_full if step4_output_full is not None else step4_internal

    result = _run_step5(
        step1_text=step1_text,
        step3_json=step3_json,
        step3b_json=step3b_json or {},
        step4_output={"internal_json": step4_internal, "meeting_brief_md": step4_out.get("meeting_brief_md", "")} if isinstance(step4_out, dict) else {"internal_json": step4_internal},
        call_llm=_call_llm,
        investment_modules=investment_modules,
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

    # ── 选择投资思维模块 ─────────────────────────────────────
    try:
        from investment_modules.module_loader import select_relevant_modules
        investment_modules = select_relevant_modules(
            project_structure=step3_json.get("project_structure", {}),
            step3b_output=None,
        )
        print(f"[投资思维模块] 已选择 {len(investment_modules)} 个模块: {[m['module_id'] for m in investment_modules]}")
    except Exception as e:
        print(f"[投资思维模块] 选择失败，使用空列表: {e}")
        investment_modules = []

    # ── Step3B ──────────────────────────────────────────────
    emit("step3b", "running", 52, "正在做BP一致性检查...")
    try:
        step3b_json = run_step3b(bp_text, step3_json, investment_modules=investment_modules)
        results["step3b"] = step3b_json
        _save_step(project_dir, "step3b", "step3b.json", json.dumps(step3b_json, ensure_ascii=False, indent=2))
        emit("step3b", "done", 55, "BP一致性检查完成")
    except Exception as e:
        emit("step3b", "error", 55, f"Step3B 失败: {e}")
        # Step3B 失败不阻断流程，继续
        results["step3b"] = {}
        step3b_json = {}

    # ── Step4 ────────────────────────────────────────────────
    try:
        step4_result = run_step4(bp_text, step1_text, step3_json, step3b_json=results.get("step3b"))
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
        step5_result = run_step5(
            step1_text,
            step3_json,
            step4_internal,
            step3b_json=results.get("step3b"),
            step4_output_full=step4_result,
            investment_modules=investment_modules,
        )
        results["step5"] = step5_result
        _save_step(project_dir, "step5", "step5_decision.md", step5_result.get("decision_md", ""))
        _save_step(project_dir, "step5", "step5_output.json",
                   json.dumps(step5_result, ensure_ascii=False, indent=2))
        # 更新项目状态为 v1_done
        update_project_status(project_dir, "v1_done")
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
        # 尝试加载 Step3B 结果
        step3b_json = _load_step_json(project_dir, "step3b", "step3b.json")
        result = run_step4(bp_text, step1_text, step3_json, step3b_json=step3b_json)
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
