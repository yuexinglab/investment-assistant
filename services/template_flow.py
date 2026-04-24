"""
template_flow.py — v2.5 模板驱动流程执行引擎
执行9步流程：Step1通用理解 → Step2-8模板驱动 → Step9投资人判断
"""

import time
import traceback
from services.template_loader import get_template_loader
from services.deepseek_service import call_deepseek
from prompts import step1_prompt, step9_prompt
from step3.step3_service import Step3Service, simple_bucket_selector
from step4.step4_service import Step4Service
import json


class TemplateFlowExecutor:
    """
    模板流程执行器
    完整执行v2.5的9步流程，输出投资判断报告
    """

    def __init__(self, template_path: str = None):
        print("[TemplateFlowExecutor] Initializing...")
        self.loader = get_template_loader(template_path)
        print(f"[TemplateFlowExecutor] Template loaded: v{self.loader.version}")
        self.steps_outputs = {}  # 存储各步骤的输出

    def run_full_flow(self, bp_text: str, company_name: str = "", industry: str = "") -> dict:
        """
        执行完整9步流程

        :param bp_text: BP原文
        :param company_name: 公司名称
        :param industry: 行业类型
        :return: 包含所有步骤输出的字典
        """
        print(f"[v2.5] Starting 9-step flow for {company_name}...")
        print(f"[v2.5] BP text length: {len(bp_text)} chars")
        print("=" * 50)

        # ===== Step1: 通用理解（升级版）=====
        print("[Step1] Running general understanding...")
        step1_result = self._run_step1(bp_text, company_name, industry)
        self.steps_outputs["step1"] = step1_result
        print(f"[Step1] Done. Length: {len(step1_result)} chars")

        # ===== Step2: 模板注入 =====
        print("[Step2] Injecting template...")
        template_info = self._run_step2()
        self.steps_outputs["step2"] = template_info

        # ===== Step3: 判断辅助背景层 =====
        print("[Step3] Running background validation...")
        step3_result = self._run_step3(bp_text, step1_result, industry)
        self.steps_outputs["step3"] = step3_result
        print(f"[Step3] Done. Length: {len(step3_result)} chars")

        # ===== Step4: 决策缺口层 =====
        print("[Step4] Identifying decision gaps...")
        gaps = self._run_step4(step3_result, step1_result, bp_text)
        self.steps_outputs["step4"] = gaps
        print(f"[Step4] Done. Length: {len(gaps)} chars")

        # ===== Step5: 问题生成 =====
        print("[Step5] Generating questions...")
        questions = self._run_step5(gaps, step1_result)
        self.steps_outputs["step5"] = questions
        print(f"[Step5] Done. Length: {len(questions)} chars")

        # ===== Step6: 规则命中 =====
        print("[Step6] Checking risk rules...")
        risk_tags = self._run_step6(step3_result, step1_result)
        self.steps_outputs["step6"] = risk_tags
        print(f"[Step6] Done. Length: {len(risk_tags)} chars")

        # ===== Step7: 评分计算（可选）=====
        print("[Step7] Calculating scores...")
        scores = self._run_step7(step3_result, step1_result)
        self.steps_outputs["step7"] = scores
        print(f"[Step7] Done.")

        # ===== Step8: 结构化报告 =====
        print("[Step8] Generating structured report...")
        structure_report = self._run_step8(
            step1_result, step3_result, gaps, questions, risk_tags, scores
        )
        self.steps_outputs["step8"] = structure_report
        print(f"[Step8] Done. Length: {len(structure_report)} chars")

        # ===== Step9: 投资人判断层（核心质变点）=====
        print("[Step9] Running investor judgment...")
        investor_judgment = self._run_step9(
            step1_result, step3_result, gaps, risk_tags, structure_report, company_name
        )
        self.steps_outputs["step9"] = investor_judgment
        print(f"[Step9] Done. Length: {len(investor_judgment)} chars")

        print("=" * 50)
        print("[v2.5] Flow completed successfully!")

        return {
            "version": "v2_5",
            "company_name": company_name,
            "industry": industry,
            "step1_one_liner": self._extract_one_liner(step1_result),
            "step5_questions": questions,
            "step6_risk_tags": risk_tags,
            "step7_scores": scores,
            "step9_judgment": investor_judgment,
            "all_steps": self.steps_outputs,
            "final_report": investor_judgment,  # 对外展示用Step9输出
        }

    def _run_step1(self, bp_text: str, company_name: str, industry: str) -> str:
        """Step1: 通用理解（升级版One-liner）"""
        return call_deepseek(
            system_prompt=step1_prompt.SYSTEM_PROMPT,
            user_prompt=step1_prompt.build_user_prompt(bp_text, company_name, industry)
        )

    def _run_step2(self) -> dict:
        """Step2: 模板注入"""
        return {
            "template_id": self.loader.template_id,
            "version": self.loader.version,
            "dimensions": len(self.loader.dimensions),
            "core_fields": len(self.loader.core_fields),
            "risk_rules": len(self.loader.risk_rules),
        }

    def _run_step3(self, bp_text: str, step1_result: str, industry: str) -> str:
        """Step3: 判断辅助背景层（新版桶+行业增强）"""
        # 兜底行业
        if not industry:
            industry = "advanced_materials"

        service = Step3Service(call_llm=call_deepseek)
        selected_buckets = simple_bucket_selector(step1_result)

        result = service.run(
            step1_text=step1_result,
            bp_text=bp_text,
            industry=industry,
            selected_buckets=selected_buckets,
        )
        # 输出结构化JSON字符串，方便存储
        return result.model_dump_json(indent=2)

    def _run_step4(self, step3_result: str, step1_result: str, bp_text: str) -> str:
        """Step4: 决策缺口层（新版桶+行业增强）"""
        service = Step4Service(call_llm=call_deepseek)
        result = service.run(
            step1_text=step1_result,
            step3_json=step3_result,
            bp_text=bp_text,
        )
        return result.model_dump_json(indent=2)

    def _run_step5(self, gaps: str, step1_result: str) -> str:
        """Step5: 问题生成"""
        prompt = self.loader.build_question_generation_prompt(gaps, step1_result)
        return call_deepseek(
            system_prompt="你是一位资深投资人，擅长提出精准的尽调问题。",
            user_prompt=prompt
        )

    def _run_step6(self, step3_result: str, step1_result: str) -> str:
        """Step6: 规则命中（基于Step3背景证据）"""
        rules = self.loader.risk_rules
        rules_text = "\n".join([
            f"- {r['rule_id']}: 如果{r['if']}，则标记为{r['then']}，严重度{r['severity']}，含义：{r['meaning']}"
            for r in rules
        ])

        prompt = f"""基于以下风险规则和Step3背景证据，识别命中了哪些风险规则：

【风险规则】
{rules_text}

【Step1通用理解】
{step1_result[:2000]}

【Step3背景证据】
{step3_result[:2000]}

请识别并输出命中的风险规则，格式：
规则ID | 命中的条件 | 风险标签 | 严重度 | 含义

如果没有命中任何规则，请输出："未检测到显著风险规则"
"""
        return call_deepseek(
            system_prompt="你是一位风险识别专家，擅长从信息中识别潜在风险。",
            user_prompt=prompt
        )

    def _run_step7(self, step3_result: str, step1_result: str) -> dict:
        """Step7: 评分计算"""
        dimensions = self.loader.dimensions
        scoring_guide_text = "\n\n".join([
            f"{d.get('dimension_name', d.get('name', 'Unknown'))}（权重{d.get('weight', 0.2)}）：\n" + "\n".join([
                f"  - {s.get('name', 'Unknown')}: {s.get('scoring', {}).get('6', '见各子维度')}"
                for s in d.get("sub_dimensions", [])
            ])
            for d in dimensions
        ])

        prompt = f"""基于以下评分维度表，对项目进行评分：

【评分维度】
{scoring_guide_text}

【Step1通用理解】
{step1_result[:2000]}

【Step3背景证据】
{step3_result[:2000]}

请输出各维度评分（1-10分），格式：
维度名: [分数]/10 | 评分理由
综合评分：[X]/10
"""
        result = call_deepseek(
            system_prompt="你是一位专业投资人，擅长对项目进行结构化评分。",
            user_prompt=prompt
        )

        # 尝试提取评分
        try:
            lines = result.split("\n")
            scores = {}
            for line in lines:
                if ":" in line and "/10" in line:
                    dim_name = line.split(":")[0].strip()
                    score = line.split("/")[0].split(":")[-1].strip()
                    if score.isdigit():
                        scores[dim_name] = int(score)
            return {
                "scores": scores,
                "detail": result
            }
        except:
            return {"detail": result}

    def _run_step8(self, step1_result: str, step3_result: str, gaps: str,
                   questions: str, risk_tags: str, scores: dict) -> str:
        """Step8: 结构化报告"""
        scores_summary = scores.get("detail", "") if isinstance(scores, dict) else str(scores)

        prompt = f"""基于以下信息，生成结构化分析报告：

【通用理解】
{step1_result[:2000]}

【Step3背景证据】
{step3_result[:1500]}

【缺口分析】
{gaps[:1000]}

【问题清单】
{questions[:1000]}

【风险标签】
{risk_tags[:500]}

【评分结果】
{scores_summary[:500]}

请生成一份结构化报告，包含：
1. 业务底盘是什么
2. 最确定的部分（已验证）
3. 最不确定的部分（未验证）
4. 真实业务 vs 估值叙事
5. 下一步必须验证的3-5个点
"""
        return call_deepseek(
            system_prompt="你是一位专业投资人分析师，擅长生成结构化的分析报告。",
            user_prompt=prompt
        )

    def _run_step9(self, step1_result: str, step3_result: str, gaps: str,
                    risk_tags: str, structure_report: str, company_name: str) -> str:
        """Step9: 投资人判断层（核心）"""
        return call_deepseek(
            system_prompt=step9_prompt.SYSTEM_PROMPT,
            user_prompt=step9_prompt.build_user_prompt(
                step1_result=step1_result,
                step3_result=step3_result,
                gaps=gaps,
                risk_tags=risk_tags,
                structure_report=structure_report,
                company_name=company_name
            )
        )

    def _extract_one_liner(self, step1_result: str) -> str:
        """从Step1结果中提取One-liner"""
        if "一、" in step1_result:
            start = step1_result.find("一、")
            end = step1_result.find("二、", start)
            if end > start:
                return step1_result[start:end].strip()
        return step1_result[:300]


# 全局执行器单例
_flow_executor = None


def get_flow_executor(template_path: str = None) -> TemplateFlowExecutor:
    """获取流程执行器单例"""
    global _flow_executor
    if _flow_executor is None:
        _flow_executor = TemplateFlowExecutor(template_path)
    return _flow_executor
