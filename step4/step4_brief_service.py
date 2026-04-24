from __future__ import annotations

from typing import Callable, Optional

from step4.step4_brief_prompt import build_step4_brief_prompt


class Step4BriefService:
    def __init__(self, call_llm: Callable[[str, str], str]):
        self.call_llm = call_llm

    def run(
        self,
        *,
        internal_json: dict,
        scan_questions: Optional[dict] = None,  # v6 新增
    ) -> str:
        """生成会前提纲

        v5: context_pack 改为 Optional，不再强制传入
        v6: 新增 scan_questions 参数
        """
        prompt = build_step4_brief_prompt(
            internal_json=internal_json,
            scan_questions=scan_questions,
        )

        raw = self.call_llm(
            system_prompt=(
                "你是一位资深投资人兼尽调提问教练。"
                "你现在只负责把内部判断翻译成会议提纲。"
                "不要重新做内部分析。"
                "只输出 Markdown。"
                "v6.1 重要规则："
                "1. scan 层只显示 best_question，不展开 opening/follow_up"
                "2. deep dive 层必须完整展示 main_path（含 deepen_1, deepen_2, trap）和 red_flag_question"
                "3. 深挖层的空间不能被 scan 层挤压"
            ),
            user_prompt=prompt,
        )
        return raw.strip()
