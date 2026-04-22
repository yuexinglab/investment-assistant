"""
report_generator.py — 报告生成主逻辑
1.0：A→B→C 串行调用
2.0：D→E→C 串行调用
"""

import json
from services.deepseek_service import call_deepseek
from prompts import role_a_analyzer, role_b_critic, role_c_integrator, role_d_meeting, role_e_questioneer


def generate_v1(bp_text: str, meta: dict) -> dict:
    """
    初判 1.0：三角色串行
    A（业务理解）→ B（风险挑刺）→ C（整合初判）
    返回：包含各角色输出和最终报告的字典
    """
    company_name = meta.get("company_name", "")
    print(f"[1.0] A角色分析中...")

    # A 角色
    a_output = call_deepseek(
        system_prompt=role_a_analyzer.SYSTEM_PROMPT,
        user_prompt=role_a_analyzer.build_user_prompt(bp_text, company_name)
    )

    print(f"[1.0] B角色挑刺中...")

    # B 角色
    b_output = call_deepseek(
        system_prompt=role_b_critic.SYSTEM_PROMPT,
        user_prompt=role_b_critic.build_user_prompt(bp_text, a_output)
    )

    print(f"[1.0] C角色整合中...")

    # C 角色
    c_output = call_deepseek(
        system_prompt=role_c_integrator.SYSTEM_PROMPT_V1,
        user_prompt=role_c_integrator.build_user_prompt_v1(a_output, b_output, company_name)
    )

    print(f"[1.0] 完成！")

    return {
        "version": "1.0",
        "company_name": company_name,
        "role_a": a_output,
        "role_b": b_output,
        "role_c": c_output,
        "final_report": c_output,   # 对外展示的主体
    }


def generate_v2(v1_report: dict, meeting_text: str) -> dict:
    """
    沟通更新 2.0：三角色串行
    D（会议分析）→ E（追问生成）→ C（整合更新）
    返回：包含各角色输出和最终更新报告的字典
    """
    company_name = v1_report.get("company_name", "")
    v1_final = v1_report.get("final_report", "")

    # 从 v1 报告里提取问题清单（模块5）用于 D 角色
    v1_questions = _extract_questions_from_report(v1_final)

    print(f"[2.0] D角色会议分析中...")

    # D 角色
    d_output = call_deepseek(
        system_prompt=role_d_meeting.SYSTEM_PROMPT,
        user_prompt=role_d_meeting.build_user_prompt(v1_questions, meeting_text)
    )

    print(f"[2.0] E角色追问生成中...")

    # E 角色
    e_output = call_deepseek(
        system_prompt=role_e_questioneer.SYSTEM_PROMPT,
        user_prompt=role_e_questioneer.build_user_prompt(d_output, v1_final)
    )

    print(f"[2.0] C角色整合更新中...")

    # C 角色（复用，但用 V2 版 Prompt）
    c_output = call_deepseek(
        system_prompt=role_c_integrator.SYSTEM_PROMPT_V2,
        user_prompt=role_c_integrator.build_user_prompt_v2(v1_final, d_output, e_output)
    )

    print(f"[2.0] 完成！")

    return {
        "version": "2.0",
        "company_name": company_name,
        "role_d": d_output,
        "role_e": e_output,
        "role_c": c_output,
        "final_report": c_output,
        "v1_report_ref": v1_final[:500] + "...",  # 备份引用
    }


def generate_v2_iteration(v2_report: dict, new_info: str) -> dict:
    """
    可选：有新信息时继续迭代更新（复用 D+E+C 结构）
    """
    return generate_v2(
        v1_report={
            "company_name": v2_report.get("company_name", ""),
            "final_report": v2_report.get("final_report", ""),
        },
        meeting_text=new_info
    )


def report_to_markdown(report: dict, meta: dict, version: str) -> str:
    """把报告字典转成 Markdown 文本用于导出"""
    company = meta.get("company_name", "未知公司")
    created = meta.get("created_at", "")[:10]

    lines = [
        f"# {company} — AI 项目判断报告 v{version}",
        f"生成时间：{created}",
        "",
        "---",
        "",
        report.get("final_report", "（报告内容为空）"),
        "",
        "---",
        "*本报告由 AI 项目判断工作台生成，供参考使用*",
    ]
    return "\n".join(lines)


def _extract_questions_from_report(report_text: str) -> str:
    """
    从 C 角色的报告中提取「模块5：第一轮问题清单」
    如果提取失败，返回完整报告（D 角色会自行处理）
    """
    if "模块5" in report_text:
        idx = report_text.find("模块5")
        # 截取到模块6
        end_idx = report_text.find("模块6", idx)
        if end_idx > 0:
            return report_text[idx:end_idx]
        return report_text[idx:]
    elif "第一轮问题清单" in report_text:
        idx = report_text.find("第一轮问题清单")
        return report_text[idx:idx + 3000]
    # 兜底：返回全文
    return report_text[:3000]
