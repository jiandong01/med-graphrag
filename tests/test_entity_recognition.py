"""实体识别测试"""

import os
import json
import pytest
from app.inference.entity_matcher import EntityRecognizer
from app.inference.models import RecognizedEntities
from app.inference.prompt import create_entity_recognition_prompt
from app.shared import get_es_client, Config

load_env = Config.load_env

# 加载环境变量
load_env()

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r') as f:
        return json.load(f)

@pytest.fixture(scope="module")
def entity_recognizer():
    """创建 EntityRecognizer 实例"""
    es_client = get_es_client()
    return EntityRecognizer(es=es_client)

@pytest.mark.parametrize("input_file,output_file", [
    ('input/entity_recognition_input_1.json', 'output/entity_recognition_output_1.json'),
    ('input/entity_recognition_input_2.json', 'output/entity_recognition_output_2.json'),
])
def test_entity_recognition(entity_recognizer, input_file, output_file, capsys):
    """测试实体识别"""
    input_data = load_test_data(input_file)
    
    print(f"\n原始输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    print(f"\n生成的Prompt:")
    prompt = create_entity_recognition_prompt(input_data)
    print(prompt)
    
    # 获取原始响应
    completion = entity_recognizer.client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": entity_recognizer.site_url,
            "X-Title": entity_recognizer.site_name,
        },
        model=entity_recognizer.model,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    raw_response = completion.choices[0].message.content
    print(f"\n原始LLM响应:\n{raw_response}")
    
    result = entity_recognizer.recognize(input_data)
    
    print(f"\n测试输入文件: {input_file}")
    print("识别结果:")
    print(f"药品: {result.drugs}")
    print(f"疾病: {result.diseases}")
    print(f"上下文: {result.context}")
    print(f"附加信息: {result.additional_info}")
    
    captured = capsys.readouterr()
    print(captured.out)

def test_entity_recognition_error(entity_recognizer, capsys):
    """测试实体识别错误处理"""
    input_data = load_test_data('input/entity_recognition_input_error.json')
    
    print(f"\n原始输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    print(f"\n生成的Prompt:")
    prompt = create_entity_recognition_prompt(input_data)
    print(prompt)
    
    # 获取原始响应
    completion = entity_recognizer.client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": entity_recognizer.site_url,
            "X-Title": entity_recognizer.site_name,
        },
        model=entity_recognizer.model,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    raw_response = completion.choices[0].message.content
    print(f"\n原始LLM响应:\n{raw_response}")
    
    result = entity_recognizer.recognize(input_data)
    
    print("\n测试错误处理:")
    print(f"识别到的药品: {result.drugs}")
    print(f"识别到的疾病: {result.diseases}")
    print(f"上下文: {result.context}")
    print(f"附加信息: {result.additional_info}")
    
    captured = capsys.readouterr()
    print(captured.out)

def test_invalid_input(entity_recognizer, capsys):
    """测试无效输入"""
    input_data = {"description": ""}
    
    print(f"\n原始输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    try:
        entity_recognizer.recognize(input_data)
    except ValueError:
        print("\n测试无效输入: 成功抛出 ValueError")
    
    captured = capsys.readouterr()
    print(captured.out)

def test_think_content(entity_recognizer, capsys):
    """测试think内容的处理"""
    input_data = {"description": "测试think内容"}
    
    print(f"\n原始输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    print(f"\n生成的Prompt:")
    prompt = create_entity_recognition_prompt(input_data)
    print(prompt)
    
    # 获取原始响应
    completion = entity_recognizer.client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": entity_recognizer.site_url,
            "X-Title": entity_recognizer.site_name,
        },
        model=entity_recognizer.model,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    raw_response = completion.choices[0].message.content
    print(f"\n原始LLM响应:\n{raw_response}")
    
    result = entity_recognizer.recognize(input_data)
    
    print("\n测试 think 内容:")
    print(f"Think 内容: {result.additional_info.get('think', '')}")
    
    captured = capsys.readouterr()
    print(captured.out)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
