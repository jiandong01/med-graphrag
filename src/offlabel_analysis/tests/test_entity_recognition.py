"""实体识别测试"""

import json
import os
import pytest
from unittest.mock import Mock, patch
from src.offlabel_analysis.entity_recognition import EntityRecognizer
from src.offlabel_analysis.models import RecognizedEntities, Drug, Disease, Context

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r') as f:
        return json.load(f)

@pytest.fixture
def mock_es_client():
    return Mock()

@pytest.fixture
def mock_inference_client():
    return Mock()

@pytest.fixture
def entity_recognizer(mock_es_client, mock_inference_client):
    with patch('src.offlabel_analysis.entity_recognition.get_elastic_client', return_value=mock_es_client), \
         patch('src.offlabel_analysis.entity_recognition.InferenceClient', return_value=mock_inference_client):
        return EntityRecognizer()

@pytest.mark.parametrize("input_file,output_file", [
    ('input/entity_recognition_input_1.json', 'output/entity_recognition_output_1.json'),
    ('input/entity_recognition_input_2.json', 'output/entity_recognition_output_2.json'),
])
def test_entity_recognition(entity_recognizer, mock_es_client, mock_inference_client, input_file, output_file):
    """测试实体识别"""
    input_data = load_test_data(input_file)
    expected_output = load_test_data(output_file)
    
    # 模拟LLM响应
    llm_response = {
        "drug": {"name": expected_output["drug"]["name"]},
        "disease": {"name": expected_output["disease"]["name"]},
        "context": expected_output["context"]
    }
    mock_inference_client.text_generation.return_value = json.dumps(llm_response)
    
    # 模拟ES搜索响应
    mock_es_client.search.side_effect = [
        {'hits': {'hits': [{'_source': {
            'id': expected_output["drug"]["id"],
            'name': expected_output["drug"]["name"]
        }}]}},
        {'hits': {'hits': [{'_source': {
            'id': expected_output["disease"]["id"],
            'name': expected_output["disease"]["name"]
        }}]}}
    ]
    
    result = entity_recognizer.recognize(input_data)
    
    assert isinstance(result, RecognizedEntities)
    assert result.drug.id == expected_output["drug"]["id"]
    assert result.drug.name == expected_output["drug"]["name"]
    assert result.drug.standard_name == expected_output["drug"]["standard_name"]
    assert result.disease.id == expected_output["disease"]["id"]
    assert result.disease.name == expected_output["disease"]["name"]
    assert result.disease.standard_name == expected_output["disease"]["standard_name"]
    assert result.context.description == expected_output["context"]["description"]

def test_entity_recognition_error(entity_recognizer, mock_es_client, mock_inference_client):
    """测试实体识别错误处理"""
    input_data = load_test_data('input/entity_recognition_input_error.json')
    expected_error = load_test_data('output/entity_recognition_output_error.json')
    
    # 模拟LLM响应
    mock_inference_client.text_generation.return_value = json.dumps(expected_error["details"]["llm_response"])
    
    # 模拟ES搜索响应 - 返回空结果
    mock_es_client.search.return_value = {'hits': {'hits': []}}
    
    with pytest.raises(ValueError) as exc_info:
        entity_recognizer.recognize(input_data)
    
    assert str(exc_info.value) == expected_error["error_message"]

def test_invalid_llm_response(entity_recognizer, mock_inference_client):
    """测试无效的LLM响应"""
    mock_inference_client.text_generation.return_value = 'Invalid JSON'
    
    input_data = {"description": "无效的输入数据"}
    
    with pytest.raises(json.JSONDecodeError):
        entity_recognizer.recognize(input_data)
