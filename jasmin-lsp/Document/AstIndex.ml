




(* Legacy AstIndex module - no longer used after switching to tree-sitter *)
(* All functions now return None/empty results *)

type position = (int * int)
type file_position = (string * position)

let empty = BatMap.empty

(* Stubbed out - no longer uses Jasmin types *)
let find_definition _name_pos _prog =
  None
