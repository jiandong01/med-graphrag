"""疾病索引处理器"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm

from src.indication.disease_mapping import get_disease_mapping


class DiseaseIndexer:
    """疾病索引处理器"""
    
    def __init__(self, es_config: Dict[str, Any]):
        """初始化
        
        Args:
            es_config: Elasticsearch配置
        """
        self.es_config = es_config
        self.es_client = Elasticsearch(**es_config)
        self.logger = logging.getLogger(__name__)
        
        # 设置ES传输日志级别为WARNING，减少输出
        logging.getLogger('elastic_transport.transport').setLevel(logging.WARNING)
    
    def create_indices(self, clear_existing: bool = False) -> None:
        """创建或更新索引
        
        Args:
            clear_existing: 是否清除已存在的索引
        """
        index_name = "diseases"
        
        try:
            # 如果需要清除已存在的索引
            if clear_existing and self.es_client.indices.exists(index=index_name):
                self.es_client.indices.delete(index=index_name)
                self.logger.info(f"已删除索引: {index_name}")
            
            # 创建新索引
            if not self.es_client.indices.exists(index=index_name):
                self.es_client.indices.create(
                    index=index_name,
                    body=get_disease_mapping(),
                    request_timeout=300
                )
                self.logger.info(f"已创建索引: {index_name}")
            
        except Exception as e:
            self.logger.error(f"创建索引时发生错误: {str(e)}")
            raise
    
    def process_diseases(self, data_dir: str) -> List[Dict[str, Any]]:
        """处理疾病数据
        
        Args:
            data_dir: 数据目录路径
            
        Returns:
            List[Dict[str, Any]]: 处理后的疾病文档列表
        """
        self.logger.info("开始处理疾病数据...")
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
                            
                            # 添加来源信息
                            if drug_id and extraction_time:
                                processed_diseases[disease_name]['sources'].append({
                                    'drug_id': drug_id,
                                    'extraction_time': extraction_time,
                                    'confidence': confidence
                                })
                
                except Exception as e:
                    self.logger.error(f"处理文件 {json_file} 时发生错误: {str(e)}")
            
            # 转换为列表
            diseases_list = list(processed_diseases.values())
            
            self.logger.info("疾病处理完成:")
            self.logger.info(f"- 总疾病数: {len(diseases_list)}")
            
            return diseases_list
            
        except Exception as e:
            self.logger.error(f"处理疾病数据时发生错误: {str(e)}")
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
        self.logger.info("开始索引疾病数据...")
        
        try:
            # 准备批量索引的操作
            actions = []
            for disease in diseases:
                action = {
                    "_index": "diseases",
                    "_id": disease['id'],
                    "_source": disease
                }
                actions.append(action)
            
            # 执行批量索引
            success, failed = bulk(
                self.es_client,
                actions,
                chunk_size=batch_size,
                request_timeout=300,
                refresh=False  # 禁用实时刷新以提高性能
            )
            
            self.logger.info("索引完成:")
            self.logger.info(f"- 成功: {success} 个文档")
            if failed:
                self.logger.warning(f"- 失败: {len(failed)} 个文档")
            
        except Exception as e:
            self.logger.error(f"索引疾病数据时发生错误: {str(e)}")
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
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "sub_diseases.name^2", "related_diseases.name"],
                        "type": "best_fields",
                        "tie_breaker": 0.3
                    }
                },
                "sort": [
                    "_score",
                    {"mention_count": "desc"},
                    {"confidence_score": "desc"}
                ]
            }
            
            # 执行搜索
            response = self.es_client.search(
                index="diseases",
                body=search_body,
                size=size
            )
            
            # 处理结果
            hits = response['hits']['hits']
            results = []
            for hit in hits:
                result = hit['_source']
                result['score'] = hit['_score']
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"搜索疾病时发生错误: {str(e)}")
            raise
