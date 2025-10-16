# Dependent File Diagnostics Implementation

## Overview

Enhanced the LSP server to send diagnostics not just for the currently edited file, but also for all files in its dependency chain. This provides real-time feedback across the entire project when a file is modified.

## Problem

Previously, when editing a file, diagnostics were only sent for that specific file. If the file had syntax errors that would affect dependent files (files that `require` it), or if it depended on other files, those diagnostics would not be updated until each file was individually opened or edited.

## Solution

Modified the `send_diagnostics` function in `LspProtocol.ml` to:

1. **Identify all relevant files** using `get_all_relevant_files(uri)`:
   - If a master file is configured, start from the master file and traverse all `require` statements recursively
   - Otherwise, start from all open files and collect their dependencies
   
2. **Filter to open files only**: Only send diagnostics for files that are currently open in the editor (in the DocumentStore). This avoids expensive disk I/O and potential issues with loading many files.

3. **Send diagnostics for each open file** in the dependency chain using `send_diagnostics_single`.

## Implementation Details

### Modified Functions

**`send_diagnostics` in `jasmin-lsp/Protocol/LspProtocol.ml`:**
```ocaml
and send_diagnostics uri =
  try
    (* Get all relevant files (including dependencies) *)
    let all_files = get_all_relevant_files uri in
    
    (* Filter to only open files *)
    let open_files = List.filter (fun file_uri ->
      Document.DocumentStore.is_open (!server_state).document_store file_uri
    ) all_files in
    
    (* Send diagnostics for each open file *)
    let events = List.concat_map (fun file_uri ->
      send_diagnostics_single file_uri
    ) open_files in
    
    events
  with e ->
    (* Error handling *)
    []
```

**`send_diagnostics_single`** (new helper function):
- Sends diagnostics for a single document that's already in the DocumentStore
- Separated from the main `send_diagnostics` function to avoid recursion
- Uses the tree-sitter parse tree and `collect_diagnostics` to find errors

### Existing Infrastructure Used

The implementation leverages existing functions:

- **`get_all_relevant_files`**: Already implemented to collect master file + transitive dependencies
- **`collect_required_files_recursive`**: Recursively follows `require` statements
- **`Document.SymbolTable.extract_required_files`**: Parses `require` statements from syntax tree
- **`Document.DocumentStore.is_open`**: Checks if a file is currently open

## Behavior

### When Editing a File

1. User edits `utils.jinc` (has syntax error)
2. LSP receives `textDocument/didChange` notification
3. `send_diagnostics` is called for `utils.jinc`
4. System identifies all open dependent files:
   - `utils.jinc` (the edited file)
   - `module.jinc` (requires `utils.jinc`)
   - `main.jazz` (requires `module.jinc`)
5. Diagnostics are sent for **all three files**
6. VS Code updates the PROBLEMS panel with errors from all files

### Scope Limitation

- **Only open files** receive updated diagnostics
- Files not open in the editor are skipped (even if in dependency chain)
- This is intentional to avoid:
  - Loading many files from disk (expensive I/O)
  - Overwhelming the editor with diagnostics for files the user isn't looking at
  - Potential crashes or hanging from processing too many files

## Testing

### Test File: `test/test_diagnostics/test_dependent_diagnostics.py`

Creates a three-file dependency chain:
```
utils.jinc  ← (required by) ← module.jinc  ← (required by) ← main.jazz
```

**Test Steps:**
1. Open all three files with valid syntax
2. Verify initial diagnostics: 0 errors for all files
3. Edit `utils.jinc` to introduce syntax error `[;]`
4. Verify updated diagnostics are sent for all 3 files
5. Confirm `utils.jinc` has 1+ diagnostic

**Test Result:**
```
✓ SUCCESS: Diagnostics sent for dependent files!
  Updated diagnostics received: 6 messages
  Total files that received diagnostics: 3
```

## Benefits

1. **Real-time project-wide feedback**: See how changes affect dependent files immediately
2. **Better developer experience**: No need to manually open each file to see errors
3. **Efficient**: Only processes files already in memory (open in editor)
4. **Respects master file configuration**: Uses configured entry point for dependency resolution

## Test Suite Results

- **106 tests passing** (increased from 105)
- **2 skipped**, **1 xfailed** (unchanged)
- New test: `test_dependent_diagnostics.py::test_diagnostics_for_dependent_files` ✓

## Future Enhancements

Potential improvements:
1. **Configurable depth limit**: Allow limiting how deep in the dependency chain to send diagnostics
2. **Smart caching**: Remember which files have been checked and avoid redundant parsing
3. **Background processing**: Send diagnostics for closed files in background without blocking
4. **Diagnostic aggregation**: Show summary of errors across all dependent files
