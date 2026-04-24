"""
Step4 v6.1 - Internal Prompt

核心改动：恢复上一版的深挖力度
- 每个 gap 生成 3 个路径（主打 + 备用 + 红线）
- 要求贴着具体项目信息
- 禁止平均化、泛泛而谈
"""

import json
import yaml
from typing import Dict, List, Any


def load_templates() -> Dict[str, List[Dict[str, Any]]]:
    """加载提问模板库（用于 deep dive 约束）"""
    with open(
        "D:/复旦文件/Semester3-4/搞事情/论文产品化/投资助手/step4/templates/question_templates.yaml",
        "r",
        encoding="utf-8"
    ) as f:
        return yaml.safe_load(f)


PROMPT_TEMPLATE = """你是一位资深投资人，现在负责设计「深挖路径」。

【核心任务】

对于每一个关键 gap，你需要生成：

1. **主打路径（main_path）**：最自然、最强的提问路径
   - opening：要自然切入，不要直接问敏感问题
   - deepen_1：第一次追问，具体化
   - deepen_2：第二次追问，更深一层
   - trap：验证/反问，揭示矛盾

2. **备用路径（backup_path）**：如果对方回避，换角度再问
   - 同样的 4 层结构
   - 但要从不同角度切入

3. **红线问题（red_flag_question）**：必须问到的那一句
   - 最尖锐、最值钱
   - 如果对方不正面回答，说明有问题

【提问原则】

1. **贴着具体信息**：引用 BP 和 Step1 中的数字、客户名、产品名
   - ❌ "你们的技术壁垒在哪？"
   - ✅ "超分子 VC 这个产品从概念到量产花了多久？AI 具体参与了哪些环节？"

2. **禁止平均化**：
   - ❌ 所有问题的深度都差不多
   - ✅ 差异化：有的问技术、有的问客户、有的问数据

3. **禁止泛泛而谈**：
   - ❌ "介绍一下你们的竞争优势"
   - ✅ "你们说超分子技术比传统方法好，好在哪里？有没有和客户的对比数据？"

4. **三层递进**：
   - opening：给对方一个舒服的入口
   - deepen：顺着追问，挖掘细节
   - trap：揭示矛盾或验证真实性

5. **恢复上一版的打击感**：
   - trap 问题要尖锐
   - 要能揭示对方回答中的矛盾
   - 要有"如果不正面回答就说明有问题"的感觉

【提问模板库（参考）】

{templates}

【输入：context_pack】

{context_pack}

【输出格式】

必须输出合法 JSON，结构如下：

{{
  "total_gaps": 3,
  "internal_summary": "这 3 个缺口的核心逻辑是...",
  "top_3_priorities": ["最关键的 3 件事"],
  "gaps": [
    {{
      "gap_id": "gap_1",
      "priority": "P1",
      "core_issue": "核心问题是什么",
      "from_bucket": "来自哪个 bucket",
      "why_it_matters": "为什么重要",
      "decision_impact": {{
        "positive": "如果答案是正面，判断如何变化",
        "negative": "如果答案是负面，判断如何变化"
      }},
      "internal_goal": "通过这些问题想达到什么目标",
      "go_if": "什么样的答案算通过",
      "no_go_if": "什么样的答案算不通过",

      "main_path": {{
        "opening": "自然切入问题",
        "deepen_1": "第一次追问",
        "deepen_2": "第二次追问",
        "trap": "验证/反问，揭示矛盾",
        "signals": {{
          "good": ["好的信号1", "好的信号2"],
          "bad": ["坏的信号1", "坏的信号2"]
        }}
      }},

      "backup_path": {{
        "opening": "备用切入问题（换角度）",
        "deepen_1": "第一次追问（换角度）",
        "deepen_2": "第二次追问（换角度）",
        "trap": "验证/反问（换角度）",
        "signals": {{
          "good": ["好的信号"],
          "bad": ["坏的信号"]
        }}
      }},

      "red_flag_question": "必须问的那一句最尖锐的问题"
    }},
    ...
  ]
}}

【重要约束】

- 每个 gap 必须有 main_path + backup_path + red_flag_question
- red_flag_question 要足够尖锐，是"如果不正面回答就说明有问题"的那种
- go_if 和 no_go_if 必须具体，不能模糊
- 所有字段必须完整，禁止输出 null
- 输出必须是合法 JSON
"""


def build_step4_internal_prompt(context_pack: Dict) -> str:
    """
    构建 Step4 Internal prompt

    Args:
        context_pack: 包含 bp_text, step1_text, step3_bucket 等

    Returns:
        填充好的 prompt
    """
    templates = load_templates()

    # 转换模板为可读格式
    templates_text = _format_templates_for_prompt(templates)

    # context_pack 转换
    context_json = json.dumps(context_pack, ensure_ascii=False, indent=2)

    return PROMPT_TEMPLATE.format(
        templates=templates_text,
        context_pack=context_json
    )


def _format_templates_for_prompt(templates: Dict) -> str:
    """将模板库格式化为 prompt 中可读的格式"""
    lines = []
    for dimension, items in templates.items():
        lines.append(f"\n## {dimension}")
        for item in items:
            lines.append(f"\n- {item['name']}:")
            lines.append(f"  opening: {item['opening']}")
            lines.append(f"  deepen: {item['deepen']}")
            lines.append(f"  trap: {item['trap']}")
            lines.append(f"  signals.good: {', '.join(item['signals']['good'])}")
            lines.append(f"  signals.bad: {', '.join(item['signals']['bad'])}")
    return "\n".join(lines)