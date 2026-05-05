import re

with open(r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\step5\step5_prompt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换【5. 必问问题】部分
old = (
    "【5. 必问问题（must_ask_questions）】:\n"
    "\n"
    "严格要求：\n"
    "- 必须来自 Step4 gaps（含 red_flag_question）\n"
    "- 不允许重新发明问题\n"
    "- 每个问题必须说明\"验证目的\"\n"
    "\n"
    "---"
)

new = (
    "【5. 必问问题（must_ask_questions）】:\n"
    "\n"
    "严格要求：\n"
    "- 必须来自 Step4 gaps（含 red_flag_question）\n"
    "- 不允许重新发明问题\n"
    "- 每个问题必须说明\"验证目的\"\n"
    "\n"
    "如果 profile 中存在 fit_questions，must_ask_questions 必须优先覆盖其中最关键的 1-2 个问题：\n"
    "- 如果 Step4 gaps 已经包含类似问题，则合并，不重复\n"
    "- 如果 Step4 gaps 没有覆盖 profile 的硬约束问题，也允许从 profile.fit_questions 中补入\n"
    "- 每个问题的 purpose 要说明它验证的是\"项目逻辑\"还是\"profile 匹配度\"\n"
    "- 特别注意：这里允许 profile.fit_questions 补入 must_ask_questions，但不要生成泛泛问题\n"
    "\n"
    "---"
)

if old in content:
    content = content.replace(old, new, 1)
    with open(r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\step5\step5_prompt.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: 必问问题部分已更新')
else:
    print('ERROR: 未找到匹配字符串')
    # 打印附近内容用于调试
    idx = content.find('【5. 必问问题')
    if idx >= 0:
        print(repr(content[idx:idx+400]))
    else:
        print('未找到【5. 必问问题')
