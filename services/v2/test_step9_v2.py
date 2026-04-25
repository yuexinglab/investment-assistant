# -*- coding: utf-8 -*-
"""
test_step9_v2.py — Step9 v2 规则驱动测试

测试决策规则是否正确：
1. weakened_count >= 2 -> pass
2. weakened >= 1 AND uncertain >= 2 -> hold
3. uncertain >= 3 -> cautious_go
4. slightly_reinforced >= 2 -> go
5. else -> cautious_go
"""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根路径（investment-assistant/）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.v2.services.step9_decider import (
    _count_change_types, _rule_based_decision, _extract_risks_from_step8
)
from services.v2.schemas import DecisionType, ConfidenceLevel


def test_count_change_types():
    """测试 change_type 统计"""
    print("=" * 60)
    print("测试 _count_change_types")
    print("=" * 60)

    # 测试用例 1：全 reinforced
    step8_1 = {
        "hypothesis_updates": [
            {"change_type": "reinforced"},
            {"change_type": "reinforced"},
            {"change_type": "reinforced"},
        ]
    }
    counts_1 = _count_change_types(step8_1)
    print(f"用例1 (reinforced only): {counts_1}")
    assert counts_1["reinforced"] == 3
    print("[OK] 用例1通过\n")

    # 测试用例 2：混合
    step8_2 = {
        "hypothesis_updates": [
            {"change_type": "reinforced"},
            {"change_type": "uncertain"},
            {"change_type": "uncertain"},
            {"change_type": "slightly_weakened"},
        ]
    }
    counts_2 = _count_change_types(step8_2)
    print(f"用例2 (mixed): {counts_2}")
    assert counts_2["reinforced"] == 1
    assert counts_2["uncertain"] == 2
    assert counts_2["slightly_weakened"] == 1
    print("[OK] 用例2通过\n")

    # 测试用例 3：空列表
    step8_3 = {}
    counts_3 = _count_change_types(step8_3)
    print(f"用例3 (empty): {counts_3}")
    assert sum(counts_3.values()) == 0
    print("[OK] 用例3通过\n")


def test_rule_based_decision():
    """测试规则决策逻辑"""
    print("=" * 60)
    print("测试 _rule_based_decision")
    print("=" * 60)

    # 用例1：weakened_count >= 2 -> pass
    counts_1 = {
        "reinforced": 0, "slightly_reinforced": 0, "uncertain": 0,
        "slightly_weakened": 0, "weakened": 2, "overturned": 0, "reframed": 0
    }
    decision_1, confidence_1, conclusion_1 = _rule_based_decision(counts_1)
    print(f"用例1 (weakened>=2): decision={decision_1.value}, confidence={confidence_1.value}")
    assert decision_1 == DecisionType.PASS
    print("[OK] 用例1通过 (weakened>=2 -> pass)\n")

    # 用例2：weakened >= 1 AND uncertain >= 2 -> hold
    counts_2 = {
        "reinforced": 0, "slightly_reinforced": 0, "uncertain": 2,
        "slightly_weakened": 0, "weakened": 1, "overturned": 0, "reframed": 0
    }
    decision_2, confidence_2, conclusion_2 = _rule_based_decision(counts_2)
    print(f"用例2 (weakened>=1 AND uncertain>=2): decision={decision_2.value}")
    assert decision_2 == DecisionType.HOLD
    print("[OK] 用例2通过 (weakened>=1 AND uncertain>=2 -> hold)\n")

    # 用例3：uncertain >= 3 -> cautious_go
    counts_3 = {
        "reinforced": 0, "slightly_reinforced": 0, "uncertain": 3,
        "slightly_weakened": 0, "weakened": 0, "overturned": 0, "reframed": 0
    }
    decision_3, confidence_3, conclusion_3 = _rule_based_decision(counts_3)
    print(f"用例3 (uncertain>=3): decision={decision_3.value}")
    assert decision_3 == DecisionType.CAUTIOUS_GO
    print("[OK] 用例3通过 (uncertain>=3 -> cautious_go)\n")

    # 用例4：slightly_reinforced >= 2 -> go
    counts_4 = {
        "reinforced": 0, "slightly_reinforced": 2, "uncertain": 0,
        "slightly_weakened": 0, "weakened": 0, "overturned": 0, "reframed": 0
    }
    decision_4, confidence_4, conclusion_4 = _rule_based_decision(counts_4)
    print(f"用例4 (slightly_reinforced>=2): decision={decision_4.value}")
    assert decision_4 == DecisionType.GO
    print("[OK] 用例4通过 (slightly_reinforced>=2 -> go)\n")

    # 用例5：else -> cautious_go（reinforced >= 2 但 slightly_reinforced < 2）
    counts_5 = {
        "reinforced": 2, "slightly_reinforced": 0, "uncertain": 0,
        "slightly_weakened": 0, "weakened": 0, "overturned": 0, "reframed": 0
    }
    decision_5, confidence_5, conclusion_5 = _rule_based_decision(counts_5)
    print(f"用例5 (reinforced>=2 but no slightly_reinforced): decision={decision_5.value}")
    assert decision_5 == DecisionType.CAUTIOUS_GO
    print("[OK] 用例5通过 (reinforced>=2 but slightly_reinforced<2 -> cautious_go)\n")

    # 用例6：overturned 也算 weakened
    counts_6 = {
        "reinforced": 0, "slightly_reinforced": 0, "uncertain": 0,
        "slightly_weakened": 0, "weakened": 1, "overturned": 1, "reframed": 0
    }
    decision_6, confidence_6, conclusion_6 = _rule_based_decision(counts_6)
    print(f"用例6 (weakened=1 + overturned=1): decision={decision_6.value}")
    assert decision_6 == DecisionType.PASS  # 1 + 1 = 2 >= 2
    print("[OK] 用例6通过 (weakened + overturned >= 2 -> pass)\n")


def test_extract_risks():
    """测试风险提取"""
    print("=" * 60)
    print("测试 _extract_risks_from_step8")
    print("=" * 60)

    step8 = {
        "overall_change": {
            "new_risks": [
                {"risk": "客户粘性未验证", "severity": "high"},
                {"risk": "专利壁垒存疑", "severity": "medium"},
            ]
        },
        "hypothesis_updates": [
            {
                "change_type": "uncertain",
                "hypothesis": "AI平台可能构成壁垒",
                "updated_view": "证据主要来自claim，有效性未验证",
            },
            {
                "change_type": "weakened",
                "hypothesis": "新能源业务短期有收入",
                "updated_view": "预计时间表缺乏合同支撑",
            }
        ]
    }

    risks = _extract_risks_from_step8(step8)
    print(f"提取到的风险数量: {len(risks)}")
    for risk in risks:
        print(f"  - {risk[:50]}...")
    assert len(risks) >= 4  # 2个new_risks + 2个hypothesis_updates
    print("[OK] 测试通过\n")


def test_full_decision():
    """测试完整决策流程"""
    print("=" * 60)
    print("测试完整 Step9 决策流程")
    print("=" * 60)

    from services.v2.services.step9_decider import to_dict

    # 模拟 Step8 输出（杉海创新案例）
    step8_output = {
        "hypothesis_updates": [
            {
                "hypothesis_id": "h_001",
                "hypothesis": "AI平台可能构成壁垒",
                "change_type": "uncertain",
                "updated_view": "证据主要来自claim，有效性未验证",
                "why_changed": "只有公司口径，无外部验证",
            },
            {
                "hypothesis_id": "h_002",
                "hypothesis": "大客户（欧莱雅/宝洁）粘性高",
                "change_type": "uncertain",
                "updated_view": "客户粘性来源未被有效验证",
                "why_changed": "缺少合同和回款记录",
            },
            {
                "hypothesis_id": "h_003",
                "hypothesis": "新能源业务有明确收入时间表",
                "change_type": "slightly_weakened",
                "updated_view": "时间表缺乏合同支撑",
                "why_changed": "预计数字无订单验证",
            },
            {
                "hypothesis_id": "h_004",
                "hypothesis": "专利保护真正构成竞争壁垒",
                "change_type": "uncertain",
                "updated_view": "专利强度未得到有效验证",
                "why_changed": "缺少专利清单和权属证明",
            },
            {
                "hypothesis_id": "h_005",
                "hypothesis": "并购千沐的协同效应真实",
                "change_type": "reinforced",
                "updated_view": "美妆业务收入得到初步验证",
                "why_changed": "有数字支撑",
            },
        ],
        "overall_change": {
            "is_judgement_significantly_changed": True,
            "new_risks": [
                {"risk": "客户粘性未验证", "severity": "high"},
                {"risk": "新能源收入时间表缺乏合同", "severity": "medium"},
            ]
        }
    }

    # 运行 Step9（不使用 LLM，只测试规则）
    counts = _count_change_types(step8_output)
    print(f"Step8 change_type 统计: {counts}")

    decision, confidence, conclusion = _rule_based_decision(counts)
    print(f"\n决策结果:")
    print(f"  decision: {decision.value}")
    print(f"  confidence: {confidence.value}")
    print(f"  conclusion: {conclusion}")

    # 预期：uncertain=3 (h_001, h_002, h_004) -> cautious_go
    assert decision == DecisionType.CAUTIOUS_GO
    print("\n[OK] 预期正确：uncertain >= 3 -> cautious_go")

    # 测试 to_dict 输出
    from services.v2.schemas import Step9Output, OverallDecision, DecisionBreakdown
    step9_output = Step9Output(
        overall_decision=OverallDecision(
            decision=decision,
            confidence=confidence,
            one_line_conclusion=conclusion,
        ),
        decision_breakdown=DecisionBreakdown(),
        action_plan=[],
        key_risks=[],
        go_no_go_logic="",
    )
    result = to_dict(step9_output)

    print(f"\n输出结构验证:")
    assert "overall_decision" in result
    assert "decision_breakdown" in result
    assert "action_plan" in result
    assert result["overall_decision"]["decision"] == "cautious_go"
    print("[OK] 输出结构正确\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Step9 v2 规则驱动测试")
    print("=" * 60 + "\n")

    try:
        test_count_change_types()
        test_rule_based_decision()
        test_extract_risks()
        test_full_decision()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
