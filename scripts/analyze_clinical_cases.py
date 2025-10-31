"""分析临床病例CSV文件的超适应症判断"""

import os
import sys
import csv
import json
from pathlib import Path
from typing import Dict, Any
from tqdm import tqdm
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.inference.engine import InferenceEngine
from app.shared import load_env, Config

load_env()

# 加载inference配置
inference_config = Config.get_inference_config()

def analyze_clinical_case(engine: InferenceEngine, row: Dict[str, str]) -> Dict[str, Any]:
    """分析单个临床病例
    
    Args:
        engine: 推理引擎
        row: CSV行数据
        
    Returns:
        分析结果
    """
    # 构建输入数据
    disease_name = row.get('罕见病适应症', '').strip()
    drug_name = row.get('标化后药名', '').strip()
    
    if not disease_name or not drug_name:
        return {
            'error': '缺少疾病或药品名称',
            'disease': disease_name,
            'drug': drug_name
        }
    
    # 构建输入（快速模式：直接使用drug_name和disease_name）
    input_data = {
        'drug_name': drug_name,
        'disease_name': disease_name,
        'description': f"患者诊断为{disease_name}，拟使用{drug_name}治疗",
        'patient_info': {
            'age': 30,
            'gender': '男'
        },
        'prescription': {
            'drug': drug_name
        }
    }
    
    try:
        # 调用推理引擎（快速模式）
        result = engine.analyze(input_data)
        return result
    
    except Exception as e:
        return {
            'error': str(e),
            'disease': disease_name,
            'drug': drug_name
        }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='分析临床病例超适应症')
    parser.add_argument('--input', default='data/raw/clinical_cases/evaluation_dataset.csv',
                       help='输入CSV文件（默认使用评估数据集）')
    parser.add_argument('--output', default='data/raw/clinical_cases/evaluation_results.jsonl',
                       help='输出JSONL文件')
    parser.add_argument('--use-full-dataset', action='store_true',
                       help='使用完整数据集而非评估数据集')
    
    args = parser.parse_args()
    
    # 根据参数选择输入文件
    if args.use_full_dataset:
        input_file = "data/raw/clinical_cases/超说明书用药判断结果-人工.csv"
        output_file = "data/raw/clinical_cases/超说明书用药判断结果-系统分析.jsonl"
    else:
        input_file = args.input
        output_file = args.output
    
    print("="*80)
    print("临床病例超适应症分析")
    print("="*80)
    print(f"\n输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    
    # 初始化推理引擎（从config读取或显式指定）
    print("\n初始化推理引擎...")
    engine = InferenceEngine()  # 从config.yaml读取skip_entity_recognition
    
    # 读取CSV
    print("\n读取CSV文件...")
    if not Path(input_file).exists():
        print(f"错误：文件不存在 {input_file}")
        print("\n提示：请先运行 python scripts/prepare_evaluation_dataset.py 生成评估数据集")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"共读取 {len(rows)} 行数据")
    
    # 询问是否限制处理数量
    limit = input("\n是否限制处理数量？(输入数字或回车跳过): ").strip()
    if limit.isdigit():
        limit = int(limit)
        rows = rows[:limit]
        print(f"将只处理前 {limit} 行")
    
    confirm = input(f"\n确认开始分析 {len(rows)} 个病例? (yes/no): ")
    if confirm.lower() != 'yes':
        print("已取消")
        return
    
    # 分析每一行
    print(f"\n开始分析...")
    results = []
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in enumerate(tqdm(rows, desc="分析进度"), 1):
            # 分析
            result = analyze_clinical_case(engine, row)
            
            # 添加原始数据
            output_row = {
                'row_number': idx,
                'disease_id': row.get('disease_id', ''),
                'disease_name': row.get('罕见病适应症', ''),
                'drug_id': row.get('drug_id', ''),
                'drug_name': row.get('标化后药名', ''),
                'manual_judgment': row.get('是否超适应症', ''),
                'system_analysis': result,
                'analysis_time': datetime.now().isoformat()
            }
            
            # 写入JSONL
            f.write(json.dumps(output_row, ensure_ascii=False) + '\n')
            f.flush()
            
            results.append(output_row)
            
            # 每10个显示一次进度
            if idx % 10 == 0:
                success = len([r for r in results if 'error' not in r['system_analysis']])
                print(f"\n已处理 {idx}/{len(rows)}, 成功 {success}")
    
    # 统计
    print("\n" + "="*80)
    print("分析完成")
    print("="*80)
    
    success_count = len([r for r in results if 'error' not in r['system_analysis']])
    error_count = len(results) - success_count
    
    print(f"\n总处理数: {len(results)}")
    print(f"成功: {success_count}")
    print(f"失败: {error_count}")
    
    # 统计超适应症判断
    offlabel_true = len([r for r in results 
                        if 'error' not in r['system_analysis'] 
                        and r['system_analysis'].get('is_offlabel') == True])
    offlabel_false = len([r for r in results 
                         if 'error' not in r['system_analysis'] 
                         and r['system_analysis'].get('is_offlabel') == False])
    
    print(f"\n超适应症判断:")
    print(f"  is_offlabel=True (超适应症): {offlabel_true}")
    print(f"  is_offlabel=False (标准用药): {offlabel_false}")
    
    # 与人工判断对比
    manual_yes = len([r for r in results if r['manual_judgment'] == '是'])
    manual_no = len([r for r in results if r['manual_judgment'] == '否'])
    
    print(f"\n人工判断:")
    print(f"  是 (超适应症): {manual_yes}")
    print(f"  否 (标准用药): {manual_no}")
    
    print(f"\n结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
