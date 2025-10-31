"""Pipeline端到端测试 - 验证数据ETL流程

测试数据从原始MySQL到Elasticsearch的完整ETL过程
每个测试步骤都会输出详细的输入输出
"""

import pytest
import json
from pathlib import Path
from app.shared import get_es_client, Config

Config.load_env()


class TestDrugETL:
    """测试药品ETL流程: MySQL → processed_drugs.json → Elasticsearch"""
    
    def test_step1_processed_drugs_file(self):
        """步骤1: 验证处理后的药品文件"""
        print("\n" + "=" * 80)
        print("步骤1: 检查 processed_drugs.json")
        print("=" * 80)
        
        drugs_file = Path("data/raw/drugs/processed_drugs.json")
        
        print(f"\n【输入】")
        print(f"  文件路径: {drugs_file}")
        
        assert drugs_file.exists(), "❌ 药品数据文件不存在"
        
        with open(drugs_file, 'r', encoding='utf-8') as f:
            drugs = json.load(f)
        
        print(f"\n【输出】")
        print(f"  ✅ 文件加载成功")
        print(f"  药品总数: {len(drugs):,}")
        
        # 检查数据结构
        sample = drugs[0]
        print(f"\n  示例药品:")
        print(f"    名称: {sample.get('name')}")
        print(f"    ID: {sample.get('id')}")
        print(f"    适应症数: {len(sample.get('indications', []))}")
        print(f"    成分数: {len(sample.get('components', []))}")
        print(f"    必需字段: {', '.join(sample.keys())}")
        
        # 验证
        assert len(drugs) > 80000, "药品数量异常"
        assert 'id' in sample, "缺少id字段"
        assert 'name' in sample, "缺少name字段"
        assert 'indications' in sample, "缺少indications字段"
    
    def test_step2_elasticsearch_drugs_index(self):
        """步骤2: 验证Elasticsearch中的drugs索引"""
        print("\n" + "=" * 80)
        print("步骤2: 检查 Elasticsearch drugs索引")
        print("=" * 80)
        
        es = get_es_client()
        
        print(f"\n【输入】")
        print(f"  ES连接: {es.info()['cluster_name']}")
        print(f"  索引名: drugs")
        
        # 检查索引存在
        assert es.indices.exists(index='drugs'), "❌ drugs索引不存在"
        
        # 统计数量
        total = es.count(index='drugs', body={'query': {'match_all': {}}})
        with_indications = es.count(
            index='drugs',
            body={'query': {'exists': {'field': 'indications_list'}}}
        )
        
        print(f"\n【输出】")
        print(f"  ✅ 索引存在")
        print(f"  药品总数: {total['count']:,}")
        print(f"  有indications_list的药品: {with_indications['count']:,}")
        
        # 查询示例
        result = es.search(
            index='drugs',
            body={'query': {'match': {'name': '阿司匹林'}}, 'size': 1}
        )
        
        if result['hits']['hits']:
            drug = result['hits']['hits'][0]['_source']
            print(f"\n  示例药品:")
            print(f"    名称: {drug['name']}")
            print(f"    ID: {drug.get('id', 'N/A')[:40]}...")
            print(f"    indications_list: {len(drug.get('indications_list', []))} 项")
            if drug.get('indications_list'):
                print(f"      {drug['indications_list'][:3]}")
            print(f"    contraindications: {len(drug.get('contraindications', []))} 项")
        
        assert total['count'] > 80000, "❌ 药品数量异常"
    
    def test_step3_drug_search_functionality(self):
        """步骤3: 验证药品搜索功能"""
        print("\n" + "=" * 80)
        print("步骤3: 测试药品搜索功能")
        print("=" * 80)
        
        es = get_es_client()
        
        test_queries = ["美托洛尔", "阿莫西林", "地塞米松"]
        
        for query in test_queries:
            print(f"\n【输入】查询: '{query}'")
            
            result = es.search(
                index='drugs',
                body={
                    'query': {
                        'bool': {
                            'should': [
                                {'term': {'name.keyword': query}},
                                {'match_phrase': {'name': query}}
                            ]
                        }
                    },
                    'size': 3
                }
            )
            
            print(f"【输出】找到 {result['hits']['total']['value']} 个结果")
            for i, hit in enumerate(result['hits']['hits'][:3], 1):
                drug = hit['_source']
                print(f"  {i}. {drug['name']} (score: {hit['_score']:.2f})")


class TestDiseaseETL:
    """测试疾病ETL流程: drugs → disease_extraction → diseases索引"""
    
    def test_step1_disease_extraction_batches(self):
        """步骤1: 验证疾病提取批次文件"""
        print("\n" + "=" * 80)
        print("步骤1: 检查疾病提取批次文件")
        print("=" * 80)
        
        diseases_dir = Path("data/processed/diseases/diseases_search_after")
        
        print(f"\n【输入】")
        print(f"  目录: {diseases_dir}")
        
        assert diseases_dir.exists(), "❌ 疾病批次目录不存在"
        
        batch_files = list(diseases_dir.glob("batch_*.json"))
        
        print(f"\n【输出】")
        print(f"  ✅ 目录存在")
        print(f"  批次文件数: {len(batch_files)}")
        
        # 加载第一个批次
        if batch_files:
            with open(batch_files[0], 'r', encoding='utf-8') as f:
                batch = json.load(f)
            
            print(f"\n  示例批次 (batch_{batch['batch_number']:05d}):")
            print(f"    药品数: {batch['drugs_count']}")
            print(f"    提取成功: {batch['success_count']}")
            print(f"    提取失败: {batch['failure_count']}")
            print(f"    成功率: {batch['success_count']/(batch['success_count']+batch['failure_count'])*100:.1f}%")
            
            if batch['extractions']:
                ex = batch['extractions'][0]
                print(f"\n    示例提取记录:")
                print(f"      药品: {ex['drug_name']}")
                print(f"      疾病数: {len(ex['diseases'])}")
                if ex['diseases']:
                    print(f"      疾病示例: {[d['name'] for d in ex['diseases'][:3]]}")
        
        assert len(batch_files) > 300, "批次文件数量异常"
    
    def test_step2_extraction_state(self):
        """步骤2: 验证提取状态文件"""
        print("\n" + "=" * 80)
        print("步骤2: 检查提取状态")
        print("=" * 80)
        
        state_file = Path("data/processed/states/extraction_states/extraction_search_after_state.json")
        
        print(f"\n【输入】")
        print(f"  文件: {state_file}")
        
        assert state_file.exists(), "❌ 状态文件不存在"
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        print(f"\n【输出】")
        print(f"  ✅ 状态文件存在")
        print(f"  总药品数: {state['total_count']:,}")
        print(f"  已处理: {state['processed_count']:,}")
        print(f"  成功: {state['success_count']:,}")
        print(f"  失败: {state['failure_count']:,}")
        print(f"  当前批次: {state['current_batch']}")
        print(f"  进度: {state['processed_count']/state['total_count']*100:.1f}%")
        
        assert state['processed_count'] > 60000, "处理数量异常"
    
    def test_step3_diseases_index(self):
        """步骤3: 验证Elasticsearch中的diseases索引"""
        print("\n" + "=" * 80)
        print("步骤3: 检查 Elasticsearch diseases索引")
        print("=" * 80)
        
        es = get_es_client()
        
        print(f"\n【输入】")
        print(f"  ES连接: 已连接")
        print(f"  索引名: diseases")
        
        if not es.indices.exists(index='diseases'):
            print(f"\n【输出】")
            print("  ⚠️  diseases索引未创建")
            print("  提示: 运行 python -m app.pipeline.disease_indexer --rebuild")
            pytest.skip("diseases索引未创建")
        
        # 统计数量
        total = es.count(index='diseases')
        
        print(f"\n【输出】")
        print(f"  ✅ 索引存在")
        print(f"  疾病总数: {total['count']:,}")
        
        # Top疾病
        top_diseases = es.search(
            index='diseases',
            body={
                'query': {'match_all': {}},
                'sort': [{'mention_count': {'order': 'desc'}}],
                'size': 5
            }
        )
        
        print(f"\n  Top 5 疾病（按提及次数）:")
        for hit in top_diseases['hits']['hits']:
            d = hit['_source']
            print(f"    {d['name']}: {d['mention_count']}次, 来源药品{len(d.get('source_drugs', []))}个")
        
        assert total['count'] > 5000, "疾病数量异常"
    
    def test_step4_disease_drug_relationship(self):
        """步骤4: 验证疾病-药品双向关联"""
        print("\n" + "=" * 80)
        print("步骤4: 验证疾病-药品双向关联")
        print("=" * 80)
        
        es = get_es_client()
        
        if not es.indices.exists(index='diseases'):
            pytest.skip("diseases索引未创建")
        
        # 查询一个疾病
        result = es.search(
            index='diseases',
            body={'query': {'match': {'name': '高血压'}}, 'size': 1}
        )
        
        if not result['hits']['hits']:
            pytest.skip("未找到测试疾病")
        
        disease = result['hits']['hits'][0]['_source']
        disease_name = disease['name']
        source_drugs = disease.get('source_drugs', [])
        
        print(f"\n【输入】疾病: {disease_name}")
        print(f"【输出】")
        print(f"  疾病信息:")
        print(f"    ID: {disease['id']}")
        print(f"    提及次数: {disease['mention_count']}")
        print(f"    关联药品数: {len(source_drugs)}")
        
        # 验证反向关联
        if source_drugs:
            drug_id = source_drugs[0]['drug_id']
            drug_name = source_drugs[0]['drug_name']
            
            print(f"\n  验证反向关联:")
            print(f"    取第一个药品: {drug_name} ({drug_id})")
            
            # 在drugs索引中查询
            drug_result = es.get(index='drugs', id=drug_id)
            drug = drug_result['_source']
            
            print(f"    ✅ 药品存在于drugs索引")
            print(f"    药品名称: {drug['name']}")
            print(f"    适应症数: {len(drug.get('indications_list', []))}")
            
            # 检查适应症中是否提到了该疾病
            indications_text = ' '.join(drug.get('indications', []))
            if disease_name in indications_text or disease_name in str(drug.get('indications_list', [])):
                print(f"    ✅ 药品适应症中包含疾病 '{disease_name}'")
            else:
                print(f"    ⚠️  药品适应症中未明确包含 '{disease_name}'（可能是模糊关联）")


class TestPipelineIntegration:
    """测试Pipeline集成 - 调用实际模块"""
    
    def test_disease_indexer_module(self):
        """测试DiseaseIndexer模块可正常调用"""
        print("\n" + "=" * 80)
        print("测试 DiseaseIndexer 模块")
        print("=" * 80)
        
        from app.pipeline.disease_indexer import DiseaseIndexer
        
        print(f"\n【步骤1】导入模块")
        print(f"  ✅ 成功导入 DiseaseIndexer")
        
        print(f"\n【步骤2】初始化实例")
        indexer = DiseaseIndexer()
        print(f"  ✅ 实例化成功")
        print(f"  ES连接状态: {indexer.es.ping()}")
        print(f"  目标索引: {indexer.diseases_index}")
        
        print(f"\n【步骤3】检查索引状态")
        es = indexer.es
        if es.indices.exists(index=indexer.diseases_index):
            count = es.count(index=indexer.diseases_index)
            mapping = es.indices.get_mapping(index=indexer.diseases_index)
            properties = mapping[indexer.diseases_index]['mappings']['properties']
            
            print(f"  ✅ 索引存在")
            print(f"  疾病数量: {count['count']:,}")
            print(f"  字段数: {len(properties)}")
            print(f"  字段列表: {', '.join(list(properties.keys())[:8])}...")
        else:
            print(f"  ⚠️  索引未创建")
            print(f"  运行命令: python -m app.pipeline.disease_indexer --rebuild")


class TestETLDataFlow:
    """测试完整的ETL数据流"""
    
    def test_end_to_end_data_flow(self):
        """端到端测试: 跟踪一个药品的完整数据流"""
        print("\n" + "=" * 80)
        print("端到端数据流测试")
        print("=" * 80)
        
        es = get_es_client()
        test_drug_name = "羟基脲"
        
        print(f"\n跟踪药品: {test_drug_name}")
        print(f"{'─' * 80}")
        
        # 步骤1: 在drugs索引中查询
        print(f"\n【步骤1】在 drugs 索引中查询")
        result = es.search(
            index='drugs',
            body={'query': {'match': {'name': test_drug_name}}, 'size': 1}
        )
        
        if not result['hits']['hits']:
            print(f"  ⚠️  未找到药品")
            pytest.skip(f"药品 '{test_drug_name}' 不在索引中")
        
        drug = result['hits']['hits'][0]['_source']
        drug_id = drug['id']
        
        print(f"  ✅ 找到药品")
        print(f"  ID: {drug_id}")
        print(f"  标准名称: {drug['name']}")
        print(f"  indications_list: {len(drug.get('indications_list', []))} 项")
        if drug.get('indications_list'):
            print(f"    示例: {drug['indications_list'][:3]}")
        
        # 步骤2: 检查疾病提取记录
        print(f"\n【步骤2】查找该药品的疾病提取记录")
        diseases_dir = Path("data/processed/diseases/diseases_search_after")
        
        found_extraction = None
        for batch_file in list(diseases_dir.glob("batch_*.json"))[:50]:  # 检查前50个批次
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch = json.load(f)
            
            for extraction in batch.get('extractions', []):
                if extraction['drug_id'] == drug_id:
                    found_extraction = extraction
                    break
            
            if found_extraction:
                break
        
        if found_extraction:
            print(f"  ✅ 找到提取记录")
            print(f"  药品名: {found_extraction['drug_name']}")
            print(f"  提取的疾病数: {len(found_extraction['diseases'])}")
            if found_extraction['diseases']:
                print(f"  疾病示例: {[d['name'] for d in found_extraction['diseases'][:5]]}")
        else:
            print(f"  ⚠️  未找到提取记录（可能在其他批次中）")
        
        # 步骤3: 在diseases索引中查找相关疾病
        if es.indices.exists(index='diseases'):
            print(f"\n【步骤3】在 diseases 索引中查找相关疾病")
            
            # 查询与该药品相关的疾病
            diseases_result = es.search(
                index='diseases',
                body={
                    'query': {
                        'nested': {
                            'path': 'source_drugs',
                            'query': {'term': {'source_drugs.drug_id': drug_id}}
                        }
                    },
                    'size': 5
                }
            )
            
            print(f"  找到 {diseases_result['hits']['total']['value']} 个关联疾病")
            for hit in diseases_result['hits']['hits'][:5]:
                disease = hit['_source']
                print(f"    - {disease['name']} (提及{disease['mention_count']}次)")
        
        print(f"\n{'─' * 80}")
        print(f"✓ 端到端数据流测试完成")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
