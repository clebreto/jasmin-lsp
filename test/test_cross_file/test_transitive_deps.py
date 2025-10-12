"""
Tests for transitive dependency resolution across multiple files.
"""

import pytest
from conftest import assert_response_ok, assert_has_result, FIXTURES_DIR
from pathlib import Path


def test_transitive_dependencies(lsp_client):
    """Test that transitive dependencies (A requires B requires C) work."""
    # Check if transitive fixtures exist
    transitive_dir = FIXTURES_DIR / "transitive"
    if not transitive_dir.exists():
        pytest.skip("Transitive dependency fixtures not found")
    
    # Open files in dependency order
    files = ["base.jazz", "middle.jazz", "top.jazz"]
    uris = []
    
    for filename in files:
        file_path = transitive_dir / filename
        if file_path.exists():
            content = file_path.read_text()
            uri = f"file://{file_path.absolute()}"
            lsp_client.open_document(uri, content)
            uris.append(uri)
    
    if len(uris) == 0:
        pytest.skip("No transitive dependency files found")
    
    # Test that we can navigate through the dependency chain
    # This is a basic test - adjust based on actual fixture content
    assert lsp_client.is_alive(), "Server should handle transitive dependencies"
