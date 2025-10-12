#!/usr/bin/env python3
"""
Simple test for transitive dependency resolution.
Uses the existing test infrastructure.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'test'))

from test_lsp import LSPClient
from pathlib import Path

def test_transitive():
    """Test that transitively required symbols are found."""
    
    # Get absolute paths
    test_dir = Path(__file__).parent / "test" / "fixtures" / "transitive"
    top_file = test_dir / "top.jazz"
    
    if not top_file.exists():
        print(f"Error: {top_file} does not exist")
        return False
    
    # Start LSP client
    server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
    client = LSPClient(server_path)
    client.start()
    
    try:
        # Initialize
        print("Initializing LSP server...")
        root_uri = Path.cwd().as_uri()
        response = client.initialize(root_uri)
        if not response:
            print("Failed to initialize")
            return False
        print("✓ Initialized")
        
        # Open top.jazz
        print(f"\nOpening {top_file}...")
        with open(top_file, 'r') as f:
            content = f.read()
        
        file_uri = top_file.as_uri()
        client.did_open(file_uri, content, "jasmin")
        print("✓ Opened")
        
        # Test 1: Hover on BASE_CONSTANT (line 7, around column 20)
        # This symbol is defined in base.jinc which is required by middle.jinc
        print("\n=== Test 1: Hover on BASE_CONSTANT (transitive dependency) ===")
        print("Looking for 'BASE_CONSTANT' on line 7...")
        
        # Find exact position of BASE_CONSTANT
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'BASE_CONSTANT' in line and i >= 6:  # Around line 7
                col = line.index('BASE_CONSTANT')
                print(f"Found at line {i}, column {col}")
                
                response = client.hover(file_uri, i, col)
                print(f"Response: {response}")
                
                if response and 'contents' in response:
                    print("✅ SUCCESS: Hover found BASE_CONSTANT")
                    print(f"   Contents: {response['contents']}")
                else:
                    print("❌ FAILED: Hover did not find BASE_CONSTANT")
                    print("   This means transitive dependencies are not being followed!")
                    return False
                break
        
        # Test 2: Go to definition for BASE_CONSTANT
        print("\n=== Test 2: Go to definition for BASE_CONSTANT ===")
        for i, line in enumerate(lines):
            if 'BASE_CONSTANT' in line and i >= 6:
                col = line.index('BASE_CONSTANT')
                
                location = client.goto_definition(file_uri, i, col)
                print(f"Location: {location}")
                
                if location and len(location) > 0:
                    uri = location[0]['uri']
                    if 'base.jinc' in uri:
                        print("✅ SUCCESS: Definition found in base.jinc")
                        print(f"   Location: {location[0]}")
                    else:
                        print(f"❌ FAILED: Definition not in base.jinc: {uri}")
                        return False
                else:
                    print("❌ FAILED: No definition found")
                    print("   This means transitive dependencies are not being followed!")
                    return False
                break
        
        # Test 3: Hover on middle_function (direct dependency)
        print("\n=== Test 3: Hover on middle_function (direct dependency) ===")
        for i, line in enumerate(lines):
            if 'middle_function' in line:
                col = line.index('middle_function')
                print(f"Found at line {i}, column {col}")
                
                response = client.hover(file_uri, i, col)
                if response and 'contents' in response:
                    print("✅ SUCCESS: Hover found middle_function")
                else:
                    print("⚠️  WARNING: Hover did not find middle_function")
                break
        
        print("\n✅ All transitive dependency tests passed!")
        return True
        
    finally:
        client.stop()

if __name__ == '__main__':
    success = test_transitive()
    sys.exit(0 if success else 1)
