# generate_step3_sample.py
# 生成包含 project_structure 的 step3.json 示例

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.deepseek_service import call_deepseek
from step3.step3_prompt import build_step3_prompt
from step3.project_structure_detector import detect_project_structure

# 斯年智驾 BP
BP_SINIAN = """
斯年智驾是一家专注于自动驾驶卡车商业化运营的公司。

公司概述：
- 成立于2020年，专注于港口及物流园区的自动驾驶卡车运营
- 已完成4轮融资，累计融资额超过3亿元
- 团队规模超过200人，其中研发人员占比60%

核心业务：
1. 自动驾驶软硬件设备销售
   - 自主研发的感知、决策、执行全栈技术
   - 已获得多项核心专利
2. 智能物流代运营服务
   - 为物流企业提供自动驾驶卡车运营托管
   - 已运营超过1000万公里
3. 物流园区智能化项目实施
   - 提供整体解决方案

商业模式：
- 重资产运营模式，自购车队
- 预计明年车队规模突破500辆
- 主要客户：顺丰、中通、京东物流等头部快递企业
- 前五大客户收入占比超过60%

竞争优势：
- 完整的自动驾驶技术栈
- 丰富的运营经验
- 与多家头部物流企业建立合作

财务数据（未经审计）：
- 2023年收入：8000万元
- 2024年预计收入：2亿元
"""

STEP1_SINIAN = """
【初始判断】
这是一个自动驾驶卡车商业化运营项目。

技术维度：
- 具备完整的自动驾驶技术栈
- 已获得多项核心专利

商业模式：
- 混合模式：设备销售 + 代运营服务 + 项目制
- 重资产运营，自购车队

风险点：
- 重资产运营带来现金流压力
- 大客户依赖（顺丰、中通等占比60%）
- 行业竞争加剧

初始评分：7.5/10
建议关注：商业化路径、现金流管理、大客户依赖
"""

def generate_sinian_step3():
    print("Generating Step3 for 斯年智驾...")

    # 识别项目结构
    text = BP_SINIAN + STEP1_SINIAN
    project_structure = detect_project_structure(text)
    ps_dict = project_structure.to_dict()

    print(f"\n项目结构识别结果:")
    print(json.dumps(ps_dict, ensure_ascii=False, indent=2))

    # 构建 prompt
    prompt = build_step3_prompt(
        step1_text=STEP1_SINIAN,
        bp_text=BP_SINIAN,
        industry="general",
        selected_buckets=["tech_barrier", "commercialization", "customer_value"],
        project_structure=ps_dict,
    )

    print("\n\nCalling DeepSeek API...")
    raw = call_deepseek(
        system_prompt="你是一位严谨的投资研究员。请严格输出合法 JSON，不要输出多余解释。",
        user_prompt=prompt,
        max_retries=2
    )

    print("\nRaw response length:", len(raw))

    # 保存结果
    result = {
        "project_structure": ps_dict,
        "raw_step3": raw[:500] + "..." if len(raw) > 500 else raw
    }

    # 保存完整 JSON（带时间戳，避免覆盖）
    from datetime import datetime
    import os
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"workspace/step3_sample_sinian_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/step3.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, ensure_ascii=False, indent=2, fp=f)

    print(f"\nResult saved to: {output_path}")
    return result


if __name__ == "__main__":
    generate_sinian_step3()
