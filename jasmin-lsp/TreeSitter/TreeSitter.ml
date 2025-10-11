(** OCaml bindings for tree-sitter library *)

(** {1 Core Types} *)

type parser
type tree
type node
type language

(** {1 Position and Range Types} *)

type point = {
  row : int;
  column : int;
}

type range = {
  start_point : point;
  end_point : point;
  start_byte : int;
  end_byte : int;
}

(** {1 External C Bindings} *)

external parser_new : unit -> parser = "caml_ts_parser_new"
external parser_delete : parser -> unit = "caml_ts_parser_delete"
external parser_set_language : parser -> language -> unit = "caml_ts_parser_set_language"
external language_jasmin : unit -> language = "caml_ts_language_jasmin"

external parser_parse_string : parser -> string -> tree option = "caml_ts_parser_parse_string"
external parser_parse_string_with_tree : parser -> tree option -> string -> tree option = "caml_ts_parser_parse_string_with_tree"

external tree_root_node : tree -> node = "caml_ts_tree_root_node"
external tree_delete : tree -> unit = "caml_ts_tree_delete"
external tree_copy : tree -> tree = "caml_ts_tree_copy"

external node_type : node -> string = "caml_ts_node_type"
external node_symbol : node -> int = "caml_ts_node_symbol"
external node_is_named : node -> bool = "caml_ts_node_is_named"
external node_has_error : node -> bool = "caml_ts_node_has_error"
external node_is_missing : node -> bool = "caml_ts_node_is_missing"
external node_range : node -> range = "caml_ts_node_range"
external node_start_point : node -> point = "caml_ts_node_start_point"
external node_end_point : node -> point = "caml_ts_node_end_point"
external node_start_byte : node -> int = "caml_ts_node_start_byte"
external node_end_byte : node -> int = "caml_ts_node_end_byte"
external node_child_count : node -> int = "caml_ts_node_child_count"
external node_child : node -> int -> node option = "caml_ts_node_child"
external node_named_child_count : node -> int = "caml_ts_node_named_child_count"
external node_named_child : node -> int -> node option = "caml_ts_node_named_child"
external node_child_by_field_name : node -> string -> node option = "caml_ts_node_child_by_field_name"
external node_parent : node -> node option = "caml_ts_node_parent"
external node_next_sibling : node -> node option = "caml_ts_node_next_sibling"
external node_prev_sibling : node -> node option = "caml_ts_node_prev_sibling"
external node_next_named_sibling : node -> node option = "caml_ts_node_next_named_sibling"
external node_prev_named_sibling : node -> node option = "caml_ts_node_prev_named_sibling"
external node_text : node -> string -> string = "caml_ts_node_text"
external node_descendant_for_point_range : node -> point -> point -> node option = "caml_ts_node_descendant_for_point_range"
external node_named_descendant_for_point_range : node -> point -> point -> node option = "caml_ts_node_named_descendant_for_point_range"
external node_is_error : node -> bool = "caml_ts_node_is_error"

(** {1 Utility Functions} *)

let point_from_byte source byte_offset =
  let row = ref 0 in
  let column = ref 0 in
  let i = ref 0 in
  while !i < byte_offset && !i < String.length source do
    if source.[!i] = '\n' then begin
      row := !row + 1;
      column := 0
    end else begin
      column := !column + 1
    end;
    i := !i + 1
  done;
  { row = !row; column = !column }

(** {1 Helper Functions} *)

(** Iterate over all children of a node *)
let node_children node =
  let count = node_child_count node in
  let rec loop i acc =
    if i >= count then List.rev acc
    else
      match node_child node i with
      | None -> loop (i + 1) acc
      | Some child -> loop (i + 1) (child :: acc)
  in
  loop 0 []

(** Iterate over all named children of a node *)
let node_named_children node =
  let count = node_named_child_count node in
  let rec loop i acc =
    if i >= count then List.rev acc
    else
      match node_named_child node i with
      | None -> loop (i + 1) acc
      | Some child -> loop (i + 1) (child :: acc)
  in
  loop 0 []

(** Fold over all children of a node *)
let node_fold_children f init node =
  let children = node_children node in
  List.fold_left f init children

(** Fold over all named children of a node *)
let node_fold_named_children f init node =
  let children = node_named_children node in
  List.fold_left f init children

(** Find a child matching a predicate *)
let node_find_child predicate node =
  let children = node_children node in
  List.find_opt predicate children

(** Find a named child matching a predicate *)
let node_find_named_child predicate node =
  let children = node_named_children node in
  List.find_opt predicate children

(** Check if a point is within a node's range *)
let point_in_range point range =
  let { start_point; end_point; _ } = range in
  (point.row > start_point.row || (point.row = start_point.row && point.column >= start_point.column)) &&
  (point.row < end_point.row || (point.row = end_point.row && point.column <= end_point.column))

(** Get a node at a specific point *)
let node_at_point root point =
  node_named_descendant_for_point_range root point point
