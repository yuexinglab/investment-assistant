# -*- coding: utf-8 -*-
"""手动触发 pipeline 测试"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant")

from services.pipeline_v1 import run_pipeline_v1

PROJECT = r"D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\杉海创新科技6_20260422_162546"

bp_path = os.path.join(PROJECT, "parsed", "bp_text.txt")
with open(bp_path, "r", encoding="utf-8") as f:
    bp_text = f.read()

print(f"BP 文本长度: {len(bp_text)} 字")
print("开始运行 pipeline...")

def on_progress(step, status, percent, msg):
    print(f"[{percent:3d}%] {step} -> {status}: {msg}")

try:
    results = run_pipeline_v1(bp_text, PROJECT, on_progress=on_progress)
    print("\n=== Pipeline 完成 ===")

    if "step3b" in results and results["step3b"]:
        print(f"\nStep3B summary (前200字): {results['step3b'].get('summary', '')[:200]}")
        print(f"Step3B consistency_checks 数量: {len(results['step3b'].get('consistency_checks', []))}")
        print(f"Step3B tensions 数量: {len(results['step3b'].get('tensions', []))}")

    if "step4" in results:
        step4 = results["step4"]
        print(f"\nStep4 keys: {list(step4.keys())}")

        # 正确读取 internal（不是 internal_json）
        internal = step4.get("internal", {})
        print(f"Step4 internal (len): {len(json.dumps(internal, ensure_ascii=False))}")

        if internal:
            gaps = internal.get("gaps", [])
            print(f"\n共生成 {len(gaps)} 个 gap:")
            for g in gaps:
                print(f"  - [{g.get('gap_id')}] {g.get('core_issue', '')[:60]}")
                print(f"    from_bucket: {g.get('from_bucket', '')}")
                print(f"    priority: {g.get('priority', '')}")
                print(f"    red_flag: {str(g.get('red_flag_question', ''))[:80]}")

        # 检查 context_pack（如果被返回）
        context_pack = step4.get("context_pack", {})
        print(f"\ncontext_pack keys: {list(context_pack.keys())}")

    # 也检查文件
    internal_file = os.path.join(PROJECT, "step4", "step4_internal.json")
    with open(internal_file, "r", encoding="utf-8") as f:
        file_content = f.read()
    print(f"\n文件 step4_internal.json 大小: {len(file_content)} 字节")
    if file_content and file_content != "{}":
        parsed = json.loads(file_content)
        print(f"文件内 gaps 数量: {len(parsed.get('gaps', []))}")

except Exception as e:
    import traceback
    print(f"\nPipeline 出错: {e}")
    traceback.print_exc()
