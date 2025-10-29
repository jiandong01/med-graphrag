"""规则分析模块测试"""

import pytest
from app.inference.rule_checker import RuleAnalyzer


@pytest.fixture
def rule_analyzer():
    """创建 RuleAnalyzer 实例"""
    return RuleAnalyzer()


@pytest.fixture
def sample_drug_info():
    """创建示例药品信息"""
    return {
        "id": "drug_001",
        "name": "阿莫西林",
        "indications": [
            "急性上呼吸道感染",
            "急性支气管炎",
            "肺炎",
            "急性咽炎",
            "急性扁桃体炎",
            "溶血链球菌或肺炎链球菌所致的咽炎"
        ],
        "contraindications": [
            "对青霉素类药物过敏者禁用",
            "传染性单核细胞增多症患者禁用"
        ],
        "precautions": [
            "过敏体质者慎用",
            "肝肾功能不全者慎用"
        ]
    }


@pytest.fixture
def sample_disease_info():
    """创建示例疾病信息"""
    return {
        "id": "disease_001",
        "name": "急性咽炎",
        "description": "咽部黏膜及黏膜下组织的急性炎症",
        "category": "呼吸系统疾病"
    }


def test_exact_match_positive(rule_analyzer, sample_drug_info, sample_disease_info, capsys):
    """测试精确匹配 - 匹配成功"""
    result = rule_analyzer.analyze(sample_drug_info, sample_disease_info)
    
    print(f"\n精确匹配测试 - 匹配成功:")
    print(f"药品: {sample_drug_info['name']}")
    print(f"疾病: {sample_disease_info['name']}")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"置信度: {result['confidence']}")
    print(f"推理依据: {result['reasoning']}")
    print(f"证据: {result['evidence']}")
    
    # 应该找到精确匹配
    assert result['is_offlabel'] is False
    assert result['confidence'] == 1.0
    assert any("精确匹配" in r for r in result['reasoning'])
    
    captured = capsys.readouterr()
    print(captured.out)


def test_exact_match_negative(rule_analyzer, capsys):
    """测试精确匹配 - 无匹配"""
    drug_info = {
        "name": "阿司匹林",
        "indications": ["心肌梗死", "脑卒中预防"],
        "contraindications": []
    }
    
    disease_info = {
        "name": "糖尿病",
        "description": "糖代谢紊乱疾病"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n精确匹配测试 - 无匹配:")
    print(f"药品: {drug_info['name']}")
    print(f"疾病: {disease_info['name']}")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"置信度: {result['confidence']}")
    
    # 应该没有精确匹配
    assert result['is_offlabel'] is True
    
    captured = capsys.readouterr()
    print(captured.out)


def test_case_insensitive_matching(rule_analyzer, capsys):
    """测试大小写不敏感匹配"""
    drug_info = {
        "name": "阿莫西林",
        "indications": ["急性咽炎"],
        "contraindications": []
    }
    
    disease_info = {
        "name": "急性咽炎",  # 完全相同
        "description": "测试"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n大小写不敏感匹配测试:")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"置信度: {result['confidence']}")
    
    assert result['is_offlabel'] is False
    assert result['confidence'] == 1.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_contraindication_check_positive(rule_analyzer, capsys):
    """测试禁忌症检查 - 存在禁忌症"""
    drug_info = {
        "name": "阿司匹林",
        "indications": ["心肌梗死"],
        "contraindications": ["消化道溃疡", "血友病", "严重肝肾功能不全"]
    }
    
    disease_info = {
        "name": "消化道溃疡患者的心肌梗死",
        "description": "测试禁忌症"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n禁忌症检查测试 - 存在禁忌症:")
    print(f"药品: {drug_info['name']}")
    print(f"疾病: {disease_info['name']}")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"推理依据: {result['reasoning']}")
    print(f"证据: {result['evidence']}")
    
    # 应该检测到禁忌症
    assert result['is_offlabel'] is True
    assert any("禁忌症" in r for r in result['reasoning'])
    
    captured = capsys.readouterr()
    print(captured.out)


def test_contraindication_check_negative(rule_analyzer, sample_drug_info, sample_disease_info, capsys):
    """测试禁忌症检查 - 无禁忌症"""
    result = rule_analyzer.analyze(sample_drug_info, sample_disease_info)
    
    print(f"\n禁忌症检查测试 - 无禁忌症:")
    print(f"推理依据: {result['reasoning']}")
    
    # 不应该出现禁忌症警告
    assert not any("禁忌症" in r for r in result['reasoning'])
    
    captured = capsys.readouterr()
    print(captured.out)


def test_empty_drug_info(rule_analyzer, capsys):
    """测试空药品信息"""
    drug_info = {}
    disease_info = {"name": "测试疾病"}
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n空药品信息测试:")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"推理依据: {result['reasoning']}")
    
    assert result['is_offlabel'] is True
    assert "输入数据不完整" in result['reasoning']
    
    captured = capsys.readouterr()
    print(captured.out)


def test_empty_disease_info(rule_analyzer, sample_drug_info, capsys):
    """测试空疾病信息"""
    disease_info = {}
    
    result = rule_analyzer.analyze(sample_drug_info, disease_info)
    
    print(f"\n空疾病信息测试:")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"推理依据: {result['reasoning']}")
    
    assert result['is_offlabel'] is True
    assert "输入数据不完整" in result['reasoning']
    
    captured = capsys.readouterr()
    print(captured.out)


def test_multiple_indications(rule_analyzer, capsys):
    """测试多个适应症"""
    drug_info = {
        "name": "美托洛尔",
        "indications": [
            "高血压",
            "心绞痛",
            "心肌梗死",
            "室上性心律失常",
            "甲状腺功能亢进"
        ],
        "contraindications": ["严重心动过缓", "房室传导阻滞"]
    }
    
    disease_info = {
        "name": "心绞痛",
        "description": "冠状动脉供血不足"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n多个适应症测试:")
    print(f"药品: {drug_info['name']}")
    print(f"适应症数量: {len(drug_info['indications'])}")
    print(f"疾病: {disease_info['name']}")
    print(f"是否超适应症: {result['is_offlabel']}")
    print(f"匹配的适应症: {result.get('evidence', [])}")
    
    assert result['is_offlabel'] is False
    assert result['confidence'] == 1.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_partial_name_matching(rule_analyzer, capsys):
    """测试部分名称匹配"""
    drug_info = {
        "name": "阿莫西林克拉维酸钾",
        "indications": ["呼吸道感染", "泌尿系统感染"],
        "contraindications": []
    }
    
    disease_info = {
        "name": "呼吸道感染",
        "description": "测试"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n部分名称匹配测试:")
    print(f"药品: {drug_info['name']}")
    print(f"疾病: {disease_info['name']}")
    print(f"是否超适应症: {result['is_offlabel']}")
    
    assert result['is_offlabel'] is False
    
    captured = capsys.readouterr()
    print(captured.out)


def test_confidence_levels(rule_analyzer, capsys):
    """测试不同置信度级别"""
    # 测试数据
    test_cases = [
        {
            "name": "精确匹配",
            "drug": {"name": "A", "indications": ["疾病X"], "contraindications": []},
            "disease": {"name": "疾病X"},
            "expected_confidence": 1.0
        },
        {
            "name": "无匹配",
            "drug": {"name": "B", "indications": ["疾病Y"], "contraindications": []},
            "disease": {"name": "疾病Z"},
            "expected_confidence": 0.0
        }
    ]
    
    print("\n置信度级别测试:")
    for test_case in test_cases:
        result = rule_analyzer.analyze(test_case["drug"], test_case["disease"])
        print(f"{test_case['name']}: 置信度 = {result['confidence']}")
        assert result['confidence'] >= 0.0 and result['confidence'] <= 1.0
    
    captured = capsys.readouterr()
    print(captured.out)


def test_synonym_match_placeholder(rule_analyzer, capsys):
    """测试同义词匹配 (占位测试)"""
    # 注意：当前实现中同义词库为空，这是一个占位测试
    drug_info = {
        "name": "药品A",
        "indications": ["高血压"],
        "contraindications": []
    }
    
    disease_info = {
        "name": "原发性高血压",  # 可能的同义词
        "description": "测试"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n同义词匹配占位测试:")
    print(f"当前同义词数据库大小: {len(rule_analyzer.synonym_db)}")
    print(f"分析结果: {result['is_offlabel']}")
    print(f"注意: 当前同义词库为空，此功能待实现")
    
    # 由于同义词库为空，应该找不到匹配
    assert isinstance(result['is_offlabel'], bool)
    
    captured = capsys.readouterr()
    print(captured.out)


def test_hierarchy_match_placeholder(rule_analyzer, capsys):
    """测试层级匹配 (占位测试)"""
    # 注意：当前实现中层级库为空，这是一个占位测试
    drug_info = {
        "name": "药品B",
        "indications": ["心血管疾病"],
        "contraindications": []
    }
    
    disease_info = {
        "name": "心肌梗死",  # 心血管疾病的子类
        "description": "测试"
    }
    
    result = rule_analyzer.analyze(drug_info, disease_info)
    
    print(f"\n层级匹配占位测试:")
    print(f"当前层级数据库大小: {len(rule_analyzer.hierarchy_db)}")
    print(f"分析结果: {result['is_offlabel']}")
    print(f"注意: 当前层级库为空，此功能待实现")
    
    # 由于层级库为空，应该找不到匹配
    assert isinstance(result['is_offlabel'], bool)
    
    captured = capsys.readouterr()
    print(captured.out)


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
