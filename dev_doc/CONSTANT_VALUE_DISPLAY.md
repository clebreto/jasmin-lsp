# Constant Value Display Feature

## Overview

When hovering over constant (`param`) declarations in Jasmin code, the LSP now displays the assigned value along with the type information.

## Feature Description

Constants in Jasmin are declared using the `param` keyword:

```jasmin
param int BUFFER_SIZE = 256;
param u64 MAX_VALUE = 0xFFFFFFFF;
param int EXPRESSION = (1 << 19) - 1;
```

When you hover over a constant name (either at the definition or at usage sites), the hover tooltip now displays:

```
param CONSTANT_NAME: type = value
```

For example, hovering over `BUFFER_SIZE` shows:
```
param BUFFER_SIZE: int = 256
```

## Implementation Details

### Files Modified

1. **`jasmin-lsp/Document/SymbolTable.ml`** - Symbol extraction
2. **`jasmin-lsp/Protocol/LspProtocol.ml`** - Hover display formatting

### Changes Made

#### 1. Enhanced Symbol Extraction

In `SymbolTable.ml`, the `extract_symbols_from_node` function was updated to extract the value from `param` nodes:

```ocaml
| "param" ->
    (match TreeSitter.node_child_by_field_name node "name" with
    | Some name_node ->
        let name = TreeSitter.node_text name_node source in
        let detail = 
          match TreeSitter.node_child_by_field_name node "type",
                TreeSitter.node_child_by_field_name node "value" with
          | Some type_node, Some value_node ->
              let type_text = TreeSitter.node_text type_node source in
              let value_text = TreeSitter.node_text value_node source in
              Some (Format.asprintf "%s = %s" type_text value_text)
          | Some type_node, None ->
              Some (TreeSitter.node_text type_node source)
          | None, Some value_node ->
              let value_text = TreeSitter.node_text value_node source in
              Some (Format.asprintf "= %s" value_text)
          | None, None -> Some "param"
        in
        {
          name;
          kind = Constant;
          range;
          definition_range = range;
          uri;
          detail;
        } :: acc
    | None -> acc)
```

**Key Changes:**
- Now extracts both the `type` and `value` fields from param nodes
- Stores the formatted string "type = value" in the `detail` field
- Handles cases where type or value might be missing gracefully

#### 2. Updated Hover Display

In `LspProtocol.ml`, the hover formatting for constants was enhanced:

```ocaml
| Document.SymbolTable.Constant ->
    (match symbol.detail with
    | Some detail_str -> Format.asprintf "param %s: %s" symbol.name detail_str
    | None -> Format.asprintf "const %s" symbol.name)
```

**Key Changes:**
- Uses the `detail` field which now contains "type = value"
- Formats as "param NAME: type = value"
- Falls back to "const NAME" if detail is not available

## Tree-Sitter Grammar

The feature relies on the tree-sitter grammar for Jasmin, which defines param nodes with named fields:

```javascript
param: ($) =>
  seq(
    "param",
    field("type", $._type),
    field("name", alias($.identifier, $.variable)),
    "=",
    field("value", $._expr),
    ";",
  ),
```

This allows the LSP to extract the type, name, and value separately using `node_child_by_field_name`.

## Examples

### Simple Constants

```jasmin
param int BUFFER_SIZE = 256;
```
Hover shows: `param BUFFER_SIZE: int = 256`

### Expression Constants

```jasmin
param int MASK = (1 << 19) - 1;
```
Hover shows: `param MASK: int = (1 << 19) - 1`

### Hexadecimal Constants

```jasmin
param u32 ADDRESS = 0x1000;
```
Hover shows: `param ADDRESS: u32 = 0x1000`

### Large Integer Constants

```jasmin
param u64 MAX_U64 = 18446744073709551615;
```
Hover shows: `param MAX_U64: u64 = 18446744073709551615`

## Testing

Two test files were created to verify the functionality:

### `test_constant_value.py`
Tests basic constant value display on a simple example from the test fixtures.

### `test_constant_types.py`
Comprehensive test covering:
- Simple integer constants
- Expression-based constants (bit shifts, arithmetic)
- Hexadecimal constants
- Large 64-bit constants
- Different integer types (int, u64, u32)

Both tests verify that:
1. The constant name appears in the hover text
2. The assigned value appears in the hover text
3. The format is correct and readable

## Benefits

1. **Quick Reference**: Developers can see constant values without navigating to the definition
2. **Better Understanding**: Complex expressions are displayed in full, helping understand computed constants
3. **Reduced Context Switching**: No need to jump to definition just to see the value
4. **Cross-File Support**: Works even when hovering over constant usages in files that import them via `require`

## Future Enhancements

Potential improvements for future versions:

1. **Evaluate Expressions**: Compute and show the evaluated value for expressions like `(1 << 19) - 1 = 524287`
2. **Show Multiple Formats**: Display hex constants in both hex and decimal
3. **Type Information**: Add more detailed type information for complex types
4. **Documentation Comments**: Extract and show comments above constant declarations
5. **Value Range Information**: Show valid ranges for different integer types

## Compatibility

This feature:
- ✅ Works with all existing Jasmin constant declarations
- ✅ Compatible with cross-file constant references
- ✅ Handles all expression types supported by Jasmin
- ✅ Gracefully degrades if type or value information is missing
- ✅ Works alongside existing hover features (functions, variables, keywords)
