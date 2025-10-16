# Diagnostics Debugging Session - Final Status

**Date:** October 16, 2025  
**Status:** IN PROGRESS - Additional fixes applied

## Summary of All Fixes Applied

### Fix #1: Tree-Sitter Library Loading ✅
**File:** `jasmin-lsp/tree-sitter-jasmin/Makefile` line 36  
**Change:** Use `@rpath` instead of hardcoded `/usr/local/lib/` path  
**Status:** WORKING

### Fix #2: ERROR Node Detection in Diagnostics ✅  
**File:** `jasmin-lsp/Protocol/LspProtocol.ml` line ~1020  
**Change:** Added check for `node_type_str = "ERROR"`  
**Status:** WORKING (confirmed via tree-sitter parse)

### Fix #3: Prevent Crash on Symbol Extraction ✅
**Files:**
- `jasmin-lsp/Document/SymbolTable.ml` line ~456
- `jasmin-lsp/Protocol/LspProtocol.ml` line ~742

**Changes:**
1. Skip ERROR nodes before accessing range
2. Wrap entire `extract_symbols_from_node` in try-catch  
3. Wrap `receive_text_document_document_symbol_request` in try-catch

**Status:** SHOULD BE WORKING

### Fix #4: Enhanced Diagnostic Logging 🆕
**File:** `jasmin-lsp/Protocol/LspProtocol.ml`  
**Change:** Added node visit counter and detailed logging

**Purpose:** To see:
- How many nodes are being visited
- If ERROR nodes are being found
- Where the diagnostic collection is failing

---

## Current Status: Diagnostics Still Not Showing

### What We Know
1. ✅ Tree-sitter **IS** detecting errors (tested with CLI)
2. ✅ ERROR nodes **ARE** being created in parse tree
3. ❌ Diagnostics **ARE NOT** being sent to client
4. ❌ Still seeing "Collected 0 diagnostics" in logs

### Possible Causes

#### Theory #1: Parse Tree Not Being Scanned Properly
The `collect_diagnostics` function might not be traversing all nodes.

**Test:** Enhanced logging will show:
```
[LOG] : Visited X nodes, found Y errors
```

If `X = 0` → Function not being called  
If `X > 0` but `Y = 0` → Not finding ERROR nodes in tree

#### Theory #2: Diagnostics Collected But Not Sent
Diagnostics might be collected but the `send_diagnostics` function isn't being called or is failing.

**Check logs for:**
- Is `send_diagnostics` being called?
- Are diagnostics being serialized to JSON?
- Are they being sent to the client?

#### Theory #3: Tree Structure Mismatch
The tree-sitter C library might be returning a different structure than expected.

**Possible issues:**
- `node_named_child_count` returning 0
- `node_named_child` returning None
- ERROR nodes not being named children

#### Theory #4: Multiple Parse Trees
There might be multiple parse trees and we're checking the wrong one.

**Check:**
- Is the tree being recreated without errors?
- Are we using a cached tree from before errors were added?

---

## Next Steps to Debug

### 1. Check if scan function is running
Look in the new log for:
```
[LOG] : Visited X nodes, found Y errors
```

- If `X = 0`: The recursive visit isn't working
- If `X > 0, Y = 0`: ERROR nodes not being found as children

### 2. Try scanning ALL children (not just named)
The issue might be that ERROR nodes are **unnamed** children.

Change in `collect_diagnostics`:
```ocaml
(* Instead of node_named_child_count *)
let child_count = TreeSitter.node_child_count node in

(* Instead of node_named_child *)
match TreeSitter.node_child node i with
```

### 3. Log the root node type
Add at the start of `collect_diagnostics`:
```ocaml
let root_type = TreeSitter.node_type root in
Io.Logger.log (Format.asprintf "Scanning tree, root type: %s" root_type);
```

### 4. Check if diagnostics are being filtered
Maybe diagnostics are collected but filtered out before sending.

Look for any code that:
- Filters diagnostics by severity
- Limits number of diagnostics
- Clears diagnostics under certain conditions

---

## Test Case

Create this file to test:
```jasmin
fn test() -> reg u32 {
    ;;;
    return 0;
}
```

Expected tree-sitter output:
```
(ERROR [1, 4] - [1, 7])
```

Expected diagnostic:
- Line 1, columns 4-7
- Message: "Syntax error"
- Severity: Error

---

## Files Modified This Session

| Order | File | Purpose |
|-------|------|---------|
| 1 | `tree-sitter-jasmin/Makefile` | Fix library loading |
| 2 | `Io/Logger.ml` | Add file logging |
| 3 | `jasmin_lsp.ml` | Initialize file logging |
| 4 | `Protocol/LspProtocol.ml` | Fix ERROR detection |
| 5 | `Protocol/LspProtocol.ml` | Add try-catch for symbols |
| 6 | `Document/SymbolTable.ml` | Skip ERROR nodes |
| 7 | `Document/SymbolTable.ml` | Add try-catch |
| 8 | `Protocol/LspProtocol.ml` | Enhanced logging |

---

## Commands to Test

### 1. Reload VS Code
```
Cmd+Shift+P → "Developer: Reload Window"
```

### 2. Open a file with errors
Type `;;;` in a Jasmin file

### 3. Check the log
```bash
cd jasmin-lsp
./view-log.sh -f
```

### 4. Look for these log lines
```
[LOG] : Visited X nodes, found Y errors
[LOG] : Found ERROR node type: ...
[LOG] : Collected X diagnostics
```

### 5. Verify tree-sitter CLI
```bash
cd tree-sitter-jasmin
tree-sitter parse /path/to/file.jazz
# Should show (ERROR ...) nodes
```

---

## If Diagnostics Still Don't Work

### Check these specific things:

1. **Is the LSP server running?**
   ```bash
   ps aux | grep jasmin_lsp
   ```

2. **Are logs being written?**
   ```bash
   ls -lt ~/.jasmin-lsp/*.log | head -1
   ```

3. **Is the file being opened?**
   Look for: `Opening document: file:///.../file.jazz`

4. **Is collect_diagnostics being called?**
   Look for: `Visited X nodes`

5. **Are ERROR nodes being found?**
   Look for: `Found ERROR node type:`

6. **Are diagnostics being sent?**
   Look for JSON with `"method":"textDocument/publishDiagnostics"`

---

## Most Likely Issue

Based on patterns, the most likely issue is:

**ERROR nodes are UNNAMED children, not NAMED children**

The current code only scans named children:
```ocaml
let child_count = TreeSitter.node_named_child_count node in
```

But tree-sitter might create ERROR as unnamed children.

**Fix:** Change to scan ALL children (named and unnamed)

---

## Contact Points for Further Help

If you need to provide logs or ask for help:
1. Latest log file: `~/.jasmin-lsp/jasmin-lsp-*.log` (most recent)
2. Key search terms: "Visited", "ERROR", "diagnostics"
3. Tree-sitter test: Output of `tree-sitter parse file.jazz`
