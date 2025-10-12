"""
Tests for find references functionality.
"""

import pytest
from conftest import assert_response_ok, assert_has_result


REFERENCES_CODE = """fn helper(reg u64 x) -> reg u64 {
  return x + 1;
}

fn main() {
  reg u64 a;
  reg u64 b;
  a = helper(5);
  b = helper(10);
  return a + b;
}
"""


def test_find_references_function(temp_document, lsp_client):
    """Test finding all references to a function."""
    uri = temp_document(REFERENCES_CODE)
    
    # Find references to "helper" function (position at definition, line 0)
    response = lsp_client.references(uri, line=0, character=3, include_declaration=True)
    assert_response_ok(response, "find references")
    assert_has_result(response, "find references")
    
    result = response["result"]
    assert result is not None, "Should find references"
    assert isinstance(result, list), "References should be array"
    
    # Should find: definition + 2 calls = 3 total (or just 2 if not including declaration)
    assert len(result) >= 2, f"Should find at least 2 references, found {len(result)}"


def test_find_references_exclude_declaration(temp_document, lsp_client):
    """Test finding references excluding the declaration."""
    uri = temp_document(REFERENCES_CODE)
    
    # Find references to "helper" excluding declaration
    response = lsp_client.references(uri, line=0, character=3, include_declaration=False)
    assert_response_ok(response, "find references")
    assert_has_result(response, "find references")
    
    result = response["result"]
    if result is not None and isinstance(result, list):
        # Should find only the 2 calls (not the definition)
        assert len(result) >= 1, "Should find at least the call sites"


def test_find_references_variable(temp_document, lsp_client):
    """Test finding all references to a variable."""
    uri = temp_document(REFERENCES_CODE)
    
    # Find references to variable "a" (declared at line 5)
    response = lsp_client.references(uri, line=5, character=10, include_declaration=True)
    assert_response_ok(response, "find references to variable")
    assert_has_result(response, "find references to variable")
    
    result = response["result"]
    if result is not None:
        assert isinstance(result, list)
        # Should find: declaration + assignment + usage in return = 3
        assert len(result) >= 2, f"Should find at least 2 references, found {len(result)}"


def test_find_references_no_references(temp_document, lsp_client):
    """Test finding references to something with no references."""
    code = """fn unused_function() {
  return 42;
}

fn main() {
  return 0;
}
"""
    uri = temp_document(code)
    
    # Find references to "unused_function"
    response = lsp_client.references(uri, line=0, character=3, include_declaration=False)
    assert_response_ok(response, "find references")
    assert_has_result(response, "find references")
    
    result = response["result"]
    # Should return empty array or null
    if result is not None:
        assert isinstance(result, list)
        assert len(result) == 0, "Unused function should have no references"
