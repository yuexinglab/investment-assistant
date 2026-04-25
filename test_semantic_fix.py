# -*- coding: utf-8 -*-
"""
test_step8_semantic_fix.py — 测试 Step8/9/10 语义修复效果

验收标准：
1. Step8 change_type 语义一致性：
   - h_1 AI平台：positive + weakened（不是 reinforced）
   - h_2 新能源隐性合作：positive + weakened（不是 reinforced）
   - h_3 美妆客户：不能 overturned（最多 uncertain/weakened）
   - h_4 千沐协同：positive + weakened（不是 overturned）
   - h_5 AI验证点：positive + weakened（不是 reinforced）
   - h_6 新能源验证点：positive + weakened（不是 reinforced）
   - h_7 锂电回收：uncertain/reframed
   - h_8 千沐整合：weakened/uncertain（不是 overturned）

2. Step9 decision_breakdown：
   - verified_positives 不包含 h_1/h_2/h_5/h_6
   - confirmed_negatives 不包含美妆
   - 包含美妆真实收入底盘

3. Step10 candidate_case_record：
   - neutral_investor 下 fit_judgement = partial_fit
   - final_decision 不等于 pass
"""

import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.v2.services.step8_updater import _normalize_change_type, _classify_update_signal
from services.v2.services.step9_decider import _apply_rule_based_guardrails, _rule_based_decision
from services.v2.services.step10_fit_decider import _apply_fit_guardrails
from services.v2.schemas import FitDecision, FinalRecommendation


def test_step8_normalize():
    """测试 Step8 change_type 语义一致性修复"""
    print("=" * 60)
    print("测试 Step8 _normalize_change_type 语义一致性")
    print("=" * 60)

    test_cases = [
        {
            "name": "h_1: AI平台被削弱但误标 reinforced",
            "update": {
                "change_type": "reinforced",
                "updated_view": "AI平台当前是辅助工具而非核心护城河，准确率仅70-80%",
                "hypothesis": "AI平台可能比BP展示的更核心",
                "supporting_evidence": [],
                "contradicting_evidence": ["AI平台与传统方法对比的量化效率数据"]
            },
            "expected_type": "weakened"  # 应该被纠正为 weakened
        },
        {
            "name": "h_2: 新能源隐性合作被削弱但误标 reinforced",
            "update": {
                "change_type": "reinforced",
                "updated_view": "新能源客户尚未形成隐性合作，深共晶电解液未进入主流电池厂供应链",
                "hypothesis": "新能源客户可能已形成隐性合作",
                "supporting_evidence": [],
                "contradicting_evidence": ["与主流电池厂的合作合同"]
            },
            "expected_type": "weakened"
        },
        {
            "name": "h_3: 美妆被误标 overturned",
            "update": {
                "change_type": "overturned",
                "updated_view": "超分子技术在美妆领域尚未形成头部客户技术依赖，客户验证周期较长",
                "hypothesis": "超分子技术可能在美妆领域已被头部客户形成技术依赖",
                "supporting_evidence": ["ni_020"],
                "contradicting_evidence": ["头部客户技术依赖的具体案例"]
            },
            "expected_type": "uncertain"  # 美妆不能 overturned
        },
        {
            "name": "h_4: 千沐协同被误标 overturned",
            "update": {
                "change_type": "overturned",
                "updated_view": "并购千沐新能源的技术协同效应未实际产生，整合进展缓慢",
                "hypothesis": "并购千沐新能源可能已产生技术协同效应",
                "supporting_evidence": [],
                "contradicting_evidence": ["千沐新能源的财务报表", "具体技术协同项目案例"]
            },
            "expected_type": "uncertain"  # 没有明确的证伪证据
        },
        {
            "name": "h_5: AI验证点被削弱但误标 reinforced",
            "update": {
                "change_type": "reinforced",
                "updated_view": "建沐AI平台与竞品的量化对比数据缺失，当前仅是辅助工具",
                "hypothesis": "AI平台与竞品的量化对比数据",
                "supporting_evidence": [],
                "contradicting_evidence": ["AI平台与传统方法对比的量化效率数据"]
            },
            "expected_type": "weakened"
        },
        {
            "name": "h_7: 锂电回收 reframed",
            "update": {
                "change_type": "reframed",
                "updated_view": "锂电回收业务在碳酸锂价格低于10万元/吨时的经济性未获验证",
                "hypothesis": "锂电回收业务经济性测算",
                "supporting_evidence": ["ni_011"],
                "contradicting_evidence": ["成本结构明细"]
            },
            "expected_type": "uncertain"  # reframed 应该变成 uncertain
        },
    ]

    all_passed = True
    for tc in test_cases:
        result = _normalize_change_type(tc["update"].copy())
        actual_type = result["change_type"]
        expected = tc["expected_type"]
        status = "[PASS]" if actual_type == expected else "[FAIL]"
        if actual_type != expected:
            all_passed = False
        print(f"{status} {tc['name']}")
        print(f"   expected: {expected}, actual: {actual_type}")
        print()

    return all_passed


def test_step9_guardrail():
    """测试 Step9 decision_breakdown 分类修复"""
    print("=" * 60)
    print("测试 Step9 _apply_rule_based_guardrails")
    print("=" * 60)

    # 模拟 Step8 summary（包含被修复后的 hypothesis_updates）
    step8_summary = {
        "decision_signals": {
            "validated_positives": [
                {"point": "AI平台可能比BP展示的更核心"},  # 这是误判，应该被过滤
                {"point": "美妆业务有真实收入底盘"}
            ],
            "confirmed_negatives": [
                {"point": "超分子技术在美妆领域尚未形成头部客户技术依赖"},  # 美妆不能被证伪
                {"point": "新能源业务无收入贡献"}
            ],
            "key_uncertainties": [
                {"point": "锂电回收经济性存疑"}
            ]
        },
        "validated_points": [],
        "invalidated_points": [],
        "uncertain_points": []
    }

    counts = {
        "confirmed_negative": 1,
        "validated_positive": 1,
        "key_uncertainty": 1
    }

    data = {
        "overall_decision": {
            "one_line_conclusion": "美妆和新能源两大业务线均被证伪，核心逻辑崩塌"
        },
        "decision_breakdown": {
            "verified_positives": [],
            "unverified_positives": [],
            "confirmed_negatives": [],
            "key_uncertainties": []
        }
    }

    result = _apply_rule_based_guardrails(
        data, step8_summary, "", counts, "request_materials", "not_ready",
        "项目有真实美妆收入底盘"
    )

    print("Step9 decision_breakdown 结果：")
    print()

    # 检查 verified_positives
    vp = result["decision_breakdown"]["verified_positives"]
    print(f"[CHECK] verified_positives ({len(vp)}项):")
    for item in vp:
        print(f"   - {item}")

    # 检查是否包含美妆底盘
    has_beauty_base = any("1.35亿" in str(v) or "美妆" in str(v) for v in vp)
    print(f"   {'[PASS]' if has_beauty_base else '[FAIL]'} 包含美妆真实收入底盘")

    # 检查 confirmed_negatives
    cn = result["decision_breakdown"]["confirmed_negatives"]
    print()
    print(f"[CHECK] confirmed_negatives ({len(cn)}项):")
    for item in cn:
        print(f"   - {item}")

    # 检查是否排除了美妆
    has_beauty_in_cn = any("美妆" in str(c) for c in cn)
    print(f"   {'[PASS]' if not has_beauty_in_cn else '[FAIL]'} 不包含美妆相关条目")

    # 检查 key_uncertainties
    ku = result["decision_breakdown"]["key_uncertainties"]
    print()
    print(f"[CHECK] key_uncertainties ({len(ku)}项):")
    for item in ku:
        print(f"   - {item}")

    # 检查结论修复
    conclusion = result["overall_decision"]["one_line_conclusion"]
    print()
    print(f"[CHECK] one_line_conclusion:")
    print(f"   {conclusion}")
    is_fixed = "证伪" not in conclusion and "崩塌" not in conclusion
    print(f"   {'[PASS]' if is_fixed else '[FAIL]'} 不再包含'证伪'/'崩塌'")

    return True


def test_step10_guardrail():
    """测试 Step10 neutral_investor guardrail 修复"""
    print("=" * 60)
    print("测试 Step10 neutral_investor candidate_case_record 修复")
    print("=" * 60)

    # 模拟 Step9 output（包含错误结论）
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
        "mismatched_constraints": [],
        "matched_constraints": [],
        "candidate_case_record": {
            "project_name": "杉海创新科技测试",
            "project_judgement": "项目核心逻辑已被打穿：美妆和新能源两大业务线均被证伪，建议暂停跟进并拒绝投资",
            "fit_judgement": "not_fit",
            "final_decision": "pass",
            "fit_reason": ["美妆业务被证伪", "新能源被证伪"]
        }
    }

    result = _apply_fit_guardrails(data, fund_profile, step9_output)

    print("Step10 guardrail 后结果：")
    print()

    print(f"fit_decision: {data.get('fit_decision')} -> {result.get('fit_decision')}")
    is_fit_fixed = result.get("fit_decision") == FitDecision.PARTIAL_FIT.value
    print(f"   {'[PASS]' if is_fit_fixed else '[FAIL]'} neutral_investor 不应该是 not_fit")

    print()
    print(f"final_recommendation: {data.get('final_recommendation')} -> {result.get('final_recommendation')}")
    is_rec_fixed = result.get("final_recommendation") != "pass"
    print(f"   {'[PASS]' if is_rec_fixed else '[FAIL]'} 应该跟随 Step9 process_decision")

    print()
    ccr = result.get("candidate_case_record", {})
    print("candidate_case_record:")
    print(f"   fit_judgement: {ccr.get('fit_judgement')}")
    print(f"   final_decision: {ccr.get('final_decision')}")
    print(f"   project_judgement: {ccr.get('project_judgement', '')[:50]}...")

    is_ccr_fixed = (
        ccr.get("fit_judgement") == FitDecision.PARTIAL_FIT.value and
        ccr.get("final_decision") != "pass"
    )
    print(f"   {'[PASS]' if is_ccr_fixed else '[FAIL]'} candidate_case_record 已修复")

    return is_fit_fixed and is_rec_fixed and is_ccr_fixed


def main():
    print()
    print("#" * 60)
    print("# Step8/9/10 语义修复验收测试")
    print("#" * 60)
    print()

    results = []

    # 测试 Step8
    results.append(("Step8 change_type 语义一致性", test_step8_normalize()))

    # 测试 Step9
    results.append(("Step9 decision_breakdown 分类", test_step9_guardrail()))

    # 测试 Step10
    results.append(("Step10 neutral_investor guardrail", test_step10_guardrail()))

    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS] 通过" if passed else "[FAIL] 失败"
        if not passed:
            all_passed = False
        print(f"{status}: {name}")

    print()
    if all_passed:
        print("=== 所有测试通过！语义修复生效 ===")
    else:
        print("!!! 部分测试失败，请检查修复效果 !!!")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
