# Production Deployment & Operational Considerations

## 1. Production Architecture Recommendations

For production deployments, NEXUS should run as an asynchronous microservice containerized with Docker or behind a reverse proxy (such as Nginx, Traefik, or AWS ALB / Cloud Run).

### Containerization (Dockerfile Concept)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 4000

USER 1000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000", "--workers", "4"]
```

---

## 2. Multi-Worker Concurrency

In production, run Uvicorn with multiple workers or through Gunicorn with the `UvicornWorker` class:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --workers 4
```

Or using Gunicorn:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:4000
```

---

## 3. Health Checks & Monitoring

NEXUS includes an enterprise-ready health check endpoint:

- **Endpoint**: `GET /health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "production",
    "configured_platforms_count": 5,
    "total_platforms_count": 5
  }
  ```
- **Kubernetes Liveness / Readiness Probe**:
  ```yaml
  livenessProbe:
    httpGet:
      path: /health
      port: 4000
    initialDelaySeconds: 5
    periodSeconds: 10
  readinessProbe:
    httpGet:
      path: /health
      port: 4000
    initialDelaySeconds: 2
    periodSeconds: 5
  ```

---

## 4. Rate Limiting & Edge Protection

- Place an API gateway (e.g., Kong, Cloudflare, or AWS API Gateway) in front of NEXUS to enforce client-side rate limiting and DDoS protection.
- For high-volume multi-platform workloads, consider introducing a background message queue (e.g., Celery, Redis Streams, or RabbitMQ) if tasks need to be queued persistently rather than synchronously aggregated.
