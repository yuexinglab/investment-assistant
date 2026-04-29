# -*- coding: utf-8 -*-
"""
A1项目1.0流程完整测试脚本
"""
import os
import sys
import datetime
import json

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.pipeline_v1 import run_pipeline_v1

def main():
    # 项目目录
    project_dir = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\A1_完整测试_fresh'

    # 读取BP原文
    bp_path = os.path.join(project_dir, 'parsed', 'bp_text.txt')
    with open(bp_path, 'r', encoding='utf-8') as f:
        bp_text = f.read()

    print(f"=" * 60)
    print(f"A1项目 1.0 完整流程测试")
    print(f"=" * 60)
    print(f"BP长度: {len(bp_text)} 字符")
    print(f"项目目录: {project_dir}")
    print()

    def on_progress(step, status, percent, msg):
        symbol = "✓" if status == "done" else "✗" if status == "error" else "→"
        print(f"  [{percent:3d}%] {symbol} {step.upper()}: {msg}")

    print("开始运行 1.0 Pipeline...")
    print("-" * 60)

    start = datetime.datetime.now()
    try:
        results = run_pipeline_v1(bp_text, project_dir, on_progress=on_progress)
        end = datetime.datetime.now()

        print("-" * 60)
        print(f"\n✓ 流程完成! 耗时: {(end-start).total_seconds():.1f}秒")
        print(f"\n已完成步骤: {list(results.keys())}")

        # 保存结果摘要
        summary = {
            "project": "A1_完整测试_fresh",
            "total_time_seconds": (end-start).total_seconds(),
            "completed_steps": list(results.keys()),
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(os.path.join(project_dir, 'pipeline_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n结果文件已保存到: {project_dir}")
        return results

    except Exception as e:
        print(f"\n✗ 流程失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
