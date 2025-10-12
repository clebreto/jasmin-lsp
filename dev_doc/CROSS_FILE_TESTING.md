# Cross-File Testing Implementation

## Summary

Successfully implemented comprehensive cross-file testing for the Jasmin LSP to verify that "jump to definition" and "find references" work correctly across file boundaries when using Jasmin's `require` statement.

## Implementation Date

October 10, 2025

## What Was Added

### 1. New Test Fixtures

#### `test/fixtures/math_lib.jazz`
A library file containing utility functions that can be required by other Jasmin files:
- `square(x)` - Returns x²
- `add(a, b)` - Returns a + b  
- `subtract(a, b)` - Returns a - b
- `double(value)` - Returns value * 2
- `increment(x)` - Returns x + 1

#### `test/fixtures/main_program.jazz`
A main program that demonstrates cross-file usage:
- Starts with `require "math_lib.jazz"`
- Contains `compute()` function that calls `square()`, `double()`, and `add()` from the library
- Contains `process_values()` function that uses multiple library functions
- Tests that goto definition correctly jumps to `math_lib.jazz`
- Tests that find references finds usages across both files

### 2. Enhanced Test Runners

#### Python Test Runner (`test/run_tests.py`)

Added two new test methods:

**`test_cross_file_goto_definition(main_file, lib_file, test_name)`**
- Opens both the main file and library file in the LSP
- Sets the workspace root to the fixtures directory
- Requests goto definition from a function call in main_program.jazz
- Verifies the response points to the correct location in math_lib.jazz
- **Status: ✅ PASSING**

**`test_cross_file_references(main_file, lib_file, test_name)`**
- Opens both files in the LSP session
- Requests find references for a function defined in math_lib.jazz
- Verifies that references in both files are detected
- **Status: ✅ PASSING**

#### Shell Test Runner (`test/test_all.sh`)

Added corresponding shell script tests:

**Test 8: Cross-File Go to Definition**
- Implements same logic as Python version using bash and LSP JSON-RPC
- Opens both files with proper workspace URI
- Tests goto definition across files

**Test 9: Cross-File Find References**
- Tests find references functionality across file boundaries
- Counts URI occurrences to verify multiple references found

### 3. Documentation Updates

Updated `test/README.md` with:
- Descriptions of new test fixtures
- Cross-file testing section explaining how it works
- Manual testing instructions for VS Code
- Explanation of Jasmin's `require` statement syntax
- LSP implementation requirements for cross-file support

## Test Results

### Python Test Runner
```
============================================================
Test 6: Cross-File Go to Definition
============================================================
✅ Cross-file goto definition (points to correct file)

============================================================
Test 7: Cross-File References
============================================================
✅ Cross-file find references (multiple references found)
```

**Result: Both tests passing! ✅**

### Shell Test Runner
The shell tests have been implemented and can be run with `./test_all.sh`.

## How Jasmin Includes Files

Jasmin uses the `require` statement to include other source files:

```jasmin
require "library.jazz"              // Simple require
require "lib1.jazz" "lib2.jazz"     // Multiple files  
from NAMESPACE require "lib.jazz"   // With namespace
```

This is similar to:
- `#include` in C/C++
- `import` in Python
- `require` in Ruby
- `use` in Rust

## LSP Requirements for Cross-File Support

For cross-file goto definition and references to work, the LSP server must:

1. **Parse require statements** - Extract file paths from `require` directives
2. **Load required files** - Read and parse the required Jasmin files
3. **Build cross-file symbol table** - Track which symbols are defined in which files
4. **Resolve references** - When a symbol is used, look it up across all loaded files
5. **Return correct URIs** - Return file:// URIs pointing to the correct source file

## Running the Tests

### Quick Test (Python)
```bash
cd test
python3 run_tests.py
```

### Comprehensive Test (Shell)
```bash
cd test
./test_all.sh
```

### Specific Cross-File Tests
```bash
cd test
python3 run_tests.py 2>&1 | grep -A 2 "Cross-file"
```

## Manual Testing in VS Code

1. Open `test/fixtures/math_lib.jazz` and `test/fixtures/main_program.jazz` in VS Code
2. Ensure jasmin-lsp is configured correctly
3. In `main_program.jazz`, Ctrl+Click (or Cmd+Click on macOS) on `square` at line 13
4. Should jump to the `square` function definition in `math_lib.jazz`
5. Right-click on `add` function in `math_lib.jazz`
6. Select "Find All References"
7. Should show references in both files

## Future Enhancements

Potential improvements for cross-file testing:

1. **Test with nested requires** - Test A requires B, B requires C
2. **Test circular dependencies** - How does LSP handle A requires B, B requires A
3. **Test namespace imports** - Test `from NAMESPACE require "file.jazz"`
4. **Test workspace-wide search** - Verify workspace symbols across all files
5. **Test incremental updates** - Change library file and verify main file updates
6. **Performance testing** - Test with large number of required files

## Related Files

- `/test/fixtures/math_lib.jazz` - Library test fixture
- `/test/fixtures/main_program.jazz` - Main program test fixture  
- `/test/run_tests.py` - Python test runner (lines ~130-270)
- `/test/test_all.sh` - Shell test runner (lines ~330-440)
- `/test/README.md` - Test documentation

## Verification Checklist

- [x] Created library file with multiple functions
- [x] Created main file with `require` statement
- [x] Added cross-file goto definition test to Python runner
- [x] Added cross-file references test to Python runner
- [x] Added cross-file tests to shell runner
- [x] Tests pass in Python runner
- [x] Updated test documentation
- [x] Documented Jasmin's `require` syntax
- [x] Provided manual testing instructions

## Conclusion

The Jasmin LSP test suite now comprehensively tests cross-file functionality, which is essential for real-world Jasmin development where projects typically consist of multiple source files connected via `require` statements. The tests verify that the LSP can correctly:

1. Handle multiple files in the same workspace
2. Resolve symbols across file boundaries  
3. Navigate between files using goto definition
4. Find all references across the entire codebase

This ensures developers can confidently use the LSP for navigation and refactoring in multi-file Jasmin projects.
