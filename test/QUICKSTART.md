# Jasmin LSP Test Suite - Quick Start

## ✅ New Pytest Architecture Ready!

All tests have been reorganized into a modern pytest-based structure with tests organized by categories.

## Quick Commands

### Run All Tests
```bash
cd test
pytest
```

### Run Specific Category
```bash
cd test
pytest test_hover/         # Hover functionality tests
pytest test_navigation/    # Go-to-definition, find references
pytest test_diagnostics/   # Error detection and reporting
pytest test_cross_file/    # Cross-file features (require statements)
pytest test_performance/   # Performance and stress tests
pytest test_crash/         # Crash and robustness tests
pytest test_symbols/       # Document/workspace symbols, rename
pytest test_master_file/   # Master file functionality
```

### Run Specific Test
```bash
cd test
pytest test_hover/test_keyword_hover.py                           # One file
pytest test_hover/test_keyword_hover.py::test_hover_on_function_name  # One test
```

### Run with Options
```bash
cd test
pytest -v           # Verbose output
pytest -s           # Show print statements
pytest -k "hover"   # Run tests matching "hover"
pytest -n auto      # Parallel execution (if pytest-xdist installed)
pytest --cov=.      # With coverage report
```

## Test Structure

```
test/
├── conftest.py              # Shared fixtures and LSP client ⭐
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Optional dependencies
├── PYTEST_GUIDE.md          # Complete documentation
├── TEST_REORGANIZATION_SUMMARY.md  # Detailed summary
├── migrate_tests.sh         # Migration helper
│
├── test_hover/              # 17 tests - Hover functionality
├── test_navigation/         # 8 tests - Goto def, references
├── test_diagnostics/        # 4 tests - Diagnostics
├── test_cross_file/         # 4 tests - Cross-file features
├── test_performance/        # 3 tests - Performance tests
├── test_crash/              # 6 tests - Crash/robustness
├── test_symbols/            # 6 tests - Symbols, rename
└── test_master_file/        # 3 tests - Master file
```

**Total: 51 example tests** organized by functionality

## Key Features

### ✅ Organized by Category
Tests are grouped by what they test, making them easy to find and run.

### ✅ Shared Fixtures
The `conftest.py` provides reusable fixtures:
- `lsp_client` - Automatic LSP server management
- `temp_document` - Create temporary test documents
- `fixture_file` - Load files from fixtures/
- Helper assertions for cleaner tests

### ✅ No Old Tests Deleted
All original tests remain in the `test/` directory. The new structure is additive.

## Writing New Tests

### Example Test
```python
"""Test description."""
import pytest
from conftest import assert_response_ok

def test_my_feature(lsp_client, temp_document):
    """Test hover on my feature."""
    # Arrange
    code = "fn my_func() { return 42; }"
    uri = temp_document(code)
    
    # Act
    response = lsp_client.hover(uri, line=0, character=3)
    
    # Assert
    assert_response_ok(response)
    assert response["result"] is not None
```

### Available Fixtures
- `lsp_client` - Ready-to-use LSP client (auto start/stop)
- `temp_document(code, filename="test.jazz")` - Create temp document
- `fixture_file(filename)` - Load from fixtures/ directory
- `lsp_server_path` - Path to LSP executable
- `fixtures_dir` - Path to fixtures directory

### Helper Functions
```python
from conftest import (
    assert_response_ok,      # Assert no error in response
    assert_has_result,       # Assert has 'result' field
    assert_result_not_null,  # Assert result is not null
)
```

## Documentation

📖 **Read the complete guide:** `PYTEST_GUIDE.md`

This includes:
- Installation instructions
- Running tests in detail
- Writing new tests
- Fixtures and patterns
- Debugging tips
- CI/CD integration
- Migration guide

## Installation (Optional)

The tests work with just pytest, but you can install extras:

```bash
cd test
pip install -r requirements.txt
```

This adds:
- `pytest-timeout` - Timeout support
- `pytest-cov` - Coverage reports
- `pytest-xdist` - Parallel execution
- `pytest-sugar` - Better output
- `pytest-html` - HTML reports

## Common Commands

```bash
# Run all tests
pytest

# Run one category
pytest test_hover/

# Run verbose
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run in parallel (faster!)
pytest -n auto

# Run only failed tests from last run
pytest --lf

# Show test durations
pytest --durations=10

# Skip slow tests
pytest -m "not slow"
```

## Test Categories Explained

| Category | Description | Test Count |
|----------|-------------|------------|
| **test_hover/** | Hover information, type display | 17 |
| **test_navigation/** | Goto definition, find references | 8 |
| **test_diagnostics/** | Syntax errors, diagnostics | 4 |
| **test_cross_file/** | Require statements, dependencies | 4 |
| **test_performance/** | Stress tests, performance | 3 |
| **test_crash/** | Robustness, invalid input | 6 |
| **test_symbols/** | Document/workspace symbols | 6 |
| **test_master_file/** | Master file functionality | 3 |

## Status

✅ **51 tests created** - All categories covered
✅ **Infrastructure working** - Fixtures operational
✅ **Test discovery working** - Pytest finds all tests
✅ **Documentation complete** - Comprehensive guides
✅ **Old tests preserved** - No breaking changes

## Next Steps

1. **Try it out:**
   ```bash
   cd test
   pytest test_hover/ -v
   ```

2. **Read the guide:**
   ```bash
   cat PYTEST_GUIDE.md
   ```

3. **Run migration helper:**
   ```bash
   ./migrate_tests.sh
   ```

4. **Start writing tests:**
   - Copy an example test
   - Modify for your case
   - Use provided fixtures

## Help

- **Full guide:** `PYTEST_GUIDE.md`
- **Summary:** `TEST_REORGANIZATION_SUMMARY.md`
- **Migration:** `./migrate_tests.sh`
- **Pytest docs:** https://docs.pytest.org/

---

🎉 **Test suite reorganization complete!**

Run tests with: `cd test && pytest`
