"""
Step4 v4 real API test
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
    # Use the correct project path
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

    print("\nStarting Step4 v4 two-stage generation...")
    service = Step4Service(call_llm=call_deepseek)

    try:
        result = service.run(
            step1_text=step1_text,
            step3_json=step3_json,
            bp_text=bp_text,
        )

        print("\n[SUCCESS] Step4 v4 execution completed!")

        # Validate internal_json
        internal = result["internal_json"]
        print(f"\nInternal JSON Quality Check:")
        print(f"  Total gaps: {internal.get('total_gaps', 0)}")

        null_count = 0
        for gap in internal.get("decision_gaps", []):
            for field in ["internal_goal", "go_if", "no_go_if"]:
                if not gap.get(field):
                    null_count += 1
            if not gap.get("decision_impact", {}).get("positive"):
                null_count += 1
            print(f"  [{gap['gap_id']}] {gap['core_issue'][:40]} ({gap['priority']})")
            print(f"    internal_goal: {gap['internal_goal'][:60]}...")
            print(f"    go_if: {gap['go_if'][:60]}...")
            print(f"    no_go_if: {gap['no_go_if'][:60]}...")

        print(f"\n  Null fields: {null_count} (should be 0)")

        # Save outputs
        output_dir = project_path / "reports"
        output_dir.mkdir(exist_ok=True)

        internal_file = output_dir / "step4_v4_internal.json"
        internal_file.write_text(
            json.dumps(result["internal_json"], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n[Saved] {internal_file}")

        brief_file = output_dir / "step4_v4_meeting_brief.md"
        brief_file.write_text(result["meeting_brief_md"], encoding="utf-8")
        print(f"[Saved] {brief_file}")

        context_file = output_dir / "step4_v4_context.json"
        context_file.write_text(
            json.dumps(result["context_pack"], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[Saved] {context_file}")

        print(f"\n[Meeting Brief Preview - first 1500 chars]")
        print(result["meeting_brief_md"][:1500])
        print("...")

    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
