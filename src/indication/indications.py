"""适应症处理核心逻辑"""

import os
import json
import uuid
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm
from huggingface_hub import InferenceClient
from elasticsearch import Elasticsearch

from src.utils import get_elastic_client, load_env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicationProcessor:
    """适应症处理器 - 包含导出和提取功能"""
    
    def __init__(self, es: Elasticsearch = None, api_key: str = None):
        """初始化处理器
        
        Args:
            es: Elasticsearch客户端实例
            api_key: HuggingFace API key
        """
        self.es = es or get_elastic_client()
        self.drugs_index = 'drugs'
        
        # HuggingFace设置
        load_env()
        self.api_key = api_key or os.getenv('HF_API_KEY')
        if not self.api_key:
            raise ValueError("HF_API_KEY not found")
        
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key
        )
        
        # 处理状态
        self.processed_count = 0
        self.save_interval = 10
        
    def _generate_stable_uuid(self, text: str) -> str:
        """根据文本生成稳定的UUID"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return str(uuid.UUID(text_hash))
    
    def export_raw_indications(self, output_dir: str) -> List[Dict[str, Any]]:
        """从drugs索引中导出所有原始适应症文本
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            List[Dict]: 导出的适应症数据列表
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 获取所有药品的适应症
        query = {
            "size": 10000,
            "_source": ["id", "name", "indications"],
            "query": {
                "exists": {
                    "field": "indications"
                }
            }
        }
        
        try:
            results = self.es.search(index=self.drugs_index, body=query)
            drugs = results['hits']['hits']
            
            # 准备导出数据
            export_data = []
            for drug in tqdm(drugs, desc="导出适应症"):
                drug_data = drug['_source']
                
                # 确保适应症是列表
                indications = drug_data.get('indications', [])
                if isinstance(indications, str):
                    indications = [indications]
                
                # 为每个适应症创建记录
                for indication in indications:
                    if not indication:  # 跳过空值
                        continue
                        
                    export_data.append({
                        'id': self._generate_stable_uuid(indication),
                        'drug_id': drug_data['id'],
                        'drug_name': drug_data['name'],
                        'indication_text': indication,
                        'metadata': {
                            'extraction_time': datetime.now().isoformat(),
                            'confidence': 0.95  # 默认置信度
                        }
                    })
            
            # 保存到文件
            output_file = output_path / f"raw_indications_{datetime.now().strftime('%Y%m%d')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"导出完成: {len(export_data)} 条适应症记录已保存到 {output_file}")
            return export_data
            
        except Exception as e:
            logger.error(f"导出适应症时发生错误: {str(e)}")
            raise
            
    def extract_diseases(self, indications_data: List[Dict], output_dir: str) -> List[Dict]:
        """从适应症文本中提取疾病信息
        
        Args:
            indications_data: 适应症数据列表
            output_dir: 输出目录路径
            
        Returns:
            List[Dict]: 提取的疾病数据列表
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        extracted_data = []
        success_log = []
        failure_log = []
        
        for item in tqdm(indications_data, desc="提取疾病信息"):
            try:
                # 构建提示
                prompt = """请从以下适应症文本中提取疾病信息，包括主要疾病、子疾病和相关疾病。
                适应症文本: """ + item['indication_text'] + """
                
                请用JSON格式返回，包含以下字段:
                - diseases: 疾病列表，每个疾病包含:
                  - name: 疾病名称
                  - type: 疾病类型 (disease)
                  - sub_diseases: 子疾病列表 (可选)
                  - related_diseases: 相关疾病列表 (可选)
                  - confidence_score: 置信度分数
                
                示例:
                {
                  "diseases": [
                    {
                      "name": "高血压",
                      "type": "disease",
                      "sub_diseases": [
                        {"name": "原发性高血压", "type": "disease"}
                      ],
                      "related_diseases": [
                        {"name": "心力衰竭", "type": "disease", "relationship": "complication"}
                      ],
                      "confidence_score": 0.95
                    }
                  ]
                }"""
                
                # 调用模型
                response = self.client.text_generation(
                    prompt,
                    model="Qwen/Qwen-14B-Chat",  # 或其他合适的模型
                    max_new_tokens=1000,
                    temperature=0.1,
                    repetition_penalty=1.1
                )
                
                # 解析响应
                try:
                    result = json.loads(response)
                    # 添加元数据
                    result.update({
                        'id': item['id'],
                        'metadata': {
                            'extraction_time': datetime.now().isoformat(),
                            'confidence': 0.95
                        }
                    })
                    extracted_data.append(result)
                    success_log.append({
                        'id': item['id'],
                        'text': item['indication_text'],
                        'time': datetime.now().isoformat()
                    })
                    
                except json.JSONDecodeError:
                    failure_log.append({
                        'id': item['id'],
                        'text': item['indication_text'],
                        'error': 'Invalid JSON response',
                        'time': datetime.now().isoformat()
                    })
                    continue
                
                # 定期保存
                self.processed_count += 1
                if self.processed_count % self.save_interval == 0:
                    self._save_intermediate_results(
                        output_path, 
                        extracted_data, 
                        success_log, 
                        failure_log
                    )
                    
            except Exception as e:
                failure_log.append({
                    'id': item['id'],
                    'text': item['indication_text'],
                    'error': str(e),
                    'time': datetime.now().isoformat()
                })
                logger.error(f"处理项目 {item['id']} 时发生错误: {str(e)}")
                continue
        
        # 最终保存
        self._save_intermediate_results(
            output_path,
            extracted_data,
            success_log,
            failure_log
        )
        
        return extracted_data
    
    def _save_intermediate_results(
        self,
        output_path: Path,
        extracted_data: List[Dict],
        success_log: List[Dict],
        failure_log: List[Dict]
    ):
        """保存中间结果和日志"""
        # 保存提取结果
        with open(output_path / 'extracted_diseases.json', 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
            
        # 保存成功日志
        with open(output_path / 'success.log', 'w', encoding='utf-8') as f:
            json.dump(success_log, f, ensure_ascii=False, indent=2)
            
        # 保存失败日志
        with open(output_path / 'failure.log', 'w', encoding='utf-8') as f:
            json.dump(failure_log, f, ensure_ascii=False, indent=2)
