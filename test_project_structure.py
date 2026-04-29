# test_project_structure.py
# 项目结构识别器测试

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step3.project_structure_detector import (
    detect_project_structure,
    detect_industry_tags,
    detect_business_models,
    detect_risk_buckets,
    detect_business_lines,
)


def test_sinian_driving():
    """测试斯年智驾 - 自动驾驶卡车"""
    text = """
    斯年智驾是一家专注于自动驾驶卡车商业化运营的公司。
    主要业务包括：1）自动驾驶软硬件设备销售；2）智能物流代运营服务；
    3）物流园区智能化项目实施。
    公司拥有完整的自动驾驶技术栈，包括感知、决策、执行全栈能力。
    已与多家头部物流企业建立合作关系，运营里程超过1000万公里。
    公司计划通过重资产运营模式扩大车队规模，预计明年车队数量突破500辆。
    主要客户包括顺丰、中通等头部快递企业，前五大客户收入占比超过60%。
    """
    
    result = detect_project_structure(text)
    
    print("\n" + "="*60)
    print("斯年智驾 - 项目结构识别结果")
    print("="*60)
    print(f"行业标签: {result.industry_tags}")
    print(f"业务线: {result.business_lines}")
    print(f"商业模式假设: {result.business_model_hypotheses}")
    print(f"风险桶: {result.risk_buckets}")
    print(f"关键不确定性:")
    for u in result.key_uncertainties:
        print(f"  - {u}")
    
    # 断言检查
    assert "autonomous_driving" in result.industry_tags, "应该有 autonomous_driving 标签"
    assert "logistics" in result.industry_tags, "应该有 logistics 标签"
    assert "equipment_sales" in result.business_model_hypotheses, "应该有 equipment_sales 模式"
    assert "asset_heavy_operation" in result.business_model_hypotheses, "应该有 asset_heavy_operation 模式"
    assert "heavy_asset_risk" in result.risk_buckets, "应该有 heavy_asset_risk"
    assert "customer_concentration_risk" in result.risk_buckets, "应该有 customer_concentration_risk"
    
    print("\n[OK] 斯年智驾测试通过!")
    return True


def test_shanhai_innovation():
    """测试杉海创新 - AI+新材料"""
    text = """
    杉海创新是一家基于AI大模型和生物计算技术的新材料研发平台公司。
    公司主营业务包括：1）AI驱动的材料筛选平台服务；
    2）生物基日化原料的研发与销售；3）新能源材料的技术授权。
    核心技术为自主研发的智能分子设计平台，已申请20余项核心专利。
    与多家国际美妆品牌建立战略合作，共同开发定制化原料解决方案。
    已完成千吨级生物基日化原料产线的建设，并开始向食品和医药领域扩张。
    公司研发投入占比超过40%，团队包括多名海归博士和行业资深专家。
    """
    
    result = detect_project_structure(text)
    
    print("\n" + "="*60)
    print("杉海创新 - 项目结构识别结果")
    print("="*60)
    print(f"行业标签: {result.industry_tags}")
    print(f"业务线: {result.business_lines}")
    print(f"商业模式假设: {result.business_model_hypotheses}")
    print(f"风险桶: {result.risk_buckets}")
    print(f"关键不确定性:")
    for u in result.key_uncertainties:
        print(f"  - {u}")
    
    # 断言检查
    assert "ai_platform" in result.industry_tags, "应该有 ai_platform 标签"
    assert "biotechnology" in result.industry_tags or "advanced_materials" in result.industry_tags, \
        "应该有 biotechnology 或 advanced_materials 标签"
    assert "tech_licensing" in result.business_model_hypotheses, "应该有 tech_licensing 模式"
    assert "研发/技术" in result.business_lines, "应该有研发/技术业务线"
    assert "制造/生产" in result.business_lines, "应该有制造/生产业务线"
    
    print("\n[OK] 杉海创新测试通过!")
    return True


def test_ai_platform_combo():
    """测试 AI研发平台 组合识别"""
    text = "这是一家AI研发平台公司，专注于大模型和算法的研发。"
    
    tags = detect_industry_tags(text)
    print("\n" + "="*60)
    print("AI研发平台组合识别测试")
    print("="*60)
    print(f"输入文本: {text}")
    print(f"识别结果: {tags}")
    
    assert "ai_platform" in tags, "应该识别出 AI研发平台"
    print("\n[OK] AI平台组合识别测试通过!")
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("开始运行项目结构识别测试")
    print("="*60)
    
    all_passed = True
    
    try:
        test_sinian_driving()
    except AssertionError as e:
        print(f"\n[X] 斯年智驾测试失败: {e}")
        all_passed = False
    
    try:
        test_shanhai_innovation()
    except AssertionError as e:
        print(f"\n[X] 杉海创新测试失败: {e}")
        all_passed = False
    
    try:
        test_ai_platform_combo()
    except AssertionError as e:
        print(f"\n[X] AI平台组合识别测试失败: {e}")
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[OK] 所有测试通过!")
    else:
        print("[WARN] 部分测试失败，请检查上述输出")
    print("="*60)
