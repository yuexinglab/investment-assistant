# -*- coding: utf-8 -*-
"""测试 Step9 是否能正常运行"""
import sys
import io
import os

# Windows 下设置 UTF-8 输出
if sys.platform == "win32":
    import msvcrt
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("1. 导入测试...")

try:
    from services.v2.services import step9_decider
    print("   step9_decider 导入成功")
except Exception as e:
    print(f"   step9_decider 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from services.v2.services import step6_extractor, step7_validator, step8_updater
    print("   所有 step 服务导入成功")
except Exception as e:
    print(f"   step 服务导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from services.v2 import PipelineV2
    print("   PipelineV2 导入成功")
except Exception as e:
    print(f"   PipelineV2 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("2. 模拟 Step9 调用...")
# 模拟一个最简单的 step9 调用
mock_step8_summary = {
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

try:
    result = step9_decider.decide(
        step8_summary=mock_step8_summary,
        step7_summary="测试",
        model="deepseek-chat"
    )
    print("   Step9 调用成功")
    print("   结果类型: " + str(type(result)))
    if isinstance(result, dict):
        print("   结果包含的 key: " + str(list(result.keys())))
    else:
        print("   结果不是 dict 类型")
except Exception as e:
    print("   Step9 调用失败: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("全部测试通过!")
