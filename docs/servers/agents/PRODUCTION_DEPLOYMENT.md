# Production Deployment Guide - OmniParser Models

## Overview

This guide explains how to handle OmniParser model weights (~1GB) in production deployments.

## ⚠️ Important: DO NOT Commit Weights to Git

**Never include model weights in your Git repository:**
- ❌ Don't commit the `weights/` directory
- ❌ Don't remove from `.gitignore`
- ✅ Weights are already gitignored

**Why?**
- 1GB files bloat repository size
- Git isn't designed for large binary files
- Slows down clones and increases storage costs
- Use Git LFS or external storage instead

## Deployment Options

### Option 1: Docker Build-Time Download (Recommended)

Download models during Docker image build and cache them in the image layer.

**Dockerfile Example:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv sync --frozen

# Download model weights (cached in Docker layer)
COPY scripts/setup_omniparser.sh scripts/
RUN chmod +x scripts/setup_omniparser.sh && \
    ./scripts/setup_omniparser.sh /app/weights

# Copy application code
COPY . .

# Set environment variable for weights location
ENV OMNIPARSER_WEIGHTS_DIR=/app/weights

# Start server
CMD ["uv", "run", "langgraph", "dev", "--host", "0.0.0.0"]
```

**Benefits:**
- ✅ Models downloaded once during build
- ✅ Cached in Docker layer (fast rebuilds)
- ✅ No runtime download delays
- ✅ Works offline after build

**Build and Run:**
```bash
docker build -t anna-agents .
docker run -p 2024:2024 -e OPENAI_API_KEY=sk-... anna-agents
```

---

### Option 2: Persistent Volume (for Kubernetes/Cloud)

Store weights in a persistent volume shared across pods/containers.

**Kubernetes Example:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: omniparser-weights
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 2Gi

---
apiVersion: batch/v1
kind: Job
metadata:
  name: download-weights
spec:
  template:
    spec:
      containers:
      - name: downloader
        image: anna-agents:latest
        command: ["/bin/bash", "-c"]
        args:
          - "./scripts/setup_omniparser.sh /weights"
        volumeMounts:
        - name: weights
          mountPath: /weights
      volumes:
      - name: weights
        persistentVolumeClaim:
          claimName: omniparser-weights
      restartPolicy: OnFailure

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anna-agents
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: anna-agents:latest
        env:
        - name: OMNIPARSER_WEIGHTS_DIR
          value: /weights
        volumeMounts:
        - name: weights
          mountPath: /weights
          readOnly: true
      volumes:
      - name: weights
        persistentVolumeClaim:
          claimName: omniparser-weights
```

**Benefits:**
- ✅ Single download shared across pods
- ✅ Fast pod startup (no download)
- ✅ Scales to many replicas
- ✅ Persistent across deployments

**Steps:**
1. Create persistent volume
2. Run one-time download job
3. Mount volume (read-only) in all pods

---

### Option 3: Cloud Storage (S3/GCS) + Init Container

Upload weights to cloud storage, download on container startup.

**Setup:**

1. **Upload to S3/GCS (one-time):**
```bash
# Download locally
./scripts/setup_omniparser.sh ./weights

# Upload to S3
aws s3 sync ./weights s3://your-bucket/omniparser-weights/

# Or GCS
gsutil -m rsync -r ./weights gs://your-bucket/omniparser-weights/
```

2. **Kubernetes with Init Container:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anna-agents
spec:
  template:
    spec:
      initContainers:
      - name: download-weights
        image: amazon/aws-cli
        command: ["/bin/bash", "-c"]
        args:
          - "aws s3 sync s3://your-bucket/omniparser-weights/ /weights"
        volumeMounts:
        - name: weights
          mountPath: /weights
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-creds
              key: access-key-id
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: aws-creds
              key: secret-access-key

      containers:
      - name: agent
        image: anna-agents:latest
        env:
        - name: OMNIPARSER_WEIGHTS_DIR
          value: /weights
        volumeMounts:
        - name: weights
          mountPath: /weights

      volumes:
      - name: weights
        emptyDir: {}
```

**Benefits:**
- ✅ Centralized storage
- ✅ Easy updates (upload new version)
- ✅ Works across cloud providers
- ❌ Slower startup (download time)

---

### Option 4: Pre-baked AMI/VM Image

Bake weights into VM/AMI image for cloud deployments.

**AWS EC2 Example:**

```bash
# On source instance
./scripts/setup_omniparser.sh /opt/anna/weights

# Create AMI from instance
aws ec2 create-image --instance-id i-xxxxx --name anna-agents-v1

# Launch new instances from AMI
aws ec2 run-instances --image-id ami-xxxxx
```

**Benefits:**
- ✅ Instant startup (pre-installed)
- ✅ No runtime downloads
- ✅ Good for auto-scaling
- ❌ Larger AMI size

---

## Comparison Matrix

| Option | Startup Speed | Storage Cost | Complexity | Best For |
|--------|---------------|--------------|------------|----------|
| Docker Build | ⚡ Fast | Low | Low | Single container, small scale |
| Persistent Volume | ⚡⚡ Very Fast | Medium | Medium | Kubernetes, multi-pod |
| Cloud Storage | 🐢 Slow | Medium | Medium | Multi-cloud, easy updates |
| Pre-baked Image | ⚡⚡ Very Fast | High | Low | VM-based, auto-scaling |

## Recommended: Docker Build-Time Download

For most production deployments, **Docker build-time download** is recommended:

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy and install dependencies
COPY pyproject.toml .
RUN uv sync --frozen

# Download models (cached layer)
COPY scripts/setup_omniparser.sh scripts/
RUN chmod +x scripts/setup_omniparser.sh && \
    ./scripts/setup_omniparser.sh /app/weights

# Copy application
COPY . .

ENV OMNIPARSER_WEIGHTS_DIR=/app/weights
CMD ["uv", "run", "langgraph", "dev", "--host", "0.0.0.0"]
```

**CI/CD Pipeline (.github/workflows/deploy.yml):**
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          cd servers/agents
          docker build -t anna-agents:${{ github.sha }} .

      - name: Push to registry
        run: |
          docker tag anna-agents:${{ github.sha }} your-registry/anna-agents:latest
          docker push your-registry/anna-agents:latest

      - name: Deploy to production
        run: |
          kubectl set image deployment/anna-agents \
            agent=your-registry/anna-agents:latest
```

## Performance Considerations

**Model Loading Time:**
- First request: ~2-3 seconds (model loads into RAM)
- Subsequent requests: ~600ms per screenshot
- Models stay in memory (~1GB RAM usage)

**Optimization:**
- Use GPU for 5-10x faster inference
- Add liveness/readiness probes with delays
- Warm up models on startup (optional)

**Startup Warmup Script:**
```python
# warmup.py
from agents.browser_agent.services.element_detector import ElementDetector

# Load models on startup
detector = ElementDetector.get_instance()
detector._load_models()
print("Models loaded and ready!")
```

**Add to CMD:**
```dockerfile
CMD uv run python warmup.py && uv run langgraph dev --host 0.0.0.0
```

## Monitoring

**Health Check Endpoint:**
```python
# Add to your FastAPI/LangGraph server
@app.get("/health")
def health_check():
    try:
        from agents.browser_agent.services.element_detector import ElementDetector
        detector = ElementDetector.get_instance()
        # Check if weights exist
        weights_exist = detector._weights_dir.exists()
        return {"status": "healthy", "weights_loaded": weights_exist}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

**Kubernetes Probes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 2024
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 2024
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Troubleshooting

**Models not found in production:**
```bash
# Check if weights directory exists
ls -lh /app/weights/

# Verify environment variable
echo $OMNIPARSER_WEIGHTS_DIR

# Test model loading
uv run python -c "from agents.browser_agent.services.element_detector import ElementDetector; ElementDetector.get_instance()._load_models()"
```

**Out of memory:**
- Increase container memory: `resources.limits.memory: 2Gi`
- Use GPU nodes: `nodeSelector: gpu=true`
- Reduce replica count if memory constrained

**Slow downloads:**
- Use closer HuggingFace mirror
- Cache weights in CI/CD build cache
- Use pre-downloaded weights in persistent volume

## Summary

**Development:**
```bash
./scripts/setup_omniparser.sh  # One-time download
langgraph dev
```

**Production (Recommended):**
```dockerfile
# Dockerfile with build-time download
RUN ./scripts/setup_omniparser.sh /app/weights
```

**Alternative for Large Scale:**
- Use persistent volume (Kubernetes)
- Or cloud storage (S3/GCS)

**Never:**
- ❌ Commit weights to Git
- ❌ Download on every container start (slow)
- ❌ Store in ephemeral storage only

---

**Need Help?**
- See `ELEMENT_DETECTION_SETUP.md` for local development
- Check Docker logs: `docker logs <container-id>`
- Test locally first: `docker run -it anna-agents bash`
