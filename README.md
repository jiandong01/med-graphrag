# 医疗超适应症知识增强推理系统

基于大语言模型(LLM)和 Elasticsearch 的医疗知识图谱系统，用于智能药品信息处理和超适应症用药分析。

## 🎯 系统功能

- **实体识别**: 自动识别病例中的药品和疾病实体
- **适应症分析**: 基于知识图谱的适应症匹配分析
- **知识增强**: 整合药品说明书、临床指南等医疗知识
- **推理综合**: 多维度评估并生成结构化分析报告
- **全文检索**: 基于 Elasticsearch 的高效药品信息检索

## 🏗️ 项目结构

```
202502-medical-graphrag/
├── src/
│   ├── drug/                    # 药品数据处理
│   │   ├── drug_pipeline.py     # ETL 数据管道
│   │   ├── drug_indexer.py      # Elasticsearch 索引
│   │   └── drug_normalizer.py   # 数据标准化
│   ├── indication/              # 适应症处理
│   │   ├── indications.py       # 适应症提取
│   │   ├── diseases.py          # 疾病实体管理
│   │   └── cli.py               # 命令行接口
│   ├── offlabel_analysis/       # 超适应症分析
│   │   ├── entity_recognition.py      # 实体识别
│   │   ├── indication_analysis.py     # 适应症分析
│   │   ├── knowledge_enhancer.py      # 知识增强
│   │   ├── rule_analyzer.py           # 规则分析
│   │   └── result_synthesizer.py      # 结果综合
│   └── utils.py                 # 工具函数
├── db/                          # 数据库配置
│   ├── mysql/                   # MySQL 数据库
│   ├── docker-elk/              # ELK Stack
│   └── pgsql/                   # PostgreSQL (可选)
├── tests/                       # 测试用例
├── examples/                    # 示例病例
└── config.yaml                  # 配置文件
```

## 🔧 核心组件

### 1. 药品数据处理 (drug/)

- **DrugPipeline**: 完整的 ETL 数据管道，从 MySQL 读取原始数据
- **DrugIndexer**: 创建和管理 Elasticsearch 索引
- **DrugNormalizer**: 药品信息标准化和分类处理

### 2. 适应症管理 (indication/)

- **IndicationProcessor**: LLM 驱动的适应症提取
- **DiseaseManager**: 疾病实体索引和检索
- **CLI**: 命令行操作接口

### 3. 超适应症分析 (offlabel_analysis/)

- **EntityRecognizer**: 识别病例中的药品和疾病
- **IndicationAnalyzer**: 分析适应症匹配情况
- **KnowledgeEnhancer**: 从知识图谱获取补充信息
- **RuleAnalyzer**: 基于规则的初步判断
- **ResultSynthesizer**: 综合多维度结果

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Docker & Docker Compose
- MySQL 8.0
- Elasticsearch 8.x

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd 202502-medical-graphrag
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   
   创建 `.env` 文件：
   ```bash
   # LLM API Keys
   HF_API_KEY=your_huggingface_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   
   # MySQL
   MYSQL_USER=myuser
   MYSQL_PASSWORD=mypassword
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DB=mydatabase
   
   # Elasticsearch
   ES_HOST=http://localhost:9200
   ES_USERNAME=elastic
   ELASTIC_PASSWORD=changeme
   ```

4. **启动数据库服务**
   ```bash
   # 启动 MySQL
   cd db/mysql && docker compose up -d
   
   # 启动 ELK Stack
   cd db/docker-elk && docker compose up -d
   ```

## 📖 使用说明

### 1. 构建药品索引

```bash
# 从 MySQL 导入药品数据到 Elasticsearch
python src/drug/drug_pipeline.py --clear
```

### 2. 提取适应症信息

```bash
# 处理适应症数据
python src/indication/cli.py process-indications --output-dir outputs/indications

# 提取疾病实体
python src/indication/cli.py process-diseases --data-dir outputs/indications
```

### 3. 分析超适应症病例

```python
from src.offlabel_analysis.main import process_case

# 准备病例数据
case_data = {
    "patient_info": "患者信息",
    "prescription": "处方信息",
    "diagnosis": "诊断信息"
}

# 执行分析
result = process_case(case_data)
print(result)
```

## 💾 数据库架构

### MySQL (原始数据)
- `drugs_table`: 药品基础信息
- `drug_details_table`: 药品详情（适应症、禁忌症等）
- `categories_table`: 药品分类信息

### Elasticsearch (检索引擎)
- `drugs_index`: 药品信息索引
- `diseases_index`: 疾病实体索引

### PostgreSQL + pgvector (可选)
- 向量相似度检索
- 语义搜索增强

## 🧪 测试

```bash
# 运行测试
pytest tests/

# 运行特定测试
pytest tests/test_entity_recognition.py
```

## 📊 示例病例

项目提供了三个示例病例：

1. **标准用药** (`examples/cases/case1_standard/`)
2. **合理超适应症** (`examples/cases/case2_reasonable_offlabel/`)
3. **不合理超适应症** (`examples/cases/case3_unreasonable_offlabel/`)

每个案例包含完整的分析流程和结果。

## 🔍 系统流程

```
输入病例
   ↓
实体识别 (EntityRecognizer)
   ↓
知识增强 (KnowledgeEnhancer)
   ↓
适应症分析 (IndicationAnalyzer)
   ↓
规则分析 (RuleAnalyzer)
   ↓
结果综合 (ResultSynthesizer)
   ↓
生成报告 (ResultGenerator)
```

## 📝 配置说明

主配置文件 `config.yaml`:

```yaml
paths:
  output_dir: "outputs"
  logs_dir: "logs"

elasticsearch:
  host: "http://localhost:9200"
  username: "elastic"
  
llm:
  provider: "openrouter"  # 或 "huggingface"
  model: "meta-llama/llama-3.1-8b-instruct"
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 联系方式

如有问题或建议，请提交 Issue。
