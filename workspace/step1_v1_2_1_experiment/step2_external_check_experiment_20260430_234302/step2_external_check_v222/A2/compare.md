# Step2 External Check Comparison Report

**Project**: A2
**Date**: 2026-04-30 23:44
**Schema Version**: step2_external_check_v2_2_2

---

## 1. Schema Validation

| Check | Result |
|-------|--------|
| Valid | PASS |
| Errors | 0 |

## 2. Step1 vs Step2 Comparison

### Step1 Judgment
- **core_identity**: 本质是吉林大学靳立强教授团队的底盘技术研发型初创公司，以自动轮智行底盘为核心技术，当前主要收入来自技术开发和定制底盘项目
- **not_identity**: 不是已量产的底盘供应商, 不是全产业链平台型企业
- **stance**: cautious_watch

### Step2 Validation Results
- **Support**: 3
- **Caution**: 2
- **Contradict**: 0

**Main Validation Conclusions**:
- [CAUTION] tech_barrier: company_essence: The technology is novel but unvalidated for mass production. Automotive-grade certification (e.g., I...
- [CAUTION] commercialization: key_judgement: BP lists potential customers but no signed contracts. Automotive OEM qualification typically takes 2...
- [SUPPORT] customer_value: red_flags: BP lists北汽, 华为, 广汽 as potential customers but no evidence of revenue. This is a common 'name-droppin...
- [SUPPORT] team_credibility: red_flags: BP explicitly states '版权属吉林大学靳立强教授所有', indicating IP is not company-owned. This is a significant ris...
- [SUPPORT] expansion_story: business_structure: Current revenue from technical services is typical of early-stage hard tech. The narrative of mass p...

## 3. BP Usage Audit

| Check | Result |
|-------|--------|
| BP Used For | claim_verification_only |
| is_clean | CLEAN |
| violations | 0 |

## 4. Knowledge Source Statistics

| Source | Count | Ratio |
|--------|-------|-------|
| general_bucket | 3 | 50% |
| industry_bucket | 2 | 33% |
| llm_common_sense | 1 | 17% |

## 5. Step1 Adjustment Hints

**Reinforce**:
- red_flags: income data missing, customer names only
- red_flags: professor IP ownership risk
- key_judgement: cautious stance on commercialization

**Needs Verification**:
- company_essence: need verification of IP ownership and founder commitment
- business_structure: need verification of current revenue sources
- key_judgement: need verification of customer contracts and certification timeline

