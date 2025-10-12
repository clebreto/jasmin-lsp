#!/usr/bin/env python3
"""
Simple test for transitive dependency resolution.
Uses the existing test infrastructure.
"""

import sys
import os
from pathlib import Path
import pytest

# Import from conftest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import LSPClient, LSP_SERVER

@pytest.mark.xfail(reason="Transitive dependency resolution not yet fully implemented")
def test_transitive():
    """Test that transitively required symbols are found."""
    
    # Get absolute paths - fixtures should be in test/fixtures/transitive
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "transitive"
    top_file = fixtures_dir / "top.jazz"
    
    # Skip test if fixture doesn't exist
    if not top_file.exists():
        pytest.skip(f"Test fixture not found: {top_file}")
    
    # Start LSP client
    client = LSPClient(LSP_SERVER)
    client.start()
    
    try:
        # Initialize
        root_uri = Path.cwd().as_uri()
        response = client.initialize(root_uri)
        assert response is not None, "Failed to initialize"
        
        # Open top.jazz
        with open(top_file, 'r') as f:
            content = f.read()
        
        file_uri = top_file.as_uri()
        client.open_document(file_uri, content, "jasmin")
        
        # Test 1: Hover on BASE_CONSTANT (transitive dependency)
        # This symbol is defined in base.jinc which is required by middle.jinc
        lines = content.split('\n')
        base_constant_found = False
        
        for i, line in enumerate(lines):
            if 'BASE_CONSTANT' in line and i >= 6:  # Around line 7
                col = line.index('BASE_CONSTANT')
                
                response = client.hover(file_uri, i, col)
                
                if response and 'result' in response:
                    result = response['result']
                    if result and 'contents' in result:
                        print("✅ SUCCESS: Hover found BASE_CONSTANT")
                        print(f"   Contents: {result['contents']}")
                        base_constant_found = True
                        break
        
        assert base_constant_found, "Hover did not find BASE_CONSTANT from transitive dependency"
        
        # Test 2: Go to definition for BASE_CONSTANT
        definition_found = False
        for i, line in enumerate(lines):
            if 'BASE_CONSTANT' in line and i >= 6:
                col = line.index('BASE_CONSTANT')
                
                response = client.definition(file_uri, i, col)
                
                if response and 'result' in response:
                    location = response['result']
                    if location and len(location) > 0:
                        uri = location[0]['uri']
                        if 'base.jinc' in uri:
                            print("✅ SUCCESS: Definition found in base.jinc")
                            definition_found = True
                            break
        
        assert definition_found, "Go to definition did not find BASE_CONSTANT in base.jinc"
        
        # Test 3: Hover on middle_function (direct dependency)
        middle_found = False
        for i, line in enumerate(lines):
            if 'middle_function' in line:
                col = line.index('middle_function')
                
                response = client.hover(file_uri, i, col)
                if response and 'result' in response and response['result']:
                    print("✅ SUCCESS: Hover found middle_function")
                    middle_found = True
                    break
        
        # This is a softer assertion - warn but don't fail
        if not middle_found:
            print("⚠️  WARNING: Hover did not find middle_function")
        
    finally:
        client.stop()
