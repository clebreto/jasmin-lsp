# Build Fix Summary

## Issue
The build was failing with the error:
```
Error: Unbound value TreeSitter.parse_string
```

## Root Cause
The code was calling `TreeSitter.parse_string` which doesn't exist. The correct function is `TreeSitter.parser_parse_string`, and it:
1. Requires a `parser` instance as the first argument
2. Returns `tree option` (not `tree`)

## Fix Applied
Changed all three occurrences in `LspProtocol.ml`:

### Before (incorrect):
```ocaml
let parsed_tree = TreeSitter.parse_string content in
Some parsed_tree, Some content
```

### After (correct):
```ocaml
let parser = Document.DocumentStore.get_parser () in
let parsed_tree = TreeSitter.parser_parse_string parser content in
parsed_tree, Some content
```

## Changes
- Line 193-198: Go to definition handler - Fixed parser call
- Line 276-283: Find references handler - Fixed parser call  
- Line 379-389: Hover handler - Fixed parser call

## Result
✅ Build now succeeds
✅ Executable created: `_build/default/jasmin-lsp/jasmin_lsp.exe` (8.1M)

## Testing
Ready to test transitive dependency resolution:
1. Open VS Code in the workspace
2. Open `test/fixtures/transitive/top.jazz`
3. Test hover and go-to-definition for `BASE_CONSTANT`
4. Should find the symbol in `base.jinc` even though it's transitively required
