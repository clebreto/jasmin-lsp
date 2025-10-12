#!/usr/bin/env python3
"""
Real-world test using actual Jasmin code from the gimli example.
This tests the LSP server with the same file VS Code is using.
"""

import json
import subprocess
import sys
import os

GREEN = '\033[0;32m'
RED = '\033[0;31m'
NC = '\033[0m'

def send_lsp(server_path, messages):
    """Send messages to LSP server and get response"""
    input_data = ""
    for msg in messages:
        content = json.dumps(msg)
        content_bytes = content.encode('utf-8')
        input_data += f"Content-Length: {len(content_bytes)}\r\n\r\n{content}"
    
    try:
        result = subprocess.run(
            [server_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired as e:
        return (e.stdout or "") + (e.stderr or "")

# Real Jasmin file content
gimli_jazz = """param int N_ROUND = 24;
param int N_COLUMN = 4;
param int ROUND_CONSTANT = 0x9e377900;

inline
fn swap(reg ptr u32[12] state, inline int i, inline int j) -> reg ptr u32[12] {
    reg u32 x y;

    x = state[i];
    y = state[j];
    state[i] = y;
    state[j] = x;

    return state;
}

export
fn gimli(reg ptr u32[12] state) -> reg ptr u32[12] {
    inline int round, column;
    reg u32 x, y, z;
    reg u32 a, b;
    reg u32 rc;

    rc = ROUND_CONSTANT;

    for round = N_ROUND downto 0 {
        for column = 0 to N_COLUMN {
            x = state[0 + column];
            x <<r= 24;
            y = state[4 + column];
            y <<r= 9;
            z = state[8 + column];

            a = x ^ (z << 1);
            b = y & z;
            a ^= b << 2;
            state[8 + column] = a;
        }

        if (round % 4 == 0) {
            state = swap(state, 0, 1);
        }
    }
    return state;
}
"""

server_path = os.environ.get(
    'LSP_SERVER_PATH',
    '_build/default/jasmin-lsp/jasmin_lsp.exe'
)

if not os.path.exists(server_path):
    print(f"{RED}Server not found: {server_path}{NC}")
    sys.exit(1)

print("Testing jasmin-lsp with real Jasmin code (gimli.jazz)")
print("=" * 60)

# Test 1: Document Symbol
print("\n1. Testing Document Symbol (outline)...")
init_msg = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "processId": os.getpid(),
        "rootUri": "file:///tmp",
        "capabilities": {}
    }
}

initialized_msg = {
    "jsonrpc": "2.0",
    "method": "initialized",
    "params": {}
}

open_msg = {
    "jsonrpc": "2.0",
    "method": "textDocument/didOpen",
    "params": {
        "textDocument": {
            "uri": "file:///tmp/gimli.jazz",
            "languageId": "jasmin",
            "version": 1,
            "text": gimli_jazz
        }
    }
}

symbol_msg = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "textDocument/documentSymbol",
    "params": {
        "textDocument": {"uri": "file:///tmp/gimli.jazz"}
    }
}

output = send_lsp(server_path, [init_msg, initialized_msg, open_msg, symbol_msg])

if '"id":2' in output and '"result"' in output and 'DocumentSymbol' in output:
    print(f"{GREEN}✅ Document symbols work!{NC}")
    # Try to extract symbol names
    if 'swap' in output and 'gimli' in output:
        print(f"   Found functions: swap, gimli")
else:
    print(f"{RED}❌ Document symbols failed{NC}")
    if "Unsupported request" in output:
        print("   Server says unsupported")

# Test 2: Hover on function name
print("\n2. Testing Hover (on 'swap' function call, line 41)...")
hover_msg = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "textDocument/hover",
    "params": {
        "textDocument": {"uri": "file:///tmp/gimli.jazz"},
        "position": {"line": 40, "character": 18}  # Position of 'swap'
    }
}

output = send_lsp(server_path, [init_msg, initialized_msg, open_msg, hover_msg])

if '"id":3' in output and '"result"' in output and 'contents' in output:
    print(f"{GREEN}✅ Hover works!{NC}")
    if 'swap' in output:
        print(f"   Shows info for 'swap'")
else:
    print(f"{RED}❌ Hover failed{NC}")

# Test 3: Go to definition
print("\n3. Testing Go to Definition (on 'swap' call)...")
def_msg = {
    "jsonrpc": "2.0",
    "id": 4,
    "method": "textDocument/definition",
    "params": {
        "textDocument": {"uri": "file:///tmp/gimli.jazz"},
        "position": {"line": 40, "character": 18}
    }
}

output = send_lsp(server_path, [init_msg, initialized_msg, open_msg, def_msg])

if '"id":4' in output and '"result"' in output and '"range"' in output:
    print(f"{GREEN}✅ Go to definition works!{NC}")
    # Check if it points to line 6 (where swap is defined)
    if '"line":5' in output or '"line":6' in output:
        print(f"   Correctly points to swap definition (line 6)")
else:
    print(f"{RED}❌ Go to definition failed{NC}")

# Test 4: Find references
print("\n4. Testing Find References (on 'swap')...")
ref_msg = {
    "jsonrpc": "2.0",
    "id": 5,
    "method": "textDocument/references",
    "params": {
        "textDocument": {"uri": "file:///tmp/gimli.jazz"},
        "position": {"line": 5, "character": 5},  # On the definition
        "context": {"includeDeclaration": True}
    }
}

output = send_lsp(server_path, [init_msg, initialized_msg, open_msg, ref_msg])

if '"id":5' in output and '"result"' in output:
    # Count occurrences of "range" to estimate number of references
    ref_count = output.count('"range"')
    if ref_count >= 2:  # At least definition + one call
        print(f"{GREEN}✅ Find references works!{NC}")
        print(f"   Found {ref_count} reference(s)")
    else:
        print(f"{RED}❌ Find references returned {ref_count} results{NC}")
else:
    print(f"{RED}❌ Find references failed{NC}")

# Test 5: Diagnostics
print("\n5. Testing Diagnostics (should be clean for gimli.jazz)...")
# Diagnostics are sent as notifications, check stderr
if "publishDiagnostics" in output:
    if '"diagnostics":[]' in output:
        print(f"{GREEN}✅ Diagnostics work (no errors)!{NC}")
    else:
        print(f"{RED}⚠️  Diagnostics found errors in clean file{NC}")
else:
    print(f"{RED}⚠️  No diagnostics published (async issue){NC}")

print("\n" + "=" * 60)
print("Real-world test complete!")
print("\nNow try opening gimli.jazz in VS Code with the LSP server.")
print("The server is installed at:")
print(f"  {os.path.abspath(server_path)}")
