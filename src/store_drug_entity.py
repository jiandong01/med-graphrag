import json
import logging
from typing import Dict, List
import psycopg2
from neo4j import GraphDatabase
from datetime import datetime
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DrugEntityStorage:
    def __init__(self, pg_config: Dict, neo4j_config: Dict):
        """初始化数据库连接"""
        self.pg_conn = psycopg2.connect(**pg_config)
        self.neo4j_driver = GraphDatabase.driver(**neo4j_config)
        
    def store_to_postgres(self, extraction_result: Dict) -> int:
        """存储到PostgreSQL"""
        with self.pg_conn.cursor() as cur:
            try:
                # 存储原始抽取结果
                cur.execute("""
                    INSERT INTO indication_extractions 
                    (original_text, extraction_result, confidence_score, created_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    extraction_result['metadata']['original_text'],
                    json.dumps(extraction_result),
                    extraction_result['metadata']['confidence_score'],
                    datetime.fromisoformat(extraction_result['metadata']['extraction_time'])
                ))
                
                extraction_id = cur.fetchone()[0]
                
                # 存储实体
                for entity in extraction_result['entities']:
                    cur.execute("""
                        INSERT INTO indication_entities 
                        (entity_id, text, type, medical_system, standard_name, 
                         pathogen, body_part, extraction_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        entity['id'], 
                        entity['text'],
                        entity['type'],
                        entity['medical_system'],
                        entity['standard_name'],
                        entity['attributes'].get('pathogen'),
                        entity['attributes'].get('body_part'),
                        extraction_id
                    ))
                
                # 存储关系
                for relation in extraction_result['relations']:
                    cur.execute("""
                        INSERT INTO indication_relations 
                        (head_entity_id, tail_entity_id, relation_type, 
                         evidence_level, source, extraction_id)
                        VALUES 
                        ((SELECT id FROM indication_entities WHERE text = %s),
                         (SELECT id FROM indication_entities WHERE text = %s),
                         %s, %s, %s, %s)
                    """, (
                        relation['head'],
                        relation['tail'],
                        relation['type'],
                        relation['evidence_level'],
                        relation['source'],
                        extraction_id
                    ))
                
                self.pg_conn.commit()
                return extraction_id
                
            except Exception as e:
                self.pg_conn.rollback()
                logger.error(f"PostgreSQL storage failed: {str(e)}")
                raise

    def store_to_neo4j(self, extraction_result: Dict):
        """存储到Neo4j"""
        with self.neo4j_driver.session() as session:
            try:
                # 创建实体节点
                for entity in extraction_result['entities']:
                    session.run("""
                        MERGE (e:IndicationEntity {id: $id})
                        SET e += $properties
                    """, {
                        'id': entity['id'],
                        'properties': {
                            'text': entity['text'],
                            'type': entity['type'],
                            'medical_system': entity['medical_system'],
                            'standard_name': entity['standard_name'],
                            'pathogen': entity['attributes'].get('pathogen'),
                            'body_part': entity['attributes'].get('body_part')
                        }
                    })
                
                # 创建关系
                for relation in extraction_result['relations']:
                    session.run("""
                        MATCH (head:IndicationEntity {text: $head_text})
                        MATCH (tail:IndicationEntity {text: $tail_text})
                        MERGE (head)-[r:INDICATION_RELATION {type: $type}]->(tail)
                        SET r += $properties
                    """, {
                        'head_text': relation['head'],
                        'tail_text': relation['tail'],
                        'type': relation['type'],
                        'properties': {
                            'evidence_level': relation['evidence_level'],
                            'source': relation['source']
                        }
                    })
                    
            except Exception as e:
                logger.error(f"Neo4j storage failed: {str(e)}")
                raise

    def process_file(self, file_path: str):
        """处理单个结果文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                extraction_result = json.load(f)
            
            # 存储到PostgreSQL
            extraction_id = self.store_to_postgres(extraction_result)
            
            # 存储到Neo4j
            self.store_to_neo4j(extraction_result)
            
            logger.info(f"Successfully processed file {file_path}")
            return extraction_id
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            return None

    def close(self):
        """关闭数据库连接"""
        self.pg_conn.close()
        self.neo4j_driver.close()

def main():
    # 加载配置
    utils.load_env()
    config = utils.load_config()
    logger = utils.setup_logging('store_drug_entity', config)
    utils.ensure_directories(config)
    
    # 获取数据库配置
    db_configs = utils.get_db_configs()
    
    # 初始化存储管理器
    storage = DrugEntityStorage(db_configs['postgresql'], db_configs['neo4j'])
    
    try:
        # 处理输出目录中的所有JSON文件
        output_dir = Path(config['paths']['output_dir'])
        processed_dir = Path(config['paths']['processed_dir'])
        failed_dir = Path(config['paths']['failed_dir'])
        
        # 处理所有JSON文件
        for file_path in output_dir.glob("*.json"):
            try:
                logger.info(f"Processing file: {file_path}")
                
                if file_path.stem.startswith('batch_results_'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                    
                    for result in results:
                        storage.store_to_postgres(result)
                        storage.store_to_neo4j(result)
                else:
                    storage.process_file(str(file_path))
                
                file_path.rename(processed_dir / file_path.name)
                logger.info(f"Successfully processed and moved {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                file_path.rename(failed_dir / file_path.name)
                
    finally:
        storage.close()