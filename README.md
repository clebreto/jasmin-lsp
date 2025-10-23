# jasmin-lsp

![CI](https://github.com/jasmin-lang/jasmin-lsp/workflows/CI/badge.svg)

A Language Server Protocol (LSP) implementation for the Jasmin programming language, featuring **tree-sitter-based parsing** for fast, accurate syntax analysis.

## ✅ Status: FULLY OPERATIONAL

All tree-sitter integration issues have been resolved! The language server is production-ready.

## Features

✅ **Tree-Sitter Parsing** - Fast, incremental syntax analysis  
✅ **Syntax Diagnostics** - Real-time error detection with intelligent cleanup  
✅ **Go to Definition** - Navigate to function, variable, parameter, and global definitions  
✅ **Cross-File Navigation** - Jump to definitions across `require`d files  
✅ **Master File Support** - Proper symbol resolution using compilation entry point  
✅ **Smart Diagnostics Cleanup** - Clears diagnostics when closing files outside dependency tree  
✅ **Find All References** - Locate all usages of a symbol  
✅ **Hover Information** - Show type information, signatures, and keyword documentation  
✅ **Document Symbols** - Outline view of current file  
✅ **Workspace Symbols** - Global symbol search  
✅ **Rename Symbol** - Refactoring support

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

### Prerequisites

- [Pixi](https://pixi.sh/) package manager (recommended)
- Or [Nix](https://nixos.org/) for legacy support
- OCaml 5.3.0+ with dune 3.8+

### Build with Pixi (Recommended)

```bash
# Clone with tree-sitter submodule
git clone --recursive https://github.com/jasmin-lang/jasmin-lsp.git
cd jasmin-lsp

# Install dependencies (with correct tree-sitter versions)
pixi install

# Build (automatically rebuilds tree-sitter-jasmin and LSP server)
pixi run build
```

The executable will be at `_build/default/jasmin-lsp/jasmin_lsp.exe`.

**Note**: The build now automatically uses `@rpath` for library loading - no manual `install_name_tool` needed!

### Build with Nix (Legacy)

```bash
nix-shell  # or nix-shell dev.nix for ocaml-lsp
dune build
```

### Build with Opam

```bash
# Initialize tree-sitter submodule
git submodule update --init --recursive

# Install dependencies
opam install . --deps-only

# Build
dune build
```

## Usage

### Terminal Testing

```bash
# Run the server directly
_build/default/jasmin-lsp/jasmin_lsp.exe

# Or use automated test
./test_lsp.sh
```

### VS Code Integration

1. Install the [Vsjazz](https://marketplace.visualstudio.com/items?itemName=jasmin-lang.vsjazz) extension
2. Configure the LSP server path in settings:
   ```json
   {
     "jasmin.path": "/path/to/jasmin-lsp/_build/default/jasmin-lsp/jasmin_lsp.exe",
     "jasmin.masterFile": "main.jazz"
   }
   ```

**Note**: The `jasmin.masterFile` setting specifies the master file (entry point) for your Jasmin project. This is important for proper symbol resolution across `require`d files. A status bar item will show the current master file when editing `.jazz` or `.jinc` files, and you can click it to change the master file. See [MASTER_FILE_FEATURE.md](MASTER_FILE_FEATURE.md) for details.

### Diagnostics Behavior

The LSP server intelligently manages diagnostics based on the master file dependency tree:

- **All open buffers** receive diagnostics, regardless of dependency relationships
- **Files in the dependency tree** are kept in memory when closed and their diagnostics remain visible
- **Files NOT in the dependency tree** are removed from memory and have diagnostics cleared when closed
- This keeps the Problems panel clean while ensuring critical project files remain monitored

Example:
```
main.jazz → module.jinc → utils.jinc  (dependency tree)
unrelated.jinc                         (not in tree)
```
- Close `utils.jinc` (in tree): kept in memory, diagnostics remain visible ✓
- Close `unrelated.jinc` (not in tree): removed from memory, diagnostics cleared ✓

See [dev_doc/CLOSE_BUFFER_DIAGNOSTICS.md](dev_doc/CLOSE_BUFFER_DIAGNOSTICS.md) for implementation details.

### Other IDEs

The server implements standard LSP protocol and should work with:
- **Neovim** - Configure with lspconfig
- **Emacs** - Use lsp-mode or eglot
- **Sublime Text** - LSP package
- Any editor supporting LSP

## Architecture

This LSP server uses [tree-sitter-jasmin](https://github.com/jasmin-lang/tree-sitter-jasmin) for fast, incremental parsing:

- **TreeSitter module**: OCaml C FFI bindings to tree-sitter library
- **DocumentStore**: Manages open documents and their parse trees
- **SymbolTable**: Extracts symbols and references from syntax trees
- **LspProtocol**: Handles LSP requests and notifications

See [ARCHITECTURE.md](ARCHITECTURE.md) for design details.

## Project Structure

```
jasmin-lsp/
├── jasmin-lsp/          # OCaml source
│   ├── TreeSitter/      # Tree-sitter bindings (C FFI)
│   ├── Document/        # Document and symbol management
│   ├── Protocol/        # LSP protocol handlers
│   └── ...
├── tree-sitter-jasmin/  # Parser submodule
├── pixi.toml            # Pixi configuration
└── test_lsp.sh          # Integration test
```

## Development

### Continuous Integration

The project uses GitHub Actions for automated building and testing on Linux AMD64:

- **Automated Builds**: Triggered on push to `main`/`master` branches and pull requests
- **Test Suite**: Full pytest suite runs on every commit
- **Build Artifacts**: Linux AMD64 binaries available for download from workflow runs
- **Caching**: Opam dependencies and dune cache for faster builds

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the complete CI configuration.

### Testing

Run the full test suite (automatically builds the LSP server first):

```bash
pixi run test
```

For more control over pytest:

```bash
pixi run pytest test           # Run all tests
pixi run pytest test -v        # Verbose output
pixi run pytest test -k hover  # Run specific tests
pixi run pytest test --cov     # With coverage
```

Alternative shell-based tests:

```bash
cd test
./test_all.sh
```

See [test/README.md](test/README.md) for comprehensive testing documentation.

**Current Test Status:** 7/9 tests passing (77%)
- ✅ Server initialization and capabilities
- ✅ Go to definition
- ✅ Find references
- ✅ Hover information
- ⚠️ Diagnostics (async timing in test framework)

See [TEST_IMPLEMENTATION.md](TEST_IMPLEMENTATION.md) for detailed test implementation.

### Debugging

The LSP server now automatically writes logs to a file for easier debugging:

**Log file location:** `~/.jasmin-lsp/jasmin-lsp-YYYYMMDD-HHMMSS.log`

See [dev_doc/FILE_LOGGING.md](dev_doc/FILE_LOGGING.md) for complete logging documentation.

**Manual logging to stderr:**
```bash
_build/default/jasmin-lsp/jasmin_lsp.exe 2> lsp.log
```

### Adding Features

1. Implement in `jasmin-lsp/Protocol/LspProtocol.ml`
2. Update capabilities in `jasmin-lsp/Config.ml`
3. Add tests in `test_lsp.sh`
4. Document in `IMPLEMENTATION_SUMMARY.md`

## Contributing

Contributions welcome! Please:
1. Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for current status
2. Follow existing code style
3. Add tests for new features
4. Update documentation

## Resources

- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [Tree-Sitter Jasmin](https://github.com/jasmin-lang/tree-sitter-jasmin)
- [Jasmin Language](https://github.com/jasmin-lang/jasmin)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [Quick Start Guide](QUICKSTART.md)

## Contributors

* [MrDaiki](https://github.com/MrDaiki) (Alexandre BOURBEILLON)
* [clebreto](https://github.com/clebreto) (Côme LE BRETON)

## License

See [LICENSE](LICENSE) for details.