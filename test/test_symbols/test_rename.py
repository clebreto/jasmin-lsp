"""
Tests for rename symbol functionality.
"""

import pytest
from conftest import assert_response_ok, assert_has_result


RENAME_CODE = """fn calculate(reg u64 value) -> reg u64 {
  reg u64 result;
  result = value * 2;
  return result;
}

fn main() {
  reg u64 x;
  x = calculate(5);
  return x;
}
"""


def test_rename_function(temp_document, lsp_client):
    """Test renaming a function."""
    uri = temp_document(RENAME_CODE)
    
    # Rename "calculate" to "compute"
    response = lsp_client.rename(uri, line=0, character=3, new_name="compute")
    assert_response_ok(response, "rename")
    assert_has_result(response, "rename")
    
    result = response["result"]
    # Result should be WorkspaceEdit with changes
    if result is not None:
        assert "changes" in result or "documentChanges" in result


def test_rename_variable(temp_document, lsp_client):
    """Test renaming a variable."""
    uri = temp_document(RENAME_CODE)
    
    # Rename "result" to "output"
    response = lsp_client.rename(uri, line=1, character=10, new_name="output")
    assert_response_ok(response, "rename variable")
    assert_has_result(response, "rename variable")
    
    result = response["result"]
    if result is not None:
        # Should have workspace edit
        assert "changes" in result or "documentChanges" in result
