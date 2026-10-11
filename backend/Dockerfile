FROM ghcr.io/astral-sh/uv:python3.14-alpine3.23
LABEL authors="Roman Sokolov"
# Працюємо в папці /app
WORKDIR /app

# Оптимізація uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Копіюємо код
COPY . /app
ENV UV_NO_DEV=1
RUN uv sync --locked
# Додаємо віртуальне оточення в PATH
ENV PATH="/app/.venv/bin:$PATH"
