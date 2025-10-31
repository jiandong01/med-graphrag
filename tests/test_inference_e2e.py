"""Inference端到端测试 - 验证推理分析流程

测试从疾病和用药输入到最终判断的完整推理过程
每个测试步骤都会输出详细的输入输出
"""

import pytest
import json
from app.inference.engine import InferenceEngine
from app.shared import Config

Config.load_env()


@pytest.fixture(scope="module")
def inference_engine():
    """创建推理引擎实例（完整模式）"""
    return InferenceEngine(skip_entity_recognition=False)


@pytest.fixture(scope="module")
def inference_engine_fast():
    """创建推理引擎实例（快速模式）"""
    return InferenceEngine(skip_entity_recognition=True)


class TestInferenceWorkflow:
    """测试完整的推理工作流程"""
    
    def test_case1_standard_use(self, inference_engine):
        """案例1: 标准用药 - 溴吡斯的明治疗重症肌无力"""
        print("\n" + "=" * 80)
        print("案例1: 标准用药测试")
        print("=" * 80)
        
        # 输入
        input_data = {
            "description": "患者诊断为重症肌无力，拟使用溴吡斯的明治疗",
            "patient_info": {"age": 45, "gender": "女"},
            "prescription": {"drug": "溴吡斯的明", "dosage": "60mg", "frequency": "每日3次"}
        }
        
        print(f"\n【步骤1: 原始输入】")
        print(json.dumps(input_data, ensure_ascii=False, indent=2))
        
        # 步骤2: 实体识别
        print(f"\n【步骤2: 实体识别】")
        recognized = inference_engine.entity_recognizer.recognize(input_data)
        
        print(f"  识别的药品: {recognized.drugs[0].name if recognized.drugs else '无'}")
        if recognized.drugs and recognized.drugs[0].matches:
            match = recognized.drugs[0].matches[0]
            print(f"    ES匹配: {match.standard_name}")
            print(f"    匹配分数: {match.score:.2f}")
            print(f"    药品ID: {match.id[:40]}...")
        
        print(f"  识别的疾病: {recognized.diseases[0].name if recognized.diseases else '无'}")
        if recognized.diseases and recognized.diseases[0].matches:
            match = recognized.diseases[0].matches[0]
            print(f"    ES匹配: {match.standard_name}")
            print(f"    匹配分数: {match.score:.2f}")
            print(f"    疾病ID: {match.id}")
        
        # 步骤3: 完整分析
        print(f"\n【步骤3: 执行完整分析】")
        result = inference_engine.analyze(input_data)
        
        print(f"  超适应症判断: {result.get('is_offlabel')}")
        print(f"  匹配分数: {result.get('analysis_details', {}).get('indication_match', {}).get('score', 'N/A')}")
        print(f"  匹配的适应症: {result.get('analysis_details', {}).get('indication_match', {}).get('matching_indication', 'N/A')}")
        
        # 步骤4: 最终输出
        print(f"\n【步骤4: 最终输出】")
        print(f"  是否超适应症: {result['is_offlabel']}")
        print(f"  决策建议: {result.get('analysis_details', {}).get('recommendation', {}).get('decision', 'N/A')}")
        print(f"  解释: {result.get('analysis_details', {}).get('recommendation', {}).get('explanation', 'N/A')[:100]}...")
        
        # 显示药品详细信息（如果有）
        drug_info = result.get('drug_info', {})
        if 'indications_list' in drug_info and drug_info['indications_list']:
            print(f"\n  药品适应症列表:")
            for ind in drug_info['indications_list'][:5]:
                print(f"    - {ind}")
        
        assert 'is_offlabel' in result
        print(f"\n✓ 案例1测试完成")
    
    def test_case2_offlabel_use(self, inference_engine):
        """案例2: 超适应症用药 - 美托洛尔治疗心力衰竭"""
        print("\n" + "=" * 80)
        print("案例2: 超适应症用药测试")
        print("=" * 80)
        
        input_data = {
            "description": "患者诊断为心力衰竭，拟使用美托洛尔治疗",
            "patient_info": {"age": 65, "gender": "男"},
            "prescription": {"drug": "美托洛尔"}
        }
        
        print(f"\n【步骤1: 原始输入】")
        print(json.dumps(input_data, ensure_ascii=False, indent=2))
        
        print(f"\n【步骤2: 实体识别】")
        recognized = inference_engine.entity_recognizer.recognize(input_data)
        
        print(f"  药品: {recognized.drugs[0].name if recognized.drugs else '无'}")
        if recognized.drugs and recognized.drugs[0].matches:
            print(f"    → {recognized.drugs[0].matches[0].standard_name}")
        
        print(f"  疾病: {recognized.diseases[0].name if recognized.diseases else '无'}")
        if recognized.diseases and recognized.diseases[0].matches:
            print(f"    → {recognized.diseases[0].matches[0].standard_name}")
        
        print(f"\n【步骤3: 执行分析】")
        result = inference_engine.analyze(input_data)
        
        print(f"\n【步骤4: 最终输出】")
        print(f"  is_offlabel: {result['is_offlabel']}")
        print(f"  机制相似度: {result.get('analysis_details', {}).get('open_evidence', {}).get('mechanism_similarity', {}).get('score', 'N/A')}")
        print(f"  证据等级: {result.get('analysis_details', {}).get('open_evidence', {}).get('evidence_support', {}).get('level', 'N/A')}")
        print(f"  建议: {result.get('analysis_details', {}).get('recommendation', {}).get('decision', 'N/A')}")
        
        assert 'is_offlabel' in result
        print(f"\n✓ 案例2测试完成")
    
    def test_case3_drug_not_found(self, inference_engine_fast):
        """案例3: 药品未匹配 - 友好错误处理"""
        print("\n" + "=" * 80)
        print("案例3: 药品未匹配测试")
        print("=" * 80)
        
        input_data = {
            "drug_name": "抗心律失常药",  # 药物类别名，不应该匹配
            "disease_name": "心律失常",
            "description": "患者诊断为心律失常，拟使用抗心律失常药治疗"
        }
        
        print(f"\n【步骤1: 原始输入】")
        print(json.dumps(input_data, ensure_ascii=False, indent=2))
        
        print(f"\n【步骤2: 严格匹配】")
        print(f"  查询药品: {input_data['drug_name']}")
        
        result = inference_engine_fast.analyze(input_data)
        
        print(f"\n【步骤3: 最终输出】")
        print(f"  is_offlabel: {result.get('is_offlabel')}")
        print(f"  drug_info:")
        print(f"    id: {result.get('drug_info', {}).get('id')}")
        print(f"    match_status: {result.get('drug_info', {}).get('match_status', 'N/A')}")
        
        if 'error' in result.get('analysis_details', {}):
            print(f"  ✅ 友好错误处理:")
            print(f"    错误: {result['analysis_details']['error']}")
            print(f"    消息: {result['analysis_details']['message'][:100]}...")
            print(f"    建议: {result['analysis_details']['suggestion']}")
        
        # 药品类别名应该返回 None
        assert result.get('is_offlabel') is None
        assert result.get('drug_info', {}).get('match_status') == 'not_found'
        
        print(f"\n✓ 案例3测试完成")


class TestInferenceStepByStep:
    """分步测试推理流程的每个环节"""
    
    def test_step_by_step_analysis(self, inference_engine):
        """完整的分步分析 - 羟基脲治疗真性红细胞增多症"""
        print("\n" + "=" * 80)
        print("分步分析测试: 羟基脲 + 真性红细胞增多症")
        print("=" * 80)
        
        input_data = {
            "description": "患者诊断为真性红细胞增多症，拟使用羟基脲治疗",
            "patient_info": {"age": 55, "gender": "男"},
            "prescription": {"drug": "羟基脲"}
        }
        
        # ===== 步骤1: 实体识别 =====
        print(f"\n{'─' * 80}")
        print("【步骤1: 实体识别】")
        print(f"{'─' * 80}")
        
        print(f"\n输入:")
        print(f"  描述: {input_data['description']}")
        
        recognized = inference_engine.entity_recognizer.recognize(input_data)
        
        print(f"\n输出:")
        print(f"  药品:")
        if recognized.drugs:
            drug = recognized.drugs[0]
            print(f"    原始名: {drug.name}")
            if drug.matches:
                print(f"    标准名: {drug.matches[0].standard_name}")
                print(f"    药品ID: {drug.matches[0].id[:40]}...")
                print(f"    匹配分数: {drug.matches[0].score:.2f}")
        
        print(f"  疾病:")
        if recognized.diseases:
            disease = recognized.diseases[0]
            print(f"    原始名: {disease.name}")
            if disease.matches:
                print(f"    标准名: {disease.matches[0].standard_name}")
                print(f"    疾病ID: {disease.matches[0].id}")
        
        # ===== 步骤2: 知识增强 =====
        print(f"\n{'─' * 80}")
        print("【步骤2: 知识增强】")
        print(f"{'─' * 80}")
        
        from app.inference.models import Case
        from app.inference.knowledge_retriever import KnowledgeEnhancer
        
        case = Case(id="test", recognized_entities=recognized)
        enhancer = KnowledgeEnhancer()
        enhanced_case = enhancer.enhance_case(case)
        
        print(f"\n输入:")
        print(f"  药品ID: {drug.matches[0].id if drug.matches else 'N/A'}")
        print(f"  疾病ID: {disease.matches[0].id if disease.matches else 'N/A'}")
        
        print(f"\n输出:")
        print(f"  药品详情:")
        print(f"    标准名: {enhanced_case.drug.standard_name}")
        print(f"    适应症数: {len(enhanced_case.drug.indications)}")
        if enhanced_case.drug.indications:
            print(f"    适应症示例: {enhanced_case.drug.indications[:3]}")
        print(f"    禁忌症数: {len(enhanced_case.drug.contraindications)}")
        
        print(f"  疾病详情:")
        print(f"    标准名: {enhanced_case.disease.standard_name or '未匹配'}")
        print(f"    ICD编码: {enhanced_case.disease.icd_code or '未匹配'}")
        
        # ===== 步骤3: 规则分析 =====
        print(f"\n{'─' * 80}")
        print("【步骤3: 规则分析】")
        print(f"{'─' * 80}")
        
        from app.inference.rule_checker import RuleAnalyzer
        
        rule_analyzer = RuleAnalyzer()
        disease_name = enhanced_case.disease.name or disease.name
        
        rule_result = rule_analyzer.analyze(
            {
                "id": enhanced_case.drug.id,
                "name": enhanced_case.drug.name,
                "indications": enhanced_case.drug.indications,
                "contraindications": enhanced_case.drug.contraindications
            },
            {
                "id": enhanced_case.disease.id,
                "name": disease_name
            }
        )
        
        print(f"\n输入:")
        print(f"  药品适应症: {enhanced_case.drug.indications[:3] if enhanced_case.drug.indications else []}")
        print(f"  患者疾病: {disease_name}")
        
        print(f"\n输出:")
        print(f"  is_offlabel: {rule_result['is_offlabel']}")
        print(f"  confidence: {rule_result['confidence']}")
        print(f"  reasoning: {rule_result['reasoning']}")
        
        # ===== 步骤4: 完整分析 =====
        print(f"\n{'─' * 80}")
        print("【步骤4: 完整推理分析（包含LLM）】")
        print(f"{'─' * 80}")
        
        result = inference_engine.analyze(input_data)
        
        print(f"\n输出:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # ===== 验证 =====
        assert 'is_offlabel' in result
        assert 'drug_info' in result
        assert 'disease_info' in result
        assert 'analysis_details' in result
        
        print(f"\n✓ 案例1测试完成")
    
    def test_case2_offlabel_reasonable(self, inference_engine_fast):
        """案例2: 合理的超适应症 - 美托洛尔治疗心力衰竭"""
        print("\n" + "=" * 80)
        print("案例2: 合理超适应症用药（快速模式）")
        print("=" * 80)
        
        input_data = {
            "drug_name": "美托洛尔",
            "disease_name": "心力衰竭",
            "description": "患者诊断为慢性心力衰竭，拟使用美托洛尔治疗"
        }
        
        print(f"\n【步骤1: 原始输入】（快速模式：直接提供药品和疾病名）")
        print(json.dumps(input_data, ensure_ascii=False, indent=2))
        
        print(f"\n【步骤2: 严格ES匹配】")
        drug_matches = inference_engine_fast.entity_recognizer._search_drug(
            input_data['drug_name'], unique=True
        )
        
        if drug_matches:
            print(f"  药品匹配: ✅")
            print(f"    标准名: {drug_matches[0]['name']}")
            print(f"    匹配分数: {drug_matches[0]['_score']:.2f}")
        else:
            print(f"  药品匹配: ❌ 未找到")
        
        print(f"\n【步骤3: 获取药品详情】")
        result = inference_engine_fast.analyze(input_data)
        
        drug_info = result.get('drug_info', {})
        print(f"  药品ID: {drug_info.get('id', 'N/A')[:40]}...")
        print(f"  标准名: {drug_info.get('standard_name', 'N/A')}")
        print(f"  适应症数: {len(drug_info.get('indications_list', []))}")
        if drug_info.get('indications_list'):
            print(f"  适应症列表: {drug_info['indications_list'][:5]}")
        
        print(f"\n【步骤4: 规则判断】")
        indication_match = result.get('analysis_details', {}).get('indication_match', {})
        print(f"  匹配分数: {indication_match.get('score', 'N/A')}")
        print(f"  匹配推理: {indication_match.get('reasoning', 'N/A')[:150]}...")
        
        print(f"\n【步骤5: AI辅助分析】")
        open_evidence = result.get('analysis_details', {}).get('open_evidence', {})
        mechanism = open_evidence.get('mechanism_similarity', {})
        evidence = open_evidence.get('evidence_support', {})
        
        print(f"  机制相似度: {mechanism.get('score', 'N/A')}")
        print(f"  机制推理: {mechanism.get('reasoning', 'N/A')[:100]}...")
        print(f"  证据等级: {evidence.get('level', 'N/A')}")
        
        print(f"\n【最终输出】")
        print(f"  is_offlabel: {result.get('is_offlabel')}")
        print(f"  决策: {result.get('analysis_details', {}).get('recommendation', {}).get('decision', 'N/A')}")
        
        assert result.get('is_offlabel') is not None
        print(f"\n✓ 案例2测试完成")
    
    def test_case3_drug_category_name(self, inference_engine_fast):
        """案例3: 药物类别名 - 应该过滤"""
        print("\n" + "=" * 80)
        print("案例3: 药物类别名过滤测试")
        print("=" * 80)
        
        input_data = {
            "drug_name": "抗代谢药",
            "disease_name": "恶性肿瘤",
            "description": "患者诊断为恶性肿瘤，拟使用抗代谢药治疗"
        }
        
        print(f"\n【步骤1: 原始输入】")
        print(json.dumps(input_data, ensure_ascii=False, indent=2))
        
        print(f"\n【步骤2: 严格匹配验证】")
        drug_matches = inference_engine_fast.entity_recognizer._search_drug(
            input_data['drug_name'], unique=True
        )
        
        print(f"  药品 '{input_data['drug_name']}' 匹配结果: {len(drug_matches)} 个")
        if drug_matches:
            print(f"  ⚠️  意外：药物类别名被匹配到了")
            for match in drug_matches:
                print(f"    - {match['name']}")
        else:
            print(f"  ✅ 正确：药物类别名被过滤")
        
        print(f"\n【步骤3: 分析结果】")
        result = inference_engine_fast.analyze(input_data)
        
        print(f"\n【输出】")
        print(f"  is_offlabel: {result.get('is_offlabel')}")
        print(f"  match_status: {result.get('drug_info', {}).get('match_status', 'N/A')}")
        
        if 'error' in result.get('analysis_details', {}):
            print(f"  ✅ 友好错误信息:")
            print(f"    {result['analysis_details']['error']}")
            print(f"    {result['analysis_details']['message']}")
        
        assert result.get('is_offlabel') is None
        assert result.get('drug_info', {}).get('match_status') == 'not_found'
        
        print(f"\n✓ 案例3测试完成")


class TestInferenceOutputStructure:
    """测试推理输出结构的完整性"""
    
    def test_output_structure_complete(self, inference_engine_fast):
        """测试输出结构包含所有必需字段"""
        print("\n" + "=" * 80)
        print("输出结构完整性测试")
        print("=" * 80)
        
        input_data = {
            "drug_name": "羟基脲",
            "disease_name": "真性红细胞增多症",
            "description": "患者诊断为真性红细胞增多症，拟使用羟基脲治疗"
        }
        
        result = inference_engine_fast.analyze(input_data)
        
        print(f"\n【验证输出结构】")
        
        # 验证顶层字段
        required_top_fields = ['case_id', 'analysis_time', 'drug_info', 'disease_info', 
                              'is_offlabel', 'analysis_details', 'metadata']
        
        print(f"\n  顶层字段:")
        for field in required_top_fields:
            exists = field in result
            print(f"    {field}: {'✓' if exists else '✗'}")
            assert exists, f"缺少必需字段: {field}"
        
        # 验证 drug_info 字段
        drug_info_fields = ['id', 'name', 'standard_name', 'indications_list', 
                           'indications', 'contraindications']
        
        print(f"\n  drug_info字段:")
        drug_info = result.get('drug_info', {})
        for field in drug_info_fields:
            exists = field in drug_info
            print(f"    {field}: {'✓' if exists else '✗'}")
        
        # 验证 analysis_details 结构
        print(f"\n  analysis_details字段:")
        analysis_details = result.get('analysis_details', {})
        analysis_fields = ['indication_match', 'open_evidence', 'recommendation']
        for field in analysis_fields:
            exists = field in analysis_details
            print(f"    {field}: {'✓' if exists else '✗'}")
        
        print(f"\n✓ 输出结构完整性验证通过")


class TestInferenceBatchProcessing:
    """测试批量处理"""
    
    def test_batch_analysis(self, inference_engine_fast):
        """测试批量分析功能"""
        print("\n" + "=" * 80)
        print("批量分析测试")
        print("=" * 80)
        
        input_list = [
            {
                "drug_name": "羟基脲",
                "disease_name": "真性红细胞增多症",
                "description": "测试1"
            },
            {
                "drug_name": "美托洛尔",
                "disease_name": "心力衰竭",
                "description": "测试2"
            },
            {
                "drug_name": "抗心律失常药",  # 这个应该失败
                "disease_name": "心律失常",
                "description": "测试3"
            }
        ]
        
        print(f"\n【输入】{len(input_list)} 个案例")
        for i, inp in enumerate(input_list, 1):
            print(f"  {i}. {inp['drug_name']} + {inp['disease_name']}")
        
        results = inference_engine_fast.analyze_batch(input_list)
        
        print(f"\n【输出】")
        print(f"  总计: {len(results)} 个结果")
        
        success_count = sum(1 for r in results if 'error' not in r and r.get('is_offlabel') is not None)
        failed_count = len(results) - success_count
        
        print(f"  成功: {success_count}")
        print(f"  失败: {failed_count}")
        
        for i, result in enumerate(results, 1):
            if result.get('is_offlabel') is not None:
                print(f"\n  案例{i}: ✅")
                print(f"    is_offlabel: {result['is_offlabel']}")
            else:
                print(f"\n  案例{i}: ⚠️  药品信息缺失")
                print(f"    match_status: {result.get('drug_info', {}).get('match_status', 'N/A')}")
        
        assert len(results) == len(input_list)
        print(f"\n✓ 批量分析测试完成")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
