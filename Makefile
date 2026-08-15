# Makefile для MAX-бота. Пакетный менеджер — uv, оркестрация — docker compose.
# Требует: uv, docker (с плагином compose).

.DEFAULT_GOAL := help

COMPOSE_LOCAL := docker compose -f docker/docker-compose.local.yml
COMPOSE_PROD  := docker compose -f docker/docker-compose.prod.yml
IMAGE         := max-id-bot

.PHONY: help install lock run lint format test check \
        build-local up-local watch down-local logs shell \
        build-prod up-prod down-prod logs-prod \
        clean

help: ## Показать это сообщение
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- Разработка (без Docker) ------------------------------------------------

install: ## Создать/обновить venv из lock-файла (uv sync)
	uv sync

lock: ## Пересобрать uv.lock
	uv lock

run: ## Запустить бота локально без Docker
	uv run python -m bot

lint: ## Проверка линтером (ruff)
	uv run ruff check .

format: ## Автоформатирование (ruff format)
	uv run ruff format .

test: ## Прогнать тесты
	uv run pytest -q

check: lint test ## Линт + тесты (то, что гоняем перед коммитом)

# --- Docker: локальный стек --------------------------------------------------

build-local: ## Собрать Docker-образ (локальный tag)
	$(COMPOSE_LOCAL) build

up-local: ## Поднять локальный стек (detached)
	$(COMPOSE_LOCAL) up -d --build

watch: ## Локальный стек с авто-перезапуском при изменении кода
	$(COMPOSE_LOCAL) watch

down-local: ## Остановить локальный стек
	$(COMPOSE_LOCAL) down

logs: ## Логи локального стека (follow)
	$(COMPOSE_LOCAL) logs -f bot

shell: ## Shell внутри локального контейнера
	$(COMPOSE_LOCAL) exec bot /bin/bash

# --- Docker: прод-стек ---------------------------------------------------------

build-prod: ## Собрать прод-образ
	$(COMPOSE_PROD) build

up-prod: ## Поднять прод-стек (detached)
	$(COMPOSE_PROD) up -d --build

down-prod: ## Остановить прод-стек
	$(COMPOSE_PROD) down

logs-prod: ## Логи прод-стека (follow)
	$(COMPOSE_PROD) logs -f bot

# --- Обслуживание -------------------------------------------------------------

clean: ## Убрать кэши и артефакты
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
