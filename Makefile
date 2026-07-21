# Makefile для MAX-бота. Пакетный менеджер — uv, оркестрация — docker compose.
# Требует: uv, docker (с плагином compose).

# ── Переменные ───────────────────────────────────────────────────────────────
COMPOSE_LOCAL := docker compose -f docker/docker-compose.local.yml
COMPOSE_PROD  := docker compose -f docker/docker-compose.prod.yml
IMAGE         := max-id-bot

# Красивый help по умолчанию
.DEFAULT_GOAL := help

# ── Разработка (без Docker) ──────────────────────────────────────────────────
.PHONY: install
install: ## Создать/обновить venv из lock-файла (uv sync)
	uv sync

.PHONY: lock
lock: ## Пересобрать uv.lock
	uv lock

.PHONY: run
run: ## Запустить бота локально без Docker
	uv run python -m bot

.PHONY: lint
lint: ## Проверка линтером (ruff)
	uv run ruff check .

.PHONY: fmt
fmt: ## Автоформатирование (ruff format)
	uv run ruff format .

.PHONY: test
test: ## Прогнать тесты
	uv run pytest -q

.PHONY: check
check: lint test ## Линт + тесты (то, что гоняем перед коммитом)

# ── Docker: локальный стек ───────────────────────────────────────────────────
.PHONY: build
build: ## Собрать Docker-образ (локальный tag)
	$(COMPOSE_LOCAL) build

.PHONY: up
up: ## Поднять локальный стек (detached)
	$(COMPOSE_LOCAL) up -d --build

.PHONY: watch
watch: ## Локальный стек с авто-перезапуском при изменении кода
	$(COMPOSE_LOCAL) watch

.PHONY: down
down: ## Остановить локальный стек
	$(COMPOSE_LOCAL) down

.PHONY: logs
logs: ## Логи локального стека (follow)
	$(COMPOSE_LOCAL) logs -f bot

.PHONY: shell
shell: ## Shell внутри локального контейнера
	$(COMPOSE_LOCAL) exec bot /bin/bash

# ── Docker: прод-стек ────────────────────────────────────────────────────────
.PHONY: prod-build
prod-build: ## Собрать прод-образ
	$(COMPOSE_PROD) build

.PHONY: prod-up
prod-up: ## Поднять прод-стек (detached)
	$(COMPOSE_PROD) up -d --build

.PHONY: prod-down
prod-down: ## Остановить прод-стек
	$(COMPOSE_PROD) down

.PHONY: prod-logs
prod-logs: ## Логи прод-стека (follow)
	$(COMPOSE_PROD) logs -f bot

# ── Обслуживание ─────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Убрать кэши и артефакты
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: help
help: ## Показать это сообщение
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
