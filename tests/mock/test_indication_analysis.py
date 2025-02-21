"""适应症分析测试"""

import os
import json
import pytest
from unittest.mock import patch
from dotenv import load_dotenv
from src.offlabel_analysis.indication_analysis import IndicationAnalyzer, ANALYSIS_PROMPT_TEMPLATE
from src.offlabel_analysis.models import (
    Case, AnalysisResult, RecognizedEntities, Context,
    RecognizedDrug, RecognizedDisease, DrugMatch, DiseaseMatch
)
from src.utils import get_elastic_client
from datetime import datetime
from src.offlabel_analysis.tests.mock.mock_elasticsearch import MockElasticsearch
from src.offlabel_analysis.tests.mock.mock_huggingface import MockInferenceClient

# 加载环境变量
load_dotenv()

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)

def create_case_from_entity_recognition(data: dict) -> Case:
    """从实体识别结果创建Case对象"""
    # 创建药品列表
    drugs = [
        RecognizedDrug(
            name=drug['name'],
            matches=[
                DrugMatch(
                    id=match['id'],
                    standard_name=match['standard_name'],
                    score=match['score']
                )
                for match in drug.get('matches', [])
            ]
        )
        for drug in data.get('drugs', [])
    ]
    
    # 创建疾病列表
    diseases = [
        RecognizedDisease(
            name=disease['name'],
            matches=[
                DiseaseMatch(
                    id=match['id'],
                    standard_name=match['standard_name'],
                    score=match['score']
                )
                for match in disease.get('matches', [])
            ]
        )
        for disease in data.get('diseases', [])
    ]
    
    # 创建上下文
    context = None
    if 'context' in data:
        context = Context(
            description=data['context']['description'],
            raw_data=data['context']['raw_data']
        )
    
    # 创建RecognizedEntities
    recognized_entities = RecognizedEntities(
        drugs=drugs,
        diseases=diseases,
        context=context
    )
    
    # 创建Case
    return Case(
        id=f"case_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        recognized_entities=recognized_entities
    )

@pytest.fixture(scope="module")
def indication_analyzer():
    """创建 IndicationAnalyzer 实例，使用mock"""
    with patch('src.utils.get_elastic_client', return_value=MockElasticsearch()):
        analyzer = IndicationAnalyzer(es=MockElasticsearch())
        analyzer.client = MockInferenceClient()
        return analyzer

@pytest.mark.parametrize("input_file,output_file", [
    ('output/entity_recognition_output_1.json', 'output/indication_analysis_output_1.json'),
    ('output/entity_recognition_output_2.json', 'output/indication_analysis_output_2.json'),
])
def test_indication_analysis(indication_analyzer, input_file, output_file, capsys):
    """测试适应症分析"""
    input_data = load_test_data(input_file)
    
    print(f"\n原始输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    case = create_case_from_entity_recognition(input_data)
    
    # 获取原始响应
    enhanced_case = indication_analyzer.knowledge_enhancer.enhance_case(case)
    rule_result = indication_analyzer.rule_analyzer.analyze(
        {
            "id": enhanced_case.drug.id,
            "name": enhanced_case.drug.name,
            "indications": enhanced_case.drug.indications,
            "contraindications": enhanced_case.drug.contraindications,
            "details": enhanced_case.drug.details
        },
        {
            "id": enhanced_case.disease.id,
            "name": enhanced_case.disease.name
        }
    )
    
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        drug_name=enhanced_case.drug.name,
        indications=json.dumps(enhanced_case.drug.indications, ensure_ascii=False),
        pharmacology=enhanced_case.drug.pharmacology or "无相关信息",
        contraindications=json.dumps(enhanced_case.drug.contraindications, ensure_ascii=False),
        precautions=json.dumps(enhanced_case.drug.precautions, ensure_ascii=False),
        diagnosis=enhanced_case.disease.name,
        description=enhanced_case.context.description if enhanced_case.context else "",
        rule_analysis=json.dumps(rule_result, ensure_ascii=False),
        clinical_guidelines=json.dumps(enhanced_case.evidence.clinical_guidelines, ensure_ascii=False),
        expert_consensus=json.dumps(enhanced_case.evidence.expert_consensus, ensure_ascii=False),
        research_papers=json.dumps(enhanced_case.evidence.research_papers, ensure_ascii=False)
    )
    print(f"\n生成的Prompt:")
    print(prompt)
    
    response = indication_analyzer.client.text_generation(
        prompt,
        model="Qwen/Qwen-14B-Chat",
        max_new_tokens=2000,
        temperature=0.1,
        repetition_penalty=1.1
    )
    print(f"\n原始LLM响应:\n{response}")
    
    result = indication_analyzer.analyze_indication(case)
    
    print(f"\n测试输入文件: {input_file}")
    print("分析结果:")
    result_dict = {
        "is_offlabel": result.is_offlabel,
        "confidence": result.confidence,
        "analysis": {
            "indication_match": {
                "score": result.analysis.indication_match.score,
                "matching_indication": result.analysis.indication_match.matching_indication,
                "reasoning": result.analysis.indication_match.reasoning
            },
            "mechanism_similarity": {
                "score": result.analysis.mechanism_similarity.score,
                "reasoning": result.analysis.mechanism_similarity.reasoning
            },
            "evidence_support": {
                "level": result.analysis.evidence_support.level,
                "description": result.analysis.evidence_support.description
            }
        },
        "recommendation": {
            "decision": result.recommendation.decision,
            "explanation": result.recommendation.explanation,
            "risk_assessment": result.recommendation.risk_assessment
        }
    }
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    # 对比结果与预期输出
    expected_output = load_test_data(output_file)
    assert result.is_offlabel == expected_output['is_offlabel']
    assert result.confidence == pytest.approx(expected_output['confidence'], 0.01)
    assert result.analysis.indication_match.score == pytest.approx(expected_output['analysis']['indication_match']['score'], 0.01)
    assert result.recommendation.decision == expected_output['recommendation']['decision']
    
    captured = capsys.readouterr()
    print(captured.out)

def test_indication_analysis_error(indication_analyzer, capsys):
    """测试适应症分析错误处理"""
    input_data = load_test_data('output/entity_recognition_output_error.json')
    case = create_case_from_entity_recognition(input_data)
    
    print(f"\n原始输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    with pytest.raises(ValueError) as excinfo:
        indication_analyzer.analyze_indication(case)
    
    print("\n测试错误处理:")
    print(f"抛出的异常: {str(excinfo.value)}")
    
    error_msg = str(excinfo.value)
    assert any(msg in error_msg for msg in ["未识别到药品信息", "未找到匹配的标准药品", "未识别到疾病信息"])
    
    captured = capsys.readouterr()
    print(captured.out)

def test_batch_analyze(indication_analyzer, capsys):
    """测试批量分析功能"""
    input_data_1 = load_test_data('output/entity_recognition_output_1.json')
    input_data_2 = load_test_data('output/entity_recognition_output_2.json')
    
    cases = [
        create_case_from_entity_recognition(input_data_1),
        create_case_from_entity_recognition(input_data_2)
    ]
    results = indication_analyzer.batch_analyze(cases)
    
    print("\n批量分析结果:")
    for i, result in enumerate(results, 1):
        print(f"Case {i}:")
        result_dict = {
            "id": result.id,
            "analysis_result": {
                "is_offlabel": result.analysis_result.is_offlabel,
                "confidence": result.analysis_result.confidence,
                "analysis": {
                    "indication_match": {
                        "score": result.analysis_result.analysis.indication_match.score,
                        "matching_indication": result.analysis_result.analysis.indication_match.matching_indication,
                        "reasoning": result.analysis_result.analysis.indication_match.reasoning
                    },
                    "mechanism_similarity": {
                        "score": result.analysis_result.analysis.mechanism_similarity.score,
                        "reasoning": result.analysis_result.analysis.mechanism_similarity.reasoning
                    },
                    "evidence_support": {
                        "level": result.analysis_result.analysis.evidence_support.level,
                        "description": result.analysis_result.analysis.evidence_support.description
                    }
                },
                "recommendation": {
                    "decision": result.analysis_result.recommendation.decision,
                    "explanation": result.analysis_result.recommendation.explanation,
                    "risk_assessment": result.analysis_result.recommendation.risk_assessment
                }
            } if result.analysis_result else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
        }
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        print()
    
    assert len(results) == 2
    assert all(isinstance(result, Case) for result in results)
    assert all(result.analysis_result is not None for result in results)
    
    captured = capsys.readouterr()
    print(captured.out)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
