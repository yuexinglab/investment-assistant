"""
report_generator.py — 报告生成主逻辑

支持两种模式：
1. v1.0 旧模式：A→B→C 串行调用（保留）
2. v2.5 新模式：模板驱动9步流程（新增）

优先使用v2.5模板流程
"""

import json
from services.deepseek_service import call_deepseek
from services.template_flow import get_flow_executor
from prompts import role_a_analyzer, role_b_critic, role_c_integrator, role_d_meeting, role_e_questioneer


# ===== v2.5 模板驱动流程（推荐使用）=====

def generate_v1_template(bp_text: str, meta: dict, template_path: str = None) -> dict:
    """
    v2.5 初判：模板驱动9步流程

    Step1: 通用理解（升级版One-liner）
    Step2: 模板注入
    Step3: 字段抽取
    Step4: 缺口识别
    Step5: 问题生成
    Step6: 规则命中
    Step7: 评分计算
    Step8: 结构化报告
    Step9: 投资人判断层（核心质变点）

    :param bp_text: BP原文
    :param meta: 项目元数据
    :param template_path: 可选，模板路径
    :return: 包含所有步骤输出的字典
    """
    company_name = meta.get("company_name", "")
    industry = meta.get("industry", "advanced_materials")  # 默认新材料行业

    print(f"[v2.5] 使用模板流程分析 {company_name}...")

    executor = get_flow_executor(template_path)
    result = executor.run_full_flow(
        bp_text=bp_text,
        company_name=company_name,
        industry=industry
    )

    return result


# ===== v1.0 旧模式（保留兼容）=====

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
    沟通更新 2.0：尽调验证系统（新版v2）
    
    使用真正的执行链 pipeline：
    1. Extractor → 2. Delta Engine → 3. QA Judge(逐题) → 4. QA汇总 → 5. Risk Update → 6. Decision Updater → 7. Alpha Layer
    
    返回：包含结构化输出和最终报告的字典
    """
    from services.v2 import run_v2_pipeline, render_markdown
    
    company_name = v1_report.get("company_name", "")
    
    print(f"[2.0] 开始执行新架构pipeline...")
    print(f"[2.0] 输入报告版本: {v1_report.get('version', 'unknown')}")
    
    try:
        # 执行真正的pipeline
        result = run_v2_pipeline(v1_report, meeting_text)
        
        print(f"[2.0] Pipeline执行完成，生成报告...")
        
        # 渲染Markdown报告
        final_report = render_markdown(result, company_name)
        
        # 转换为可存储的dict
        result_dict = result.to_dict()
        
        return {
            "version": "2.0",
            "company_name": company_name,
            # 结构化输出（供UI消费）
            "v2_structured": result_dict,
            # UI展示用数据
            "one_liner_decision": result.decision.one_line_decision,
            "recommendation": result.decision.recommendation.value,
            "risk_signal": result.alpha.risk_signal.value,
            "meeting_score": result.alpha.meeting_quality_score,
            # 最终报告
            "final_report": final_report,
            "v1_report_ref": v1_report.get("final_report", "")[:500] + "...",
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] generate_v2 执行失败: {e}")
        print(error_detail)
        return {
            "version": "2.0",
            "company_name": company_name,
            "error": f"生成2.0报告时出错: {str(e)}",
            "error_detail": error_detail,
        }


def _extract_one_liner_decision(decision_text: str) -> str:
    """从 Decision Updater 输出中提取一句话决策"""
    if "【一句话决策】" in decision_text:
        start = decision_text.find("【一句话决策】") + len("【一句话决策】")
        end = decision_text.find("\n", start)
        if end > start:
            return decision_text[start:end].strip()
    return "（请参考完整判断更新）"


def _extract_one_liner_alpha(alpha_text: str) -> str:
    """从 Alpha Layer 输出中提取一句话洞察"""
    if "【一句话洞察】" in alpha_text:
        start = alpha_text.find("【一句话洞察】") + len("【一句话洞察】")
        end = alpha_text.find("\n", start)
        if end > start:
            return alpha_text[start:end].strip()
    # 尝试找 "这是一场" 模式
    if "这是一场" in alpha_text:
        idx = alpha_text.find("这是一场")
        return alpha_text[idx:idx+50].strip()
    return "（请参考完整直觉洞察）"


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
    
    # 根据版本选择报告内容
    if version == "v2.5":
        # v2.5: 优先使用 step9_judgment（投资人判断层）
        main_content = report.get("step9_judgment") or report.get("final_report") or report.get("step1_one_liner", "")
        
        # 补充其他有用信息
        lines = [
            f"# {company} — AI 项目判断报告 v2.5（模板驱动）",
            f"",
            f"**生成时间**：{created}",
            f"",
            f"## 核心判断",
            f"",
            main_content,
            f"",
            f"---",
            f"",
        ]
        
        # 如果有其他步骤输出，添加摘要
        all_steps = report.get("all_steps", {})
        if all_steps:
            lines.extend([
                f"## 分析摘要",
                f"",
                f"**Step1 业务理解**：{report.get('step1_one_liner', 'N/A')[:200]}...",
                f"",
            ])
            
            step5 = report.get("step5_questions", "")
            if step5 and len(step5) > 10:
                lines.extend([
                    f"**Step5 追问问题**：",
                    f"",
                    f"{step5[:1000]}...",
                    f"",
                ])
        
        lines.extend([
            f"---",
            f"",
            f"*本报告由 AI 项目判断工作台 v2.5 生成*",
        ])
    elif version == "2.0":
        # v2.0: 使用结构化数据和 Markdown 报告
        v2_structured = report.get("v2_structured", {})
        lines = [
            f"# {company} — AI 项目判断报告 v2.0（尽调更新）",
            f"",
            f"**生成时间**：{created}",
            f"**建议**：{report.get('recommendation', '继续跟进')}",
            f"",
            f"## 一句话决策",
            f"",
            report.get("one_liner_decision", "暂无决策"),
            f"",
            f"## 会议风险信号",
            f"",
            f"- 风险等级：{report.get('risk_signal', 'yellow')}",
            f"- 会议质量评分：{report.get('meeting_score', 'N/A')}/10",
            f"",
            f"## 完整报告",
            f"",
            report.get("final_report", "（报告内容为空）"),
            f"",
        ]
        
        # 如果有结构化数据，添加详细信息
        if v2_structured:
            # 新增信息摘要
            new_info = v2_structured.get("new_info", [])
            if new_info:
                lines.extend([
                    f"## 本次会议新增信息（共{len(new_info)}条）",
                    f"",
                ])
                for info in new_info[:10]:  # 最多显示10条
                    cat = info.get("category", "其他")
                    content = info.get("content", "")
                    lines.append(f"- 【{cat}】{content}")
                lines.append("")
            
            # 风险更新摘要
            risk_summary = v2_structured.get("risk_summary", {})
            if risk_summary:
                lines.extend([
                    f"## 风险状态更新",
                    f"",
                    risk_summary.get("summary", "暂无风险更新"),
                    f"",
                ])
            
            # 决策逻辑
            decision = v2_structured.get("decision", {})
            if decision:
                lines.extend([
                    f"## 决策逻辑",
                    f"",
                    f"- 前期立场：{decision.get('previous_stance', '未知')}",
                    f"- 当前立场：{decision.get('current_stance', '未知')}",
                    f"- 决策变化：{'是' if decision.get('changed') else '否'}",
                    f"",
                ])
                logic = decision.get("decision_logic", [])
                if logic:
                    lines.append("**决定理由：**")
                    for item in logic:
                        lines.append(f"- {item}")
                    lines.append("")
                why_not_now = decision.get("why_not_now", [])
                if why_not_now:
                    lines.append("**暂不推进原因：**")
                    for item in why_not_now:
                        lines.append(f"- {item}")
                    lines.append("")
            
            # Alpha 信号
            alpha = v2_structured.get("alpha", {})
            if alpha:
                lines.extend([
                    f"## 团队直觉信号",
                    f"",
                    f"- 团队画像：{alpha.get('team_profile_label', '无法判断')}",
                    f"- 风险信号：{alpha.get('risk_signal', 'yellow')}",
                    f"- 回避频率：{alpha.get('avoidance_frequency', 'medium')}",
                    f"- 一句话洞察：{alpha.get('one_line_insight', '暂无洞察')}",
                    f"",
                ])
        
        lines.extend([
            f"---",
            f"",
            f"*本报告由 AI 项目判断工作台 v2.0 生成*",
        ])
    else:
        # v1.0: 使用 final_report
        lines = [
            f"# {company} — AI 项目判断报告 v{version}",
            f"",
            f"**生成时间**：{created}",
            f"",
            f"---",
            f"",
            report.get("final_report", "（报告内容为空）"),
            f"",
            f"---",
            f"",
            f"*本报告由 AI 项目判断工作台生成，供参考使用*",
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
