#!/usr/bin/env python3
"""Test if the syntax is valid."""

import sys
sys.path.insert(0, 'test')

from conftest import LSPClient, LSP_SERVER
from pathlib import Path

# Create LSP client
client = LSPClient(LSP_SERVER)
client.start()
client.initialize()

# Test different parameter syntaxes
test_cases = [
    ("comma-separated", "fn test(reg u32 a, b) -> reg u32 { return a; }"),
    ("space-separated", "fn test(reg u32 a b) -> reg u32 { return a; }"),
    ("mixed", "fn test(reg u32 a, stack u64 x) -> reg u32 { return a; }"),
]

for name, code in test_cases:
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Code: {code}")
    print('='*60)
    
    uri = f"file:///tmp/test_{name}.jazz"
    client.open_document(uri, code)
    
    # Get document symbols
    response = client.document_symbols(uri)
    if response and "result" in response:
        result = response["result"]
        if result:
            print("Symbols extracted:")
            for symbol in result:
                print(f"  - {symbol['name']}: {symbol.get('detail', 'no detail')}")
        else:
            print("No symbols found (parse error?)")
    
    client.close_document(uri)

client.stop()
