# -*- coding: utf-8 -*-
"""
AI 项目判断工作台 -- Flask 主入口

路由总览(新):
  GET  /                              -> 首页(项目列表)
  GET  /project/new                   -> 创建新项目页
  POST /project/create                -> 创建项目 + 上传 BP
  GET  /project/<id>                  -> 项目详情页

  ===== 1.0 新流程(主推) =====
  POST /project/<id>/run_pipeline     -> 触发完整 Step1->3->4->5 流程(SSE 流式进度)
  POST /project/<id>/run_step/<step>  -> 单步运行(step1/step3/step4/step5)
  GET  /project/<id>/result_new       -> 查看新 1.0 结果页(5标签)
  GET  /project/<id>/download/<step>/<file> -> 下载各步输出文件

  ===== 旧流程(保留兼容) =====
  POST /project/<id>/analyze          -> 旧1.0 AB互检
  POST /project/<id>/analyze_v25      -> 旧v2.5 9步流程
"""
import sys, io, os
# Windows 控制台 UTF-8 编码支持（仅 Windows 生效）
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    # 重定向 stdout/stderr 为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response, stream_with_context
import os
import json
from datetime import datetime
import threading
import queue
from config import WORKSPACE_DIR, SECRET_KEY, DEBUG, ALLOWED_EXTENSIONS

from services.file_parser import save_and_parse
from services.project_manager import (
    create_project, list_projects, get_project_meta,
    save_report, load_project_context, update_project_status
)
from services.report_generator import generate_v1, generate_v2, generate_v1_template
from services.pipeline_v1 import run_pipeline_v1, run_single_step, load_pipeline_results
from services.profile import (
    DEFAULT_PROFILE_ID, list_fund_profiles, load_profile,
    load_project_profile, save_project_profile, get_profile_summary
)
from services.deepseek_service import call_deepseek
from services.feedback import (
    append_feedback_case, find_feedback_case, find_feedback_by_project,
    generate_feedback_id, HumanNoteNormalizer, KnowledgeCandidateGenerator
)

app = Flask(__name__)
app.secret_key = SECRET_KEY
# 确保 jsonify / tojson 输出 UTF-8 中文
app.json.ensure_ascii = False

os.makedirs(WORKSPACE_DIR, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------- 首页：项目列表 ----------
@app.route("/")
def index():
    projects = list_projects()
    return render_template("index.html", projects=projects)


@app.route("/profile_comparison")
def profile_comparison():
    """Profile 对比测试页"""
    return render_template("profile_comparison.html")


# ---------- 创建新项目 ----------
@app.route("/project/new")
def new_project():
    return render_template("new_project.html")


@app.route("/project/create", methods=["POST"])
def create_project_route():
    company_name = request.form.get("company_name", "").strip()
    if not company_name:
        return "公司名称不能为空", 400

    file = request.files.get("bp_file")
    if not file or not allowed_file(file.filename):
        return "请上传有效的 BP 文件（PDF / TXT / DOCX）", 400

    # 获取选择的 profile_id（默认 neutral_investor）
    profile_id = request.form.get("profile_id", DEFAULT_PROFILE_ID)

    # 创建项目目录
    project_dir = create_project(company_name)

    # 保存并解析 BP 文件
    save_and_parse(file, project_dir, source_type="bp")

    # 保存项目 profile
    profile = load_profile(profile_id)
    save_project_profile(project_dir, profile)

    project_id = os.path.basename(project_dir)
    return redirect(url_for("project_detail", project_id=project_id))


# ---------- 项目详情页 ----------
@app.route("/project/<project_id>")
def project_detail(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return "项目不存在", 404
    meta = get_project_meta(project_dir)
    context = load_project_context(project_dir)
    # 检查是否有 v2.5 报告
    v2_5_available = context.get("latest_v2_5_report") is not None
    # 检查是否有新 pipeline 结果
    pipeline_results = load_pipeline_results(project_dir)
    results_available = len(pipeline_results.get("completed_steps", [])) > 0

    # 加载项目 profile
    project_profile = load_project_profile(project_dir)
    profile_summary = get_profile_summary(project_profile)

    # 加载反馈标注状态
    feedback_case = find_feedback_by_project(project_id)

    return render_template(
        "project_detail.html",
        meta=meta, context=context,
        v2_5_available=v2_5_available,
        project_id=project_id,
        results_available=results_available,
        project_profile=project_profile,
        profile_summary=profile_summary,
        feedback_case=feedback_case
    )


# ---------- 触发初判 1.0 ----------
@app.route("/project/<project_id>/analyze", methods=["POST"])
def analyze(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    # 读取解析后的 BP 文本
    bp_text_path = os.path.join(project_dir, "parsed", "bp_text.txt")
    if not os.path.exists(bp_text_path):
        return jsonify({"error": "未找到 BP 解析文本，请先上传 BP"}), 400

    with open(bp_text_path, "r", encoding="utf-8") as f:
        bp_text = f.read()

    meta = get_project_meta(project_dir)

    # 调用三角色生成初判报告
    report = generate_v1(bp_text, meta)

    # 保存报告
    save_report(project_dir, "v1_0", report)

    return jsonify({"status": "ok", "redirect": url_for("result_v1", project_id=project_id)})


# ---------- 触发 v2.5 模板分析 ----------
@app.route("/project/<project_id>/analyze_v25", methods=["POST"])
def analyze_v25(project_id):
    """
    v2.5模板驱动分析
    使用新的9步流程（Step1升级版 + Step9投资人判断层）
    """
    try:
        project_dir = os.path.join(WORKSPACE_DIR, project_id)
        if not os.path.exists(project_dir):
            return jsonify({"error": "项目不存在"}), 404

        # 读取解析后的BP文本
        bp_text_path = os.path.join(project_dir, "parsed", "bp_text.txt")
        if not os.path.exists(bp_text_path):
            return jsonify({"error": "未找到BP解析文本，请先上传BP"}), 400

        with open(bp_text_path, "r", encoding="utf-8") as f:
            bp_text = f.read()

        meta = get_project_meta(project_dir)

        # 调用v2.5模板流程
        report = generate_v1_template(bp_text, meta)

        # 保存报告
        save_report(project_dir, "v2_5", report)

        return jsonify({"status": "ok", "redirect": url_for("result_v25", project_id=project_id)})
    except Exception as e:
        import traceback
        error_msg = f"v2.5分析出错: {str(e)}"
        print(f"[ERROR] {error_msg}")
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500


# ---------- 查看 1.0 报告 ----------
@app.route("/project/<project_id>/result")
def result_v1(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    context = load_project_context(project_dir)
    latest_report = context.get("latest_v1_report")
    if not latest_report:
        return redirect(url_for("project_detail", project_id=project_id))
    meta = get_project_meta(project_dir)
    return render_template("result_1_0.html", report=latest_report, meta=meta, project_id=project_id)


# ---------- 查看 v2.5 报告 ----------
@app.route("/project/<project_id>/result25")
def result_v25(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    context = load_project_context(project_dir)
    latest_report = context.get("latest_v2_5_report")
    if not latest_report:
        return redirect(url_for("project_detail", project_id=project_id))
    meta = get_project_meta(project_dir)
    return render_template("result_2_5.html", report=latest_report, meta=meta, project_id=project_id)


# ---------- 上传会议记录，触发 2.0 更新 ----------
@app.route("/project/<project_id>/update", methods=["POST"])
def update_v2(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    file = request.files.get("meeting_file")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "请上传有效的会议记录文件"}), 400

    # 保存并解析会议记录
    save_and_parse(file, project_dir, source_type="meeting")

    # 读取会议文本
    meeting_text_path = os.path.join(project_dir, "parsed", "meeting_text.txt")
    with open(meeting_text_path, "r", encoding="utf-8") as f:
        meeting_text = f.read()

    # 加载报告上下文（优先用 v2.5，其次 v1.0）
    context = load_project_context(project_dir)
    v1_report = context.get("latest_v2_5_report") or context.get("latest_v1_report")
    if not v1_report:
        return jsonify({"error": "请先生成初判报告（1.0 或 2.5）"}), 400

    # 调用 D+E+C 三角色生成 2.0 更新报告
    report_v2 = generate_v2(v1_report, meeting_text)

    # 检查是否有错误
    if report_v2.get("error"):
        return jsonify({
            "error": report_v2["error"],
            "detail": report_v2.get("error_detail", "")
        }), 500

    # 保存
    save_report(project_dir, "v2_0", report_v2)

    return jsonify({"status": "ok", "redirect": url_for("result_v2", project_id=project_id)})


# ---------- 查看 2.0 报告 ----------
@app.route("/project/<project_id>/result2")
def result_v2(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    context = load_project_context(project_dir)
    latest_report = context.get("latest_v2_report")
    if not latest_report:
        return redirect(url_for("project_detail", project_id=project_id))
    meta = get_project_meta(project_dir)
    return render_template("result_2_0.html", report=latest_report, meta=meta, project_id=project_id)


# ---------- 导出 Markdown 报告 ----------
@app.route("/project/<project_id>/export")
@app.route("/project/<project_id>/export/<version>")
def export_report(project_id, version=None):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    context = load_project_context(project_dir)

    # 根据 version 参数选择报告版本
    version_map = {
        "v1_0": ("latest_v1_report", "1.0"),
        "v2_5": ("latest_v2_5_report", "v2.5"),
        "v2_0": ("latest_v2_report", "2.0"),
    }

    if version and version in version_map:
        ctx_key, display_version = version_map[version]
        report = context.get(ctx_key)
        if not report:
            return f"暂无可导出的 {display_version} 报告", 404
    else:
        # 默认导出最新版本：v2.5 > v2.0 > v1.0
        report = context.get("latest_v2_5_report") or context.get("latest_v2_report") or context.get("latest_v1_report")
        if not report:
            return "暂无可导出的报告", 404
        display_version = "v2.5" if context.get("latest_v2_5_report") else ("2.0" if context.get("latest_v2_report") else "1.0")

    meta = get_project_meta(project_dir)

    # 生成 Markdown 内容
    from services.report_generator import report_to_markdown
    md_content = report_to_markdown(report, meta, display_version)

    export_path = os.path.join(project_dir, f"{meta['company_name']}_判断报告_{display_version}.md")
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return send_file(export_path, as_attachment=True)


# ============================================================
# 新 1.0 会前流程路由
# ============================================================

# ---------- 全局 pipeline 进度队列（跨请求共享）----------
# 使用 Flask g 对象 + 全局 dict，每个 project_id 一个 queue
_pipeline_queues: dict[str, queue.Queue] = {}
_pipeline_lock = threading.Lock()


def _get_pipeline_queue(project_id: str) -> queue.Queue:
    with _pipeline_lock:
        if project_id not in _pipeline_queues:
            _pipeline_queues[project_id] = queue.Queue()
        return _pipeline_queues[project_id]


def _clear_pipeline_queue(project_id: str):
    with _pipeline_lock:
        if project_id in _pipeline_queues:
            # 清空旧消息
            while not _pipeline_queues[project_id].empty():
                try:
                    _pipeline_queues[project_id].get_nowait()
                except queue.Empty:
                    break


# ---------- 触发 pipeline（POST）—— 返回 SSE 流 ----------
@app.route("/project/<project_id>/run_pipeline", methods=["GET", "POST"])
def run_pipeline(project_id):
    """
    GET  : EventSource 连接，拉取 SSE 进度流（pipeline 已启动时用）
    POST : 验证 + 启动 pipeline + 返回 SSE 流

    前端流程：
      1. fetch(POST) 触发启动，获取 response
      2. EventSource(GET) 连接 SSE 流
    """
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    bp_text_path = os.path.join(project_dir, "parsed", "bp_text.txt")
    if not os.path.exists(bp_text_path):
        return jsonify({"error": "未找到 BP，请先上传"}), 400

    # POST：验证 BP + 启动 pipeline
    if request.method == "POST":
        with open(bp_text_path, "r", encoding="utf-8") as f:
            bp_text = f.read()

        # 每次新运行先清空旧队列
        _clear_pipeline_queue(project_id)
        progress_q = _get_pipeline_queue(project_id)

        def on_progress(step, status, percent, msg=""):
            progress_q.put({
                "step": step, "status": status,
                "percent": percent, "msg": msg
            })

        def bg_run():
            try:
                run_pipeline_v1(bp_text, project_dir, on_progress=on_progress)
                progress_q.put({"step": "all", "status": "done", "percent": 100, "msg": "分析完成！"})
            except Exception as e:
                progress_q.put({"step": "all", "status": "error", "percent": 100, "msg": str(e)})

        thread = threading.Thread(target=bg_run, daemon=True)
        thread.start()

    # GET / POST：统一返回 SSE 流
    progress_q = _get_pipeline_queue(project_id)

    def sse_stream():
        thinking_phrases = {
            "step1": ["正在理解公司核心业务...", "正在判断商业模式...", "正在形成初步看法..."],
            "step3": ["正在分析行业背景...", "正在识别潜在风险...", "正在梳理背景结构..."],
            "step4": ["正在生成关键问题...", "正在设计追问路径...", "正在确定深挖方向..."],
            "step5": ["正在整理判断逻辑...", "正在形成验证框架...", "正在收敛会前判断..."],
        }

        import time
        last_step = None
        done_steps: set = set()

        while True:
            try:
                item = progress_q.get(timeout=60)
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"
                yield b""
                continue

            step = item.get("step", "")
            status = item.get("status", "")

            # 步骤刚启动时，依次推送"思考流"句子
            if status == "running" and step != last_step:
                last_step = step
                for phrase in thinking_phrases.get(step, []):
                    time.sleep(0.3)
                    data = json.dumps({"type": "thinking", "step": step, "msg": phrase}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    yield b""  # 强制 flush
                    time.sleep(0.1)

            data = json.dumps({"type": "progress", **item}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield b""  # 强制 flush

            if status == "done" and step != "all":
                done_steps.add(step)

            if status in ("done", "error") and step == "all":
                redirect_url = url_for("result_new", project_id=project_id)
                data = json.dumps({"type": "redirect", "url": redirect_url}, ensure_ascii=False)
                yield f"data: {data}\n\n"
                yield b""
                _clear_pipeline_queue(project_id)
                break

    return Response(
        stream_with_context(sse_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


# ---------- 单步运行 ----------
@app.route("/project/<project_id>/run_step/<step_name>", methods=["POST"])
def run_step(project_id, step_name):
    """单步运行：step1 / step3 / step4 / step5"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    valid_steps = ["step1", "step3", "step4", "step5"]
    if step_name not in valid_steps:
        return jsonify({"error": f"无效步骤，支持：{valid_steps}"}), 400

    try:
        result = run_single_step(step_name, project_dir)
        return jsonify({"status": "ok", "step": step_name, "msg": f"{step_name} 完成"})
    except FileNotFoundError as e:
        return jsonify({"error": str(e), "hint": "请先完成前置步骤"}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------- 查看新 1.0 结果页 ----------
@app.route("/project/<project_id>/result_new")
def result_new(project_id):
    """新 1.0 结果页：5标签展示"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return "项目不存在", 404

    meta = get_project_meta(project_dir)
    pipeline_results = load_pipeline_results(project_dir)
    project_profile = load_project_profile(project_dir)
    feedback_case = find_feedback_by_project(project_id)

    return render_template(
        "result_1_0_new.html",
        meta=meta,
        project_id=project_id,
        results=pipeline_results,
        project_profile=project_profile,
        feedback_case=feedback_case
    )


# ---------- 分步下载 ----------
@app.route("/project/<project_id>/download/<step_name>/<file_name>")
def download_step_file(project_id, step_name, file_name):
    """下载各步骤输出文件"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)

    # 安全校验
    allowed_downloads = {
        "step0": ["step0.json"],
        "step1": ["step1.txt"],
        "step3": ["step3.json"],
        "step4": ["step4_meeting_brief.md", "step4_internal.json", "step4_scan_questions.json"],
        "step5": ["step5_decision.md", "step5_output.json"],
        "step6": ["step6_latest.json", "step6_v2_2_001.json"],
        "step7": ["step7_latest.json", "step7_v2_2_001.json"],
        "step8": ["step8_latest.json", "step8_v2_2_001.json"],
        "step9": ["step9_latest.json", "step9_v2_2_001.json"],
        "step10": ["step10.json"],
    }

    if step_name not in allowed_downloads:
        return "无效步骤", 400
    if file_name not in allowed_downloads[step_name]:
        return "无效文件", 400

    file_path = os.path.join(project_dir, step_name, file_name)
    if not os.path.exists(file_path):
        return f"文件不存在，请先运行 {step_name}", 404

    # 根据文件类型设置正确的 MIME type
    mime_map = {
        ".json": "application/json; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
    }
    ext = os.path.splitext(file_name)[1].lower()
    mimetype = mime_map.get(ext, "application/octet-stream")

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=file_name
    )


# ---------- 下载完整分析包（ZIP）----------
@app.route("/project/<project_id>/download_all")
def download_all(project_id):
    """打包下载完整分析结果"""
    import zipfile
    import tempfile

    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    meta = get_project_meta(project_dir)
    company = meta.get("company_name", project_id)

    # 创建临时 zip 文件
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for step in ["step1", "step3", "step4", "step5"]:
            step_dir = os.path.join(project_dir, step)
            if os.path.exists(step_dir):
                for fname in os.listdir(step_dir):
                    fpath = os.path.join(step_dir, fname)
                    if os.path.isfile(fpath):
                        zf.write(fpath, arcname=f"{step}/{fname}")

    zip_name = f"{company}_会前分析包.zip"
    return send_file(tmp.name, as_attachment=True, download_name=zip_name)


# ============================================================
# 2.0 会后分析层路由
# ============================================================

from services.v2 import PipelineV2
from services.v2.schemas import DialogueTurn
from services.file_parser import parse_meeting_file


_v2_queues: dict[str, queue.Queue] = {}
_v2_lock = threading.Lock()


def _get_v2_queue(project_id: str) -> queue.Queue:
    with _v2_lock:
        if project_id not in _v2_queues:
            _v2_queues[project_id] = queue.Queue()
        return _v2_queues[project_id]


def _clear_v2_queue(project_id: str):
    with _v2_lock:
        if project_id in _v2_queues:
            while not _v2_queues[project_id].empty():
                try:
                    _v2_queues[project_id].get_nowait()
                except queue.Empty:
                    break


# ---------- 进入 2.0 会后分析页 ----------
@app.route("/project/<project_id>/v2")
def project_v2(project_id):
    """2.0 会后分析入口页"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return "项目不存在", 404

    meta = get_project_meta(project_dir)

    # 检查 1.0 是否已完成（2.0 需要 Step4/5 的输出）
    step4_exists = os.path.exists(os.path.join(project_dir, "step4", "step4_internal.json"))
    step5_exists = os.path.exists(os.path.join(project_dir, "step5", "step5_output.json"))

    # 加载 v2_context 数据（沉淀层）
    v2_context = _load_v2_context(project_dir)

    # 加载对话历史
    dialogue_history = _load_dialogue_history(project_dir)

    # 加载项目 profile
    project_profile = load_project_profile(project_dir)
    profile_summary = get_profile_summary(project_profile)

    return render_template(
        "project_v2.html",
        meta=meta,
        project_id=project_id,
        step4_exists=step4_exists,
        step5_exists=step5_exists,
        v2_context=v2_context,
        dialogue_history=dialogue_history,
        project_profile=project_profile,
        profile_summary=profile_summary
    )


# ---------- 保存会议笔记 ----------
@app.route("/project/<project_id>/save_meeting_log", methods=["POST"])
def save_meeting_log(project_id):
    """保存用户的会议对话笔记"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    data = request.get_json()
    log_text = data.get("log", "")

    os.makedirs(os.path.join(project_dir, "v2_context"), exist_ok=True)
    log_path = os.path.join(project_dir, "v2_context", "meeting_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log_text)

    return jsonify({"status": "ok"})


# ---------- 上传会议记录 ----------
@app.route("/project/<project_id>/upload_meeting", methods=["POST"])
def upload_meeting(project_id):
    """上传会议记录文件"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    # 支持文件上传 + 文本粘贴
    file = request.files.get("meeting_file")
    text = request.form.get("meeting_text", "").strip()
    dialogue_raw = request.form.get("dialogue_history", "").strip()

    if not file and not text:
        return jsonify({"error": "请上传文件或粘贴会议记录"}), 400

    # 解析会议内容
    if file and allowed_file(file.filename):
        meeting_record = parse_meeting_file(file, project_dir, source_type="meeting")
        file_source = file.filename.rsplit(".", 1)[-1].lower()
    else:
        meeting_record = text
        file_source = "text"

    # 解析对话历史
    dialogue_history = []
    if dialogue_raw:
        try:
            dialogue_history = json.loads(dialogue_raw)
        except json.JSONDecodeError:
            dialogue_history = []

    # 读取 1.0 的输出（Step4 问题 + Step5 判断）
    step5_summary, step5_judgements, step5_decision = _load_step5_data(project_dir)
    step4_questions = _load_step4_questions(project_dir)

    # 保存会议记录
    meeting_save_path = os.path.join(project_dir, "v2_context", "meeting_record.txt")
    os.makedirs(os.path.dirname(meeting_save_path), exist_ok=True)
    with open(meeting_save_path, "w", encoding="utf-8") as f:
        f.write(meeting_record)

    return jsonify({
        "status": "ok",
        "source": file_source,
        "record_length": len(meeting_record),
        "dialogue_count": len(dialogue_history)
    })


# ---------- 触发 2.0 全流程（SSE 流式）----------
@app.route("/project/<project_id>/run_v2", methods=["GET", "POST"])
def run_v2(project_id):
    """
    2.0 会后分析全流程
    GET  : EventSource 连接
    POST : 启动流程 + 返回 SSE 流
    """
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    # 读取会议记录
    meeting_path = os.path.join(project_dir, "v2_context", "meeting_record.txt")
    if not os.path.exists(meeting_path):
        return jsonify({"error": "请先上传会议记录"}), 400

    with open(meeting_path, "r", encoding="utf-8") as f:
        meeting_record = f.read()

    # 读取 1.0 输出
    step5_summary, step5_judgements, step5_decision = _load_step5_data(project_dir)
    step4_questions = _load_step4_questions(project_dir)
    print(f"[DEBUG run_v2] step4_questions count={len(step4_questions)}, step5_summary len={len(step5_summary)}")
    if not step4_questions:
        return jsonify({"error": f"请先完成 1.0 的 Step4（解析到 {len(step4_questions)} 个问题）"}), 400

    # 读取对话历史
    dialogue_history = _load_dialogue_history(project_dir)

    # 加载项目 profile（v2.3 新增）
    project_profile = load_project_profile(project_dir)
    profile_id = project_profile.get("profile_id", "neutral_investor")
    print(f"[DEBUG run_v2] profile_id={profile_id}")

    # 合并 base questions 和 profile questions（v2.3 新增）
    # 如果 profile 有 fit_questions，追加到问题列表
    merged_questions = step4_questions
    if profile_id != "neutral_investor":
        from services.profile import get_fit_questions_for_profile
        profile_fit_questions = get_fit_questions_for_profile(project_profile)
        if profile_fit_questions:
            # 合并：基础问题 + profile 问题
            merged_questions = step4_questions + [q["question"] for q in profile_fit_questions]
            print(f"[DEBUG run_v2] merged questions: base={len(step4_questions)} + profile={len(profile_fit_questions)} = {len(merged_questions)}")

    # 启动流程
    if request.method == "POST":
        _clear_v2_queue(project_id)
        progress_q = _get_v2_queue(project_id)

        def on_progress(step, status, percent, msg=""):
            progress_q.put({
                "step": step, "status": status,
                "percent": percent, "msg": msg
            })

        def bg_run():
            try:
                pipeline = PipelineV2(project_id, os.path.basename(project_dir), project_dir)
                pipeline.model = "deepseek-chat"
                pipeline.fund_profile = project_profile

                on_progress("step6", "running", 10, "")
                step6 = pipeline.run_step6(step5_summary, meeting_record)
                on_progress("step6", "done", 20, f"提取了 {len(step6.get('new_information', []))} 条新增信息")

                # Step7：使用两步架构 + profile 问题（v2.3 修改）
                on_progress("step7", "running", 30, "")
                step7 = pipeline.run_step7(
                    step4_questions=merged_questions,
                    step6_new_information=step6.get("new_information", []),
                    meeting_record=meeting_record,
                    step6_summary=step6.get("meeting_summary", "")
                )
                on_progress("step7", "done", 40, f"问题对齐完成（base + profile）")

                step7_summary = pipeline._summarize_step7(step7)
                step7_val_summary = pipeline._summarize_validation(step7)

                on_progress("step8", "running", 50, "")
                step8 = pipeline.run_step8(
                    step5_judgements,
                    step7_result=step7
                )
                print(f"[DEBUG Step8] hypothesis_updates count={len(step8.get('hypothesis_updates', []))}")
                print(f"[DEBUG Step8] unchanged_hypotheses count={len(step8.get('unchanged_hypotheses', []))}")
                on_progress("step8", "done", 60, f"认知更新完成（{len(step8.get('hypothesis_updates', []))} 条更新）")

                on_progress("step9", "running", 70, "")
                print(f"[DEBUG Step9] hypothesis_updates count={len(step8.get('hypothesis_updates', []))}")
                step9 = pipeline.run_step9(
                    step6_output=step6,
                    step7_output=step7,
                    step8_output=step8
                )
                on_progress("step9", "done", 80, f"决策完成（{step9.get('overall_decision', {}).get('process_decision', 'N/A')} / {step9.get('overall_decision', {}).get('investment_decision', 'N/A')}）")

                # 沉淀层
                on_progress("沉淀", "running", 85, "")
                _沉淀 = pipeline._extract_candidates(step7, step8, dialogue_history)
                on_progress("沉淀", "done", 90, f"问题库 {len(_沉淀.get('question_candidates', []))} 条")

                # Step10: Fit 判断（项目是否适合当前基金）
                on_progress("step10", "running", 92, "")
                step10 = pipeline.run_step10(
                    step9_output=step9,
                    profile_id=profile_id,
                    user_description="",
                    user_feedback=""
                )
                on_progress("step10", "done", 95, f"Fit判断完成（{step10.get('fit_decision', 'N/A')}）")

                # 保存完整报告
                on_progress("report", "running", 97, "")
                report = pipeline._render_report({
                    "step6": step6, "step7": step7,
                    "step8": step8, "step9": step9,
                    "step10": step10,
                    "沉淀": _沉淀
                })
                report_path = os.path.join(project_dir, "v2_context", "v2_report.md")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                on_progress("report", "done", 100, "报告生成完成")

                # 更新项目状态为 v2_done
                update_project_status(project_dir, "v2_done")

                progress_q.put({"step": "all", "status": "done", "percent": 100, "msg": "2.0 分析完成！"})
            except Exception as e:
                import traceback
                traceback.print_exc()
                progress_q.put({"step": "all", "status": "error", "percent": 100, "msg": str(e)})

        thread = threading.Thread(target=bg_run, daemon=True)
        thread.start()

    # 返回 SSE 流
    progress_q = _get_v2_queue(project_id)

    def sse_stream():
        thinking_phrases = {
            "step6": ["正在阅读会议记录...", "正在提取新增信息...", "正在与BP对比..."],
            "step7": ["正在对齐关键问题...", "正在评估会议质量...", "正在识别回避信号..."],
            "step8": ["正在寻找支持证据...", "正在寻找反对证据...", "正在更新认知..."],
            "step9": ["正在分析决策选项...", "正在识别剩余未知...", "正在生成行动建议..."],
            "step10": ["正在判断基金适配度...", "正在生成沉淀候选...", "正在整合最终报告..."],
        }

        import time
        last_step = None
        # 记录每个 step 的 done 状态，用于重连后恢复 active
        done_steps: set = set()

        while True:
            try:
                item = progress_q.get(timeout=60)
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"
                yield b""
                continue

            step = item.get("step", "")
            status = item.get("status", "")

            # 发送 thinking 消息（仅新 step 首次切 running 时）
            if status == "running" and step != last_step:
                last_step = step
                for phrase in thinking_phrases.get(step, []):
                    time.sleep(0.3)
                    data = json.dumps({"type": "thinking", "step": step, "msg": phrase}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    # 强制 flush，防止被 WSGI 缓冲
                    yield b""
                    time.sleep(0.1)

            # 发 progress 消息
            data = json.dumps({"type": "progress", **item}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield b""  # 强制 flush

            # 记录已完成的 step（用于重连后重建 active 状态）
            if status == "done" and step != "all":
                done_steps.add(step)

            if status in ("done", "error") and step == "all":
                redirect_url = url_for("result_v2_page", project_id=project_id)
                data = json.dumps({"type": "redirect", "url": redirect_url}, ensure_ascii=False)
                yield f"data: {data}\n\n"
                yield b""
                _clear_v2_queue(project_id)
                break

    return Response(
        stream_with_context(sse_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ---------- 查看 2.0 报告 ----------
@app.route("/project/<project_id>/result_v2_page")
def result_v2_page(project_id):
    """2.0 会后分析报告页（含 Step10 Fit 判断）"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return "项目不存在", 404

    meta = get_project_meta(project_dir)
    v2_context = _load_v2_context(project_dir)

    # 读取各步骤输出（pipeline 保存的是 latest.json）
    step6 = _load_json(os.path.join(project_dir, "step6", "step6_latest.json")) if os.path.exists(os.path.join(project_dir, "step6", "step6_latest.json")) else {}
    step7 = _load_json(os.path.join(project_dir, "step7", "step7_latest.json")) if os.path.exists(os.path.join(project_dir, "step7", "step7_latest.json")) else {}
    step8 = _load_json(os.path.join(project_dir, "step8", "step8_latest.json")) if os.path.exists(os.path.join(project_dir, "step8", "step8_latest.json")) else {}
    step9 = _load_json(os.path.join(project_dir, "step9", "step9_latest.json")) if os.path.exists(os.path.join(project_dir, "step9", "step9_latest.json")) else {}
    step10 = _load_json(os.path.join(project_dir, "step10", "step10.json")) if os.path.exists(os.path.join(project_dir, "step10", "step10.json")) else {}

    # 加载当前 profile（用于 Step10 展示）
    project_profile = load_project_profile(project_dir)

    report_path = os.path.join(project_dir, "v2_context", "v2_report.md")
    has_report = os.path.exists(report_path)

    return render_template(
        "result_v2.html",
        meta=meta,
        project_id=project_id,
        v2_context=v2_context,
        step6=step6, step7=step7, step8=step8, step9=step9, step10=step10,
        project_profile=project_profile,
        has_report=has_report
    )


# ---------- 下载 2.0 报告 ----------
@app.route("/project/<project_id>/download_v2_report")
def download_v2_report(project_id):
    """下载 2.0 完整报告"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    meta = get_project_meta(project_dir)
    report_path = os.path.join(project_dir, "v2_context", "v2_report.md")
    if not os.path.exists(report_path):
        return "报告不存在，请先运行 2.0 分析", 404

    return send_file(
        report_path,
        mimetype="text/markdown; charset=utf-8",
        as_attachment=True,
        download_name=f"{meta.get('company_name', project_id)}_会后分析报告.md"
    )


# ---------- 沉淀层下载 ----------
@app.route("/project/<project_id>/download_v2_candidates/<c_type>")
def download_v2_candidates(project_id, c_type):
    """下载沉淀候选文件（questions / industry_insights / user_profile）"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    filename_map = {
        "questions": "questions.json",
        "industry": "industry_insights.json",
        "user_profile": "user_profile_candidates.json",
    }
    if c_type not in filename_map:
        return "无效类型", 400

    file_path = os.path.join(project_dir, "v2_context", filename_map[c_type])
    if not os.path.exists(file_path):
        return "文件不存在", 404

    return send_file(file_path, as_attachment=True)


# ---------- 辅助函数 ----------

def _load_step5_data(project_dir):
    """加载 Step5 输出（支持 v5 探索型格式和旧版格式）"""
    path = os.path.join(project_dir, "step5", "step5_output.json")
    if not os.path.exists(path):
        return "", [], ""

    with open(path, "r", encoding="utf-8") as f:
        step5 = json.load(f)

    # v5 探索型格式（优先级最高）
    if "current_hypothesis" in step5:
        summary = step5.get("current_hypothesis", "")
        decision = step5.get("meeting_objective", "")

        judgements = []
        # 从 why_this_might_be_wrong 提取假设
        for i, wrong in enumerate(step5.get("why_this_might_be_wrong", [])):
            judgements.append({
                "hypothesis": f"假设{i+1}: {wrong[:100]}...",
                "view": wrong,
                "source": "why_this_might_be_wrong"
            })
        # 从 key_validation_points 提取验证点作为假设
        for i, vp in enumerate(step5.get("key_validation_points", [])):
            point = vp.get("point", "")
            if point:
                judgements.append({
                    "hypothesis": f"验证点{i+1}: {point[:100]}...",
                    "view": f"为什么重要: {vp.get('why_it_matters', '')}",
                    "source": "key_validation_points"
                })

        return summary, judgements, decision

    # 旧版格式 fallback
    summary = step5.get("summary", "")
    decision = step5.get("decision", {}).get("conclusion", "")

    judgements = []
    if "judgment" in step5:
        for j in step5["judgment"].get("judgments", []):
            judgements.append({
                "hypothesis": j.get("dimension", ""),
                "view": j.get("summary", "")
            })
    if "internal_json" in step5:
        for gap in step5["internal_json"].get("gaps", []):
            judgements.append({
                "hypothesis": gap.get("focus_area", ""),
                "view": gap.get("current_state", "")
            })

    return summary, judgements, decision


def _load_step4_questions(project_dir):
    """加载 Step4 的关键问题"""
    path = os.path.join(project_dir, "step4", "step4_meeting_brief.md")
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    questions = []
    # 策略1：提取"优先搞清楚的N件事"中的编号问题
    in_priority_section = False
    for line in content.split("\n"):
        stripped = line.strip()
        # 检测进入优先问题区
        if "优先搞清楚" in stripped or "建议提问路径" in stripped:
            in_priority_section = True
        if in_priority_section and stripped.startswith("#"):
            # 遇到下一个一级标题，退出
            if not stripped.startswith("# "):
                in_priority_section = False
        # 提取编号问题：1. xxx, 2. xxx, 3. xxx
        import re
        if re.match(r"^\d+[.、]", stripped):
            q = re.sub(r"^\d+[.、]\s*", "", stripped).strip()
            if q and len(q) > 5:
                questions.append(q)

    # 策略2：从"深挖"段落中提取主路径问题（① ② ③ ④ 引导的问句）
    # 按缺口分组，每个缺口取前2-3个主路径问题
    current_gap = ""
    gap_questions = {}
    for line in content.split("\n"):
        stripped = line.strip()
        # 检测进入缺口区
        gap_match = re.match(r"^#{1,3}\s*缺口[^\s]*[：:]\s*(.+)", stripped)
        if gap_match:
            current_gap = gap_match.group(1).strip()
            gap_questions[current_gap] = []
        # 提取主路径引导的问句
        if current_gap and re.match(r"^[①②③④][\s　]", stripped):
            # 去掉引导符，提取句子主干（到句号或问号）
            q = re.sub(r"^[①②③④][\s　]*", "", stripped)
            q = q.split("？")[0].split("？")[0].split("。")[0].strip()
            if q and len(q) > 8 and len(gap_questions.get(current_gap, [])) < 2:
                gap_questions[current_gap].append(q)

    # 添加缺口级别的问题
    for gap_qs in gap_questions.values():
        questions.extend(gap_qs)

    # 策略3：从 step4_internal.json 兜底
    if not questions:
        internal_path = os.path.join(project_dir, "step4", "step4_internal.json")
        if os.path.exists(internal_path):
            with open(internal_path, "r", encoding="utf-8") as f:
                internal = json.load(f)
            for gap in internal.get("gaps", []):
                for q in gap.get("verification_questions", []):
                    questions.append(q)
        # 备用：从 meeting_brief_md 中的追问树提取
        if not questions:
            for section in content.split("\n"):
                if section.strip().startswith("**问：**"):
                    q = section.replace("**问：**", "").strip()
                    if q:
                        questions.append(q)
    return questions


def _load_dialogue_history(project_dir):
    """加载对话历史"""
    path = os.path.join(project_dir, "v2_context", "dialogue_history.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [DialogueTurn(**d) for d in data]
    return []


def _load_v2_context(project_dir):
    """加载 v2_context 目录下的所有沉淀数据"""
    v2_ctx_dir = os.path.join(project_dir, "v2_context")
    if not os.path.exists(v2_ctx_dir):
        return {"questions": [], "industry_insights": [], "user_profile": []}

    questions = _load_json(os.path.join(v2_ctx_dir, "questions.json")) or []
    insights = _load_json(os.path.join(v2_ctx_dir, "industry_insights.json")) or []
    user_profile = _load_json(os.path.join(v2_ctx_dir, "user_profile_candidates.json")) or []

    return {
        "questions": questions,
        "industry_insights": insights,
        "user_profile": user_profile
    }


def _load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ============================================================
# Profile 相关路由
# ============================================================

@app.route("/profiles", methods=["GET"])
def list_profiles():
    """列出可选的 fund profiles"""
    profiles = list_fund_profiles()
    return jsonify({
        "status": "ok",
        "profiles": profiles,
        "default_profile_id": DEFAULT_PROFILE_ID
    })


@app.route("/project/<project_id>/set_profile", methods=["POST"])
def set_project_profile(project_id):
    """设置项目的 fund profile"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    data = request.get_json() or {}
    profile_id = data.get("profile_id", DEFAULT_PROFILE_ID)

    # 加载 profile 并保存
    profile = load_profile(profile_id)
    save_project_profile(project_dir, profile)

    return jsonify({
        "status": "ok",
        "profile": profile,
        "profile_summary": get_profile_summary(profile)
    })


@app.route("/project/<project_id>/get_profile", methods=["GET"])
def get_project_profile_route(project_id):
    """获取项目的当前 fund profile"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "项目不存在"}), 404

    profile = load_project_profile(project_dir)

    return jsonify({
        "status": "ok",
        "profile": profile,
        "profile_summary": get_profile_summary(profile)
    })


# ============================================================
# 反馈标注模块（1.0 精修）
# ============================================================

# --- 自由输入自动整理 ---
@app.route("/api/feedback/normalize-human-note", methods=["POST"])
def normalize_human_note():
    """将用户乱写的初判文字整理成结构化字段"""
    payload = request.get_json(force=True)
    raw_note = payload.get("raw_note", "").strip()

    if not raw_note:
        return jsonify({"error": "raw_note 不能为空"}), 400

    try:
        # HumanNoteNormalizer 期望 call_llm_func(prompt) -> str
        # call_deepseek 需要 (system_prompt, user_prompt)，需要适配器
        def llm_wrapper(prompt: str) -> str:
            return call_deepseek(system_prompt="", user_prompt=prompt)
        normalizer = HumanNoteNormalizer(call_llm_func=llm_wrapper)
        result = normalizer.normalize(raw_note)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- 保存人工初判（Pre-AI）---
@app.route("/api/feedback/save-pre-ai", methods=["POST"])
def save_pre_ai_feedback():
    """
    保存人工初判数据。
    可以覆盖同一 project_id 的旧记录。
    """
    payload = request.get_json(force=True)

    required = ["project_id", "project_name", "profile_id", "human_pre_ai_judgement"]
    for key in required:
        if key not in payload:
            return jsonify({"error": f"缺少必填字段: {key}"}), 400

    judgement = payload["human_pre_ai_judgement"]

    # ── Upsert 逻辑：按 project_id 查找现有记录 ──────────────────────
    project_id = payload["project_id"]
    existing = find_feedback_by_project(project_id)

    if existing:
        # 有记录 → 合并更新（保留旧记录中已填、但本次未提交的字段）
        existing["project_name"] = payload.get("project_name", existing.get("project_name", ""))
        existing["bp_source"] = payload.get("bp_source", existing.get("bp_source", ""))
        existing["profile_id"] = payload["profile_id"]
        existing["profile_type"] = payload.get("profile_type", existing.get("profile_type", "fund"))
        existing["annotator"] = payload.get("annotator", existing.get("annotator", ""))

        # 合并人工初判字段：新值为空时保留旧值
        old_j = existing.get("human_pre_ai_judgement", {})
        new_j = judgement
        existing["human_pre_ai_judgement"] = {
            "one_liner":         new_j.get("one_liner")         or old_j.get("one_liner", ""),
            "current_business":  new_j.get("current_business")  or old_j.get("current_business", ""),
            "future_story":      new_j.get("future_story")      or old_j.get("future_story", ""),
            "real_customer":     new_j.get("real_customer")     or old_j.get("real_customer", ""),
            "market_view":       new_j.get("market_view")       or old_j.get("market_view", ""),
            "decision":          new_j.get("decision", "maybe_meet"),
            "priority":          new_j.get("priority", "medium"),
            "confidence":        new_j.get("confidence", "medium"),
            "reasons_to_meet":   new_j.get("reasons_to_meet")   if new_j.get("reasons_to_meet") else old_j.get("reasons_to_meet", []),
            "reasons_to_pass":   new_j.get("reasons_to_pass")   if new_j.get("reasons_to_pass") else old_j.get("reasons_to_pass", []),
            "key_unknowns":      new_j.get("key_unknowns")     if new_j.get("key_unknowns") else old_j.get("key_unknowns", []),
            "must_ask_questions":new_j.get("must_ask_questions")if new_j.get("must_ask_questions") else old_j.get("must_ask_questions", []),
            "raw_note":          new_j.get("raw_note")          or old_j.get("raw_note", ""),
        }
        existing["updated_at"] = datetime.now().isoformat()
        case = existing
    else:
        # 无记录 → 创建新 case
        case = {
            "project_id": project_id,
            "project_name": payload.get("project_name", ""),
            "industry": payload.get("industry", ""),
            "bp_source": payload.get("bp_source", ""),
            "profile_id": payload["profile_id"],
            "profile_type": payload.get("profile_type", "fund"),
            "annotator": payload.get("annotator", ""),
            "human_pre_ai_judgement": {
                "one_liner":         judgement.get("one_liner", ""),
                "current_business":  judgement.get("current_business", ""),
                "future_story":      judgement.get("future_story", ""),
                "real_customer":     judgement.get("real_customer", ""),
                "market_view":       judgement.get("market_view", ""),
                "decision":          judgement.get("decision", "maybe_meet"),
                "priority":          judgement.get("priority", "medium"),
                "confidence":        judgement.get("confidence", "medium"),
                "reasons_to_meet":   judgement.get("reasons_to_meet") or [],
                "reasons_to_pass":   judgement.get("reasons_to_pass") or [],
                "key_unknowns":      judgement.get("key_unknowns") or [],
                "must_ask_questions": judgement.get("must_ask_questions") or [],
                "raw_note":          judgement.get("raw_note", ""),
            },
            "system_1_0_snapshot": {},
            "human_post_ai_feedback": {},
            "knowledge_candidates": {},
            "review_status": "pre_ai_saved",
        }

    saved = append_feedback_case(case)
    return jsonify({"status": "ok", "feedback_id": saved["feedback_id"]})


def _merge_raw_note(new_note: str, old_note: str) -> str:
    """
    raw_note 合并策略（零丢失原则）：
    - 新值非空 且 与旧值相同 → 直接返回新值（幂等）
    - 新值非空 且 与旧值不同 → 拼接（旧值在前，新值在后，分隔符标注时间戳）
    - 新值为空 → 保留旧值，不覆盖
    """
    new_note = (new_note or "").strip()
    old_note = (old_note or "").strip()

    if not new_note:
        # 前端没有传内容（空提交），保留已有内容
        return old_note

    if new_note == old_note:
        # 内容一致，幂等保存
        return new_note

    if not old_note:
        # 第一次写入
        return new_note

    # 新旧都有内容且不同：拼接保留，确保一字不丢
    from datetime import datetime as _dt
    separator = f"\n\n{'─' * 40}\n【追加更新 {_dt.now().strftime('%Y-%m-%d %H:%M')}】\n{'─' * 40}\n"
    return old_note + separator + new_note


# --- 保存第一直觉（Layer 1）---
@app.route("/api/feedback/save-first-impression", methods=["POST"])
def save_first_impression():
    """
    保存第一直觉，独立于深思层。
    每次保存会合并（不覆盖已有直觉内容）。
    """
    payload = request.get_json(force=True)
    project_id = payload.get("project_id")
    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400

    fi = payload.get("first_impression", {})

    existing = find_feedback_by_project(project_id)

    def merge_field(new_val, old_val, default=""):
        """新值非空则用新值，否则保留旧值"""
        return new_val if new_val and new_val != default else (old_val or default)

    if existing:
        old_fi = existing.get("first_impression", {})
        merged = {
            # 基础信息
            "one_liner":        merge_field(fi.get("one_liner"), old_fi.get("one_liner", "")),
            "top_confusion":    merge_field(fi.get("top_confusion"), old_fi.get("top_confusion", "")),
            "decision":         merge_field(fi.get("decision"), old_fi.get("decision", "")),
            "priority":         merge_field(fi.get("priority"), old_fi.get("priority", "")),
            "confidence":       merge_field(fi.get("confidence"), old_fi.get("confidence", "")),
            # 深入分析
            "current_business": merge_field(fi.get("current_business"), old_fi.get("current_business", "")),
            "future_story":     merge_field(fi.get("future_story"), old_fi.get("future_story", "")),
            "real_customer":    merge_field(fi.get("real_customer"), old_fi.get("real_customer", "")),
            "market_view":      merge_field(fi.get("market_view"), old_fi.get("market_view", "")),
            # 判断理由
            "reasons_to_meet":  fi.get("reasons_to_meet") if fi.get("reasons_to_meet") else old_fi.get("reasons_to_meet", []),
            "reasons_to_pass":  fi.get("reasons_to_pass") if fi.get("reasons_to_pass") else old_fi.get("reasons_to_pass", []),
            "key_unknowns":     fi.get("key_unknowns") if fi.get("key_unknowns") else old_fi.get("key_unknowns", []),
            "must_ask_questions": fi.get("must_ask_questions") if fi.get("must_ask_questions") else old_fi.get("must_ask_questions", []),
            # 原始笔记（直接覆盖）
            "raw_note":         fi.get("raw_note") or old_fi.get("raw_note", ""),
        }
        existing["first_impression"] = merged
        # 升级状态
        if existing.get("deep_reflection"):
            existing["review_status"] = "deep_reflection_saved"
        else:
            existing["review_status"] = "first_impression_saved"
        existing["updated_at"] = datetime.now().isoformat()
        case = existing
    else:
        case = {
            "project_id":   project_id,
            "project_name": payload.get("project_name", ""),
            "profile_id":   payload.get("profile_id", "neutral_investor"),
            "profile_type": payload.get("profile_type", "fund"),
            "bp_source":    "",
            "first_impression": {
                "one_liner":           fi.get("one_liner", ""),
                "top_confusion":       fi.get("top_confusion", ""),
                "decision":            fi.get("decision", ""),
                "priority":            fi.get("priority", ""),
                "confidence":          fi.get("confidence", ""),
                "current_business":    fi.get("current_business", ""),
                "future_story":        fi.get("future_story", ""),
                "real_customer":       fi.get("real_customer", ""),
                "market_view":         fi.get("market_view", ""),
                "reasons_to_meet":     fi.get("reasons_to_meet", []),
                "reasons_to_pass":     fi.get("reasons_to_pass", []),
                "key_unknowns":        fi.get("key_unknowns", []),
                "must_ask_questions":  fi.get("must_ask_questions", []),
                "raw_note":            fi.get("raw_note", ""),
            },
            "deep_reflection": {},
            "system_1_0_snapshot": {},
            "human_post_ai_feedback": {},
            "knowledge_candidates": {},
            "review_status": "first_impression_saved",
        }

    saved = append_feedback_case(case)
    return jsonify({"status": "ok", "feedback_id": saved["feedback_id"]})




# --- AI 自动整理直觉层（Layer 1）---
def _build_normalize_intuition_prompt(company_name, raw_note):
    """构建 AI 整理直觉笔记的 prompt"""
    return f"""你是一个专业的投资分析师，正在帮助整理投资人对项目的第一直觉判断。

项目名称：{company_name}

以下是投资人对这个项目的原始笔记（可能是碎片化的、随意的、甚至自相矛盾的判断）：

---
{raw_note}
---

请仔细阅读以上笔记，提取并结构化成以下字段。即使笔记中没有明确提到，也要基于内容合理推断：

请以 JSON 格式输出：
{{
    "one_liner": "一句话理解这家公司是干什么的（30字以内）",
    "top_confusion": "投资人最困惑或最不确定的一个点",
    "decision": "判断：meet（建议约）/ maybe_meet（可以约）/ request_materials（先要材料）/ pass（直接pass）",
    "priority": "优先级：高/中/低",
    "confidence": "信心度：高/中/低（对这个判断有多大把握）",
    "current_business": "当前真实业务是什么（只写现在的，不确定的写「不确定」）",
    "future_story": "未来故事或包装叙事（BP里哪些可能是夸大的）",
    "real_customer": "真正的客户是谁，谁会真的付钱",
    "market_view": "对市场容量和机会的看法",
    "reasons_to_meet": ["值得约见的一个理由"],
    "reasons_to_pass": ["不值得约见的一个理由（如果有）"],
    "key_unknowns": ["最需要搞清楚的一个问题"],
    "must_ask_questions": ["见面时必须问的一个核心问题"]
}}

注意：
- 如果笔记中某些信息确实没有提到，相关字段填空字符串
- decision 字段必须从 meet/maybe_meet/request_materials/pass 中选择
- reasons_to_meet 和 reasons_to_pass 应该是列表，即使只有一个也要用列表格式
- 推理过程不要写在输出里，直接输出 JSON
"""


@app.route("/api/feedback/normalize-first-impression", methods=["POST"])
def normalize_first_impression():
    """
    接收用户的自由书写笔记，AI 自动识别并填充各结构化字段。
    """
    from services.deepseek_service import call_deepseek

    payload = request.get_json(force=True)
    project_id = payload.get("project_id")
    raw_note = payload.get("raw_note", "").strip()

    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400
    if not raw_note:
        return jsonify({"error": "请先填写原始笔记"}), 400

    # 加载项目信息作为上下文
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    meta = get_project_meta(project_dir) if os.path.exists(project_dir) else {}
    company_name = meta.get("company_name", "未知公司")

    # 构建 prompt
    system_prompt = "你是一个专业的投资分析师。你会严格以 JSON 格式输出，不要包含任何其他文字。"
    user_prompt = _build_normalize_intuition_prompt(company_name, raw_note)

    try:
        content = call_deepseek(system_prompt, user_prompt, temperature=0.3, max_tokens=4096)
        print(f"[normalize_first_impression] raw response: {content[:200]}...", flush=True)

        # 清理可能的 markdown 代码块
        content = content.strip()
        if content.startswith("```"):
            # 去掉 ```json 或 ``` 等前缀和 ``` 后缀
            lines = content.split("\n")
            content = "\n".join(lines[1:])  # 去掉第一行
            if content.endswith("```"):
                content = content[:-3]
        content = content.strip()

        structured = json.loads(content)

        return jsonify({
            "status": "ok",
            "structured": {
                "one_liner":           structured.get("one_liner", ""),
                "top_confusion":       structured.get("top_confusion", ""),
                "decision":           structured.get("decision", ""),
                "priority":           structured.get("priority", ""),
                "confidence":         structured.get("confidence", ""),
                "current_business":   structured.get("current_business", ""),
                "future_story":       structured.get("future_story", ""),
                "real_customer":      structured.get("real_customer", ""),
                "market_view":        structured.get("market_view", ""),
                "reasons_to_meet":    structured.get("reasons_to_meet", []),
                "reasons_to_pass":    structured.get("reasons_to_pass", []),
                "key_unknowns":        structured.get("key_unknowns", []),
                "must_ask_questions":  structured.get("must_ask_questions", []),
            }
        })
    except json.JSONDecodeError as e:
        print(f"[normalize_first_impression] JSON parse error: {e}, content: {content[:500] if 'content' in dir() else 'N/A'}", flush=True)
        return jsonify({"error": "AI 返回格式错误，请重试"}), 500
    except Exception as e:
        print(f"[normalize_first_impression] error: {e}", flush=True)
        return jsonify({"error": f"整理失败: {str(e)}"}), 500





# --- 保存深入判断（Layer 2）---
@app.route("/api/feedback/save-deep-reflection", methods=["POST"])
def save_deep_reflection():
    """
    保存深入判断，独立于直觉层。
    每次保存会合并（不覆盖已有直觉层内容）。
    """
    payload = request.get_json(force=True)
    project_id = payload.get("project_id")
    if not project_id:
        return jsonify({"error": "缺少 project_id"}), 400

    dr = payload.get("deep_reflection", {})

    existing = find_feedback_by_project(project_id)

    if existing:
        old_dr = existing.get("deep_reflection", {})
        merged = {
            "one_liner":          dr.get("one_liner")          or old_dr.get("one_liner", ""),
            "current_business":   dr.get("current_business")   or old_dr.get("current_business", ""),
            "future_story":       dr.get("future_story")       or old_dr.get("future_story", ""),
            "real_customer":      dr.get("real_customer")      or old_dr.get("real_customer", ""),
            "market_view":        dr.get("market_view")        or old_dr.get("market_view", ""),
            "decision":           dr.get("decision")           or old_dr.get("decision", ""),
            "priority":           dr.get("priority", "medium"),
            "confidence":         dr.get("confidence", "medium"),
            "reasons_to_meet":    dr.get("reasons_to_meet") if dr.get("reasons_to_meet") else old_dr.get("reasons_to_meet", []),
            "reasons_to_pass":    dr.get("reasons_to_pass") if dr.get("reasons_to_pass") else old_dr.get("reasons_to_pass", []),
            "key_unknowns":       dr.get("key_unknowns")      if dr.get("key_unknowns") else old_dr.get("key_unknowns", []),
            "must_ask_questions": dr.get("must_ask_questions") if dr.get("must_ask_questions") else old_dr.get("must_ask_questions", []),
            # ⚠️ raw_note 是原始输入源文件，用于规则蒸馏和认知回溯，绝对不能丢失或截断。
            # 规则：新值非空 → 必须原文覆盖；新值为空 → 保留已有内容；
            #       如果新旧都有内容且不同 → 用换行符拼接，确保不丢失任何内容。
            "raw_note": _merge_raw_note(dr.get("raw_note", ""), old_dr.get("raw_note", "")),
        }
        existing["deep_reflection"] = merged
        existing["bp_source"] = payload.get("bp_source") or existing.get("bp_source", "")
        existing["profile_id"] = payload.get("profile_id") or existing.get("profile_id", "neutral_investor")
        existing["review_status"] = "deep_reflection_saved"
        existing["updated_at"] = datetime.now().isoformat()
        case = existing
    else:
        case = {
            "project_id":   project_id,
            "project_name": payload.get("project_name", ""),
            "profile_id":   payload.get("profile_id", "neutral_investor"),
            "profile_type": payload.get("profile_type", "fund"),
            "bp_source":    payload.get("bp_source", ""),
            "first_impression": {},
            "deep_reflection": {
                "one_liner":          dr.get("one_liner", ""),
                "current_business":   dr.get("current_business", ""),
                "future_story":       dr.get("future_story", ""),
                "real_customer":      dr.get("real_customer", ""),
                "market_view":        dr.get("market_view", ""),
                "decision":           dr.get("decision", ""),
                "priority":           dr.get("priority", "medium"),
                "confidence":         dr.get("confidence", "medium"),
                "reasons_to_meet":    dr.get("reasons_to_meet") or [],
                "reasons_to_pass":    dr.get("reasons_to_pass") or [],
                "key_unknowns":       dr.get("key_unknowns") or [],
                "must_ask_questions": dr.get("must_ask_questions") or [],
                "raw_note":           dr.get("raw_note", ""),
            },
            "system_1_0_snapshot": {},
            "human_post_ai_feedback": {},
            "knowledge_candidates": {},
            "review_status": "deep_reflection_saved",
        }

    saved = append_feedback_case(case)
    return jsonify({"status": "ok", "feedback_id": saved["feedback_id"]})


# --- 保存人机对比反馈（Post-AI）---
@app.route("/api/feedback/save-post-ai", methods=["POST"])
def save_post_ai_feedback():
    """
    保存人机对比反馈，覆盖同一 feedback_id 的旧记录。
    """
    payload = request.get_json(force=True)
    feedback_id = payload.get("feedback_id")

    if not feedback_id:
        return jsonify({"error": "feedback_id 不能为空"}), 400

    old_case = find_feedback_case(feedback_id)
    if not old_case:
        return jsonify({"error": "未找到对应的 feedback case，请先保存人工初判"}), 404

    # 合并更新
    old_case["system_1_0_snapshot"] = payload.get("system_1_0_snapshot") or {}
    old_case["human_post_ai_feedback"] = payload.get("human_post_ai_feedback") or {}
    old_case["review_status"] = "feedback_completed"

    saved = append_feedback_case(old_case)
    return jsonify({"status": "ok", "feedback_id": saved["feedback_id"]})


# --- 生成候选知识 ---
@app.route("/api/feedback/generate-knowledge-candidates", methods=["POST"])
def generate_knowledge_candidates():
    """从一条 feedback case 生成候选知识"""
    payload = request.get_json(force=True)
    feedback_id = payload.get("feedback_id")

    if not feedback_id:
        return jsonify({"error": "feedback_id 不能为空"}), 400

    case = find_feedback_case(feedback_id)
    if not case:
        return jsonify({"error": "未找到对应的 feedback case"}), 404

    if not case.get("human_pre_ai_judgement"):
        return jsonify({"error": "该 case 还没有人工初判数据"}), 400

    try:
        generator = KnowledgeCandidateGenerator(call_llm=call_deepseek)
        candidates = generator.generate(case)

        # 保存候选知识
        case["knowledge_candidates"] = candidates
        case["review_status"] = "candidate_generated"
        append_feedback_case(case)

        return jsonify(candidates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- 分析自由备注并自动填表 ---
@app.route("/api/feedback/analyze-free-note", methods=["POST"])
def analyze_free_note():
    """
    接收用户的自由备注 + AI输出，分析后返回结构化数据用于自动填表
    核心功能：训练数据采集
    """
    payload = request.get_json(force=True)
    free_note = payload.get("free_note", "").strip()
    ai_outputs = payload.get("ai_outputs", {})

    if not free_note:
        return jsonify({"error": "备注内容不能为空"}), 400

    if len(free_note) < 10:
        return jsonify({"error": "备注内容太短，请输入更多内容"}), 400

    try:
        import json as json_lib

        # 构建更强大的分析 prompt
        system_prompt = """你是一个专业的投资评审反馈分析助手。你的任务是把用户对AI判断的自由评价，解析成结构化人机对比反馈。

输入包括：
1. 用户自由评价 raw_human_feedback（最重要，不允许修改）
2. AI输出结果，包括 Step3 / Step3B / Step4 / Step5

请完成以下分析并输出 JSON：

1. evaluation（评价字段）：
   - essence_alignment: 本质理解一致程度，取值 "aligned" | "partially_aligned" | "misaligned" | "unclear"
   - essence_score: 本质理解评分，1-5整数
   - meeting_judgement_alignment: 约交流判断是否一致，取值 "aligned" | "partially_aligned" | "misaligned" | "unclear"
   - reasoning_score: 理由覆盖评分，1-5整数
   - question_coverage_score: 问题覆盖评分，1-5整数
   - overall_usefulness_score: 总体有用性，1-5整数
   - ai_bias_direction: AI判断偏差方向，取值 "too_optimistic" | "too_conservative" | "wrong_focus" | "too_generic" | "not_applicable"
   - wrong_steps: AI主要错在哪一步，数组，取值 "step0_profile" | "step1_essence" | "step3_structure" | "step3b_consistency" | "step4_gap_ranking" | "step5_decision"
   - error_types: 错误类型数组，取值 "missed_company_essence" | "treated_future_as_current" | "overestimated_tech_moat" | "underestimated_tech_moat" | "overestimated_market_size" | "underestimated_market_size" | "missed_packaging_story" | "missed_team_or_endorsement_packaging" | "ignored_fund_profile" | "questions_too_broad" | "missed_key_question" | "too_optimistic" | "too_conservative" | "wrong_priority" | "overweighted_secondary_issue"
   - brief_error_summary: 简单说明AI哪里错了，50字以内字符串

2. core_difference（核心差异记录区 - 最重要！）：
   - ai_main_thesis: AI选的主线，字符串数组
   - human_main_thesis: 用户认为正确的主线，字符串数组
   - missed_key_issues: AI漏掉的关键问题，字符串数组
   - overweighted_issues: AI过度提权的问题，字符串数组
   - underweighted_issues: AI权重不足的问题，字符串数组
   - priority_correction: 正确优先级修正，对象数组，格式 [{"rank": 1, "issue": "问题描述"}, ...]
   - one_sentence_learning: 一句话学习，总结核心教训，80字以内

重要规则：
- 不要替用户新增没有表达过的观点
- 如果用户没有明确提到某个字段，可以留空数组或空字符串
- one_sentence_learning 必须从用户的评价中提炼，不能编造
- 只输出 JSON，不要有任何其他内容"""

        # 构建用户 prompt，包含 AI 输出供对比
        ai_summary = ""
        if ai_outputs:
            if ai_outputs.get("step5"):
                step5 = ai_outputs["step5"]
                if isinstance(step5, dict):
                    ai_summary += f"\n【AI Step5 决策】：\n"
                    ai_summary += f"- 一句话判断：{step5.get('current_hypothesis', step5.get('one_liner', '无'))}\n"
                    ai_summary += f"- 决策：{step5.get('decision', '无')}\n"
            if ai_outputs.get("step4"):
                step4 = ai_outputs["step4"]
                if isinstance(step4, dict):
                    meeting_brief = step4.get("meeting_brief_md", "")
                    if meeting_brief:
                        ai_summary += f"\n【AI Step4 开会问题】：\n"
                        # 提取前500字
                        ai_summary += meeting_brief[:500] + "..." if len(meeting_brief) > 500 else meeting_brief

        user_prompt = f"""请分析以下用户对AI判断的评价，提取结构化评估信息：

【用户原始评价】：
{free_note}

{ai_summary}

只输出 JSON，不要有任何其他内容。"""

        result = call_deepseek(system_prompt=system_prompt, user_prompt=user_prompt, max_retries=2)

        # 尝试解析 JSON
        import re

        # 提取 JSON（可能有 markdown 包裹）
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            parsed = json_lib.loads(json_match.group())
            return jsonify({"status": "ok", "analysis": parsed})
        else:
            return jsonify({"error": "无法解析分析结果，请重试", "raw": result[:500]}), 500

    except Exception as e:
        return jsonify({"error": f"分析失败: {str(e)}"}), 500


# --- 保存对比反馈 V2（训练数据采集） ---
@app.route("/api/feedback/save-comparison-v2", methods=["POST"])
def save_comparison_v2():
    """
    保存人机对比反馈（新版训练数据格式）
    保存完整数据：原始文本 + evaluation + core_difference + ai_outputs_snapshot
    """
    import sys
    print("[SAVE] ROUTE HIT", flush=True)
    payload = request.get_json(force=True)
    feedback_id = payload.get("feedback_id")
    project_id = payload.get("project_id")
    print(f"[SAVE] payload keys={list(payload.keys())}", flush=True)
    print(f"[SAVE] evaluation payload keys={list(payload.get('evaluation', {}).keys())}", flush=True)
    print(f"[SAVE] core_difference payload keys={list(payload.get('core_difference', {}).keys())}", flush=True)
    print(f"[SAVE] core_diff payload content={payload.get('core_difference')}", flush=True)

    print(f"[SAVE_COMPARISON] feedback_id={feedback_id}, project_id={project_id}", flush=True)
    print(f"[SAVE_COMPARISON] payload keys={list(payload.keys())}", flush=True)
    print(f"[SAVE_COMPARISON] evaluation fields: {list(payload.get('evaluation', {}).keys())}", flush=True)
    print(f"[SAVE_COMPARISON] core_difference fields: {list(payload.get('core_difference', {}).keys())}", flush=True)

    if not feedback_id:
        return jsonify({"error": "feedback_id 不能为空"}), 400

    # 查找现有记录
    old_case = find_feedback_case(feedback_id)
    if not old_case:
        return jsonify({"error": "未找到对应的 feedback case，请先保存人工初判"}), 404

    # 更新字段（写入两套字段名，保证兼容性）
    # 新版字段（训练数据格式）
    old_case["raw_human_feedback"] = payload.get("raw_human_feedback", "")
    old_case["ai_outputs_snapshot"] = payload.get("ai_outputs_snapshot", {})
    old_case["evaluation"] = payload.get("evaluation", {})
    old_case["core_difference"] = payload.get("core_difference", {})

    # 兼容下载接口 `_build_comparison_md` 期望的字段
    # 把 evaluation/core_difference 映射到 human_post_ai_feedback 下
    evaluation = payload.get("evaluation", {})
    core_diff = payload.get("core_difference", {})
    post_feedback = {
        "system_alignment": {
            "decision_match": evaluation.get("decision_match", False),
            "core_understanding_alignment": evaluation.get("core_understanding_alignment", "未知"),
            "core_understanding_score": evaluation.get("core_understanding_score", "未评分"),
            "decision_bias": evaluation.get("decision_bias", ""),
            "reason_match_score": evaluation.get("reason_match_score", "未评分"),
            "question_coverage_score": evaluation.get("question_coverage_score", "未评分"),
            "overall_usefulness_score": evaluation.get("overall_usefulness_score", "未评分"),
        },
        "error_analysis": core_diff,
        "question_feedback": evaluation.get("key_questions", [])
    }
    old_case["human_post_ai_feedback"] = post_feedback
    old_case["review_status"] = "comparison_saved"

    # 保存
    saved = append_feedback_case(old_case)
    print(f"[SAVE] saved feedback_id={saved.get('feedback_id')}, review_status={saved.get('review_status')}", flush=True)
    print(f"[SAVE] case keys={list(saved.keys())}", flush=True)
    print(f"[SAVE] evaluation keys={list(saved.get('evaluation', {}).keys())}", flush=True)
    print(f"[SAVE] core_difference keys={list(saved.get('core_difference', {}).keys())}", flush=True)
    print(f"[SAVE] core_diff content={saved.get('core_difference')}", flush=True)
    return jsonify({"status": "ok", "feedback_id": saved["feedback_id"]})


# --- 获取项目当前反馈状态 ---
@app.route("/api/feedback/status/<project_id>", methods=["GET"])
def get_feedback_status(project_id):
    """获取某项目的反馈标注状态"""
    case = find_feedback_by_project(project_id)
    if not case:
        return jsonify({"has_feedback": False, "review_status": None})

    return jsonify({
        "has_feedback": True,
        "feedback_id": case.get("feedback_id"),
        "review_status": case.get("review_status"),
        # 两层结构
        "has_first_impression": bool(case.get("first_impression", {}).get("one_liner")),
        "has_deep_reflection": bool(case.get("deep_reflection", {}).get("one_liner")),
        # 兼容旧结构
        "has_pre_ai": bool(case.get("human_pre_ai_judgement", {}).get("one_liner")),
        "has_post_ai": bool(case.get("human_post_ai_feedback", {}).get("system_alignment")),
        "has_knowledge_candidates": bool(case.get("knowledge_candidates")),
    })


# --- 下载完整对比文档 ---
@app.route("/project/<project_id>/comparison-doc")
def comparison_doc(project_id):
    """生成并下载完整对比文档（人工初判 + AI报告 + 人机对比）"""
    import sys
    print(f"[DOWNLOAD] ROUTE HIT project_id={project_id}", flush=True)
    from services.pipeline_v1 import load_pipeline_results
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return "项目不存在", 404

    meta = get_project_meta(project_dir)
    case = find_feedback_by_project(project_id)

    print(f"[DOWNLOAD] project_id={project_id}, case found: {case is not None}", flush=True)
    if case:
        print(f"[DOWNLOAD] feedback_id={case.get('feedback_id')}, review_status={case.get('review_status')}", flush=True)
        print(f"[DOWNLOAD] case keys={list(case.keys())}", flush=True)
        print(f"[DOWNLOAD] core_diff keys={list(case.get('core_difference', {}).keys())}", flush=True)
        print(f"[DOWNLOAD] evaluation keys={list(case.get('evaluation', {}).keys())}", flush=True)
        print(f"[DOWNLOAD] core_diff content={case.get('core_difference')}", flush=True)

    if not case:
        return "该项目还没有反馈数据", 404

    # 加载 1.0 AI 结果
    pipeline_results = load_pipeline_results(project_dir)

    # 生成 Markdown 文档
    doc = _build_comparison_md(meta, case, pipeline_results)
    print(f"[DOWNLOAD] generated doc length={len(doc)} chars", flush=True)
    print(f"[DOWNLOAD] doc first 500 chars:\n{doc[:500]}", flush=True)

    # 写入临时文件
    tmp_file = os.path.join(project_dir, f"对比文档_{meta.get('company_name', project_id)}.md")
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(doc)

    return send_file(tmp_file, as_attachment=True,
                    download_name=f"对比文档_{meta.get('company_name', project_id)}.md",
                    mimetype="text/markdown; charset=utf-8")


def _list_section(title, items):
    """渲染一个列表 section"""
    lines = [f"### {title}"]
    if not items:
        lines.append("- （未填写）")
    elif isinstance(items, str):
        lines.append(f"- {items}")
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                text = item.get("content", item.get("text", item.get("rule", str(item))))
                lines.append(f"- {text}")
            else:
                lines.append(f"- {item}")
    else:
        lines.append(f"- {items}")
    return "\n".join(lines) + "\n"


def _build_comparison_md(meta, case, pipeline_results):
    """构建对比 Markdown 文档（四段式：直觉层 → AI分析 → 深思层 → 人机对比）"""
    # 展开新版字段
    evaluation = case.get("evaluation", {})
    core_diff = case.get("core_difference", {})
    ai_snapshot = case.get("ai_outputs_snapshot", {})
    raw_feedback = case.get("raw_human_feedback", "")

    # 新版字段（直觉层 + 深思层）
    first_impression = case.get("first_impression", {})
    deep_reflection = case.get("deep_reflection", {})

    # 旧版兼容字段
    judgement = case.get("human_pre_ai_judgement", {})

    step5 = pipeline_results.get("step5", {})
    ai_decision = step5.get("meeting_decision", step5.get("decision", "未知"))
    ai_must_ask = step5.get("must_ask_questions", [])

    # 决策映射
    decision_map = {
        "meet": "建议约",
        "maybe_meet": "可以约",
        "request_materials": "先要材料",
        "pass": "直接 Pass",
    }

    # 判断来源：优先用新版 first_impression，否则用旧版
    if first_impression:
        human_source = first_impression
        human_dec = decision_map.get(first_impression.get("decision", ""), first_impression.get("decision", "未知"))
    else:
        human_source = judgement
        human_dec = decision_map.get(judgement.get("decision", ""), judgement.get("decision", "未知"))

    # 对齐判断（兼容实际存储的字段名，可能是布尔或字符串）
    decision_match = evaluation.get("meeting_judgement_alignment") or evaluation.get("decision_match")
    # 字符串 "一致"/"aligned" 或布尔 True 视为一致
    if decision_match in (True, "一致", "aligned", "fully_aligned"):
        match_text = "一致"
    elif decision_match in (False, "不一致", "misaligned", "fully_misaligned"):
        match_text = "不一致"
    else:
        # partially_aligned 等情况显示原始值
        match_text = str(decision_match) if decision_match else "未填写"

    lines = [
        f"# {meta.get('company_name', '未知公司')} — BP研判对比文档",
        "",
        f"**项目ID**: {meta.get('project_id', '')}",
        f"**BP来源**: {case.get('bp_source', '未知')}",
        f"**投资人画像**: {case.get('profile_id', 'neutral_investor')}",
        f"**标注时间**: {case.get('created_at', '')}",
        "",
        "---",
        "",
        "# 一、人工直觉层判断（30秒速判，不看AI）",
        "",
        "## 1.1 一句话理解",
        human_source.get("one_liner", ""),
        "",
        "## 1.2 当前真实业务",
        human_source.get("current_business", ""),
        "",
        "## 1.3 未来故事 / 包装叙事",
        human_source.get("future_story", ""),
        "",
        "## 1.4 客户与付费逻辑",
        human_source.get("real_customer", ""),
        "",
        "## 1.5 市场 / 容量判断",
        human_source.get("market_view", ""),
        "",
        "## 1.6 是否约第一轮交流",
        f"**判断**: {human_dec}（优先级: {human_source.get('priority', '未知')}，信心: {human_source.get('confidence', '未知')}）",
        "",
        "### 值得约的理由",
    ]
    for r in human_source.get("reasons_to_meet", []):
        lines.append(f"- {r}")
    if not human_source.get("reasons_to_meet"):
        lines.append("- （未填写）")

    lines += ["", "### 不值得约 / 暂不约的理由",]
    for r in human_source.get("reasons_to_pass", []):
        lines.append(f"- {r}")
    if not human_source.get("reasons_to_pass"):
        lines.append("- （未填写）")

    lines += [
        "",
        "### 关键未知点",
    ]
    for u in human_source.get("key_unknowns", []):
        lines.append(f"- {u}")
    if not human_source.get("key_unknowns"):
        lines.append("- （未填写）")

    lines += [
        "",
        "### 必须问的问题",
    ]
    for q in human_source.get("must_ask_questions", []):
        if isinstance(q, dict):
            lines.append(f"- **{q.get('question', '')}**（{q.get('why_important', '')}）")
        else:
            lines.append(f"- {q}")
    if not human_source.get("must_ask_questions"):
        lines.append("- （未填写）")

    # AI 结果
    step1 = pipeline_results.get("step1", {})

    lines += [
        "",
        "---",
        "",
        "# 二、AI 1.0 分析结果",
        "",
        "## 2.1 AI 对项目本质的理解",
        step1 if isinstance(step1, str) else (step1.get("project_essence", step1.get("core_judgement", ""))),
        "",
        "## 2.2 AI 的约 / 不约判断",
        f"**AI 判断**: {ai_decision}",
        "",
        "## 2.3 AI 理由",
        step5.get("reason", step5.get("reasoning", "")),
        "",
        "## 2.4 AI 提出的问题清单",
    ]
    for q in ai_must_ask:
        if isinstance(q, dict):
            lines.append(f"- {q.get('question', q)}")
        else:
            lines.append(f"- {q}")
    if not ai_must_ask:
        lines.append("- （无）")

    # ============ Step3B: BP 内部一致性检查 ============
    step3b = pipeline_results.get("step3b", {})
    if step3b:
        lines += [
            "",
            "---",
            "",
            "# 三、Step3B — BP 内部一致性检查（AI 自动分析）",
            "",
            "## 3.1 一致性核查",
        ]
        consistency_checks = step3b.get("consistency_checks", [])
        if consistency_checks:
            judgement_icon = {"support": "✓", "contradict": "✗", "uncertain": "?"}
            for item in consistency_checks:
                icon = judgement_icon.get(item.get("judgement", ""), "?")
                confidence = item.get("confidence", "")
                lines += [
                    f"**[{icon}] {item.get('topic', '未知维度')}**（置信度: {confidence}）",
                    f"- BP说法: {item.get('claim', '')}",
                    f"- 现实支撑: {item.get('reality', '')}",
                    f"- 缺失/问题: {item.get('gap', '')}",
                    "",
                ]
        else:
            lines.append("- （未执行一致性检查）")

        lines += ["", "## 3.2 关键矛盾", ""]
        tensions = step3b.get("tensions", [])
        if tensions:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for t in tensions:
                icon = severity_icon.get(t.get("severity", ""), "⚪")
                lines += [
                    f"**{icon} {t.get('tension', '未知矛盾')}**",
                    f"- 为什么重要: {t.get('why_it_matters', '')}",
                    "",
                ]
        else:
            lines.append("- （未发现关键矛盾）")

        lines += ["", "## 3.3 过度包装信号", ""]
        overpackaging = step3b.get("overpackaging_signals", [])
        if overpackaging:
            type_map = {
                "tech_overstatement": "🔧 技术夸大",
                "expansion_story": "📈 扩张故事",
                "team_overuse": "👥 团队过度包装",
                "vague_terms": "💭 模糊术语"
            }
            for sig in overpackaging:
                sig_type = type_map.get(sig.get("type", ""), sig.get("type", ""))
                severity = "🔴高" if sig.get("severity") == "high" else ("🟡中" if sig.get("severity") == "medium" else "🟢低")
                lines += [
                    f"**[{severity}] {sig_type}**",
                    f"- {sig.get('signal', '')}",
                    "",
                ]
        else:
            lines.append("- （未发现明显过度包装）")

        lines += [
            "",
            "## 3.4 AI 总结",
            step3b.get("summary", "（未填写）"),
        ]

    # ============ 深思层判断 ============
    # 深思层判断（如果存在）
    if deep_reflection and (deep_reflection.get("one_liner") or deep_reflection.get("current_business") or deep_reflection.get("decision")):
        deep_dec = decision_map.get(deep_reflection.get("decision", ""), deep_reflection.get("decision", "未知"))
        lines += [
            "",
            "---",
            "",
            "# 三、人工深思层判断（看完AI后修正）",
            "",
            "## 3.1 一句话理解（修正版）",
            deep_reflection.get("one_liner", ""),
            "",
            "## 3.2 当前真实业务（修正版）",
            deep_reflection.get("current_business", ""),
            "",
            "## 3.3 未来故事 / 包装叙事（修正版）",
            deep_reflection.get("future_story", ""),
            "",
            "## 3.4 客户与付费逻辑（修正版）",
            deep_reflection.get("real_customer", ""),
            "",
            "## 3.5 市场 / 容量判断（修正版）",
            deep_reflection.get("market_view", ""),
            "",
            "## 3.6 是否约第一轮交流（修正版）",
            f"**判断**: {deep_dec}（优先级: {deep_reflection.get('priority', '未知')}，信心: {deep_reflection.get('confidence', '未知')}）",
            "",
            "### 值得约的理由",
        ]
        for r in deep_reflection.get("reasons_to_meet", []):
            lines.append(f"- {r}")
        if not deep_reflection.get("reasons_to_meet"):
            lines.append("- （未填写）")

        lines += ["", "### 不值得约 / 暂不约的理由",]
        for r in deep_reflection.get("reasons_to_pass", []):
            lines.append(f"- {r}")
        if not deep_reflection.get("reasons_to_pass"):
            lines.append("- （未填写）")

        lines += [
            "",
            "### 关键未知点",
        ]
        for u in deep_reflection.get("key_unknowns", []):
            lines.append(f"- {u}")
        if not deep_reflection.get("key_unknowns"):
            lines.append("- （未填写）")

        lines += [
            "",
            "### 必须问的问题",
        ]
        for q in deep_reflection.get("must_ask_questions", []):
            if isinstance(q, dict):
                lines.append(f"- **{q.get('question', '')}**（{q.get('why_important', '')}）")
            else:
                lines.append(f"- {q}")
        if not deep_reflection.get("must_ask_questions"):
            lines.append("- （未填写）")

        # 深思层总结
        lines += [
            "",
            "### 看完AI后的认知变化",
            deep_reflection.get("cognitive_change", "（未填写）"),
            "",
            "### AI帮我纠正了什么",
            deep_reflection.get("ai_correction", "（未填写）"),
        ]

    # 人机对比（读取 evaluation + core_difference）
    lines += [
        "",
        "---",
        "",
        "# 五、人机对比标注",
        "",
        "## 5.1 核心差异记录",
        "",
        _list_section("AI选的主线", core_diff.get("ai_main_thesis")),
        _list_section("你认为正确的主线", core_diff.get("human_main_thesis")),
        _list_section("AI漏掉的关键问题", core_diff.get("missed_key_issues")),
        _list_section("AI过度提权的问题", core_diff.get("overweighted_issues")),
        _list_section("AI权重不足的问题", core_diff.get("underweighted_issues")),
        "",
        "## 5.2 一句话学习",
        core_diff.get("one_sentence_learning") or "（未填写）",
        "",
        "## 5.3 对齐评估",
        f"本质理解对齐分: {evaluation.get('essence_score', '未评分')}/5",
        f"判断是否一致: {match_text}",
        f"AI偏差方向: {evaluation.get('ai_bias_direction', '（未填写）')}",
        f"理由覆盖评分: {evaluation.get('reasoning_score', '未评分')}/5",
        f"问题覆盖评分: {evaluation.get('question_coverage_score', '未评分')}/5",
        f"总体有用性: {evaluation.get('overall_usefulness_score', '未评分')}/5",
        "",
        "## 5.4 错误归因",
        f"错误类型: {', '.join(evaluation.get('error_types', [])) or '（未填写）'}",
        f"错误所在步骤: {', '.join(evaluation.get('wrong_steps', [])) or '（未填写）'}",
        f"简要总结: {evaluation.get('brief_error_summary', '（未填写）')}",
        "",
        "## 5.5 问题质量标注",
    ]
    key_qs = evaluation.get("key_questions", [])
    if key_qs:
        quality_map = {"critical": "关键", "useful": "有用", "generic": "泛泛", "useless": "没必要"}
        for q in key_qs:
            if isinstance(q, dict):
                q_text = q.get("question", "")
                q_qual = q.get("quality", "")
                qual_text = quality_map.get(q_qual, q_qual)
                lines.append(f"- [{qual_text}] {q_text}")
            else:
                lines.append(f"- {q}")
    else:
        lines.append("- （未填写）")

    # 原始反馈原文
    lines += [
        "",
        "---",
        "",
        f"*本文档由 AI 项目判断工作台自动生成 | {case.get('created_at', '')}*",
    ]

    return "\n".join(lines)


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("AI 项目判断工作台已启动")
    print("浏览器打开：http://localhost:5000")
    print("=" * 50)
    # SSE 流式需要禁用 reloader，避免子进程导致队列共享问题
    app.run(debug=DEBUG, host="127.0.0.1", port=5000, use_reloader=False, threaded=True)
