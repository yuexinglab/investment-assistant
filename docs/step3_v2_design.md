# Step3 重新设计文档

**版本**: v2.0
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
【输入3：bucket/行业 knowhow】
============================================

{bucket_specs}

============================================
【输入4：BP 原文（严格限制）】
============================================

{ bp_text }
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

【bucket_key: customer_value】
...
```

---

## 五、输出 JSON Schema

### 5.1 完整 Schema

```json
{
  "schema_version": "v2.0",

  // =========================================
  // 1. 外部投资逻辑（external_investment_logic）
  // =========================================
  "external_investment_logic": {
    "bucket_key": "...",
    "core_investment_thesis": "这类项目核心投资逻辑是什么",
    "critical_validation_points": [
      "这类赛道最关键的验证点1",
      "这类赛道最关键的验证点2"
    ],
    "common_failure_modes": [
      "常见失败点1",
      "常见失败点2"
    ],
    "common_packaging_tells": [
      "常见包装点1",
      "常见包装点2"
    ],
    "key_indicators": [
      "最关键的指标/证据1",
      "最关键的指标/证据2"
    ]
  },

  // =========================================
  // 2. Step1 校验（step1_external_check）
  // =========================================
  "step1_external_check": {
    "bucket_key": "...",
    "checks": [
      {
        "step1_claim": "Step1 中的具体判断",
        "external_logic": "外部行业逻辑通常怎么看",
        "verdict": "support | caution | contradict",
        "reasoning": "判断理由",
        "evidence_source": "行业常识 / 投资规律 / 技术商业化逻辑"
      }
    ]
  },

  // =========================================
  // 3. 信息解析（information_resolution）
  // =========================================
  "information_resolution": {
    "publicly_resolvable": [
      {
        "question": "问题",
        "how_to_resolve": "通过什么公开资料/方式可以确认",
        "current_gap": "当前信息缺口"
      }
    ],
    "founder_needed": [
      {
        "question": "问题",
        "why_founder_only": "为什么只有创始人能回答",
        "importance": "high | medium | low"
      }
    ],
    "decision_blockers": [
      {
        "question": "阻断性问题",
        "why_blocking": "为什么这个问题不解决就无法做决策",
        "can_resolve": "在当前阶段能否解决"
      }
    ]
  },

  // =========================================
  // 4. 张力（tensions）
  // =========================================
  "tensions": [
    {
      "type": "current_vs_future | tech_vs_commercial | revenue_vs_valuation",
      "description": "张力描述",
      "step1_position": "Step1 的立场",
      "external_view": "外部视角怎么看",
      "gap_size": "large | medium | small"
    }
  ],

  // =========================================
  // 5. Step1 调整提示（step1_adjustment_hints）
  // =========================================
  "step1_adjustment_hints": {
    "reinforce": [
      "Step1 中应该被外部逻辑支持的判断"
    ],
    "weaken": [
      "Step1 中被外部逻辑质疑的判断"
    ],
    "needs_verification": [
      "Step1 中需要进一步验证的判断"
    ]
  },

  // =========================================
  // 元信息
  // =========================================
  "meta": {
    "buckets_analyzed": ["tech_barrier", "customer_value"],
    "industry_tags_used": ["自动驾驶", "新能源"],
    "bp_text_used_for": ["claim_verification_only"],
    "external_logic_sources": ["行业常识", "投资规律", "技术商业化逻辑"]
  }
}
```

### 5.2 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| external_investment_logic | 是 | 这类项目外部视角应该怎么看 |
| step1_external_check | 是 | 用外部逻辑校验 Step1 |
| information_resolution | 是 | 把问题分类为公开可解/创始人/决策阻断 |
| tensions | 是 | 识别结构性冲突 |
| step1_adjustment_hints | 是 | 给出 reinforce/weaken/needs_verification |
| meta | 是 | 记录分析过程（用于审计） |

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
| **不允许做的事** | 重读 BP、重新分析项目 | 替代 Step1、下投资结论 |

### 6.1 流程关系

```
Step1 v1.2.1
    ↓
┌─────────────────────────────────────┐
│           Step3                      │
│  外部行业/投资逻辑校验               │
│  - external_investment_logic         │
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
每个 bucket 输出完整的 5 个字段
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

## 九、附录：现有 Step3 vs 新 Step3 对比

| 维度 | 旧版 Step3 | 新版 Step3 v2.0 |
|------|-----------|----------------|
| BP 原文定位 | 主要输入 | 仅用于 claim 核对 |
| 判断依据 | BP + 行业逻辑混合 | 纯外部行业/投资逻辑 |
| 输出结构 | bucket_outputs + tensions | external_investment_logic + step1_external_check |
| 核心问题 | "这个 bucket 怎么看" | "这类项目外部怎么看" |
| BP 叙事风险 | 高（沉浸式读取） | 低（严格约束） |
| 与 Step3B 关系 | 混合 | 明确分工 |
