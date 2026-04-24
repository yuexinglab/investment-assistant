# Step4 v4：上下文打包 + 两阶段生成

这个版本彻底放弃"单次调用同时输出 internal_json + meeting_brief"的方式，
改成：

1. **context_builder**
   - 从 Step1 / Step3 / BP 中抽取 Step4 真正需要的上下文
   - 不再简单硬截断全文
   - 用关键词语义抽取代替机械截断

2. **step4_internal_service**
   - 只生成 internal_json
   - 只做内部判断，不做人类可读表达
   - 所有关键字段必填（decision_impact, internal_goal, go_if, no_go_if）
   - 内置重试机制，字段不完整自动重试

3. **step4_brief_service**
   - 基于 internal_json + context_pack 生成 meeting_brief_md
   - 只做人类可读的会前提纲
   - 不承担内部推理职责

## 目录

```text
step4/
  __init__.py
  context_builder.py              # 结构化上下文打包
  step4_internal_schema.py        # internal_json 的 schema（必填字段）
  step4_internal_prompt.py        # internal 生成 prompt
  step4_internal_parser.py        # internal JSON 解析
  step4_internal_service.py       # internal 生成服务（含重试）
  step4_brief_prompt.py           # meeting_brief 生成 prompt
  step4_brief_service.py          # meeting_brief 生成服务
  step4_service.py                # 统一编排入口
  example_integration.py          # 集成测试示例
  README.md                       # 本文件
```

## 数据流

```
Step1 + Step3 + BP
        ↓
context_builder.py
        ↓
step4_internal_service.py   →   internal_json  (第一次 LLM 调用)
        ↓
step4_brief_service.py      →   meeting_brief_md  (第二次 LLM 调用)
```

## 输出

`Step4Service.run(...)` 返回：

```python
{
    "context_pack": {
        "step1_core": "...",
        "step3_selected_buckets": [...],
        "step3_key_unknowns": [...],
        "step3_tensions": [...],
        "step3_hints": {...},
        "step3_bucket_points": [...],
        "bp_signals": {
            "revenue_and_growth": "...",
            "customer_and_cooperation": "...",
            "ai_and_platform": "...",
            "new_business": "...",
            "production_and_capacity": "...",
            "technology_and_patents": "..."
        }
    },
    "internal_json": {
        "total_gaps": 3,
        "meeting_strategy": "...",
        "decision_gaps": [
            {
                "gap_id": "G1",
                "priority": "P1",
                "core_issue": "...",
                "from_bucket": "...",
                "why_it_matters": "...",
                "decision_impact": {
                    "positive": "...",
                    "negative": "..."
                },
                "internal_goal": "...",
                "go_if": "...",
                "no_go_if": "...",
                "candidate_questions": [...]
            }
        ],
        "summary": "..."
    },
    "meeting_brief_md": "..."
}
```

## internal_json 验收标准

### 必须满足
- 至少 3 个 gap
- 所有 gap 都有：
  - `priority`
  - `why_it_matters`
  - `decision_impact`（positive + negative）
  - `internal_goal`
  - `go_if`
  - `no_go_if`

### 不允许
- 大面积 null
- 只有 meeting_questions，没有内部判断

## meeting_brief_md 验收标准

### 必须满足
- 普通人一眼能看懂
- 不出现 JSON 字段名
- 读起来像会前提纲，不像分析报告
- 每个主题都有：
  - 主问题
  - 理想信号
  - 危险信号
  - 正面追问
  - 模糊追问

## v4 相比 v3 的核心改进

| 维度 | v3 | v4 |
|------|----|----|
| 架构 | 单次双输出 | 两阶段独立调用 |
| 截断风险 | 高（一次太多） | 低（每次更轻） |
| internal 质量 | 易退化 | 有重试保障 |
| 字段完整性 | 可能有 null | 必填 + 重试 |
| 输入处理 | 硬截断 | 语义抽取 |
