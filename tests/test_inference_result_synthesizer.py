"""结果综合模块测试"""

import pytest
from app.inference.result_synthesizer import ResultSynthesizer


@pytest.fixture
def result_synthesizer():
    """创建 ResultSynthesizer 实例"""
    return ResultSynthesizer()


@pytest.fixture
def sample_rule_result():
    """创建示例规则分析结果"""
    return {
        "is_offlabel": False,
        "confidence": 1.0,
        "reasoning": ["疾病名称与药品适应症精确匹配"],
        "evidence": ["适应症: 急性咽炎"]
    }


@pytest.fixture
def sample_llm_result():
    """创建示例LLM分析结果"""
    return {
        "is_offlabel": False,
        "confidence": 0.9,
        "analysis": {
            "indication_match": {
                "score": 0.95,
                "matching_indication": "急性咽炎",
                "reasoning": "患者诊断与药品适应症完全匹配"
            },
            "mechanism_similarity": {
                "score": 0.85,
                "reasoning": "药物机制与疾病病理生理相符"
            },
            "evidence_support": {
                "level": "A",
                "description": "有明确的临床证据支持该用药"
            }
        }
    }


@pytest.fixture
def sample_knowledge_context():
    """创建示例知识上下文"""
    return {
        "clinical_guidelines": [
            {
                "title": "急性咽炎诊疗指南",
                "recommendation_level": "A",
                "content": "推荐使用阿莫西林治疗细菌性急性咽炎"
            }
        ],
        "expert_consensus": [
            {
                "title": "抗菌药物临床应用共识",
                "content": "阿莫西林是治疗链球菌性咽炎的一线药物"
            }
        ],
        "research_papers": [
            {
                "title": "阿莫西林治疗急性咽炎的疗效研究",
                "study_type": "RCT",
                "conclusion": "阿莫西林显著改善症状"
            }
        ]
    }


def test_synthesize_standard_use(result_synthesizer, sample_rule_result, 
                                 sample_llm_result, sample_knowledge_context, capsys):
    """测试标准用药的结果综合"""
    result = result_synthesizer.synthesize(
        sample_rule_result,
        sample_llm_result,
        sample_knowledge_context
    )
    
    print(f"\n标准用药结果综合:")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"置信度: {result['confidence']}")
    print(f"决策建议: {result['recommendation']['decision']}")
    print(f"适应症匹配度: {result['analysis']['indication_match']['score']}")
    print(f"证据等级: {result['analysis']['evidence_support']['level']}")
    
    # 验证结果
    assert result['is_offlabel'] is False
    assert result['confidence'] > 0.8
    assert "建议使用" in result['recommendation']['decision']
    assert result['metadata']['rule_confidence'] == 1.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_synthesize_offlabel_use(result_synthesizer, capsys):
    """测试超适应症用药的结果综合"""
    rule_result = {
        "is_offlabel": True,
        "confidence": 0.0,
        "reasoning": ["未找到匹配的适应症"],
        "evidence": []
    }
    
    llm_result = {
        "is_offlabel": True,
        "confidence": 0.6,
        "analysis": {
            "indication_match": {
                "score": 0.3,
                "matching_indication": "",
                "reasoning": "无直接匹配的适应症"
            },
            "mechanism_similarity": {
                "score": 0.7,
                "reasoning": "药理机制有一定相关性"
            },
            "evidence_support": {
                "level": "C",
                "description": "证据支持较弱"
            }
        }
    }
    
    knowledge_context = {
        "clinical_guidelines": [],
        "expert_consensus": [],
        "research_papers": []
    }
    
    result = result_synthesizer.synthesize(rule_result, llm_result, knowledge_context)
    
    print(f"\n超适应症用药结果综合:")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"置信度: {result['confidence']}")
    print(f"决策建议: {result['recommendation']['decision']}")
    print(f"解释: {result['recommendation']['explanation']}")
    
    assert result['is_offlabel'] is True
    assert result['confidence'] < 0.6
    
    captured = capsys.readouterr()
    print(captured.out)


def test_calculate_weighted_scores(result_synthesizer, sample_rule_result,
                                   sample_llm_result, sample_knowledge_context, capsys):
    """测试加权得分计算"""
    scores = result_synthesizer._calculate_weighted_scores(
        sample_rule_result,
        sample_llm_result,
        sample_knowledge_context
    )
    
    print(f"\n加权得分计算:")
    print(f"适应症匹配度: {scores['indication_match']}")
    print(f"机制相似度: {scores['mechanism_similarity']}")
    print(f"总分: {scores['total_score']}")
    
    # 验证得分范围
    assert 0.0 <= scores['indication_match'] <= 1.0
    assert 0.0 <= scores['mechanism_similarity'] <= 1.0
    assert 0.0 <= scores['total_score'] <= 1.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_determine_final_offlabel_status(result_synthesizer, capsys):
    """测试最终超适应症状态判定"""
    # 测试场景1: 规则高置信度判定为非超适应症
    rule_result1 = {"is_offlabel": False, "confidence": 0.95}
    llm_result1 = {"is_offlabel": True, "confidence": 0.5}
    weighted_scores1 = {"total_score": 0.7}
    
    status1 = result_synthesizer._determine_final_offlabel_status(
        rule_result1, llm_result1, weighted_scores1
    )
    
    print(f"\n场景1 - 规则高置信度非超适应症:")
    print(f"规则判定: {rule_result1['is_offlabel']}, 置信度: {rule_result1['confidence']}")
    print(f"最终判定: {status1}")
    assert status1 is False
    
    # 测试场景2: 规则高置信度判定为超适应症
    rule_result2 = {"is_offlabel": True, "confidence": 0.95}
    llm_result2 = {"is_offlabel": False, "confidence": 0.8}
    weighted_scores2 = {"total_score": 0.7}
    
    status2 = result_synthesizer._determine_final_offlabel_status(
        rule_result2, llm_result2, weighted_scores2
    )
    
    print(f"\n场景2 - 规则高置信度超适应症:")
    print(f"规则判定: {rule_result2['is_offlabel']}, 置信度: {rule_result2['confidence']}")
    print(f"最终判定: {status2}")
    assert status2 is True
    
    # 测试场景3: 综合得分决定
    rule_result3 = {"is_offlabel": True, "confidence": 0.5}
    llm_result3 = {"is_offlabel": True, "confidence": 0.6}
    weighted_scores3 = {"total_score": 0.4}
    
    status3 = result_synthesizer._determine_final_offlabel_status(
        rule_result3, llm_result3, weighted_scores3
    )
    
    print(f"\n场景3 - 综合得分决定:")
    print(f"综合得分: {weighted_scores3['total_score']}")
    print(f"最终判定: {status3}")
    assert status3 is True
    
    captured = capsys.readouterr()
    print(captured.out)


def test_synthesize_evidence(result_synthesizer, sample_rule_result,
                            sample_llm_result, sample_knowledge_context, capsys):
    """测试证据整合"""
    evidence = result_synthesizer._synthesize_evidence(
        sample_rule_result,
        sample_llm_result,
        sample_knowledge_context
    )
    
    print(f"\n证据整合结果:")
    print(f"匹配的适应症: {evidence['matching_indication']}")
    print(f"适应症匹配推理: {evidence['indication_match_reasoning']}")
    print(f"机制推理: {evidence['mechanism_reasoning']}")
    print(f"证据等级: {evidence['evidence_level']}")
    print(f"证据来源数量: {len(evidence['sources'])}")
    
    # 验证证据完整性
    assert 'matching_indication' in evidence
    assert 'evidence_level' in evidence
    assert isinstance(evidence['sources'], list)
    
    captured = capsys.readouterr()
    print(captured.out)


def test_generate_recommendation(result_synthesizer, capsys):
    """测试建议生成"""
    # 测试场景1: 建议使用
    weighted_scores1 = {"total_score": 0.9}
    evidence1 = {"evidence_level": "A", "sources": []}
    recommendation1 = result_synthesizer._generate_recommendation(
        False, weighted_scores1, evidence1
    )
    
    print(f"\n建议生成 - 场景1 (建议使用):")
    print(f"决策: {recommendation1['decision']}")
    print(f"解释: {recommendation1['explanation']}")
    assert "建议使用" in recommendation1['decision']
    
    # 测试场景2: 谨慎使用
    weighted_scores2 = {"total_score": 0.5}
    evidence2 = {"evidence_level": "B", "sources": []}
    recommendation2 = result_synthesizer._generate_recommendation(
        True, weighted_scores2, evidence2
    )
    
    print(f"\n建议生成 - 场景2 (谨慎使用):")
    print(f"决策: {recommendation2['decision']}")
    print(f"解释: {recommendation2['explanation']}")
    assert "谨慎使用" in recommendation2['decision']
    
    # 测试场景3: 不建议使用
    weighted_scores3 = {"total_score": 0.2}
    evidence3 = {"evidence_level": "C", "sources": []}
    recommendation3 = result_synthesizer._generate_recommendation(
        True, weighted_scores3, evidence3
    )
    
    print(f"\n建议生成 - 场景3 (不建议使用):")
    print(f"决策: {recommendation3['decision']}")
    print(f"解释: {recommendation3['explanation']}")
    assert "不建议使用" in recommendation3['decision']
    
    captured = capsys.readouterr()
    print(captured.out)


def test_evaluate_guideline_support(result_synthesizer, capsys):
    """测试临床指南支持度评估"""
    guidelines = [
        {"recommendation_level": "A"},
        {"recommendation_level": "B"},
        {"recommendation_level": "C"}
    ]
    
    support = result_synthesizer._evaluate_guideline_support(guidelines)
    
    print(f"\n临床指南支持度评估:")
    print(f"指南数量: {len(guidelines)}")
    print(f"支持度: {support}")
    
    assert 0.0 <= support <= 1.0
    
    # 测试空指南
    empty_support = result_synthesizer._evaluate_guideline_support([])
    print(f"空指南支持度: {empty_support}")
    assert empty_support == 0.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_evaluate_research_support(result_synthesizer, capsys):
    """测试研究文献支持度评估"""
    papers = [
        {"study_type": "RCT"},
        {"study_type": "Cohort"},
        {"study_type": "Case-Control"}
    ]
    
    support = result_synthesizer._evaluate_research_support(papers)
    
    print(f"\n研究文献支持度评估:")
    print(f"文献数量: {len(papers)}")
    print(f"支持度: {support}")
    
    assert 0.0 <= support <= 1.0
    
    # 测试空文献
    empty_support = result_synthesizer._evaluate_research_support([])
    print(f"空文献支持度: {empty_support}")
    assert empty_support == 0.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_assess_risks(result_synthesizer, capsys):
    """测试风险评估"""
    evidence_with_risks = {
        "sources": [
            {"type": "guideline", "content": "注意监测肝功能，存在肝损伤风险"},
            {"type": "paper", "content": "可能导致胃肠道不适风险"},
            {"type": "consensus", "content": "过敏体质者使用风险较高"}
        ]
    }
    
    risks = result_synthesizer._assess_risks(evidence_with_risks)
    
    print(f"\n风险评估 - 有风险:")
    print(f"风险描述: {risks}")
    assert len(risks) > 0
    
    # 测试无风险证据
    evidence_no_risks = {"sources": [{"content": "安全有效"}]}
    no_risks = result_synthesizer._assess_risks(evidence_no_risks)
    
    print(f"\n风险评估 - 无明显风险:")
    print(f"风险描述: {no_risks}")
    assert "未发现明显风险" in no_risks
    
    captured = capsys.readouterr()
    print(captured.out)


def test_weights_configuration(result_synthesizer, capsys):
    """测试权重配置"""
    print(f"\n权重配置:")
    print(f"规则分析权重: {result_synthesizer.weights['rule_analysis']}")
    print(f"临床指南权重: {result_synthesizer.weights['clinical_guidelines']}")
    print(f"LLM分析权重: {result_synthesizer.weights['llm_analysis']}")
    print(f"研究证据权重: {result_synthesizer.weights['research_evidence']}")
    
    # 验证权重总和为1
    total_weight = sum(result_synthesizer.weights.values())
    print(f"权重总和: {total_weight}")
    assert abs(total_weight - 1.0) < 0.01
    
    captured = capsys.readouterr()
    print(captured.out)


def test_metadata_generation(result_synthesizer, sample_rule_result,
                            sample_llm_result, sample_knowledge_context, capsys):
    """测试元数据生成"""
    result = result_synthesizer.synthesize(
        sample_rule_result,
        sample_llm_result,
        sample_knowledge_context
    )
    
    print(f"\n元数据生成:")
    print(f"分析时间: {result['metadata']['analysis_time']}")
    print(f"规则置信度: {result['metadata']['rule_confidence']}")
    print(f"LLM置信度: {result['metadata']['llm_confidence']}")
    print(f"证据来源数量: {len(result['metadata']['evidence_sources'])}")
    
    # 验证元数据完整性
    assert 'analysis_time' in result['metadata']
    assert 'rule_confidence' in result['metadata']
    assert 'llm_confidence' in result['metadata']
    assert 'evidence_sources' in result['metadata']
    
    captured = capsys.readouterr()
    print(captured.out)


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
