# The SETI engine service (stateless). Build from services/engine: docker build -t seti-engine services/engine
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md* ./
COPY src ./src
RUN pip install --no-cache-dir "pydantic>=2.8" "fastapi>=0.115" "uvicorn>=0.30" "cryptography>=43" && pip install --no-cache-dir --no-deps .
ENV PORT=8080
# One process per CPU: a move is CPU work, and one Python process uses one core. Set WEB_CONCURRENCY to the number of CPUs of the Cloud Run instance.
ENV WEB_CONCURRENCY=2
CMD ["sh", "-c", "uvicorn seti_engine.service:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY}"]
