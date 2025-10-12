# Cross-File Hover Fix

## Problem

Hover on variables and symbols defined in other files was not working correctly, especially when those files were not directly open in the editor. The issue occurred because:

1. The symbol table was built file-by-file during hover lookup
2. The source_map for constant evaluation was rebuilt for each file individually
3. Files loaded from disk were not properly integrated into the symbol resolution

## Solution

Modified the hover implementation to build a **complete source_map upfront** with all files reachable from the master file (or all open files if no master file is set).

### Key Changes

**File: `jasmin-lsp/Protocol/LspProtocol.ml`**

#### Before (around line 475):
```ocaml
let rec search_documents uris acc_trees =
  match uris with
  | [] -> 
      let _ = acc_trees in
      None
  | doc_uri :: rest ->
      (* Load file, parse, extract symbols *)
      let doc_symbols = extract_symbols_with_values doc_uri doc_source doc_tree all_uris in
      (* This rebuilt source_map for EACH file *)
      ...
```

#### After:
```ocaml
(* Build complete source map upfront with all files from master file dependency tree *)
let source_map = build_source_map all_uris in
Io.Logger.log (Format.asprintf "Hover: Source map built with %d entries" (Hashtbl.length source_map));

let rec search_documents uris =
  match uris with
  | [] -> None
  | doc_uri :: rest ->
      (* Extract basic symbols *)
      let doc_symbols = Document.SymbolTable.extract_symbols doc_uri doc_source doc_tree in
      (* Enhance with constant values using the complete source_map *)
      let doc_symbols_with_values = Document.SymbolTable.enhance_constants_with_values doc_symbols source_map in
      ...
```

### How It Works

1. **Master File Support**: When a master file is set via `jasmin/setMasterFile` notification, the LSP server uses it as the entry point for building the complete dependency tree.

2. **Complete Tree Building**: The `get_all_relevant_files` function recursively follows all `require` statements from the master file to build a complete list of all files in the dependency tree.

3. **Upfront Source Map**: The `build_source_map` function loads and parses all files in the dependency tree **once**, creating a hash table of `(uri -> (source, tree))` pairs.

4. **Constant Evaluation**: The `enhance_constants_with_values` function can now resolve constants that depend on values defined in other files, because it has access to the complete source_map with all files.

5. **Symbol Lookup**: During hover, symbols are looked up using the pre-built source_map, ensuring consistent and complete type information including computed constant values.

## Benefits

1. **Cross-File Resolution**: Hover now works on symbols defined in any file reachable from the master file
2. **Transitive Dependencies**: Works even for symbols defined in files that are not directly required (e.g., `BASE_CONSTANT` in `base.jinc` when hovering in `top.jazz` that only requires `middle.jinc`)
3. **Constant Value Computation**: Constants that reference other constants from different files are now computed correctly
4. **Performance**: Source map is built once per hover request instead of rebuilding for each file during search
5. **Consistency**: All files use the same source_map, ensuring consistent symbol resolution

## Testing

### Existing Test Files

The fix can be tested with existing test fixtures:
- `test/fixtures/transitive/top.jazz` (master file)
- `test/fixtures/transitive/middle.jinc` (requires base.jinc)
- `test/fixtures/transitive/base.jinc` (defines BASE_CONSTANT)

### Test Cases

1. **Direct Dependencies**: Hover on `middle_function` in `top.jazz` → should show function signature from `middle.jinc`
2. **Transitive Dependencies**: Hover on `BASE_CONSTANT` in `top.jazz` → should show `param BASE_CONSTANT: int = 42` from `base.jinc`
3. **Cross-File Functions**: Hover on `base_function` in `middle.jinc` → should show function signature from `base.jinc`
4. **Local Variables**: Hover on local variables should still work as before
5. **Computed Constants**: Constants that reference other constants should show computed values

### Manual Testing

1. Build the LSP server: `dune build`
2. Open VS Code with the extension
3. Open `test/fixtures/transitive/` as workspace
4. Set master file to `top.jazz` (via command palette or status bar)
5. Hover over symbols to verify cross-file resolution works

## Related Features

This fix also improves:
- **Goto Definition**: Already uses the same `get_all_relevant_files` mechanism
- **Find References**: Already searches across all files in the dependency tree
- **Document Symbols**: Local to single file, unaffected
- **Constant Evaluation**: Now works across multiple files

## Implementation Details

### Files Modified

- `jasmin-lsp/Protocol/LspProtocol.ml`: Modified `receive_text_document_hover_request` function

### Functions Used

- `get_all_relevant_files(uri)`: Returns list of all files reachable from master file (or all open files)
- `build_source_map(uris)`: Builds hash table of (uri -> (source, tree)) for all files
- `extract_symbols(uri, source, tree)`: Extracts basic symbols from a single file
- `enhance_constants_with_values(symbols, source_map)`: Adds computed constant values using complete source_map
- `find_definition(symbols, name)`: Finds symbol definition by name

### Master File Flow

```
User Sets Master File
  ↓
jasmin/setMasterFile notification
  ↓
ServerState.set_master_file(uri)
  ↓
Hover Request
  ↓
get_all_relevant_files(uri)
  ↓
collect_required_files_recursive(master_uri)
  ↓
build_source_map(all_uris)
  ↓
Search symbols with complete source_map
```

## Edge Cases Handled

1. **No Master File**: Falls back to using all open files as entry points
2. **File Not Found**: Gracefully handles missing required files
3. **Circular Dependencies**: Uses visited set to avoid infinite loops
4. **Parse Errors**: Handles files that fail to parse
5. **Unopened Files**: Loads files from disk if not already open

## Performance Considerations

- Source map is built once per hover request (not per file)
- Files are only parsed once (cached in source_map)
- Tree objects are kept alive during search to avoid GC
- Logarithmic lookup in hash table for symbol resolution

## Future Improvements

Potential optimizations:
1. Cache source_map across hover requests (invalidate on file changes)
2. Incremental updates when files change
3. Lazy loading of files (only load when symbols not found in already-loaded files)
4. Parallel file loading and parsing

## Conclusion

This fix ensures that hover works correctly across file boundaries by building a complete view of the project from the master file. All symbols in the dependency tree are now available for lookup, and constant values are computed using the complete context.
