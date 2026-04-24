from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class BucketDefinition:
    key: str
    label: str
    description: str
    common_checks: List[str] = field(default_factory=list)


GENERAL_BUCKETS: Dict[str, BucketDefinition] = {
    "tech_barrier": BucketDefinition(
        key="tech_barrier",
        label="技术/壁垒是否成立",
        description="判断技术是不是行业通用、是否形成真实壁垒、是否容易被复制，AI/平台是否只是工具包装。",
        common_checks=[
            "这项技术是行业通用技术、工程常规，还是公司独有核心能力？",
            "技术优势是概念优势、实验优势，还是已落入真实产品与客户验证？",
            "如果去掉公司自述，这项技术是否仍然成立为壁垒？",
            "AI/算法/平台在这里是核心护城河，还是效率工具？",
        ],
    ),
    "customer_value": BucketDefinition(
        key="customer_value",
        label="客户为什么付钱",
        description="判断客户真实购买动机、付费点与替代动机，不看技术炫耀，只看客户价值。",
        common_checks=[
            "客户到底为哪个具体价值付钱：性能、成本、合规、效率还是卖点？",
            "该价值是可有可无，还是会影响客户收入、产品力或生产稳定性？",
            "客户更换现有方案的动力强不强？",
            "公司讲的技术指标，是否真的对应客户订单与采购动作？",
        ],
    ),
    "commercialization": BucketDefinition(
        key="commercialization",
        label="商业化路径是否成立",
        description="判断从实验室到客户验证到交付放量的路径是否真实、节奏是否合理。",
        common_checks=[
            "当前处于什么阶段：概念、实验室、中试、客户验证、小批量、量产？",
            "真正卡住商业化的瓶颈是什么？",
            "交付、良率、验证周期、供应链是否构成增长限制？",
            "增长来自新客户、新产品，还是老客户放量？",
        ],
    ),
    "expansion_story": BucketDefinition(
        key="expansion_story",
        label="扩张/故事是否合理",
        description="判断多行业、多场景、第二曲线等扩张叙事是否真实可落地，还是提前讲故事。",
        common_checks=[
            "公司当前业务底盘是否足够扎实，能够支撑新故事？",
            "新业务是已验证增长点，还是论文、合作、概念和规划？",
            "跨行业扩张是否会遇到完全不同的验证体系、法规、供应链和销售逻辑？",
            "历史上该行业类似扩张通常成功还是失败？",
        ],
    ),
    "team_credibility": BucketDefinition(
        key="team_credibility",
        label="团队/背书是否被高估",
        description="判断诺奖、院士、博士、名校、顾问等背书是否真的转化为商业化能力，而不是人设包装。",
        common_checks=[
            "团队强项更偏科研、工程、销售还是管理？",
            "背书是否转化为排他性技术、实际产品或客户资源？",
            "高学历/强学术是否被误当成可规模化商业能力？",
            "团队能力与当前阶段是否匹配，而不是只看履历好不好看？",
        ],
    ),
}


def list_bucket_keys() -> List[str]:
    return list(GENERAL_BUCKETS.keys())


def get_general_bucket(bucket_key: str) -> BucketDefinition:
    return GENERAL_BUCKETS[bucket_key]
