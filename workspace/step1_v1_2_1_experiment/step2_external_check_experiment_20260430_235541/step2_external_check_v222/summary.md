# Step2 External Check Experiment Summary

**Date**: 2026-04-30 23:57
**Version**: v2.2.2

---

## Experiment Results Overview

| Metric | Result |
|--------|--------|
| Test Projects | 3 |
| Schema Valid | PASS 3/3 |
| BP Clean | PASS 3/3 |
| Has knowledge_source Stats | PASS 3/3 |

---

## Validation Dimensions

### 1. Strictly Around Step1, No Company Redefinition

- **A1**: new_conclusion=False, related_to_step1=True
- **A2**: new_conclusion=False, related_to_step1=True
- **C1**: new_conclusion=False, related_to_step1=True


### 2. BP Only Used for Claim Verification

- **A1**: is_clean=True, bp_used_for=claim_verification_only, violations=0
- **A2**: is_clean=True, bp_used_for=claim_verification_only, violations=0
- **C1**: is_clean=True, bp_used_for=claim_verification_only, violations=0


### 3. bp_usage_audit Cleanliness

- **A1**: PASS
- **A2**: PASS
- **C1**: PASS


### 4. knowledge_source Statistics

- **A1**: total=10, breakdown={'general_bucket': 5, 'industry_bucket': 5, 'llm_common_sense': 0}
- **A2**: total=5, breakdown={'general_bucket': 5, 'industry_bucket': 0, 'llm_common_sense': 0}
- **C1**: total=7, breakdown={'general_bucket': 3, 'industry_bucket': 3, 'llm_common_sense': 1}


### 5. C1 Maintains Module/System Integration Judgment (Step2 Output)

**评估范围: 仅 C1 项目**
- **C1**: PASS
  - step2_reinforces_module: True
  - is_module_or_system (Step1 core_identity): True
  - core_identity: 本质是新能源商用车电驱动系统及功率模块的硬件供应商，以项目制交付为主


### 6. 硬科技项目强制 Caution（按项目类型差异化）

**tech_rd/mixed 类型**: tech_barrier caution >= 1 且 commercialization caution >= 1
**system_integration 类型**: commercialization caution >= 1

- **A1** [system_integration]: PASS
  - tech_barrier caution: N/A (集成型，tech_barrier 可为 support)
  - commercialization caution: PASS (2/1 required)
- **A2** [tech_rd]: PASS
  - tech_barrier caution: PASS (1/1 required)
  - commercialization caution: PASS (1/1 required)
- **C1** [tech_rd]: PASS
  - tech_barrier caution: PASS (1/1 required)
  - commercialization caution: PASS (1/1 required)


### 7. A1 保持 Cautious，不被 BP 强化成 Positive

**评估范围: 仅 A1 项目**
- **A1**: PASS
  - step1_stance: cautious_watch PASS
  - contradicts: 0 PASS


---

## Conclusion

### Acceptance Criteria

| Criteria | Status |
|----------|--------|
| Strictly around Step1 | Pending review |
| BP only for claim verification | Pending review |
| bp_usage_audit clean | PASS 3/3 |
| knowledge_source has stats | PASS 3/3 |
| C1 保持模块/电控判断 | Pending review |
| 硬科技项目 tech_barrier caution >= 1 | Pending review |
| 硬科技项目 commercialization caution >= 1 | Pending review |
| A1 保持 cautious | Pending review |

### Recommendations

- Next: Connect to Step3B experiment (BP packaging identification layer)
- Or: Fix bp_usage_audit violations first
