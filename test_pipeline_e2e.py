# -*- coding: utf-8 -*-
"""端到端测试 PipelineV2 完整流程（模拟 app.py 的实际调用）"""
import sys
import os

# Windows 下设置 UTF-8 输出
if sys.platform == "win32":
    import msvcrt
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("端到端测试 PipelineV2 完整流程")
print("=" * 60)

# 测试项目目录
test_project_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace",
    "test_e2e_project"
)
os.makedirs(test_project_dir, exist_ok=True)
os.makedirs(os.path.join(test_project_dir, "v2_context"), exist_ok=True)

# 写入模拟数据
print("\n1. 准备模拟数据...")

# 模拟会议记录
meeting_record = """会议记录测试
问：关于AI平台的技术壁垒是什么？
答：我们的AI平台准确率在70-80%之间。

问：关于2026年客户放量的预测依据？
答：我们预计欧莱雅2026年会有3000万以上的订单。

问：关于新能源业务的进展？
答：深共晶电解液方案预计2026年5月落地，但没有签署正式合同。
"""

with open(os.path.join(test_project_dir, "v2_context", "meeting_record.txt"), "w", encoding="utf-8") as f:
    f.write(meeting_record)
print("   会议记录已写入")

# 模拟 step5 数据
step5_summary = "杉海创新是一家美妆原料+AI平台+新能源业务的创业公司..."
step5_judgements = [
    {"hypothesis_id": "h_001", "hypothesis": "AI平台可能构成技术壁垒", "view": "AI平台准确率较高"},
    {"hypothesis_id": "h_002", "hypothesis": "新能源业务有明确收入时间表", "view": "预计2026年5月落地"},
]
step5_decision = "继续尽调，关注AI平台和新能源业务的进展"

# 模拟 step4 问题
step4_questions = [
    "AI平台的技术壁垒是什么？",
    "2026年客户放量的预测依据？",
    "新能源业务的进展如何？",
]

# 加载 Pipeline
try:
    from services.v2 import PipelineV2
    from services.v2.services import step6_extractor, step7_validator, step8_updater, step9_decider
    print("\n2. 导入模块成功")
except Exception as e:
    print(f"   导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 创建 Pipeline
pipeline = PipelineV2(
    project_id="test_e2e",
    project_name="test_e2e_project",
    workspace_dir=test_project_dir
)
pipeline.model = "deepseek-chat"
print("\n3. PipelineV2 创建成功")

# 模拟 app.py 的完整流程
print("\n" + "=" * 60)
print("开始执行完整流程...")
print("=" * 60)

try:
    # Step6
    print("\n[Step6] 开始...")
    step6 = pipeline.run_step6(step5_summary, meeting_record)
    print(f"[Step6] 完成，提取了 {len(step6.get('new_information', []))} 条新增信息")
    
    # Step7
    print("\n[Step7] 开始...")
    merged_questions = step4_questions
    step7 = pipeline.run_step7(
        step4_questions=merged_questions,
        step6_new_information=step6.get("new_information", []),
        meeting_record=meeting_record,
        step6_summary=step6.get("meeting_summary", "")
    )
    print(f"[Step7] 完成，问题对齐结果: {len(step7.get('question_validation', []))} 个问题")
    
    step7_summary = pipeline._summarize_step7(step7)
    step7_val_summary = pipeline._summarize_validation(step7)
    
    # Step8
    print("\n[Step8] 开始...")
    step8 = pipeline.run_step8(
        step5_judgements,
        step7_result=step7
    )
    print(f"[Step8] 完成，hypothesis_updates: {len(step8.get('hypothesis_updates', []))} 条")
    print(f"[Step8] unchanged_hypotheses: {len(step8.get('unchanged_hypotheses', []))} 条")
    
    # Step9
    print("\n[Step9] 开始...")
    print(f"[Step9] 接收到的 step8_output keys: {list(step8.keys())}")
    step9 = pipeline.run_step9(
        step6_output=step6,
        step7_output=step7,
        step8_output=step8
    )
    print(f"[Step9] 完成!")
    print(f"[Step9] overall_decision: {step9.get('overall_decision', {})}")
    
    # 检查输出文件
    print("\n" + "=" * 60)
    print("检查输出文件...")
    print("=" * 60)
    
    for step_name in ["step6", "step7", "step8", "step9"]:
        step_dir = os.path.join(test_project_dir, step_name)
        if os.path.exists(step_dir):
            files = os.listdir(step_dir)
            print(f"   {step_name}: {files}")
        else:
            print(f"   {step_name}: 目录不存在!")
    
    print("\n" + "=" * 60)
    print("端到端测试完成!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n执行失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
