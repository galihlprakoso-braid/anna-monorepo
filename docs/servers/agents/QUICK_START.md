# Quick Start - UI Element Detection

## Fixed Issues

### 1. ✅ huggingface-cli Command Not Found

**Fixed:** Updated `scripts/setup_omniparser.sh` to use `uv run huggingface-cli` instead of just `huggingface-cli`.

### 2. ✅ Test Organization

**Fixed:** Moved tests to `tests/browser_agent/` for better organization:
- `tests/browser_agent/test_element_detector.py` - Unit tests
- `tests/browser_agent/test_element_detection_integration.py` - Integration tests
- `tests/browser_agent/images/ss-1.png` - Test screenshot

### 3. ✅ Production Deployment

**Created:** `PRODUCTION_DEPLOYMENT.md` with comprehensive deployment strategies.

## Quick Setup

### Development

```bash
cd servers/agents

# Install dependencies
uv sync

# Download OmniParser models (~1GB)
./scripts/setup_omniparser.sh

# Start server
langgraph dev
```

### Run Tests

```bash
# All browser agent tests
pytest tests/browser_agent/ -v

# Just integration tests
pytest tests/browser_agent/test_element_detection_integration.py -v -s

# Just unit tests
pytest tests/browser_agent/test_element_detector.py -v
```

## Production Deployment

**Recommended: Docker Build-Time Download**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install dependencies
COPY pyproject.toml .
RUN uv sync --frozen

# Download models (cached in Docker layer)
COPY scripts/setup_omniparser.sh scripts/
RUN chmod +x scripts/setup_omniparser.sh && \
    ./scripts/setup_omniparser.sh /app/weights

# Copy application
COPY . .

ENV OMNIPARSER_WEIGHTS_DIR=/app/weights
CMD ["uv", "run", "langgraph", "dev", "--host", "0.0.0.0"]
```

**Build and run:**
```bash
docker build -t anna-agents .
docker run -p 2024:2024 -e OPENAI_API_KEY=sk-... anna-agents
```

## DO NOT Include Models in Git

- ✅ Models are gitignored in `weights/`
- ❌ Never commit 1GB model files to Git
- ✅ Download during Docker build or use persistent volumes

## Deployment Options

See `PRODUCTION_DEPLOYMENT.md` for complete guide:

1. **Docker Build-Time** (Recommended) - Bake into image
2. **Persistent Volume** (Kubernetes) - Shared storage
3. **Cloud Storage** (S3/GCS) - Download on startup
4. **Pre-baked AMI** (EC2) - VM image with models

## Documentation

- `PRODUCTION_DEPLOYMENT.md` - Complete production deployment guide
- `CLAUDE.md` - Updated with UI element detection section
- `tests/browser_agent/` - Test files and examples

## Need Help?

**Script not working:**
```bash
# Make sure dependencies are installed
uv sync

# Run with verbose output
bash -x ./scripts/setup_omniparser.sh
```

**Tests failing:**
```bash
# Check if models downloaded
ls -lh weights/

# Run with verbose output
pytest tests/browser_agent/ -vv -s
```

**Production issues:**
See troubleshooting section in `PRODUCTION_DEPLOYMENT.md`
