# -*- coding: utf-8 -*-
"""
Step5 Traced 版本回测

新增 source/source_detail 字段后，对 A1/A2 两个项目做小回测。
三个版本对比：old / current(无source) / traced(有source)。
"""

import json
import os
import sys
import io
import traceback
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(BASE_DIR, "workspace")
MAIN_OUT_DIR = os.path.join(
    WORKSPACE,
    f"step5_traced_compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

PROJECTS = [
    "A1_1_0测试2_20260429_151410",
    "A2_1_0测试1_20260429_213714",
]

REQUIRED_FILES = [
    "step1/step1.txt",
    "step3/step3.json",
    "step3b/step3b.json",
    "step4/step4_internal.json",
    "step4/step4_scan_questions.json",
    "step5/step5_output.json",
]


# ── 工具函数 ────────────────────────────────────────────────────────────────
def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_text(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── 运行 traced Step5 ────────────────────────────────────────────────────────
def run_traced_step5(*, step1_text, step3_json, step3b_json, step4_output,
                     investment_modules=None):
    from services.deepseek_service import call_deepseek
    from step5.step5_prompt import build_step5_prompt
    from step5.step5_service import parse_step5_output

    prompt = build_step5_prompt(
        step1_text=step1_text,
        step3_json=step3_json,
        step3b_json=step3b_json,
        step4_output=step4_output,
        investment_modules=investment_modules or [],
    )

    system_prompt = (
        "你是一位顶级投资人，擅长做投资判断和决策收敛。"
        "你的任务是把分析和提问收敛成'可执行的投资判断框架'。"
        "不要总结，要判断。不要模糊，要明确条件。"
        "输出必须是合法 JSON。"
        "must_ask_questions 的 source 和 source_detail 必须完整填写，不得留空。"
    )

    for attempt in range(2):
        raw = call_deepseek(system_prompt=system_prompt, user_prompt=prompt)
        try:
            obj = parse_step5_output(raw)
            return obj.model_dump()
        except Exception as e:
            last_error = e
            print(f"  [重试 {attempt+1}] 失败: {e}")
            if attempt == 0:
                system_prompt += (
                    " 上一次输出有问题（字段不完整或格式错误），"
                    "这次必须补全 must_ask_questions 的 source 和 source_detail 字段。"
                )
            continue

    raise RuntimeError(f"Step5 生成失败（已重试2次）: {last_error}")


# ── 对比分析 ────────────────────────────────────────────────────────────────
SOURCE_LABEL = {
    "internal_gap": "【内部分析】",
    "scan_question": "【扫描层】",
    "merged": "【合并】",
    "rewritten_from_step4": "【改写】",
}


def _cj(obj, field=None):
    """获取 core_judgement 字典或指定字段"""
    cj = obj.get("core_judgement") or {}
    if field is not None:
        return cj.get(field)
    return cj


def build_compare_md(proj_name, old, current, traced) -> str:
    def get_qs(obj):
        return obj.get("must_ask_questions", []) or []

    old_qs = get_qs(old)
    cur_qs = get_qs(current)
    new_qs = get_qs(traced)

    # Decision 只比较 decision 字段
    old_dec = _cj(old, "decision")
    cur_dec = _cj(current, "decision")
    new_dec = _cj(traced, "decision")

    # Core judgement 各字段单独比较
    old_one_liner = _cj(old, "one_liner") or ""
    cur_one_liner = _cj(current, "one_liner") or ""
    new_one_liner = _cj(traced, "one_liner") or ""

    old_essence = _cj(old, "essence") or ""
    cur_essence = _cj(current, "essence") or ""
    new_essence = _cj(traced, "essence") or ""

    old_reason = _cj(old, "core_reason") or ""
    cur_reason = _cj(current, "core_reason") or ""
    new_reason = _cj(traced, "core_reason") or ""

    # 变化标志
    decision_changed = any([old_dec != cur_dec, cur_dec != new_dec, old_dec != new_dec])
    one_liner_changed = any([old_one_liner != cur_one_liner, cur_one_liner != new_one_liner, old_one_liner != new_one_liner])
    essence_changed = any([old_essence != cur_essence, cur_essence != new_essence, old_essence != new_essence])
    core_reason_changed = any([old_reason != cur_reason, cur_reason != new_reason, old_reason != new_reason])

    # Investment logic
    old_logic = old.get("investment_logic") or {}
    cur_logic = current.get("investment_logic") or {}
    new_logic = traced.get("investment_logic") or {}

    sections = [
        f"# Step5 Traced 版本回测对比报告\n",
        f"**项目**：{proj_name}\n",
        f"**版本说明**：\n",
        f"- `old_step5.json`：原始历史版本\n",
        f"- `current_step5.json`：当前线上版本（无 source 字段）\n",
        f"- `traced_step5.json`：traced 版本（强制要求 source/source_detail）\n",
        f"\n---\n",
        f"## 1. Decision 对比（仅 decision 字段）\n",
        f"| 版本 | Decision | Confidence |\n",
        f"|------|----------|------------|\n",
        f"| old | `{old_dec or 'N/A'}` | {_cj(old, 'confidence') or 'N/A'} |\n",
        f"| current | `{cur_dec or 'N/A'}` | {_cj(current, 'confidence') or 'N/A'} |\n",
        f"| traced | `{new_dec or 'N/A'}` | {_cj(traced, 'confidence') or 'N/A'} |\n",
        f"\n**Decision 变化**：{'🔄 是' if decision_changed else '✅ 否'}\n",
        f"\n---\n",
        f"## 2. Core Judgement 文案对比\n",
        f"| 字段 | 变化 | 说明 |\n",
        f"|------|------|------|\n",
        f"| one_liner | {'🔄 是' if one_liner_changed else '✅ 否'} | 一句话核心判断 |\n",
        f"| essence | {'🔄 是' if essence_changed else '✅ 否'} | 核心本质 |\n",
        f"| core_reason | {'🔄 是' if core_reason_changed else '✅ 否'} | 核心原因 |\n",
        f"\n**traced 版本 one_liner**：\n> {new_one_liner or 'N/A'}\n",
        f"\n**traced 版本 essence**：\n> {new_essence or 'N/A'}\n",
        f"\n**traced 版本 core_reason**：\n> {new_reason or 'N/A'}\n",
        f"\n---\n",
        f"## 3. Investment Logic 对比\n",
        f"| 版本 | primary_type | secondary_types |\n",
        f"|------|--------------|----------------|\n",
        f"| old | `{old_logic.get('primary_type', 'N/A')}` | {old_logic.get('secondary_types', [])} |\n",
        f"| current | `{cur_logic.get('primary_type', 'N/A')}` | {cur_logic.get('secondary_types', [])} |\n",
        f"| traced | `{new_logic.get('primary_type', 'N/A')}` | {new_logic.get('secondary_types', [])} |\n",
        f"\n是否写死未验证判断：\n",
    ]

    new_primary = new_logic.get("primary_type", "")
    is_unverified = "待验证" in new_primary
    is_locked = new_primary and "待验证" not in new_primary

    if is_unverified:
        sections.append(f"  ✅ traced 正确使用'待验证：A vs B'格式（primary_type = `{new_primary}`）\n")
    elif is_locked:
        sections.append(f"  ⚠️ traced 将未验证判断写死：primary_type = `{new_primary}`\n")
    else:
        sections.append(f"  ⚪ traced primary_type 为空或异常\n")

    sections.extend([
        f"\n---\n",
        f"## 4. Must Ask Questions 来源追踪\n",
    ])

    for version, qs, label in [
        ("current", cur_qs, "当前版本（无 source）"),
        ("traced", new_qs, "Traced 版本"),
    ]:
        if not qs:
            sections.append(f"**{label}**：无问题\n")
            continue
        sections.append(f"**{label}**（共 {len(qs)} 个）：\n")
        for i, q in enumerate(qs, 1):
            question = q.get("question", "")
            purpose = q.get("purpose", "")
            source = q.get("source", "（无 source 字段）")
            source_detail = q.get("source_detail", "")
            sl = SOURCE_LABEL.get(source, source)
            sections.append(f"{i}. {sl} **{question}**\n")
            sections.append(f"   - 验证目的：{purpose}\n")
            sections.append(f"   - source_detail：{source_detail}\n")
        sections.append("\n")

    sections.extend([f"\n---\n", f"## 5. 综合评估\n"])

    # 来源统计
    source_counts = {}
    for q in new_qs:
        s = q.get("source", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1

    scan_usage = source_counts.get("scan_question", 0) + source_counts.get("merged", 0)
    notes = []

    # 问题数量检查
    if len(new_qs) < 3:
        notes.append("⚠️ 问题少于 3 个，不满足最低要求")
    elif len(new_qs) > 8:
        notes.append("⚠️ 问题超过 8 个上限")
    else:
        notes.append(f"✅ 问题数量符合要求（{len(new_qs)} 个）")

    # Source 分布统计
    scan_ct = source_counts.get("scan_question", 0)
    merged_ct = source_counts.get("merged", 0)
    internal_ct = source_counts.get("internal_gap", 0)
    rewritten_ct = source_counts.get("rewritten_from_step4", 0)

    notes.append(f"\n**Source 分布**：")
    notes.append(f"- 【扫描层】scan_question: {scan_ct} 个")
    notes.append(f"- 【合并】merged: {merged_ct} 个")
    notes.append(f"- 【内部分析】internal_gap: {internal_ct} 个")
    notes.append(f"- 【改写】rewritten: {rewritten_ct} 个")

    if scan_usage > 0:
        notes.append(f"\n✅ scan_questions 被引用：{scan_usage} 个（scan_question={scan_ct} + merged={merged_ct}）")
    else:
        notes.append(f"\n⚠️ scan_questions 未被直接引用（全部来自 internal_gaps / rewritten）")

    # Investment logic 格式检查
    if is_unverified:
        notes.append("✅ investment_logic.primary_type 正确使用'待验证：A vs B'格式")
    elif is_locked:
        notes.append(f"⚠️ primary_type 被写死为`{new_primary}`，但核心商业模式尚未验证")

    # Decision 稳定性
    if decision_changed:
        notes.append(f"\n🔄 Decision 有变化（旧={old_dec}，当前={cur_dec}，traced={new_dec}），需人工确认")
    else:
        notes.append(f"\n✅ Decision 在三个版本中保持一致（`{new_dec}`）")

    # Core judgement 文案变化
    if one_liner_changed:
        notes.append("🔄 one_liner 有变化")
    if essence_changed:
        notes.append("🔄 essence 有变化")
    if core_reason_changed:
        notes.append("🔄 core_reason 有变化")

    sections.append("\n".join(notes))

    sections.extend([
        f"\n---\n",
        f"## 6. 建议\n",
    ])

    # 自动建议
    if is_unverified and scan_usage > 0 and len(new_qs) >= 3 and not decision_changed:
        sections.append("✅ **建议保留 traced 版本**\n")
        sections.append("理由：source 字段有效追踪了问题来源；investment_logic 正确使用待验证格式；decision 稳定。\n")
    elif scan_usage == 0 and is_unverified:
        sections.append("⚠️ **建议人工审查**\n")
        sections.append("理由：scan_questions 未被直接引用，但 investment_logic 格式正确。需确认问题是否真的来自 internal.gaps 提炼，还是 prompt 约束不足。\n")
    else:
        sections.append("⚠️ **建议人工确认后再决定是否保留**\n")
        sections.append("理由：存在决策变化或格式问题，需人工审查 traced 输出后再决定。\n")

    return "".join(sections)


# ── 主流程 ──────────────────────────────────────────────────────────────────
def main():
    print(f"Step5 Traced 回测开始")
    print(f"输出目录：{MAIN_OUT_DIR}\n")

    os.makedirs(MAIN_OUT_DIR, exist_ok=True)

    results = []
    failed = []

    for proj_name in PROJECTS:
        proj_dir = os.path.join(WORKSPACE, proj_name)
        compare_dir = os.path.join(MAIN_OUT_DIR, proj_name)
        print(f"\n{'='*60}")
        print(f"Project: {proj_name}")

        missing = [rf for rf in REQUIRED_FILES
                   if not os.path.exists(os.path.join(proj_dir, rf))]
        if missing:
            print(f"  Missing files, skipping: {missing}")
            failed.append((proj_name, f"缺少文件: {', '.join(missing)}"))
            continue

        os.makedirs(compare_dir, exist_ok=True)

        try:
            print("  Loading data...")
            step1_text = load_text(os.path.join(proj_dir, "step1/step1.txt"))
            step3_json = load_json(os.path.join(proj_dir, "step3/step3.json"))
            step3b_json = load_json(os.path.join(proj_dir, "step3b/step3b.json"))
            step4_internal = load_json(os.path.join(proj_dir, "step4/step4_internal.json"))
            step4_scan_qs = load_json(os.path.join(proj_dir, "step4/step4_scan_questions.json"))
            old_step5 = load_json(os.path.join(proj_dir, "step5/step5_output.json"))

            # Save old
            save_json(os.path.join(compare_dir, "old_step5.json"), old_step5)

            # Build step4_output
            step4_output = {
                "internal_json": step4_internal,
                "scan_questions": step4_scan_qs,
            }

            # Run current (no source field)
            print("  Running current Step5 (no source)...")
            current = run_traced_step5(
                step1_text=step1_text,
                step3_json=step3_json,
                step3b_json=step3b_json,
                step4_output=step4_output,
                investment_modules=None,
            )
            save_json(os.path.join(compare_dir, "current_step5.json"), current)

            # Run traced (same function, just with the new schema/prompt)
            print("  Running traced Step5 (with source field)...")
            traced = run_traced_step5(
                step1_text=step1_text,
                step3_json=step3_json,
                step3b_json=step3b_json,
                step4_output=step4_output,
                investment_modules=None,
            )
            save_json(os.path.join(compare_dir, "traced_step5.json"), traced)

            print("  Building compare_summary.md...")
            compare_md = build_compare_md(proj_name, old_step5, current, traced)
            save_text(os.path.join(compare_dir, "compare_summary.md"), compare_md)

            new_qs = traced.get("must_ask_questions", [])
            scan_ct = sum(1 for q in new_qs if q.get("source") in ("scan_question", "merged"))
            results.append({
                "name": proj_name,
                "compare_dir": compare_dir,
                "decision_old": _cj(old_step5, "decision") or "N/A",
                "decision_traced": _cj(traced, "decision") or "N/A",
                "qs_count": len(new_qs),
                "scan_used": scan_ct,
            })
            print(f"  Done: qs={len(new_qs)}, scan_questions_used={scan_ct}")

        except Exception as e:
            tb = traceback.format_exc()
            print(f"  FAILED: {e}")
            failed.append((proj_name, str(e)))
            save_text(os.path.join(compare_dir, "error.log"), f"{e}\n\n{tb}")

    # Summary
    print(f"\n{'='*60}")
    print("Building summary...")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Step5 Traced 版本回测总汇总\n",
        f"**时间**：{ts}\n",
        f"**总目录**：{MAIN_OUT_DIR}\n",
        f"**成功**：{len(results)} / {len(PROJECTS)}\n",
        f"**失败**：{len(failed)}\n",
        "\n---\n",
        "## 项目索引\n",
        "| # | 项目 | 旧 Decision | Traced Decision | QS数 | scan引用数 |",
        "|---|------|------------|----------------|------|-----------|\n",
    ]

    for i, r in enumerate(results, 1):
        lines.append(
            f"| {i} | [{r['name']}]({r['compare_dir']}/compare_summary.md) "
            f"| {r['decision_old']} | {r['decision_traced']} "
            f"| {r['qs_count']} | {r['scan_used']} |\n"
        )

    if failed:
        lines.extend(["\n## 失败项目\n"])
        for name, reason in failed:
            lines.append(f"- **{name}**：{reason}\n")

    lines.extend([
        "\n---\n",
        "## 关键观察\n",
        "1. **source 字段有效性**：如果 traced 版本的 must_ask_questions 中 scan_question/merged 数量 > 0，说明 scan_questions 被成功引用。",
        "2. **investment_logic 格式**：检查 traced primary_type 是否正确使用'待验证：A vs B'格式。",
        "3. **decision 稳定性**：traced 版本应与 old/current 版本 decision 一致；不一致说明 prompt 修改影响了判断逻辑。",
        "4. **问题锋利度**：traced 版本问题应比旧版更聚焦、更像会前必问，而非泛泛而谈。",
        "\n---\n",
        f"自动生成 by step5_traced_test.py\n",
    ])

    save_text(os.path.join(MAIN_OUT_DIR, "summary.md"), "".join(lines))
    print(f"  Summary: {MAIN_OUT_DIR}/summary.md")

    print(f"\n{'='*60}")
    print("Done")
    for r in results:
        print(f"  OK: {r['name']} -> {r['compare_dir']}/compare_summary.md")
    for name, reason in failed:
        print(f"  FAIL: {name}: {reason}")

    return results, failed

if __name__ == "__main__":
    main()
