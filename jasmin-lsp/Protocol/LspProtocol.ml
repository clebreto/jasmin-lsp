open RpcProtocolEvent



let get_initialize_response (params : Lsp.Types.InitializeParams.t) =
  let param_options = params.initializationOptions in
  let _ = match param_options with
  | None -> Logger.log  "Failed to decode initialization options\n"; ()
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

let receive_lsp_request_inner : type a. Jsonrpc.Id.t -> a Lsp.Client_request.t -> (a,string) result * (Priority.t * RpcProtocolEvent.t) list =
  fun _ req ->
    match req with
    | Lsp.Client_request.Initialize params -> receive_initialize_request params
    | _ -> Logger.log ("Unsupported request\n") ; Error "Unsupported request", []

let receive_lsp_request id req =
  match req with
  | Lsp.Client_request.E req ->
    let response, events = receive_lsp_request_inner id req in
    match response with
    | Ok ok_response ->
        let result_json = Lsp.Client_request.yojson_of_result req ok_response in
        let response_json = RpcProtocolEvent.build_rpc_response id result_json in
        (Priority.Next,Send (response_json)):: events
  | _ -> []

let receive_lsp_notification (notif : Lsp.Client_notification.t) =
  match notif with
  | Lsp.Client_notification.Initialized ->
    Logger.log "Server initialized\n";
    []
  | _ -> []


(*

let send_lsp_packet (request : Lsp.Types.Packet) : protocol_event =
  match request with
  | Lsp.Types.Request.Request req ->
      let packet = Jsonrpc.Packet.t_of_request req in
      Send packet
  | _ -> Receive None *)
