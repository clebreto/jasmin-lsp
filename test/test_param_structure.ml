open TreeSitter

let () =
  let source = "param int BASE_CONSTANT = 42;" in
  let parser = TreeSitter.parser_new () in
  let language = TreeSitter.language_jasmin () in
  TreeSitter.parser_set_language parser language;
  
  match TreeSitter.parser_parse_string parser source with
  | None -> Printf.printf "Parse failed\n"
  | Some tree ->
      let root = TreeSitter.tree_root_node tree in
      let param_node = TreeSitter.node_named_child root 0 in
      (match param_node with
      | None -> Printf.printf "No param node\n"
      | Some node ->
          Printf.printf "Node type: %s\n" (TreeSitter.node_type node);
          Printf.printf "Node text: %s\n" (TreeSitter.node_text node source);
          
          (* Try to get fields *)
          (match TreeSitter.node_child_by_field_name node "name" with
          | Some n -> Printf.printf "Name field: %s\n" (TreeSitter.node_text n source)
          | None -> Printf.printf "No name field\n");
          
          (match TreeSitter.node_child_by_field_name node "type" with
          | Some n -> Printf.printf "Type field: %s\n" (TreeSitter.node_text n source)
          | None -> Printf.printf "No type field\n");
          
          (match TreeSitter.node_child_by_field_name node "value" with
          | Some n -> Printf.printf "Value field: %s\n" (TreeSitter.node_text n source)
          | None -> Printf.printf "No value field\n");
          
          (* Print all named children *)
          let count = TreeSitter.node_named_child_count node in
          Printf.printf "Named children count: %d\n" count;
          for i = 0 to count - 1 do
            match TreeSitter.node_named_child node i with
            | Some child -> 
                Printf.printf "  Child %d: %s = '%s'\n" i 
                  (TreeSitter.node_type child) 
                  (TreeSitter.node_text child source)
            | None -> ()
          done)
