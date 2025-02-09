import os
import logging
from elasticsearch import Elasticsearch
from typing import List, Dict, Any
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DrugKnowledgeGraph:
    """药品知识图谱索引器"""
    
    def __init__(self, es_config: Dict[str, Any]):
        """初始化ES客户端
        
        Args:
            es_config: ES配置，包含hosts和basic_auth
        """
        self.es = Elasticsearch(**es_config)
        self.drug_index = "drugs"
    
    def create_indices(self):
        """创建所需的索引"""
        logger.info("Creating indices...")
        
        # 药品索引设置
        drug_settings = {
            "analysis": {
                "analyzer": {
                    "text_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop"],
                        "char_filter": ["html_strip"]
                    }
                }
            }
        }
        
        # 药品索引映射
        drug_mapping = {
            "properties": {
                "id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "spec": {"type": "text"},
                "create_time": {"type": "date"},
                "components": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "indications": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "contraindications": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "adverse_reactions": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "precautions": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "interactions": {
                    "type": "text",
                    "analyzer": "text_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "usage": {"type": "text"},
                "approval_number": {"type": "keyword"},
                "details": {
                    "type": "nested",
                    "properties": {
                        "tag": {"type": "keyword"},
                        "content": {"type": "text"}
                    }
                }
            }
        }
        
        logger.info("Creating drug index...")
        self.es.indices.create(
            index=self.drug_index,
            body={"settings": drug_settings, "mappings": drug_mapping},
            ignore=400  # 忽略已存在的索引错误
        )
        logger.info(f"Created index: {self.drug_index}")
    
    def clear_all_indices(self):
        """清空所有索引"""
        logger.info("Clearing all indices...")
        if self.es.indices.exists(index=self.drug_index):
            self.es.indices.delete(index=self.drug_index)
            logger.info(f"Deleted index: {self.drug_index}")
    
    def index_drug(self, drug: Dict):
        """索引单个药品
        
        Args:
            drug: 药品数据
        """
        try:
            self.es.index(index=self.drug_index, id=drug['id'], document=drug)
        except Exception as e:
            logger.error(f"Error indexing drug {drug['id']}: {str(e)}")
            raise
    
    def index_drugs(self, drugs: List[Dict]):
        """索引药品数据
        
        Args:
            drugs: 处理后的药品列表
        """
        logger.info("Indexing drugs...")
        
        # 批量索引
        batch_size = 500  # 增加批量大小以减少请求次数
        total_batches = (len(drugs) + batch_size - 1) // batch_size
        
        # 使用tqdm显示总体进度
        with tqdm(total=len(drugs), desc="Indexing drugs") as pbar:
            for i in range(0, len(drugs), batch_size):
                batch = drugs[i:i + batch_size]
                operations = []
                
                for drug in batch:
                    operations.extend([
                        {"index": {"_index": self.drug_index, "_id": drug["id"]}},
                        drug
                    ])
                
                if operations:
                    try:
                        # 使用bulk API批量索引
                        response = self.es.bulk(operations=operations, refresh=True)
                        if response.get('errors'):
                            # 记录失败的文档
                            for item in response['items']:
                                if item['index'].get('error'):
                                    logger.error(f"Error indexing document {item['index']['_id']}: {item['index']['error']}")
                    except Exception as e:
                        logger.error(f"Error in batch indexing: {str(e)}")
                        raise
                
                # 更新进度条
                pbar.update(len(batch))
        
        logger.info(f"Successfully indexed {len(drugs)} drugs")

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
            drugs = []
            for _, drug in tqdm(drugs_df.iterrows(), total=len(drugs_df)):
                try:
                    # 处理药品详情
                    details = drug_details_df[drug_details_df['id'] == drug['id']]
                    processed_details = {}
                    
                    if not details.empty:
                        # Process each detail type
                        for _, detail in details.iterrows():
                            content = detail['tcontent']
                            tag = detail['tag']
                            
                            if not content or not isinstance(content, str):
                                continue
                            
                            # Store original detail
                            processed_details.setdefault('details', []).append({
                                'tag': tag,
                                'content': content.strip()
                            })
                    
                    # 构建文档
                    doc = {
                        'id': drug['id'],
                        'name': drug['name'],
                        'spec': drug['spec'],
                        'manufacturer': drug['manufacturer'],
                        'create_time': drug['create_time'].isoformat() if pd.notnull(drug['create_time']) else None,
                        'category_id': drug['parent_id'],
                        'components': [],
                        'indications': '',
                        'contraindications': '',
                        'adverse_reactions': '',
                        'precautions': '',
                        'interactions': '',
                        'usage': '',
                        'approval_number': '',
                        'details': processed_details.get('details', [])
                    }
                    
                    drugs.append(doc)
                except Exception as e:
                    print(f"Error processing drug {drug['id']}: {str(e)}")
            
            kg.index_drugs(drugs)
            
            print("\nKnowledge graph creation completed successfully!")
            
        finally:
            if engine:
                engine.dispose()
                
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise

if __name__ == "__main__":
    main()