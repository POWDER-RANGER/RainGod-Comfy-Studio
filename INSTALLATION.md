# 📦 Installation Guide

> **Complete setup instructions for RAINGOD-ComfyUI-Integration**

## 🎯 Prerequisites

### Required Software

- **Python**: 3.10 or higher
- **Git**: Latest version
- **pip**: Latest version (comes with Python)

### Recommended Hardware

**Minimum**:
- CPU: 4 cores
- RAM: 16GB
- Storage: 20GB free space

**Recommended**:
- CPU: 8+ cores
- RAM: 32GB+
- GPU: NVIDIA RTX 3060 (12GB VRAM) or better
- Storage: 50GB+ SSD

**Optimal**:
- GPU: NVIDIA RTX 4090 (24GB VRAM)
- RAM: 64GB+
- Storage: 100GB+ NVMe SSD

---

## 🚀 Quick Install (Recommended)

### Option 1: One-Command Quickstart

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/POWDER-RANGER/RAINGOD-ComfyUI-Integration.git
cd RAINGOD-ComfyUI-Integration

# Run quickstart script
chmod +x scripts/rain_quickstart.sh
./scripts/rain_quickstart.sh
```

This script will:
1. ✅ Check system requirements
2. ✅ Create virtual environment
3. ✅ Install dependencies
4. ✅ Set up ComfyUI (if not installed)
5. ✅ Create directory structure
6. ✅ Start all services
7. ✅ Run health checks

**Expected Time**: 5-15 minutes (depending on internet speed)

---

## 📋 Manual Installation

If you prefer manual control or the quickstart fails:

### Step 1: Clone Repository

```bash
git clone https://github.com/POWDER-RANGER/RAINGOD-ComfyUI-Integration.git
cd RAINGOD-ComfyUI-Integration
```

### Step 2: Set Up Virtual Environment

**Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**:
```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install backend requirements
pip install -r backend/requirements.txt
```

### Step 4: Install PyTorch (GPU Support)

Choose based on your GPU:

**NVIDIA GPU (CUDA 11.8)**:
```bash
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```

**NVIDIA GPU (CUDA 12.1)**:
```bash
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121
```

**CPU Only** (slower):
```bash
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
```

### Step 5: Install ComfyUI

```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI dependencies
cd ComfyUI
pip install -r requirements.txt
cd ..
```

### Step 6: Create Directory Structure

```bash
mkdir -p outputs temp logs cache workflows/exports
```

### Step 7: Configure Environment

Create `.env` file (optional):

```bash
# .env
COMFYUI_API_ENDPOINT=http://127.0.0.1:8188
COMFYUI_DEFAULT_CHECKPOINT=sdxl
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

---

## 🎨 ComfyUI Models Setup

### Download Checkpoints

ComfyUI requires diffusion models. Download to `ComfyUI/models/checkpoints/`:

**Stable Diffusion XL (Recommended)**:
```bash
# Download SDXL Base
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors \
  -P ComfyUI/models/checkpoints/
```

**Stable Diffusion 1.5** (Alternative):
```bash
# Download SD 1.5
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors \
  -P ComfyUI/models/checkpoints/
```

### Download LoRA Models (Optional)

LoRAs add style customization. Place in `ComfyUI/models/loras/`:

```bash
# Example: Download style LoRAs
mkdir -p ComfyUI/models/loras
cd ComfyUI/models/loras

# Add your LoRA files here
# Update COMFYUI_LORA_MAPPINGS in rain_backend_config.py
```

### Download VAE (Optional)

Better image quality with custom VAE:

```bash
wget https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors \
  -P ComfyUI/models/vae/
```

---

## 🚀 Starting Services

### Option 1: Use Start Scripts

**Start everything**:
```bash
./scripts/start_all.sh
```

**Start individually**:
```bash
# ComfyUI only
./scripts/start_comfyui.sh

# Backend only
./scripts/start_backend.sh
```

### Option 2: Manual Start

**Terminal 1 - ComfyUI**:
```bash
cd ComfyUI
python main.py --port 8188
```

**Terminal 2 - Backend**:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
cd backend
uvicorn rain_backend:app --host 0.0.0.0 --port 8000 --reload
```

---

## ✅ Verification

### Check Service Status

**Backend Health**:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "comfyui_healthy": true,
  "comfyui_latency_ms": 15.3,
  "queue_pending": 0,
  "queue_running": 0
}
```

**ComfyUI**:
Open browser: `http://localhost:8188`

**API Documentation**:
Open browser: `http://localhost:8000/docs`

### Run Test Generation

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful sunset over mountains",
    "preset": "fast",
    "resolution": "thumbnail"
  }'
```

---

## 🐛 Troubleshooting

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
```bash
# Find and kill process on port 8188 (ComfyUI)
lsof -ti:8188 | xargs kill -9

# Find and kill process on port 8000 (Backend)
lsof -ti:8000 | xargs kill -9
```

Or use different ports:
```bash
# Start ComfyUI on different port
python main.py --port 8189

# Update backend config
export COMFYUI_API_ENDPOINT=http://127.0.0.1:8189
```

### ComfyUI Connection Failed

**Error**: `ComfyUI health check failed`

**Solutions**:
1. Verify ComfyUI is running: `curl http://localhost:8188`
2. Check firewall settings
3. Verify endpoint in `rain_backend_config.py`

### Out of Memory (GPU)

**Error**: `CUDA out of memory`

**Solutions**:
1. Use smaller resolution presets
2. Use "fast" sampler preset (fewer steps)
3. Reduce batch size
4. Close other GPU applications
5. Switch to CPU mode (slower)

### Missing Models

**Error**: `Checkpoint not found`

**Solutions**:
1. Download required checkpoint (see Models Setup above)
2. Update `COMFYUI_CHECKPOINT_PRESETS` in config
3. Place files in correct directories

### Python Version Mismatch

**Error**: `Python 3.10 or higher required`

**Solutions**:
```bash
# Check Python version
python --version

# Install Python 3.10+ using:
# - pyenv (Linux/Mac)
# - Official installer (Windows)
# - Homebrew (Mac): brew install python@3.10
```

### Import Errors

**Error**: `ModuleNotFoundError`

**Solutions**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate

# Reinstall requirements
pip install -r backend/requirements.txt
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file in root directory:

```bash
# ComfyUI Configuration
COMFYUI_API_ENDPOINT=http://127.0.0.1:8188
COMFYUI_DEFAULT_CHECKPOINT=sdxl
COMFYUI_LORA_DIR=ComfyUI/models/loras

# Backend Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
API_WORKERS=4

# Logging
LOG_LEVEL=INFO

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Custom Configuration

Edit `backend/rain_backend_config.py` for:
- Resolution presets
- Sampler configurations
- LoRA mappings
- Quality tiers
- Batch processing settings

---

## 📊 Performance Tuning

### For RTX 3060 (12GB)

```python
# In rain_backend_config.py
DEFAULT_PRESET = "fast_3060"
BATCH_CONFIG["max_concurrent_jobs"] = 2
```

### For RTX 4090 (24GB)

```python
# In rain_backend_config.py
DEFAULT_PRESET = "fast_4090"
BATCH_CONFIG["max_concurrent_jobs"] = 4
```

### For CPU Only

```python
# In rain_backend_config.py
DEFAULT_PRESET = "fast"
BATCH_CONFIG["max_concurrent_jobs"] = 1
COMFYUI_TIMEOUT_READ = 600  # 10 minutes
```

---

## 🐳 Docker Installation (Optional)

### Build Image

```bash
docker build -t raingod-backend .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

### Check Logs

```bash
docker-compose logs -f
```

---

## 🔄 Updating

### Update RAINGOD Backend

```bash
cd RAINGOD-ComfyUI-Integration
git pull origin main
pip install -r backend/requirements.txt --upgrade
```

### Update ComfyUI

```bash
cd ComfyUI
git pull origin master
pip install -r requirements.txt --upgrade
cd ..
```

---

## 🧪 Development Installation

For contributing or development:

```bash
# Install development dependencies
pip install -r backend/requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Run linting
black backend/
flake8 backend/
mypy backend/
```

---

## 📚 Next Steps

After installation:

1. 📖 Read [QUICKSTART.md](QUICKSTART.md) for usage examples
2. 🏗️ Study [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
3. 🤝 See [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
4. 📧 Check [CONTACT.md](CONTACT.md) for support

---

## ❓ Getting Help

**Installation Issues?**

1. Check [Troubleshooting](#-troubleshooting) section above
2. Search existing [GitHub Issues](https://github.com/POWDER-RANGER/RAINGOD-ComfyUI-Integration/issues)
3. Join [ComfyUI Discussion #11176](https://github.com/comfyanonymous/ComfyUI/discussions/11176)
4. Open a new issue with:
   - Operating system & version
   - Python version
   - GPU model (if applicable)
   - Complete error message
   - Steps to reproduce

**Still Stuck?**

See [CONTACT.md](CONTACT.md) for direct support channels.

---

**Installation Complete! 🎉**

You're ready to start generating AI music visuals!

---

*Last Updated: January 8, 2026*  
*Maintainer: Curtis Charles Farrar*  
*ORCID: 0009-0008-9273-2458*
