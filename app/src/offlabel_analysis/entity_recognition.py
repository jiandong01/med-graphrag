"""实体识别模块"""

import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
from elasticsearch import Elasticsearch

from app.src.utils import get_elastic_client, load_env
from .models import (
    RecognizedEntities, RecognizedDrug as Drug, 
    RecognizedDisease as Disease, Context, 
    DrugMatch, DiseaseMatch
)
from .prompt import create_entity_recognition_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EntityRecognizer:
    """实体识别器 - 识别输入中的药品和疾病实体并与数据库对齐"""
    
    def __init__(self, es: Elasticsearch = None):
        """初始化识别器
        
        Args:
            es: Elasticsearch客户端实例
        """
        # Elasticsearch设置
        self.es = es or get_elastic_client()
        self.drugs_index = 'drugs'
        self.diseases_index = 'diseases'
        
        # OpenAI/OpenRouter设置
        load_env()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = "deepseek/deepseek-r1-distill-qwen-32b"
        self.site_url = os.getenv("SITE_URL", "http://localhost:3000")
        self.site_name = os.getenv("SITE_NAME", "Medical GraphRAG")
    
    def _clean_json_string(self, json_str: str) -> str:
        """清理JSON字符串，移除无效字符
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            str: 清理后的JSON字符串
        """
        # 移除控制字符，但保留换行和空格
        json_str = ''.join(char for char in json_str if char >= ' ' or char in ['\n', '\r', '\t'])
        
        # 尝试修复常见的JSON格式问题
        json_str = json_str.replace('\n', ' ')  # 将换行符替换为空格
        json_str = json_str.replace('\r', ' ')  # 将回车符替换为空格
        json_str = re.sub(r'\s+', ' ', json_str)  # 将多个空白字符替换为单个空格
        
        return json_str.strip()
    
    def _extract_json_from_response(self, response: str) -> Tuple[Optional[str], str]:
        """从响应中提取JSON内容和think内容
        
        Args:
            response: LLM的原始响应文本
            
        Returns:
            tuple[Optional[str], str]: (think内容, JSON内容)
        """
        # 提取think内容
        think_content = None
        if "<think>" in response and "</think>" in response:
            start = response.find("<think>") + len("<think>")
            end = response.find("</think>")
            think_content = response[start:end].strip()
            response = response[end + len("</think>"):].strip()
        
        # 提取JSON内容
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response.strip()
        
        # 清理JSON字符串
        return think_content, self._clean_json_string(json_str)
    
    def _search_drug(self, name: str, unique: bool = False) -> List[Dict]:
        """在ES中搜索药品
        
        Args:
            name: 药品名称
            unique: 是否只返回唯一结果
            
        Returns:
            List[Dict]: 匹配的药品信息列表
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
                },
                "size": 1 if unique else 5
            }
            result = self.es.search(index=self.drugs_index, body=query)
            hits = result['hits']['hits']
            return [
                {
                    'id': hit['_source'].get('id', ''),
                    'name': hit['_source'].get('name', ''),
                    '_score': hit.get('_score', 0)
                }
                for hit in hits
            ]
        except Exception as e:
            logger.error(f"搜索药品时发生错误: {str(e)}")
            raise
    
    def _search_disease(self, name: str, unique: bool = False) -> List[Dict]:
        """在ES中搜索疾病
        
        Args:
            name: 疾病名称
            unique: 是否只返回唯一结果
            
        Returns:
            List[Dict]: 匹配的疾病信息列表
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
                },
                "size": 1 if unique else 5
            }
            result = self.es.search(index=self.diseases_index, body=query)
            hits = result['hits']['hits']
            return [
                {
                    'id': hit['_source'].get('id', ''),
                    'name': hit['_source'].get('name', ''),
                    '_score': hit.get('_score', 0)
                }
                for hit in hits
            ]
        except Exception as e:
            logger.error(f"搜索疾病时发生错误: {str(e)}")
            raise
    
    def recognize(self, input_data: Dict[str, Any], unique_results: bool = True) -> RecognizedEntities:
        """识别输入数据中的实体并与数据库对齐
        
        Args:
            input_data: 输入数据，包含病例描述等信息
            unique_results: 是否只返回唯一的匹配结果
            
        Returns:
            RecognizedEntities: 识别出的实体
        """
        try:
            # 输入验证
            if not input_data.get("description"):
                raise ValueError("输入数据必须包含非空的description字段")

            # 1. 使用LLM进行初步实体识别
            prompt = create_entity_recognition_prompt(input_data)
            
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response = completion.choices[0].message.content
            
            # 解析响应
            think_content, json_str = self._extract_json_from_response(response)
            try:
                initial_entities = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}")
                logger.error(f"JSON字符串: {json_str}")
                raise
            
            # 2. 在数据库中查找匹配的标准实体
            drugs = []
            for drug_entity in initial_entities.get('drugs', []):
                drug_matches = self._search_drug(drug_entity['name'], unique_results)
                if drug_matches:  # 只有在找到匹配时才添加
                    drug = Drug(
                        name=drug_entity['name'],
                        matches=[
                            DrugMatch(
                                id=match['id'],
                                standard_name=match['name'],
                                score=match['_score']
                            )
                            for match in drug_matches
                        ]
                    )
                    drugs.append(drug)
            
            diseases = []
            for disease_entity in initial_entities.get('diseases', []):
                disease_matches = self._search_disease(disease_entity['name'], unique_results)
                if disease_matches:  # 只有在找到匹配时才添加
                    disease = Disease(
                        name=disease_entity['name'],
                        matches=[
                            DiseaseMatch(
                                id=match['id'],
                                standard_name=match['name'],
                                score=match['_score']
                            )
                            for match in disease_matches
                        ]
                    )
                    diseases.append(disease)
            
            # 构建上下文
            context = Context(
                description=initial_entities['context']['description'],
                raw_data=input_data
            )
            
            # 3. 返回标准化的实体
            return RecognizedEntities(
                drugs=drugs,
                diseases=diseases,
                context=context,
                additional_info={"think": think_content or ""}  # 确保think内容始终是字符串
            )
                
        except Exception as e:
            logger.error(f"识别实体时发生错误: {str(e)}")
            raise
