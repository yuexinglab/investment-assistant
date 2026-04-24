"""
template_loader.py — v2.5 模板加载器
加载行业模板JSON，提供字段/维度/规则的访问接口
"""

import json
import os

# 模板路径（与项目根目录同级的模板文件）
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))  # 项目根目录
DEFAULT_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "advanced_materials_v2.5.json")


class TemplateLoader:
    """模板加载器，提供v2.5模板的各个组成部分"""

    def __init__(self, template_path: str = None):
        """
        初始化加载器
        :param template_path: 模板JSON路径，默认使用v2.5通用模板
        """
        if template_path is None:
            # 优先从workspace目录加载
            if os.path.exists(DEFAULT_TEMPLATE_PATH):
                template_path = DEFAULT_TEMPLATE_PATH
            else:
                # 回退到项目父目录
                template_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "advanced_materials_v2.5.json"
                )

        with open(template_path, "r", encoding="utf-8") as f:
            self.template = json.load(f)

        self.template_id = self.template.get("template_id", "")
        self.version = self.template.get("version", "2.5")

    @property
    def core_fields(self) -> list:
        """29个核心字段列表"""
        return self.template.get("core_fields", [])

    @property
    def dimensions(self) -> list:
        """5个维度列表"""
        return self.template.get("dimensions", [])

    @property
    def sub_dimensions(self) -> list:
        """所有子维度（24个）"""
        subs = []
        for dim in self.dimensions:
            subs.extend(dim.get("sub_dimensions", []))
        return subs

    @property
    def risk_rules(self) -> list:
        """8条风险规则"""
        return self.template.get("risk_rules", [])

    @property
    def special_flags(self) -> dict:
        """四坑七难题"""
        return self.template.get("special_flags", {})

    @property
    def step1_config(self) -> dict:
        """Step1通用理解配置"""
        return self.template.get("step1_prompts", {})

    @property
    def investor_judgment_config(self) -> dict:
        """Step9投资人判断层配置"""
        return self.template.get("investor_judgment_layer", {})

    def get_field_definition(self, field_name: str) -> dict:
        """获取某个字段的详细定义"""
        # 在dimensions的sub_dimensions中查找
        for dim in self.dimensions:
            for sub in dim.get("sub_dimensions", []):
                if sub.get("field") == field_name:
                    return sub
        return {}

    def get_dimension_by_field(self, field_name: str) -> dict:
        """获取某字段所属的维度"""
        for dim in self.dimensions:
            for sub in dim.get("sub_dimensions", []):
                if sub.get("field") == field_name:
                    return dim
        return {}

    def build_field_extraction_prompt(self, bp_text: str) -> str:
        """
        构建字段抽取的Prompt
        基于Step1通用理解的结果，引导AI抽取核心字段
        """
        fields = self.core_fields
        prompt = f"""请从以下BP材料中，抽取以下{len(fields)}个核心字段的信息。

对于每个字段，请标注：
- known: 有明确信息
- partial: 有部分信息但不完整
- missing: 未提及
- weak_evidence: 有提及但缺乏证据支撑
- conflicting: 信息矛盾

字段列表：
{chr(10).join([f'{i+1}. {f}' for i, f in enumerate(fields)])}

BP材料：
{bp_text[:10000]}

输出格式：
字段名: [状态] | 提取的信息 | 来源依据
"""
        return prompt

    def build_gap_analysis_prompt(self, field_extraction_result: str, step1_result: str) -> str:
        """
        构建缺口识别的Prompt
        基于字段抽取结果，识别高/中/低优先级缺口
        """
        rules = self.risk_rules
        rules_text = "\n".join([f"- {r['rule_id']}: {r['meaning']}" for r in rules])

        prompt = f"""基于以下字段抽取结果和Step1通用理解，识别项目的关键缺口：

【Step1通用理解摘要】
{step1_result[:2000]}

【字段抽取结果】
{field_extraction_result[:3000]}

【风险规则参考】
{rules_text}

请识别：
1. 高优先级缺口（必须追问的核心问题）
2. 中优先级缺口（重要但不紧急）
3. 低优先级缺口（nice to have）

输出格式：
## 高优先级缺口
- 缺口字段 | 原因 | 优先级

## 中优先级缺口
...

## 低优先级缺口
...
"""
        return prompt

    def build_question_generation_prompt(self, gaps: str, step1_result: str) -> str:
        """
        构建问题生成的Prompt
        基于缺口清单，生成追问问题
        """
        prompt = f"""基于以下缺口清单，生成投资人应该追问的核心问题：

【Step1通用理解摘要】
{step1_result[:1500]}

【缺口清单】
{gaps[:2000]}

请为高优先级缺口生成追问问题，每个问题包含：
- question: 追问问题
- why: 为什么问这个问题
- ideal_answer: 理想回答
- risk_signal: 危险信号（什么样的回答是减分项）

输出格式：
## 高优先级问题

### 问题1：[追问问题]
- 为什么问：...
- 理想回答：...
- 危险信号：...

（以此类推）
"""
        return prompt

    def to_dict(self) -> dict:
        """返回原始模板字典"""
        return self.template


# 全局单例
_template_loader = None


def get_template_loader(template_path: str = None) -> TemplateLoader:
    """获取模板加载器单例"""
    global _template_loader
    if _template_loader is None:
        _template_loader = TemplateLoader(template_path)
    return _template_loader
