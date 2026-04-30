# -*- coding: utf-8 -*-
"""
Step3 v3 实验脚本（基于 Step2 外部约束的 BP 叙事审查）

实验目标：验证 Step3 是否真正使用 Step2 约束审查 BP 叙事

输入：
  - step1_v1_2_1.json
  - project_structure.json
  - bp_text.txt
  - step2_external_check_v2_2_2.json（最新版本）

输出：
  - step3_exp.json
  - prompt_step3.txt
  - summary.md
  - validation.json

实验项目：
  - A1（仅此一项，节约 token）

验证点：
  1. Step3 是否引用 Step2（不是只看 BP）
  2. 是否识别"BP是否绕过关键约束"
  3. 是否减少纯 BP 复述
  4. 是否没有重新定义公司
  5. 是否输出具体而不是泛泛
"""

import sys
import io
import json
import os
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from step3.step3_service import run_step3_simple
from step3.step3_schema import Step3Output


# ============================================================
# Schema Validation
# ============================================================

def validate_step3_schema(output: dict) -> dict:
    """验证 Step3 v3 输出 schema"""
    errors = []

    required_fields = ["consistency_checks", "tensions", "overpackaging_signals", "summary"]
    for field in required_fields:
        if field not in output:
            errors.append(f"Missing required field: {field}")

    # consistency_checks 必须有新增字段
    cc_list = output.get("consistency_checks", [])
    if isinstance(cc_list, list) and len(cc_list) > 0:
        first = cc_list[0]
        if "related_step2_check" not in first:
            errors.append("consistency_checks missing related_step2_check field")
        if "external_constraint" not in first:
            errors.append("consistency_checks missing external_constraint field")
        if "bp_claim_checked" not in first:
            errors.append("consistency_checks missing bp_claim_checked field")

    # overpackaging_signals 必须有新增字段
    ops_list = output.get("overpackaging_signals", [])
    if isinstance(ops_list, list) and len(ops_list) > 0:
        first = ops_list[0]
        if "related_step2_constraint" not in first:
            errors.append("overpackaging_signals missing related_step2_constraint field")
        if "packaging_type" not in first:
            errors.append("overpackaging_signals missing packaging_type field")

    # tensions 必须有新增字段
    t_list = output.get("tensions", [])
    if isinstance(t_list, list) and len(t_list) > 0:
        first = t_list[0]
        if "related_step2_logic" not in first:
            errors.append("tensions missing related_step2_logic field")
        if "conflict_type" not in first:
            errors.append("tensions missing conflict_type field")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "checked_at": datetime.now().isoformat()
    }


# ============================================================
# Step3 Experiment
# ============================================================

def run_step3_experiment(
    project_dir: Path,
    output_dir: Path,
    project_name: str,
) -> dict:
    """运行单个项目的 Step3 实验"""

    print(f"\n{'='*50}")
    print(f"Project: {project_name}")
    print(f"{'='*50}")

    # ── Load inputs ────────────────────────────────────────────────────────────
    bp_path = project_dir / "bp_text.txt"
    step1_path = project_dir / "step1_v1_2_1.json"
    ps_path = project_dir / "project_structure.json"

    # Try multiple Step2 locations (newest first)
    step2_candidates = [
        project_dir.parent / "step2_external_check_v222" / project_name / "step2_external_check_v2_2_2.json",
        project_dir.parent.parent / "step2_external_check_v222" / project_name / "step2_external_check_v2_2_2.json",
    ]
    step2_path = None
    for candidate in step2_candidates:
        if candidate.exists():
            step2_path = candidate
            break

    if not bp_path.exists():
        return {"error": f"bp_text.txt not found at {bp_path}"}
    if not step1_path.exists():
        return {"error": f"step1_v1_2_1.json not found at {step1_path}"}
    if not ps_path.exists():
        return {"error": f"project_structure.json not found at {ps_path}"}
    if not step2_path:
        return {"error": f"step2_external_check_v2_2_2.json not found in any candidate path"}

    with open(bp_path, "r", encoding="utf-8") as f:
        bp_text = f.read()

    with open(step1_path, "r", encoding="utf-8") as f:
        step1_data = json.load(f)

    with open(ps_path, "r", encoding="utf-8") as f:
        project_structure = json.load(f)

    with open(step2_path, "r", encoding="utf-8") as f:
        step2_data = json.load(f)

    print(f"  BP length: {len(bp_text)} chars")
    print(f"  Step1 stance: {step1_data.get('key_judgement', {}).get('stance', 'N/A')}")
    print(f"  Step2 version: {step2_data.get('schema_version', 'N/A')}")
    print(f"  Step2 caution count: {step2_data.get('step1_external_check', {}).get('summary', {}).get('caution_count', 'N/A')}")

    # ── Run Step3 ──────────────────────────────────────────────────────────
    print(f"\n  Running Step3 v3...")

    step3_output = run_step3_simple(
        bp_text=bp_text,
        project_structure=project_structure,
        step2_json=step2_data,
        investment_modules=None,
    )

    # ── Validate schema ────────────────────────────────────────────────────
    schema_validation = validate_step3_schema(step3_output)
    print(f"  Schema valid: {'PASS' if schema_validation['valid'] else 'FAIL'}")
    if not schema_validation['valid']:
        for err in schema_validation['errors']:
            print(f"    - {err}")

    # ── Save outputs ──────────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "step3_exp.json", "w", encoding="utf-8") as f:
        json.dump(step3_output, f, ensure_ascii=False, indent=2)

    # Save validation
    with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
        json.dump(schema_validation, f, ensure_ascii=False, indent=2)

    # ── Build summary ──────────────────────────────────────────────────────
    summary = build_summary(project_name, step1_data, step2_data, step3_output)
    with open(output_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"\n  Step3 output:")
    print(f"  - consistency_checks: {len(step3_output.get('consistency_checks', []))}")
    print(f"  - tensions: {len(step3_output.get('tensions', []))}")
    print(f"  - overpackaging_signals: {len(step3_output.get('overpackaging_signals', []))}")
    print(f"  - summary: {step3_output.get('summary', '')[:80]}")
    print(f"  - step2_constraints_used: {step3_output.get('step2_constraints_used', 0)}")
    print(f"  - step2_caution_references: {step3_output.get('step2_caution_references', 0)}")

    return {
        "project_name": project_name,
        "step3_output": step3_output,
        "schema_valid": schema_validation["valid"],
        "schema_errors": schema_validation.get("errors", []),
    }


def build_summary(
    project_name: str,
    step1_data: dict,
    step2_data: dict,
    step3_output: dict,
) -> str:
    """构建实验 summary"""

    step1_essence = step1_data.get("company_essence", {})
    step1_stance = step1_data.get("key_judgement", {}).get("stance", "unknown")

    step2_summary = step2_data.get("step1_external_check", {}).get("summary", {})
    step2_version = step2_data.get("schema_version", "")

    cc_list = step3_output.get("consistency_checks", [])
    ops_list = step3_output.get("overpackaging_signals", [])
    t_list = step3_output.get("tensions", [])

    # 统计 Step2 引用情况
    cc_with_step2_ref = sum(1 for c in cc_list if c.get("related_step2_check"))
    cc_contradict = sum(1 for c in cc_list if c.get("judgement") == "contradict")
    cc_uncertain = sum(1 for c in cc_list if c.get("judgement") == "uncertain")

    ops_with_step2_ref = sum(1 for o in ops_list if o.get("related_step2_constraint"))
    ops_packaging_types = [o.get("packaging_type", o.get("type", "")) for o in ops_list]

    t_with_step2_ref = sum(1 for t in t_list if t.get("related_step2_logic"))
    t_conflict_types = [t.get("conflict_type", "") for t in t_list]

    # 验证点
    v1_step2_ref = cc_with_step2_ref > 0 or ops_with_step2_ref > 0 or t_with_step2_ref > 0
    v2_constraint_bypass = any(
        c.get("gap", "").lower() in ["跳过", "未回应", "未提及", "忽略", "bypass", "skip"]
        or len(c.get("gap", "")) > 20
        for c in cc_list
    )
    v3_no_repeat = len(cc_list) > 0 and all(
        len(c.get("claim", "")) < 200 for c in cc_list
    )
    v4_no_redefine = True  # 通过 summary 判断是否重新定义了公司
    v5_specific = len(step3_output.get("summary", "")) > 10

    # 检查是否有重新定义公司本质（精确短语，不含误判词）
    summary_text = step3_output.get("summary", "")
    redefine_keywords = ["本质是", "本质为", "其实是", "实际上是"]
    v4_no_redefine = not any(kw in summary_text for kw in redefine_keywords)

    md = f"""# Step3 v3 实验报告

**项目**: {project_name}
**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Step2 版本**: {step2_version}

---

## 1. 项目基本信息

| 信息 | 值 |
|------|-----|
| Step1 stance | {step1_stance} |
| Step2 caution count | {step2_summary.get('caution_count', 'N/A')} |
| Step2 contradict count | {step2_summary.get('contradict_count', 'N/A')} |

## 2. Step3 v3 输出统计

| 字段 | 数量 |
|------|------|
| consistency_checks | {len(cc_list)} |
| tensions | {len(t_list)} |
| overpackaging_signals | {len(ops_list)} |

**Step2 引用统计**:
- consistency_checks 中引用 Step2: {cc_with_step2_ref}/{len(cc_list)}
- tensions 中引用 Step2: {t_with_step2_ref}/{len(t_list)}
- overpackaging_signals 中引用 Step2: {ops_with_step2_ref}/{len(ops_list)}
- step2_constraints_used: {step3_output.get('step2_constraints_used', 0)}

## 3. 核心判断

**Summary**: {step3_output.get('summary', '')}

## 4. 验证点检查

| 验证点 | 结果 | 说明 |
|--------|------|------|
| V1: Step3 引用 Step2 | {'PASS' if v1_step2_ref else 'FAIL'} | cc_step2_ref={cc_with_step2_ref}, ops_step2_ref={ops_with_step2_ref}, t_step2_ref={t_with_step2_ref} |
| V2: 识别 BP 绕过关键约束 | {'PASS' if v2_constraint_bypass else 'FAIL'} | 检查 consistency_checks.gap 是否有约束未回应相关内容 |
| V3: 减少纯 BP 复述 | {'PASS' if v3_no_repeat else 'FAIL'} | 所有 claim 字段均在 200 字以内 |
| V4: 没有重新定义公司 | {'PASS' if v4_no_redefine else 'FAIL'} | summary 中无"本质是/本质为"等重新定义表述 |
| V5: 输出具体而非泛泛 | {'PASS' if v5_specific else 'FAIL'} | summary 长度={len(step3_output.get('summary', ''))} |

## 5. consistency_checks 详情

"""
    for i, check in enumerate(cc_list, 1):
        md += f"""
### 检查 {i}: {check.get('topic', '')}

- **BP 说法**: {check.get('claim', '')[:100]}
- **判断**: {check.get('judgement', '').upper()}
- **引用 Step2**: {check.get('related_step2_check', '(无)')}
- **外部约束**: {check.get('external_constraint', '(无)')[:100]}
- **gap**: {check.get('gap', '')[:100]}
"""
    md += f"""
## 6. overpackaging_signals 详情

"""
    for i, sig in enumerate(ops_list, 1):
        md += f"""
### 信号 {i}: {sig.get('signal', '')}

- **类型**: {sig.get('type', '')}
- **细分包装类型**: {sig.get('packaging_type', '(无)')}
- **关联 Step2 约束**: {sig.get('related_step2_constraint', '(无)')[:100]}
- **严重程度**: {sig.get('severity', '')}
"""

    md += f"""
## 7. tensions 详情

"""
    for i, t in enumerate(t_list, 1):
        md += f"""
### 矛盾 {i}: {t.get('tension', '')}

- **冲突类型**: {t.get('conflict_type', '')}
- **关联 Step2 逻辑**: {t.get('related_step2_logic', '(无)')[:100]}
- **为何重要**: {t.get('why_it_matters', '')[:100]}
- **严重程度**: {t.get('severity', '')}
"""

    md += f"""
---

## 8. 结论

**总体评估**: {'PASS' if all([v1_step2_ref, v2_constraint_bypass, v4_no_redefine, v5_specific]) else 'NEEDS_IMPROVEMENT'}

**关键发现**:
1. Step3 是否引用了 Step2 约束: {'是' if v1_step2_ref else '否'}
2. Step3 是否识别了 BP 绕过关键约束: {'是' if v2_constraint_bypass else '否'}
3. Step3 是否减少了纯 BP 复述: {'是' if v3_no_repeat else '否'}
4. Step3 是否重新定义了公司: {'否 (好)' if v4_no_redefine else '是 (需修复)'}
5. Step3 输出是否具体: {'是' if v5_specific else '否'}

**建议**:
- V1 FAIL → 检查 prompt 是否正确传递了 Step2 数据
- V2 FAIL → 增加对 caution/decision_blocker 的显式引用
- V3 FAIL → prompt 中要求不要复述 BP
- V4 FAIL → 强调"不允许重新定义公司本质"
- V5 FAIL → summary 改为更具体的表述
"""

    return md


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Step3 v3 Experiment")
    print(f"Timestamp: {timestamp}")
    print(f"Project root: {project_root}")

    # 使用最新的 step2 实验数据
    v121_workspace = project_root / "workspace" / "step1_v1_2_1_experiment"

    # 找最新实验
    experiments = sorted([d for d in v121_workspace.iterdir() if d.is_dir()], reverse=True)
    if not experiments:
        print("ERROR: No experiment data found")
        exit(1)

    latest_exp = experiments[0]
    print(f"Latest experiment: {latest_exp.name}")

    # 实验输出目录
    exp_workspace = latest_exp / f"step3_v3_experiment_{timestamp}"
    exp_workspace.mkdir(parents=True, exist_ok=True)

    # 只跑 A2 和 C1
    projects = ["A2", "C1"]

    results = []
    for project_name in projects:
        project_dir = latest_exp / project_name
        output_dir = exp_workspace / project_name

        if not project_dir.exists():
            print(f"Project {project_name} not found at {project_dir}")
            continue

        result = run_step3_experiment(project_dir, output_dir, project_name)
        results.append(result)

    print(f"\n{'='*50}")
    print(f"Experiment complete!")
    print(f"Output: {exp_workspace}")
    for r in results:
        status = "OK" if not r.get("error") else f"ERR: {r.get('error')}"
        schema = "PASS" if r.get("schema_valid") else "FAIL"
        print(f"  {r.get('project_name', '?')}: {status}, schema={schema}")
