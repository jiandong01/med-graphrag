import os
import logging
import argparse
from pathlib import Path
from typing import List, Dict
import hashlib
import json
from datetime import datetime
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.analysis.indication_stats import get_indication_stats
from src.normalizers.indication_normalizer import IndicationNormalizer
from src.extractors.indication_extractor import IndicationEntityExtractor
from src.indexers.indication_indexer import IndicationIndexer
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IndicationPipeline:
    """适应症处理管道"""
    
    def __init__(self):
        """初始化管道组件"""
        # 初始化ES客户端
        es_config = {
            'hosts': ['http://localhost:9200'],
            'basic_auth': ('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
        }
        self.es = Elasticsearch(**es_config)
        
        # 初始化各个组件
        self.normalizer = IndicationNormalizer()
        self.extractor = IndicationEntityExtractor(
            api_key=os.getenv('HF_API_KEY'),
            es_config=es_config
        )
        self.indexer = IndicationIndexer(es_config=es_config)
    
    def generate_indication_id(self, indication: str) -> str:
        """生成适应症ID
        
        Args:
            indication: 适应症文本
            
        Returns:
            str: 适应症ID
        """
        return hashlib.md5(indication.encode()).hexdigest()
    
    def process_raw_indications(self) -> List[Dict]:
        """处理原始适应症数据
        
        Returns:
            List[Dict]: 处理后的适应症列表
        """
        logger.info("Getting raw indications from drugs index...")
        stats = get_indication_stats(self.es)
        
        processed_indications = []
        for name, info in stats['counts'].items():
            # 标准化名称
            normalized_name = self.normalizer.standardize_name(name)
            if not normalized_name:
                continue
                
            # 获取类别
            category = self.normalizer.get_category(normalized_name)
            
            # 构建适应症对象
            indication = {
                'id': self.generate_indication_id(normalized_name),
                'name': name,
                'normalized_name': normalized_name,
                'category': category,
                'source_drugs': [],  # 将在后续步骤填充
                'entities': [],      # 将由LLM抽取
                'create_time': datetime.now().isoformat()
            }
            
            processed_indications.append(indication)
            
        logger.info(f"Processed {len(processed_indications)} raw indications")
        return processed_indications
    
    def extract_entities(self, indications: List[Dict]) -> List[Dict]:
        """使用LLM抽取实体
        
        Args:
            indications: 适应症列表
            
        Returns:
            List[Dict]: 添加了实体信息的适应症列表
        """
        logger.info("Extracting entities using LLM...")
        for indication in indications:
            # 抽取实体
            entities = self.extractor.extract_entities([indication['normalized_name']])
            if entities:
                indication['entities'] = entities
        
        return indications
    
    def add_source_drugs(self, indications: List[Dict]):
        """添加来源药品信息
        
        Args:
            indications: 适应症列表
        """
        logger.info("Adding source drug information...")
        
        # 获取所有药品
        response = self.es.search(
            index='drugs',
            body={
                'query': {'match_all': {}},
                '_source': ['id', 'name', 'indications'],
                'size': 10000
            }
        )
        
        # 构建适应症到药品的映射
        indication_to_drugs = {}
        for hit in response['hits']['hits']:
            drug = hit['_source']
            if 'indications' in drug:
                for indication in drug['indications']:
                    normalized = self.normalizer.standardize_name(indication)
                    if normalized:
                        if normalized not in indication_to_drugs:
                            indication_to_drugs[normalized] = []
                        indication_to_drugs[normalized].append({
                            'drug_id': drug['id'],
                            'drug_name': drug['name']
                        })
        
        # 添加来源药品信息
        for indication in indications:
            if indication['normalized_name'] in indication_to_drugs:
                indication['source_drugs'] = indication_to_drugs[indication['normalized_name']]
    
    def run(self, output_dir: str = None):
        """运行完整的处理管道
        
        Args:
            output_dir: 输出目录，用于保存中间结果
        """
        try:
            # 1. 处理原始适应症
            indications = self.process_raw_indications()
            
            if output_dir:
                # 保存中间结果
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                with open(output_path / 'raw_indications.json', 'w', encoding='utf-8') as f:
                    json.dump(indications, f, ensure_ascii=False, indent=2)
            
            # 2. 抽取实体
            indications = self.extract_entities(indications)
            
            if output_dir:
                with open(output_path / 'indications_with_entities.json', 'w', encoding='utf-8') as f:
                    json.dump(indications, f, ensure_ascii=False, indent=2)
            
            # 3. 添加来源药品信息
            self.add_source_drugs(indications)
            
            if output_dir:
                with open(output_path / 'final_indications.json', 'w', encoding='utf-8') as f:
                    json.dump(indications, f, ensure_ascii=False, indent=2)
            
            # 4. 索引数据
            logger.info("Indexing processed indications...")
            self.indexer.clear_indices()
            self.indexer.create_indices()
            self.indexer.index_indications(indications)
            
            logger.info("Pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            raise

def main():
    """Main function to run the indication pipeline"""
    parser = argparse.ArgumentParser(description='Run indication processing pipeline')
    parser.add_argument('--output-dir', type=str, help='Directory to save intermediate results')
    args = parser.parse_args()
    
    pipeline = IndicationPipeline()
    pipeline.run(output_dir=args.output_dir)

if __name__ == "__main__":
    main()
