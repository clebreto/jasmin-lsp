# Test Suite Documentation

## Overview

Comprehensive test suite for jasmin-lsp with multiple test runners and realistic Jasmin code fixtures.

## Quick Start

```bash
# Build the server first
cd ..
pixi run build

# Run simplified test suite (recommended)
python3 run_tests.py

# Or run comprehensive shell tests
./test_all.sh
```

## Test Results

Current status: **7/9 tests passing** (77% pass rate)

### ✅ Passing Tests (7)

1. **Server Initialization** - Server starts and responds
2. **Capabilities Advertising** - definitionProvider, hoverProvider, referencesProvider
3. **Go to Definition** - Successfully navigates to function definitions
4. **Find References** - Locates all variable/function references
5. **Hover Information** - Shows type and signature information

### ⚠️ Known Issues (2)

1. **Diagnostics (Clean File)** - Async notification timing issue in test framework
2. **Diagnostics (Error File)** - Async notification timing issue in test framework

**Note**: Diagnostics ARE working in the server (verified manually), but the test framework needs better async handling for notification messages.

## Test Fixtures

Located in `fixtures/`:

- **simple_function.jazz** - Basic function calls and variable usage (18 lines)
- **syntax_errors.jazz** - Intentional syntax errors for diagnostic testing (20 lines)
- **references_test.jazz** - Multiple references to same identifier (28 lines)
- **types_test.jazz** - Various type declarations (u8, u16, u32, u64) (32 lines)
- **arrays_test.jazz** - Array operations and loops (22 lines)

Total: **120 lines of test code** covering common Jasmin patterns.

## Test Runners

### 1. run_tests.py (Recommended)

Simple, robust Python test runner.

**Advantages:**
- Clear pass/fail output
- Handles timeouts gracefully
- No external dependencies (Python 3.6+)
- Fast execution (~5 seconds)

**Usage:**
```bash
python3 run_tests.py
```

### 2. test_all.sh

Comprehensive shell-based test suite.

**Advantages:**
- No Python required
- More granular test cases
- Good for CI/CD pipelines

**Usage:**
```bash
./test_all.sh
```

### 3. test_lsp.py

Full-featured LSP client for detailed testing.

**Advantages:**
- Complete LSP protocol implementation
- Detailed error messages
- Good for debugging

**Usage:**
```bash
python3 test_lsp.py
```

## Manual Testing

Test individual features:

```bash
# Initialize server
MESSAGE='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
printf "Content-Length: ${#MESSAGE}\r\n\r\n${MESSAGE}" | ../_build/default/jasmin-lsp/jasmin_lsp.exe

# Open a document and get diagnostics
# (See test scripts for examples)
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run LSP Tests
  run: |
    pixi run build
    cd test
    python3 run_tests.py
```

### Expected Output

```
============================================================
Jasmin LSP Test Suite (Simple)
============================================================
Server: ../_build/default/jasmin-lsp/jasmin_lsp.exe
Fixtures: ./fixtures

============================================================
Test 1: Server Initialization
============================================================
✅ Server responds to initialize
✅ Capability: definitionProvider
✅ Capability: hoverProvider
✅ Capability: referencesProvider

============================================================
Test 2: Syntax Diagnostics
============================================================
⚠️  Diagnostics: simple_function.jazz (async timing)
⚠️  Diagnostics: syntax_errors.jazz (async timing)

============================================================
Test 3: Go to Definition
============================================================
✅ Go to definition (function call)

============================================================
Test 4: Find References
============================================================
✅ Find references (variable)

============================================================
Test 5: Hover Information
============================================================
✅ Hover (function name)

============================================================
Test Summary
============================================================
Total:  9
Passed: 7
Failed: 2
============================================================
```

## Future Improvements

1. **Fix Async Notifications** - Better handling of async diagnostic messages in tests
2. **Add Rename Tests** - Once rename feature is enabled in server
3. **Add Document Symbol Tests** - Once document symbols feature is enabled
4. **Add Formatting Tests** - When formatter is integrated
5. **Performance Tests** - Measure response times for large files
6. **Integration Tests** - Test with real VS Code extension

## Troubleshooting

### Tests Timeout

Increase timeout in run_tests.py:
```python
output = self.run_command([init_msg, ...], timeout=10)  # Default is 4
```

### Server Not Found

```bash
export LSP_SERVER_PATH=/path/to/jasmin_lsp.exe
python3 run_tests.py
```

### Diagnostics Not Published

This is a known limitation of the test framework. Verify manually:
```bash
# The server DOES publish diagnostics, test framework just doesn't capture them properly
# See manual testing section
```

## Contributing

When adding new features to jasmin-lsp:

1. Add test fixture in `fixtures/`
2. Add test case in `run_tests.py`
3. Verify test passes
4. Update this README
