import os
from elasticsearch import Elasticsearch
from typing import List, Dict, Any
import logging
from datetime import datetime
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IndicationIndexer:
    """适应症索引管理器"""
    
    def __init__(self, es_config: Dict[str, Any]):
        """初始化ES客户端
        
        Args:
            es_config: ES配置信息
        """
        self.es = Elasticsearch(**es_config)
        
    def create_indices(self):
        """创建适应症索引"""
        indication_mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "drug_analyzer",
                        "fields": {
                            "raw": {"type": "keyword"}
                        }
                    },
                    "category": {"type": "keyword"},
                    "normalized_name": {
                        "type": "text",
                        "analyzer": "drug_analyzer",
                        "fields": {
                            "raw": {"type": "keyword"}
                        }
                    },
                    "source_drugs": {
                        "type": "nested",
                        "properties": {
                            "drug_id": {"type": "keyword"},
                            "drug_name": {
                                "type": "text",
                                "fields": {
                                    "raw": {"type": "keyword"}
                                }
                            }
                        }
                    },
                    "entities": {
                        "type": "nested",
                        "properties": {
                            "type": {"type": "keyword"},
                            "name": {
                                "type": "text",
                                "fields": {
                                    "raw": {"type": "keyword"}
                                }
                            },
                            "attributes": {
                                "type": "nested",
                                "properties": {
                                    "key": {"type": "keyword"},
                                    "value": {"type": "keyword"}
                                }
                            }
                        }
                    },
                    "create_time": {"type": "date"},
                    "update_time": {"type": "date"}
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "drug_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"],
                            "char_filter": ["html_strip"]
                        }
                    }
                }
            }
        }
        
        try:
            if not self.es.indices.exists(index='indications'):
                self.es.indices.create(index='indications', body=indication_mapping)
                logger.info("Created indications index")
            else:
                logger.info("Indications index already exists")
        except Exception as e:
            logger.error(f"Error creating indices: {str(e)}")
            raise
    
    def clear_indices(self):
        """清空适应症索引"""
        try:
            if self.es.indices.exists(index='indications'):
                self.es.indices.delete(index='indications')
                logger.info("Deleted indications index")
        except Exception as e:
            logger.error(f"Error clearing indices: {str(e)}")
            raise
    
    def index_indications(self, indications: List[Dict]):
        """索引适应症数据
        
        Args:
            indications: 适应症数据列表
        """
        try:
            for indication in indications:
                # 添加时间戳
                indication['update_time'] = datetime.now().isoformat()
                if 'create_time' not in indication:
                    indication['create_time'] = indication['update_time']
                
                # 索引文档
                self.es.index(
                    index='indications',
                    id=indication['id'],
                    body=indication
                )
            
            logger.info(f"Indexed {len(indications)} indications")
        except Exception as e:
            logger.error(f"Error indexing indications: {str(e)}")
            raise
    
    def search_indications(self, query: str, fields: List[str] = None) -> List[Dict]:
        """搜索适应症
        
        Args:
            query: 搜索查询
            fields: 搜索字段列表
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        if fields is None:
            fields = ['name^2', 'normalized_name', 'entities.name']
            
        try:
            response = self.es.search(
                index='indications',
                body={
                    'query': {
                        'multi_match': {
                            'query': query,
                            'fields': fields
                        }
                    }
                }
            )
            
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception as e:
            logger.error(f"Error searching indications: {str(e)}")
            raise

def main():
    """Main function to manage indication indices"""
    parser = argparse.ArgumentParser(description='Manage indication indices')
    parser.add_argument('--clear', action='store_true', help='Clear existing indices before processing')
    args = parser.parse_args()
    
    # Initialize indexer
    indexer = IndicationIndexer(
        es_config={
            'hosts': ['http://localhost:9200'],
            'basic_auth': ('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
        }
    )
    
    if args.clear:
        logger.info("Clearing existing indices...")
        indexer.clear_indices()
    
    logger.info("Creating indices...")
    indexer.create_indices()

if __name__ == "__main__":
    main()
