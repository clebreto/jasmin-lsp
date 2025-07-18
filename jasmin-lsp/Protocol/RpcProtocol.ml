type content_type =
  | VscodeHeader
  | ApplicationJson
  | Unknown of string

type request_headers = {
  content_length : int option;
  content_type : content_type option;
  other_headers : (string * string) list;
}

let empty_headers = {
  content_length = None;
  content_type = None;
  other_headers = [];
}

let parse_content_length (headers : request_headers) (content : string)  =
  let length = int_of_string content in
  { headers with
    content_length = Some length;
  }

let parse_content_type (headers : request_headers) (content : string) =
  let content_type = match content with
  | "application/vscode-jsonrpc; charset=utf-8" -> Some VscodeHeader
  | "application/json" -> Some ApplicationJson
  | _ -> Some (Unknown content)
  in
  { headers with
    content_type;
  }

let parse_nonstandard_header (headers : request_headers) (key : string) (value : string) =
  { headers with
    other_headers = (key, value) :: headers.other_headers;
  }


let read_rpc_header () : (string, EventError.t) result Lwt.t =
  Lwt.catch
    (fun () ->
      (* Read a line from the channel, which is expected to be a header line *)
      (* Note: This assumes that the headers are sent one per line, ending with an empty line *)
      let%lwt line = Io.Channel.read_raw_line Config.channels in
      Lwt.return (Ok line))
    (function
      | exn -> Lwt.return (Error EventError.EndOfFile)
    )

let read_rpc_headers () : (request_headers, EventError.t) result Lwt.t =
  let rec loop acc =
    let%lwt header = read_rpc_header () in
    match header with
    | Ok line when String.trim line = "" -> Lwt.return (Ok acc)
    | Error _ as e -> Lwt.return e
    | Ok line ->
        try
          let split = String.split_on_char ':' line in (*TODO : replace with scanf "%s: %s" when bug on it is found*)
          match split with
            | [key; value] ->
              begin
                let key = String.trim key in
                let value = String.trim value in
                (* Handle the header based on its key *)
                let new_headers = match key with
                | "Content-Length" -> parse_content_length acc value
                | "Content-Type"   -> parse_content_type acc value
                | _                -> parse_nonstandard_header acc key value
                in loop new_headers
              end
            | _ ->
                Io.Logger.log (Format.asprintf "Invalid header format: %s\n" line);
                Lwt.return (Error EventError.ParseError)
        with
        | Scanf.Scan_failure _ ->
            Io.Logger.log (Format.asprintf "Failed scan: %s\n" line);
            Lwt.return (Error EventError.ParseError)
  in
  loop empty_headers

let read_rpc_body (size : int) : (string,EventError.t) result Lwt.t =
    let left = ref size in
    let stream = Lwt_stream.from (fun () ->
        if !left <= 0 then Lwt.return_none
        else
          begin
            let%lwt s = Io.Channel.read_raw_chars Config.channels !left in
            left:=!left - (String.length s);
            Lwt.return (Some s)
          end
        ) in
    let%lwt inputs = Lwt_stream.to_list stream in
    let body = String.concat "" inputs in
    Lwt.return (Ok(body))

let read_raw_rpc_from_channel () : ((int * string),EventError.t) result Lwt.t =
  let%lwt headers = read_rpc_headers () in
  match headers with
  | Error _ as e -> Lwt.return e
  | Ok headers ->
    match headers.content_length with
    | None -> Lwt.return (Error EventError.ParseError)
    | Some size ->
      let%lwt body = read_rpc_body size in
      match body with
      | Error _ as e -> Lwt.return e
      | Ok body ->
        Lwt.return (Ok (size, body))

let read_json_rpc () : (Jsonrpc.Packet.t, EventError.t) result Lwt.t =
  let%lwt content = read_raw_rpc_from_channel () in
  match content with
  | Error _ as e ->
      Lwt.return e
  | Ok (size, body) ->
      try
        let json = Yojson.Safe.from_string body in
        let packet = Jsonrpc.Packet.t_of_yojson json in
        Lwt.return (Ok packet)
      with
      | Yojson.Json_error err ->
          Io.Logger.log (Format.asprintf "Failed to decode JSON-RPC packet: %s" err);
          Lwt.return (Error (EventError.ParseError))
      | _ ->
          Io.Logger.log "Unexpected error while decoding JSON-RPC packet";
          Lwt.return (Error (EventError.ParseError))

let write_json_rpc (json: Yojson.Safe.t) =
  let content  = Yojson.Safe.pretty_to_string ~std:true json in
  let size = String.length content in
  let message = Format.asprintf"Content-Length: %d\r\n\r\n%s" size content in
  Io.Channel.write_string_to_channel Config.channels message

(*=====================================================================================*)

(**
Handlers for receiving each kind of JSON-RPC packet.
These functions should call the appropriate LSP protocol functions see [LspProtocol.ml]
*)
let receive_rpc_request (req : Jsonrpc.Request.t) prog =
  let id = req.id in
  let req = Lsp.Client_request.of_jsonrpc req in
  match req with
  | Error err ->
      Io.Logger.log (Format.asprintf "Failed to decode request: %s\n" err);
      []
  | Ok req -> LspProtocol.receive_lsp_request id req prog

let receive_rpc_notification (notif : Jsonrpc.Notification.t) =
  let lsp_notif = Lsp.Client_notification.of_jsonrpc notif in
  match lsp_notif with
  | Error err ->
      Io.Logger.log (Format.asprintf "Failed to decode notification: %s\n" err);
      []
  | Ok notif -> LspProtocol.receive_lsp_notification notif

(*TODO : Check if this function should raise an error*)
let receive_rpc_response (_ : Jsonrpc.Response.t) = []

let receive_rpc_batch_response (_ : Jsonrpc.Response.t list) = []

let receive_rpc_batch_call (_) = []

let handle_rpc_packet (packet : Jsonrpc.Packet.t) (prog) : (Priority.t * RpcProtocolEvent.t) list =
  match packet with
  | Request req -> receive_rpc_request req prog
  | Notification notif -> receive_rpc_notification notif
  | Response resp -> receive_rpc_response resp
  | Batch_response batch_resp -> receive_rpc_batch_response batch_resp
  | Batch_call batch_call -> receive_rpc_batch_call batch_call

let receive_rpc_packet prog : ((Priority.t * RpcProtocolEvent.t) list, EventError.t) result Lwt.t  =
  let%lwt rpc = read_json_rpc () in
  let result = match rpc with
    | Error e -> Error e
    | Ok packet ->
      Io.Logger.log (Format.asprintf "Received RPC packet: %s" (Yojson.Safe.to_string (Jsonrpc.Packet.yojson_of_t packet)));
      Ok (handle_rpc_packet packet prog)
  in
  Lwt.return result


