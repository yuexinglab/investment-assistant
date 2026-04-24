from __future__ import annotations

import json

from step4.step4_service import Step4Service


def fake_llm(system_prompt: str, user_prompt: str) -> str:
    if "内部决策骨架" in system_prompt or "内部决策骨架" in user_prompt:
        return '''
        {
          "total_gaps": 3,
          "meeting_strategy": "先锁底盘与客户，再切AI和第二曲线。",
          "decision_gaps": [
            {
              "gap_id": "G1",
              "priority": "P1",
              "core_issue": "AI平台到底是真提效还是包装",
              "from_bucket": "tech_barrier",
              "why_it_matters": "这会直接影响公司估值口径和平台叙事是否成立。",
              "decision_impact": {
                "positive": "如果AI有量化提效和连续案例，可上调技术壁垒判断。",
                "negative": "如果AI只是工具，则估值应回到材料应用公司。"
              },
              "internal_goal": "确认AI是否真实改变了研发效率和成功率。",
              "go_if": "能给出至少1个具体案例和量化改善数据。",
              "no_go_if": "没有具体案例，只停留在概念描述。",
              "candidate_questions": [
                {
                  "question": "这套AI现在主要用在哪些研发环节？",
                  "intent": "先定位使用场景",
                  "question_type": "fact"
                },
                {
                  "question": "如果没有这套AI，几个代表性产品的研发路径会有什么不同？",
                  "intent": "看AI的边际贡献",
                  "question_type": "counterfactual"
                }
              ]
            },
            {
              "gap_id": "G2",
              "priority": "P1",
              "core_issue": "客户是长期依赖还是短期尝鲜",
              "from_bucket": "customer_value",
              "why_it_matters": "这会影响客户粘性、定价权和收入稳定性。",
              "decision_impact": {
                "positive": "如果客户持续复购并形成替代，客户依赖成立。",
                "negative": "如果只是试用和营销卖点，增长不可持续。"
              },
              "internal_goal": "确认客户付费动机是否稳定。",
              "go_if": "有持续采购、联合开发或替代发生。",
              "no_go_if": "项目制采购、缺乏复购证据。",
              "candidate_questions": [
                {
                  "question": "这些核心客户通常怎么开始合作？",
                  "intent": "判断主动性和需求强度",
                  "question_type": "fact"
                },
                {
                  "question": "如果不用你们方案，客户通常会用什么替代？",
                  "intent": "判断替代关系",
                  "question_type": "counterfactual"
                }
              ]
            },
            {
              "gap_id": "G3",
              "priority": "P2",
              "core_issue": "食品和新能源这些第二曲线是真收入还是故事",
              "from_bucket": "commercialization",
              "why_it_matters": "这决定跨行业扩张的可信度和近端增长空间。",
              "decision_impact": {
                "positive": "如果已有绝对收入和复购，第二曲线初步成立。",
                "negative": "如果只有小基数高增长和论文合作，仍是故事。"
              },
              "internal_goal": "确认第二曲线是否已经开始贡献实质收入。",
              "go_if": "能说出绝对金额、复购客户和推进时间表。",
              "no_go_if": "只说增长率，不说基数和客户。",
              "candidate_questions": [
                {
                  "question": "食品业务增长很快，这个增长是基于多大体量？",
                  "intent": "验证绝对规模",
                  "question_type": "fact"
                },
                {
                  "question": "未来1-2年最可能先跑出来的是哪个方向？",
                  "intent": "判断战略优先级",
                  "question_type": "path"
                }
              ]
            }
          ],
          "summary": "重点判断AI、客户依赖和第二曲线的真实性。"
        }
        '''
    return '''
# 📌 本场会议目标

**一句话：** 先把美妆底盘和客户依赖问实，再判断 AI 和第二曲线到底是能力还是包装。

---

# 🎯 优先搞清楚的3件事（按重要性排序）

1️⃣ AI 到底是真提效，还是包装  
2️⃣ 客户到底是长期依赖，还是短期尝鲜  
3️⃣ 食品/新能源这些第二曲线，是真收入还是故事  

---

# 🧭 建议提问路径（会议节奏）

**第一段：先锁底盘和客户**
先从当前业务和客户合作方式切入，降低防御，同时验证基本盘。

**第二段：再问 AI**
顺着代表性产品开发过程，把 AI 的真实作用问出来。

**第三段：最后问第二曲线**
再去看食品、新能源这些方向，到底有没有实质收入和落地节奏。

---

# 🧩 主题1：客户依赖

🎯 **想搞清楚：**
→ 客户是因为真实效果持续采购，还是短期尝鲜。

🧠 **主问题：**
👉 这些核心客户通常是怎么开始合作的？是主动找上门，还是你们去推动的？

👂 **理想信号：**
- 客户主动
- 从测试走向持续采购
- 有替代原供应商的情况

⚠️ **危险信号：**
- 强销售推动
- 只试用不复购
- 项目制采购

🔁 **如果对方回答偏正面：**
👉 那这些客户后来是怎么从小批量测试走到持续采购的？有没有客户直接替换掉原来的供应商？

🔁 **如果对方回答模糊：**
👉 有没有客户试过之后，没有继续合作？一般是什么原因？

---

# 🧩 主题2：AI 平台

🎯 **想搞清楚：**
→ AI 是否真实参与研发流程并带来量化价值。

🧠 **主问题：**
👉 你们这套 AI 现在最常用在哪些研发环节？如果拿超分子 VC 这种代表产品来说，它具体帮到了哪一步？

👂 **理想信号：**
- 实际参与筛选或优化
- 有周期缩短或实验减少
- 有内部跟踪指标

⚠️ **危险信号：**
- 主要用于记录
- 回避量化
- 仍停留在建设阶段

🔁 **如果对方回答偏正面：**
👉 那相比传统做法，它大概帮你们减少了多少实验次数，或者缩短了多少研发周期？

🔁 **如果对方回答模糊：**
👉 那目前看，这套系统更像辅助工具，对吗？公司内部有没有追踪过它的命中率或提效情况？

---

# 🧩 主题3：第二曲线

🎯 **想搞清楚：**
→ 食品和新能源这些方向，是不是已经开始形成真实收入。

🧠 **主问题：**
👉 食品业务增长挺快，这个增长大概是基于多大的体量？目前更偏研发合作，还是已经进入持续出货？

👂 **理想信号：**
- 能说绝对金额
- 有复购客户
- 有清晰推进时间表

⚠️ **危险信号：**
- 只说增长率
- 仍是样品或测试
- 没有明确客户和时间节点

🔁 **如果对方回答偏正面：**
👉 这些订单主要来自哪些类型客户？他们采购之后，是做研发测试还是已经开始销售？

🔁 **如果对方回答模糊：**
👉 那目前这块业务更偏验证阶段，对吗？未来1-2年你们觉得最可能先跑出来的是哪个方向？

---

# 📊 最终判断标准（会后用）

**如果满足：**
✔ AI 有具体案例和量化提效  
✔ 客户有持续采购或替代发生  
✔ 第二曲线有绝对收入和复购客户  

→ **可以继续推进**

**否则：**
→ **按高端配方公司看待，降低对平台叙事和第二曲线的预期**
    '''


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    service = Step4Service(call_llm=fake_llm)
    demo_step3 = json.dumps({
        "selected_buckets": ["tech_barrier", "customer_value", "commercialization"],
        "still_unresolved": [
            {"bucket_key": "tech_barrier", "question": "AI 是否真的提效", "why_unresolved": "无量化数据", "impact_level": "high"},
            {"bucket_key": "customer_value", "question": "客户是否长期依赖", "why_unresolved": "无合同细节", "impact_level": "high"},
            {"bucket_key": "commercialization", "question": "食品收入是否真实", "why_unresolved": "只有增长率", "impact_level": "high"}
        ],
        "tensions": [
            "美妆底盘成立 vs 平台故事可能过度包装",
            "客户有头部背书 vs 客户粘性未证实"
        ],
        "step1_adjustment_hints": {
            "supported": ["本质更像材料应用公司"],
            "caution": ["AI壁垒可能被高估"],
            "to_step4": ["AI真实效用", "客户依赖", "食品业务"]
        },
        "bucket_outputs": []
    }, ensure_ascii=False)

    result = service.run(
        step1_text="我判断这家公司本质更像配方型材料公司，而不是底层AI平台公司；最关键要看AI效用、客户依赖和第二曲线真实性。",
        step3_json=demo_step3,
        bp_text="公司服务欧莱雅、华熙生物等客户，强调AI平台建沐、食品业务增长、新能源布局、千吨级产能和多项专利。"
    )

    print("=== context_pack ===")
    print(json.dumps(result["context_pack"], ensure_ascii=False, indent=2))
    print("\n=== internal_json ===")
    print(json.dumps(result["internal_json"], ensure_ascii=False, indent=2))
    print("\n=== meeting_brief_md ===")
    print(result["meeting_brief_md"])
