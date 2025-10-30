"""结果生成器"""

import logging
from typing import Dict, Any
from datetime import datetime

from .models import Case

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultGenerator:
    """结果生成器 - 生成最终的分析报告"""
    
    def generate(self, case: Case, synthesis_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成分析报告 - 适配新的数据结构
        
        Args:
            case: 病例数据
            synthesis_result: result_synthesizer返回的综合结果（如果有）
            
        Returns:
            Dict: 分析报告（符合新的输出结构）
        """
        try:
            # 如果提供了synthesis_result，直接使用它组装输出
            if synthesis_result:
                return {
                    "case_id": case.id,
                    "analysis_time": synthesis_result["metadata"]["analysis_time"],
                    "drug_info": {
                        "id": case.recognized_entities.drugs[0].matches[0].id if (case.recognized_entities.drugs and case.recognized_entities.drugs[0].matches) else None,
                        "name": case.recognized_entities.drugs[0].name if case.recognized_entities.drugs else None,
                        "standard_name": case.recognized_entities.drugs[0].matches[0].standard_name if (case.recognized_entities.drugs and case.recognized_entities.drugs[0].matches) else None
                    },
                    "disease_info": {
                        "id": case.recognized_entities.diseases[0].matches[0].id if (case.recognized_entities.diseases and case.recognized_entities.diseases[0].matches) else None,
                        "name": case.recognized_entities.diseases[0].name if case.recognized_entities.diseases else None,
                        "standard_name": case.recognized_entities.diseases[0].matches[0].standard_name if (case.recognized_entities.diseases and case.recognized_entities.diseases[0].matches) else None
                    },
                    "is_offlabel": synthesis_result["is_offlabel"],
                    "analysis_details": synthesis_result["analysis_details"],
                    "metadata": synthesis_result["metadata"]
                }
            
            # 否则从case.analysis_result提取（兼容性处理）
            result = case.analysis_result
            if hasattr(result, 'analysis_details'):
                # 新结构
                return {
                    "case_id": result.case_id,
                    "analysis_time": result.analysis_time,
                    "drug_info": {
                        "id": result.drug_info.id,
                        "name": result.drug_info.name,
                        "standard_name": result.drug_info.standard_name
                    },
                    "disease_info": {
                        "id": result.disease_info.id,
                        "name": result.disease_info.name,
                        "standard_name": result.disease_info.standard_name
                    },
                    "is_offlabel": result.is_offlabel,
                    "analysis_details": {
                        "indication_match": {
                            "score": result.analysis_details.indication_match.score,
                            "matching_indication": result.analysis_details.indication_match.matching_indication,
                            "reasoning": result.analysis_details.indication_match.reasoning
                        },
                        "open_evidence": {
                            "mechanism_similarity": {
                                "score": result.analysis_details.open_evidence.mechanism_similarity.score,
                                "reasoning": result.analysis_details.open_evidence.mechanism_similarity.reasoning
                            },
                            "evidence_support": {
                                "level": result.analysis_details.open_evidence.evidence_support.level,
                                "clinical_guidelines": result.analysis_details.open_evidence.evidence_support.clinical_guidelines or [],
                                "expert_consensus": result.analysis_details.open_evidence.evidence_support.expert_consensus or [],
                                "research_papers": result.analysis_details.open_evidence.evidence_support.research_papers or [],
                                "description": result.analysis_details.open_evidence.evidence_support.description
                            }
                        },
                        "recommendation": {
                            "decision": result.analysis_details.recommendation.decision,
                            "explanation": result.analysis_details.recommendation.explanation,
                            "risk_assessment": result.analysis_details.recommendation.risk_assessment
                        }
                    },
                    "metadata": result.metadata
                }
            else:
                # 旧结构（向后兼容）
                return {
                    "case_id": case.id,
                    "analysis_time": datetime.now().isoformat(),
                    "drug_info": {
                        "id": case.recognized_entities.drugs[0].matches[0].id if (case.recognized_entities.drugs and case.recognized_entities.drugs[0].matches) else None,
                        "name": case.recognized_entities.drugs[0].name if case.recognized_entities.drugs else None,
                        "standard_name": case.recognized_entities.drugs[0].matches[0].standard_name if (case.recognized_entities.drugs and case.recognized_entities.drugs[0].matches) else None
                    },
                    "disease_info": {
                        "id": case.recognized_entities.diseases[0].matches[0].id if (case.recognized_entities.diseases and case.recognized_entities.diseases[0].matches) else None,
                        "name": case.recognized_entities.diseases[0].name if case.recognized_entities.diseases else None,
                        "standard_name": case.recognized_entities.diseases[0].matches[0].standard_name if (case.recognized_entities.diseases and case.recognized_entities.diseases[0].matches) else None
                    },
                    "is_offlabel": result.is_offlabel,
                    "analysis_details": {
                        "indication_match": {
                            "score": result.analysis.indication_match.score,
                            "matching_indication": result.analysis.indication_match.matching_indication,
                            "reasoning": result.analysis.indication_match.reasoning
                        },
                        "open_evidence": {
                            "mechanism_similarity": {
                                "score": result.analysis.mechanism_similarity.score,
                                "reasoning": result.analysis.mechanism_similarity.reasoning
                            },
                            "evidence_support": {
                                "level": result.analysis.evidence_support.level,
                                "clinical_guidelines": [],
                                "expert_consensus": [],
                                "research_papers": [],
                                "description": result.analysis.evidence_support.description
                            }
                        },
                        "recommendation": {
                            "decision": result.recommendation.decision,
                            "explanation": result.recommendation.explanation,
                            "risk_assessment": result.recommendation.risk_assessment
                        }
                    },
                    "metadata": result.metadata
                }
            
        except Exception as e:
            logger.error(f"生成分析报告时发生错误: {str(e)}")
            raise
