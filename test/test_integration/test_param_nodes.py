#!/usr/bin/env python3
"""Test to see what tree-sitter nodes are created for param declarations"""

import subprocess
import json
import tempfile
import os
from pathlib import Path

# Create test file in temporary directory
test_content = """// Test param declaration
param int BUFFER_SIZE = 256;

fn test() -> reg u64 {
  reg u64 x;
  x = BUFFER_SIZE;
  return x;
}
"""

# Use temporary directory
tmpdir = tempfile.mkdtemp(prefix="jasmin_test_")
test_param_path = os.path.join(tmpdir, "test_param.jazz")

with open(test_param_path, "w") as f:
    f.write(test_content)

print(f"Created test file: {test_param_path}")

# Use the tree-sitter CLI or a simple Python script
# Let's make a simple OCaml test program instead

ocaml_test = """
open TreeSitter

let () =
  let source = {|param int BUFFER_SIZE = 256;

fn test() -> reg u64 {
  reg u64 x;
  x = BUFFER_SIZE;
  return x;
}|} in
  
  let tree = parse_string source in
  let root = tree_root_node tree in
  
  (* Print tree structure *)
  let rec print_node indent node =
    let node_type = node_type node in
    let text = node_text node source in
    let short_text = if String.length text > 40 then 
      String.sub text 0 40 ^ "..." 
    else text in
    Printf.printf "%s%s: '%s'\\n" indent node_type short_text;
    
    let child_count = node_named_child_count node in
    for i = 0 to child_count - 1 do
      match node_named_child node i with
      | Some child -> print_node (indent ^ "  ") child
      | None -> ()
    done
  in
  
  print_node "" root
"""

test_tree_path = os.path.join(tmpdir, "test_tree_structure.ml")

with open(test_tree_path, "w") as f:
    f.write(ocaml_test)

print(f"Created test_tree_structure.ml: {test_tree_path}")
print(f"\nTemporary directory: {tmpdir}")
print("\nTo compile and run:")
print(f"  cd {tmpdir}")
print("  dune exec -- ocaml -I _build/default/jasmin-lsp/ -I _build/default/jasmin-lsp/TreeSitter tree-sitter.cma test_tree_structure.ml")
print(f"\nTo clean up when done:")
print(f"  rm -rf {tmpdir}")
