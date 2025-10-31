"""分析评估数据集（100条：50是+50否）"""

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
from app.shared import load_env

load_env()

def analyze_clinical_case(engine: InferenceEngine, row: Dict[str, str]) -> Dict[str, Any]:
    """分析单个临床病例"""
    disease_name = row.get('罕见病适应症', '').strip()
    drug_name = row.get('标化后药名', '').strip()
    
    if not disease_name or not drug_name:
        return {'error': '缺少疾病或药品名称'}
    
    # 构建输入
    input_data = {
        'drug_name': drug_name,
        'disease_name': disease_name,
        'description': f"患者诊断为{disease_name}，拟使用{drug_name}治疗",
    }
    
    try:
        return engine.analyze(input_data)
    except Exception as e:
        return {'error': str(e)}

def main():
    # 文件路径
    input_file = "data/raw/clinical_cases/evaluation_dataset.csv"
    output_file = "data/raw/clinical_cases/evaluation_results.jsonl"
    
    print("="*80)
    print("评估数据集分析（100条）")
    print("="*80)
    print(f"\n输入: {input_file}")
    print(f"输出: {output_file}")
    
    # 检查文件
    if not Path(input_file).exists():
        print(f"\n错误：{input_file} 不存在")
        print("请先运行: python scripts/prepare_evaluation_dataset.py")
        return
    
    # 初始化引擎（从config读取配置）
    print("\n初始化推理引擎（从config.yaml读取配置）...")
    engine = InferenceEngine()
    
    # 读取数据
    with open(input_file, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    
    print(f"数据量: {len(rows)} 条")
    
    # 统计
    manual_yes = len([r for r in rows if r.get('是否超适应症') == '是'])
    manual_no = len([r for r in rows if r.get('是否超适应症') == '否'])
    print(f"人工判断: 是={manual_yes}, 否={manual_no}")
    
    # 确认
    limit_input = input(f"\n处理全部{len(rows)}条？输入数字限制数量，或回车继续: ").strip()
    if limit_input.isdigit():
        rows = rows[:int(limit_input)]
        print(f"将只处理前 {limit_input} 条")
    
    if input(f"\n开始分析{len(rows)}条数据？(yes/no): ").lower() != 'yes':
        print("已取消")
        return
    
    # 分析
    print("\n开始分析...")
    start_time = datetime.now()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in enumerate(tqdm(rows, desc="分析进度"), 1):
            result = analyze_clinical_case(engine, row)
            
            output_row = {
                'row_number': idx,
                'disease_name': row.get('罕见病适应症', ''),
                'drug_name': row.get('标化后药名', ''),
                'manual_judgment': row.get('是否超适应症', ''),
                'system_analysis': result,
                'analysis_time': datetime.now().isoformat()
            }
            
            f.write(json.dumps(output_row, ensure_ascii=False) + '\n')
            f.flush()
    
    # 统计
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n分析完成！耗时: {elapsed:.1f}秒 (平均{elapsed/len(rows):.1f}秒/条)")
    print(f"结果: {output_file}")
    
    print("\n下一步:")
    print(f"  python scripts/evaluate_results.py --input {output_file}")

if __name__ == "__main__":
    main()
