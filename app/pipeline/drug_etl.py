import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
import sys
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.src.drug.drug_indexer import DrugIndexer
from app.src.drug.drug_normalizer import DrugNormalizer
from app.src.drug.tag_preprocessor import TagPreprocessor
from app.src.utils import get_es_client, setup_logging, load_env, load_config, ensure_directories
import logging

# Load environment variables
load_env()

# 使用简单的日志配置避免权限问题
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DrugPipeline:
    """药品数据处理管道"""
    
    def __init__(self, db_url: str, es_config: Dict[str, Any]):
        """初始化

        Args:
            db_url: 数据库连接URL (支持 PostgreSQL 和 MySQL)
            es_config: Elasticsearch配置
        """
        self.db_url = db_url
        self.es_config = es_config
        self.normalizer = None  # 延迟初始化
        self.logger = logging.getLogger(__name__)
        
        # 设置ES传输日志级别为WARNING，减少输出
        logging.getLogger('elastic_transport.transport').setLevel(logging.WARNING)
        
        # 初始化ES索引器
        self.indexer = DrugIndexer(es_config=es_config)

    def fetch_data(self) -> tuple:
        """从数据库获取药品数据（支持 PostgreSQL 和 MySQL）
        
        Returns:
            tuple: (drugs_df, drug_details_df, categories_df)
        """
        try:
            engine = create_engine(self.db_url)
            
            # 判断数据库类型
            is_postgres = 'postgresql' in self.db_url
            
            # 1. 获取药品基础信息，使用 GROUP BY 合并同一药品的多条记录
            if is_postgres:
                # PostgreSQL 使用 STRING_AGG
                drugs_query = """
                    SELECT 
                        id,
                        MAX(name) as name,
                        MAX(spec) as spec,
                        MAX(create_time) as create_time,
                        STRING_AGG(DISTINCT parent_id::text, ',') as parent_ids
                    FROM drugs_table
                    GROUP BY id
                """
            else:
                # MySQL 使用 GROUP_CONCAT
                drugs_query = """
                    SELECT 
                        id,
                        MAX(name) as name,
                        MAX(spec) as spec,
                        MAX(create_time) as create_time,
                        GROUP_CONCAT(DISTINCT parent_id) as parent_ids
                    FROM drugs_table
                    GROUP BY id
                """
            drugs_df = pd.read_sql(drugs_query, engine)
            
            # 2. 获取分类信息
            categories_query = """
                SELECT id as category_id, category, parent_id
                FROM categories_table
                WHERE category IS NOT NULL
            """
            categories_df = pd.read_sql(categories_query, engine)
            
            # 3. 获取药品详情
            details_query = """
                SELECT 
                    id as drug_id,  -- id 字段作为 drug_id
                    tag,
                    tcontent as content,  -- tcontent 字段作为 content
                    create_time,
                    update_time
                FROM drug_details_table
                WHERE del_flag = 0  -- 只获取未删除的记录
            """
            drug_details_df = pd.read_sql(details_query, engine)
            
            # 4. 处理parent_ids，转换为列表
            drugs_df['parent_ids'] = drugs_df['parent_ids'].apply(
                lambda x: list(map(str.strip, str(x).split(','))) if pd.notna(x) else []
            )
            
            # 记录数据获取情况
            total_drugs = len(drugs_df)
            total_details = len(drug_details_df)
            drugs_with_details = len(drug_details_df['drug_id'].unique())
            
            self.logger.info("数据获取完成:")
            self.logger.info(f"- 总药品数: {total_drugs}")
            self.logger.info(f"- 详情记录数: {total_details}")
            self.logger.info(f"- 有详情的药品数: {drugs_with_details}")
            
            # 检查是否有药品缺少详情
            drugs_without_details = total_drugs - drugs_with_details
            if drugs_without_details > 0:
                self.logger.warning(f"发现 {drugs_without_details} 个药品没有详情信息")
            
            return drugs_df, drug_details_df, categories_df
            
        except Exception as e:
            self.logger.error(f"获取数据时发生错误: {str(e)}")
            raise

    def process_drug_details(self, drug_details_df: pd.DataFrame) -> Dict[str, Dict]:
        """处理药品详情数据"""
        self.logger.info("开始处理药品详情...")
        processed_details = {}
        
        # 先初始化一个基础的 DrugNormalizer
        self.normalizer = DrugNormalizer()
        
        # 获取分类信息
        try:
            engine = create_engine(self.db_url)
            categories_query = """
                SELECT id as category_id, category, parent_id
                FROM categories_table
                WHERE category IS NOT NULL
            """
            categories_df = pd.read_sql(categories_query, engine)
            
            # 构建分类树
            category_tree = {}
            for _, cat in categories_df.iterrows():
                category_tree[cat['category_id']] = {
                    'category': self.normalizer.clean_text(cat['category']) if cat['category'] else '',
                    'parent_id': cat['parent_id']
                }
            
            # 使用分类树重新初始化 DrugNormalizer
            self.normalizer = DrugNormalizer(category_tree=category_tree)
            
        except Exception as e:
            self.logger.error(f"获取分类信息时发生错误: {str(e)}")
            # 如果获取分类失败，继续使用基础的 DrugNormalizer
            pass
        
        # 按药品ID分组
        for drug_id, group in tqdm(drug_details_df.groupby('drug_id'), desc="处理药品详情"):
            try:
                details = []
                
                # 处理每条详情记录
                for _, row in group.iterrows():
                    tag = row['tag']
                    content = row['content']
                    
                    # 跳过空内容
                    if pd.isna(content) or not content.strip():
                        continue
                        
                    # 添加到详情列表
                    details.append({
                        'original_tag': tag,
                        'normalized_tag': tag.lower(),  # 标准化tag
                        'content': content.strip()
                    })
                
                # 使用DrugNormalizer处理详情
                if details:
                    processed_details[drug_id] = self.normalizer.process_details(details)
                
            except Exception as e:
                self.logger.error(f"处理药品 {drug_id} 的详情时发生错误: {str(e)}")
        
        self.logger.info("详情处理完成:")
        self.logger.info(f"- 成功处理: {len(processed_details)} 个药品")
        failed_count = len(drug_details_df['drug_id'].unique()) - len(processed_details)
        if failed_count > 0:
            self.logger.warning(f"- 处理失败: {failed_count} 个药品")
        
        return processed_details

    def process_drugs(self, drugs_df: pd.DataFrame, processed_details: Dict[str, Dict], categories_df: pd.DataFrame) -> List[Dict]:
        """处理药品数据"""
        self.logger.info("开始处理药品数据...")
        processed_drugs = []
        
        # 构建分类ID到分类信息的映射
        category_map = {}
        for _, cat in categories_df.iterrows():
            category_map[str(cat['category_id'])] = {
                'category': self.normalizer.clean_text(cat['category']) if cat['category'] else '',
                'parent_id': cat['parent_id']
            }
        
        # 只处理有详情的药品
        drugs_with_details = list(processed_details.keys())
        drugs_df = drugs_df[drugs_df['id'].isin(drugs_with_details)]
        
        # 按药品ID分组处理
        for _, drug in tqdm(drugs_df.iterrows(), desc="处理药品数据", total=len(drugs_df)):
            try:
                drug_id = drug['id']
                # 获取详情数据
                details = processed_details.get(drug_id)
                
                if details is not None:
                    # 格式化日期为ES要求的格式
                    create_time = str(drug['create_time'])
                    if len(create_time) == 8:  # 如果是 YYYYMMDD 格式
                        create_time = f"{create_time[:4]}-{create_time[4:6]}-{create_time[6:]}"
                    
                    # 处理分类信息
                    categories = []
                    category_hierarchy = []
                    
                    # 从parent_ids获取分类信息
                    parent_ids = drug['parent_ids']
                    for parent_id in parent_ids:
                        if parent_id in category_map:
                            cat_info = category_map[parent_id]
                            cat_name = cat_info['category']
                            
                            # 添加分类名称
                            if cat_name and cat_name not in categories:
                                categories.append(cat_name)
                            
                            # 构建分类层级
                            hierarchy = {
                                'category': cat_name,
                                'category_id': parent_id,
                                'parent_id': cat_info['parent_id'] if cat_info['parent_id'] != '0' else None
                            }
                            if hierarchy not in category_hierarchy:
                                category_hierarchy.append(hierarchy)
                            
                            # 添加父分类
                            current_parent_id = cat_info['parent_id']
                            while current_parent_id and current_parent_id != '0':
                                parent = category_map.get(current_parent_id)
                                if parent:
                                    parent_name = parent['category']
                                    if parent_name and parent_name not in categories:
                                        categories.append(parent_name)
                                    
                                    parent_hierarchy = {
                                        'category': parent_name,
                                        'category_id': current_parent_id,
                                        'parent_id': parent['parent_id'] if parent['parent_id'] != '0' else None
                                    }
                                    if parent_hierarchy not in category_hierarchy:
                                        category_hierarchy.append(parent_hierarchy)
                                    
                                    current_parent_id = parent['parent_id']
                                else:
                                    break
                    
                    # 构建药品文档
                    processed_drug = {
                        'id': drug_id,
                        'name': self.normalizer.standardize_name(drug['name']),
                        'spec': self.normalizer.standardize_spec(drug['spec']),
                        'create_time': create_time,
                        'categories': categories,
                        'category_hierarchy': category_hierarchy,
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
                self.logger.error(f"处理药品 {drug_id} 时发生错误: {str(e)}")
        
        self.logger.info(f"药品处理完成:")
        self.logger.info(f"- 成功处理: {len(processed_drugs)} 个药品")
        failed_count = len(drugs_df) - len(processed_drugs)
        if failed_count > 0:
            self.logger.warning(f"- 处理失败: {failed_count} 个药品")
        
        return processed_drugs

    def run(self, output_dir: Optional[str] = None, clear_indices: bool = False) -> None:
        """运行数据处理管道
        
        Args:
            output_dir: 输出目录路径，用于保存中间结果
            clear_indices: 是否清空现有索引
        """
        try:
            # 1. 获取数据
            drugs_df, drug_details_df, categories_df = self.fetch_data()
            
            # 2. 预处理详情数据
            processed_details = self.process_drug_details(drug_details_df)
            
            # 3. 处理药品数据
            processed_drugs = self.process_drugs(drugs_df, processed_details, categories_df)
            
            # 4. 保存中间结果（如果指定了输出目录）
            if output_dir:
                self.save_intermediate_results(processed_drugs, output_dir)
            
            # 5. 更新ES索引
            self.logger.info("更新Elasticsearch索引...")
            indexer = DrugIndexer(self.es_config)
            if clear_indices:
                self.logger.info("清空现有索引...")
                indexer.clear_all_indices()
            self.logger.info("创建索引...")
            indexer.create_indices()
            self.logger.info("开始索引数据...")
            indexer.index_drugs(processed_drugs)
            self.logger.info("索引更新完成")
            
        except Exception as e:
            self.logger.error(f"管道运行失败: {str(e)}")
            raise

    def save_intermediate_results(self, processed_drugs: List[Dict], output_dir: str) -> None:
        """保存中间结果
        
        Args:
            processed_drugs: 处理后的药品列表
            output_dir: 输出目录路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存处理后的数据
        with open(output_path / 'processed_drugs.json', 'w', encoding='utf-8') as f:
            json.dump(processed_drugs, f, ensure_ascii=False, indent=2)

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='处理药品数据并建立ES索引')
    parser.add_argument('--output-dir', type=str, help='输出目录路径，用于保存中间结果')
    parser.add_argument('--clear', action='store_true', help='是否清空现有索引')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    args = parser.parse_args()
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 确保所需目录存在
        ensure_directories(config)
        
        # 从环境变量读取配置（PostgreSQL）
        db_url = (
            f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'medical')}"
        )
        
        es_config = {
            'hosts': [os.getenv('ELASTIC_HOST', 'http://localhost:9200')],
            'basic_auth': (
                os.getenv('ELASTIC_USERNAME', 'elastic'),
                os.getenv('ELASTIC_PASSWORD', 'changeme')
            )
        }
        
        # 初始化并运行管道
        pipeline = DrugPipeline(db_url=db_url, es_config=es_config)
        
        # 运行管道
        pipeline.run(
            output_dir=args.output_dir or "outputs",  # 默认输出目录
            clear_indices=args.clear
        )
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
