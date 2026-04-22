"""
deepseek_service.py — DeepSeek API 调用封装
"""

import requests
import time
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def call_deepseek(system_prompt: str, user_prompt: str,
                  model: str = None, max_retries: int = 3) -> str:
    """
    调用 DeepSeek 对话 API
    返回：AI 回复的文本字符串
    """
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your_api_key_here":
        raise ValueError("请先在 .env 文件中配置 DEEPSEEK_API_KEY")

    model = model or DEEPSEEK_MODEL
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            last_error = "请求超时"
            time.sleep(2 * attempt)
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP 错误: {e.response.status_code} - {e.response.text}"
            if e.response.status_code in (400, 401, 403):
                break   # 不可重试的错误
            time.sleep(2 * attempt)
        except Exception as e:
            last_error = str(e)
            time.sleep(2 * attempt)

    raise RuntimeError(f"DeepSeek API 调用失败（重试 {max_retries} 次）：{last_error}")
