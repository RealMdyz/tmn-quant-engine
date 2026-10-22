# TMN Portal (سه‌سبد). Build context = repo root, so the portal reuses the engine's Wallex client and config.yaml:
#   liara deploy --app <portal-app> --liara-json portal/liara.json --dockerfile portal/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY portal/requirements.txt portal/requirements.txt
RUN pip install --no-cache-dir -r portal/requirements.txt \
    || pip install --no-cache-dir -r portal/requirements.txt -i https://package-mirror.liara.ir/repository/pypi/simple
COPY bot/__init__.py bot/wallex_client.py bot/
COPY config.yaml .
COPY data/hourly.json data/
COPY portal portal
ENV PYTHONUNBUFFERED=1 TZ=Asia/Tehran PORTAL_DATA_DIR=/app/var
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "portal.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
