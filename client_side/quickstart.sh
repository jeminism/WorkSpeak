#!/bin/bash
# Quick setup and run for WorkSpeak Client

echo "=========================================="
echo "WorkSpeak Client Quick Start"
echo "=========================================="
echo ""

# Step 1: Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python 3 found"

# Step 2: Create venv
if [ ! -d "client_side/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv client_side/venv
fi
echo "✓ Virtual environment ready"

# Step 3: Activate and install
echo "Installing dependencies..."
source client_side/venv/bin/activate
pip install -q -r client_side/requirements.txt
echo "✓ Dependencies installed"

# Step 4: Create config
if [ ! -f "config/client_config.yaml" ]; then
    echo "Creating configuration file..."
    python -m client_side --create-config --config config/client_config.yaml
    echo ""
    echo "⚠️  You need to edit config/client_config.yaml and add your LLM API key!"
    echo "   Run this command to open the file:"
    echo "   nano config/client_config.yaml"
    exit 0
else
    echo "✓ Configuration exists"
fi

# Step 5: Run tests
echo ""
echo "Running tests..."
python -m client_side --test

echo ""
echo "=========================================="
echo "Ready to run!"
echo "=========================================="
echo ""
echo "To start the client:"
echo "  python -m client_side"
echo ""
echo "Or run without tray:"
echo "  python -m client_side --no-tray"
echo ""
echo "For configuration:"
echo "  python -m client_side --config config/client_config.yaml"
echo ""
