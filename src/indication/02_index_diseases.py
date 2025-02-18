"""索引疾病数据"""

import json
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.indication.disease_indexer import DiseaseIndexer

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='索引疾病数据到Elasticsearch')
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='src/indication/data',
        help='包含疾病JSON数据的目录路径'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='是否清除现有索引'
    )
    
    parser.add_argument(
        '--examples',
        type=int,
        default=1,
        help='显示示例数量'
    )
    
    return parser.parse_args()

def main():
    # 解析参数
    args = parse_args()
    
    # 确保数据目录存在
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")
    
    # 加载环境变量
    load_dotenv()
    
    # ES配置
    es_config = {
        "hosts": [f"{os.getenv('ELASTIC_HOST')}"],
        "basic_auth": (
            os.getenv("ELASTIC_USERNAME"),
            os.getenv("ELASTIC_PASSWORD")
        )
    }
    
    # 初始化索引器
    indexer = DiseaseIndexer(es_config)
    
    # 创建索引
    indexer.create_indices(clear_existing=args.clear)
    
    # 处理数据
    diseases = indexer.process_diseases(str(data_dir))
    
    # 打印一些示例疾病文档
    print("\n处理后的疾病文档示例:")
    for disease in diseases[:args.examples]:
        print("\n" + "="*50)
        print(json.dumps(disease, ensure_ascii=False, indent=2))
    
    # 索引数据
    indexer.index_diseases(diseases)
    
    # 进行一些示例搜索
    print("\n搜索示例:")
    
    # 1. 搜索特定疾病
    query = "咽炎"
    results = indexer.search_diseases(query)
    print(f"\n搜索 '{query}' 的结果:")
    for result in results[:args.examples]:
        print("\n" + "-"*50)
        print(json.dumps({
            "name": result["name"],
            "confidence_score": result["confidence_score"],
            "mention_count": result["mention_count"],
            "related_diseases": result["related_diseases"],
            "sources": result["sources"][:2]  # 只显示前两个来源
        }, ensure_ascii=False, indent=2))
    
    # 2. 搜索带有相关疾病的疾病
    query = "肺炎"
    results = indexer.search_diseases(query)
    print(f"\n搜索 '{query}' 的结果:")
    for result in results[:args.examples]:
        print("\n" + "-"*50)
        print(json.dumps({
            "name": result["name"],
            "confidence_score": result["confidence_score"],
            "mention_count": result["mention_count"],
            "related_diseases": result["related_diseases"],
            "sources": result["sources"][:2]
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
