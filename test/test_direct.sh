#!/bin/bash

SERVER="_build/default/jasmin-lsp/jasmin_lsp.exe"

# Initialize
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{"textDocument":{"hover":{"contentFormat":["plaintext"]},"definition":{"linkSupport":false}}}}}'
printf "Content-Length: ${#INIT}\r\n\r\n${INIT}" | $SERVER 2>&1 &
SERVER_PID=$!
sleep 1

# Open document
DOC='{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///tmp/test.jazz","languageId":"jasmin","version":1,"text":"fn add_numbers(reg u64 x, reg u64 y) -> reg u64 {\n  reg u64 result;\n  result = x + y;\n  return result;\n}\n\nexport fn main(reg u64 input) -> reg u64 {\n  reg u64 temp;\n  temp = add_numbers(input, #42);\n  return temp;\n}"}}}'
printf "Content-Length: ${#DOC}\r\n\r\n${DOC}" | $SERVER 2>&1

# Wait and check
sleep 1

# Go to definition
GOTO='{"jsonrpc":"2.0","id":2,"method":"textDocument/definition","params":{"textDocument":{"uri":"file:///tmp/test.jazz"},"position":{"line":8,"character":9}}}'
printf "Content-Length: ${#GOTO}\r\n\r\n${GOTO}" | $SERVER 2>&1

wait $SERVER_PID
