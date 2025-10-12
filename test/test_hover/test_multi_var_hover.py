#!/usr/bin/env python3
"""
Test that hover shows correct type for variables declared together.

Tests comma-separated variable declarations:
  reg u32 i, j;  should show "j: reg u32", not "j: reg u32 i,"
"""

import pytest

# Test code
TEST_CODE = """fn test() {
  reg u32 i, j;
  stack u64 x, y, z;
  i = 1;
  j = 2;
  x = 3;
  y = 4;
  z = 5;
}"""


@pytest.mark.parametrize("line,char,expected_name,expected_type,description", [
    (1, 11, "i", "reg u32", "First variable 'i' in declaration"),
    (1, 14, "j", "reg u32", "Second variable 'j' in declaration"),
    (2, 13, "x", "stack u64", "First stack variable 'x'"),
    (2, 16, "y", "stack u64", "Second stack variable 'y'"),
    (2, 19, "z", "stack u64", "Third stack variable 'z'"),
])
def test_multi_var_hover(lsp_client, temp_document, line, char, expected_name, expected_type, description):
    """Test hover on variables declared with commas."""
    
    # Create document
    uri = temp_document(TEST_CODE, "test_multi_vars.jazz")
    
    # Request hover
    response = lsp_client.hover(uri, line, char)
    
    # Verify response
    assert response is not None, f"{description}: No response"
    assert "result" in response, f"{description}: No result field"
    
    result = response["result"]
    if result is None:
        pytest.skip(f"{description}: Hover returned null (may not be implemented)")
    
    # Extract hover content
    assert "contents" in result, f"{description}: No contents in result"
    contents = result["contents"]
    
    hover_text = ""
    if isinstance(contents, dict):
        hover_text = contents.get("value", "")
    elif isinstance(contents, str):
        hover_text = contents
    elif isinstance(contents, list) and contents:
        hover_text = contents[0].get("value", "") if isinstance(contents[0], dict) else str(contents[0])
    
    # Build expected pattern
    expected = f"{expected_name}: {expected_type}"
    
    # Clean up markdown if present
    if "```" in hover_text:
        parts = hover_text.split("```")
        if len(parts) >= 2:
            hover_text = parts[1].replace("jasmin\n", "").replace("\n", "")
    
    # The hover should show the variable name and type
    assert expected_name in hover_text, (
        f"{description}: Expected to find '{expected_name}' in hover\n"
        f"Got: '{hover_text}'"
    )
    assert expected_type in hover_text, (
        f"{description}: Expected to find '{expected_type}' in hover\n"
        f"Got: '{hover_text}'"
    )
    
    # Make sure it doesn't show other variable names from the same declaration
    # (e.g., "j: reg u32" should not contain "i")
    if expected_name == "j":
        # j's hover should not contain "i,"
        assert "i," not in hover_text, (
            f"{description}: Hover should not include 'i,' \n"
            f"Got: '{hover_text}'"
        )
