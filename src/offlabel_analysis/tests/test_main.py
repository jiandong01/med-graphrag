"""主流程测试"""

import json
import os
import pytest
from unittest.mock import Mock, patch
from src.offlabel_analysis.main import process_case

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r') as f:
        return json.load(f)

@pytest.fixture
def mock_environment():
    """模拟所有外部依赖"""
    with patch('src.offlabel_analysis.entity_recognition.get_elastic_client') as mock_es, \
         patch('src.offlabel_analysis.entity_recognition.InferenceClient') as mock_llm:
        
        mock_es_client = Mock()
        mock_llm_client = Mock()
        mock_es.return_value = mock_es_client
        mock_llm.return_value = mock_llm_client
        
        yield {
            'es_client': mock_es_client,
            'llm_client': mock_llm_client
        }

def test_process_case_entity_recognition(mock_environment):
    """测试主流程中的实体识别部分"""
    # 加载测试数据
    input_data = load_test_data('input/entity_recognition_input_1.json')
    expected_output = load_test_data('output/entity_recognition_output_1.json')
    
    # 模拟LLM响应
    mock_environment['llm_client'].text_generation.return_value = json.dumps({
        "drug": {"name": expected_output["drug"]["name"]},
        "disease": {"name": expected_output["disease"]["name"]},
        "context": expected_output["context"]
    })
    
    # 模拟ES搜索响应
    mock_environment['es_client'].search.side_effect = [
        {'hits': {'hits': [{'_source': expected_output["drug"]}]}},
        {'hits': {'hits': [{'_source': expected_output["disease"]}]}}
    ]
    
    # 执行测试
    result = process_case(input_data)
    
    # 验证结果
    assert result['drug_info']['id'] == expected_output['drug']['id']
    assert result['drug_info']['name'] == expected_output['drug']['name']
    assert result['disease_info']['id'] == expected_output['disease']['id']
    assert result['disease_info']['name'] == expected_output['disease']['name']

def test_process_case_entity_recognition_error(mock_environment):
    """测试主流程中实体识别错误的处理"""
    # 加载测试数据
    input_data = load_test_data('input/entity_recognition_input_error.json')
    expected_error = load_test_data('output/entity_recognition_output_error.json')
    
    # 模拟LLM响应
    mock_environment['llm_client'].text_generation.return_value = json.dumps(
        expected_error["details"]["llm_response"]
    )
    
    # 模拟ES搜索响应
    mock_environment['es_client'].search.return_value = \
        expected_error["details"]["es_search_results"]["drug_search"]
    
    # 执行测试并验证错误
    with pytest.raises(Exception) as exc_info:
        process_case(input_data)
    
    assert str(exc_info.value) == expected_error["error_message"]
