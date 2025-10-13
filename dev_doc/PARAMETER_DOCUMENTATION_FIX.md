# Parameter Documentation Fix

## Issue

When hovering over a parameter in a function definition (e.g., parameter `a` in `fn _cddq(reg u32 a)`), the LSP was incorrectly showing documentation comments from nearby functions instead of showing no documentation (since parameters don't have their own documentation).

**Example Problem:**
```jasmin
/* This is the comment for _caddq function */
inline fn _caddq(reg u32 x) -> reg u32 {
  // ...
}

// This function has no documentation comment
fn _cddq(reg u32 a) -> reg u32 {
  // When hovering on 'a' here, it was showing _caddq's documentation!
}
```

## Root Cause

In `SymbolTable.ml`, when extracting parameter symbols (lines 493-518), the code was calling `extract_doc_comment` for each parameter node and assigning the result to the parameter's `documentation` field.

The `extract_doc_comment` function looks backwards from any given node to find comments. For a parameter inside a function definition, this could incorrectly pick up documentation from a previous function if there happened to be one nearby.

## Solution

Parameters that are part of a function signature should **not** have individual documentation comments. Only the function itself should have documentation.

### Code Changes

**File:** `jasmin-lsp/Document/SymbolTable.ml`

**Changed:**
- Line 493-504: `"parameter" | "formal_arg"` case - Set `documentation = None` instead of `documentation = doc`
- Line 507-518: `"param_decl"` case - Set `documentation = None` instead of `documentation = doc`

**Before:**
```ocaml
| "parameter" | "formal_arg" ->
    (match extract_parameter_info node source with
    | Some (name, detail) ->
        {
          ...
          documentation = doc;  (* ❌ Could pick up wrong comment *)
        } :: acc
    | None -> acc)
```

**After:**
```ocaml
| "parameter" | "formal_arg" ->
    (* Parameters inside function signatures should not have their own documentation *)
    (match extract_parameter_info node source with
    | Some (name, detail) ->
        {
          ...
          documentation = None;  (* ✅ Parameters don't have individual docs *)
        } :: acc
    | None -> acc)
```

## Testing

Created comprehensive test to verify the fix:

**Test File:** `test/test_hover/test_param_no_doc.py`  
**Fixture:** `test/fixtures/param_doc_test.jazz`

### Test Cases

1. **Parameter without documentation** - Hover on `a` in `fn _cddq(reg u32 a)` shows only type info, no documentation
2. **Parameter in documented function** - Hover on `value` in `fn main_function(reg u32 value)` shows only type info
3. **Function with documentation** - Hover on function name shows the function's documentation correctly

### Test Results

```
Test 1: Hover on parameter 'a' in _cddq (line 11)
✅ PASS: Parameter 'a' has no documentation (correct!)

Test 2: Hover on parameter 'value' in main_function (line 19)
✅ PASS: Parameter 'value' has no documentation (correct!)

Test 3: Hover on function name 'main_function' (line 19)
✅ PASS: Function shows its documentation correctly!

ALL TESTS PASSED! ✅
```

## Full Test Suite

All existing tests continue to pass:
- **103 tests passed**
- 2 skipped (expected)
- 1 xfailed (expected)
- 0 failures

## Behavior After Fix

| Hover Target | Documentation Shown | Correct? |
|-------------|-------------------|----------|
| Parameter in function signature | None (only type) | ✅ Yes |
| Function name | Function's documentation | ✅ Yes |
| Variable declaration | Variable's documentation | ✅ Yes |
| Constant/param declaration | Constant's documentation | ✅ Yes |

## Summary

Parameters are now correctly recognized as not having individual documentation. Only declarations that can have their own documentation comments (functions, variables, constants) will show documentation in hover tooltips.

**Files Modified:** 1 (`SymbolTable.ml`)  
**Lines Changed:** ~30 lines (added comments, changed 2 assignments)  
**Build Status:** ✅ Success  
**Test Status:** ✅ All tests passing (103/103)
