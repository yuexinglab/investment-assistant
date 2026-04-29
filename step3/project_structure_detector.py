# step3/project_structure_detector.py

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


# =========================================================
# 1. 标准 bucket 元数据
# =========================================================

BUCKET_META = {
    "hardtech_commercialization": {
        "name": "硬科技商业化型",
        "description": "技术能否从实验室/样机走向稳定量产和真实客户",
    },
    "manufacturing_product_sales": {
        "name": "制造/产品销售型",
        "description": "能否稳定生产、控制成本、卖出产品并形成毛利",
    },
    "project_delivery": {
        "name": "项目制交付型",
        "description": "是否每单都要定制，规模化后毛利和交付是否崩",
    },
    "asset_heavy_operation": {
        "name": "重资产运营型",
        "description": "是否需要自投资产、垫资运营、靠长期回收现金流",
    },
    "software_platform_saas": {
        "name": "软件/SaaS/平台型",
        "description": "是否有标准化产品、续费、低边际成本和可复制销售",
    },
    "data_ai_model": {
        "name": "数据/AI模型驱动型",
        "description": "AI是否真的构成壁垒，数据闭环是否独占且可持续",
    },
    "channel_brand_consumer": {
        "name": "渠道/品牌/消费型",
        "description": "是否有用户心智、渠道效率、复购和品牌势能",
    },
    "government_industrial_landing": {
        "name": "政府/产业落地型",
        "description": "是否符合地方基金诉求，能否反投、建厂、带产值",
    },
    "policy_driven": {
        "name": "政策驱动型",
        "description": "需求是否来自真实经济性，还是政策/补贴/考核推动",
    },
    "expansion_story": {
        "name": "多业务扩张/第二曲线型",
        "description": "新业务是真增长，还是为扩大估值边界讲故事",
    },
    "financing_valuation_story": {
        "name": "融资估值叙事型",
        "description": "融资用途和估值逻辑是否匹配真实业务阶段",
    },
    "team_credibility_story": {
        "name": "团队/背书叙事型",
        "description": "学历、奖项、名人、机构背书是否真正转化为壁垒",
    },
    "customer_concentration": {
        "name": "客户集中风险",
        "description": "是否依赖少数大客户，议价权和收入稳定性是否受影响",
    },
}


# =========================================================
# 2. 数据结构
# =========================================================

@dataclass
class IndustryTag:
    tag: str
    label: str
    confidence: str
    evidence: str


@dataclass
class BusinessLine:
    name: str
    role: str
    status: str
    revenue_status: str
    evidence: str
    confidence: str


@dataclass
class BusinessModelHypothesis:
    bucket_key: str
    bucket_name: str
    role: str
    current_or_future: str
    confidence: str
    evidence: str
    why_it_matters: str


@dataclass
class RiskBucket:
    bucket_key: str
    bucket_name: str
    risk_role: str
    confidence: str
    evidence: str
    why_it_matters: str


@dataclass
class KeyUncertainty:
    uncertainty: str
    why_it_matters: str
    related_buckets: List[str]
    discriminating_questions: List[str]


@dataclass
class ProjectStructure:
    industry_tags: List[IndustryTag] = field(default_factory=list)
    business_lines: List[BusinessLine] = field(default_factory=list)
    business_model_hypotheses: List[BusinessModelHypothesis] = field(default_factory=list)
    risk_buckets: List[RiskBucket] = field(default_factory=list)
    key_uncertainties: List[KeyUncertainty] = field(default_factory=list)
    structure_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "industry_tags": [asdict(x) for x in self.industry_tags],
            "business_lines": [asdict(x) for x in self.business_lines],
            "business_model_hypotheses": [asdict(x) for x in self.business_model_hypotheses],
            "risk_buckets": [asdict(x) for x in self.risk_buckets],
            "key_uncertainties": [asdict(x) for x in self.key_uncertainties],
            "structure_summary": self.structure_summary,
        }


# =========================================================
# 3. 工具函数
# =========================================================

def _hit_keywords(text: str, keywords: List[str]) -> List[str]:
    return [kw for kw in keywords if kw.lower() in text.lower()]


def _confidence(hit_count: int) -> str:
    if hit_count >= 4:
        return "high"
    if hit_count >= 2:
        return "medium"
    return "low"


def _evidence(hits: List[str]) -> str:
    if not hits:
        return "未命中明确关键词"
    return "命中关键词：" + "、".join(hits[:8])


def _bucket_name(bucket_key: str) -> str:
    return BUCKET_META.get(bucket_key, {}).get("name", bucket_key)


def _bucket_desc(bucket_key: str) -> str:
    return BUCKET_META.get(bucket_key, {}).get("description", "")


def _dedup_by_key(items: List[Any], key_attr: str) -> List[Any]:
    seen = set()
    result = []
    for item in items:
        key = getattr(item, key_attr)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _contains_any(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords)


def _contains_combo(text: str, group_a: List[str], group_b: List[str]) -> bool:
    lowered = text.lower()
    return (
        any(a.lower() in lowered for a in group_a)
        and any(b.lower() in lowered for b in group_b)
    )


def _merge_hits(*hit_lists: List[str]) -> List[str]:
    seen = set()
    merged = []
    for hits in hit_lists:
        for h in hits:
            if h not in seen:
                seen.add(h)
                merged.append(h)
    return merged


# =========================================================
# 4. 行业标签识别
# =========================================================

INDUSTRY_PATTERNS = {
    "autonomous_driving": {
        "label": "自动驾驶",
        "keywords": ["自动驾驶", "无人驾驶", "智能驾驶", "智驾", "无人集卡", "无人重卡", "L2", "L3", "L4"],
    },
    "industrial_logistics": {
        "label": "工业物流/场内物流",
        "keywords": ["物流", "运输", "港口", "矿区", "园区", "短驳", "集装箱", "TEU"],
    },
    "commercial_vehicle": {
        "label": "商用车/重卡",
        "keywords": ["重卡", "集卡", "自卸车", "底盘", "线控底盘", "商用车"],
    },
    "advanced_materials": {
        "label": "新材料",
        "keywords": ["材料", "超分子", "分子", "聚合物", "催化剂", "配方", "原料", "功能材料"],
    },
    "beauty_ingredients": {
        "label": "美妆/日化原料",
        "keywords": ["美妆", "日化", "护肤", "化妆品", "原料", "配方"],
    },
    "food_ingredients": {
        "label": "食品/营养原料",
        "keywords": ["食品", "保健品", "营养", "功能食品", "食品添加剂"],
    },
    "ai_application": {
        "label": "AI应用",
        "keywords": ["AI", "人工智能", "算法", "大模型", "模型", "数据"],
    },
    "new_energy": {
        "label": "新能源",
        "keywords": ["新能源", "锂电", "储能", "电池", "回收", "光伏"],
    },
}


def detect_industry_tags(text: str) -> List[IndustryTag]:
    tags: List[IndustryTag] = []

    for tag, cfg in INDUSTRY_PATTERNS.items():
        hits = _hit_keywords(text, cfg["keywords"])
        if hits:
            tags.append(
                IndustryTag(
                    tag=tag,
                    label=cfg["label"],
                    confidence=_confidence(len(hits)),
                    evidence=_evidence(hits),
                )
            )

    if not tags:
        tags.append(
            IndustryTag(
                tag="general",
                label="通用",
                confidence="low",
                evidence="未命中明确行业关键词",
            )
        )

    rank = {"high": 3, "medium": 2, "low": 1}
    tags.sort(key=lambda x: rank.get(x.confidence, 0), reverse=True)
    return tags[:6]


# =========================================================
# 5. 业务线识别
# =========================================================

BUSINESS_LINE_PATTERNS = [
    {
        "name": "无人重载车辆/无人集卡",
        "keywords": [
            "无人集卡", "无人重卡", "无人重载", "智能集卡",
            "自卸车", "重卡", "集卡", "商用车",
            "无人运输车辆", "重载运输机器人", "运输机器人",
            "无人驾驶车辆", "智能驾驶车辆", "整车销售",
            "车辆销售", "设备销售", "硬件销售"
        ],
        "combo": [
            {
                "group_a": ["自动驾驶", "无人驾驶", "智能驾驶", "智驾"],
                "group_b": ["车辆", "重卡", "集卡", "运输", "机器人", "整车"]
            }
        ],
        "role": "current_business",
        "status": "核心产品/已落地业务",
        "revenue_status": "可能已有设备/整车/硬件收入，具体金额待确认",
    },
    {
        "name": "自动驾驶系统/云端调度平台",
        "keywords": [
            "云平台", "调度", "车队监管", "车队管理",
            "自动驾驶系统", "智能驾驶系统", "无人驾驶系统",
            "远程控制", "远程监管", "数字孪生",
            "感知", "决策", "规划", "控制", "算法平台"
        ],
        "combo": [
            {
                "group_a": ["自动驾驶", "无人驾驶", "智能驾驶", "智驾"],
                "group_b": ["系统", "平台", "调度", "监管", "控制", "车队", "算法"]
            }
        ],
        "role": "supporting_capability",
        "status": "支撑主业务的技术/平台能力",
        "revenue_status": "可能作为技术服务或软件服务收费，需确认",
    },
    {
        "name": "项目制交付/场景解决方案",
        "keywords": [
            "项目", "项目制", "交付", "部署", "实施",
            "解决方案", "场景方案", "系统集成",
            "港口项目", "矿区项目", "园区项目",
            "改造", "适配", "落地项目"
        ],
        "combo": [
            {
                "group_a": ["港口", "矿区", "园区", "工厂", "场内"],
                "group_b": ["项目", "部署", "交付", "实施", "解决方案", "落地"]
            }
        ],
        "role": "current_business",
        "status": "项目制落地/场景交付",
        "revenue_status": "项目收入和毛利待确认",
    },
    {
        "name": "代运营服务",
        "keywords": [
            "代运营", "运营车队", "车队运营", "运营托管",
            "按量收费", "按产量", "按里程", "按车次",
            "租赁", "托管运营", "运营服务"
        ],
        "combo": [
            {
                "group_a": ["运营", "托管", "租赁"],
                "group_b": ["车辆", "车队", "项目", "运输", "物流"]
            }
        ],
        "role": "growth_story",
        "status": "持续收入模式待验证",
        "revenue_status": "是否已经形成稳定持续收入待确认",
    },
    {
        "name": "美妆/日化原料",
        "keywords": [
            "美妆", "日化", "护肤", "化妆品", "原料",
            "配方", "功效成分", "活性物"
        ],
        "combo": [
            {
                "group_a": ["美妆", "日化", "化妆品", "护肤"],
                "group_b": ["原料", "配方", "成分", "功效"]
            }
        ],
        "role": "current_business",
        "status": "当前收入底盘",
        "revenue_status": "已有收入但金额需确认",
    },
    {
        "name": "食品/营养原料",
        "keywords": [
            "食品", "保健品", "营养", "功能食品",
            "食品添加剂", "营养补充剂"
        ],
        "combo": [
            {
                "group_a": ["食品", "保健品", "营养"],
                "group_b": ["原料", "成分", "配方", "添加剂"]
            }
        ],
        "role": "growth_story",
        "status": "增长业务",
        "revenue_status": "收入基数和复购待确认",
    },
    {
        "name": "AI研发平台",
        "keywords": [
            "AI", "人工智能", "算法", "大模型",
            "筛选", "预测", "研发平台", "分子设计",
            "材料筛选", "模型平台"
        ],
        "combo": [
            {
                "group_a": ["AI", "人工智能", "算法", "大模型", "模型"],
                "group_b": ["研发", "筛选", "预测", "平台", "设计", "优化"]
            }
        ],
        "role": "supporting_capability",
        "status": "研发工具/效率工具",
        "revenue_status": "是否对外收费待确认",
    },
    {
        "name": "新能源材料/回收业务",
        "keywords": [
            "新能源", "锂电", "电池", "回收", "储能",
            "正极", "负极", "电解液", "电池材料"
        ],
        "combo": [
            {
                "group_a": ["新能源", "锂电", "电池", "储能"],
                "group_b": ["材料", "回收", "原料", "业务", "应用"]
            }
        ],
        "role": "valuation_story",
        "status": "远期故事/待验证业务",
        "revenue_status": "是否已有收入待确认",
    },
]


def detect_business_lines(
    text: str,
    business_models: List[BusinessModelHypothesis] | None = None,
    industry_tags: List[IndustryTag] | None = None,
) -> List[BusinessLine]:
    """
    识别业务线。

    逻辑：
    1. 先通过业务线关键词/组合词直接识别；
    2. 再根据 business_model_hypotheses 反推补充业务线；
    3. 再根据行业标签补充业务线；
    4. 去重；
    5. 返回对象数组。
    """

    lines: List[BusinessLine] = []

    # 1. 关键词 + 组合命中
    for cfg in BUSINESS_LINE_PATTERNS:
        direct_hits = _hit_keywords(text, cfg.get("keywords", []))

        combo_hits: List[str] = []
        for combo in cfg.get("combo", []):
            if _contains_combo(text, combo["group_a"], combo["group_b"]):
                combo_hits.extend(combo["group_a"][:2] + combo["group_b"][:2])

        hits = _merge_hits(direct_hits, combo_hits)

        if hits:
            lines.append(
                BusinessLine(
                    name=cfg["name"],
                    role=cfg["role"],
                    status=cfg["status"],
                    revenue_status=cfg["revenue_status"],
                    evidence=_evidence(hits),
                    confidence=_confidence(len(hits)),
                )
            )

    # 2. 根据 business model 反推补业务线
    model_keys = {x.bucket_key for x in (business_models or [])}
    industry_keys = {x.tag for x in (industry_tags or [])}

    def add_line_if_missing(
        name: str,
        role: str,
        status: str,
        revenue_status: str,
        evidence: str,
        confidence: str = "medium",
    ):
        if any(x.name == name for x in lines):
            return
        lines.append(
            BusinessLine(
                name=name,
                role=role,
                status=status,
                revenue_status=revenue_status,
                evidence=evidence,
                confidence=confidence,
            )
        )

    # 自动驾驶 / 工业物流项目：如果有制造销售，就补车辆/硬件业务线
    if (
        "manufacturing_product_sales" in model_keys
        and (
            "autonomous_driving" in industry_keys
            or "industrial_logistics" in industry_keys
            or "commercial_vehicle" in industry_keys
        )
    ):
        add_line_if_missing(
            name="无人重载车辆/无人集卡",
            role="current_business",
            status="核心产品/已落地业务",
            revenue_status="可能已有设备/整车/硬件收入，具体金额待确认",
            evidence="根据商业模式识别为制造/产品销售型，并结合自动驾驶/工业物流行业标签反推",
            confidence="medium",
        )

    # 自动驾驶项目：如果有 hardtech 或 data_ai_model，补系统/平台能力
    if (
        ("hardtech_commercialization" in model_keys or "data_ai_model" in model_keys)
        and "autonomous_driving" in industry_keys
    ):
        add_line_if_missing(
            name="自动驾驶系统/云端调度平台",
            role="supporting_capability",
            status="支撑主业务的技术/平台能力",
            revenue_status="可能作为技术服务或软件服务收费，需确认",
            evidence="根据自动驾驶行业标签及硬科技/数据模型逻辑反推",
            confidence="medium",
        )

    # 项目制交付
    if "project_delivery" in model_keys:
        add_line_if_missing(
            name="项目制交付/场景解决方案",
            role="current_business",
            status="项目制落地/场景交付",
            revenue_status="项目收入和毛利待确认",
            evidence="根据商业模式识别为项目制交付型反推",
            confidence="medium",
        )

    # 重资产运营
    if "asset_heavy_operation" in model_keys:
        add_line_if_missing(
            name="代运营服务",
            role="growth_story",
            status="持续收入模式待验证",
            revenue_status="是否已经形成稳定持续收入待确认",
            evidence="根据商业模式识别为重资产运营型反推",
            confidence="medium",
        )

    # 新材料项目：制造产品销售 → 美妆/日化原料
    if (
        "manufacturing_product_sales" in model_keys
        and (
            "advanced_materials" in industry_keys
            or "beauty_ingredients" in industry_keys
        )
    ):
        add_line_if_missing(
            name="美妆/日化原料",
            role="current_business",
            status="当前收入底盘",
            revenue_status="已有收入但金额需确认",
            evidence="根据制造/产品销售型及新材料/美妆原料行业标签反推",
            confidence="medium",
        )

    # AI应用 → AI研发平台
    if "data_ai_model" in model_keys:
        add_line_if_missing(
            name="AI研发平台",
            role="supporting_capability",
            status="研发工具/效率工具",
            revenue_status="是否对外收费待确认",
            evidence="根据数据/AI模型驱动型反推",
            confidence="medium",
        )

    # 扩张故事 → 如果文本出现食品/新能源，则补对应业务线
    if "expansion_story" in model_keys:
        if _contains_any(text, ["食品", "保健品", "营养", "功能食品"]):
            add_line_if_missing(
                name="食品/营养原料",
                role="growth_story",
                status="增长业务",
                revenue_status="收入基数和复购待确认",
                evidence="根据扩张故事及食品/营养关键词反推",
                confidence="medium",
            )

        if _contains_any(text, ["新能源", "锂电", "电池", "回收", "储能"]):
            add_line_if_missing(
                name="新能源材料/回收业务",
                role="valuation_story",
                status="远期故事/待验证业务",
                revenue_status="是否已有收入待确认",
                evidence="根据扩张故事及新能源关键词反推",
                confidence="medium",
            )

    # 3. 如果仍然没有识别到，保底
    if not lines:
        lines.append(
            BusinessLine(
                name="主营业务",
                role="unclear",
                status="无法从文本中明确拆分",
                revenue_status="收入状态待确认",
                evidence="未命中明确业务线关键词",
                confidence="low",
            )
        )

    # 4. 排序：current_business 优先，其次 growth_story，再 supporting，最后 valuation
    role_rank = {
        "current_business": 1,
        "growth_story": 2,
        "supporting_capability": 3,
        "valuation_story": 4,
        "unclear": 9,
    }

    lines.sort(key=lambda x: role_rank.get(x.role, 9))

    return lines[:8]


# =========================================================
# 6. 商业模式假设识别
# =========================================================

BUSINESS_MODEL_PATTERNS = {
    "manufacturing_product_sales": {
        "keywords": ["整车销售", "设备销售", "硬件销售", "产品销售", "原料销售", "销售", "卖车", "卖设备"],
        "role": "primary",
        "current_or_future": "current",
        "why": "如果当前收入主要来自产品/设备/原料销售，则公司更接近制造/产品销售型公司。",
    },
    "project_delivery": {
        "keywords": ["项目", "交付", "部署", "定制", "实施", "解决方案", "集成", "改造"],
        "role": "secondary",
        "current_or_future": "current",
        "why": "如果收入依赖一个个项目交付，则需要重点验证标准化和毛利稳定性。",
    },
    "asset_heavy_operation": {
        "keywords": ["代运营", "运营车队", "车队运营", "租赁", "按量收费", "按产量", "托管运营", "自投"],
        "role": "secondary",
        "current_or_future": "mixed",
        "why": "如果公司需要自投资产或长期运营回收现金流，则估值和风险更接近重资产运营公司。",
    },
    "software_platform_saas": {
        "keywords": ["SaaS", "订阅", "软件", "平台费", "License", "API", "云平台"],
        "role": "secondary",
        "current_or_future": "mixed",
        "why": "如果软件收入标准化且可续费，才适合按软件/平台公司分析。",
    },
    "data_ai_model": {
        "keywords": ["AI", "人工智能", "算法", "大模型", "数据", "模型", "筛选", "预测"],
        "role": "secondary",
        "current_or_future": "narrative",
        "why": "如果AI只是内部效率工具，则不应按AI平台公司估值；如果形成数据闭环，才可能构成壁垒。",
    },
    "hardtech_commercialization": {
        "keywords": ["技术", "专利", "研发", "材料", "自动驾驶", "机器人", "量产", "中试"],
        "role": "secondary",
        "current_or_future": "mixed",
        "why": "硬科技项目重点不是技术先进，而是能否稳定量产并被真实客户持续采购。",
    },
    "government_industrial_landing": {
        "keywords": ["政府", "基金", "反投", "落地", "产业园", "招商", "制造基地", "本地"],
        "role": "secondary",
        "current_or_future": "mixed",
        "why": "对政府基金而言，需判断项目是否能真实落地产值、税收、就业和产业协同。",
    },
    "expansion_story": {
        "keywords": ["多行业", "第二曲线", "平台化", "生态", "跨行业", "新能源", "农业", "医药", "食品"],
        "role": "narrative",
        "current_or_future": "future",
        "why": "如果当前收入来自A业务，但估值故事来自B/C业务，需警惕扩张叙事。",
    },
    "policy_driven": {
        "keywords": ["政策", "补贴", "示范", "试点", "新质生产力", "国产替代", "双碳"],
        "role": "risk",
        "current_or_future": "mixed",
        "why": "如果需求主要来自政策/补贴/示范项目，需验证政策退坡后的商业可持续性。",
    },
    "team_credibility_story": {
        "keywords": ["诺奖", "院士", "博士", "名校", "实验室", "教授", "专家"],
        "role": "risk",
        "current_or_future": "narrative",
        "why": "团队/背书需要验证是否转化为排他资源、成果转化或商业化能力。",
    },
    "financing_valuation_story": {
        "keywords": ["融资", "估值", "并购", "扩产", "补充现金流", "战略布局"],
        "role": "risk",
        "current_or_future": "narrative",
        "why": "需验证融资用途和估值逻辑是否匹配真实业务阶段。",
    },
}


def detect_business_model_hypotheses(text: str) -> List[BusinessModelHypothesis]:
    items: List[BusinessModelHypothesis] = []

    for bucket_key, cfg in BUSINESS_MODEL_PATTERNS.items():
        hits = _hit_keywords(text, cfg["keywords"])
        if hits:
            items.append(
                BusinessModelHypothesis(
                    bucket_key=bucket_key,
                    bucket_name=_bucket_name(bucket_key),
                    role=cfg["role"],
                    current_or_future=cfg["current_or_future"],
                    confidence=_confidence(len(hits)),
                    evidence=_evidence(hits),
                    why_it_matters=cfg["why"],
                )
            )

    return _dedup_by_key(items, "bucket_key")[:10]


# =========================================================
# 7. 风险桶识别
# =========================================================

RISK_PATTERNS = {
    "asset_heavy_operation": {
        "keywords": ["代运营", "自投", "车队", "固定资产", "垫资", "租赁", "设备投入", "重资产"],
        "why": "如果业务扩张需要同步投入大量资产，会带来现金流和回本周期风险。",
    },
    "project_delivery": {
        "keywords": ["定制", "项目制", "交付", "实施", "改造", "适配", "验收", "非标"],
        "why": "如果每个项目都需要定制，规模化后交付和毛利可能承压。",
    },
    "policy_driven": {
        "keywords": ["政策", "政府", "补贴", "示范", "试点", "新质生产力"],
        "why": "如果需求由政策驱动，需要验证政策退坡后客户是否仍会付费。",
    },
    "asset_heavy_operation_cashflow": {
        "keywords": ["回款", "应收", "账期", "垫资", "现金流", "资金占用"],
        "why": "如果回款慢或需要垫资，增长可能反而加剧资金压力。",
    },
    "hardtech_commercialization": {
        "keywords": ["外采", "供应商", "芯片", "激光雷达", "传感器", "第三方", "良率", "量产"],
        "why": "硬科技项目需要验证关键供应链、量产良率和工程化能力。",
    },
    "customer_concentration": {
        "keywords": ["大客户", "头部客户", "前五大", "客户集中", "欧莱雅", "宝洁", "港口"],
        "why": "如果收入依赖少数大客户，公司议价权和收入稳定性可能较弱。",
    },
    "expansion_story": {
        "keywords": ["多行业", "第二曲线", "平台化", "生态", "新能源", "农业", "医药"],
        "why": "多业务扩张可能是真增长，也可能只是扩大估值边界。",
    },
    "team_credibility_story": {
        "keywords": ["诺奖", "院士", "博士", "实验室", "教授"],
        "why": "背书需要验证是否真正转化为公司壁垒。",
    },
    "financing_valuation_story": {
        "keywords": ["融资", "估值", "并购", "扩产", "补充现金流"],
        "why": "融资用途和估值逻辑可能与真实业务阶段不匹配。",
    },
}


def detect_risk_buckets(text: str) -> List[RiskBucket]:
    risks: List[RiskBucket] = []

    for bucket_key, cfg in RISK_PATTERNS.items():
        hits = _hit_keywords(text, cfg["keywords"])
        if hits:
            risks.append(
                RiskBucket(
                    bucket_key=bucket_key,
                    bucket_name=_bucket_name(bucket_key),
                    risk_role="risk",
                    confidence=_confidence(len(hits)),
                    evidence=_evidence(hits),
                    why_it_matters=cfg["why"],
                )
            )

    return _dedup_by_key(risks, "bucket_key")[:10]


# =========================================================
# 8. 关键不确定性生成
# =========================================================

def generate_key_uncertainties(
    business_models: List[BusinessModelHypothesis],
    risk_buckets: List[RiskBucket],
    business_lines: List[BusinessLine],
) -> List[KeyUncertainty]:
    model_keys = {x.bucket_key for x in business_models}
    risk_keys = {x.bucket_key for x in risk_buckets}
    all_keys = model_keys | risk_keys

    uncertainties: List[KeyUncertainty] = []

    if "manufacturing_product_sales" in all_keys and "asset_heavy_operation" in all_keys:
        uncertainties.append(
            KeyUncertainty(
                uncertainty="公司到底是客户买产品/设备，还是公司自投资产做运营？",
                why_it_matters="这决定公司是偏轻资产产品销售型，还是重资产运营型，估值和现金流逻辑完全不同。",
                related_buckets=["manufacturing_product_sales", "asset_heavy_operation"],
                discriminating_questions=[
                    "客户是否直接购买设备/车辆/产品？",
                    "是否存在公司自投资产并通过运营回收现金流？",
                    "资产由谁持有？折旧和维修由谁承担？",
                    "收入是一次性销售，还是按使用量/服务费持续收费？",
                ],
            )
        )

    if "project_delivery" in all_keys:
        uncertainties.append(
            KeyUncertainty(
                uncertainty="项目交付是否标准化，还是每个客户都需要大量定制？",
                why_it_matters="决定公司能否规模化复制，以及毛利率是否会被交付成本侵蚀。",
                related_buckets=["project_delivery"],
                discriminating_questions=[
                    "一个新项目中有多少模块可以复用？",
                    "单个项目从签约到验收回款需要多久？",
                    "每个项目需要多少实施人员？",
                    "不同项目毛利率差异大不大？",
                ],
            )
        )

    if "data_ai_model" in all_keys:
        uncertainties.append(
            KeyUncertainty(
                uncertainty="AI/数据能力是核心壁垒，还是研发/交付效率工具？",
                why_it_matters="如果AI只是内部工具，则不应按AI平台公司估值。",
                related_buckets=["data_ai_model"],
                discriminating_questions=[
                    "AI是否直接决定客户购买或产品性能？",
                    "AI相比传统方法带来什么量化提升？",
                    "数据是否独占并形成持续反馈闭环？",
                    "模型输出是否仍需要大量人工验证？",
                ],
            )
        )

    if "expansion_story" in all_keys or any(x.role == "valuation_story" for x in business_lines):
        uncertainties.append(
            KeyUncertainty(
                uncertainty="当前真实收入、增长业务和估值叙事是否错位？",
                why_it_matters="如果当前收入来自小业务，但融资按平台/多行业故事估值，可能存在估值泡沫。",
                related_buckets=["expansion_story", "financing_valuation_story"],
                discriminating_questions=[
                    "当前收入主要来自哪条业务线？",
                    "增长最快的业务线收入基数是多少？",
                    "估值主要依据当前收入还是未来平台故事？",
                    "新业务是否已有真实收入、复购和毛利？",
                ],
            )
        )

    if "policy_driven" in all_keys:
        uncertainties.append(
            KeyUncertainty(
                uncertainty="客户需求是政策驱动，还是真实经济 ROI 驱动？",
                why_it_matters="如果主要依赖政策/示范项目，政策退坡后收入可持续性存疑。",
                related_buckets=["policy_driven", "government_industrial_landing"],
                discriminating_questions=[
                    "客户中有多少是纯商业ROI驱动？",
                    "如果没有补贴或政策要求，客户是否仍会采购？",
                    "客户是否有明确降本增效测算？",
                    "是否有非政策客户的复购案例？",
                ],
            )
        )

    if "team_credibility_story" in all_keys:
        uncertainties.append(
            KeyUncertainty(
                uncertainty="团队/学术/名人背书是否真正转化为排他壁垒？",
                why_it_matters="学历、奖项、名人、实验室背书本身不等于商业化能力。",
                related_buckets=["team_credibility_story"],
                discriminating_questions=[
                    "专家/实验室与公司的关系是全职、股东、顾问还是普通合作？",
                    "是否有排他性成果转化协议？",
                    "知识产权归属公司还是高校/实验室？",
                    "背书是否已经转化为产品、客户或收入？",
                ],
            )
        )

    if not uncertainties:
        uncertainties.append(
            KeyUncertainty(
                uncertainty="商业模式和核心收入来源仍需进一步确认。",
                why_it_matters="决定后续应该按什么类型公司分析和估值。",
                related_buckets=list(all_keys)[:3],
                discriminating_questions=[
                    "当前收入主要来自哪类业务？",
                    "客户为什么付费？",
                    "收入是否可持续和可复制？",
                ],
            )
        )

    return uncertainties[:8]


# =========================================================
# 9. 总结生成
# =========================================================

def generate_structure_summary(
    industry_tags: List[IndustryTag],
    business_lines: List[BusinessLine],
    business_models: List[BusinessModelHypothesis],
    risks: List[RiskBucket],
) -> str:
    industries = "、".join([x.label for x in industry_tags[:3]])
    models = "、".join([x.bucket_name for x in business_models[:3]])
    main_lines = "、".join([x.name for x in business_lines[:3]])

    return (
        f"系统初步识别该项目涉及行业：{industries}；"
        f"主要业务线包括：{main_lines}；"
        f"可能适用的投资逻辑包括：{models}。"
        f"该识别仅作为后续分析入口，不代表最终判断。"
    )


# =========================================================
# 10. 主入口
# =========================================================

def detect_project_structure(text: str) -> ProjectStructure:
    industry_tags = detect_industry_tags(text)
    business_models = detect_business_model_hypotheses(text)
    business_lines = detect_business_lines(
        text=text,
        business_models=business_models,
        industry_tags=industry_tags,
    )
    risk_buckets = detect_risk_buckets(text)

    key_uncertainties = generate_key_uncertainties(
        business_models=business_models,
        risk_buckets=risk_buckets,
        business_lines=business_lines,
    )

    structure_summary = generate_structure_summary(
        industry_tags=industry_tags,
        business_lines=business_lines,
        business_models=business_models,
        risks=risk_buckets,
    )

    return ProjectStructure(
        industry_tags=industry_tags,
        business_lines=business_lines,
        business_model_hypotheses=business_models,
        risk_buckets=risk_buckets,
        key_uncertainties=key_uncertainties,
        structure_summary=structure_summary,
    )


# =========================================================
# 11. 测试入口
# =========================================================

if __name__ == "__main__":
    # 斯年智驾
    SINIAN_TEXT = """
    斯年智驾是一家专注于自动驾驶卡车商业化运营的公司。
    主要业务包括：1）自动驾驶软硬件设备销售；2）智能物流代运营服务；
    3）物流园区智能化项目实施。
    公司拥有完整的自动驾驶技术栈，包括感知、决策、执行全栈能力。
    已与多家头部物流企业建立合作关系，运营里程超过1000万公里。
    已部署240台无人重载运输车辆，落地20个项目。
    前五大客户收入占比超过60%。
    """

    # 杉海创新
    SHANHAI_TEXT = """
    杉海创新是一家基于AI大模型和生物计算技术的新材料研发平台公司。
    公司主营业务包括：1）AI驱动的材料筛选平台服务；
    2）生物基日化原料的研发与销售；3）新能源材料的技术授权。
    核心技术为自主研发的智能分子设计平台，已申请20余项核心专利。
    与多家国际美妆品牌建立战略合作，共同开发定制化原料解决方案。
    已完成千吨级生物基日化原料产线的建设，并开始向食品和医药领域扩张。
    """

    import json

    print("=" * 60)
    print("斯年智驾 - 项目结构识别")
    print("=" * 60)
    result = detect_project_structure(SINIAN_TEXT)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("杉海创新 - 项目结构识别")
    print("=" * 60)
    result = detect_project_structure(SHANHAI_TEXT)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
