.PHONY: help setup clean test

# 默认显示帮助
.DEFAULT_GOAL := help

# 服务定义
SERVICES := api es postgres
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
	@echo "  make clean              清理临时文件"
	@echo "  make test               运行测试"
	@echo ""
	@echo "$(GREEN)服务管理 (格式: make <service> <action>):$(NC)"
	@echo "  $(YELLOW)服务列表:$(NC) api, es, postgres, all"
	@echo "  $(YELLOW)操作:$(NC) up, down, restart, logs, status"
	@echo ""
	@echo "$(GREEN)示例:$(NC)"
	@echo "  make api up             启动 API 服务"
	@echo "  make es down            停止 Elasticsearch"
	@echo "  make all up             启动所有服务"
	@echo "  make api logs           查看 API 日志"
	@echo "  make es status          查看 ES 状态"
	@echo ""

# ==================== 基础命令 ====================

setup: ## 初始化环境
	@echo "$(BLUE)初始化环境...$(NC)"
	@cp -n .env.example .env || true
	@echo "$(YELLOW)请编辑 .env 文件配置 API Keys$(NC)"
	@pip install -r requirements.txt
	@[ -f app/requirements.txt ] && pip install -r app/requirements.txt || true
	@echo "$(GREEN)✓ 完成$(NC)"

clean: ## 清理临时文件
	@echo "$(BLUE)清理临时文件...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@rm -rf .pytest_cache htmlcov .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ 完成$(NC)"

test: ## 运行测试
	@echo "$(BLUE)运行测试...$(NC)"
	@pytest tests/ -v
	@echo "$(GREEN)✓ 完成$(NC)"

# ==================== 服务管理 ====================

# API 服务
api: ## API 服务管理 (up/down/restart/logs/status)
	@$(MAKE) -s _service_action SERVICE=api COMPOSE_FILE="" ACTION=$(filter-out api,$(MAKECMDGOALS))

# Elasticsearch
es: ## Elasticsearch 服务管理 (up/down/restart/logs/status)
	@$(MAKE) -s _service_action SERVICE=elasticsearch COMPOSE_FILE="-f services/elasticsearch/docker-compose.yml" ACTION=$(filter-out es,$(MAKECMDGOALS))

# PostgreSQL
postgres: ## PostgreSQL 服务管理 (up/down/restart/logs/status)
	@$(MAKE) -s _service_action SERVICE=postgres COMPOSE_FILE="-f services/postgresql/docker-compose.yaml" ACTION=$(filter-out postgres,$(MAKECMDGOALS))

# 所有服务
all: ## 所有服务管理 (up/down/restart/logs/status)
	@$(MAKE) -s _service_action SERVICE="" COMPOSE_FILE="-f docker-compose.yml" ACTION=$(filter-out all,$(MAKECMDGOALS))

# ==================== 内部函数 ====================

_service_action:
	@case "$(ACTION)" in \
		up) \
			echo "$(BLUE)启动 $(SERVICE) ...$(NC)"; \
			$(COMPOSE) $(COMPOSE_FILE) up -d $(SERVICE); \
			echo "$(GREEN)✓ $(SERVICE) 已启动$(NC)"; \
			;; \
		down) \
			echo "$(BLUE)停止 $(SERVICE) ...$(NC)"; \
			$(COMPOSE) $(COMPOSE_FILE) down $(SERVICE); \
			echo "$(GREEN)✓ $(SERVICE) 已停止$(NC)"; \
			;; \
		restart) \
			echo "$(BLUE)重启 $(SERVICE) ...$(NC)"; \
			$(COMPOSE) $(COMPOSE_FILE) restart $(SERVICE); \
			echo "$(GREEN)✓ $(SERVICE) 已重启$(NC)"; \
			;; \
		logs) \
			$(COMPOSE) $(COMPOSE_FILE) logs -f $(SERVICE); \
			;; \
		status) \
			echo "$(BLUE)服务状态:$(NC)"; \
			$(COMPOSE) $(COMPOSE_FILE) ps $(SERVICE); \
			;; \
		*) \
			echo "$(YELLOW)用法: make <service> <action>$(NC)"; \
			echo "服务: api, es, postgres, all"; \
			echo "操作: up, down, restart, logs, status"; \
			;; \
	esac

# 捕获参数，避免 make 报错
up down restart logs status:
	@:

%:
	@:
