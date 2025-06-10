

(**
Channel level module : read and write raw inputs to defined channels. These functions serves as abstraction for console I/O operations.
*)

type t = {
  in_channel : Lwt_io.input_channel;
  out_channel : Lwt_io.output_channel;
  err_channel : Lwt_io.output_channel;
}

let std_channel : t = {
  in_channel = Lwt_io.stdin;
  out_channel = Lwt_io.stdout;
  err_channel = Lwt_io.stderr;
}

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

let write_string_to_channel (channel : t) (str: string) =
  Lwt_io.write_chars channel.out_channel (Lwt_stream.of_string str)

let write_string_to_channel_err (channel : t) (str: string) =
  Lwt_io.write_chars channel.err_channel (Lwt_stream.of_string str)


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


let read_header (channel : t) : (string, EventError.t) result Lwt.t = 
  Lwt.catch
    (fun () ->
      let%lwt line = Lwt_io.read_line channel.in_channel in
      Lwt.return (Ok line))
    (function
      | exn -> Lwt.return (Error EventError.EndOfFile)
    )

let read_rpc_headers (channel : t) : (request_headers, EventError.t) result Lwt.t =
  let rec loop acc =
    match%lwt read_header channel with
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
                Logger.log (Logger.std_logger) (Format.asprintf "Invalid header format: %s\n" line);
                Lwt.return (Error EventError.ParseError)
        with
        | Scanf.Scan_failure _ ->
            Logger.log (Logger.std_logger) (Format.asprintf "Failed scan: %s\n" line);
            Lwt.return (Error EventError.ParseError)
  in
  loop empty_headers

let read_rpc_body (channel : t) (size : int) : (string,EventError.t)result Lwt.t =
  Lwt.catch
    (fun () ->
      let%lwt body = Lwt_io.read ~count:size channel.in_channel in
      Lwt.return (Ok body))
    (fun exn ->Lwt.return (Error EventError.EndOfFile))

let read_raw_rpc_from_channel (channel : t) : ((int * string),EventError.t) result Lwt.t =
  let%lwt headers = read_rpc_headers channel in
  match headers with
  | Error _ as e -> Lwt.return e
  | Ok headers ->
    match headers.content_length with
    | None -> Lwt.return (Error EventError.ParseError)
    | Some size ->
      let%lwt body = read_rpc_body channel size in
      match body with
      | Error _ as e -> Lwt.return e
      | Ok body -> Lwt.return (Ok (size, body))

