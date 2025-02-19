import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.offlabel_analysis.indication_analysis import IndicationAnalyzer
from src.offlabel_analysis.models import Case, RecognizedEntities, Drug, Disease, Context, AnalysisResult

@pytest.fixture
def mock_es_client():
    return Mock()

@pytest.fixture
def mock_inference_client():
    return Mock()

@pytest.fixture
def indication_analyzer(mock_es_client, mock_inference_client):
    with patch('src.offlabel_analysis.indication_analysis.get_elastic_client', return_value=mock_es_client), \
         patch('src.offlabel_analysis.indication_analysis.InferenceClient', return_value=mock_inference_client):
        return IndicationAnalyzer()

@pytest.fixture
def sample_case():
    return Case(
        id="case_001",
        recognized_entities=RecognizedEntities(
            drug=Drug(id="drug_001", name="阿莫西林", standard_name="阿莫西林"),
            disease=Disease(id="disease_001", name="急性链球菌性咽炎", standard_name="急性链球菌性咽炎"),
            context=Context(description="患者因发热、咽痛就诊", additional_info={})
        )
    )

def test_analyze_standard_indication(indication_analyzer, mock_es_client, mock_inference_client, sample_case):
    """测试标准适应症用药分析"""
    # 模拟药品信息
    mock_es_client.get.return_value = {
        '_source': {
            'id': 'drug_001',
            'name': '阿莫西林',
            'indications': ['用于敏感菌所致的急性链球菌性咽炎等感染'],
            'contraindications': ['对青霉素类药物过敏的患者禁用'],
            'precautions': ['用药期间注意观察不良反应'],
            'details': {'药理毒理': '阿莫西林为广谱青霉素类抗生素，通过抑制细菌细胞壁合成发挥杀菌作用'}
        }
    }
    
    # 模拟LLM分析结果
    mock_inference_client.text_generation.return_value = '''
    {
        "is_offlabel": false,
        "analysis": {
            "indication_match": {
                "score": 0.95,
                "matching_indication": "用于敏感菌所致的急性链球菌性咽炎等感染",
                "reasoning": "患者诊断与药品适应症完全匹配"
            },
            "mechanism_similarity": {
                "score": 1.0,
                "reasoning": "作为青霉素类抗生素，阿莫西林是治疗链球菌性咽炎的一线用药"
            },
            "evidence_support": {
                "level": "A",
                "description": "有充分的循证医学证据支持该用药"
            }
        },
        "recommendation": {
            "decision": "建议使用",
            "explanation": "该用药符合适应症，有充分的循证医学证据支持",
            "risk_assessment": "在注意青霉素过敏等禁忌症的情况下，不良反应风险可控"
        }
    }
    '''
    
    result = indication_analyzer.analyze_indication(sample_case)
    
    assert isinstance(result, AnalysisResult)
    assert result.is_offlabel == False
    assert result.analysis.indication_match.score == 0.95
    assert result.recommendation.decision == "建议使用"

def test_analyze_reasonable_offlabel(indication_analyzer, mock_es_client, mock_inference_client):
    """测试合理的超适应症用药分析"""
    case = Case(
        id="case_002",
        recognized_entities=RecognizedEntities(
            drug=Drug(id="drug_002", name="西地那非", standard_name="西地那非"),
            disease=Disease(id="disease_002", name="肺动脉高压", standard_name="肺动脉高压"),
            context=Context(description="患者诊断为继发性肺动脉高压", additional_info={})
        )
    )
    
    # 模拟药品信息
    mock_es_client.get.return_value = {
        '_source': {
            'id': 'drug_002',
            'name': '西地那非',
            'indications': ['用于勃起功能障碍的治疗'],
            'contraindications': ['硝酸酯类药物治疗的患者禁用'],
            'precautions': ['心血管疾病患者慎用'],
            'details': {'药理毒理': '西地那非通过抑制PDE5，增加cGMP浓度，导致平滑肌舒张'}
        }
    }
    
    # 模拟LLM分析结果
    mock_inference_client.text_generation.return_value = '''
    {
        "is_offlabel": true,
        "analysis": {
            "indication_match": {
                "score": 0.2,
                "matching_indication": "用于勃起功能障碍的治疗",
                "reasoning": "当前用药不在药品说明书的适应症范围内"
            },
            "mechanism_similarity": {
                "score": 0.9,
                "reasoning": "药物作用机制与肺动脉高压的病理机制相关，PDE5抑制剂可降低肺动脉压力"
            },
            "evidence_support": {
                "level": "B",
                "description": "有临床研究证据支持该超适应症用药的安全性和有效性"
            }
        },
        "recommendation": {
            "decision": "谨慎使用",
            "explanation": "虽为超适应症用药，但有机制和临床证据支持",
            "risk_assessment": "需要密切监测心血管不良反应"
        }
    }
    '''
    
    result = indication_analyzer.analyze_indication(case)
    
    assert isinstance(result, AnalysisResult)
    assert result.is_offlabel == True
    assert result.analysis.mechanism_similarity.score == 0.9
    assert result.recommendation.decision == "谨慎使用"

def test_analyze_unreasonable_offlabel(indication_analyzer, mock_es_client, mock_inference_client):
    """测试不推荐的超适应症用药分析"""
    case = Case(
        id="case_003",
        recognized_entities=RecognizedEntities(
            drug=Drug(id="drug_003", name="奥氮平", standard_name="奥氮平"),
            disease=Disease(id="disease_003", name="轻度焦虑症", standard_name="轻度焦虑症"),
            context=Context(description="患者因轻度焦虑就诊", additional_info={})
        )
    )
    
    # 模拟药品信息
    mock_es_client.get.return_value = {
        '_source': {
            'id': 'drug_003',
            'name': '奥氮平',
            'indications': ['用于精神分裂症和中重度躁狂发作的治疗'],
            'contraindications': ['对奥氮平过敏者禁用'],
            'precautions': ['可能导致体重增加和代谢综合征'],
            'details': {'药理毒理': '奥氮平是一种非典型抗精神病药，主要通过阻断多巴胺D2受体和5-HT2A受体发挥作用'}
        }
    }
    
    # 模拟LLM分析结果
    mock_inference_client.text_generation.return_value = '''
    {
        "is_offlabel": true,
        "analysis": {
            "indication_match": {
                "score": 0.1,
                "matching_indication": "用于精神分裂症和中重度躁狂发作的治疗",
                "reasoning": "当前诊断与药品适应症不符"
            },
            "mechanism_similarity": {
                "score": 0.3,
                "reasoning": "轻度焦虑症不需要使用抗精神病药物，作用机制过强"
            },
            "evidence_support": {
                "level": "D",
                "description": "缺乏证据支持在轻度焦虑症中使用，且存在明显过度用药风险"
            }
        },
        "recommendation": {
            "decision": "不建议使用",
            "explanation": "不符合适应症，且存在明显的获益-风险比失衡",
            "risk_assessment": "可能导致不必要的代谢不良反应，建议改用其他抗焦虑药物"
        }
    }
    '''
    
    result = indication_analyzer.analyze_indication(case)
    
    assert isinstance(result, AnalysisResult)
    assert result.is_offlabel == True
    assert result.analysis.mechanism_similarity.score == 0.3
    assert result.recommendation.decision == "不建议使用"

def test_analyze_drug_not_found(indication_analyzer, mock_es_client):
    """测试药品信息获取失败的情况"""
    case = Case(
        id="case_error",
        recognized_entities=RecognizedEntities(
            drug=Drug(id="not_exist", name="不存在的药", standard_name="不存在的药"),
            disease=Disease(id="disease_001", name="感冒", standard_name="感冒"),
            context=Context(description="测试用例", additional_info={})
        )
    )
    
    mock_es_client.get.side_effect = Exception("Drug not found")
    
    with pytest.raises(Exception, match="Drug not found"):
        indication_analyzer.analyze_indication(case)

def test_analyze_invalid_llm_response(indication_analyzer, mock_es_client, mock_inference_client, sample_case):
    """测试LLM响应解析失败的情况"""
    mock_es_client.get.return_value = {
        '_source': {
            'id': 'drug_001',
            'name': '测试药品',
            'indications': ['测试适应症']
        }
    }
    
    mock_inference_client.text_generation.return_value = 'Invalid JSON'
    
    with pytest.raises(json.JSONDecodeError):
        indication_analyzer.analyze_indication(sample_case)
