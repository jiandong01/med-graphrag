"""
数据建库模块 (Pipeline)

功能：
- 从PostgreSQL提取药品原始数据
- 清洗、标准化、结构化
- 导入Elasticsearch建立索引
- LLM提取疾病实体并入库

使用方式：
    # 药品ETL
    from app.pipeline.drug_etl import DrugETL
    etl = DrugETL()
    etl.run()
    
    # 疾病提取
    from app.pipeline.disease_extraction import DiseaseExtraction
    extractor = DiseaseExtraction()
    extractor.run()
"""

__all__ = []
