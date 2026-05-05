import os

filepath = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\step5\step5_prompt.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到【5. 必问问题】和【6. 投资逻辑归因】之间的内容
import re

# 使用正则匹配
pattern = r'(【5\. 必问问题（must_ask_questions）】:\n\n严格要求：\n- 必须来自 Step4 gaps（含 red_flag_question）\n- 不允许重新发明问题\n- 每个问题必须说明"验证目的"\n\n)---'

match = re.search(pattern, content)
if match:
    print("找到匹配！")
    print("匹配内容:", repr(match.group(1)[:100]))
else:
    print("未找到匹配，打印附近内容用于调试:")
    idx = content.find('【5. 必问问题')
    if idx >= 0:
        print(repr(content[idx:idx+500]))
    else:
        print("未找到【5. 必问问题")
