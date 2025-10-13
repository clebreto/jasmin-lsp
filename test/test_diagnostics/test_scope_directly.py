#!/usr/bin/env python3
"""Test scope bug with correct positions."""

import sys
sys.path.insert(0, 'test')

from conftest import LSPClient, LSP_SERVER
import tempfile
from pathlib import Path

test_content = """export fn first_function(
    #public reg ptr u8[32] sig
) -> #public reg u32
{
    reg u32 status;
    
    status = 0;
    
    return status;
}

export fn second_function(
    #public reg ptr u8[64] data
) -> #public reg u32 {
    reg u32 status;
    
    status = 1;
    status = status;
    
    return status;
}
"""

# Create LSP client
client = LSPClient(LSP_SERVER)
client.start()
client.initialize()

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.jazz"
    test_file.write_text(test_content)
    uri = f"file://{test_file}"
    
    # Open the document
    client.open_document(uri, test_content)
    
    print("Testing go-to-definition on 'status' variables:")
    print("=" * 60)
    
    # Line 17 (0-indexed), second status at column 13
    print(f"\nLine 17, column 13 (second 'status' in 'status = status;'):")
    response = client.definition(uri, 17, 13)
    if response and "result" in response and response["result"]:
        location = response["result"][0] if isinstance(response["result"], list) else response["result"]
        def_line = location["range"]["start"]["line"]
        print(f"  Definition found at line {def_line}")
        if def_line == 14:
            print(f"  ✅ CORRECT: Points to declaration in second_function")
        elif def_line == 4:
            print(f"  ❌ BUG: Points to declaration in first_function!")
    else:
        print(f"  ERROR: {response}")

client.stop()
