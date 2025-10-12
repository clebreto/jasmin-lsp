#!/bin/bash
# Quick test runner for jasmin-lsp
# Builds the server if needed, then runs tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PATH="${SCRIPT_DIR}/_build/default/jasmin-lsp/jasmin_lsp.exe"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "Jasmin LSP - Quick Test Runner"
echo "================================"

# Check if server exists
if [ ! -f "$SERVER_PATH" ]; then
    echo -e "${YELLOW}Server not found. Building...${NC}"
    pixi run build
    
    # Fix library path on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [ -f "$SERVER_PATH" ]; then
            echo "Fixing library path for macOS..."
            install_name_tool -change \
                /usr/local/lib/libtree-sitter-jasmin.15.2025.dylib \
                @executable_path/../../../tree-sitter-jasmin/libtree-sitter-jasmin.dylib \
                "$SERVER_PATH" 2>/dev/null || true
        fi
    fi
fi

# Check again
if [ ! -f "$SERVER_PATH" ]; then
    echo -e "${RED}Error: Failed to build server${NC}"
    exit 1
fi

echo -e "${GREEN}Server found: $SERVER_PATH${NC}"
echo ""

# Choose test runner
if command -v python3 &> /dev/null; then
    echo "Running Python test suite..."
    cd "${SCRIPT_DIR}/test"
    python3 run_tests.py
else
    echo "Python not found. Running shell test suite..."
    cd "${SCRIPT_DIR}/test"
    ./test_all.sh
fi
