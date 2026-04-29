# investment_modules/module_loader.py
# 投资思维模块加载器和选择器

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_investment_modules(version: str = "v0_1") -> List[Dict[str, Any]]:
    """
    加载投资思维模块库。

    默认加载 modules_v0_1.json。

    Returns:
        List[Dict]: 模块列表，每个模块包含:
            - module_id: str
            - module_name: str
            - definition: str
            - applicable_when: List[str]
            - core_questions: List[str]
            - red_flags: List[str]
            - good_signals: List[str]
            - step3b_usage: str
            - step5_usage: str
    """
    base_dir = Path(__file__).resolve().parent
    path = base_dir / f"modules_{version}.json"

    if not path.exists():
        raise FileNotFoundError(f"Investment modules file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Investment modules must be a list.")

    return data


def select_relevant_modules(
    *,
    project_structure: Dict[str, Any],
    step3b_output: Dict[str, Any] | None = None,
    max_modules: int = 6,
) -> List[Dict[str, Any]]:
    """
    根据 Step3 project_structure 和 Step3B 初步输出，选择最相关的投资思维模块。

    v0.1 用规则选择，后续可升级为 LLM selector。

    Args:
        project_structure: Step3 输出的 project_structure 字典
        step3b_output: Step3B 输出（可选，用于二次筛选）
        max_modules: 最多返回多少个模块

    Returns:
        List[Dict]: 选中的模块列表，按优先级排序
    """
    modules = load_investment_modules()
    module_by_id = {m["module_id"]: m for m in modules}

    selected_ids: List[str] = []

    def add(module_id: str):
        if module_id in module_by_id and module_id not in selected_ids:
            selected_ids.append(module_id)

    # 永远建议启用的基础模块
    add("company_essence")
    add("business_model_reality")
    add("intuition_red_flags")

    # 合并所有文本用于关键词匹配
    business_models = project_structure.get("business_model_hypotheses", [])
    risks = project_structure.get("risk_buckets", [])
    uncertainties = project_structure.get("key_uncertainties", [])
    industry_tags = project_structure.get("industry_tags", [])

    all_text = json.dumps(project_structure, ensure_ascii=False)
    if step3b_output:
        all_text += json.dumps(step3b_output, ensure_ascii=False)

    # 提取 bucket_key 和 tag
    bucket_keys = set()
    for item in business_models + risks:
        if isinstance(item, dict):
            key = item.get("bucket_key")
            if key:
                bucket_keys.add(key)

    tag_keys = set()
    for tag in industry_tags:
        if isinstance(tag, dict) and tag.get("tag"):
            tag_keys.add(tag["tag"])

    # === 模块选择规则 ===

    # 资产结构 / 单位经济
    if any(k in bucket_keys for k in ["asset_heavy_operation", "equipment_operation"]) \
        or "代运营" in all_text or "租赁" in all_text or "自持" in all_text \
        or "车辆" in all_text or "设备" in all_text:
        add("asset_structure")
        add("unit_economics")

    # 项目制 / 非标交付
    if any(k in bucket_keys for k in ["project_delivery", "customized_rnd"]) \
        or "定制" in all_text or "部署" in all_text or "实施" in all_text \
        or "集成" in all_text:
        add("scalability_and_replication")

    # AI / 数据
    if any(k in bucket_keys for k in ["data_ai_model"]) \
        or "AI" in all_text or "大模型" in all_text or "数据" in all_text \
        or "算法" in all_text or "平台" in all_text:
        add("tech_barrier_reality")
        add("data_moat_reality")

    # 政策驱动
    if any(k in bucket_keys for k in ["policy_driven"]) \
        or "政策" in all_text or "补贴" in all_text or "示范" in all_text \
        or "国产替代" in all_text or "新质生产力" in all_text:
        add("demand_reality")

    # 融资
    if "融资" in all_text or "估值" in all_text or "扩产" in all_text \
        or "建厂" in all_text or "补流" in all_text:
        add("financing_use_fit")

    # 产业链竞争（物流、自动驾驶、工业等领域）
    if any(k in tag_keys for k in ["autonomous_driving", "commercial_vehicle", "industrial_logistics"]) \
        or "主机厂" in all_text or "供应商" in all_text or "大厂" in all_text \
        or "替代" in all_text or "竞争" in all_text:
        add("value_chain_competition")

    # 验证程度
    if "客户" in all_text or "部署" in all_text or "案例" in all_text \
        or "试点" in all_text or "样板" in all_text:
        add("validation_level")

    # 返回选中的模块
    selected = [module_by_id[mid] for mid in selected_ids[:max_modules]]
    return selected


def format_modules_for_prompt(modules: List[Dict[str, Any]]) -> str:
    """
    将模块列表格式化为 prompt 文本。
    """
    if not modules:
        return ""

    lines = ["【投资思维模块库】\n"]
    lines.append("以下模块是历史项目和投资人经验沉淀出来的判断框架。")
    lines.append("你必须参考这些模块来识别：")
    lines.append("- BP包装")
    lines.append("- 结构矛盾")
    lines.append("- 关键红旗")
    lines.append("- 需要验证的核心问题\n")
    lines.append("使用规则：")
    lines.append("1. 模块不是结论，只是判断工具。不要机械套用所有模块。")
    lines.append("2. 只使用和本项目相关的模块。")
    lines.append("3. 如果模块中的 red_flags 与 BP 内容匹配，请体现在 consistency_checks / tensions / overpackaging_signals 中。")
    lines.append("4. 如果模块中的 good_signals 已经被 BP 证明，也可以写为 support。")
    lines.append("5. 不要让模块取代项目事实，必须结合 BP 和 project_structure。\n")

    for i, m in enumerate(modules, 1):
        lines.append(f"## 模块{i}: {m['module_name']} ({m['module_id']})")
        lines.append(f"定义: {m['definition']}")
        lines.append(f"适用场景: {', '.join(m['applicable_when'])}")
        lines.append(f"核心问题: {', '.join(m['core_questions'])}")
        lines.append(f"红旗信号: {', '.join(m['red_flags'])}")
        lines.append(f"正面信号: {', '.join(m['good_signals'])}")
        lines.append("")

    return "\n".join(lines)


def get_module_usage_summary(modules: List[Dict[str, Any]]) -> str:
    """
    获取模块在 Step3B 和 Step5 中的使用说明摘要。
    """
    lines = ["【模块使用说明】\n"]
    for m in modules:
        lines.append(f"- {m['module_name']}:")
        lines.append(f"  Step3B: {m['step3b_usage']}")
        lines.append(f"  Step5: {m['step5_usage']}")
        lines.append("")
    return "\n".join(lines)
