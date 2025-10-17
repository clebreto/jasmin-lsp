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
    
    # Set as master file
    lsp_client.set_master_file(uri)
    
    # Wait a bit for diagnostics to be computed
    time.sleep(0.2)
    
    # Collect diagnostics
    diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    
    # Clean code should have no diagnostics
    assert uri in diagnostics, "Should receive diagnostics for the file"
    assert len(diagnostics[uri]) == 0, f"Clean code should have no errors, got {len(diagnostics[uri])}"
    assert lsp_client.is_alive(), "Server should still be alive"


def test_syntax_errors_generate_diagnostics(temp_document, lsp_client):
    """Test that syntax errors generate diagnostics."""
    uri = temp_document(SYNTAX_ERROR_CODE)
    
    # Set as master file
    lsp_client.set_master_file(uri)
    
    # Wait for diagnostics to be computed and sent
    time.sleep(0.2)
    
    # Collect diagnostics
    diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    
    # Syntax errors should generate diagnostics
    assert uri in diagnostics, "Should receive diagnostics for the file"
    assert len(diagnostics[uri]) > 0, "Syntax errors should generate diagnostics"
    assert lsp_client.is_alive(), "Server should handle syntax errors gracefully"


def test_document_change_updates_diagnostics(temp_document, lsp_client):
    """Test that changing a document updates diagnostics."""
    uri = temp_document(CLEAN_CODE)
    
    # Set as master file
    lsp_client.set_master_file(uri)
    time.sleep(0.1)
    
    # Check initial diagnostics (should be clean)
    initial_diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    assert uri in initial_diagnostics, "Should receive initial diagnostics"
    assert len(initial_diagnostics[uri]) == 0, "Initial code should have no errors"
    
    # Introduce a syntax error
    lsp_client.change_document(uri, SYNTAX_ERROR_CODE, version=2)
    time.sleep(0.2)
    
    # Check diagnostics after introducing error
    error_diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    assert uri in error_diagnostics, "Should receive diagnostics after change"
    assert len(error_diagnostics[uri]) > 0, "Should have errors after introducing syntax error"
    assert lsp_client.is_alive(), "Server should handle document changes"
    
    # Fix the syntax error
    lsp_client.change_document(uri, CLEAN_CODE, version=3)
    time.sleep(0.2)
    
    # Check diagnostics after fix
    fixed_diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    assert uri in fixed_diagnostics, "Should receive diagnostics after fix"
    assert len(fixed_diagnostics[uri]) == 0, "Should have no errors after fix"
    assert lsp_client.is_alive(), "Server should update diagnostics on fix"


def test_multiple_files_diagnostics(temp_document, lsp_client):
    """Test diagnostics for multiple files."""
    uri1 = temp_document(CLEAN_CODE, "file1.jazz")
    
    # Set first file as master
    lsp_client.set_master_file(uri1)
    time.sleep(0.1)
    
    uri2 = temp_document(SYNTAX_ERROR_CODE, "file2.jazz")
    time.sleep(0.2)
    
    # Collect diagnostics
    diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    
    # Both files should be handled
    assert lsp_client.is_alive(), "Server should handle multiple files"
    
    # First file should have no errors
    assert uri1 in diagnostics, "Should receive diagnostics for first file"
    assert len(diagnostics[uri1]) == 0, "First file should have no errors"
    
    # Second file should have errors
    assert uri2 in diagnostics, "Should receive diagnostics for second file"
    assert len(diagnostics[uri2]) > 0, "Second file should have syntax errors"


def test_array_index_with_cast_syntax_error(temp_document, lsp_client):
    """Test that (uint) cast operator works correctly.
    
    According to Jasmin documentation on wint conversion:
    'Conversion to int is safe and performed through the prefix (int) operator 
    or its more specific variants (sint) and (uint).'
    
    This test verifies that (uint) is recognized as a valid cast operator.
    However, RC[(uint) c] may still have syntax errors depending on the context.
    We test the cast operator in a straightforward assignment.
    """
    code_with_uint_cast = """fn test_cast(reg u64 c) -> reg u64 {
  reg u64 result;
  result = (uint) c;
  return result;
}
"""
    uri = temp_document(code_with_uint_cast)
    
    # Set as master file
    lsp_client.set_master_file(uri)
    
    # Wait for diagnostics to be computed
    time.sleep(0.2)
    
    # Collect diagnostics
    diagnostics = lsp_client.collect_diagnostics(timeout=0.5)
    
    # Valid (uint) cast syntax should produce no diagnostics
    assert lsp_client.is_alive(), "Server should handle valid (uint) cast syntax"
    assert uri in diagnostics, "Should receive diagnostics for the file"
    
    # Check if there are any errors and print them for debugging
    if len(diagnostics[uri]) > 0:
        print(f"\nDiagnostics found: {diagnostics[uri]}")
    
    assert len(diagnostics[uri]) == 0, f"Valid (uint) cast should have no errors, got {len(diagnostics[uri])} errors"
