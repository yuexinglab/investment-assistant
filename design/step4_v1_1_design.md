# Step4 v1.1 设计文档

> 版本：v1.1（v1.0 基础上增加硬约束、source_trace、去重合并三项）
> 原则：设计先于代码，只做设计，不写实现

---

## 0. 定位与硬约束（新增）

### 0.1 角色定位

Step4 是**决策缺口的翻译层**，不是判断层。

```
Step1 → 投不投的判断（人形）
Step2 → 外部约束的判断（外部逻辑）
Step3 → 包装识别的判断（叙事分析）

Step4 → 把上述判断 翻译成 可执行的会议问题
         不产生新判断，不评价 BP，不发明投资观点
```

### 0.2 硬约束（不可违反）

| 约束 | 说明 |
|------|------|
| **不产生新判断** | Step4 不得输出"这家公司技术不行"等独立结论 |
| **不发明 gap** | gap 必须在 Step1/Step2/Step3 中有明确来源 |
| **不创造 good_answer** | good_answer 的标准必须来自 Step1/Step2/Step3 的判断标准 |
| **原文引用** | 每个 gap 的 why_it_matters 必须引用来源字段原文 |
| **禁止泛化** | 不能写"需要核实技术壁垒"——必须精确到具体是哪项技术的哪个说法 |

### 0.3 违反硬约束的示例

| ❌ 违规 | ✅ 合规 |
|--------|--------|
| `"gap": "技术壁垒可能不高"` | `"gap": "BP称TransportAGI为端到端大模型，但外部约束指出感知/规划技术均为行业通用技术"` |
| `"why_it_matters": "需要核实技术壁垒"` | `"why_it_matters": "技术壁垒是估值叙事的核心，一旦壁垒不成立，估值逻辑崩溃（来源：Step2 step1_external_check.caution[0]）"` |
| `"good_answer": "有技术壁垒"` | `"good_answer": "有XX场景下的实际运营数据，里程数超过XX万公里，感知延迟低于XX毫秒"` |

---

## 1. 输入重组

```
Step4 输入：
├── Step1
│   ├── stance / company_essence
│   ├── red_flags
│   └── must_ask_questions
│
├── Step2
│   ├── step1_external_check
│   │   ├── decision_blockers  → P0
│   │   ├── caution            → P1
│   │   └── contradict          → P1
│   └── information_resolution
│       └── decision_blockers  → P0
│
└── Step3
    ├── consistency_checks (contradict/uncertain)  → P2
    ├── tensions
    │   ├── type=external_vs_bp   → P1
    │   └── type=step1_vs_bp     → P1
    ├── overpackaging_signals     → P2
    └── summary                   → 叙事错位判断
```

---

## 2. 优先级体系（P0/P1/P2/P3）

| 优先级 | 来源 | 含义 | 最大数量 |
|--------|------|------|----------|
| P0 | Step2 `decision_blockers`（任一层） | 投不投的绝对前提，不解决不讨论其他 | 1-2 个 |
| P1 | Step2 caution/contradict **且** Step3 tensions/packaging **同向** | 外部约束与包装信号双重指向同一问题 | 2-3 个 |
| P2 | Step3 `consistency_check`（contradict/uncertain） | BP叙事内部存在漏洞，需现场核实 | 2-3 个 |
| P3 | Step1 `red_flags` / `must_ask_questions` | 常规尽调项，不影响核心决策 | 1-2 个 |

**为什么需要 Step2 + Step3 同向才进 P1**：
单独来自 Step2 的 caution 是"外部逻辑认为需要注意"，单独来自 Step3 的 packaging 是"BP叙事有包装"。两者同时指向同一问题，说明有独立分析链路汇聚——这是真正的风险叠加，不是单一来源的过度解读。

---

## 3. 输出结构（最终版）

```json
{
  "decision_gaps": [
    {
      "gap_id": "gap_p0_1",
      "gap": "（精确描述：BP某具体说法 vs 外部约束/内部矛盾）",
      "priority": "P0",
      "source": ["step2"],
      "source_trace": [
        {
          "step": "step2",
          "field": "step1_external_check.decision_blockers",
          "id_or_index": "info_resolution",
          "quoted_content": "（原文引用，保留关键数值/术语）"
        }
      ],
      "why_it_matters": "（引用原文，说明这个判断对投不投意味着什么）",
      "question_to_ask": "（具体可问，不是泛泛的'核实技术壁垒'）",
      "good_answer": "（具体标准，精确到数字/合同/数据点）",
      "bad_answer": "（具体特征，精确到'没有XX'或'只有YY'）",
      "go_criteria": "（满足哪些条件可以继续推进）",
      "no_go_criteria": "（满足哪些条件直接暂停）"
    },
    {
      "gap_id": "gap_p1_1",
      "gap": "（当 Step2 caution/contradict + Step3 packaging 同向时）",
      "priority": "P1",
      "source": ["step2", "step3"],
      "source_trace": [
        {
          "step": "step2",
          "field": "step1_external_check.caution",
          "id_or_index": "0",
          "quoted_content": "（Step2 原文）"
        },
        {
          "step": "step3",
          "field": "overpackaging_signals",
          "id_or_index": "0",
          "quoted_content": "（Step3 原文）"
        }
      ],
      "why_it_matters": "（说明为什么 Step2 和 Step3 指向同一问题意味着更大风险）",
      "question_to_ask": "...",
      "good_answer": "...",
      "bad_answer": "...",
      "go_criteria": "...",
      "no_go_criteria": "..."
    },
    {
      "gap_id": "gap_p2_1",
      "gap": "（Step3 内部叙事矛盾）",
      "priority": "P2",
      "source": ["step3"],
      "source_trace": [
        {
          "step": "step3",
          "field": "consistency_checks",
          "id_or_index": "0",
          "quoted_content": "（原文）"
        }
      ],
      "why_it_matters": "...",
      "question_to_ask": "...",
      "good_answer": "...",
      "bad_answer": "...",
      "go_criteria": "...",
      "no_go_criteria": "..."
    },
    {
      "gap_id": "gap_p3_1",
      "gap": "（Step1 通用尽调项）",
      "priority": "P3",
      "source": ["step1"],
      "source_trace": [
        {
          "step": "step1",
          "field": "must_ask_questions",
          "id_or_index": "0",
          "quoted_content": "（原文）"
        }
      ],
      "why_it_matters": "...",
      "question_to_ask": "...",
      "good_answer": "...",
      "bad_answer": "...",
      "go_criteria": "...",
      "no_go_criteria": "..."
    }
  ],

  "meeting_question_path": {
    "opening_questions": [
      {
        "purpose": "验证基本业务假设，同时自然引入核心问题",
        "question": "...",
        "source": "P1 或 P2",
        "listen_for": "答案与 BP 描述是否一致"
      }
    ],
    "deepening_questions": [
      {
        "purpose": "深入 P1 核心风险",
        "leading_question": "带着 Step2 + Step3 同向的发现提问",
        "follow_up": "连续追问，逼近具体数字/合同/数据",
        "trap": "设置一个 BP 叙事中的陷阱问题，验证真实性",
        "source": "P1"
      }
    ],
    "trap_questions": [
      {
        "purpose": "揭示 P0 红线问题",
        "question": "直接问 P0 decision_blocker 对应的核心问题",
        "if_avoided": "说明 BP 对该问题没有合理答案",
        "source": "P0"
      }
    ]
  },

  "decision_summary": {
    "top_3_must_know": ["必须通过这3个问题来建立或推翻估值叙事"],
    "meeting_goal": "..."
  }
}
```

---

## 4. source_trace 详细规范（新增）

### 4.1 为什么需要 source_trace

没有 source_trace 的 gap 是"无来源gap"——这违反了硬约束。
source_trace 让每个 decision_gap 可以被追溯到原始数据，确保：

1. **可审计**：投资人可以回查原始判断来源
2. **可验证**：不同时间跑 Step4，source_trace 一致则 gap 应一致
3. **防伪造**：Step4 不能凭空发明 gap

### 4.2 字段路径规范

#### Step1 字段路径

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `red_flags` | 列表 | 每条是独立来源 |
| `must_ask_questions` | 列表 | 每条是独立来源 |
| `company_essence` | 字符串 | 直接引用 |
| `stance` | 字符串 | 直接引用（但不直接产生 gap） |

#### Step2 字段路径

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `step1_external_check.decision_blockers` | 列表 | 索引对应 |
| `step1_external_check.caution` | 列表 | 索引对应 |
| `step1_external_check.contradict` | 列表 | 索引对应 |
| `information_resolution.decision_blockers` | 列表 | 索引对应 |
| `information_resolution.potential_inconsistencies` | 列表 | 索引对应 |

#### Step3 字段路径

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `consistency_checks` | 列表 | 索引对应，status=contradict/uncertain 进 P2 |
| `tensions` | 列表 | 索引对应，type=external_vs_bp/step1_vs_bp 进 P1 |
| `overpackaging_signals` | 列表 | 索引对应，进 P2 |
| `summary` | 字符串 | 叙事错位判断，用于 why_it_matters 补充说明 |

### 4.3 quoted_content 规范

每个 source_trace 必须包含被引用字段的原文，字数不限，但必须保留：

- **关键术语**（如"代运营"、"全栈自研"、"IGBT"）
- **关键数值**（如"20万台套"、"1亿元"、"1%渗透率"）
- **判断性词汇**（如"caution"、"contradict"标签）

```
# 合规示例
"quoted_content": "代运营模式存在资金门槛，项目制交付与运营制交付的边界不清晰"

# 违规示例（截断了关键信息）
"quoted_content": "代运营模式..."
```

---

## 5. Gap 合并/去重规则（新增）

### 5.1 为什么要合并

同一物理问题可能被多个步骤独立识别：

```
Step2 decision_blockers → "代运营需要自持车辆，资金规模不明确"
Step3 overpackaging      → "BP声称轻资产代运营，但代运营本质是重资产运营"
Step1 red_flags         → "商业模式待确认"
```

三条来源指向同一问题（代运营模式本质），必须合并为 **一个** decision_gap。

### 5.2 合并检测规则

**触发条件**（满足任一即检测为同一 gap）：

| 规则类型 | 检测逻辑 | 示例 |
|---------|---------|------|
| **关键词重叠** | gap 描述共享 ≥1 个核心实体词 | "代运营" + "车辆" 同时出现 |
| **问题域重叠** | 指向同一个 BP 说法 | 同一句话被 Step2 和 Step3 同时引用 |
| **决策影响重叠** | good_answer / bad_answer 的判断标准相同 | 都要求"有车辆租赁合同" |

**判定流程**：

```
1. 穷举所有 gap 对
2. 对每对 gap，运行合并检测
3. 如果检测为"同一问题"：
   a. 优先级取 MAX（P0 > P1 > P2 > P3）
   b. source_trace 保留所有来源（去重）
   c. gap 描述取最精确/最长版本
   d. question_to_ask 取最高优先级来源的表述
   e. good_answer/bad_answer 取最严格标准
4. 合并后删除被吸收的 gap
```

### 5.3 合并后 source_trace 示例

```json
{
  "gap_id": "gap_p1_1",
  "gap": "代运营模式的资金规模和单位经济模型未在 BP 中明确说明",
  "priority": "P1",
  "source": ["step2", "step3", "step1"],
  "source_trace": [
    {
      "step": "step2",
      "field": "information_resolution.decision_blockers",
      "id_or_index": "0",
      "quoted_content": "代运营模式存在资金门槛，项目制交付与运营制交付的边界不清晰"
    },
    {
      "step": "step3",
      "field": "overpackaging_signals",
      "id_or_index": "0",
      "quoted_content": "BP声称轻资产代运营，但代运营本质是重资产运营，商业叙事与业务实质存在错位"
    },
    {
      "step": "step1",
      "field": "red_flags",
      "id_or_index": "0",
      "quoted_content": "商业模式待确认"
    }
  ],
  "why_it_matters": "代运营模式是该项目估值叙事的核心（Step2: 代运营边界不清晰 → 估值基础不稳；Step3: BP轻资产叙事与实际重资产矛盾 → 包装信号），如果模式本质是项目制，估值逻辑需要重新构建（Step1: 商业模式待确认）",
  "question_to_ask": "代运营模式中，车辆是自持还是租赁？如果是自持，这一轮融资够买多少台？单台盈亏平衡需要跑多少里程？",
  "good_answer": "已锁定XX台车辆租赁合同（附合同编号），租金锁定X年，IRR超过XX%，最快XX个月回本",
  "bad_answer": "还在和物流公司谈，车辆成本由客户承担（无具体数字，无合同，无单位经济模型）",
  "go_criteria": "有车辆来源 + 有单位经济模型 + 有客户合同 + 有回本测算",
  "no_go_criteria": "没有具体数字，或依赖尚未锁定的客户承诺，或自持车辆数量超出本轮融资规模"
}
```

### 5.4 未合并的 gap 数量预期

合并后，每个项目预期 gap 总数：

| 项目 | 预期 gap 数 | 说明 |
|------|------------|------|
| A1 | 3-4 个 | 技术壁垒 + 代运营 + 客户关系 + 团队 IP |
| A2 | 3-4 个 | 技术优势未验证 + 客户意向无合同 + 量产计划无数据 + 教授IP归属 |
| C1 | 3-4 个 | 芯片外购≠全产业链 + 装车量≠收入 + 客户关系项目制 + SiC量产无验证 |

---

## 6. A1/A2/C1 具体 gap 推演（示例，非实验结果）

> 以下是设计阶段的示例推演，实际 gap 以实验为准。

### 6.1 A1（智能驾驶代运营）

**Step2 来源**（v2.2.2）：

```
decision_blockers:
  - "代运营模式存在资金门槛，项目制交付与运营制交付的边界不清晰"
  - "感知/规划技术均为行业通用技术，技术壁垒论证不充分"

step1_external_check:
  caution: ["tech_barrier caution: 1", "commercialization caution: 2"]
  caution_summary: "A1 mixed项目，需关注tech_barrier和commercialization双重验证"
```

**Step3 来源**（v3）：

```
overpackaging_signals:
  - type: "tech_overstatement", claim: "TransportAGI/端到端大模型", gap: "技术优势未经验证"
  - type: "future_as_present", claim: "代运营行业首次提出且业绩领先", gap: "无合同证明"

tensions:
  - type: "external_vs_bp", step2_field: "tech_barrier_caution", gap: "技术壁垒低 vs BP叙事"
```

**推演合并结果**：

| gap_id | 来源合并 | 优先级 | gap |
|--------|---------|--------|-----|
| gap_p0_1 | Step2 `decision_blockers[0]` + Step3 `overpackaging[1]` + Step1 | P0 | 代运营模式：BP声称轻资产，但实际需要重资产运营，且无资金规模说明 |
| gap_p1_1 | Step2 `decision_blockers[1]` + Step3 `overpackaging[0]` + Step2 `tech_barrier_caution` | P1 | 技术壁垒：BP声称TransportAGI为端到端大模型，但外部约束指出感知/规划均为行业通用技术 |
| gap_p2_1 | Step3 `tensions[0]` | P2 | BP叙事中技术优势与外部约束的技术壁垒评估存在矛盾 |
| gap_p3_1 | Step1 `must_ask_questions` | P3 | 教授IP归属、车辆运营数据、港口客户关系 |

---

### 6.2 A2（港口自动驾驶）

**Step2 来源**（v2.2.2）：

```
step1_external_check:
  caution: ["caution: 1", "commercialization caution: 1"]
  caution_summary: "A2 mixed项目"
```

**Step3 来源**（v3）：

```
overpackaging_signals:
  - type: "cooperation_as_revenue", claim: "北汽/华为/广汽", gap: "无合同无收入"
  - type: "future_as_present", claim: "2028量产计划", gap: "无生产数据"

tensions:
  - type: "step1_vs_bp", step1_field: "red_flags", gap: "技术与市场预测过于乐观"
```

**推演合并结果**：

| gap_id | 来源合并 | 优先级 | gap |
|--------|---------|--------|-----|
| gap_p1_1 | Step2 `caution` + Step3 `overpackaging[0]` + Step3 `tensions[0]` | P1 | 客户合作：BP声称与北汽/华为/广汽合作，但无合同无收入，Step2 caution指出商业化验证不足 |
| gap_p2_1 | Step3 `overpackaging[1]` | P2 | 量产验证：2028量产计划展示为能力，但无生产资质/产能数据/客户承诺 |
| gap_p3_1 | Step1 `red_flags` | P3 | 教授IP归属、技术团队规模 |

---

### 6.3 C1（IGBT/SiC模块）

**Step2 来源**（v2.2.2）：

```
step1_external_check:
  caution: ["caution: 1"]
  caution_summary: "C1 mixed项目，需关注模块/电控特征"
```

**Step3 来源**（v3）：

```
overpackaging_signals:
  - type: "tech_as_capability", claim: "全产业链/SiC量产", gap: "IGBT/SiC芯片依赖外购"
  - type: "platform_narrative", claim: "多款标准化产品", gap: "实际定制化项目交付"

tensions:
  - type: "external_vs_bp", step2_field: "caution", gap: "模块/电控本质 vs BP全产业链叙事"
```

**推演合并结果**：

| gap_id | 来源合并 | 优先级 | gap |
|--------|---------|--------|-----|
| gap_p1_1 | Step2 `caution` + Step3 `overpackaging[0]` + Step3 `tensions[0]` | P1 | 产业链叙事：BP声称全产业链，但IGBT/SiC芯片依赖外购，Step2 caution指出本质是模块/电控 |
| gap_p2_1 | Step3 `overpackaging[1]` | P2 | 产品平台：BP声称多款标准化产品，实际定制化项目交付，收入规模与装车量不匹配 |
| gap_p3_1 | Step1 `must_ask_questions` | P3 | 客户关系稳定性、SiC量产验证 |

---

## 7. meeting_question_path 编排规则

### 7.1 问题编排原则

- **P0 放 trap_questions**：不作为开场，因为一旦被问可能会改变后续氛围
- **P1 放 deepening_questions**：在破冰后深入，用 P1 验证 BP 叙事的核心
- **P2 放 deepening_questions**：与 P1 交叉追问
- **P3 放 opening_questions**：用 P3 作为破冰话题，因为它最安全

### 7.2 问题数量上限

| 类型 | 上限 |
|------|------|
| opening_questions | 2 个 |
| deepening_questions | 4 个（P1+P2） |
| trap_questions | 2 个（P0） |

### 7.3 trap 问题设计原则

P0 trap 问题必须满足：
1. **直接问**：不能绕弯子，直接问 decision_blocker 的核心
2. **有预判**：设计人知道这个问题被回避或被模糊回答意味着什么
3. **可执行**：如果被回避，可以追问"那能不能给我看合同/数据/邮件"

---

## 8. 设计决策记录

| 决策 | 理由 | 替代方案 |
|------|------|---------|
| Step4 不产生新判断 | 防止 Step4 污染判断层，每层各司其职 | 允许 Step4 补充判断（被否决：职责不清） |
| P1 需 Step2+Step3 同向 | 双重信号才是真正风险叠加 | 单独来源进 P1（被否决：信号不够强） |
| source_trace 必须含 quoted_content | 可审计、可追溯，防止凭空发明 gap | 只写字段路径（不够：无法验证原文） |
| gap 合并取最高优先级 | 确保 P0 永远被识别为 P0 | 取平均优先级（被否决：P0 稀释） |
| trap 问题不作为开场 | P0 问题需要铺垫，直接问可能被防备 | 直接问 P0（被否决：信息质量下降） |
