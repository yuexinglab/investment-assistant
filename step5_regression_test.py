# -*- coding: utf-8 -*-
"""
Step5 Prompt 回测脚本

对已完成的 4 个 1.0 项目运行新 Step5 prompt，
与旧 step5_output.json 对比，生成 compare_summary.md。
"""

import json
import os
import sys
import io
import shutil
import traceback
from datetime import datetime

# Windows GBK 兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 路径设置 ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(BASE_DIR, "workspace")
MAIN_OUT_DIR = os.path.join(WORKSPACE, f"step5_regression_compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

# ── 目标项目 ────────────────────────────────────────────────────────────────
# 取最近的 4 个（含 scan_questions 的 v6 项目）
PROJECTS = [
    "C1_1_0测试1_20260430_080032",       # 今天
    "A2_1_0测试1_20260429_213714",       # 昨天晚
    "A1_1_0测试2_20260429_151410",       # 昨天下午
    "第一批测试A1_20260428_101520",       # 前天下午
]

# ── 必要文件清单 ─────────────────────────────────────────────────────────────
REQUIRED_FILES = [
    "step1/step1.txt",
    "step3/step3.json",
    "step3b/step3b.json",
    "step4/step4_internal.json",
    "step4/step4_scan_questions.json",
    "step5/step5_output.json",
]

def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_text(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Step5 单独运行（复制 pipeline_v1.py 的调用逻辑）─────────────────────────
def run_new_step5(*, step1_text, step3_json, step3b_json, step4_output, investment_modules=None):
    """使用修改后的 step5_prompt.py 重新运行 Step5"""
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
    )

    # 重试机制（与 pipeline 保持一致）
    for attempt in range(2):
        if attempt > 0:
            system_prompt += (
                " 上一次输出有问题（字段不完整或格式错误），"
                "这次必须严格按照 JSON 格式输出所有字段。"
            )
        raw = call_deepseek(system_prompt=system_prompt, user_prompt=prompt)
        try:
            obj = parse_step5_output(raw)
            return obj.model_dump()
        except Exception as e:
            last_error = e
            print(f"  [Step5 重试 {attempt+1}] 解析失败: {e}")
            continue

    raise RuntimeError(f"Step5 生成失败（已重试）: {last_error}")

# ── 对比分析 ────────────────────────────────────────────────────────────────
def compare_step5(old, new):
    """对比新旧 Step5 输出，返回对比结果 dict"""
    def get_qs(obj):
        qs = obj.get("must_ask_questions", [])
        return qs if isinstance(qs, list) else []

    def get_reason_list(obj, key):
        items = obj.get(key, [])
        return items if isinstance(items, list) else []

    old_qs = get_qs(old)
    new_qs = get_qs(new)

    old_decision = old.get("core_judgement", {}).get("decision", "N/A") if old.get("core_judgement") else "N/A"
    new_decision = new.get("core_judgement", {}).get("decision", "N/A") if new.get("core_judgement") else "N/A"

    old_core = old.get("core_judgement", {})
    new_core = new.get("core_judgement", {})

    old_ess = old_core.get("essence", "")
    new_ess = new_core.get("essence", "")

    return {
        "decision_changed": old_decision != new_decision,
        "old_decision": old_decision,
        "new_decision": new_decision,
        "old_qs_count": len(old_qs),
        "new_qs_count": len(new_qs),
        "old_essence": old_ess,
        "new_essence": new_ess,
        "essence_changed": old_ess != new_ess,
        "old_reasons_to_meet_count": len(get_reason_list(old, "reasons_to_meet")),
        "new_reasons_to_meet_count": len(get_reason_list(new, "reasons_to_meet")),
        "old_reasons_to_pass_count": len(get_reason_list(old, "reasons_to_pass")),
        "new_reasons_to_pass_count": len(get_reason_list(new, "reasons_to_pass")),
        "old_qs": old_qs,
        "new_qs": new_qs,
    }

def build_compare_md(proj_name, compare_result, old_full, new_full) -> str:
    """生成 compare_summary.md"""
    cr = compare_result

    # 辅助函数：格式化问题列表
    def format_qs(qs, label):
        if not qs:
            return f"**{label}**：无问题（⚠️ 不符合最少 3 个要求）"
        lines = [f"**{label}**（共 {len(qs)} 个）："]
        for i, q in enumerate(qs, 1):
            question = q.get("question", q.get("q", ""))
            purpose = q.get("purpose", q.get("验证目的", ""))
            lines.append(f"{i}. **{question}**")
            if purpose:
                lines.append(f"   - 验证目的：{purpose}")
        return "\n".join(lines)

    decision_icon = "🔄 变了" if cr["decision_changed"] else "✅ 不变"

    sections = [
        f"# Step5 Prompt 回测对比报告\n",
        f"**项目**：{proj_name}\n",
        f"---\n",
        f"## 1. Decision 变化\n",
        f"- 旧：`{cr['old_decision']}`\n",
        f"- 新：`{cr['new_decision']}`\n",
        f"- 状态：{decision_icon}\n",
        f"---\n",
        f"## 2. Core Judgement 清晰度\n",
        f"- 旧 essence：{cr['old_essence'] or '（空）'}\n",
        f"- 新 essence：{cr['new_essence'] or '（空）'}\n",
        f"- 变化：{'✅ 有变化' if cr['essence_changed'] else '⚪ 无变化'}\n",
        f"---\n",
        f"## 3. Must Ask Questions 数量\n",
        f"- 旧：{cr['old_qs_count']} 个\n",
        f"- 新：{cr['new_qs_count']} 个\n",
        f"- 要求：3-8 个\n",
        f"---\n",
        f"## 4. Must Ask Questions 内容对比\n",
        format_qs(cr["old_qs"], "旧版"),
        "\n",
        format_qs(cr["new_qs"], "新版"),
        "\n",
        f"---\n",
        f"## 5. Reasons to Meet / Pass 数量\n",
        f"- 旧 reasons_to_meet：{cr['old_reasons_to_meet_count']} 条\n",
        f"- 新 reasons_to_meet：{cr['new_reasons_to_meet_count']} 条\n",
        f"- 旧 reasons_to_pass：{cr['old_reasons_to_pass_count']} 条\n",
        f"- 新 reasons_to_pass：{cr['new_reasons_to_pass_count']} 条\n",
        f"---\n",
        f"## 6. 综合评估\n",
    ]

    # 自动评估
    issues = []
    positives = []

    if cr["new_qs_count"] < 3:
        issues.append("⚠️ 新 must_ask_questions 少于 3 个，不满足最低要求")
    elif cr["new_qs_count"] > 8:
        issues.append("⚠️ 新 must_ask_questions 超过 8 个上限")
    else:
        positives.append(f"✅ 数量符合要求（{cr['new_qs_count']} 个）")

    if cr["decision_changed"]:
        positives.append(f"🔄 decision 发生变化（{cr['old_decision']} → {cr['new_decision']}），需人工确认是否合理")

    # 检查新问题是否比旧问题更具体
    old_has_detailed = any(len(q.get("question", "")) > 20 for q in cr["new_qs"])
    if old_has_detailed:
        positives.append("✅ 新问题包含具体表述")

    sections.append("\n".join(positives) if positives else "")
    sections.append("\n".join(issues) if issues else "")

    sections.extend([
        f"\n---\n",
        f"**注**：新版 Step5 prompt 新增了对 `scan_questions` 的引用规则。",
        f"如果新版问题明显来自 scan_questions 的 opening/deepening/trap，说明修改生效。",
        f"如果问题与 scan_questions 无关但更聚焦，说明 LLM 自行提炼了 internal.gaps。",
        f"如果问题数量异常少，说明 prompt 约束生效（不再允许凭空发明）。",
    ])

    return "\n".join(sections)

# ── 主流程 ──────────────────────────────────────────────────────────────────
def main():
    print(f"Step5 Prompt 回测开始")
    print(f"总输出目录：{MAIN_OUT_DIR}\n")

    os.makedirs(MAIN_OUT_DIR, exist_ok=True)

    project_results = []
    failed_projects = []

    for proj_name in PROJECTS:
        proj_dir = os.path.join(WORKSPACE, proj_name)
        compare_dir = os.path.join(MAIN_OUT_DIR, proj_name)
        print(f"\n{'='*60}")
        print(f"▶ 项目：{proj_name}")
        print(f"  目录：{proj_dir}")

        # ── 1. 验证必要文件 ─────────────────────────────────────────
        missing = []
        for rf in REQUIRED_FILES:
            if not os.path.exists(os.path.join(proj_dir, rf)):
                missing.append(rf)
        if missing:
            print(f"  ⚠️ 缺少文件，跳过：{missing}")
            failed_projects.append((proj_name, f"缺少文件: {', '.join(missing)}"))
            continue

        os.makedirs(compare_dir, exist_ok=True)

        try:
            # ── 2. 加载旧数据 ──────────────────────────────────────────
            print("  加载数据...")
            step1_text = load_text(os.path.join(proj_dir, "step1/step1.txt"))
            step3_json = load_json(os.path.join(proj_dir, "step3/step3.json"))
            step3b_json = load_json(os.path.join(proj_dir, "step3b/step3b.json"))
            step4_internal = load_json(os.path.join(proj_dir, "step4/step4_internal.json"))
            step4_scan_qs = load_json(os.path.join(proj_dir, "step4/step4_scan_questions.json"))
            old_step5 = load_json(os.path.join(proj_dir, "step5/step5_output.json"))

            # ── 3. 保存旧版 Step5 ─────────────────────────────────────
            save_json(os.path.join(compare_dir, "old_step5.json"), old_step5)
            print("  ✓ 已保存 old_step5.json")

            # ── 4. 构建 step4_output ─────────────────────────────────
            step4_output = {
                "internal_json": step4_internal,
                "scan_questions": step4_scan_qs,
                # meeting_brief_md 非必需，Step5 不读它
            }

            # ── 5. 运行新版 Step5 ─────────────────────────────────────
            print("  运行新 Step5 prompt（可能需要 1-2 分钟）...")
            new_step5 = run_new_step5(
                step1_text=step1_text,
                step3_json=step3_json,
                step3b_json=step3b_json,
                step4_output=step4_output,
                investment_modules=None,
            )
            save_json(os.path.join(compare_dir, "new_step5.json"), new_step5)
            print("  ✓ 已保存 new_step5.json")

            # ── 6. 对比分析 ──────────────────────────────────────────
            print("  生成对比报告...")
            cr = compare_step5(old_step5, new_step5)
            compare_md = build_compare_md(proj_name, cr, old_step5, new_step5)
            save_text(os.path.join(compare_dir, "compare_summary.md"), compare_md)
            print("  ✓ 已保存 compare_summary.md")

            project_results.append({
                "name": proj_name,
                "compare_dir": compare_dir,
                "decision_old": cr["old_decision"],
                "decision_new": cr["new_decision"],
                "qs_old": cr["old_qs_count"],
                "qs_new": cr["new_qs_count"],
                "decision_changed": cr["decision_changed"],
                "essence_changed": cr["essence_changed"],
            })
            print(f"  ✅ 完成 | decision: {cr['old_decision']} → {cr['new_decision']} | qs: {cr['old_qs_count']} → {cr['new_qs_count']}")

        except Exception as e:
            tb = traceback.format_exc()
            print(f"  ❌ 失败：{e}")
            print(tb)
            failed_projects.append((proj_name, str(e)))
            # 保存错误日志
            save_text(os.path.join(compare_dir, "error.log"), f"{e}\n\n{tb}")

    # ── 7. 生成总汇总 ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("生成总汇总...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary_lines = [
        f"# Step5 Prompt 回测总汇总",
        "",
        f"**回测时间**：{timestamp}",
        f"**总对比目录**：{MAIN_OUT_DIR}",
        f"**项目总数**：{len(PROJECTS)}",
        f"**成功**：{len(project_results)}",
        f"**失败**：{len(failed_projects)}",
        "",
        "---\n",
        "## 项目索引\n",
        "| # | 项目名 | 旧 Decision | 新 Decision | 变化 | 旧 QS 数 | 新 QS 数 |",
        "|---|--------|------------|------------|------|---------|---------|",
    ]

    for i, r in enumerate(project_results, 1):
        changed_icon = "🔄" if r["decision_changed"] else "✅"
        summary_lines.append(
            f"| {i} | [{r['name']}]({r['compare_dir']}/compare_summary.md) "
            f"| {r['decision_old']} | {r['decision_new']} | {changed_icon} "
            f"| {r['qs_old']} | {r['qs_new']} |"
        )

    if failed_projects:
        summary_lines.extend(["", "## 失败项目\n"])
        for name, reason in failed_projects:
            summary_lines.append(f"- **{name}**：{reason}")

    summary_lines.extend([
        "",
        "---\n",
        "## 关键观察\n",
        "1. **decision 变化**：如果 decision 发生变化，说明 prompt 修改影响了 LLM 的最终判断逻辑，需人工确认合理性。",
        "2. **must_ask_questions 数量**：新 prompt 要求 3-8 个，如果数量明显变化说明约束生效。",
        "3. **scan_questions 引用**：检查新版问题是否比旧版更聚焦（来自 scan_questions 的 opening/deepening/trap）。",
        "4. **凭空发明**：如果新问题比旧问题更少但更精准，说明 prompt 约束有效减少了随意发挥。",
        "",
        f"---\n",
        f"本汇总由 `step5_regression_test.py` 自动生成\n",
    ])

    save_text(os.path.join(MAIN_OUT_DIR, "summary.md"), "\n".join(summary_lines))
    print(f"  ✓ 总汇总已保存：{MAIN_OUT_DIR}/summary.md")

    # ── 8. 输出总结 ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("回测完成")
    print(f"总对比目录：{MAIN_OUT_DIR}")
    print(f"\n项目结果：")
    for r in project_results:
        print(f"  ✅ {r['name']}")
        print(f"     compare_summary.md: {r['compare_dir']}/compare_summary.md")
    if failed_projects:
        print(f"\n失败项目：")
        for name, reason in failed_projects:
            print(f"  ❌ {name}: {reason}")

    return project_results, failed_projects

if __name__ == "__main__":
    results, failed = main()
