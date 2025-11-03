"""
Test semantic tokens feature for syntax highlighting.

This tests the textDocument/semanticTokens/full LSP request to ensure
proper syntax highlighting support in editors.
"""

import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from conftest import LSPClient


def test_semantic_tokens_basic_function(lsp_client, fixtures_dir):
    """Test semantic tokens for a simple function with basic token types."""
    
    # Open a file with a simple function
    file_path = fixtures_dir / 'semantic_tokens_basic.jazz'
    uri = file_path.as_uri()
    
    # Create test file content
    content = """
// This is a comment
fn add(reg u64 a, reg u64 b) -> reg u64 {
  reg u64 result;
  result = a + b;
  return result;
}
"""
    
    file_path.write_text(content)
    
    # Open the document
    lsp_client.open_document(uri, content, language_id='jasmin')
    
    # Request semantic tokens
    req_id = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {
            'textDocument': {'uri': uri}
        }
    )
    response = lsp_client.read_response(expect_id=req_id)
    
    # Check that we got a response with token data
    assert response is not None, "Should receive semantic tokens response"
    assert 'result' in response, "Response should contain result"
    result = response['result']
    
    assert result is not None, "Result should not be null"
    assert 'data' in result, "Result should contain data array"
    
    # The data should be a list of integers encoded as:
    # [deltaLine, deltaStartChar, length, tokenType, tokenModifiers, ...]
    data = result['data']
    assert isinstance(data, list), "Data should be a list"
    assert len(data) > 0, "Data should contain tokens"
    assert len(data) % 5 == 0, "Data should be groups of 5 integers"
    
    # All values should be non-negative integers
    for value in data:
        assert isinstance(value, int), f"Token data should be integers, got {type(value)}"
        assert value >= 0, f"Token data should be non-negative, got {value}"


def test_semantic_tokens_legend(lsp_client, fixtures_dir):
    """Test that server provides semantic tokens legend in capabilities."""
    
    # Re-initialize to get capabilities (the fixture may not have stored them)
    init_response = lsp_client.initialize()
    
    assert 'result' in init_response, "Initialize response should have result"
    assert 'capabilities' in init_response['result'], "Result should have capabilities"
    
    capabilities = init_response['result']['capabilities']
    
    assert 'semanticTokensProvider' in capabilities, \
        "Server should advertise semanticTokensProvider capability"
    
    provider = capabilities['semanticTokensProvider']
    assert provider is not None, "semanticTokensProvider should not be null"
    
    # Check for legend
    assert 'legend' in provider, "Provider should include legend"
    legend = provider['legend']
    
    # Legend should have token types
    assert 'tokenTypes' in legend, "Legend should have tokenTypes"
    token_types = legend['tokenTypes']
    assert isinstance(token_types, list), "tokenTypes should be a list"
    assert len(token_types) > 0, "tokenTypes should not be empty"
    
    # Should include standard LSP token types
    expected_types = ['function', 'variable', 'parameter', 'type', 'keyword', 'comment']
    for expected in expected_types:
        assert expected in token_types, f"tokenTypes should include '{expected}'"
    
    # Legend should have token modifiers
    assert 'tokenModifiers' in legend, "Legend should have tokenModifiers"
    token_modifiers = legend['tokenModifiers']
    assert isinstance(token_modifiers, list), "tokenModifiers should be a list"
    
    # Check that full range is supported
    assert 'full' in provider, "Provider should support full document tokens"
    assert provider['full'] is True or isinstance(provider['full'], dict), \
        "Provider should indicate full token support"


def test_semantic_tokens_complex_file(lsp_client, fixtures_dir):
    """Test semantic tokens for a file with various language constructs."""
    
    file_path = fixtures_dir / 'semantic_tokens_complex.jazz'
    uri = file_path.as_uri()
    
    # Create test file with various constructs
    content = """
// Function with parameters and local variables
param int CONSTANT = 100;

fn compute(reg u64 x, reg u64 y) -> reg u64 {
  reg u64 temp;
  stack u64 buffer;
  
  // Arithmetic operations
  temp = x + y;
  temp = temp * CONSTANT;
  
  // Control flow
  if temp > 0 {
    return temp;
  } else {
    return 0;
  }
}

// Export function
export fn main() {
  reg u64 result;
  result = compute(10, 20);
}
"""
    
    file_path.write_text(content)
    
    # Open the document
    lsp_client.open_document(uri, content, language_id='jasmin')
    
    # Request semantic tokens
    req_id = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {
            'textDocument': {'uri': uri}
        }
    )
    response = lsp_client.read_response(expect_id=req_id)
    
    assert response is not None
    assert 'result' in response
    result = response['result']
    assert result is not None
    assert 'data' in result
    
    data = result['data']
    assert len(data) > 0, "Should have tokens for complex file"
    assert len(data) % 5 == 0, "Token data should be properly encoded"
    
    # With multiple lines and tokens, we should have a substantial amount of data
    # Each construct should generate at least a few tokens
    num_tokens = len(data) // 5
    assert num_tokens >= 20, f"Complex file should have at least 20 tokens, got {num_tokens}"


def test_semantic_tokens_empty_file(lsp_client, fixtures_dir):
    """Test semantic tokens for an empty file."""
    
    file_path = fixtures_dir / 'semantic_tokens_empty.jazz'
    uri = file_path.as_uri()
    content = ""
    
    file_path.write_text(content)
    lsp_client.open_document(uri, content, language_id='jasmin')
    
    # Request semantic tokens
    req_id = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {
            'textDocument': {'uri': uri}
        }
    )
    response = lsp_client.read_response(expect_id=req_id)
    
    assert response is not None
    assert 'result' in response
    result = response['result']
    
    # Empty file should return empty data or null
    if result is not None:
        assert 'data' in result
        data = result['data']
        assert isinstance(data, list)
        assert len(data) == 0, "Empty file should have no tokens"


def test_semantic_tokens_comments_only(lsp_client, fixtures_dir):
    """Test semantic tokens for a file with only comments."""
    
    file_path = fixtures_dir / 'semantic_tokens_comments.jazz'
    uri = file_path.as_uri()
    
    content = """
// This is a single line comment
// Another comment line

/* This is a multi-line
   comment block
   spanning multiple lines */
"""
    
    file_path.write_text(content)
    lsp_client.open_document(uri, content, language_id='jasmin')
    
    req_id = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {
            'textDocument': {'uri': uri}
        }
    )
    response = lsp_client.read_response(expect_id=req_id)
    
    assert response is not None
    assert 'result' in response
    result = response['result']
    assert result is not None
    assert 'data' in result
    
    data = result['data']
    # Comments should generate tokens
    if len(data) > 0:
        # If we tokenize comments, check they're properly encoded
        assert len(data) % 5 == 0
        num_tokens = len(data) // 5
        assert num_tokens >= 1, "Should have at least one comment token"


def test_semantic_tokens_keywords(lsp_client, fixtures_dir):
    """Test that keywords are properly highlighted."""
    
    file_path = fixtures_dir / 'semantic_tokens_keywords.jazz'
    uri = file_path.as_uri()
    
    # File with many keywords
    content = """
require "other.jazz"
from NS require "lib.jazz"

param int VALUE = 42;
global u64 GLOBAL_VAR;

inline fn helper() {
  reg u64 x;
  return x;
}

export fn process(stack u64 input) -> reg u64 {
  reg u64 result;
  
  if input > 0 {
    while input > 10 {
      input = input - 1;
    }
    for i = 0 to 100 {
      result = result + i;
    }
  } else {
    result = 0;
  }
  
  return result;
}
"""
    
    file_path.write_text(content)
    lsp_client.open_document(uri, content, language_id='jasmin')
    
    req_id = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {
            'textDocument': {'uri': uri}
        }
    )
    response = lsp_client.read_response(expect_id=req_id)
    
    assert response is not None
    assert 'result' in response
    result = response['result']
    assert result is not None
    assert 'data' in result
    
    data = result['data']
    assert len(data) > 0, "File with many keywords should have tokens"
    
    num_tokens = len(data) // 5
    # Keywords: require, from, param, global, inline, fn, export, return, if, else, while, for, to
    # Plus identifiers, types, operators...
    assert num_tokens >= 15, f"Should have many tokens for keyword-heavy file, got {num_tokens}"


def test_semantic_tokens_incremental_updates(lsp_client, fixtures_dir):
    """Test that semantic tokens update correctly after document changes."""
    
    file_path = fixtures_dir / 'semantic_tokens_update.jazz'
    uri = file_path.as_uri()
    
    # Initial content
    initial_content = """
fn original() {
  return 0;
}
"""
    
    file_path.write_text(initial_content)
    lsp_client.open_document(uri, initial_content, language_id='jasmin')
    
    # Get initial tokens
    req_id1 = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {'textDocument': {'uri': uri}}
    )
    response1 = lsp_client.read_response(expect_id=req_id1)
    assert response1 is not None
    data1 = response1['result']['data']
    initial_token_count = len(data1) // 5
    
    # Update document with more content
    updated_content = """
fn original() {
  return 0;
}

fn new_function(reg u64 param1, reg u64 param2) -> reg u64 {
  reg u64 local_var;
  local_var = param1 + param2;
  return local_var;
}
"""
    
    lsp_client.change_document(uri, updated_content, 2)
    
    # Get updated tokens
    req_id2 = lsp_client.send_request(
        'textDocument/semanticTokens/full',
        {'textDocument': {'uri': uri}}
    )
    response2 = lsp_client.read_response(expect_id=req_id2)
    assert response2 is not None
    data2 = response2['result']['data']
    updated_token_count = len(data2) // 5
    
    # After adding more code, should have more tokens
    assert updated_token_count > initial_token_count, \
        f"Updated file should have more tokens: {updated_token_count} vs {initial_token_count}"
