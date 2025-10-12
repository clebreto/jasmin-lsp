# Scope Resolution Bug Fix

## Problem

When using "Go to Definition" on a variable in Jasmin LSP, if multiple functions contained variables with the same name, the LSP would jump to the **first** variable with that name in the file, regardless of which function the cursor was in.

### Example Bug

```jasmin
export fn ml_dsa_44_sign(...) -> ... {
    reg u32 status;      // Line 7
    status = 0;
    return sig, status;
}

export fn ml_dsa_44_verify(...) -> ... {
    reg u32 status;      // Line 20
    status = 1;
    status = status;     // Cursor here - should jump to line 20, but jumped to line 7
    return status;
}
```

When clicking "Go to Definition" on the second `status` in `status = status;` (line 23), the LSP would incorrectly jump to line 7 (the `status` in `ml_dsa_44_sign`) instead of line 20 (the `status` in `ml_dsa_44_verify`).

## Root Cause

The bug had two components:

### 1. Tree-Sitter Node Type Issue
The `node_at_point` function in Tree-Sitter returns the node at the cursor, which for a variable usage is a `variable` node, not an `identifier` node. The original code only looked for `identifier` nodes, so it failed to find the symbol.

### 2. Lack of Scope Filtering
The `find_definition` function in `SymbolTable.ml` searched for symbols by name across the entire file without considering function scope. It would return the first matching symbol found, which could be from any function.

## Solution

### Part 1: Find Identifier/Variable Nodes
Added a new helper function `find_identifier_at_point` in `LspProtocol.ml` that:
- Recursively searches the syntax tree starting from the node at cursor
- Accepts both `identifier` and `variable` node types
- Returns the innermost matching node

```ocaml
let rec find_identifier_at_point node point =
  let node_type = TreeSitter.node_type node in
  
  if node_type = "identifier" || node_type = "variable" then
    Some node
  else
    (* Recursively check children... *)
```

### Part 2: Scope-Aware Definition Lookup
Added a new function `find_definition_at_position` in `SymbolTable.ml` that:
1. Finds which function contains the cursor position
2. Filters variable/parameter symbols to only those defined within that function
3. Maintains prioritization: parameters > variables > other symbols

```ocaml
let find_definition_at_position symbols name position =
  (* Find containing function *)
  let containing_function = 
    List.find_opt (fun sym ->
      sym.kind = Function &&
      (* Check if position is within function's range *)
      ...
    ) symbols
  in
  
  (* Filter variables/parameters to those in the same function *)
  let scoped_syms = match containing_function with
    | Some func ->
        List.filter (fun sym ->
          match sym.kind with
          | Variable | Parameter ->
              (* Check if definition is within function bounds *)
              ...
          | _ -> true
        ) matching_symbols
    | _ -> matching_symbols
  in
  
  (* Return the scoped symbol with prioritization *)
  ...
```

### Part 3: Integration
Updated `receive_text_document_definition_request` in `LspProtocol.ml` to:
1. Use `find_identifier_at_point` to get the symbol at cursor
2. Call `find_definition_at_position` (the new scope-aware function) instead of `find_definition`

## Files Modified

1. **jasmin-lsp/Document/SymbolTable.ml**
   - Added `find_definition_at_position` function with scope filtering logic

2. **jasmin-lsp/Document/SymbolTable.mli**
   - Added interface declaration for `find_definition_at_position`

3. **jasmin-lsp/Protocol/LspProtocol.ml**
   - Added `find_identifier_at_point` helper function
   - Updated definition request handler to use scope-aware lookup

4. **jasmin-lsp/Document/AstIndex.ml**
   - Added logging (for debugging, can be removed)

## Testing

Created `test_simple_scope.py` which:
1. Creates a test file with two functions, each with a `status` variable
2. Opens the file in the LSP
3. Requests definition for the second `status` in `status = status;` in the second function
4. Verifies it jumps to the correct line (line 20, not line 7)

### Test Results
```
✅ SUCCESS: Correctly jumped to 'reg u32 status;' in ml_dsa_44_verify!
   The scope resolution bug is FIXED!
```

## Impact

This fix ensures that:
- ✅ Go to Definition respects function scope
- ✅ Variables with the same name in different functions are correctly distinguished
- ✅ Parameters and local variables within a function are correctly resolved
- ✅ Cross-file symbol resolution still works (unchanged)
- ✅ Function and constant lookups still work (unchanged)

## Notes

- LSP uses 0-indexed line numbers internally, while editors typically display 1-indexed line numbers
- Tree-Sitter node types for variables include both `identifier` (in declarations) and `variable` (in usages)
- The fix maintains backward compatibility - symbols not in functions (globals, etc.) still work as before
- Logging was added during development and can be removed or adjusted for production

## Date
October 12, 2025
