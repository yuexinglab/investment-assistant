# Step3 v2：插件式行业增强结构

本版本把 Step3 拆成：

- **通用层**：固定桶（bucket）骨架
- **行业插件层**：每个行业一个文件，单独维护增强规则
- **主流程层**：只负责调度、构造 prompt、解析输出

## 目录结构

```text
step3/
  __init__.py
  bucket_registry.py
  industry_loader.py
  step3_prompt.py
  step3_parser.py
  step3_schema.py
  step3_service.py
  example_integration.py
  industries/
    __init__.py
    advanced_materials.py
    commercial_space.py
```

## 核心原则

### 通用桶（固定）
- tech_barrier
- customer_value
- commercialization
- expansion_story
- team_credibility

### 行业增强（插件）
每个行业文件只定义该行业下各个桶的：
- checks
- red_flags
- public_info_candidates

## 如何新增行业

例如新增机器人行业：

1. 新建文件：`step3/industries/robotics.py`
2. 定义：
   - `INDUSTRY_NAME = "robotics"`
   - `ENHANCEMENTS = {...}`
3. 不需要改主流程代码

## 如何接入你现有项目

把 `Step3Service` 接到你的 `call_deepseek` 即可：

```python
from step3.step3_service import Step3Service
from services.deepseek_service import call_deepseek

service = Step3Service(call_llm=call_deepseek)

result = service.run(
    step1_text=step1_output,
    bp_text=bp_text,
    industry="advanced_materials"
)
```
