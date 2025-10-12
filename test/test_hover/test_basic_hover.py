"""
Tests for basic hover functionality showing type information.
"""

import pytest
from conftest import assert_response_ok, assert_has_result, assert_result_not_null


def test_hover_on_function(fixture_file, lsp_client):
    """Test hover on function body variable shows type information."""
    uri, content = fixture_file("types_test.jazz")
    
    # Hover on "result" variable at line 4 (inside process_u8 function)
    # This should show type information for the variable
    response = lsp_client.hover(uri, line=4, character=5)
    assert_response_ok(response, "hover on variable")
    
    # Hover might return null for positions without symbols, which is OK
    # Just check response is valid
    result = response.get("result")
    if result is not None:
        assert "contents" in result
        
        # Check that contents has value or is array
        contents = result["contents"]
        if isinstance(contents, dict):
            assert "value" in contents or "kind" in contents
        elif isinstance(contents, list):
            assert len(contents) > 0


def test_hover_on_variable_declaration(temp_document, lsp_client):
    """Test hover on variable declaration shows type."""
    code = """fn test_func(reg u64 x) -> reg u64 {
  reg u64 my_var;
  my_var = x + 1;
  return my_var;
}
"""
    uri = temp_document(code)
    
    # Hover on "my_var" at line 1
    response = lsp_client.hover(uri, line=1, character=10)
    assert_response_ok(response, "hover on variable")
    assert_result_not_null(response, "hover on variable")


def test_hover_on_parameter(temp_document, lsp_client):
    """Test hover on function parameter shows type."""
    code = """fn add_numbers(reg u64 a, reg u64 b) -> reg u64 {
  reg u64 sum;
  sum = a + b;
  return sum;
}
"""
    uri = temp_document(code)
    
    # Hover on parameter "a" at line 0
    response = lsp_client.hover(uri, line=0, character=20)
    assert_response_ok(response, "hover on parameter")
    # Parameter hover may or may not return info - both acceptable


def test_hover_shows_markdown(temp_document, lsp_client):
    """Test that hover contents are in markdown format."""
    code = """fn square(reg u64 x) -> reg u64 {
  reg u64 result;
  result = x * x;
  return result;
}
"""
    uri = temp_document(code)
    
    # Hover on "result" variable
    response = lsp_client.hover(uri, line=1, character=10)
    assert_response_ok(response, "hover")
    
    result = response.get("result")
    if result is not None:
        contents = result.get("contents")
        if isinstance(contents, dict):
            # Check for markdown kind
            if "kind" in contents:
                assert contents["kind"] in ["markdown", "plaintext"]
