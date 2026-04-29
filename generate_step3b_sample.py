# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
from step3b.step3b_service import run_step3b

SINIAN_TEXT = '''
斯年智驾是一家专注于自动驾驶卡车商业化运营的公司。
主要业务包括：1）自动驾驶软硬件设备销售；2）智能物流代运营服务；
3）物流园区智能化项目实施。
公司拥有完整的自动驾驶技术栈，包括感知、决策、执行全栈能力。
已与多家头部物流企业建立合作关系，运营里程超过1000万公里。
已部署240台无人重载运输车辆，落地20个项目。
前五大客户收入占比超过60%。
'''

SHANHAI_TEXT = '''
杉海创新是一家基于AI大模型和生物计算技术的新材料研发平台公司。
公司主营业务包括：1）AI驱动的材料筛选平台服务；
2）生物基日化原料的研发与销售；3）新能源材料的技术授权。
核心技术为自主研发的智能分子设计平台，已申请20余项核心专利。
与多家国际美妆品牌建立战略合作，共同开发定制化原料解决方案。
已完成千吨级生物基日化原料产线的建设，并开始向食品和医药领域扩张。
'''

project_structure_sinian = {
    'industry_tags': [
        {'tag': 'autonomous_driving', 'label': '自动驾驶'},
        {'tag': 'industrial_logistics', 'label': '工业物流'}
    ],
    'business_lines': [
        {'name': '无人重载车辆/无人集卡', 'role': 'current_business'},
        {'name': '项目制交付/场景解决方案', 'role': 'current_business'},
        {'name': '代运营服务', 'role': 'growth_story'},
        {'name': '自动驾驶系统/云端调度平台', 'role': 'supporting_capability'}
    ]
}

project_structure_shanhai = {
    'industry_tags': [
        {'tag': 'advanced_materials', 'label': '新材料'},
        {'tag': 'beauty_ingredients', 'label': '美妆/日化原料'},
        {'tag': 'ai_application', 'label': 'AI应用'}
    ],
    'business_lines': [
        {'name': '美妆/日化原料', 'role': 'current_business'},
        {'name': '食品/营养原料', 'role': 'growth_story'},
        {'name': 'AI研发平台', 'role': 'supporting_capability'},
        {'name': '新能源材料/回收业务', 'role': 'valuation_story'}
    ]
}

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
folder = f'step3b_sample_{ts}'
os.makedirs(folder, exist_ok=True)

sinian = run_step3b(SINIAN_TEXT, project_structure_sinian)
with open(f'{folder}/step3b_sinian.json', 'w', encoding='utf-8') as f:
    json.dump(sinian.model_dump(), f, ensure_ascii=False, indent=2)

shanhai = run_step3b(SHANHAI_TEXT, project_structure_shanhai)
with open(f'{folder}/step3b_shanhai.json', 'w', encoding='utf-8') as f:
    json.dump(shanhai.model_dump(), f, ensure_ascii=False, indent=2)

print(f'已生成文件夹: {folder}')
print(f'  - step3b_sinian.json')
print(f'  - step3b_shanhai.json')
