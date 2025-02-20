"""适应症分析测试"""

import os
import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.offlabel_analysis.indication_analysis import IndicationAnalyzer
from src.offlabel_analysis.models import Case, AnalysisResult
from src.utils import get_elastic_client

# 获取测试数据目录的路径
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_test_data(filename):
    """加载测试数据"""
    with open(os.path.join(TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)

class DateTimeEncoder(json.JSONEncoder):
    """处理datetime的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

@pytest.fixture
def mock_es_client():
    """创建模拟的Elasticsearch客户端"""
    mock_client = Mock()
    
    def get_mock_response(index, id):
        return {
            '_source': {
                'id': id,
                'name': '模拟药品',
                'indications': ['适应症1', '适应症2'],
                'details': {'药理毒理': '模拟药理毒理信息'},
                'contraindications': ['禁忌1', '禁忌2'],
                'precautions': ['注意事项1', '注意事项2']
            }
        }
    
    mock_client.get = Mock(side_effect=get_mock_response)
    return mock_client

@pytest.fixture
def mock_hf_client():
    """创建模拟的HuggingFace客户端"""
    mock_client = Mock()
    
    def mock_text_generation(prompt, **kwargs):
        if "继发性肺动脉高压" in prompt:
            return json.dumps({
                "is_offlabel": True,
                "analysis": {
                    "indication_match": {
                        "score": 0.7,
                        "matching_indication": "原发性肺动脉高压",
                        "reasoning": "西地那非主要适应症为原发性肺动脉高压，而患者诊断为继发性肺动脉高压，存在一定差异。"
                    },
                    "mechanism_similarity": {
                        "score": 0.9,
                        "reasoning": "西地那非作为PDE5抑制剂，其作用机制在原发性和继发性肺动脉高压中都有潜在益处，但在继发性病例中的效果可能存在差异。"
                    },
                    "evidence_support": {
                        "level": "B",
                        "description": "有部分临床研究支持西地那非用于治疗继发性肺动脉高压，但证据级别不如原发性肺动脉高压充分。"
                    }
                },
                "recommendation": {
                    "decision": "谨慎使用",
                    "explanation": "虽然西地那非在继发性肺动脉高压中可能有效，但这属于超适应症用药。需要权衡潜在获益和风险，并密切监测患者反应。",
                    "risk_assessment": "可能的风险包括血压降低、视力变化和头痛。由于患者同时患有系统性硬化症，需要特别关注药物相互作用和副作用。"
                }
            })
        else:
            return json.dumps({
                "is_offlabel": False,
                "analysis": {
                    "indication_match": {
                        "score": 0.95,
                        "matching_indication": "模拟匹配适应症",
                        "reasoning": "模拟推理过程"
                    },
                    "mechanism_similarity": {
                        "score": 0.9,
                        "reasoning": "模拟机制相似性分析"
                    },
                    "evidence_support": {
                        "level": "B",
                        "description": "模拟证据支持描述"
                    }
                },
                "recommendation": {
                    "decision": "建议使用",
                    "explanation": "模拟建议说明",
                    "risk_assessment": "模拟风险评估"
                }
            })
    
    mock_client.text_generation = Mock(side_effect=mock_text_generation)
    return mock_client

@pytest.fixture
def indication_analyzer(mock_es_client, mock_hf_client):
    """创建IndicationAnalyzer实例"""
    analyzer = IndicationAnalyzer(es=mock_es_client)
    analyzer.client = mock_hf_client
    return analyzer

@pytest.mark.parametrize("input_file,output_file", [
    ('input/indication_analysis_input_1.json', 'output/indication_analysis_output_1.json'),
    ('input/indication_analysis_input_2.json', 'output/indication_analysis_output_2.json'),
])
def test_indication_analysis(indication_analyzer, input_file, output_file, capsys):
    """测试适应症分析"""
    input_data = load_test_data(input_file)
    expected_output = load_test_data(output_file)
    
    case = Case(**input_data)
    result = indication_analyzer.analyze_indication(case)
    
    print(f"\n测试输入文件: {input_file}")
    print("分析结果:")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2, cls=DateTimeEncoder))
    
    assert isinstance(result, AnalysisResult)
    assert result.is_offlabel == expected_output['is_offlabel']
    assert result.analysis.indication_match.score == pytest.approx(expected_output['analysis']['indication_match']['score'], 0.01)
    assert result.recommendation.decision == expected_output['recommendation']['decision']
    
    captured = capsys.readouterr()
    print(captured.out)

def test_indication_analysis_error(indication_analyzer, capsys):
    """测试适应症分析错误处理"""
    input_data = load_test_data('input/indication_analysis_input_error.json')
    case = Case(**input_data)
    
    with pytest.raises(ValueError) as excinfo:
        indication_analyzer.analyze_indication(case)
    
    print("\n测试错误处理:")
    print(f"抛出的异常: {str(excinfo.value)}")
    
    error_msg = str(excinfo.value)
    assert any(msg in error_msg for msg in ["未识别到药品信息", "未找到匹配的标准药品", "未识别到疾病信息"])
    
    captured = capsys.readouterr()
    print(captured.out)

def test_batch_analyze(indication_analyzer, capsys):
    """测试批量分析功能"""
    input_data_1 = load_test_data('input/indication_analysis_input_1.json')
    input_data_2 = load_test_data('input/indication_analysis_input_2.json')
    
    cases = [Case(**input_data_1), Case(**input_data_2)]
    results = indication_analyzer.batch_analyze(cases)
    
    print("\n批量分析结果:")
    for i, result in enumerate(results, 1):
        print(f"Case {i}:")
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2, cls=DateTimeEncoder))
        print()
    
    assert len(results) == 2
    assert all(isinstance(result, Case) for result in results)
    assert all(hasattr(result, 'analysis_result') for result in results)
    
    captured = capsys.readouterr()
    print(captured.out)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
