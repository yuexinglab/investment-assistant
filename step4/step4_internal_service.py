from __future__ import annotations

from typing import Callable

from step4.step4_internal_prompt import build_step4_internal_prompt
from step4.step4_internal_parser import parse_step4_internal_output


def validate_internal_output(obj) -> bool:
    """
    v6.1 验证规则：检查新结构

    - 必须有 total_gaps >= 3
    - 每个 gap 必须有：main_path, backup_path, red_flag_question
    - 每个 path 必须有：opening, deepen_1, deepen_2, trap, signals
    """
    if not hasattr(obj, 'gaps') or not obj.gaps or len(obj.gaps) < 3:
        return False

    for gap in obj.gaps:
        # v6.1 新结构验证
        if not hasattr(gap, 'main_path') or not gap.main_path:
            return False
        if not hasattr(gap, 'backup_path') or not gap.backup_path:
            return False
        if not hasattr(gap, 'red_flag_question') or not gap.red_flag_question:
            return False

        # path 内部验证
        for path_name in ['main_path', 'backup_path']:
            path = getattr(gap, path_name)
            if not path.opening or not path.deepen_1 or not path.deepen_2:
                return False
            if not path.trap or not path.signals:
                return False

        # 旧字段验证（兼容）
        if not gap.go_if or not gap.no_go_if:
            return False

    return True


class Step4InternalService:
    def __init__(self, call_llm: Callable[[str, str], str], max_retries: int = 2):
        self.call_llm = call_llm
        self.max_retries = max_retries

    def run(self, *, context_pack: dict):
        last_error = None
        for attempt in range(self.max_retries):
            prompt = build_step4_internal_prompt(context_pack)

            # v6.1 system prompt：强调多路径结构
            system_prompt = (
                "你是一位资深投资人。"
                "你现在只负责生成内部决策骨架 + 提问路径，不负责写会议提纲。"
                "每个 gap 必须包含：main_path（主打）+ backup_path（备用）+ red_flag_question（红线）。"
                "每个 path 必须包含：opening, deepen_1, deepen_2, trap, signals。"
                "禁止输出 null。输出必须是合法 JSON。"
            )
            if attempt > 0:
                system_prompt += " 上一次输出字段不完整，这次必须补全所有字段，尤其是 main_path、backup_path、red_flag_question、deepen_2。"

            raw = self.call_llm(
                system_prompt=system_prompt,
                user_prompt=prompt,
            )
            try:
                obj = parse_step4_internal_output(raw)
                if validate_internal_output(obj):
                    return obj
                last_error = ValueError("internal output 字段不完整")
            except Exception as e:
                last_error = e

        raise RuntimeError(f"Step4 internal 生成失败: {last_error}")
