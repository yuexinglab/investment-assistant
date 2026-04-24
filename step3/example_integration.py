from __future__ import annotations

from step3.step3_service import Step3Service


def fake_llm(system_prompt: str, user_prompt: str) -> str:
    return '''
    {
      "selected_buckets": ["tech_barrier", "expansion_story", "team_credibility"],
      "bucket_outputs": [
        {
          "bucket_key": "tech_barrier",
          "bucket_label": "技术/壁垒是否成立",
          "point": "超分子改性在材料/制剂领域属于成熟工具箱，而非天然独占路线。",
          "explanation": "技术路径成立，但更像应用层工艺组合，不天然等于平台级壁垒。",
          "relation_to_step1": "support",
          "certainty": "high",
          "source_type": "common_sense"
        },
        {
          "bucket_key": "expansion_story",
          "bucket_label": "扩张/故事是否合理",
          "point": "从美妆扩到食品、医药、新能源通常会遇到完全不同的验证与法规体系。",
          "explanation": "跨行业扩张在新材料中经常被提前讲故事，但落地难度高。",
          "relation_to_step1": "support",
          "certainty": "high",
          "source_type": "common_sense"
        },
        {
          "bucket_key": "team_credibility",
          "bucket_label": "团队/背书是否被高估",
          "point": "诺奖/院士/博士背书常用于提升可信度，但不自动转化为商业护城河。",
          "explanation": "商业成功仍取决于工程化、客户验证和成本控制。",
          "relation_to_step1": "support",
          "certainty": "high",
          "source_type": "common_sense"
        }
      ],
      "publicly_resolvable": [
        {
          "bucket_key": "tech_barrier",
          "item": "专利路线与公开技术路径",
          "current_conclusion": "可以通过公开专利和论文初步判断技术是否通用。",
          "confidence": "high"
        }
      ],
      "still_unresolved": [
        {
          "bucket_key": "tech_barrier",
          "question": "AI 在研发中是否真的形成数据闭环与量化业务影响？",
          "why_unresolved": "核心数据和内部研发效率提升情况不会在公开材料中充分披露。",
          "impact_level": "high"
        }
      ],
      "step1_adjustment_hints": {
        "supported": [
          "公司更像材料应用/改性公司，而非底层 AI 材料平台。"
        ],
        "caution": [
          "不能仅因头部客户和学术背书就高估长期壁垒。"
        ],
        "to_step4": [
          "AI能力是否构成护城河"
        ]
      }
    }
    '''

if __name__ == "__main__":
    step1_text = '''
    本质上是一家利用超分子技术对现有化学原料进行物理改性的配方型公司，而不是一个具备底层材料发现能力的AI平台公司。
    我最不信的点包括：AI平台的真实含金量、跨行业扩张真实性、诺奖/博士背书是否构成商业壁垒。
    '''
    bp_text = "这是一个演示输入。"

    service = Step3Service(call_llm=fake_llm)
    result = service.run(
        step1_text=step1_text,
        bp_text=bp_text,
        industry="advanced_materials",
    )
    print(result.model_dump_json(indent=2, ensure_ascii=False))
