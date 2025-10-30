"""从适应症文本中提取疾病列表的测试脚本"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
from openai import OpenAI

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shared import get_es_client, load_env

load_env()

# 初始化DeepSeek客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def extract_diseases_from_indications(indications: List[str]) -> List[str]:
    """使用LLM从适应症列表中提取疾病名称
    
    Args:
        indications: 适应症文本列表
        
    Returns:
        疾病名称列表
    """
    if not indications:
        return []
    
    prompt = f"""请从以下药品适应症描述中，提取所有提到的疾病名称。

适应症列表：
{json.dumps(indications, ensure_ascii=False, indent=2)}

要求：
1. 只提取疾病名称，不要包含描述性文字
2. 每个疾病名称应该是一个独立的医学术语
3. 去除重复的疾病
4. 返回JSON格式的疾病列表

返回格式：
{{"diseases": ["疾病1", "疾病2", ...]}}

示例：
输入：["主要用于治疗肾上腺皮质功能减退症的替代治疗及先天性肾上腺皮质增生症"]
输出：{{"diseases": ["肾上腺皮质功能减退症", "先天性肾上腺皮质增生症"]}}
"""
    
    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的医学文本分析助手，擅长从医学文本中提取疾病实体。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        response = completion.choices[0].message.content
        
        # 解析响应
        # 尝试提取JSON部分
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group(0))
            return result.get("diseases", [])
        else:
            print(f"无法解析响应: {response}")
            return []
            
    except Exception as e:
        print(f"提取疾病时发生错误: {str(e)}")
        return []

def test_extraction():
    """测试疾病提取功能"""
    
    # 连接ES
    es = get_es_client()
    
    # 获取几个测试样例
    test_drugs = [
        "氢化可的松",
        "阿莫西林",
        "美托洛尔"
    ]
    
    print("=" * 80)
    print("测试疾病提取功能")
    print("=" * 80)
    
    for drug_name in test_drugs:
        # 查询药品
        result = es.search(
            index="drugs",
            body={
                "query": {"match": {"name": drug_name}},
                "size": 1
            }
        )
        
        if not result['hits']['hits']:
            print(f"\n未找到药品: {drug_name}")
            continue
        
        drug = result['hits']['hits'][0]['_source']
        indications = drug.get('indications', [])
        
        print(f"\n药品: {drug['name']}")
        print(f"ID: {drug['id']}")
        print(f"\n原始适应症:")
        for i, indication in enumerate(indications, 1):
            print(f"  {i}. {indication}")
        
        # 提取疾病
        print(f"\n提取疾病列表...")
        diseases = extract_diseases_from_indications(indications)
        
        print(f"\n提取结果:")
        for i, disease in enumerate(diseases, 1):
            print(f"  {i}. {disease}")
        
        print("\n" + "-" * 80)

def update_sample_drugs():
    """更新少量药品的indications_list字段"""
    
    es = get_es_client()
    
    # 选择几个测试药品
    test_drug_names = [
        "氢化可的松",
        "阿莫西林", 
        "美托洛尔"
    ]
    
    print("=" * 80)
    print("更新样例药品的indications_list")
    print("=" * 80)
    
    for drug_name in test_drug_names:
        # 查询药品
        result = es.search(
            index="drugs",
            body={
                "query": {"match": {"name": drug_name}},
                "size": 1
            }
        )
        
        if not result['hits']['hits']:
            print(f"\n未找到药品: {drug_name}")
            continue
        
        hit = result['hits']['hits'][0]
        drug = hit['_source']
        drug_id = hit['_id']
        indications = drug.get('indications', [])
        
        print(f"\n处理: {drug['name']} (ID: {drug_id})")
        
        # 提取疾病
        diseases = extract_diseases_from_indications(indications)
        print(f"提取到 {len(diseases)} 个疾病")
        
        # 更新ES
        es.update(
            index="drugs",
            id=drug_id,
            body={
                "doc": {
                    "indications_list": diseases
                }
            }
        )
        print(f"✓ 已更新indications_list字段")
    
    print("\n" + "=" * 80)
    print("更新完成！")

def verify_updates():
    """验证更新结果"""
    
    es = get_es_client()
    
    print("=" * 80)
    print("验证更新结果")
    print("=" * 80)
    
    test_drug_names = ["氢化可的松", "阿莫西林", "美托洛尔"]
    
    for drug_name in test_drug_names:
        result = es.search(
            index="drugs",
            body={
                "query": {"match": {"name": drug_name}},
                "size": 1
            }
        )
        
        if result['hits']['hits']:
            drug = result['hits']['hits'][0]['_source']
            print(f"\n药品: {drug['name']}")
            print(f"indications_list: {drug.get('indications_list', '无')}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='从适应症中提取疾病列表')
    parser.add_argument('--test', action='store_true', help='测试提取功能')
    parser.add_argument('--update', action='store_true', help='更新样例药品')
    parser.add_argument('--verify', action='store_true', help='验证更新结果')
    
    args = parser.parse_args()
    
    if args.test:
        test_extraction()
    elif args.update:
        update_sample_drugs()
    elif args.verify:
        verify_updates()
    else:
        print("请指定操作: --test, --update, 或 --verify")
        print("示例: python scripts/extract_indications_diseases.py --test")
