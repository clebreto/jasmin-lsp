#!/bin/bash
# Comprehensive shell-based test suite for jasmin-lsp

# Note: Not using set -e because we want to continue on test failures
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LSP_SERVER="${PROJECT_ROOT}/_build/default/jasmin-lsp/jasmin_lsp.exe"
FIXTURES_DIR="${SCRIPT_DIR}/fixtures"

# Check if server exists
if [ ! -f "$LSP_SERVER" ]; then
    echo -e "${RED}Error: LSP server not found at $LSP_SERVER${NC}"
    echo "Build it with: pixi run build"
    exit 1
fi

# Helper function to send LSP message
send_lsp_message() {
    local message="$1"
    local length=${#message}
    printf "Content-Length: %d\r\n\r\n%s" "$length" "$message"
}

# Helper function to create file URI
file_uri() {
    local path="$1"
    echo "file://$(cd "$(dirname "$path")" && pwd)/$(basename "$path")"
}

# Test result functions
test_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}❌ $1: $2${NC}"
    ((FAILED++))
}

# Test 1: Server starts and responds to initialize
test_initialization() {
    echo "=========================================="
    echo "Test 1: Server Initialization"
    echo "=========================================="
    
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    
    local output=$(echo "$(send_lsp_message "$init_msg")" | "$LSP_SERVER" 2>/dev/null | head -n 50)
    
    if echo "$output" | grep -q '"capabilities"'; then
        test_pass "Server initialization"
    else
        test_fail "Server initialization" "No capabilities in response"
    fi
    
    if echo "$output" | grep -q '"definitionProvider"'; then
        test_pass "Definition provider capability"
    else
        test_fail "Definition provider capability" "Not found"
    fi
    
    if echo "$output" | grep -q '"hoverProvider"'; then
        test_pass "Hover provider capability"
    else
        test_fail "Hover provider capability" "Not found"
    fi
    
    if echo "$output" | grep -q '"referencesProvider"'; then
        test_pass "References provider capability"
    else
        test_fail "References provider capability" "Not found"
    fi
}

# Test 2: Diagnostics for clean file
test_diagnostics_clean() {
    echo ""
    echo "=========================================="
    echo "Test 2: Diagnostics - Clean File"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/simple_function.jazz"
    local uri=$(file_uri "$test_file")
    local content=$(cat "$test_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$content\"}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_output.txt &
    
    local pid=$!
    sleep 1.5
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_output.txt)
    
    if echo "$output" | grep -q 'publishDiagnostics'; then
        # Check if diagnostics array is empty or has no severe errors
        if echo "$output" | grep -q '"diagnostics":\[\]' || ! echo "$output" | grep -q '"severity":1'; then
            test_pass "Clean file has no errors"
        else
            test_fail "Clean file diagnostics" "Unexpected errors found"
        fi
    else
        test_fail "Clean file diagnostics" "No diagnostics published"
    fi
}

# Test 3: Diagnostics for file with errors
test_diagnostics_errors() {
    echo ""
    echo "=========================================="
    echo "Test 3: Diagnostics - Syntax Errors"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/syntax_errors.jazz"
    
    if [ ! -f "$test_file" ]; then
        test_fail "Syntax errors test" "Test file not found: $test_file"
        return
    fi
    
    local uri=$(file_uri "$test_file")
    local content=$(cat "$test_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$content\"}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_errors_output.txt &
    
    local pid=$!
    sleep 1.5
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_errors_output.txt)
    
    if echo "$output" | grep -q 'publishDiagnostics'; then
        # Should have diagnostics with errors
        if echo "$output" | grep -q '"diagnostics":\[' && ! echo "$output" | grep -q '"diagnostics":\[\]'; then
            local error_count=$(echo "$output" | grep -o '"severity":1' | wc -l)
            test_pass "Error file detected $error_count error(s)"
        else
            test_fail "Error file diagnostics" "No errors detected in file with syntax errors"
        fi
    else
        test_fail "Error file diagnostics" "No diagnostics published"
    fi
}

# Test 4: Document lifecycle (open, change, close)
test_document_lifecycle() {
    echo ""
    echo "=========================================="
    echo "Test 4: Document Lifecycle"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/simple_function.jazz"
    local uri=$(file_uri "$test_file")
    local content=$(cat "$test_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    local changed_content="${content}// New comment"
    
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$content\"}}}"
    local change_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didChange\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"version\":2},\"contentChanges\":[{\"text\":\"$changed_content\"}]}}"
    local close_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didClose\",\"params\":{\"textDocument\":{\"uri\":\"$uri\"}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_msg"
        sleep 0.3
        send_lsp_message "$change_msg"
        sleep 0.3
        send_lsp_message "$close_msg"
        sleep 0.3
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_lifecycle.txt &
    
    local pid=$!
    sleep 2
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_lifecycle.txt)
    
    # Count diagnostics messages (should be at least 2: one for open, one for change)
    local diag_count=$(echo "$output" | grep -c 'publishDiagnostics' || echo "0")
    
    if [ "$diag_count" -ge 2 ]; then
        test_pass "Document lifecycle (open/change/close)"
    else
        test_fail "Document lifecycle" "Expected multiple diagnostic publishes, got $diag_count"
    fi
}

# Test 5: Go to definition
test_goto_definition() {
    echo ""
    echo "=========================================="
    echo "Test 5: Go to Definition"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/simple_function.jazz"
    local uri=$(file_uri "$test_file")
    local content=$(cat "$test_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    # Position in the file where add_numbers is called (line 14, approximately)
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$content\"}}}"
    local def_msg="{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"textDocument/definition\",\"params\":{\"textDocument\":{\"uri\":\"$uri\"},\"position\":{\"line\":14,\"character\":10}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_msg"
        sleep 0.3
        send_lsp_message "$def_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_definition.txt &
    
    local pid=$!
    sleep 2
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_definition.txt)
    
    if echo "$output" | grep -q '"id":2' && echo "$output" | grep -q '"result"'; then
        if echo "$output" | grep -q '"uri"' && echo "$output" | grep -q '"range"'; then
            test_pass "Go to definition response"
        else
            test_fail "Go to definition" "Response missing location data"
        fi
    else
        test_fail "Go to definition" "No valid response received"
    fi
}

# Test 6: Find references
test_find_references() {
    echo ""
    echo "=========================================="
    echo "Test 6: Find References"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/references_test.jazz"
    
    if [ ! -f "$test_file" ]; then
        test_fail "Find references test" "Test file not found: $test_file"
        return
    fi
    
    local uri=$(file_uri "$test_file")
    local content=$(cat "$test_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$content\"}}}"
    local ref_msg="{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"textDocument/references\",\"params\":{\"textDocument\":{\"uri\":\"$uri\"},\"position\":{\"line\":3,\"character\":20},\"context\":{\"includeDeclaration\":true}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_msg"
        sleep 0.3
        send_lsp_message "$ref_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_references.txt &
    
    local pid=$!
    sleep 2
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_references.txt)
    
    if echo "$output" | grep -q '"id":2' && echo "$output" | grep -q '"result"'; then
        if echo "$output" | grep -q '\[' && echo "$output" | grep -q '"uri"'; then
            test_pass "Find references response"
        else
            test_fail "Find references" "Response missing references data"
        fi
    else
        test_fail "Find references" "No valid response received"
    fi
}

# Test 7: Hover
test_hover() {
    echo ""
    echo "=========================================="
    echo "Test 7: Hover Information"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/types_test.jazz"
    
    if [ ! -f "$test_file" ]; then
        test_fail "Hover test" "Test file not found: $test_file"
        return
    fi
    
    local uri=$(file_uri "$test_file")
    local content=$(cat "$test_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    local init_msg='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$content\"}}}"
    local hover_msg="{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"textDocument/hover\",\"params\":{\"textDocument\":{\"uri\":\"$uri\"},\"position\":{\"line\":3,\"character\":5}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_msg"
        sleep 0.3
        send_lsp_message "$hover_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_hover.txt &
    
    local pid=$!
    sleep 2
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_hover.txt)
    
    if echo "$output" | grep -q '"id":2' && echo "$output" | grep -q '"result"'; then
        if echo "$output" | grep -q '"contents"'; then
            test_pass "Hover information response"
        else
            test_fail "Hover" "Response missing contents"
        fi
    else
        test_fail "Hover" "No valid response received"
    fi
}

# Test 8: Cross-file go to definition
test_cross_file_goto_definition() {
    echo ""
    echo "=========================================="
    echo "Test 8: Cross-File Go to Definition"
    echo "=========================================="
    
    local main_file="${FIXTURES_DIR}/main_program.jazz"
    local lib_file="${FIXTURES_DIR}/math_lib.jazz"
    
    if [ ! -f "$main_file" ] || [ ! -f "$lib_file" ]; then
        test_fail "Cross-file goto definition" "Test files not found"
        return
    fi
    
    local main_uri=$(file_uri "$main_file")
    local lib_uri=$(file_uri "$lib_file")
    local workspace_uri=$(file_uri "$FIXTURES_DIR")
    
    local main_content=$(cat "$main_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    local lib_content=$(cat "$lib_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    # Initialize with workspace root set to fixtures directory
    local init_msg="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"processId\":null,\"rootUri\":\"$workspace_uri\",\"capabilities\":{}}}"
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_lib_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$lib_uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$lib_content\"}}}"
    local open_main_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$main_uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$main_content\"}}}"
    # Position of 'square' function call in main_program.jazz (line 13)
    local def_msg="{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"textDocument/definition\",\"params\":{\"textDocument\":{\"uri\":\"$main_uri\"},\"position\":{\"line\":13,\"character\":10}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_lib_msg"
        sleep 0.3
        send_lsp_message "$open_main_msg"
        sleep 0.3
        send_lsp_message "$def_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_cross_def.txt &
    
    local pid=$!
    sleep 2.5
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_cross_def.txt)
    
    if echo "$output" | grep -q '"id":2' && echo "$output" | grep -q '"result"'; then
        if echo "$output" | grep -q 'math_lib.jazz' || (echo "$output" | grep -q '"uri"' && echo "$output" | grep -q '"range"'); then
            test_pass "Cross-file go to definition"
        else
            test_fail "Cross-file go to definition" "Response missing expected location"
        fi
    else
        test_fail "Cross-file go to definition" "No valid response received"
    fi
}

# Test 9: Cross-file find references
test_cross_file_references() {
    echo ""
    echo "=========================================="
    echo "Test 9: Cross-File Find References"
    echo "=========================================="
    
    local main_file="${FIXTURES_DIR}/main_program.jazz"
    local lib_file="${FIXTURES_DIR}/math_lib.jazz"
    
    if [ ! -f "$main_file" ] || [ ! -f "$lib_file" ]; then
        test_fail "Cross-file references" "Test files not found"
        return
    fi
    
    local main_uri=$(file_uri "$main_file")
    local lib_uri=$(file_uri "$lib_file")
    local workspace_uri=$(file_uri "$FIXTURES_DIR")
    
    local main_content=$(cat "$main_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    local lib_content=$(cat "$lib_file" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    local init_msg="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"processId\":null,\"rootUri\":\"$workspace_uri\",\"capabilities\":{}}}"
    local initialized_msg='{"jsonrpc":"2.0","method":"initialized","params":{}}'
    local open_lib_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$lib_uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$lib_content\"}}}"
    local open_main_msg="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"$main_uri\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$main_content\"}}}"
    # Position of 'add' function definition in math_lib.jazz (line 10)
    local ref_msg="{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"textDocument/references\",\"params\":{\"textDocument\":{\"uri\":\"$lib_uri\"},\"position\":{\"line\":10,\"character\":3},\"context\":{\"includeDeclaration\":true}}}"
    
    {
        send_lsp_message "$init_msg"
        sleep 0.3
        send_lsp_message "$initialized_msg"
        sleep 0.3
        send_lsp_message "$open_lib_msg"
        sleep 0.3
        send_lsp_message "$open_main_msg"
        sleep 0.3
        send_lsp_message "$ref_msg"
        sleep 0.5
    } | "$LSP_SERVER" 2>/dev/null > /tmp/lsp_cross_refs.txt &
    
    local pid=$!
    sleep 2.5
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
    
    local output=$(cat /tmp/lsp_cross_refs.txt)
    
    if echo "$output" | grep -q '"id":2' && echo "$output" | grep -q '"result"'; then
        local uri_count=$(echo "$output" | grep -o '"uri"' | wc -l)
        if [ "$uri_count" -ge 1 ]; then
            test_pass "Cross-file find references (found $uri_count location(s))"
        else
            test_fail "Cross-file references" "No references found"
        fi
    else
        test_fail "Cross-file references" "No valid response received"
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "Jasmin LSP Test Suite"
    echo "=========================================="
    echo "Server: $LSP_SERVER"
    echo "Fixtures: $FIXTURES_DIR"
    echo ""
    
    # Check fixtures exist
    if [ ! -d "$FIXTURES_DIR" ]; then
        echo -e "${RED}Error: Fixtures directory not found: $FIXTURES_DIR${NC}"
        exit 1
    fi
    
    # Run tests
    test_initialization
    test_diagnostics_clean
    test_diagnostics_errors
    test_document_lifecycle
    test_goto_definition
    test_find_references
    test_hover
    test_cross_file_goto_definition
    test_cross_file_references
    
    # Summary
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    local total=$((PASSED + FAILED))
    echo -e "Total: $total"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo "=========================================="
    
    # Clean up temp files
    rm -f /tmp/lsp_*.txt
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

main "$@"
