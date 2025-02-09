from huggingface_hub import InferenceClient
import json
import logging
import argparse
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IndicationEntityExtractor:
    def __init__(self, api_key: str, es_config: Dict):
        """初始化实体抽取器和ES客户端"""
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=api_key
        )
        self.es = Elasticsearch(**es_config)
        
    def create_extraction_prompt(self, text: str) -> list:
        """创建实体抽取的prompt"""
        # 限制文本长度，避免超出模型上下文窗口
        max_text_length = 4000  # 根据模型的具体限制调整
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
            logger.warning(f"Text was truncated to {max_text_length} characters")
            
        system_message = {
            "role": "system",
            "content": """你是一个医学文本分析专家。请从医药说明书中抽取适应症相关实体，直接输出JSON格式，不要包含任何其他内容。
JSON格式如下：
{
    "entities": [
        {
            "id": "e1",
            "text": "疾病名称",
            "type": "disease",
            "medical_system": "western或tcm",
            "standard_name": "标准化名称",
            "attributes": {
                "pathogen": "病原体（如果有）",
                "body_part": "相关部位（如果有）"
            }
        }
    ],
    "relations": [
        {
            "head": "源疾病",
            "tail": "目标疾病",
            "type": "关系类型",
            "evidence_level": "A/B/C",
            "source": "说明书"
        }
    ],
    "metadata": {
        "original_text": "原始文本",
        "processing_notes": "处理说明",
        "confidence_score": 0.95
    }
}"""
        }
        
        user_message = {
            "role": "user",
            "content": f"请从以下医药说明书文本中抽取适应症相关实体，直接输出JSON格式：\n\n{text}"
        }
        
        return [system_message, user_message]

    def extract_entities(self, text: str) -> Optional[Dict]:
        """调用API进行实体抽取"""
        try:
            messages = self.create_extraction_prompt(text)
            logger.info(f"Sending request to API with text length: {len(text)}")
            logger.debug(f"Request messages: {json.dumps(messages, ensure_ascii=False)}")
            
            completion = self.client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                messages=messages,
                max_tokens=4000,
                temperature=0.1
            )
            
            logger.info("Received response from API")
            response_content = completion.choices[0].message.content
            logger.debug(f"Raw API response: {response_content}")
            
            # 尝试从响应中提取 JSON
            try:
                # 首先尝试直接解析
                try:
                    result = json.loads(response_content)
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试查找 JSON 部分
                    json_start = response_content.find('{')
                    json_end = response_content.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_content = response_content[json_start:json_end]
                        result = json.loads(json_content)
                    else:
                        raise ValueError("No valid JSON found in response")
                
                # 验证结果格式
                if not isinstance(result, dict) or 'entities' not in result:
                    raise ValueError("Invalid result format: missing required fields")
                
                result['metadata']['extraction_time'] = datetime.now().isoformat()
                return result
                
            except Exception as je:
                logger.error(f"Failed to parse API response: {str(je)}")
                logger.error(f"Response content: {response_content}")
                return None
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"API response status: {e.response.status_code}")
                logger.error(f"API response content: {e.response.text}")
            return None

    def fetch_drugs_with_indications(self, batch_size: int = 100) -> List[Dict]:
        """从ES中获取带有适应症的药品"""
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "exists": {
                                "field": "indications"
                            }
                        },
                        {
                            "nested": {
                                "path": "details",
                                "query": {
                                    "bool": {
                                        "must": [
                                            {
                                                "term": {
                                                    "details.tag": "适应症"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "_source": ["id", "name", "indications", "details", "approval_number"]
        }
        
        drugs = []
        try:
            response = self.es.search(
                index="drugs",
                body=query,
                size=batch_size
            )
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                # 首先检查顶层的 indications 字段
                indications_content = source.get('indications')
                
                # 如果顶层没有，则从 details 中查找
                if not indications_content and 'details' in source:
                    for detail in source['details']:
                        if isinstance(detail, dict) and detail.get('tag') == '适应症':
                            indications_content = detail.get('content')
                            break
                
                # 获取批准文号，现在是顶层字段
                approval_number = source.get('approval_number')
                
                # 如果顶层没有批准文号，从 details 中查找（兼容旧数据）
                if not approval_number and 'details' in source:
                    for detail in source['details']:
                        if isinstance(detail, dict) and detail.get('tag') == '批准文号':
                            approval_number = detail.get('content')
                            break
                
                if indications_content:
                    drugs.append({
                        'id': source['id'],
                        'name': source['name'],
                        'indications': indications_content,
                        'approval_number': approval_number
                    })
            
            logger.info(f"Found {len(drugs)} drugs with indications")
            return drugs
            
        except Exception as e:
            logger.error(f"Error fetching drugs: {str(e)}")
            return []

    def create_indices(self):
        """创建适应症实体索引"""
        indication_entities_index = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "entity_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop",
                                "trim"
                            ]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "drug_id": {"type": "keyword"},
                    "drug_name": {
                        "type": "text",
                        "analyzer": "entity_analyzer",
                        "fields": {
                            "raw": {"type": "keyword"}
                        }
                    },
                    "approval_number": {"type": "keyword"},
                    "entities": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "text": {
                                "type": "text",
                                "analyzer": "entity_analyzer",
                                "fields": {
                                    "raw": {"type": "keyword"}
                                }
                            },
                            "type": {"type": "keyword"},
                            "medical_system": {"type": "keyword"},
                            "standard_name": {
                                "type": "text",
                                "analyzer": "entity_analyzer",
                                "fields": {
                                    "raw": {"type": "keyword"}
                                }
                            },
                            "attributes": {
                                "properties": {
                                    "pathogen": {"type": "keyword"},
                                    "body_part": {"type": "keyword"}
                                }
                            }
                        }
                    },
                    "relations": {
                        "type": "nested",
                        "properties": {
                            "head": {"type": "keyword"},
                            "tail": {"type": "keyword"},
                            "type": {"type": "keyword"},
                            "evidence_level": {"type": "keyword"},
                            "source": {"type": "keyword"}
                        }
                    },
                    "metadata": {
                        "properties": {
                            "original_text": {"type": "text"},
                            "processing_notes": {"type": "text"},
                            "confidence_score": {"type": "float"},
                            "extraction_time": {"type": "date"}
                        }
                    }
                }
            }
        }
        
        try:
            if self.es.indices.exists(index="indication_entities"):
                self.es.indices.delete(index="indication_entities")
            
            self.es.indices.create(
                index="indication_entities",
                body=indication_entities_index
            )
            logger.info("Created 'indication_entities' index")
            
        except Exception as e:
            logger.error(f"Error creating indices: {str(e)}")

    def clear_indices(self):
        """清空适应症实体索引"""
        try:
            if self.es.indices.exists(index="indication_entities"):
                self.es.indices.delete(index="indication_entities")
                logger.info("Cleared 'indication_entities' index.")
        except Exception as e:
            logger.error(f"Error clearing indices: {str(e)}")
            raise

    def store_entities(self, drug_id: str, drug_name: str, entities: Dict):
        """存储抽取的实体到新的索引中"""
        try:
            doc = {
                "drug_id": drug_id,
                "drug_name": drug_name,
                "entities": entities
            }
            self.es.index(index="indication_entities", document=doc)
        except Exception as e:
            logger.error(f"Failed to store entities for drug {drug_id}: {str(e)}")

    def process_batch(self, output_dir: str = "outputs", clear_existing: bool = False):
        """批量处理ES中的适应症并保存结果"""
        Path(output_dir).mkdir(exist_ok=True)
        
        # 如果需要，清空现有索引
        if clear_existing:
            logger.info("Clearing existing indices...")
            self.clear_indices()
        
        # 创建新的索引
        self.create_indices()
        
        # 获取所有带有适应症的药品
        drugs = self.fetch_drugs_with_indications()
        logger.info(f"Found {len(drugs)} drugs with indications")
        
        success_count = 0
        error_count = 0
        
        for drug in tqdm(drugs):
            try:
                logger.info(f"Processing drug: {drug['name']} (ID: {drug['id']})")
                indications_text = drug['indications']
                logger.info(f"Indications text length: {len(indications_text)}")
                
                # 抽取实体
                result = self.extract_entities(indications_text)
                if not result:
                    logger.warning(f"No entities extracted for drug {drug['id']}")
                    error_count += 1
                    continue
                
                # 构建文档
                doc = {
                    'drug_id': drug['id'],
                    'drug_name': drug['name'],
                    'approval_number': drug.get('approval_number'),
                    'entities': result.get('entities', []),
                    'relations': result.get('relations', []),
                    'metadata': result.get('metadata', {})
                }
                
                # 索引文档
                try:
                    response = self.es.index(index='indication_entities', document=doc)
                    if response['result'] not in ['created', 'updated']:
                        logger.error(f"Failed to index document for drug {drug['id']}: {response}")
                        error_count += 1
                    else:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error indexing document for drug {drug['id']}: {str(e)}")
                    error_count += 1
                
            except Exception as e:
                logger.error(f"Error processing drug {drug['id']}: {str(e)}")
                error_count += 1
        
        logger.info(f"Batch processing completed. Success: {success_count}, Error: {error_count}")

def main():
    """Main function to extract indication entities"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Extract and store indication entities from drug descriptions')
    parser.add_argument('--clear', action='store_true', help='Clear existing indication_entities index before processing')
    parser.add_argument('--output-dir', type=str, default='outputs', help='Directory to store output files')
    args = parser.parse_args()
    
    # 初始化ES配置
    es_config = {
        "hosts": ["http://localhost:9200"],
        "basic_auth": ("elastic", os.getenv("ELASTIC_PASSWORD", "changeme"))
    }
    
    try:
        # 创建实体抽取器
        extractor = IndicationEntityExtractor(
            api_key=os.getenv("HF_API_KEY"),
            es_config=es_config
        )
        
        # 处理数据
        extractor.process_batch(
            output_dir=args.output_dir,
            clear_existing=args.clear
        )
        
        print("\nIndication entity extraction completed successfully!")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise

if __name__ == "__main__":
    main()
