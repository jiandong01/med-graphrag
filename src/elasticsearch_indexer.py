from elasticsearch import Elasticsearch
from datetime import datetime
from typing import List, Dict, Any
import json
from tqdm import tqdm
import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text
import re
import argparse
from tag_normalizer import TagPreprocessor

# Load environment variables
load_dotenv()

# Configure MySQL URL with proper environment variable names
MYSQL_URL = f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DB')}"

def parse_chinese_date(date_str: str) -> str:
    """Convert Chinese date format to ISO format"""
    if not date_str or not isinstance(date_str, str):
        return None
        
    # Extract year, month, day using regex
    pattern = r'(\d{4})年(\d{2})月(\d{2})日'
    match = re.match(pattern, date_str)
    if match:
        year, month, day = match.groups()
        try:
            return f"{year}-{month}-{day}"
        except ValueError:
            return None
    return None

class DrugKnowledgeGraph:
    def __init__(self, es_config: Dict[str, Any]):
        """初始化ES客户端"""
        self.es = Elasticsearch(**es_config)
        self.tag_processor = TagPreprocessor()
        
    def clear_all_indices(self):
        """Clear application indices while preserving system indices"""
        try:
            # List of indices we want to manage
            app_indices = ['drugs']
            
            for index in app_indices:
                if self.es.indices.exists(index=index):
                    print(f"Deleting index: {index}")
                    self.es.indices.delete(index=index, ignore=[404])
            print("Application indices cleared successfully.")
        except Exception as e:
            print(f"Error clearing indices: {str(e)}")
            raise
    
    def create_indices(self):
        """创建必要的索引"""
        # 1. 药品索引
        drug_index = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "drug_analyzer": {
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
                    "id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "drug_analyzer",
                        "fields": {
                            "raw": {"type": "keyword"}
                        }
                    },
                    "spec": {"type": "text"},
                    "manufacturer": {"type": "keyword"},
                    "create_time": {"type": "date"},
                    "category_id": {"type": "keyword"},
                    "approval_number": {"type": "keyword"},
                    "details": {
                        "type": "nested",
                        "properties": {
                            "tag": {"type": "keyword"},
                            "content": {"type": "text"}
                        }
                    },
                    "components": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "text", "analyzer": "drug_analyzer"},
                            "content": {"type": "text"}
                        }
                    },
                    "indications": {
                        "type": "text",
                        "analyzer": "drug_analyzer",
                        "fields": {
                            "raw": {"type": "keyword"}
                        }
                    },
                    "contraindications": {"type": "text", "analyzer": "drug_analyzer"},
                    "adverse_reactions": {"type": "text", "analyzer": "drug_analyzer"},
                    "precautions": {"type": "text", "analyzer": "drug_analyzer"},
                    "interactions": {"type": "text", "analyzer": "drug_analyzer"},
                    "usage": {"type": "text", "analyzer": "drug_analyzer"}
                }
            }
        }
        
        self.es.indices.create(index="drugs", body=drug_index)
        print("Created 'drugs' index with updated mappings.")

    def _process_drug_details(self, details_df) -> Dict:
        """处理药品详情"""
        result = {
            'details': []  # 存储所有原始详细信息
        }
        
        if details_df.empty:
            return result
            
        # Process each detail type
        for _, detail in details_df.iterrows():
            content = detail['tcontent']
            tag = detail['tag']
            
            if not content or not isinstance(content, str):
                continue
                
            # Store original detail
            result['details'].append({
                'tag': tag,
                'content': content.strip()
            })
            
            # Get normalized tag and check if it's a main category
            normalized_tag, is_main = self.tag_processor.process_tag(tag)
            
            # Process main category tags for analysis
            if is_main:
                if normalized_tag == 'components':
                    # Parse components into structured format
                    components = []
                    component_matches = re.finditer(r'(.+?)[:：]\s*(.+?)(?=\n|$)', content)
                    for match in component_matches:
                        components.append({
                            'name': match.group(1).strip(),
                            'content': match.group(2).strip()
                        })
                    if components:
                        result[normalized_tag] = components
                else:
                    # Store other main category fields as text
                    result[normalized_tag] = content.strip()
        
        return result

    def process_drugs(self, drugs_df, drug_details_df):
        """处理药品数据"""
        print("\nProcessing drugs...")
        failed_docs = []
        
        # Show a sample of processed document
        if len(drugs_df) > 0:
            print("\nProcessing first document as sample...")
            first_drug = drugs_df.iloc[0]
            details = drug_details_df[drug_details_df['id'] == first_drug['id']]
            processed_details = self._process_drug_details(details) if not details.empty else {}
            
            sample_doc = {
                'id': first_drug['id'],
                'name': first_drug['name'],
                'spec': first_drug['spec'],
                'manufacturer': first_drug['manufacturer'],
                'create_time': first_drug['create_time'].isoformat() if pd.notnull(first_drug['create_time']) else None,
                'category_id': first_drug['parent_id'],
                'details': processed_details.get('details', []),
                'components': processed_details.get('components'),
                'indications': processed_details.get('indications'),
                'contraindications': processed_details.get('contraindications'),
                'adverse_reactions': processed_details.get('adverse_reactions'),
                'precautions': processed_details.get('precautions'),
                'interactions': processed_details.get('interactions'),
                'usage': processed_details.get('usage'),
                'approval_number': processed_details.get('approval_number')
            }
            
            print("\nSample processed document structure:")
            print(json.dumps(sample_doc, ensure_ascii=False, indent=2))
            print("\nContinuing with full processing...")
        
        for _, drug in tqdm(drugs_df.iterrows(), total=len(drugs_df)):
            try:
                # 处理药品详情
                details = drug_details_df[drug_details_df['id'] == drug['id']]
                processed_details = self._process_drug_details(details) if not details.empty else {}
                
                # 构建文档
                doc = {
                    'id': drug['id'],
                    'name': drug['name'],
                    'spec': drug['spec'],
                    'manufacturer': drug['manufacturer'],
                    'create_time': drug['create_time'].isoformat() if pd.notnull(drug['create_time']) else None,
                    'category_id': drug['parent_id'],
                    'details': processed_details.get('details', []),
                    'components': processed_details.get('components'),
                    'indications': processed_details.get('indications'),
                    'contraindications': processed_details.get('contraindications'),
                    'adverse_reactions': processed_details.get('adverse_reactions'),
                    'precautions': processed_details.get('precautions'),
                    'interactions': processed_details.get('interactions'),
                    'usage': processed_details.get('usage'),
                    'approval_number': processed_details.get('approval_number')
                }
                
                # 索引文档
                try:
                    response = self.es.index(index='drugs', document=doc)
                    if response['result'] not in ['created', 'updated']:
                        failed_docs.append({
                            'id': drug['id'],
                            'error': f"Unexpected result: {response['result']}"
                        })
                except Exception as e:
                    failed_docs.append({
                        'id': drug['id'],
                        'error': str(e)
                    })
            except Exception as e:
                failed_docs.append({
                    'id': drug['id'],
                    'error': str(e)
                })
        
        if failed_docs:
            print("\nFailed to process the following documents:")
            for doc in failed_docs:
                print(f"ID: {doc['id']}, Error: {doc['error']}")
        else:
            print("\nAll documents processed successfully!")

    def search_drugs(self, query: str, fields: List[str] = None) -> Dict:
        """搜索药品"""
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": fields or [
                        "name^3",
                        "details.tag^3",
                        "details.content^2",
                        "indications^2",
                        "components.name",
                        "contraindications",
                        "adverse_reactions",
                        "precautions",
                        "interactions",
                        "usage"
                    ],
                    "type": "best_fields",
                    "tie_breaker": 0.3
                }
            },
            "highlight": {
                "fields": {
                    "*": {}
                }
            }
        }
        
        return self.es.search(index="drugs", body=search_body)
    
    def get_similar_drugs(self, drug_id: str) -> Dict:
        """获取相似药品"""
        # 先获取目标药品信息
        drug = self.es.get(index="drugs", id=drug_id)
        
        # 构建相似性查询
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "more_like_this": {
                                "fields": ["indications"],
                                "like": drug['_source']['indications'],
                                "min_term_freq": 1,
                                "max_query_terms": 12
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"category_id": drug['_source']['category_id']}}
                    ],
                    "must_not": [
                        {"term": {"_id": drug_id}}
                    ]
                }
            }
        }
        
        return self.es.search(index="drugs", body=search_body)

def main():
    """Main function to create the knowledge graph"""
    parser = argparse.ArgumentParser(description='Generate Elasticsearch indices for medical knowledge graph')
    parser.add_argument('--clear', action='store_true', help='Clear all existing indices before processing')
    args = parser.parse_args()
    
    # 初始化ES客户端
    es_config = {
        "hosts": ["http://localhost:9200"],
        "basic_auth": ("elastic", os.getenv("ELASTIC_PASSWORD", "changeme"))
    }
    
    try:
        # 创建知识图谱对象
        kg = DrugKnowledgeGraph(es_config)
        
        # Clear all indices if requested
        if args.clear:
            print("\nClearing all existing indices...")
            kg.clear_all_indices()
        
        # 创建索引
        print("\nCreating indices...")
        kg.create_indices()
        
        # 连接MySQL数据库
        print("\nConnecting to MySQL database...")
        engine = None
        try:
            engine = create_engine(MYSQL_URL)
            
            # Check available tables
            with engine.connect() as connection:
                # Get list of tables in the database
                result = connection.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
                print("\nAvailable tables in database:", tables)
            
            # 读取数据
            print("\nLoading data from MySQL...")
            
            # Load categories if table exists
            categories_df = pd.DataFrame()
            if 'categories_table' in tables:
                categories_df = pd.read_sql(text("SELECT * FROM categories_table"), engine)
                print(f"  Loaded {len(categories_df)} categories")
            else:
                print("  Categories table not found, skipping...")
            
            # Load drugs
            if 'drugs_table' not in tables:
                raise Exception("Required table 'drugs_table' not found in database!")
            drugs_df = pd.read_sql(text("SELECT * FROM drugs_table"), engine)
            print(f"  Loaded {len(drugs_df)} drugs")
            
            # Load drug details
            if 'drug_details_table' not in tables:
                raise Exception("Required table 'drug_details_table' not found in database!")
            drug_details_df = pd.read_sql(text("SELECT * FROM drug_details_table"), engine)
            print(f"  Loaded {len(drug_details_df)} drug details")
            
            # 处理数据
            kg.process_drugs(drugs_df, drug_details_df)
            
            print("\nKnowledge graph creation completed successfully!")
            
        finally:
            if engine:
                engine.dispose()
                
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise

if __name__ == "__main__":
    main()