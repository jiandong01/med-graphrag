"""简洁版端到端测试 - 基于CSV数据格式

输入格式: CSV行数据 (疾病, 药物)
输出: 结构化的超适应症判断结果
"""

import pytest
import json
from app.inference.engine import InferenceEngine
from app.shared import Config

load_env = Config.load_env
load_env()


@pytest.fixture(scope="module")
def inference_engine():
    """创建推理引擎实例"""
    return InferenceEngine()


def test_e2e_case_1_rare_disease(inference_engine, capsys):
    """
    端到端测试案例1: 罕见病超适应症用药 - 显示完整流程
    
    CSV数据: disease_id=1, 疾病=21-羟化酶缺乏症, group=代谢, drug_id=1, 药品=氟氢可的松, 是否超适应症=是
    """
    # 输入: 疾病和药物
    disease = "21-羟化酶缺乏症"
    drug = "氟氢可的松"
    
    # 构造输入
    input_data = {
        "description": f"患者诊断为{disease}，拟使用{drug}治疗",
        "patient_info": {"age": 25, "gender": "男"},
        "prescription": {"drug": drug, "dosage": "0.1mg", "frequency": "每日一次"}
    }
    
    print(f"\n{'='*70}")
    print(f"测试案例: {disease} + {drug} (CSV第1行)")
    print(f"{'='*70}")
    
    # 阶段1：原始输入
    print("\n【阶段1: 原始输入】")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    # 阶段2：实体识别
    print("\n【阶段2: 实体识别】")
    recognized = inference_engine.entity_recognizer.recognize(input_data)
    print(f"识别到的药品: {recognized.drugs[0].name if recognized.drugs else '无'}")
    if recognized.drugs and recognized.drugs[0].matches:
        print(f"  匹配结果: {recognized.drugs[0].matches[0].standard_name} (ID: {recognized.drugs[0].matches[0].id})")
    print(f"识别到的疾病: {recognized.diseases[0].name if recognized.diseases else '无'}")
    if recognized.diseases and recognized.diseases[0].matches:
        print(f"  匹配结果: {recognized.diseases[0].matches[0].standard_name} (ID: {recognized.diseases[0].matches[0].id})")
    
    # 阶段3：知识增强
    print("\n【阶段3: 知识增强】")
    from app.inference.models import Case
    from app.inference.knowledge_retriever import KnowledgeEnhancer
    
    case = Case(id="test", recognized_entities=recognized)
    enhancer = KnowledgeEnhancer()
    enhanced_case = enhancer.enhance_case(case)
    
    print(f"药品信息:")
    print(f"  标准名称: {enhanced_case.drug.standard_name}")
    print(f"  适应症数量: {len(enhanced_case.drug.indications)}")
    if enhanced_case.drug.indications:
        print(f"  适应症示例: {enhanced_case.drug.indications[:2]}")
    
    print(f"疾病信息:")
    print(f"  标准名称: {enhanced_case.disease.standard_name}")
    print(f"  ICD编码: {enhanced_case.disease.icd_code}")
    
    # 阶段4：LLM分析（显示传给LLM的数据）
    print("\n【阶段4: LLM分析】")
    print("传给LLM的关键数据:")
    llm_input_summary = {
        "药品名称": enhanced_case.drug.name,
        "药品适应症": enhanced_case.drug.indications[:3] if enhanced_case.drug.indications else [],
        "疾病名称": enhanced_case.disease.name,
        "疾病描述": enhanced_case.disease.description[:100] if enhanced_case.disease.description else None
    }
    print(json.dumps(llm_input_summary, ensure_ascii=False, indent=2))
    
    # 阶段5：完整分析（执行完整流程）
    print("\n【阶段5: 完整分析执行】")
    result = inference_engine.analyze(input_data)
    
    # 最终输出
    print("\n【最终输出】")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 验证
    assert 'is_offlabel' in result
    assert 'recommendation' in result
    
    print(f"\n{'='*70}")
    print("✓ 测试通过")
    print(f"{'='*70}\n")
    
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_case_2_common_disease(inference_engine, capsys):
    """
    端到端测试案例2: 常见病标准用药（对照）
    
    疾病: 急性咽炎, 药物: 阿莫西林 (应为标准适应症)
    """
    disease = "急性咽炎"
    drug = "阿莫西林"
    
    input_data = {
        "description": f"患者诊断为{disease}，拟使用{drug}治疗",
        "patient_info": {"age": 30, "gender": "男"},
        "prescription": {"drug": drug}
    }
    
    print(f"\n{'='*70}")
    print(f"测试案例: {disease} + {drug} (常见病对照)")
    print(f"{'='*70}")
    
    print("\n【输入】")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    print("\n【执行分析...】")
    result = inference_engine.analyze(input_data)
    
    print("\n【输出】")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    assert 'is_offlabel' in result
    
    print(f"\n{'='*70}")
    print(f"✓ 测试通过 - 系统识别为: {'超适应症' if result.get('is_offlabel') else '标准适应症'}")
    print(f"{'='*70}\n")
    
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_output_json_format(inference_engine, capsys):
    """
    测试输出JSON格式
    
    验证输出可以被序列化为JSON
    """
    input_data = {
        "description": "患者诊断为高血压，拟使用氢氯噻嗪治疗",
        "patient_info": {"age": 50, "gender": "男"},
        "prescription": {"drug": "氢氯噻嗪"}
    }
    
    print(f"\n{'='*70}")
    print("测试JSON序列化")
    print(f"{'='*70}")
    
    result = inference_engine.analyze(input_data)
    
    # 尝试序列化为JSON
    try:
        json_output = json.dumps(result, ensure_ascii=False, indent=2)
        print(f"\n✓ 结果可以成功序列化为JSON")
        print(f"\n【JSON输出】")
        print(json_output)
        assert True
    except Exception as e:
        print(f"\n✗ JSON序列化失败: {str(e)}")
        assert False, f"结果无法序列化为JSON: {str(e)}"
    
    print(f"\n{'='*70}")
    print("✓ 测试通过")
    print(f"{'='*70}\n")
    
    captured = capsys.readouterr()
    print(captured.out)


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
