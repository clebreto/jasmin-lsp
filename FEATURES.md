# Jasmin-LSP Features

A comprehensive Language Server Protocol implementation for the Jasmin programming language, providing IDE support with syntax analysis, symbol navigation, and cross-file resolution.

## Table of Contents

1. [Core LSP Protocol](#core-lsp-protocol)
2. [Symbol Analysis](#symbol-analysis)
3. [Navigation Features](#navigation-features)
4. [Diagnostics](#diagnostics)
5. [Code Intelligence](#code-intelligence)
6. [File Management](#file-management)
7. [Configuration](#configuration)
8. [Architecture](#architecture)

---

## Core LSP Protocol

### Server Initialization
- ✅ Standard LSP initialization handshake
- ✅ Server capability advertisement
- ✅ `initialized` notification handling
- ✅ Configuration request to client
- ✅ File operation registration (watch `.jazz` and `.jinc` files)

### Capability Declarations
- ✅ **textDocumentSync**: Full document synchronization with open/close tracking
- ✅ **definitionProvider**: Navigate to definitions
- ✅ **hoverProvider**: Display hover information with type details
- ✅ **referencesProvider**: Find all symbol references
- ✅ **documentSymbolProvider**: Show symbol outline/hierarchy
- ✅ **workspaceSymbolProvider**: Global symbol search
- ✅ **renameProvider**: Refactor symbol names
- ⏳ **documentFormattingProvider**: Not implemented
- ⏳ **codeActionProvider**: Not implemented

### Document Lifecycle
- ✅ `textDocument/didOpen`: Open document notification
- ✅ `textDocument/didChange`: Full document change notification
- ✅ `textDocument/didClose`: Close document notification
- ✅ `workspace/didChangeWatchedFiles`: External file change detection

---

## Symbol Analysis

### Symbol Extraction
Automatically discovers and indexes all symbol types:

- ✅ **Functions**
  - Function declarations with parameters and return types
  - Export modifier support
  - Inline modifier support
  - Signatures with argument lists

- ✅ **Variables**
  - Local variables with storage class (reg, stack, inline)
  - Type information
  - Declaration ranges

- ✅ **Parameters**
  - Function parameters
  - Parameter types
  - Parameter positions in function signature

- ✅ **Types**
  - Type definitions
  - Type names and ranges

- ✅ **Constants**
  - Parameter constants (`param` declarations)
  - Compile-time constant values
  - Expression evaluation

### Symbol Information

Each symbol includes:
- ✅ **Name**: Symbol identifier
- ✅ **Kind**: Type of symbol (Function, Variable, Parameter, Type, Constant)
- ✅ **Range**: Full declaration range (for folding/selection)
- ✅ **Selection Range**: Identifier only (for precise navigation)
- ✅ **URI**: File location
- ✅ **Type Information**: Type signatures and details
- ✅ **Documentation**: Extracted comments (see below)
- ✅ **Storage Class**: For variables (reg, stack, inline)

### Documentation Extraction

Automatically extracts comments before declarations:

- ✅ **Single-line Comments**: `// comment text`
  - Consecutive `//` comments merged into one documentation block
  - Allows one blank line within comment block

- ✅ **Multi-line Comments**: `/* ... */`
  - Full block extraction from `/*` to `*/`
  - Automatic formatting and cleanup
  - Preserved indentation handling

- ✅ **Comment Parsing**
  - Allows up to one blank line between comment and declaration
  - Strips comment markers (`/*`, `*/`, `//`)
  - Preserves meaningful indentation

### Constant Value Computation

For `param` constants, both declared and computed values:

- ✅ **Expression Evaluation**
  - Binary operations: `+`, `-`, `*`, `/`, `%`, `<<`, `>>`, `&`, `|`, `^`
  - Unary operations: `-`, `!`, `~`
  - Operator precedence respected

- ✅ **Cross-File Resolution**
  - Identifier resolution across all files
  - Recursive dependency traversal
  - Constant value propagation

- ✅ **Display Modes**
  - Simple constants: Shows type and value
  - Complex constants: Shows declared value and computed value (if different)
  - Expandable `<details>` sections for clarity

---

## Navigation Features

### Go To Definition

Navigate to symbol definitions with sophisticated scoping:

- ✅ **Local Navigation**
  - Jump to function definitions in current file
  - Navigate to local variable declarations
  - Jump to function parameter declarations
  - Navigate to type definitions

- ✅ **Cross-File Navigation**
  - Definitions in required files
  - Global variables (`param` declarations)
  - Constants in other files
  - Type definitions across modules
  - Transitive dependency resolution

- ✅ **Master File-Based Resolution**
  - Uses master file as root for dependency analysis
  - Collects all transitively required files
  - Searches entire project dependency graph
  - Fallback to all open files if no master file configured

- ✅ **Require Statement Navigation**
  - Click on filename in `require "file.jazz"` to open that file
  - Namespace-aware file resolution
  - Supports `from NAMESPACE require "file.jazz"`
  - Searches multiple directory locations:
    - `./namespace/filename`
    - `./namespace_lower/filename` (lowercase variant)
    - `../namespace/filename` (sibling directories)
    - Multiple levels up the directory tree

- ✅ **Scope Resolution**
  - Finds innermost identifier at cursor position
  - Distinguishes identifiers from Jasmin keywords
  - Handles nested scopes correctly

### Find References

Locate all uses of a symbol:

- ✅ **Reference Detection**
  - All symbol usages in current file
  - Cross-file reference search
  - Variable, function, parameter, and global references
  - Includes/excludes declaration location

- ✅ **Reference Scope**
  - Searches all files from master file dependency tree
  - Loads files from disk if not open in editor
  - Transitive dependency traversal
  - Deduplicates results

- ✅ **Cross-File References**
  - Functions used in multiple files
  - Global variables referenced across modules
  - Parameter constants used in dependencies

### Workspace Symbol Search

Global symbol search and navigation:

- ✅ **Query-Based Search**
  - Case-insensitive substring matching
  - Empty query returns all symbols
  - Search across all open documents

- ✅ **Symbol Information**
  - Symbol name and kind
  - Location (URI + range)
  - Container name (if applicable)

---

## Diagnostics

### Syntax Error Detection

Real-time syntax analysis:

- ✅ **Error Detection**
  - ERROR nodes from tree-sitter parser
  - Missing nodes detection
  - Node type "ERROR" identification
  - Recursive tree traversal for nested errors

- ✅ **Error Information**
  - Line and column range
  - Error message
  - Error severity (always Error level)
  - File URI

- ✅ **Error Categorization**
  - Missing syntax elements
  - Malformed constructs
  - Invalid token sequences

### Diagnostic Publishing

Real-time diagnostic updates:

- ✅ **On File Open**: Diagnostics published immediately
- ✅ **On Document Change**: Updates as user types
- ✅ **On External Changes**: Detects changes from git, external editors, etc.
- ✅ **Dependency-Aware**: Sends diagnostics for current file and all dependencies
- ✅ **Performance Optimized**: Only scans open files (not disk files)

### Diagnostic Triggers

- ✅ `textDocument/didOpen`: On opening a file
- ✅ `textDocument/didChange`: On editing content
- ✅ `workspace/didChangeWatchedFiles`: On external changes
- ✅ After master file configuration
- ✅ After namespace path configuration

---

## Code Intelligence

### Hover Information

Display detailed symbol information on hover:

- ✅ **Type Information**
  - Variables: `name: type`
  - Parameters: `name: type`
  - Functions: Full signature with params and return type
  - Constants: Type information

- ✅ **Constant Value Display**
  - Declared value shown
  - Computed value shown (if different)
  - Expandable `<details>` section for clarity
  - Handles complex expressions

- ✅ **Keyword Documentation**
  - Built-in documentation for Jasmin keywords:
    - Control flow: `fn`, `inline`, `export`, `return`, `if`, `else`, `while`, `for`
    - Declarations: `require`, `from`, `param`, `global`, `reg`, `stack`, `const`
  - Markdown-formatted documentation
  - Syntax examples

- ✅ **Hover Content Formatting**
  - Markdown code blocks for syntax
  - Type information in jasmin syntax highlighting
  - Documentation section with separator
  - Collapsible value sections for constants

- ✅ **Cross-File Hover**
  - Looks up symbols in all relevant files
  - Uses master file dependency tree
  - Loads files from disk if needed
  - Source maps for constant evaluation

### Document Symbols

Symbol outline and navigation:

- ✅ **Hierarchical Symbol List**
  - All symbols in current file
  - Symbol kind classification
  - Range information for navigation

- ✅ **Symbol Information**
  - Symbol name and kind
  - Full declaration range
  - Identifier range for precise jump
  - Type/signature detail

### Rename Symbol

Refactoring support:

- ✅ **Symbol Rename**
  - Find all references to symbol
  - Generate text edits for each reference
  - Batch update across files
  - `textDocument/rename` LSP request

- ✅ **Edit Generation**
  - Creates `TextEdit` for each reference
  - Preserves code formatting
  - Updates all occurrences simultaneously
  - Returns `WorkspaceEdit` for client application

---

## File Management

### Document Store

Efficient document caching:

- ✅ **In-Memory Storage**
  - Source text caching
  - Parse tree caching
  - Version tracking
  - URI-based indexing

- ✅ **Document Operations**
  - `open_document`: Add and parse
  - `update_document`: Re-parse on changes
  - `close_document`: Remove from store
  - `get_document`: Retrieve metadata
  - `get_text`: Get source code
  - `get_tree`: Get syntax tree
  - `get_all_uris`: List all documents
  - `is_open`: Check if document open

### Require Statement Parsing

Sophisticated handling of file inclusion:

- ✅ **Require Statement Detection**
  - Extracts required filenames from `require` statements
  - Handles multiple files in one statement: `require "file1.jazz" "file2.jazz"`
  - Namespace-prefixed requires: `from NAMESPACE require "file.jazz"`

- ✅ **Namespace Resolution**
  - Looks up namespace in configured paths
  - Searches multiple directory levels
  - Case-insensitive namespace matching
  - Multiple fallback locations

- ✅ **Dependency Resolution**
  - Recursive traversal of `require` statements
  - Cycle detection (visited set prevention)
  - Transitive dependency collection
  - Used for go-to-definition, references, hover

### On-Demand Loading

Files loaded dynamically when needed:

- ✅ **Disk Loading**
  - Loads files from disk when not open in editor
  - Parses loaded files immediately
  - Caches parsed trees
  - Builds source maps for evaluation

- ✅ **File System Watching**
  - External file creation detection
  - File modification detection
  - File deletion detection
  - Reloads changed files
  - Updates diagnostics
  - Clears diagnostics for deleted files

---

## Configuration

### Master File Feature

Specify compilation entry point:

- ✅ **Master File Setting**
  - `jasmin.masterFile` configuration option
  - Specifies root of dependency tree
  - Supports `${workspaceFolder}` variable
  - Both relative and absolute paths

- ✅ **Master File Configuration**
  - Custom `jasmin/setMasterFile` LSP notification
  - Stores master file URI in server state
  - Used as root for dependency resolution
  - Enables full project analysis

- ✅ **Required Namespaces Query**
  - Custom `jasmin/getRequiredNamespaces` LSP request
  - Analyzes master file for namespace requirements
  - Returns list of required namespace identifiers
  - Used by extension for configuration UI

### Namespace Path Configuration

Map namespaces to filesystem paths:

- ✅ **Namespace Paths Setting**
  - `jasmin.namespacePaths` configuration object
  - Maps namespace IDs to filesystem paths
  - Supports `${workspaceFolder}` variable
  - Workspace-scoped configuration

- ✅ **Namespace Configuration**
  - Custom `jasmin/setNamespacePaths` LSP notification
  - Stores namespace-to-path mappings
  - Used for resolving namespace-prefixed requires
  - Triggers file loading and diagnostics

- ✅ **Dynamic Updates**
  - Reloads master file and dependencies on configuration change
  - Recomputes diagnostics for all files
  - Updates symbol indexes

---

## Architecture

### Core System Design

Event-driven architecture with priorities:

- ✅ **Priority-Based Event Queue**
  - Min-heap based event scheduling
  - Priority levels: Next (immediate), High (important), Low (background)
  - Prevents priority inversion
  - Ensures timely response sending

- ✅ **Asynchronous I/O**
  - Lwt cooperative threading
  - Non-blocking operations
  - Efficient resource utilization
  - Graceful error handling

### Parsing Engine

Tree-sitter integration:

- ✅ **Tree-Sitter Grammar**
  - tree-sitter-jasmin grammar integration
  - Incremental parsing support
  - Fast syntax tree construction
  - C FFI bindings

- ✅ **Tree Navigation API**
  - `node_type`: Get node classification
  - `node_range`: Get position information
  - `node_at_point`: Find node at cursor
  - `node_child`, `node_named_child`: Navigate tree structure
  - `node_text`: Extract source text
  - `node_is_error`, `node_is_missing`: Error detection
  - `node_parent`: Parent navigation

### Memory Management

Efficient resource handling:

- ✅ **Garbage Collection**
  - OCaml garbage collection for trees
  - No manual tree deletion needed
  - Automatic resource cleanup
  - Safe C stub interactions

- ✅ **Caching Strategy**
  - Document store caches parse trees
  - Parser singleton (reused across documents)
  - Source maps for constant evaluation
  - Incremental updates on changes

### Error Handling

Robust error recovery:

- ✅ **Exception Handling**
  - Try-catch blocks around all operations
  - Nested exception handling in tree traversal
  - Safe recovery from parsing failures
  - Graceful handling of invalid input

- ✅ **Null Safety**
  - Null checks before all node operations
  - Bounds checking in diagnostics
  - Null pointer checks in C stubs
  - Safe finalizers

### Logging

Comprehensive diagnostic logging:

- ✅ **File-Based Logging**
  - Automatic log file creation in `~/.jasmin-lsp/`
  - Timestamped log files: `jasmin-lsp-YYYYMMDD-HHMMSS.log`
  - Detailed operation tracking

- ✅ **Log Information**
  - LSP request types and parameters
  - Symbol resolution steps
  - File loading operations
  - Diagnostic counts
  - Error messages with stack traces
  - Performance metrics

---

## Test Coverage

### Tested Features

- ✅ Server initialization and capability advertisement
- ✅ Syntax diagnostics and error detection
- ✅ Go to definition (local and cross-file)
- ✅ Find references (local and cross-file)
- ✅ Hover information with type details
- ✅ Document symbols and outline
- ✅ Workspace symbol search
- ✅ Rename symbol refactoring
- ✅ Master file configuration
- ✅ Namespace path configuration
- ✅ Document lifecycle (open, change, close)
- ✅ File system watching
- ✅ Require statement navigation
- ✅ Constant value computation
- ✅ Cross-file analysis

### Test Suites

- ✅ **Integration Tests**: Full LSP protocol testing
- ✅ **Diagnostics Tests**: Syntax error detection
- ✅ **Navigation Tests**: Go to definition and references
- ✅ **Hover Tests**: Type information and documentation
- ✅ **Cross-File Tests**: Multi-file analysis
- ✅ **Performance Tests**: Large documents, rapid changes
- ✅ **Crash Resilience Tests**: Invalid inputs, edge cases

---

## Known Limitations

- ⏳ Code formatting not implemented
- ⏳ Code actions not implemented
- ⏳ Batch request handling not implemented
- ⏳ Configuration response not dynamically updated
- ⏳ Incremental parsing not fully utilized

---

## Future Enhancements

Planned features for future releases:

- 🔄 Code formatting support
- 🔄 Code completion
- 🔄 Quick fixes (code actions)
- 🔄 Semantic highlighting
- 🔄 Inlay hints for type information
- 🔄 Call hierarchy
- 🔄 Linked editing range
- 🔄 Moniker support for cross-project symbols

---

## Performance Characteristics

- ✅ Fast incremental parsing with tree-sitter
- ✅ Efficient symbol indexing
- ✅ Lazy file loading (on-demand)
- ✅ Asynchronous I/O (no blocking)
- ✅ Memory-efficient document caching
- ✅ Handles large files (tested with 10,000+ lines)
- ✅ Supports rapid concurrent edits
- ✅ Scalable to large projects with many files

---

## Configuration Reference

### Server Settings (in `.vscode/settings.json`)

```json
{
  "jasmin.path": "/path/to/jasmin-lsp",
  "jasmin.args": [],
  "jasmin.masterFile": "main.jazz",
  "jasmin.namespacePaths": {
    "Common": "./common",
    "Crypto": "./crypto"
  }
}
```

### Server Capabilities

Advertised in `initialize` response:

```ocaml
textDocumentSync: TextDocumentSyncOptions {
  openClose: true,
  change: Full
}
definitionProvider: true
hoverProvider: true
referencesProvider: true
documentSymbolProvider: true
workspaceSymbolProvider: true
renameProvider: true
```

---

## Integration

Jasmin-LSP follows the **Language Server Protocol (LSP) 3.x specification** and works with:

- ✅ VS Code (via vsjazz extension)
- ✅ Neovim (with lspconfig)
- ✅ Emacs (with lsp-mode or eglot)
- ✅ Sublime Text (with LSP package)
- ✅ Any editor supporting LSP

---

## License

MIT License - Same as jasmin-lsp project

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system design
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [README.md](README.md) - Project overview
- [test/README.md](test/README.md) - Testing documentation
