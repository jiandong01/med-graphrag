.PHONY: help setup clean deploy build up down restart logs status

# 默认显示帮助
.DEFAULT_GOAL := help

COMPOSE := docker compose

# 颜色输出
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# ==================== 帮助 ====================

help: ## 显示帮助信息
	@echo "$(BLUE)Medical GraphRAG 运维命令$(NC)"
	@echo ""
	@echo "$(GREEN)基础命令:$(NC)"
	@echo "  make setup              初始化环境"
	@echo "  make clean              清理临时文件和 Docker 资源"
	@echo "  make deploy             构建并启动所有服务"
	@echo ""
	@echo "$(GREEN)服务操作（默认对所有服务）:$(NC)"
	@echo "  make build              构建所有镜像"
	@echo "  make up                 启动所有服务"
	@echo "  make down               停止所有服务"
	@echo "  make restart            重启所有服务"
	@echo "  make logs               查看所有日志"
	@echo "  make status             查看所有状态"
	@echo ""
	@echo "$(GREEN)特定服务操作（格式: make <service>-<action>）:$(NC)"
	@echo "  $(YELLOW)服务:$(NC) api, es, postgres"
	@echo "  $(YELLOW)操作:$(NC) build, up, down, restart, logs, status"
	@echo ""
	@echo "$(GREEN)示例:$(NC)"
	@echo "  make api-build          构建 API 镜像"
	@echo "  make es-up              启动 Elasticsearch"
	@echo "  make api-logs           查看 API 日志"
	@echo "  make build              构建所有镜像"
	@echo "  make up                 启动所有服务"
	@echo ""

# ==================== 基础命令 ====================

setup: ## 初始化环境
	@echo "$(BLUE)初始化环境...$(NC)"
	@cp -n .env.example .env || true
	@echo "$(GREEN)✓ 环境配置文件已创建$(NC)"
	@echo ""
	@echo "$(YELLOW)请编辑 .env 文件配置以下 API Key:$(NC)"
	@echo "  - DEEPSEEK_API_KEY       (必需)"
	@echo "  - ELASTIC_PASSWORD       (可选，默认: changeme)"
	@echo ""
	@echo "$(GREEN)配置完成后运行:$(NC) make deploy"

clean: ## 清理临时文件和 Docker 资源
	@echo "$(BLUE)清理临时文件...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ 临时文件清理完成$(NC)"
	@echo ""
	@echo "$(BLUE)清理 Docker 资源...$(NC)"
	@docker system prune -f --filter "label=com.docker.compose.project=202502-medical-graphrag" 2>/dev/null || true
	@echo "$(YELLOW)清理未使用的卷（需要确认）:$(NC)"
	@docker volume ls -q --filter "name=202502-medical-graphrag" 2>/dev/null || true
	@echo "$(YELLOW)如需删除卷，运行: docker volume prune$(NC)"
	@echo "$(GREEN)✓ Docker 清理完成$(NC)"

deploy: ## 构建并启动所有服务
	@echo "$(BLUE)构建并部署所有服务...$(NC)"
	@$(COMPOSE) build
	@$(COMPOSE) up -d
	@echo "$(GREEN)✓ 部署完成$(NC)"
	@echo "$(YELLOW)API 文档: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Kibana: http://localhost:5601$(NC)"

# ==================== 所有服务操作 ====================

build: ## 构建所有镜像
	@echo "$(BLUE)构建所有镜像...$(NC)"
	@$(COMPOSE) build
	@echo "$(GREEN)✓ 完成$(NC)"

up: ## 启动所有服务
	@echo "$(BLUE)启动所有服务...$(NC)"
	@$(COMPOSE) up -d
	@echo "$(GREEN)✓ 完成$(NC)"

down: ## 停止所有服务
	@echo "$(BLUE)停止所有服务...$(NC)"
	@$(COMPOSE) down
	@echo "$(GREEN)✓ 完成$(NC)"

restart: ## 重启所有服务
	@echo "$(BLUE)重启所有服务...$(NC)"
	@$(COMPOSE) restart
	@echo "$(GREEN)✓ 完成$(NC)"

logs: ## 查看所有日志
	@$(COMPOSE) logs -f

status: ## 查看所有服务状态
	@echo "$(BLUE)服务状态:$(NC)"
	@$(COMPOSE) ps

# ==================== 特定服务操作 ====================

api-build: ## 构建 API 镜像
	@echo "$(BLUE)构建 API...$(NC)"
	@$(COMPOSE) build api
	@echo "$(GREEN)✓ 完成$(NC)"

api-up: ## 启动 API
	@echo "$(BLUE)启动 API...$(NC)"
	@$(COMPOSE) up -d api
	@echo "$(GREEN)✓ 完成$(NC)"

api-down: ## 停止 API
	@echo "$(BLUE)停止 API...$(NC)"
	@$(COMPOSE) stop api
	@echo "$(GREEN)✓ 完成$(NC)"

api-restart: ## 重启 API
	@echo "$(BLUE)重启 API...$(NC)"
	@$(COMPOSE) restart api
	@echo "$(GREEN)✓ 完成$(NC)"

api-logs: ## 查看 API 日志
	@$(COMPOSE) logs -f api

api-status: ## 查看 API 状态
	@$(COMPOSE) ps api

es-build: ## 构建 Elasticsearch 镜像
	@echo "$(BLUE)构建 Elasticsearch...$(NC)"
	@$(COMPOSE) -f services/elasticsearch/docker-compose.yml build elasticsearch
	@echo "$(GREEN)✓ 完成$(NC)"

es-up: ## 启动 Elasticsearch
	@echo "$(BLUE)启动 Elasticsearch...$(NC)"
	@$(COMPOSE) -f services/elasticsearch/docker-compose.yml up -d elasticsearch
	@echo "$(GREEN)✓ 完成$(NC)"

es-down: ## 停止 Elasticsearch
	@echo "$(BLUE)停止 Elasticsearch...$(NC)"
	@$(COMPOSE) -f services/elasticsearch/docker-compose.yml down
	@echo "$(GREEN)✓ 完成$(NC)"

es-restart: ## 重启 Elasticsearch
	@echo "$(BLUE)重启 Elasticsearch...$(NC)"
	@$(COMPOSE) -f services/elasticsearch/docker-compose.yml restart elasticsearch
	@echo "$(GREEN)✓ 完成$(NC)"

es-logs: ## 查看 Elasticsearch 日志
	@$(COMPOSE) -f services/elasticsearch/docker-compose.yml logs -f elasticsearch

es-status: ## 查看 Elasticsearch 状态
	@$(COMPOSE) -f services/elasticsearch/docker-compose.yml ps

postgres-build: ## 构建 PostgreSQL 镜像
	@echo "$(BLUE)构建 PostgreSQL...$(NC)"
	@$(COMPOSE) -f services/postgres/docker-compose.yaml build
	@echo "$(GREEN)✓ 完成$(NC)"

postgres-up: ## 启动 PostgreSQL
	@echo "$(BLUE)启动 PostgreSQL...$(NC)"
	@$(COMPOSE) -f services/postgres/docker-compose.yaml up -d
	@echo "$(GREEN)✓ 完成$(NC)"

postgres-down: ## 停止 PostgreSQL
	@echo "$(BLUE)停止 PostgreSQL...$(NC)"
	@$(COMPOSE) -f services/postgres/docker-compose.yaml down
	@echo "$(GREEN)✓ 完成$(NC)"

postgres-restart: ## 重启 PostgreSQL
	@echo "$(BLUE)重启 PostgreSQL...$(NC)"
	@$(COMPOSE) -f services/postgres/docker-compose.yaml restart
	@echo "$(GREEN)✓ 完成$(NC)"

postgres-logs: ## 查看 PostgreSQL 日志
	@$(COMPOSE) -f services/postgres/docker-compose.yaml logs -f

postgres-status: ## 查看 PostgreSQL 状态
	@$(COMPOSE) -f services/postgres/docker-compose.yaml ps
