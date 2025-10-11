(** OCaml bindings for tree-sitter library *)

(** {1 Core Types} *)

(** Opaque type representing a tree-sitter parser *)
type parser

(** Opaque type representing a parsed syntax tree *)
type tree

(** Opaque type representing a node in the syntax tree *)
type node

(** Opaque type representing the language grammar *)
type language

(** {1 Position and Range Types} *)

(** Point in the source code (row, column) *)
type point = {
  row : int;
  column : int;
}

(** Range in the source code *)
type range = {
  start_point : point;
  end_point : point;
  start_byte : int;
  end_byte : int;
}

(** {1 Parser Creation and Management} *)

(** Create a new parser instance *)
val parser_new : unit -> parser

(** Delete a parser instance *)
val parser_delete : parser -> unit

(** Set the language for the parser *)
val parser_set_language : parser -> language -> unit

(** Get the Jasmin language definition *)
val language_jasmin : unit -> language

(** {1 Parsing} *)

(** Parse a string and return a syntax tree *)
val parser_parse_string : parser -> string -> tree option

(** Parse a string with an old tree for incremental parsing *)
val parser_parse_string_with_tree : parser -> tree option -> string -> tree option

(** {1 Tree Operations} *)

(** Get the root node of a tree *)
val tree_root_node : tree -> node

(** Delete a tree instance *)
val tree_delete : tree -> unit

(** Copy a tree *)
val tree_copy : tree -> tree

(** {1 Node Operations} *)

(** Get the type (kind) of a node as a string *)
val node_type : node -> string

(** Get the symbol ID of a node *)
val node_symbol : node -> int

(** Check if a node is named (not anonymous) *)
val node_is_named : node -> bool

(** Check if a node has an error *)
val node_has_error : node -> bool

(** Check if a node is missing (syntax error) *)
val node_is_missing : node -> bool

(** Get the range of a node *)
val node_range : node -> range

(** Get the start position of a node *)
val node_start_point : node -> point

(** Get the end position of a node *)
val node_end_point : node -> point

(** Get the start byte offset of a node *)
val node_start_byte : node -> int

(** Get the end byte offset of a node *)
val node_end_byte : node -> int

(** Get the number of children of a node *)
val node_child_count : node -> int

(** Get the nth child of a node *)
val node_child : node -> int -> node option

(** Get the number of named children of a node *)
val node_named_child_count : node -> int

(** Get the nth named child of a node *)
val node_named_child : node -> int -> node option

(** Get a child by field name *)
val node_child_by_field_name : node -> string -> node option

(** Get the parent of a node *)
val node_parent : node -> node option

(** Get the next sibling of a node *)
val node_next_sibling : node -> node option

(** Get the previous sibling of a node *)
val node_prev_sibling : node -> node option

(** Get the next named sibling of a node *)
val node_next_named_sibling : node -> node option

(** Get the previous named sibling of a node *)
val node_prev_named_sibling : node -> node option

(** Get the text content of a node from the source string *)
val node_text : node -> string -> string

(** {1 Query Operations} *)

(** Get a descendant node at a given point *)
val node_descendant_for_point_range : node -> point -> point -> node option

(** Get a named descendant node at a given point *)
val node_named_descendant_for_point_range : node -> point -> point -> node option

(** Get a node at a specific point *)
val node_at_point : node -> point -> node option

(** {1 Utility Functions} *)

(** Convert a byte offset to a point in the source code *)
val point_from_byte : string -> int -> point

(** Check if a node represents a syntax error *)
val node_is_error : node -> bool

(** Check if a point is within a range *)
val point_in_range : point -> range -> bool
