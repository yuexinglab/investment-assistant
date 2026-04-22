import os
from dotenv import load_dotenv

load_dotenv()

# ===== DeepSeek API 配置 =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# ===== 路径配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")   # 所有项目存储目录
UPLOAD_MAX_MB = 50                                      # 最大上传文件 MB

# ===== Flask 配置 =====
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# ===== 支持的文件类型 =====
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "md"}
