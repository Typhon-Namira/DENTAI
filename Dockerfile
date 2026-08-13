FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.12.3 \
    && uv export --frozen --no-dev --no-emit-project --format requirements-txt > requirements.txt \
    && pip install --no-cache-dir --require-hashes -r requirements.txt \
    && pip uninstall -y uv
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini README.md ./
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
