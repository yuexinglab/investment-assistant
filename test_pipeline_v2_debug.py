# -*- coding: utf-8 -*-
"""测试完整的 PipelineV2 流程"""
import sys
import os

# Windows 下设置 UTF-8 输出
if sys.platform == "win32":
    import msvcrt
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("=" * 50)
print("测试 PipelineV2 完整流程")
print("=" * 50)

# 测试项目目录
test_project_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace",
    "test_debug_project"
)
os.makedirs(test_project_dir, exist_ok=True)

print(f"项目目录: {test_project_dir}")

try:
    from services.v2 import PipelineV2
    
    # 创建 Pipeline 实例
    pipeline = PipelineV2(
        project_id="test_debug",
        project_name="test_debug_project",
        workspace_dir=os.path.dirname(test_project_dir)
    )
    pipeline.model = "deepseek-chat"
    print("PipelineV2 创建成功")
    
    # 测试单步运行 - Step9
    print("\n" + "=" * 50)
    print("测试 run_step9 (单步)")
    print("=" * 50)
    
    mock_step6_output = {
        "new_information": []
    }
    mock_step7_output = {
        "meeting_quality": {},
        "question_validation": []
    }
    mock_step8_output = {
        "decision_signals": {
            "confirmed_negatives": [],
            "validated_positives": [],
            "key_uncertainties": []
        },
        "invalidated_points": [],
        "uncertain_points": [],
        "validated_points": [],
        "_counts": {
            "confirmed_negative": 0,
            "validated_positive": 0,
            "key_uncertainty": 0,
            "weakened": 0,
            "uncertain": 0,
            "reinforced": 0
        }
    }
    
    result = pipeline.run_step9(
        step6_output=mock_step6_output,
        step7_output=mock_step7_output,
        step8_output=mock_step8_output
    )
    
    print(f"run_step9 成功!")
    print(f"结果包含: {list(result.keys())}")
    
    # 检查输出文件
    step9_dir = os.path.join(test_project_dir, "step9")
    if os.path.exists(step9_dir):
        print(f"step9 输出目录已创建: {step9_dir}")
        files = os.listdir(step9_dir)
        print(f"输出文件: {files}")
    else:
        print("WARNING: step9 输出目录未创建")
    
    print("\n" + "=" * 50)
    print("全部测试通过!")
    print("=" * 50)
    
except Exception as e:
    print(f"\n测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
