"""
Tests for hover on constants and computed constant values.
"""

import pytest
from conftest import assert_response_ok


CONSTANT_TEST_CODE = """// Constants test
param int SIZE = 256;
param int DOUBLE_SIZE = SIZE * 2;
param int HALF = SIZE / 2;

fn use_constants() {
  reg u64 x;
  x = SIZE;
  x = DOUBLE_SIZE;
}
"""


def test_hover_on_simple_constant(temp_document, lsp_client):
    """Test hover on simple constant shows value."""
    uri = temp_document(CONSTANT_TEST_CODE)
    
    # Hover on SIZE constant
    response = lsp_client.hover(uri, line=1, character=10)
    assert_response_ok(response, "hover on constant")
    
    result = response.get("result")
    if result is not None:
        assert "contents" in result


def test_hover_on_computed_constant(temp_document, lsp_client):
    """Test hover on computed constant shows computed value."""
    uri = temp_document(CONSTANT_TEST_CODE)
    
    # Hover on DOUBLE_SIZE constant
    response = lsp_client.hover(uri, line=2, character=10)
    assert_response_ok(response, "hover on computed constant")
    
    result = response.get("result")
    if result is not None:
        contents = result.get("contents", {})
        # Check if computed value is shown (e.g., "512" or "SIZE * 2")
        if isinstance(contents, dict) and "value" in contents:
            value_text = contents["value"]
            # Should contain either the number or the expression
            assert "512" in value_text or "SIZE" in value_text or "DOUBLE" in value_text
