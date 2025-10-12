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
  try
    let id = req.id in
    let req = Lsp.Client_request.of_jsonrpc req in
    match req with
    | Error err ->
        Io.Logger.log (Format.asprintf "Failed to decode request: %s\n" err);
        []
    | Ok req -> LspProtocol.receive_lsp_request id req prog
  with e ->
    Io.Logger.log (Format.asprintf "Exception in receive_rpc_request: %s\n%s" 
      (Printexc.to_string e)
      (Printexc.get_backtrace ()));
    []

let receive_rpc_notification (notif : Jsonrpc.Notification.t) =
  try
    (* Check for custom jasmin-lsp notifications first *)
    let method_name = notif.method_ in
    
    (* Handle custom jasmin/setMasterFile notification *)
    if method_name = "jasmin/setMasterFile" then (
      Io.Logger.log "Received jasmin/setMasterFile notification";
      match notif.params with
      | Some params ->
          (try
            (* Parse the URI from the params *)
            let uri_str = match params with
            | `Assoc fields ->
                (match List.assoc_opt "uri" fields with
                | Some (`String s) -> Some s
                | _ -> None)
            | _ -> None
            in
            match uri_str with
            | Some uri_str ->
                let uri = Lsp.Types.DocumentUri.of_string uri_str in
                LspProtocol.receive_set_master_file_notification uri
            | None ->
                Io.Logger.log "Failed to extract URI from jasmin/setMasterFile params";
                []
          with e ->
            Io.Logger.log (Format.asprintf "Error processing jasmin/setMasterFile: %s" 
              (Printexc.to_string e));
            [])
      | None ->
          Io.Logger.log "jasmin/setMasterFile notification missing params";
          []
    ) else (
      (* Standard LSP notification *)
      let lsp_notif = Lsp.Client_notification.of_jsonrpc notif in
      match lsp_notif with
      | Error err ->
          Io.Logger.log (Format.asprintf "Failed to decode notification: %s\n" err);
          []
      | Ok notif -> LspProtocol.receive_lsp_notification notif
    )
  with e ->
    Io.Logger.log (Format.asprintf "Exception in receive_rpc_notification: %s\n%s" 
      (Printexc.to_string e)
      (Printexc.get_backtrace ()));
    []

(*TODO : Check if this function should raise an error*)
let receive_rpc_response (resp : Jsonrpc.Response.t) = 
  try
    (* Check if this is a response to our workspace/configuration request *)
    match resp.id with
    | `Int id when id = Config.conf_request_id ->
        Io.Logger.log "Received workspace/configuration response";
        (* Try to parse the configuration from the response *)
        (try
          let result_json = match resp with
          | { result = Ok json; _ } -> Some json
          | _ -> None
          in
          match result_json with
          | Some result ->
              (* The result is an array with one element (our single ConfigurationItem) *)
              let config_array = Yojson.Safe.Util.to_list result in
              (match config_array with
              | [config_obj] ->
                  (* Extract jasmin-root field if present *)
                  (try
                    let jasmin_root = Yojson.Safe.Util.member "jasmin-root" config_obj in
                    let root_path = Yojson.Safe.Util.to_string jasmin_root in
                    Io.Logger.log (Format.asprintf "Found jasmin-root in configuration: %s" root_path);
                    (* Convert to URI and set as master file *)
                    let uri = Lsp.Uri.of_path root_path in
                    LspProtocol.receive_set_master_file_notification uri
                  with _ ->
                    Io.Logger.log "No jasmin-root found in configuration or failed to parse";
                    [])
              | _ ->
                  Io.Logger.log "Unexpected configuration response format";
                  [])
          | None ->
              Io.Logger.log "Configuration response has no result or is an error";
              []
        with e ->
          Io.Logger.log (Format.asprintf "Failed to parse configuration response: %s" 
            (Printexc.to_string e));
          [])
    | _ -> []
  with e ->
    Io.Logger.log (Format.asprintf "Exception in receive_rpc_response: %s" 
      (Printexc.to_string e));
    []

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


