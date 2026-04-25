# -*- coding: utf-8 -*-
"""
pipeline.py — 2.0 会后分析主流程编排

数据流: Step6 → Step7 → Step8 → Step9
沉淀: 问题库候选 + 行业认知候选 + 用户画像候选
"""
import json
import os
from typing import Dict, Any, List, Optional

from .schemas import (
    V2Output, DialogueTurn, UserProfileCandidate,
    QuestionCandidate, IndustryInsightCandidate
)
from .services import step6_extractor, step7_validator, step8_updater, step9_decider
from .services import step0_profile_loader, step10_fit_decider, candidate_writer
from .renderer import render_v2_report


class PipelineV2:
    """2.0 会后分析主流程"""

    def __init__(self, project_id: str, project_name: str, workspace_dir: str = None):
        self.project_id = project_id
        self.project_name = project_name
        # workspace 路径
        if workspace_dir is None:
            workspace_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "workspace", project_name)
            )
        self.workspace_dir = workspace_dir
        self.model = None  # 可传入 DeepSeek 模型名
        # Step0 基金画像
        self.fund_profile = None

    # ============================================================
    # Step0: 投资人/基金画像加载
    # ============================================================

    def run_step0(
        self,
        profile_id: str = None,
        user_description: str = ""
    ) -> Dict[str, Any]:
        """
        Step0: 加载投资人/基金画像

        Args:
            profile_id: 已有画像ID，若为 None 则根据 user_description 匹配或创建
            user_description: 用户描述（用于生成新画像）

        Returns:
            画像 dict
        """
        profile = step0_profile_loader.load_or_create_profile(
            profile_id=profile_id,
            user_description=user_description
        )
        self.fund_profile = step0_profile_loader.to_dict(profile)

        # 持久化
        self._save_json("step0", "step0.json", self.fund_profile)

        return self.fund_profile

    # ============================================================
    # Step6: 新增信息提取
    # ============================================================

    def run_step6(
        self,
        step5_summary: str,
        meeting_record: str
    ) -> Dict[str, Any]:
        """Step6: 从会议记录中提取新增信息"""
        output = step6_extractor.extract(
            step5_summary=step5_summary,
            meeting_record=meeting_record,
            model=self.model
        )

        # 持久化（版本号文件 + latest）
        self._save_versioned_json("step6", "step6", step6_extractor.to_dict(output))

        return step6_extractor.to_dict(output)

    # ============================================================
    # Step7: 问题对齐 + 会议质量
    # ============================================================

    def run_step7(
        self,
        step4_questions: List[str],
        step6_new_information: List[Dict[str, Any]],
        meeting_record: str = None,
        step6_summary: str = None
    ) -> Dict[str, Any]:
        """
        Step7: 问题对齐与会议质量评估

        优先使用 step6_new_information（新两步架构），不推荐用旧参数。
        """
        output = step7_validator.validate(
            step4_questions=step4_questions,
            meeting_record=meeting_record,
            step6_summary=step6_summary,
            step6_new_information=step6_new_information,
            model=self.model
        )

        # 持久化（版本号文件 + latest）
        self._save_versioned_json("step7", "step7", step7_validator.to_dict(output))

        return step7_validator.to_dict(output)

    # ============================================================
    # Step8: 对抗式认知更新
    # ============================================================

    def run_step8(
        self,
        step5_judgements: List[Dict[str, str]],
        step7_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step8: 认知更新（规则驱动）"""
        output = step8_updater.update(
            step5_judgements=step5_judgements,
            step7_result=step7_result,
            model=self.model
        )

        # 持久化（版本号文件 + latest）
        self._save_versioned_json("step8", "step8", step8_updater.to_dict(output))

        return step8_updater.to_dict(output)

    # ============================================================
    # Step9: 决策与行动
    # ============================================================

    def run_step9(
        self,
        step6_output: Dict[str, Any],
        step7_output: Dict[str, Any],
        step8_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step9: 双层决策与行动（v3）

        架构：Step9 只接收 step8_summary（轻量摘要），不接收原始完整数据。
        目的：避免 token 过多导致 LLM 输出截断。
        """
        # 生成 Step8 摘要（轻量结构化结论）
        step8_summary = step8_updater.build_step8_summary(step8_output)

        # 生成 Step7 摘要
        step7_summary = self._summarize_step7(step7_output)

        # 持久化 step8_summary（给后续分析用）
        summary_path = os.path.join(self._ensure_dir("step8"), "step8_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(step8_summary, f, ensure_ascii=False, indent=2)

        output = step9_decider.decide(
            step8_summary=step8_summary,
            step7_summary=step7_summary,
            model=self.model
        )

        # 持久化（版本号文件 + latest）
        self._save_versioned_json("step9", "step9", output)

        return output

    # ============================================================
    # Step10: Fit 判断（投资匹配）
    # ============================================================

    def run_step10(
        self,
        step9_output: Dict[str, Any],
        profile_id: str = None,
        user_description: str = "",
        user_feedback: str = ""
    ) -> Dict[str, Any]:
        """
        Step10: Fit 判断（项目是否适合当前基金/投资人）

        Args:
            step9_output: Step9 输出的项目决策
            profile_id: 基金画像ID（可选，默认使用 self.fund_profile）
            user_description: 用户描述（用于生成新画像）
            user_feedback: 用户额外反馈

        Returns:
            Step10 输出 dict
        """
        # Step0: 确保有基金画像
        if self.fund_profile is None:
            self.fund_profile = self.run_step0(
                profile_id=profile_id,
                user_description=user_description
            )

        project_summary = {
            "project_id": self.project_id,
            "project_name": self.project_name
        }

        # Step10: Fit 判断
        output = step10_fit_decider.decide_fit(
            fund_profile=self.fund_profile,
            step9_output=step9_output,
            project_summary=project_summary,
            user_feedback=user_feedback,
            model=self.model
        )

        # 持久化
        self._save_json("step10", "step10.json", output)

        # 沉淀候选（到 knowledge_base/candidates/）
        self._persist_step10_candidates(output)

        return output

    def _persist_step10_candidates(self, step10_output: Dict[str, Any]):
        """
        将 Step10 的候选沉淀写入 knowledge_base/candidates/
        """
        writer = candidate_writer.get_writer()

        # 画像更新候选
        for item in step10_output.get("candidate_profile_updates", []):
            writer.append_candidate("profile_candidates", item)

        # Fit 反馈候选
        case_record = step10_output.get("candidate_case_record", {})
        if case_record:
            writer.append_fit_feedback(
                project_name=case_record.get("project_name", self.project_name),
                fit_decision=step10_output.get("fit_decision", "not_fit"),
                final_decision=step10_output.get("final_recommendation", "pass"),
                fit_reason=case_record.get("fit_reason", []),
                project_judgement=case_record.get("project_judgement", ""),
                source_profile=case_record.get("source_profile", "")
            )

    # ============================================================
    # 全流程运行
    # ============================================================

    def run_full(
        self,
        meeting_record: str,
        step5_summary: str,
        step5_judgements: List[Dict[str, str]],
        step5_decision: str,
        step4_questions: List[str],
        dialogue_history: List[DialogueTurn] = None,
        profile_id: str = "government_fund",
        user_description: str = "",
        user_feedback: str = ""
    ) -> Dict[str, Any]:
        """
        运行完整的 2.0 会后分析流程

        Args:
            meeting_record: 原始会议记录
            step5_summary: Step5 会前判断摘要
            step5_judgements: Step5 的假设与判断列表
            step5_decision: Step5 的决策结论
            step4_questions: Step4 的关键问题列表
            dialogue_history: 对话历史（可选）
            profile_id: 基金画像ID（默认 government_fund）
            user_description: 用户描述（用于生成新画像）
            user_feedback: 用户额外反馈

        Returns:
            包含所有步骤输出的完整结果
        """
        results = {}

        # Step0: 加载基金画像
        step0 = self.run_step0(profile_id=profile_id, user_description=user_description)
        results["step0"] = step0

        # Step6: 新增信息提取
        step6 = self.run_step6(
            step5_summary=step5_summary,
            meeting_record=meeting_record
        )
        results["step6"] = step6
        step6_summary_text = step6.get("meeting_summary", "")

        # Step7: 问题对齐 + 会议质量（传 step6_new_information，走两步架构）
        step7 = self.run_step7(
            step4_questions=step4_questions,
            step6_new_information=step6.get("new_information", []),
            meeting_record=meeting_record,
            step6_summary=step6_summary_text
        )
        results["step7"] = step7

        # 生成 Step7 摘要（用于 Step9 的输入）
        step7_summary_text = self._summarize_step7(step7)
        step7_validation_summary = self._summarize_validation(step7)

        # Step8: 认知更新（规则驱动，需注入 step6 new_information 以查 info_type）
        step7_for_step8 = dict(step7)  # 浅拷贝，避免修改原始 step7
        step7_for_step8["_step6_new_information"] = step6.get("new_information", [])
        step8 = self.run_step8(
            step5_judgements=step5_judgements,
            step7_result=step7_for_step8
        )
        results["step8"] = step8

        # Step9: 双层决策与行动
        step9 = self.run_step9(
            step6_output=step6,
            step7_output=step7,
            step8_output=step8
        )
        results["step9"] = step9

        # 沉淀层：问题库候选 + 行业认知候选 + 用户画像候选
        沉淀_result = self._extract_candidates(step7, step8, dialogue_history or [])
        results["沉淀"] =沉淀_result

        # Step10: Fit 判断（项目是否适合当前基金）
        step10 = self.run_step10(
            step9_output=step9,
            profile_id=profile_id,
            user_description=user_description,
            user_feedback=user_feedback
        )
        results["step10"] = step10

        # 保存对话历史
        if dialogue_history:
            self._save_dialogue_history(dialogue_history)

        # 生成完整报告
        results["report"] = self._render_report(results)

        return results

    # ============================================================
    # 单步运行（用于 UI 分步执行）
    # ============================================================

    def run_single_step(
        self,
        step_name: str,
        meeting_record: str = None,
        step5_summary: str = None,
        step5_judgements: List[Dict[str, str]] = None,
        step5_decision: str = None,
        step4_questions: List[str] = None,
        step6_summary: str = None,
        step6_new_info: List[Dict[str, Any]] = None,
        step7_summary: str = None,
        step7_quality: Dict[str, Any] = None,
        step7_validation_summary: str = None,
        step8_updates: Dict[str, Any] = None,
        dialogue_history: List[DialogueTurn] = None,
    ) -> Dict[str, Any]:
        """
        运行单个步骤

        step_name: step6 / step7 / step8 / step9 / 沉淀
        """
        if step_name == "step6":
            return self.run_step6(step5_summary, meeting_record)
        elif step_name == "step7":
            return self.run_step7(
                step4_questions=step4_questions,
                step6_new_information=step6_new_info or [],
                meeting_record=meeting_record,
                step6_summary=step6_summary
            )
        elif step_name == "step8":
            # step7_result 是 Step7 的完整 dict 输出，注入 step6 info 以便查 info_type
            step7_for_step8 = dict(step7_result) if step7_result else {}
            step7_for_step8["_step6_new_information"] = step6_new_info or []
            return self.run_step8(step5_judgements=step5_judgements, step7_result=step7_for_step8)
        elif step_name == "step9":
            return self.run_step9(
                step6_output={"new_information": step6_new_info or []},
                step7_output=step7_quality or {},
                step8_output=step8_updates or {}
            )
        elif step_name == "沉淀":
            return self._extract_candidates(
                step7_quality or {},
                step8_updates or {},
                dialogue_history or []
            )
        else:
            raise ValueError(f"未知步骤: {step_name}")

    # ============================================================
    # 沉淀层
    # ============================================================

    def _extract_candidates(
        self,
        step7: Dict[str, Any],
        step8: Dict[str, Any],
        dialogue_history: List[DialogueTurn]
    ) -> Dict[str, List]:
        """
        从 Step7/8 和对话历史中提取沉淀候选
        第一版：只做结构化输出，不做自动入库
        """
        # 读取之前的沉淀文件（增量追加）
        q_candidates = self._load_candidates("questions.json")
        i_candidates = self._load_candidates("industry_insights.json")
        u_candidates = self._load_candidates("user_profile_candidates.json")

        # TODO: 调用 LLM 提炼高质量候选（第一版先用规则判断）
        # 第一版 MVP: 从 step7 的低质量回答中提名问题
        question_validations = step7.get("question_validation", [])
        for v in question_validations:
            if v.get("quality") == "weak":
                q_candidates.append({
                    "question": v.get("original_question", ""),
                    "use_case": "质量弱的问题（需优化后复用）",
                    "why_effective": f"回答质量为 weak，可能暴露了真实风险点",
                    "triggered_at": "Step7",
                    "trigger_reason": f"回答质量: {v.get('quality')}"
                })

        # 从 step8 的被推翻/削弱的假设中提炼行业洞察
        hypothesis_updates = step8.get("hypothesis_updates", [])
        for h in hypothesis_updates:
            if h.get("change_type") in ("weakened", "overturned"):
                i_candidates.append({
                    "industry": "通用",
                    "insight": f"假设 '{h.get('hypothesis', '')}' 被新证据{h.get('change_type')}，需关注",
                    "core_question": h.get("final_view", ""),
                    "bucket_target": "risk_management",
                    "triggered_at": "Step8",
                    "confidence": "medium",
                    "note": "待更多交叉验证"
                })

        # 从对话历史中提炼用户画像
        for turn in dialogue_history:
            if turn.role == "user" and len(turn.content) > 10:
                u_candidates.append({
                    "dimension": "待分析",
                    "pattern": turn.content[:50],
                    "evidence": turn.content,
                    "triggered_at": "对话"
                })

        # 去重（基于问题/洞察的文本）
        q_candidates = self._deduplicate_candidates(q_candidates, "question")
        i_candidates = self._deduplicate_candidates(i_candidates, "insight")
        u_candidates = self._deduplicate_candidates(u_candidates, "pattern")

        # 持久化
        self._save_v2_context("questions.json", q_candidates)
        self._save_v2_context("industry_insights.json", i_candidates)
        self._save_v2_context("user_profile_candidates.json", u_candidates)

        return {
            "question_candidates": q_candidates,
            "industry_insight_candidates": i_candidates,
            "user_profile_candidates": u_candidates
        }

    # ============================================================
    # 辅助方法
    # ============================================================

    def _ensure_dir(self, sub_dir: str):
        """确保子目录存在"""
        path = os.path.join(self.workspace_dir, sub_dir)
        os.makedirs(path, exist_ok=True)
        return path

    def _get_next_version_num(self, sub_dir: str, step_prefix: str) -> str:
        """
        自动找最大版本号，返回形如 _001 的字符串。
        扫描 {workspace}/{sub_dir}/ 目录下所有 {step_prefix}_v2_2_*.json 文件，
        提取序号，最大序号+1，不存在则返回 _001。
        """
        import re
        dir_path = self._ensure_dir(sub_dir)
        pattern = re.compile(rf"^{re.escape(step_prefix)}_v2_2_(\d{{3}})\.json$")
        max_num = 0
        for fname in os.listdir(dir_path):
            m = pattern.match(fname)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
        return f"_{max_num + 1:03d}"

    def _save_versioned_json(self, sub_dir: str, step_prefix: str, data: Dict[str, Any]):
        """
        保存带版本号的 JSON 文件，同时写一份 latest.json 方便后续步骤读取。
        版本命名：{step_prefix}_v2_2_001.json, _002, _003 ...
        """
        version = self._get_next_version_num(sub_dir, step_prefix)
        versioned_name = f"{step_prefix}_v2_2{version}.json"
        self._save_json(sub_dir, versioned_name, data)
        # 同时写一份 latest.json（覆盖模式，方便后续步骤读取）
        self._save_json(sub_dir, f"{step_prefix}_latest.json", data)

    def _ensure_v2_context_dir(self):
        """确保 v2_context 目录存在"""
        return self._ensure_dir("v2_context")

    def _save_json(self, sub_dir: str, filename: str, data: Dict[str, Any]):
        """保存 JSON 文件到 step 目录"""
        path = os.path.join(self._ensure_dir(sub_dir), filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_v2_context(self, filename: str, data: list):
        """保存沉淀文件到 v2_context"""
        path = os.path.join(self._ensure_v2_context_dir(), filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_candidates(self, filename: str) -> list:
        """读取沉淀文件（用于增量追加）"""
        path = os.path.join(self._ensure_v2_context_dir(), filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_dialogue_history(self, dialogue_history: List[DialogueTurn]):
        """保存对话历史"""
        path = os.path.join(self._ensure_v2_context_dir(), "dialogue_history.json")
        data = [
            {"turn_id": t.turn_id, "role": t.role, "content": t.content, "timestamp": t.timestamp}
            for t in dialogue_history
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_dialogue_history(self) -> List[DialogueTurn]:
        """读取对话历史"""
        path = os.path.join(self._ensure_v2_context_dir(), "dialogue_history.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [DialogueTurn(**d) for d in data]
        return []

    def _summarize_step7(self, step7: Dict[str, Any]) -> str:
        """生成 Step7 的摘要文本"""
        quality = step7.get("meeting_quality", {})
        validations = step7.get("question_validation", [])

        answered = sum(1 for v in validations if v.get("status") == "answered")
        evaded = sum(1 for v in validations if v.get("status") == "evaded")

        return (
            f"会议整体可信度：{quality.get('overall_confidence', 'medium')}；"
            f"回答直接性：{quality.get('answer_directness', 'medium')}；"
            f"共 {len(validations)} 个问题，{answered} 个被正面回答，{evaded} 个被回避。"
        )

    def _summarize_validation(self, step7: Dict[str, Any]) -> str:
        """生成问题验证的摘要"""
        validations = step7.get("question_validation", [])
        parts = []
        for v in validations:
            parts.append(f"Q: {v.get('original_question', '')[:30]}... → {v.get('status', '')} ({v.get('quality', '')})")
        return "\n".join(parts)

    def _deduplicate_candidates(self, candidates: list, key: str) -> list:
        """基于文本字段去重"""
        seen = set()
        result = []
        for c in candidates:
            val = c.get(key, "")
            if val and val not in seen:
                seen.add(val)
                result.append(c)
        return result

    def _render_report(self, results: Dict[str, Any]) -> str:
        """渲染完整报告"""
        from .schemas import Step6Output, Step7Output, Step8Output, Step9Output
        from .services import step6_extractor, step7_validator, step8_updater, step9_decider

        # 统一为 dict 格式（避免重复调用 to_dict()）
        step6_raw = results.get("step6", {})
        step7_raw = results.get("step7", {})
        step8_raw = results.get("step8", {})
        step9_raw = results.get("step9", {})

        # 如果是 dataclass，转为 dict；如果是 dict，直接使用
        step6 = step6_extractor.to_dict(step6_raw) if hasattr(step6_raw, "meeting_summary") else step6_raw
        step7 = step7_validator.to_dict(step7_raw) if hasattr(step7_raw, "meeting_quality") else step7_raw
        step8 = step8_updater.to_dict(step8_raw) if hasattr(step8_raw, "hypothesis_updates") else step8_raw
        step9 = step9_decider.to_dict(step9_raw) if hasattr(step9_raw, "next_decision") else step9_raw

        沉淀_data = results.get("沉淀", {})

        return render_v2_report(
            project_name=self.project_name,
            step6=step6,
            step7=step7,
            step8=step8,
            step9=step9,
            question_candidates=沉淀_data.get("question_candidates", []),
            industry_insight_candidates=沉淀_data.get("industry_insight_candidates", []),
            user_profile_candidates=沉淀_data.get("user_profile_candidates", [])
        )
