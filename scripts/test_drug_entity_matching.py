#!/usr/bin/env python3
"""
测试药品实体匹配 - 处理前100条ATC标准药品

用途：验证匹配方案可行性
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict
from elasticsearch import Elasticsearch

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_atc_drugs(atc_file: str, limit: int = 100):
    """加载ATC药品编码数据（前N条）"""
    df = pd.read_csv(atc_file, nrows=limit)
    
    # 按通用名去重
    entity_mapping = {}
    for _, row in df.iterrows():
        generic_name = str(row['西药药品名称']).strip()
        
        if pd.notna(generic_name) and generic_name and generic_name not in entity_mapping:
            entity_mapping[generic_name] = {
                'entity_id': row['西药药品代码'],
                'generic_name': generic_name,
                'atc_domestic': {
                    'atc1': row['ATC1'],
                    'atc1_name': row['ATC1名称'],
                    'atc2': row['ATC2'],
                    'atc2_name': row['ATC2名称'],
                    'atc3': row['ATC3'],
                    'atc3_name': row['ATC3名称'],
                    'drug_class': row['药品分类'],
                    'drug_class_name': row['药品分类名称']
                }
            }
    
    print(f"加载ATC数据: {len(entity_mapping)}个通用名")
    return entity_mapping


def match_drugs_in_es(generic_name: str, es: Elasticsearch) -> list:
    """用通用名在ES中查询匹配的药品（精确过滤中药）⭐"""
    try:
        query = {
            "query": {
                "bool": {
                    "must": [
                        # 匹配药品名称
                        {"match_phrase": {"name": generic_name}},
                        # 只要西药：parent_id = "1"
                        {
                            "nested": {
                                "path": "category_hierarchy",
                                "query": {
                                    "term": {
                                        "category_hierarchy.parent_id": "1                               "
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "size": 100
        }
        
        result = es.search(index='drugs', body=query)
        return [hit['_source'] for hit in result['hits']['hits']]
    except Exception as e:
        print(f"查询失败 [{generic_name}]: {e}")
        return []


def create_entities(entity_mapping: dict, es: Elasticsearch):
    """创建药物实体"""
    entities = []
    matched_count = 0
    unmatched_entities = []
    
    for generic_name, base_info in entity_mapping.items():
        print(f"匹配: {generic_name}...", end=' ')
        
        # 在ES中查询
        drugs = match_drugs_in_es(generic_name, es)
        
        if drugs:
            print(f"✅ 找到 {len(drugs)} 个制剂")
            matched_count += 1
            
            entity = {
                'entity_id': base_info['entity_id'],
                'generic_name': generic_name,
                'atc_domestic': base_info['atc_domestic'],
                'formulations': [
                    {
                        'formulation_id': d['id'],
                        'name': d['name'],
                        'spec': d.get('spec', ''),
                        'indications_list': d.get('indications_list', []),
                        'contraindications': d.get('contraindications', [])
                    }
                    for d in drugs
                ],
                'formulation_count': len(drugs)
            }
            
            entities.append(entity)
        else:
            print(f"❌ 未找到")
            unmatched_entities.append(generic_name)
    
    print(f"\n匹配结果: {matched_count}/{len(entity_mapping)} ({matched_count/len(entity_mapping)*100:.1f}%)")
    
    return entities, unmatched_entities


def main():
    """主函数"""
    # 配置
    atc_file = 'data/raw/drugs/ATC药品编码-2022.csv'
    output_dir = 'data/raw/drugs/test_results'
    
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 连接ES
    es = Elasticsearch(
        [os.getenv('ELASTIC_HOST', 'http://localhost:9200')],
        basic_auth=(
            os.getenv('ELASTIC_USERNAME', 'elastic'),
            os.getenv('ELASTIC_PASSWORD', 'changeme')
        )
    )
    
    print("="*80)
    print("测试药品实体匹配 - 前100条")
    print("="*80)
    
    # 1. 加载ATC数据（前100条）
    print("\n1. 加载ATC数据...")
    entity_mapping = load_atc_drugs(atc_file, limit=100)
    
    # 2. 匹配ES药品
    print("\n2. 匹配ES药品...")
    entities, unmatched = create_entities(entity_mapping, es)
    
    # 3. 保存结果
    print("\n3. 保存结果...")
    
    # 保存匹配的实体
    entities_file = f'{output_dir}/matched_entities_top100.json'
    with open(entities_file, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 实体保存到: {entities_file}")
    
    # 保存未匹配的通用名
    unmatched_file = f'{output_dir}/unmatched_entities_top100.json'
    with open(unmatched_file, 'w', encoding='utf-8') as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 未匹配保存到: {unmatched_file}")
    
    # 4. 生成统计报告
    print("\n4. 统计报告:")
    total_formulations = sum(e['formulation_count'] for e in entities)
    print(f"   - ATC实体数: {len(entity_mapping)}")
    print(f"   - 匹配成功: {len(entities)}")
    print(f"   - 未匹配: {len(unmatched)}")
    print(f"   - 匹配率: {len(entities)/len(entity_mapping)*100:.1f}%")
    print(f"   - 总制剂数: {total_formulations}")
    print(f"   - 平均制剂数/实体: {total_formulations/len(entities):.1f}" if entities else "")
    
    # 保存统计
    stats = {
        'atc_entities': len(entity_mapping),
        'matched_entities': len(entities),
        'unmatched_entities': len(unmatched),
        'match_rate': f"{len(entities)/len(entity_mapping)*100:.1f}%",
        'total_formulations': total_formulations,
        'avg_formulations_per_entity': f"{total_formulations/len(entities):.1f}" if entities else "0"
    }
    
    stats_file = f'{output_dir}/statistics_top100.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 统计保存到: {stats_file}")
    
    print("\n" + "="*80)
    print("测试完成!")
    print("="*80)


if __name__ == '__main__':
    main()
