#FROM ghcr.io/astral-sh/uv:python3.14-alpine3.23
#LABEL authors="Roman Sokolov"
## Працюємо в папці /app
#WORKDIR /app
#
## Оптимізація uv
#ENV UV_COMPILE_BYTECODE=1
#ENV UV_LINK_MODE=copy
#ENV UV_NO_DEV=1
#
#COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
## Копіюємо код
#COPY . /app
#ENV UV_NO_DEV=1
#RUN uv sync --locked
## Додаємо віртуальне оточення в PATH
#ENV PATH="/app/.venv/bin:$PATH"
FROM ghcr.io/astral-sh/uv:python3.14-alpine3.23
LABEL authors="Roman Sokolov"

# Працюємо в папці /app
WORKDIR /app

# Оптимізація uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1

# Копіюємо лише файли конфігурації залежностей (щоб кешувати шар)
COPY pyproject.toml uv.lock ./

# Встановлюємо залежності з використанням кешу uv через --mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Тепер копіюємо весь решта проєкту та код
COPY . /app

# Фінальна синхронізація проєкту (займає мінімум часу, якщо код змінився, а залежності ні)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Додаємо віртуальне оточення в PATH
ENV PATH="/app/.venv/bin:$PATH"