import logging
from typing import Dict, List, Any
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import hashlib
import argparse
import os

logger = logging.getLogger(__name__)

class IndicationIndexer:
    """适应症索引器"""
    
    def __init__(self, es: Elasticsearch):
        """初始化索引器
        
        Args:
            es: Elasticsearch 客户端实例
        """
        self.es = es
        self.index_name = 'indications'
    
    def create_indices(self):
        """创建或更新索引映射"""
        logger.info("Creating indication index...")
        
        # 定义索引映射
        mappings = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},  # 实体ID
                    "text": {  # 实体文本
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "type": {"type": "keyword"},  # 实体类型
                    "medical_system": {"type": "keyword"},  # 医学体系
                    "standard_name": {  # 标准化名称
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "raw": {"type": "keyword"}
                        }
                    },
                    "attributes": {  # 属性
                        "properties": {
                            "pathogen": {"type": "keyword"},  # 病原体
                            "body_part": {"type": "keyword"}  # 相关部位
                        }
                    },
                    "relations": {  # 关系
                        "properties": {
                            "head": {"type": "keyword"},
                            "tail": {"type": "keyword"},
                            "type": {"type": "keyword"},
                            "evidence_level": {"type": "keyword"},
                            "source": {"type": "keyword"}
                        }
                    },
                    "drug_ids": {"type": "keyword"},  # 关联的药品ID
                    "metadata": {  # 元数据
                        "properties": {
                            "original_text": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "processing_notes": {"type": "text"},
                            "confidence_score": {"type": "float"}
                        }
                    },
                    "create_time": {"type": "date"}
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "text_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop"
                            ]
                        }
                    }
                }
            }
        }
        
        # 如果索引存在则删除
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)
        
        # 创建新索引
        self.es.indices.create(index=self.index_name, body=mappings)
        logger.info(f"Created index: {self.index_name}")
    
    def clear_all_indices(self):
        """清除所有相关索引"""
        logger.info("Clearing all indices...")
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)
            logger.info(f"Deleted index: {self.index_name}")
    
    def generate_entity_id(self, text: str, type: str) -> str:
        """生成实体ID
        
        Args:
            text: 实体文本
            type: 实体类型
            
        Returns:
            str: 实体ID
        """
        content = f"{text}_{type}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def index_entities(self, entities_data: Dict[str, Any], drug_id: str) -> Dict[str, int]:
        """索引实体数据
        
        Args:
            entities_data: LLM 返回的实体数据，包含 entities 和 metadata
            drug_id: 药品ID
            
        Returns:
            Dict[str, int]: 索引统计信息
        """
        stats = {'success': 0, 'failed': 0}
        
        # 确保数据格式正确
        if not isinstance(entities_data, dict):
            logger.error(f"Invalid entities data format: {type(entities_data)}")
            return stats
            
        entities = entities_data.get('entities', [])
        if not isinstance(entities, list):
            logger.error(f"Invalid entities format: {type(entities)}")
            return stats
        
        def generate_actions():
            """生成批量索引操作"""
            for entity in entities:
                try:
                    # 生成实体ID
                    entity_id = self.generate_entity_id(
                        entity.get('text', ''),
                        entity.get('type', 'unknown')
                    )
                    
                    # 检查实体是否已存在
                    try:
                        existing = self.es.get(index=self.index_name, id=entity_id)
                        # 如果存在，更新drug_ids
                        doc = existing['_source']
                        if 'drug_ids' not in doc:
                            doc['drug_ids'] = []
                        if drug_id not in doc['drug_ids']:
                            doc['drug_ids'].append(drug_id)
                        yield {
                            '_index': self.index_name,
                            '_id': entity_id,
                            '_op_type': 'index',
                            '_source': doc
                        }
                    except:
                        # 如果不存在，创建新文档
                        doc = {
                            'id': entity_id,
                            'text': entity.get('text', ''),
                            'type': entity.get('type', 'unknown'),
                            'medical_system': entity.get('medical_system', 'unknown'),
                            'standard_name': entity.get('standard_name', ''),
                            'attributes': entity.get('attributes', {}),
                            'drug_ids': [drug_id],
                            'metadata': entities_data.get('metadata', {})
                        }
                        yield {
                            '_index': self.index_name,
                            '_id': entity_id,
                            '_op_type': 'index',
                            '_source': doc
                        }
                except Exception as e:
                    logger.error(f"Error generating action for entity: {str(e)}")
                    stats['failed'] += 1
        
        try:
            # 执行批量索引
            success, failed = bulk(
                self.es,
                generate_actions(),
                stats_only=True,
                raise_on_error=False
            )
            
            stats['success'] = success
            stats['failed'] = failed
            
        except Exception as e:
            logger.error(f"Error during bulk indexing: {str(e)}")
            stats['failed'] += len(entities)
        
        return stats

def main():
    """Main function to manage indication indices"""
    parser = argparse.ArgumentParser(description='Manage indication indices')
    parser.add_argument('--clear', action='store_true', help='Clear existing indices before processing')
    args = parser.parse_args()
    
    # Initialize indexer
    indexer = IndicationIndexer(
        es=Elasticsearch(
            hosts=['http://localhost:9200'],
            basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
        )
    )
    
    if args.clear:
        logger.info("Clearing existing indices...")
        indexer.clear_all_indices()
    
    logger.info("Creating indices...")
    indexer.create_indices()

if __name__ == "__main__":
    main()
