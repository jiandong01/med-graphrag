import os
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from tqdm import tqdm
from dotenv import load_dotenv

from .indication_indexer import IndicationIndexer
from .indication_normalizer import IndicationNormalizer
from .indication_extractor import IndicationEntityExtractor
from ..utils import get_elastic_client

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)

class IndicationPipeline:
    """适应症处理管道"""
    
    def __init__(self, output_dir: str):
        """初始化处理管道
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化错误日志
        self.error_log = self.output_dir / 'errors.log'
        self.error_handler = logging.FileHandler(self.error_log)
        self.error_handler.setLevel(logging.ERROR)
        logger.addHandler(self.error_handler)
        
        # 初始化 ES 客户端
        self.es = get_elastic_client()
        
        # 初始化组件
        self.normalizer = IndicationNormalizer()
        self.indexer = IndicationIndexer(es=self.es)
        self.extractor = IndicationEntityExtractor(
            api_key=os.getenv('HF_API_KEY'),
            es_config={
                'hosts': ['http://localhost:9200'],
                'basic_auth': ('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
            }
        )
    
    def fetch_indications(self) -> List[Dict[str, Any]]:
        """从 ES 获取适应症数据
        
        Returns:
            List[Dict[str, Any]]: 适应症数据列表
        """
        try:
            # 从 drugs 索引中获取所有药品数据
            response = self.es.search(
                index='drugs',
                body={
                    'query': {'match_all': {}},
                    '_source': ['id', 'name', 'indications'],
                    'size': 10000  # 根据实际数据量调整
                }
            )
            
            # 组织数据结构
            indications = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                if 'indications' in source and source['indications']:
                    indications.append({
                        'id': source.get('id'),
                        'name': source.get('name'),
                        'indications': source['indications']
                    })
            
            logger.info(f"Retrieved {len(indications)} drugs with indications from Elasticsearch")
            return indications
            
        except Exception as e:
            logger.error(f"Error fetching indications from Elasticsearch: {str(e)}")
            return []
    
    def process_indications(self, indications: List[Dict[str, Any]]) -> Dict[str, int]:
        """处理适应症数据
        
        Args:
            indications: 原始适应症数据列表
            
        Returns:
            Dict[str, int]: 处理统计信息
        """
        stats = {
            'total': len(indications),
            'processed': 0,
            'indexed': 0,
            'errors': 0
        }
        
        # 使用tqdm显示处理进度
        for drug in tqdm(indications, desc="Processing indications"):
            try:
                # 获取适应症列表
                indication_texts = drug.get('indications', [])
                if not indication_texts:
                    logger.warning(f"No indications found for drug: {drug.get('name', 'Unknown')} ({drug.get('id', 'Unknown')})")
                    continue
                
                # 清理和规范化文本
                cleaned_texts = []
                for text in indication_texts:
                    cleaned = self.normalizer.clean_text(text)
                    if cleaned:
                        cleaned_texts.extend(self.normalizer.split_into_sentences(cleaned))
                
                if not cleaned_texts:
                    continue
                
                # 使用 LLM 抽取实体
                try:
                    entities_data = self.extractor.extract_entities(cleaned_texts)
                    if not entities_data:
                        logger.warning(f"No entities extracted for drug: {drug.get('name', 'Unknown')}")
                        continue
                        
                    # 确保返回的是字典格式
                    if not isinstance(entities_data, dict):
                        try:
                            # 尝试解析 JSON 字符串
                            import json
                            entities_data = json.loads(entities_data)
                        except:
                            logger.error(f"Invalid entities data format for drug {drug.get('name', 'Unknown')}")
                            continue
                    
                    # 添加原始文本到元数据
                    if 'metadata' not in entities_data:
                        entities_data['metadata'] = {}
                    entities_data['metadata']['original_text'] = ' '.join(cleaned_texts)
                    
                    # 索引实体
                    index_stats = self.indexer.index_entities(entities_data, drug.get('id'))
                    stats['indexed'] += index_stats['success']
                    stats['errors'] += index_stats['failed']
                    stats['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error extracting entities for drug {drug.get('name', 'Unknown')}: {str(e)}")
                    stats['errors'] += 1
                
            except Exception as e:
                logger.error(f"Error processing drug {drug.get('name', 'Unknown')}: {str(e)}")
                stats['errors'] += 1
        
        return stats

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Process and index indications')
    parser.add_argument('--output-dir', required=True, help='Output directory path')
    parser.add_argument('--clear', action='store_true', help='Clear existing indices before processing')
    args = parser.parse_args()
    
    # 初始化管道
    pipeline = IndicationPipeline(args.output_dir)
    
    # 清理现有索引
    if args.clear:
        logger.info("Clearing existing indices...")
        pipeline.indexer.clear_all_indices()
    
    # 创建索引
    logger.info("Creating indices...")
    pipeline.indexer.create_indices()
    
    # 从 ES 获取适应症数据
    logger.info("Fetching indications from Elasticsearch...")
    indications = pipeline.fetch_indications()
    
    # 处理数据
    logger.info("Processing indications...")
    stats = pipeline.process_indications(indications)
    
    # 输出统计信息
    logger.info("Processing completed:")
    logger.info(f"Total drugs: {stats['total']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Indexed entities: {stats['indexed']}")
    logger.info(f"Errors: {stats['errors']}")
    
    if stats['errors'] > 0:
        logger.info(f"Check {pipeline.error_log} for error details")

if __name__ == '__main__':
    main()
