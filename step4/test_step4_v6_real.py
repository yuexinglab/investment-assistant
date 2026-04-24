"""
Step4 v6 real API test
测试 v6 升级：基础扫描层 + 深挖层
"""

import os
import sys
import io
import json
from pathlib import Path

# Fix Windows GBK encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from step4.step4_service import Step4Service


def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    import requests

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("Please set DEEPSEEK_API_KEY")

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def main():
    # Use the same project path as v4/v5 test
    project_path = Path("D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/workspace/杉海创新科技6_20260422_162546")
    step1_file = project_path / "step1_v2_new.txt"
    step3_file = project_path / "step3_v3_bucket.json"
    bp_file = project_path / "materials" / "bp_162546.pdf"

    for name, f in [("Step1", step1_file), ("Step3", step3_file), ("BP", bp_file)]:
        if f.exists():
            print(f"[OK] {name}: found")
        else:
            print(f"[FAIL] {name} not found: {f}")
            return

    step1_text = step1_file.read_text(encoding="utf-8")
    step3_json = step3_file.read_text(encoding="utf-8")

    # Extract BP from PDF
    import pdfplumber
    with pdfplumber.open(bp_file) as pdf:
        bp_text = "\n".join([p.extract_text() or "" for p in pdf.pages])

    print(f"Data loaded - Step1: {len(step1_text)}, Step3: {len(step3_json)}, BP: {len(bp_text)}")

    print("\n" + "=" * 60)
    print("Step4 v6 Real API Test (扫描层 + 深挖层)")
    print("=" * 60)

    service = Step4Service(call_llm=call_deepseek)

    try:
        result = service.run(
            step1_text=step1_text,
            step3_json=step3_json,
            bp_text=bp_text,
        )

        print("\n[SUCCESS] Step4 v6 execution completed!")

        # ============================================================
        # 1. Scan Questions (v6 新增)
        # ============================================================
        print("\n" + "=" * 60)
        print("v6 基础扫描层 (Scan Questions)")
        print("=" * 60)

        scan_questions = result.get("scan_questions", {})
        if "error" in scan_questions:
            print(f"[ERROR] {scan_questions['error']}")
        else:
            for dimension, questions in scan_questions.items():
                if isinstance(questions, list):
                    print(f"\n【{dimension}】")
                    for i, q in enumerate(questions, 1):
                        print(f"  {i}. {q}")

        # ============================================================
        # 2. Internal JSON (深挖层)
        # ============================================================
        print("\n" + "=" * 60)
        print("深挖层 (Deep Questions)")
        print("=" * 60)

        internal = result["internal_json"]
        print(f"Total gaps: {internal.get('total_gaps', 0)}")

        for gap in internal.get("decision_gaps", []):
            print(f"\n[{gap['gap_id']}] {gap['core_issue'][:50]}... ({gap['priority']})")
            qps = gap.get("question_paths", [])
            print(f"  Question paths: {len(qps)}")

        # ============================================================
        # 3. Save outputs
        # ============================================================
        output_dir = project_path / "reports"
        output_dir.mkdir(exist_ok=True)

        # Save scan questions
        scan_file = output_dir / "step4_v6_scan_questions.json"
        scan_file.write_text(
            json.dumps(scan_questions, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n[Saved] {scan_file}")

        # Save full result
        full_result = {
            "context_pack": result["context_pack"],
            "internal_json": result["internal_json"],
            "scan_questions": scan_questions,
            "meeting_brief_md": result["meeting_brief_md"],
        }
        full_file = output_dir / "step4_v6_full_result.json"
        full_file.write_text(
            json.dumps(full_result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[Saved] {full_file}")

        brief_file = output_dir / "step4_v6_meeting_brief.md"
        brief_file.write_text(result["meeting_brief_md"], encoding="utf-8")
        print(f"[Saved] {brief_file}")

        # ============================================================
        # 4. Meeting Brief Preview
        # ============================================================
        print("\n" + "=" * 60)
        print("Meeting Brief Preview (v6 - 含扫描层)")
        print("=" * 60)
        print(result["meeting_brief_md"])

    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
