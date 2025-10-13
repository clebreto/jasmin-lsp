#!/usr/bin/env python3
"""
Test namespace-based require navigation as a proper pytest test.
"""

import json
import subprocess
import os
import tempfile
import pytest


def parse_lsp_messages(output):
    """Parse LSP messages from output"""
    messages = []
    remaining = output
    
    while 'Content-Length:' in remaining:
        try:
            # Find Content-Length header
            cl_idx = remaining.index('Content-Length:')
            remaining = remaining[cl_idx:]
            header_end = remaining.index('\n\n')
            
            # Extract content length
            header = remaining[:header_end]
            length = int(header.split(':')[1].strip())
            
            # Extract JSON content
            body_start = header_end + 2
            body = remaining[body_start:body_start + length]
            
            try:
                message = json.loads(body)
                messages.append(message)
            except json.JSONDecodeError:
                pass
            
            # Move to next message
            remaining = remaining[body_start + length:]
        except (ValueError, IndexError):
            break
    
    return messages


def send_goto_definition_request(server_path, main_uri, workspace_uri, main_content, line, char):
    """Send a goto definition request and return the response"""
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
         'params': {'processId': None, 'rootUri': workspace_uri, 'capabilities': {}}},
        {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
        {'jsonrpc': '2.0', 'method': 'textDocument/didOpen',
         'params': {'textDocument': {'uri': main_uri, 'languageId': 'jasmin', 'version': 1, 'text': main_content}}},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition',
         'params': {'textDocument': {'uri': main_uri}, 'position': {'line': line, 'character': char}}}
    ]
    
    # Send to LSP server
    input_data = ''.join(f'Content-Length: {len(json.dumps(m))}\n\n{json.dumps(m)}' for m in messages)
    
    proc = subprocess.Popen([server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(input=input_data, timeout=15)
    
    # Parse messages
    response_messages = parse_lsp_messages(stdout)
    
    # Look for definition response
    for msg in response_messages:
        if msg.get('id') == 2:
            return msg
    
    return None


def test_namespace_require_navigation(lsp_server_path):
    """Test that namespace-based require statements can be navigated correctly"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Common directory and reduce.jinc
        common_dir = os.path.join(tmpdir, 'Common')
        os.makedirs(common_dir)
        
        reduce_file = os.path.join(common_dir, 'reduce.jinc')
        with open(reduce_file, 'w') as f:
            f.write("""// Common library for reduction operations
fn reduce_sum(reg u64 array_ptr, reg u32 length) -> reg u64 {
  return #0;
}""")
        
        # Test content with namespace require
        main_content = """// Test namespace navigation
from Common require "reduce.jinc"

fn test() -> reg u64 {
  return reduce_sum(#0, #0);
}"""
        
        main_file = os.path.join(tmpdir, 'test.jazz')
        with open(main_file, 'w') as f:
            f.write(main_content)
        
        main_uri = f"file://{main_file}"
        workspace_uri = f"file://{tmpdir}"
        expected_target_uri = f"file://{reduce_file}"
        
        # Test clicking on different parts of the filename in the require statement
        require_line = 1  # Zero-indexed line with "from Common require "reduce.jinc""
        
        # Find positions within "reduce.jinc"
        lines = main_content.split('\n')
        require_text = lines[require_line]
        filename_start = require_text.index('reduce.jinc')
        
        test_positions = [
            (filename_start + 1, "Start of filename"),
            (filename_start + 6, "Middle of filename"),
            (filename_start + 10, "End of filename")
        ]
        
        for char_pos, description in test_positions:
            response = send_goto_definition_request(
                lsp_server_path, main_uri, workspace_uri, main_content, require_line, char_pos
            )
            
            assert response is not None, f"No response for {description}"
            assert 'result' in response, f"No result in response for {description}"
            assert response['result'], f"Empty result for {description}"
            
            result_uri = response['result'][0]['uri']
            assert result_uri == expected_target_uri, f"Wrong target for {description}: expected {expected_target_uri}, got {result_uri}"


def test_namespace_require_navigation_negative_case(lsp_server_path):
    """Test that clicking outside require statements doesn't navigate"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Common directory and reduce.jinc
        common_dir = os.path.join(tmpdir, 'Common')
        os.makedirs(common_dir)
        
        reduce_file = os.path.join(common_dir, 'reduce.jinc')
        with open(reduce_file, 'w') as f:
            f.write('fn reduce_sum() { }')
        
        main_content = """// Test namespace navigation
from Common require "reduce.jinc"

fn test() -> reg u64 {
  return #0;
}"""
        
        main_file = os.path.join(tmpdir, 'test.jazz')
        with open(main_file, 'w') as f:
            f.write(main_content)
        
        main_uri = f"file://{main_file}"
        workspace_uri = f"file://{tmpdir}"
        
        # Test clicking in function body (should not navigate to require target)
        response = send_goto_definition_request(
            lsp_server_path, main_uri, workspace_uri, main_content, 4, 10  # Inside function body
        )
        
        # Response might be None (no definition found) or might point to something else, 
        # but it should NOT point to reduce.jinc
        if response and 'result' in response and response['result']:
            result_uri = response['result'][0]['uri']
            reduce_uri = f"file://{reduce_file}"
            assert result_uri != reduce_uri, f"Unexpected navigation to require target from non-require position"