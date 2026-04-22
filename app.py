"""
AI 项目判断工作台 — Flask 主入口
路由总览：
  GET  /                  → 首页（项目列表）
  GET  /project/new       → 创建新项目页
  POST /project/create    → 创建项目 + 上传 BP
  GET  /project/<id>      → 项目详情页
  POST /project/<id>/analyze   → 触发初判 1.0
  GET  /project/<id>/result    → 查看 1.0 报告
  POST /project/<id>/update    → 上传会议记录，触发 2.0 更新
  GET  /project/<id>/result2   → 查看 2.0 更新报告
  GET  /project/<id>/export    → 导出 Markdown 报告
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os
from config import WORKSPACE_DIR, SECRET_KEY, DEBUG, ALLOWED_EXTENSIONS

from services.file_parser import save_and_parse
from services.project_manager import (
    create_project, list_projects, get_project_meta,
    save_report, load_project_context
)
from services.report_generator import generate_v1, generate_v2

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
    return render_template("project_detail.html", meta=meta, context=context, project_id=project_id)


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

    # 加载 1.0 报告上下文
    context = load_project_context(project_dir)
    v1_report = context.get("latest_v1_report")
    if not v1_report:
        return jsonify({"error": "请先生成初判 1.0 报告"}), 400

    # 调用 D+E+C 三角色生成 2.0 更新报告
    report_v2 = generate_v2(v1_report, meeting_text)

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
def export_report(project_id):
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    context = load_project_context(project_dir)

    # 优先导出最新版本
    report = context.get("latest_v2_report") or context.get("latest_v1_report")
    if not report:
        return "暂无可导出的报告", 404

    meta = get_project_meta(project_dir)
    version = "2.0" if context.get("latest_v2_report") else "1.0"

    # 生成 Markdown 内容
    from services.report_generator import report_to_markdown
    md_content = report_to_markdown(report, meta, version)

    export_path = os.path.join(project_dir, f"{meta['company_name']}_判断报告_v{version}.md")
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return send_file(export_path, as_attachment=True)


if __name__ == "__main__":
    print("=" * 50)
    print("AI 项目判断工作台已启动")
    print("浏览器打开：http://localhost:5000")
    print("=" * 50)
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)
