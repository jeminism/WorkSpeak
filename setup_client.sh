#!/bin/bash
# WorkSpeak Client Setup Script

set -e

echo "=========================================="
echo "WorkSpeak Client Setup"
echo "=========================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install client dependencies
echo "Installing client dependencies..."
pip install -r client_side/requirements.txt

# Install dev dependencies
echo "Installing testing dependencies..."
pip install pytest

# Create default config
echo "Creating default configuration..."
python -m client_side --create-config --config config/client_config.yaml

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config/client_config.yaml with your LLM API key"
echo "2. Grant accessibility permissions (macOS)"
echo "3. Run: python -m client_side"
echo "4. For test mode: python -m client_side --test"
echo ""
