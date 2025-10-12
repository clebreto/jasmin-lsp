(** Server state containing document store and other global state *)

type t = {
  document_store: Document.DocumentStore.t;
  prog: (unit, unit) Jasmin.Prog.prog option ref;
  master_file: Lsp.Types.DocumentUri.t option ref;
}

let create () = {
  document_store = Document.DocumentStore.create ();
  prog = ref None;
  master_file = ref None;
}

let get_document_store state = state.document_store

let get_prog state = !(state.prog)

let set_prog state prog = state.prog := Some prog

let get_master_file state = !(state.master_file)

let set_master_file state uri = 
  state.master_file := Some uri;
  Io.Logger.log (Format.asprintf "Master file set to: %s" (Lsp.Types.DocumentUri.to_string uri))
