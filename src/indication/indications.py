"""适应症处理核心逻辑"""

import os
import json
import uuid
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm
from openai import OpenAI
from elasticsearch import Elasticsearch

from src.utils import get_elastic_client, setup_logging, load_env, load_config, ensure_directories

logger = setup_logging(__name__)

# Load environment variables
load_env()

class IndicationProcessor:
    """适应症处理器 - 包含导出和提取功能"""
    
    def __init__(self, es: Elasticsearch = None):
        """初始化处理器
        
        Args:
            es: Elasticsearch客户端实例
        """
        self.es = es or get_elastic_client()
        self.drugs_index = 'drugs'
        
        # OpenAI/OpenRouter设置
        load_env()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = "deepseek/deepseek-r1-distill-qwen-32b"
        self.site_url = os.getenv("SITE_URL", "http://localhost:3000")
        self.site_name = os.getenv("SITE_NAME", "Medical GraphRAG")
        
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
                prompt = f"""请从以下适应症文本中提取疾病信息，包括主要疾病、子疾病和相关疾病。
                适应症文本: {item['indication_text']}
                
                请用JSON格式返回，包含以下字段:
                - diseases: 疾病列表，每个疾病包含:
                  - name: 疾病名称
                  - type: 疾病类型 (disease)
                  - sub_diseases: 子疾病列表 (可选)
                  - related_diseases: 相关疾病列表 (可选)
                  - confidence_score: 置信度分数
                
                示例:
                {{
                  "diseases": [
                    {{
                      "name": "高血压",
                      "type": "disease",
                      "sub_diseases": [
                        {{"name": "原发性高血压", "type": "disease"}}
                      ],
                      "related_diseases": [
                        {{"name": "心力衰竭", "type": "disease", "relationship": "complication"}}
                      ],
                      "confidence_score": 0.95
                    }}
                  ]
                }}"""
                
                # 调用模型
                completion = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": self.site_url,
                        "X-Title": self.site_name,
                    },
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that extracts disease information from medical indications."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                response = completion.choices[0].message.content
                
                # 解析响应
                think_content, json_str = self._extract_json_from_response(response)
                try:
                    result = json.loads(json_str)
                    # 添加元数据
                    result.update({
                        'id': item['id'],
                        'metadata': {
                            'extraction_time': datetime.now().isoformat(),
                            'confidence': 0.95,
                            'think': think_content or ""  # 确保think内容始终是字符串
                        }
                    })
                    extracted_data.append(result)
                    success_log.append({
                        'id': item['id'],
                        'text': item['indication_text'],
                        'time': datetime.now().isoformat()
                    })
                    
                except json.JSONDecodeError as e:
                    failure_log.append({
                        'id': item['id'],
                        'text': item['indication_text'],
                        'error': f'Invalid JSON response: {str(e)}',
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
