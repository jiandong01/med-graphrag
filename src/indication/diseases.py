"""疾病索引管理"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm

from src.utils import get_elastic_client, setup_logging, load_env
from src.indication.es_mappings import DISEASE_MAPPING

logger = setup_logging(__name__)

# Load environment variables
load_env()

class DiseaseManager:
    """疾病管理器 - 处理疾病数据的索引和查询"""
    
    def __init__(self, es: Elasticsearch = None):
        """初始化
        
        Args:
            es: Elasticsearch客户端实例
        """
        self.es = es or get_elastic_client()
        self.index_name = "diseases"
    
    def create_index(self, clear_existing: bool = False) -> None:
        """创建或更新疾病索引
        
        Args:
            clear_existing: 是否清除已存在的索引
        """
        try:
            # 如果需要清除已存在的索引
            if clear_existing and self.es.indices.exists(index=self.index_name):
                self.es.indices.delete(index=self.index_name)
                logger.info(f"已删除索引: {self.index_name}")
            
            # 创建新索引
            if not self.es.indices.exists(index=self.index_name):
                self.es.indices.create(
                    index=self.index_name,
                    body=DISEASE_MAPPING,
                    request_timeout=300
                )
                logger.info(f"已创建索引: {self.index_name}")
            
        except Exception as e:
            logger.error(f"创建索引时发生错误: {str(e)}")
            raise
    
    def process_diseases(self, data_dir: str) -> List[Dict[str, Any]]:
        """处理疾病数据
        
        Args:
            data_dir: 数据目录路径
            
        Returns:
            List[Dict[str, Any]]: 处理后的疾病文档列表
        """
        logger.info("开始处理疾病数据...")
        processed_diseases = {}  # 用于去重和合并相同疾病的信息
        
        try:
            # 遍历数据目录下的所有JSON文件
            data_path = Path(data_dir)
            for json_file in tqdm(list(data_path.glob("*.json")), desc="处理疾病数据"):
                try:
                    # 读取JSON文件
                    with open(json_file, 'r', encoding='utf-8') as f:
                        extractions = json.load(f)
                    
                    # 处理每个提取结果
                    for extraction in extractions:
                        drug_id = extraction.get('id')
                        extraction_time = extraction.get('metadata', {}).get('extraction_time')
                        confidence = extraction.get('metadata', {}).get('confidence')
                        
                        # 处理疾病列表
                        for disease in extraction.get('diseases', []):
                            disease_name = disease.get('name')
                            if not disease_name:
                                continue
                            
                            # 使用疾病名称作为键进行去重和合并
                            if disease_name not in processed_diseases:
                                # 新疾病
                                processed_diseases[disease_name] = {
                                    'id': f"disease_{len(processed_diseases) + 1}",
                                    'name': disease_name,
                                    'type': disease.get('type', 'disease'),
                                    'sub_diseases': disease.get('sub_diseases', []),
                                    'related_diseases': disease.get('related_diseases', []),
                                    'confidence_score': disease.get('confidence_score', 0.0),
                                    'sources': [],
                                    'first_seen': extraction_time,
                                    'last_updated': extraction_time,
                                    'mention_count': 1
                                }
                            else:
                                # 更新已存在的疾病信息
                                existing = processed_diseases[disease_name]
                                existing['mention_count'] += 1
                                
                                # 更新时间
                                if extraction_time:
                                    if extraction_time < existing['first_seen']:
                                        existing['first_seen'] = extraction_time
                                    if extraction_time > existing['last_updated']:
                                        existing['last_updated'] = extraction_time
                                
                                # 合并子疾病和相关疾病
                                self._merge_disease_lists(existing['sub_diseases'], 
                                                       disease.get('sub_diseases', []))
                                self._merge_disease_lists(existing['related_diseases'], 
                                                       disease.get('related_diseases', []))
                                
                                # 更新置信度分数（取最高值）
                                if disease.get('confidence_score', 0.0) > existing['confidence_score']:
                                    existing['confidence_score'] = disease['confidence_score']
                            
                            # 添加来源信息（去重）
                            if drug_id and extraction_time:
                                # 检查是否已存在相同的 drug_id
                                source_exists = False
                                for source in processed_diseases[disease_name]['sources']:
                                    if source['drug_id'] == drug_id:
                                        source_exists = True
                                        # 如果现有source的时间更早，则更新为新的时间和置信度
                                        if extraction_time > source['extraction_time']:
                                            source['extraction_time'] = extraction_time
                                            source['confidence'] = confidence
                                        break
                                
                                # 如果不存在相同的drug_id，则添加新的source
                                if not source_exists:
                                    processed_diseases[disease_name]['sources'].append({
                                        'drug_id': drug_id,
                                        'extraction_time': extraction_time,
                                        'confidence': confidence
                                    })
                
                except Exception as e:
                    logger.error(f"处理文件 {json_file} 时发生错误: {str(e)}")
            
            # 转换为列表
            diseases_list = list(processed_diseases.values())
            
            logger.info("疾病处理完成:")
            logger.info(f"- 总疾病数: {len(diseases_list)}")
            
            return diseases_list
            
        except Exception as e:
            logger.error(f"处理疾病数据时发生错误: {str(e)}")
            raise
    
    def _merge_disease_lists(self, existing_list: List[Dict], new_list: List[Dict]) -> None:
        """合并疾病列表，去重并保留最新信息
        
        Args:
            existing_list: 现有的疾病列表
            new_list: 新的疾病列表
        """
        # 使用疾病名称作为键进行去重
        existing_names = {d['name']: d for d in existing_list}
        
        for new_disease in new_list:
            name = new_disease['name']
            if name not in existing_names:
                existing_list.append(new_disease)
            else:
                # 可以在这里添加更新逻辑，如合并属性等
                pass
    
    def index_diseases(self, diseases: List[Dict[str, Any]], batch_size: int = 100) -> None:
        """索引疾病数据
        
        Args:
            diseases: 疾病文档列表
            batch_size: 批量索引大小
        """
        logger.info("开始索引疾病数据...")
        
        try:
            # 准备批量索引的操作
            actions = []
            for disease in diseases:
                action = {
                    "_index": self.index_name,
                    "_id": disease['id'],
                    "_source": disease
                }
                actions.append(action)
            
            # 执行批量索引
            success, failed = bulk(
                self.es,
                actions,
                chunk_size=batch_size,
                request_timeout=300,
                refresh=True  # 立即刷新以便搜索
            )
            
            logger.info("索引完成:")
            logger.info(f"- 成功: {success} 个文档")
            if failed:
                logger.warning(f"- 失败: {len(failed)} 个文档")
            
        except Exception as e:
            logger.error(f"索引疾病数据时发生错误: {str(e)}")
            raise
    
    def search_diseases(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """搜索疾病
        
        Args:
            query: 搜索查询
            size: 返回结果数量
            
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            # 构建搜索查询
            search_body = {
                "size": size,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "sub_diseases.name^2", "related_diseases.name"],
                        "type": "best_fields",
                        "operator": "and"
                    }
                },
                "sort": [
                    {"confidence_score": {"order": "desc"}},
                    {"mention_count": {"order": "desc"}}
                ]
            }
            
            # 执行搜索
            results = self.es.search(
                index=self.index_name,
                body=search_body
            )
            
            # 提取结果
            hits = results['hits']['hits']
            diseases = [hit['_source'] for hit in hits]
            
            return diseases
            
        except Exception as e:
            logger.error(f"搜索疾病时发生错误: {str(e)}")
            raise
