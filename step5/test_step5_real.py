# -*- coding: utf-8 -*-
"""
Step5 真实测试

使用杉海创新项目的数据测试决策收敛层
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import json
from datetime import datetime

# Ensure can import step5
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from step5.step5_service import Step5Service


def load_test_data():
    """加载测试数据"""
    base = "D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/workspace/杉海创新科技6_20260422_162546"

    # Step1
    with open(f"{base}/step1_v2_new.txt", "r", encoding="utf-8") as f:
        step1_text = f.read()

    # Step3
    with open(f"{base}/step3_v3_bucket.json", "r", encoding="utf-8") as f:
        step3_json = json.load(f)

    # Step4 Internal（使用 v6.1 的结果）
    with open(f"{base}/reports/step4_v61_internal.json", "r", encoding="utf-8") as f:
        step4_internal = json.load(f)

    return step1_text, step3_json, step4_internal


def save_output(result, prefix="v1"):
    """保存输出"""
    base = "D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/workspace/杉海创新科技6_20260422_162546/reports"
    os.makedirs(base, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存 JSON
    with open(f"{base}/step5_{prefix}_output.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    # 保存 Markdown
    with open(f"{base}/step5_{prefix}_decision.md", "w", encoding="utf-8") as f:
        f.write(result.to_markdown())

    return ts


def main():
    print("=" * 60)
    print("Step5 Decision Layer Test")
    print("=" * 60)

    # 加载数据
    print("\n[1] Loading test data...")
    step1_text, step3_json, step4_internal = load_test_data()
    print(f"  - Step1: {len(step1_text)} chars")
    print(f"  - Step3: {len(json.dumps(step3_json))} chars")
    print(f"  - Step4 Internal: {len(json.dumps(step4_internal))} chars")

    # 加载 API key
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
            temperature=0.5,
            max_tokens=3000,
        )
        return response.choices[0].message.content

    # 运行 Step5
    print("\n[2] Running Step5...")
    service = Step5Service(call_llm=call_llm)

    result = service.run(
        step1_text=step1_text,
        step3_json=step3_json,
        step4_internal=step4_internal
    )

    # 保存结果
    ts = save_output(result, prefix="v1")
    print(f"\n[OK] Results saved (timestamp: {ts})")

    # 验证结果
    print("\n[3] Validating results...")

    # 基本信息
    print(f"\n--- Basic Info ---")
    print(f"  updated_view: {len(result.updated_view)} chars")
    print(f"  must_win_conditions: {len(result.must_win_conditions)}")
    print(f"  deal_breakers: {len(result.deal_breakers)}")
    print(f"  key_unknowns: {len(result.key_unknowns)}")

    # Must win conditions
    print(f"\n--- Must Win Conditions ---")
    for i, cond in enumerate(result.must_win_conditions, 1):
        print(f"  {i}. {cond.condition}")
        print(f"     why: {cond.why[:50]}...")
        print(f"     verify: {cond.how_to_verify[:50]}...")

    # Deal breakers
    print(f"\n--- Deal Breakers ---")
    for i, db in enumerate(result.deal_breakers, 1):
        print(f"  {i}. {db.risk}")
        print(f"     trigger: {db.trigger}")

    # Key unknowns
    print(f"\n--- Key Unknowns ---")
    for i, ku in enumerate(result.key_unknowns, 1):
        blocking = "[BLOCKING]" if ku.blocking else "[OK]"
        print(f"  {i}. [{blocking}] {ku.question}")

    # Pre-meeting decision
    print(f"\n--- Pre-Meeting Decision ---")
    incline_map = {
        "lean_yes": "LEARN YES (lean toward investment)",
        "lean_no": "LEARN NO (lean toward passing)",
        "neutral": "NEUTRAL (need more info)"
    }
    print(f"  Inclination: {incline_map.get(result.pre_meeting_decision.inclination, '?')}")
    print(f"  Confidence: {result.pre_meeting_decision.confidence}")
    print(f"  Reason: {result.pre_meeting_decision.reason}")

    # 输出 Markdown 预览
    print("\n" + "=" * 60)
    print("Decision Framework Preview")
    print("=" * 60)
    print(result.to_markdown())

    print("\n" + "=" * 60)
    print("Step5 Test Complete!")
    print("=" * 60)

    return result


if __name__ == "__main__":
    main()
