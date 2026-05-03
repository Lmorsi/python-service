FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=10000
EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "60", "app:app"]
```

---

## render.yaml (deploy automático no Render.com)

```yaml
services:
  - type: web
    name: avaliaedu-opencv
    runtime: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: OPENCV_API_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production
    healthCheckPath: /health
```
