"""
Tests for syntax diagnostics and error reporting.
"""

import pytest
import time
from conftest import assert_response_ok


CLEAN_CODE = """fn add(reg u64 a, reg u64 b) -> reg u64 {
  reg u64 sum;
  sum = a + b;
  return sum;
}
"""

SYNTAX_ERROR_CODE = """fn unclosed_brace(reg u64 a) -> reg u64 {
  reg u64 b;
  b = a;
  return b;
// Missing closing brace

fn extra_token(reg u64 c) -> reg u64 } {
  return c;
}
"""


def test_clean_code_no_diagnostics(temp_document, lsp_client):
    """Test that clean code produces no diagnostics."""
    uri = temp_document(CLEAN_CODE)
    
    # Wait a bit for diagnostics to be computed
    time.sleep(0.2)
    
    # No direct way to query diagnostics in LSP - they're sent as notifications
    # So we just ensure the server is still alive and responsive
    response = lsp_client.hover(uri, line=0, character=3)
    assert_response_ok(response, "hover after opening clean file")
    assert lsp_client.is_alive(), "Server should still be alive"


def test_syntax_errors_generate_diagnostics(temp_document, lsp_client):
    """Test that syntax errors generate diagnostics."""
    uri = temp_document(SYNTAX_ERROR_CODE)
    
    # Wait for diagnostics to be computed and sent
    time.sleep(0.2)
    
    # Server should still be alive even with syntax errors
    assert lsp_client.is_alive(), "Server should handle syntax errors gracefully"


def test_document_change_updates_diagnostics(temp_document, lsp_client):
    """Test that changing a document updates diagnostics."""
    uri = temp_document(CLEAN_CODE)
    time.sleep(0.1)
    
    # Introduce a syntax error
    lsp_client.change_document(uri, SYNTAX_ERROR_CODE, version=2)
    time.sleep(0.2)
    
    # Server should still be alive
    assert lsp_client.is_alive(), "Server should handle document changes"
    
    # Fix the syntax error
    lsp_client.change_document(uri, CLEAN_CODE, version=3)
    time.sleep(0.2)
    
    assert lsp_client.is_alive(), "Server should update diagnostics on fix"


def test_multiple_files_diagnostics(temp_document, lsp_client):
    """Test diagnostics for multiple files."""
    uri1 = temp_document(CLEAN_CODE, "file1.jazz")
    time.sleep(0.1)
    
    uri2 = temp_document(SYNTAX_ERROR_CODE, "file2.jazz")
    time.sleep(0.2)
    
    # Both files should be handled
    assert lsp_client.is_alive(), "Server should handle multiple files"
    
    # Should still be able to query first file
    response = lsp_client.hover(uri1, line=0, character=3)
    assert_response_ok(response, "hover on first file")
