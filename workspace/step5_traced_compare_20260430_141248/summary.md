# Step5 Traced 版本回测总汇总
**时间**：2026-04-30 14:14:18
**总目录**：D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_traced_compare_20260430_141248
**成功**：2 / 2
**失败**：0

---
## 项目索引
| # | 项目 | 旧 Decision | Traced Decision | QS数 | scan引用数 ||---|------|------------|----------------|------|-----------|
| 1 | [A1_1_0测试2_20260429_151410](D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_traced_compare_20260430_141248\A1_1_0测试2_20260429_151410/compare_summary.md) | maybe | maybe | 6 | 3 |
| 2 | [A2_1_0测试1_20260429_213714](D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_traced_compare_20260430_141248\A2_1_0测试1_20260429_213714/compare_summary.md) | maybe | maybe | 6 | 5 |

---
## 关键观察
1. **source 字段有效性**：如果 traced 版本的 must_ask_questions 中 scan_question/merged 数量 > 0，说明 scan_questions 被成功引用。2. **investment_logic 格式**：检查 traced primary_type 是否正确使用'待验证：A vs B'格式。3. **decision 稳定性**：traced 版本应与 old/current 版本 decision 一致；不一致说明 prompt 修改影响了判断逻辑。4. **问题锋利度**：traced 版本问题应比旧版更聚焦、更像会前必问，而非泛泛而谈。
---
自动生成 by step5_traced_test.py
