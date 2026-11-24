FROM python:3.12-slim AS base
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.13.9
COPY pyproject.toml uv.lock ./

FROM base AS checks
RUN uv sync --locked --no-install-project
COPY ruletrace ruletrace
COPY sql sql
COPY corpus corpus
COPY tests tests
CMD ["sh", "-c", ".venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest -q"]

FROM base AS runtime
RUN uv sync --locked --no-dev --no-install-project
COPY ruletrace ruletrace
COPY sql sql
COPY corpus corpus
COPY evals evals
USER 65534:65534
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["uvicorn", "ruletrace.api:app", "--host", "0.0.0.0", "--port", "8000", "--limit-concurrency", "8", "--no-access-log"]
