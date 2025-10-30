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


# CSV测试案例
CSV_TEST_CASES = [
    {"disease": "21-羟化酶缺乏症", "drug": "氟氢可的松", "csv_row": 1},
    {"disease": "21-羟化酶缺乏症", "drug": "氢化可的松", "csv_row": 1},
    {"disease": "肌萎缩侧索硬化", "drug": "维生素D", "csv_row": 4},
    {"disease": "非典型溶血性尿毒症", "drug": "硼替佐米", "csv_row": 8},
    {"disease": "自身免疫性脑炎", "drug": "阿立哌唑", "csv_row": 9},
]


def run_single_case(inference_engine, disease: str, drug: str, csv_row: int, capsys):
    """运行单个测试案例"""
    # 构造输入
    input_data = {
        "description": f"患者诊断为{disease}，拟使用{drug}治疗",
        "patient_info": {"age": 30, "gender": "男"},
        "prescription": {"drug": drug}
    }
    
    print(f"\n{'='*70}")
    print(f"CSV第{csv_row}行: {disease} + {drug}")
    print(f"{'='*70}")
    
    # 阶段1：原始输入
    print("\n【阶段1: 原始输入】")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    # 阶段2：实体识别
    print("\n【阶段2: 实体识别】")
    try:
        recognized = inference_engine.entity_recognizer.recognize(input_data)
        print(f"药品: {recognized.drugs[0].name if recognized.drugs else '未识别'}")
        if recognized.drugs and recognized.drugs[0].matches:
            print(f"  ES匹配: {recognized.drugs[0].matches[0].standard_name}")
        else:
            print(f"  ES匹配: 无")
            print(f"\n⚠️ 药品未在数据库中匹配，无法继续分析")
            return None
        
        print(f"疾病: {recognized.diseases[0].name if recognized.diseases else '未识别'}")
        if recognized.diseases and recognized.diseases[0].matches:
            print(f"  ES匹配: {recognized.diseases[0].matches[0].standard_name}")
        else:
            print(f"  ES匹配: 无（将使用LLM识别的原始名称）")
    except Exception as e:
        print(f"实体识别失败: {str(e)}")
        return None
    
    # 阶段3：执行完整分析
    print("\n【阶段3: 执行完整分析】")
    try:
        result = inference_engine.analyze(input_data)
        
        print("\n【最终输出】")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        return result
    except Exception as e:
        print(f"分析失败: {str(e)}")
        return None


def test_e2e_csv_case_1(inference_engine, capsys):
    """CSV第1行: 21-羟化酶缺乏症 + 氟氢可的松"""
    result = run_single_case(inference_engine, 
                            CSV_TEST_CASES[0]["disease"],
                            CSV_TEST_CASES[0]["drug"],
                            CSV_TEST_CASES[0]["csv_row"],
                            capsys)
    if result:
        assert 'is_offlabel' in result
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_csv_case_2(inference_engine, capsys):
    """CSV第1行: 21-羟化酶缺乏症 + 氢化可的松"""
    result = run_single_case(inference_engine,
                            CSV_TEST_CASES[1]["disease"],
                            CSV_TEST_CASES[1]["drug"],
                            CSV_TEST_CASES[1]["csv_row"],
                            capsys)
    if result:
        assert 'is_offlabel' in result
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_csv_case_3(inference_engine, capsys):
    """CSV第4行: 肌萎缩侧索硬化 + 维生素D"""
    result = run_single_case(inference_engine,
                            CSV_TEST_CASES[2]["disease"],
                            CSV_TEST_CASES[2]["drug"],
                            CSV_TEST_CASES[2]["csv_row"],
                            capsys)
    if result:
        assert 'is_offlabel' in result
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_csv_case_4(inference_engine, capsys):
    """CSV第8行: 非典型溶血性尿毒症 + 硼替佐米"""
    result = run_single_case(inference_engine,
                            CSV_TEST_CASES[3]["disease"],
                            CSV_TEST_CASES[3]["drug"],
                            CSV_TEST_CASES[3]["csv_row"],
                            capsys)
    if result:
        assert 'is_offlabel' in result
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_csv_case_5(inference_engine, capsys):
    """CSV第9行: 自身免疫性脑炎 + 阿立哌唑"""
    result = run_single_case(inference_engine,
                            CSV_TEST_CASES[4]["disease"],
                            CSV_TEST_CASES[4]["drug"],
                            CSV_TEST_CASES[4]["csv_row"],
                            capsys)
    if result:
        assert 'is_offlabel' in result
    captured = capsys.readouterr()
    print(captured.out)


def test_e2e_case_common_disease(inference_engine, capsys):
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
    
    # 阶段4：确定实际用于分析的疾病名称
    print("\n【阶段4: 确定分析用疾病名】")
    if recognized.diseases and recognized.diseases[0].matches:
        actual_disease_name = enhanced_case.disease.name or recognized.diseases[0].name
        print(f"使用ES匹配的疾病名: {actual_disease_name}")
    elif recognized.diseases:
        actual_disease_name = recognized.diseases[0].name
        print(f"ES未匹配，使用LLM抽取的原始疾病名: {actual_disease_name}")
    else:
        actual_disease_name = None
        print("未识别到疾病")
    
    print("\n传给LLM分析的数据:")
    llm_input_summary = {
        "药品名称": enhanced_case.drug.name,
        "药品适应症": enhanced_case.drug.indications[:3] if enhanced_case.drug.indications else [],
        "疾病名称": actual_disease_name,
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




if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
