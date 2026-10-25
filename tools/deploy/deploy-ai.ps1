# Deploy the AI lobby service to Cloud Run from this machine (docs/deploy-ai.md). The weights are not in git, so the image is built from a staged folder.
#   powershell -File tools/deploy/deploy-ai.ps1 [-Models models_alpha,models_v3] [-Cpu 1] [-Memory 1Gi]
# Run `python -m seti_ai.publish --approve <version> --live <version>` first (it marks the version approved where the export reads it).
param([string[]]$Models = @("models_alpha", "models_v3"), [string]$Region = "us-central1", [int]$Cpu = 1, [string]$Memory = "1Gi" # the owner sets the size of the service: never raise these without their permission)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ai = Join-Path $repo "services\ai"
$stage = Join-Path ([IO.Path]::GetTempPath()) "seti-ai-stage"
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory $stage, "$stage\engine", "$stage\ai" | Out-Null

Push-Location $ai
foreach ($m in ($Models -split ",")) { python -m uv run python -m seti_ai.lobby_export --models $m --out serve_models }
Pop-Location

Copy-Item "$repo\services\engine\pyproject.toml" "$stage\engine\"
if (Test-Path "$repo\services\engine\README.md") { Copy-Item "$repo\services\engine\README.md" "$stage\engine\" }
Copy-Item -Recurse "$repo\services\engine\src" "$stage\engine\src"
Copy-Item "$ai\pyproject.toml" "$stage\ai\"
Copy-Item -Recurse "$ai\src" "$stage\ai\src"
Copy-Item -Recurse "$ai\serve_models" "$stage\serve_models"
Get-ChildItem -Recurse -Directory -Filter __pycache__ $stage | Remove-Item -Recurse -Force

@'
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY engine ./engine
COPY ai ./ai
RUN pip install --no-cache-dir "pydantic>=2.8" "fastapi>=0.115" "uvicorn>=0.30" "cryptography>=43" "numpy>=2.0" \
 && pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --no-deps ./engine ./ai
COPY serve_models /models
ENV PORT=8080 SETI_MODELS=/models
CMD ["sh", "-c", "uvicorn seti_ai.lobby_server:app --host 0.0.0.0 --port ${PORT}"]
'@ | Set-Content "$stage\Dockerfile" -Encoding ascii

# the trusted public keys are the engine service's (the Worker signs both with the same key)
$keys = (gcloud run services describe seti-engine --region $Region --format=json | ConvertFrom-Json).spec.template.spec.containers[0].env |
  Where-Object name -eq ENGINE_TRUSTED_KEYS | Select-Object -ExpandProperty value
$envFile = Join-Path ([IO.Path]::GetTempPath()) "seti-ai-env.yaml"
("ENGINE_TRUSTED_KEYS: " + ($keys | ConvertTo-Json)) | Set-Content $envFile -Encoding utf8

Push-Location $stage
gcloud run deploy seti-ai --source . --region $Region --cpu $Cpu --memory $Memory --concurrency 4 --min-instances 0 --max-instances 1 --timeout 300 --env-vars-file $envFile --quiet
Pop-Location
Remove-Item $envFile
