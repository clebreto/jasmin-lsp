# Real-Time Diagnostics Implementation

**Date**: October 16, 2025
**Status**: ✅ Complete

## Overview

Enhanced the Jasmin LSP server to provide real-time diagnostics (PROBLEMS panel updates) whenever `.jazz` or `.jinc` files are modified, both in the editor and externally on disk.

## Implementation

### What Was Already Working

The LSP server already had diagnostics functionality that sends syntax errors to VS Code in real-time:

1. **TextDocumentDidOpen**: Sends diagnostics when a file is opened
2. **TextDocumentDidChange**: Sends diagnostics when file content changes in the editor
3. **Diagnostics Collection**: Uses tree-sitter to detect syntax errors (missing tokens, error nodes)

### What Was Added

Added support for **external file changes** via the `DidChangeWatchedFiles` notification:

```ocaml
| Lsp.Client_notification.DidChangeWatchedFiles params ->
    (* Handle external file changes *)
    Io.Logger.log (Format.asprintf "Watched files changed: %d files" 
      (List.length params.changes));
    (* Re-send diagnostics for all changed files that are open *)
    let events = List.concat_map (fun (change : Lsp.Types.FileEvent.t) ->
      let uri = change.uri in
      (* Check if the file is currently open in the editor *)
      match Document.DocumentStore.get_document (!server_state).document_store uri with
      | Some _ ->
          (* File is open, re-send diagnostics *)
          Io.Logger.log (Format.asprintf "Re-sending diagnostics for watched file: %s" 
            (Lsp.Types.DocumentUri.to_string uri));
          send_diagnostics uri
      | None ->
          (* File is not open, no need to send diagnostics *)
          []
    ) params.changes in
    events
```

**File Modified**: `jasmin-lsp/jasmin-lsp/Protocol/LspProtocol.ml`

## How It Works

### In-Editor Changes (Already Working)
1. User types in a `.jazz` or `.jinc` file
2. VS Code sends `TextDocumentDidChange` notification
3. LSP server parses the file with tree-sitter
4. Syntax errors are detected (missing semicolons, unclosed braces, etc.)
5. Diagnostics are sent via `PublishDiagnostics` notification
6. VS Code displays errors in PROBLEMS panel immediately

### External File Changes (Newly Added)
1. File is modified externally (git pull, external editor, etc.)
2. VS Code file watcher detects the change
3. VS Code sends `DidChangeWatchedFiles` notification
4. LSP server checks if the file is currently open
5. If open, re-sends diagnostics for that file
6. PROBLEMS panel updates automatically

### VS Code Extension Configuration

The extension already had proper configuration for watching files:

```typescript
synchronize: {
  // Notify the server about file changes to '.jazz' and '.jinc' files
  fileEvents: workspace.createFileSystemWatcher('**/*.{jazz,jinc}'),
  configurationSection: 'jasmin'
},
diagnosticCollectionName: 'jasmin',
```

## Diagnostic Types

The LSP server currently detects **syntax errors** using tree-sitter:
- Missing tokens (e.g., missing semicolons)
- Error nodes (malformed syntax)
- Unclosed braces
- Invalid function signatures
- Other parsing errors

## Testing

### Manual Testing Steps

1. **Open a `.jazz` file** in VS Code
   - PROBLEMS panel should show any syntax errors immediately

2. **Edit the file and introduce an error**:
   ```jasmin
   fn test() -> reg u64 {
     reg u64 x;
     x = 5  // Missing semicolon
     return x;
   }
   ```
   - PROBLEMS panel should update in real-time

3. **Save the file** (Ctrl/Cmd+S)
   - Diagnostics remain current

4. **Modify file externally** (e.g., via git or another editor)
   - PROBLEMS panel should update when file is detected as changed

### Test Files Available

Use existing test file with intentional errors:
- `jasmin-lsp/test/fixtures/syntax_errors.jazz`

## Build Instructions

To rebuild the LSP server with these changes:

```bash
cd jasmin-lsp
git submodule update --init --recursive
pixi run build
```

The executable will be at: `_build/default/jasmin-lsp/jasmin_lsp.exe`

## Extension Setup

Configure VS Code to use the built LSP server:

1. Install the `vsjazz` extension (jasmin-lang.vsjazz)
2. Configure in workspace settings (`.vscode/settings.json`):
   ```json
   {
     "jasmin.path": "${workspaceFolder}/jasmin-lsp/_build/default/jasmin-lsp/jasmin_lsp.exe"
   }
   ```
3. Reload VS Code window

## Verification

To verify diagnostics are working:

1. Open a `.jazz` file
2. Check Output panel → Jasmin Language Server
3. Look for log messages like:
   - "Collected N diagnostics"
   - "Watched files changed: N files"
   - "Re-sending diagnostics for watched file: ..."

## Future Enhancements

Potential improvements for diagnostics:

1. **Semantic Diagnostics**: Add type checking, undefined variable detection
2. **Warning Level**: Distinguish between errors and warnings
3. **Quick Fixes**: Suggest automatic fixes for common errors
4. **Diagnostic Codes**: Add error codes for better documentation lookup
5. **Related Information**: Link related errors (e.g., mismatched braces)

## Summary

✅ **Real-time diagnostics now work for**:
- Files opened in VS Code
- Content changes while editing
- External file modifications (with file watcher)

✅ **The PROBLEMS panel updates automatically** whenever `.jazz` or `.jinc` files are modified.

✅ **No configuration needed** - works out of the box once the LSP path is set.
