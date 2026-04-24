"""
测试 Step3 新旧 prompt 输出对比

旧版：字段抽取（29个字段逐个标记）
新版：判断辅助背景层（5大模块，服务Step1）
"""
import os
import sys
import io

# 强制UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 项目路径
PROJECT_DIR = r"D:\复旦文件\Semester3-4\搞事情\论文产品化\投资助手"
PROJECT_NAME = "杉海创新科技6_20260422_162546"
PROJECT_DIR_FULL = os.path.join(PROJECT_DIR, "workspace", PROJECT_NAME)

# 加载config
sys.path.insert(0, PROJECT_DIR)
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from services.deepseek_service import call_deepseek

# ============ 加载数据 ============
print("加载数据...")

# BP原文
bp_path = os.path.join(PROJECT_DIR_FULL, "parsed", "bp_text.txt")
with open(bp_path, "r", encoding="utf-8") as f:
    bp_text = f.read()

step1_path = os.path.join(PROJECT_DIR_FULL, "step1_v2_new.txt")
with open(step1_path, "r", encoding="utf-8") as f:
    step1_result = f.read()

print(f"BP长度: {len(bp_text)} chars")
print(f"Step1长度: {len(step1_result)} chars")
print()

# ============ 旧版 Prompt（字段抽取） ============
print("=" * 60)
print("【旧版 Step3 - 字段抽取】")
print("=" * 60)

OLD_SYSTEM_PROMPT = """你是一位专业的数据提取师，擅长从非结构化文本中提取结构化信息。
你的任务是根据给定的字段列表，从BP材料中系统性地提取每个字段的信息。
对于每个字段，请标注：
- known: 有明确信息
- partial: 有部分信息但不完整
- missing: 未提及
- weak_evidence: 有提及但缺乏证据支撑
- conflicting: 信息矛盾

请严格按以下格式输出：
字段名: [状态] | 提取的信息 | 来源依据
"""
OLD_USER_PROMPT = f"""请从以下BP材料中，抽取29个核心字段的信息。

字段列表：
1. current_main_application
2. revenue_by_application
3. main_customer_type
4. customer_paid_feature
5. customer_pain_point
6. direct_competitors
7. market_position
8. core_technology
9. technical_uniqueness
10. stage_lab_to_mass
11. mass_production_status
12. avg_conversion_time
13. main_bottleneck
14. conversion_success_rate
15. inhouse_capabilities
16. team_roles
17. industrialization_experience
18. top5_customer_ratio
19. single_customer_dependency
20. revenue_growth_source
21. revenue_model
22. gross_margin_logic
23. new_business_stage
24. new_business_revenue
25. ai_data_source
26. ai_closed_loop
27. ai_business_impact
28. shareholding_structure
29. future_financing_need

BP材料：
{bp_text[:10000]}

[材料过长，已截取前10000字进行分析]
"""

print("正在调用DeepSeek（旧版字段抽取）...")
old_result = call_deepseek(
    system_prompt=OLD_SYSTEM_PROMPT,
    user_prompt=OLD_USER_PROMPT
)
print("旧版完成")
print(old_result[:500] if len(old_result) > 500 else old_result)

# ============ 新版 Prompt（判断辅助背景层） ============
print()
print("=" * 60)
print("【新版 Step3 - 判断辅助背景层】")
print("=" * 60)

# SYSTEM_PROMPT with placeholders filled
NEW_SYSTEM_PROMPT_TPL = """你是一位有经验的投资研究员，正在为投资人提供"判断辅助背景信息"。

你的任务不是下投资结论，而是：
在已有Step1初始判断的基础上，补充相关背景信息，帮助投资人避免盲点、识别包装，并区分哪些信息可以通过公开资料解决，哪些必须进一步尽调。

重要原则：
- 不要重复Step1的判断
- 不要写完整行业报告
- 不要试图覆盖所有信息
- 只补充"与判断相关"的背景
- 所有内容都要服务于"是否影响投资判断"
- Step3不是让你知道更多，而是让你知道"哪些东西不值得信"+"哪些必须再确认"

请严格按照以下结构输出：

----------------------------------

【输入信息】

Step1 初始判断：
{step1_output}

项目材料（BP/纪要等）：
{project_info}

----------------------------------

一、【与当前判断主线相关的背景补充】

围绕Step1的核心判断（如公司本质、收入来源、AI定位等），补充关键背景信息：

- 背景点：
- 行业/常识解释：
- 对当前判断的意义（支持 / 削弱 / 中性）：

（最多3条，只选最相关的）

----------------------------------

二、【行业/技术常识校验（拆包装）】

针对材料中的关键表述，判断其在行业中的真实含义：

- 哪些说法在行业中是"成立的常识"
- 哪些说法"常被用来包装，但不等于壁垒"
- 哪些点需要谨慎理解

重点关注：
- AI能力（是否只是工具）
- 平台化/多行业扩展（是否提前讲故事）
- 技术壁垒
- 团队/背书（如诺奖、院士、博士）：这些是否真正转化为排他性技术、实际产品、商业化能力

----------------------------------

三、【公开可补的信息（无需尽调）】

列出可以通过公开资料大致确认的信息：

- 信息点：
- 当前可获得结论：
- 可信度（高/中/低）：

（例如：行业结构、对标公司、技术路线是否通用等）

----------------------------------

四、【公开仍无法确认的关键问题】

列出即使通过公开信息仍然无法确认，但会影响判断的点：

- 问题：
- 为什么公开无法确认：
- 对投资判断影响程度（高/中/低）：

只保留真正影响决策的问题（最多5个）

----------------------------------

五、【对Step1的校正提示（不做结论）】

基于以上背景信息：

- 当前背景更支持Step1的哪些判断：
- 当前背景提示Step1需要谨慎/收缩的地方：
- 哪些问题应进入下一步（决策缺口识别）做重点缺口识别：

不要直接推翻Step1，只做"提示"

----------------------------------

【写作要求】

- 用投资人内部讨论的语气，不要写成报告
- 可以有判断，但不能下最终结论
- 控制篇幅，避免冗长
"""

new_system_prompt = NEW_SYSTEM_PROMPT_TPL.format(
    step1_output=step1_result[:3000],
    project_info=bp_text[:5000]
)
new_user_prompt = "请根据上述Step1判断和项目材料，输出判断辅助背景信息。"

print("正在调用DeepSeek（新版判断辅助背景层）...")
new_result = call_deepseek(
    system_prompt=new_system_prompt,
    user_prompt=new_user_prompt
)
print("新版完成")
print(new_result[:500] if len(new_result) > 500 else new_result)

# ============ 保存结果 ============
with open(os.path.join(PROJECT_DIR_FULL, "step3_v1_old.txt"), "w", encoding="utf-8") as f:
    f.write(old_result)

with open(os.path.join(PROJECT_DIR_FULL, "step3_v2_new.txt"), "w", encoding="utf-8") as f:
    f.write(new_result)

print()
print("=" * 60)
print("[OK] 对比结果已保存到项目目录（基于 step1_v2_new.txt）")
print(f"   旧版v1（字段抽取）: step3_v1_old.txt ({len(old_result)} chars)")
print(f"   新版v2（判断辅助背景层）: step3_v2_new.txt ({len(new_result)} chars)")
