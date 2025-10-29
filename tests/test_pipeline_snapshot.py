"""Pipeline模块测试 - 药品处理和疾病提取"""

import pytest
import json
from pathlib import Path
from app.shared import get_es_client, Config

Config.load_env()


class TestDrugData:
    """测试药品数据处理"""
    
    def test_load_processed_drugs(self):
        """测试加载处理后的药品数据"""
        drugs_file = Path("data/raw/drugs/processed_drugs.json")
        assert drugs_file.exists(), "药品数据文件不存在"
        
        with open(drugs_file, 'r', encoding='utf-8') as f:
            drugs = json.load(f)
        
        print(f"\n✅ 成功加载药品数据")
        print(f"  总数: {len(drugs)}")
        
        # 检查数据结构
        sample = drugs[0]
        print(f"  示例药品: {sample.get('name')}")
        print(f"  字段: {list(sample.keys())}")
        
        assert len(drugs) > 80000, "药品数量异常"
        assert 'id' in sample, "缺少id字段"
        assert 'name' in sample, "缺少name字段"
        assert 'indications' in sample, "缺少indications字段"
    
    def test_drug_in_elasticsearch(self):
        """测试药品是否在ES中"""
        es = get_es_client()
        
        # 查询总数
        count = es.count(
            index='drugs',
            body={'query': {'match_all': {}}}
        )
        
        print(f"\n✅ ES中的药品数量: {count['count']}")
        
        # 查询示例
        result = es.search(
            index='drugs',
            body={
                'query': {'match': {'name': '阿司匹林'}},
                'size': 1
            }
        )
        
        if result['hits']['hits']:
            drug = result['hits']['hits'][0]['_source']
            print(f"  示例药品: {drug.get('name')}")
            print(f"  适应症数: {len(drug.get('indications', []))}")
        
        assert count['count'] > 80000, "ES中药品数量异常"


class TestDiseaseExtraction:
    """测试疾病提取"""
    
    def test_load_disease_batches(self):
        """测试加载疾病提取批次"""
        diseases_dir = Path("data/processed/diseases/diseases_search_after")
        assert diseases_dir.exists(), "疾病数据目录不存在"
        
        batch_files = list(diseases_dir.glob("batch_*.json"))
        print(f"\n✅ 找到批次文件数: {len(batch_files)}")
        
        # 加载第一个批次
        if batch_files:
            with open(batch_files[0], 'r', encoding='utf-8') as f:
                batch = json.load(f)
            
            print(f"  批次示例: batch_{batch['batch_number']:05d}")
            print(f"  药品数: {batch['drugs_count']}")
            print(f"  提取成功: {batch['success_count']}")
            print(f"  提取失败: {batch['failure_count']}")
            
            if batch['extractions']:
                extraction = batch['extractions'][0]
                print(f"  示例提取:")
                print(f"    药品: {extraction['drug_name']}")
                print(f"    疾病数: {len(extraction['diseases'])}")
                if extraction['diseases']:
                    print(f"    疾病示例: {extraction['diseases'][0]['name']}")
        
        assert len(batch_files) > 300, "批次文件数量异常"
    
    def test_load_extraction_state(self):
        """测试加载提取状态"""
        state_file = Path("data/processed/states/extraction_states/extraction_search_after_state.json")
        assert state_file.exists(), "状态文件不存在"
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        print(f"\n✅ 提取任务状态:")
        print(f"  已处理: {state['processed_count']}/{state['total_count']}")
        print(f"  成功率: {state['success_count']/(state['success_count']+state['failure_count'])*100:.2f}%")
        print(f"  当前批次: {state['current_batch']}")
        print(f"  已处理药品ID数: {len(state['processed_drug_ids'])}")
        
        assert state['processed_count'] > 60000, "处理数量异常"
        assert state['success_count'] > 0, "成功数为0"
    
    def test_extract_diseases_from_batch(self):
        """测试从批次文件中统计疾病"""
        diseases_dir = Path("data/processed/diseases/diseases_search_after")
        batch_files = list(diseases_dir.glob("batch_*.json"))[:10]  # 测试前10个批次
        
        all_diseases = set()
        total_extractions = 0
        
        for batch_file in batch_files:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch = json.load(f)
            
            for extraction in batch.get('extractions', []):
                total_extractions += 1
                for disease in extraction.get('diseases', []):
                    all_diseases.add(disease['name'])
        
        print(f"\n✅ 前10批次统计:")
        print(f"  提取记录数: {total_extractions}")
        print(f"  独特疾病数: {len(all_diseases)}")
        print(f"  疾病示例: {list(all_diseases)[:10]}")
        
        assert len(all_diseases) > 100, "疾病种类过少"


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
