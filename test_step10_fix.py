# -*- coding: utf-8 -*-
"""快速测试 Step10 guardrail 修复"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.v2.services.step10_fit_decider import _apply_fit_guardrails
from services.v2.schemas import FitDecision, FinalRecommendation

def test_step10_guardrail():
    print("Testing Step10 _apply_fit_guardrails for neutral_investor...")

    step9_output = {
        "overall_decision": {
            "process_decision": "request_materials",
            "investment_decision": "not_ready",
            "one_line_conclusion": "项目核心逻辑已被打穿：美妆和新能源两大业务线均被证伪"
        }
    }

    fund_profile = {
        "profile_id": "neutral_investor",
        "name": "中性投资人",
        "hard_constraints": [],
        "preferences": [],
        "avoid": []
    }

    # 模拟 LLM 生成的错误数据
    data = {
        "fit_decision": "not_fit",
        "final_recommendation": "pass",
        "candidate_case_record": {
            "project_name": "杉海创新科技测试",
            "project_judgement": "项目核心逻辑已被打穿：美妆和新能源两大业务线均被证伪，建议暂停跟进并拒绝投资",
            "fit_judgement": "not_fit",
            "final_decision": "pass",
            "fit_reason": ["美妆业务被证伪", "新能源被证伪"]
        }
    }

    result = _apply_fit_guardrails(data, fund_profile, step9_output)

    print("\n=== Results ===")
    print(f"fit_decision: {data.get('fit_decision')} -> {result.get('fit_decision')}")
    print(f"final_recommendation: {data.get('final_recommendation')} -> {result.get('final_recommendation')}")

    ccr = result.get("candidate_case_record", {})
    print(f"\ncandidate_case_record:")
    print(f"  fit_judgement: {ccr.get('fit_judgement')}")
    print(f"  final_decision: {ccr.get('final_decision')}")
    print(f"  fit_reason: {ccr.get('fit_reason')}")
    print(f"  project_judgement: {ccr.get('project_judgement', '')[:60]}...")

    # 验证
    fit_ok = result.get("fit_decision") == FitDecision.PARTIAL_FIT.value
    rec_ok = result.get("final_recommendation") != "pass"
    ccr_fit_ok = ccr.get("fit_judgement") == FitDecision.PARTIAL_FIT.value
    ccr_rec_ok = ccr.get("final_decision") != "pass"

    print(f"\n=== Validation ===")
    print(f"fit_decision fixed to partial_fit: {fit_ok}")
    print(f"final_recommendation not pass: {rec_ok}")
    print(f"ccr fit_judgement fixed: {ccr_fit_ok}")
    print(f"ccr final_decision fixed: {ccr_rec_ok}")

    all_pass = fit_ok and rec_ok and ccr_fit_ok and ccr_rec_ok
    print(f"\n{'=== All Step10 tests passed! ===' if all_pass else '!!! Some tests failed !!!'}")
    return all_pass

if __name__ == "__main__":
    test_step10_guardrail()
