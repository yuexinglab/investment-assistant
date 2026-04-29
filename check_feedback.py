# -*- coding: utf-8 -*-
import json, os

fb_file = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\knowledge_base\feedback\bp_review_feedback.jsonl'
if not os.path.exists(fb_file):
    print('文件不存在')
else:
    with open(fb_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f'共 {len(lines)} 条记录\n')
    for i, line in enumerate(lines):
        case = json.loads(line)
        print(f'--- 记录{i+1} ---')
        print(f'  feedback_id: {case.get("feedback_id")}')
        print(f'  project_id: {case.get("project_id")}')
        print(f'  review_status: {case.get("review_status")}')
        print(f'  top keys: {list(case.keys())}')
        print(f'  evaluation keys: {list(case.get("evaluation", {}).keys())}')
        core_diff = case.get("core_difference", {})
        print(f'  core_difference keys: {list(core_diff.keys())}')
        if core_diff:
            print(f'    ai_main_thesis: {core_diff.get("ai_main_thesis")}')
            print(f'    human_main_thesis: {core_diff.get("human_main_thesis")}')
            print(f'    one_sentence_learning: {core_diff.get("one_sentence_learning")}')
        print()
