"""Prompt templates for entity recognition and indication analysis"""

import json

def create_entity_recognition_prompt(input_data: dict) -> str:
    """Create a prompt for entity recognition

    Args:
        input_data: Input data containing medical record

    Returns:
        str: Formatted prompt for entity recognition
    """
    return f"""请从以下医疗记录中识别所有的药品和疾病实体。

医疗记录：
{json.dumps(input_data, ensure_ascii=False)}

请以JSON格式返回识别结果，包含以下字段：
{{
    "drugs": [
        {{
            "name": "药品名称1"
        }},
        {{
            "name": "药品名称2"
        }}
    ],
    "diseases": [
        {{
            "name": "疾病名称1"
        }},
        {{
            "name": "疾病名称2"
        }}
    ],
    "context": {{
        "description": "相关描述"
    }}
}}

在返回结果之前，请先用<think>标签记录你的思考过程。"""

def create_indication_analysis_prompt(
    drug_name: str,
    indications: str,
    pharmacology: str,
    contraindications: str,
    precautions: str,
    diagnosis: str,
    description: str,
    rule_analysis: str,
    clinical_guidelines_status: str,
    clinical_guidelines: str,
    expert_consensus_status: str,
    expert_consensus: str,
    research_papers_status: str,
    research_papers: str
) -> str:
    """Create a prompt for indication analysis

    Args:
        drug_name: Name of the drug
        indications: Standard indications of the drug
        pharmacology: Pharmacology of the drug
        contraindications: Contraindications of the drug
        precautions: Precautions for the drug
        diagnosis: Patient's diagnosis
        description: Detailed description of the patient's condition
        rule_analysis: Result of rule-based analysis
        clinical_guidelines_status: Status of clinical guidelines data
        clinical_guidelines: Clinical guidelines data
        expert_consensus_status: Status of expert consensus data
        expert_consensus: Expert consensus data
        research_papers_status: Status of research papers data
        research_papers: Research papers data

    Returns:
        str: Formatted prompt for indication analysis
    """
    return f"""请分析以下用药情况是否属于超适应症用药。

输入信息：
1. 药品信息：
   - 名称：{drug_name}
   - 标准适应症：{indications}
   - 药理毒理：{pharmacology}
   - 禁忌：{contraindications}
   - 注意事项：{precautions}

2. 患者情况：
   - 诊断：{diagnosis}
   - 详细描述：{description}

3. 规则分析结果：
   {rule_analysis}

4. 临床指南：
   {clinical_guidelines_status}
   {clinical_guidelines}

5. 专家共识：
   {expert_consensus_status}
   {expert_consensus}

6. 研究证据：
   {research_papers_status}
   {research_papers}

注意事项：
1. 对于标记为"（数据不可用）"的信息，请在分析中明确指出缺少该类数据，并解释这可能如何影响您的判断。
2. 在证据等级评估时，如果某类证据缺失，应相应降低整体评估的可信度。
3. 即使缺少部分数据，也请尽可能基于现有信息给出合理的分析和建议。
4. 在结果中，请明确指出哪些结论是基于完整数据得出的，哪些是在数据缺失情况下的推测。

**重要：超适应症判断规则**
- 适应症匹配判断应该**严格基于字符串匹配**，不要做医学知识推理
- 检查患者诊断（{diagnosis}）是否**精确出现**在药品适应症列表中
- 如果患者诊断不在适应症列表中，即使医学上属于相关疾病，也应该标记为无匹配
- 例如：即使"21-羟化酶缺乏症"医学上属于"先天性肾上腺皮质增生症"，但如果适应症中只写了后者，也应该判定为不匹配

请按照以下格式返回分析结果（注意：必须是合法的JSON格式，不要添加任何注释或说明）：

{{
  "is_offlabel": false,
  "confidence": 0.85,
  "analysis": {{
    "indication_match": {{
      "score": 0.9,
      "matching_indication": "精确匹配到的适应症文本（如果有）或'无'",
      "reasoning": "说明是否找到精确字符串匹配"
    }},
    "mechanism_similarity": {{
      "score": 0.8,
      "reasoning": "药理机制分析说明（仅作参考，不影响超适应症判断）"
    }},
    "evidence_support": {{
      "level": "B",
      "description": "支持证据说明"
    }}
  }},
  "recommendation": {{
    "decision": "建议使用",
    "explanation": "建议说明",
    "risk_assessment": "风险评估说明"
  }},
  "data_limitations": {{
    "missing_data": ["临床指南", "专家共识"],
    "impact_on_analysis": "数据缺失对分析的影响说明"
  }}
}}"""
