# -*- coding: utf-8 -*-
"""
Step2 External Check Experiment (Step3 v2.2)

验证 Step3 v2.2 设计:
1. external_investment_logic 是否绑定 Step1
2. bp_usage_audit 是否干净
3. knowledge_source 是否有统计
4. 是否不重新定义公司本质

输入: step1_v1_2_1.json, project_structure.json, bp_text
输出: step2_external_check.json, prompt_step2.txt, bp_usage_audit.json,
      schema_validation.json, compare.md, summary.md
"""

import sys
import io
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.deepseek_service import call_deepseek

# ============================================================
# Step2 v2.2 Schema
# ============================================================

STEP2_SCHEMA_V2_2 = {
    "schema_version": "v2.2",
    "external_investment_logic": [
        {
            "related_to_step1": "company_essence | revenue_logic | customer_logic | red_flags | key_judgement | business_structure",
            "bucket_key": "tech_barrier | customer_value | commercialization | expansion_story | team_credibility",
            "knowledge_source": "general_bucket | industry_bucket | llm_common_sense",
            "logic_statement": "For Step1 field, external logic...",
            "implication": "support | caution | contradict",
            "why_it_matters": "Why this matters for investment"
        }
    ],
    "step1_external_check": {
        "checks": [
            {
                "step1_field": "company_essence | revenue_logic | ...",
                "step1_claim": "Step1 claim content",
                "bucket_key": "tech_barrier | ...",
                "knowledge_source": "general_bucket | industry_bucket | llm_common_sense",
                "external_logic": "External logic for this claim",
                "verdict": "support | caution | contradict",
                "reasoning": "Reasoning",
                "evidence_source": "Industry knowledge | Investment logic | Tech commercialization",
                "confidence": "high | medium | low"
            }
        ],
        "summary": {
            "support_count": 0,
            "caution_count": 0,
            "contradict_count": 0
        }
    },
    "information_resolution": {
        "publicly_resolvable": [],
        "founder_needed": [],
        "decision_blockers": []
    },
    "tensions": [],
    "step1_adjustment_hints": {
        "reinforce": [],
        "weaken": [],
        "needs_verification": []
    },
    "bp_usage_audit": {
        "bp_used_for": "claim_verification_only | not_used",
        "bp_claims_checked": [],
        "bp_claims_not_used_as_fact": [],
        "violations": [],
        "bp_text_tokens_used": 0,
        "is_clean": True
    },
    "meta": {
        "buckets_analyzed": [],
        "industry_tags_used": [],
        "bucket_as_checklist": True,
        "knowledge_source_breakdown": {
            "general_bucket": 0,
            "industry_bucket": 0,
            "llm_common_sense": 0
        },
        "external_logic_sources": ["Industry knowledge", "Investment logic", "Tech commercialization"],
        "new_conclusion_generated": False,
        "step1_fields_covered": []
    }
}


# ============================================================
# Bucket Loading
# ============================================================

def load_buckets_for_step2(step1_data: dict, project_structure: dict) -> str:
    """Load bucket specs for prompt"""
    from step3.bucket_registry import GENERAL_BUCKETS
    from step3.industry_loader import load_industry_enhancements

    industry_tags = project_structure.get("industry_tags", [])
    industries = []
    for tag in industry_tags[:3]:
        if isinstance(tag, dict) and tag.get("confidence") == "high":
            industries.append(tag.get("label", ""))

    bucket_specs = ["[General Investment Framework Buckets]\n"]

    for bucket_key, bucket_def in GENERAL_BUCKETS.items():
        bucket_specs.append(f"[bucket_key: {bucket_key}]")
        bucket_specs.append(f"label: {bucket_def.label}")
        bucket_specs.append(f"description: {bucket_def.description}")
        bucket_specs.append("Required checks:")
        for check in bucket_def.common_checks:
            bucket_specs.append(f"  - {check}")
        bucket_specs.append("")

    # Load industry enhancements
    for industry in industries:
        industry_lower = industry.lower()
        industry_map = {
            "自动驾驶": "autonomous_driving",
            "新能源": "new_energy",
            "半导体": "semiconductor",
            "新材料": "advanced_materials",
            "商业航天": "commercial_space",
        }
        industry_key = industry_map.get(industry, industry_lower)
        enhancements = load_industry_enhancements(industry_key)
        if enhancements:
            bucket_specs.append(f"\n[Industry Enhancement: {industry}]")
            if "prompt_guidance" in enhancements:
                bucket_specs.append(enhancements["prompt_guidance"])
            if "red_flags" in enhancements:
                bucket_specs.append("\nIndustry red flags:")
                for flag in enhancements["red_flags"][:5]:
                    bucket_specs.append(f"  - {flag}")

    return "\n".join(bucket_specs)


# ============================================================
# Build Step2 Prompt
# ============================================================

def build_step2_prompt(step1_data: dict, project_structure: dict, bp_text: str) -> str:
    """Build Step2 v2.2 system prompt"""

    step1_text = f"""
[Step1 v1.2.1 Output]

company_essence:
{json.dumps(step1_data.get("company_essence", {}), ensure_ascii=False, indent=2)}

business_structure:
{json.dumps(step1_data.get("business_structure", {}), ensure_ascii=False, indent=2)}

key_judgement:
{json.dumps(step1_data.get("key_judgement", {}), ensure_ascii=False, indent=2)}

red_flags:
{json.dumps(step1_data.get("red_flags", {}), ensure_ascii=False, indent=2)}

must_ask_questions:
{json.dumps(step1_data.get("must_ask_questions", {}), ensure_ascii=False, indent=2)}
"""

    structure_text = f"""
[Project Structure Summary]

Industry: {', '.join([t.get('label', '') for t in project_structure.get('industry_tags', [])[:5]])}

Business Lines:
{json.dumps(project_structure.get('business_lines', []), ensure_ascii=False, indent=2)}

Business Model Hypotheses:
{json.dumps(project_structure.get('business_model_hypotheses', []), ensure_ascii=False, indent=2)}

Risk Buckets:
{json.dumps(project_structure.get('risk_buckets', []), ensure_ascii=False, indent=2)}
"""

    bucket_specs = load_buckets_for_step2(step1_data, project_structure)

    prompt = f"""You are in Step2: External Industry/Investment Logic Validation Layer.

Your task:
NOT to analyze the project, but to use the "how should this type of project be evaluated" external perspective
to validate whether Step1's judgments are sound.

[Core Constraints]
- BP text = unverified company claims, NOT facts
- Your judgment basis = industry common sense, investment logic, tech commercialization patterns
- Step1 = your INPUT, not your OUTPUT
- You CANNOT override Step1, only reinforce / weaken / needs_verification

[Hard Constraint - NO New Conclusions]
- PROHIBITED: output any new "company essence judgment"
- PROHIBITED: write "this company is X" or "essentially belongs to X"
- All judgments MUST cite: specific Step1 fields, or external logic
- Your output is "validation result", NOT "new company analysis"

[BP Usage Rules]
BP text = unverified company claims, NOT facts.
BP text can ONLY be used for: verifying if Step1 claims match BP.
PROHIBITED: re-analyze project, support new conclusions.

[Forbidden BP Claims (MUST track in bp_usage_audit)]
- Company self-claimed titles (e.g., "full industry chain", "chip manufacturer", "platform")
- Customer relationships ("already partnered with XX leading customer")
- Technical capabilities ("achieved XX technical breakthrough")
- Market position ("only one in China", "industry leader")
- Strategic partnerships ("established strategic partnership with XX")

[Bucket Usage Rules]
Buckets are NOT "reference knowledge" but "mandatory checklist".
For each bucket_key, you MUST check:
1. Whether key validation points are satisfied
2. Whether common failure modes are triggered
3. Whether common packaging signals appear

Write results to external_investment_logic and step1_external_check.

[knowledge_source Labeling Requirement]
Each external_investment_logic and step1_external_check.checks MUST label knowledge source:
- general_bucket: from general bucket (general.py)
- industry_bucket: from industry enhancement bucket (industries/*.py)
- llm_common_sense: only from LLM general knowledge

============================================
[Input 1: Step1 v1.2.1 Output]
============================================
{step1_text}
============================================
[Input 2: Project Structure Summary]
============================================
{structure_text}
============================================
[Input 3: Bucket/Industry Knowhow (Mandatory Checklist)]
============================================
{bucket_specs}
============================================
[Input 4: BP Text (Strictly Limited)]
============================================
{bp_text[:3000]}
[Usage constraint: only for verifying Step1 claims, NOT for reasoning]
============================================
[Required JSON Output]
============================================

Please output complete JSON, must include all fields:
- external_investment_logic (MUST bind to Step1)
- step1_external_check (MUST cite Step1 fields)
- information_resolution (questions MUST come from Step1)
- tensions (conflicts MUST cite Step1 position)
- step1_adjustment_hints (cite step1_external_check results)
- bp_usage_audit (track ALL BP usage)
- meta (include knowledge_source_breakdown)

JSON Output:
"""

    return prompt


# ============================================================
# Schema Validation
# ============================================================

def validate_step2_schema(output: dict) -> dict:
    """Validate Step2 v2.2 output schema"""
    errors = []

    required_fields = [
        "schema_version", "external_investment_logic", "step1_external_check",
        "information_resolution", "tensions", "step1_adjustment_hints",
        "bp_usage_audit", "meta"
    ]
    for field in required_fields:
        if field not in output:
            errors.append(f"Missing required field: {field}")

    if "external_investment_logic" in output:
        eil = output["external_investment_logic"]
        if not isinstance(eil, list):
            errors.append("external_investment_logic must be an array")
        else:
            for i, item in enumerate(eil):
                if "related_to_step1" not in item:
                    errors.append(f"external_investment_logic[{i}] missing related_to_step1")
                if "knowledge_source" not in item:
                    errors.append(f"external_investment_logic[{i}] missing knowledge_source")

    if "step1_external_check" in output:
        sec = output["step1_external_check"]
        if "checks" in sec and isinstance(sec["checks"], list):
            for i, check in enumerate(sec["checks"]):
                if "step1_field" not in check:
                    errors.append(f"step1_external_check.checks[{i}] missing step1_field")
                if "knowledge_source" not in check:
                    errors.append(f"step1_external_check.checks[{i}] missing knowledge_source")

    if "bp_usage_audit" in output:
        bp_audit = output["bp_usage_audit"]
        if "is_clean" not in bp_audit:
            errors.append("bp_usage_audit missing is_clean field")

    if "meta" in output:
        meta = output["meta"]
        if "knowledge_source_breakdown" not in meta:
            errors.append("meta missing knowledge_source_breakdown")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "checked_at": datetime.now().isoformat()
    }


# ============================================================
# Run Step2
# ============================================================

def run_step2(
    step1_data: dict,
    project_structure: dict,
    bp_text: str,
    deepseek_model: str = "deepseek-chat"
) -> dict:
    """Run Step2 external logic validation"""

    prompt = build_step2_prompt(step1_data, project_structure, bp_text)

    # Build system prompt for context
    system_prompt = """You are an expert investment analyst. Output valid JSON only."""
    user_prompt = prompt

    # Call DeepSeek API
    content = call_deepseek(system_prompt, user_prompt, model=deepseek_model)

    try:
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        else:
            json_str = content.strip()

        output = json.loads(json_str)
    except json.JSONDecodeError as e:
        output = {
            "error": f"JSON parse failed: {str(e)}",
            "raw_content": content[:2000]
        }

    return {
        "prompt": prompt,
        "output": output
    }


# ============================================================
# Generate Compare Report
# ============================================================

def generate_compare_md(
    project_name: str,
    step1_data: dict,
    step2_data: dict,
    schema_validation: dict
) -> str:
    """Generate comparison report"""

    md = f"""# Step2 External Check Comparison Report

**Project**: {project_name}
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 1. Schema Validation

| Check | Result |
|-------|--------|
| Valid | {'PASS' if schema_validation.get('valid') else 'FAIL'} |
| Errors | {len(schema_validation.get('errors', []))} |

"""
    if schema_validation.get('errors'):
        md += "**Error Details**:\n"
        for err in schema_validation['errors']:
            md += f"- {err}\n"
        md += "\n"

    step1_essence = step1_data.get("company_essence", {})
    step1_stance = step1_data.get("key_judgement", {}).get("stance", "unknown")

    md += f"""## 2. Step1 vs Step2 Comparison

### Step1 Judgment
- **core_identity**: {step1_essence.get("core_identity", "N/A")}
- **not_identity**: {', '.join(step1_essence.get("not_identity", [])[:2])}
- **stance**: {step1_stance}

"""

    if "step1_external_check" in step2_data:
        sec = step2_data["step1_external_check"]
        summary = sec.get("summary", {}) if isinstance(sec, dict) else {}
        if isinstance(summary, dict):
            md += f"""### Step2 Validation Results
- **Support**: {summary.get('support_count', 0)}
- **Caution**: {summary.get('caution_count', 0)}
- **Contradict**: {summary.get('contradict_count', 0)}

"""
        if "checks" in sec and sec["checks"]:
            md += "**Main Validation Conclusions**:\n"
            for check in sec["checks"][:3]:
                verdict = check.get("verdict", "?")
                step1_field = check.get("step1_field", "?")
                reasoning = check.get("reasoning", "")[:100]
                md += f"- [{verdict.upper()}] {step1_field}: {reasoning}...\n"
            md += "\n"

    if "bp_usage_audit" in step2_data and isinstance(step2_data["bp_usage_audit"], dict):
        bp_audit = step2_data["bp_usage_audit"]
        is_clean = bp_audit.get("is_clean", False)
        violations = bp_audit.get("violations", []) if isinstance(bp_audit, dict) else []

        md += f"""## 3. BP Usage Audit

| Check | Result |
|-------|--------|
| BP Used For | {bp_audit.get('bp_used_for', 'N/A')} |
| is_clean | {'CLEAN' if is_clean else 'HAS ISSUES'} |
| violations | {len(violations)} |

"""
        if violations:
            md += "**Violation Details**:\n"
            for v in violations:
                md += f"- [{v.get('severity', '?')}] {v.get('type', '?')}: {v.get('description', '')}\n"
            md += "\n"

    if "meta" in step2_data and "knowledge_source_breakdown" in step2_data["meta"]:
        ksb = step2_data["meta"]["knowledge_source_breakdown"]
        try:
            total = sum(int(v) for v in ksb.values() if isinstance(v, (int, str)))
        except (TypeError, ValueError):
            total = 0

        def safe_int(val, default=0):
            try:
                if isinstance(val, list):
                    return len(val)
                return int(val)
            except (TypeError, ValueError):
                return default

        gb = safe_int(ksb.get('general_bucket', 0))
        ib = safe_int(ksb.get('industry_bucket', 0))
        llm = safe_int(ksb.get('llm_common_sense', 0))
        total = gb + ib + llm

        md += f"""## 4. Knowledge Source Statistics

| Source | Count | Ratio |
|--------|-------|-------|
| general_bucket | {gb} | {gb/max(total,1)*100:.0f}% |
| industry_bucket | {ib} | {ib/max(total,1)*100:.0f}% |
| llm_common_sense | {llm} | {llm/max(total,1)*100:.0f}% |

"""

    if "step1_adjustment_hints" in step2_data and isinstance(step2_data["step1_adjustment_hints"], dict):
        hints = step2_data["step1_adjustment_hints"]
        md += """## 5. Step1 Adjustment Hints

"""
        if hints.get("reinforce") and isinstance(hints.get("reinforce"), list):
            md += "**Reinforce**:\n"
            for r in hints["reinforce"][:3]:
                md += f"- {str(r)[:100]}...\n"
            md += "\n"

        if hints.get("weaken") and isinstance(hints.get("weaken"), list):
            md += "**Weaken**:\n"
            for w in hints["weaken"][:3]:
                md += f"- {str(w)[:100]}...\n"
            md += "\n"

        if hints.get("needs_verification") and isinstance(hints.get("needs_verification"), list):
            md += "**Needs Verification**:\n"
            for nv in hints["needs_verification"][:3]:
                md += f"- {nv[:100]}...\n"
            md += "\n"

    return md


# ============================================================
# Generate Summary
# ============================================================

def generate_summary(all_results: list) -> str:
    """Generate experiment summary"""

    total = len(all_results)
    schema_pass = sum(1 for r in all_results if r.get("schema_valid"))
    bp_clean = sum(1 for r in all_results if r.get("bp_is_clean"))
    has_knowledge_breakdown = sum(
        1 for r in all_results
        if r.get("step2_data", {}).get("meta", {}).get("knowledge_source_breakdown")
    )

    md = f"""# Step2 External Check Experiment Summary

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Version**: v2.2

---

## Experiment Results Overview

| Metric | Result |
|--------|--------|
| Test Projects | {total} |
| Schema Valid | {schema_pass}/{total} |
| BP Clean | {bp_clean}/{total} |
| Has knowledge_source Stats | {has_knowledge_breakdown}/{total} |

---

## Validation Dimensions

### 1. Strictly Around Step1, No Company Redefinition

"""
    for result in all_results:
        project = result["project_name"]
        step2 = result.get("step2_data", {})
        new_conclusion = step2.get("meta", {}).get("new_conclusion_generated", False)
        eil_related = all(
            "related_to_step1" in item
            for item in step2.get("external_investment_logic", [])
        )
        md += f"- **{project}**: new_conclusion={new_conclusion}, related_to_step1={eil_related}\n"

    md += """

### 2. BP Only Used for Claim Verification

"""
    for result in all_results:
        project = result["project_name"]
        step2 = result.get("step2_data", {})
        bp_audit = step2.get("bp_usage_audit", {}) if isinstance(step2, dict) else {}
        if isinstance(bp_audit, dict):
            is_clean = bp_audit.get("is_clean", False)
            bp_used_for = bp_audit.get("bp_used_for", "N/A")
            violations = len(bp_audit.get("violations", []))
        else:
            is_clean = False
            bp_used_for = "N/A"
            violations = 0
        md += f"- **{project}**: is_clean={is_clean}, bp_used_for={bp_used_for}, violations={violations}\n"

    md += """

### 3. bp_usage_audit Cleanliness

"""
    for result in all_results:
        project = result["project_name"]
        step2 = result.get("step2_data", {})
        bp_audit = step2.get("bp_usage_audit", {}) if isinstance(step2, dict) else {}
        if isinstance(bp_audit, dict):
            is_clean = bp_audit.get("is_clean", False)
        else:
            is_clean = False
        md += f"- **{project}**: {'PASS' if is_clean else 'FAIL'}\n"

    md += """

### 4. knowledge_source Statistics

"""
    for result in all_results:
        project = result["project_name"]
        step2 = result.get("step2_data", {})
        ksb = step2.get("meta", {}).get("knowledge_source_breakdown", {})

        def safe_int(val, default=0):
            try:
                if isinstance(val, list):
                    return len(val)
                return int(val)
            except (TypeError, ValueError):
                return default

        total = sum(safe_int(v) for v in ksb.values())
        md += f"- **{project}**: total={total}, breakdown={ksb}\n"

    md += """

### 5. C1 Maintains Module/System Integration Judgment

"""
    for result in all_results:
        project = result["project_name"]
        step1 = result.get("step1_data", {})
        essence = step1.get("company_essence", {})
        core_identity = essence.get("core_identity", "")
        not_identity = essence.get("not_identity", [])

        is_module_or_system = any(
            kw in core_identity
            for kw in ["模块", "电控", "系统集成", "集成商", "改装", "制造", "module", "system", "integration"]
        )
        is_not_chip_factory = any(
            kw in " ".join(not_identity)
            for kw in ["芯片原厂", "芯片公司", "全产业链", "chip manufacturer", "full chain"]
        )

        md += f"- **{project}**: is_module_or_system={is_module_or_system}, is_not_chip_factory={is_not_chip_factory}\n"
        md += f"  - core_identity: {core_identity[:80]}...\n"

    md += """

### 6. A2 Complements Tech Validation/Mass Production Gap

"""
    for result in all_results:
        project = result["project_name"]
        step2 = result.get("step2_data", {})
        checks = step2.get("step1_external_check", {}).get("checks", [])
        tech_commercial_cautions = [
            c for c in checks
            if c.get("bucket_key") in ["tech_barrier", "commercialization"]
            and c.get("verdict") == "caution"
        ]
        md += f"- **{project}**: tech/commercialization cautions={len(tech_commercial_cautions)}\n"

    md += """

### 7. A1 Maintains Cautious, Not Reinforced to Positive by BP

"""
    for result in all_results:
        project = result["project_name"]
        step1 = result.get("step1_data", {})
        step2 = result.get("step2_data", {})
        step1_stance = step1.get("key_judgement", {}).get("stance", "unknown")
        checks = step2.get("step1_external_check", {}).get("checks", [])
        contradicts = [c for c in checks if c.get("verdict") == "contradict"]
        md += f"- **{project}**: step1_stance={step1_stance}, contradicts={len(contradicts)}\n"

    md += """

---

## Conclusion

### Acceptance Criteria

| Criteria | Status |
|----------|--------|
| Strictly around Step1 | Pending review |
| BP only for claim verification | Pending review |
| bp_usage_audit clean | {'PASS' if bp_clean == total else 'WARNING'} {bp_clean}/{total} |
| knowledge_source has stats | {'PASS' if has_knowledge_breakdown == total else 'WARNING'} {has_knowledge_breakdown}/{total} |
| C1 maintains judgment | Pending review |
| A2 complements gap | Pending review |
| A1 maintains cautious | Pending review |

### Recommendations

- Next: Connect to Step3B experiment (BP packaging identification layer)
- Or: Fix bp_usage_audit violations first
"""

    return md


# ============================================================
# Main Experiment
# ============================================================

def run_experiment(projects: list, workspace: str):
    """Run Step2 external logic validation experiment"""

    print(f"Starting Step2 v2.2 experiment...")
    print(f"Workspace: {workspace}")
    print(f"Projects: {len(projects)}")
    print("-" * 50)

    all_results = []

    for project_name in projects:
        print(f"\nProcessing: {project_name}")

        project_dir = Path(workspace) / project_name

        step1_path = project_dir / "step1_v1_2_1.json"
        if not step1_path.exists():
            print(f"  SKIP: step1_v1_2_1.json not found")
            continue

        with open(step1_path, "r", encoding="utf-8") as f:
            step1_data = json.load(f)

        ps_path = project_dir / "project_structure.json"
        if ps_path.exists():
            with open(ps_path, "r", encoding="utf-8") as f:
                project_structure = json.load(f)
        else:
            project_structure = {"industry_tags": [], "business_lines": [], "business_model_hypotheses": [], "risk_buckets": []}

        bp_path = project_dir / "bp_text.txt"
        if bp_path.exists():
            with open(bp_path, "r", encoding="utf-8") as f:
                bp_text = f.read()
        else:
            bp_text = ""

        print(f"  - Step1 loaded: stance={step1_data.get('key_judgement', {}).get('stance')}")
        print(f"  - BP length: {len(bp_text)} chars")

        result = run_step2(step1_data, project_structure, bp_text)
        step2_output = result["output"]

        schema_validation = validate_step2_schema(step2_output)

        output_dir = Path(workspace) / "step2_external_check" / project_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save outputs
        with open(output_dir / "step2_external_check.json", "w", encoding="utf-8") as f:
            json.dump(step2_output, f, ensure_ascii=False, indent=2)

        with open(output_dir / "prompt_step2.txt", "w", encoding="utf-8") as f:
            f.write(result["prompt"])

        bp_audit = step2_output.get("bp_usage_audit", {}) if isinstance(step2_output, dict) else {}
        with open(output_dir / "bp_usage_audit.json", "w", encoding="utf-8") as f:
            json.dump(bp_audit, f, ensure_ascii=False, indent=2)

        with open(output_dir / "schema_validation.json", "w", encoding="utf-8") as f:
            json.dump(schema_validation, f, ensure_ascii=False, indent=2)

        compare_md = generate_compare_md(
            project_name, step1_data, step2_output, schema_validation
        )
        with open(output_dir / "compare.md", "w", encoding="utf-8") as f:
            f.write(compare_md)

        error_str = step2_output.get('error', '')[:50] if isinstance(step2_output, dict) and 'error' in step2_output else ''
        print(f"  - Step2 output: {'OK' if not error_str else 'ERR ' + error_str}")
        print(f"  - Schema valid: {'PASS' if schema_validation['valid'] else 'FAIL'}")
        is_clean = bp_audit.get('is_clean', 'N/A') if isinstance(bp_audit, dict) else 'N/A'
        print(f"  - BP is_clean: {is_clean}")

        all_results.append({
            "project_name": project_name,
            "step1_data": step1_data,
            "step2_data": step2_output,
            "schema_valid": schema_validation["valid"],
            "bp_is_clean": bp_audit.get("is_clean", False) if isinstance(bp_audit, dict) else False,
            "schema_errors": schema_validation.get("errors", [])
        })

    summary_md = generate_summary(all_results)
    summary_path = Path(workspace) / "step2_external_check" / "summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    print("\n" + "=" * 50)
    print(f"Experiment complete! Results at: {summary_path.parent}")
    print(f"Summary: {summary_path}")

    return all_results


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace = project_root / "workspace" / "step2_external_check_experiment" / timestamp

    print(f"Project root: {project_root}")

    # Find v1.2.1 experiment data
    v121_workspace = project_root / "workspace" / "step1_v1_2_1_experiment"

    experiments = sorted([d for d in v121_workspace.iterdir() if d.is_dir()], reverse=True)
    if experiments:
        latest_exp = experiments[0]
        projects = [p.name for p in latest_exp.iterdir() if p.is_dir() and (p / "step1_v1_2_1.json").exists()]
        print(f"Found v1.2.1 experiment: {latest_exp.name}")
        print(f"Projects: {projects}")

        # Create new workspace
        workspace = latest_exp.parent / f"step2_external_check_experiment_{timestamp}"
        workspace.mkdir(parents=True, exist_ok=True)

        # Copy project data
        for project in projects:
            src = latest_exp / project
            dst = workspace / project
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)

        run_experiment(projects, str(workspace))
    else:
        print("No v1.2.1 experiment data found")
