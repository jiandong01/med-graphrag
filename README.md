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
├── app/                         # 应用层
│   ├── api/                     # REST API 服务
│   │   ├── __init__.py
│   │   ├── __main__.py          # API 主入口
│   │   ├── routers/             # API 路由模块
│   │   └── README.md
│   ├── src/                     # 核心业务逻辑
│   │   ├── drug/                # 药品数据处理
│   │   ├── indication/          # 适应症处理
│   │   ├── offlabel_analysis/   # 超适应症分析
│   │   └── utils.py
│   ├── cli/                     # CLI 工具
│   └── requirements.txt
├── deployments/                 # 部署配置
│   ├── docker/                  # Docker 配置
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── kubernetes/              # K8s 配置（待实现）
├── services/                    # 基础设施服务
│   ├── elasticsearch/           # Elasticsearch + Kibana
│   ├── mysql/                   # MySQL 数据库
│   └── postgresql/              # PostgreSQL + pgvector
├── tests/                       # 测试用例
├── examples/                    # 示例病例
├── docs/                        # 文档
│   └── development/             # 开发文档
├── scripts/                     # 工具脚本
├── Makefile                     # 运维命令
├── docker-compose.yml           # 服务编排
└── config.yaml                  # 配置文件
```

## 🔧 核心组件

### 1. 应用层 (app/)

#### API 服务 (app/api/)
- **REST API**: 提供完整的 HTTP 接口
- **Swagger 文档**: 自动生成的 API 文档
- **健康检查**: 服务状态监控

#### 核心业务逻辑 (app/src/)

**药品数据处理 (drug/)**
- **DrugPipeline**: 完整的 ETL 数据管道
- **DrugIndexer**: Elasticsearch 索引管理
- **DrugNormalizer**: 数据标准化处理

**适应症管理 (indication/)**
- **IndicationProcessor**: LLM 驱动的适应症提取
- **DiseaseManager**: 疾病实体索引和检索
- **CLI**: 命令行操作接口

**超适应症分析 (offlabel_analysis/)**
- **EntityRecognizer**: 实体识别
- **IndicationAnalyzer**: 适应症匹配分析
- **KnowledgeEnhancer**: 知识图谱增强
- **RuleAnalyzer**: 规则推理
- **ResultSynthesizer**: 多维度结果综合

### 2. 部署层 (deployments/)
- **Docker**: 容器化部署配置
- **Kubernetes**: 云原生部署（待实现）

### 3. 基础设施层 (services/)
- **Elasticsearch**: 全文检索和知识图谱存储
- **MySQL**: 原始数据存储（可选）
- **PostgreSQL**: 向量检索（可选）

## 🚀 快速开始

### 方式一：使用 Docker Compose (推荐)

**一键启动 API 服务**：

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Keys

# 2. 启动所有服务 (API + Elasticsearch + Kibana)
docker compose up -d

# 3. 访问服务
# API 文档: http://localhost:8000/docs
# API 服务: http://localhost:8000
# Kibana: http://localhost:5601
```

详细说明见 [API 使用文档](api/README.md)

### 方式二：本地开发模式

**环境要求**：
- Python 3.8+
- Docker & Docker Compose
- MySQL 8.0 (可选)
- Elasticsearch 8.x

**安装步骤**：

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
   ```bash
   cp .env.example .env
   # 编辑 .env 文件
   ```

4. **启动 Elasticsearch**
   ```bash
   docker compose up -d elasticsearch
   ```

## 📖 使用说明

### 使用 Makefile 管理服务

```bash
# 查看所有可用命令
make help

# 启动开发环境
make dev

# 查看服务状态
make ps

# 查看日志
make logs

# 健康检查
make health

# 运行测试
make test
```

### 1. 构建药品索引

```bash
# 从 MySQL 导入药品数据到 Elasticsearch
python app/src/drug/drug_pipeline.py --clear

# 或使用 make 命令
make data-import
```

### 2. 提取适应症信息

```bash
# 处理适应症数据
python app/src/indication/cli.py process-indications --output-dir outputs/indications

# 提取疾病实体
python app/src/indication/cli.py process-diseases --data-dir outputs/indications
```

### 3. 分析超适应症病例（通过 API）

```bash
# 使用 curl 调用 API
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "age": 65,
      "gender": "男",
      "diagnosis": "心力衰竭"
    },
    "prescription": {
      "drug_name": "美托洛尔缓释片",
      "dosage": "47.5mg",
      "frequency": "qd"
    }
  }'
```

或在 Python 中：

```python
from app.src.offlabel_analysis.main import process_case

# 准备病例数据
case_data = {
    "patient_info": {
        "age": 65,
        "gender": "男",
        "diagnosis": "心力衰竭"
    },
    "prescription": {
        "drug_name": "美托洛尔缓释片",
        "dosage": "47.5mg"
    }
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
