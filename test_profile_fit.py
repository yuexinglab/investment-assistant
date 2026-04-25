# -*- coding: utf-8 -*-
"""
test_profile_fit.py - 验证不同 Profile 对同一项目给出不同 Fit 判断

测试场景：
- 杉海项目（有真实美妆收入，但拒绝本地落地和反投）
- government_fund: 应该输出 not_fit / pass
- neutral_investor: 不应因为反投/落地问题直接 pass
"""

import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 UTF-8 输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from services.profile import load_profile, list_fund_profiles
from services.v2.services.step10_fit_decider import decide_fit


def create_mock_step9_output():
    """创建模拟的 Step9 输出"""
    return {
        "overall_decision": {
            "process_decision": "request_materials",
            "investment_decision": "not_ready",
            "confidence": "medium",
            "one_line_conclusion": "项目有真实美妆收入底盘，但AI能力验证存疑，需进一步核实"
        },
        "decision_breakdown": {
            "verified_positives": [
                "有真实的美妆ODM/OEM收入",
                "有明确的客户（国际美妆品牌）",
                "新能源材料项目有技术积累"
            ],
            "unverified_positives": [
                "AI美妆工具的真实需求和付费意愿",
                "客户粘性和复购率",
                "专利商业化价值"
            ],
            "confirmed_negatives": [
                "项目方明确拒绝本地落地和反投",
                "AI工具在美妆行业的应用深度有限"
            ],
            "key_uncertainties": [
                "新能源材料能否规模化落地",
                "客户是否会为AI工具付费",
                "技术壁垒是否足够"
            ]
        }
    }


def test_government_fund():
    """测试 government_fund 画像"""
    print("\n" + "=" * 60)
    print("Test 1: Government Fund Profile")
    print("=" * 60)

    profile = load_profile("government_fund")
    print(f"\nProfile Name: {profile['name']}")
    print(f"Hard Constraints: {len(profile['hard_constraints'])}")
    for hc in profile['hard_constraints']:
        print(f"  - [{hc['priority']}] {hc['description'][:40]}...")

    step9_output = create_mock_step9_output()
    project_summary = {
        "project_id": "test_shanhai",
        "project_name": "Shanhai Innovation"
    }

    result = decide_fit(
        fund_profile=profile,
        step9_output=step9_output,
        project_summary=project_summary,
        model="deepseek-chat"
    )

    print(f"\n[Fit Decision Result]")
    print(f"  fit_decision: {result.get('fit_decision')}")
    print(f"  final_recommendation: {result.get('final_recommendation')}")
    print(f"  fit_score: {result.get('fit_score')}")
    print(f"  reasoning: {result.get('reasoning', '')[:100]}...")

    # 验证
    assert result.get('fit_decision') == 'not_fit', f"Expected not_fit, got {result.get('fit_decision')}"
    assert result.get('final_recommendation') == 'pass', f"Expected pass, got {result.get('final_recommendation')}"
    print("\n[PASS] Government Fund Test: Project clearly not fit")


def test_neutral_investor():
    """测试 neutral_investor 画像"""
    print("\n" + "=" * 60)
    print("Test 2: Neutral Investor Profile")
    print("=" * 60)

    profile = load_profile("neutral_investor")
    print(f"\nProfile Name: {profile['name']}")
    print(f"Hard Constraints: {len(profile['hard_constraints'])}")
    print(f"Preferences: {len(profile['preferences'])}")

    step9_output = create_mock_step9_output()
    project_summary = {
        "project_id": "test_shanhai",
        "project_name": "Shanhai Innovation"
    }

    result = decide_fit(
        fund_profile=profile,
        step9_output=step9_output,
        project_summary=project_summary,
        model="deepseek-chat"
    )

    print(f"\n[Fit Decision Result]")
    print(f"  fit_decision: {result.get('fit_decision')}")
    print(f"  final_recommendation: {result.get('final_recommendation')}")
    print(f"  fit_score: {result.get('fit_score')}")
    print(f"  reasoning: {result.get('reasoning', '')[:100]}...")

    # 验证：neutral_investor 不应该因为落地问题直接 pass
    # 它应该基于项目本身质量判断
    assert result.get('fit_decision') != 'not_fit' or result.get('final_recommendation') != 'pass', \
        f"neutral_investor should not pass just because of landing issues"
    print("\n[PASS] Neutral Investor Test: Not rejected due to landing issues")


def test_list_profiles():
    """测试列出所有 profiles"""
    print("\n" + "=" * 60)
    print("Test 3: List All Profiles")
    print("=" * 60)

    profiles = list_fund_profiles()
    print(f"\nAvailable Profiles: {len(profiles)}")

    for p in profiles:
        is_default = " [DEFAULT]" if p.get('is_default') else ""
        print(f"  - {p['profile_id']}: {p['name']}{is_default}")
        print(f"    {p['description'][:50]}...")

    # 验证 neutral_investor 在列表中
    profile_ids = [p['profile_id'] for p in profiles]
    assert 'neutral_investor' in profile_ids, "neutral_investor should be in list"
    assert 'government_fund' in profile_ids, "government_fund should be in list"
    assert 'vc_fund' in profile_ids, "vc_fund should be in list"
    assert 'industrial_fund' in profile_ids, "industrial_fund should be in list"

    # 验证 neutral_investor 是默认的
    neutral = next((p for p in profiles if p['profile_id'] == 'neutral_investor'), None)
    assert neutral and neutral.get('is_default'), "neutral_investor should be default"

    print("\n[PASS] List Profiles Test")


def test_default_is_neutral():
    """测试默认 profile 是 neutral_investor"""
    print("\n" + "=" * 60)
    print("Test 4: Verify Default Profile is neutral_investor")
    print("=" * 60)

    # 不传 profile_id，应该返回 neutral_investor
    profile = load_profile(None)
    print(f"\nWhen profile_id is None: {profile['profile_id']} - {profile['name']}")

    assert profile['profile_id'] == 'neutral_investor', \
        f"Default profile should be neutral_investor, got {profile['profile_id']}"

    # 传空字符串
    profile = load_profile("")
    print(f"When profile_id is empty: {profile['profile_id']} - {profile['name']}")
    assert profile['profile_id'] == 'neutral_investor'

    print("\n[PASS] Default Profile Test")


def main():
    print("\n" + "=" * 60)
    print("Profile / Step0 Integration Test")
    print("=" * 60)

    # 测试列出 profiles
    test_list_profiles()

    # 测试默认 profile
    test_default_is_neutral()

    # 测试 government_fund
    try:
        test_government_fund()
    except Exception as e:
        print(f"\n[FAIL] Government Fund Test: {e}")

    # 测试 neutral_investor
    try:
        test_neutral_investor()
    except Exception as e:
        print(f"\n[FAIL] Neutral Investor Test: {e}")

    print("\n" + "=" * 60)
    print("All Tests Completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
