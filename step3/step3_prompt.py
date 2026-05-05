from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from step3.bucket_registry import get_general_bucket
from step3.industry_loader import load_industry_enhancements


PROMPT_TEMPLATE = """你现在是 Step3：行业校准层。

你的任务不是反驳 Step1，也不是总结 BP，而是：

👉 基于 Step1 的初步判断，从"行业外部视角"校准这个项目，
并输出"投资决策需要进一步确认的关键问题"。

---

【当前项目输入，必须优先依据这些内容分析】

【Step1 初步判断】
{step1_text}

【BP 原文】
{bp_text}

【project_structure 仅作参考，可能有噪音；若与 Step1/BP 冲突，以 Step1 和 BP 为准】
{project_structure_text}

【行业桶参考】
{bucket_specs}

【最终输出 bucket 硬约束】
无论 selected_buckets / bucket_specs 传入什么，Step3 最终 selected_buckets 必须固定输出以下六项：

1. 商业模式与收入结构
2. 产业链与价值层级
3. 客户购买驱动
4. 竞争格局与替代方案
5. 关键成功要素
6. 常见投资误判

bucket_outputs 也必须围绕这六项输出。
禁止把 tech_barrier / customer_value / commercialization / expansion_story / team_credibility 作为最终 bucket_key 输出。
这些旧 bucket 只能作为内部参考，不得出现在 selected_buckets 或 bucket_outputs.bucket_key 中。

【外部补充信息】
{external_context}

硬性要求：
1. 所有公司定位、产业链位置、收入模式判断，必须优先基于 Step1 和 BP 原文。
2. project_structure 只能作为参考，不能覆盖 Step1/BP。
3. 如果 project_structure 与 Step1/BP 冲突，必须忽略 project_structure。
4. 不要使用历史项目内容或旧 case 信息。

---

【第一部分：行业校准（投资视角）】

请基于 Step1 判断该项目所属行业/赛道，从投资经理视角回答：

1. 行业如何赚钱（核心商业模式）
- 收入来源是什么？（产品销售 / 项目制 / 订阅 / 平台抽成等）
- 毛利结构大致如何？（高毛利技术 / 低毛利供应链）

2. 产业链与价值层级
- 行业分为哪些层级？
- 哪一层价值最高？哪一层最竞争激烈？
- 该类公司通常处于哪一层？

3. 客户为什么购买（真实驱动）
- 客户核心决策因素是：价格 / 性能 / 可靠性 / 关系 / 政策 / 替代进口？
- 是刚需还是可选？

4. 竞争格局与替代方案
- 主要竞争对手是谁？（龙头 / 新玩家 / 大厂）
- 客户不用它，可以用谁？（竞品 / 自研 / 其他技术路径）

5. 行业关键成功要素
- 在这个行业中，决定公司能否做成的关键能力是什么？（技术 / 渠道 / 产能 / 认证 / 资金等）

6. 常见投资误判（非常重要）
- 投资人最容易看错什么？
- 哪些叙事最容易被高估？（例如：把供应链当平台、把项目当产品等）

---

【第二部分：隐式校准 Step1】

不需要系统化输出 Step1 哪些对/错。

你只需要把行业外部视角下发现的关键偏差，转化为：

- **tensions**：公司当前定位 vs BP/Step1 叙事之间的张力
- **still_unresolved**：必须进一步验证的关键问题

---

【第三部分：转化为决策缺口（供 Step4 使用）】

请输出 3–5 个"必须在投资人会议中确认的问题"，写入 still_unresolved。

要求：

1. 每个问题必须：
- 直接影响投资决策
- 不是泛信息收集问题

2. 每个问题必须说明：
- 为什么重要（影响哪一个核心判断）
- 如果答案不同，将如何改变投资判断

3. still_unresolved 必须输出 3–5 条，每条都必须是投资决策问题，优先包括：
- 真实收入/商业模式是否成立
- 公司定位是否被高估
- 客户是否真实付费/复购
- 技术优势是否能转化为商业壁垒
- 量产/交付/毛利/现金流等关键经营数据

---

【必须输出：公司类型判断】（最重要）

请用一句话明确判断：

👉 该公司当前最可能属于哪一类公司（**只能选一个主类型**）：

- 材料 / 设备 / 整机 / 项目制 / 平台 / 服务

并说明原因（不超过50字）。

建议将判断写入 `tensions`，也可作为总结段落输出。

---

【公司定位校准（必须输出）】

在行业校准之后，请补充一个"公司定位校准"小节，要求基于行业外部视角回答：

1. 当前业务定位：
这家公司当前最像哪类玩家？请用自然语言判断，不要强行套固定标签。

【硬约束：定位判断必须基于主营产品/收入证据】
- 公司定位判断必须优先依据 Step1 和 BP 中明确出现的主营产品/服务、收入来源和交付对象。
- 禁止在没有明确证据时，把项目归为"整机/硬件/平台/设备"等类型。
- 如果主营产品是材料、化学品、分子筛、催化剂、原料、工艺包，则应优先按"材料/工艺应用/项目制交付"框架判断，而不是整机硬件框架。
- 如果主营产品是设备、仪器、产线，则按"设备"框架判断。
- 如果收入来自项目交付/工程服务，则按"项目制"框架判断。
- 如果收入来自持续服务/订阅/运维，则按"服务"框架判断。

2. 产业链位置：
它位于该行业价值链的哪一层？上游/中游/下游/平台/运营/服务等均可，但必须结合BP和Step1说明原因。

3. 价值层级判断：
该位置在行业中的价值高低如何？主要体现在毛利、壁垒、议价权、可复制性中的哪些方面？

4. 定位与叙事落差：
公司当前实际定位，是否低于BP或Step1中的高估值叙事？例如：
- 当前是产品销售，但讲平台
- 当前是项目制，但讲标准化
- 当前是材料/部件，但讲系统/生态
- 当前是整机，但讲底层基础设施

5. 最需要验证的定位问题：
为了确认公司真实定位，最应该验证哪1-3个问题？

6. 定位校准结论写入要求（强制执行）：

- **tensions 必须输出 2–4 条**，其中至少一条必须是"当前公司定位 vs BP/Step1 高估值叙事"的张力，例如：
  - 当前是硬件销售公司，但BP叙事为平台公司
  - 当前是中试阶段技术公司，但BP叙事为规模化产品公司
  - 当前是项目制交付，但BP叙事为标准化产品销售

- **step1_adjustment_hints 仅作为辅助字段**，不作为核心输出：
  - supported 可以为空或少量输出
  - caution 可以少量输出
  - to_step4 不作为核心输出
  - 核心内容必须进入 still_unresolved 和 tensions

---

【重要约束】

- 不要重复 Step3B 的工作（不要专门做"BP包装识别"）
- 不要泛泛而谈行业，要有"判断感"
- 不要输出与当前项目无关的行业内容
- 所有结论尽量与 Step1 和 BP 有关联
- **所有行业分析必须最终落到该公司：**
  - 不仅描述行业结构
  - 必须明确说明：👉 该公司在行业中的哪一层 / 哪个位置
- 错误示例：`行业分为三层：上游、中游、下游`
- 正确示例：`行业可分为若干价值层，但该公司所在位置必须根据主营产品、收入来源和交付对象判断，不能套用通用行业模板。`
- **Step3B 独立性**：Step3B 只基于 BP、project_structure、user_input、investment_modules 运行，不依赖 Step3 的 still_unresolved / tensions / to_step4。

【硬约束：定位判断必须基于主营产品/收入证据】

- 公司定位判断必须优先依据 Step1 和 BP 中明确出现的主营产品/服务、收入来源和交付对象。
- 禁止在没有明确证据时，把项目归为"整机/硬件/平台/设备"等类型。
- 如果主营产品是材料、化学品、分子筛、催化剂、原料、工艺包，则应优先按"材料/工艺应用/项目制交付"框架判断，而不是整机硬件框架。
- 如果主营产品是设备、仪器、产线，则按"设备"框架判断。
- 如果收入来自项目交付/工程服务，则按"项目制"框架判断。
- 如果收入来自持续服务/订阅/运维，则按"服务"框架判断。

---

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
  "tensions": ["张力描述1（必须包含当前定位 vs 估值叙事落差）", "张力描述2"],
  "step1_adjustment_hints": {{
    "supported": [],
    "caution": [],
    "to_step4": []
  }}

【重要：relation_to_step1 字段取值规则】

你必须严格按照以下规则输出 relation_to_step1，只能输出这三个值之一：

- support    -> 即使语义上是"符合行业常识"、"aligned"、"合理"，也必须写 support
- contradict -> 即使语义上是"需要收缩"、"caution"、"有风险"、"有问题"，也必须写 contradict
- neutral    -> 即使语义上是"补充视角"、"gap"、"missing"、"needs_adjustment"，也必须写 neutral

禁止输出：aligned / caution / gap / missing / needs_adjustment / 任何其他值
只允许输出：support / contradict / neutral

}}"""


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
