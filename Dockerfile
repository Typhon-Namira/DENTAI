FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend-test/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend-test ./
ENV VITE_DENTAI_API_BASE_URL=""
RUN npm run build

FROM node:20-bookworm-slim AS whatsapp-deps
WORKDIR /whatsapp_service
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY whatsapp_service/package.json ./
RUN npm install --omit=dev --no-audit --no-fund

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.12.3 \
    && uv export --frozen --no-dev --no-emit-project --format requirements-txt > requirements.txt \
    && pip install --no-cache-dir --require-hashes -r requirements.txt \
    && pip uninstall -y uv
COPY app ./app
COPY ai_engine ./ai_engine
COPY configs ./configs
COPY config ./config
COPY artifacts/production ./artifacts/production
COPY migrations ./migrations
COPY docs/ai ./docs/ai
COPY scripts ./scripts
COPY whatsapp_service ./whatsapp_service
COPY alembic.ini README.md ./
COPY --from=frontend-build /frontend/dist ./frontend-dist
COPY --from=whatsapp-deps /usr/local/bin/node /usr/local/bin/node
COPY --from=whatsapp-deps /whatsapp_service/node_modules ./whatsapp_service/node_modules
RUN useradd --create-home appuser \
    && mkdir -p /app/data/whatsapp_sessions \
    && chmod +x /app/scripts/start_railway.sh \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "scripts/start_railway.sh"]
