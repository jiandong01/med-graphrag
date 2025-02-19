"""实体识别模块"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from huggingface_hub import InferenceClient
from elasticsearch import Elasticsearch

from src.utils import get_elastic_client, load_env
from .models import Case, RecognizedEntities, Drug, Disease, Context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EntityRecognizer:
    """实体识别器 - 识别输入中的药品和疾病实体并与数据库对齐"""
    
    def __init__(self, es: Elasticsearch = None, api_key: str = None):
        """初始化识别器
        
        Args:
            es: Elasticsearch客户端实例
            api_key: HuggingFace API key
        """
        # Elasticsearch设置
        self.es = es or get_elastic_client()
        self.drugs_index = 'drugs'
        self.diseases_index = 'diseases'
        
        # HuggingFace设置
        load_env()
        self.api_key = api_key or os.getenv('HF_API_KEY')
        if not self.api_key:
            raise ValueError("HF_API_KEY not found")
        
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key
        )
    
    def _search_drug(self, name: str) -> Optional[Dict]:
        """在ES中搜索药品
        
        Args:
            name: 药品名称
            
        Returns:
            Optional[Dict]: 匹配的药品信息
        """
        try:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"name": name}},
                            {"match": {"details.content": name}}
                        ]
                    }
                }
            }
            result = self.es.search(index=self.drugs_index, body=query)
            hits = result['hits']['hits']
            if hits:
                return hits[0]['_source']
            return None
        except Exception as e:
            logger.error(f"搜索药品时发生错误: {str(e)}")
            raise
    
    def _search_disease(self, name: str) -> Optional[Dict]:
        """在ES中搜索疾病
        
        Args:
            name: 疾病名称
            
        Returns:
            Optional[Dict]: 匹配的疾病信息
        """
        try:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"name": name}},
                            {"match": {"sub_diseases.name": name}},
                            {"match": {"related_diseases.name": name}}
                        ]
                    }
                }
            }
            result = self.es.search(index=self.diseases_index, body=query)
            hits = result['hits']['hits']
            if hits:
                return hits[0]['_source']
            return None
        except Exception as e:
            logger.error(f"搜索疾病时发生错误: {str(e)}")
            raise
    
    def recognize(self, input_data: Dict[str, Any]) -> RecognizedEntities:
        """识别输入数据中的实体并与数据库对齐
        
        Args:
            input_data: 输入数据，包含病例描述等信息
            
        Returns:
            RecognizedEntities: 识别出的实体
        """
        try:
            # 1. 使用LLM进行初步实体识别
            prompt_template = """请从以下医疗记录中识别药品和疾病实体。

医疗记录：
{{medical_record}}

请以JSON格式返回识别结果，包含以下字段：
{{
    "drug": {{
        "name": "药品名称"
    }},
    "disease": {{
        "name": "疾病名称"
    }},
    "context": {{
        "description": "相关描述",
        "additional_info": {{}}
    }}
}}"""
            
            prompt = prompt_template.format(
                medical_record=json.dumps(input_data, ensure_ascii=False)
            )

            # 调用模型
            response = self.client.text_generation(
                prompt,
                model="Qwen/Qwen-14B-Chat",
                max_new_tokens=1000,
                temperature=0.1,
                repetition_penalty=1.1
            )
            
            # 解析响应
            initial_entities = json.loads(response)
            
            # 2. 在数据库中查找匹配的标准实体
            # 药品匹配
            drug_info = self._search_drug(initial_entities['drug']['name'])
            if not drug_info:
                raise ValueError(f"未找到匹配的药品: {initial_entities['drug']['name']}")
            
            drug = Drug(
                id=drug_info['id'],
                name=drug_info['name'],
                standard_name=drug_info['name']  # 使用药品名称作为标准名称
            )
            
            # 疾病匹配
            disease_info = self._search_disease(initial_entities['disease']['name'])
            if not disease_info:
                raise ValueError(f"未找到匹配的疾病: {initial_entities['disease']['name']}")
            
            # 对于疾病，我们尝试从不同来源获取标准名称
            standard_name = None
            if disease_info.get('standard_name'):
                standard_name = disease_info['standard_name']
            elif disease_info.get('parent_disease', {}).get('name'):
                standard_name = disease_info['parent_disease']['name']
            else:
                # 如果没有明确的标准名称，使用最基本的疾病名称
                # 例如："继发性肺动脉高压" -> "肺动脉高压"
                standard_name = disease_info['name'].replace('继发性', '').replace('原发性', '').strip()
            
            disease = Disease(
                id=disease_info['id'],
                name=disease_info['name'],
                standard_name=standard_name
            )
            
            # 构建上下文
            context = Context(
                description=initial_entities['context']['description'],
                additional_info=initial_entities['context'].get('additional_info', {})
            )
            
            # 3. 返回标准化的实体
            return RecognizedEntities(
                drug=drug,
                disease=disease,
                context=context
            )
                
        except Exception as e:
            logger.error(f"识别实体时发生错误: {str(e)}")
            raise
