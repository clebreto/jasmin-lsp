#!/usr/bin/env python3
import tree_sitter_jasmin as ts_jasmin
from tree_sitter import Language, Parser

code = b"fn test(reg u32 a, b, stack u64 x, y, z) -> reg u32 { return a; }"

parser = Parser()
parser.language = Language(ts_jasmin.language())
tree = parser.parse(code)

def print_tree(node, indent=0):
    node_type = node.type
    if node.is_named:
        text = code[node.start_byte:node.end_byte].decode('utf-8')
        if len(text) < 50:
            print("  " * indent + f"{node_type}: {repr(text)}")
        else:
            print("  " * indent + f"{node_type}: [...]")
        for child in node.children:
            print_tree(child, indent + 1)

print_tree(tree.root_node)
