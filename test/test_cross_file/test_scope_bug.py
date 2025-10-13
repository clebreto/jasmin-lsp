#!/usr/bin/env python3
"""
Test for scope resolution bug where go-to-definition on a variable
in one function jumps to a variable with the same name in a different function.
"""

import pytest
import tempfile
import os
from pathlib import Path


def test_scope_resolution(lsp_client, temp_document):
    """Test that go-to-definition respects function scope"""
    
    # Create test file with two functions, each with a 'status' variable
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
    
    # Use temp_document fixture to create and open the document
    uri = temp_document(test_content)
    
    print("\n🔍 Testing scope resolution bug...")
    print("=" * 60)
    
    # Test 1: Go to definition on 'status' in first function (line 6, should stay in first function)
    print("\n📍 Test 1: 'status' in first_function (line 6)")
    response = lsp_client.definition(uri, line=6, character=4)
    
    if "result" in response and response["result"]:
        location = response["result"][0] if isinstance(response["result"], list) else response["result"]
        def_line = location["range"]["start"]["line"]
        print(f"Definition found at line {def_line}")
        
        # Should be line 4 (the declaration in first_function)
        assert def_line == 4, f"Expected line 4 (first_function declaration), got line {def_line}"
        print("✅ CORRECT: Jumped to declaration in first_function")
    else:
        pytest.fail("No definition found for 'status' in first_function")
    
    # Test 2: Go to definition on second 'status' in 'status = status;' in second function
    # This should jump to line 14 (declaration in second_function), NOT line 4 (first_function)
    print("\n📍 Test 2: Second 'status' in 'status = status;' in second_function (line 17)")
    
    # The second 'status' is at column 13
    response = lsp_client.definition(uri, line=17, character=13)
    print(f"  Response: {response.get('result') if 'result' in response else response.get('error')}")
    
    if response and "result" in response and response["result"]:
        location = response["result"][0] if isinstance(response["result"], list) else response["result"]
        def_line = location["range"]["start"]["line"]
        print(f"Definition found at line {def_line}")
        
        # Should be line 14 (the declaration in second_function)
        # If it's line 4, that's the bug - it jumped to first_function
        if def_line == 14:
            print("✅ CORRECT: Jumped to declaration in second_function")
        elif def_line == 4:
            pytest.fail("Bug: Go-to-definition jumps to wrong function (line 4 instead of 14)")
        else:
            pytest.fail(f"Unexpected: Got line {def_line}, expected 4 or 14")
    else:
        # If we can't find the symbol, this test isn't working as expected
        pytest.fail(f"Cannot find 'status' symbol on line 17: {response}")
    
    # Test 3: Go to definition on first 'status' in 'status = status;' (should also go to line 14)
    print("\n📍 Test 3: First 'status' in 'status = status;' in second_function (line 17)")
    
    # The first 'status' is at column 4
    response = lsp_client.definition(uri, line=17, character=4)
    
    if response and "result" in response and response["result"]:
        location = response["result"][0] if isinstance(response["result"], list) else response["result"]
        def_line = location["range"]["start"]["line"]
        print(f"Definition found at line {def_line}")
        
        if def_line == 14:
            print("✅ CORRECT: Jumped to declaration in second_function")
        elif def_line == 4:
            pytest.fail("Bug: Go-to-definition jumps to wrong function")
        else:
            print(f"⚠️ Unexpected line: {def_line}")
    else:
        pytest.fail(f"Cannot find 'status' symbol on line 17 at column 4: {response}")
    
    print("\n✅ All scope resolution tests passed!")

