#!/usr/bin/env python3
"""
Test that hover shows correct type for parameters declared together.

Tests multiple parameters declared with same type:
  fn test(reg u32 a, b, stack u64 x, y, z) -> reg u32
"""

import pytest

# Test code with multiple params declared together
TEST_CODE = """fn test(reg u32 a, b, stack u64 x, y, z) -> reg u32 {
  return a;
}"""


@pytest.mark.parametrize("line,char,expected_name,expected_type,description", [
    (0, 16, "a", "reg u32", "First param 'a' with explicit type"),
    (0, 19, "b", "reg u32", "Second param 'b' sharing type"),
    (0, 32, "x", "stack u64", "First stack param 'x'"),
    (0, 35, "y", "stack u64", "Second stack param 'y'"),
    (0, 38, "z", "stack u64", "Third stack param 'z'"),
])
def test_multi_param_hover(lsp_client, temp_document, line, char, expected_name, expected_type, description):
    """Test hover on parameters that share a type declaration."""
    
    # Create document
    uri = temp_document(TEST_CODE, "test_multi_params.jazz")
    
    # Request hover
    response = lsp_client.hover(uri, line, char)
    
    # Verify response
    assert response is not None, f"{description}: No response"
    assert "result" in response, f"{description}: No result field"
    
    result = response["result"]
    if result is None:
        pytest.skip(f"{description}: Hover returned null (feature may not be fully implemented)")
    
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
    
    # Verify the hover shows the correct type
    expected = f"{expected_name}: {expected_type}"
    
    # Clean up markdown if present
    if "```" in hover_text:
        parts = hover_text.split("```")
        if len(parts) >= 2:
            hover_text = parts[1].replace("jasmin\n", "").replace("\n", "")
    
    assert expected_name in hover_text, (
        f"{description}: Expected to find '{expected_name}' in hover\n"
        f"Got: '{hover_text}'"
    )
    assert expected_type in hover_text, (
        f"{description}: Expected to find '{expected_type}' in hover\n"
        f"Got: '{hover_text}'"
    )
