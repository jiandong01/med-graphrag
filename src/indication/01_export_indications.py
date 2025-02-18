import os
import json
import uuid
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from elasticsearch import Elasticsearch
from src.utils import get_elastic_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicationExporter:
    def __init__(self, es: Elasticsearch = None):
        self.es = es or get_elastic_client()
        self.drugs_index = 'drugs'
    
    def _generate_stable_uuid(self, text: str) -> str:
        """根据文本生成稳定的UUID
        
        使用文本的hash值作为UUID的种子，这样相同的文本会生成相同的UUID
        
        Args:
            text: 适应症文本
            
        Returns:
            str: UUID字符串
        """
        # 使用MD5生成稳定的hash值
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        # 使用hash值生成UUID
        return str(uuid.UUID(text_hash))
    
    def export_raw_indications(self, output_dir: str):
        """从drugs索引中导出所有原始适应症文本
        
        Args:
            output_dir: 输出目录路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 获取所有药品的适应症
        query = {
            "size": 10000,
            "_source": ["id", "name", "indications"],  # 只获取需要的字段
            "query": {
                "exists": {
                    "field": "indications"  # 只获取有适应症字段的文档
                }
            }
        }
        
        try:
            response = self.es.search(
                index=self.drugs_index,
                body=query
            )
            
            # 收集所有unique适应症文本
            unique_indications = {}  # 使用dict保存文本到药品的映射
            drug_indication_counts = {}  # 每个药品的适应症数量
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                drug_id = source.get('id')
                drug_name = source.get('name')
                indications = source.get('indications', [])
                
                if isinstance(indications, str):
                    indications = [indications]
                
                # 记录每个药品的适应症数量
                drug_indication_counts[drug_id] = len(indications)
                
                for indication in indications:
                    if indication:  # 忽略空字符串
                        if indication not in unique_indications:
                            unique_indications[indication] = {
                                'id': self._generate_stable_uuid(indication),  # 添加稳定的UUID
                                'text': indication,
                                'drugs': []
                            }
                        unique_indications[indication]['drugs'].append({
                            'id': drug_id,
                            'name': drug_name
                        })
            
            # 转换为列表并按文本排序
            indication_list = list(unique_indications.values())
            indication_list.sort(key=lambda x: x['text'])
            
            # 生成统计信息
            stats = {
                'total_unique_indications': len(indication_list),
                'total_drugs': len(drug_indication_counts),
                'avg_indications_per_drug': sum(drug_indication_counts.values()) / len(drug_indication_counts) if drug_indication_counts else 0,
                'extraction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'indication_stats': {
                    'min_drugs': min(len(ind['drugs']) for ind in indication_list),
                    'max_drugs': max(len(ind['drugs']) for ind in indication_list),
                    'avg_drugs': sum(len(ind['drugs']) for ind in indication_list) / len(indication_list)
                },
                'drug_stats': {
                    'min_indications': min(drug_indication_counts.values()),
                    'max_indications': max(drug_indication_counts.values()),
                    'avg_indications': sum(drug_indication_counts.values()) / len(drug_indication_counts)
                }
            }
            
            # 保存到文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = output_path / f'raw_indications_{timestamp}.json'
            
            # 组合数据和统计信息
            output_data = {
                'data': indication_list,
                'stats': stats
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 输出日志信息
            logger.info(f"Successfully exported {len(indication_list)} unique raw indications to {output_file}")
            logger.info(f"Total drugs processed: {stats['total_drugs']}")
            logger.info(f"\nIndication statistics:")
            logger.info(f"  Min drugs per indication: {stats['indication_stats']['min_drugs']}")
            logger.info(f"  Max drugs per indication: {stats['indication_stats']['max_drugs']}")
            logger.info(f"  Avg drugs per indication: {stats['indication_stats']['avg_drugs']:.2f}")
            
            logger.info(f"\nDrug statistics:")
            logger.info(f"  Min indications per drug: {stats['drug_stats']['min_indications']}")
            logger.info(f"  Max indications per drug: {stats['drug_stats']['max_indications']}")
            logger.info(f"  Avg indications per drug: {stats['drug_stats']['avg_indications']:.2f}")
            
        except Exception as e:
            logger.error(f"Error exporting indications: {str(e)}")
            raise

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export raw indications from drugs index')
    parser.add_argument('--output-dir', type=str, default='outputs/',
                      help='Directory to save the exported indications')
    
    args = parser.parse_args()
    
    exporter = IndicationExporter()
    exporter.export_raw_indications(args.output_dir)

if __name__ == '__main__':
    main()
