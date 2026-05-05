# -*- coding: utf-8 -*-
"""更新 step5_prompt.py 的【5. 必问问题】和【重要约束】部分"""

filepath = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\step5\step5_prompt.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换【5. 必问问题】部分
old_questions = (
    '【5. 必问问题（must_ask_questions）】:\n'
    '\n'
    '严格要求：\n'
    '- 必须来自 Step4 gaps（含 red_flag_question）\n'
    '- 不允许重新发明问题\n'
    '- 每个问题必须说明"验证目的"\n'
    '\n'
    '---'
)

new_questions = (
    '【5. 必问问题（must_ask_questions）】:\n'
    '\n'
    '严格要求：\n'
    '- 必须来自 Step4 gaps（含 red_flag_question）\n'
    '- 不允许重新发明问题\n'
    '- 每个问题必须说明"验证目的"\n'
    '\n'
    '如果 profile 中存在 fit_questions，must_ask_questions 必须优先覆盖其中最关键的 1-2 个问题：\n'
    '- 如果 Step4 gaps 已经包含类似问题，则合并，不重复\n'
    '- 如果 Step4 gaps 没有覆盖 profile 的硬约束问题，也允许从 profile.fit_questions 中补入\n'
    '- 每个问题的 purpose 要说明它验证的是"项目逻辑"还是"profile 匹配度"\n'
    '- 特别注意：这里允许 profile.fit_questions 补入 must_ask_questions，但不要生成泛泛问题\n'
    '\n'
    '---'
)

if old_questions in content:
    content = content.replace(old_questions, new_questions, 1)
    print('SUCCESS: 【5. 必问问题】已更新')
else:
    print('ERROR: 未找到【5. 必问问题】匹配字符串')
    idx = content.find('【5. 必问问题')
    if idx >= 0:
        print('附近内容:', repr(content[idx:idx+400]))

# 2. 在【重要约束】中增加新约束
old_constraints = (
    '6. reasons_to_meet 和 reasons_to_pass 必须和 Step3B 的核心矛盾强相关，不是罗列一般性优缺点\n'
    '"""'
)

new_constraints = (
    '6. reasons_to_meet 和 reasons_to_pass 必须和 Step3B 的核心矛盾强相关，不是罗列一般性优缺点\n'
    '7. 如果提供了非 neutral_investor 的 profile，输出必须能看出当前基金/投资人视角；不能只做通用项目判断。\n'
    '8. profile 相关内容必须落在现有字段中，不允许新增字段。\n'
    '9. 不要出现"基金匹配度"新字段，因为当前 schema 不支持。\n'
    '10. 如果 profile 的关键约束没有在 BP/Step4 中被验证，应在 reasons_to_pass 或 must_ask_questions 中体现。\n'
    '"""'
)

if old_constraints in content:
    content = content.replace(old_constraints, new_constraints, 1)
    print('SUCCESS: 【重要约束】已更新')
else:
    print('ERROR: 未找到【重要约束】匹配字符串')
    idx = content.find('【重要约束】')
    if idx >= 0:
        print('附近内容:', repr(content[idx:idx+600]))

# 写回文件
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('文件已更新:', filepath)
