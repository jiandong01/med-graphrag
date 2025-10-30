"""分析JSON提取结果中的drug_id在ES中的匹配情况"""

import os
import sys
import json
from pathlib import Path
from typing import Set, Dict, List
from collections import defaultdict
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shared import get_es_client, load_env

load_env()

def extract_drug_ids_from_json(json_dir: str) -> Dict[str, Dict]:
    """从JSON文件中提取所有drug_id及其相关信息
    
    Returns:
        Dict[drug_id, {name, extraction_count}]
    """
    json_path = Path(json_dir)
    batch_files = sorted(json_path.glob("batch_*.json"))
    
    print(f"找到 {len(batch_files)} 个批次文件")
    
    drug_info = defaultdict(lambda: {"names": set(), "extraction_count": 0})
    
    for batch_file in tqdm(batch_files, desc="读取JSON文件"):
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            extractions = batch_data.get('extractions', [])
            
            for extraction in extractions:
                drug_id = extraction.get('drug_id')
                drug_name = extraction.get('drug_name')
                
                if drug_id:
                    drug_info[drug_id]['names'].add(drug_name)
                    drug_info[drug_id]['extraction_count'] += 1
        
        except Exception as e:
            print(f"处理文件 {batch_file} 时出错: {str(e)}")
            continue
    
    # 转换set为list
    for drug_id in drug_info:
        drug_info[drug_id]['names'] = list(drug_info[drug_id]['names'])
    
    return dict(drug_info)

def check_ids_in_es(es, drug_ids: Set[str], batch_size: int = 100) -> Dict[str, bool]:
    """批量检查drug_id在ES中是否存在
    
    Returns:
        Dict[drug_id, exists]
    """
    results = {}
    drug_id_list = list(drug_ids)
    
    print(f"\n检查 {len(drug_id_list)} 个drug_id在ES中的存在情况...")
    
    for i in tqdm(range(0, len(drug_id_list), batch_size), desc="批量查询ES"):
        batch_ids = drug_id_list[i:i+batch_size]
        
        # 使用mget批量查询
        try:
            response = es.mget(
                index='drugs',
                body={'ids': batch_ids},
                _source=False
            )
            
            for doc in response['docs']:
                doc_id = doc['_id']
                results[doc_id] = doc['found']
        
        except Exception as e:
            print(f"批量查询出错: {str(e)}")
            # 降级为单个查询
            for drug_id in batch_ids:
                try:
                    exists = es.exists(index='drugs', id=drug_id)
                    results[drug_id] = exists
                except:
                    results[drug_id] = False
    
    return results

def check_names_in_es(es, drug_names: Set[str]) -> Dict[str, int]:
    """检查drug_name在ES中的匹配数量
    
    Returns:
        Dict[drug_name, match_count]
    """
    results = {}
    
    print(f"\n检查 {len(drug_names)} 个药品名称在ES中的匹配情况...")
    
    for drug_name in tqdm(drug_names, desc="按名称查询"):
        try:
            response = es.count(
                index='drugs',
                body={
                    "query": {"match": {"name": drug_name}}
                }
            )
            results[drug_name] = response['count']
        except Exception as e:
            results[drug_name] = 0
    
    return results

def generate_report(drug_info: Dict, id_matching: Dict, name_matching: Dict):
    """生成详细报告"""
    
    print("\n" + "=" * 80)
    print("匹配分析报告")
    print("=" * 80)
    
    # 统计基本信息
    total_drugs = len(drug_info)
    total_extractions = sum(info['extraction_count'] for info in drug_info.values())
    
    print(f"\n【基本信息】")
    print(f"  JSON中的唯一drug_id数: {total_drugs}")
    print(f"  总提取记录数: {total_extractions}")
    
    # ID匹配统计
    matched_ids = sum(1 for exists in id_matching.values() if exists)
    unmatched_ids = total_drugs - matched_ids
    match_rate = (matched_ids / total_drugs * 100) if total_drugs > 0 else 0
    
    print(f"\n【ID匹配情况】")
    print(f"  ES中存在的ID: {matched_ids} ({match_rate:.2f}%)")
    print(f"  ES中不存在的ID: {unmatched_ids} ({100-match_rate:.2f}%)")
    
    # 名称匹配统计
    all_names = set()
    for info in drug_info.values():
        all_names.update(info['names'])
    
    names_with_matches = sum(1 for count in name_matching.values() if count > 0)
    names_without_matches = len(name_matching) - names_with_matches
    
    print(f"\n【名称匹配情况】")
    print(f"  唯一药品名称数: {len(all_names)}")
    print(f"  能在ES中找到的名称: {names_with_matches}")
    print(f"  ES中找不到的名称: {names_without_matches}")
    
    # 详细统计
    total_name_matches = sum(name_matching.values())
    avg_matches_per_name = total_name_matches / len(name_matching) if name_matching else 0
    
    print(f"  ES中总匹配记录数: {total_name_matches}")
    print(f"  平均每个名称匹配数: {avg_matches_per_name:.1f}")
    
    # 分析不匹配的药品
    print(f"\n【不匹配药品分析】")
    
    unmatched_drugs = []
    for drug_id, info in drug_info.items():
        if not id_matching.get(drug_id, False):
            # 检查名称是否能匹配
            name_match_counts = [name_matching.get(name, 0) for name in info['names']]
            total_name_matches = sum(name_match_counts)
            
            unmatched_drugs.append({
                'drug_id': drug_id,
                'names': info['names'],
                'extraction_count': info['extraction_count'],
                'name_matches': total_name_matches
            })
    
    # 按提取次数排序
    unmatched_drugs.sort(key=lambda x: x['extraction_count'], reverse=True)
    
    # 统计有多少不匹配的ID但名称能匹配上
    name_recoverable = sum(1 for d in unmatched_drugs if d['name_matches'] > 0)
    
    if unmatched_ids > 0:
        print(f"  ID不匹配但名称可匹配: {name_recoverable} ({name_recoverable/unmatched_ids*100:.1f}%)")
        print(f"  ID和名称都不匹配: {unmatched_ids - name_recoverable}")
    else:
        print(f"  ✅ 所有ID都能在ES中匹配！")
    
    # 展示前10个高频不匹配药品
    print(f"\n【前10个高频不匹配药品】")
    for i, drug in enumerate(unmatched_drugs[:10], 1):
        print(f"\n  {i}. {', '.join(drug['names'])}")
        print(f"     ID: {drug['drug_id']}")
        print(f"     提取次数: {drug['extraction_count']}")
        print(f"     名称在ES中的匹配数: {drug['name_matches']}")
    
    # 结论
    print(f"\n" + "=" * 80)
    print("【结论】")
    print("=" * 80)
    
    if match_rate > 90:
        print("✅ ID匹配率很高，可以直接使用ID更新")
    elif match_rate > 50:
        print("⚠️  ID匹配率中等，建议结合名称匹配")
    else:
        print("❌ ID匹配率低，建议使用名称匹配策略")
    
    if name_recoverable > unmatched_ids * 0.8:
        print("✅ 大部分不匹配ID可以通过名称恢复")
        print("💡 建议：修改更新脚本，使用名称匹配策略")
    else:
        print("⚠️  很多药品名称也无法匹配，可能是不同的数据来源")
    
    return {
        'total_drugs': total_drugs,
        'matched_ids': matched_ids,
        'unmatched_ids': unmatched_ids,
        'match_rate': match_rate,
        'name_recoverable': name_recoverable,
        'unmatched_drugs': unmatched_drugs
    }

def save_detailed_report(report_data: Dict, output_file: str = "data/cache/drug_id_matching_report.json"):
    """保存详细报告"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到: {output_file}")

def main():
    es = get_es_client()
    json_dir = "data/processed/diseases/diseases_search_after"
    
    # 1. 提取drug_id
    drug_info = extract_drug_ids_from_json(json_dir)
    
    # 2. 检查ID匹配
    drug_ids = set(drug_info.keys())
    id_matching = check_ids_in_es(es, drug_ids)
    
    # 3. 检查名称匹配
    all_names = set()
    for info in drug_info.values():
        all_names.update(info['names'])
    name_matching = check_names_in_es(es, all_names)
    
    # 4. 生成报告
    report_data = generate_report(drug_info, id_matching, name_matching)
    
    # 5. 保存详细数据
    detailed_data = {
        'drug_info': {k: dict(v) for k, v in drug_info.items()},
        'id_matching': id_matching,
        'name_matching': name_matching,
        'summary': {
            'total_drugs': report_data['total_drugs'],
            'matched_ids': report_data['matched_ids'],
            'unmatched_ids': report_data['unmatched_ids'],
            'match_rate': report_data['match_rate'],
            'name_recoverable': report_data['name_recoverable']
        }
    }
    save_detailed_report(detailed_data)

if __name__ == "__main__":
    main()
