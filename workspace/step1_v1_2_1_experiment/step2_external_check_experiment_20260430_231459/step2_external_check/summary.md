# Step2 External Check Experiment Summary

**Date**: 2026-04-30 23:16
**Version**: v2.2

---

## Experiment Results Overview

| Metric | Result |
|--------|--------|
| Test Projects | 3 |
| Schema Valid | 0/3 |
| BP Clean | 0/3 |
| Has knowledge_source Stats | 3/3 |

---

## Validation Dimensions

### 1. Strictly Around Step1, No Company Redefinition

- **A1**: new_conclusion=False, related_to_step1=False
- **A2**: new_conclusion=False, related_to_step1=False
- **C1**: new_conclusion=False, related_to_step1=False


### 2. BP Only Used for Claim Verification

- **A1**: is_clean=False, bp_used_for=N/A, violations=0
- **A2**: is_clean=False, bp_used_for=N/A, violations=0
- **C1**: is_clean=False, bp_used_for=N/A, violations=0


### 3. bp_usage_audit Cleanliness

- **A1**: FAIL
- **A2**: FAIL
- **C1**: FAIL


### 4. knowledge_source Statistics

- **A1**: total=6, breakdown={'general_bucket': 5, 'industry_bucket': 1, 'llm_common_sense': 0}
- **A2**: total=5, breakdown={'general_bucket': ['tech_barrier', 'customer_value', 'commercialization', 'expansion_story', 'team_credibility'], 'industry_bucket': [], 'llm_common_sense': []}
- **C1**: total=8, breakdown={'general_bucket': ['tech_barrier', 'customer_value', 'commercialization', 'expansion_story', 'team_credibility', 'step1_external_check.checks[1-6]', 'step1_external_check.overall_validation'], 'industry_bucket': ['step1_external_check.checks[0]'], 'llm_common_sense': []}


### 5. C1 Maintains Module/System Integration Judgment

- **A1**: is_module_or_system=True, is_not_chip_factory=True
  - core_identity: 本质是重载物流场景的自动驾驶系统集成商和车辆改装/制造商，以项目制交付和车辆销售为主要收入来源...
- **A2**: is_module_or_system=False, is_not_chip_factory=True
  - core_identity: 本质是吉林大学靳立强教授团队的底盘技术研发型初创公司，以自动轮智行底盘为核心技术，当前主要收入来自技术开发和定制底盘项目...
- **C1**: is_module_or_system=True, is_not_chip_factory=True
  - core_identity: 本质是新能源商用车电驱动系统及功率模块的硬件供应商，以项目制交付为主...


### 6. A2 Complements Tech Validation/Mass Production Gap

- **A1**: tech/commercialization cautions=0
- **A2**: tech/commercialization cautions=0
- **C1**: tech/commercialization cautions=0


### 7. A1 Maintains Cautious, Not Reinforced to Positive by BP

- **A1**: step1_stance=cautious_watch, contradicts=0
- **A2**: step1_stance=cautious_watch, contradicts=0
- **C1**: step1_stance=cautious_watch, contradicts=0


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
