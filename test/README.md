# Jasmin LSP Test Suite

This directory contains comprehensive tests for all jasmin-lsp features.

## Test Files

### Test Fixtures (`fixtures/`)

Sample Jasmin programs for testing various features:

- **`simple_function.jazz`** - Basic functions with parameters and returns
- **`syntax_errors.jazz`** - Intentional syntax errors for diagnostics testing
- **`references_test.jazz`** - Multiple references to test find-references
- **`types_test.jazz`** - Various type declarations for hover testing
- **`arrays_test.jazz`** - Array operations and complex structures
- **`math_lib.jazz`** - Library file with utility functions (for cross-file testing)
- **`main_program.jazz`** - Main program that requires math_lib.jazz (tests cross-file goto definition and references)

### Test Scripts

1. **`test_all.sh`** - Shell-based test suite (recommended for quick testing)
2. **`test_lsp.py`** - Python-based comprehensive test suite (more detailed)

## Running Tests

### Prerequisites

Build the LSP server first:

```bash
cd ..
pixi run build
```

### Quick Test (Shell Script)

```bash
./test_all.sh
```

This runs all tests using shell commands and shows pass/fail results.

### Comprehensive Test (Python Script)

```bash
python3 test_lsp.py
```

This provides more detailed output and better error messages.

Requires Python 3.6+. No additional dependencies needed.

## Test Coverage

### ✅ Implemented Tests

1. **Server Initialization**
   - Server starts successfully
   - Capabilities are advertised correctly
   - Configuration requests work

2. **Syntax Diagnostics**
   - Clean files show no errors
   - Files with syntax errors are detected
   - Diagnostics have proper severity and range

3. **Go to Definition**
   - Jump to function definitions
   - Navigate to variable declarations
   - Handle missing definitions gracefully
   - **Cross-file goto definition** - Jump from main_program.jazz to definitions in math_lib.jazz

4. **Find References**
   - Find all usages of a symbol
   - Include/exclude declaration
   - Multiple references detected
   - **Cross-file references** - Find references across multiple files (e.g., functions used in both math_lib.jazz and main_program.jazz)

5. **Hover Information**
   - Show type information
   - Display function signatures
   - Format as Markdown

6. **Document Lifecycle**
   - Open document (`textDocument/didOpen`)
   - Change document (`textDocument/didChange`)
   - Close document (`textDocument/didClose`)
   - Diagnostics update on changes

7. **Cross-File Analysis**
   - Test `require` statements that include other Jasmin files
   - Verify goto definition works across file boundaries
   - Verify find references works across file boundaries
   - Multiple files opened in the same LSP session
   - **Navigate to required files** - Click on filename in `require "file.jazz"` to open that file

## Test Output

### Shell Script Output

```
==========================================
Jasmin LSP Test Suite
==========================================
Server: ../_build/default/jasmin-lsp/jasmin_lsp.exe
Fixtures: ./fixtures

==========================================
Test 1: Server Initialization
==========================================
✅ Server initialization
✅ Definition provider capability
✅ Hover provider capability
✅ References provider capability

==========================================
Test 2: Diagnostics - Clean File
==========================================
✅ Clean file has no errors

...

==========================================
Test Summary
==========================================
Total: 15
Passed: 15
Failed: 0
==========================================
All tests passed!
```

### Python Script Output

```
Starting jasmin-lsp test suite...
Server: ../_build/default/jasmin-lsp/jasmin_lsp.exe

============================================================
Test 1: Server Initialization
============================================================
✅ Initialization: textDocumentSync capability
✅ Initialization: hoverProvider capability
✅ Initialization: definitionProvider capability
✅ Initialization: referencesProvider capability

...

============================================================
Test Results: 18/18 passed
============================================================
```

## Adding New Tests

### Adding a Test Fixture

1. Create a new `.jazz` file in `fixtures/`
2. Add test scenario (e.g., edge cases, specific features)
3. Update test scripts to reference the new fixture

Example:

```bash
# In fixtures/
cat > my_test.jazz << 'EOF'
fn test_feature(reg u64 x) -> reg u64 {
  // Your test code here
  return x;
}
EOF
```

### Adding a Test Case (Shell Script)

Add a new function in `test_all.sh`:

```bash
test_my_feature() {
    echo ""
    echo "=========================================="
    echo "Test N: My Feature"
    echo "=========================================="
    
    local test_file="${FIXTURES_DIR}/my_test.jazz"
    local uri=$(file_uri "$test_file")
    # ... test implementation
    
    if [ condition ]; then
        test_pass "My feature works"
    else
        test_fail "My feature" "Reason for failure"
    fi
}
```

Then call it from `main()`:

```bash
test_my_feature
```

### Adding a Test Case (Python Script)

Add a new function in `run_tests.py`:

```python
def test_my_feature(self, fixture_path, test_name):
    """Test my new feature"""
    # ... test implementation
    
    if condition:
        self.test_pass(test_name)
    else:
        self.test_fail(test_name, "Reason for failure")
```

Then call it from `main()`:

```python
runner.test_my_feature(fixtures_dir / 'my_test.jazz', 'My feature test')
```

## Cross-File Testing

The test suite includes comprehensive cross-file testing to verify that the LSP correctly handles Jasmin's `require` statement for file inclusion.

### How It Works

1. **`math_lib.jazz`** - A library file containing utility functions:
   - `square(x)` - Returns x²
   - `add(a, b)` - Returns a + b
   - `subtract(a, b)` - Returns a - b
   - `double(value)` - Returns value * 2
   - `increment(x)` - Returns x + 1

2. **`main_program.jazz`** - A main program that uses the library:
   - Contains `require "math_lib.jazz"` at the top
   - Calls functions defined in `math_lib.jazz`
   - Tests cross-file goto definition and references

### Cross-File Test Cases

**Test 6: Cross-File Go to Definition**
- Opens both `math_lib.jazz` and `main_program.jazz`
- Requests goto definition on a function call in `main_program.jazz` (e.g., `square()`)
- Verifies the response points to the definition in `math_lib.jazz`
- Status: ✅ **PASSING** (Python runner)

**Test 7: Cross-File Find References**
- Opens both files in the LSP session
- Requests find references for a function defined in `math_lib.jazz` (e.g., `add()`)
- Verifies that references in both files are found
- Status: ✅ **PASSING** (Python runner)

**Test 8: Navigate to Required File**
- Opens `main_program.jazz` containing `require "math_lib.jazz"`
- Requests goto definition on the filename string in the require statement
- Verifies the response points to `math_lib.jazz`
- Status: ✅ **PASSING** (Python runner)

This is incredibly useful for navigating between files - just Ctrl+Click (or Cmd+Click) on any filename in a require statement to jump to that file!

### Testing Cross-File Features Manually

You can test cross-file features in VS Code:

1. Open both `test/fixtures/math_lib.jazz` and `test/fixtures/main_program.jazz`
2. In `main_program.jazz`, Ctrl+Click on `square` (line 13)
3. Should jump to `math_lib.jazz` at the `square` function definition
4. Right-click on `add` in `math_lib.jazz` → Find All References
5. Should show references in both files

### Understanding Jasmin's `require`

Jasmin uses `require` statements to include other source files:

```jasmin
require "library.jazz"           // Simple require
require "lib1.jazz" "lib2.jazz" // Multiple files
from NAMESPACE require "lib.jazz" // With namespace
```

The LSP server must:
1. Parse `require` statements in each file
2. Load and parse the required files
3. Build a cross-file symbol table
4. Resolve references across file boundaries

## Debugging Failed Tests

### Enable Verbose Logging

For shell tests:

```bash
# Modify test_all.sh to remove 2>/dev/null
"$LSP_SERVER" > /tmp/lsp_debug.txt  # Instead of 2>/dev/null

# Then check logs
cat /tmp/lsp_debug.txt
```

For Python tests:

```python
# In test_lsp.py, comment out stderr suppression
self.process = subprocess.Popen(
    [self.server_path],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    # stderr=subprocess.PIPE,  # Comment this out
    text=False
)
```

### Manual Testing

Test individual requests manually:

```bash
cd ..
MESSAGE='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
printf "Content-Length: ${#MESSAGE}\r\n\r\n${MESSAGE}" | \
  _build/default/jasmin-lsp/jasmin_lsp.exe 2>&1 | head -50
```

### Common Issues

1. **Server not found**: Build with `pixi run build`
2. **Timeout**: Increase sleep times in test scripts
3. **Parse errors**: Check test fixture syntax with tree-sitter-jasmin
4. **No response**: Verify Content-Length header is correct

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test LSP

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          submodules: recursive
      
      - name: Install Pixi
        run: curl -fsSL https://pixi.sh/install.sh | bash
      
      - name: Build LSP
        run: pixi run build
      
      - name: Run Tests
        run: cd test && ./test_all.sh
```

### GitLab CI Example

```yaml
test:
  image: ubuntu:latest
  before_script:
    - apt-get update
    - apt-get install -y curl git
    - curl -fsSL https://pixi.sh/install.sh | bash
  script:
    - pixi run build
    - cd test && ./test_all.sh
```

## Test Maintenance

### Regular Updates

1. Update fixtures when language syntax changes
2. Add tests for new LSP features
3. Update expected outputs when server behavior changes
4. Keep test documentation current

### Test File Versions

Test fixtures should match the tree-sitter-jasmin version:

```bash
# Check tree-sitter version
cd ../tree-sitter-jasmin
git describe --tags  # Should match version in pixi.toml
```

## Contributing

When adding new LSP features:

1. ✅ Create test fixtures demonstrating the feature
2. ✅ Add tests to both shell and Python scripts
3. ✅ Verify tests pass before committing
4. ✅ Update this README with test descriptions

## License

Same as jasmin-lsp project (MIT).
