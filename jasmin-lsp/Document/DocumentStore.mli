(** Document Store - Manages open documents and their parse trees *)

(** Document information *)
type document = {
  uri: Lsp.Types.DocumentUri.t;
  text: string;
  version: int;
  tree: TreeSitter.tree option;
}

(** The document store type *)
type t

(** Create a new empty document store *)
val create : unit -> t

(** Open a document and parse it *)
val open_document : t -> Lsp.Types.DocumentUri.t -> string -> int -> unit

(** Update a document with new content and reparse *)
val update_document : t -> Lsp.Types.DocumentUri.t -> string -> int -> unit

(** Close a document *)
val close_document : t -> Lsp.Types.DocumentUri.t -> unit

(** Get a document by URI *)
val get_document : t -> Lsp.Types.DocumentUri.t -> document option

(** Get the text of a document *)
val get_text : t -> Lsp.Types.DocumentUri.t -> string option

(** Get the parse tree of a document *)
val get_tree : t -> Lsp.Types.DocumentUri.t -> TreeSitter.tree option

(** Get all open document URIs *)
val get_all_uris : t -> Lsp.Types.DocumentUri.t list

(** Check if a document is open *)
val is_open : t -> Lsp.Types.DocumentUri.t -> bool

(** Get parser instance (shared across all documents) *)
val get_parser : unit -> TreeSitter.parser
