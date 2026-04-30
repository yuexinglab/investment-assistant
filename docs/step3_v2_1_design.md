# Step3 重新设计文档

**版本**: v2.1
**日期**: 2026-04-30
**核心原则**: Step3 不能被 BP 叙事污染。Step3 的核心价值是"外部行业/投资逻辑视角"，不是重读 BP 后再分析一遍。

---

## 一、重新定义 Step3 定位

### 1.1 原设计的问题

原 Step3 的问题：
- `bp_text` 作为主要输入（占大量 token），容易导致模型沉浸式重读 BP
- 容易变成"基于 BP 的深度分析"，而不是"外部逻辑校验"
- Step1 的判断容易被 BP 叙事覆盖，而不是被外部行业逻辑校验

### 1.2 新的 Step3 定位

```
Step3 = 外部行业/赛道投资逻辑校验层
```

**核心价值**：用行业常识、投资逻辑、技术商业化逻辑，去校验 Step1 的判断是否站得住脚。

**Step3 不做什么**：
- 不重读 BP 再分析项目
- 不重新定义 company_essence
- 不输出完整投资结论
- 不接受 BP 作为主要判断依据
- **不产生任何新的"公司本质判断"**

**Step3B 做什么**（BP 包装识别层）：
- 识别 BP 内部的不一致
- 识别包装话术和叙事陷阱
- 识别 claim vs evidence 的差距

---

## 二、输入字段（优先级排序）

### 2.1 必须输入（优先级从高到低）

```
1. Step1 v1.2.1 输出（JSON）
   - company_essence
   - business_structure
   - revenue_logic
   - customer_logic
   - key_judgement
   - red_flags
   - must_ask_questions

2. project_structure 结构摘要
   - industry_tags（行业标签）
   - business_lines（业务线 + role）
   - business_model_hypotheses（商业模式假设）
   - risk_buckets（风险桶）
   - structure_summary（系统生成的摘要）

3. bucket / industry knowhow
   - 根据识别到的行业，加载对应的 bucket 定义
   - 包括：common_checks、red_flags、key_questions

4. BP 原文（严格限制）
   - 只在需要核对具体 claim 时使用
   - 需要在 prompt 中明确标注：仅用于核对，不用于推理
```

### 2.2 BP 原文的使用约束

```
【BP 原文使用约束】
BP 原文 = 未经核实的公司主张（claim），不是事实。

BP 原文只能用于：
1. 核对 Step1 中提到的具体 claim 是否与 BP 原文一致
2. 识别 Step1 可能遗漏的 BP 中的 claim

BP 原文不能用于：
1. 重新分析项目本质
2. 替代外部行业逻辑判断
3. 支撑 Step3 的核心结论

如果 BP 原文与外部行业逻辑矛盾，以外部行业逻辑为准。
```

---

## 三、Prompt 结构

### 3.1 Prompt 模板

```
你处于 Step3：外部行业/投资逻辑校验层。

你的任务是：
不是分析项目，而是用"这类项目通常应该怎么看"的外部视角，
去校验 Step1 的判断是否站得住脚。

【核心约束】
- BP 原文 = 未经核实的公司主张，不是事实
- 你的判断依据 = 行业常识、投资逻辑、技术商业化规律
- Step1 = 你的输入，不是你的输出
- 你不能覆盖 Step1，只能reinforce / weaken / needs_verification

【强制约束 - 禁止产生新结论】
- 禁止输出任何新的"公司本质判断"
- 禁止写"这家公司是xxx"或"本质上属于xxx"
- 所有判断必须引用：Step1 中的具体字段，或 external logic
- 你的输出是"校验结果"，不是"新的公司分析"

【BP 原文使用约束】
BP 原文 = 未经核实的公司主张，不是事实。
BP 原文只能用于：核对 Step1 claim 是否与 BP 一致。
禁止用于：重新分析项目、支撑新结论。

============================================
【输入1：Step1 v1.2.1 判断结果】
============================================

company_essence:
{step1.company_essence}

business_structure:
{step1.business_structure}

key_judgement:
{step1.key_judgement}

red_flags:
{step1.red_flags}

============================================
【输入2：project_structure 结构摘要】
============================================

识别行业: {project_structure.industry_tags}

业务线:
{project_structure.business_lines}

商业模式假设:
{project_structure.business_model_hypotheses}

风险桶:
{project_structure.risk_buckets}

============================================
【输入3：bucket/行业 knowhow（强制检查清单）】
============================================

【重要】bucket 不是"参考知识"，而是"强制检查清单"。
对于每个 bucket_key，你必须逐条检查：

1. 是否满足该 bucket 的关键验证点（critical_validation_points）
2. 是否触发该 bucket 的常见失败模式（common_failure_modes）
3. 是否出现该 bucket 的常见包装信号（common_packaging_tells）

并把检查结果写入 external_investment_logic 和 step1_external_check。

{bucket_specs}

============================================
【输入4：BP 原文（严格限制）】
============================================

{bp_text}
[使用约束：仅用于核对 Step1 claim，不用于推理]

============================================
【必须输出的 JSON】
============================================
```

---

## 四、bucket / industry knowhow 如何接入

### 4.1 加载逻辑

```
Step1 v1.2.1 project_structure
    ↓
提取 industry_tags（取 confidence=high 的前3个）
    ↓
加载对应行业的 industry_enhancements.py
    ↓
同时加载 general.py（通用投资逻辑）
    ↓
合并为 bucket_specs
```

### 4.2 bucket_specs 格式

```
【bucket_key: tech_barrier】
标签：技术/壁垒是否成立

行业 Knowhow:
- 这类项目的技术壁垒通常来自：...
- 这类项目常见的包装点：...
- 这类项目最关键的验证指标：...

通用投资逻辑:
- 技术壁垒判断标准：是否落入真实产品、客户验证
- 常见失败点：...

【强制检查项】:
1. [ ] 是否有关键技术的自主知识产权证明？
2. [ ] 是否有头部客户验证（非演示/测试）？
3. [ ] 是否有规模化量产能力？

【bucket_key: customer_value】
...
```

### 4.3 bucket 作为检查器的核心要求

**不再是"提示"，而是"检查清单"**：

对于每个加载的 bucket，必须输出：
1. **critical_validation_points** - 这个 bucket 的关键验证点，该项目满足了多少
2. **common_failure_modes** - 该项目触发了哪些失败模式
3. **common_packaging_tells** - 该项目出现了哪些包装信号

并将这些检查结果**绑定到 Step1 的具体字段**，形成 `step1_external_check` 的 checks。

---

## 五、输出 JSON Schema

### 5.1 完整 Schema（v2.1）

```json
{
  "schema_version": "v2.1",

  // =========================================
  // 1. 外部投资逻辑（external_investment_logic） - 必须绑定 Step1
  // =========================================
  "external_investment_logic": [
    {
      "related_to_step1": "company_essence | revenue_logic | customer_logic | red_flags | key_judgement | business_structure",
      "bucket_key": "tech_barrier | customer_value | revenue_model | market_timing | team_capability",
      "logic_statement": "对于【Step1中的related_to_step1字段：具体内容】，外部行业逻辑通常是...",
      "implication": "这意味着 Step1 的这个判断是 support | caution | contradict",
      "why_it_matters": "如果这个逻辑不成立，会影响什么投资判断"
    }
  ],

  // =========================================
  // 2. Step1 校验（step1_external_check） - 每个检查必须引用 Step1
  // =========================================
  "step1_external_check": {
    "checks": [
      {
        "step1_field": "company_essence | revenue_logic | ...（必须是 Step1 的字段）",
        "step1_claim": "Step1 中的具体判断内容",
        "bucket_key": "tech_barrier（用哪个 bucket 来校验）",
        "external_logic": "外部行业逻辑通常怎么看这个判断",
        "verdict": "support | caution | contradict",
        "reasoning": "判断理由，必须引用行业常识/投资规律/技术商业化逻辑",
        "evidence_source": "行业常识 | 投资规律 | 技术商业化逻辑",
        "confidence": "high | medium | low（对这个校验结论的确信度）"
      }
    ],
    "summary": {
      "support_count": 0,
      "caution_count": 0,
      "contradict_count": 0
    }
  },

  // =========================================
  // 3. 信息解析（information_resolution）
  // =========================================
  "information_resolution": {
    "publicly_resolvable": [
      {
        "question": "问题（必须来自 Step1 must_ask_questions 或 red_flags）",
        "how_to_resolve": "通过什么公开资料/方式可以确认",
        "current_gap": "当前信息缺口"
      }
    ],
    "founder_needed": [
      {
        "question": "问题（必须来自 Step1 must_ask_questions 或 red_flags）",
        "why_founder_only": "为什么只有创始人能回答",
        "importance": "high | medium | low"
      }
    ],
    "decision_blockers": [
      {
        "question": "阻断性问题（必须来自 Step1 red_flags）",
        "why_blocking": "为什么这个问题不解决就无法做决策",
        "can_resolve": "在当前阶段能否解决"
      }
    ]
  },

  // =========================================
  // 4. 张力（tensions） - 必须是结构化冲突
  // =========================================
  "tensions": [
    {
      "type": "current_vs_future | tech_vs_commercial | revenue_vs_valuation | structure_vs_narrative",
      "step1_position": "Step1 对这个张力的立场（引用 Step1 字段）",
      "external_view": "外部视角怎么看这个张力",
      "gap_size": "large | medium | small",
      "investment_implication": "这个张力对投资决策的影响"
    }
  ],

  // =========================================
  // 5. Step1 调整提示（step1_adjustment_hints） - 不允许覆盖 Step1
  // =========================================
  "step1_adjustment_hints": {
    "reinforce": [
      "Step1 中被外部逻辑支持的判断（必须引用 step1_external_check.support）"
    ],
    "weaken": [
      "Step1 中被外部逻辑质疑的判断（必须引用 step1_external_check.caution/contradict）"
    ],
    "needs_verification": [
      "Step1 中需要进一步验证的判断（必须引用 information_resolution）"
    ]
  },

  // =========================================
  // 元信息
  // =========================================
  "meta": {
    "buckets_analyzed": ["tech_barrier", "customer_value"],
    "industry_tags_used": ["自动驾驶", "新能源"],
    "bucket_as_checklist": true,
    "bp_text_used_for": ["claim_verification_only"],
    "external_logic_sources": ["行业常识", "投资规律", "技术商业化逻辑"],
    "new_conclusion_generated": false,
    "step1_fields_covered": ["company_essence", "red_flags"]
  }
}
```

### 5.2 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| external_investment_logic | 是 | **必须绑定 Step1**，每条必须指向 Step1 的具体字段 |
| step1_external_check | 是 | 每个检查必须引用 Step1 字段和 bucket |
| information_resolution | 是 | 问题必须来自 Step1，不能凭空创造 |
| tensions | 是 | 冲突描述必须引用 Step1 立场 |
| step1_adjustment_hints | 是 | 引用 step1_external_check 的校验结果 |
| meta.new_conclusion_generated | 是 | 必须是 false，检测是否产生新结论 |

### 5.3 核心约束（v2.1 新增）

```json
{
  "hard_constraints": {
    "no_new_essence": "禁止输出新的 company_essence 或公司本质判断",
    "must_bind_step1": "external_investment_logic 每条必须 related_to_step1",
    "bucket_as_checklist": "bucket 必须是检查清单，不是参考知识",
    "all_checks_must_cite": "所有校验必须引用 Step1 字段或 bucket"
  }
}
```

---

## 六、与 Step3B 的边界

| 维度 | Step3（外部逻辑校验） | Step3B（BP 包装识别） |
|------|----------------------|----------------------|
| **核心问题** | "这类项目外部怎么看" | "BP 内部有没有自相矛盾" |
| **输入重点** | Step1 + 行业 knowhow | BP 原文 + Step1 |
| **判断依据** | 行业常识、投资规律 | BP 内部一致性 |
| **关注点** | claim 是否符合行业规律 | claim 是否有 evidence 支撑 |
| **输出风格** | 外部视角校验 | BP 内部审计 |
| **允许做的事** | reinforce/weaken/needs_verification | 识别包装话术、不一致、夸大 |
| **不允许做的事** | 重读 BP、重新分析项目、产生新结论 | 替代 Step1、下投资结论 |

### 6.1 流程关系

```
Step1 v1.2.1
    ↓
┌─────────────────────────────────────┐
│           Step3                      │
│  外部行业/投资逻辑校验               │
│  - external_investment_logic（绑定Step1）│
│  - step1_external_check              │
│  - tensions                          │
│  - step1_adjustment_hints           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│           Step3B                     │
│  BP 包装识别                         │
│  - 内部一致性检查                     │
│  - claim vs evidence 差距            │
│  - 包装话术识别                      │
└─────────────────────────────────────┘
    ↓
Step4 / Step5
```

---

## 七、关键技术决策

### 7.1 BP 原文 Token 限制

```
BP 原文建议 Token：≤ 3000
（仅包含 claim 列表，不包含完整叙事）
```

### 7.2 bucket 选择逻辑

```
Step1 v1.2.1 中的 red_flags / must_ask_questions
    ↓
提取关键词 → 映射到 bucket_key
    ↓
选择 top-3 buckets
    ↓
每个 bucket 输出完整的 external_investment_logic + step1_external_check
```

### 7.3 行业 Knowhow 加载

```
1. 从 project_structure.industry_tags 获取高置信度行业
2. 加载对应行业的 industries/*.py
3. 合并 general.py 的通用投资逻辑
4. bucket_specs = 行业 Knowhow + 通用逻辑
```

---

## 八、已知限制与后续迭代

### 8.1 当前限制

- 行业 Knowhow 库还不够丰富（当前只有 advanced_materials, commercial_space, general）
- bucket 定义只有 5 个通用桶，后续需要按行业扩展

### 8.2 后续迭代方向

- 补充更多行业的 industries/*.py
- 扩展 bucket 库，增加行业特定 bucket
- 考虑引入外部数据源（如行业报告摘要）作为 knowhow 补充

---

## 九、附录：v2.0 vs v2.1 差异

| 维度 | v2.0 | v2.1 |
|------|------|------|
| external_investment_logic | 泛化的"这类项目..." | **必须绑定 Step1 字段** |
| 新结论约束 | 无 | **强制禁止，产生新结论=错误** |
| bucket 定位 | "参考知识" | **"强制检查清单"** |
| step1_external_check | 可选引用 | **必须引用 Step1 字段** |
| information_resolution | 可凭空创造问题 | **必须来自 Step1** |
| meta | 无 | **新增 new_conclusion_generated 检测** |

---

## 十、附录：现有 Step3 vs 新 Step3 对比

| 维度 | 旧版 Step3 | 新版 Step3 v2.1 |
|------|-----------|----------------|
| BP 原文定位 | 主要输入 | 仅用于 claim 核对 |
| 判断依据 | BP + 行业逻辑混合 | 纯外部行业/投资逻辑 |
| 输出结构 | bucket_outputs + tensions | external_investment_logic（绑定Step1）+ step1_external_check |
| 核心问题 | "这个 bucket 怎么看" | "这类项目外部怎么看，校验 Step1 的哪些判断" |
| BP 叙事风险 | 高（沉浸式读取） | 低（严格约束） |
| 新结论风险 | 中 | **低（有硬约束）** |
| 与 Step3B 关系 | 混合 | 明确分工 |