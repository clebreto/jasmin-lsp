
let read_json_rpc (channels: Channel.t) : (Jsonrpc.Packet.t, EventError.t) result Lwt.t =
  let%lwt content = Channel.read_raw_rpc_from_channel channels in
  match content with
  | Error _ as e ->
      Lwt.return e
  | Ok (size, body) ->
      try
        Logger.log (Logger.std_logger) (Format.asprintf "Decoding JSON-RPC packet : %d %s" size body);
        let json = Yojson.Safe.from_string body in
        let packet = Jsonrpc.Packet.t_of_yojson json in
        Lwt.return (Ok packet)
      with
      | Yojson.Json_error err ->
          Logger.log (Logger.std_logger) (Format.asprintf "Failed to decode JSON-RPC packet: %s" err);
          Lwt.return (Error (EventError.ParseError))
      | _ ->
          Logger.log (Logger.std_logger) "Unexpected error while decoding JSON-RPC packet";
          Lwt.return (Error (EventError.ParseError))

let write_json_rpc (channels: Channel.t) (json: Yojson.Safe.t) =
  let content  = Yojson.Safe.pretty_to_string ~std:true json in
  let size = String.length content in
  let message = Format.asprintf"Content-Length: %d\r\n\r\n%s" size content in
  Channel.write_string_to_channel channels message

(*=====================================================================================*)

(**
Handlers for receiving each kind of JSON-RPC packet.
These functions should call the appropriate LSP protocol functions see [LspProtocol.ml]
*)
let receive_rpc_request (req : Jsonrpc.Request.t)  =
  let id = req.id in
  let req = Lsp.Client_request.of_jsonrpc req in
  match req with
  | Error err ->
      Logger.log (Logger.std_logger) (Format.asprintf "Failed to decode request: %s\n" err);
      []
  | Ok req -> LspProtocol.receive_lsp_request id req

let receive_rpc_notification (notif : Jsonrpc.Notification.t) =
  let lsp_notif = Lsp.Client_notification.of_jsonrpc notif in
  match lsp_notif with
  | Error err ->
      Logger.log (Logger.std_logger) (Format.asprintf "Failed to decode notification: %s\n" err);
      []
  | Ok notif -> LspProtocol.receive_lsp_notification notif

(*TODO : Check if this function should raise an error*)
let receive_rpc_response (_ : Jsonrpc.Response.t) = []

let receive_rpc_batch_response (_ : Jsonrpc.Response.t list) = []

let receive_rpc_batch_call (_) = []

let handle_rpc_packet (packet : Jsonrpc.Packet.t) : (Priority.t * RpcProtocolEvent.t) list =
  match packet with
  | Request req -> receive_rpc_request req
  | Notification notif -> receive_rpc_notification notif
  | Response resp -> receive_rpc_response resp
  | Batch_response batch_resp -> receive_rpc_batch_response batch_resp
  | Batch_call batch_call -> receive_rpc_batch_call batch_call

let receive_rpc_packet (channel : Channel.t) : ((Priority.t * RpcProtocolEvent.t) list, EventError.t) result Lwt.t  =
  let%lwt rpc = read_json_rpc channel in
  let result = match rpc with
    | Error e -> Error e
    | Ok packet -> Ok (handle_rpc_packet packet)
  in
  Lwt.return result


