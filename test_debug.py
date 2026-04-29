# -*- coding: utf-8 -*-
"""Debug: 直接测试 step4_service"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant")

# 直接 import 和调用
from step4.step4_service import Step4Service

def fake_llm(system_prompt, user_prompt):
    print(f"[MOCK LLM调用] system长度={len(system_prompt)}, user长度={len(user_prompt)}")
    return '{"total_gaps":1,"internal_summary":"test","top_3_priorities":["t1"],"gaps":[{"gap_id":"g1","priority":"P1","core_issue":"test","from_bucket":"test","why_it_matters":"import","decision_impact":{"positive":"p","negative":"n"},"internal_goal":"g","go_if":"y","no_go_if":"n","main_path":{"opening":"o1","deepen_1":"d1","deepen_2":"d2","trap":"t","signals":{"good":["g"],"bad":["b"]}},"backup_path":{"opening":"o2","deepen_1":"d1","deepen_2":"d2","trap":"t","signals":{"good":["g"],"bad":["b"]}},"red_flag_question":"rfq"}]}'

service = Step4Service(call_llm=fake_llm)

# 构造最小 context_pack
context_pack = {
    "step1_core": "test co",
    "step3_key_unknowns": [],
    "step3_tensions": [],
    "decision_gap_candidates": [
        {"source": "step3b_tension", "issue": "gap1", "severity": "high"},
    ]
}

result = service.run(
    step1_text="test",
    step3_json='{"selected_buckets":[],"bucket_outputs":[],"step1_adjustment_hints":{}}',
    bp_text="test bp",
    step3b_json='{"summary":"test","consistency_checks":[],"tensions":[],"overpackaging_signals":[]}',
)

print(f"\nresult type: {type(result)}")
print(f"result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

if isinstance(result, dict):
    print(f"internal_json in result: {'internal_json' in result}")
    if "internal_json" in result:
        ij = result["internal_json"]
        print(f"internal_json type: {type(ij)}")
        print(f"internal_json is empty: {not ij}")
