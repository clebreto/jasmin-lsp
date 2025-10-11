open RpcProtocolEvent

(** Global server state *)
let server_state = ref (ServerState.create ())



let get_initialize_response (params : Lsp.Types.InitializeParams.t) =
  let param_options = params.initializationOptions in
  let _ = match param_options with
  | None -> Io.Logger.log  "Failed to decode initialization options\n"; ()
  | Some _ -> ()
  in
  let server_infos = Lsp.Types.InitializeResult.create_serverInfo
    ~name:Config.name
    ~version:Config.version
    ()
  in
  let content = Lsp.Types.InitializeResult.{
    capabilities= Config.capabilities;
    serverInfo=Some (server_infos)
  }
  in
  content

let configuration_request =
  let id = `Int Config.conf_request_id in
  let items = [
    Lsp.Types.ConfigurationItem.{ scopeUri = None; section = Some (Config.name) }] in
  let content = Lsp.Server_request.(to_jsonrpc_request (WorkspaceConfiguration { items }) ~id) in
  Jsonrpc.Packet.Request content

let receive_initialize_request (params : Lsp.Types.InitializeParams.t) =
  let initialize_response = get_initialize_response params in
  let config = Jsonrpc.Packet.yojson_of_t configuration_request in
  Ok(initialize_response), [(Priority.Low, Send config)]

(** Recursively collect all files reachable through require statements *)
let rec collect_required_files_recursive uri visited =
  if List.mem uri visited then
    visited  (* Already visited, avoid cycles *)
  else
    let visited = uri :: visited in
    match Document.DocumentStore.get_tree (!server_state).document_store uri,
          Document.DocumentStore.get_text (!server_state).document_store uri with
    | Some tree, Some source ->
        let required_uris = Document.SymbolTable.extract_required_files uri source tree in
        Io.Logger.log (Format.asprintf "Found %d requires in %s" 
          (List.length required_uris) (Lsp.Types.DocumentUri.to_string uri));
        (* Recursively collect from each required file *)
        List.fold_left (fun acc req_uri ->
          collect_required_files_recursive req_uri acc
        ) visited required_uris
    | _ -> visited

(** Get all files relevant for symbol lookup: open files + their transitive dependencies *)
let get_all_relevant_files uri =
  (* Start with all open files *)
  let open_files = Document.DocumentStore.get_all_uris (!server_state).document_store in
  Io.Logger.log (Format.asprintf "Starting with %d open files" (List.length open_files));
  
  (* For each open file, collect its transitive dependencies *)
  let all_files = List.fold_left (fun acc file_uri ->
    let with_deps = collect_required_files_recursive file_uri [] in
    (* Merge, avoiding duplicates *)
    List.fold_left (fun acc2 u -> 
      if List.mem u acc2 then acc2 else u :: acc2
    ) acc with_deps
  ) [] open_files in
  
  (* Make sure the current file is included *)
  let all_files = if List.mem uri all_files then all_files else uri :: all_files in
  
  Io.Logger.log (Format.asprintf "Total files including dependencies: %d" (List.length all_files));
  all_files

let receive_text_document_definition_request (params : Lsp.Types.DefinitionParams.t) (prog:('info,'asm) Jasmin.Prog.prog option) =
  let uri = params.textDocument.uri in
  let position = params.position in
  let point = { TreeSitter.row = position.line; column = position.character } in
  
  Io.Logger.log (Format.asprintf "Definition request for %s at %d:%d" 
    (Lsp.Types.DocumentUri.to_string uri) position.line position.character);
  
  (* Helper: Check if node is inside a require statement *)
  let rec is_in_require_statement node =
    match TreeSitter.node_type node with
    | "require" -> true
    | _ -> 
        match TreeSitter.node_parent node with
        | None -> false
        | Some parent -> is_in_require_statement parent
  in
  
  (* Helper: Resolve file path relative to current document *)
  let resolve_required_file current_uri filename =
    try
      let current_path = Lsp.Uri.to_path current_uri in
      let current_dir = Filename.dirname current_path in
      let resolved_path = Filename.concat current_dir filename in
      
      (* Check if file exists *)
      if Sys.file_exists resolved_path then
        Some (Lsp.Uri.of_path resolved_path)
      else (
        Io.Logger.log (Format.asprintf "Required file not found: %s" resolved_path);
        None
      )
    with e ->
      Io.Logger.log (Format.asprintf "Error resolving file path: %s" (Printexc.to_string e));
      None
  in
  
  (* Try tree-sitter based approach first *)
  match Document.DocumentStore.get_tree (!server_state).document_store uri,
        Document.DocumentStore.get_text (!server_state).document_store uri with
  | Some tree, Some source ->
      Io.Logger.log "Found tree and source for definition request";
      let symbols = Document.SymbolTable.extract_symbols uri source tree in
      let root = TreeSitter.tree_root_node tree in
      
      (* Find the node at cursor position *)
      (match TreeSitter.node_at_point root point with
      | None -> Error "No symbol at position", []
      | Some node ->
          let node_type = TreeSitter.node_type node in
          
          (* Check if cursor is on a string literal in a require statement *)
          if (node_type = "string_literal" || node_type = "string_content") && is_in_require_statement node then (
            Io.Logger.log "Cursor is on a require statement string";
            
            (* Get the string content node if we're on string_literal *)
            let content_node = 
              if node_type = "string_literal" then
                match TreeSitter.node_child_by_field_name node "content" with
                | Some n -> n
                | None -> node
              else node
            in
            
            let filename = TreeSitter.node_text content_node source in
            Io.Logger.log (Format.asprintf "Attempting to resolve required file: %s" filename);
            
            match resolve_required_file uri filename with
            | Some target_uri ->
                let location = Lsp.Types.Location.create
                  ~uri:target_uri
                  ~range:(Lsp.Types.Range.create 
                    ~start:(Lsp.Types.Position.create ~line:0 ~character:0)
                    ~end_:(Lsp.Types.Position.create ~line:0 ~character:0))
                in
                Io.Logger.log (Format.asprintf "Resolved to: %s" (Lsp.Types.DocumentUri.to_string target_uri));
                Ok (Some (`Location [location])), []
            | None ->
                Error "Required file not found", []
          ) else (
            (* Standard symbol-based goto definition *)
            let symbol_name = TreeSitter.node_text node source in
            Io.Logger.log (Format.asprintf "Looking for definition of symbol: %s" symbol_name);
            
            (* First try to find in current file *)
            match Document.SymbolTable.find_definition symbols symbol_name with
            | Some symbol ->
                Io.Logger.log (Format.asprintf "Found definition in current file");
                let location = Lsp.Types.Location.create
                  ~uri:symbol.uri
                  ~range:(Document.SymbolTable.range_to_lsp_range symbol.definition_range)
                in
                Ok (Some (`Location [location])), []
            | None ->
                (* Not in current file, search all files including dependencies *)
                Io.Logger.log "Not found in current file, searching other files and dependencies";
                let all_uris = get_all_relevant_files uri in
                let rec search_files uris acc_trees =
                  match uris with
                  | [] -> 
                      (* Keep trees alive *)
                      let _ = acc_trees in
                      None
                  | search_uri :: rest ->
                      if search_uri = uri then
                        (* Skip current file, already searched *)
                        search_files rest acc_trees
                      else
                        (* Try to load the file if not already open *)
                        let tree_opt, source_opt, new_tree = 
                          match Document.DocumentStore.get_tree (!server_state).document_store search_uri,
                                Document.DocumentStore.get_text (!server_state).document_store search_uri with
                          | Some t, Some s -> Some t, Some s, None
                          | _ ->
                              (* File not open, try to load it from disk *)
                              try
                                let path = Lsp.Uri.to_path search_uri in
                                if Sys.file_exists path then (
                                  let ic = open_in path in
                                  let len = in_channel_length ic in
                                  let content = really_input_string ic len in
                                  close_in ic;
                                  let parser = Document.DocumentStore.get_parser () in
                                  let parsed_tree = TreeSitter.parser_parse_string parser content in
                                  (match parsed_tree with
                                  | Some t -> Some t, Some content, Some t
                                  | None -> None, Some content, None)
                                ) else None, None, None
                              with e ->
                                Io.Logger.log (Format.asprintf "Error loading file %s: %s" 
                                  (Lsp.Types.DocumentUri.to_string search_uri)
                                  (Printexc.to_string e));
                                None, None, None
                        in
                        (* Add new tree to accumulator *)
                        let new_acc = match new_tree with
                          | Some t -> t :: acc_trees
                          | None -> acc_trees
                        in
                        (* Extract symbols immediately while tree is still valid *)
                        let result = 
                          try
                            match tree_opt, source_opt with
                            | Some search_tree, Some search_source ->
                                let search_symbols = Document.SymbolTable.extract_symbols search_uri search_source search_tree in
                                (match Document.SymbolTable.find_definition search_symbols symbol_name with
                                | Some symbol ->
                                    Io.Logger.log (Format.asprintf "Found definition in file: %s" 
                                      (Lsp.Types.DocumentUri.to_string search_uri));
                                    (* Keep trees alive *)
                                    let _ = new_acc in
                                    Some symbol
                                | None -> None)
                            | _ -> None
                          with e ->
                            Io.Logger.log (Format.asprintf "Error extracting symbols from %s: %s\n%s" 
                              (Lsp.Types.DocumentUri.to_string search_uri)
                              (Printexc.to_string e)
                              (Printexc.get_backtrace ()));
                            None
                        in
                        match result with
                        | Some symbol -> Some symbol
                        | None -> search_files rest new_acc
                in
                match search_files all_uris [] with
                | Some symbol ->
                    let location = Lsp.Types.Location.create
                      ~uri:symbol.uri
                      ~range:(Document.SymbolTable.range_to_lsp_range symbol.definition_range)
                    in
                    Ok (Some (`Location [location])), []
                | None ->
                    Io.Logger.log "Definition not found in any open file";
                    Error "No definition found", []
          ))
  | _ ->
      Io.Logger.log (Format.asprintf "No tree or source available for %s" 
        (Lsp.Types.DocumentUri.to_string uri));
      (* Fallback to old Jasmin AST-based approach *)
      match params.partialResultToken with
      | None -> Error "No text document provided", []
      | Some text_doc ->
        match text_doc with
        | `Int id -> Error "Invalid token type", []
        | `String name ->
          match prog with
          | None -> Error "Static program not set", []
          | Some prog ->
            let pos = (Lsp.Types.DocumentUri.to_string params.textDocument.uri, (params.position.character, params.position.line)) in
            let definition = Document.AstIndex.find_definition (name, pos) prog in
            match definition with
            | None -> Error "No definition found", []
            | Some (loc_start,loc_end,loc_file) ->
              let rg = Lsp.Types.Range.create ~end_:loc_end ~start:loc_start in
              let def = Some (`Location [(Lsp.Types.Location.create ~range:rg ~uri:loc_file)]) in
                Ok(def), []

(** Handle find references request *)
let receive_text_document_references_request (params : Lsp.Types.ReferenceParams.t) =
  let uri = params.textDocument.uri in
  let position = params.position in
  let point = { TreeSitter.row = position.line; column = position.character } in
  
  match Document.DocumentStore.get_tree (!server_state).document_store uri,
        Document.DocumentStore.get_text (!server_state).document_store uri with
  | Some tree, Some source ->
      let root = TreeSitter.tree_root_node tree in
      
      (* Find the symbol at cursor *)
      (match TreeSitter.node_at_point root point with
      | None -> Error "No symbol at position", []
      | Some node ->
          let symbol_name = TreeSitter.node_text node source in
          Io.Logger.log (Format.asprintf "Finding references for '%s'" symbol_name);
          
          (* Search all relevant files including dependencies *)
          let all_uris = get_all_relevant_files uri in
          let all_references, _ = List.fold_left (fun (acc, trees) doc_uri ->
            try
              (* Try to get the document from store or load from disk *)
              let tree_opt, source_opt, new_tree =
                match Document.DocumentStore.get_tree (!server_state).document_store doc_uri,
                      Document.DocumentStore.get_text (!server_state).document_store doc_uri with
                | Some t, Some s -> Some t, Some s, None
                | _ ->
                    (* File not open, try to load it from disk *)
                    try
                      let path = Lsp.Uri.to_path doc_uri in
                      if Sys.file_exists path then (
                        let ic = open_in path in
                        let len = in_channel_length ic in
                        let content = really_input_string ic len in
                        close_in ic;
                        let parser = Document.DocumentStore.get_parser () in
                        let parsed_tree = TreeSitter.parser_parse_string parser content in
                        (match parsed_tree with
                        | Some t -> Some t, Some content, Some t
                        | None -> None, Some content, None)
                      ) else None, None, None
                    with e ->
                      Io.Logger.log (Format.asprintf "Error loading file %s: %s"
                        (Lsp.Types.DocumentUri.to_string doc_uri)
                        (Printexc.to_string e));
                      None, None, None
              in
              (* Keep new tree in accumulator *)
              let new_trees = match new_tree with
                | Some t -> t :: trees
                | None -> trees
              in
              (* Extract references immediately while tree is valid *)
              (try
                match tree_opt, source_opt with
                | Some doc_tree, Some doc_source ->
                    let references = Document.SymbolTable.extract_references doc_uri doc_source doc_tree in
                    let matching_refs = Document.SymbolTable.find_references_to references symbol_name in
                    (acc @ matching_refs, new_trees)
                | _ -> (acc, new_trees)
              with e ->
                Io.Logger.log (Format.asprintf "Error extracting references from %s: %s\n%s"
                  (Lsp.Types.DocumentUri.to_string doc_uri)
                  (Printexc.to_string e)
                  (Printexc.get_backtrace ()));
                (acc, new_trees))
            with e ->
              Io.Logger.log (Format.asprintf "Error processing file %s: %s\n%s"
                (Lsp.Types.DocumentUri.to_string doc_uri)
                (Printexc.to_string e)
                (Printexc.get_backtrace ()));
              (acc, trees)
          ) ([], []) all_uris in
          
          let locations = List.map (fun ref ->
            Lsp.Types.Location.create
              ~uri:ref.Document.SymbolTable.uri
              ~range:(Document.SymbolTable.range_to_lsp_range ref.Document.SymbolTable.range)
          ) all_references in
          
          Io.Logger.log (Format.asprintf "Found %d references for '%s'" (List.length locations) symbol_name);
          Ok (Some locations), [])
  | _ -> Error "Document not open or not parsed", []

(** Handle hover request *)
let receive_text_document_hover_request (params : Lsp.Types.HoverParams.t) =
  let uri = params.textDocument.uri in
  let position = params.position in
  let point = { TreeSitter.row = position.line; column = position.character } in
  
  (* Jasmin keywords that should not be looked up as symbols *)
  let jasmin_keywords = [
    "fn"; "inline"; "export"; "return"; "if"; "else"; "while"; "for";
    "require"; "from"; "param"; "global"; "reg"; "stack"; "const";
    "int"; "u8"; "u16"; "u32"; "u64"; "u128"; "u256";
  ] in
  
  (* Keyword documentation *)
  let keyword_docs = function
    | "fn" -> Some "Function declaration keyword\n\nSyntax: `fn name(params) -> return_type { ... }`"
    | "inline" -> Some "Inline function modifier\n\nInline functions are expanded at call site."
    | "export" -> Some "Export modifier\n\nMakes a function visible outside the module."
    | "return" -> Some "Return statement\n\nReturns a value from a function."
    | "if" -> Some "Conditional statement\n\nSyntax: `if condition { ... } else { ... }`"
    | "else" -> Some "Else clause\n\nExecuted when if condition is false."
    | "while" -> Some "While loop\n\nSyntax: `while condition { ... }`"
    | "for" -> Some "For loop\n\nSyntax: `for i = start to end { ... }`"
    | "require" -> Some "Import directive\n\nSyntax: `require \"filename.jazz\"`\n\nImports symbols from another file."
    | "from" -> Some "Namespace import\n\nSyntax: `from NAMESPACE require \"file.jazz\"`"
    | "param" -> Some "Compile-time parameter\n\nSyntax: `param type NAME = value;`\n\nDefines a compile-time constant."
    | "global" -> Some "Global variable declaration\n\nSyntax: `type NAME = value;`"
    | "reg" -> Some "Register storage class\n\nValues stored in CPU registers."
    | "stack" -> Some "Stack storage class\n\nValues stored on the stack."
    | "const" -> Some "Constant modifier"
    | _ -> None
  in
  
  match Document.DocumentStore.get_tree (!server_state).document_store uri,
        Document.DocumentStore.get_text (!server_state).document_store uri with
  | Some tree, Some source ->
      let root = TreeSitter.tree_root_node tree in
      
      (* Find the symbol at cursor *)
      (match TreeSitter.node_at_point root point with
      | None -> Error "No symbol at position", []
      | Some node ->
          let symbol_name = TreeSitter.node_text node source in
          Io.Logger.log (Format.asprintf "Hover: Looking for symbol '%s'" symbol_name);
          
          (* Check if it's a keyword *)
          if List.mem symbol_name jasmin_keywords then (
            Io.Logger.log (Format.asprintf "Hover: '%s' is a keyword" symbol_name);
            match keyword_docs symbol_name with
            | Some doc ->
                let hover_content = `MarkupContent (Lsp.Types.MarkupContent.create
                  ~kind:Lsp.Types.MarkupKind.Markdown
                  ~value:(Format.asprintf "**%s** _(keyword)_\n\n%s" symbol_name doc))
                in
                let hover = Lsp.Types.Hover.create ~contents:hover_content () in
                Ok (Some hover), []
            | None ->
                (* Return nothing for keywords without docs *)
                Ok None, []
          ) else (
          (* Search across all documents including dependencies *)
          let all_uris = get_all_relevant_files uri in
          let rec search_documents uris acc_trees =
            match uris with
            | [] -> 
                (* Keep trees alive until we're done searching all files *)
                let _ = acc_trees in
                None
            | doc_uri :: rest ->
                try
                  (* Try to get the document from store or load from disk *)
                  let tree_opt, source_opt, new_tree =
                    match Document.DocumentStore.get_tree (!server_state).document_store doc_uri,
                          Document.DocumentStore.get_text (!server_state).document_store doc_uri with
                    | Some t, Some s -> Some t, Some s, None
                    | _ ->
                        (* File not open, try to load it from disk *)
                        try
                          let path = Lsp.Uri.to_path doc_uri in
                          if Sys.file_exists path then (
                            let ic = open_in path in
                            let len = in_channel_length ic in
                            let content = really_input_string ic len in
                            close_in ic;
                            let parser = Document.DocumentStore.get_parser () in
                            let parsed_tree = TreeSitter.parser_parse_string parser content in
                            (* Keep the parsed tree in a list to prevent GC *)
                            (match parsed_tree with
                            | Some t -> Some t, Some content, Some t
                            | None -> None, Some content, None)
                          ) else None, None, None
                        with e ->
                          Io.Logger.log (Format.asprintf "Error loading file %s: %s"
                            (Lsp.Types.DocumentUri.to_string doc_uri)
                            (Printexc.to_string e));
                          None, None, None
                  in
                  (* Add new tree to accumulator to keep it alive *)
                  let new_acc = match new_tree with
                    | Some t -> t :: acc_trees
                    | None -> acc_trees
                  in
                  (* Extract symbols immediately while tree is valid *)
                  (match tree_opt, source_opt with
                  | Some doc_tree, Some doc_source ->
                      (try
                        let doc_symbols = Document.SymbolTable.extract_symbols doc_uri doc_source doc_tree in
                        (match Document.SymbolTable.find_definition doc_symbols symbol_name with
                        | Some symbol -> 
                            Io.Logger.log (Format.asprintf "Hover: Found symbol '%s' in %s" 
                              symbol_name (Lsp.Types.DocumentUri.to_string doc_uri));
                            (* Keep trees alive by referencing them *)
                            let _ = new_acc in
                            Some symbol
                        | None -> search_documents rest new_acc)
                      with e ->
                        Io.Logger.log (Format.asprintf "Error extracting symbols from %s: %s\n%s"
                          (Lsp.Types.DocumentUri.to_string doc_uri)
                          (Printexc.to_string e)
                          (Printexc.get_backtrace ()));
                        search_documents rest new_acc)
                  | _ -> search_documents rest new_acc)
                with e ->
                  Io.Logger.log (Format.asprintf "Error processing file %s: %s\n%s"
                    (Lsp.Types.DocumentUri.to_string doc_uri)
                    (Printexc.to_string e)
                    (Printexc.get_backtrace ()));
                  search_documents rest acc_trees
          in
          
          match search_documents all_uris [] with
          | None -> 
              Io.Logger.log (Format.asprintf "Hover: No definition found for '%s'" symbol_name);
              Ok None, []  (* Return None instead of error for unknown symbols *)
          | Some symbol ->
              (* Format hover content based on symbol kind *)
              let content = match symbol.kind with
              | Document.SymbolTable.Parameter | Document.SymbolTable.Variable ->
                  (match symbol.detail with
                  | Some type_str -> Format.asprintf "%s: %s" symbol.name type_str
                  | None -> Format.asprintf "%s: <unknown type>" symbol.name)
              | Document.SymbolTable.Function ->
                  (match symbol.detail with
                  | Some fn_sig -> fn_sig
                  | None -> Format.asprintf "fn %s" symbol.name)
              | Document.SymbolTable.Type ->
                  Format.asprintf "type %s" symbol.name
              | Document.SymbolTable.Constant ->
                  Format.asprintf "const %s" symbol.name
              in
              let hover_content = `MarkupContent (Lsp.Types.MarkupContent.create
                ~kind:Lsp.Types.MarkupKind.Markdown
                ~value:(Format.asprintf "```jasmin\n%s\n```" content))
              in
              let hover = Lsp.Types.Hover.create
                ~contents:hover_content
                ()
              in
              Io.Logger.log (Format.asprintf "Hover: Returning info for '%s'" symbol.name);
              Ok (Some hover), []))
  | _ -> Error "Document not open or not parsed", []

(** Handle document symbol request *)
let receive_text_document_document_symbol_request (params : Lsp.Types.DocumentSymbolParams.t) =
  let uri = params.textDocument.uri in
  
  match Document.DocumentStore.get_tree (!server_state).document_store uri,
        Document.DocumentStore.get_text (!server_state).document_store uri with
  | Some tree, Some source ->
      let symbols = Document.SymbolTable.extract_symbols uri source tree in
      let document_symbols = List.map Document.SymbolTable.symbol_to_document_symbol symbols in
      Ok (Some (`DocumentSymbol document_symbols)), []
  | _ -> Error "Document not open or not parsed", []

(** Handle workspace symbol request *)
let receive_workspace_symbol_request (params : Lsp.Types.WorkspaceSymbolParams.t) =
  let query = params.query in
  let all_uris = Document.DocumentStore.get_all_uris (!server_state).document_store in
  
  let all_symbols = List.concat_map (fun uri ->
    match Document.DocumentStore.get_tree (!server_state).document_store uri,
          Document.DocumentStore.get_text (!server_state).document_store uri with
    | Some tree, Some source ->
        Document.SymbolTable.extract_symbols uri source tree
    | _ -> []
  ) all_uris in
  
  (* Filter symbols by query *)
  let filtered_symbols = 
    if query = "" then all_symbols
    else List.filter (fun sym ->
      let name_lower = String.lowercase_ascii sym.Document.SymbolTable.name in
      let query_lower = String.lowercase_ascii query in
      try
        let _ = Str.search_forward (Str.regexp_string query_lower) name_lower 0 in
        true
      with Not_found -> false
    ) all_symbols
  in
  
  let symbol_infos = List.map Document.SymbolTable.symbol_to_lsp filtered_symbols in
  Ok (Some symbol_infos), []

(** Handle rename request *)
let receive_text_document_rename_request (params : Lsp.Types.RenameParams.t) =
  let uri = params.textDocument.uri in
  let position = params.position in
  let new_name = params.newName in
  let point = { TreeSitter.row = position.line; column = position.character } in
  
  match Document.DocumentStore.get_tree (!server_state).document_store uri,
        Document.DocumentStore.get_text (!server_state).document_store uri with
  | Some tree, Some source ->
      let root = TreeSitter.tree_root_node tree in
      
      (* Find the symbol at cursor *)
      (match TreeSitter.node_at_point root point with
      | None -> Error "No symbol at position", []
      | Some node ->
          let symbol_name = TreeSitter.node_text node source in
          
          (* Find all references to this symbol *)
          let references = Document.SymbolTable.extract_references uri source tree in
          let matching_refs = Document.SymbolTable.find_references_to references symbol_name in
          
          (* Create text edits for each reference *)
          let edits = List.map (fun ref ->
            Lsp.Types.TextEdit.create
              ~range:(Document.SymbolTable.range_to_lsp_range ref.Document.SymbolTable.range)
              ~newText:new_name
          ) matching_refs in
          
          (* Create workspace edit *)
          let changes = [(uri, edits)] in
          let workspace_edit = Lsp.Types.WorkspaceEdit.create
            ~changes
            ()
          in
          
          Ok workspace_edit, [])
  | _ -> Error "Document not open or not parsed", []

(** Handle formatting request *)
let receive_text_document_formatting_request (params : Lsp.Types.DocumentFormattingParams.t) =
  (* Formatting is not implemented yet *)
  Error "Formatting not implemented", []

(** Handle document symbols request *)
let receive_text_document_code_action_request (params : Lsp.Types.CodeActionParams.t) =
  (* Code actions not implemented yet *)
  Ok (Some []), []

let receive_lsp_request_inner : type a. Jsonrpc.Id.t -> a Lsp.Client_request.t -> ('info,'asm) Jasmin.Prog.prog option -> (a,string) result * (Priority.t * RpcProtocolEvent.t) list =
  fun _ req prog ->
    match req with
    | Lsp.Client_request.Initialize params -> receive_initialize_request params
    | Lsp.Client_request.TextDocumentDefinition params -> receive_text_document_definition_request params prog
    | Lsp.Client_request.TextDocumentReferences params -> receive_text_document_references_request params
    | Lsp.Client_request.TextDocumentHover params -> receive_text_document_hover_request params
    | Lsp.Client_request.DocumentSymbol params -> receive_text_document_document_symbol_request params
    | Lsp.Client_request.WorkspaceSymbol params -> receive_workspace_symbol_request params
    | Lsp.Client_request.TextDocumentRename params -> receive_text_document_rename_request params
    (* | Lsp.Client_request.TextDocumentFormatting params -> receive_text_document_formatting_request params *)
    (* | Lsp.Client_request.TextDocumentCodeAction params -> receive_text_document_code_action_request params *)
    | _ -> Io.Logger.log ("Unsupported request\n") ; Error "Unsupported request", []

let receive_lsp_request id req prog =
  match req with
  | Lsp.Client_request.E req ->
    let response, events = receive_lsp_request_inner id req prog in
    (match response with
    | Ok ok_response ->
        let result_json = Lsp.Client_request.yojson_of_result req ok_response in
        let response_json = RpcProtocolEvent.build_rpc_response id result_json in
        (Priority.Next,Send (response_json)):: events
    | Error err_msg ->
        Io.Logger.log (Printf.sprintf "Request error: %s\n" err_msg);
        let error = Jsonrpc.Response.Error.make ~code:InternalError ~message:err_msg () in
        let error_response = RpcProtocolEvent.build_rpc_response_error id error in
        (Priority.Next, Send error_response) :: events)

let rec receive_lsp_notification (notif : Lsp.Client_notification.t) =
  match notif with
  | Lsp.Client_notification.Initialized ->
    Io.Logger.log "Server initialized\n";
    []
  | Lsp.Client_notification.TextDocumentDidOpen params ->
      let uri = params.textDocument.uri in
      let text = params.textDocument.text in
      let version = params.textDocument.version in
      Document.DocumentStore.open_document (!server_state).document_store uri text version;
      (* Send diagnostics after opening *)
      send_diagnostics uri
  | Lsp.Client_notification.TextDocumentDidChange params ->
      let uri = params.textDocument.uri in
      let version = params.textDocument.version in
      (match params.contentChanges with
      | [] -> []
      | changes ->
          (* For full document sync, take the last change *)
          let last_change = List.hd (List.rev changes) in
          let text = last_change.text in
          Document.DocumentStore.update_document (!server_state).document_store uri text version;
          (* Send diagnostics after change *)
          send_diagnostics uri)
  | Lsp.Client_notification.TextDocumentDidClose params ->
      let uri = params.textDocument.uri in
      Document.DocumentStore.close_document (!server_state).document_store uri;
      []
  | _ -> []

(** Send diagnostics for a document *)
and send_diagnostics uri =
  try
    match Document.DocumentStore.get_tree (!server_state).document_store uri with
    | None -> 
        Io.Logger.log "No tree available for diagnostics";
        []
    | Some tree ->
        let source = Document.DocumentStore.get_text (!server_state).document_store uri |> Option.value ~default:"" in
        let diagnostics = collect_diagnostics tree source in
        Io.Logger.log (Format.asprintf "Collected %d diagnostics" (List.length diagnostics));
        let params = Lsp.Types.PublishDiagnosticsParams.create ~uri ~diagnostics () in
        let notification = Lsp.Server_notification.PublishDiagnostics params in
        let json = Lsp.Server_notification.to_jsonrpc notification in
        let packet_json = Jsonrpc.Notification.yojson_of_t json in
        [(Priority.High, Send packet_json)]
  with e ->
    Io.Logger.log (Format.asprintf "Exception in send_diagnostics: %s\n%s" 
      (Printexc.to_string e) 
      (Printexc.get_backtrace ()));
    []

(** Collect diagnostics from syntax tree *)
and collect_diagnostics tree source =
  try
    let root = TreeSitter.tree_root_node tree in
    let errors = ref [] in
    
    let rec visit_node node =
      try
        (* Check if this node is an error node *)
        let node_type_str = TreeSitter.node_type node in
        let is_error = TreeSitter.node_is_error node in
        let is_missing = TreeSitter.node_is_missing node in
        
        if is_error || is_missing then begin
          Io.Logger.log (Format.asprintf "Found error node: type=%s, is_error=%b, is_missing=%b" 
            node_type_str is_error is_missing);
          let range = TreeSitter.node_range node in
          let lsp_range = Document.SymbolTable.range_to_lsp_range range in
          let message = 
            if is_missing then
              Format.asprintf "Missing: %s" node_type_str
            else
              "Syntax error"
          in
          let diagnostic = Lsp.Types.Diagnostic.create 
            ~range:lsp_range 
            ~message:(`String message)
            ~severity:Lsp.Types.DiagnosticSeverity.Error
            ()
          in
          errors := diagnostic :: !errors
        end;
        
        (* Visit all children to find nested errors *)
        let child_count = TreeSitter.node_named_child_count node in
        let rec visit_children i =
          if i < child_count then begin
            try
              match TreeSitter.node_named_child node i with
              | Some child -> visit_node child; visit_children (i + 1)
              | None -> visit_children (i + 1)
            with e ->
              Io.Logger.log (Format.asprintf "Exception visiting child %d: %s" i (Printexc.to_string e));
              visit_children (i + 1)
          end
        in
        visit_children 0
      with e ->
        Io.Logger.log (Format.asprintf "Exception in visit_node: %s" (Printexc.to_string e))
    in
    
    visit_node root;
    List.rev !errors
  with e ->
    Io.Logger.log (Format.asprintf "Exception in collect_diagnostics: %s" (Printexc.to_string e));
    []


(*

let send_lsp_packet (request : Lsp.Types.Packet) : protocol_event =
  match request with
  | Lsp.Types.Request.Request req ->
      let packet = Jsonrpc.Packet.t_of_request req in
      Send packet
  | _ -> Receive None *)
