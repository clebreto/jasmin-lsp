# Tree Lifetime Crash Fix

## Problem

The LSP server was crashing when hovering over symbols that required searching through multiple dependency files. The logs showed:

```
[LOG] : Hover: Looking for symbol 'ETA'
[LOG] : Starting with 3 open files
[LOG] : Total files including dependencies: 7
[Info  - 9:36:08 PM] Connection to server got closed. Server will restart.
```

## Root Cause

When the LSP server processes hover, definition, or reference requests, it may need to search through multiple files including dependencies. For files not currently open in the editor, the code would:

1. Load the file from disk
2. Parse it with Tree-sitter to create a temporary tree
3. Extract symbols from the tree
4. Recursively search the next file

The problem was that the temporary trees created in step 2 were not being kept alive long enough. When the recursive call searched the next file, OCaml's garbage collector could run and finalize (delete) the trees from previous iterations. Since Tree-sitter trees have finalizers that call `ts_tree_delete()`, this could cause:

- Use-after-free if any nodes were still being referenced
- Crashes when accessing freed tree memory
- Race conditions between tree access and finalization

## Solution

Modified the recursive search functions to accumulate all temporary trees in a list parameter, keeping them alive until the entire search completes:

### Files Modified

**`jasmin-lsp/Protocol/LspProtocol.ml`**

### Changes Made

#### 1. Hover Request Handler (`receive_text_document_hover_request`)

**Before:**
```ocaml
let rec search_documents uris =
  match uris with
  | [] -> None
  | doc_uri :: rest ->
      (* Load file, parse tree, extract symbols *)
      let parsed_tree = TreeSitter.parser_parse_string parser content in
      (* ... use tree ... *)
      search_documents rest  (* Tree goes out of scope here! *)
```

**After:**
```ocaml
let rec search_documents uris acc_trees =
  match uris with
  | [] -> 
      (* Keep trees alive until search completes *)
      let _ = acc_trees in
      None
  | doc_uri :: rest ->
      (* Load file, parse tree, extract symbols *)
      let parsed_tree = TreeSitter.parser_parse_string parser content in
      let new_acc = match parsed_tree with
        | Some t -> t :: acc_trees  (* Keep tree alive *)
        | None -> acc_trees
      in
      (* ... use tree immediately ... *)
      search_documents rest new_acc  (* Tree kept in accumulator *)
```

#### 2. Definition Request Handler (`receive_text_document_definition_request`)

Applied the same pattern to the `search_files` recursive function.

#### 3. References Request Handler (`receive_text_document_references_request`)

Modified the `fold_left` to accumulate both references and trees:

**Before:**
```ocaml
let all_references = List.fold_left (fun acc doc_uri ->
  (* Load file, parse tree, extract references *)
  acc @ matching_refs  (* Tree can be GC'd *)
) [] all_uris
```

**After:**
```ocaml
let all_references, _ = List.fold_left (fun (acc, trees) doc_uri ->
  (* Load file, parse tree, extract references *)
  let new_trees = match parsed_tree with
    | Some t -> t :: trees  (* Keep tree alive *)
    | None -> trees
  in
  (acc @ matching_refs, new_trees)
) ([], []) all_uris
```

### Additional Improvements

Added better error logging with stack traces:
```ocaml
with e ->
  Io.Logger.log (Format.asprintf "Error extracting symbols from %s: %s\n%s"
    (Lsp.Types.DocumentUri.to_string doc_uri)
    (Printexc.to_string e)
    (Printexc.get_backtrace ()));
```

## Key Insights

1. **Tree-sitter trees have finalizers**: Trees are automatically deleted by the OCaml GC when they go out of scope
2. **Recursive calls can trigger GC**: Each recursive call builds up stack frames, potentially triggering garbage collection
3. **Accumulator pattern for lifetime management**: Keeping trees in an accumulator list ensures they stay alive for the entire search
4. **Extract symbols immediately**: The code already extracted symbols immediately after parsing, which was good, but the trees still needed to be kept alive

## Testing

The fix should be tested with:
1. Hovering over symbols in files with many dependencies
2. Go-to-definition across multiple files
3. Find references across large codebases
4. Rapid consecutive requests that might trigger GC

## Memory Implications

This fix does increase memory usage slightly, as all temporary trees are kept in memory until the search completes. However:
- Trees are only kept for the duration of a single request
- They are automatically freed when the request completes
- This is necessary to prevent crashes
- The memory overhead is small compared to parsing all files multiple times

## Alternative Approaches Considered

1. **Caching parsed trees**: Would use more memory long-term
2. **Manual tree deletion**: Risky and error-prone with finalizers
3. **Disabling GC during search**: Too coarse-grained and affects performance
4. **Opening all dependency files**: Would bloat the document store unnecessarily

The accumulator approach is the cleanest solution that balances safety and memory usage.
