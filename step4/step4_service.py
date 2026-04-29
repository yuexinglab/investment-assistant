"""
Step4 Service - v6.1 完整版
包含：基础扫描层（会话式）+ 深挖层（多路径）+ 会前提纲

v6.1 改动：
- scan 层：从简单列表 → {opening, follow_up, best_question} 结构
- deep dive 层：从 2 个 question_paths → main_path + backup_path + red_flag_question
- brief 展示：scan 只显示 best_question，deep dive 完整展开
"""

from __future__ import annotations

from typing import Callable, Optional

from step4.context_builder import build_step4_context
from step4.step4_internal_service import Step4InternalService
from step4.step4_brief_service import Step4BriefService
from step4.scan.scan_service import ScanService


class Step4Service:
    def __init__(self, call_llm: Callable[[str, str], str]):
        self.call_llm = call_llm
        # v6: 新增基础扫描服务
        self.scan_service = ScanService(call_llm=call_llm)
        self.internal_service = Step4InternalService(call_llm=call_llm)
        self.brief_service = Step4BriefService(call_llm=call_llm)

    def run(
        self,
        *,
        step1_text: str,
        step3_json: str,
        bp_text: str,
        step3b_json: Optional[str | dict] = None,
    ):
        # 1. 基础扫描层（v6 新增：快速扫一遍7个维度）
        scan_questions = self.scan_service.run(
            step1_text=step1_text,
            bp_text=bp_text,
        )

        # 2. Context pack（供深挖层使用，新增 Step3B 整合）
        context_pack = build_step4_context(
            step1_text=step1_text,
            step3_json=step3_json,
            bp_text=bp_text,
            step3b_json=step3b_json,
        )

        # 3. 深挖层（v5：决策缺口 + 提问路径）
        internal_obj = self.internal_service.run(context_pack=context_pack)

        # 4. 会前提纲（整合扫描 + 深挖）
        meeting_brief_md = self.brief_service.run(
            internal_json=internal_obj.model_dump(),
            scan_questions=scan_questions,  # v6: 传入扫描问题
        )

        return {
            "context_pack": context_pack,
            "internal_json": internal_obj.model_dump(),
            # v6 新增
            "scan_questions": scan_questions,
            "meeting_brief_md": meeting_brief_md,
        }
