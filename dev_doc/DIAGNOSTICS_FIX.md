# Diagnostics Not Working - Root Cause Analysis & Fix

**Date:** October 16, 2025  
**Issue:** Syntax errors (e.g., `;;;`) not reported in editor despite tree-sitter detecting them

## Problem Analysis

### What We Observed

From the log file analysis (`jasmin-lsp-20251016-103324.log`):

1. **File opened**: `Collected 0 diagnostics` ✓
2. **User typed `;;;` (version 6)**: `Collected 0 diagnostics` ❌
3. **File saved (disk change)**: `Collected 0 diagnostics` ❌

Even though tree-sitter clearly detects the error:
```
(ERROR [4, 4] - [4, 7])
```

### Root Cause

The `collect_diagnostics` function in `LspProtocol.ml` was **only** checking:
- `TreeSitter.node_is_error node` - Returns boolean from C API
- `TreeSitter.node_is_missing node` - Returns boolean from C API

However, tree-sitter **also** creates nodes with **type name** = `"ERROR"` which need to be checked separately!

### The Bug

```ocaml
(* BEFORE - Missing ERROR type check *)
if is_error || is_missing then begin
  (* Report diagnostic *)
end
```

This meant:
- Tree-sitter parsed `;;;` and created an `ERROR` node
- But `node_is_error()` returned `false` (because it checks a different flag)
- So the ERROR node was **silently ignored**
- Result: 0 diagnostics collected

## The Fix

Added explicit check for `"ERROR"` node type:

```ocaml
(* AFTER - Fixed to detect ERROR nodes *)
let node_type_str = TreeSitter.node_type node in

(* Check both is_error function AND "ERROR" node type *)
if is_error || is_missing || node_type_str = "ERROR" then begin
  Io.Logger.log (Format.asprintf "Found error node: type=%s, is_error=%b, is_missing=%b" 
    node_type_str is_error is_missing);
  (* ... create diagnostic ... *)
end
```

### Additional Debug Logging

Added specific logging for ERROR nodes:
```ocaml
if node_type_str = "ERROR" then
  Io.Logger.log (Format.asprintf "Found ERROR node type: type=%s, is_error=%b, is_missing=%b" 
    node_type_str is_error is_missing);
```

This helps debug future issues by showing when ERROR nodes are detected.

## Why Diagnostics Worked Before (Sometimes)

The function **did** work for certain types of errors:
- **Missing nodes** (incomplete syntax) - caught by `is_missing`
- **Certain error types** - caught by `is_error` flag

But it **failed** for:
- Unexpected tokens (like `;;;`)
- Invalid syntax that creates ERROR nodes
- Many common syntax mistakes

## Testing

### Test Case 1: Syntax Error
```jasmin
export fn test() -> reg u32 {
    ;;;  // Should show error
    return 0;
}
```

**Expected**: Diagnostic showing "Syntax error" at line with `;;;`

### Test Case 2: Missing Semicolon
```jasmin
export fn test() -> reg u32 {
    reg u32 x  // Missing semicolon
    return x;
}
```

**Expected**: Diagnostic showing "Missing: ;" 

### Tree-Sitter Verification

```bash
cd tree-sitter-jasmin
tree-sitter parse /path/to/file.jazz
```

Look for `(ERROR ...)` nodes in output.

## Why This Wasn't Caught Earlier

1. **No visible errors in logs** - The function silently returned empty list
2. **No ERROR in test files** - Test files might have been syntactically correct
3. **Tree-sitter abstraction** - The C API has multiple ways to represent errors

## Files Modified

- `jasmin-lsp/Protocol/LspProtocol.ml` - Line ~1015-1040
  - Added check for `node_type_str = "ERROR"`
  - Added debug logging for ERROR nodes

## Related Issues

### Why `didChange` Didn't Show Diagnostics
✅ **Working as designed** - `textDocument/didChange` was calling `send_diagnostics` correctly

### Why File Save Didn't Show Diagnostics  
✅ **Working as designed** - `workspace/didChangeWatchedFiles` was reloading and calling diagnostics correctly

The real issue: **Diagnostics collection was broken** for ERROR nodes, so even though the system was working, it had nothing to report!

## Verification After Fix

After rebuilding, you should see in the logs:

```
[LOG HH:MM:SS] : Found ERROR node type: type=ERROR, is_error=false, is_missing=false
[LOG HH:MM:SS] : Found error node: type=ERROR, is_error=false, is_missing=false  
[LOG HH:MM:SS] : Collected 1 diagnostics
```

And in VS Code:
- Red squiggly under the `;;;`
- Error message: "Syntax error"
- Problems panel shows 1 error

## Lessons Learned

1. **Tree-sitter has multiple error representations**
   - `is_error()` function
   - `is_missing()` function  
   - `"ERROR"` node type
   - All three need to be checked!

2. **File logging was crucial**
   - Showed diagnostics collection was returning 0
   - Proved the system was calling the function correctly
   - Narrowed down the bug to `collect_diagnostics`

3. **Test with actual errors**
   - Need test cases with syntax errors
   - Not just valid code

## Future Improvements

1. **Add test suite** for diagnostics with various error types
2. **Log all node types** during development (can be removed in production)
3. **Check tree-sitter documentation** for all error representations
4. **Add integration test** that verifies error reporting end-to-end
