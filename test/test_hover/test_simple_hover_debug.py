#!/usr/bin/env python3
"""Simple test to debug hover on local variables with logging."""

import sys
sys.path.insert(0, 'test')

from conftest import LSPClient, LSP_SERVER
from pathlib import Path
import tempfile
import time
import select

# Create LSP client
client = LSPClient(LSP_SERVER)
client.start()
time.sleep(0.5)  # Give server time to start

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
    time.sleep(0.2)
    
    # Test hover on 'i' at line 1, column 11
    print(f"Testing hover on 'i' at line 1, column 10 (start of 'i')")
    print(f"URI: {uri}")
    response = client.hover(uri, 1, 10)
    print(f"Response: {response}\n")
    
    # Check for any stderr output from the server
    print("=" * 80)
    print("Server STDERR output:")
    print("=" * 80)
    
    # Read available stderr (non-blocking)
    import fcntl
    import os
    
    # Make stderr non-blocking
    fd = client.process.stderr.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    try:
        stderr_output = client.process.stderr.read()
        if stderr_output:
            print(stderr_output.decode('utf-8', errors='ignore'))
        else:
            print("(no stderr output)")
    except:
        print("(stderr not available)")

client.stop()
