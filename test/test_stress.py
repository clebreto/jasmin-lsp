#!/usr/bin/env python3
"""
Extended stress test for jasmin-lsp server.
Simulates heavier real-world workloads.
"""

import subprocess
import json
import time
import threading
import os
import sys

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def test_extreme_rapid_changes():
    """Test with 50 documents changing rapidly"""
    print("\n" + "="*60)
    print("STRESS TEST: Extreme Rapid Changes (50 documents)")
    print("="*60)
    
    proc = subprocess.Popen(
        [SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    
    def send(msg):
        msg_str = json.dumps(msg)
        content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
        proc.stdin.write(content.encode('utf-8'))
        proc.stdin.flush()
    
    try:
        # Initialize
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", 
              "params": {"processId": os.getpid(), "rootUri": f"file://{os.getcwd()}", "capabilities": {}}})
        time.sleep(0.5)
        send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.5)
        
        # Create 50 documents with rapid changes
        for i in range(50):
            uri = f"file:///tmp/stress{i}.jazz"
            
            # Open
            send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
                "textDocument": {"uri": uri, "languageId": "jasmin", "version": 1, "text": f"fn func{i}() {{ }}"}
            }})
            
            # Rapid changes
            for v in range(2, 10):
                send({"jsonrpc": "2.0", "method": "textDocument/didChange", "params": {
                    "textDocument": {"uri": uri, "version": v},
                    "contentChanges": [{"text": f"fn func{i}_v{v}() {{ }}"}]
                }})
            
            # Close
            send({"jsonrpc": "2.0", "method": "textDocument/didClose", "params": {
                "textDocument": {"uri": uri}
            }})
            
            if i % 10 == 0:
                print(f"  Progress: {i}/50 documents")
                time.sleep(0.1)
                if proc.poll() is not None:
                    print(f"✗ CRASH at document {i}!")
                    return False
        
        time.sleep(1.0)
        if proc.poll() is None:
            print("✓ PASSED: Server handled 50 documents with 450 changes!")
            proc.terminate()
            return True
        else:
            print("✗ FAILED: Server crashed")
            return False
            
    finally:
        try:
            proc.kill()
        except:
            pass

def test_long_running_session():
    """Test server stability over extended period"""
    print("\n" + "="*60)
    print("STRESS TEST: Long Running Session (3 minutes)")
    print("="*60)
    
    proc = subprocess.Popen(
        [SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    
    def send(msg):
        msg_str = json.dumps(msg)
        content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
        try:
            proc.stdin.write(content.encode('utf-8'))
            proc.stdin.flush()
            return True
        except:
            return False
    
    try:
        # Initialize
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", 
              "params": {"processId": os.getpid(), "rootUri": f"file://{os.getcwd()}", "capabilities": {}}})
        time.sleep(0.5)
        send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.5)
        
        start = time.time()
        duration = 180  # 3 minutes
        iteration = 0
        
        while time.time() - start < duration:
            if proc.poll() is not None:
                elapsed = time.time() - start
                print(f"✗ FAILED: Server crashed after {elapsed:.1f} seconds")
                return False
            
            # Simulate typical usage
            uri = f"file:///tmp/session_{iteration % 10}.jazz"
            
            # Open
            if not send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
                "textDocument": {"uri": uri, "languageId": "jasmin", "version": 1, "text": f"fn session{iteration}() {{ }}"}
            }}):
                print("✗ FAILED: Could not send message")
                return False
            
            time.sleep(0.1)
            
            # Change
            if not send({"jsonrpc": "2.0", "method": "textDocument/didChange", "params": {
                "textDocument": {"uri": uri, "version": 2},
                "contentChanges": [{"text": f"fn session{iteration}_v2() {{ }}"}]
            }}):
                print("✗ FAILED: Could not send message")
                return False
            
            time.sleep(0.1)
            
            # Request hover
            if not send({"jsonrpc": "2.0", "id": iteration + 100, "method": "textDocument/hover", "params": {
                "textDocument": {"uri": uri},
                "position": {"line": 0, "character": 3}
            }}):
                print("✗ FAILED: Could not send message")
                return False
            
            time.sleep(0.1)
            
            # Close
            if not send({"jsonrpc": "2.0", "method": "textDocument/didClose", "params": {
                "textDocument": {"uri": uri}
            }}):
                print("✗ FAILED: Could not send message")
                return False
            
            iteration += 1
            
            if iteration % 50 == 0:
                elapsed = time.time() - start
                print(f"  {iteration} iterations, {elapsed:.1f}s elapsed, server still running...")
        
        if proc.poll() is None:
            print(f"✓ PASSED: Server ran for {duration} seconds with {iteration} iterations!")
            proc.terminate()
            return True
        else:
            print("✗ FAILED: Server crashed")
            return False
            
    finally:
        try:
            proc.kill()
        except:
            pass

def main():
    if not os.path.exists(SERVER):
        print(f"ERROR: Server executable not found at {SERVER}")
        return 1
    
    results = []
    
    print("\n" + "="*60)
    print("EXTENDED STRESS TESTING")
    print("="*60)
    
    results.append(("Extreme Rapid Changes", test_extreme_rapid_changes()))
    results.append(("Long Running Session", test_long_running_session()))
    
    print("\n" + "="*60)
    print("STRESS TEST RESULTS")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("="*60)
    if all_passed:
        print("ALL STRESS TESTS PASSED! 🎉")
        return 0
    else:
        print("SOME STRESS TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
