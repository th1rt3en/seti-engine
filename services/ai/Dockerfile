# The AI lobby service (stateless; docs/deploy-ai.md). Build from the repository root, after `python -m seti_ai.lobby_export` has filled services/ai/serve_models:
#   docker build -f services/ai/Dockerfile -t seti-ai .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/engine/pyproject.toml services/engine/README.md* ./engine/
COPY services/engine/src ./engine/src
COPY services/ai/pyproject.toml ./ai/
COPY services/ai/src ./ai/src
RUN pip install --no-cache-dir "pydantic>=2.8" "fastapi>=0.115" "uvicorn>=0.30" "cryptography>=43" "numpy>=2.0" \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --no-deps ./engine ./ai
COPY services/ai/serve_models /models
ENV PORT=8080 SETI_MODELS=/models
# One process: the network is loaded once and the search uses the cores of the instance.
CMD ["sh", "-c", "uvicorn seti_ai.lobby_server:app --host 0.0.0.0 --port ${PORT}"]
