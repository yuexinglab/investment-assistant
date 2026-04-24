# -*- coding: utf-8 -*-
"""
Step4 v6.1 - Brief Prompt

Display rules:
1. Basic scan layer: only show best_question (brief)
2. Deep dive layer: fully show main_path (including deepen_1, deepen_2, trap) and red_flag_question

Principle: Deep dive layer space must not be squeezed by scan layer
"""

import json
from typing import Dict, Any


PROMPT_TEMPLATE = """你负责把 internal_json 转换为「会前提纲」。

【风格要求】

- 像投资人自己写的会议小抄
- 不是报告，不要长段分析
- 可以有一点判断感，但不要攻击性

【重要：分层展示规则】

本次 v6.1 升级了展示逻辑：

## 基础扫描层（折叠/简短）

只展示每个维度的 **best_question**：
- 放在最前面，让投资人快速扫一眼
- opening 和 follow_up 不在主文展示（可忽略）
- 格式：维度名 + best_question

## 深挖层（完整展示）

每个深挖主题必须完整展示：
- 主路径 opening → deepen_1 → deepen_2 → trap
- 理想信号 / 危险信号
- 红线问题（重点标注）

【深挖层要保证完整展示，不能被 scan 层挤压空间】

【结构必须严格遵守】

# 本场会议目标

一句话判断：

# 优先搞清楚的3件事

1.
2.
3.

# 建议提问路径

（说明会议节奏：先 scan 快速扫一遍 → 再 deep dive 聚焦深挖）

---

# 基础扫描（快速扫一遍）

每个维度只展示 best_question：

## 收入与增长

## 客户结构

## 行业竞争

## 产能与供应

## 技术壁垒

## 商业模式

## 新业务进展

---

# 深挖：重点缺口（完整展开）

对于每个 gap，你需要展开以下结构：

## 主题名称（从 gap_id 和 core_issue 推断）

想搞清楚：[core_issue]

**主路径（最自然的提问节奏）**：

① 切入：[从 main_path.opening]
② 追问：[从 main_path.deepen_1]
③ 再追：[从 main_path.deepen_2]
④ 验证（trap）：[从 main_path.trap]

**理想信号**：
- [从 main_path.signals.good 列出]

**危险信号**：
- [从 main_path.signals.bad 列出]

**红线问题**（必须问的那一句）：[red_flag_question]

**备用路径**（如果对方回避，换角度）：
- 切入：[从 backup_path.opening]
- 追问：[从 backup_path.deepen_1]
- 再追：[从 backup_path.deepen_2]
- 验证：[从 backup_path.trap]

---

# 最终判断标准

结合 go_if / no_go_if 给出：

**投的逻辑**：[go_if]

**不投的逻辑**：[no_go_if]

【禁止】

- 不要输出 JSON
- 不要写分析报告
- 不要复述 internal 字段名
- scan 层不要展开 opening/follow_up，只显示 best_question
- 深挖层不要省略 deepen_2 和 red_flag_question

【输入】

internal_json:
{internal_json}

scan_questions:
{scan_questions}
"""


def build_step4_brief_prompt(
    internal_json: Dict[str, Any],
    scan_questions: Dict[str, Any] = None
) -> str:
    """
    Build Step4 Brief prompt

    Args:
        internal_json: internal layer output
        scan_questions: scan layer output (optional)

    Returns:
        Filled prompt
    """
    # Default empty
    if scan_questions is None:
        scan_questions = {}

    # Format input
    internal_text = json.dumps(internal_json, ensure_ascii=False, indent=2)
    scan_text = json.dumps(scan_questions, ensure_ascii=False, indent=2)

    return PROMPT_TEMPLATE.format(
        internal_json=internal_text,
        scan_questions=scan_text
    )
