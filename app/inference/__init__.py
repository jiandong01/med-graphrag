"""
推理分析模块 (Inference)

功能：
- 以Elasticsearch为单一数据源
- 实体识别与匹配
- 知识检索与增强
- 规则分析 + LLM推理
- 结果综合与生成

使用方式：
    # 单例分析
    from app.inference.engine import InferenceEngine
    
    engine = InferenceEngine()
    result = engine.analyze(
        drug_name="美托洛尔",
        disease_name="心力衰竭"
    )
    
    # 批量分析CSV
    import pandas as pd
    df = pd.read_csv("cases.csv")
    results = engine.analyze_batch(df.to_dict('records'))
"""

__all__ = []
