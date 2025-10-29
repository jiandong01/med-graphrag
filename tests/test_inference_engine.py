"""推理引擎端到端测试"""

import os
import json
import pytest
from app.inference.engine import InferenceEngine
from app.shared import Config

load_env = Config.load_env
load_env()

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'input')


def load_test_input(filename):
    """加载测试输入数据"""
    filepath = os.path.join(TEST_DATA_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope="module")
def inference_engine():
    """创建 InferenceEngine 实例"""
    return InferenceEngine()


def test_analyze_standard_case(inference_engine, capsys):
    """测试标准用药案例分析"""
    input_data = load_test_input("entity_recognition_input_1.json")
    
    print("\n标准用药案例分析:")
    print(f"输入: {input_data['description']}")
    
    result = inference_engine.analyze(input_data)
    
    print(f"\n分析结果:")
    print(f"是否超适应症: {result.get('is_offlabel', 'N/A')}")
    print(f"置信度: {result.get('confidence', 'N/A')}")
    print(f"建议: {result.get('recommendation', {}).get('decision', 'N/A')}")
    
    # 验证结果结构
    assert 'is_offlabel' in result
    assert 'confidence' in result
    assert 'analysis' in result
    assert 'recommendation' in result
    
    captured = capsys.readouterr()
    print(captured.out)


def test_analyze_with_custom_input(inference_engine, capsys):
    """测试自定义输入数据"""
    custom_input = {
        "description": "患者65岁，诊断为慢性心力衰竭，拟使用美托洛尔缓释片治疗",
        "patient_info": {
            "age": 65,
            "gender": "男",
            "symptoms": ["呼吸困难", "乏力", "下肢水肿"],
            "duration": "3个月"
        },
        "prescription": {
            "drug": "美托洛尔缓释片",
            "dosage": "47.5mg",
            "frequency": "每日一次",
            "duration": "长期"
        }
    }
    
    print("\n自定义输入案例分析:")
    print(f"药品: {custom_input['prescription']['drug']}")
    print(f"疾病描述: {custom_input['description']}")
    
    result = inference_engine.analyze(custom_input)
    
    print(f"\n分析结果:")
    print(f"是否超适应症: {result.get('is_offlabel', 'N/A')}")
    print(f"置信度: {result.get('confidence', 'N/A')}")
    print(f"适应症匹配分数: {result.get('analysis', {}).get('indication_match', {}).get('score', 'N/A')}")
    print(f"机制相似度: {result.get('analysis', {}).get('mechanism_similarity', {}).get('score', 'N/A')}")
    
    assert result is not None
    assert 'is_offlabel' in result
    
    captured = capsys.readouterr()
    print(captured.out)


def test_analyze_batch(inference_engine, capsys):
    """测试批量分析"""
    input_list = [
        load_test_input("entity_recognition_input_1.json"),
        load_test_input("entity_recognition_input_2.json")
    ]
    
    print("\n批量分析测试:")
    print(f"病例数量: {len(input_list)}")
    
    results = inference_engine.analyze_batch(input_list)
    
    print(f"\n批量分析结果:")
    print(f"成功处理: {len([r for r in results if 'error' not in r])}/{len(results)}")
    print(f"失败处理: {len([r for r in results if 'error' in r])}/{len(results)}")
    
    for idx, result in enumerate(results, 1):
        if 'error' not in result:
            print(f"\n病例 {idx}:")
            print(f"  是否超适应症: {result.get('is_offlabel', 'N/A')}")
            print(f"  置信度: {result.get('confidence', 'N/A')}")
        else:
            print(f"\n病例 {idx}: 处理失败 - {result.get('error', 'Unknown error')}")
    
    assert len(results) == len(input_list)
    
    captured = capsys.readouterr()
    print(captured.out)


def test_analyze_result_structure(inference_engine, capsys):
    """测试分析结果的完整性"""
    input_data = load_test_input("entity_recognition_input_1.json")
    result = inference_engine.analyze(input_data)
    
    print("\n结果结构验证:")
    
    # 检查必需字段
    required_fields = [
        'is_offlabel',
        'recommendation'
    ]
    
    for field in required_fields:
        is_present = field in result
        print(f"  {field}: {'✓' if is_present else '✗'}")
        assert is_present, f"缺少必需字段: {field}"
    
    # 检查analysis子字段
    if 'analysis' in result:
        analysis_fields = ['indication_match', 'mechanism_similarity', 'evidence_support']
        print("\n  analysis子字段:")
        for field in analysis_fields:
            is_present = field in result['analysis']
            print(f"    {field}: {'✓' if is_present else '✗'}")
    
    # 检查recommendation子字段
    if 'recommendation' in result:
        recommendation_fields = ['decision', 'explanation']
        print("\n  recommendation子字段:")
        for field in recommendation_fields:
            is_present = field in result['recommendation']
            print(f"    {field}: {'✓' if is_present else '✗'}")
    
    captured = capsys.readouterr()
    print(captured.out)


def test_analyze_evidence_synthesis(inference_engine, capsys):
    """测试证据综合"""
    input_data = load_test_input("entity_recognition_input_1.json")
    result = inference_engine.analyze(input_data)
    
    print("\n证据综合测试:")
    
    if 'evidence_synthesis' in result:
        evidence = result['evidence_synthesis']
        print(f"匹配的适应症: {evidence.get('matching_indication', 'N/A')}")
        print(f"证据等级: {evidence.get('evidence_level', 'N/A')}")
        print(f"证据来源数量: {len(evidence.get('sources', []))}")
        
        assert 'evidence_level' in evidence
    else:
        print("注意: 结果中不包含evidence_synthesis字段")
    
    captured = capsys.readouterr()
    print(captured.out)


def test_batch_process_backward_compatibility(capsys):
    """测试向后兼容的批量处理函数"""
    from app.inference.engine import batch_process
    
    input_list = [
        load_test_input("entity_recognition_input_1.json"),
    ]
    
    print("\n向后兼容性测试 - batch_process:")
    
    results = batch_process(input_list)
    
    print(f"处理结果数量: {len(results)}")
    assert len(results) == len(input_list)
    
    captured = capsys.readouterr()
    print(captured.out)


def test_process_case_backward_compatibility(capsys):
    """测试向后兼容的单例处理函数"""
    from app.inference.engine import process_case
    
    input_data = load_test_input("entity_recognition_input_1.json")
    
    print("\n向后兼容性测试 - process_case:")
    
    result = process_case(input_data)
    
    print(f"是否超适应症: {result.get('is_offlabel', 'N/A')}")
    assert 'is_offlabel' in result
    
    captured = capsys.readouterr()
    print(captured.out)


def test_end_to_end_workflow(inference_engine, capsys):
    """测试完整的端到端工作流程"""
    print("\n完整端到端工作流程测试:")
    
    # 准备输入
    input_data = {
        "description": "患者诊断为高血压，处方阿司匹林肠溶片用于预防心血管事件",
        "patient_info": {
            "age": 58,
            "gender": "男",
            "symptoms": ["血压升高"],
            "duration": "5年"
        },
        "prescription": {
            "drug": "阿司匹林肠溶片",
            "dosage": "100mg",
            "frequency": "每日一次",
            "duration": "长期"
        }
    }
    
    print("步骤1: 输入数据准备 ✓")
    
    # 执行分析
    print("步骤2: 执行推理引擎...")
    result = inference_engine.analyze(input_data)
    print("步骤2: 推理引擎执行完成 ✓")
    
    # 验证输出
    print("步骤3: 验证输出结构...")
    assert 'is_offlabel' in result
    assert 'recommendation' in result
    print("步骤3: 输出结构验证通过 ✓")
    
    # 显示结果
    print("\n最终结果:")
    print(f"  是否超适应症: {result['is_offlabel']}")
    print(f"  决策建议: {result['recommendation']['decision']}")
    print(f"  解释: {result['recommendation']['explanation'][:100]}...")
    
    print("\n端到端工作流程测试完成 ✓")
    
    captured = capsys.readouterr()
    print(captured.out)


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
