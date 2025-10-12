# Tree-Sitter Integration for Jasmin-LSP

## Setup Complete! ✓

The jasmin-lsp project has been successfully configured to use tree-sitter-jasmin for parsing.

## What's Been Done

### 1. Submodule Added
- Added `tree-sitter-jasmin` as a git submodule from https://github.com/jasmin-lang/tree-sitter-jasmin.git
- Located at: `tree-sitter-jasmin/`

### 2. Pixi Configuration
Updated `pixi.toml` with:
- **Dependencies**: 
  - `libtree-sitter` - Tree-sitter runtime library
  - `tree-sitter-cli` - Tree-sitter CLI tools
  - `clang` - C compiler
  - Existing: `gmp`, `mpfr`, `pkgconf`, `ppl`

- **Tasks**:
  - `pixi run build-tree-sitter` - Build the tree-sitter-jasmin parser
  - `pixi run clean` - Clean build artifacts
  - `pixi run build` - Build the entire project (includes tree-sitter)
  - `pixi run test` - Run tests
  - `pixi run run` - Run the language server
  - `pixi run setup` - Initial setup (build tree-sitter + install opam deps)

### 3. OCaml Bindings Created
Created complete OCaml bindings for tree-sitter in `jasmin-lsp/TreeSitter/`:

- **TreeSitter.mli** - Interface file with type definitions and function signatures
- **TreeSitter.ml** - Implementation with external C bindings and helper functions
- **tree_sitter_stubs.c** - C FFI stubs connecting OCaml to tree-sitter C API

### 4. Build Configuration
Updated `jasmin-lsp/dune` to:
- Compile C stubs (`tree_sitter_stubs.c`)
- Link against `libtree-sitter` and `libtree-sitter-jasmin`
- Include proper header paths
- Set up runtime paths (rpath) for dynamic libraries

## How to Use

### Initial Setup

```bash
cd /path/to/jasmin-lsp

# Install all dependencies and build tree-sitter
pixi install
pixi run setup
```

### Building

```bash
# Clean build
pixi run clean

# Build everything (automatically builds tree-sitter first)
pixi run build
```

### Running

```bash
# Run the language server
pixi run run
```

## Tree-Sitter API Usage in OCaml

Here's how to use the tree-sitter bindings in your OCaml code:

```ocaml
(* Create a parser *)
let parser = TreeSitter.parser_new () in

(* Get the Jasmin language *)
let language = TreeSitter.language_jasmin () in

(* Configure the parser *)
TreeSitter.parser_set_language parser language;

(* Parse source code *)
let source = "fn test() { ... }" in
match TreeSitter.parser_parse_string parser source with
| None -> (* parsing failed *)
| Some tree ->
    (* Get the root node *)
    let root = TreeSitter.tree_root_node tree in
    
    (* Get node information *)
    let node_type = TreeSitter.node_type root in
    let has_error = TreeSitter.node_has_error root in
    let child_count = TreeSitter.node_child_count root in
    
    (* Navigate the tree *)
    let first_child = TreeSitter.node_child root 0 in
    let named_children = TreeSitter.node_named_children root in
    
    (* Get text *)
    let text = TreeSitter.node_text root source in
    
    (* Find node at position *)
    let point = { TreeSitter.row = 1; column = 5 } in
    let node_at_pos = TreeSitter.node_at_point root point in
    
    (* Cleanup *)
    TreeSitter.tree_delete tree;
    TreeSitter.parser_delete parser
```

## Available Tree-Sitter Functions

### Parser Management
- `parser_new : unit -> parser`
- `parser_delete : parser -> unit`
- `parser_set_language : parser -> language -> unit`
- `language_jasmin : unit -> language`

### Parsing
- `parser_parse_string : parser -> string -> tree option`
- `parser_parse_string_with_tree : parser -> tree option -> string -> tree option` (incremental)

### Tree Operations
- `tree_root_node : tree -> node`
- `tree_delete : tree -> unit`
- `tree_copy : tree -> tree`

### Node Inspection
- `node_type : node -> string` - Get node type name
- `node_is_named : node -> bool` - Check if named node
- `node_has_error : node -> bool` - Check for syntax errors
- `node_is_missing : node -> bool` - Check if node is missing
- `node_is_error : node -> bool` - Check if node is ERROR type

### Node Navigation
- `node_child : node -> int -> node option` - Get nth child
- `node_named_child : node -> int -> node option` - Get nth named child
- `node_child_count : node -> int`
- `node_named_child_count : node -> int`
- `node_child_by_field_name : node -> string -> node option`
- `node_parent : node -> node option`
- `node_next_sibling : node -> node option`
- `node_prev_sibling : node -> node option`

### Position and Range
- `node_start_point : node -> point`
- `node_end_point : node -> point`
- `node_start_byte : node -> int`
- `node_end_byte : node -> int`
- `node_range : node -> range`

### Text Extraction
- `node_text : node -> string -> string`
- `node_descendant_for_point_range : node -> point -> point -> node option`
- `node_named_descendant_for_point_range : node -> point -> point -> node option`

### Helper Functions
- `node_children : node -> node list`
- `node_named_children : node -> node list`
- `node_at_point : node -> point -> node option`
- `point_in_range : point -> range -> bool`

## Directory Structure

```
jasmin-lsp/
├── tree-sitter-jasmin/          # Git submodule
│   ├── src/
│   │   ├── parser.c             # Generated parser
│   │   └── tree_sitter/         # Tree-sitter headers
│   ├── bindings/c/              # C bindings
│   ├── libtree-sitter-jasmin.a  # Static library
│   └── libtree-sitter-jasmin.dylib  # Dynamic library
│
├── jasmin-lsp/
│   └── TreeSitter/              # OCaml bindings
│       ├── TreeSitter.ml        # Implementation
│       ├── TreeSitter.mli       # Interface
│       └── tree_sitter_stubs.c  # C FFI stubs
│
├── .pixi/
│   └── envs/default/
│       ├── include/
│       │   └── tree_sitter/api.h  # Tree-sitter API
│       └── lib/
│           └── libtree-sitter.*   # Tree-sitter library
│
└── pixi.toml                    # Package manager config
```

## Next Steps

Now that tree-sitter is integrated, you can:

1. **Implement Document Store** - Track open documents and their parse trees
2. **Build Symbol Table** - Extract symbol information from syntax trees
3. **Add Diagnostics** - Use tree-sitter error nodes for syntax error reporting
4. **Enhance Go-to-Definition** - Use tree-sitter for symbol resolution
5. **Implement Find References** - Track symbol usages across files
6. **Add Hover Information** - Extract documentation from parse trees
7. **Implement Document Symbols** - Generate outline from syntax tree
8. **Add Code Actions** - Provide quick fixes based on syntax tree analysis

## Troubleshooting

### Build Errors

If you get linking errors:
```bash
# Rebuild tree-sitter-jasmin
pixi run build-tree-sitter

# Clean and rebuild
pixi run clean
pixi run build
```

### Missing Dependencies

```bash
# Reinstall pixi environment
pixi install
```

### Path Issues

The dune configuration uses absolute paths. If you move the project, update the paths in `jasmin-lsp/dune`:
- Replace `/Users/clebreto/dev/splits/jasmin-lsp/` with your project path

## References

- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Tree-sitter Jasmin Grammar](https://github.com/jasmin-lang/tree-sitter-jasmin)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [Pixi Package Manager](https://pixi.sh/)
