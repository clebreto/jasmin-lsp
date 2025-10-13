#!/usr/bin/env python3
"""Test if find references works for variable 'a'."""

import sys
sys.path.insert(0, 'test')

from conftest import LSPClient, LSP_SERVER
import tempfile
from pathlib import Path

REFERENCES_CODE = """fn helper(reg u64 x) -> reg u64 {
  return x + 1;
}

fn main() {
  reg u64 a;
  reg u64 b;
  a = helper(5);
  b = helper(10);
  return a + b;
}
"""

# Create LSP client
client = LSPClient(LSP_SERVER)
client.start()
client.initialize()

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.jazz"
    test_file.write_text(REFERENCES_CODE)
    uri = f"file://{test_file}"
    
    # Open the document
    client.open_document(uri, REFERENCES_CODE)
    
    print("Testing find references for variable 'a':")
    print("=" * 60)
    
    # Line 5, column 10 (declaration of 'a')
    print(f"\nFinding references to 'a' at line 5, column 10 (declaration):")
    response = client.references(uri, 5, 10, include_declaration=True)
    if response and "result" in response:
        result = response["result"]
        if result:
            print(f"  Found {len(result)} references:")
            for ref in result:
                line = ref["range"]["start"]["line"]
                col = ref["range"]["start"]["character"]
                print(f"    - Line {line}, column {col}")
        else:
            print(f"  No references found (result is null/empty)")
    else:
        print(f"  ERROR: {response}")

client.stop()
