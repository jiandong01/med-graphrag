"""准备评估数据集：筛选50条是+50条否"""

import sys
import csv
import json
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shared import Config

def prepare_evaluation_dataset():
    """从CSV中筛选评估数据集（使用config.yaml配置）"""
    
    # 加载评估配置
    inference_config = Config.get_inference_config()
    eval_config = inference_config.get('evaluation', {})
    
    sample_size_yes = eval_config.get('sample_size_yes', 50)
    sample_size_no = eval_config.get('sample_size_no', 50)
    random_seed = eval_config.get('random_seed', 42)
    
    input_file = "data/raw/clinical_cases/超说明书用药判断结果-人工.csv"
    output_file = "data/raw/clinical_cases/evaluation_dataset.csv"
    output_json = "data/raw/clinical_cases/evaluation_dataset.json"
    
    print("="*80)
    print("准备评估数据集")
    print("="*80)
    print(f"\n配置: sample_size_yes={sample_size_yes}, sample_size_no={sample_size_no}, seed={random_seed}")
    print(f"输入: {input_file}")
    print(f"输出CSV: {output_file}")
    print(f"输出JSON: {output_json}")
    
    # 读取CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"\n总数据: {len(rows)} 行")
    
    # 筛选"是"和"否"的数据
    offlabel_yes = [r for r in rows if r.get('是否超适应症', '').strip() == '是']
    offlabel_no = [r for r in rows if r.get('是否超适应症', '').strip() == '否']
    
    print(f"\n筛选结果:")
    print(f"  是否超适应症='是': {len(offlabel_yes)} 条")
    print(f"  是否超适应症='否': {len(offlabel_no)} 条")
    
    # 随机抽取
    random.seed(random_seed)
    
    selected_yes = random.sample(offlabel_yes, min(sample_size_yes, len(offlabel_yes)))
    selected_no = random.sample(offlabel_no, min(sample_size_no, len(offlabel_no)))
    
    evaluation_set = selected_yes + selected_no
    random.shuffle(evaluation_set)  # 打乱顺序
    
    print(f"\n评估数据集:")
    print(f"  是否超适应症='是': {len(selected_yes)} 条")
    print(f"  是否超适应症='否': {len(selected_no)} 条")
    print(f"  总计: {len(evaluation_set)} 条")
    
    # 保存CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        if evaluation_set:
            fieldnames = evaluation_set[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(evaluation_set)
    
    print(f"\n✓ 已保存CSV: {output_file}")
    
    # 转换为JSON格式（方便脚本使用）
    json_data = []
    for row in evaluation_set:
        json_data.append({
            'disease_id': row.get('disease_id', ''),
            'disease_name': row.get('罕见病适应症', ''),
            'drug_id': row.get('drug_id', ''),
            'drug_name': row.get('标化后药名', ''),
            'manual_judgment': row.get('是否超适应症', ''),
            'group': row.get('group', ''),
            'approval_number': row.get('批准文号', '')
        })
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已保存JSON: {output_json}")
    
    # 显示样例
    print(f"\n样例数据（前3条）:")
    for i, item in enumerate(json_data[:3], 1):
        print(f"\n{i}. {item['drug_name']} + {item['disease_name']}")
        print(f"   人工判断: {item['manual_judgment']}")
    
    return evaluation_set

if __name__ == "__main__":
    prepare_evaluation_dataset()
