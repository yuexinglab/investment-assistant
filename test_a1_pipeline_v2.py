# -*- coding: utf-8 -*-
"""
A1项目1.0流程完整测试脚本 - V2
使用已有目录重跑
"""
import os
import sys
import datetime
import json
import shutil

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.pipeline_v1 import run_pipeline_v1

def main():
    # 使用已有的A1项目目录
    base_dir = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace'
    src_project = os.path.join(base_dir, '第一批测试A1_20260428_101520')

    # 创建新的输出目录（带时间戳）
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    project_dir = os.path.join(base_dir, f'A1_重测_{timestamp}')

    print(f"创建测试目录: {project_dir}")
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'parsed'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'step1'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'step3'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'step3b'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'step4'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'step5'), exist_ok=True)

    # 复制BP原文
    src_bp = os.path.join(src_project, 'parsed', 'bp_text.txt')
    dst_bp = os.path.join(project_dir, 'parsed', 'bp_text.txt')
    shutil.copy(src_bp, dst_bp)
    print(f"已复制BP到: {dst_bp}")

    # 读取BP原文
    with open(dst_bp, 'r', encoding='utf-8') as f:
        bp_text = f.read()

    print(f"\n{'=' * 60}")
    print(f"A1项目 1.0 完整流程测试")
    print(f"{'=' * 60}")
    print(f"BP长度: {len(bp_text)} 字符")
    print(f"项目目录: {project_dir}")
    print()

    def on_progress(step, status, percent, msg):
        symbol = "[OK]" if status == "done" else "[X]" if status == "error" else "..."
        print(f"  [{percent:3d}%] {symbol} {step.upper()}: {msg}")

    print("开始运行 1.0 Pipeline...")
    print("-" * 60)

    start = datetime.datetime.now()
    try:
        results = run_pipeline_v1(bp_text, project_dir, on_progress=on_progress)
        end = datetime.datetime.now()

        print("-" * 60)
        print(f"\n[OK] 流程完成! 耗时: {(end-start).total_seconds():.1f}秒")
        print(f"\n已完成步骤: {list(results.keys())}")

        # 保存结果摘要
        summary = {
            "project": f"A1_重测_{timestamp}",
            "total_time_seconds": (end-start).total_seconds(),
            "completed_steps": list(results.keys()),
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(os.path.join(project_dir, 'pipeline_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n结果文件已保存到: {project_dir}")

        # 打印输出文件列表
        print("\n生成的文件:")
        for step in ['step1', 'step3', 'step3b', 'step4', 'step5']:
            step_dir = os.path.join(project_dir, step)
            if os.path.exists(step_dir):
                files = os.listdir(step_dir)
                for f in files:
                    print(f"  - {step}/{f}")

        return results

    except Exception as e:
        print(f"\n[X] 流程失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
