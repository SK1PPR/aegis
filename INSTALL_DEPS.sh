#!/bin/bash
# Install dependencies for OTA benchmarking

echo "Installing OTA benchmark dependencies..."
pip install psutil matplotlib seaborn numpy pandas

echo ""
echo "✓ Installation complete!"
echo ""
echo "Run verification:"
echo "  python verify_ota_setup.py"
echo ""
echo "Start benchmarking:"
echo "  python run_ota_benchmark.py"
