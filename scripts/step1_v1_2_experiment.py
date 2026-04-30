# -*- coding: utf-8 -*-
"""
Step1 v1.2 实验脚本

验证"结构识别 + 通用投资框架进入Step1"是否真的有效。

与 v1.1 的区别：
- v1.1: 只测试7字段JSON输出格式，未使用project_structure_detector和general.py
- v1.2: 真实调用project_structure_detector + 把general压缩成思考约束注入prompt

运行：
    python scripts/step1_v1_2_experiment.py

输出：
    workspace/step1_v1_2_experiment/YYYYMMDD_HHMMSS/
    ├── A1/
    │   ├── step1_current.txt
    │   ├── step1_v1_1.json
    │   ├── step1_v1_2.json
    │   ├── project_structure.json
    │   └── compare.md
    ├── A2/...
    ├── C1/...
    ├── compare_all.md
    └── summary.md
"""

import io
import json
import os
import sys
from datetime import datetime

# 修复 Windows GBK 输出问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from services.deepseek_service import call_deepseek


# ============================================================
# Step1 当前版本（不做任何改动）
# ============================================================

STEP1_CURRENT_SYSTEM = (
    "你是一位资深投资人兼业务理解专家。"
    "你现在的任务是：读完一份 BP，输出一份清晰的初步判断。"
    "风格：有观点、有逻辑、不废话。不要大量引用原文，要形成判断。"
)

STEP1_CURRENT_USER = """
请对以下BP进行初步判断，输出：

一、【这家公司本质上是什么 / 不是什么】
- 一句话定位
- 2-3条关键判断

二、【初步看法】
- 这个方向靠谱吗？
- 最值得关注的亮点是什么？
- 最大的疑问是什么？

三、【需要重点了解的问题】
- 3-5个关键问题（会前就想知道的）

---

BP 全文：

{bp_text}
"""


# ============================================================
# Step1 v1.1（无结构识别，无框架注入）
# ============================================================

STEP1_V1_1_SYSTEM = """你是一位资深投资人。你的任务是对 BP 形成第一判断：轻量、精准、有观点。

必须直接输出 JSON 格式，不要输出任何解释性文字。JSON 必须包含以下 7 个字段：
company_essence, business_structure, revenue_logic, customer_logic, key_judgement, red_flags, must_ask_questions。

格式：
{
  "company_essence": {"是什么": "...", "不是什么": ["..."], "confidence": "high"},
  "business_structure": {"current_business": [...], "narrative_business": [...]},
  "revenue_logic": {"current_money_source": "...", "clarity": "...", "red_flag_note": null},
  "customer_logic": {"who_pays": "...", "why_pays": "...", "sustainability": "..."},
  "key_judgement": {"statement": "...", "reasoning": "...", "stance": "meet|pass|hold"},
  "red_flags": {"flags": [...]},
  "must_ask_questions": {"questions": [...]}
}
"""


# ============================================================
# Step1 v1.2（真实结构识别 + 框架约束）
# ============================================================

# general.py 压缩成思考约束（不是直接塞字段，而是作为prompt约束）
GENERAL_FRAMEWORK_CONSTRAINTS = """
【投资框架约束 - 必须遵守】

在形成判断时，你必须思考以下问题，但不能在输出中展开分析：

1. 收入真实性
   - 当前真实收入来源是什么？不要基于BP叙事判断。
   - 收入是否可持续，还是一次性或依赖补贴？

2. 叙事 vs 现实
   - BP声称的"全产业链/平台/AI/客户合作"，是否真的已验证？
   - 如果只是"接触/探讨/意向"，不能写成"已合作"。

3. 商业模式是否跑通
   - 公司是否已从"试点"进化到"稳定交付"？
   - 客户是否愿意持续付费，还是一次性采购？

4. 客户逻辑
   - 客户为什么付钱：刚需？效率驱动？还是政策/试点驱动？
   - 如果政策退坡，客户是否仍会付费？

5. 现金流风险
   - 是否需要公司垫资（设备/库存/项目实施）？
   - 回款周期如何？收入确认与现金流是否匹配？

6. 可复制性
   - 每个客户都需要定制吗？
   - 规模化后，毛利率会上升还是下降？

7. 估值叙事风险
   - 当前估值是基于现实业务，还是未来故事？
   - 如果只按当前业务估值，是否明显偏高？

8. 假好项目红旗（必须识别）
   - 商业模式描述复杂但无法清晰解释收入来源
   - 大量使用"平台""生态""赋能"等模糊表述
   - 强调案例数量但不披露收入规模
   - 扩张依赖大量资本投入（重资产）
   - 声称"全产业链"但实际依赖外部供应商
"""


def build_step1_v1_2_system_prompt(project_structure: dict) -> str:
    """
    构建 v1.2 system prompt：
    1. 项目结构识别结果（project_structure_detector输出）
    2. 投资框架约束（general.py压缩版）
    """

    # 格式化 project_structure
    industry_tags = project_structure.get("industry_tags", [])
    business_lines = project_structure.get("business_lines", [])
    business_model_hypotheses = project_structure.get("business_model_hypotheses", [])
    risk_buckets = project_structure.get("risk_buckets", [])
    key_uncertainties = project_structure.get("key_uncertainties", [])

    # 行业标签
    industry_text = " | ".join([f"{t.get('label','')}({t.get('confidence','')})" for t in industry_tags[:5]])

    # 业务线（当前 vs 叙事）
    current_lines = [b.get("name") for b in business_lines if b.get("role") == "current_business"]
    narrative_lines = [b.get("name") for b in business_lines if b.get("role") not in ["current_business", "supporting_capability"]]
    supporting_lines = [b.get("name") for b in business_lines if b.get("role") == "supporting_capability"]

    # 商业模式假设
    models_primary = [m.get("bucket_name") for m in business_model_hypotheses if m.get("role") == "primary"]
    models_secondary = [m.get("bucket_name") for m in business_model_hypotheses if m.get("role") == "secondary"]
    models_narrative = [m.get("bucket_name") for m in business_model_hypotheses if m.get("role") in ["narrative", "risk"]]

    # 风险桶
    risks = [r.get("bucket_name") for r in risk_buckets]

    # 关键不确定性
    uncertainties_text = "\n".join([
        f"  - {u.get('uncertainty', '')}: {', '.join(u.get('discriminating_questions', [])[:2])}"
        for u in key_uncertainties[:5]
    ])

    structure_section = f"""
【系统结构识别结果 - 仅供参照，不是结论】

识别行业: {industry_text or '未识别到明确行业'}

业务线（当前业务）: {', '.join(current_lines) if current_lines else '未识别到'}
业务线（叙事/增长）: {', '.join(narrative_lines) if narrative_lines else '未识别到'}
业务线（支撑能力）: {', '.join(supporting_lines) if supporting_lines else '未识别到'}

商业模式假设（主要）: {', '.join(models_primary) if models_primary else '无'}
商业模式假设（次要）: {', '.join(models_secondary) if models_secondary else '无'}
商业模式假设（叙事/风险）: {', '.join(models_narrative) if models_narrative else '无'}

风险信号: {', '.join(risks) if risks else '无明确风险信号'}

关键不确定性:
{uncertainties_text if uncertainties_text else '无'}

---
"""

    base_system = """你是一位资深投资人。你的任务是对 BP 形成第一判断：轻量、精准、有观点。

重要规则：
1. 必须直接输出 JSON 格式，不要输出任何解释性文字或格式说明。
2. 不要照抄 BP 的定位表述，要用自己的判断重新表述。
3. 如果 BP 声称"全产业链/平台/AI/客户合作"，必须判断是否只是叙事，不是事实。
4. 未验证的内容必须写成"待验证"，不能写死。
5. business_structure 必须区分 current_business 和 narrative_business。
6. stance 只能用：positive_watch / cautious_watch / pass_for_now，不要用 meet/pass/hold。

JSON 必须包含以下 8 个字段（structure_evidence 是 v1.2 新增）：
company_essence, business_structure, revenue_logic, customer_logic, key_judgement, red_flags, must_ask_questions, structure_evidence
"""

    return base_system + structure_section + GENERAL_FRAMEWORK_CONSTRAINTS


# ============================================================
# 测试项目列表
# ============================================================

TEST_PROJECTS = [
    {
        "id": "A1",
        "name": "斯年智驾（无人重载运输）",
        "bp_path": os.path.join(
            PROJECT_ROOT, "workspace", "A1_1_0测试2_20260429_151410", "parsed", "bp_text.txt"
        )
    },
    {
        "id": "A2",
        "name": "A2项目（自动轮底盘）",
        "bp_path": os.path.join(
            PROJECT_ROOT, "workspace", "A2_1_0测试1_20260429_213714", "parsed", "bp_text.txt"
        )
    },
    {
        "id": "C1",
        "name": "C1项目（电驱动系统）",
        "bp_path": os.path.join(
            PROJECT_ROOT, "workspace", "C1_1_0测试1_20260430_080032", "parsed", "bp_text.txt"
        )
    }
]


# ============================================================
# 运行函数
# ============================================================

def run_step1_current(bp_text: str) -> str:
    """运行当前版本的 Step1"""
    prompt = STEP1_CURRENT_USER.format(bp_text=bp_text)
    return call_deepseek(
        system_prompt=STEP1_CURRENT_SYSTEM,
        user_prompt=prompt,
        max_retries=2
    )


def run_step1_v1_1(bp_text: str) -> dict:
    """运行 v1.1（无结构识别，无框架约束）"""
    raw_output = call_deepseek(
        system_prompt=STEP1_V1_1_SYSTEM,
        user_prompt=f"请直接输出JSON，不要任何解释。\n\nBP文本：\n\n{bp_text}",
        max_retries=2
    )
    return parse_json_output(raw_output)


def run_project_structure(bp_text: str) -> dict:
    """运行 project_structure_detector"""
    from step3.project_structure_detector import detect_project_structure
    structure = detect_project_structure(bp_text)
    return structure.to_dict()


def run_step1_v1_2(bp_text: str, project_structure: dict) -> dict:
    """运行 v1.2（真实结构识别 + 框架约束）"""
    system_prompt = build_step1_v1_2_system_prompt(project_structure)
    user_prompt = f"请直接输出JSON，不要任何解释。\n\nBP文本：\n\n{bp_text}"
    raw_output = call_deepseek(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_retries=2
    )
    return parse_json_output(raw_output)


def parse_json_output(raw_output: str) -> dict:
    """解析 LLM 输出的 JSON"""
    if not raw_output:
        return {"error": "Empty output"}

    # 尝试直接解析
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 部分
    import re
    json_match = re.search(r'\{[\s\S]*\}', raw_output)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return {"error": "JSON解析失败", "raw": raw_output[:500]}

    return {"error": "未找到JSON", "raw": raw_output[:500]}


def run_experiment():
    """运行完整实验"""
    base_dir = os.path.join(
        PROJECT_ROOT, "workspace", "step1_v1_2_experiment",
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    os.makedirs(base_dir, exist_ok=True)

    all_results = []

    for project in TEST_PROJECTS:
        print(f"\n{'='*60}")
        print(f"[{project['id']}] {project['name']}")
        print(f"{'='*60}")

        # 读取 BP
        if not os.path.exists(project["bp_path"]):
            print(f"[WARN] BP file not found: {project['bp_path']}")
            continue

        with open(project["bp_path"], "r", encoding="utf-8") as f:
            bp_text = f.read()
        print(f"[OK] BP text: {len(bp_text)} chars")

        project_dir = os.path.join(base_dir, project["id"])
        os.makedirs(project_dir, exist_ok=True)

        # 1. step1_current
        print(f"  Running step1_current...")
        step1_current = run_step1_current(bp_text)
        with open(os.path.join(project_dir, "step1_current.txt"), "w", encoding="utf-8") as f:
            f.write(step1_current)

        # 2. project_structure（v1.2 专用）
        print(f"  Running project_structure_detector...")
        project_structure = run_project_structure(bp_text)
        with open(os.path.join(project_dir, "project_structure.json"), "w", encoding="utf-8") as f:
            json.dump(project_structure, ensure_ascii=False, indent=2, fp=f)

        # 3. step1_v1_1
        print(f"  Running step1_v1_1...")
        step1_v1_1 = run_step1_v1_1(bp_text)
        with open(os.path.join(project_dir, "step1_v1_1.json"), "w", encoding="utf-8") as f:
            json.dump(step1_v1_1, ensure_ascii=False, indent=2, fp=f)

        # 4. step1_v1_2
        print(f"  Running step1_v1_2 (with structure + framework)...")
        step1_v1_2 = run_step1_v1_2(bp_text, project_structure)
        with open(os.path.join(project_dir, "step1_v1_2.json"), "w", encoding="utf-8") as f:
            json.dump(step1_v1_2, ensure_ascii=False, indent=2, fp=f)

        print(f"  [OK] Results saved to: {project_dir}")

        all_results.append({
            "id": project["id"],
            "name": project["name"],
            "current": step1_current,
            "v1_1": step1_v1_1,
            "v1_2": step1_v1_2,
            "project_structure": project_structure
        })

    return base_dir, all_results


def generate_project_compare_md(result: dict) -> str:
    """生成单个项目的三版本对比报告"""
    lines = [
        f"# {result['id']} - {result['name']}",
        "",
        "## Project Structure 识别结果（v1.2 输入）",
        ""
    ]

    ps = result.get("project_structure", {})
    industry_tags = [t.get("label") for t in ps.get("industry_tags", [])]
    business_lines = ps.get("business_lines", [])
    current_lines = [b.get("name") for b in business_lines if b.get("role") == "current_business"]
    narrative_lines = [b.get("name") for b in business_lines if b.get("role") not in ["current_business", "supporting_capability"]]
    models = [m.get("bucket_name") for m in ps.get("business_model_hypotheses", [])]

    lines.append(f"- 行业标签: {', '.join(industry_tags) if industry_tags else '未识别'}")
    lines.append(f"- 当前业务线: {', '.join(current_lines) if current_lines else '未识别'}")
    lines.append(f"- 叙事业务线: {', '.join(narrative_lines) if narrative_lines else '未识别'}")
    lines.append(f"- 商业模式: {', '.join(models) if models else '未识别'}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 三版本对比")
    lines.append("")
    lines.append(f"### key_judgement.statement")
    lines.append("")
    lines.append(f"| 版本 | stance | 核心判断 |")
    lines.append(f"|------|--------|----------|")

    for label, data in [
        ("current", result.get("current", "")),
        ("v1.1", result.get("v1_1", {})),
        ("v1.2", result.get("v1_2", {}))
    ]:
        if not isinstance(data, dict):
            # 从 current 文本中提取关键句（或者其他非dict数据）
            stance = "N/A"
            statement = (data[:200] + "..." if len(data) > 200 else data) if isinstance(data, str) else "N/A"
        elif label == "current":
            stance = "N/A"
            statement = (data[:200] + "..." if len(data) > 200 else data)
        else:
            jg = data.get("key_judgement", {})
            stance = jg.get("stance", "N/A") if isinstance(jg, dict) else "N/A"
            statement = jg.get("statement", "N/A") if isinstance(jg, dict) else "N/A"
        lines.append(f"| {label} | {stance} | {statement} |")

    lines.append("")
    lines.append("### company_essence")
    lines.append("")

    for label, data in [("v1.1", result.get("v1_1", {})), ("v1.2", result.get("v1_2", {}))]:
        if not isinstance(data, dict):
            continue
        ce = data.get("company_essence", {})
        if not isinstance(ce, dict):
            lines.append(f"**{label}**: (company_essence not a dict: {str(ce)[:50]})")
            lines.append("")
            continue
        lines.append(f"**{label}**:")
        lines.append(f"- 是什么: {ce.get('是什么', 'N/A')}")
        lines.append(f"- 不是什么: {ce.get('不是什么', [])}")
        lines.append(f"- confidence: {ce.get('confidence', 'N/A')}")
        lines.append("")

    lines.append("### business_structure")
    lines.append("")

    for label, data in [("v1.1", result.get("v1_1", {})), ("v1.2", result.get("v1_2", {}))]:
        if not isinstance(data, dict):
            continue
        bs = data.get("business_structure", {})
        if not isinstance(bs, dict):
            lines.append(f"**{label}**: (business_structure not a dict: {str(bs)[:80]})")
            lines.append("")
            continue
        current = bs.get("current_business", [])
        narrative = bs.get("narrative_business", [])
        current_names = [b.get('name') if isinstance(b, dict) else str(b) for b in current] if isinstance(current, list) else 'N/A'
        narrative_names = [b.get('name') if isinstance(b, dict) else str(b) for b in narrative] if isinstance(narrative, list) else 'N/A'
        lines.append(f"**{label}**:")
        lines.append(f"- 当前业务: {current_names if current_names else 'N/A'}")
        lines.append(f"- 叙事业务: {narrative_names if narrative_names else 'N/A'}")
        lines.append("")

    lines.append("### revenue_logic")
    lines.append("")

    for label, data in [("v1.1", result.get("v1_1", {})), ("v1.2", result.get("v1_2", {}))]:
        if not isinstance(data, dict):
            continue
        rl = data.get("revenue_logic", {})
        if not isinstance(rl, dict):
            lines.append(f"**{label}**: (revenue_logic not a dict)")
            lines.append("")
            continue
        lines.append(f"**{label}**: {rl.get('current_money_source', 'N/A')} (clarity: {rl.get('clarity', 'N/A')})")
    lines.append("")

    lines.append("### red_flags")
    lines.append("")

    for label, data in [("v1.1", result.get("v1_1", {})), ("v1.2", result.get("v1_2", {}))]:
        if not isinstance(data, dict):
            continue
        rf = data.get("red_flags", {})
        if not isinstance(rf, dict):
            lines.append(f"**{label}**: (red_flags not a dict)")
            lines.append("")
            continue
        flags = rf.get("flags", [])
        lines.append(f"**{label}** ({len(flags)}个):")
        for f in flags:
            if isinstance(f, dict):
                lines.append(f"- {f.get('flag', 'N/A')}")
        lines.append("")

    lines.append("### must_ask_questions")
    lines.append("")

    for label, data in [("v1.1", result.get("v1_1", {})), ("v1.2", result.get("v1_2", {}))]:
        if not isinstance(data, dict):
            continue
        maq = data.get("must_ask_questions", {})
        if not isinstance(maq, dict):
            lines.append(f"**{label}**: (must_ask_questions not a dict)")
            lines.append("")
            continue
        qs = maq.get("questions", [])
        lines.append(f"**{label}** ({len(qs)}个):")
        for q in qs:
            if isinstance(q, dict):
                lines.append(f"- {q.get('question', 'N/A')} (related_to: {q.get('related_to', 'N/A')})")
        lines.append("")

    lines.append("### structure_evidence（v1.2 新增字段）")
    lines.append("")

    v1_2 = result.get("v1_2", {})
    if isinstance(v1_2, dict) and "error" not in v1_2:
        se = v1_2.get("structure_evidence", {})
        if isinstance(se, dict) and se:
            lines.append(f"- 识别到的行业: {se.get('recognized_industry', 'N/A')}")
            lines.append(f"- 识别到的商业模式: {se.get('recognized_business_models', 'N/A')}")
            lines.append(f"- 识别到的叙事: {se.get('recognized_narratives', 'N/A')}")
            lines.append(f"- Step1 判断与系统识别的差异: {se.get('step1_vs_detector_gap', 'N/A')}")
        else:
            lines.append("(v1.2 未输出 structure_evidence)")

    return "\n".join(lines)


def generate_summary_md(all_results: list) -> str:
    """生成汇总报告（人工评估式，不自动打分）"""
    # 安全获取嵌套数据
    def safe_get(data, *keys, default="N/A"):
        result = data
        for k in keys:
            if isinstance(result, dict):
                result = result.get(k, default)
            else:
                return default
        return result if result is not None else default

    lines = []

    # 头部
    lines.append("# Step1 v1.2 实验汇总报告")
    lines.append("")
    lines.append(f"实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"实验项目: {', '.join([r['id'] for r in all_results])}")
    lines.append("")
    lines.append("## 实验背景")
    lines.append("")
    lines.append("v1.1 只测试了7字段JSON输出格式，没有使用 project_structure_detector 和 general.py。")
    lines.append("v1.2 真实调用结构识别 + 把 general.py 压缩成思考约束注入 prompt。")
    lines.append("")
    lines.append("## 重点评估问题")
    lines.append("")
    lines.append("请逐项人工评估，不要自动打分：")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Q1
    lines.append("### Q1: A1 v1.2 的 stance 是否还过度 positive？")
    lines.append("")
    lines.append("**v1.1 stance**: " + safe_get(all_results[0], "v1_1", "key_judgement", "stance"))
    lines.append("**v1.2 stance**: " + safe_get(all_results[0], "v1_2", "key_judgement", "stance"))
    lines.append("")
    lines.append("_请人工评估：v1.2 是否比 v1.1 更谨慎？_")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Q2
    lines.append("### Q2: C1 v1.2 是否能识别「系统集成商而非芯片公司」？")
    lines.append("")
    lines.append("**v1.1 company_essence**: " + safe_get(all_results[2], "v1_1", "company_essence", "是什么"))
    lines.append("**v1.2 company_essence**: " + safe_get(all_results[2], "v1_2", "company_essence", "是什么"))
    lines.append("")
    lines.append("_请人工评估：v1.2 是否比 v1.1 更准确？是否识别到「自称全产业链，实际是系统集成商」？_")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Q3
    lines.append("### Q3: A2 v1.2 是否保持「技术验证/量产缺口」判断？")
    lines.append("")
    lines.append("**v1.1 key_judgement**: " + str(safe_get(all_results[1], "v1_1", "key_judgement", "statement"))[:200])
    lines.append("**v1.2 key_judgement**: " + str(safe_get(all_results[1], "v1_2", "key_judgement", "statement"))[:200])
    lines.append("")
    lines.append("_请人工评估：v1.2 是否保持了 v1.1 对「技术验证阶段、量产缺口」的准确判断？_")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Q4
    lines.append("### Q4: v1.2 是否真的利用了 project_structure_detector？")
    lines.append("")
    for r in all_results:
        ps = r.get("project_structure", {})
        v1_2 = r.get("v1_2", {})
        if isinstance(v1_2, dict) and "error" not in v1_2:
            industry = [t.get("label") for t in ps.get("industry_tags", [])]
            se = v1_2.get("structure_evidence", {})
            lines.append(f"**{r['id']}**:")
            lines.append(f"- 系统识别行业: {', '.join(industry) if industry else '无'}")
            lines.append(f"- v1.2 structure_evidence: {se if se else '(未输出)'}")
            lines.append("")
    lines.append("_请人工评估：v1.2 输出是否与 project_structure_detector 的识别结果一致？是否有矛盾？_")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Q5
    lines.append("### Q5: v1.2 是否比 v1.1 更不容易被 BP 叙事带偏？")
    lines.append("")
    lines.append("_请逐项目对比 v1.1 vs v1.2 的 red_flags 和 business_structure.narrative_business：_")
    lines.append("")
    for r in all_results:
        v1_1 = r.get("v1_1", {})
        v1_2 = r.get("v1_2", {})
        if isinstance(v1_1, dict) and isinstance(v1_2, dict):
            def get_narrative(data_dict, key):
                bs = data_dict.get(key, {})
                if not isinstance(bs, dict):
                    return []
                nb = bs.get("narrative_business", [])
                if not isinstance(nb, list):
                    return []
                return [b.get("name") for b in nb if isinstance(b, dict)]
            v1_1_narrative = get_narrative(v1_1, "business_structure")
            v1_2_narrative = get_narrative(v1_2, "business_structure")
            lines.append(f"**{r['id']}**:")
            lines.append(f"- v1.1 narrative_business: {v1_1_narrative if v1_1_narrative else '无'}")
            lines.append(f"- v1.2 narrative_business: {v1_2_narrative if v1_2_narrative else '无'}")
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 总体评估（请人工填写）")
    lines.append("")
    lines.append("### v1.2 优于 v1.1 的地方")
    lines.append("_请列举_")
    lines.append("")
    lines.append("### v1.2 比 v1.1 更差的地方")
    lines.append("_请列举_")
    lines.append("")
    lines.append("### 是否建议进入阶段二")
    lines.append("- [ ] 是，原因: ")
    lines.append("- [ ] 否，原因: ")
    lines.append("")
    lines.append("### 下一步改进方向")
    lines.append("_请列举_")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Step1 v1.2 实验开始")
    print("(v1.2 = 真实结构识别 + 框架约束)")
    print("=" * 60)

    base_dir, results = run_experiment()

    # 生成各项目对比报告
    for result in results:
        compare_md = generate_project_compare_md(result)
        with open(os.path.join(base_dir, result["id"], "compare.md"), "w", encoding="utf-8") as f:
            f.write(compare_md)

    # 生成汇总报告
    summary_md = generate_summary_md(results)
    with open(os.path.join(base_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\n{'='*60}")
    print(f"实验完成！结果保存在: {base_dir}")
    print(f"{'='*60}")
    print("\n请查看 summary.md 填写人工评估结果。")


if __name__ == "__main__":
    main()
