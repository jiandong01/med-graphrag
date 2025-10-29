"""
数据建库模块 (Pipeline)

这个模块负责将原始医疗数据处理并导入Elasticsearch，构建知识图谱的基础。

## 模块文件说明 (6个核心文件)

### 药品数据流程 (Drug Pipeline)
1. **drug_etl.py** - 药品ETL主流程 ⭐
   - DrugPipeline类：协调整个药品数据处理
   - PostgreSQL/MySQL → 清洗标准化 → ES索引
   - 调用normalizer清洗，调用indexer导入
   
2. **drug_normalizer.py** - 数据标准化
   - DrugNormalizer类：清洗和标准化
   - 标准化名称、规格、成分、适应症
   - 提取结构化字段
   
3. **drug_indexer.py** - ES索引管理
   - DrugIndexer类：药品索引操作
   - 创建mapping、批量导入
   
4. **drug_mapping.py** - 字段映射定义
   - 标准字段结构定义
   - 标签转换规则

### 疾病数据流程 (Disease Pipeline)
5. **disease_extraction.py** - 疾病提取主流程 ⭐
   - AsyncDiseaseExtractionSearchAfter类：LLM提取疾病
   - ES适应症文本 → LLM分析 → 批次文件
   - 异步并发处理，支持断点续传
   
6. **disease_indexer.py** - ES索引管理
   - DiseaseIndexer类：疾病索引操作
   - 批次聚合 → 去重统计 → ES索引
   - 建立药品-疾病关联

## 命名规范

- `*_etl.py` - 主流程（Extract-Transform-Load）
- `*_extraction.py` - 数据提取流程
- `*_indexer.py` - Elasticsearch索引管理
- `*_normalizer.py` - 数据标准化工具
- `*_mapping.py` - 字段映射定义

## 完整工作流程

### 阶段1: 药品数据建库
```bash
# 从PostgreSQL提取并处理药品数据
python -m app.pipeline.drug_etl --output data/raw/drugs/

# 导入Elasticsearch
python -m app.pipeline.drug_etl --load
```

### 阶段2: 疾病数据提取
```bash
# 从药品适应症提取疾病（LLM）
python -m app.pipeline.disease_extraction --concurrency 20 --resume

# 构建疾病索引（聚合并导入ES）
python -m app.pipeline.disease_indexer --rebuild
```

## 数据流转

```
PostgreSQL (原始药品)
    ↓ drug_etl.py + drug_normalizer.py
data/raw/drugs/processed_drugs.json (86k药品)
    ↓ drug_indexer.py
Elasticsearch: drugs索引
    ↓ disease_extraction.py (LLM提取)
data/processed/diseases/ (342批次)
    ↓ disease_indexer.py (聚合去重)
Elasticsearch: diseases索引 (8.5k疾病)
```

## 当前数据状态

- ✅ 药品索引: 86,345个
- ✅ 疾病索引: 8,585个（从25,561个名称去重）
- ✅ 药品-疾病关联已建立
- ✅ 知识图谱完整可用

使用示例：
    # 药品ETL
    from app.pipeline.drug_etl import DrugPipeline
    pipeline = DrugPipeline(db_url, es_config)
    pipeline.run()
    
    # 疾病提取  
    from app.pipeline.disease_extraction import AsyncDiseaseExtractionSearchAfter
    extractor = AsyncDiseaseExtractionSearchAfter()
    extractor.run()
    
    # 疾病索引
    from app.pipeline.disease_indexer import DiseaseIndexer
    indexer = DiseaseIndexer()
    indexer.run(rebuild=True)
"""

__all__ = []
