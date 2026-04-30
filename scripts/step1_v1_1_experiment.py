# -*- coding: utf-8 -*-
"""
Step1 v1.1 实验脚本

对比 step1_current vs step1_v1_1_structured 的输出质量

运行：
    python scripts/step1_v1_1_experiment.py

输出：
    workspace/step1_experiment/
    ├── A1/
    │   ├── step1_current.txt
    │   ├── step1_v1_1.json
    │   └── compare.md
    ├── A2/
    │   ├── step1_current.txt
    │   ├── step1_v1_1.json
    │   └── compare.md
    ├── C1/
    │   ├── step1_current.txt
    │   ├── step1_v1_1.json
    │   └── compare.md
    ├── compare_all.md
    └── summary.md
"""

import io
import json
import os
import sys
from datetime import datetime

# 修复 Windows GBK 输出问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.deepseek_service import call_deepseek


# ============================================================
# Step1 当前版本
# ============================================================

STEP1_CURRENT_SYSTEM = (
    "你是一位资深投资人兼业务理解专家。"
    "你现在的任务是：读完一份 BP，输出一份清晰的初步判断。"
    "风格：有观点、有逻辑、不废话。不要大量引用原文，要形成判断。"
)

STEP1_CURRENT_USER = """
请对以下BP进行初步判断，输出：

一、【这家公司本质上是什么 / 不是什么】
- 一句话定位
- 2-3条关键判断

二、【初步看法】
- 这个方向靠谱吗？
- 最值得关注的亮点是什么？
- 最大的疑问是什么？

三、【需要重点了解的问题】
- 3-5个关键问题（会前就想知道的）

---

BP 全文：

{bp_text}
"""


# ============================================================
# Step1 v1.1 版本
# ============================================================

STEP1_V1_1_SYSTEM = """你是一位资深投资人。你的任务是对 BP 形成第一判断：轻量、精准、有观点。

重要：必须直接输出 JSON 格式，不要输出任何解释性文字。JSON 必须包含以下 7 个字段：company_essence, business_structure, revenue_logic, customer_logic, key_judgement, red_flags, must_ask_questions。

格式示例（注意：只需要输出JSON，不需要输出这个示例）：
{
  "company_essence": {"是什么": "...", "不是什么": ["..."], "confidence": "high"},
  "business_structure": {"current_business": [...], "narrative_business": [...]},
  "revenue_logic": {"current_money_source": "...", "clarity": "...", "red_flag_note": null},
  "customer_logic": {"who_pays": "...", "why_pays": "...", "sustainability": "..."},
  "key_judgement": {"statement": "...", "reasoning": "...", "stance": "meet"},
  "red_flags": {"flags": [...]},
  "must_ask_questions": {"questions": [...]}
}
"""

STEP1_V1_1_USER = """
你刚刚拿到一份 BP，请快速形成以下 7 个判断，用 JSON 格式输出：

【字段 1】company_essence（公司本质）
JSON格式输出，包含:
- 是什么: 一句话说明公司本质上在做什么
- 不是什么: 列出2-3条，明确划清边界的描述
- confidence: high | medium | low

【字段 2】business_structure（业务结构）
JSON格式输出，包含:
- current_business: 当前业务列表，每项包含name/description/confidence
- narrative_business: 叙事业务列表，每项包含name/description/evidence/confidence

【字段 3】revenue_logic（收入逻辑）
JSON格式输出，包含:
- current_money_source: 一句话说明当前钱从哪里来
- clarity: clear | vague | unclear
- red_flag_note: 如果不清楚，一句话说明最可疑的地方（如果没有则填null）

【字段 4】customer_logic（客户逻辑）
JSON格式输出，包含:
- who_pays: 谁在付钱（客户类型）
- why_pays: 客户付钱的动机是什么
- sustainability: 一次性 | 偶发性 | 持续性

【字段 5】key_judgement（核心判断）
JSON格式输出，包含:
- statement: 一句话核心判断
- reasoning: 为什么这么判断（一句话）
- stance: meet | pass | hold

【字段 6】red_flags（红旗）
JSON格式输出，包含:
- flags: 列表，每项包含flag（最不信的一点）/reason（一句话说明）/source（Step1判断|BP内容）

【字段 7】must_ask_questions（必问问题）
JSON格式输出，包含:
- questions: 列表，每项包含question（问题内容）/why（为什么问）/related_to（关联哪个字段）

请直接输出 JSON，不要输出任何解释性文字或格式说明。

---
BP 全文：

{bp_text}
"""


# ============================================================
# 测试项目列表
# ============================================================

TEST_PROJECTS = [
    {
        "id": "A1",
        "name": "斯年智驾（无人重载运输）",
        "bp_path": os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "workspace", "A1_1_0测试2_20260429_151410", "parsed", "bp_text.txt"
        )
    },
    {
        "id": "A2",
        "name": "A2项目",
        "bp_path": os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "workspace", "A2_1_0测试1_20260429_213714", "parsed", "bp_text.txt"
        )
    },
    {
        "id": "C1",
        "name": "C1项目",
        "bp_path": os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "workspace", "C1_1_0测试1_20260430_080032", "parsed", "bp_text.txt"
        )
    }
]


# ============================================================
# 运行函数
# ============================================================

def run_step1_current(bp_text: str) -> str:
    """运行当前版本的 Step1"""
    prompt = STEP1_CURRENT_USER.format(bp_text=bp_text)
    return call_deepseek(
        system_prompt=STEP1_CURRENT_SYSTEM,
        user_prompt=prompt,
        max_retries=2
    )


def run_step1_v1_1(bp_text: str) -> dict:
    """运行 v1.1 版本的 Step1"""
    prompt = STEP1_V1_1_USER.format(bp_text=bp_text)
    raw_output = call_deepseek(
        system_prompt=STEP1_V1_1_SYSTEM,
        user_prompt=prompt,
        max_retries=2
    )

    # 尝试解析 JSON
    try:
        # 尝试直接解析
        result = json.loads(raw_output)
        return result
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw_output)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except json.JSONDecodeError:
                return {"error": "JSON解析失败", "raw": raw_output}
        return {"error": "未找到JSON", "raw": raw_output}


def run_experiment():
    """运行完整实验"""
    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "workspace", "step1_v1_1_experiment", datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    os.makedirs(base_dir, exist_ok=True)

    all_results = []

    for project in TEST_PROJECTS:
        print(f"\n{'='*60}")
        print(f"处理项目: {project['id']} - {project['name']}")
        print(f"{'='*60}")

        # 读取 BP
        if not os.path.exists(project["bp_path"]):
            print(f"[WARN] BP file not found: {project['bp_path']}")
            continue

        with open(project["bp_path"], "r", encoding="utf-8") as f:
            bp_text = f.read()

        print(f"[OK] BP text length: {len(bp_text)} characters")

        # 运行当前版本
        print(f"运行 step1_current...")
        step1_current = run_step1_current(bp_text)

        # 运行 v1.1 版本
        print(f"运行 step1_v1_1...")
        step1_v1_1 = run_step1_v1_1(bp_text)

        # 创建项目目录
        project_dir = os.path.join(base_dir, project["id"])
        os.makedirs(project_dir, exist_ok=True)

        # 保存结果
        with open(os.path.join(project_dir, "step1_current.txt"), "w", encoding="utf-8") as f:
            f.write(step1_current)

        with open(os.path.join(project_dir, "step1_v1_1.json"), "w", encoding="utf-8") as f:
            json.dump(step1_v1_1, ensure_ascii=False, indent=2, fp=f)

        print(f"[OK] Results saved to: {project_dir}")

        all_results.append({
            "id": project["id"],
            "name": project["name"],
            "current": step1_current,
            "v1_1": step1_v1_1
        })

    return base_dir, all_results


def generate_compare_markdown(project_id: str, project_name: str, current: str, v1_1: dict) -> str:
    """生成单个项目的对比报告"""
    lines = [
        f"# {project_id} - {project_name}",
        f"",
        f"## 版本对比",
        f"",
        f"**step1_current**（纯文本）",
        f"",
        f"```",
        current[:500] + "..." if len(current) > 500 else current,
        f"```",
        f"",
        f"**step1_v1_1**（结构化 JSON）",
        f"",
    ]

    # 提取 v1_1 的关键信息
    if isinstance(v1_1, dict) and "error" not in v1_1:
        lines.append(f"### company_essence")
        lines.append(f"- 是什么: {v1_1.get('company_essence', {}).get('是什么', 'N/A')}")
        lines.append(f"- 不是什么: {v1_1.get('company_essence', {}).get('不是什么', [])}")
        lines.append(f"- confidence: {v1_1.get('company_essence', {}).get('confidence', 'N/A')}")
        lines.append(f"")

        lines.append(f"### business_structure")
        current_biz = v1_1.get('business_structure', {}).get('current_business', [])
        narrative_biz = v1_1.get('business_structure', {}).get('narrative_business', [])
        lines.append(f"- 当前业务: {[b.get('name') for b in current_biz] if current_biz else 'N/A'}")
        lines.append(f"- 叙事业务: {[b.get('name') for b in narrative_biz] if narrative_biz else 'N/A'}")
        lines.append(f"")

        lines.append(f"### revenue_logic")
        lines.append(f"- 当前钱从哪里来: {v1_1.get('revenue_logic', {}).get('current_money_source', 'N/A')}")
        lines.append(f"- 清晰度: {v1_1.get('revenue_logic', {}).get('clarity', 'N/A')}")
        lines.append(f"")

        lines.append(f"### customer_logic")
        lines.append(f"- 谁在付钱: {v1_1.get('customer_logic', {}).get('who_pays', 'N/A')}")
        lines.append(f"- 付钱动机: {v1_1.get('customer_logic', {}).get('why_pays', 'N/A')}")
        lines.append(f"- 持续性: {v1_1.get('customer_logic', {}).get('sustainability', 'N/A')}")
        lines.append(f"")

        lines.append(f"### key_judgement")
        lines.append(f"- 核心判断: {v1_1.get('key_judgement', {}).get('statement', 'N/A')}")
        lines.append(f"- 初步倾向: {v1_1.get('key_judgement', {}).get('stance', 'N/A')}")
        lines.append(f"")

        lines.append(f"### red_flags（{len(v1_1.get('red_flags', {}).get('flags', []))}个）")
        for flag in v1_1.get('red_flags', {}).get('flags', []):
            lines.append(f"- {flag.get('flag', 'N/A')}: {flag.get('reason', 'N/A')}")
        lines.append(f"")

        lines.append(f"### must_ask_questions（{len(v1_1.get('must_ask_questions', {}).get('questions', []))}个）")
        for q in v1_1.get('must_ask_questions', {}).get('questions', []):
            lines.append(f"- {q.get('question', 'N/A')} (为什么: {q.get('why', 'N/A')})")
    else:
        lines.append(f"[WARN] v1_1 output error: {v1_1}")

    return "\n".join(lines)


def generate_summary_markdown(all_results: list) -> str:
    """生成汇总报告"""
    lines = [
        "# Step1 v1.1 实验汇总报告",
        "",
        f"实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"实验项目: {', '.join([r['id'] for r in all_results])}",
        "",
        "## 评估维度",
        "",
        "| 维度 | 说明 |",
        "|------|------|",
        "| 更像投资人第一反应 | 读起来像有经验的投资人在说话，还是像AI在写报告？ |",
        "| 更清晰定义公司本质 | 能否用一句话说清楚'这家公司是什么'？ |",
        "| 更容易生成高质量问题 | must_ask_questions是否和red_flags/key_judgement有逻辑关联？ |",
        "| 是否'过度分析' | 是否出现了现金流分析、估值计算、壁垒展开等Step5才该有的内容？ |",
        "| 是否把未验证内容写死 | 是否把BP叙事当成事实判断了？ |",
        "",
        "## 各项目评估",
        ""
    ]

    for result in all_results:
        lines.append(f"### {result['id']} - {result['name']}")
        lines.append("")
        lines.append(f"**v1_1 核心判断:** {result['v1_1'].get('key_judgement', {}).get('statement', 'N/A')}")
        lines.append(f"**初步倾向:** {result['v1_1'].get('key_judgement', {}).get('stance', 'N/A')}")
        lines.append("")
        lines.append("**TODO: 请手动评估以下维度并填写**")
        lines.append("")
        lines.append("- [ ] 更像投资人第一反应")
        lines.append("- [ ] 更清晰定义公司本质")
        lines.append("- [ ] 更容易生成高质量问题")
        lines.append("- [ ] 没有'过度分析'")
        lines.append("- [ ] 没有把未验证内容写死")
        lines.append("")
        lines.append("**手动评估备注:**")
        lines.append("_(请在此填写你的评估理由)_")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 实验结论")
    lines.append("")
    lines.append("### v1.1 优于当前版本的维度（≥3个则建议进入阶段二）")
    lines.append("")
    lines.append("- [ ] 维度1: ")
    lines.append("- [ ] 维度2: ")
    lines.append("- [ ] 维度3: ")
    lines.append("- [ ] 维度4: ")
    lines.append("- [ ] 维度5: ")
    lines.append("")
    lines.append("### 主要发现")
    lines.append("_(请在此填写主要发现)_")
    lines.append("")
    lines.append("### 是否进入阶段二")
    lines.append("")
    lines.append("- [ ] 是")
    lines.append("- [ ] 否，原因: ")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Step1 v1.1 实验开始")
    print("=" * 60)

    base_dir, results = run_experiment()

    # 生成各项目对比报告
    for result in results:
        compare_md = generate_compare_markdown(
            result["id"],
            result["name"],
            result["current"],
            result["v1_1"]
        )
        with open(os.path.join(base_dir, result["id"], "compare.md"), "w", encoding="utf-8") as f:
            f.write(compare_md)

    # 生成汇总报告
    summary_md = generate_summary_markdown(results)
    with open(os.path.join(base_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\n{'='*60}")
    print(f"实验完成！结果保存在: {base_dir}")
    print(f"{'='*60}")
    print(f"\n请查看 summary.md 填写评估结果。")


if __name__ == "__main__":
    main()
