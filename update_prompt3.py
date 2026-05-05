import os

filepath = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\step5\step5_prompt.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到【5. 必问问题】的行号
start = None
for i, line in enumerate(lines):
    if '【5. 必问问题' in line:
        start = i
        break

if start is None:
    print("ERROR: 未找到【5. 必问问题】")
    exit(1)

# 找到下一个【之间的结束位置（--- 分隔线）
end = None
for i in range(start+1, len(lines)):
    if lines[i].strip() == '---' and i > start + 5:
        end = i
        break

if end is None:
    print("ERROR: 未找到【5. 必问问题】的结束位置")
    exit(1)

print(f"找到【5. 必问问题】在第 {start} 到 {end} 行")
print("当前内容:")
print(''.join(lines[start:end+1]))

# 新内容
new_content = [
    '【5. 必问问题（must_ask_questions）】:\n',
    '\n',
    '严格要求：\n',
    '- 必须来自 Step4 gaps（含 red_flag_question）\n',
    '- 不允许重新发明问题\n',
    '- 每个问题必须说明"验证目的"\n',
    '\n',
    '如果 profile 中存在 fit_questions，must_ask_questions 必须优先覆盖其中最关键的 1-2 个问题：\n',
    '- 如果 Step4 gaps 已经包含类似问题，则合并，不重复\n',
    '- 如果 Step4 gaps 没有覆盖 profile的硬约束问题，也允许从 profile.fit_questions 中补入\n',
    '- 每个问题的 purpose 要说明它验证的是"项目逻辑"还是"profile 匹配度"\n',
    '- 特别注意：这里允许 profile.fit_questions 补入 must_ask_questions，但不要生成泛泛问题\n',
    '\n',
    '---\n'
]

# 替换
lines[start:end+1] = new_content

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\nSUCCESS: 【5. 必问问题】已更新")
