# Close Buffer Diagnostics Implementation

## Summary

Implemented intelligent diagnostics clearing when closing files, based on whether the file is in the master file dependency tree or not.

## Behavior

### When Closing a File

1. **File IS in master file dependency tree** (e.g., utils.jinc required by main.jazz):
   - File is kept in memory (DocumentStore)
   - Diagnostics are re-sent to ensure they remain visible
   - Problems panel continues to show errors for this file
   - Future edits to other files may still trigger re-analysis

2. **File is NOT in master file dependency tree** (e.g., unrelated.jinc):
   - File is closed and removed from DocumentStore
   - Diagnostics ARE cleared immediately with empty diagnostics message
   - Editor no longer shows errors for the closed file
   - Keeps the Problems panel clean and relevant

3. **No master file set**:
   - All closed files are removed from DocumentStore
   - Diagnostics are cleared for all closed files
   - Fallback to conservative behavior

## Implementation

### Changes to `LspProtocol.ml`

1. **`TextDocumentDidClose` handler** - Enhanced to check dependency tree:
```ocaml
| Lsp.Client_notification.TextDocumentDidClose params ->
    let uri = params.textDocument.uri in
    
    (* Check if this file is in the master file dependency tree *)
    let in_dependency_tree = 
      match ServerState.get_master_file (!server_state) with
      | Some master_uri ->
          let all_files = collect_required_files_recursive master_uri [] in
          List.mem uri all_files || uri = master_uri
      | None -> false
    in
    
    if in_dependency_tree then
      (* Keep file in memory and re-send diagnostics *)
      send_diagnostics_single uri
    else (
      (* Close file and clear diagnostics *)
      Document.DocumentStore.close_document (!server_state).document_store uri;
      (* Send empty diagnostics to clear Problems panel *)
      ...
    )
```

2. **`send_diagnostics` function** - Enhanced to include ALL open buffers:
```ocaml
(** Send diagnostics for a document and all its dependencies, plus all open buffers *)
and send_diagnostics uri =
    (* Get all relevant files from dependency tree *)
    let dep_tree_files = get_all_relevant_files uri in
    
    (* Get all open files *)
    let all_open_files = Document.DocumentStore.get_all_uris (!server_state).document_store in
    
    (* Combine: dependency tree files + all open files (remove duplicates) *)
    let files_to_diagnose = List.fold_left (fun acc file_uri ->
      if List.mem file_uri acc then acc else file_uri :: acc
    ) dep_tree_files all_open_files in
    
    (* Send diagnostics for each open file *)
```

### Test Coverage

### New Test: `test_close_buffer_diagnostics.py`

Tests the following scenarios:

1. **Setup**: 4 files - 3 in dependency tree (utils.jinc → module.jinc → main.jazz), 1 unrelated
   - `utils.jinc` contains a syntax error (missing semicolon) to verify diagnostics are preserved
2. **Test 1**: Close `utils.jinc` (IN tree) - diagnostics RE-SENT and kept visible ✓
3. **Test 2**: Close `unrelated.jinc` (NOT in tree) - diagnostics ARE cleared ✓
4. **Test 3**: Modify `main.jazz` - only open files get updated diagnostics

### Test Results

```
✓ All 110 tests passing
✓ New test: test_close_buffer_diagnostics passes
✓ No regressions in existing tests
```

## Benefits

1. **Clean Problems Panel**: Only shows errors for relevant files
2. **Master File Awareness**: Respects project structure defined by master file
3. **All Open Buffers Get Diagnostics**: Any open file receives diagnostics, even if not in dependency tree
4. **Smart Cleanup**: Automatically clears diagnostics when closing irrelevant files
5. **Persistent Diagnostics for Dependencies**: Files in dependency tree keep diagnostics visible even when closed

## Edge Cases Handled

- **No master file set**: Falls back to clearing diagnostics for all closed files
- **Master file itself**: Correctly identified as "in dependency tree" and kept in memory
- **Open files outside dependency tree**: Still receive diagnostics while open
- **Closed files in dependency tree**: Kept in memory with diagnostics re-sent to ensure visibility
- **Files with no errors**: Still handled correctly (0 diagnostics re-sent)

## Logging

The implementation includes detailed logging:
```
[LOG] : Closing document: file:///path/to/file.jazz
[LOG] : File is in dependency tree, keeping in memory and diagnostics: ...
```
or
```
[LOG] : File not in dependency tree, closing and clearing diagnostics: ...
```
