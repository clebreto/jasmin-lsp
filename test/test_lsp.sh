#!/bin/bash
# Test script for jasmin-lsp with tree-sitter diagnostics

LSP_SERVER="_build/default/jasmin-lsp/jasmin_lsp.exe"

# Create a test Jasmin file with syntax error
TEST_FILE="/tmp/test.jazz"
cat > "$TEST_FILE" <<'EOF'
fn test_function(reg u64 x) -> reg u64 {
  reg u64 y;
  y = x + 1;
  return y
  // Missing semicolon should trigger diagnostic
}

fn broken_syntax {
  // Missing parameter list
  reg u64 z;
}
EOF

# Function to send LSP message
send_lsp() {
    local message="$1"
    local length=${#message}
    printf "Content-Length: %d\r\n\r\n%s" "$length" "$message"
}

# Initialize
INIT_MSG='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{"textDocument":{"publishDiagnostics":{}}}}}'

# Open document
OPEN_MSG="{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didOpen\",\"params\":{\"textDocument\":{\"uri\":\"file://$TEST_FILE\",\"languageId\":\"jasmin\",\"version\":1,\"text\":\"$(cat "$TEST_FILE" | sed 's/"/\\"/g' | tr '\n' ' ')\"}}}"

# Send messages to server
{
    send_lsp "$INIT_MSG"
    sleep 0.5
    send_lsp '{"jsonrpc":"2.0","id":2,"method":"initialized","params":{}}'
    sleep 0.5
    send_lsp "$OPEN_MSG"
    sleep 1
    send_lsp '{"jsonrpc":"2.0","id":3,"method":"shutdown","params":null}'
    send_lsp '{"jsonrpc":"2.0","method":"exit","params":null}'
} | "$LSP_SERVER" 2>&1 | grep -A 10 "diagnostic\|ERROR\|syntax"

echo ""
echo "Test complete. Check output above for diagnostics."
