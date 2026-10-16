# syntax=docker/dockerfile:1
# The web API (FastAPI + uvicorn) for the browser interface. Same hardening as the CLI image:
# multi-stage, no build tools or caches at runtime, non-root user, no secrets baked in.
# Build from the repository root:  docker build -f docker/api.Dockerfile -t sixhats-api .

FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable --extra web

FROM python:3.13-slim
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin sixhats
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
WORKDIR /work
EXPOSE 8000
# Inside a container the API must listen on all interfaces so the web container can reach it. It has no
# login, so never publish this port to a network you do not trust (compose.yaml does not publish it).
ENTRYPOINT ["sixhats"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
