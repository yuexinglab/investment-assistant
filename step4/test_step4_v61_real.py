# -*- coding: utf-8 -*-
"""
Step4 v6.1 Real Test

Test content:
1. Basic scan layer (conversational)
2. Deep dive layer (multi-path + deepen_2)
3. Meeting brief (layered display)
"""

import sys
import os
import json
from datetime import datetime

# Ensure can import step4
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from step4.step4_service import Step4Service


def load_test_data():
    """Load test data"""
    base = "D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/workspace/杉海创新科技6_20260422_162546"

    # Step1
    with open(f"{base}/step1_v2_new.txt", "r", encoding="utf-8") as f:
        step1_text = f.read()

    # Step3
    with open(f"{base}/step3_v3_bucket.json", "r", encoding="utf-8") as f:
        step3_json = f.read()

    # BP
    bp_path = f"{base}/materials/bp_162546.pdf"
    # Try to read txt version
    bp_txt_path = bp_path.replace(".pdf", ".txt")
    if os.path.exists(bp_txt_path):
        with open(bp_txt_path, "r", encoding="utf-8") as f:
            bp_text = f.read()
    else:
        # Try parsed txt
        for root, dirs, files in os.walk(f"{base}/parsed"):
            for f in files:
                if "bp" in f.lower() and f.endswith(".txt"):
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                        bp_text = fp.read()
                    break
            else:
                continue
            break
        else:
            bp_text = "Cannot load BP text"

    return step1_text, step3_json, bp_text


def save_output(result, prefix="v61"):
    """Save output"""
    base = "D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/workspace/杉海创新科技6_20260422_162546/reports"
    os.makedirs(base, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save scan_questions
    with open(f"{base}/step4_{prefix}_scan_questions.json", "w", encoding="utf-8") as f:
        json.dump(result["scan_questions"], f, ensure_ascii=False, indent=2)

    # Save internal_json (full)
    with open(f"{base}/step4_{prefix}_internal.json", "w", encoding="utf-8") as f:
        json.dump(result["internal_json"], f, ensure_ascii=False, indent=2)

    # Save meeting_brief
    with open(f"{base}/step4_{prefix}_meeting_brief.md", "w", encoding="utf-8") as f:
        f.write(result["meeting_brief_md"])

    # Save full result
    with open(f"{base}/step4_{prefix}_full_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": ts,
            "scan_questions_count": len(result["scan_questions"]),
            "internal_gaps_count": result["internal_json"].get("total_gaps", 0),
            "gaps": [
                {
                    "gap_id": g["gap_id"],
                    "has_main_path": "main_path" in g,
                    "has_backup_path": "backup_path" in g,
                    "has_red_flag": "red_flag_question" in g,
                    "main_path_deepens": len(g.get("main_path", {}).get("deepen_2", "")) if g.get("main_path") else 0,
                }
                for g in result["internal_json"].get("gaps", [])
            ]
        }, f, ensure_ascii=False, indent=2)

    return ts


def main():
    print("=" * 60)
    print("Step4 v6.1 Real Test")
    print("=" * 60)

    # Load data
    print("\n[1] Loading test data...")
    step1_text, step3_json, bp_text = load_test_data()
    print(f"  - Step1: {len(step1_text)} chars")
    print(f"  - Step3: {len(step3_json)} chars")
    print(f"  - BP: {len(bp_text)} chars")

    # Load API key
    from dotenv import load_dotenv
    load_dotenv("D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/.env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not found")
        return

    def call_llm(system_prompt: str, user_prompt: str) -> str:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=3000,
        )
        return response.choices[0].message.content

    # Run v6.1
    print("\n[2] Running Step4 v6.1...")
    service = Step4Service(call_llm=call_llm)

    result = service.run(
        step1_text=step1_text,
        step3_json=step3_json,
        bp_text=bp_text,
    )

    # Save result
    ts = save_output(result, prefix="v61")
    print(f"\n[OK] Results saved (timestamp: {ts})")

    # Validate result
    print("\n[3] Validating results...")

    # 1. scan_questions
    scan_q = result["scan_questions"]
    print(f"\n--- Basic Scan Layer ---")
    print(f"  Dimensions: {len(scan_q)}")
    for dim, data in scan_q.items():
        if isinstance(data, dict) and "best_question" in data:
            print(f"  - {dim}: OK (has best_question)")
        elif isinstance(data, list):
            print(f"  - {dim}: FAIL (old format)")

    # 2. internal_json
    internal = result["internal_json"]
    print(f"\n--- Deep Dive Layer ---")
    print(f"  Gaps: {internal.get('total_gaps', 0)}")

    for gap in internal.get("gaps", []):
        gap_id = gap.get("gap_id", "?")
        main = gap.get("main_path", {})
        backup = gap.get("backup_path", {})

        print(f"\n  {gap_id}:")
        print(f"    main_path: {'OK' if main else 'FAIL'}")
        if main:
            print(f"      - deepen_1: {'OK' if main.get('deepen_1') else 'FAIL'}")
            print(f"      - deepen_2: {'OK' if main.get('deepen_2') else 'FAIL'}")
            print(f"      - trap: {'OK' if main.get('trap') else 'FAIL'}")

        print(f"    backup_path: {'OK' if backup else 'FAIL'}")
        print(f"    red_flag_question: {'OK' if gap.get('red_flag_question') else 'FAIL'}")

    # 3. meeting_brief
    print(f"\n--- Meeting Brief ---")
    brief = result["meeting_brief_md"]
    print(f"  Length: {len(brief)} chars")

    # Check if contains scan layer and deep dive layer
    has_scan = "基础扫描" in brief or "Basic Scan" in brief
    has_deep_dive = "深挖" in brief or "Deep Dive" in brief
    print(f"  Has scan layer: {'OK' if has_scan else 'FAIL'}")
    print(f"  Has deep dive layer: {'OK' if has_deep_dive else 'FAIL'}")

    print("\n" + "=" * 60)
    print("v6.1 Test Complete!")
    print("=" * 60)

    return result


if __name__ == "__main__":
    main()
