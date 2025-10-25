"""适应症分析核心逻辑"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any
from openai import OpenAI
from elasticsearch import Elasticsearch

from app.src.utils import get_elastic_client, load_env
from .models import (
    Case, AnalysisResult, EnhancedCase, Analysis, Recommendation, 
    IndicationMatch, MechanismSimilarity, EvidenceSupport
)
from .rule_analyzer import RuleAnalyzer
from .knowledge_enhancer import KnowledgeEnhancer
from .result_synthesizer import ResultSynthesizer
from .prompt import create_indication_analysis_prompt

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndicationAnalyzer:
    """适应症分析器 - 分析用药是否属于超适应症"""
    
    def __init__(self, es: Elasticsearch = None):
        """初始化分析器
        
        Args:
            es: Elasticsearch客户端实例
        """
        self.es = es or get_elastic_client()
        
        # OpenAI/OpenRouter设置
        load_env()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = "deepseek/deepseek-r1-distill-qwen-32b"
        self.site_url = os.getenv("SITE_URL", "http://localhost:3000")
        self.site_name = os.getenv("SITE_NAME", "Medical GraphRAG")
        
        # 初始化其他模块
        self.rule_analyzer = RuleAnalyzer()
        self.knowledge_enhancer = KnowledgeEnhancer(es)
        self.result_synthesizer = ResultSynthesizer()

    def _clean_json_response(self, response: str) -> str:
        """清理和格式化JSON响应
        
        Args:
            response: 原始响应文本
            
        Returns:
            str: 清理后的JSON文本
        """
        try:
            # 移除所有前导和尾随的空白字符
            response = response.strip()
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning(f"未找到有效的JSON内容，原始响应: {response}")
                raise ValueError("未找到有效的JSON内容")
                
            json_str = json_match.group(0)
            
            # 移除所有注释
            json_str = re.sub(r'//.*$|/\*[\s\S]*?\*/|#.*$', '', json_str, flags=re.MULTILINE)
            
            # 规范化布尔值和数字
            json_str = re.sub(r':\s*true\b', ': true', json_str, flags=re.IGNORECASE)
            json_str = re.sub(r':\s*false\b', ': false', json_str, flags=re.IGNORECASE)
            json_str = re.sub(r':\s*(\d+\.?\d*)', r': \1', json_str)
            
            # 清理字符串值
            json_str = re.sub(r':\s*"([^"]*)"', r': "\1"', json_str)
            
            # 清理数组
            json_str = re.sub(r':\s*\[', ': [', json_str)
            json_str = re.sub(r'\]\s*,', '],', json_str)
            
            # 清理对象
            json_str = re.sub(r':\s*\{', ': {', json_str)
            json_str = re.sub(r'\}\s*,', '},', json_str)
            
            # 移除多余的空白字符
            json_str = re.sub(r'\s+', ' ', json_str)
            json_str = re.sub(r',\s+', ', ', json_str)
            json_str = re.sub(r':\s+', ': ', json_str)
            
            # 确保键名使用双引号
            json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
            
            # 最后一次尝试解析和格式化
            parsed = json.loads(json_str)
            return json.dumps(parsed, ensure_ascii=False)  # 重新序列化以确保格式正确
        except Exception as e:
            logger.error(f"JSON清理和解析失败: {str(e)}")
            logger.error(f"原始响应: {response}")
            raise ValueError(f"无法解析JSON响应: {str(e)}")

    def analyze_indication(self, case: Case) -> AnalysisResult:
        """分析用药适应症情况
        
        Args:
            case: 包含实体识别结果的病例数据
            
        Returns:
            AnalysisResult: 分析结果
        """
        try:
            if not case.recognized_entities.drugs:
                raise ValueError("未识别到药品信息")
            
            if not case.recognized_entities.diseases:
                raise ValueError("未识别到疾病信息")
            
            # 知识增强
            enhanced_case = self.knowledge_enhancer.enhance_case(case)
            logger.debug(f"Enhanced case: {enhanced_case}")
            
            # 规则分析
            rule_result = self.rule_analyzer.analyze(
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
            logger.debug(f"Rule analysis result: {rule_result}")
            
            # 检查补充数据的可用性
            clinical_guidelines = enhanced_case.evidence.clinical_guidelines
            expert_consensus = enhanced_case.evidence.expert_consensus
            research_papers = enhanced_case.evidence.research_papers
            
            # 构建数据状态说明
            clinical_guidelines_status = "（数据不可用）" if not clinical_guidelines else ""
            expert_consensus_status = "（数据不可用）" if not expert_consensus else ""
            research_papers_status = "（数据不可用）" if not research_papers else ""
            
            # 构建分析提示
            prompt = create_indication_analysis_prompt(
                drug_name=enhanced_case.drug.name,
                indications=json.dumps(enhanced_case.drug.indications, ensure_ascii=False),
                pharmacology=enhanced_case.drug.pharmacology or "无相关信息",
                contraindications=json.dumps(enhanced_case.drug.contraindications, ensure_ascii=False),
                precautions=json.dumps(enhanced_case.drug.precautions, ensure_ascii=False),
                diagnosis=enhanced_case.disease.name,
                description=enhanced_case.context.description if enhanced_case.context else "",
                rule_analysis=json.dumps(rule_result, ensure_ascii=False),
                clinical_guidelines_status=clinical_guidelines_status,
                clinical_guidelines=json.dumps(clinical_guidelines or [], ensure_ascii=False),
                expert_consensus_status=expert_consensus_status,
                expert_consensus=json.dumps(expert_consensus or [], ensure_ascii=False),
                research_papers_status=research_papers_status,
                research_papers=json.dumps(research_papers or [], ensure_ascii=False)
            )
            logger.debug(f"Analysis prompt: {prompt}")

            # 调用模型
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的医学分析助手，请严格按照要求的JSON格式返回分析结果，不要添加任何额外的说明或注释。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 降低随机性
                max_tokens=2000,
                response_format={"type": "json_object"}  # 明确要求JSON格式响应
            )
            
            response = completion.choices[0].message.content
            logger.debug(f"Raw LLM response: {response}")
            
            # 解析响应
            try:
                # 清理和格式化响应
                cleaned_response = self._clean_json_response(response)
                logger.debug(f"Cleaned LLM response: {cleaned_response}")
                
                llm_result = json.loads(cleaned_response)
                logger.debug(f"Parsed LLM result: {llm_result}")
                
                # 综合分析结果
                final_result = self.result_synthesizer.synthesize(
                    rule_result,
                    llm_result,
                    {
                        "clinical_guidelines": clinical_guidelines or [],
                        "expert_consensus": expert_consensus or [],
                        "research_papers": research_papers or []
                    }
                )
                logger.debug(f"Final synthesized result: {final_result}")
                
                # 创建分析结果对象
                analysis = Analysis(
                    indication_match=IndicationMatch(
                        score=final_result["analysis"]["indication_match"]["score"],
                        matching_indication=final_result["analysis"]["indication_match"]["matching_indication"],
                        reasoning=final_result["analysis"]["indication_match"]["reasoning"]
                    ),
                    mechanism_similarity=MechanismSimilarity(
                        score=final_result["analysis"]["mechanism_similarity"]["score"],
                        reasoning=final_result["analysis"]["mechanism_similarity"]["reasoning"]
                    ),
                    evidence_support=EvidenceSupport(
                        level=final_result["analysis"]["evidence_support"]["level"],
                        description=final_result["analysis"]["evidence_support"]["description"]
                    )
                )
                
                recommendation = Recommendation(
                    decision=final_result["recommendation"]["decision"],
                    explanation=final_result["recommendation"]["explanation"],
                    risk_assessment=final_result["recommendation"]["risk_assessment"]
                )

                result = AnalysisResult(
                    is_offlabel=final_result["is_offlabel"],
                    confidence=final_result["confidence"],
                    analysis=analysis,
                    recommendation=recommendation,
                    evidence_synthesis=final_result.get("evidence_synthesis", {}),
                    metadata=final_result.get("metadata", {
                        "analysis_time": datetime.now().isoformat(),
                        "data_availability": {
                            "clinical_guidelines": bool(clinical_guidelines),
                            "expert_consensus": bool(expert_consensus),
                            "research_papers": bool(research_papers)
                        },
                        "data_limitations": final_result.get("data_limitations", {})
                    })
                )
                logger.debug(f"Final AnalysisResult: {result}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"解析模型响应时发生错误: {str(e)}")
                logger.error(f"原始响应: {response}")
                raise ValueError(f"无法解析模型响应: {str(e)}")
                
        except Exception as e:
            logger.error(f"分析适应症时发生错误: {str(e)}")
            raise
    
    def batch_analyze(self, cases: List[Case]) -> List[Case]:
        """批量分析多个病例
        
        Args:
            cases: 病例数据列表
            
        Returns:
            List[Case]: 更新后的病例列表
        """
        for case in cases:
            try:
                case.analysis_result = self.analyze_indication(case)
                case.updated_at = datetime.now()
            except Exception as e:
                logger.error(f"处理病例 {case.id} 时发生错误: {str(e)}")
