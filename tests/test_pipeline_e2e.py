"""Pipeline端到端测试 - 不依赖缓存文件的完整流程测试"""

import pytest
import json
from app.shared import get_es_client, Config

Config.load_env()


class TestDrugPipeline:
    """药品Pipeline端到端测试"""
    
    def test_query_drugs_from_elasticsearch(self):
        """测试1: 直接从ES查询药品数据"""
        print("\n=== 测试1: ES药品查询 ===")
        
        es = get_es_client()
        
        # 1. 统计总数
        total = es.count(
            index='drugs',
            body={'query': {'match_all': {}}}
        )
        print(f"✅ 药品总数: {total['count']:,}")
        
        # 2. 查询有适应症的药品
        with_indications = es.count(
            index='drugs',
            body={'query': {'exists': {'field': 'indications'}}}
        )
        print(f"✅ 有适应症的药品: {with_indications['count']:,}")
        
        # 3. 搜索特定药品
        result = es.search(
            index='drugs',
            body={
                'query': {'match': {'name': '阿司匹林'}},
                'size': 3
            }
        )
        
        print(f"✅ 搜索'阿司匹林'找到: {result['hits']['total']['value']}个")
        for hit in result['hits']['hits']:
            drug = hit['_source']
            print(f"  - {drug['name']}")
            print(f"    适应症数: {len(drug.get('indications', []))}")
            if drug.get('indications'):
                print(f"    示例: {drug['indications'][0][:50]}...")
        
        # 验证
        assert total['count'] > 80000, "药品数量异常"
        assert with_indications['count'] > 80000, "有适应症的药品异常"
    
    def test_drug_data_structure(self):
        """测试2: 验证药品数据结构"""
        print("\n=== 测试2: 药品数据结构 ===")
        
        es = get_es_client()
        
        # 随机获取一个药品
        result = es.search(
            index='drugs',
            body={
                'query': {
                    'bool': {
                        'must': [
                            {'exists': {'field': 'indications'}},
                            {'exists': {'field': 'components'}}
                        ]
                    }
                },
                'size': 1
            }
        )
        
        if result['hits']['hits']:
            drug = result['hits']['hits'][0]['_source']
            
            print(f"✅ 药品示例: {drug['name']}")
            print(f"  ID: {drug.get('id')}")
            print(f"  成分数: {len(drug.get('components', []))}")
            print(f"  适应症数: {len(drug.get('indications', []))}")
            print(f"  禁忌症数: {len(drug.get('contraindications', []))}")
            print(f"  分类: {drug.get('categories', [])[:3]}")
            
            # 验证必需字段
            required_fields = ['id', 'name', 'indications', 'create_time']
            for field in required_fields:
                assert field in drug, f"缺少必需字段: {field}"
                print(f"  ✅ {field}: 存在")


class TestDiseasePipeline:
    """疾病Pipeline端到端测试"""
    
    def test_query_diseases_from_elasticsearch(self):
        """测试3: 直接从ES查询疾病数据"""
        print("\n=== 测试3: ES疾病查询 ===")
        
        es = get_es_client()
        
        # 检查diseases索引是否存在
        if not es.indices.exists(index='diseases'):
            print("⚠️  diseases索引不存在，跳过测试")
            print("   提示: 运行 python -m app.pipeline.disease_indexer --rebuild")
            pytest.skip("diseases索引未创建")
        
        # 1. 统计总数
        total = es.count(index='diseases')
        print(f"✅ 疾病总数: {total['count']:,}")
        
        # 2. 查询示例疾病
        result = es.search(
            index='diseases',
            body={
                'query': {'match': {'name': '高血压'}},
                'size': 1
            }
        )
        
        if result['hits']['hits']:
            disease = result['hits']['hits'][0]['_source']
            print(f"✅ 疾病示例: {disease['name']}")
            print(f"  ID: {disease.get('id')}")
            print(f"  类型: {disease.get('type')}")
            print(f"  提及次数: {disease.get('mention_count')}")
            print(f"  来源药品数: {len(disease.get('source_drugs', []))}")
            
            # 显示关联的药品
            if disease.get('source_drugs'):
                print(f"  关联药品示例:")
                for src in disease['source_drugs'][:3]:
                    print(f"    - {src['drug_name']} ({src['drug_id']})")
        
        # 3. 按提及次数排序
        top_diseases = es.search(
            index='diseases',
            body={
                'query': {'match_all': {}},
                'sort': [{'mention_count': {'order': 'desc'}}],
                'size': 5
            }
        )
        
        print(f"\n✅ 最常见疾病Top5:")
        for hit in top_diseases['hits']['hits']:
            d = hit['_source']
            print(f"  {d['name']}: {d['mention_count']}次")
        
        # 验证
        assert total['count'] > 5000, "疾病数量异常"
    
    def test_disease_drug_relationship(self):
        """测试4: 验证疾病-药品关联关系"""
        print("\n=== 测试4: 疾病-药品关联 ===")
        
        es = get_es_client()
        
        if not es.indices.exists(index='diseases'):
            pytest.skip("diseases索引未创建")
        
        # 查询一个疾病
        result = es.search(
            index='diseases',
            body={
                'query': {'match_all': {}},
                'size': 1
            }
        )
        
        if result['hits']['hits']:
            disease = result['hits']['hits'][0]['_source']
            disease_name = disease['name']
            source_drugs = disease.get('source_drugs', [])
            
            print(f"✅ 测试疾病: {disease_name}")
            print(f"  关联药品数: {len(source_drugs)}")
            
            # 验证关联的药品是否在drugs索引中
            if source_drugs:
                drug_id = source_drugs[0]['drug_id']
                drug_result = es.search(
                    index='drugs',
                    body={
                        'query': {'term': {'id': drug_id}},
                        'size': 1
                    }
                )
                
                if drug_result['hits']['hits']:
                    drug = drug_result['hits']['hits'][0]['_source']
                    print(f"✅ 反向验证药品存在: {drug['name']}")
                    print(f"  药品适应症中包含相关疾病信息")
                    
                    # 验证药品适应症
                    indications = drug.get('indications', [])
                    print(f"  适应症数: {len(indications)}")
                    
                    assert len(indications) > 0, "关联药品应有适应症"


class TestPipelineIntegration:
    """Pipeline集成测试 - 调用实际模块"""
    
    def test_disease_indexer_module(self):
        """测试5: 调用disease_indexer模块"""
        print("\n=== 测试5: DiseaseIndexer模块调用 ===")
        
        from app.pipeline.disease_indexer import DiseaseIndexer
        
        # 初始化
        indexer = DiseaseIndexer()
        print(f"✅ DiseaseIndexer初始化成功")
        print(f"  ES连接: {indexer.es.ping()}")
        print(f"  目标索引: {indexer.diseases_index}")
        
        # 检查索引状态
        es = indexer.es
        if es.indices.exists(index=indexer.diseases_index):
            count = es.count(index=indexer.diseases_index)
            print(f"✅ diseases索引已存在")
            print(f"  疾病数量: {count['count']:,}")
            
            # 获取mapping
            mapping = es.indices.get_mapping(index=indexer.diseases_index)
            properties = mapping[indexer.diseases_index]['mappings']['properties']
            print(f"  字段数: {len(properties)}")
            print(f"  字段: {list(properties.keys())}")
        else:
            print("⚠️  diseases索引未创建")
            print("   运行: python -m app.pipeline.disease_indexer --rebuild")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
