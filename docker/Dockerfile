# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────────────────────
# Multi-stage сборка MAX-бота с помощью uv.
# Стратегия (по официальной документации Astral):
#   1) builder — ставим зависимости отдельным слоем (кэшируется), затем проект
#      в non-editable режиме, чтобы в рантайм ушёл только .venv без исходников
#      в editable-ссылках;
#   2) runtime — чистый slim-образ, без uv и без build-инструментов, копируем
#      только виртуальное окружение и исходный код, запускаемся под non-root.
# ─────────────────────────────────────────────────────────────────────────────

ARG PYTHON_VERSION=3.12
# uv-версию пиним ради воспроизводимости сборок
ARG UV_VERSION=0.11

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-trixie AS builder

# uv-бинарник копируем из официального distroless-образа (быстрее установки)
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

# Используем системный Python из базового образа в обеих стадиях
ENV UV_PYTHON_DOWNLOADS=0 \
    # копирование вместо hardlink — cache-mount на другой ФС
    UV_LINK_MODE=copy \
    # компиляция в байткод ускоряет старт в проде
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Слой 1: только зависимости (меняются редко → отличный кэш).
# Bind-mount на lock и pyproject, чтобы не инвалидировать слой копированием.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --no-dev

# Слой 2: исходники проекта + установка самого проекта (меняется часто).
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-trixie AS runtime

# non-root пользователь
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

# Копируем готовое окружение и код из builder (без uv и без кэшей)
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

# venv в начало PATH — активация не нужна
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

USER app

# Лёгкий healthcheck: процесс жив и модуль импортируется
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import bot" || exit 1

# Бот работает в режиме polling — long-running процесс
CMD ["python", "-m", "bot"]
