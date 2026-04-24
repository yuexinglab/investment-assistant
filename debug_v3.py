"""快速测试 JSON 截断情况"""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_DIR = r"D:\复旦文件\Semester3-4\搞事情\论文产品化\投资助手"
PROJECT_DIR_FULL = os.path.join(PROJECT_DIR, "workspace", "杉海创新科技6_20260422_162546")

sys.path.insert(0, PROJECT_DIR)
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from services.deepseek_service import call_deepseek
from step4.step4_prompt import build_step4_prompt

with open(os.path.join(PROJECT_DIR_FULL, "step1_v2_new.txt"), encoding="utf-8") as f:
    step1 = f.read()
with open(os.path.join(PROJECT_DIR_FULL, "step3_v3_bucket.json"), encoding="utf-8") as f:
    step3 = f.read()
with open(os.path.join(PROJECT_DIR_FULL, "parsed", "bp_text.txt"), encoding="utf-8") as f:
    bp = f.read()

prompt = build_step4_prompt(step1, step3, bp)
raw = call_deepseek("你是一位资深投资人兼尽调提问教练。输出JSON+Markdown", prompt)

print("Total raw:", len(raw))

# 找 ```json 后的内容
import re
match = re.search(r'```json', raw, re.IGNORECASE)
if match:
    after = raw[match.end():]
    # 找第一个 {
    brace_idx = after.find('{')
    if brace_idx >= 0:
        json_text = after[brace_idx:]
        # 找最后一个完整的对象
        depth = 0
        last_end = 0
        in_str = False
        esc = False
        for i, c in enumerate(json_text):
            if esc:
                esc = False
                continue
            if c == '\\':
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == '{':
                if depth == 0:
                    last_end = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    last_end = i + 1
        print("JSON完整部分:", last_end, "chars, 剩余深度:", depth)

        # 尝试解析
        from step4.step4_parser import normalize_json_text
        test_json = normalize_json_text(json_text[:last_end])
        try:
            data = json.loads(test_json)
            print("JSON解析成功! gaps:", len(data.get("decision_gaps", [])))
        except Exception as e:
            print("JSON解析失败:", e)
            print("最后200字符:", repr(test_json[-200:]))
