(** Document Store - Manages open documents and their parse trees *)

type document = {
  uri: Lsp.Types.DocumentUri.t;
  text: string;
  version: int;
  tree: TreeSitter.tree option;
}

type t = {
  mutable documents: (Lsp.Types.DocumentUri.t * document) list;
  parser: TreeSitter.parser;
}

(** Global parser instance - created once and reused *)
let global_parser = lazy (
  let parser = TreeSitter.parser_new () in
  let language = TreeSitter.language_jasmin () in
  TreeSitter.parser_set_language parser language;
  parser
)

let get_parser () = Lazy.force global_parser

let create () = {
  documents = [];
  parser = get_parser ();
}

let parse_document parser text old_tree =
  try
    let result = TreeSitter.parser_parse_string_with_tree parser old_tree text in
    (match result with
    | Some _ -> Io.Logger.log "Successfully parsed document"
    | None -> Io.Logger.log "Parser returned None");
    result
  with
  | e -> 
      Io.Logger.log (Format.asprintf "Failed to parse document: %s" (Printexc.to_string e));
      None

let open_document store uri text version =
  Io.Logger.log (Format.asprintf "Opening document: %s (version %d, %d bytes)" 
    (Lsp.Types.DocumentUri.to_string uri) version (String.length text));
  let tree = parse_document store.parser text None in
  let doc = { uri; text; version; tree } in
  store.documents <- (uri, doc) :: store.documents;
  Io.Logger.log (Format.asprintf "Document opened: %s (tree=%s)" 
    (Lsp.Types.DocumentUri.to_string uri)
    (match tree with Some _ -> "Some" | None -> "None"))

let update_document store uri text version =
  match List.assoc_opt uri store.documents with
  | None ->
      Io.Logger.log (Format.asprintf "Warning: Updating non-open document %s" 
        (Lsp.Types.DocumentUri.to_string uri));
      open_document store uri text version
  | Some old_doc ->
      let tree = parse_document store.parser text old_doc.tree in
      let doc = { uri; text; version; tree } in
      store.documents <- (uri, doc) :: (List.remove_assoc uri store.documents);
      Io.Logger.log (Format.asprintf "Updated document: %s (version %d)" 
        (Lsp.Types.DocumentUri.to_string uri) version)

let close_document store uri =
  match List.assoc_opt uri store.documents with
  | None ->
      Io.Logger.log (Format.asprintf "Warning: Closing non-open document %s" 
        (Lsp.Types.DocumentUri.to_string uri))
  | Some doc ->
      (* Clean up the tree if it exists *)
      (match doc.tree with
      | Some tree -> TreeSitter.tree_delete tree
      | None -> ());
      store.documents <- List.remove_assoc uri store.documents;
      Io.Logger.log (Format.asprintf "Closed document: %s" 
        (Lsp.Types.DocumentUri.to_string uri))

let get_document store uri =
  List.assoc_opt uri store.documents

let get_text store uri =
  match get_document store uri with
  | Some doc -> Some doc.text
  | None -> None

let get_tree store uri =
  match get_document store uri with
  | Some doc -> doc.tree
  | None -> None

let get_all_uris store =
  List.map fst store.documents

let is_open store uri =
  List.mem_assoc uri store.documents
