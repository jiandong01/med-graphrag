"""命令行工具"""

import argparse
from pathlib import Path

from app.src.indication.indications import IndicationProcessor
from app.src.indication.diseases import DiseaseManager
from app.src.utils import setup_logging, load_env, load_config, ensure_directories

logger = setup_logging(__name__)

# Load environment variables
load_env()

def process_indications(args):
    """处理适应症命令"""
    processor = IndicationProcessor()
    
    # 导出原始适应症
    logger.info("开始导出原始适应症...")
    indications = processor.export_raw_indications(args.output_dir)
    
    if args.extract:
        # 提取疾病信息
        logger.info("开始提取疾病信息...")
        processor.extract_diseases(indications, args.output_dir)

def process_diseases(args):
    """处理疾病命令"""
    manager = DiseaseManager()
    
    # 创建索引
    manager.create_index(clear_existing=args.clear)
    
    # 处理并索引疾病数据
    diseases = manager.process_diseases(args.data_dir)
    manager.index_diseases(diseases)
    
    # 显示示例
    if args.examples > 0:
        logger.info("\n处理后的疾病文档示例:")
        import json
        for disease in diseases[:args.examples]:
            print("\n" + "="*50)
            print(json.dumps(disease, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description='医疗数据处理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 适应症处理命令
    indication_parser = subparsers.add_parser('indications', help='处理适应症数据')
    indication_parser.add_argument(
        '--output-dir',
        type=str,
        default='src/indication/data',
        help='输出目录路径'
    )
    indication_parser.add_argument(
        '--extract',
        action='store_true',
        help='是否提取疾病信息'
    )
    
    # 疾病处理命令
    disease_parser = subparsers.add_parser('diseases', help='处理疾病数据')
    disease_parser.add_argument(
        '--data-dir',
        type=str,
        default='src/indication/data',
        help='包含疾病JSON数据的目录路径'
    )
    disease_parser.add_argument(
        '--clear',
        action='store_true',
        help='是否清除现有索引'
    )
    disease_parser.add_argument(
        '--examples',
        type=int,
        default=1,
        help='显示示例数量'
    )
    
    args = parser.parse_args()
    
    if args.command == 'indications':
        process_indications(args)
    elif args.command == 'diseases':
        process_diseases(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
