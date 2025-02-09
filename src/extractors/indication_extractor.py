from huggingface_hub import InferenceClient
import json
import logging
import argparse
from typing import Dict, Optional, List, Set
from datetime import datetime
from pathlib import Path
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
from tqdm import tqdm
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.normalizers.indication_normalizer import IndicationNormalizer

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
        self.normalizer = IndicationNormalizer()
        
    def create_extraction_prompt(self, indications: List[str]) -> list:
        """创建实体抽取的prompt"""
        # 将多个适应症组合成一个文本，每个适应症单独一行
        text = "\n".join(indications)
        
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

    def extract_entities(self, indications: List[str]) -> Optional[Dict]:
        """调用API进行实体抽取"""
        try:
            messages = self.create_extraction_prompt(indications)
            logger.info(f"Sending request to API with {len(indications)} indications")
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

    def process_batch(self, drugs: List[Dict]) -> None:
        """处理一批药品数据"""
        success_count = 0
        error_count = 0
        
        # 收集所有药品的适应症文本
        all_indications_texts = [drug['indications'] for drug in drugs]
        
        # 使用规范化器分析所有适应症
        logger.info("Analyzing and normalizing indications...")
        analysis = self.normalizer.analyze_indications(all_indications_texts)
        logger.info(f"Found {analysis['total_unique']} unique indications across {len(analysis['categories'])} categories")
        
        # 为每个标准化的适应症调用一次API
        logger.info("Extracting entities for unique indications...")
        std_indications = list(analysis['standardization_map'].keys())
        result = self.extract_entities(std_indications)
        
        if not result:
            logger.error("Failed to extract entities from standardized indications")
            return
        
        # 为每个药品创建文档
        for drug in tqdm(drugs, desc="Processing drugs"):
            try:
                # 获取该药品的原始适应症
                original_indications = self.normalizer.split_indications(drug['indications'])
                
                # 获取标准化的适应症
                drug_std_indications = set()
                for ind in original_indications:
                    std_name = self.normalizer.standardize_name(ind)
                    drug_std_indications.add(std_name)
                
                # 从API结果中筛选出该药品的实体
                drug_entities = []
                for entity in result['entities']:
                    if entity['text'] in drug_std_indications:
                        drug_entities.append(entity)
                
                # 构建文档
                doc = {
                    'drug_id': drug['id'],
                    'drug_name': drug['name'],
                    'approval_number': drug.get('approval_number'),
                    'entities': drug_entities,
                    'relations': result.get('relations', []),
                    'metadata': {
                        'original_text': drug['indications'],
                        'standardized_indications': list(drug_std_indications),
                        'extraction_time': datetime.now().isoformat(),
                        'confidence_score': result['metadata'].get('confidence_score', 0.95)
                    }
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
                            "standardized_indications": {
                                "type": "keyword"
                            },
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
            self.create_indices()
        except Exception as e:
            logger.error(f"Error clearing indices: {str(e)}")

def main():
    """Main function to extract indication entities"""
    parser = argparse.ArgumentParser(description='Extract indication entities from drug descriptions')
    parser.add_argument('--clear', action='store_true', help='Clear existing indices before processing')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                      help='Set the logging level')
    parser.add_argument('--stats', action='store_true', help='Show indication statistics')
    parser.add_argument('--top-n', type=int, default=10, help='Show top N indications in statistics')
    parser.add_argument('--export-stats', type=str, help='Export statistics to CSV file')
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Initialize extractor
    extractor = IndicationEntityExtractor(
        api_key=os.getenv('HF_API_KEY'),
        es_config={
            'hosts': ['http://localhost:9200'],
            'basic_auth': ('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
        }
    )
    
    if args.clear:
        logger.info("Clearing existing indices...")
        extractor.clear_indices()
    
    # Fetch and process drugs
    drugs = extractor.fetch_drugs_with_indications(args.batch_size)
    if drugs:
        # 如果需要显示统计信息
        if args.stats or args.export_stats:
            logger.info("Analyzing indications...")
            all_indications = [drug['indications'] for drug in drugs]
            
            # 打印统计信息
            if args.stats:
                extractor.normalizer.print_value_counts(
                    all_indications,
                    top_n=args.top_n,
                    show_details=True
                )
            
            # 导出统计信息
            if args.export_stats:
                logger.info(f"Exporting statistics to {args.export_stats}")
                extractor.normalizer.export_value_counts(
                    all_indications,
                    output_file=args.export_stats
                )
        
        # 处理实体抽取
        extractor.process_batch(drugs)
    else:
        logger.warning("No drugs found with indications")

if __name__ == "__main__":
    main()
