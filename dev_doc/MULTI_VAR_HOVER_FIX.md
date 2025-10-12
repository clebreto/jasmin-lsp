# Multi-Variable Declaration Hover Fix

## Problem

When multiple variables were declared together on the same line (e.g., `reg u32 i, j;`), hovering over the second variable `j` would incorrectly show the type as `reg u32 i,` instead of just `reg u32`.

Similarly for function parameters declared together (e.g., `fn f(reg u32 a b)`), only the first parameter would be extracted.

## Root Cause

The original implementation in `SymbolTable.ml` had two issues:

1. **For each variable/parameter, it extracted type text from the start of the entire declaration node to that specific variable's position**. For the second variable `j` in `reg u32 i, j;`, this meant extracting "reg u32 i, " instead of just "reg u32".

2. **All variables/parameters in a declaration shared the same range** (the range of the entire `var_decl` or `param_decl` node), so only one symbol was effectively stored.

## Solution

Modified two functions in `jasmin-lsp/Document/SymbolTable.ml`:

### 1. `extract_variable_info`
- Find ALL variable nodes in the declaration
- Extract type text from declaration start to the FIRST variable only
- Return list of (name, type, **individual_range**) tuples
- Each variable gets its own unique range

### 2. `extract_param_decl_info`
- Find ALL parameter nodes in the declaration  
- Extract type text from declaration start to the FIRST parameter only
- Return list of (name, type, **individual_range**) tuples
- Each parameter gets its own unique range

### 3. Updated symbol creation code
- Changed from using the declaration node's range for all symbols
- Now uses the individual variable/parameter node's range for each symbol

## Testing

### Test Results

✅ **Variables (comma-separated)**:
```jasmin
fn test() {
  reg u32 i, j;        // Both show "reg u32"
  stack u64 x, y, z;   // All three show "stack u64"
}
```

✅ **Parameters (whitespace-separated)**:
```jasmin
fn test(reg u32 a b, stack u64 x y z) {
  // a, b: both show "reg u32"
  // x, y, z: all show "stack u64"
}
```

### Test Files Created
- `test_multi_var_hover.py` - Tests variable declarations with commas
- `test_multi_param_hover.py` - Tests parameter declarations (no commas)
- `test_comprehensive_hover.py` - Combined test

## Important Notes

**Jasmin Syntax Differences**:
- Variable declarations **use commas**: `reg u32 i, j, k;`
- Function parameters **use whitespace**: `fn f(reg u32 a b c)`

## Files Modified

- `jasmin-lsp/Document/SymbolTable.ml`:
  - `extract_variable_info` - Fixed to extract type once and return individual ranges
  - `extract_param_decl_info` - Fixed to extract type once and return individual ranges
  - Symbol creation code - Updated to use individual ranges instead of declaration range

## Verification

```bash
# Run tests
python3 test_multi_var_hover.py
python3 test_multi_param_hover.py

# Both should show all tests passing
```

## Summary

The fix ensures that:
1. ✅ Each variable/parameter in a multi-declaration shows only its own type
2. ✅ Type information is correct (no trailing commas or other variable names)
3. ✅ Each symbol has its own unique range for precise hover positioning
4. ✅ Works for both variables (with commas) and parameters (without commas)
