"""实体识别测试"""

import json
import os
import pytest
from unittest.mock import Mock, patch
from src.offlabel_analysis.entity_recognition import EntityRecognizer
from src.offlabel_analysis.models import RecognizedEntities, Drug, Disease, Context, DrugMatch, DiseaseMatch

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r') as f:
        return json.load(f)

class MockMessage:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, message):
        self.message = message

class MockCompletion:
    def __init__(self, choices):
        self.choices = choices

class MockChatCompletions:
    def __init__(self):
        self.create = Mock()

class MockChat:
    def __init__(self):
        self.completions = MockChatCompletions()

@pytest.fixture
def mock_es_client():
    return Mock()

@pytest.fixture
def mock_openai_client():
    client = Mock()
    client.chat = MockChat()
    return client

@pytest.fixture
def entity_recognizer(mock_es_client, mock_openai_client):
    with patch('src.offlabel_analysis.entity_recognition.get_elastic_client', return_value=mock_es_client), \
         patch('src.offlabel_analysis.entity_recognition.OpenAI', return_value=mock_openai_client):
        recognizer = EntityRecognizer()
        recognizer.client = mock_openai_client
        return recognizer

def setup_mock_completion(mock_openai_client, content):
    """设置模拟的OpenAI completion响应"""
    message = MockMessage(content)
    choice = MockChoice(message)
    completion = MockCompletion([choice])
    mock_openai_client.chat.completions.create.return_value = completion

@pytest.mark.parametrize("input_file,output_file", [
    ('input/entity_recognition_input_1.json', 'output/entity_recognition_output_1.json'),
    ('input/entity_recognition_input_2.json', 'output/entity_recognition_output_2.json'),
])
def test_entity_recognition(entity_recognizer, mock_es_client, mock_openai_client, input_file, output_file):
    """测试实体识别"""
    input_data = load_test_data(input_file)
    expected_output = load_test_data(output_file)
    
    # 模拟LLM响应
    llm_response = {
        "drugs": [{"name": drug["name"]} for drug in expected_output["drugs"]],
        "diseases": [{"name": disease["name"]} for disease in expected_output["diseases"]],
        "context": expected_output["context"]
    }
    setup_mock_completion(mock_openai_client, json.dumps(llm_response))
    
    # 模拟ES搜索响应
    def mock_es_search(*args, **kwargs):
        if kwargs['index'] == entity_recognizer.drugs_index:
            return {
                'hits': {
                    'hits': [
                        {
                            '_source': {
                                'id': match['id'],
                                'name': match['standard_name']
                            },
                            '_score': match['score']
                        }
                        for drug in expected_output["drugs"]
                        for match in drug["matches"]
                    ]
                }
            }
        elif kwargs['index'] == entity_recognizer.diseases_index:
            return {
                'hits': {
                    'hits': [
                        {
                            '_source': {
                                'id': match['id'],
                                'name': match['standard_name']
                            },
                            '_score': match['score']
                        }
                        for disease in expected_output["diseases"]
                        for match in disease["matches"]
                    ]
                }
            }
    
    mock_es_client.search.side_effect = mock_es_search
    
    result = entity_recognizer.recognize(input_data)
    
    assert isinstance(result, RecognizedEntities)
    assert len(result.drugs) == len(expected_output["drugs"])
    assert len(result.diseases) == len(expected_output["diseases"])
    
    for i, drug in enumerate(result.drugs):
        assert drug.name == expected_output["drugs"][i]["name"]
        assert len(drug.matches) > 0
        assert drug.matches[0].id == expected_output["drugs"][i]["matches"][0]["id"]
        assert drug.matches[0].standard_name == expected_output["drugs"][i]["matches"][0]["standard_name"]
    
    for i, disease in enumerate(result.diseases):
        assert disease.name == expected_output["diseases"][i]["name"]
        assert len(disease.matches) > 0
        assert disease.matches[0].id == expected_output["diseases"][i]["matches"][0]["id"]
        assert disease.matches[0].standard_name == expected_output["diseases"][i]["matches"][0]["standard_name"]
    
    assert result.context.description == expected_output["context"]["description"]
    assert result.context.raw_data == input_data

def test_entity_recognition_error(entity_recognizer, mock_es_client, mock_openai_client):
    """测试实体识别错误处理"""
    input_data = load_test_data('input/entity_recognition_input_error.json')
    expected_error = load_test_data('output/entity_recognition_output_error.json')
    
    # 模拟LLM响应
    llm_response = {
        "drugs": [],
        "diseases": [],
        "context": {
            "description": expected_error["context"]["description"]
        }
    }
    setup_mock_completion(mock_openai_client, json.dumps(llm_response))
    
    # 模拟ES搜索响应 - 返回空结果
    mock_es_client.search.return_value = {'hits': {'hits': []}}
    
    result = entity_recognizer.recognize(input_data)
    
    assert isinstance(result, RecognizedEntities)
    assert len(result.drugs) == 0
    assert len(result.diseases) == 0
    assert result.context.description == expected_error["context"]["description"]
    assert result.context.raw_data == input_data

def test_invalid_input(entity_recognizer):
    """测试无效输入"""
    input_data = {"description": ""}
    
    with pytest.raises(ValueError):
        entity_recognizer.recognize(input_data)

def test_think_content(entity_recognizer, mock_openai_client):
    """测试think内容的处理"""
    input_data = {"description": "测试think内容"}
    think_content = "这是模型的思考过程"
    response_content = f"<think>{think_content}</think>{{\"drugs\": [], \"diseases\": [], \"context\": {{\"description\": \"测试描述\"}}}}"
    setup_mock_completion(mock_openai_client, response_content)
    
    result = entity_recognizer.recognize(input_data)
    
    assert "think" in result.additional_info
    assert isinstance(result.additional_info["think"], str)
    assert result.additional_info["think"] == think_content
