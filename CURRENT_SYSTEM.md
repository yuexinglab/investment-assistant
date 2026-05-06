# CURRENT_SYSTEM.md — 当前系统地图（2026-05-06）

> **说明**：本文档只描述"当前真正运行的系统"，不描述理想架构、不描述历史设计。
> 以实际 `import`、函数调用、路由注册为准，不猜测。

---

## 一、当前真实运行入口

### Flask 主入口

| 项目 | 值 |
|------|-----|
| **文件** | `app.py`（项目根目录） |
| **启动方式** | `python app.py` 或 Flask 开发服务器 |
| **当前 active 的 pipeline** | `services/pipeline_v1.py` 的 `run_pipeline_v1()` |

### 关键路由 → 实际调用关系

```
用户上传 BP
  → POST /project/create
  → app.py: create_project() + save_and_parse()
  → 生成项目目录：workspace/{project_id}/
  → 重定向到 /project/{id}/run_pipeline

触发完整流程：
  → POST /project/<id>/run_pipeline
  → app.py 调用 services.pipeline_v1.run_pipeline_v1()
  → 返回 SSE 流式进度

单步触发：
  → POST /project/<id>/run_step/<step>
  → app.py 调用 services.pipeline_v1.run_single_step()
  → 单步执行（step1/step3/step4/step5）

查看结果：
  → GET /project/<id>/result_new
  → app.py 调用 load_pipeline_results() 加载已保存文件
  → 渲染 result_1_0_new.html（5标签展示页）
```

### ⚠️ 重要结论

- **`active_v1/` 目录：完全未被引用，是历史残留，当前系统不运行其中任何代码**
- **`services/v2/` 目录：是 2.0 会后流程，与当前 1.0 流程无关**
- **当前 1.0 流程唯一入口 = `services/pipeline_v1.py`**

---

## 二、1.0 当前完整运行链路

### 调用链（A → B → C）

```
上传 BP（app.py: /project/create）
  │
  ▼
Step0：选择/保存 Profile
  │  文件：services/profile/profile_loader.py
  │  输入：用户选择的 profile_id（默认 neutral_investor）
  │  输出：保存到 {project_dir}/step0/step0.json
  │  衔接：后续步骤通过 load_project_profile(project_dir) 加载
  ▼
Step1：初步业务判断（inline，在 pipeline_v1.py 内）
  │  文件：services/pipeline_v1.py → run_step1()
  │  输入：BP 原文（bp_text）
  │  输出：{project_dir}/step1/step1.txt（纯文本）
  │  衔接：step1_text 传给 Step3 / Step4 / Step5
  ▼
Step3：行业背景分析
  │  文件：step3/step3_service.py（通过 pipeline_v1.py:run_step3() 调用）
  │  辅助：step3/project_structure_detector.py（项目结构检测）
  │  辅助：step3/step3_prompt.py（prompt 构建）
  │  辅助：step3/step3_schema.py（输出 schema）
  │  辅助：step3/bucket_registry.py（行业桶定义）
  │  输入：bp_text + step1_text
  │  输出：{project_dir}/step3/step3.json（结构化 dict）
  │  衔接：step3_json（含 project_structure）传给 Step3B / Step4 / Step5
  ▼
投资思维模块选择（inline，在 pipeline_v1.py 内）
  │  文件：investment_modules/module_loader.py
  │  输入：step3_json 中的 project_structure
  │  输出：investment_modules 列表（传给 Step3B）
  │  衔接：investment_modules 传给 Step3B
  ▼
Step3B：BP 一致性 & 包装识别
  │  文件：step3b/step3b_service.py（通过 pipeline_v1.py:run_step3b() 调用）
  │  输入：bp_text + step3_json.project_structure + investment_modules
  │  输出：{project_dir}/step3b/step3b.json（dict）
  │  衔接：step3b_json 传给 Step4 / Step5
  ▼
Step4：决策缺口分析 + 会前提纲
  │  文件：step4/step4_service.py（通过 pipeline_v1.py:run_step4() 调用）
  │  辅助：step4/step4_internal_service.py（内部 JSON 分析）
  │  辅助：step4/step4_internal_prompt.py / schema.py / parser.py
  │  辅助：step4/step4_brief_service.py（会前提纲生成）
  │  输入：bp_text + step1_text + step3_json + step3b_json + profile（fit_questions）
  │  输出：
  │    - {project_dir}/step4/step4_meeting_brief.md（会前提纲 Markdown）
  │    - {project_dir}/step4/step4_internal.json（内部分析 JSON）
  │    - {project_dir}/step4/step4_scan_questions.json（扫描问题）
  │  衔接：step4_internal + step4_output_full 传给 Step5
  ▼
Step5：会前初步判断（决策收敛）
  │  文件：step5/step5_service.py（通过 pipeline_v1.py:run_step5() 调用）
  │  辅助：step5/step5_prompt.py（prompt 构建，含 profile 注入）
  │  辅助：step5/step5_schema.py（Step5Output schema + to_markdown()）
  │  输入：step1_text + step3_json + step4_internal + step3b_json + profile
  │  输出：
  │    - {project_dir}/step5/step5_decision.md（Markdown，标题"会前初步判断"）
  │    - {project_dir}/step5/step5_output.json（完整 JSON，含 fund_fit + investment_logic）
  │  衔接：完成，更新项目状态为 v1_done
```

### 各步骤输入/输出汇总表

| 步骤 | 核心输入 | 核心输出 | 输出保存位置 |
|------|----------|-----------|--------------|
| Step0 | profile_id（用户选择） | profile dict | `{project}/step0/step0.json` |
| Step1 | bp_text | step1.txt（纯文本） | `{project}/step1/step1.txt` |
| Step3 | bp_text + step1_text | step3.json（含 project_structure） | `{project}/step3/step3.json` |
| 模块选择 | step3.project_structure | investment_modules 列表 | 仅内存，不保存 |
| Step3B | bp_text + project_structure + modules | step3b.json | `{project}/step3b/step3b.json` |
| Step4 | bp_text + step1 + step3 + step3b + profile | step4_meeting_brief.md + step4_internal.json + step4_scan_questions.json | `{project}/step4/` |
| Step5 | step1 + step3 + step4_internal + step3b + profile | step5_decision.md + step5_output.json | `{project}/step5/` |

---

## 三、Step5 当前真实结构（重点）

### 文件职责

| 文件 | 职责 | 状态 |
|------|------|------|
| `step5/step5_schema.py` | 定义 `Step5Output` Pydantic schema + `to_markdown()` 渲染 | ✅ 当前运行 |
| `step5/step5_prompt.py` | 构建 Step5 LLM prompt（含 profile 注入到输入区） | ✅ 当前运行 |
| `step5/step5_service.py` | `run_step5()` 函数：调用 prompt → LLM → schema 解析 | ✅ 当前运行 |
| `step5/test_step5_real.py` | 旧版测试脚本（引用旧字段名） | ⚠️ 废弃，不运行 |
| `step5/test_step5_v2_real.py` | 探索型投资人版本测试脚本 | ⚠️ 废弃，不运行 |

### Step5Output 当前最终字段（7个）

```python
Step5Output:
  ├── core_judgement: CoreJudgement      # 核心判断（one_liner / essence / decision / confidence / core_reason）
  ├── reasons_to_meet: List[ReasonItem]  # 为什么值得继续看
  ├── reasons_to_pass: List[ReasonItem]  # 为什么不投
  ├── key_risks: List[RiskItem]          # 核心风险（来源 Step3B）
  ├── fund_fit: FundFit                  # 基金/Profile 匹配度（含 fit_summary / matched_points / mismatch_or_uncertain_points / required_verifications）
  ├── must_ask_questions: List[QuestionItem]  # 必问问题（来自 Step4 gaps）
  └── investment_logic: InvestmentLogic  # 投资逻辑归因（primary_type / secondary_types / risk_type）
```

### Step5 Markdown 生成方式

1. `step5_service.py` 调用 LLM 返回 `Step5Output` 对象（Pydantic）
2. `pipeline_v1.py` 检查 `hasattr(result, "to_markdown")`，调用 `result.to_markdown()`
3. `to_markdown()` 在 `step5_schema.py` 中定义，输出 Markdown 字符串
4. Markdown 标题为 **"会前初步判断"**（2026-05-05 阶段3B 修改）
5. 不输出"投资逻辑归因"到 Markdown，但 `investment_logic` 字段仍保留在 JSON 中

### fund_fit 当前状态

- ✅ **schema 已定义**：`step5_schema.py` 中 `FundFit` 类 + `Step5Output.fund_fit` 字段
- ✅ **prompt 已注入**：`step5_prompt.py` 中 `build_step5_prompt()` 在输入区加入【Step0 / 基金画像】区块，并在输出格式中要求 `fund_fit`
- ✅ **pipeline 已传参**：`pipeline_v1.py` 中 `run_step5()` 传入 `profile=profile`
- ✅ **Markdown 已渲染**：`to_markdown()` 中"## 4. 和基金匹配度怎么看"展示 `fund_fit` 全字段
- ✅ **已正式接入**，不是实验状态

### Profile 进入 Step5 的完整链路

```
用户选择 profile（或默认 neutral_investor）
  → 保存到 {project}/step0/step0.json（Step0）

pipeline_v1.py:run_pipeline_v1()
  → load_project_profile(project_dir)  ← profile_loader.py
  → 得到 profile dict（含 profile_id / hard_constraints / fit_questions 等）

  → 传给 run_step5(profile=profile)
    → step5_service.py:run_step5(profile=profile)
      → step5_prompt.py:build_step5_prompt(profile=profile)
        → profile 格式化为 profile_text
        → 注入 prompt 输入区【Step0 / 基金画像】
        → LLM 输出时根据 profile 调整判断

  → 同时传给 run_step4(profile=profile 间接通过 fit_questions)
```

---

## 四、Profile 系统

### Profile 文件位置

```
knowledge_base/profiles/fund_profiles/
  ├── neutral_investor.json      # 中性投资人（默认）
  ├── government_fund.json      # 政府产业基金
  ├── vc_fund.json              # VC基金
  ├── industrial_fund.json      # 产业基金
  └── hong_gov_fund_v1.json    # 地方政府版
```

### 当前可用 Profile 清单

| profile_id | 名称 | 状态 |
|------------|------|------|
| `neutral_investor` | 中性投资人 | ✅ 默认 |
| `government_fund` | 政府产业基金 | ✅ 可用 |
| `vc_fund` | VC基金 | ✅ 可用 |
| `industrial_fund` | 产业基金 | ✅ 可用 |
| `hong_gov_fund_v1` | 地方政府版 | ✅ 可用 |

### Profile Loader（唯一 active）

- **文件**：`services/profile/profile_loader.py`
- **核心函数**：
  - `load_profile(profile_id)`：按 ID 加载画像（默认 neutral_investor）
  - `load_project_profile(project_dir)`：从项目目录加载已保存画像（step0/step0.json）
  - `save_project_profile(project_dir, profile)`：保存画像到项目目录
  - `list_fund_profiles()`：列出所有可用画像（供前端选择）
  - `get_fit_questions_for_profile(profile)`：提取 fit_questions（供 Step4 使用）
  - `extract_profile_constraints(profile)`：提取约束结构（供 Step10 使用）

### 各步骤 Profile 使用情况

| 步骤 | 是否使用 | 用途 | 调用方式 |
|------|----------|------|----------|
| Step0 | ✅ 强使用 | 用户选择，保存到 step0.json | `save_project_profile()` |
| Step1 | ⚠️ 弱使用 | 辅助识别项目匹配度 | profile 未直接传入 Step1（inline） |
| Step3 | ⚠️ 中使用 | 生成 profile 相关问题和判断 | `step3_service.py` 中调用 |
| Step3B | ❌ 不使用 | 只做 BP 包装识别 | 不传 profile |
| Step4 | ✅ 中使用 | 追加 profile.fit_questions 到问题列表 | `get_fit_questions_for_profile()` |
| **Step5** | ✅ **已接入** | 基金匹配度判断（fund_fit） | `pipeline_v1.py` → `run_step5(profile=profile)` |
| Step6 | ❌ 禁止使用 | 只提取会议记录事实 | profile_loader.py 注释明确禁止 |
| Step7 | ⚠️ 中使用 | 检查 profile 相关问题是否被回答 | `services/v2/` 中调用 |
| Step10 | ✅ 强使用 | 最终 fit 判断 | `services/v2/` 中调用 |

---

## 五、当前 1.0 已冻结/已稳定部分

### ✅ 已稳定，不建议现在重构

| 模块 | 原因 |
|------|------|
| `app.py` 路由层 | 路由清晰，1.0/2.0 分离明确，运行稳定 |
| `services/pipeline_v1.py` 主流程 | 调用链完整，Step1→3→3B→4→5 串行稳定 |
| `step3/step3_service.py` + `step3_prompt.py` + `step3_schema.py` | 行业校准六桶已稳定，输出结构固定 |
| `step3/project_structure_detector.py` | 项目结构检测逻辑稳定 |
| `step3b/step3b_service.py` | BP 一致性检查逻辑稳定 |
| `step4/step4_service.py` + 内部模块 | 决策缺口分析 + 会前提纲生成稳定 |
| `step5/step5_schema.py` | Step5Output schema 已定型（7字段），`to_markdown()` 刚重构完成 |
| `step5/step5_prompt.py` | profile 注入完成，输出格式稳定 |
| `services/profile/profile_loader.py` | 加载器功能完整，5个 profile 可用 |
| `investment_modules/module_loader.py` | 模块选择逻辑稳定 |

### ⚠️ 实验状态，后续可能变化

| 模块 | 当前状态 |
|------|----------|
| `step5/step5_prompt.py` 的 profile 使用效果 | prompt 已注入 profile，但 LLM 是否"真正用好"需验证 |
| `fund_fit` 字段的实际质量 | schema 已定义，prompt 已要求，但输出质量待验证 |
| Step1（inline） | 当前是 `pipeline_v1.py` 内的简单 prompt，无独立 schema/schema解析，无 profile 传入 |
| `candidate_v1_new/` | 实验版 Step1（detector+llm+general），未接入主流程 |

---

## 六、当前目录中的历史残留/测试文件

### 扫描范围

项目根目录 + 各 step 目录 + services/ + workspace/

---

### A类（当前运行核心 — Active）

这些文件**真正被 import / 调用**，是当前系统的主干：

**入口层**
- `app.py`（Flask 主入口）
- `config.py`（配置：WORKSPACE_DIR / SECRET_KEY 等）

**Pipeline 层**
- `services/pipeline_v1.py`（1.0 主流程编排）
- `services/file_parser.py`（BP 解析：PDF/DOCX → 文本）
- `services/project_manager.py`（项目 CRUD + 元数据管理）
- `services/deepseek_service.py`（DeepSeek API 封装）
- `services/report_generator.py`（报告生成，兼容旧流程）
- `services/feedback.py`（人工反馈系统）

**Step3 层**
- `step3/step3_service.py`
- `step3/step3_prompt.py`
- `step3/step3_schema.py`
- `step3/project_structure_detector.py`
- `step3/bucket_registry.py`
- `step3/industry_loader.py`

**Step3B 层**
- `step3b/step3b_service.py`
- `step3b/step3b_prompt.py`
- `step3b/step3b_schema.py`

**Step4 层**
- `step4/step4_service.py`
- `step4/step4_internal_service.py`
- `step4/step4_internal_prompt.py`
- `step4/step4_internal_schema.py`
- `step4/step4_internal_parser.py`
- `step4/step4_brief_service.py`
- `step4/step4_brief_prompt.py`

**Step5 层**
- `step5/step5_service.py`
- `step5/step5_prompt.py`
- `step5/step5_schema.py`

**Profile 层**
- `services/profile/profile_loader.py`
- `services/profile/__init__.py`

**投资思维模块**
- `investment_modules/module_loader.py`
- `investment_modules/` 下各模块定义文件

**前端层**
- `templates/index.html`
- `templates/new_project.html`
- `templates/project_detail.html`
- `templates/result_1_0_new.html`（1.0 结果页，5标签）
- `templates/project_v2.html`（2.0 结果页）
- `templates/profile_comparison.html`
- `static/` 下相关静态资源

**知识库**
- `knowledge_base/profiles/fund_profiles/*.json`（5个 profile）
- `knowledge_base/` 下其他参考文件

---

### B类（仍可能参考 — Reference）

这些文件**当前不被直接调用**，但包含有价值的逻辑/思路，后续可能参考或合并：

- `step3/example_integration.py`（Step3 集成示例）
- `step4/example_integration.py`（Step4 集成示例）
- `step3b/__init__.py`（可能含初始化逻辑）
- `step5/__init__.py`
- `step3/README.md`（Step3 说明文档）
- `step4/README.md`（Step4 说明文档）
- `prompts/` 目录（历史 prompt 存档，可能参考）
- `archive_branches/` 目录（历史版本快照，如 `step5_before_profile_and_memo_20260505/`）
- `所有的GPT上下文/` 目录（GPT 讨论上下文存档）
- `过程文档+接力文档/` 目录（历史过程文档）

---

### C类（大概率废弃 — Deprecated）

这些文件**没有被 import，也没有被调用**，当前系统不运行它们：

**旧流程/实验代码**
- `active_v1/` 整个目录（无任何文件被 import，完全被 `services/pipeline_v1.py` 取代）
- `services/v2/` 整个目录（2.0 会后流程，与当前 1.0 无关，但属于"下一个版本"）
- `candidate_v1_new/` 目录（实验版 Step1，未接入主流程）

**测试脚本（引用旧字段名，已不适用当前 schema）**
- `step3/test_*.py`（如有）
- `step4/test_step4_v*_real.py`（多个旧版本测试脚本）
- `step4/test_v4_output.txt`
- `step4/test_v4_real_output.txt`
- `step5/test_step5_real.py`（引用旧字段名）
- `step5/test_step5_v2_real.py`（探索型版本测试）

**根目录临时/调试文件（当前工作区）**
- `check_1180.py`
- `check_last.py`
- `check_line_count.py`
- `find_triple.py`
- `show_lines.py`
- `test_char.py` / `test_char2.py` / `test_char3.py` / `test_char4.py` / `test_char5.py`
- `test_docstring.py`
- `test_full_fields.py`
- `test_parse.py`
- `test_real.py`
- `test_simple.py`
- `test_stdout_save.py`
- `shanhai_bp.txt`
- `step3_buckets_implementation.md`
- `temp_read_pipeline.py`
- `v2_package/` 目录
- `done/` 目录
- `echo/` 目录
- `mkdir/` 目录

**workspace/ 中的历史项目**
- `workspace/` 目录下的老项目数据（不属于代码，但属于历史残留数据）

---

## 七、当前建议

### ✅ 不要动的部分（稳定运行）

1. **`app.py` 路由层**：1.0/2.0 分离清晰，不要混在一起
2. **`services/pipeline_v1.py` 主流程**：调用链已稳定，Step1→3→3B→4→5 完整
3. **Step3/3B/4 的 schema 和 service**：输出结构已固定，不要大改
4. **`profile_loader.py`**：功能完整，5个 profile 正常工作
5. **`step5_schema.py` 的 Step5Output 字段定义**：7个字段已定型，fund_fit 已接入

### ⚠️ 可以验证/优化的部分

1. **Step5 的 profile 使用效果**：prompt 已注入，但需跑真实项目验证 LLM 是否真正用好 profile
2. **Step1 无 schema 问题**：当前 Step1 是 inline 纯文本输出，没有结构化 schema，后续可考虑接入 `candidate_v1_new/` 的实验成果
3. **`fund_fit` 输出质量**：跑几个真实项目，看匹配度判断是否合理

### ❌ 不要现在做的

1. **删除 `active_v1/`**：虽然是废弃代码，但属于历史快照，不急着删
2. **删除 `services/v2/`**：这是 2.0 流程，属于下一个版本，不是废弃代码
3. **重构 Step1**：当前 inline 版本虽然简陋，但运行稳定，等 candidate_v1_new 验证成熟后再接入
4. **大规模清理测试文件**：C类文件不影响运行，可以留着，不急着删

---

## 八、一句话总结

> **当前真正运行的是 `app.py` + `services/pipeline_v1.py` 驱动的 1.0 流程（Step1→3→3B→4→5），所有 step 模块在根目录的 `step3/`、`step3b/`、`step4/`、`step5/` 下，profile 系统通过 `services/profile/profile_loader.py` 工作，fund_fit 已正式接入 Step5。**
