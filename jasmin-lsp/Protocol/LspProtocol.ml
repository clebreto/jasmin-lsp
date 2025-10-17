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

(** Get all files relevant for symbol lookup: master file + its transitive dependencies *)
let get_all_relevant_files uri =
  match ServerState.get_master_file (!server_state) with
  | Some master_uri ->
      (* If a master file is set, start traversal from it *)
      Io.Logger.log (Format.asprintf "Using master file for dependency resolution: %s" 
        (Lsp.Types.DocumentUri.to_string master_uri));
      
      (* Collect all files reachable from the master file *)
      let all_files = collect_required_files_recursive master_uri [] in
      
      (* Make sure the current file is included (it might not be in the dependency tree) *)
      let all_files = if List.mem uri all_files then all_files else uri :: all_files in
      
      Io.Logger.log (Format.asprintf "Total files from master file: %d" (List.length all_files));
      all_files
  | None ->
      (* Fallback: No master file set, use the old behavior *)
      Io.Logger.log "No master file set, using all open files as entry points";
      
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

(** Build a source map from URIs to (source, tree) pairs for constant evaluation *)
let build_source_map uris =
  let source_map = Hashtbl.create (List.length uris) in
  List.iter (fun doc_uri ->
    match Document.DocumentStore.get_tree (!server_state).document_store doc_uri,
          Document.DocumentStore.get_text (!server_state).document_store doc_uri with
    | Some tree, Some source ->
        Hashtbl.add source_map doc_uri (source, tree)
    | _ ->
        (* Try to load from disk *)
        try
          let path = Lsp.Uri.to_path doc_uri in
          if Sys.file_exists path then (
            let ic = open_in path in
            let len = in_channel_length ic in
            let content = really_input_string ic len in
            close_in ic;
            let parser = Document.DocumentStore.get_parser () in
            match TreeSitter.parser_parse_string parser content with
            | Some tree -> Hashtbl.add source_map doc_uri (content, tree)
            | None -> ()
          )
        with _ -> ()
  ) uris;
  source_map

(** Extract symbols with computed constant values from a URI *)
let extract_symbols_with_values uri source tree all_uris =
  (* Extract basic symbols *)
  let symbols = Document.SymbolTable.extract_symbols uri source tree in
  (* Build source map for all related files *)
  let source_map = build_source_map all_uris in
  (* Enhance constants with computed values *)
  Document.SymbolTable.enhance_constants_with_values symbols source_map

(** Find the innermost identifier or variable node at or containing the given point *)
let rec find_identifier_at_point node point =
  let node_type = TreeSitter.node_type node in
  
  (* If this node is an identifier or variable, return it *)
  if node_type = "identifier" || node_type = "variable" then
    Some node
  else
    (* Otherwise, check all children (including unnamed ones) *)
    let child_count = TreeSitter.node_child_count node in
    let rec check_children i best =
      if i >= child_count then best
      else
        match TreeSitter.node_child node i with
        | None -> check_children (i + 1) best
        | Some child ->
            let child_range = TreeSitter.node_range child in
            let start_point = child_range.start_point in
            let end_point = child_range.end_point in
            
            (* Check if point is within this child *)
            let point_in_child = 
              (point.TreeSitter.row > start_point.row || 
               (point.TreeSitter.row = start_point.row && point.TreeSitter.column >= start_point.column)) &&
              (point.TreeSitter.row < end_point.row || 
               (point.TreeSitter.row = end_point.row && point.TreeSitter.column <= end_point.column))
            in
            
            if point_in_child then (
              (* Point is within this child, recursively search it *)
              match find_identifier_at_point child point with
              | Some id -> Some id  (* Found an identifier, return immediately *)
              | None -> check_children (i + 1) best
            ) else
              check_children (i + 1) best
    in
    check_children 0 None

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
  
  (* Helper: Resolve file path using namespace-aware logic from SymbolTable *)
  let resolve_required_file_namespace_aware current_uri node source =
    try
      (* Use the same logic as SymbolTable.extract_requires_from_node *)
      (* Check if there's a 'from' clause with a namespace *)
      let require_node = 
        (* Find the parent require node *)
        let rec find_require_parent n =
          match TreeSitter.node_type n with
          | "require" -> Some n
          | _ -> 
              (match TreeSitter.node_parent n with
              | Some parent -> find_require_parent parent  
              | None -> None)
        in
        find_require_parent node
      in
      
      match require_node with
      | None -> None
      | Some req_node ->
          let namespace_opt = 
            let child_count = TreeSitter.node_named_child_count req_node in
            let rec find_from i =
              if i >= child_count then None
              else
                match TreeSitter.node_named_child req_node i with
                | None -> find_from (i + 1)
                | Some child ->
                    if TreeSitter.node_type child = "from" then
                      (* Extract the namespace identifier from the 'from' node *)
                      match TreeSitter.node_child_by_field_name child "id" with
                      | Some id_node -> Some (TreeSitter.node_text id_node source)
                      | None -> find_from (i + 1)
                    else
                      find_from (i + 1)
            in
            find_from 0
          in
          
          (* Find the filename from the string literal *)
          let filename = TreeSitter.node_text node source in
          (* Remove quotes if present *)
          let filename = 
            if String.length filename >= 2 && 
               String.get filename 0 = '"' && 
               String.get filename (String.length filename - 1) = '"' 
            then String.sub filename 1 (String.length filename - 2)
            else filename
          in
          
          let current_path = Lsp.Uri.to_path current_uri in
          let current_dir = Filename.dirname current_path in
          
          (* If there's a namespace, we need to search for it *)
          let resolved_path = match namespace_opt with
            | Some ns ->
                (* Search for namespace directory in current dir and parent dirs *)
                (* Try lowercase version of namespace (e.g., "Common" -> "common") *)
                let ns_lower = String.lowercase_ascii ns in
                
                (* Try: current_dir/namespace/filename *)
                let try1 = Filename.concat (Filename.concat current_dir ns) filename in
                let try2 = Filename.concat (Filename.concat current_dir ns_lower) filename in
                
                (* Try: parent_dir/namespace/filename (for sibling directories) *)
                let parent_dir = Filename.dirname current_dir in
                let try3 = Filename.concat (Filename.concat parent_dir ns) filename in
                let try4 = Filename.concat (Filename.concat parent_dir ns_lower) filename in
                
                (* Try: grandparent_dir/namespace/filename *)
                let grandparent_dir = Filename.dirname parent_dir in
                let try5 = Filename.concat (Filename.concat grandparent_dir ns) filename in
                let try6 = Filename.concat (Filename.concat grandparent_dir ns_lower) filename in
                
                Io.Logger.log (Format.asprintf "Namespace-aware resolving: from %s require \"%s\"" ns filename);
                Io.Logger.log (Format.asprintf "  Current dir: %s" current_dir);
                
                (* Return first existing path *)
                if Sys.file_exists try1 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try1); Some try1)
                else if Sys.file_exists try2 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try2); Some try2)
                else if Sys.file_exists try3 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try3); Some try3)
                else if Sys.file_exists try4 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try4); Some try4)
                else if Sys.file_exists try5 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try5); Some try5)
                else if Sys.file_exists try6 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try6); Some try6)
                else (Io.Logger.log "  NOT FOUND in any namespace location"; None)
            | None ->
                (* No namespace, resolve relative to current dir *)
                let path = Filename.concat current_dir filename in
                if Sys.file_exists path then (
                  Io.Logger.log (Format.asprintf "Simple require resolved to: %s" path);
                  Some path
                ) else (
                  Io.Logger.log (Format.asprintf "Simple require NOT FOUND: %s" path);
                  None
                )
          in
          
          (match resolved_path with
          | Some path -> Some (Lsp.Uri.of_path path)
          | None -> None)
    with e ->
      Io.Logger.log (Format.asprintf "Error in namespace-aware file resolution: %s" (Printexc.to_string e));
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
      | None -> 
          Io.Logger.log "node_at_point returned None";
          Error "No symbol at position", []
      | Some node ->
          let node_type = TreeSitter.node_type node in
          Io.Logger.log (Format.asprintf "node_at_point returned node of type: %s" node_type);
          
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
            
            match resolve_required_file_namespace_aware uri content_node source with
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
            (* Standard symbol-based goto definition - find identifier node *)
            match find_identifier_at_point node point with
            | None ->
                Io.Logger.log "No identifier found at cursor position";
                Error "No symbol at position", []
            | Some id_node ->
                let symbol_name = TreeSitter.node_text id_node source in
                Io.Logger.log (Format.asprintf "Looking for definition of symbol: %s" symbol_name);
            
                (* First try to find in current file *)
                match Document.SymbolTable.find_definition_at_position symbols symbol_name point with
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
      let tree_available = Document.DocumentStore.get_tree (!server_state).document_store uri in
      let source_available = Document.DocumentStore.get_text (!server_state).document_store uri in
      Io.Logger.log (Format.asprintf "No tree or source available for %s (tree=%b, source=%b)" 
        (Lsp.Types.DocumentUri.to_string uri)
        (Option.is_some tree_available)
        (Option.is_some source_available));
      (* Fallback to old Jasmin AST-based approach *)
      match params.partialResultToken with
      | None -> 
          Io.Logger.log "No partialResultToken provided, cannot use AST fallback";
          Error "No text document provided", []
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
          Io.Logger.log (Format.asprintf "Hover: Building complete source map with %d files" (List.length all_uris));
          
          (* Build complete source map upfront with all files from master file dependency tree *)
          let source_map = build_source_map all_uris in
          Io.Logger.log (Format.asprintf "Hover: Source map built with %d entries" (Hashtbl.length source_map));
          
          let rec search_documents uris =
            match uris with
            | [] -> None
            | doc_uri :: rest ->
                try
                  (* Try to get the document from store or source_map *)
                  let tree_opt, source_opt =
                    match Document.DocumentStore.get_tree (!server_state).document_store doc_uri,
                          Document.DocumentStore.get_text (!server_state).document_store doc_uri with
                    | Some t, Some s -> Some t, Some s
                    | _ ->
                        (* Try to get from source_map (loaded from disk) *)
                        match Hashtbl.find_opt source_map doc_uri with
                        | Some (s, t) -> Some t, Some s
                        | None -> None, None
                  in
                  
                  (* Extract symbols using the pre-built source_map *)
                  (match tree_opt, source_opt with
                  | Some doc_tree, Some doc_source ->
                      (try
                        (* Extract basic symbols *)
                        let doc_symbols = Document.SymbolTable.extract_symbols doc_uri doc_source doc_tree in
                        (* Enhance with constant values using the complete source_map *)
                        let doc_symbols_with_values = Document.SymbolTable.enhance_constants_with_values doc_symbols source_map in
                        
                        (match Document.SymbolTable.find_definition doc_symbols_with_values symbol_name with
                        | Some symbol -> 
                            Io.Logger.log (Format.asprintf "Hover: Found symbol '%s' in %s" 
                              symbol_name (Lsp.Types.DocumentUri.to_string doc_uri));
                            Some symbol
                        | None -> search_documents rest)
                      with e ->
                        Io.Logger.log (Format.asprintf "Error extracting symbols from %s: %s\n%s"
                          (Lsp.Types.DocumentUri.to_string doc_uri)
                          (Printexc.to_string e)
                          (Printexc.get_backtrace ()));
                        search_documents rest)
                  | _ -> 
                      Io.Logger.log (Format.asprintf "Hover: No tree/source for %s" 
                        (Lsp.Types.DocumentUri.to_string doc_uri));
                      search_documents rest)
                with e ->
                  Io.Logger.log (Format.asprintf "Error processing file %s: %s\n%s"
                    (Lsp.Types.DocumentUri.to_string doc_uri)
                    (Printexc.to_string e)
                    (Printexc.get_backtrace ()));
                  search_documents rest
          in
          
          match search_documents all_uris with
          | None -> 
              Io.Logger.log (Format.asprintf "Hover: No definition found for '%s'" symbol_name);
              Ok None, []  (* Return None instead of error for unknown symbols *)
          | Some symbol ->
              (* Format hover content based on symbol kind *)
              let base_markdown = match symbol.kind with
              | Document.SymbolTable.Parameter | Document.SymbolTable.Variable ->
                  (match symbol.detail with
                  | Some type_str -> 
                      Format.asprintf "```jasmin\n%s: %s\n```" symbol.name type_str
                  | None -> 
                      Format.asprintf "```jasmin\n%s: <unknown type>\n```" symbol.name)
              | Document.SymbolTable.Function ->
                  (match symbol.detail with
                  | Some fn_sig -> Format.asprintf "```jasmin\n%s\n```" fn_sig
                  | None -> Format.asprintf "```jasmin\nfn %s\n```" symbol.name)
              | Document.SymbolTable.Type ->
                  Format.asprintf "```jasmin\ntype %s\n```" symbol.name
              | Document.SymbolTable.Constant ->
                  (* Parse detail string to extract type, declared value, and computed value *)
                  (* Format is: "type = declared_value" or "type = declared_value = computed_value" *)
                  (match symbol.detail with
                  | Some detail_str ->
                      (* Split by " = " to get parts *)
                      let parts = Str.split (Str.regexp " = ") detail_str in
                      (match parts with
                      | [type_str; declared_value; computed_value] ->
                          (* Three parts: type, declared value, computed value *)
                          (* Check if declared and computed are the same *)
                          if declared_value = computed_value then
                            (* Don't duplicate if they're the same - show simple value *)
                            Format.asprintf "```jasmin\nparam %s: %s\n```\n\n<details>\n<summary>Value</summary>\n\n`%s`\n</details>" 
                              symbol.name type_str declared_value
                          else
                            (* Different values - show both in expandable section *)
                            Format.asprintf "```jasmin\nparam %s: %s\n```\n\n<details>\n<summary>Value</summary>\n\n**Declared:** `%s`\n\n**Computed:** `%s`\n</details>" 
                              symbol.name type_str declared_value computed_value
                      | [type_str; value] ->
                          (* Two parts: type and value (simple constant with declared value) *)
                          Format.asprintf "```jasmin\nparam %s: %s\n```\n\n<details>\n<summary>Value</summary>\n\n`%s`\n</details>"
                            symbol.name type_str value
                      | [type_str] ->
                          (* Only type, no value *)
                          Format.asprintf "```jasmin\nparam %s: %s\n```" symbol.name type_str
                      | _ ->
                          (* Fallback for unexpected format *)
                          Format.asprintf "```jasmin\nparam %s: %s\n```" symbol.name detail_str)
                  | None -> Format.asprintf "```jasmin\nconst %s\n```" symbol.name)
              in
              
              (* Add documentation if available *)
              let markdown_value = match symbol.documentation with
              | Some doc -> 
                  (* Add a horizontal rule and documentation section *)
                  Format.asprintf "%s\n\n---\n\n%s" base_markdown doc
              | None -> base_markdown
              in
              
              let hover_content = `MarkupContent (Lsp.Types.MarkupContent.create
                ~kind:Lsp.Types.MarkupKind.Markdown
                ~value:markdown_value)
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
      (try
        let symbols = Document.SymbolTable.extract_symbols uri source tree in
        let document_symbols = List.map Document.SymbolTable.symbol_to_document_symbol symbols in
        Ok (Some (`DocumentSymbol document_symbols)), []
      with e ->
        Io.Logger.log (Format.asprintf "Error extracting symbols: %s\n%s"
          (Printexc.to_string e)
          (Printexc.get_backtrace ()));
        (* Return empty symbols list instead of erroring *)
        Ok (Some (`DocumentSymbol [])), [])
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

(** Handle custom jasmin/setMasterFile notification *)
let receive_set_master_file_notification uri =
  Io.Logger.log (Format.asprintf "Setting master file to: %s" 
    (Lsp.Types.DocumentUri.to_string uri));
  ServerState.set_master_file (!server_state) uri;
  []

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
      Io.Logger.log (Format.asprintf "Closing document: %s" 
        (Lsp.Types.DocumentUri.to_string uri));
      
      (* Check if this file is in the master file dependency tree *)
      let in_dependency_tree = 
        match ServerState.get_master_file (!server_state) with
        | Some master_uri ->
            let all_files = collect_required_files_recursive master_uri [] in
            List.mem uri all_files || uri = master_uri
        | None ->
            (* No master file, so files should be removed when closed *)
            false
      in
      
      (* If the file is in the dependency tree, keep it in the document store
         and re-send its diagnostics to ensure they stay visible *)
      if in_dependency_tree then (
        Io.Logger.log (Format.asprintf "File is in dependency tree, keeping in memory and diagnostics: %s" 
          (Lsp.Types.DocumentUri.to_string uri));
        (* Don't close the document - keep it loaded *)
        (* Re-send diagnostics to ensure they remain visible in Problems panel *)
        send_diagnostics_single uri
      ) else (
        Io.Logger.log (Format.asprintf "File not in dependency tree, closing and clearing diagnostics: %s" 
          (Lsp.Types.DocumentUri.to_string uri));
        Document.DocumentStore.close_document (!server_state).document_store uri;
        (* Clear diagnostics for files not in dependency tree *)
        let params = Lsp.Types.PublishDiagnosticsParams.create ~uri ~diagnostics:[] () in
        let notification = Lsp.Server_notification.PublishDiagnostics params in
        let json = Lsp.Server_notification.to_jsonrpc notification in
        let packet_json = Jsonrpc.Notification.yojson_of_t json in
        [(Priority.High, Send packet_json)]
      )
  | Lsp.Client_notification.DidChangeWatchedFiles params ->
      (* Handle external file changes *)
      Io.Logger.log (Format.asprintf "Watched files changed: %d files" 
        (List.length params.changes));
      (* Send diagnostics for all changed files (both open and closed) *)
      let events = List.concat_map (fun (change : Lsp.Types.FileEvent.t) ->
        let uri = change.uri in
        let change_type = match change.type_ with
          | Lsp.Types.FileChangeType.Created -> "Created"
          | Lsp.Types.FileChangeType.Changed -> "Changed"
          | Lsp.Types.FileChangeType.Deleted -> "Deleted"
        in
        Io.Logger.log (Format.asprintf "File %s: %s" 
          change_type (Lsp.Types.DocumentUri.to_string uri));
        
        (* For deleted files, clear diagnostics *)
        (match change.type_ with
        | Lsp.Types.FileChangeType.Deleted ->
          Io.Logger.log (Format.asprintf "Clearing diagnostics for deleted file: %s" 
            (Lsp.Types.DocumentUri.to_string uri));
          let params = Lsp.Types.PublishDiagnosticsParams.create ~uri ~diagnostics:[] () in
          let notification = Lsp.Server_notification.PublishDiagnostics params in
          let json = Lsp.Server_notification.to_jsonrpc notification in
          let packet_json = Jsonrpc.Notification.yojson_of_t json in
          [(Priority.High, Send packet_json)]
        (* For created or changed files, send diagnostics *)
        | Lsp.Types.FileChangeType.Created | Lsp.Types.FileChangeType.Changed ->
          match Document.DocumentStore.get_document (!server_state).document_store uri with
          | Some _ ->
              (* File is open in editor, reload and re-send diagnostics *)
              Io.Logger.log (Format.asprintf "File is open, reloading from disk: %s" 
                (Lsp.Types.DocumentUri.to_string uri));
              (try
                let path = Lsp.Uri.to_path uri in
                if Sys.file_exists path then (
                  let ic = open_in path in
                  let len = in_channel_length ic in
                  let content = really_input_string ic len in
                  close_in ic;
                  (* Update the document store with disk content *)
                  let version = match Document.DocumentStore.get_document (!server_state).document_store uri with
                    | Some doc -> doc.version + 1
                    | None -> 0
                  in
                  Document.DocumentStore.update_document (!server_state).document_store uri content version;
                  send_diagnostics uri
                ) else (
                  Io.Logger.log (Format.asprintf "File does not exist: %s" path);
                  []
                )
              with e ->
                Io.Logger.log (Format.asprintf "Error reloading file: %s" (Printexc.to_string e));
                [])
          | None ->
              (* File is not open, load from disk and send diagnostics *)
              Io.Logger.log (Format.asprintf "File not open, loading from disk for diagnostics: %s" 
                (Lsp.Types.DocumentUri.to_string uri));
              send_diagnostics_for_disk_file uri
        )
      ) params.changes in
      events
  | _ -> []

(** Send diagnostics for a single document *)
and send_diagnostics_single uri =
  try
    match Document.DocumentStore.get_tree (!server_state).document_store uri with
    | None -> 
        Io.Logger.log (Format.asprintf "No tree available for diagnostics: %s" 
          (Lsp.Types.DocumentUri.to_string uri));
        []
    | Some tree ->
        let source = Document.DocumentStore.get_text (!server_state).document_store uri |> Option.value ~default:"" in
        let diagnostics = collect_diagnostics tree source in
        Io.Logger.log (Format.asprintf "Collected %d diagnostics for %s" 
          (List.length diagnostics) (Lsp.Types.DocumentUri.to_string uri));
        let params = Lsp.Types.PublishDiagnosticsParams.create ~uri ~diagnostics () in
        let notification = Lsp.Server_notification.PublishDiagnostics params in
        let json = Lsp.Server_notification.to_jsonrpc notification in
        let packet_json = Jsonrpc.Notification.yojson_of_t json in
        [(Priority.High, Send packet_json)]
  with e ->
    Io.Logger.log (Format.asprintf "Exception in send_diagnostics_single: %s\n%s" 
      (Printexc.to_string e) 
      (Printexc.get_backtrace ()));
    []

(** Send diagnostics for a document and all its dependencies, plus all open buffers *)
and send_diagnostics uri =
  try
    Io.Logger.log (Format.asprintf "Sending diagnostics for %s and its dependencies" 
      (Lsp.Types.DocumentUri.to_string uri));
    
    (* Get all relevant files from dependency tree *)
    let dep_tree_files = get_all_relevant_files uri in
    
    (* Get all open files *)
    let all_open_files = Document.DocumentStore.get_all_uris (!server_state).document_store in
    
    (* Combine: dependency tree files + all open files (remove duplicates) *)
    let files_to_diagnose = List.fold_left (fun acc file_uri ->
      if List.mem file_uri acc then acc else file_uri :: acc
    ) dep_tree_files all_open_files in
    
    (* Filter to only files that are actually open *)
    let open_files = List.filter (fun file_uri ->
      Document.DocumentStore.is_open (!server_state).document_store file_uri
    ) files_to_diagnose in
    
    Io.Logger.log (Format.asprintf "Will send diagnostics for %d open files (%d from dep tree, %d total open)" 
      (List.length open_files) (List.length dep_tree_files) (List.length all_open_files));
    
    (* Send diagnostics for each open file *)
    let events = List.concat_map (fun file_uri ->
      Io.Logger.log (Format.asprintf "  - %s" 
        (Lsp.Types.DocumentUri.to_string file_uri));
      send_diagnostics_single file_uri
    ) open_files in
    
    Io.Logger.log (Format.asprintf "Sent diagnostics for %d files" 
      (List.length open_files));
    events
  with e ->
    Io.Logger.log (Format.asprintf "Exception in send_diagnostics: %s\n%s" 
      (Printexc.to_string e) 
      (Printexc.get_backtrace ()));
    []

(** Send diagnostics for a file loaded from disk (not in document store) *)
and send_diagnostics_for_disk_file uri =
  try
    let path = Lsp.Uri.to_path uri in
    if not (Sys.file_exists path) then (
      Io.Logger.log (Format.asprintf "File does not exist: %s" path);
      []
    ) else (
      Io.Logger.log (Format.asprintf "Loading file from disk: %s" path);
      let ic = open_in path in
      let len = in_channel_length ic in
      let content = really_input_string ic len in
      close_in ic;
      
      (* Parse the file *)
      let parser = Document.DocumentStore.get_parser () in
      match TreeSitter.parser_parse_string parser content with
      | None ->
          Io.Logger.log "Failed to parse file";
          []
      | Some tree ->
          let diagnostics = collect_diagnostics tree content in
          Io.Logger.log (Format.asprintf "Collected %d diagnostics from disk file" (List.length diagnostics));
          let params = Lsp.Types.PublishDiagnosticsParams.create ~uri ~diagnostics () in
          let notification = Lsp.Server_notification.PublishDiagnostics params in
          let json = Lsp.Server_notification.to_jsonrpc notification in
          let packet_json = Jsonrpc.Notification.yojson_of_t json in
          [(Priority.High, Send packet_json)]
    )
  with e ->
    Io.Logger.log (Format.asprintf "Exception in send_diagnostics_for_disk_file: %s\n%s" 
      (Printexc.to_string e) 
      (Printexc.get_backtrace ()));
    []

(** Collect diagnostics from syntax tree *)
and collect_diagnostics tree source =
  try
    let root = TreeSitter.tree_root_node tree in
    let errors = ref [] in
    let nodes_visited = ref 0 in
    
    let rec visit_node node =
      try
        incr nodes_visited;
        (* Check if this node is an error node *)
        let node_type_str = TreeSitter.node_type node in
        let is_error = TreeSitter.node_is_error node in
        let is_missing = TreeSitter.node_is_missing node in
        
        (* Log every node type to debug *)
        if node_type_str = "ERROR" then
          Io.Logger.log (Format.asprintf "Found ERROR node type: type=%s, is_error=%b, is_missing=%b" 
            node_type_str is_error is_missing);
        
        (* Check both is_error function and "ERROR" node type *)
        if is_error || is_missing || node_type_str = "ERROR" then begin
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
        
        (* Visit all children to find nested errors - use ALL children, not just named ones *)
        let child_count = TreeSitter.node_child_count node in
        let rec visit_children i =
          if i < child_count then begin
            try
              match TreeSitter.node_child node i with
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
    Io.Logger.log (Format.asprintf "Visited %d nodes, found %d errors" !nodes_visited (List.length !errors));
    List.rev !errors
  with e ->
    Io.Logger.log (Format.asprintf "Exception in collect_diagnostics: %s" (Printexc.to_string e));
    []

(** Handle custom jasmin/setNamespacePaths notification *)
let receive_set_namespace_paths_notification paths =
  Io.Logger.log (Format.asprintf "Setting namespace paths: %d namespaces" (List.length paths));
  ServerState.set_namespace_paths (!server_state) paths;
  
  (* If a master file is set, load it and its dependencies, then trigger diagnostics *)
  match ServerState.get_master_file (!server_state) with
  | Some master_uri ->
      Io.Logger.log "Master file is set, loading files and triggering diagnostics";
      
      (* Load master file if not already open *)
      let load_file uri =
        if not (Document.DocumentStore.is_open (!server_state).document_store uri) then (
          try
            let path = Lsp.Uri.to_path uri in
            if Sys.file_exists path then (
              Io.Logger.log (Format.asprintf "Loading file: %s" path);
              let ic = open_in path in
              let len = in_channel_length ic in
              let content = really_input_string ic len in
              close_in ic;
              Document.DocumentStore.open_document (!server_state).document_store uri content 0;
              true
            ) else (
              Io.Logger.log (Format.asprintf "File does not exist: %s" path);
              false
            )
          with e ->
            Io.Logger.log (Format.asprintf "Error loading file: %s" (Printexc.to_string e));
            false
        ) else (
          Io.Logger.log (Format.asprintf "File already open: %s" (Lsp.Types.DocumentUri.to_string uri));
          true
        )
      in
      
      (* Load master file *)
      let _ = load_file master_uri in
      
      (* Get all dependencies and load them *)
      let all_files = get_all_relevant_files master_uri in
      Io.Logger.log (Format.asprintf "Found %d files to load" (List.length all_files));
      List.iter (fun uri -> ignore (load_file uri)) all_files;
      
      (* Now send diagnostics *)
      send_diagnostics master_uri
  | None ->
      Io.Logger.log "No master file set, skipping diagnostics";
      []


(*

let send_lsp_packet (request : Lsp.Types.Packet) : protocol_event =
  match request with
  | Lsp.Types.Request.Request req ->
      let packet = Jsonrpc.Packet.t_of_request req in
      Send packet
  | _ -> Receive None *)
