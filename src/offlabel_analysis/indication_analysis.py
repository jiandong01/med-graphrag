"""适应症分析核心逻辑"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
from huggingface_hub import InferenceClient
from elasticsearch import Elasticsearch

from src.utils import get_elastic_client, load_env
from .models import Case, AnalysisResult

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 提示模板
ANALYSIS_PROMPT_TEMPLATE = """请分析以下用药情况是否属于超适应症用药。

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

请进行分析并以JSON格式返回结果，包含以下字段：
{{
    "is_offlabel": true/false,  # 是否为超适应症用药
    "analysis": {{
        "indication_match": {{
            "score": float,  # 与标准适应症的匹配度(0-1)
            "matching_indication": str,  # 最匹配的标准适应症
            "reasoning": str  # 匹配度分析原因
        }},
        "mechanism_similarity": {{
            "score": float,  # 机制相似度(0-1)
            "reasoning": str  # 机制相似性分析
        }},
        "evidence_support": {{
            "level": str,  # 证据等级：A/B/C/D
            "description": str  # 支持证据说明
        }}
    }},
    "recommendation": {{
        "decision": str,  # "建议使用"/"谨慎使用"/"不建议使用"
        "explanation": str,  # 建议说明
        "risk_assessment": str  # 风险评估
    }}
}}"""

class IndicationAnalyzer:
    """适应症分析器 - 分析用药是否属于超适应症"""
    
    def __init__(self, es: Elasticsearch = None, api_key: str = None):
        """初始化分析器
        
        Args:
            es: Elasticsearch客户端实例
            api_key: HuggingFace API key
        """
        self.es = es or get_elastic_client()
        self.drugs_index = 'drugs'
        
        # HuggingFace设置
        load_env()
        self.api_key = api_key or os.getenv('HF_API_KEY')
        if not self.api_key:
            raise ValueError("HF_API_KEY not found")
        
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key
        )
    
    def get_drug_info(self, drug_id: str) -> Dict[str, Any]:
        """获取药品的详细信息
        
        Args:
            drug_id: 药品ID
            
        Returns:
            Dict[str, Any]: 药品详细信息
        """
        try:
            result = self.es.get(index=self.drugs_index, id=drug_id)
            return result['_source']
        except Exception as e:
            logger.error(f"获取药品信息时发生错误: {str(e)}")
            raise

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
            
            drug = case.recognized_entities.drugs[0]
            if not drug.matches:
                raise ValueError("未找到匹配的标准药品")
            
            # 获取药品详细信息
            drug_info = self.get_drug_info(drug.matches[0].id)
            
            if not case.recognized_entities.diseases:
                raise ValueError("未识别到疾病信息")
            
            # 构建分析提示
            prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                drug_name=drug_info['name'],
                indications=json.dumps(drug_info.get('indications', []), ensure_ascii=False),
                pharmacology=drug_info.get('details', {}).get('药理毒理', '无相关信息'),
                contraindications=json.dumps(drug_info.get('contraindications', []), ensure_ascii=False),
                precautions=json.dumps(drug_info.get('precautions', []), ensure_ascii=False),
                diagnosis=case.recognized_entities.diseases[0].name,
                description=case.recognized_entities.context.description if case.recognized_entities.context else ""
            )

            # 调用模型
            response = self.client.text_generation(
                prompt,
                model="Qwen/Qwen-14B-Chat",
                max_new_tokens=2000,
                temperature=0.1,
                repetition_penalty=1.1
            )
            
            # 解析响应
            try:
                result = json.loads(response)
                # 添加分析元数据
                result.update({
                    'metadata': {
                        'analysis_time': datetime.now().isoformat(),
                        'model_used': "Qwen-14B-Chat",
                        'drug_id': drug.matches[0].id,
                        'disease_id': case.recognized_entities.diseases[0].matches[0].id if case.recognized_entities.diseases[0].matches else None
                    }
                })
                return AnalysisResult(**result)
                
            except json.JSONDecodeError as e:
                logger.error(f"解析模型响应时发生错误: {str(e)}")
                raise
                
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
                continue
        return cases
