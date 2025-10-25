# PostgreSQL 数据库项目

本项目包含一个独立的 PostgreSQL 数据库实例，包含医疗数据的三张表。

## 项目结构

```
postgres/
├── docker-compose.yaml           # Docker Compose 配置文件
├── .env.example                  # 环境变量模板
├── .env                          # 实际环境变量（不提交到Git）
├── .gitignore                    # Git忽略文件配置
├── README.md                     # 本文档
├── config/                       # PostgreSQL 配置文件目录
│   └── postgresql.conf           # PostgreSQL 自定义配置
├── init/                         # 数据库初始化脚本目录
│   └── 01_create_tables.sql      # 表结构定义
└── data/                         # PostgreSQL 数据存储目录（持久化）
    └── .gitkeep                  # 保持目录结构
```

### 目录说明

- **config/**: PostgreSQL 配置文件，可根据实际需求调整数据库参数
- **init/**: 初始化 SQL 脚本，容器首次启动时自动执行
- **data/**: 数据持久化目录，包含数据库文件和日志

## 数据库信息

### 连接信息

连接信息通过环境变量配置（见下方配置说明）：

- **Host:** localhost
- **Port:** 默认 5432（可通过 `POSTGRES_PORT` 配置）
- **Database:** 通过 `POSTGRES_DB` 配置
- **Username:** 通过 `POSTGRES_USER` 配置
- **Password:** 通过 `POSTGRES_PASSWORD` 配置

### 数据表

| 表名               | 说明       | 记录数    |
| ------------------ | ---------- | --------- |
| categories_table   | 分类表     | 1,206     |
| drugs_table        | 药品表     | 137,065   |
| drug_details_table | 药品详情表 | 1,598,722 |

## 快速开始

### 1. 配置环境变量

首次使用前，需要配置数据库连接信息：

```bash
# 复制环境变量模板文件
cp .env.example .env

# 编辑 .env 文件，设置你的数据库配置
# 特别注意修改 POSTGRES_PASSWORD 为强密码
nano .env  # 或使用其他编辑器
```

`.env` 文件示例：

```bash
POSTGRES_DB=mydatabase
POSTGRES_USER=pguser
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_PORT=5432
```

⚠️ **安全提示：** `.env` 文件包含敏感信息，已添加到 `.gitignore`，不会被提交到 Git 仓库。

### 1.5. 调整 PostgreSQL 配置（可选）

如需调整数据库性能参数，可编辑 `config/postgresql.conf` 文件：

```bash
# 编辑配置文件
nano config/postgresql.conf
```

**常用配置项说明：**

- `shared_buffers`: 共享内存缓冲区大小，建议设置为系统内存的 25%
- `effective_cache_size`: 可用于缓存的内存估计值，建议设置为系统内存的 50-75%
- `max_connections`: 最大连接数
- `work_mem`: 每个查询操作可用的内存
- `log_min_duration_statement`: 记录慢查询的阈值（毫秒）

配置修改后需要重启容器才能生效。

### 2. 启动 PostgreSQL

```bash
docker-compose up -d
```

### 3. 查看运行状态

```bash
docker-compose ps
```

### 4. 查看日志

```bash
docker-compose logs -f postgres
```

### 5. 停止服务

```bash
docker-compose stop
```

### 6. 停止并删除容器

```bash
docker-compose down
```

## 数据库操作

### 连接到数据库

```bash
# 使用 psql 客户端（替换为你的实际用户名和数据库名）
docker exec -it postgres_container psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# 或直接使用具体值
docker exec -it postgres_container psql -U pguser -d mydatabase
```

### 常用 SQL 命令

```sql
-- 列出所有表
\dt

-- 查看表结构
\d categories_table

-- 查询数据
SELECT COUNT(*) FROM categories_table;
SELECT * FROM categories_table LIMIT 10;

-- 退出
\q
```

### 使用 DBeaver 连接

1. 打开 DBeaver
2. 创建新连接 → PostgreSQL
3. 输入连接信息（使用 `.env` 文件中配置的值）
   - Host: localhost
   - Port: 5432（或你配置的端口）
   - Database: 你的数据库名
   - Username: 你的用户名
   - Password: 你的密码
4. 测试连接
5. 完成

## 数据备份与恢复

### 备份数据库

```bash
# 备份所有数据（替换为你的实际用户名和数据库名）
docker exec postgres_container pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_$(date +%Y%m%d).sql

# 备份特定表
docker exec postgres_container pg_dump -U ${POSTGRES_USER} -t categories_table ${POSTGRES_DB} > categories_backup.sql
```

### 恢复数据库

```bash
# 从备份恢复（替换为你的实际用户名和数据库名）
docker exec -i postgres_container psql -U ${POSTGRES_USER} ${POSTGRES_DB} < backup.sql
```

## 性能优化

### 更新统计信息

```bash
docker exec postgres_container psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "VACUUM ANALYZE;"
```

### 查看表大小

```bash
docker exec postgres_container psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## 配置说明

### 修改端口

编辑 `.env` 文件中的 `POSTGRES_PORT`：

```bash
POSTGRES_PORT=5433
```

### 修改密码或其他配置

编辑 `.env` 文件中的相应变量：

```bash
POSTGRES_DB=mydatabase
POSTGRES_USER=newuser
POSTGRES_PASSWORD=new_strong_password
POSTGRES_PORT=5432
```

⚠️ **重要：** 修改后需要删除 `data` 目录并重新初始化：

```bash
docker-compose down
rm -rf data/*
docker-compose up -d
```

## 故障排除

### 问题 1：端口已被占用

**错误信息：** `Bind for 0.0.0.0:5432 failed: port is already allocated`

**解决方法：**

- 修改 docker-compose.yaml 中的端口映射
- 或停止占用 5432 端口的其他服务

### 问题 2：数据目录权限问题

**解决方法：**

```bash
sudo chown -R 999:999 storage/
```

### 问题 3：容器无法启动

**检查日志：**

```bash
docker-compose logs postgres
```

## 数据迁移说明

本项目的数据已从 MySQL 迁移而来，包含：

- 原 MySQL 表 `zhushou` → PostgreSQL 表 `categories_table`
- 原 MySQL 表 `zhushouc` → PostgreSQL 表 `drugs_table`
- 原 MySQL 表 `zhushour` → PostgreSQL 表 `drug_details_table`

所有数据已完整迁移，总计 1,736,993 条记录。

## 技术栈

- **PostgreSQL:** 15
- **Docker:** 用于容器化部署
- **Docker Compose:** 用于服务编排

## 配置文件说明

### PostgreSQL 配置 (config/postgresql.conf)

本项目提供了优化的 PostgreSQL 配置文件，主要配置项包括：

**性能相关：**

- 内存设置（shared_buffers, effective_cache_size 等）
- WAL 日志配置
- 查询优化参数

**日志相关：**

- 开启慢查询日志（默认记录超过 1 秒的查询）
- 日志轮转配置
- 详细的日志格式

**维护相关：**

- 自动清理(autovacuum)配置
- 统计信息收集

根据你的服务器配置，建议调整以下参数：

```conf
shared_buffers = 256MB              # 系统内存的25%
effective_cache_size = 1GB          # 系统内存的50-75%
```

## 注意事项

1. **环境变量：** 首次使用前必须配置 `.env` 文件，`.env` 文件不会被提交到 Git 仓库
2. **数据持久化：** 数据存储在 `data` 目录，删除此目录会丢失所有数据
3. **配置文件：** `config/postgresql.conf` 可根据实际需求调整，修改后需重启容器
4. **初始化脚本：** `init` 目录中的 SQL 文件只在首次创建数据库时执行
5. **生产环境：** 必须使用强密码，不要使用示例中的默认值
6. **备份策略：** 定期备份数据到安全的位置
7. **安全性：** 永远不要将 `.env` 文件提交到版本控制系统
8. **日志管理：** PostgreSQL 日志存储在 `data/pg_log/` 目录，定期清理以节省空间

## 维护建议

### 定期维护

```bash
# 1. 优化数据库性能
docker exec postgres_container psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "VACUUM ANALYZE;"

# 2. 查看数据库大小
docker exec postgres_container psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT pg_size_pretty(pg_database_size('${POSTGRES_DB}'));"

# 3. 查看慢查询日志
docker exec postgres_container tail -f /var/lib/postgresql/data/pg_log/postgresql-*.log
```

### 性能监控

建议定期关注：

- 连接数使用情况
- 慢查询日志（超过 1 秒的查询）
- 数据库大小增长趋势
- 缓存命中率
- 死锁情况

### 配置调优

根据实际使用情况调整 `config/postgresql.conf` 中的参数：

- 如果内存充足，可增加 `shared_buffers` 和 `effective_cache_size`
- 如果有大量并发连接，可适当增加 `max_connections`
- 如果经常有复杂查询，可增加 `work_mem`
- 定期检查日志，优化慢查询

### 备份策略

建议采用多层备份策略：

1. **每日全量备份**：保留最近 7 天
2. **每周归档**：保留最近 4 周
3. **每月归档**：长期保存

## 支持与反馈

如有问题或建议，请联系项目维护者。
