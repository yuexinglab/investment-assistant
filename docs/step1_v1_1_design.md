# Step1 v1.1 设计方案（实验版）

## 一、问题诊断

### 当前 Step1 的根本问题

**不是"不够全面"，而是"没有成为唯一判断源头"。**

当前 Step1 输出是纯文本：
```
一、【这家公司本质上是什么 / 不是什么】
二、【初步看法】
三、【需要重点了解的问题】
```

**问题在哪：**

| 症状 | 根因 |
|------|------|
| Step3 说"背景分析"，Step1 也在说"初步判断"，职责重叠 | Step1 没有明确定义"判断什么" |
| Step4 生成问题时，回头读 Step1 的纯文本 | 没有结构化，Step4 很难精准提取 |
| Step5 结论和 Step1 结论可能矛盾 | 没有"唯一源头"，每个 Step 都在独立生成 |
| 项目结构信息分散在 Step1 自由文本和 project_structure_detector | 两个地方都在做"识别"，没有合并 |

---

## 二、设计原则

### 核心原则：Step1 = "第一判断源头"

Step1 的职责是**立判断**，不是"全面分析"。

```
Step1 立判断   →  Step3 校验判断   →  Step4 提问   →  Step5 决策
```

每个后续 Step 的存在前提是 Step1 已经立了判断。后续 Step 要么"验证"、要么"反驳"、要么"深化"，但不能"重新生成"。

### 三不原则

- ❌ **不做全量分析**（现金流/估值/壁垒/可复制性，这些是 Step4/Step5 的事）
- ❌ **不删除 general.py**（它是思考框架，先用起来，再决定如何结构化）
- ❌ **不动 investment_modules**（它在 Step3B 承担"防骗/叙事拆解"，迁移会削弱 Step3B）

### 三可以原则

- ✅ **project_structure_detector 可以进入 Step1**（结构识别是判断的前提，不是判断本身）
- ✅ **general 可以作为 Step1 的思考框架**（不强制全部结构化输出）
- ✅ **Step1 输出 JSON 化**（但只包含 7 个核心字段）

---

## 三、7 个字段设计

### 字段 1：company_essence

**字段定义**
```json
{
  "是什么": "一句话说明公司本质上在做什么",
  "不是什么": ["2-3条，明确划清边界的描述"],
  "confidence": "high | medium | low（对定位的置信度）"
}
```

**来源**
- **Step1 prompt（核心来源）**：定性判断，"是什么/不是什么"本来就是 Step1 的职责
- **project_structure_detector（辅助来源）**：industry_tags 和 business_lines 提供了客观的事实锚点，帮助 Step1 不跑偏

**为什么必须在 Step1**

这是 Step1 最原生的能力，其他 Step 都在此基础上做判断：
- Step3 校验：验证"是什么/不是什么"是否与 BP 事实一致
- Step4 提问：基于"不是什么"生成追问
- Step5 决策：基于"是什么"判断是否适合基金

如果这个字段不在 Step1，后续每个 Step 都要自己理解"公司是什么"，导致判断标准不统一。

---

### 字段 2：business_structure

**字段定义**
```json
{
  "current_business": [
    {
      "name": "业务线名称",
      "description": "一句话说明",
      "confidence": "high | medium | low"
    }
  ],
  "narrative_business": [
    {
      "name": "叙事业务名称",
      "description": "一句话说明",
      "evidence": "BP 中哪个说法暴露这是叙事而非现实",
      "confidence": "high | medium | low"
    }
  ]
}
```

**来源**
- **project_structure_detector（主要来源）**：
  - `detect_business_lines()` → 识别当前业务 vs 叙事业务
  - `detect_business_model_hypotheses()` → 区分 primary/current vs narrative/future
  - 关键字段：`role`（current_business / growth_story / valuation_story）

**为什么必须在 Step1**

投资判断的第一步是"区分现实和叙事"。如果 Step1 不做这件事：
- Step3B 不知道该防什么骗
- Step4 不知道该问"你现在到底靠什么赚钱"
- Step5 可能把叙事当现实来判断

project_structure_detector 的结构化能力（关键词命中、confidence 评分）可以在这里被直接利用，但判断本身仍然是 Step1 的。

---

### 字段 3：revenue_logic

**字段定义**
```json
{
  "current_money_source": "一句话说明当前钱从哪里来",
  "clarity": "clear | vague | unclear（当前收入来源是否清晰）",
  "red_flag_note": "如果不清楚，用一句话说明最可疑的地方"
}
```

**来源**
- **Step1 prompt（核心来源）**：这是投资人的第一反应，"这公司现在到底靠什么赚钱"
- **general.py（参考来源）**：`business_model_checks` 和 `cashflow_checks` 提供了思考维度
- **project_structure_detector（辅助来源）**：`BUSINESS_MODEL_PATTERNS` 中的 current_or_future 标注

**为什么必须在 Step1**

"现在怎么赚钱"是最根本的问题：
- Step3 要校验：BP 说的收入来源和 Step1 判断的是否一致
- Step4 要提问：围绕收入来源的真实性和持续性追问
- Step5 要判断：当前业务能否支撑估值

如果 Step1 没有这个字段，每个 Step 都要自己猜"公司怎么赚钱"，判断会失焦。

**注意：这个字段只要求"一句话"，不是展开分析。**

---

### 字段 4：customer_logic

**字段定义**
```json
{
  "who_pays": "谁在付钱（客户类型）",
  "why_pays": "客户付钱的动机是什么",
  "sustainability": "一次性 | 偶发性 | 持续性（判断依据一句话）"
}
```

**来源**
- **Step1 prompt（核心来源）**：这是投资人天然的疑问，"客户为什么要买"
- **general.py（参考来源）**：`customer_checks` 提供了思考维度

**为什么必须在 Step1**

客户逻辑决定商业模式是否成立：
- 持续性付费 → 好的商业模式
- 一次性付费 → 需要不断找新客户
- 偶发性付费 → 收入不稳定

如果 Step1 没有这个字段，Step4 不知道该问"客户复购率"，Step5 不知道该怎么判断可复制性。

---

### 字段 5：key_judgement

**字段定义**
```json
{
  "statement": "一句话核心判断",
  "reasoning": "一句话说明为什么这么判断",
  "stance": "meet | pass | hold（初步倾向）"
}
```

**来源**
- **Step1 prompt（核心来源）**：这是 Step1 的灵魂，输出的结论必须是一个可追溯的判断
- **general.py（参考来源）**：`general_focus` 中的"判断而不是叙事"原则

**为什么必须在 Step1**

"初步倾向"（meet/pass/hold）是整个流程的北极星：
- Step3 校验：判断是否有事实支撑
- Step4 提问：围绕判断的关键点提问
- Step5 决策：最终决策是否推翻/修正 Step1 的判断

**关键约束：这个字段必须是一句话或一小段，不能展开成长篇分析。**

---

### 字段 6：red_flags

**字段定义**
```json
{
  "flags": [
    {
      "flag": "最不信的一点",
      "reason": "一句话说明为什么不信任",
      "source": "Step1 判断 | BP 内容（这个 flag 是来自哪里）"
    }
  ]
}
```

**来源**
- **Step1 prompt（核心来源）**：投资人的"不对劲"直觉
- **general.py（参考来源）**：`red_flags` 清单提供了思考维度，但不直接照搬
- **project_structure_detector（辅助来源）**：`RISK_PATTERNS` 提供了风险关键词

**为什么必须在 Step1**

"最不信的点"是后续验证的锚点：
- Step3 要校验：这些 flag 是否有事实支撑
- Step3B 要识别：这些 flag 是否是包装信号
- Step4 要提问：围绕这些 flag 追问

**关键约束：只列出 3 个最核心的 flag，不展开分析，每个 flag 一句话。**

---

### 字段 7：must_ask_questions

**字段定义**
```json
{
  "questions": [
    {
      "question": "问题内容",
      "why": "为什么这个问题必须问",
      "related_to": "关联的字段（company_essence | revenue_logic | red_flags | ...）"
    }
  ]
}
```

**来源**
- **Step1 prompt（核心来源）**：投资人拿到 BP 一定会问的问题
- **project_structure_detector（辅助来源）**：`key_uncertainties` 中的 `discriminating_questions` 提供了高质量问题模板
- **general.py（参考来源）**：各维度的思考问题

**为什么必须在 Step1**

这些问题是给 Step4 用的，Step4 需要：
- 知道该问什么（来自 Step1 的判断）
- 知道为什么问（关联到 Step1 的某个判断）
- 知道问题指向什么（关联到 Step1 的某个字段）

如果 Step1 没有这个字段，Step4 生成的问题是"盲问"，不是"有判断支撑的追问"。

**关键约束：3-5 个问题，不要多，每个问题一句话。**

---

## 四、字段来源汇总

| 字段 | 主要来源 | 辅助来源 | 思考框架 |
|------|----------|----------|----------|
| company_essence | Step1 prompt | project_structure_detector (industry_tags) | - |
| business_structure | project_structure_detector | Step1 prompt | - |
| revenue_logic | Step1 prompt | general.py | general/business_model_checks |
| customer_logic | Step1 prompt | general.py | general/customer_checks |
| key_judgement | Step1 prompt | - | general/general_focus |
| red_flags | Step1 prompt | general.py | general/red_flags |
| must_ask_questions | Step1 prompt | project_structure_detector | general/* |

---

## 五、向后兼容方案

### 不改正式 pipeline

Step1 v1.1 作为**实验版本**，不影响现有 pipeline：

1. **保留当前 `run_step1()`**：仍然输出 `step1.txt`，作为兼容
2. **新增 `run_step1_v1_1()`**：输出 `step1_v1_1.json`，用于实验对比
3. **Step3/Step4/Step5 继续读 `step1.txt`**：不感知 v1.1 输出

### 三阶段实施

#### 阶段一：只改 run_step1（实验模式）

```
实验模式：
  bp_text → run_step1_v1_1() → step1_v1_1.json
  
不改变正式流程，Step3/4/5 继续读 step1.txt
```

#### 阶段二：Step3 优先读 v1.1

```
如果 step1_v1_1.json 存在，Step3 优先读它
如果不存在，Step3 回退到读 step1.txt
```

#### 阶段三（可选）：正式替换

```
确认 v1.1 比当前版本更好 → 正式替换 run_step1()
step1.txt 成为历史文件
```

---

## 六、实验设计

### 实验对象

对 A1、A2、C1 三个项目运行：
- `step1_current` → 输出 `step1_current.txt`
- `step1_v1_1` → 输出 `step1_v1_1_structured.json`

### 对比维度

| 维度 | 评估标准 |
|------|----------|
| **更像"投资人第一反应"** | 读起来像有经验的投资人在说话，还是像 AI 在写报告？ |
| **更清晰定义公司本质** | 能否用一句话说清楚"这家公司是什么"？ |
| **更容易生成高质量问题** | must_ask_questions 是否和 red_flags/key_judgement 有逻辑关联？ |
| **是否"过度分析"** | 是否出现了现金流分析、估值计算、壁垒展开等 Step5 才该有的内容？ |
| **是否把未验证内容写死** | 是否把 BP 叙事当成事实判断了？ |

### 输出文件

- `step1_current.txt`：当前版本的纯文本输出
- `step1_v1_1_structured.json`：v1.1 版本的 JSON 输出
- `compare_step1_v1_1.md`：对比分析
- `summary.md`：实验结论

---

## 七、实现代码

### Step1 v1.1 prompt 设计

```python
STEP1_V1_1_SYSTEM = (
    "你是一位资深投资人。"
    "你的任务是对 BP 形成第一判断：轻量、精准、有观点。"
    "风格：像投资人在脑中快速过项目一样，不要写成分析报告。"
    "约束：每个字段一句话或一小段，不要展开分析。"
)

STEP1_V1_1_USER_TEMPLATE = """
你刚刚拿到一份 BP，请快速形成以下 7 个判断：

【字段 1】company_essence（公司本质）
- 是什么：用一句话说明公司本质上在做什么
- 不是什么：2-3 条，明确划清边界的描述

【字段 2】business_structure（业务结构）
- 当前业务：现在在做的、能产生收入的业务（列出名称 + 一句话说明）
- 叙事业务：听起来很宏大、但还没验证的业务（列出名称 + 证据）

【字段 3】revenue_logic（收入逻辑）
- 当前钱从哪里来（一句话）
- 来源是否清晰（clear / vague / unclear）

【字段 4】customer_logic（客户逻辑）
- 谁在付钱
- 客户为什么付钱
- 是持续付费还是一次性

【字段 5】key_judgement（核心判断）
- 一句话核心判断
- 为什么这么判断
- 初步倾向：meet / pass / hold

【字段 6】red_flags（红旗）
- 最不信的 3 个点（每个一句话）

【字段 7】must_ask_questions（必问问题）
- 第一轮必须问的 3-5 个问题（每个问题 + 为什么问 + 关联哪个字段）

---
BP 全文：

{bp_text}
"""
```

### Step1 v1.1 输出解析

```python
def run_step1_v1_1(bp_text: str) -> dict:
    """运行 Step1 v1.1，输出结构化 JSON"""
    prompt = STEP1_V1_1_USER_TEMPLATE.format(bp_text=bp_text)
    raw_output = call_deepseek(
        system_prompt=STEP1_V1_1_SYSTEM,
        user_prompt=prompt,
        max_retries=2
    )
    return parse_step1_output(raw_output)
```

输出格式：

```json
{
  "company_essence": {
    "是什么": "一句话说明",
    "不是什么": ["描述1", "描述2"],
    "confidence": "high"
  },
  "business_structure": {
    "current_business": [
      {"name": "...", "description": "...", "confidence": "high"}
    ],
    "narrative_business": [
      {"name": "...", "description": "...", "evidence": "...", "confidence": "low"}
    ]
  },
  "revenue_logic": {
    "current_money_source": "一句话",
    "clarity": "clear",
    "red_flag_note": null
  },
  "customer_logic": {
    "who_pays": "客户类型",
    "why_pays": "付钱动机",
    "sustainability": "持续性"
  },
  "key_judgement": {
    "statement": "一句话核心判断",
    "reasoning": "为什么",
    "stance": "meet"
  },
  "red_flags": {
    "flags": [
      {"flag": "红旗1", "reason": "一句话", "source": "Step1 判断"}
    ]
  },
  "must_ask_questions": {
    "questions": [
      {"question": "问题", "why": "为什么问", "related_to": "revenue_logic"}
    ]
  }
}
```

---

## 八、关键约束清单

| 约束 | 说明 |
|------|------|
| **Step1 只立判断** | 不做全面分析，现金流/估值/壁垒等是 Step4/Step5 的事 |
| **7 个字段之外不扩展** | 实验阶段不加字段，先验证这 7 个是否足够 |
| **每个字段简洁** | 一句话或一小段，不写成长篇分析 |
| **must_ask_questions 要有逻辑关联** | 问题要和 red_flags/key_judgement 有关联，不能乱问 |
| **不删除 general.py** | 它是思考框架，继续保留 |
| **不动 investment_modules** | 它在 Step3B，继续保留 |
| **不改正式 pipeline** | Step3/4/5 继续读 step1.txt |

---

## 九、实验结论验收标准

如果 v1.1 在以下 3 个以上维度优于当前版本，则建议进入阶段二：

1. ✅ 更像"投资人第一反应"
2. ✅ 更清晰定义公司本质
3. ✅ 更容易生成高质量问题
4. ❌ 没有"过度分析"
5. ❌ 没有把未验证内容写死

---

## 十、待确认事项

1. **字段数量**：7 个字段是否足够？是否有遗漏的"必须由 Step1 立的判断"？
2. **字段粒度**：每个字段要求"一句话"是否太严格？某些字段是否需要更丰富的输出？
3. **实验样本**：A1、A2、C1 是否能覆盖足够多样的业务类型？
4. **评估标准**：上述 5 个维度是否完整？是否有其他重要的评估维度？
