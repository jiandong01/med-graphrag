"""推理引擎 - 超适应症分析的主入口"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from app.shared import setup_logging
from .entity_matcher import EntityRecognizer
from .llm_reasoner import IndicationAnalyzer
from .result_generator import ResultGenerator
from .models import Case

logger = setup_logging("inference_engine")


class InferenceEngine:
    """推理引擎 - 协调所有分析步骤"""
    
    def __init__(self):
        """初始化推理引擎"""
        self.entity_recognizer = EntityRecognizer()
        self.indication_analyzer = IndicationAnalyzer()
        self.result_generator = ResultGenerator()
        logger.info("推理引擎初始化完成")
    
    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """单例分析
        
        Args:
            input_data: 输入数据
                {
                    "drug_name": "美托洛尔",
                    "disease_name": "心力衰竭",
                    "patient": {...}  # 可选
                }
        
        Returns:
            Dict: 分析结果
                {
                    "offlabel_status": "reasonable_offlabel",
                    "confidence": 0.85,
                    "reasoning": [...],
                    "recommendation": {...}
                }
        """
        try:
            # 1. 实体识别
            logger.info("开始实体识别...")
            recognized_entities = self.entity_recognizer.recognize(input_data)
            
            # 2. 创建病例对象
            case = Case(
                id=input_data.get('id', str(datetime.now().timestamp())),
                recognized_entities=recognized_entities
            )
            
            # 3. 适应症分析
            logger.info("开始适应症分析...")
            case.analysis_result = self.indication_analyzer.analyze_indication(case)
            
            # 4. 生成结果
            logger.info("生成分析结果...")
            final_result = self.result_generator.generate(case)
            
            return final_result
            
        except Exception as e:
            logger.error(f"处理病例时发生错误: {str(e)}")
            raise
    
    def analyze_batch(self, input_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量分析
        
        Args:
            input_data_list: 输入数据列表
        
        Returns:
            List[Dict]: 分析结果列表
        """
        results = []
        total = len(input_data_list)
        
        logger.info(f"开始批量分析: {total} 个病例")
        
        for idx, input_data in enumerate(input_data_list, 1):
            try:
                logger.info(f"处理 {idx}/{total}: {input_data.get('drug_name', 'unknown')} - {input_data.get('disease_name', 'unknown')}")
                result = self.analyze(input_data)
                results.append(result)
                
            except Exception as e:
                logger.error(f"处理病例 {input_data.get('id', 'unknown')} 时发生错误: {str(e)}")
                results.append({
                    "id": input_data.get('id', 'unknown'),
                    "error": str(e),
                    "input": input_data
                })
        
        logger.info(f"批量分析完成: 成功 {len([r for r in results if 'error' not in r])}/{total}")
        return results


# 保持向后兼容的函数接口
def process_case(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个病例 (向后兼容接口)"""
    engine = InferenceEngine()
    return engine.analyze(input_data)


def batch_process(input_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理 (向后兼容接口)"""
    engine = InferenceEngine()
    return engine.analyze_batch(input_data_list)
