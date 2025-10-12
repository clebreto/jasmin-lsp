
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
    Printf.printf "%s%s: '%s'\n" indent node_type short_text;
    
    let child_count = node_named_child_count node in
    for i = 0 to child_count - 1 do
      match node_named_child node i with
      | Some child -> print_node (indent ^ "  ") child
      | None -> ()
    done
  in
  
  print_node "" root
