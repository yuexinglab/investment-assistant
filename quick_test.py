# -*- coding: utf-8 -*-
"""快速测试 _normalize_change_type 修复"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.v2.services.step8_updater import _normalize_change_type

def test_normalize():
    print("Testing _normalize_change_type...")

    # 测试1: reinforced 被纠正为 weakened
    test1 = {
        "change_type": "reinforced",
        "updated_view": "AI平台当前是辅助工具而非核心护城河，准确率仅70-80%",
        "hypothesis": "AI平台可能比BP展示的更核心",
        "supporting_evidence": [],
        "contradicting_evidence": ["AI平台与传统方法对比的量化效率数据"]
    }
    result1 = _normalize_change_type(test1.copy())
    print(f"Test 1: {result1['change_type']} (expected: weakened)")
    assert result1["change_type"] == "weakened", f"Failed: {result1['change_type']}"

    # 测试2: 美妆被 overturned 纠正为 uncertain
    test2 = {
        "change_type": "overturned",
        "updated_view": "超分子技术在美妆领域尚未形成头部客户技术依赖，客户验证周期较长",
        "hypothesis": "超分子技术可能在美妆领域已被头部客户形成技术依赖",
        "supporting_evidence": ["ni_020"],
        "contradicting_evidence": ["头部客户技术依赖的具体案例"]
    }
    result2 = _normalize_change_type(test2.copy())
    print(f"Test 2: {result2['change_type']} (expected: uncertain)")
    assert result2["change_type"] == "uncertain", f"Failed: {result2['change_type']}"

    # 测试3: 千沐协同 overturned 纠正
    test3 = {
        "change_type": "overturned",
        "updated_view": "并购千沐新能源的技术协同效应未实际产生，整合进展缓慢",
        "hypothesis": "并购千沐新能源可能已产生技术协同效应",
        "supporting_evidence": [],
        "contradicting_evidence": ["千沐新能源的财务报表"]
    }
    result3 = _normalize_change_type(test3.copy())
    print(f"Test 3: {result3['change_type']} (expected: uncertain)")
    assert result3["change_type"] == "uncertain", f"Failed: {result3['change_type']}"

    print("\n=== All tests passed! ===")

if __name__ == "__main__":
    test_normalize()
