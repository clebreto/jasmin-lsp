#!/bin/bash
# Create a named pipe for testing
mkfifo test_pipe

# Start server reading from pipe
OCAMLRUNPARAM=b ./_build/default/jasmin-lsp/jasmin_lsp.exe < test_pipe &
LSP_PID=$!

# Send test messages
{
  printf "Content-Length: 121\r\n\r\n"
  printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":null,"capabilities":{}}}'
} > test_pipe

# Wait and check logs
sleep 1

# Cleanup
kill $LSP_PID 2>/dev/null
rm test_pipe