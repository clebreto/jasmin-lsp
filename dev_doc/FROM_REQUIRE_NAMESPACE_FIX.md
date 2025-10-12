# From/Require Namespace Fix

## Date
October 12, 2025

## Problem

The `from NAMESPACE require "file.jinc"` syntax was not working correctly. When users tried to use "Go to Definition" on symbols from files imported with a namespace, the LSP server couldn't find the files.

### Example Issue

```jasmin
from Common require "poly.jinc"

fn main() {
  poly_add();  // ❌ "Go to Definition" didn't work
}
```

The file structure:
```
project/
  main.jazz
  Common/
    poly.jinc  // Contains poly_add()
```

**Expected**: Clicking "Go to Definition" on `poly_add()` should navigate to `Common/poly.jinc`

**Actual**: Definition not found, file not being resolved

## Root Cause

The `extract_requires_from_node` function in `SymbolTable.ml` only extracted the filename from `require` statements, but ignored the `from` clause containing the namespace identifier.

When the code saw:
```jasmin
from Common require "poly.jinc"
```

It tried to resolve just `"poly.jinc"` relative to the current directory, instead of `"Common/poly.jinc"`.

## Solution

Modified `extract_requires_from_node` in `jasmin-lsp/Document/SymbolTable.ml` to:

1. **Check for `from` clause**: Look for a child node of type `"from"` in the `require` node
2. **Extract namespace**: If found, get the identifier from the `from` node's `id` field
3. **Prepend namespace as folder**: When resolving the file path, prepend the namespace as a directory name
4. **Maintain backward compatibility**: If no `from` clause exists, work as before

### Implementation Details

The tree-sitter grammar structure for require statements:

```
require                    // Node type: "require"
  from (optional)         // Node type: "from"
    identifier            // Field: "id" - the namespace
  string_literal          // Field: "file" - the filename
```

The fix:
1. When processing a `require` node, first scan for a `from` child
2. If found, extract the namespace identifier text
3. Use `Filename.concat namespace filename` to build the path
4. Resolve the path relative to the current file's directory

## Test Results

### Test Coverage

✅ **Simple namespace**: `from Common require "poly.jinc"` → resolves to `Common/poly.jinc`

✅ **Nested paths**: `from Common require "crypto/aes.jinc"` → resolves to `Common/crypto/aes.jinc`

✅ **No namespace**: `require "poly.jinc"` → resolves to `poly.jinc` (backward compatible)

✅ **Case sensitivity**: `from common require "poly.jinc"` → resolves to `common/poly.jinc`

✅ **Multiple requires**: Multiple `from X require Y` statements work correctly

### Example Test Case

```jasmin
// File: main.jazz
from Common require "poly.jinc"
from Crypto require "aes.jinc"

fn test() {
  poly_add();      // ✅ Navigates to Common/poly.jinc
  aes_encrypt();   // ✅ Navigates to Crypto/aes.jinc
}
```

## Files Modified

- **`jasmin-lsp/Document/SymbolTable.ml`**:
  - `extract_requires_from_node`: Added namespace detection and path resolution

## Benefits

1. ✅ **Proper module organization**: Users can organize code in folders/namespaces
2. ✅ **Go to Definition works**: Navigate to symbols in namespaced files
3. ✅ **Cross-file features work**: Hover, references, etc. all work with namespaced imports
4. ✅ **Backward compatible**: Plain `require` statements without `from` still work
5. ✅ **Matches ML-DSA patterns**: The ML-DSA Jasmin codebase uses this pattern extensively

## Real-World Impact

This fix enables proper navigation in large Jasmin projects like ML-DSA that use the namespace pattern:

```jasmin
from Common require "arithmetic/rounding.jinc"
from Common require "arithmetic/modular.jinc"  
from Common require "keccak/keccak1600.jinc"
from Common require "constants.jinc"
```

All of these now resolve correctly to their respective files in the `Common/` directory.

## Verification

Run the comprehensive test:
```bash
python3 test_from_require_comprehensive.py
```

All tests should pass:
- ✅ Simple namespace
- ✅ Nested path in namespace
- ✅ No namespace (plain require)
- ✅ Lowercase namespace folder
- ✅ Multiple from/require

## Technical Notes

### Path Resolution Logic

```ocaml
(* If there's a namespace, prepend it as a folder *)
let filename_with_namespace = match namespace_opt with
  | Some ns -> Filename.concat ns filename
  | None -> filename
in

let resolved_path = Filename.concat current_dir filename_with_namespace in
```

This ensures:
- `from Common require "poly.jinc"` → `current_dir/Common/poly.jinc`
- `require "poly.jinc"` → `current_dir/poly.jinc`

### Case Sensitivity

The namespace is used as-is from the source code:
- `from Common` → looks for `Common/` folder
- `from common` → looks for `common/` folder

This respects the user's choice and matches filesystem behavior.
