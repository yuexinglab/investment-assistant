"""
AI 项目判断工作台 — Flask 主入口

路由总览（新）：
  GET  /                              → 首页（项目列表）
  GET  /project/new                   → 创建新项目页
  POST /project/create                → 创建项目 + 上传 BP
  GET  /project/<id>                  → 项目详情页

  ===== 1.0 新流程（主推）=====
  POST /project/<id>/run_pipeline     → 触发完整 Step1→3→4→5 流程（SSE 流式进度）
  POST /project/<id>/run_step/<step>  → 单步运行（step1/step3/step4/step5）
  GET  /project/<id>/result_new       → 查看新 1.0 结果页（5标签）
  GET  /project/<id>/download/<step>/<file> → 下载各步输出文件

  ===== 旧流程（保留兼容）=====
  POST /project/<id>/analyze          → 旧1.0 AB互检
  POST /project/<id>/analyze_v25      → 旧v2.5 9步流程
  GET  /project/<id>/result           → 查看旧1.0报告
  GET  /project/<id>/result25         → 查看旧v2.5报告
  POST /project/<id>/update           → 上传会议记录，触发 2.0 更新
  GET  /project/<id>/result2          → 查看2.0报告
  GET  /project/<id>/export[/<ver>]   → 导出旧版 Markdown
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, Response, stream_with_context
import os
import json
import threading
import queue
from config import WORKSPACE_DIR, SECRET_KEY, DEBUG, ALLOWED_EXTENSIONS

from services.file_parser import save_and_parse
from services.project_manager import (
    create_project, list_projects, get_project_meta,
    save_report, load_project_context
)
from services.report_generator import generate_v1, generate_v2, generate_v1_template
from services.pipeline_v1 import run_pipeline_v1, run_single_step, load_pipeline_results

app = Flask(__name__)
app.secret_key = SECRET_KEY

os.makedirs(WORKSPACE_DIR, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------- 首页：项目列表 ----------
@app.route("/")
def index():
    projects = list_projects()
    return render_template("index.html", projects=projects)


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

    # 创建项目目录
    project_dir = create_project(company_name)

    # 保存并解析 BP 文件
    save_and_parse(file, project_dir, source_type="bp")

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
    return render_template(
        "project_detail.html",
        meta=meta, context=context,
        v2_5_available=v2_5_available,
        project_id=project_id,
        results_available=results_available
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

        while True:
            try:
                item = progress_q.get(timeout=60)
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"
                continue

            step = item.get("step", "")
            status = item.get("status", "")

            # 步骤刚启动时，依次推送"思考流"句子
            if status == "running" and step != last_step:
                last_step = step
                for phrase in thinking_phrases.get(step, []):
                    time.sleep(0.4)
                    data = json.dumps({"type": "thinking", "step": step, "msg": phrase}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            data = json.dumps({"type": "progress", **item}, ensure_ascii=False)
            yield f"data: {data}\n\n"

            if status in ("done", "error") and step == "all":
                redirect_url = url_for("result_new", project_id=project_id)
                data = json.dumps({"type": "redirect", "url": redirect_url}, ensure_ascii=False)
                yield f"data: {data}\n\n"
                # 清空队列，释放资源
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

    return render_template(
        "result_1_0_new.html",
        meta=meta,
        project_id=project_id,
        results=pipeline_results
    )


# ---------- 分步下载 ----------
@app.route("/project/<project_id>/download/<step_name>/<file_name>")
def download_step_file(project_id, step_name, file_name):
    """下载各步骤输出文件"""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)

    # 安全校验
    allowed_downloads = {
        "step1": ["step1.txt"],
        "step3": ["step3.json"],
        "step4": ["step4_meeting_brief.md", "step4_internal.json", "step4_scan_questions.json"],
        "step5": ["step5_decision.md", "step5_output.json"],
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


if __name__ == "__main__":
    print("=" * 50)
    print("AI 项目判断工作台已启动")
    print("浏览器打开：http://localhost:5000")
    print("=" * 50)
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)
