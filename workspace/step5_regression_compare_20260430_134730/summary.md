# Step5 Prompt 回测总汇总

**回测时间**：2026-04-30 13:48:48
**总对比目录**：D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_regression_compare_20260430_134730
**项目总数**：4
**成功**：4
**失败**：0

---

## 项目索引

| # | 项目名 | 旧 Decision | 新 Decision | 变化 | 旧 QS 数 | 新 QS 数 |
|---|--------|------------|------------|------|---------|---------|
| 1 | [C1_1_0测试1_20260430_080032](D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_regression_compare_20260430_134730\C1_1_0测试1_20260430_080032/compare_summary.md) | maybe | maybe | ✅ | 3 | 5 |
| 2 | [A2_1_0测试1_20260429_213714](D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_regression_compare_20260430_134730\A2_1_0测试1_20260429_213714/compare_summary.md) | maybe | maybe | ✅ | 3 | 3 |
| 3 | [A1_1_0测试2_20260429_151410](D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_regression_compare_20260430_134730\A1_1_0测试2_20260429_151410/compare_summary.md) | maybe | maybe | ✅ | 3 | 5 |
| 4 | [第一批测试A1_20260428_101520](D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\workspace\step5_regression_compare_20260430_134730\第一批测试A1_20260428_101520/compare_summary.md) | N/A | maybe | 🔄 | 0 | 5 |

---

## 关键观察

1. **decision 变化**：如果 decision 发生变化，说明 prompt 修改影响了 LLM 的最终判断逻辑，需人工确认合理性。
2. **must_ask_questions 数量**：新 prompt 要求 3-8 个，如果数量明显变化说明约束生效。
3. **scan_questions 引用**：检查新版问题是否比旧版更聚焦（来自 scan_questions 的 opening/deepening/trap）。
4. **凭空发明**：如果新问题比旧问题更少但更精准，说明 prompt 约束有效减少了随意发挥。

---

本汇总由 `step5_regression_test.py` 自动生成
