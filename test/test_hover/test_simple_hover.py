#!/usr/bin/env python3
"""Simple test to debug hover on local variables."""

import sys
sys.path.insert(0, 'test')

from conftest import LSPClient, LSP_SERVER
from pathlib import Path
import tempfile

# Create LSP client
client = LSPClient(LSP_SERVER)
client.start()
client.initialize()

# Create a simple test file
TEST_CODE = """fn test() {
  reg u32 i, j;
  i = 1;
  j = 2;
}"""

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.jazz"
    test_file.write_text(TEST_CODE)
    uri = f"file://{test_file}"
    
    # Open the document
    client.open_document(uri, TEST_CODE)
    
    # Test hover on 'i' at line 1, column 11
    print(f"Testing hover on 'i' at line 1, column 11")
    print(f"URI: {uri}")
    response = client.hover(uri, 1, 11)
    print(f"Response: {response}")
    
    # Also try hovering on the declaration line (where the type is)
    print(f"\n\nTesting hover on type 'reg' at line 1, column 2")
    response2 = client.hover(uri, 1, 2)
    print(f"Response: {response2}")
    
    # Try on the 'u32' part
    print(f"\n\nTesting hover on 'u32' at line 1, column 6")
    response3 = client.hover(uri, 1, 6)
    print(f"Response: {response3}")
    
    if response and "result" in response:
        result = response["result"]
        if result is None:
            print("ERROR: Hover returned null!")
        else:
            print(f"Hover result: {result}")
    else:
        print(f"ERROR: No response or no result field")
    
    # Try to get document symbols to see what's extracted
    print("\n\nGetting document symbols...")
    symbols_response = client.document_symbols(uri)
    print(f"Symbols response: {symbols_response}")

client.stop()
