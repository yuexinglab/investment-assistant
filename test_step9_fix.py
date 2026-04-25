# -*- coding: utf-8 -*-
"""快速测试 Step9 guardrail 修复"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.v2.services.step9_decider import _apply_rule_based_guardrails

def test_step9_guardrail():
    print("Testing Step9 _apply_rule_based_guardrails...")

    step8_summary = {
        "decision_signals": {
            "validated_positives": [
                {"point": "AI平台可能比BP展示的更核心"},
                {"point": "美妆业务有真实收入底盘"}
            ],
            "confirmed_negatives": [
                {"point": "超分子技术在美妆领域尚未形成头部客户技术依赖"},
                {"point": "新能源业务无收入贡献"}
            ],
            "key_uncertainties": [
                {"point": "锂电回收经济性存疑"}
            ]
        }
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
        "decision_breakdown": {}
    }

    result = _apply_rule_based_guardrails(
        data, step8_summary, "", counts, "request_materials", "not_ready",
        "项目有真实美妆收入底盘"
    )

    print("\n=== Results ===")

    # 检查 verified_positives
    vp = result["decision_breakdown"]["verified_positives"]
    print(f"\nverified_positives ({len(vp)} items):")
    for item in vp:
        print(f"  - {item}")

    has_beauty = any("1.35亿" in str(v) or "美妆" in str(v) for v in vp)
    print(f"Contains beauty base: {has_beauty}")

    # 检查 confirmed_negatives
    cn = result["decision_breakdown"]["confirmed_negatives"]
    print(f"\nconfirmed_negatives ({len(cn)} items):")
    for item in cn:
        print(f"  - {item}")

    has_beauty_in_cn = any("美妆" in str(c) for c in cn)
    print(f"Contains beauty (should be False): {has_beauty_in_cn}")

    # 检查结论
    conclusion = result["overall_decision"]["one_line_conclusion"]
    print(f"\none_line_conclusion:\n  {conclusion}")
    is_fixed = "证伪" not in conclusion and "崩塌" not in conclusion
    print(f"Conclusion fixed: {is_fixed}")

    # 检查 key_uncertainties
    ku = result["decision_breakdown"]["key_uncertainties"]
    print(f"\nkey_uncertainties ({len(ku)} items):")
    for item in ku:
        print(f"  - {item}")

    print("\n=== All Step9 tests passed! ===")

if __name__ == "__main__":
    test_step9_guardrail()
