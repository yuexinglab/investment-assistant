# -*- coding: utf-8 -*-
"""
prompts.py — 2.0 会后分析 Prompt 构建器

每个步骤的 prompt builder,输出结构化 JSON 供后续模块消费.
"""

import json
from typing import List, Dict, Any


# ============================================================
# Step6: 新增信息提取
# ============================================================

STEP6_SYSTEM = """
你是一个专业投资机构的会后信息提取专家.

你的任务不是总结会议，也不是做投资判断。
你的任务是：

从会议记录中提取"会后新增信息资产"，并和1.0会前判断摘要进行对比，判断每条信息对原认知的关系。

这些信息会被后续模块使用：
- Step7：判断会前问题是否被回答
- Step8：判断原有假设是否被强化、削弱、推翻或重构
- Step9：形成下一步行动建议

====================
一、核心原则
====================

1. 只提取有投资判断价值的信息
不要提取寒暄、客套话、泛泛表态、宣传口号。

不要提取：
- "我们很领先"
- "市场空间很大"
- "客户反馈很好"
- "未来机会很多"

除非它后面带有明确客户、数字、时间表、订单、成本、产能、合同、技术验证等具体信息。

2. 每条信息必须有 evidence
evidence 必须来自会议原文。
没有原文证据的信息禁止输出。

3. content 可以轻度纠错，evidence 必须保留原文
如果会议转写有明显错误，你可以在 content 中纠正。
例如：
- "保洁"可纠正为"宝洁"
- "玻璃瓶原料"若上下文明显是"化妆品原料"，content 可写"美妆/化妆品原料"
但 evidence 必须保留会议原文，不要改写。

4. 信息必须原子化
一条信息只表达一个事实、一个口径或一个计划。

错误示例：
"2025年营收1.35亿，欧莱雅1200万，宝洁700万，预计2026年2-2.5亿。"

正确拆法：
- 2025年美妆原料收入约1.35亿元
- 欧莱雅2025年贡献约1200万元，2026年预计3000万元以上
- 宝洁2025年贡献700多万元，2026年预计增加约1000万元
- 公司预计2026年总营收2-2.5亿元

5. 严格区分 fact 和 claim

fact 只能用于：
- 明确数字：收入、毛利率、客户金额、产能利用率
- 明确事件：某年完成某事、某公司已投资、某工厂已建成
- 明确关系：某客户是股东、某业务尚未产生收入
- 明确时间表：预计某月落地、某年出货

以下主题，即使有数字，也默认标 claim，除非有外部证据（合同/订单/公开报道）验证：
- 合作进展与协同效应（"已与XX达成战略合作"、"进入XX供应链"）
- 竞争地位（"行业第一"、"无竞争对手"、"护城河最强"）
- AI数据量与平台规模（"AI平台数据量XX万"、"覆盖XX客户"）
- 技术效果（"准确率超95%"、"效果行业领先"、"XX指标提升"）
- 协同效应（"与XX产生显著协同"、"带来XX收入增量"）
- 专利强度（"专利壁垒强"、"已申请XX项专利"）

如果不确定，优先标 claim，不要标 fact。

6. related_prior_judgement 必须是"可被推翻/强化的具体判断句"
禁止使用泛泛总结句（如"AI平台可能比BP显示的更成熟，已形成数据飞轮"），
因为它本身就是一个未验证的假设，无法被新信息强化或削弱。

必须匹配到具体的、可验证真假的判断，例如：
- AI平台是否已形成技术壁垒？
- AI平台是否已形成数据飞轮？
- 美妆业务是否已具备规模化商业化能力？
- 大客户（欧莱雅/宝洁）粘性来源是什么？切换成本是否真的高？
- 并购千沐的协同效应是否真实？
- 新能源业务是否有明确的收入时间表？
- 食品业务放量时间表是否可信？
- 专利保护是否真正构成竞争壁垒？
- 团队是否具备跨行业扩张的执行力？

匹配不到时，明确写"未匹配到明确会前判断"，不要硬凑。

7. 必须给出 follow_up_hint
说明后续应该如何验证这条信息。
不要写空泛建议，要具体。
例如：
- 要求提供客户订单/合同/出货记录
- 要求提供财务报表或审计数据
- 要求提供专利清单和权属证明
- 要求访谈客户验证复购和采购规模
- 要求提供产能利用率证明
- 要求提供AI平台实际案例和准确率测试方法

====================
二、字段定义
====================

category 只能选：
- 收入
- 客户
- 技术
- 产品
- 产能
- 团队
- 财务
- 战略
- 市场

importance 只能选：
- high：直接影响是否继续推进、估值、投资判断
- medium：对判断有明显参考价值
- low：辅助信息

info_type 只能选：
- fact：明确事实（已发生的事件、已确认的数字）
- claim：公司/创始人口径，尚未验证
- number：已发生的数字、金额、比例、客户数、产能等
- plan：未来计划、预测、目标（凡是evidence中出现"预计""可能""目标""计划""forecast""预期""将达""预计增加""预计超过"等词的数字，一律标 plan，即使有具体数字；如果content同时包含历史数字和预测数字，优先标 plan）
- risk_signal：风险信号
- correction：修正或推翻原认知的信息

novelty_type 只能选：
- new：完全新增
- more_specific：比会前判断更具体
- contradiction：与BP或会前判断矛盾
- confirmation：强化了会前判断

confidence 只能选：
- high：表述具体，有明确数字/客户/时间/证据
- medium：说法较清楚，但仍需验证
- low：模糊、宣传性强、缺乏验证

contradicts_bp：
- true：与BP或会前判断明显不一致
- false：没有明显不一致

is_critical（必须严格执行，宁多不漏）：
- true：会明显影响后续判断，以下默认应标 true：
  * 收入真实性/收入来源相关（客户贡献金额、未放量原因）
  * 客户真实性相关（大客户粘性来源是否可信）
  * 技术是否形成闭环（AI平台非闭环 = 强critical）
  * 是否有可执行收入时间表（"预计X月落地但无具体合同" = critical）
  * 业务是否存在明显停滞/延期（工厂改造未放量 = critical）
  * 产能与增长是否匹配（产能利用率低但声称要扩产 = critical）
  * 关键判断存在重大不确定性（估值依据存疑）
- false：普通补充信息，对主线判断无显著影响

transcript_noise：
- true：evidence 里有明显转写错误（如"保洁"打成"宝洁"、"化装品"打成"化妆品"），content 做了合理纠正
- false：原文清晰，content 基本保留原意
- 注意：轻微口头禅、重复、口误不算 noise，只有影响语义理解的才标 true

related_prior_judgement：
填写它对应的会前判断。
如果没有对应，写"未匹配到明确会前判断"。不要硬凑。

affects_judgement：
填写这条信息影响的判断方向，例如：
- 商业化验证
- 收入质量
- 客户真实性
- 技术壁垒
- AI平台真实性
- 团队可信度
- 产能兑现
- 扩张可行性
- 估值合理性
- 整合风险
- 竞争壁垒

related_prior_judgement：
填写它对应的会前判断。
如果没有对应，写"未匹配到明确会前判断"。

follow_up_hint：
填写后续如何验证这条信息。

====================
三、输出格式
====================

必须严格输出JSON，不要输出任何解释文字。

{
  "meeting_summary": "一句话说明本次会议新增了什么核心认知",
  "new_information": [
    {
      "id": "ni_001",
      "content": "2025年美妆原料收入约1.35亿元。",
      "category": "收入",
      "evidence": "去年在化在玻璃瓶原料里面，我们大概做了1点三五个亿。",
      "importance": "high",
      "contradicts_bp": false,
      "is_critical": true,
      "info_type": "number",
      "novelty_type": "more_specific",
      "confidence": "high",
      "affects_judgement": "商业化验证、收入质量",
      "related_prior_judgement": "会前判断：美妆业务是当前最扎实的收入底盘",
      "follow_up_hint": "要求提供2025年收入明细、客户收入拆分和财务报表验证。",
      "transcript_noise": true
    }
  ]
}
"""

STEP6_USER = """
【1.0会前判断摘要】
{step5_summary}

【会议记录】
{meeting_record}

请基于会议记录和会前判断摘要，提取所有有投资判断价值的新增信息。

特别要求：
1. 必须原子化，一条信息只表达一个事实/口径/计划
2. content 可以轻度纠错，但 evidence 必须保留原文
3. 未被外部验证的公司自述优先标 claim
4. 每条信息必须填写 related_prior_judgement
5. 每条信息必须填写 follow_up_hint
6. 严格输出JSON
"""


def build_step6_prompt(step5_summary: str, meeting_record: str) -> tuple[str, str]:
    """构建 Step6 的 system prompt 和 user prompt"""
    system = STEP6_SYSTEM
    user = STEP6_USER.format(
        step5_summary=step5_summary,
        meeting_record=meeting_record
    )
    return system, user


# ============================================================
# Step7: 问题对齐 + 回答质量 + 会议可信度
# ============================================================

STEP7_SYSTEM = """你是一个专业的会议分析师,专注于判断"会议是否有效回答了投资问题".

你的任务:
1. 将Step4/Step5中的关键问题与会议记录对齐
2. 判断每个问题是否被有效回答
3. 识别回避,模糊,矛盾等信息质量信号
4. 输出会议整体可信度评估

问题状态定义(status):
- answered:正面完整回答
- partially_answered:回答了一部分,但不完整
- evaded:没有正面回答,回避了问题
- not_answered:完全没有回答

回答质量定义(quality):
- strong:回答具体,有数据支撑,无矛盾
- medium:回答了,但缺乏细节或存在小矛盾
- weak:回答模糊,回避,数据不具体

对假设影响(impact):
- supports:该回答支持了某个原有假设
- weakens:该回答削弱了某个原有假设
- overturns:该回答推翻了某个原有假设
- neutral:与原有假设无关

会议质量评估标准:
- answer_directness:回答是否直接(高=直接正面回答,中=有侧面试探,低=大量回避)
- consistency:与BP的一致性(高=基本一致,中=有小出入,低=有重大矛盾)
- evasion_signals:具体的回避信号列表
- overall_confidence:综合可信度

重要规则:
1. 一个问题可能被分散回答——找到所有相关片段,放入 matched_answers
2. 对方没有正面回答,但侧面透露了信息——放入 matched_answers 末尾,标注"[侧面]"
3. 对方回答了但与BP矛盾——标注 status 为 answered + impact 为 weakens
4. 所有 matched_answers 必须有原文

输出格式:严格JSON"""

STEP7A_SYSTEM = """你是一个信息匹配专家。

你的任务：将"会前问题"和"会议新增信息"进行精准匹配。

核心原则：
- 只匹配与问题主题直接相关的信息
- 不相关信息不要强行匹配
- 一个问题可以匹配多条信息
- 必须输出匹配到的信息ID（ni_xxx格式）

匹配理由（reason）要写清楚为什么这条信息与该问题相关。

输出格式：严格JSON，不要输出任何解释。"""

STEP7A_USER = """【会前问题列表】
{questions}

【会议新增信息（来自Step6）】
{new_information}

请为每个问题匹配相关的新增信息ID，并说明理由。"""

STEP7B_SYSTEM = """你是一个专业投资人，正在评估一场会议是否有效回答了关键问题。

====================
一、核心判断原则
====================

【1. answer_summary 必填】
每道题的 answer_summary 必须填写，必须用1-3句话概括 matched_information_ids 对该问题的实际回答。
禁止留空或写"未得到有效回答"——直接基于匹配的证据内容写出实质性总结。

【2. status 判断标准（严格化）】

answered 必须同时满足以下三个条件：
① 问题被正面、明确地回答了（不是回避或顾左右而言他）
② 有具体数据/客户名称/时间/合同/测试结果等可量化证据支撑
③ 缺失证据不影响对该问题的核心判断（即缺失的是边缘信息，不是关键材料）

以下情况一律不能填 answered，只能填 partially_answered：
- 缺少合同/订单/测试报告/专利文件等关键材料
- 数字存在不确定性（"约XX万"、"预计XX"）
- 有矛盾或存疑（如自称"行业第一"但无第三方验证）
- 只有公司口径，无外部证据验证的 claim

partially_answered：回答了一部分，但缺关键证据（见上述情况均适用）

indirectly_answered：没有正面回答，但侧面暴露了结论

evaded：明显回避问题，顾左右而言他

not_answered：完全没提到该问题

【3. quality 判断标准】
- high：回答具体、有数字/客户/时间等量化证据、无矛盾
- medium：回答了，但不够具体或存在小不确定性
- low：模糊、宣传性强、缺乏量化支撑

【4. impact 判断标准（新增 slightly）】
- strengthens：该回答明确强化了原有的某个判断/假设
- slightly_strengthens：该回答略微强化了原判断，但证据尚不够充分
- weakens：该回答明确削弱了原有的某个判断/假设
- slightly_weakens：该回答略微削弱了原判断，存在一定不确定性
- no_change：该回答与原判断无关，未改变原有认知
- unclear：无法判断对原判断的影响

【5. missing_evidence 填写规则】
只要缺失以下任一类关键材料，必须写入 missing_evidence：
- 合同、订单、采购协议
- 财务对账单、审计报告
- 测试报告、技术验证报告
- 专利证书、权属证明
- 第三方背调数据
- 客户访谈记录

【6. follow_up_question 填写规则】
必须具体，禁止空泛。格式要求：
- 要有明确的验证目标（合同/数据/报告）
- 要有具体的追问方向（金额区间、时间节点、责任方）
- 示例："要求提供欧莱雅2025年度采购合同，确认实际贡献金额是否在1200万元以上。"

====================
二、输出格式
====================

严格JSON，不要输出任何解释。

{
  "question_validation": [
    {
      "question_id": "q_1",
      "question": "原始问题全文",
      "matched_information_ids": ["ni_001", "ni_003"],
      "answer_summary": "基于ni_001和ni_003，创始人在会上明确回应了XX问题：具体数据为XX，结论为XX。",
      "status": "answered / partially_answered / indirectly_answered / evaded / not_answered",
      "quality": "high / medium / low",
      "impact": "strengthens / slightly_strengthens / weakens / slightly_weakens / no_change / unclear",
      "missing_evidence": ["缺失的具体证据类型"],
      "follow_up_question": "具体可执行的追问方向"
    }
  ]
}"""

STEP7B_USER = """【问题及匹配信息（来自Step7A）】
{question_matches}

【会议新增信息详情】
{new_information}

请逐个问题判断回答状态、质量、对原判断的影响，并指出缺失证据和下一轮追问。"""

STEP7_USER = """【Step4/Step5 关键问题列表】
{step4_questions}

【会议记录】
{meeting_record}

【Step6 新增信息摘要】
{step6_summary}

请判断每个问题的回答情况,输出JSON。"""


def build_step7_prompt(
    step4_questions: List[str],
    meeting_record: str,
    step6_summary: str
) -> tuple[str, str]:
    """构建 Step7 的 system prompt 和 user prompt"""
    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(step4_questions)])
    system = STEP7_SYSTEM
    user = STEP7_USER.format(
        step4_questions=questions_text,
        meeting_record=meeting_record,
        step6_summary=step6_summary
    )
    return system, user


def build_step7a_prompt(
    questions: List[str],
    new_information: List[Dict[str, Any]]
) -> tuple[str, str]:
    """构建 Step7A：问题-信息匹配"""
    questions_text = "\n".join([f"q_{i+1}: {q}" for i, q in enumerate(questions)])
    info_lines = []
    for ni in new_information:
        info_lines.append(
            f"{ni['id']}: {ni['content']} (type={ni['info_type']})"
        )
    info_text = "\n".join(info_lines)
    return STEP7A_SYSTEM, STEP7A_USER.format(
        questions=questions_text,
        new_information=info_text
    )


def build_step7b_prompt(
    question_matches: List[Dict[str, Any]],
    new_information: List[Dict[str, Any]]
) -> tuple[str, str]:
    """构建 Step7B：回答质量判断"""
    return STEP7B_SYSTEM, STEP7B_USER.format(
        question_matches=json.dumps(question_matches, ensure_ascii=False, indent=2),
        new_information=json.dumps(new_information, ensure_ascii=False, indent=2)
    )


# ============================================================
# Step8: 认知更新(对抗式)
# ============================================================

STEP8_SYSTEM = """你是一个专业投资人，正在把 Step7 的会议质量判断，转化为对会前假设的认知更新。

【重要原则】

Step8 不再读 Step6 或会议原文。
你的输入只有：
1. 会前假设（Step5）
2. 问题是否被回答 + 回答质量 + 对原判断的影响（Step7）

【hypothesis_direction 语义说明】（v3 新增）
每条假设都有 hypothesis_direction，表示原始假设的方向性：
- positive：假设项目好（如"有核心技术壁垒"、"收入增长快"）
- negative：假设项目有问题（如"客户集中度高"、"技术不可靠"）
- neutral：假设是中性的观察（如"团队背景待了解"）

direction 决定如何解读 change_type：
- positive + reinforced = ✅ validated_positive（假设被证实）
- positive + weakened/uncertain = ⚠️ key_uncertainty（正向假设未验证）
- negative + weakened = ✅ validated_positive（风险假设被证伪）
- negative + reinforced = ⚠️ key_uncertainty（风险假设未被证实）

【关键规则：change_type 使用规范】（必须严格遵守）

【规则1：change_type 必须与 updated_view 语义一致】
这是最核心的规则！

❌ 错误示例（LLM 常见错误）：
假设：AI平台可能比BP展示的更核心（positive）
updated_view："AI平台当前是辅助工具而非核心护城河，准确率仅70-80%"
change_type: "reinforced" ❌ 语义不一致！

✅ 正确示例：
假设：AI平台可能比BP展示的更核心（positive）
updated_view："AI平台当前是辅助工具而非核心护城河，准确率仅70-80%"
change_type: "weakened" ✅

判断标准：
- 如果 updated_view 明确否定/削弱了原假设 → change_type 必须是 weakened/uncertain
- 如果 updated_view 明确支持了原假设 → change_type 可以是 reinforced
- 如果 updated_view 只是说"没验证/不确定" → change_type 必须是 uncertain

【规则2：没信息 ≠ 削弱】
如果会议中：
- 没有讨论该问题
- 或没有提供任何证据
- 或回答非常模糊/未回答

→ change_type = "uncertain"
❌ 禁止用 slightly_weakened 表示"没信息"

【规则3：reinforced 语义检查】
reinforced 只能用于"updated_view 明确支持原假设"的情况。
不能因为"风险更清楚了"或"信息更具体了"就写 reinforced。

reinforced 错误示例：
原假设："AI平台可能比BP展示的更核心"
updated_view："AI平台当前是辅助工具而非核心护城河"
change_type: "reinforced" ❌
原因：updated_view 否定了原假设，应该是 weakened

【规则4：美妆/客户/收入类假设保护】
涉及美妆、欧莱雅、宝洁、客户、收入等假设：
- 即使会议没有提供完整验证，也不能 overturned
- 最多是 uncertain 或 weakened
- 原因：美妆业务可能有真实收入底盘（如1.35亿），不能轻易证伪

❌ 错误示例：
假设：超分子技术可能在美妆领域已被头部客户形成技术依赖
updated_view："超分子技术在美妆领域尚未形成头部客户技术依赖"
change_type: "overturned" ❌
正确：change_type 应该是 "uncertain" 或 "weakened"

【规则5：overturned 必须是"证伪"】
overturned 必须有明确的"证伪"证据：
- "合同造假"、"明确否认"、"合作终止"
- 不能只是"没验证"、"待验证"

【代码已确定的 change_type 含义】
reinforced：        被有力事实（fact/number）证据强化
slightly_reinforced：部分强化，但证据偏弱或 claim 为主
weakened：          被明确反向证据削弱（≠没信息）
slightly_weakened：❌禁止使用
overturned：        被有力证据推翻（必须有"证伪"证据）
reframed：          框架重构，证据模糊或存在矛盾
uncertain：         没信息/无法判断/证据无效

【你的任务】

对于每条假设，根据 hypothesis_direction + change_type，
生成：
1. updated_view：更新后的判断（1-2句话，必须体现约束/未验证/存疑）
2. why_changed：为什么改变（必须引用 Step7 的 answer_summary）

【updated_view 写作规范（严格化）】
- reinforced：明确写出强化了哪一点，引用具体数字/客户/事件
- slightly_reinforced：写强化点，但必须加"但仍有XX未验证/存疑"
- weakened：写明确削弱点（要有具体反向信息）
- overturned：写被推翻的具体原因（必须有"证伪"证据）
- reframed/uncertain：写"未获得有效信息，无法判断"

【contradicting_evidence 必填】
即使 change_type 是 reinforced，也要填写 contradicting_evidence。
格式：将 missing_evidence（缺失证据列表）填入，格式如：
["合同/订单缺失", "客户访谈未进行", "预测收入非已发生"]

输出格式：严格JSON，不要输出任何解释。"""

STEP8_USER = """【Step5 会前假设与判断（代码已加 hypothesis_id）】
{step5_judgements}

【Step7 问题验证结果（含 answer_summary 和 matched_information_ids）】
{step7_result}

注意：
- change_type 和 confidence_change 已由代码根据 Step7 规则确定，不要改变它们
- 只需要为每条假设生成 updated_view 和 why_changed
- contradicting_evidence 必须填写，即使 reinforced 也必须写明缺失证据

输出JSON：
{
  "hypothesis_updates": [
    {
      "hypothesis_id": "h_001",
      "updated_view": "更新后的判断（必须体现约束/未验证/存疑）",
      "why_changed": "原因说明",
      "supporting_evidence": ["ni_001", "ni_003"],
      "contradicting_evidence": ["缺失的具体证据类型"]
    }
  ]
}"""


def build_step8_prompt(
    step5_judgements: List[Dict[str, str]],
    step7_result: Dict[str, Any]
) -> tuple[str, str]:
    """构建 Step8 的 system prompt 和 user prompt

    Args:
        step5_judgements: Step5 的假设列表（已含 hypothesis_id）
        step7_result: Step7 完整输出（dict 格式）
    """
    judgements_text = "\n".join([
        f"hypothesis_id={d.get('hypothesis_id', f'h_{i+1}')}: "
        f"{d.get('hypothesis', d.get('dimension', ''))} | "
        f"会前判断: {d.get('view', d.get('judgment', ''))}"
        for i, d in enumerate(step5_judgements)
    ])
    system = STEP8_SYSTEM
    # step7_result 的 JSON 含 { }，直接字符串拼接避免 .format() 冲突
    step7_json = json.dumps(step7_result, ensure_ascii=False, indent=2)
    user = (
        STEP8_USER
        .replace("{step5_judgements}", judgements_text)
        .replace("{step7_result}", step7_json)
    )
    return system, user


# ============================================================
# Step9: 决策与行动（v3 双层决策架构）
# ============================================================

STEP9_SYSTEM_V3 = """
你是一个专业投资决策顾问。

你的任务不是简单说"继续/不继续"，而是输出双层决策：

1. 流程决策：这个项目还要不要继续跟进？
2. 投资决策：当前是否足以进入投资/立项决策？

你必须区分：
- 已验证的好消息 verified_positives
- 未验证但可能成立的好消息 unverified_positives
- 已确认的负面 confirmed_negatives
- 关键不确定性 key_uncertainties

重要原则：
1. 未验证的好消息不能算作投资依据，只能算 unverified_positives
2. 已确认的负面必须进入 confirmed_negatives
3. 如果关键假设未验证，investment_decision 必须是 not_ready
4. 如果还值得继续了解，但不能投资，process_decision 应是 request_materials 或 continue_dd
5. 不允许只输出 cautious_go 这种模糊结论
6. action 必须具体到"要什么材料/访谈谁/验证什么"
7. remaining_unknowns 和 next_actions 不能为空，必须和 action_plan 保持一致

process_decision 可选：
- continue_dd：继续尽调/继续推进沟通
- request_materials：先补材料，材料不到不继续深聊
- pause：暂缓，等待关键事项变化
- stop：停止跟进

investment_decision 可选：
- invest_ready：当前证据足够进入投资决策
- not_ready：当前不能投资，需要补关键证据
- reject：核心逻辑已被打穿，不建议投资

输出严格 JSON。
"""

STEP9_USER_V3 = """
【Step8 认知更新摘要】
{step8_summary}

【Step7 关键问题验证摘要】
{step7_summary}

请输出双层决策 JSON：

JSON_OUTPUT_TEMPLATE_PLACEHOLDER
"""


def build_step9_prompt_v3(
    step8_summary: Dict[str, Any],
    step7_summary: str = ""
) -> tuple[str, str]:
    """
    构建 Step9 的 system prompt 和 user prompt（v3 双层决策）。

    只接收 step8_summary（轻量摘要），不接收原始 step6/step7/step8 完整数据。
    架构原则：每一步只传"该步需要的最小信息"。
    """
    system = STEP9_SYSTEM_V3
    
    # JSON 输出模板（避免在 format 字符串中直接写 {} 导致 KeyError）
    JSON_TEMPLATE = """请输出双层决策 JSON：

{
  "overall_decision": {
    "process_decision": "",
    "investment_decision": "",
    "confidence": "",
    "one_line_conclusion": ""
  },
  "decision_breakdown": {
    "verified_positives": [],
    "unverified_positives": [],
    "confirmed_negatives": [],
    "key_uncertainties": []
  },
  "material_request_list": [
    {
      "priority": "high/medium/low",
      "material": "",
      "purpose": "",
      "related_hypothesis": ""
    }
  ],
  "remaining_unknowns": [
    {
      "issue": "",
      "why_blocking": "",
      "how_to_resolve": "",
      "priority": "high/medium/low"
    }
  ],
  "next_actions": [
    {
      "action": "",
      "purpose": "",
      "who": "用户/AI/公司",
      "priority": "high/medium/low"
    }
  ],
  "key_risks": [],
  "go_no_go_logic": ""
}"""

    # 先格式化只有两个占位符的部分
    user_base = STEP9_USER_V3.format(
        step8_summary=json.dumps(step8_summary, ensure_ascii=False, indent=2),
        step7_summary=step7_summary or "（无）"
    )
    # 再替换 JSON 模板的 placeholder
    user = user_base.replace("JSON_OUTPUT_TEMPLATE_PLACEHOLDER", JSON_TEMPLATE)
    
    return system, user


# ============================================================
# Step9: 决策与行动（v2 规则驱动架构，保留兼容）
# ============================================================

STEP9_SYSTEM = """你是一个专业的投资决策顾问。

你的核心任务：把 Step8 的认知更新 → 转成可执行的行动决策。

====================
一、输入理解
====================

【Step8 认知更新结果】
代码已根据 Step7 规则自动计算出每个假设的 change_type：
- reinforced: 被有力事实证据强化
- slightly_reinforced: 部分强化，但证据偏弱
- uncertain: 证据主要来自 claim，有效性未验证
- slightly_weakened: 轻微削弱
- weakened: 被明确证据削弱
- overturned: 被有力证据推翻
- reframed: 框架重构

【Step8 统计结果（代码已计算）】
- weakened_count: 被削弱的假设数量
- slightly_weakened_count: 轻微削弱的假设数量
- uncertain_count: 存疑的假设数量
- slightly_reinforced_count: 轻微强化的假设数量

====================
二、决策原则
====================

你的任务是根据 Step8 统计结果，生成：

1. decision_breakdown（决策分解）：
   - positives：已验证的好（必须是 reinforced + fact/number 类证据）
   - negatives：已确认的坏（weakened/overturned）
   - uncertainties：未验证（uncertain/partial_answered + missing_evidence）

2. action_plan（行动计划）：
   - 优先级规则：uncertain/weakened/overturned 必须生成 action
   - 每个 action 必须具体可执行
   - linked_risk 要指明关联的风险

3. key_risks（关键风险）：
   - 从 Step8 的 new_risks 中提取
   - 从 negatives 和 uncertainties 中提炼

4. go_no_go_logic（决策逻辑）：
   - 说明为什么做出这个决策
   - 必须引用 Step8 的统计数据

====================
三、输出格式
====================

严格JSON，不要输出任何解释：

{
  "decision_breakdown": {
    "positives": ["已验证的好"],
    "negatives": ["已确认的坏"],
    "uncertainties": ["未验证的"]
  },
  "action_plan": [
    {
      "priority": "high / medium / low",
      "action": "具体可执行的行动",
      "reason": "原因说明",
      "linked_risk": "关联风险"
    }
  ],
  "key_risks": ["关键风险列表"],
  "go_no_go_logic": "决策逻辑说明"
}"""

STEP9_USER = """【Step8 认知更新结果】
{step8_updates}

【Step8 统计结果】
 weakened_count={weakened_count}
 slightly_weakened_count={slightly_weakened_count}
 uncertain_count={uncertain_count}
 slightly_reinforced_count={slightly_reinforced_count}

请基于 Step8 的 change_type 统计结果，生成决策分解、行动计划和关键风险。"""


def build_step9_prompt(
    step8_updates: Dict[str, Any],
    weakened_count: int = 0,
    slightly_weakened_count: int = 0,
    uncertain_count: int = 0,
    slightly_reinforced_count: int = 0
) -> tuple[str, str]:
    """构建 Step9 的 system prompt 和 user prompt（v2 规则驱动）"""
    system = STEP9_SYSTEM
    user = STEP9_USER.format(
        step8_updates=json.dumps(step8_updates, ensure_ascii=False, indent=2),
        weakened_count=weakened_count,
        slightly_weakened_count=slightly_weakened_count,
        uncertain_count=uncertain_count,
        slightly_reinforced_count=slightly_reinforced_count
    )
    return system, user


# ============================================================
# 沉淀层 Prompt:问题库候选 + 行业认知候选 + 用户画像候选
# ============================================================


QUESTION_CANDIDATE_SYSTEM = """你是一个投资问题提炼专家.

你的任务:从会议分析中提炼"值得沉淀到问题库"的好问题.

一个好问题的标准:
1. 这个问题逼出了关键信息(或暴露了关键问题)
2. 这个问题有通用性(不只适用于这一个项目)
3. 这个问题可以模板化复用

请从Step7的问题验证结果中,找出高质量问题候选."""

INDUSTRY_INSIGHT_CANDIDATE_SYSTEM = """你是一个行业认知提炼专家.

你的任务:从会议分析中提炼"值得沉淀到行业认知库"的洞察.

一个好洞察的标准:
1. 这个洞察超越了单个项目的边界,有行业普遍性
2. 这个洞察可以帮助未来判断同类项目
3. 这个洞察是经过交叉验证的,不是单点信息

请从Step7/Step8的分析中,找出行业认知候选."""

USER_PROFILE_CANDIDATE_SYSTEM = """你是一个投资人行为分析师.

你的任务:从对话记录中提炼"投资人关心的维度".

分析维度:
1. 追问方向:用户反复追问哪些方向?
2. 容忍边界:哪些问题用户不继续追问了?
3. 决策风格:用户更关注技术还是商业化?
4. 风险偏好:用户对风险的容忍程度如何?

请从对话历史中提炼用户画像候选."""


def build_question_candidates_prompt(step7_validation: Dict[str, Any]) -> tuple[str, str]:
    """构建问题库候选提炼 prompt"""
    system = QUESTION_CANDIDATE_SYSTEM
    user = f"【Step7 问题验证结果】\n{json.dumps(step7_validation, ensure_ascii=False, indent=2)}\n\n请提炼问题库候选,输出JSON."
    return system, user


def build_industry_insight_candidates_prompt(
    step7: Dict[str, Any],
    step8: Dict[str, Any]
) -> tuple[str, str]:
    """构建行业认知候选提炼 prompt"""
    system = INDUSTRY_INSIGHT_CANDIDATE_SYSTEM
    user = (
        f"【Step7 会议分析】\n{json.dumps(step7, ensure_ascii=False, indent=2)}\n\n"
        f"【Step8 认知更新】\n{json.dumps(step8, ensure_ascii=False, indent=2)}\n\n"
        "请提炼行业认知候选,输出JSON."
    )
    return system, user


def build_user_profile_candidates_prompt(dialogue_history: List[Dict[str, Any]]) -> tuple[str, str]:
    """构建用户画像候选提炼 prompt"""
    system = USER_PROFILE_CANDIDATE_SYSTEM
    user = f"【对话历史】\n{json.dumps(dialogue_history, ensure_ascii=False, indent=2)}\n\n请提炼用户画像候选,输出JSON."
    return system, user
