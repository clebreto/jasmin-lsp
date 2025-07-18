open RpcProtocolEvent



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

let receive_text_document_definition_request (params : Lsp.Types.DefinitionParams.t) (prog:('info,'asm) Jasmin.Prog.prog option) =
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

let receive_lsp_request_inner : type a. Jsonrpc.Id.t -> a Lsp.Client_request.t -> ('info,'asm) Jasmin.Prog.prog option -> (a,string) result * (Priority.t * RpcProtocolEvent.t) list =
  fun _ req prog ->
    match req with
    | Lsp.Client_request.Initialize params -> receive_initialize_request params
    | Lsp.Client_request.TextDocumentDefinition params -> receive_text_document_definition_request params prog
    | _ -> Io.Logger.log ("Unsupported request\n") ; Error "Unsupported request", []

let receive_lsp_request id req prog =
  match req with
  | Lsp.Client_request.E req ->
    let response, events = receive_lsp_request_inner id req prog in
    match response with
    | Ok ok_response ->
        let result_json = Lsp.Client_request.yojson_of_result req ok_response in
        let response_json = RpcProtocolEvent.build_rpc_response id result_json in
        (Priority.Next,Send (response_json)):: events
  | _ -> []

let receive_lsp_notification (notif : Lsp.Client_notification.t) =
  match notif with
  | Lsp.Client_notification.Initialized ->
    Io.Logger.log "Server initialized\n";
    []
  | _ -> []


(*

let send_lsp_packet (request : Lsp.Types.Packet) : protocol_event =
  match request with
  | Lsp.Types.Request.Request req ->
      let packet = Jsonrpc.Packet.t_of_request req in
      Send packet
  | _ -> Receive None *)
