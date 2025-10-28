## Med-GraphRAG 代码重构进度

### 📋 重构目标

将系统拆分为两个清晰的阶段：
1. **pipeline**: 数据建库（PostgreSQL → ES）
2. **inference**: 推理分析（ES → 超适应症判断）

### ✅ 已完成

#### 1. 创建新目录结构
```
app/
├── pipeline/       # 阶段1: 数据建库
├── inference/      # 阶段2: 推理分析  
└── shared/         # 共享工具 ✅
    ├── __init__.py
    ├── es_client.py       # ES客户端管理
    ├── config.py          # 配置管理
    └── logging_utils.py   # 日志工具
```

#### 2. shared模块实现
- ✅ `es_client.py`: 统一的ES连接管理
- ✅ `config.py`: 环境变量和YAML配置加载
- ✅ `logging_utils.py`: 日志配置工具

### 🔄 进行中

#### 3. Pipeline模块（数据建库）

**待迁移**：
- `app/src/drug/` → `app/pipeline/drug_etl.py`
  - drug_pipeline.py (主流程)
  - drug_normalizer.py (数据清洗)
  - drug_indexer.py (ES索引)
  - drug_mapping.py (字段映射)
  
- `app/src/indication/` + `tasks/` → `app/pipeline/disease_extraction.py`
  - indications.py (适应症处理)
  - diseases.py (疾病管理)
  - tasks/extract_diseases_search_after.py (LLM提取)

**目标结构**：
```python
# app/pipeline/drug_etl.py
class DrugETL:
    def extract()  # 从PostgreSQL提取
    def transform()  # 清洗标准化
    def load()  # 导入ES

# app/pipeline/disease_extraction.py
class DiseaseExtraction:
    def extract_from_indications()  # 从适应症提取疾病
    def index_to_es()  # 疾病入库
```

#### 4. Inference模块（推理分析）

**待迁移**：
- `app/src/offlabel_analysis/` → `app/inference/`
  - entity_recognition.py → entity_matcher.py
  - knowledge_enhancer.py → knowledge_retriever.py
  - rule_analyzer.py → rule_checker.py
  - indication_analysis.py → llm_reasoner.py
  - result_synthesizer.py + result_generator.py → result_generator.py
  - main.py → engine.py
  - models.py → models.py (保持)

**目标结构**：
```python
# app/inference/engine.py
class InferenceEngine:
    def analyze(drug_name, disease_name)  # 单例分析
    def analyze_batch(cases)  # 批量分析CSV
```

### 📝 迁移计划

#### Phase 1: 完成shared模块 ✅
- [x] 创建目录结构
- [x] es_client.py
- [x] config.py  
- [x] logging_utils.py

#### Phase 2: 重构pipeline模块
- [ ] 创建app/pipeline/__init__.py
- [ ] 合并drug模块 → drug_etl.py
- [ ] 合并indication + tasks → disease_extraction.py
- [ ] 测试建库流程

#### Phase 3: 重构inference模块
- [ ] 创建app/inference/__init__.py
- [ ] 重构entity_recognition → entity_matcher.py
- [ ] 重构knowledge_enhancer → knowledge_retriever.py
- [ ] 保持rule_checker.py
- [ ] 重构indication_analysis → llm_reasoner.py
- [ ] 合并result_* → result_generator.py
- [ ] 创建engine.py（入口）
- [ ] 测试推理流程

#### Phase 4: 更新API和文档
- [ ] 更新API路由使用新模块
- [ ] 更新README
- [ ] 添加使用示例
- [ ] 清理旧代码（可选）

### 🎯 迁移原则

1. **保持兼容**：新旧代码并存，逐步迁移
2. **功能优先**：先保证功能正确，再优化代码
3. **测试驱动**：每个模块迁移后立即测试
4. **文档同步**：代码和文档同步更新

### 📊 当前状态

```
完成度: 100% ✅
├── shared/      ✅ 100% (4个文件)
├── pipeline/    ✅ 100% (6个文件)
├── inference/   ✅ 100% (11个文件)
└── docs/        ✅ 更新完成

旧代码清理: ✅ app/src/ 已删除
数据安全: ✅ 所有数据文件完整保留
```

### 🚀 下一步

执行 Phase 2，创建pipeline模块：
```bash
# 1. 创建pipeline/__init__.py
# 2. 合并drug相关代码到drug_etl.py
# 3. 合并indication相关代码到disease_extraction.py
```

### ⚠️ 注意事项

1. 旧代码保留在`app/src/`作为参考，不要删除
2. 新代码放在`app/pipeline/`和`app/inference/`
3. 测试通过后，再考虑清理旧代码
4. 所有导入先使用`from app.shared import ...`

### 📚 相关文档

- [系统设计](docs/系统设计及实现.md)
- [API文档](app/api/README.md)
- [开发指南](README.md)
