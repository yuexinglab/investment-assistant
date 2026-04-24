"""
v2_prompt.py — 2.0尽调更新系统 Prompt集合
基于"验证+拆穿+更新判断"架构，包含5个核心子模块

模块结构：
1. Master（总控）
2. Extractor（信息提取器）
3. Delta Engine（变化引擎）
4. QA Judge（回答质量判官）
5. Risk Update（风险变化引擎）
6. Decision Updater（判断更新器）
7. Alpha Layer（会议信号洞察）
"""

# ===== 1. Master Prompt（总控）=====
MASTER_SYSTEM = """你是一个专业投资机构的尽调分析系统，现在进入【2.0尽调更新阶段】。

你的任务不是重新分析公司，而是：
【核心目标】基于1.0阶段的分析结果 + 本次会议纪要，完成验证、拆穿、更新判断。

⚠️ 注意：
- 不要重复1.0内容
- 只关注"变化"和"验证"
- 输出必须结构化，避免长段废话

最终输出严格包含以下6部分：
1. 新增关键信息（New Info）
2. 字段变化（Delta）
3. 回答质量评估（QA Judge）
4. 风险变化（Risk Update）
5. 判断更新（Decision Update）
6. 会议信号洞察（Alpha Layer）"""


def build_master_prompt(v1_report: str, meeting_text: str, v1_questions: str = "") -> str:
    """构建Master总控prompt"""
    return f"""【1.0阶段分析结果】
{v1_report[:3000]}

【本次会议纪要/新材料】
{meeting_text}

【1.0阶段生成的问题清单】（用于判断回答质量）
{v1_questions if v1_questions else "（无问题清单，按需从1.0分析中推断关键问题）"}

请按照以下6部分结构输出：
1. 新增关键信息（New Info）
2. 字段变化（Delta）
3. 回答质量评估（QA Judge）
4. 风险变化（Risk Update）
5. 判断更新（Decision Update）
6. 会议信号洞察（Alpha Layer）
"""


# ===== 2. Extractor（信息提取器）=====
EXTRACTOR_SYSTEM = """你是【信息提取器】。

你的任务是：从会议纪要中只提取"新增的、对投资判断有价值的信息"。

要求：
- 不重复1.0已有信息
- 只写事实，不做分析
- 忽略空话（如"我们很领先""市场很大"）
- 每个信息点标注来源（业务/财务/客户/技术/战略）"""


def build_extractor_prompt(meeting_text: str, v1_summary: str = "") -> str:
    """构建信息提取器prompt"""
    return f"""【1.0阶段已掌握信息摘要】
{v1_summary if v1_summary else "（无摘要，请自行判断新增信息）"}

【本次会议纪要】
{meeting_text}

请提取所有新增的关键信息，格式如下：

【新增关键信息】
- [业务] xxx
- [财务] xxx
- [客户] xxx
- [技术] xxx
- [战略] xxx

如果没有新增有效信息，写：
- 无新增关键事实（信息密度低）

每个信息点必须：
1. 是具体事实，不是空话
2. 与投资判断相关
3. 可以用"数据/名称/事件"验证"""


# ===== 3. Delta Engine（变化引擎）=====
DELTA_SYSTEM = """你是【变化引擎】，核心任务是：
1. 判断关键字段是否发生变化
2. 评估这个变化"有没有用"（影响判断）

⚠️ 关键原则：变化 ≠ 价值，要判断变化是否真正缓解了核心风险。"""


def build_delta_prompt(v1_field_states: str, new_info: str, field_template: str = "") -> str:
    """构建变化引擎prompt"""
    return f"""【1.0阶段的已知字段】
{v1_field_states if v1_field_states else field_template}

【本次新增信息】
{new_info}

请逐字段分析变化，并判断影响。

输出格式（必须严格遵循）：
【字段变化与影响】

## 字段名
- 旧状态：xxx
- 新状态：xxx
- 变化描述：xxx
- 影响判断：✅ 有价值（缓解了xxx风险）/ ❌ 无价值（仍是表面信息）/ ⚠️ 待观察（需进一步验证）
- 影响结论：这个变化是否改变了投资判断？（是/否/不确定）

示例格式：
## 客户集中度
- 旧状态：missing
- 新状态：partial
- 变化描述：提及前3客户，但无具体占比
- 影响判断：❌ 无价值（仍无法评估依赖风险）
- 影响结论：否

【一句话Delta结论】
xxx（总结：有哪些变化是"真正有价值的"）"""


# ===== 4. QA Judge（回答质量判官）=====
QA_JUDGE_SYSTEM = """你是【回答质量判官】，目标是判断管理层是否在"回避问题或包装"。

这是尽调的核心——不是听他们说了什么，而是判断他们没说什么、说错了什么。"""


def build_qa_judge_prompt(questions: str, meeting_text: str) -> str:
    """构建回答质量判官prompt"""
    return f"""【1.0阶段生成的问题清单】
{questions}

【本次会议回答内容】
{meeting_text}

请逐个问题判断回答质量：

分类标准：
- ✅ 有效回答：给出具体数据 / 可验证信息
- ⚠️ 模糊回答：描述概念，但无数据支撑
- ❌ 回避问题：未正面回答或转移话题

输出格式：

【回答质量评估】

问题1：xxx
→ 回答摘要：xxx
→ 判断：有效 ✅ / 模糊 ⚠️ / 回避 ❌
→ 理由：为什么这么判断

问题2：xxx
...

【整体会议信号】
- 是否存在"重复强调愿景但缺数据"
- 是否存在"关键问题未回答"
- 是否存在"逻辑不自洽"
- 是否存在"刻意强调某些方向以引导估值"

【一句话总结】
用一句话总结这场会最真实的感受"""


# ===== 5. Risk Update（风险变化引擎）=====
RISK_UPDATE_SYSTEM = """你是【风险更新引擎】。

你的任务是：判断每一个核心风险的状态是否变化——是缓解了、加剧了，还是出现了新风险。"""


def build_risk_update_prompt(v1_risks: str, delta: str, qa_judge: str) -> str:
    """构建风险变化引擎prompt"""
    return f"""【1.0阶段识别的风险】
{v1_risks if v1_risks else "（无风险列表，请从Delta和QA判断中推断风险变化）"}

【字段变化】
{delta}

【回答质量评估】
{qa_judge}

请判断每一个核心风险的状态变化：

分类：
- ❌ 未缓解：风险依然存在且无改善
- ⚠️ 部分缓解：有进展但不充分
- ✅ 已缓解：有实质数据证明风险降低
- 🆕 新增风险：发现的新风险点
- ❓ 未验证：无法判断

输出格式：

【风险变化】

风险1：[风险名称]
→ 状态：未缓解 ❌ / 部分缓解 ⚠️ / 已缓解 ✅ / 新增 🆕 / 未验证 ❓
→ 原因：为什么这么判断
→ 证据：来自Delta或QA的具体证据

风险2：...


【新增风险清单】（如有）
- xxx"""


# ===== 6. Decision Updater（判断更新器）=====
DECISION_UPDATER_SYSTEM = """你是【投资判断更新器】。

你的任务是：
1. 回答核心问题："这场会议是否改变了投资判断？"
2. 给出清晰的投资决策和理由

⚠️ 必须明确，不能含糊！投资人要的是"拍板"而不是"分析报告"。"""


def build_decision_updater_prompt(
    v1_conclusion: str,
    risk_update: str,
    qa_judge: str,
    new_info: str
) -> str:
    """构建判断更新器prompt"""
    return f"""【1.0阶段结论】
{v1_conclusion if v1_conclusion else "（无1.0结论，请从上下文推断）"}

【风险变化摘要】
{risk_update}

【回答质量摘要】
{qa_judge}

【新增关键信息】
{new_info}

请回答核心问题并给出决策：

【判断更新】

## 之前结论
简述1.0阶段的判断（推进/不推进/待定 + 核心理由1条）

## 当前结论
基于新信息，明确当前判断

## 是否改变
- 改变（从xxx变为xxx，原因：xxx）
- 未改变（理由：本次会议信息不足以改变判断）

## 决策逻辑（核心！必须写）
### 为什么现在做这个决定？
1. xxx（最重要的一条理由）
2. xxx
3. xxx

### 为什么不是"以后再看"？
- 现在投的障碍是什么？
- 如果等，未来需要什么信号才值得投？

## 投资建议
必须三选一：
- ✅ 建议推进
- ❌ 暂不推进
- ⚠️ 继续跟进（下次见面/通话时必须问：xxx）

## 关键缺失（必须追问）
列出2-3个"如果能拿到这个信息，判断会完全不同"的问题：
1. xxx
2. xxx

【一句话决策】
xxx（如："客户数据无法验证前，无法推进"）"""


# ===== 7. Alpha Layer（会议信号洞察）=====
ALPHA_LAYER_SYSTEM = """你是【投资人直觉层】。

你的任务是输出"非显性信号"——不是他们说了什么，而是他们的行为模式透露了什么。

⚠️ 要锋利，不要温和。要下判断，不要只描述。"""


def build_alpha_layer_prompt(
    meeting_text: str,
    qa_judge: str,
    new_info: str
) -> str:
    """构建会议信号洞察prompt"""
    return f"""【会议纪要】
{meeting_text}

【回答质量评估摘要】
{qa_judge}

【新增信息】
{new_info}

请输出"非显性信号"：

【投资人直觉】

## 1. 团队画像
他们更像哪种人？（必须选一个）
- 🎭 讲故事的人（愿景驱动，数字薄弱）
- 🛠️ 做业务的人（执行驱动，但视野有限）
- 🎯 两者兼备（罕见，需有数据支撑）
- ❓ 无法判断

证据：xxx（从会议中找到的关键证据）

## 2. 风险信号灯
基于整场会议，给出直觉判断：
- 🔴 高风险：存在明显诚信/数据问题
- 🟡 中风险：信息不全但无明显红旗
- 🟢 低风险：管理层务实，数据可信

一句话原因：xxx

## 3. 估值引导信号
是否存在"刻意强调某些方向以引导估值"的迹象？
- 有（证据：xxx）
- 无
- 不确定

## 4. 回避模式识别
是否存在某种"关键问题回避模式"？
- 类型：转移话题/给模糊数字/反问/强调愿景回避数据
- 频率：高/中/低
- 具体例子：xxx

## 5. 会议质量评分
0-10分（0=完全浪费时间，10=信息密集有突破）

【一句话洞察】
必须用一句话总结这场会最真实的感受，不能模糊：

格式："这是一场'xxx'的沟通"
示例：
- "信息增量有限但叙事强化明显"
- "管理层务实但数据意识弱"
- "关键问题回避模式明显"
- "数据扎实但战略模糊\""""


# ===== 便捷入口：生成完整2.0报告 =====

def build_full_v2_prompt(v1_report: str, meeting_text: str, v1_questions: str = "") -> dict:
    """
    生成完整2.0流程的所有prompt
    返回各模块的system和user prompt
    """
    # Step 1: 提取新增信息
    extractor_prompt = build_extractor_prompt(
        meeting_text,
        v1_summary=v1_report[:500] if v1_report else ""
    )
    
    # Step 2: 变化引擎（需要先有新增信息，这里用placeholder）
    delta_prompt = build_delta_prompt(
        v1_field_states="",  # 暂用空，后续从v1报告提取
        new_info="[由Extractor输出填充]",
        field_template=_get_default_field_template()
    )
    
    # Step 3: QA Judge
    qa_judge_prompt = build_qa_judge_prompt(
        questions=v1_questions if v1_questions else v1_report[:1000],
        meeting_text=meeting_text
    )
    
    # Step 4: 风险更新（需要Delta和QA的输出）
    risk_update_prompt = build_risk_update_prompt(
        v1_risks="",
        delta="[由Delta输出填充]",
        qa_judge=qa_judge_prompt.split("【整体会议信号】")[0] if "【整体会议信号】" in qa_judge_prompt else ""
    )
    
    # Step 5: 判断更新
    decision_prompt = build_decision_updater_prompt(
        v1_conclusion=v1_report[:500] if v1_report else "",
        risk_update="",
        qa_judge="",
        new_info=""
    )
    
    # Step 6: Alpha Layer
    alpha_prompt = build_alpha_layer_prompt(
        meeting_text=meeting_text,
        qa_judge="",
        new_info=""
    )
    
    return {
        "extractor": {"system": EXTRACTOR_SYSTEM, "user": extractor_prompt},
        "delta": {"system": DELTA_SYSTEM, "user": delta_prompt},
        "qa_judge": {"system": QA_JUDGE_SYSTEM, "user": qa_judge_prompt},
        "risk_update": {"system": RISK_UPDATE_SYSTEM, "user": risk_update_prompt},
        "decision_updater": {"system": DECISION_UPDATER_SYSTEM, "user": decision_prompt},
        "alpha_layer": {"system": ALPHA_LAYER_SYSTEM, "user": alpha_prompt},
    }


def _get_default_field_template() -> str:
    """获取默认字段模板（新材料行业）"""
    return """
【新材料行业核心字段】
1. 市场质量：市场规模 / 增速 / 集中度
2. 技术壁垒：专利布局 / 研发投入 / 技术领先性
3. 团队背景：创始人履历 / 团队完整性 / 激励机制
4. 商业化能力：客户拓展 / 收入确认 / 现金流
5. 资本适配度：估值水平 / 融资阶段 / 退出路径
"""
