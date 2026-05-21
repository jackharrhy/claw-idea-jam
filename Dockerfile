# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first for better layer caching
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source
COPY src ./src
COPY prompts ./prompts
COPY README.md ./

# Install the project itself
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL="sqlite:////data/idea_jam.db"

# Mount point for the DB
VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "idea_jam.main:app", "--host", "0.0.0.0", "--port", "8000"]
