#!/usr/bin/env python3
"""
预处理ATC药品编码-2022数据

目的：
1. 去重：确保每个通用名只对应一个实体
2. 清洗：处理数据质量问题
3. 输出：生成干净的实体基准表
"""

import pandas as pd
from pathlib import Path

def preprocess_atc_data(input_file: str, output_file: str):
    """预处理ATC数据"""
    
    print("="*80)
    print("ATC药品编码-2022数据预处理")
    print("="*80)
    
    # 1. 加载数据
    print("\n1. 加载原始数据...")
    df = pd.read_csv(input_file, low_memory=False)
    print(f"   - 原始行数: {len(df):,}")
    print(f"   - 列数: {len(df.columns)}")
    
    # 2. 基本统计
    print("\n2. 数据统计...")
    print(f"   - 唯一通用名: {df['西药药品名称'].nunique():,}")
    print(f"   - 唯一药品代码: {df['西药药品代码'].nunique():,}")
    print(f"   - 唯一ATC1: {df['ATC1'].nunique()}")
    print(f"   - 唯一ATC2: {df['ATC2'].nunique()}")
    print(f"   - 唯一ATC3: {df['ATC3'].nunique()}")
    print(f"   - 唯一药品分类: {df['药品分类'].nunique()}")
    
    # 3. 检查通用名与药品代码的关系
    print("\n3. 检查数据一致性...")
    
    # 按通用名分组，检查是否有多个药品代码
    name_code_mapping = df.groupby('西药药品名称')['西药药品代码'].unique()
    multiple_codes = name_code_mapping[name_code_mapping.apply(len) > 1]
    
    if len(multiple_codes) > 0:
        print(f"   ⚠️  发现 {len(multiple_codes)} 个通用名对应多个药品代码")
        print(f"   示例：")
        for name, codes in list(multiple_codes.head(3).items()):
            print(f"     - {name}: {codes}")
    else:
        print(f"   ✅ 所有通用名都唯一对应一个药品代码")
    
    # 4. 按通用名去重（保留第一条记录）
    print("\n4. 按通用名去重...")
    df_unique = df.drop_duplicates(subset=['西药药品名称'], keep='first')
    print(f"   - 去重后行数: {len(df_unique):,}")
    print(f"   - 减少: {len(df) - len(df_unique):,} 条")
    
    # 5. 数据清洗
    print("\n5. 数据清洗...")
    
    # 去除空通用名
    before = len(df_unique)
    df_unique = df_unique[df_unique['西药药品名称'].notna()]
    df_unique = df_unique[df_unique['西药药品名称'].str.strip() != '']
    print(f"   - 去除空通用名: {before - len(df_unique)} 条")
    
    # 去除空药品代码
    before = len(df_unique)
    df_unique = df_unique[df_unique['西药药品代码'].notna()]
    print(f"   - 去除空药品代码: {before - len(df_unique)} 条")
    
    # 6. 选择必要的列
    print("\n6. 选择输出列...")
    output_columns = [
        'ATC1', 'ATC1名称',
        'ATC2', 'ATC2名称',
        'ATC3', 'ATC3名称',
        '药品分类', '药品分类名称',
        '西药药品代码', '西药药品名称',
        '剂型'
    ]
    
    df_output = df_unique[output_columns].copy()
    
    # 7. 按ATC分类排序
    print("\n7. 数据排序...")
    df_output = df_output.sort_values(['ATC1', 'ATC2', 'ATC3', '药品分类', '西药药品名称'])
    
    # 8. 保存结果
    print("\n8. 保存结果...")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"   ✅ 保存到: {output_file}")
    
    # 9. 统计报告
    print("\n9. 最终统计:")
    print(f"   - 输出实体数: {len(df_output):,}")
    print(f"   - ATC1分类数: {df_output['ATC1'].nunique()}")
    print(f"   - ATC2分类数: {df_output['ATC2'].nunique()}")
    print(f"   - ATC3分类数: {df_output['ATC3'].nunique()}")
    print(f"   - 药品分类数: {df_output['药品分类'].nunique()}")
    
    # 按ATC1统计
    print("\n   ATC1分布:")
    atc1_counts = df_output.groupby(['ATC1', 'ATC1名称']).size().sort_values(ascending=False)
    for (code, name), count in atc1_counts.head(10).items():
        print(f"     {code} {name}: {count:,}")
    
    print("\n" + "="*80)
    print("预处理完成!")
    print("="*80)
    
    return df_output


def main():
    input_file = 'data/raw/drugs/ATC药品编码-2022.csv'
    output_file = 'data/processed/drugs/atc_entities_unique.csv'
    
    df = preprocess_atc_data(input_file, output_file)


if __name__ == '__main__':
    main()
