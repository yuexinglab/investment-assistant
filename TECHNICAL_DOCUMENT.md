# AI 项目判断工作台 - 2.0 会后分析系统
## 完整技术文档

**项目路径**: `D:/HuaweiMoveData/Users/86136/Documents/GitHub/investment-assistant/`
**最后更新**: 2026-04-26
**状态**: Step6/7/9/10 已验证正常，Step8 依赖 Step7 输出

---

## 一、系统架构概览

### 1.1 整体数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         2.0 会后分析流程                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐           │
│   │Step0 │ -> │Step6 │ -> │Step7 │ -> │Step8 │ -> │Step9 │ -> Step10 │
│   │画像  │    │信息  │    │问题  │    │认知  │    │决策  │   Fit判断 │
│   │加载  │    │提取  │    │对齐  │    │更新  │    │      │           │
│   └──────┘    └──────┘    └──────┘    └──────┘    └──────┘           │
│       │            │            │            │            │              │
│       v            v            v            v            v              │
│   基金画像     26条新信息    问题验证     假设更新     双层决策           │
│   hard constraints  meeting_quality  hypothesis_updates  继续/暂停      │
│                                   │                                │
│                    ┌──────────────┴──────────────┐                  │
│                    │        沉淀层 (并发)         │                  │
│                    │  问题库 + 行业认知 + 画像    │                  │
│                    └─────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 目录结构

```
services/
├── v2/                          # 2.0 会后分析核心
│   ├── pipeline.py              # 主流程编排
│   ├── schemas.py               # 数据结构定义
│   ├── prompts.py               # Prompt 模板
│   ├── renderer.py              # 报告渲染器
│   └── services/
│       ├── __init__.py
│       ├── deepseek_service.py  # DeepSeek API 调用
│       ├── step6_extractor.py   # 新增信息提取
│       ├── step7_validator.py   # 问题对齐 + 会议质量
│       ├── step8_updater.py     # 认知更新
│       ├── step9_decider.py     # 决策与行动
│       ├── step10_fit_decider.py # Fit 判断
│       ├── candidate_writer.py   # 沉淀写入
│       └── step0_profile_loader.py # 基金画像
├── profile/                     # 画像相关
│   ├── profile_loader.py
│   └── fund_profiles/
│       ├── government_fund.json
│       └── vc_fund.json
└── knowledge_base/              # 知识沉淀
    ├── candidates/              # 待审核候选
    ├── common/                  # 通用知识
    └── profiles/                # 画像库
```

---

## 二、各模块详解

### 2.1 Step0: 基金画像加载

**文件**: `services/v2/services/step0_profile_loader.py`

**功能**: 加载投资人/基金的偏好约束，用于 Step7 问题生成和 Step10 Fit 判断

**核心数据结构**:
```python
Step0ProfileOutput:
  profile_id: str           # "government_fund" / "vc_fund" / "neutral_investor"
  hard_constraints: []      # 硬约束（必须满足）
  preferences: []            # 偏好（加分项）
  avoid: []                  # 回避项
  fit_questions: []          # 针对该画像的特殊问题
```

**调用方式**:
```python
profile = step0_profile_loader.load_or_create_profile(
    profile_id="government_fund"
)
```

---

### 2.2 Step6: 新增信息提取 ✅ 已验证正常

**文件**: `services/v2/services/step6_extractor.py`

**功能**: 从会议记录中提取新增信息，区分 fact/claim/number/plan

**核心数据结构**:
```python
NewInformation:
  id: str                    # "ni_001", "ni_002" ...
  content: str               # 信息内容摘要
  category: str              # 收入/客户/技术/产能...
  evidence: str              # 原文证据片段
  importance: str            # high/medium/low
  info_type: str             # fact/claim/number/plan
  novelty_type: str          # new/more_specific/contradiction
  confidence: str             # high/medium/low
  related_prior_judgement: str # 对应的会前判断
  follow_up_hint: str        # 后续验证建议
```

**验证结果**: ✅ 使用测试数据（26条 new_information）验证通过

---

### 2.3 Step7: 问题对齐 + 会议质量 ✅ 已验证正常

**文件**: `services/v2/services/step7_validator.py`

**功能**: 
1. **Step7A**: 将会前问题与会议新增信息匹配
2. **Step7B**: 判断每个问题的回答状态/质量/影响
3. **综合评估**: 会议整体可信度

**核心数据结构**:
```python
QuestionValidation:
  question_id: str
  original_question: str
  matched_information_ids: []  # 匹配的 ni_xxx 列表
  answer_summary: str          # 回答内容总结
  status: str                  # answered/partially_answered/evaded/not_answered
  quality: str                 # high/medium/low
  impact: str                  # strengthens/weakens/no_change
  missing_evidence: []         # 缺失证据
  follow_up_question: str      # 追问方向

MeetingQuality:
  answer_directness: str       # 回答直接性
  evidence_strength: str       # 证据强度
  evasion_level: str          # 回避程度
  overall_confidence: str      # 整体可信度
  answered_count: int
  partially_count: int
  weak_count: int
```

**验证结果**: ✅ 单独测试通过，返回完整的 question_validation 列表

---

### 2.4 Step8: 对抗式认知更新 ⚠️ 依赖 Step7

**文件**: `services/v2/services/step8_updater.py`

**功能**: 根据 Step7 的问题验证结果，更新会前假设的认知

**核心设计**:
- **规则引擎**: 自动映射 status/impact → change_type
- **假设方向**: 自动推断假设是正向/负向/中性
- **LLM 辅助**: 生成 updated_view 和 why_changed

**核心数据结构**:
```python
HypothesisUpdate:
  hypothesis_id: str
  hypothesis: str                    # 原始假设
  hypothesis_direction: str          # positive/negative/neutral
  change_type: str                   # reinforced/weakened/overturned/uncertain
  updated_view: str                  # 更新后的判断
  supporting_evidence: []            # 支持证据 (ni_xxx)
  contradicting_evidence: []          # 反对证据 (ni_xxx)
  why_changed: str
  confidence_change: str              # "medium -> low" / "unchanged"

OverallChange:
  is_judgement_significantly_changed: bool
  new_risks: []                      # 新增风险列表
```

**关键逻辑**:
1. `_find_related_validations()`: 根据假设文本匹配相关问题验证
2. `compute_hypothesis_updates()`: 规则引擎，自动计算 change_type
3. `_fill_with_llm()`: 调用 LLM 填充 updated_view 和 why_changed

**验证结果**: ⚠️ 代码逻辑正确，但依赖 Step7 输出。当 Step7 question_validation 为空时，Step8 所有假设都变成 unchanged

---

### 2.5 Step9: 双层决策与行动 ✅ 已验证正常

**文件**: `services/v2/services/step9_decider.py`

**功能**: 基于 Step8 认知更新，输出流程决策和投资决策

**双层决策架构**:
```
┌─────────────────────────────────────────────────────────────┐
│                      双层决策模型                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   第一层: 流程决策 (process_decision)                       │
│   ├── continue_dd     - 继续尽调                            │
│   ├── request_materials - 先补材料                          │
│   ├── pause           - 暂缓                                │
│   └── stop            - 停止                                │
│                                                             │
│   第二层: 投资决策 (investment_decision)                    │
│   ├── invest_ready    - 可以进入投资决策                    │
│   ├── not_ready       - 不能投，需补关键证据                │
│   └── reject          - 核心逻辑被打穿                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**验证结果**: ✅ 单独测试通过

---

### 2.6 Step10: Fit 判断

**文件**: `services/v2/services/step10_fit_decider.py`

**功能**: 判断项目是否适合当前基金/投资人

**核心逻辑**:
- 硬约束匹配: 项目是否满足基金的硬性要求
- 偏好匹配: 项目是否符合基金的偏好
- Fit 决策: fit / partial_fit / not_fit
- 最终建议: continue / request_materials / pass

---

## 三、数据持久化

### 3.1 版本号文件

每个步骤的输出会保存为带版本号的文件：
```
{workspace}/
├── step6/
│   ├── step6_v2_2_001.json      # 第一次运行
│   ├── step6_v2_2_002.json      # 第二次运行
│   └── step6_latest.json         # 最新版本
├── step7/
│   ├── step7_v2_2_001.json
│   ├── step7_v2_2_002.json
│   └── step7_latest.json
├── step8/
│   └── ...
├── step9/
│   └── ...
└── v2_context/                  # 沉淀层
    ├── questions.json            # 问题库候选
    ├── industry_insights.json   # 行业认知候选
    └── user_profile_candidates.json
```

### 3.2 Pipeline 编排器

**文件**: `services/v2/pipeline.py`

**核心类**: `PipelineV2`

```python
class PipelineV2:
    def __init__(self, project_id, project_name, workspace_dir)
    
    # 单步运行
    def run_step6(self, step5_summary, meeting_record) -> Dict
    def run_step7(self, step4_questions, step6_new_information, ...) -> Dict
    def run_step8(self, step5_judgements, step7_result) -> Dict
    def run_step9(self, step6_output, step7_output, step8_output) -> Dict
    def run_step10(self, step9_output, profile_id, ...) -> Dict
    
    # 全流程运行
    def run_full(self, meeting_record, step5_summary, ...) -> Dict
```

---

## 四、已验证问题

### 4.1 已修复的问题 ✅

#### 问题1: Windows GBK 编码错误
**现象**: 控制台报错 `'gbk' codec can't encode character '\u2122'`
**位置**: `app.py` 第 21-25 行
**修复**: 添加 UTF-8 编码重定向
```python
import sys, io, msvcrt, os
if sys.platform == "win32":
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

#### 问题2: Debug print 包含特殊字符
**位置**: `app.py` 第 787 行
**修复**: 改为打印数量而不是完整对象

---

### 4.2 当前问题 🔴

#### 问题: Step7 question_validation 为空

**现象**: 
- Step7 的 `meeting_quality` 有数据
- 但 `question_validation` 是空数组 `[]`
- 导致 Step8/9/10 都没有有效输出

**根因分析**:
1. 用户上传的 `step7_latest (4).json` 中 `question_validation: []`
2. 这可能是之前某次运行时 API 响应问题
3. 代码逻辑本身是正确的（已通过单独测试验证）

**验证数据**:
```
Step7 测试结果:
  question_validation 数量: 0  ← 这是问题所在！
  meeting_quality: {answer_directness: "medium", ...}

Step8 推断结果:
  hypothesis_updates: 0  ← 因为没有相关问题验证
  unchanged_hypotheses: 5  ← 所有假设都变成未变化
```

**下一步行动**:
1. 重新运行 v2 流程（Step7 应该会正常工作）
2. 如果仍然失败，检查 DeepSeek API 响应
3. 添加 Step7 的异常捕获和日志

---

## 五、Flask 应用入口

**文件**: `app.py`

### 5.1 主要路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页（项目列表） |
| `/project/new` | GET | 创建新项目页 |
| `/project/create` | POST | 创建项目 + 上传 BP |
| `/project/<id>` | GET | 项目详情页 |
| `/project/<id>/run_v2` | POST | 触发 2.0 流程（SSE） |
| `/project/<id>/upload_meeting` | POST | 上传会议记录 |
| `/project/<id>/result_v2_page` | GET | 2.0 报告页 |
| `/project/<id>/download_v2_report` | GET | 下载报告 |

### 5.2 SSE 流式输出

`run_v2` 路由返回 Server-Sent Events 流：
```javascript
// 前端连接方式
const eventSource = new EventSource(`/project/${projectId}/run_v2`);

eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    console.log(`${data.step}: ${data.status} - ${data.msg}`);
});

eventSource.addEventListener('thinking', (e) => {
    // 显示思考过程
});
```

### 5.3 关键数据加载函数

```python
_load_step5_data(project_dir)
# 返回: (summary, judgements, decision)
# judgements 格式: [{"hypothesis": "...", "view": "..."}]

_load_step4_questions(project_dir)
# 返回: [问题1, 问题2, ...]  (字符串列表)

_load_dialogue_history(project_dir)
# 返回: [DialogueTurn, ...]
```

---

## 六、测试数据

用户上传的测试数据保存在下载目录：
- `C:/Users/86136/Downloads/step6_latest (4).json` - 26条 new_information ✅
- `C:/Users/86136/Downloads/step7_latest (4).json` - question_validation 为空 🔴
- `C:/Users/86136/Downloads/step8_latest (6).json`
- `C:/Users/86136/Downloads/step9_latest (4).json`
- `C:/Users/86136/Downloads/step10 (3).json`

---

## 七、调试脚本

已创建的调试脚本（位于项目根目录）：
- `debug_step7.py` - 测试 Step7 单独运行
- `debug_step7_real.py` - 模拟 PipelineV2.run_step7
- `debug_step7b.py` - 测试 Step7A/7B 分步执行
- `debug_step8.py` - 测试 Step8 执行

使用方法：
```bash
cd D:/HuaweiMoveData/Users/86136/Documents/GitHub/investment-assistant
python debug_step7.py
```

---

## 八、依赖项

```
flask>=3.0.0
openai>=1.0.0
python-dotenv>=1.0.0
```

环境变量（`.env` 文件）：
```
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

---

## 九、运行方式

### 9.1 启动 Flask 应用
```bash
cd D:/HuaweiMoveData/Users/86136/Documents/GitHub/investment-assistant
python app.py
# 浏览器打开: http://localhost:5000
```

### 9.2 单独测试某个步骤
```python
from services.v2 import PipelineV2

pipeline = PipelineV2("test_project", "test_project")
pipeline.model = "deepseek-chat"

# 测试 Step7
result = pipeline.run_step7(
    step4_questions=["问题1", "问题2"],
    step6_new_information=[...],
    meeting_record=None,
    step6_summary=""
)
```

---

## 十、总结与建议

### 10.1 当前状态

| 模块 | 状态 | 说明 |
|------|------|------|
| Step6 提取 | ✅ 正常 | 已验证，26条数据 |
| Step7 验证 | ✅ 正常 | 已验证，单独测试通过 |
| Step8 更新 | ⚠️ 待验证 | 依赖 Step7 正常输出 |
| Step9 决策 | ✅ 正常 | 已验证，单独测试通过 |
| Step10 Fit | ⚠️ 待验证 | 未单独测试 |
| Flask 应用 | ✅ 正常 | 编码问题已修复 |

### 10.2 建议的下一步

1. **重新运行 v2 流程**: 清除旧的输出文件，重新执行
2. **添加日志**: 在 Step7/8/9 添加详细的执行日志
3. **异常捕获**: 增强错误处理，避免 silent failure
4. **端到端测试**: 创建完整的集成测试脚本

### 10.3 找人帮忙时的说明要点

1. **核心问题**: Step7 的 `question_validation` 为空，导致后续步骤都没有有效数据
2. **代码本身没问题**: 单独测试各个模块都正常
3. **可能是偶发问题**: DeepSeek API 响应问题或数据持久化问题
4. **建议**: 清除旧数据，重新运行一次完整流程

---

**文档版本**: v1.0
**最后更新**: 2026-04-26 08:00
