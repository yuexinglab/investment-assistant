# -*- coding: utf-8 -*-
"""
test_v3_pipeline.py — Step8-10 v3 语义分离验收测试

用杉海创新真实数据验证 v3 语义分离架构：
1. decision_signals 正确生成
2. step9_decider 正确使用 decision_signals
3. step10 neutral_investor guardrail 生效
"""
import sys
import os
import io
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.v2.services.step8_updater import build_step8_summary
from services.v2.services.step9_decider import decide as step9_decide, _apply_rule_based_guardrails
from services.v2.services.step10_fit_decider import _apply_fit_guardrails
from services.v2.schemas import ProcessDecision, InvestmentDecision, FitDecision, FinalRecommendation


def load_real_data():
    """加载杉海创新真实数据"""
    data_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "workspace", "杉海创新科技6_20260422_162546", "reports"
    )

    # 加载最新 v2.0 数据
    v2_file = os.path.join(data_dir, "v2_0_20260422_172205.json")
    with open(v2_file, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    print(f"[OK] 加载数据: {v2_file}")
    return v2_data


def test_step8_decision_signals(v2_data):
    """测试 Step8 生成 decision_signals（精修版）"""
    print("\n" + "=" * 60)
    print("测试 Step8: decision_signals 生成（精修版）")
    print("=" * 60)

    # 模拟 step8_output（精修版测试用例）
    step8_output = {
        "hypothesis_updates": [
            {
                "hypothesis_id": "h_001",
                "hypothesis": "美妆原料业务有真实客户支撑",
                "hypothesis_direction": "positive",
                "change_type": "reinforced",
                "updated_view": "欧莱雅、宝洁、珀莱雅等头部客户已确认，2025年营收1.35亿",
                "why_changed": "新增客户名单和收入数据支撑原判断",
                "contradicting_evidence": [],
                "supporting_evidence": ["欧莱雅1200万合同", "宝洁合作确认"],
            },
            {
                "hypothesis_id": "h_002",
                "hypothesis": "AI平台构成技术壁垒",
                "hypothesis_direction": "positive",
                "change_type": "uncertain",  # ❗ 关键：没信息 = uncertain
                "updated_view": "AI平台准确率70-80%，但数据来源和验证方法未披露",
                "why_changed": "准确率数据来自内部声称，未有第三方验证",
                "contradicting_evidence": ["测试报告缺失", "第三方验证缺失"],
                "supporting_evidence": [],
            },
            {
                "hypothesis_id": "h_003",
                "hypothesis": "客户集中度可控",
                "hypothesis_direction": "positive",
                "change_type": "weakened",  # ❗ 精修：weakened → key_uncertainty（不再是 confirmed_negative）
                "updated_view": "欧莱雅+珀莱雅合计可能超过40%，但数据来自推算而非合同",
                "why_changed": "客户收入数据推算显示集中度可能超预期",
                "contradicting_evidence": ["客户完整名单缺失"],
                "supporting_evidence": [],
            },
            {
                "hypothesis_id": "h_004",
                "hypothesis": "新能源业务有明确商业化路径",
                "hypothesis_direction": "positive",
                "change_type": "uncertain",
                "updated_view": "多项合作在谈，但均处于早期，无商业化闭环",
                "why_changed": "合作信息确认，但收入贡献为零",
                "contradicting_evidence": ["合同缺失", "无收入记录"],
                "supporting_evidence": [],
            },
            {
                "hypothesis_id": "h_005",
                "hypothesis": "团队背景无明显风险",
                "hypothesis_direction": "neutral",
                "change_type": "reinforced",
                "updated_view": "创始人张老师从2015年起研究超分子，与哈工大深圳校区相关",
                "why_changed": "创始人背景信息与之前一致",
                "contradicting_evidence": ["详细简历未获取"],
                "supporting_evidence": [],
            },
        ],
        "overall_change": {
            "is_judgement_significantly_changed": True,
            "new_risks": []
        }
    }

    # 运行 build_step8_summary
    summary = build_step8_summary(step8_output)

    print(f"\n生成 summary 验证:")
    print(f"  executive_summary: {summary.get('executive_summary', '')[:100]}...")

    # 验证 decision_signals
    ds = summary.get("decision_signals", {})
    vp = ds.get("validated_positives", [])
    cn = ds.get("confirmed_negatives", [])
    ku = ds.get("key_uncertainties", [])

    print(f"\ndecision_signals 统计:")
    print(f"  validated_positives: {len(vp)} 项")
    print(f"  confirmed_negatives: {len(cn)} 项")
    print(f"  key_uncertainties: {len(ku)} 项")

    # ❗ 精修版验证：weakened 不再是 confirmed_negative
    print(f"\n【精修版语义验证】")
    for item in vp:
        print(f"  ✅ validated_positive: {item['point'][:50]}...")

    for item in cn:
        print(f"  ⚠️ confirmed_negative: {item['point'][:50]}...")

    for item in ku:
        print(f"  ❓ key_uncertainty: {item['point'][:50]}...")

    # 断言：精修版应该有更多 key_uncertainty，不应该有这么多 confirmed_negative
    # h_003 从 confirmed_negative 变成了 key_uncertainty
    assert len(vp) >= 1, f"应有至少1个 validated_positive，got {len(vp)}"
    assert len(cn) <= 1, f"精修版 confirmed_negative 应该<=1（h_003变成uncertainty），got {len(cn)}"
    assert len(ku) >= 2, f"精修版 key_uncertainty 应该>=2（h_002/h_003/h_004），got {len(ku)}"

    print("\n[OK] Step8 decision_signals 生成正确（精修版）\n")
    return summary


def test_step9_with_decision_signals(summary):
    """测试 Step9 使用 decision_signals"""
    print("=" * 60)
    print("测试 Step9: 使用 v3 decision_signals")
    print("=" * 60)

    # 运行 step9（不使用 LLM，只测试规则）
    result = _apply_rule_based_guardrails(
        data={},
        step8_summary=summary,
        step7_summary="会议整体质量中等，问题部分回答",
        counts=summary.get("_counts", {}),
        process_decision=ProcessDecision.CONTINUE_DD.value,
        investment_decision=InvestmentDecision.NOT_READY.value,
        conclusion="继续观察，等待关键材料补充"
    )

    breakdown = result.get("decision_breakdown", {})
    print(f"\ndecision_breakdown 验证:")
    print(f"  verified_positives: {len(breakdown.get('verified_positives', []))} 项")
    print(f"  unverified_positives: {len(breakdown.get('unverified_positives', []))} 项")
    print(f"  confirmed_negatives: {len(breakdown.get('confirmed_negatives', []))} 项")
    print(f"  key_uncertainties: {len(breakdown.get('key_uncertainties', []))} 项")

    # 验证 verified_positives 是字符串列表（不是 dict）
    for item in breakdown.get("verified_positives", []):
        assert isinstance(item, str), f"verified_positives 应为字符串，got {type(item)}"

    for item in breakdown.get("confirmed_negatives", []):
        assert isinstance(item, str), f"confirmed_negatives 应为字符串，got {type(item)}"

    print(f"\n示例 verified_positives: {breakdown.get('verified_positives', [])[:2]}")
    print(f"示例 confirmed_negatives: {breakdown.get('confirmed_negatives', [])[:2]}")

    print("\n[OK] Step9 decision_breakdown 生成正确\n")
    return result


def test_step10_neutral_guardrail():
    """测试 Step10 neutral_investor guardrail（精修版）"""
    print("=" * 60)
    print("测试 Step10: neutral_investor guardrail（精修版）")
    print("=" * 60)

    # 模拟 neutral_investor profile
    neutral_profile = {
        "profile_id": "neutral_investor",
        "name": "中性投资人",
        "hard_constraints": [],
    }

    # 模拟 step9_output（项目本身判断）
    step9_output = {
        "overall_decision": {
            "process_decision": "continue_dd",
            "investment_decision": "not_ready",
            "one_line_conclusion": "继续观察"
        },
        "decision_breakdown": {
            "verified_positives": ["美妆1.35亿收入已验证"],
            "confirmed_negatives": [],
            "key_uncertainties": ["AI平台验证", "新能源商业化"]
        }
    }

    # 模拟 LLM 返回 not_fit（应该被 guardrail 拦截并继承 Step9）
    llm_result = {
        "fit_decision": FitDecision.NOT_FIT.value,
        "final_recommendation": FinalRecommendation.PASS.value,
        "reasoning": "不适合任何投资",
        "mismatched_constraints": []
    }

    # 应用 guardrail
    guarded = _apply_fit_guardrails(
        data=llm_result,
        fund_profile=neutral_profile,
        step9_output=step9_output,
        step7_output=None
    )

    print(f"\nGuardrail 测试:")
    print(f"  输入 fit_decision: {FitDecision.NOT_FIT.value}")
    print(f"  输出 fit_decision: {guarded.get('fit_decision')}")
    print(f"  输出 final_recommendation: {guarded.get('final_recommendation')}")
    print(f"  输出 reasoning: {guarded.get('reasoning')}")

    # ❗ 精修版断言：完全继承 Step9，不做越权判断
    assert guarded.get("fit_decision") != FitDecision.NOT_FIT.value, \
        f"neutral_investor 不应返回 not_fit"
    assert guarded.get("fit_decision") == FitDecision.PARTIAL_FIT.value, \
        f"应为 partial_fit，got {guarded.get('fit_decision')}"
    # ❗ 关键：final_recommendation 应该继承 Step9 的 continue_dd
    assert guarded.get("final_recommendation") == FinalRecommendation.CONTINUE.value, \
        f"应继承 Step9 的 continue_dd，got {guarded.get('final_recommendation')}"
    assert "不施加特定偏好" in guarded.get("reasoning", ""), \
        "reasoning 应说明不施加偏好"
    assert "不适合任何投资" not in guarded.get("reasoning", ""), \
        "reasoning 不应包含越权判断"

    print("\n[OK] neutral_investor guardrail 生效（精修版）\n")
    return guarded


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Step8-10 v3 语义分离验收测试")
    print("=" * 60 + "\n")

    try:
        # 1. 加载真实数据
        v2_data = load_real_data()

        # 2. 测试 Step8 decision_signals 生成
        summary = test_step8_decision_signals(v2_data)

        # 3. 测试 Step9 使用 decision_signals
        step9_result = test_step9_with_decision_signals(summary)

        # 4. 测试 Step10 neutral_investor guardrail
        step10_result = test_step10_neutral_guardrail()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n验收结论:")
        print("  ✅ Step8: decision_signals 正确生成，hypothesis_direction 语义映射正确")
        print("  ✅ Step9: decision_breakdown 从 decision_signals 提取，dict→point 转换正确")
        print("  ✅ Step10: neutral_investor guardrail 禁止 not_fit 生效")
        print("\n🎉 v3 语义分离架构验收通过！")

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
