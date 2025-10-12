# Constant Value Computation Feature

## Overview

The Jasmin LSP now automatically computes and displays the actual numerical values of constants that are defined using expressions or references to other constants.

## How It Works

When you hover over a constant declaration or usage, the LSP will:
1. Parse the expression assigned to the constant
2. Resolve any references to other constants
3. Evaluate the expression to compute the actual value
4. Display both the original expression AND the computed value

## Examples

### Simple Arithmetic
```jasmin
param int BASE = 100;
param int OFFSET = 50;
param int TOTAL = BASE + OFFSET;
```
Hovering over `TOTAL` shows:
```
param TOTAL: int = BASE + OFFSET = 150
```

### Complex Expressions
```jasmin
param int DOUBLED = TOTAL * 2;
```
Hovering shows:
```
param DOUBLED: int = TOTAL * 2 = 300
```

### Bit Operations
```jasmin
param int SHIFTED = 1 << 10;
```
Hovering shows:
```
param SHIFTED: int = 1 << 10 = 1024
```

### Constants Built from Other Constants
```jasmin
param int START_OF_HINT_IN_SIGNATURE = 200;
param int HINT_ENCODED_SIZE = 150;
param int SIGNATURE_SIZE = START_OF_HINT_IN_SIGNATURE + HINT_ENCODED_SIZE;
```
Hovering over `SIGNATURE_SIZE` shows:
```
param SIGNATURE_SIZE: int = START_OF_HINT_IN_SIGNATURE + HINT_ENCODED_SIZE = 350
```

## Supported Operations

The evaluator supports:
- **Arithmetic**: `+`, `-`, `*`, `/`, `%`
- **Bitwise**: `<<`, `>>`, `&`, `|`, `^`
- **Unary**: `-`, `+`, `~`, `!`
- **Parentheses**: `(expression)`
- **Number formats**: decimal, hexadecimal (0x...), binary (0b...)

## Implementation Details

### Multi-Pass Evaluation

The evaluator uses a multi-pass algorithm to handle constants that depend on other constants:

1. **Pass 1**: Evaluate all constants with literal values (e.g., `param int X = 42`)
2. **Pass 2**: Evaluate constants that reference constants from Pass 1
3. **Pass 3+**: Continue until all possible constants are evaluated (up to 10 passes)

This allows complex dependency chains like:
```jasmin
param int A = 10;
param int B = A + 5;      // Evaluated in pass 2
param int C = B * 2;      // Evaluated in pass 3
```

### Cross-File Support

The feature works across files via `require` statements. If a constant references another constant from a required file, the evaluator will find and use that value.

## Testing

Run the test suite:
```bash
python3 test_constant_computation.py
```

This tests:
- Simple integer constants
- Arithmetic expressions
- Constants referencing other constants  
- Bit shift operations
- Cross-file constant references

## Benefits

1. **Immediate Feedback**: See computed values without manually calculating or searching
2. **Reduced Errors**: Verify that expressions evaluate to expected values
3. **Better Understanding**: Quickly understand what a constant's actual value is
4. **No Code Changes**: Works automatically with existing code

## Technical Implementation

### Files Modified

1. **`ExprEvaluator.ml`** (new): Expression evaluation engine
2. **`SymbolTable.ml`**: Enhanced to compute constant values
3. **`LspProtocol.ml`**: Updated hover handler to use computed values

### Key Functions

- `ExprEvaluator.eval_expr`: Recursively evaluates expression trees
- `SymbolTable.build_const_env`: Builds environment of constant values with multi-pass evaluation
- `SymbolTable.enhance_constants_with_values`: Adds computed values to symbol details
- `LspProtocol.extract_symbols_with_values`: Extracts and enhances symbols in one step
