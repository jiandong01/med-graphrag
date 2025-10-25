"""适应症分析测试"""

import os
import json
import pytest
import logging
from app.src.offlabel_analysis.indication_analysis import IndicationAnalyzer
from app.src.offlabel_analysis.models import (
    Case, AnalysisResult, RecognizedEntities, Context,
    RecognizedDrug, RecognizedDisease, DrugMatch, DiseaseMatch
)
from app.src.utils import get_elastic_client, load_env
from app.src.offlabel_analysis.utils import create_case_from_entity_recognition
from app.src.offlabel_analysis.prompt import create_indication_analysis_prompt

# 加载环境变量
load_env()

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.fixture(autouse=True)
def set_log_level():
    previous_level = logging.getLogger().level
    logging.getLogger().setLevel(logging.DEBUG)
    yield
    logging.getLogger().setLevel(previous_level)

@pytest.fixture(scope="module")
def indication_analyzer():
    """创建 IndicationAnalyzer 实例"""
    return IndicationAnalyzer(es=get_elastic_client())

def test_indication_analysis_case1(indication_analyzer, capsys):
    """测试适应症分析 - Case 1"""
    input_file = 'output/entity_recognition_output_1.json'
    input_data = load_test_data(input_file)
    
    print("\n=== Case 1 ===")
    print("\n1. 输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    case = create_case_from_entity_recognition(input_data)
    
    print("\n2. 创建的 Case 对象:")
    print(f"Case ID: {case.id}")
    print(f"Drugs: {[drug.name for drug in case.recognized_entities.drugs]}")
    print(f"Diseases: {[disease.name for disease in case.recognized_entities.diseases]}")
    if case.recognized_entities.context:
        print(f"Context: {case.recognized_entities.context.description}")
    
    try:
        # 获取知识增强后的 Case
        enhanced_case = indication_analyzer.knowledge_enhancer.enhance_case(case)
        print("\n3. 知识增强后的 Case 信息:")
        print("药品信息:")
        print(f"- 名称: {enhanced_case.drug.name}")
        print(f"- 标准名称: {enhanced_case.drug.standard_name}")
        print(f"- 适应症: {enhanced_case.drug.indications}")
        print(f"- 禁忌症: {enhanced_case.drug.contraindications}")
        print(f"- 注意事项: {enhanced_case.drug.precautions}")
        print("\n疾病信息:")
        print(f"- 名称: {enhanced_case.disease.name}")
        print(f"- 标准名称: {enhanced_case.disease.standard_name}")
        print(f"- ICD编码: {enhanced_case.disease.icd_code}")
        
        # 获取规则分析结果
        rule_result = indication_analyzer.rule_analyzer.analyze(
            {
                "id": enhanced_case.drug.id,
                "name": enhanced_case.drug.name,
                "indications": enhanced_case.drug.indications,
                "contraindications": enhanced_case.drug.contraindications,
                "details": enhanced_case.drug.details
            },
            {
                "id": enhanced_case.disease.id,
                "name": enhanced_case.disease.name
            }
        )
        print("\n4. 规则分析结果:")
        print(json.dumps(rule_result, ensure_ascii=False, indent=2))
        
        # 获取生成的提示
        prompt = create_indication_analysis_prompt(
            drug_name=enhanced_case.drug.name,
            indications=json.dumps(enhanced_case.drug.indications, ensure_ascii=False),
            pharmacology=enhanced_case.drug.pharmacology or "无相关信息",
            contraindications=json.dumps(enhanced_case.drug.contraindications, ensure_ascii=False),
            precautions=json.dumps(enhanced_case.drug.precautions, ensure_ascii=False),
            diagnosis=enhanced_case.disease.name,
            description=enhanced_case.context.description if enhanced_case.context else "",
            rule_analysis=json.dumps(rule_result, ensure_ascii=False),
            clinical_guidelines_status="（数据不可用）" if not enhanced_case.evidence.clinical_guidelines else "",
            clinical_guidelines=json.dumps(enhanced_case.evidence.clinical_guidelines or [], ensure_ascii=False),
            expert_consensus_status="（数据不可用）" if not enhanced_case.evidence.expert_consensus else "",
            expert_consensus=json.dumps(enhanced_case.evidence.expert_consensus or [], ensure_ascii=False),
            research_papers_status="（数据不可用）" if not enhanced_case.evidence.research_papers else "",
            research_papers=json.dumps(enhanced_case.evidence.research_papers or [], ensure_ascii=False)
        )
        print("\n5. 生成的提示:")
        print(prompt)
        
        # 获取LLM响应
        completion = indication_analyzer.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": indication_analyzer.site_url,
                "X-Title": indication_analyzer.site_name,
            },
            model=indication_analyzer.model,
            messages=[
                {"role": "system", "content": "你是一个专业的医学分析助手，请严格按照要求的JSON格式返回分析结果，不要添加任何额外的说明或注释。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        raw_response = completion.choices[0].message.content
        print("\n6. 原始LLM响应:")
        print(raw_response)
        
        # 获取清理后的响应
        cleaned_response = indication_analyzer._clean_json_response(raw_response)
        print("\n7. 清理后的LLM响应:")
        print(cleaned_response)
        
        # 获取最终分析结果
        result = indication_analyzer.analyze_indication(case)
        print("\n8. 最终分析结果:")
        result_dict = {
            "is_offlabel": result.is_offlabel,
            "confidence": result.confidence,
            "analysis": {
                "indication_match": {
                    "score": result.analysis.indication_match.score,
                    "matching_indication": result.analysis.indication_match.matching_indication,
                    "reasoning": result.analysis.indication_match.reasoning
                },
                "mechanism_similarity": {
                    "score": result.analysis.mechanism_similarity.score,
                    "reasoning": result.analysis.mechanism_similarity.reasoning
                },
                "evidence_support": {
                    "level": result.analysis.evidence_support.level,
                    "description": result.analysis.evidence_support.description
                }
            },
            "recommendation": {
                "decision": result.recommendation.decision,
                "explanation": result.recommendation.explanation,
                "risk_assessment": result.recommendation.risk_assessment
            },
            "evidence_synthesis": result.evidence_synthesis,
            "metadata": result.metadata
        }
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n=== 错误信息 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误描述: {str(e)}")
        raise
    
    captured = capsys.readouterr()
    print(captured.out)

def test_indication_analysis_case2(indication_analyzer, capsys):
    """测试适应症分析 - Case 2"""
    input_file = 'output/entity_recognition_output_2.json'
    input_data = load_test_data(input_file)
    
    print("\n=== Case 2 ===")
    print("\n1. 输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    case = create_case_from_entity_recognition(input_data)
    
    print("\n2. 创建的 Case 对象:")
    print(f"Case ID: {case.id}")
    print(f"Drugs: {[drug.name for drug in case.recognized_entities.drugs]}")
    print(f"Diseases: {[disease.name for disease in case.recognized_entities.diseases]}")
    if case.recognized_entities.context:
        print(f"Context: {case.recognized_entities.context.description}")
    
    try:
        # 获取知识增强后的 Case
        enhanced_case = indication_analyzer.knowledge_enhancer.enhance_case(case)
        print("\n3. 知识增强后的 Case 信息:")
        print("药品信息:")
        print(f"- 名称: {enhanced_case.drug.name}")
        print(f"- 标准名称: {enhanced_case.drug.standard_name}")
        print(f"- 适应症: {enhanced_case.drug.indications}")
        print(f"- 禁忌症: {enhanced_case.drug.contraindications}")
        print(f"- 注意事项: {enhanced_case.drug.precautions}")
        print("\n疾病信息:")
        print(f"- 名称: {enhanced_case.disease.name}")
        print(f"- 标准名称: {enhanced_case.disease.standard_name}")
        print(f"- ICD编码: {enhanced_case.disease.icd_code}")
        
        # 获取规则分析结果
        rule_result = indication_analyzer.rule_analyzer.analyze(
            {
                "id": enhanced_case.drug.id,
                "name": enhanced_case.drug.name,
                "indications": enhanced_case.drug.indications,
                "contraindications": enhanced_case.drug.contraindications,
                "details": enhanced_case.drug.details
            },
            {
                "id": enhanced_case.disease.id,
                "name": enhanced_case.disease.name
            }
        )
        print("\n4. 规则分析结果:")
        print(json.dumps(rule_result, ensure_ascii=False, indent=2))
        
        # 获取生成的提示
        prompt = create_indication_analysis_prompt(
            drug_name=enhanced_case.drug.name,
            indications=json.dumps(enhanced_case.drug.indications, ensure_ascii=False),
            pharmacology=enhanced_case.drug.pharmacology or "无相关信息",
            contraindications=json.dumps(enhanced_case.drug.contraindications, ensure_ascii=False),
            precautions=json.dumps(enhanced_case.drug.precautions, ensure_ascii=False),
            diagnosis=enhanced_case.disease.name,
            description=enhanced_case.context.description if enhanced_case.context else "",
            rule_analysis=json.dumps(rule_result, ensure_ascii=False),
            clinical_guidelines_status="（数据不可用）" if not enhanced_case.evidence.clinical_guidelines else "",
            clinical_guidelines=json.dumps(enhanced_case.evidence.clinical_guidelines or [], ensure_ascii=False),
            expert_consensus_status="（数据不可用）" if not enhanced_case.evidence.expert_consensus else "",
            expert_consensus=json.dumps(enhanced_case.evidence.expert_consensus or [], ensure_ascii=False),
            research_papers_status="（数据不可用）" if not enhanced_case.evidence.research_papers else "",
            research_papers=json.dumps(enhanced_case.evidence.research_papers or [], ensure_ascii=False)
        )
        print("\n5. 生成的提示:")
        print(prompt)
        
        # 获取LLM响应
        completion = indication_analyzer.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": indication_analyzer.site_url,
                "X-Title": indication_analyzer.site_name,
            },
            model=indication_analyzer.model,
            messages=[
                {"role": "system", "content": "你是一个专业的医学分析助手，请严格按照要求的JSON格式返回分析结果，不要添加任何额外的说明或注释。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        raw_response = completion.choices[0].message.content
        print("\n6. 原始LLM响应:")
        print(raw_response)
        
        # 获取清理后的响应
        cleaned_response = indication_analyzer._clean_json_response(raw_response)
        print("\n7. 清理后的LLM响应:")
        print(cleaned_response)
        
        # 获取最终分析结果
        result = indication_analyzer.analyze_indication(case)
        print("\n8. 最终分析结果:")
        result_dict = {
            "is_offlabel": result.is_offlabel,
            "confidence": result.confidence,
            "analysis": {
                "indication_match": {
                    "score": result.analysis.indication_match.score,
                    "matching_indication": result.analysis.indication_match.matching_indication,
                    "reasoning": result.analysis.indication_match.reasoning
                },
                "mechanism_similarity": {
                    "score": result.analysis.mechanism_similarity.score,
                    "reasoning": result.analysis.mechanism_similarity.reasoning
                },
                "evidence_support": {
                    "level": result.analysis.evidence_support.level,
                    "description": result.analysis.evidence_support.description
                }
            },
            "recommendation": {
                "decision": result.recommendation.decision,
                "explanation": result.recommendation.explanation,
                "risk_assessment": result.recommendation.risk_assessment
            },
            "evidence_synthesis": result.evidence_synthesis,
            "metadata": result.metadata
        }
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n=== 错误信息 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误描述: {str(e)}")
        raise
    
    captured = capsys.readouterr()
    print(captured.out)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
