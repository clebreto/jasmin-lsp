# Transitive Dependency Resolution Implementation

## Overview

This document describes the implementation of transitive dependency resolution for the Jasmin LSP server. The problem was that symbols defined in transitively required files (A requires B requires C) were not found during symbol lookup operations.

## Problem Statement

Previously, when a file A requires file B, which in turn requires file C:
```jasmin
// base.jinc (C)
param int BASE_CONSTANT = 42;

// middle.jinc (B)
require "base.jinc"

// top.jazz (A)
require "middle.jinc"
export fn test() {
  reg u64 x = BASE_CONSTANT;  // <-- This would fail
}
```

When hovering or going to definition for `BASE_CONSTANT` in `top.jazz`, the LSP would report "No definition found" because it only searched:
1. The current file (`top.jazz`)
2. Files currently open in the editor

It did NOT follow the `require` chain to load and search `base.jinc`.

## Root Cause

The LSP protocol only has knowledge of files that are explicitly opened by the editor. The server needs to:
1. Parse `require` statements from files
2. Recursively follow the dependency chain
3. Load files from disk even if they're not open
4. Search all reachable files for symbol definitions

## Solution Architecture

### 1. Require Extraction (SymbolTable.ml)

Added function to extract all `require` statements from a parsed AST:

```ocaml
let rec extract_requires_from_node uri source node acc =
  (* Recursively traverse the tree looking for require_declaration nodes *)
  ...

let extract_required_files uri source tree =
  (* Returns a list of absolute file URIs for all required files *)
  ...
```

This handles both `require` syntaxes:
- `require "file.jazz"` - simple relative path
- `from NAMESPACE require "file.jazz"` - namespaced require

### 2. Transitive Dependency Collection (LspProtocol.ml)

Added two helper functions to recursively collect all reachable files:

```ocaml
let rec collect_required_files_recursive uri visited =
  (* Recursively follow requires, avoiding cycles with visited set *)
  if List.mem uri visited then visited
  else
    let visited = uri :: visited in
    match load_and_parse_file uri with
    | Some (tree, source) ->
        let requires = SymbolTable.extract_required_files uri source tree in
        List.fold_left (fun acc req_uri ->
          collect_required_files_recursive req_uri acc
        ) visited requires
    | None -> visited

let get_all_relevant_files uri =
  (* Returns open files + transitive dependencies *)
  let open_files = DocumentStore.get_all_uris doc_store in
  let all_deps = collect_required_files_recursive uri [] in
  (* Combine and deduplicate *)
  ...
```

### 3. Updated LSP Handlers

Modified three main handlers to use transitive dependency resolution:

#### a. Go to Definition
```ocaml
(* Before *)
let all_uris = DocumentStore.get_all_uris doc_store in

(* After *)
let all_uris = get_all_relevant_files uri in
```

Now searches:
- Current file
- All open files
- All transitively required files (loaded from disk if needed)

#### b. Hover
Same change: replaced `get_all_uris` with `get_all_relevant_files`.

#### c. Find References
Updated to search across all relevant files, including transitive dependencies.

### 4. File Loading Strategy

For files not currently open in the editor, the implementation:
1. Converts URI to filesystem path
2. Reads file contents from disk
3. Parses using tree-sitter
4. Extracts symbols
5. Searches for the requested symbol

```ocaml
let tree_opt, source_opt =
  match DocumentStore.get_tree doc_store uri with
  | Some t, Some s -> Some t, Some s  (* Use open file *)
  | _ ->
      (* Load from disk *)
      try
        let path = Lsp.Uri.to_path uri in
        if Sys.file_exists path then
          let content = read_file path in
          let parsed = TreeSitter.parse_string content in
          Some parsed, Some content
        else None, None
      with _ -> None, None
```

## Files Modified

### SymbolTable.ml
- Added `extract_requires_from_node` (~60 lines) - Recursively extracts require declarations
- Added `extract_required_files` (~10 lines) - Public interface for require extraction

### SymbolTable.mli
- Added `extract_required_files` signature

### LspProtocol.ml
- Added `collect_required_files_recursive` (~20 lines) - Recursive dependency collector with cycle detection
- Added `get_all_relevant_files` (~25 lines) - Combines open files with transitive deps
- Modified `receive_text_document_definition_request` (~40 lines changed) - Uses transitive deps, loads files from disk
- Modified `receive_text_document_hover_request` (~35 lines changed) - Same changes
- Modified `receive_text_document_references_request` (~50 lines changed) - Searches across all relevant files

Total: ~230 lines added/modified across 3 files

## Testing

### Test Structure
Created test files in `test/fixtures/transitive/`:

```
test/fixtures/transitive/
  ├── base.jinc       # Defines BASE_CONSTANT
  ├── middle.jinc     # Requires base.jinc, defines MIDDLE_CONSTANT
  └── top.jazz        # Requires middle.jinc, uses BASE_CONSTANT
```

### Manual Test Procedure
1. Open `top.jazz` in VS Code
2. Hover over `BASE_CONSTANT` (line 8)
   - Expected: Shows "param int BASE_CONSTANT = 42" from base.jinc
3. Go to definition for `BASE_CONSTANT`
   - Expected: Jumps to base.jinc line 2

### Running Tests
```bash
# View test structure
./test_transitive_manual.sh

# Build and install
pixi run build

# Manual test in VS Code
code test/fixtures/transitive/top.jazz
```

## Performance Considerations

### Cycle Detection
The `collect_required_files_recursive` function maintains a `visited` list to avoid infinite loops in case of circular dependencies.

### File Caching
Files loaded from disk are parsed but not cached in the DocumentStore. Each lookup re-reads from disk. This could be optimized by caching parsed trees for required files.

### Search Strategy
Search order:
1. Current file (fast - already in memory)
2. Open files (fast - already parsed)
3. Transitively required files (slower - may need disk I/O and parsing)

## Edge Cases Handled

1. **Circular dependencies**: Prevented by visited list
2. **Missing files**: Gracefully ignored, search continues
3. **Parse errors**: Caught and logged, search continues
4. **Absolute vs relative paths**: Properly resolved relative to requiring file
5. **Namespaced requires**: Handled by require extraction

## Limitations

1. **Namespace resolution**: Currently treats namespaced requires (`from X require "file"`) as simple relative paths. May need enhancement for complex namespace scenarios.

2. **Performance**: Large projects with deep dependency trees may experience slower symbol lookup. Consider implementing:
   - Cache for required file parse trees
   - Dependency graph pre-computation
   - Incremental updates

3. **Workspace vs file-local dependencies**: Currently follows all requires. May want to respect workspace boundaries in multi-workspace scenarios.

## Logging

Added debug logging to track dependency resolution:
```
[LOG] Found %d requires in file: %s
[LOG] Total files including dependencies: %d
[LOG] Found definition in file: %s
```

Enable with LSP server debug mode to diagnose issues.

## Future Enhancements

1. **Dependency Graph Visualization**: Show require chain in UI
2. **Caching**: Cache parsed trees for required files
3. **Workspace Analysis**: Pre-compute full dependency graph on workspace open
4. **Incremental Updates**: Update dependency graph when files change
5. **Performance Metrics**: Track lookup times and optimize hot paths

## References

- Original issue: "variables defined in a file required in a file required in another file lead to No definition found"
- Jasmin language spec: Module system with `require` directive
- LSP specification: Symbol lookup across files
