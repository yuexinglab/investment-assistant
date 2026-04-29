"""
Step4 v6.1 - Internal Prompt

核心改动：恢复上一版的深挖力度
- 每个 gap 生成 3 个路径（主打 + 备用 + 红线）
- 要求贴着具体项目信息
- 禁止平均化、泛泛而谈

v6.2 改动（Step3B 整合）：
- 优先从 decision_gap_candidates 中选择最重要的 gap
- 按优先级规则排序：Step3B tension(high) > Step3B consistency_check(contradict) > Step3B packaging > Step3 key_uncertainty
- 回退机制：如果 decision_gap_candidates 为空，使用 step3_key_unknowns / step3_tensions
"""

import json
import os
import yaml
from typing import Dict, List, Any


def load_templates() -> Dict[str, List[Dict[str, Any]]]:
    """加载提问模板库（用于 deep dive 约束）"""
    _dir = os.path.dirname(os.path.abspath(__file__))
    _path = os.path.join(_dir, "templates", "question_templates.yaml")
    with open(_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


PROMPT_TEMPLATE = """你是一位资深投资人，现在负责设计「深挖路径」。

【第一步：选择 gap（最重要）】

优先从 context_pack.decision_gap_candidates 中选择最重要的 3 个 gap：

**优先级规则（按序取最高优先）**：
1. Step3B tension，severity=critical 优先
2. Step3B tension，severity=high 优先
3. Step3B consistency_check，judgement=contradict 优先
4. Step3B consistency_check，judgement=uncertain 优先
5. Step3B overpackaging_signal（不要超过 1 个，辅助性质）
6. Step3 key_uncertainty，涉及商业模式/收入结构/现金流/客户需求的优先

**回退机制**：
- 如果 decision_gap_candidates 为空或数量不足 3 个，使用 step3_key_unknowns + step3_tensions 补充

**gap 来源标记**：
- 每个 gap 的 core_issue 要保留 from_bucket / from_source 字段，注明来源（step3_key_uncertainty / step3b_tension / step3b_consistency_check / step3b_packaging_signal）

【第二步：为每个 gap 生成深挖路径】

对于每一个选定的 gap，你需要生成：

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

【第三步：提问原则】

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

5. **打击感**：
   - trap 问题要尖锐
   - 要能揭示对方回答中的矛盾
   - 要有"如果不正面回答就说明有问题"的感觉

【第四步：关于 Step3B 的特殊要求】

当 gap 来自 Step3B 时（tension / consistency_check / packaging_signal）：

- core_issue 要引用具体的 claim vs gap
- trap 问题要能揭示 BP 叙事中的包装成分
- red_flag_question 要直接点破矛盾点
- 示例（正）：❌ "你们的技术有什么优势？" → ✅ "你们说TransportGPT比传统方案好，好在哪里？有没有量化数据？如果没有TransportGPT，你们的无人重载车辆还能稳定运营吗？它到底是核心能力，还是对外融资叙事？"

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
      "from_bucket": "来自哪个 bucket（如：step3b_tension / step3_key_uncertainty 等）",
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
- gap 来源必须标注清楚（from_bucket 字段）

【禁止引入 context_pack 以外的项目实体】

所有问题（opening / deepen / trap / red_flag_question）必须严格基于 context_pack 中出现的实体，禁止引入其他项目的实体：

1. **实体来源锁定**：所有问题中的项目名、产品名、技术词、客户名必须来自 context_pack 中的以下字段之一：
   - bp_signals（关键词提取）
   - step3_bucket_points（具体判断点）
   - step3_key_unknowns / step3_tensions
   - decision_gap_candidates
   - step3b_consistency_checks / step3b_tensions / step3b_packaging_signals

2. **明确禁止的行业/业务词**：如果 context_pack 中没有以下词，禁止在问题中出现：
   - 配方、筛选、美妆、化妆品、原料（属于美妆/材料类项目）
   - 食品、新能源、医药、农业（属于跨行业扩张类项目）
   - 超分子、离子盐、共晶（属于材料化学类项目）
   - 建沐、千沐（属于特定公司项目）
   - 欧莱雅、华熙（属于美妆客户项目）

3. **自检规则（每个 gap 输出前必须执行）**：
   - 扫描当前 gap 的 main_path / backup_path / red_flag_question
   - 检查是否出现了 context_pack 未提供的：行业词 / 产品名 / 技术词 / 客户名
   - 如果发现污染词，立即改写为当前项目的对应词汇
   - 改写原则：用 context_pack 中已有的同领域词替换，或用更通用的业务描述替换

4. **red_flag_question 专项约束**：
   - 必须与当前 gap 的 core_issue 强相关
   - 必须引用当前项目的具体业务场景（客户类型、技术路线、商业模式之一）
   - 禁止使用跨项目的类比或举例
   - 示例（正）："如果没有 TransportGPT，你们现有无人重载车辆还能稳定运营吗？"
   - 示例（误）："如果没有AI，你们的配方筛选还能做吗？"（← 污染词，来自其他项目）

5. **跨项目污染典型案例**：
   - ❌ "研发团队里AI背景的有几人？具体负责什么环节？"（来自材料/美妆项目语境）
   - ❌ "这些产品还能做出来吗？"（来自材料项目语境）
   - ✅ "TransportGPT到底是核心能力，还是对外融资叙事？"
   - ✅ "如果代运营需要公司自持车辆，那这轮融资够买多少台车？"

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