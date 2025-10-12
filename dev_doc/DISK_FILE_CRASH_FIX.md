# Critical Fix: Disk-Loaded File Crashes

## Issue

Server was crashing when processing multi-file projects with `require` statements, particularly when:
- Hovering over symbols defined in required files
- Requesting document symbols  
- Finding references across files

**Error Pattern:**
```
[LOG] : Total files including dependencies: 7
[Info] Connection to server got closed. Server will restart.
```

## Root Cause

When the server loaded files from disk (files not yet opened in the editor), it would:
1. Parse the file and create a tree-sitter tree
2. Extract symbols from that tree
3. The tree would become eligible for GC
4. **CRASH**: Trying to use nodes from the now-freed tree

The trees created for disk-loaded files weren't being stored anywhere, so they could be GC'd while nodes extracted from them were still being used. This is a **use-after-free** bug.

## The Fix

Restructured code to ensure symbol extraction happens **immediately** while the tree is still valid, before it can be GC'd:

### Before (Crashed):
```ocaml
let tree_opt, source_opt = 
  (* Load from disk, creates tree *)
  let parsed_tree = TreeSitter.parser_parse_string parser content in
  parsed_tree, Some content
in
(* Tree might be GC'd here! *)
match tree_opt, source_opt with
| Some tree, Some source ->
    (* CRASH: Using freed tree *)
    let symbols = extract_symbols uri source tree in
    ...
```

### After (Fixed):
```ocaml
let tree_opt, source_opt = 
  (* Load from disk *)
  let parsed_tree = TreeSitter.parser_parse_string parser content in
  parsed_tree, Some content
in
(* Extract symbols IMMEDIATELY while tree is valid *)
let result = 
  try
    match tree_opt, source_opt with
    | Some tree, Some source ->
        let symbols = extract_symbols uri source tree in
        (* Use symbols right away *)
        find_definition symbols name
    | _ -> None
  with e -> log_error e; None
in
(* Tree can be GC'd now - we're done with it *)
match result with ...
```

## Files Modified

`jasmin-lsp/Protocol/LspProtocol.ml` - Fixed 3 locations:
1. **Definition search** (`receive_text_document_definition_request`)
2. **References search** (`receive_text_document_references_request`)
3. **Hover** (`receive_text_document_hover_request`)

Each location now:
- ✅ Extracts data immediately while tree is valid
- ✅ Wraps operations in try-catch
- ✅ Logs errors properly
- ✅ Continues gracefully on error

## Testing

Created `test_multi_file_crash.py` to specifically test this scenario:
- Creates temp directory with 3 files (params.jinc, eta.jinc, main.jazz)
- Files have `require` statements linking them
- Opens all files
- Requests document symbols
- Hovers over cross-file references

**Result:** ✅ Test passes, no crashes

All existing tests still pass:
- ✅ 10/10 crash scenarios
- ✅ Stress tests
- ✅ Multi-file project test

## Key Lesson

When loading files from disk and parsing them on-demand:
1. **Extract all needed data immediately** while the tree is valid
2. **Don't store nodes** for later use - they reference the tree
3. **Store the extracted information** (symbols, ranges, etc.) instead
4. **Let the tree be GC'd** after extraction is complete

## Impact

This fix resolves the VSCode crashes that occurred when:
- Working with multi-file Jasmin projects
- Using `require` statements
- Hovering over symbols from required files
- Navigating between files

The server is now stable for real-world multi-file projects! 🎉
