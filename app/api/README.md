# Medical GraphRAG API 使用文档

基于知识图谱的医疗超适应症用药分析系统 REST API 服务。

## 🚀 快速开始

### 1. 环境准备

创建 `.env` 文件：

```bash
# LLM API Keys (必需)
HF_API_KEY=your_huggingface_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Elasticsearch (可选，使用默认值)
ELASTIC_PASSWORD=changeme

# MySQL (可选，仅数据导入时需要)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=myuser
MYSQL_PASSWORD=mypassword
MYSQL_DB=mydatabase
```

### 2. 启动服务

使用 Docker Compose 一键启动：

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api
```

服务启动后：
- API 服务: http://localhost:8000
- API 文档: http://localhost:8000/docs
- Kibana: http://localhost:5601

### 3. 健康检查

```bash
curl http://localhost:8000/health
```

响应示例：
```json
{
  "status": "healthy",
  "timestamp": "2025-01-24T12:00:00",
  "elasticsearch": "connected",
  "version": "1.0.0"
}
```

## 📖 API 接口

### 1. 超适应症用药分析

**POST** `/api/v1/analyze`

分析处方药品对于患者诊断疾病的适用性。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "age": 65,
      "gender": "男",
      "diagnosis": "心力衰竭",
      "medical_history": "高血压10年"
    },
    "prescription": {
      "drug_name": "美托洛尔缓释片",
      "dosage": "47.5mg",
      "frequency": "qd",
      "duration": "长期"
    },
    "clinical_context": "慢性心力衰竭，NYHA II级"
  }'
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "offlabel_status": "reasonable_offlabel",
    "conclusion": "该用药属于合理超适应症用药",
    "rationale": [
      "虽然说明书未明确列出心力衰竭，但有充分循证医学证据支持",
      "国内外权威指南均推荐β受体阻滞剂用于慢性心衰治疗"
    ],
    "confidence": 0.85,
    "evidence_sources": [
      "ACC/AHA 心力衰竭指南 (2022)",
      "中国心力衰竭诊断和治疗指南"
    ]
  },
  "timestamp": "2025-01-24T12:00:00"
}
```

### 2. 批量分析

**POST** `/api/v1/analyze/batch`

批量处理多个病例的超适应症用药分析。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/analyze/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "cases": [
      {
        "patient": {...},
        "prescription": {...}
      },
      {
        "patient": {...},
        "prescription": {...}
      }
    ]
  }'
```

### 3. 实体识别

**POST** `/api/v1/entity/recognize`

从文本中识别药品和疾病实体。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/entity/recognize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "患者诊断为高血压，处方阿司匹林肠溶片",
    "context": "门诊处方"
  }'
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "drugs": [
      {
        "name": "阿司匹林肠溶片",
        "id": "drug_12345",
        "confidence": 0.95
      }
    ],
    "diseases": [
      {
        "name": "高血压",
        "id": "disease_67890",
        "confidence": 0.98
      }
    ]
  },
  "timestamp": "2025-01-24T12:00:00"
}
```

### 4. 药品搜索

**POST** `/api/v1/search/drug`

根据关键词搜索药品信息。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/search/drug" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "阿司匹林",
    "size": 10
  }'
```

### 5. 疾病搜索

**POST** `/api/v1/search/disease`

根据关键词搜索疾病信息。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/search/disease" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "心力衰竭",
    "size": 10
  }'
```

### 6. 药品详情

**POST** `/api/v1/drug/detail`

获取完整的药品信息。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/drug/detail" \
  -H "Content-Type: application/json" \
  -d '{
    "drug_name": "美托洛尔缓释片"
  }'
```

### 7. 疾病详情

**POST** `/api/v1/disease/detail`

获取完整的疾病信息。

**请求示例**：
```bash
curl -X POST "http://localhost:8000/api/v1/disease/detail" \
  -H "Content-Type: application/json" \
  -d '{
    "disease_name": "心力衰竭"
  }'
```

## 🐍 Python 客户端示例

```python
import requests

# API 基础 URL
BASE_URL = "http://localhost:8000"

# 超适应症分析
def analyze_offlabel(patient, prescription, clinical_context=None):
    """分析超适应症用药"""
    url = f"{BASE_URL}/api/v1/analyze"
    data = {
        "patient": patient,
        "prescription": prescription,
        "clinical_context": clinical_context
    }
    response = requests.post(url, json=data)
    return response.json()

# 使用示例
patient = {
    "age": 65,
    "gender": "男",
    "diagnosis": "心力衰竭",
    "medical_history": "高血压10年"
}

prescription = {
    "drug_name": "美托洛尔缓释片",
    "dosage": "47.5mg",
    "frequency": "qd"
}

result = analyze_offlabel(patient, prescription)
print(f"分析结果: {result['data']['conclusion']}")
print(f"置信度: {result['data']['confidence']}")
```

## 🔧 开发模式

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt
pip install -r api/requirements.txt

# 启动开发服务器
cd 202502-medical-graphrag
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 测试

```bash
# 运行测试
pytest tests/

# 查看 API 文档
# 浏览器访问: http://localhost:8000/docs
```

## 📊 性能优化

### 1. 并发处理

API 默认使用 4 个 worker 进程：

```yaml
# docker-compose.yml
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

可根据服务器配置调整 worker 数量：
```bash
# 推荐: CPU核心数 * 2 + 1
workers = (2 * cpu_cores) + 1
```

### 2. 响应缓存

可以使用 Redis 缓存常见查询：

```python
# 添加 Redis 服务到 docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

### 3. 负载均衡

生产环境建议使用 Nginx 作为反向代理：

```nginx
upstream medical_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://medical_api;
    }
}
```

## 🔒 安全配置

### 1. API 认证

在 `api/main.py` 中添加认证中间件：

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/api/v1/analyze")
async def analyze(request: AnalysisRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    # 验证 token
    verify_token(credentials.credentials)
    ...
```

### 2. CORS 配置

生产环境应限制允许的域名：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 指定允许的域名
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)
```

### 3. 速率限制

使用 `slowapi` 限制请求频率：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/analyze")
@limiter.limit("10/minute")
async def analyze(...):
    ...
```

## 🐛 故障排查

### 1. Elasticsearch 连接失败

```bash
# 检查 ES 服务状态
docker compose logs elasticsearch

# 测试连接
curl -u elastic:changeme http://localhost:9200/_cluster/health
```

### 2. API 响应慢

```bash
# 查看 API 日志
docker compose logs -f api

# 检查资源使用
docker stats
```

### 3. 内存不足

调整 Elasticsearch 内存限制：

```yaml
environment:
  - "ES_JAVA_OPTS=-Xms1g -Xmx1g"  # 增加到 1GB
```

## 📝 日志

日志文件位置：
- API 日志: `logs/api_*.log`
- 错误日志: `logs/api_error_*.log`

查看日志：
```bash
# 实时查看
tail -f logs/api_$(date +%Y%m%d)_*.log

# 搜索错误
grep "ERROR" logs/api_*.log
```

## 🔄 版本更新

```bash
# 停止服务
docker compose down

# 拉取最新代码
git pull

# 重新构建并启动
docker compose build
docker compose up -d
```

## 📞 技术支持

- 问题反馈: 提交 GitHub Issue
- API 文档: http://localhost:8000/docs
- 系统监控: http://localhost:5601 (Kibana)
