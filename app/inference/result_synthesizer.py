"""结果综合模块"""

from typing import Dict, List, Any
from datetime import datetime

class ResultSynthesizer:
    def __init__(self):
        # 定义各个来源的权重
        self.weights = {
            "rule_analysis": 0.4,      # 规则分析权重
            "clinical_guidelines": 0.3, # 临床指南权重
            "llm_analysis": 0.2,       # LLM分析权重
            "research_evidence": 0.1    # 研究文献权重
        }

    def synthesize(self, 
                  rule_result: Dict[str, Any], 
                  llm_result: Dict[str, Any], 
                  knowledge_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        综合各个分析结果 - 重构后的结构
        
        Args:
            rule_result: 规则分析结果
            llm_result: LLM分析结果
            knowledge_context: 知识上下文（包含临床指南、专家共识等）
        
        Returns:
            Dict: 综合分析结果（符合新的数据结构）
        """
        # 计算加权得分
        weighted_scores = self._calculate_weighted_scores(
            rule_result, llm_result, knowledge_context
        )
        
        # 确定最终的超适应症判断（严格规则判断）
        final_is_offlabel = self._determine_final_offlabel_status(
            rule_result, llm_result, weighted_scores
        )
        
        # 整合所有证据和推理过程
        evidence_synthesis = self._synthesize_evidence(
            rule_result, llm_result, knowledge_context
        )
        
        # 生成最终建议
        final_recommendation = self._generate_recommendation(
            final_is_offlabel, weighted_scores, evidence_synthesis
        )
        
        # 按照新的数据结构组织输出
        return {
            "is_offlabel": final_is_offlabel,  # 严格规则判断
            "analysis_details": {
                # 规则判断部分
                "indication_match": {
                    "score": rule_result.get("confidence", 0.0),  # 使用规则判断的置信度
                    "matching_indication": evidence_synthesis["matching_indication"],
                    "reasoning": " ".join(evidence_synthesis["indication_match_reasoning"])
                },
                # AI辅助部分
                "open_evidence": {
                    "mechanism_similarity": {
                        "score": weighted_scores["mechanism_similarity"],
                        "reasoning": " ".join(evidence_synthesis["mechanism_reasoning"]) if evidence_synthesis["mechanism_reasoning"] else "未进行机制分析"
                    },
                    "evidence_support": {
                        "level": evidence_synthesis["evidence_level"],
                        "clinical_guidelines": knowledge_context.get("clinical_guidelines", []),
                        "expert_consensus": knowledge_context.get("expert_consensus", []),
                        "research_papers": knowledge_context.get("research_papers", []),
                        "description": " ".join(evidence_synthesis["evidence_description"])
                    }
                },
                # 推荐建议
                "recommendation": final_recommendation
            },
            "metadata": {
                "analysis_time": datetime.now().isoformat(),
                "rule_confidence": rule_result.get("confidence", 0.0),
                "llm_confidence": llm_result.get("confidence", 0.0),
                "evidence_sources": evidence_synthesis["sources"]
            }
        }

    def _calculate_weighted_scores(self, 
                                 rule_result: Dict, 
                                 llm_result: Dict, 
                                 knowledge_context: Dict) -> Dict[str, float]:
        """计算加权得分"""
        scores = {
            "indication_match": 0.0,
            "mechanism_similarity": 0.0,
            "total_score": 0.0
        }
        
        # 规则分析得分
        if not rule_result.get("is_offlabel", True):
            scores["indication_match"] += self.weights["rule_analysis"]
        
        # 临床指南得分
        if knowledge_context.get("clinical_guidelines"):
            guideline_support = self._evaluate_guideline_support(
                knowledge_context["clinical_guidelines"]
            )
            scores["indication_match"] += guideline_support * self.weights["clinical_guidelines"]
        
        # LLM分析得分
        if llm_result.get("analysis"):
            llm_scores = llm_result["analysis"]
            scores["indication_match"] += (
                llm_scores.get("indication_match", {}).get("score", 0) * 
                self.weights["llm_analysis"]
            )
            scores["mechanism_similarity"] = llm_scores.get("mechanism_similarity", {}).get("score", 0)
        
        # 研究文献得分
        if knowledge_context.get("research_papers"):
            research_support = self._evaluate_research_support(
                knowledge_context["research_papers"]
            )
            scores["indication_match"] += research_support * self.weights["research_evidence"]
        
        # 计算总分
        scores["total_score"] = (scores["indication_match"] + scores["mechanism_similarity"]) / 2
        
        return scores

    def _determine_final_offlabel_status(self, 
                                       rule_result: Dict, 
                                       llm_result: Dict, 
                                       weighted_scores: Dict) -> bool:
        """确定最终的超适应症状态 - 严格基于规则判断
        
        超适应症判断应该严格基于药品说明书适应症的精确匹配，
        而不是基于AI推理或机制相似度。
        
        判断标准：
        - 只有精确匹配(confidence=1.0)才判定为非超适应症
        - 同义词匹配、层级关系匹配等都视为超适应症
        - AI分析结果不影响is_offlabel判断
        """
        # 严格基于规则的精确匹配
        # 只有confidence=1.0（精确匹配）才判定为非超适应症
        if not rule_result.get("is_offlabel", True):
            confidence = rule_result.get("confidence", 0)
            if confidence >= 1.0:
                # 精确匹配，判定为标准用药
                return False
        
        # 其他所有情况都判定为超适应症
        # 包括：
        # - 同义词匹配（confidence=0.9）
        # - 层级关系匹配（confidence=0.8）
        # - AI推理认为机制相似
        return True

    def _synthesize_evidence(self, 
                           rule_result: Dict, 
                           llm_result: Dict, 
                           knowledge_context: Dict) -> Dict:
        """整合所有证据"""
        evidence = {
            "matching_indication": "",
            "indication_match_reasoning": [],
            "mechanism_reasoning": [],
            "evidence_level": "C",  # 默认证据等级
            "evidence_description": [],
            "sources": []
        }
        
        # 添加规则分析的证据
        if rule_result.get("reasoning"):
            evidence["indication_match_reasoning"].extend(rule_result["reasoning"])
        if rule_result.get("evidence"):
            evidence["evidence_description"].extend(rule_result["evidence"])
            
        # 添加LLM分析的证据
        if llm_result.get("analysis"):
            llm_analysis = llm_result["analysis"]
            if "indication_match" in llm_analysis:
                evidence["matching_indication"] = llm_analysis["indication_match"].get("matching_indication", "")
                evidence["indication_match_reasoning"].append(
                    llm_analysis["indication_match"].get("reasoning", "")
                )
            if "mechanism_similarity" in llm_analysis:
                evidence["mechanism_reasoning"].append(
                    llm_analysis["mechanism_similarity"].get("reasoning", "")
                )
            if "evidence_support" in llm_analysis:
                evidence["evidence_level"] = llm_analysis["evidence_support"].get("level", "C")
                evidence["evidence_description"].append(
                    llm_analysis["evidence_support"].get("description", "")
                )
                
        # 添加知识库的证据
        if knowledge_context.get("clinical_guidelines"):
            evidence["sources"].extend([
                {"type": "clinical_guideline", "content": g}
                for g in knowledge_context["clinical_guidelines"]
            ])
        if knowledge_context.get("expert_consensus"):
            evidence["sources"].extend([
                {"type": "expert_consensus", "content": c}
                for c in knowledge_context["expert_consensus"]
            ])
        if knowledge_context.get("research_papers"):
            evidence["sources"].extend([
                {"type": "research_paper", "content": p}
                for p in knowledge_context["research_papers"]
            ])
            
        return evidence

    def _generate_recommendation(self, 
                               is_offlabel: bool, 
                               weighted_scores: Dict, 
                               evidence: Dict) -> Dict:
        """生成最终建议"""
        if not is_offlabel:
            decision = "建议使用"
            explanation = "该用药符合适应症要求，有充分的循证医学证据支持。"
        elif weighted_scores["total_score"] > 0.4:
            decision = "谨慎使用"
            explanation = "虽然属于超适应症用药，但有一定的证据支持其合理性。建议在充分评估风险收益后决定是否使用。"
        else:
            decision = "不建议使用"
            explanation = "证据支持不足，且存在潜在风险。建议考虑其他治疗方案。"
            
        return {
            "decision": decision,
            "explanation": explanation,
            "risk_assessment": self._assess_risks(evidence)
        }

    def _evaluate_guideline_support(self, guidelines: List[Dict]) -> float:
        """评估临床指南的支持程度"""
        if not guidelines:
            return 0.0
            
        support_level = 0.0
        for guideline in guidelines:
            # 根据推荐等级评估支持程度
            if guideline.get("recommendation_level") == "A":
                support_level += 1.0
            elif guideline.get("recommendation_level") == "B":
                support_level += 0.7
            elif guideline.get("recommendation_level") == "C":
                support_level += 0.4
                
        return min(support_level / len(guidelines), 1.0)

    def _evaluate_research_support(self, papers: List[Dict]) -> float:
        """评估研究文献的支持程度"""
        if not papers:
            return 0.0
            
        support_level = 0.0
        for paper in papers:
            # 根据研究类型评估支持程度
            if paper.get("study_type") == "RCT":
                support_level += 1.0
            elif paper.get("study_type") == "Cohort":
                support_level += 0.7
            elif paper.get("study_type") == "Case-Control":
                support_level += 0.5
                
        return min(support_level / len(papers), 1.0)

    def _assess_risks(self, evidence: Dict) -> str:
        """评估风险"""
        risks = []
        
        # 从各种来源收集风险信息
        for source in evidence.get("sources", []):
            if "risk" in str(source.get("content", "")):
                risks.append(source["content"])
                
        if not risks:
            return "未发现明显风险，但仍需要注意监测不良反应。"
            
        return "、".join(risks[:3])  # 返回前三个主要风险
