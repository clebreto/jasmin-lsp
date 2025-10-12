# Jasmin LSP Quick Start Guide

## Build and Run

### Prerequisites
- [Pixi](https://pixi.sh/) package manager installed
- Git with submodules support
- OCaml environment (managed by pixi)

### Setup

```bash
# Clone with submodules
git clone --recursive <repository-url>
cd jasmin-lsp

# Or initialize submodules after clone
git submodule update --init --recursive

# Setup pixi environment (first time only)
pixi install

# Build the LSP server
pixi run build
```

### Fix Library Path (macOS)

After building, the executable needs a library path fix:

```bash
install_name_tool -change /usr/local/lib/libtree-sitter-jasmin.15.2025.dylib \
  @executable_path/../../../tree-sitter-jasmin/libtree-sitter-jasmin.dylib \
  _build/default/jasmin-lsp/jasmin_lsp.exe
```

### Run the Server

```bash
# Run directly
_build/default/jasmin-lsp/jasmin_lsp.exe

# Or use pixi task
pixi run run
```

## Testing

### Manual Test

```bash
# Test with a simple initialize request
MESSAGE='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}'
printf "Content-Length: ${#MESSAGE}\r\n\r\n${MESSAGE}" | _build/default/jasmin-lsp/jasmin_lsp.exe
```

### Automated Test

```bash
./test_lsp.sh
```

## VS Code Integration

### Option 1: Install System-Wide

```bash
# Install to system
dune install

# The binary will be at: ~/.opam/default/bin/jasmin-lsp
```

### Option 2: Use Build Artifact

Point your VS Code Jasmin extension to:
```
/path/to/jasmin-lsp/_build/default/jasmin-lsp/jasmin_lsp.exe
```

### VS Code Extension Configuration

In your Jasmin extension's `settings.json`:

```json
{
  "jasmin.lsp.path": "/path/to/jasmin-lsp/_build/default/jasmin-lsp/jasmin_lsp.exe",
  "jasmin.lsp.trace.server": "verbose"
}
```

## Features

### ✅ Working Features

1. **Syntax Diagnostics**
   - Real-time error detection
   - Published on file open/change
   - Shows exact error location

2. **Go to Definition** (F12 or Cmd+Click)
   - Jump to function definitions
   - Navigate to variable declarations
   - Find parameter definitions

3. **Find All References** (Shift+F12)
   - Shows all usages of a symbol
   - Works across the document
   - Highlights references

4. **Hover Information** (Mouse hover)
   - Shows function signatures
   - Displays variable types
   - Type information from tree-sitter

### ⚠️ Partially Available

5. **Document Symbols** (Cmd+Shift+O)
   - Outline view of functions/variables
   - *Currently commented out*

6. **Workspace Symbols** (Cmd+T)
   - Search symbols across files
   - *Currently commented out*

7. **Rename Symbol** (F2)
   - Rename across document
   - *Currently commented out*

### ❌ Not Yet Implemented

8. **Code Formatting**
   - Requires jasmin-format integration

9. **Code Actions** (Quick Fixes)
   - Requires semantic analysis

## Development

### Rebuild After Changes

```bash
# Full rebuild
pixi run clean
pixi run build

# Incremental build
pixi run build
```

### Debugging

Enable verbose logging in your LSP client or check stderr:

```bash
_build/default/jasmin-lsp/jasmin_lsp.exe 2> lsp.log
```

Log messages show:
- `[LOG] : Received RPC packet:` - Incoming requests
- `[LOG] : Opened document:` - File tracking
- `[LOG] : Failed to decode` - Protocol errors

### Common Issues

**Issue**: `dyld: Library not loaded: /usr/local/lib/libtree-sitter-jasmin.15.2025.dylib`  
**Fix**: Run the `install_name_tool` command shown above

**Issue**: `Error (warning 32 [unused-value-declaration])`  
**Fix**: Already fixed in dune with `-w -32` flag

**Issue**: Tree-sitter library not found  
**Fix**: Ensure pixi environment is activated: `pixi shell`

## Project Structure

```
jasmin-lsp/
├── jasmin-lsp/               # Main source directory
│   ├── TreeSitter/          # Tree-sitter bindings
│   │   ├── TreeSitter.mli
│   │   ├── TreeSitter.ml
│   │   └── tree_sitter_stubs.c
│   ├── Document/            # Document management
│   │   ├── DocumentStore.ml[i]
│   │   ├── SymbolTable.ml[i]
│   │   └── AstIndex.ml
│   ├── Protocol/            # LSP protocol
│   │   ├── LspProtocol.ml[i]
│   │   ├── RpcProtocol.ml
│   │   └── EventError.ml
│   ├── ServerState.ml       # Server state
│   ├── Config.ml            # Configuration
│   └── jasmin_lsp.ml        # Entry point
├── tree-sitter-jasmin/      # Submodule
│   └── ...                  # Parser implementation
├── pixi.toml                # Dependency management
├── dune-project             # Build configuration
└── test_lsp.sh             # Test script
```

## Contributing

### Adding Features

1. Implement in `LspProtocol.ml`
2. Add handler in `receive_lsp_request_inner` or `receive_lsp_notification`
3. Update capabilities in `Config.ml`
4. Test with `test_lsp.sh`
5. Document in `IMPLEMENTATION_SUMMARY.md`

### Testing Changes

```bash
# Build and test
pixi run build && pixi run test

# Or manual test
pixi run build && ./test_lsp.sh
```

## Resources

- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [Tree-Sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Tree-Sitter Jasmin](https://github.com/jasmin-lang/tree-sitter-jasmin)
- [OCaml LSP Library](https://github.com/ocaml/ocaml-lsp)

## Support

For issues or questions:
1. Check `IMPLEMENTATION_SUMMARY.md` for implementation details
2. Review `ARCHITECTURE.md` for design decisions
3. Enable verbose logging to debug protocol issues
4. Check that tree-sitter-jasmin submodule is up to date

## License

See [LICENSE](LICENSE) file for details.
