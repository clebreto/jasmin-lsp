"""
Tests for go-to-definition functionality.
"""

import pytest
from conftest import assert_response_ok, assert_has_result, assert_result_not_null


GOTO_DEF_CODE = """fn add_numbers(reg u64 a, reg u64 b) -> reg u64 {
  reg u64 sum;
  sum = a + b;
  return sum;
}

fn main() {
  reg u64 result;
  result = add_numbers(5, 10);
  return result;
}
"""


def test_goto_definition_function_call(temp_document, lsp_client):
    """Test go-to-definition on a function call jumps to function definition."""
    uri = temp_document(GOTO_DEF_CODE)
    
    # Position on "add_numbers" call at line 8 (in main function)
    response = lsp_client.definition(uri, line=8, character=11)
    assert_response_ok(response, "goto definition")
    assert_has_result(response, "goto definition")
    
    result = response["result"]
    assert result is not None, "Should find definition"
    
    # Result can be Location or Location[]
    if isinstance(result, list):
        assert len(result) > 0, "Should have at least one location"
        location = result[0]
    else:
        location = result
    
    # Should point to line 0 (where add_numbers is defined)
    assert "range" in location
    assert location["range"]["start"]["line"] == 0


def test_goto_definition_variable(temp_document, lsp_client):
    """Test go-to-definition on a variable usage jumps to declaration."""
    uri = temp_document(GOTO_DEF_CODE)
    
    # Position on "sum" usage at line 2 (sum = a + b)
    response = lsp_client.definition(uri, line=2, character=2)
    assert_response_ok(response, "goto definition for variable")
    assert_has_result(response, "goto definition for variable")
    
    result = response["result"]
    if result is not None:
        # Should point to line 1 (where sum is declared)
        if isinstance(result, list) and len(result) > 0:
            location = result[0]
            assert "range" in location
            assert location["range"]["start"]["line"] == 1


def test_goto_definition_on_definition_itself(temp_document, lsp_client):
    """Test go-to-definition on the definition itself."""
    uri = temp_document(GOTO_DEF_CODE)
    
    # Position on function name in its definition (line 0)
    response = lsp_client.definition(uri, line=0, character=3)
    assert_response_ok(response, "goto definition on definition")
    assert_has_result(response, "goto definition on definition")
    
    result = response["result"]
    # Should return the same location or null
    if result is not None:
        if isinstance(result, list):
            assert len(result) > 0
        else:
            assert "range" in result


def test_goto_definition_nonexistent(temp_document, lsp_client):
    """Test go-to-definition on a non-existent symbol."""
    code = """fn test() {
  reg u64 x;
  x = 5;
}
"""
    uri = temp_document(code)
    
    # Position on whitespace or number (no symbol)
    response = lsp_client.definition(uri, line=2, character=6)
    
    # The server may return either:
    # 1. An error: "No symbol at position" (current behavior)
    # 2. null result (also acceptable)
    # 3. empty array (also acceptable)
    
    if "error" in response:
        # Accept error response for "no symbol"
        assert response["error"]["message"] == "No symbol at position"
    else:
        # Accept null or empty result
        assert_response_ok(response, "goto definition on non-symbol")
        assert_has_result(response, "goto definition on non-symbol")
        
        result = response["result"]
        # Should return null or empty array
        if isinstance(result, list):
            assert len(result) == 0 or result[0] is None
        else:
            assert result is None
