# -*- coding: utf-8 -*-
"""
Step1 v1.2.1 实验脚本

v1.2 方向认可，但不能进入正式 pipeline。现在做 v1.2.1 小修。

修复4个问题：
1. 输出 schema 强约束 - company_essence 必须是 object
2. 强化 company_essence 的"X 而非 Y"判断
3. 控制 Step1 输出规模（red_flags 最多3条，must_ask_questions 3-5条）
4. 补齐审计文件（prompt_v1_2_1.txt, bp_text.txt, schema_validation.json）

运行：
    python scripts/step1_v1_2_1_experiment.py

输出：
    workspace/step1_v1_2_1_experiment/YYYYMMDD_HHMMSS/
    ├── A1/
    │   ├── step1_v1_2.json
    │   ├── step1_v1_2_1.json
    │   ├── prompt_v1_2_1.txt
    │   ├── bp_text.txt
    │   ├── schema_validation.json
    │   └── compare.md
    ├── A2/...
    ├── C1/...
    ├── compare_v1_2_vs_v1_2_1.md
    └── summary.md
"""

import io
import json
import os
import re
import sys
from datetime import datetime

# 修复 Windows GBK 输出问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from services.deepseek_service import call_deepseek


# ============================================================
# 从 v1.2 复制的函数（避免导入 stdout 冲突）
# ============================================================

def build_step1_v1_2_system_prompt(project_structure: dict) -> str:
    """构建 v1.2 system prompt（复制的 v1.2 版本）"""
    industry_tags = project_structure.get("industry_tags", [])
    business_lines = project_structure.get("business_lines", [])
    business_model_hypotheses = project_structure.get("business_model_hypotheses", [])
    risk_buckets = project_structure.get("risk_buckets", [])
    key_uncertainties = project_structure.get("key_uncertainties", [])

    industry_text = " | ".join([f"{t.get('label','')}({t.get('confidence','')})" for t in industry_tags[:5]])

    current_lines = [b.get("name") for b in business_lines if b.get("role") == "current_business"]
    narrative_lines = [b.get("name") for b in business_lines if b.get("role") not in ["current_business", "supporting_capability"]]
    supporting_lines = [b.get("name") for b in business_lines if b.get("role") == "supporting_capability"]

    models_primary = [m.get("bucket_name") for m in business_model_hypotheses if m.get("role") == "primary"]
    models_secondary = [m.get("bucket_name") for m in business_model_hypotheses if m.get("role") == "secondary"]
    models_narrative = [m.get("bucket_name") for m in business_model_hypotheses if m.get("role") in ["narrative", "risk"]]

    risks = [r.get("bucket_name") for r in risk_buckets]

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
# Step1 v1.2.1（schema 强约束版）
# ============================================================

# general.py 压缩成思考约束
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


def build_step1_v1_2_1_system_prompt(project_structure: dict) -> str:
    """
    构建 v1.2.1 system prompt：
    1. 强 schema 约束（company_essence 必须是 object）
    2. 强化"X 而非 Y"判断
    3. 控制输出规模
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

    # v1.2.1 强 schema 约束
    base_system = """你是一位资深投资人。你的任务是对 BP 形成第一判断：轻量、精准、有观点。

【JSON Schema 强约束 - 必须遵守】
JSON 必须直接输出，不要输出任何解释性文字或格式说明。

字段类型约束：
- company_essence: 必须是 object，包含 {core_identity, not_identity, why_not, confidence}
- business_structure: 必须是 object，包含 {current_business, narrative_business}
- revenue_logic: 必须是 object，包含 {current_money_source, clarity, red_flag_note}
- customer_logic: 必须是 object，包含 {who_pays, why_pays, sustainability}
- key_judgement: 必须是 object，包含 {statement, reasoning, stance}
- red_flags: 必须是 object，包含 {flags: array}，flags 数组最多 3 条
- must_ask_questions: 必须是 object，包含 {questions: array}，questions 数组 3-5 条
- structure_evidence: 必须是 object，包含 {recognized_industry, recognized_business_models, recognized_narratives, step1_vs_detector_gap}

重要规则：
1. 不要照抄 BP 的定位表述，要用自己的判断重新表述。
2. 如果 BP 声称"全产业链/平台/AI/客户合作"，必须判断：这是已验证事实、叙事、还是只是能力延伸。
3. 未验证的内容必须写成"待验证"，不能写死。
4. business_structure 必须区分 current_business 和 narrative_business。
5. stance 只能用：positive_watch / cautious_watch / pass_for_now。
6. red_flags 最多 3 条，只输出最影响项目本质判断的风险。
7. must_ask_questions 3-5 条，每条必须直接对应 company_essence / business_structure / revenue_logic / customer_logic / red_flags 之一。

【company_essence 格式要求】
company_essence.core_identity 必须输出"本质是X，而非BP声称的Y"：
{
  "core_identity": "本质是X（简洁的本质判断）",
  "not_identity": ["不是Y1", "不是Y2"],
  "why_not": "为什么不是BP声称的那个定位",
  "confidence": "high/medium/low"
}

特别规则：
如果 BP 声称"芯片/全产业链/平台/AI/生态"，必须判断：
- 已验证事实：BP中明确列出客户、收入、交付成果的
- 叙事：BP中只描述愿景、能力、接触，没有实际交付的
- 能力延伸：描述技术能力，但没有商业化验证的
"""

    return base_system + structure_section + GENERAL_FRAMEWORK_CONSTRAINTS


# ============================================================
# Schema 验证函数
# ============================================================

def validate_step1_v1_2_1_schema(output: dict) -> dict:
    """
    验证 Step1 v1.2.1 输出是否符合 schema 约束。
    返回验证结果，包含 schema_errors 列表。
    """
    errors = []

    # 检查 company_essence
    ce = output.get("company_essence")
    if ce is None:
        errors.append("company_essence 字段缺失")
    elif not isinstance(ce, dict):
        errors.append(f"company_essence 必须是 object，实际是 {type(ce).__name__}")
    else:
        required_ce_fields = ["core_identity", "not_identity", "why_not", "confidence"]
        for field in required_ce_fields:
            if field not in ce:
                errors.append(f"company_essence.{field} 缺失")
        if not isinstance(ce.get("not_identity"), list):
            errors.append("company_essence.not_identity 必须是 array")

    # 检查 business_structure
    bs = output.get("business_structure")
    if bs is None:
        errors.append("business_structure 字段缺失")
    elif not isinstance(bs, dict):
        errors.append(f"business_structure 必须是 object，实际是 {type(bs).__name__}")
    else:
        if "current_business" not in bs:
            errors.append("business_structure.current_business 缺失")
        if "narrative_business" not in bs:
            errors.append("business_structure.narrative_business 缺失")

    # 检查 red_flags
    rf = output.get("red_flags")
    if rf is None:
        errors.append("red_flags 字段缺失")
    elif not isinstance(rf, dict):
        errors.append(f"red_flags 必须是 object，实际是 {type(rf).__name__}")
    else:
        flags = rf.get("flags", [])
        if not isinstance(flags, list):
            errors.append("red_flags.flags 必须是 array")
        elif len(flags) > 3:
            errors.append(f"red_flags.flags 超过3条，实际 {len(flags)} 条")

    # 检查 must_ask_questions
    maq = output.get("must_ask_questions")
    if maq is None:
        errors.append("must_ask_questions 字段缺失")
    elif not isinstance(maq, dict):
        errors.append(f"must_ask_questions 必须是 object，实际是 {type(maq).__name__}")
    else:
        questions = maq.get("questions", [])
        if not isinstance(questions, list):
            errors.append("must_ask_questions.questions 必须是 array")
        elif len(questions) < 3:
            errors.append(f"must_ask_questions.questions 少于3条，实际 {len(questions)} 条")
        elif len(questions) > 5:
            errors.append(f"must_ask_questions.questions 超过5条，实际 {len(questions)} 条")

    # 检查 structure_evidence
    se = output.get("structure_evidence")
    if se is None:
        errors.append("structure_evidence 字段缺失")
    elif not isinstance(se, dict):
        errors.append(f"structure_evidence 必须是 object，实际是 {type(se).__name__}")

    # 检查其他必需字段
    for field in ["revenue_logic", "customer_logic", "key_judgement"]:
        f = output.get(field)
        if f is None:
            errors.append(f"{field} 字段缺失")
        elif not isinstance(f, dict):
            errors.append(f"{field} 必须是 object，实际是 {type(f).__name__}")

    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "schema_errors": errors
    }


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

def run_project_structure(bp_text: str) -> dict:
    """运行 project_structure_detector"""
    from step3.project_structure_detector import detect_project_structure
    structure = detect_project_structure(bp_text)
    return structure.to_dict()


def run_step1_v1_2(bp_text: str, project_structure: dict) -> dict:
    """运行 v1.2（旧版本，用于对比）"""
    # 使用本地定义的 v1.2 prompt
    system_prompt = build_step1_v1_2_system_prompt(project_structure)
    user_prompt = f"请直接输出JSON，不要任何解释。\n\nBP文本：\n\n{bp_text}"
    raw_output = call_deepseek(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_retries=2
    )
    return parse_json_output(raw_output)


def run_step1_v1_2_1(bp_text: str, project_structure: dict) -> dict:
    """运行 v1.2.1（新版本）"""
    system_prompt = build_step1_v1_2_1_system_prompt(project_structure)
    user_prompt = f"请直接输出JSON，不要任何解释。\n\nBP文本：\n\n{bp_text}"
    raw_output = call_deepseek(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_retries=2
    )
    return parse_json_output(raw_output), system_prompt


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
        PROJECT_ROOT, "workspace", "step1_v1_2_1_experiment",
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

        # 1. project_structure
        print(f"  Running project_structure_detector...")
        project_structure = run_project_structure(bp_text)
        with open(os.path.join(project_dir, "project_structure.json"), "w", encoding="utf-8") as f:
            json.dump(project_structure, ensure_ascii=False, indent=2, fp=f)

        # 2. step1_v1_2（旧版本）
        print(f"  Running step1_v1_2...")
        step1_v1_2 = run_step1_v1_2(bp_text, project_structure)
        with open(os.path.join(project_dir, "step1_v1_2.json"), "w", encoding="utf-8") as f:
            json.dump(step1_v1_2, ensure_ascii=False, indent=2, fp=f)

        # 3. step1_v1_2_1（新版本）
        print(f"  Running step1_v1_2_1 (schema 强约束)...")
        step1_v1_2_1_result = run_step1_v1_2_1(bp_text, project_structure)
        step1_v1_2_1 = step1_v1_2_1_result[0]
        prompt_v1_2_1 = step1_v1_2_1_result[1]

        # 保存审计文件
        with open(os.path.join(project_dir, "step1_v1_2_1.json"), "w", encoding="utf-8") as f:
            json.dump(step1_v1_2_1, ensure_ascii=False, indent=2, fp=f)
        with open(os.path.join(project_dir, "prompt_v1_2_1.txt"), "w", encoding="utf-8") as f:
            f.write(prompt_v1_2_1)
        with open(os.path.join(project_dir, "bp_text.txt"), "w", encoding="utf-8") as f:
            f.write(bp_text)

        # 4. Schema 验证
        schema_validation = validate_step1_v1_2_1_schema(step1_v1_2_1)
        with open(os.path.join(project_dir, "schema_validation.json"), "w", encoding="utf-8") as f:
            json.dump(schema_validation, ensure_ascii=False, indent=2, fp=f)

        print(f"  Schema validation: {'PASS' if schema_validation['valid'] else 'FAIL'}")
        if not schema_validation['valid']:
            print(f"    Errors: {schema_validation['schema_errors'][:3]}")

        print(f"  [OK] Results saved to: {project_dir}")

        all_results.append({
            "id": project["id"],
            "name": project["name"],
            "v1_2": step1_v1_2,
            "v1_2_1": step1_v1_2_1,
            "schema_validation": schema_validation,
            "project_structure": project_structure
        })

    return base_dir, all_results


def generate_project_compare_md(result: dict) -> str:
    """生成单个项目的 v1.2 vs v1.2.1 对比报告"""
    lines = [
        f"# {result['id']} - {result['name']}",
        "",
        "## Schema 验证结果",
        ""
    ]

    sv = result.get("schema_validation", {})
    lines.append(f"- **验证通过**: {'是' if sv.get('valid') else '否'}")
    lines.append(f"- **错误数量**: {sv.get('error_count', 0)}")
    if sv.get("schema_errors"):
        lines.append(f"- **错误列表**: {', '.join(sv.get('schema_errors', []))}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## v1.2 vs v1.2.1 对比")
    lines.append("")
    lines.append(f"### key_judgement.statement")
    lines.append("")
    lines.append(f"| 版本 | stance | 核心判断 |")
    lines.append(f"|------|--------|----------|")

    for label, data in [("v1.2", result.get("v1_2", {})), ("v1.2.1", result.get("v1_2_1", {}))]:
        if not isinstance(data, dict) or "error" in data:
            lines.append(f"| {label} | N/A | {data.get('error', 'N/A')[:50]} |")
            continue
        jg = data.get("key_judgement", {})
        stance = jg.get("stance", "N/A") if isinstance(jg, dict) else "N/A"
        statement = jg.get("statement", "N/A") if isinstance(jg, dict) else "N/A"
        lines.append(f"| {label} | {stance} | {statement[:80] if statement else 'N/A'} |")

    lines.append("")
    lines.append("### company_essence（v1.2.1 新格式）")
    lines.append("")

    v1_2_1 = result.get("v1_2_1", {})
    if isinstance(v1_2_1, dict) and "error" not in v1_2_1:
        ce = v1_2_1.get("company_essence", {})
        if isinstance(ce, dict):
            lines.append(f"- **core_identity**: {ce.get('core_identity', 'N/A')}")
            lines.append(f"- **not_identity**: {ce.get('not_identity', [])}")
            lines.append(f"- **why_not**: {ce.get('why_not', 'N/A')}")
            lines.append(f"- **confidence**: {ce.get('confidence', 'N/A')}")
        else:
            lines.append(f"company_essence 类型错误: {type(ce).__name__}")
    lines.append("")

    # 对比 v1.2
    v1_2 = result.get("v1_2", {})
    if isinstance(v1_2, dict) and "error" not in v1_2:
        ce = v1_2.get("company_essence", {})
        lines.append(f"**v1.2 company_essence**: {type(ce).__name__}")
        if isinstance(ce, dict):
            lines.append(f"- 是什么: {ce.get('是什么', ce.get('core_identity', 'N/A'))}")
            lines.append(f"- 不是什么: {ce.get('不是什么', ce.get('not_identity', []))}")
        else:
            lines.append(f"- (原始内容): {str(ce)[:100]}")
    lines.append("")

    lines.append("### red_flags（v1.2.1 限制最多3条）")
    lines.append("")

    for label, data in [("v1.2", result.get("v1_2", {})), ("v1.2.1", result.get("v1_2_1", {}))]:
        if not isinstance(data, dict) or "error" in data:
            continue
        rf = data.get("red_flags", {})
        if not isinstance(rf, dict):
            lines.append(f"**{label}**: (red_flags not a dict: {type(rf).__name__})")
            continue
        flags = rf.get("flags", [])
        lines.append(f"**{label}** ({len(flags)}条):")
        if isinstance(flags, list):
            for f in flags:
                if isinstance(f, dict):
                    lines.append(f"- {f.get('flag', 'N/A')}")
                else:
                    lines.append(f"- {str(f)[:100]}")
        lines.append("")

    lines.append("### must_ask_questions（v1.2.1 限制3-5条）")
    lines.append("")

    for label, data in [("v1.2", result.get("v1_2", {})), ("v1.2.1", result.get("v1_2_1", {}))]:
        if not isinstance(data, dict) or "error" in data:
            continue
        maq = data.get("must_ask_questions", {})
        if not isinstance(maq, dict):
            lines.append(f"**{label}**: (must_ask_questions not a dict)")
            continue
        questions = maq.get("questions", [])
        lines.append(f"**{label}** ({len(questions)}条):")
        if isinstance(questions, list):
            for q in questions:
                if isinstance(q, dict):
                    related = q.get('related_to', 'N/A')
                    lines.append(f"- {q.get('question', 'N/A')} (related_to: {related})")
                else:
                    lines.append(f"- {str(q)[:100]}")
        lines.append("")

    lines.append("### structure_evidence")
    lines.append("")

    if isinstance(v1_2_1, dict) and "error" not in v1_2_1:
        se = v1_2_1.get("structure_evidence", {})
        if isinstance(se, dict) and se:
            lines.append(f"- recognized_industry: {se.get('recognized_industry', 'N/A')}")
            lines.append(f"- recognized_business_models: {se.get('recognized_business_models', 'N/A')}")
            lines.append(f"- recognized_narratives: {se.get('recognized_narratives', 'N/A')}")
            lines.append(f"- step1_vs_detector_gap: {se.get('step1_vs_detector_gap', 'N/A')}")
        else:
            lines.append("(v1.2.1 未输出或格式错误)")
    lines.append("")

    return "\n".join(lines)


def generate_compare_all_md(all_results: list) -> str:
    """生成所有项目的汇总对比报告"""
    lines = [
        "# v1.2 vs v1.2.1 汇总对比",
        "",
        f"实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]

    for result in all_results:
        lines.append(f"## {result['id']} - {result['name']}")
        lines.append("")

        sv = result.get("schema_validation", {})
        lines.append(f"**Schema 验证**: {'✅ 通过' if sv.get('valid') else '❌ 失败'} ({sv.get('error_count', 0)} 个错误)")

        v1_2_1 = result.get("v1_2_1", {})
        if isinstance(v1_2_1, dict) and "error" not in v1_2_1:
            ce = v1_2_1.get("company_essence", {})
            stance = v1_2_1.get("key_judgement", {}).get("stance", "N/A") if isinstance(v1_2_1.get("key_judgement"), dict) else "N/A"
            rf_count = len(v1_2_1.get("red_flags", {}).get("flags", [])) if isinstance(v1_2_1.get("red_flags"), dict) else "N/A"
            maq_count = len(v1_2_1.get("must_ask_questions", {}).get("questions", [])) if isinstance(v1_2_1.get("must_ask_questions"), dict) else "N/A"

            lines.append(f"**stance**: {stance}")
            lines.append(f"**red_flags 数量**: {rf_count}（限制3条）")
            lines.append(f"**must_ask_questions 数量**: {maq_count}（限制3-5条）")

            if isinstance(ce, dict):
                lines.append(f"**company_essence.core_identity**: {ce.get('core_identity', 'N/A')[:100]}")
                lines.append(f"**company_essence.not_identity**: {ce.get('not_identity', [])}")
            else:
                lines.append(f"**company_essence 类型错误**: {type(ce).__name__}")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_summary_md(all_results: list) -> str:
    """生成验收报告"""

    def safe_get(data, *keys, default="N/A"):
        result = data
        for k in keys:
            if isinstance(result, dict):
                result = result.get(k, default)
            else:
                return default
        return result if result is not None else default

    lines = [
        "# Step1 v1.2.1 验收报告",
        "",
        f"实验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        ""
    ]

    # 1. Schema 稳定性
    lines.append("## 1. Schema 是否稳定")
    lines.append("")
    all_valid = all(r.get("schema_validation", {}).get("valid", False) for r in all_results)
    if all_valid:
        lines.append("✅ **全部通过** - 所有项目均符合 schema 约束")
    else:
        lines.append("❌ **存在失败** - 以下项目存在问题：")
        for r in all_results:
            sv = r.get("schema_validation", {})
            if not sv.get("valid"):
                lines.append(f"  - {r['id']}: {', '.join(sv.get('schema_errors', [])[:2])}")
    lines.append("")

    # 2. A1 stance
    lines.append("## 2. A1 是否保持 cautious_watch")
    lines.append("")
    a1_result = next((r for r in all_results if r["id"] == "A1"), None)
    if a1_result:
        a1_stance = safe_get(a1_result, "v1_2_1", "key_judgement", "stance")
        lines.append(f"**A1 v1.2.1 stance**: {a1_stance}")
        if a1_stance == "cautious_watch":
            lines.append("✅ **通过** - stance 保持为 cautious_watch")
        else:
            lines.append(f"⚠️ **需关注** - stance 为 {a1_stance}，期望 cautious_watch")
    lines.append("")

    # 3. A2 stance
    lines.append("## 3. A2 是否保持技术验证/量产缺口判断")
    lines.append("")
    a2_result = next((r for r in all_results if r["id"] == "A2"), None)
    if a2_result:
        a2_statement = safe_get(a2_result, "v1_2_1", "key_judgement", "statement")
        lines.append(f"**A2 v1.2.1 key_judgement**: {a2_statement[:200] if a2_statement else 'N/A'}")
        if "量产" in str(a2_statement) or "技术验证" in str(a2_statement) or "待验证" in str(a2_statement):
            lines.append("✅ **通过** - 保持了技术验证/量产缺口判断")
        else:
            lines.append("⚠️ **需关注** - 未明确体现技术验证/量产缺口")
    lines.append("")

    # 4. C1 company_essence
    lines.append("## 4. C1 是否达到「模块/电控/系统集成，而非芯片原厂」表达")
    lines.append("")
    c1_result = next((r for r in all_results if r["id"] == "C1"), None)
    if c1_result:
        ce = c1_result.get("v1_2_1", {}).get("company_essence", {})
        core_identity = ce.get("core_identity", "N/A") if isinstance(ce, dict) else str(ce)
        not_identity = ce.get("not_identity", []) if isinstance(ce, dict) else []
        why_not = ce.get("why_not", "N/A") if isinstance(ce, dict) else "N/A"

        lines.append(f"**core_identity**: {core_identity}")
        lines.append(f"**not_identity**: {not_identity}")
        lines.append(f"**why_not**: {why_not[:200] if why_not else 'N/A'}")

        # 判断是否达标
        keywords = ["模块", "电控", "系统集成", "集成商", "芯片原厂", "全产业链"]
        found = any(kw in str(core_identity) or kw in str(not_identity) or kw in str(why_not) for kw in keywords)
        if found:
            lines.append("✅ **通过** - 表达了模块/电控/系统集成，而非芯片原厂的判断")
        else:
            lines.append("⚠️ **需关注** - 未明确体现「模块/电控/系统集成，而非芯片原厂」")
    lines.append("")

    # 5. red_flags 数量
    lines.append("## 5. red_flags 是否严格控制为 3 条")
    lines.append("")
    for r in all_results:
        rf = r.get("v1_2_1", {}).get("red_flags", {})
        flags = rf.get("flags", []) if isinstance(rf, dict) else []
        status = "✅" if len(flags) <= 3 else "❌"
        lines.append(f"- **{r['id']}**: {status} {len(flags)} 条")
    lines.append("")

    # 6. 是否建议下一步
    lines.append("## 6. 是否建议接入 Step3 实验")
    lines.append("")
    schema_pass = all(r.get("schema_validation", {}).get("valid", False) for r in all_results)
    a1_pass = safe_get(a1_result, "v1_2_1", "key_judgement", "stance") == "cautious_watch" if a1_result else False
    c1_pass = any(
        kw in str(c1_result.get("v1_2_1", {}).get("company_essence", {}).get("core_identity", ""))
        for kw in ["模块", "电控", "系统集成", "集成商"]
    ) if c1_result else False

    if schema_pass and a1_pass:
        lines.append("✅ **建议下一步** - Schema 稳定，A1 stance 正确")
        if c1_pass:
            lines.append("✅ C1 判断准确")
    else:
        lines.append("⚠️ **暂不建议** - 存在问题需要修复")
        if not schema_pass:
            lines.append("  - Schema 验证有失败")
        if not a1_pass:
            lines.append("  - A1 stance 未保持 cautious_watch")
        if not c1_pass:
            lines.append("  - C1 判断不够准确")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 详细数据")
    lines.append("")
    for r in all_results:
        lines.append(f"### {r['id']} - {r['name']}")
        lines.append("")
        lines.append(f"```json")
        lines.append(json.dumps(r.get("v1_2_1", {}), ensure_ascii=False, indent=2))
        lines.append(f"```")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Step1 v1.2.1 实验开始")
    print("(Schema 强约束 + X 而非 Y 判断 + 输出规模控制)")
    print("=" * 60)

    base_dir, results = run_experiment()

    # 生成各项目对比报告
    for result in results:
        compare_md = generate_project_compare_md(result)
        with open(os.path.join(base_dir, result["id"], "compare.md"), "w", encoding="utf-8") as f:
            f.write(compare_md)

    # 生成汇总对比报告
    compare_all_md = generate_compare_all_md(results)
    with open(os.path.join(base_dir, "compare_v1_2_vs_v1_2_1.md"), "w", encoding="utf-8") as f:
        f.write(compare_all_md)

    # 生成验收报告
    summary_md = generate_summary_md(results)
    with open(os.path.join(base_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\n{'='*60}")
    print(f"实验完成！结果保存在: {base_dir}")
    print(f"{'='*60}")
    print("\n请查看 summary.md 确认验收结果。")


if __name__ == "__main__":
    main()
