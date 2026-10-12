# syntax=docker/dockerfile:1
# Minimal, hardened image: multi-stage, no build tools or caches at runtime, non-root user.
# Run it read-only with all capabilities dropped (see README). Secrets come from the environment
# at run time; none are baked into the image.

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin sixhats
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
WORKDIR /work
ENTRYPOINT ["sixhats"]
CMD ["--help"]
