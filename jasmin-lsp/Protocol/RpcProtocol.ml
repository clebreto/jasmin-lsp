let read_json_rpc (channels: Channel.t) : Jsonrpc.Packet.t option Lwt.t =
  let%lwt content = Channel.read_raw_rpc_from_channel channels in
  match content with
  | None ->
      Lwt.return None
  | Some (_, body) ->
      try
        let json = Yojson.Safe.from_string body in
        let packet = Jsonrpc.Packet.t_of_yojson json in
        Lwt.return (Some packet)
      with
      | Yojson.Json_error err ->
          Logger.log (Logger.std_logger) (Format.asprintf "Failed to decode JSON-RPC packet: %s" err);
          Lwt.return None
      | _ ->
          Logger.log (Logger.std_logger) "Unexpected error while decoding JSON-RPC packet";
          Lwt.return None

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

let receive_rpc_notification (_ : Jsonrpc.Notification.t) = []

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

let receive_rpc_packet (channel : Channel.t) : (Priority.t * RpcProtocolEvent.t) list option Lwt.t  =
  let%lwt rpc = read_json_rpc channel in
  let result = match rpc with
    | None -> None
    | Some packet ->
      Some (handle_rpc_packet packet)
  in
  Lwt.return result


