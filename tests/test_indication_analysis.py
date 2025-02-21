"""适应症分析测试"""

import os
import json
import pytest
import logging
from dotenv import load_dotenv
from src.offlabel_analysis.indication_analysis import IndicationAnalyzer
from src.offlabel_analysis.models import (
    Case, AnalysisResult, RecognizedEntities, Context,
    RecognizedDrug, RecognizedDisease, DrugMatch, DiseaseMatch
)
from src.utils import get_elastic_client
from src.offlabel_analysis.utils import create_case_from_entity_recognition

# 加载环境变量
load_dotenv()

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.fixture(autouse=True)
def set_log_level():
    previous_level = logging.getLogger().level
    logging.getLogger().setLevel(logging.DEBUG)
    yield
    logging.getLogger().setLevel(previous_level)

@pytest.fixture(scope="module")
def indication_analyzer():
    """创建 IndicationAnalyzer 实例"""
    return IndicationAnalyzer(es=get_elastic_client())

def test_indication_analysis_case1(indication_analyzer, capsys):
    """测试适应症分析 - Case 1"""
    input_file = 'output/entity_recognition_output_1.json'
    input_data = load_test_data(input_file)
    
    print("\n=== Case 1 ===")
    print("\n1. 输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    case = create_case_from_entity_recognition(input_data)
    
    print("\n2. 创建的 Case 对象:")
    print(f"Case ID: {case.id}")
    print(f"Drugs: {[drug.name for drug in case.recognized_entities.drugs]}")
    print(f"Diseases: {[disease.name for disease in case.recognized_entities.diseases]}")
    if case.recognized_entities.context:
        print(f"Context: {case.recognized_entities.context.description}")
    
    try:
        result = indication_analyzer.analyze_indication(case)
        
        print("\n7. 最终分析结果:")
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
            },
            "metadata": result.metadata
        }
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n=== 错误信息 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误描述: {str(e)}")
        raise
    
    captured = capsys.readouterr()
    print(captured.out)

def test_indication_analysis_case2(indication_analyzer, capsys):
    """测试适应症分析 - Case 2"""
    input_file = 'output/entity_recognition_output_2.json'
    input_data = load_test_data(input_file)
    
    print("\n=== Case 2 ===")
    print("\n1. 输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    case = create_case_from_entity_recognition(input_data)
    
    print("\n2. 创建的 Case 对象:")
    print(f"Case ID: {case.id}")
    print(f"Drugs: {[drug.name for drug in case.recognized_entities.drugs]}")
    print(f"Diseases: {[disease.name for disease in case.recognized_entities.diseases]}")
    if case.recognized_entities.context:
        print(f"Context: {case.recognized_entities.context.description}")
    
    try:
        result = indication_analyzer.analyze_indication(case)
        
        print("\n7. 最终分析结果:")
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
            },
            "metadata": result.metadata
        }
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n=== 错误信息 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误描述: {str(e)}")
        raise
    
    captured = capsys.readouterr()
    print(captured.out)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
