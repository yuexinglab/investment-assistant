"""
file_parser.py — 文件解析
支持：PDF / TXT / DOCX
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename


def parse_pdf(path: str) -> str:
    import pdfplumber
    texts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t and t.strip():
                texts.append(t)
    return "\n\n".join(texts)


def parse_txt(path: str) -> str:
    for enc in ("utf-8", "gbk", "utf-8-sig"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def save_and_parse(file_obj, project_dir: str, source_type: str = "bp") -> str:
    """
    保存上传文件到 materials/，解析后存到 parsed/
    source_type: "bp" | "meeting"
    返回：解析后纯文本的文件路径
    """
    materials_dir = os.path.join(project_dir, "materials")
    parsed_dir = os.path.join(project_dir, "parsed")
    os.makedirs(materials_dir, exist_ok=True)
    os.makedirs(parsed_dir, exist_ok=True)

    # 保存原始文件
    filename = secure_filename(file_obj.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    ts = datetime.now().strftime("%H%M%S")
    save_name = f"{source_type}_{ts}.{ext}"
    raw_path = os.path.join(materials_dir, save_name)
    file_obj.save(raw_path)

    # 解析文本
    if ext == "pdf":
        text = parse_pdf(raw_path)
    elif ext == "docx":
        text = parse_docx(raw_path)
    else:
        text = parse_txt(raw_path)

    # 存为纯文本
    text_filename = f"{source_type}_text.txt"
    text_path = os.path.join(parsed_dir, text_filename)
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)

    return text_path


def parse_meeting_file(file_obj, project_dir: str, source_type: str = "meeting") -> str:
    """
    解析会议记录文件（txt / doc / docx），返回纯文本内容。
    保存到 v2_context/materials/
    """
    materials_dir = os.path.join(project_dir, "v2_context", "materials")
    os.makedirs(materials_dir, exist_ok=True)

    filename = secure_filename(file_obj.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    ts = datetime.now().strftime("%H%M%S")
    save_name = f"{source_type}_{ts}.{ext}"
    raw_path = os.path.join(materials_dir, save_name)
    file_obj.save(raw_path)

    # 解析
    if ext in ("docx",):
        text = parse_docx(raw_path)
    elif ext in ("pdf",):
        text = parse_pdf(raw_path)
    else:
        text = parse_txt(raw_path)

    return text
