# -*- coding: utf-8 -*-
"""
Step5 v2 真实测试 - 探索型投资人版本

使用杉海创新项目的数据测试决策收敛层 v2
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
from step5.step5_prompt import build_step5_prompt


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


def save_output(result, prefix="v2"):
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
    print("=" * 70)
    print("Step5 v2 - 探索型投资人版本测试")
    print("=" * 70)

    # 加载数据
    print("\n[1] 加载测试数据...")
    step1_text, step3_json, step4_internal = load_test_data()
    print(f"  - Step1: {len(step1_text):,} 字符")
    print(f"  - Step3: {len(json.dumps(step3_json)):,} 字符")
    print(f"  - Step4 Internal: {len(json.dumps(step4_internal)):,} 字符")

    # 验证 prompt 长度
    prompt = build_step5_prompt(step1_text, step3_json, step4_internal)
    print(f"  - Prompt 总计: {len(prompt):,} 字符")

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
            max_tokens=4000,
        )
        return response.choices[0].message.content

    # 运行 Step5 v2
    print("\n[2] 运行 Step5 v2...")
    service = Step5Service(call_llm=call_llm)

    result = service.run(
        step1_text=step1_text,
        step3_json=step3_json,
        step4_internal=step4_internal
    )

    # 保存结果
    ts = save_output(result, prefix="v2")
    print(f"\n[OK] 结果已保存 (时间戳: {ts})")

    # 验证结果
    print("\n[3] 验证结果...")

    # 1. 当前假设
    print(f"\n--- 当前假设 ---")
    print(f"  {result.current_hypothesis[:200]}...")

    # 2. 为什么可能是错的
    print(f"\n--- 为什么这个假设可能是错的 (关键!) ---")
    for i, reason in enumerate(result.why_this_might_be_wrong, 1):
        print(f"  {i}. {reason[:100]}...")

    # 3. 投资逻辑
    print(f"\n--- 投资逻辑 ---")
    print(f"  Bull Case ({len(result.investment_logic.bull_case)}条):")
    for i, item in enumerate(result.investment_logic.bull_case, 1):
        print(f"    {i}. {item[:80]}...")
    print(f"  Bear Case ({len(result.investment_logic.bear_case)}条):")
    for i, item in enumerate(result.investment_logic.bear_case, 1):
        print(f"    {i}. {item[:80]}...")

    # 4. 关键验证点
    print(f"\n--- 关键验证点 ---")
    for i, vp in enumerate(result.key_validation_points, 1):
        print(f"  {i}. {vp.point[:60]}...")

    # 5. 放弃信号
    print(f"\n--- 放弃信号 ---")
    for i, db in enumerate(result.deal_breaker_signals, 1):
        print(f"  {i}. {db.signal[:60]}...")

    # 6. 会前目标
    print(f"\n--- 会前目标 ---")
    print(f"  {result.meeting_objective[:150]}...")

    # 7. 下一步策略
    print(f"\n--- 下一步策略 ---")
    print(f"  当前动作: {result.next_step_strategy.current_action}")

    # 输出 Markdown 预览
    print("\n" + "=" * 70)
    print("Step5 v2 完整输出预览")
    print("=" * 70)
    print(result.to_markdown())

    print("\n" + "=" * 70)
    print("Step5 v2 测试完成!")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()
