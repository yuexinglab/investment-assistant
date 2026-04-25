#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 Step8 - 检查卡住的原因
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json

# 加载测试数据
step6_path = r"C:\Users\86136\Downloads\step6_latest (4).json"
step7_path = r"C:\Users\86136\Downloads\step7_latest (4).json"
step8_path = r"C:\Users\86136\Downloads\step8_latest (6).json"

with open(step6_path, "r", encoding="utf-8") as f:
    step6 = json.load(f)

with open(step7_path, "r", encoding="utf-8") as f:
    step7 = json.load(f)

print("="*50)
print("Step8 调试...")
print("="*50)

print(f"\nStep6 new_information 数量: {len(step6.get('new_information', []))}")
print(f"Step7 question_validation 数量: {len(step7.get('question_validation', []))}")

# 检查 step7 数据
print(f"\nStep7 数据检查:")
print(f"  - meeting_quality: {list(step7.get('meeting_quality', {}).keys())}")
print(f"  - question_validation 类型: {type(step7.get('question_validation'))}")
print(f"  - question_validation[0] 样例: {step7.get('question_validation', [{}])[0] if step7.get('question_validation') else 'EMPTY'}")

# 模拟 step5_judgements
step5_judgements = [
    {"hypothesis": "美妆业务是当前最扎实的收入底盘", "view": "欧莱雅、宝洁等大客户验证"},
    {"hypothesis": "AI平台构成核心技术壁垒", "view": "准确率70-80%，正在优化"},
    {"hypothesis": "食品业务放量时间表可信", "view": "韶关工厂改造中"},
    {"hypothesis": "新能源业务有明确的收入时间表", "view": "预计2026年5月方案落地"},
    {"hypothesis": "并购千沐的协同效应真实", "view": "研发中台共享"},
]

print(f"\n模拟 step5_judgements: {len(step5_judgements)} 条")

# 构造 step7_result（包含 _step6_new_information）
step7_result = dict(step7)
step7_result["_step6_new_information"] = step6.get("new_information", [])

print(f"\nstep7_result keys: {list(step7_result.keys())}")

# 测试 Step8
print("\n" + "="*50)
print("开始测试 Step8...")
print("="*50)

try:
    from services.v2.services.step8_updater import update, compute_hypothesis_updates
    
    print("\nStep 1: 测试 compute_hypothesis_updates...")
    hypothesis_updates, new_risks, unchanged = compute_hypothesis_updates(
        step5_judgements=step5_judgements,
        step7_validations=step7.get("question_validation", []),
        step7_result=step7_result
    )
    print(f"  hypothesis_updates 数量: {len(hypothesis_updates)}")
    print(f"  new_risks 数量: {len(new_risks)}")
    print(f"  unchanged 数量: {len(unchanged)}")
    
    if hypothesis_updates:
        print(f"\n  hypothesis_updates[0]:")
        h = hypothesis_updates[0]
        print(f"    hypothesis_id: {h.hypothesis_id}")
        print(f"    hypothesis: {h.hypothesis[:30]}...")
        print(f"    change_type: {h.change_type}")
        print(f"    updated_view: {h.updated_view}")
    
    print("\nStep 2: 测试完整的 update (包含 LLM 调用)...")
    print("  (这会调用 DeepSeek API，可能需要一些时间...)")
    
    result = update(
        step5_judgements=step5_judgements,
        step7_result=step7_result,
        model="deepseek-chat"
    )
    
    print(f"\n  update 结果:")
    print(f"    hypothesis_updates 数量: {len(result.hypothesis_updates)}")
    print(f"    unchanged_hypotheses 数量: {len(result.unchanged_hypotheses)}")
    print(f"    overall_change: {result.overall_change}")
    
    if result.hypothesis_updates:
        print(f"\n  hypothesis_updates[0]:")
        h = result.hypothesis_updates[0]
        print(f"    hypothesis_id: {h.hypothesis_id}")
        print(f"    hypothesis: {h.hypothesis[:30]}...")
        print(f"    change_type: {h.change_type}")
        print(f"    updated_view: {h.updated_view[:50] if h.updated_view else 'EMPTY'}...")
        print(f"    why_changed: {h.why_changed[:50] if h.why_changed else 'EMPTY'}...")
    
    print("\n[OK] Step8 测试成功!")
    
except Exception as e:
    import traceback
    print(f"\n[ERROR] Step8 测试失败: {e}")
    traceback.print_exc()

print("\n调试完成!")
