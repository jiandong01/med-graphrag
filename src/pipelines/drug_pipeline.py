import os
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
from dotenv import load_dotenv
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.normalizers.drug_normalizer import DrugNormalizer
from src.normalizers.tag_normalizer import TagPreprocessor
from src.indexers.drug_indexer import DrugKnowledgeGraph

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DrugPipeline:
    """药品数据处理管道"""
    
    def __init__(self):
        """初始化管道组件"""
        self.normalizer = DrugNormalizer()
        self.tag_processor = TagPreprocessor()
        
        # 设置ES传输日志级别为WARNING，减少输出
        logging.getLogger('elastic_transport.transport').setLevel(logging.WARNING)
        
        # 初始化ES索引器
        es_config = {
            'hosts': ['http://localhost:9200'],
            'basic_auth': ('elastic', os.getenv('ELASTIC_PASSWORD', 'changeme'))
        }
        self.indexer = DrugKnowledgeGraph(es_config=es_config)
        
        # MySQL配置
        self.mysql_url = (
            f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:"
            f"{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST', 'localhost')}:"
            f"{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DB')}"
        )
        
        # 设置日志格式
        self.logger = logging.getLogger(__name__)
    
    def fetch_data(self) -> tuple:
        """从MySQL获取药品数据
        
        Returns:
            tuple: (drugs_df, drug_details_df)
        """
        self.logger.info("Fetching data from MySQL...")
        try:
            engine = create_engine(self.mysql_url)
            
            # 获取药品基本信息
            drugs_query = """
                SELECT id, name, spec, create_time
                FROM drugs_table
            """
            drugs_df = pd.read_sql(drugs_query, engine)
            
            # 获取药品详情
            details_query = """
                SELECT id as drug_id, tag, tcontent as content
                FROM drug_details_table
                WHERE del_flag = 0
            """
            drug_details_df = pd.read_sql(details_query, engine)
            
            self.logger.info(f"Fetched {len(drugs_df)} drugs and {len(drug_details_df)} details")
            return drugs_df, drug_details_df
            
        except Exception as e:
            self.logger.error(f"Error fetching data: {str(e)}")
            raise
    
    def process_drug_details(self, details_df: pd.DataFrame) -> Dict[str, Dict]:
        """处理药品详情数据
        
        Args:
            details_df: 药品详情DataFrame
            
        Returns:
            Dict[str, Dict]: 处理后的详情数据，以drug_id为key
        """
        self.logger.info("Processing drug details...")
        processed_details = {}
        
        # 统计信息
        total_details = len(details_df)
        total_unique_drugs = len(details_df['drug_id'].unique())
        details_per_drug = details_df.groupby('drug_id').size()
        
        self.logger.info(f"Total details: {total_details}")
        self.logger.info(f"Average details per drug: {total_details/total_unique_drugs:.2f}")
        self.logger.info(f"Max details per drug: {details_per_drug.max()}")
        self.logger.info(f"Min details per drug: {details_per_drug.min()}")
        
        # 按drug_id分组处理
        for drug_id, group in tqdm(details_df.groupby('drug_id'),
                                 desc="Processing drug details",
                                 total=len(details_df['drug_id'].unique())):
            try:
                # 转换为列表格式
                details = [
                    {
                        'tag': row['tag'],
                        'content': row['content']
                    }
                    for _, row in group.iterrows()
                    if pd.notnull(row['tag']) and pd.notnull(row['content'])
                ]
                
                # 记录原始标签统计
                tag_counts = group['tag'].value_counts()
                if len(tag_counts) > 1:
                    self.logger.debug(f"Drug {drug_id} has multiple tags: {dict(tag_counts)}")
                
                # 处理标签
                normalized_details = []
                skipped_details = []
                for detail in details:
                    try:
                        tag, is_main = self.tag_processor.process_tag(detail['tag'])
                        if is_main:  # 只处理主要标签
                            normalized_details.append({
                                'tag': tag,
                                'content': detail['content']
                            })
                        else:
                            skipped_details.append(detail['tag'])
                    except Exception as e:
                        self.logger.warning(f"Error processing tag for drug {drug_id}: {str(e)}")
                
                if skipped_details:
                    self.logger.debug(f"Skipped non-main tags for drug {drug_id}: {skipped_details}")
                
                # 使用规范化器处理详情
                processed_details[drug_id] = self.normalizer.process_details(normalized_details)
            except Exception as e:
                self.logger.error(f"Error processing drug details for drug {drug_id}: {str(e)}")
        
        # 输出处理后的统计信息
        processed_drugs_count = len(processed_details)
        self.logger.info(f"Successfully processed details for {processed_drugs_count} drugs")
        if processed_drugs_count != total_unique_drugs:
            self.logger.warning(f"Failed to process {total_unique_drugs - processed_drugs_count} drugs")
        
        return processed_details
    
    def process_drugs(self, drugs_df: pd.DataFrame, processed_details: Dict[str, Dict]) -> List[Dict]:
        """处理药品数据
        
        Args:
            drugs_df: 药品DataFrame
            processed_details: 处理后的详情数据
            
        Returns:
            List[Dict]: 处理后的药品列表
        """
        self.logger.info("Processing drugs...")
        processed_drugs = []
        
        # 使用tqdm显示进度
        for _, drug in tqdm(drugs_df.iterrows(), desc="Processing drugs", total=len(drugs_df)):
            try:
                # 获取详情数据
                details = processed_details.get(drug['id'], None)
                
                # 只处理有详情的药品
                if details is not None:
                    # 构建药品文档
                    processed_drug = {
                        'id': drug['id'],
                        'name': self.normalizer.standardize_name(drug['name']),
                        'spec': self.normalizer.standardize_spec(drug['spec']),
                        'create_time': self.normalizer.normalize_date(str(drug['create_time'])),
                        'components': details.get('components', []),
                        'indications': details.get('indications', []),
                        'contraindications': details.get('contraindications', []),
                        'adverse_reactions': details.get('adverse_reactions', []),
                        'precautions': details.get('precautions', []),
                        'interactions': details.get('interactions', []),
                        'usage': details.get('usage', ''),
                        'approval_number': details.get('approval_number', ''),
                        'details': details.get('details', [])
                    }
                    
                    processed_drugs.append(processed_drug)
            except Exception as e:
                self.logger.error(f"Error processing drug {drug['id']}: {str(e)}")
        
        self.logger.info(f"Successfully processed {len(processed_drugs)} drugs with details")
        return processed_drugs
    
    def run(self, output_dir: str = None, clear_indices: bool = False):
        """运行完整的处理管道
        
        Args:
            output_dir: 输出目录，用于保存中间结果
            clear_indices: 是否清空现有索引
        """
        try:
            if output_dir:
                # 设置文件日志
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                # 添加文件处理器
                fh = logging.FileHandler(output_path / 'pipeline.log')
                fh.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                fh.setFormatter(formatter)
                self.logger.addHandler(fh)
            
            # 1. 获取原始数据
            drugs_df, drug_details_df = self.fetch_data()
            self.logger.info(f"Fetched raw data: {len(drugs_df)} drugs, {len(drug_details_df)} details")
            
            # 统计数据
            total_drugs = len(drugs_df)
            unique_drug_ids_in_details = len(drug_details_df['drug_id'].unique())
            drugs_in_drugs_table = set(drugs_df['id'].unique())
            drugs_in_details_table = set(drug_details_df['drug_id'].unique())
            
            # 详细统计
            self.logger.info(f"Total unique drugs in drugs table: {len(drugs_in_drugs_table)}")
            self.logger.info(f"Total unique drugs in details table: {len(drugs_in_details_table)}")
            self.logger.info(f"Drugs with details: {unique_drug_ids_in_details}")
            
            # 检查数据不一致
            drugs_without_details = drugs_in_drugs_table - drugs_in_details_table
            details_without_drugs = drugs_in_details_table - drugs_in_drugs_table
            
            self.logger.info(f"Number of drugs without any details: {len(drugs_without_details)}")
            self.logger.info(f"Number of details for non-existent drugs: {len(details_without_drugs)}")
            
            if output_dir:
                # 保存原始数据
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                drugs_df.to_csv(output_path / 'raw_drugs.csv', index=False)
                drug_details_df.to_csv(output_path / 'raw_drug_details.csv', index=False)
                
                # 保存统计信息
                stats = {
                    'total_drugs': total_drugs,
                    'unique_drugs_with_details': unique_drug_ids_in_details,
                    'drugs_without_details': list(drugs_without_details),
                    'details_without_drugs': list(details_without_drugs)
                }
                with open(output_path / 'data_stats.json', 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
                
                # 保存没有详情的药品列表
                if len(drugs_without_details) > 0:
                    drugs_without_details_df = drugs_df[drugs_df['id'].isin(drugs_without_details)]
                    drugs_without_details_df.to_csv(output_path / 'drugs_without_details.csv', index=False)
                
                # 保存没有对应药品的详情列表
                if len(details_without_drugs) > 0:
                    details_without_drugs_df = drug_details_df[drug_details_df['drug_id'].isin(details_without_drugs)]
                    details_without_drugs_df.to_csv(output_path / 'details_without_drugs.csv', index=False)
            
            # 2. 处理详情数据
            processed_details = self.process_drug_details(drug_details_df)
            self.logger.info(f"Processed details for {len(processed_details)} drugs")
            
            if output_dir:
                with open(output_path / 'processed_details.json', 'w', encoding='utf-8') as f:
                    json.dump(processed_details, f, ensure_ascii=False, indent=2)
            
            # 3. 处理药品数据
            processed_drugs = self.process_drugs(drugs_df, processed_details)
            self.logger.info(f"Processed {len(processed_drugs)} drugs")
            
            # 检查处理后丢失的药品
            processed_drug_ids = {drug['id'] for drug in processed_drugs}
            missing_drugs = set(drugs_df['id'].unique()) - processed_drug_ids
            self.logger.info(f"Number of drugs lost during processing: {len(missing_drugs)}")
            
            if output_dir:
                with open(output_path / 'processed_drugs.json', 'w', encoding='utf-8') as f:
                    json.dump(processed_drugs, f, ensure_ascii=False, indent=2)
                    
                # 保存丢失的药品列表
                missing_drugs_df = drugs_df[drugs_df['id'].isin(missing_drugs)]
                missing_drugs_df.to_csv(output_path / 'missing_drugs.csv', index=False)
            
            # 4. 索引数据
            self.logger.info("Indexing processed drugs...")
            if clear_indices:
                self.indexer.clear_all_indices()
            self.indexer.create_indices()
            
            # 使用批量索引
            self.indexer.index_drugs(processed_drugs)
            
            self.logger.info("Pipeline completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in pipeline: {str(e)}")
            raise

def main():
    """Main function to run the drug pipeline"""
    parser = argparse.ArgumentParser(description='Run drug processing pipeline')
    parser.add_argument('--output-dir', type=str, help='Directory to save intermediate results')
    parser.add_argument('--clear', action='store_true', help='Clear existing indices before processing')
    args = parser.parse_args()
    
    pipeline = DrugPipeline()
    pipeline.run(output_dir=args.output_dir, clear_indices=args.clear)

if __name__ == "__main__":
    main()
