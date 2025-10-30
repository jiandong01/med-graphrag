"""从disease_extraction的JSON结果更新ES的indications_list字段"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shared import get_es_client, load_env

load_env()

def extract_all_disease_names(diseases: List[Dict]) -> Set[str]:
    """递归提取所有疾病名称（包括sub_diseases）
    
    Args:
        diseases: 疾病列表
        
    Returns:
        疾病名称集合
    """
    disease_names = set()
    
    for disease in diseases:
        if 'name' in disease and disease['name']:
            disease_names.add(disease['name'])
        
        # 递归处理sub_diseases
        if 'sub_diseases' in disease and disease['sub_diseases']:
            sub_names = extract_all_disease_names(disease['sub_diseases'])
            disease_names.update(sub_names)
    
    return disease_names

def load_all_extractions(json_dir: str) -> Dict[str, Set[str]]:
    """加载所有JSON文件，按drug_id聚合疾病列表
    
    Args:
        json_dir: JSON文件目录
        
    Returns:
        Dict[drug_id, Set[disease_names]]
    """
    json_path = Path(json_dir)
    batch_files = sorted(json_path.glob("batch_*.json"))
    
    print(f"找到 {len(batch_files)} 个批次文件")
    
    # 按drug_id聚合疾病
    drug_diseases = defaultdict(set)
    
    for batch_file in tqdm(batch_files, desc="读取JSON文件"):
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            extractions = batch_data.get('extractions', [])
            
            for extraction in extractions:
                drug_id = extraction.get('drug_id')
                diseases = extraction.get('diseases', [])
                
                if drug_id and diseases:
                    disease_names = extract_all_disease_names(diseases)
                    drug_diseases[drug_id].update(disease_names)
        
        except Exception as e:
            print(f"处理文件 {batch_file} 时出错: {str(e)}")
            continue
    
    print(f"\n总共处理了 {len(drug_diseases)} 个药品")
    return drug_diseases

def update_es_batch(es, drug_diseases: Dict[str, Set[str]], batch_size: int = 100):
    """批量更新ES的indications_list字段
    
    Args:
        es: ES客户端
        drug_diseases: 药品疾病映射
        batch_size: 批次大小
    """
    from elasticsearch.helpers import bulk
    
    print(f"\n开始更新ES...")
    
    # 准备批量更新操作
    actions = []
    for drug_id, disease_set in tqdm(drug_diseases.items(), desc="准备更新操作"):
        disease_list = sorted(list(disease_set))  # 转为列表并排序
        
        actions.append({
            '_op_type': 'update',
            '_index': 'drugs',
            '_id': drug_id,
            'doc': {
                'indications_list': disease_list
            },
            'doc_as_upsert': False
        })
        
        # 每batch_size个执行一次
        if len(actions) >= batch_size:
            success, failed = bulk(es, actions, raise_on_error=False)
            print(f"  批次更新: 成功 {success}, 失败 {len(failed)}")
            actions = []
    
    # 更新剩余的
    if actions:
        success, failed = bulk(es, actions, raise_on_error=False)
        print(f"  最后批次: 成功 {success}, 失败 {len(failed)}")
    
    print("\n✓ ES更新完成！")

def update_sample_drugs(drug_names: List[str] = None):
    """更新指定的样例药品
    
    Args:
        drug_names: 药品名称列表，如果为None则使用默认测试药品
    """
    if drug_names is None:
        drug_names = ["氢化可的松", "阿莫西林", "美托洛尔"]
    
    es = get_es_client()
    json_dir = "data/processed/diseases/diseases_search_after"
    
    # 加载所有提取结果
    drug_diseases = load_all_extractions(json_dir)
    
    print(f"\n查找并更新指定药品...")
    
    for drug_name in drug_names:
        # 查询药品
        result = es.search(
            index="drugs",
            body={
                "query": {"match": {"name": drug_name}},
                "size": 10  # 可能有多个同名药品
            }
        )
        
        if not result['hits']['hits']:
            print(f"\n未找到药品: {drug_name}")
            continue
        
        print(f"\n药品: {drug_name}")
        print(f"找到 {len(result['hits']['hits'])} 个匹配")
        
        for hit in result['hits']['hits']:
            drug_id = hit['_id']
            drug_source = hit['_source']
            
            if drug_id in drug_diseases:
                disease_list = sorted(list(drug_diseases[drug_id]))
                
                # 更新ES
                es.update(
                    index="drugs",
                    id=drug_id,
                    body={
                        "doc": {
                            "indications_list": disease_list
                        }
                    }
                )
                
                print(f"  ✓ {drug_source['name']} (ID: {drug_id})")
                print(f"    疾病数: {len(disease_list)}")
                print(f"    疾病列表: {disease_list[:5]}{'...' if len(disease_list) > 5 else ''}")
            else:
                print(f"  ✗ {drug_source['name']} (ID: {drug_id}) - 未找到提取结果")

def update_all_drugs():
    """更新所有药品"""
    es = get_es_client()
    json_dir = "data/processed/diseases/diseases_search_after"
    
    # 加载所有提取结果
    drug_diseases = load_all_extractions(json_dir)
    
    # 批量更新ES
    update_es_batch(es, drug_diseases)

def show_stats():
    """显示统计信息"""
    json_dir = "data/processed/diseases/diseases_search_after"
    drug_diseases = load_all_extractions(json_dir)
    
    print(f"\n统计信息:")
    print(f"  总药品数: {len(drug_diseases)}")
    
    # 统计疾病数量分布
    disease_counts = [len(diseases) for diseases in drug_diseases.values()]
    if disease_counts:
        print(f"  平均每个药品的疾病数: {sum(disease_counts)/len(disease_counts):.1f}")
        print(f"  最多疾病数: {max(disease_counts)}")
        print(f"  最少疾病数: {min(disease_counts)}")

def verify_updates(drug_names: List[str] = None):
    """验证更新结果"""
    if drug_names is None:
        drug_names = ["氢化可的松", "阿莫西林", "美托洛尔"]
    
    es = get_es_client()
    
    print("=" * 80)
    print("验证更新结果")
    print("=" * 80)
    
    for drug_name in drug_names:
        result = es.search(
            index="drugs",
            body={
                "query": {"match": {"name": drug_name}},
                "size": 1
            }
        )
        
        if result['hits']['hits']:
            drug = result['hits']['hits'][0]['_source']
            indications_list = drug.get('indications_list', [])
            
            print(f"\n药品: {drug['name']}")
            print(f"indications_list数量: {len(indications_list) if indications_list else 0}")
            if indications_list:
                print(f"前5个疾病: {indications_list[:5]}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='从JSON结果更新indications_list')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--update-samples', action='store_true', help='更新样例药品')
    parser.add_argument('--update-all', action='store_true', help='更新所有药品')
    parser.add_argument('--verify', action='store_true', help='验证更新结果')
    parser.add_argument('--drugs', nargs='+', help='指定药品名称')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.update_samples:
        update_sample_drugs(args.drugs)
    elif args.update_all:
        confirm = input("确认要更新所有药品吗? (yes/no): ")
        if confirm.lower() == 'yes':
            update_all_drugs()
        else:
            print("取消操作")
    elif args.verify:
        verify_updates(args.drugs)
    else:
        print("请指定操作:")
        print("  --stats          显示统计信息")
        print("  --update-samples 更新样例药品")
        print("  --update-all     更新所有药品")
        print("  --verify         验证更新结果")
        print("\n示例:")
        print("  python scripts/update_indications_list_from_json.py --stats")
        print("  python scripts/update_indications_list_from_json.py --update-samples")
        print("  python scripts/update_indications_list_from_json.py --update-samples --drugs 氢化可的松 阿莫西林")
