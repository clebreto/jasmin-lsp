#!/usr/bin/env python3
"""Debug parameter extraction."""

import sys
sys.path.insert(0, 'test')

from conftest import LSPClient, LSP_SERVER
from pathlib import Path
import tempfile

# Create LSP client
client = LSPClient(LSP_SERVER)
client.start()
client.initialize()

# Test code with comma-separated params
TEST_CODE = """fn test(reg u32 a, b, stack u64 x, y, z) -> reg u32 {
  return a;
}"""

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.jazz"
    test_file.write_text(TEST_CODE)
    uri = f"file://{test_file}"
    
    # Open the document
    client.open_document(uri, TEST_CODE)
    
    # Get document symbols to see what's extracted
    print("Getting document symbols...")
    symbols_response = client.document_symbols(uri)
    
    if symbols_response and "result" in symbols_response:
        result = symbols_response["result"]
        if result:
            for symbol in result:
                print(f"- {symbol['name']}: {symbol.get('detail', 'no detail')} (kind: {symbol['kind']})")
        else:
            print("No symbols found")
    else:
        print(f"ERROR: {symbols_response}")

client.stop()
