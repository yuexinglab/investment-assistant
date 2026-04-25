# -*- coding: utf-8 -*-
import json, os, sys
sys.path.insert(0, r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant')
from services.v2.services.step8_updater import (
    _has_missing_evidence, _check_evidence_quality,
    _find_related_validations, _map_status_impact
)

workspace = r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\测试科技公司_20260424_173519'

with open(os.path.join(workspace, 'step7', 'step7_v2_2_003.json'), encoding='utf-8') as f:
    step7_result = json.load(f)

with open(os.path.join(workspace, 'step6', 'step6_v2_2_003.json'), encoding='utf-8') as f:
    step6_data = json.load(f)

step7_result['_step6_new_information'] = step6_data.get('new_information', [])

validations = step7_result['question_validation']

print('=== Step7 验证分析 ===')
for v in validations:
    qid = v['question_id']
    has_missing = _has_missing_evidence(v)
    quality, ratio = _check_evidence_quality(v, step7_result)
    matched = v['matched_information_ids']
    status = v['status']
    impact = v['impact']
    print(f'{qid}: status={status}, impact={impact}')
    print(f'  missing={has_missing}, quality={quality}({ratio:.0%})')
    print(f'  matched={matched}')

    # 构建 related_validations
    related = _find_related_validations(v['original_question'], validations)
    best = related[0] if related else None
    if best:
        ct, delta, risk, _ = _map_status_impact(related, step7_result)
        print(f'  -> change_type={ct.value}, confidence={delta}, adds_risk={risk}')
    print()

# 测试 h_002 手动追踪
print('=== h_002 手动追踪 ===')
h2_val = [v for v in validations if v['question_id'] == 'q_2'][0]
rel = _find_related_validations('大客户（欧莱雅/宝洁）粘性高，切换成本大', validations)
ct, delta, risk, _ = _map_status_impact(rel, step7_result)
print(f'q_2: status={h2_val["status"]}, impact={h2_val["impact"]}')
print(f'has_missing={_has_missing_evidence(h2_val)}, quality={_check_evidence_quality(h2_val, step7_result)}')
print(f'-> change_type={ct.value}, confidence={delta}')
print(f'约束1触发? partially+missing={h2_val["status"] in ("partially_answered","indirectly_answered") and _has_missing_evidence(h2_val)}')

# 测试 h_005
print()
print('=== h_005 手动追踪 ===')
h5_val = [v for v in validations if v['question_id'] == 'q_5'][0]
rel5 = _find_related_validations('专利保护构成有效竞争壁垒', validations)
ct5, delta5, risk5, _ = _map_status_impact(rel5, step7_result)
print(f'q_5: status={h5_val["status"]}, impact={h5_val["impact"]}')
print(f'has_missing={_has_missing_evidence(h5_val)}, quality={_check_evidence_quality(h5_val, step7_result)}')
print(f'-> change_type={ct5.value}, confidence={delta5}')
