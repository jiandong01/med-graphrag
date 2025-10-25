"""主流程控制"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from .models import Case
from .entity_recognition import EntityRecognizer
from .indication_analysis import IndicationAnalyzer
from .result_generator import ResultGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_case(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个病例
    
    Args:
        input_data: 输入数据
        
    Returns:
        Dict: 处理结果
    """
    try:
        # 1. 实体识别
        logger.info("开始实体识别...")
        recognizer = EntityRecognizer()
        recognized_entities = recognizer.recognize(input_data)
        
        # 2. 创建病例对象
        case = Case(
            id=input_data.get('id', str(datetime.now().timestamp())),
            recognized_entities=recognized_entities
        )
        
        # 3. 适应症分析
        logger.info("开始适应症分析...")
        analyzer = IndicationAnalyzer()
        case.analysis_result = analyzer.analyze_indication(case)
        
        # 4. 生成结果
        logger.info("生成分析结果...")
        generator = ResultGenerator()
        final_result = generator.generate(case)
        
        return final_result
        
    except Exception as e:
        logger.error(f"处理病例时发生错误: {str(e)}")
        raise

def batch_process(input_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理多个病例
    
    Args:
        input_data_list: 输入数据列表
        
    Returns:
        List[Dict]: 处理结果列表
    """
    results = []
    for input_data in input_data_list:
        try:
            result = process_case(input_data)
            results.append(result)
        except Exception as e:
            logger.error(f"处理病例 {input_data.get('id', 'unknown')} 时发生错误: {str(e)}")
            results.append({
                "id": input_data.get('id', 'unknown'),
                "error": str(e)
            })
    return results
