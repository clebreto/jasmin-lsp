(** Server state containing document store and other global state *)

type t = {
  document_store: Document.DocumentStore.t;
  prog: (unit, unit) Jasmin.Prog.prog option ref;
}

let create () = {
  document_store = Document.DocumentStore.create ();
  prog = ref None;
}

let get_document_store state = state.document_store

let get_prog state = !(state.prog)

let set_prog state prog = state.prog := Some prog
