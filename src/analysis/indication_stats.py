import os
import logging
import argparse
from elasticsearch import Elasticsearch
from pathlib import Path
import csv
from collections import Counter
from normalizers.indication_normalizer import IndicationNormalizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_indication_stats(es: Elasticsearch, index: str = 'drugs') -> dict:
    """获取适应症字段的统计信息
    
    Args:
        es: Elasticsearch客户端
        index: 索引名称
        
    Returns:
        dict: 统计结果
    """
    # 使用 terms aggregation 统计适应症
    query = {
        "size": 0,  # 我们只需要聚合结果
        "aggs": {
            "indication_counts": {
                "terms": {
                    "field": "indications.raw",
                    "size": 10000  # 获取足够多的唯一值
                }
            }
        }
    }
    
    try:
        response = es.search(index=index, body=query)
        buckets = response['aggregations']['indication_counts']['buckets']
        
        # 使用规范化器处理适应症
        normalizer = IndicationNormalizer()
        indication_counts = Counter()
        original_to_std = {}  # 原始名称到标准名称的映射
        
        # 处理每个适应症
        for bucket in buckets:
            original_text = bucket['key']
            count = bucket['doc_count']
            
            # 标准化名称
            std_name = normalizer.standardize_name(original_text)
            if std_name:  # 忽略空字符串
                indication_counts[std_name] += count
                if std_name not in original_to_std:
                    original_to_std[std_name] = set()
                original_to_std[std_name].add(original_text)
        
        # 获取类别信息
        categories = {}
        for name in indication_counts:
            categories[name] = normalizer.get_category(name)
        
        # 计算类别统计
        category_stats = Counter()
        for name, count in indication_counts.items():
            category_stats[categories[name]] += count
        
        total_mentions = sum(indication_counts.values())
        
        return {
            'statistics': {
                'total_mentions': total_mentions,
                'unique_mentions': len(indication_counts),
                'top_categories': [
                    {
                        'category': cat,
                        'count': count,
                        'percentage': round(count / total_mentions * 100, 2)
                    }
                    for cat, count in category_stats.most_common()
                ]
            },
            'counts': {
                name: {
                    'count': count,
                    'category': categories[name],
                    'original_names': list(original_to_std[name])
                }
                for name, count in indication_counts.most_common()
            }
        }
    except Exception as e:
        logger.error(f"Error getting indication stats: {str(e)}")
        raise

def export_stats(stats: dict, output_file: str):
    """导出统计结果到CSV文件
    
    Args:
        stats: 统计结果
        output_file: 输出文件路径
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # 写入头部
        writer.writerow(['标准名称', '频次', '类别', '原始名称'])
        
        # 写入数据
        for name, info in stats['counts'].items():
            writer.writerow([
                name,
                info['count'],
                info['category'],
                '|'.join(info['original_names'])
            ])
        
        # 写入统计摘要
        writer.writerow([])
        writer.writerow(['统计摘要'])
        writer.writerow(['总提及次数', stats['statistics']['total_mentions']])
        writer.writerow(['唯一适应症数', stats['statistics']['unique_mentions']])
        writer.writerow([])
        
        # 写入类别统计
        writer.writerow(['疾病类别统计'])
        writer.writerow(['类别', '数量', '占比(%)'])
        for cat_info in stats['statistics']['top_categories']:
            writer.writerow([
                cat_info['category'],
                cat_info['count'],
                cat_info['percentage']
            ])

def print_stats(stats: dict, top_n: int = None):
    """打印统计结果
    
    Args:
        stats: 统计结果
        top_n: 显示前N个结果
    """
    print("\n=== 适应症统计摘要 ===")
    print(f"总提及次数: {stats['statistics']['total_mentions']}")
    print(f"唯一适应症数: {stats['statistics']['unique_mentions']}")
    
    print("\n=== 疾病类别统计 ===")
    for cat_info in stats['statistics']['top_categories']:
        print(f"{cat_info['category']}: {cat_info['count']} ({cat_info['percentage']}%)")
    
    print("\n=== 适应症频次统计 ===")
    for i, (name, info) in enumerate(stats['counts'].items(), 1):
        if top_n and i > top_n:
            break
        
        print(f"\n{i}. {name}")
        print(f"   频次: {info['count']}")
        print(f"   类别: {info['category']}")
        if len(info['original_names']) > 1:  # 只在有不同的原始名称时显示
            print("   原始名称:")
            for orig in info['original_names']:
                if orig != name:
                    print(f"    - {orig}")

def main():
    parser = argparse.ArgumentParser(description='统计ES中的适应症字段')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--top-n', type=int, default=10, help='显示前N个结果')
    parser.add_argument('--export', type=str, help='导出统计结果到CSV文件')
    parser.add_argument('--index', type=str, default='drugs', help='ES索引名称')
    args = parser.parse_args()
    
    # 初始化ES客户端
    es = Elasticsearch(
        hosts=['http://localhost:9200'],
        basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
    )
    
    try:
        # 获取统计信息
        stats = get_indication_stats(es, args.index)
        
        # 显示统计信息
        if args.stats:
            print_stats(stats, args.top_n)
        
        # 导出到CSV
        if args.export:
            export_stats(stats, args.export)
            logger.info(f"Statistics exported to {args.export}")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == '__main__':
    main()
