#!/usr/bin/env python3
"""测试实体匹配的严格性

统一的药品匹配测试脚本，包含所有已知的测试案例。
可以持续扩充新的测试案例。
"""

import sys
sys.path.insert(0, '.')

from app.inference.entity_matcher import EntityRecognizer

# 测试用例集合
# 每个测试用例包含：
# - drug: 查询的药品名
# - expected_should_match: 期望匹配到的药品（可选）
# - expected_should_not_match: 不应该匹配到的药品（可选）
# - note: 测试用例说明（可选）
TEST_CASES = [
    # 第一批：错误匹配案例（应该避免）
    {
        "drug": "艾塞那肽",
        "expected_should_not_match": "聚乙二醇洛塞那肽注射液",
        "note": "只匹配了部分字符，应该避免"
    },
    {
        "drug": "西罗莫司", 
        "expected_should_not_match": "司莫司汀胶囊",
        "note": "只匹配了部分字符，应该避免"
    },
    {
        "drug": "依那西普",
        "expected_should_not_match": "马来酸依那普利片",
        "note": "完全不同的药品"
    },
    {
        "drug": "环孢素",
        "expected_should_not_match": "四环素片",
        "note": "只匹配了部分字符，应该避免"
    },
    
    # 第二批：药物类别名（应该避免匹配具体药品）
    {
        "drug": "抗心律失常药",
        "expected_should_not_match": "心律宁片",
        "note": "药物类别名，不应该匹配具体药品"
    },
    {
        "drug": "抗代谢药",
        "expected_should_not_match": "代代花枳壳",
        "note": "药物类别名，完全不相关"
    },
    
    # 第三批：正确匹配案例（应该匹配）
    {
        "drug": "美托洛尔",
        "expected_should_match": "酒石酸美托洛尔片",
        "note": "应该正确匹配"
    },
    {
        "drug": "羟基脲",
        "expected_should_match": "羟基脲片",
        "note": "应该正确匹配"
    },
    {
        "drug": "多柔比星",
        "expected_should_match": "注射用盐酸多柔比星",
        "note": "应该正确匹配"
    },
]


def test_drug_matching():
    """测试药品匹配的严格性"""
    recognizer = EntityRecognizer()
    
    print("=" * 80)
    print("药品实体匹配严格性测试")
    print("=" * 80)
    print(f"共 {len(TEST_CASES)} 个测试案例\n")
    
    passed = 0
    failed = 0
    warnings = 0
    
    for i, case in enumerate(TEST_CASES, 1):
        drug = case["drug"]
        note = case.get("note", "")
        
        print(f"{i}. 测试药品: {drug}")
        if note:
            print(f"   说明: {note}")
        print("-" * 40)
        
        # 搜索药品
        results = recognizer._search_drug(drug, unique=False)
        
        # 判断测试结果
        case_passed = True
        has_warning = False
        
        if not results:
            # 没有找到匹配
            if "expected_should_not_match" in case:
                print(f"   ✅ 正确：未找到匹配（成功避免错误匹配）")
                passed += 1
            elif "expected_should_match" in case:
                print(f"   ❌ 错误：未找到期望的匹配 '{case['expected_should_match']}'")
                failed += 1
                case_passed = False
            else:
                print(f"   ⚠️  警告：未找到匹配（需检查是否合理）")
                warnings += 1
                has_warning = True
        else:
            # 找到了匹配
            print(f"   匹配结果数: {len(results)}")
            
            for j, result in enumerate(results[:3], 1):
                matched_name = result['name']
                score = result['_score']
                print(f"   {j}. {matched_name} (score: {score:.2f})")
                
                # 检查期望应该匹配的
                if "expected_should_match" in case:
                    expected = case["expected_should_match"]
                    if expected in matched_name or matched_name in expected:
                        print(f"      ✅ 正确：匹配到期望的药品")
                    else:
                        print(f"      ⚠️  警告：匹配到 '{matched_name}'，期望 '{expected}'")
                        has_warning = True
                
                # 检查不应该匹配的
                if "expected_should_not_match" in case:
                    unexpected = case["expected_should_not_match"]
                    if unexpected == matched_name:
                        print(f"      ❌ 错误：不应该匹配到 '{matched_name}'")
                        case_passed = False
                    else:
                        print(f"      ✅ 正确：未匹配到错误的药品 '{unexpected}'")
            
            if case_passed and not has_warning:
                passed += 1
            elif has_warning:
                warnings += 1
            else:
                failed += 1
        
        print()  # 空行分隔
    
    # 输出测试总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总计: {len(TEST_CASES)} 个测试案例")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"⚠️  警告: {warnings}")
    print(f"通过率: {passed/len(TEST_CASES)*100:.1f}%")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_drug_matching()
    sys.exit(0 if success else 1)
