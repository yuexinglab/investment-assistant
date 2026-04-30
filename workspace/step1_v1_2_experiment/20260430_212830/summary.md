# Step1 v1.2 实验汇总报告

实验时间: 2026-04-30 21:28
实验项目: A1（斯年智驾）、A2（自动轮底盘）、C1（电驱动系统）

---

## 实验背景

v1.1 只测试了7字段JSON输出格式，没有使用 project_structure_detector 和 general.py。
v1.2 真实调用结构识别 + 把 general.py 压缩成思考约束注入 prompt。

---

## 重点评估问题

---

### Q1: A1 v1.2 的 stance 是否还过度 positive？

| 版本 | stance |
|------|--------|
| v1.1 | meet |
| v1.2 | **cautious_watch** |

**人工评估：✅ v1.2 显著优于 v1.1**

- v1.1 stance = meet：过度相信先发优势和规模壁垒
- v1.2 stance = cautious_watch：更符合投资人的谨慎判断
- v1.2 的 red_flags 有7条（v1.1只有3条），且都是具体问题
- v1.2 narrative_business 区分了"代运营/增材制造/L2量产"等未验证业务

---

### Q2: C1 v1.2 是否能识别「系统集成商而非芯片公司」？

| 版本 | company_essence |
|------|----------------|
| v1.1 | 新能源汽车电驱动系统及核心功率器件（IGBT/SiC模块）的**垂直一体化供应商**，覆盖从芯片设计到系统集成的完整产业链 |
| v1.2 | **一家以新能源商用车电驱动系统为核心产品，向上游IGBT/SiC模块封装延伸的硬科技零部件供应商** |
| current | 本质是"系统集成商"，而非"芯片原厂" |

**人工评估：⚠️ v1.2 部分优于 v1.1，但仍有差距**

- v1.1：直接抄BP叙事，写成"垂直一体化供应商"，被带偏
- v1.2：写成"硬科技零部件供应商"，比v1.1准确，但没有current版本那么精准地指出"本质是系统集成商而非芯片原厂"
- v1.2 的 narrative_business 正确识别了"IGBT芯片设计"是叙事
- v1.2 的 key_judgement 指出"IGBT芯片设计环节实际依赖外部采购"

**结论：v1.2 比 v1.1 强，但不如 current 版本精准。** current 版本有"本质是系统集成商，而非芯片原厂"这种一针见血的判断，v1.2 没有达到这个水准。

---

### Q3: A2 v1.2 是否保持「技术验证/量产缺口」判断？

| 版本 | stance |
|------|--------|
| v1.1 | hold |
| v1.2 | hold |

**人工评估：✅ v1.2 保持了准确判断**

- 两个版本 stance 都是 hold（技术验证阶段）
- v1.2 的 red_flags 更详细（5条 vs 3条）
- v1.2 的 must_ask_questions 质量更高（5个具体问题）

---

### Q4: v1.2 是否真的利用了 project_structure_detector？

| 项目 | 系统识别行业 | structure_evidence |
|------|------------|-------------------|
| A1 | 自动驾驶、工业物流、商用车 | ✅ 完整包含 |
| A2 | 商用车、AI应用、新能源 | ✅ 完整包含 |
| C1 | 新能源、商用车、新材料 | ✅ 完整包含 |

**人工评估：✅ v1.2 真实利用了 project_structure_detector**

- 所有三个项目的 structure_evidence 都完整包含了 detector 的输出
- 关键不确定性部分直接引用了 detector 的 discriminating_questions
- A1 的 structure_evidence 包含了完整的"商业模式假设"和"风险信号"

---

### Q5: v1.2 是否比 v1.1 更不容易被 BP 叙事带偏？

| 项目 | v1.1 narrative_business | v1.2 narrative_business |
|------|-------------------------|------------------------|
| A1 | 无 | 代运营服务、增材制造、L2量产等（5条）|
| A2 | 无 | 乘用车配套、低速作业车辆（2条）|
| C1 | 无 | IGBT芯片设计、全产业链、储能等（3条）|

**人工评估：✅ v1.2 显著优于 v1.1**

- v1.1 三个项目的 narrative_business 都是"无"——完全没识别出叙事
- v1.2 全部三个项目都正确识别了叙事业务
- v1.2 的 red_flags 有具体的 evidence 和 reasoning

---

## 总体评估

### v1.2 优于 v1.1 的地方

1. **更准确的 stance**：从 meet/pass/hold 改为 positive_watch/cautious_watch/pass_for_now，避免过早给出"约/不约"结论
2. **真实利用结构识别**：project_structure_detector 的输出完整注入 prompt
3. **真实注入框架约束**：general.py 的8个思考维度被压缩成 prompt 约束
4. **正确识别叙事**：v1.1 完全没识别出 narrative_business，v1.2 全部识别
5. **更详细的 red_flags**：A1从3条增加到7条，且有 evidence
6. **structure_evidence 字段**：记录了 Step1 判断与系统识别的差异

### v1.2 比 v1.1 更差的地方

1. **C1 company_essence 仍有叙事残留**：v1.2 写成"硬科技零部件供应商"，不如 current 版本的"本质是系统集成商"精准
2. **部分字段被解析为字符串**：A1 的 company_essence 被解析成字符串而不是 dict，说明 prompt 格式仍需优化

### 是否建议进入阶段二

**建议条件性进入：**

- [x] **是，但需要先修复格式问题**：
  1. company_essence/business_structure 等字段被解析成字符串的问题
  2. C1 的 company_essence 需要更精准（学习 current 版本的表述方式）

- [ ] **否，原因**：如果格式问题无法稳定解决

### 下一步改进方向

1. **修复字段解析问题**：company_essence/business_structure 等被解析成字符串，需要优化 prompt 格式要求
2. **C1 精准度提升**：学习 current 版本"本质是X而非Y"的结构化表述
3. **实验扩大**：用更多项目验证 v1.2 的稳定性
4. **与 current 版本的混合**：考虑将 current 版本的判断框架（"本质是X而非Y"）整合进 v1.2

---

## 原始数据位置

```
workspace/step1_v1_2_experiment/20260430_212830/
├── A1/
│   ├── step1_current.txt
│   ├── step1_v1_1.json
│   ├── step1_v1_2.json
│   ├── project_structure.json
│   └── compare.md
├── A2/
├── C1/
├── compare_all.md
└── summary.md (本文件)
```
