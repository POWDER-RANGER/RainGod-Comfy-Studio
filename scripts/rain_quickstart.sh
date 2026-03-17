#!/bin/bash

# ============================================================================
# RAINGOD Quickstart Script
# One-command setup and launch for RAINGOD-ComfyUI-Integration
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Configuration
# ============================================================================

COMFYUI_DIR="${COMFYUI_DIR:-./ComfyUI}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
PYTHON_CMD="${PYTHON_CMD:-python3}"
VENV_DIR="${VENV_DIR:-venv}"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 found"
        return 0
    else
        print_error "$1 not found"
        return 1
    fi
}

# ============================================================================
# System Checks
# ============================================================================

print_header "RAINGOD Quickstart - System Check"

# Check Python
if ! check_command $PYTHON_CMD; then
    print_error "Python 3.10+ is required"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    print_error "Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Check Git
if ! check_command git; then
    print_warning "Git not found - ComfyUI installation may fail"
fi

# Check for GPU (optional)
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
    print_success "GPU detected: $GPU_INFO"
else
    print_warning "No NVIDIA GPU detected - will run on CPU (slower)"
fi

# ============================================================================
# Virtual Environment Setup
# ============================================================================

print_header "Setting Up Python Environment"

if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv $VENV_DIR
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source $VENV_DIR/bin/activate || source $VENV_DIR/Scripts/activate
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "Pip upgraded"

# ============================================================================
# Install Dependencies
# ============================================================================

print_header "Installing Dependencies"

if [ -f "backend/requirements.txt" ]; then
    print_info "Installing backend requirements..."
    pip install -r backend/requirements.txt
    print_success "Backend dependencies installed"
else
    print_warning "requirements.txt not found - skipping dependency installation"
fi

# ============================================================================
# ComfyUI Setup
# ============================================================================

print_header "ComfyUI Setup"

if [ ! -d "$COMFYUI_DIR" ]; then
    print_info "ComfyUI not found. Would you like to install it? (y/n)"
    read -r INSTALL_COMFYUI
    
    if [ "$INSTALL_COMFYUI" = "y" ] || [ "$INSTALL_COMFYUI" = "Y" ]; then
        print_info "Cloning ComfyUI repository..."
        git clone https://github.com/comfyanonymous/ComfyUI.git $COMFYUI_DIR
        
        print_info "Installing ComfyUI dependencies..."
        cd $COMFYUI_DIR
        pip install -r requirements.txt
        cd ..
        
        print_success "ComfyUI installed"
    else
        print_warning "ComfyUI not installed - you'll need to install it manually"
        print_info "Clone from: https://github.com/comfyanonymous/ComfyUI"
    fi
else
    print_success "ComfyUI already installed at $COMFYUI_DIR"
fi

# ============================================================================
# Directory Structure
# ============================================================================

print_header "Creating Directory Structure"

# Create required directories
mkdir -p outputs
mkdir -p temp
mkdir -p logs
mkdir -p cache
mkdir -p workflows/exports

print_success "Directory structure created"

# ============================================================================
# Configuration Check
# ============================================================================

print_header "Configuration Check"

# Check for config file
if [ -f "backend/rain_backend_config.py" ]; then
    print_success "Configuration file found"
else
    print_error "Configuration file missing: backend/rain_backend_config.py"
    exit 1
fi

# Check for backend
if [ -f "backend/rain_backend.py" ]; then
    print_success "Backend file found"
else
    print_error "Backend file missing: backend/rain_backend.py"
    exit 1
fi

# ============================================================================
# Start Services
# ============================================================================

print_header "Starting Services"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# Start ComfyUI
if check_port $COMFYUI_PORT; then
    print_info "ComfyUI already running on port $COMFYUI_PORT"
else
    print_info "Starting ComfyUI on port $COMFYUI_PORT..."
    
    if [ -d "$COMFYUI_DIR" ]; then
        cd $COMFYUI_DIR
        nohup $PYTHON_CMD main.py --port $COMFYUI_PORT > ../logs/comfyui.log 2>&1 &
        COMFYUI_PID=$!
        echo $COMFYUI_PID > ../logs/comfyui.pid
        cd ..
        
        # Wait for ComfyUI to start
        print_info "Waiting for ComfyUI to start..."
        for i in {1..30}; do
            if check_port $COMFYUI_PORT; then
                print_success "ComfyUI started (PID: $COMFYUI_PID)"
                break
            fi
            sleep 1
        done
        
        if ! check_port $COMFYUI_PORT; then
            print_error "ComfyUI failed to start - check logs/comfyui.log"
        fi
    else
        print_warning "ComfyUI directory not found - skipping ComfyUI start"
    fi
fi

# Start Backend
if check_port $BACKEND_PORT; then
    print_info "Backend already running on port $BACKEND_PORT"
else
    print_info "Starting RAINGOD Backend on port $BACKEND_PORT..."
    
    cd backend
    nohup uvicorn rain_backend:app --host 0.0.0.0 --port $BACKEND_PORT > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../logs/backend.pid
    cd ..
    
    # Wait for backend to start
    print_info "Waiting for backend to start..."
    for i in {1..20}; do
        if check_port $BACKEND_PORT; then
            print_success "Backend started (PID: $BACKEND_PID)"
            break
        fi
        sleep 1
    done
    
    if ! check_port $BACKEND_PORT; then
        print_error "Backend failed to start - check logs/backend.log"
    fi
fi

# ============================================================================
# Health Check
# ============================================================================

print_header "Health Check"

sleep 2  # Give services a moment to fully initialize

# Check backend health
if command -v curl &> /dev/null; then
    HEALTH_RESPONSE=$(curl -s http://localhost:$BACKEND_PORT/health 2>/dev/null || echo "")
    
    if [ ! -z "$HEALTH_RESPONSE" ]; then
        print_success "Backend health check passed"
        
        # Check ComfyUI connection
        if echo "$HEALTH_RESPONSE" | grep -q '"comfyui_healthy":true'; then
            print_success "ComfyUI connection verified"
        else
            print_warning "ComfyUI connection failed - check configuration"
        fi
    else
        print_error "Backend health check failed"
    fi
else
    print_warning "curl not found - skipping health check"
fi

# ============================================================================
# Summary
# ============================================================================

print_header "RAINGOD Services Status"

echo ""
echo "🎵 RAINGOD-ComfyUI-Integration is ready!"
echo ""
echo "Service URLs:"
echo "  • ComfyUI:        http://localhost:$COMFYUI_PORT"
echo "  • Backend API:    http://localhost:$BACKEND_PORT"
echo "  • API Docs:       http://localhost:$BACKEND_PORT/docs"
echo "  • Health Check:   http://localhost:$BACKEND_PORT/health"
echo ""
echo "Logs:"
echo "  • ComfyUI:        logs/comfyui.log"
echo "  • Backend:        logs/backend.log"
echo ""
echo "Next Steps:"
echo "  1. Open API docs: http://localhost:$BACKEND_PORT/docs"
echo "  2. Try a test generation"
echo "  3. Check out examples/ directory"
echo ""
echo "To stop services:"
echo "  ./scripts/stop_all.sh"
echo ""

# ============================================================================
# Interactive Mode (Optional)
# ============================================================================

print_info "Would you like to run a test generation? (y/n)"
read -r RUN_TEST

if [ "$RUN_TEST" = "y" ] || [ "$RUN_TEST" = "Y" ]; then
    print_info "Running test generation..."
    
    if command -v curl &> /dev/null; then
        curl -X POST "http://localhost:$BACKEND_PORT/generate" \
          -H "Content-Type: application/json" \
          -d '{
            "prompt": "a beautiful sunset over mountains",
            "preset": "fast",
            "resolution": "thumbnail"
          }' | python -m json.tool
    else
        print_warning "curl not found - skipping test generation"
    fi
fi

print_success "Quickstart complete! Happy creating! 🎨"
