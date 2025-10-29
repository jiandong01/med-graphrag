"""疾病数据索引管理 - 将提取的疾病导入Elasticsearch"""

import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from app.shared import get_es_client, setup_logging

logger = setup_logging("disease_indexer")


class DiseaseIndexer:
    """疾病索引管理"""
    
    def __init__(self):
        self.es = get_es_client()
        self.diseases_index = 'diseases'
        logger.info("DiseaseIndexer初始化完成")
    
    def create_index(self, delete_if_exists: bool = False):
        """创建疾病索引
        
        Args:
            delete_if_exists: 是否删除已存在的索引
        """
        if delete_if_exists and self.es.indices.exists(index=self.diseases_index):
            logger.info(f"删除已存在的索引: {self.diseases_index}")
            self.es.indices.delete(index=self.diseases_index)
        
        if not self.es.indices.exists(index=self.diseases_index):
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "type": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "sub_diseases": {"type": "keyword"},
                        "related_diseases": {"type": "keyword"},
                        "confidence_score": {"type": "float"},
                        "mention_count": {"type": "integer"},
                        "source_drugs": {
                            "type": "nested",
                            "properties": {
                                "drug_id": {"type": "keyword"},
                                "drug_name": {"type": "text"},
                                "extraction_time": {"type": "date"}
                            }
                        },
                        "first_seen": {"type": "date"},
                        "last_updated": {"type": "date"}
                    }
                }
            }
            
            self.es.indices.create(index=self.diseases_index, body=mapping)
            logger.info(f"✅ 创建疾病索引: {self.diseases_index}")
    
    def load_diseases_from_batches(
        self,
        batches_dir: str = "data/processed/diseases/diseases_search_after"
    ) -> Dict[str, Dict]:
        """从批次文件加载并聚合疾病数据
        
        Args:
            batches_dir: 批次文件目录
            
        Returns:
            Dict: 聚合后的疾病字典 {disease_name: disease_data}
        """
        diseases = defaultdict(lambda: {
            'name': None,
            'type': 'disease',
            'category': '',
            'sub_diseases': set(),
            'related_diseases': set(),
            'confidence_scores': [],
            'source_drugs': [],
            'mention_count': 0
        })
        
        batches_path = Path(batches_dir)
        batch_files = sorted(batches_path.glob("batch_*.json"))
        
        logger.info(f"开始加载 {len(batch_files)} 个批次文件...")
        
        for idx, batch_file in enumerate(batch_files, 1):
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch = json.load(f)
            
            for extraction in batch.get('extractions', []):
                drug_id = extraction['drug_id']
                drug_name = extraction['drug_name']
                extraction_time = extraction['extraction_time']
                
                for disease_info in extraction.get('diseases', []):
                    disease_name = disease_info['name']
                    disease_data = diseases[disease_name]
                    
                    # 更新疾病信息
                    if disease_data['name'] is None:
                        disease_data['name'] = disease_name
                    
                    disease_data['type'] = disease_info.get('type', 'disease')
                    disease_data['confidence_scores'].append(
                        disease_info.get('confidence_score', 0.95)
                    )
                    disease_data['mention_count'] += 1
                    
                    # 添加来源药品
                    disease_data['source_drugs'].append({
                        'drug_id': drug_id,
                        'drug_name': drug_name,
                        'extraction_time': extraction_time
                    })
                    
                    # 收集子疾病和相关疾病
                    for sub in disease_info.get('sub_diseases', []):
                        if isinstance(sub, dict):
                            disease_data['sub_diseases'].add(sub.get('name', ''))
                        elif sub:
                            disease_data['sub_diseases'].add(str(sub))
                    
                    for related in disease_info.get('related_diseases', []):
                        if isinstance(related, dict):
                            disease_data['related_diseases'].add(related.get('name', ''))
                        elif related:
                            disease_data['related_diseases'].add(str(related))
            
            if idx % 50 == 0:
                logger.info(f"已处理 {idx}/{len(batch_files)} 批次...")
        
        logger.info(f"✅ 加载完成: 共 {len(diseases)} 个独特疾病")
        
        # 转换为最终格式
        final_diseases = {}
        for disease_name, data in diseases.items():
            final_diseases[disease_name] = {
                'id': f"disease_{abs(hash(disease_name)) % 1000000:06d}",
                'name': data['name'],
                'type': data['type'],
                'category': data['category'],
                'sub_diseases': list(data['sub_diseases']),
                'related_diseases': list(data['related_diseases']),
                'avg_confidence': sum(data['confidence_scores']) / len(data['confidence_scores']) if data['confidence_scores'] else 0.95,
                'mention_count': data['mention_count'],
                'source_drugs': data['source_drugs'][:10],  # 只保留前10个来源
                'first_seen': data['source_drugs'][0]['extraction_time'] if data['source_drugs'] else None,
                'last_updated': data['source_drugs'][-1]['extraction_time'] if data['source_drugs'] else None
            }
        
        return final_diseases
    
    def index_diseases(self, diseases: Dict[str, Dict], batch_size: int = 500):
        """批量索引疾病到ES
        
        Args:
            diseases: 疾病字典
            batch_size: 批次大小
        """
        from elasticsearch.helpers import bulk
        
        # 准备批量索引数据
        actions = []
        for disease_name, disease_data in diseases.items():
            action = {
                '_index': self.diseases_index,
                '_id': disease_data['id'],
                '_source': disease_data
            }
            actions.append(action)
        
        logger.info(f"开始批量索引 {len(actions)} 个疾病...")
        
        # 批量索引
        success, failed = bulk(
            self.es,
            actions,
            chunk_size=batch_size,
            raise_on_error=False
        )
        
        logger.info(f"✅ 索引完成: 成功 {success}, 失败 {failed}")
        
        return success, failed
    
    def run(
        self,
        batches_dir: str = "data/processed/diseases/diseases_search_after",
        rebuild: bool = False
    ):
        """完整流程：加载 → 索引
        
        Args:
            batches_dir: 批次文件目录
            rebuild: 是否重建索引
        """
        logger.info("=" * 50)
        logger.info("疾病索引构建流程")
        logger.info("=" * 50)
        
        # 1. 创建索引
        self.create_index(delete_if_exists=rebuild)
        
        # 2. 加载疾病数据
        diseases = self.load_diseases_from_batches(batches_dir)
        logger.info(f"共加载 {len(diseases)} 个独特疾病")
        
        # 3. 索引到ES
        success, failed = self.index_diseases(diseases)
        
        # 4. 验证
        count = self.es.count(index=self.diseases_index)
        logger.info(f"✅ ES中疾病总数: {count['count']}")
        
        logger.info("=" * 50)
        logger.info("流程完成！")
        logger.info("=" * 50)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='疾病索引构建')
    parser.add_argument('--rebuild', action='store_true', help='重建索引')
    parser.add_argument('--batches-dir', default='data/processed/diseases/diseases_search_after', help='批次目录')
    
    args = parser.parse_args()
    
    indexer = DiseaseIndexer()
    indexer.run(batches_dir=args.batches_dir, rebuild=args.rebuild)


if __name__ == '__main__':
    main()
