from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from step3.bucket_registry import get_general_bucket
from step3.industry_loader import load_industry_enhancements


PROMPT_TEMPLATE = """你现在处于 Step3：对抗型分析层。

你的任务不是下投资结论，而是：
在 Step1 初始判断的基础上，同时扮演"支持者"和"反对者"，
主动寻找 Step1 可能错的地方，帮助后续 Step4 做决策缺口识别。

============================================
【核心原则 — 必须遵守】
============================================

1. 【强制对抗性】每个桶必须同时输出：
   - 至少1条 support（支持 Step1）
   - 至少1条 contradict 或 neutral（挑战 Step1）
   如果找不到反例，必须说明："为什么这个判断难以被反驳"

2. 【BP主张校验】所有 BP 内容都是"公司主张（claim）"，不是事实。
   每条输出必须隐含以下结构：
   - 【claim】BP说了什么
   - 【reality】行业通常如何
   - 【gap】是否存在证据缺口或矛盾
   - 【结论】support / contradict / neutral

3. 【限制单边强化】如果一个桶全是 support，说明分析不完整。
   必须补充反例。

4. 【收敛性】你不是在"分析公司"，而是在"找判断的盲点"。

============================================
【输入信息】
============================================

【Step1 初始判断】
{step1_text}

【项目材料（BP）】
{bp_text}

【项目结构识别结果（系统初判，仅作参考）】
{project_structure_text}

【外部补充信息（可为空）】
{external_context}

【本次分析桶（已自动选择）】
{selected_bucket_labels}

============================================
【被选桶的定义与增强要求】
{bucket_specs}

============================================
【必须按以下结构输出 JSON】

第一部分：桶内关键背景信息（对抗性）
- 每个桶必须恰好2条：
  - 1条 relation_to_step1 = "support"
  - 1条 relation_to_step1 = "contradict" 或 "neutral"
- 每条必须包含：
  - bucket_key, bucket_label, point, explanation
  - relation_to_step1, certainty, source_type

第二部分：公开可补的信息
- 每个桶最多1条
- 只写"通过公开资料大致可确认"的信息

第三部分：公开仍无法确认的问题（决策阻断问题）
- 总计最多3条
- 只保留：impact_level = high 的问题
- 只保留：无法通过公开信息解决、必须通过尽调/沟通/实验验证的问题
- 格式：bucket_key, question, why_unresolved, impact_level

第四部分：关键张力（tensions）— 新增
- 提取2–3个最重要的"认知冲突"
- 必须是不同桶之间的矛盾，或同一问题的正反两面
- 格式：字符串，如"技术壁垒弱 vs 商业化已成立"
- 如果没有张力，输出空列表 []

第五部分：对 Step1 的校正提示
- supported：当前更支持 Step1 的地方
- caution：当前提示 Step1 需要谨慎或收缩的地方（至少1条反例带来的谨慎）
- to_step4：必须带入 Step4 做决策缺口识别的问题

============================================
【输出 JSON 结构】

{{
  "selected_buckets": [...],
  "bucket_outputs": [
    {{
      "bucket_key": "...",
      "bucket_label": "...",
      "point": "...",
      "explanation": "...",
      "relation_to_step1": "support | contradict | neutral",
      "certainty": "high | medium | low",
      "source_type": "common_sense | bp | external_context | unknown"
    }}
  ],
  "publicly_resolvable": [
    {{
      "bucket_key": "...",
      "item": "...",
      "current_conclusion": "...",
      "confidence": "high | medium | low"
    }}
  ],
  "still_unresolved": [
    {{
      "bucket_key": "...",
      "question": "...",
      "why_unresolved": "...",
      "impact_level": "high"
    }}
  ],
  "tensions": ["张力描述1", "张力描述2"],
  "step1_adjustment_hints": {{
    "supported": [],
    "caution": [],
    "to_step4": []
  }}
}}
"""


def build_bucket_specs(industry: str, selected_buckets: List[str]) -> str:
    enhancements = load_industry_enhancements(industry)
    blocks = []

    for bucket_key in selected_buckets:
        general = get_general_bucket(bucket_key)
        enhancement = enhancements.get(bucket_key, {})

        lines = [
            f"- bucket_key: {general.key}",
            f"  bucket_label: {general.label}",
            f"  description: {general.description}",
            "  common_checks:",
        ]
        for item in general.common_checks:
            lines.append(f"    - {item}")

        checks = enhancement.get("checks", [])
        red_flags = enhancement.get("red_flags", [])
        public_info_candidates = enhancement.get("public_info_candidates", [])

        if checks:
            lines.append("  industry_enhancement_checks:")
            for item in checks:
                lines.append(f"    - {item}")

        if red_flags:
            lines.append("  red_flags:")
            for item in red_flags:
                lines.append(f"    - {item}")

        if public_info_candidates:
            lines.append("  public_info_candidates:")
            for item in public_info_candidates:
                lines.append(f"    - {item}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def build_step3_prompt(
    *,
    step1_text: str,
    bp_text: str,
    industry: str,
    selected_buckets: List[str],
    external_context: Optional[str] = None,
    project_structure: Optional[Dict[str, Any]] = None,
) -> str:
    selected_bucket_labels = []
    for bucket_key in selected_buckets:
        general = get_general_bucket(bucket_key)
        selected_bucket_labels.append(f"{bucket_key}: {general.label}")

    # 格式化 project_structure
    if project_structure:
        project_structure_text = json.dumps(
            project_structure,
            ensure_ascii=False,
            indent=2,
        )
    else:
        project_structure_text = "（未提供）"

    return PROMPT_TEMPLATE.format(
        step1_text=step1_text[:6000],
        bp_text=bp_text[:12000],
        project_structure_text=project_structure_text,
        external_context=(external_context or "无"),
        selected_bucket_labels="\n".join(f"- {x}" for x in selected_bucket_labels),
        bucket_specs=build_bucket_specs(industry, selected_buckets),
    )
