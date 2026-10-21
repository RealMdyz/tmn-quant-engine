FROM python:3.11-slim
WORKDIR /app
RUN apt-get update -qq && apt-get install -y -qq git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1 PORT=8080 DISABLE_PULL=1 TZ=Asia/Tehran
EXPOSE 8080
CMD ["python", "deploy/supervisor.py"]
