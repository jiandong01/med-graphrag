"""结果生成器"""

import logging
from typing import Dict, Any
from datetime import datetime

from .models import Case

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultGenerator:
    """结果生成器 - 生成最终的分析报告"""
    
    def generate(self, case: Case) -> Dict[str, Any]:
        """生成分析报告
        
        Args:
            case: 病例数据
            
        Returns:
            Dict: 分析报告
        """
        try:
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
                "is_offlabel": case.analysis_result.is_offlabel,
                "analysis_details": {
                    "indication_match": {
                        "score": case.analysis_result.analysis.indication_match.score,
                        "matching_indication": case.analysis_result.analysis.indication_match.matching_indication,
                        "reasoning": case.analysis_result.analysis.indication_match.reasoning
                    },
                    "mechanism_similarity": {
                        "score": case.analysis_result.analysis.mechanism_similarity.score,
                        "reasoning": case.analysis_result.analysis.mechanism_similarity.reasoning
                    },
                    "evidence_support": {
                        "level": case.analysis_result.analysis.evidence_support.level,
                        "description": case.analysis_result.analysis.evidence_support.description
                    }
                },
                "recommendation": {
                    "decision": case.analysis_result.recommendation.decision,
                    "explanation": case.analysis_result.recommendation.explanation,
                    "risk_assessment": case.analysis_result.recommendation.risk_assessment
                },
                "metadata": case.analysis_result.metadata
            }
            
        except Exception as e:
            logger.error(f"生成分析报告时发生错误: {str(e)}")
            raise
