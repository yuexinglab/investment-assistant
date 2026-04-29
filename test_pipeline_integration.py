# test_pipeline_integration.py
# Pipeline 集成测试 - 验证 Step3 + project_structure 完整流程

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step3.project_structure_detector import detect_project_structure
from step3.step3_prompt import build_step3_prompt


def test_step3_prompt_with_project_structure():
    """测试 Step3 prompt 正确包含 project_structure"""
    step1_text = "这是一个自动驾驶卡车项目，技术有一定壁垒，但商业化路径需要验证。"
    bp_text = """
    斯年智驾是一家专注于自动驾驶卡车商业化运营的公司。
    主要业务包括：1）自动驾驶软硬件设备销售；2）智能物流代运营服务；
    3）物流园区智能化项目实施。
    """
    project_structure = {
        "industry_tags": ["autonomous_driving", "logistics"],
        "business_lines": ["销售/商业化", "运营/服务"],
        "business_model_hypotheses": ["equipment_sales", "asset_heavy_operation"],
        "risk_buckets": ["heavy_asset_risk", "customer_concentration_risk"],
        "key_uncertainties": ["设备是否真的被采购", "现金流压力"],
    }
    
    prompt = build_step3_prompt(
        step1_text=step1_text,
        bp_text=bp_text,
        industry="general",
        selected_buckets=["tech_barrier", "commercialization", "customer_value"],
        project_structure=project_structure,
    )
    
    print("\n" + "="*60)
    print("Step3 Prompt 集成测试")
    print("="*60)
    
    # 检查 project_structure_text 是否出现在 prompt 中
    assert "项目结构识别结果（系统初判，仅作参考）" in prompt, \
        "prompt 中应该包含 project_structure 部分"
    assert "autonomous_driving" in prompt, \
        "prompt 中应该包含 industry_tags"
    assert "equipment_sales" in prompt, \
        "prompt 中应该包含 business_model_hypotheses"
    assert "heavy_asset_risk" in prompt, \
        "prompt 中应该包含 risk_buckets"
    
    print("[OK] Step3 prompt 正确包含 project_structure")
    print("\n[Preview] project_structure 部分片段:")
    start = prompt.find("项目结构识别结果")
    end = prompt.find("外部补充信息")
    if start != -1 and end != -1:
        print(prompt[start:end])
    
    return True


def test_detect_industry_fallback():
    """测试 detect_industry fallback 改为 general"""
    # 测试无法识别的文本
    from services.pipeline_v1 import detect_industry
    
    text = "这是一个通用项目，没有特殊行业关键词。"
    industry = detect_industry(text)
    
    print("\n" + "="*60)
    print("detect_industry fallback 测试")
    print("="*60)
    print(f"无法识别的文本返回行业: {industry}")
    
    assert industry == "general", f"fallback 应该返回 'general'，实际返回 '{industry}'"
    print("[OK] detect_industry fallback 测试通过!")
    return True


def test_industry_loader_general_fallback():
    """测试 industry_loader 对 general 的 fallback"""
    from step3.industry_loader import load_industry_enhancements
    
    print("\n" + "="*60)
    print("industry_loader general fallback 测试")
    print("="*60)
    
    # 测试空字符串
    result1 = load_industry_enhancements("")
    print(f"空字符串返回: {result1}")
    assert result1 == {}, "空字符串应该返回 {}"
    
    # 测试 "general"
    result2 = load_industry_enhancements("general")
    print(f"'general' 返回: {result2}")
    assert result2 == {}, "'general' 应该返回 {}"
    
    # 测试不存在的行业
    result3 = load_industry_enhancements("nonexistent_industry")
    print(f"不存在的行业返回: {result3}")
    assert result3 == {}, "不存在的行业应该返回 {}"
    
    print("[OK] industry_loader general fallback 测试通过!")
    return True


def test_full_project_structure_flow():
    """测试完整的 project_structure 检测流程"""
    texts = [
        # 斯年智驾
        """
        斯年智驾是一家专注于自动驾驶卡车商业化运营的公司。
        主要业务包括：1）自动驾驶软硬件设备销售；2）智能物流代运营服务；
        3）物流园区智能化项目实施。
        公司拥有完整的自动驾驶技术栈，包括感知、决策、执行全栈能力。
        已与多家头部物流企业建立合作关系，运营里程超过1000万公里。
        """,
        # 杉海创新
        """
        杉海创新是一家基于AI大模型和生物计算技术的新材料研发平台公司。
        公司主营业务包括：1）AI驱动的材料筛选平台服务；
        2）生物基日化原料的研发与销售；3）新能源材料的技术授权。
        """,
    ]
    
    print("\n" + "="*60)
    print("完整 project_structure 流程测试")
    print("="*60)
    
    for i, text in enumerate(texts, 1):
        result = detect_project_structure(text)
        print(f"\n项目 {i} 项目结构:")
        print(f"  行业标签: {result.industry_tags}")
        print(f"  业务线: {result.business_lines}")
        print(f"  商业模式: {result.business_model_hypotheses}")
        print(f"  风险桶: {result.risk_buckets}")
        
        # 验证输出格式
        d = result.to_dict()
        assert isinstance(d, dict), "to_dict() 应该返回 dict"
        assert "industry_tags" in d, "应该包含 industry_tags"
        assert "business_lines" in d, "应该包含 business_lines"
        assert "business_model_hypotheses" in d, "应该包含 business_model_hypotheses"
        assert "risk_buckets" in d, "应该包含 risk_buckets"
        assert "key_uncertainties" in d, "应该包含 key_uncertainties"
    
    print("\n[OK] 完整流程测试通过!")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Pipeline 集成测试")
    print("="*60)
    
    all_passed = True
    
    tests = [
        ("Step3 Prompt + project_structure", test_step3_prompt_with_project_structure),
        ("detect_industry fallback", test_detect_industry_fallback),
        ("industry_loader general fallback", test_industry_loader_general_fallback),
        ("完整 project_structure 流程", test_full_project_structure_flow),
    ]
    
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"\n[PASS] {name}")
        except AssertionError as e:
            print(f"\n[FAIL] {name}: {e}")
            all_passed = False
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] 所有集成测试通过!")
    else:
        print("[WARN] 部分测试失败")
    print("="*60)
