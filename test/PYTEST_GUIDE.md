# Jasmin LSP Test Suite - Pytest Architecture

## Overview

The jasmin-lsp test suite has been completely reorganized to use **pytest** as the test runner, with tests organized into logical categories for easy navigation and execution.

## Architecture

### Test Structure

```
test/
├── conftest.py              # Shared fixtures and utilities
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Python dependencies
├── fixtures/                # Test fixture files (*.jazz)
│   ├── simple_function.jazz
│   ├── types_test.jazz
│   ├── math_lib.jazz
│   ├── main_program.jazz
│   └── ...
├── test_hover/              # Hover functionality tests
│   ├── __init__.py
│   ├── test_keyword_hover.py
│   ├── test_basic_hover.py
│   └── test_constant_hover.py
├── test_navigation/         # Navigation tests (goto, references)
│   ├── __init__.py
│   ├── test_goto_definition.py
│   └── test_find_references.py
├── test_diagnostics/        # Diagnostics and error reporting
│   ├── __init__.py
│   └── test_syntax_errors.py
├── test_cross_file/         # Cross-file features
│   ├── __init__.py
│   ├── test_require_statements.py
│   └── test_transitive_deps.py
├── test_performance/        # Performance and stress tests
│   ├── __init__.py
│   └── test_stress.py
├── test_crash/              # Crash and robustness tests
│   ├── __init__.py
│   └── test_robustness.py
├── test_symbols/            # Symbol-related features
│   ├── __init__.py
│   ├── test_document_symbols.py
│   └── test_rename.py
└── test_master_file/        # Master file functionality
    ├── __init__.py
    └── test_master_file.py
```

## Installation

### Prerequisites

1. **Build the LSP server** (required):
   ```bash
   cd /path/to/jasmin-lsp
   pixi run build
   ```

2. **Install Python dependencies** (optional but recommended):
   ```bash
   cd test
   pip install -r requirements.txt
   ```

   The test suite uses only Python standard library, but the requirements.txt provides optional enhancements:
   - `pytest-timeout`: Timeout support for slow tests
   - `pytest-cov`: Coverage reporting
   - `pytest-xdist`: Parallel test execution
   - `pytest-sugar`: Better output formatting
   - `pytest-html`: HTML test reports

## Running Tests

### Run All Tests

```bash
cd test
pytest
```

This discovers and runs all tests in all categories.

### Run Tests by Category

```bash
# Hover tests only
pytest test_hover/

# Navigation tests only
pytest test_navigation/

# Diagnostics tests
pytest test_diagnostics/

# Cross-file tests
pytest test_cross_file/

# Performance tests
pytest test_performance/

# Crash/robustness tests
pytest test_crash/

# Symbol tests
pytest test_symbols/

# Master file tests
pytest test_master_file/
```

### Run a Specific Test File

```bash
pytest test_hover/test_keyword_hover.py
```

### Run a Specific Test Function

```bash
pytest test_hover/test_keyword_hover.py::test_hover_on_function_name
```

### Run Tests Matching a Pattern

```bash
# Run all tests with "hover" in the name
pytest -k hover

# Run all tests with "goto" or "definition"
pytest -k "goto or definition"

# Exclude slow tests
pytest -m "not slow"
```

### Run Tests in Parallel (faster)

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4
```

### Generate Coverage Report

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Generate HTML Test Report

```bash
pytest --html=report.html --self-contained-html
```

## Test Categories Explained

### 1. Hover Tests (`test_hover/`)

Tests for hover functionality showing type information and documentation.

**Tests:**
- `test_keyword_hover.py` - Hovering on keywords vs symbols
- `test_basic_hover.py` - Basic hover on functions, variables, parameters
- `test_constant_hover.py` - Hover on constants and computed values

**Example:**
```bash
pytest test_hover/ -v
```

### 2. Navigation Tests (`test_navigation/`)

Tests for go-to-definition and find-references functionality.

**Tests:**
- `test_goto_definition.py` - Jump to definitions
- `test_find_references.py` - Find all references to symbols

**Example:**
```bash
pytest test_navigation/test_goto_definition.py
```

### 3. Diagnostics Tests (`test_diagnostics/`)

Tests for syntax error detection and diagnostic reporting.

**Tests:**
- `test_syntax_errors.py` - Syntax error detection and updates

**Example:**
```bash
pytest test_diagnostics/ -v
```

### 4. Cross-File Tests (`test_cross_file/`)

Tests for cross-file features using `require` statements.

**Tests:**
- `test_require_statements.py` - Navigation across files
- `test_transitive_deps.py` - Transitive dependency resolution

**Example:**
```bash
pytest test_cross_file/ -v
```

### 5. Performance Tests (`test_performance/`)

Performance and stress tests.

**Tests:**
- `test_stress.py` - Stress tests with many operations

**Example:**
```bash
pytest test_performance/ -v --durations=10
```

### 6. Crash Tests (`test_crash/`)

Robustness tests for crash scenarios.

**Tests:**
- `test_robustness.py` - Invalid input, malformed requests, edge cases

**Example:**
```bash
pytest test_crash/ -v
```

### 7. Symbol Tests (`test_symbols/`)

Tests for symbol-related features.

**Tests:**
- `test_document_symbols.py` - Document outline
- `test_rename.py` - Rename refactoring

**Example:**
```bash
pytest test_symbols/ -v
```

### 8. Master File Tests (`test_master_file/`)

Tests for master file functionality.

**Tests:**
- `test_master_file.py` - Master file notifications and navigation

**Example:**
```bash
pytest test_master_file/ -v
```

## Writing New Tests

### Using Fixtures

The `conftest.py` provides several helpful fixtures:

#### `lsp_client` - Automatic LSP Client

Automatically starts and stops the LSP server:

```python
def test_my_feature(lsp_client):
    """Test with automatic LSP client."""
    response = lsp_client.hover(uri, line=0, character=3)
    assert response is not None
```

#### `temp_document` - Temporary Test Documents

Creates temporary documents for testing:

```python
def test_something(temp_document, lsp_client):
    """Test with temporary document."""
    code = "fn test() { return 42; }"
    uri = temp_document(code)
    
    response = lsp_client.hover(uri, line=0, character=3)
    assert response is not None
```

#### `fixture_file` - Use Fixture Files

Opens files from the `fixtures/` directory:

```python
def test_with_fixture(fixture_file, lsp_client):
    """Test with fixture file."""
    uri, content = fixture_file("simple_function.jazz")
    
    response = lsp_client.hover(uri, line=0, character=3)
    assert response is not None
```

### Helper Functions

```python
from conftest import (
    assert_response_ok,      # Assert no error in response
    assert_has_result,       # Assert response has 'result' field
    assert_result_not_null,  # Assert result is not null
)

def test_example(lsp_client, temp_document):
    uri = temp_document("fn test() { }")
    response = lsp_client.hover(uri, 0, 3)
    
    assert_response_ok(response, "hover")
    assert_result_not_null(response, "hover")
```

### Test Template

```python
"""
Description of what this test file tests.
"""

import pytest
from conftest import assert_response_ok, assert_has_result


def test_feature_name(lsp_client, temp_document):
    """Test specific feature behavior."""
    # Arrange
    code = "fn test() { return 42; }"
    uri = temp_document(code)
    
    # Act
    response = lsp_client.hover(uri, line=0, character=3)
    
    # Assert
    assert_response_ok(response, "hover")
    assert response["result"] is not None


@pytest.mark.parametrize("line,char,expected", [
    (0, 0, "fn"),
    (0, 3, "test"),
])
def test_parameterized(lsp_client, temp_document, line, char, expected):
    """Parameterized test example."""
    code = "fn test() { return 42; }"
    uri = temp_document(code)
    
    response = lsp_client.hover(uri, line=line, character=char)
    assert_response_ok(response, f"hover at {line}:{char}")
```

## Common Test Patterns

### Testing Hover

```python
def test_hover_example(lsp_client, temp_document):
    uri = temp_document("fn square(reg u64 x) -> reg u64 { return x * x; }")
    
    response = lsp_client.hover(uri, line=0, character=3)
    assert_response_ok(response)
    
    result = response["result"]
    if result:
        assert "contents" in result
```

### Testing Go-to-Definition

```python
def test_goto_def_example(lsp_client, temp_document):
    code = """fn helper() { }
fn main() { helper(); }"""
    uri = temp_document(code)
    
    response = lsp_client.definition(uri, line=1, character=12)
    assert_response_ok(response)
    
    result = response["result"]
    if result:
        location = result[0] if isinstance(result, list) else result
        assert location["range"]["start"]["line"] == 0
```

### Testing Find References

```python
def test_references_example(lsp_client, temp_document):
    code = """fn func() { }
fn main() { func(); func(); }"""
    uri = temp_document(code)
    
    response = lsp_client.references(uri, line=0, character=3, include_declaration=True)
    assert_response_ok(response)
    
    result = response["result"]
    assert isinstance(result, list)
    assert len(result) >= 2  # definition + 2 calls
```

## Debugging Tests

### Run with Verbose Output

```bash
pytest -vv
```

### Show Print Statements

```bash
pytest -s
```

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### Run Only Failed Tests from Last Run

```bash
pytest --lf
```

### Show Full Traceback

```bash
pytest --tb=long
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test LSP

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
      
      - name: Build LSP server
        run: |
          # Install pixi and build
          curl -fsSL https://pixi.sh/install.sh | bash
          pixi run build
      
      - name: Run tests
        run: |
          cd test
          pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Migration Guide

### Converting Old Tests

Old test structure:
```python
#!/usr/bin/env python3
def main():
    # Manual LSP client setup
    proc = subprocess.Popen([LSP_SERVER], ...)
    # Manual message sending
    # Manual assertions
    
if __name__ == "__main__":
    main()
```

New test structure:
```python
import pytest
from conftest import assert_response_ok

def test_feature(lsp_client, temp_document):
    """Test description."""
    uri = temp_document("code here")
    response = lsp_client.hover(uri, 0, 3)
    assert_response_ok(response)
```

**Benefits:**
- ✅ No manual LSP client setup
- ✅ Automatic cleanup
- ✅ Reusable fixtures
- ✅ Better error messages
- ✅ Parallel execution
- ✅ Easy test discovery
- ✅ Integrated with pytest ecosystem

## Troubleshooting

### LSP Server Not Found

```
FileNotFoundError: LSP server not found at _build/default/jasmin-lsp/jasmin_lsp.exe
```

**Solution:** Build the server first:
```bash
cd /path/to/jasmin-lsp
pixi run build
```

### Tests Timing Out

**Solution:** Increase timeout or mark as slow:
```python
@pytest.mark.slow
def test_slow_operation(lsp_client):
    # test code
```

Then skip slow tests:
```bash
pytest -m "not slow"
```

### Import Errors

**Solution:** Run pytest from the `test/` directory:
```bash
cd test
pytest
```

### Server Crashes During Tests

**Solution:** Check server logs and use crash tests to identify the issue:
```bash
pytest test_crash/ -v -s
```

## Performance Tips

1. **Run in parallel**: `pytest -n auto`
2. **Skip slow tests**: `pytest -m "not slow"`
3. **Run only failed tests**: `pytest --lf`
4. **Reuse LSP instance**: Use `lsp_client` fixture (auto-managed)

## Best Practices

1. ✅ **Use fixtures** - Don't manually start/stop LSP server
2. ✅ **Use helper assertions** - `assert_response_ok()`, etc.
3. ✅ **Write focused tests** - One feature per test
4. ✅ **Use parametrize** - Test multiple cases with one function
5. ✅ **Add docstrings** - Explain what each test does
6. ✅ **Clean code** - Tests should be readable documentation
7. ✅ **Mark slow tests** - Use `@pytest.mark.slow`
8. ✅ **Test edge cases** - Include error conditions

## Summary

The new pytest-based architecture provides:

- 🗂️ **Organized by category** - Easy to find and run related tests
- 🔄 **Reusable fixtures** - No code duplication
- ⚡ **Parallel execution** - Run tests faster
- 📊 **Coverage reports** - Track test coverage
- 🎯 **Selective testing** - Run specific categories or tests
- 🛠️ **Better debugging** - Pytest's excellent tooling
- 📝 **Clear structure** - Easy to understand and extend
- ✨ **Modern practices** - Industry-standard testing patterns

Run all tests with:
```bash
cd test && pytest
```

Run specific category:
```bash
cd test && pytest test_hover/
```

Happy testing! 🚀
