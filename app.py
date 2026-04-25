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
import sys, io, msvcrt, os
# Windows 控制台 UTF-8 编码支持
if sys.platform == "win32":
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    # 重定向 stdout/stderr 为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response, stream_with_context
import os
import json
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

    return render_template(
        "project_detail.html",
        meta=meta, context=context,
        v2_5_available=v2_5_available,
        project_id=project_id,
        results_available=results_available,
        project_profile=project_profile,
        profile_summary=profile_summary
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

    return render_template(
        "result_1_0_new.html",
        meta=meta,
        project_id=project_id,
        results=pipeline_results,
        project_profile=project_profile
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
# 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("AI 项目判断工作台已启动")
    print("浏览器打开：http://localhost:5000")
    print("=" * 50)
    # SSE 流式需要禁用 reloader，避免子进程导致队列共享问题
    app.run(debug=DEBUG, host="127.0.0.1", port=5000, use_reloader=False, threaded=True)
