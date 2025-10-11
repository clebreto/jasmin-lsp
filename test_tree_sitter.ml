(* Simple test program to verify tree-sitter bindings work *)

let () =
  print_endline "Testing tree-sitter-jasmin bindings...";
  
  (* Create a parser *)
  let parser = TreeSitter.TreeSitter.parser_new () in
  print_endline "✓ Parser created";
  
  (* Get Jasmin language *)
  let language = TreeSitter.TreeSitter.language_jasmin () in
  print_endline "✓ Jasmin language loaded";
  
  (* Set the language *)
  TreeSitter.TreeSitter.parser_set_language parser language;
  print_endline "✓ Language set";
  
  (* Parse a simple Jasmin program *)
  let source_code = {|
fn test() -> reg u64 {
  reg u64 x;
  x = 42;
  return x;
}
|} in
  
  print_endline "\nParsing source code:";
  print_endline source_code;
  
  match TreeSitter.TreeSitter.parser_parse_string parser source_code with
  | None -> 
      print_endline "✗ Parsing failed!";
      TreeSitter.TreeSitter.parser_delete parser;
      exit 1
  | Some tree ->
      print_endline "✓ Parsing succeeded!";
      
      (* Get the root node *)
      let root = TreeSitter.TreeSitter.tree_root_node tree in
      print_endline "✓ Root node obtained";
      
      (* Print some information about the root node *)
      let node_type = TreeSitter.TreeSitter.node_type root in
      Printf.printf "  Root node type: %s\n" node_type;
      
      let has_error = TreeSitter.TreeSitter.node_has_error root in
      Printf.printf "  Has error: %b\n" has_error;
      
      let child_count = TreeSitter.TreeSitter.node_child_count root in
      Printf.printf "  Child count: %d\n" child_count;
      
      let start_point = TreeSitter.TreeSitter.node_start_point root in
      let end_point = TreeSitter.TreeSitter.node_end_point root in
      Printf.printf "  Range: (%d,%d) - (%d,%d)\n" 
        start_point.row start_point.column
        end_point.row end_point.column;
      
      (* Clean up *)
      TreeSitter.TreeSitter.tree_delete tree;
      TreeSitter.TreeSitter.parser_delete parser;
      
      print_endline "\n✓ All tests passed!"
