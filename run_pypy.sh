#!/bin/bash
# Run MCP Gateway with PyPy for JIT compilation performance

# Check if PyPy is installed
if ! command -v pypy3 &> /dev/null; then
    echo "PyPy3 not found. Install with:"
    echo "  macOS: brew install pypy3"
    echo "  Linux: sudo apt install pypy3"
    exit 1
fi

# Create PyPy virtual environment if not exists
if [ ! -d "venv_pypy" ]; then
    echo "Creating PyPy virtual environment..."
    pypy3 -m venv venv_pypy
    source venv_pypy/bin/activate
    pip install -r requirements.txt
else
    source venv_pypy/bin/activate
fi

# Run with PyPy
export PYTHONPATH="$PWD/src"
pypy3 run_mcp_gateway.py "$@"