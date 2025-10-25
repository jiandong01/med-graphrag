# Infrastructure Services

基础设施服务配置

## 服务列表

- `mysql/` - MySQL 数据库服务
- `elasticsearch/` - Elasticsearch 搜索引擎
- `postgresql/` - PostgreSQL + pgvector 向量数据库

## 使用方式

每个服务都可以独立启动：

```bash
# 启动 Elasticsearch
cd services/elasticsearch && docker compose up -d

# 启动 MySQL
cd services/mysql && docker compose up -d

# 启动 PostgreSQL
cd services/postgresql && docker compose up -d
```

或使用根目录的 Makefile：

```bash
make start-es
make start-mysql
make start-pg
```
