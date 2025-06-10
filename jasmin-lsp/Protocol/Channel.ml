
open Batteries

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

let write_string_to_channel (channel : t) (str: string) =
  Lwt_io.write_chars channel.out_channel (Lwt_stream.of_string str)

let write_string_to_channel_err (channel : t) (str: string) =
  Lwt_io.write_chars channel.err_channel (Lwt_stream.of_string str)


let read_rpc_header (channel : t) : string option Lwt.t = 
  Lwt.catch
  (fun () ->
    let%lwt header = Lwt_io.read_line channel.in_channel in
    Lwt.return (Some header))
  (fun exn ->
    Lwt.return None)

let read_rpc_body (channel : t) (size : int) : string option Lwt.t =
  Lwt.catch
    (fun () ->
      let%lwt body = Lwt_io.read ~count:size channel.in_channel in
      Lwt.return (Some body))
    (fun exn ->Lwt.return_none)


let read_raw_rpc_from_channel (channel : t) : (int * string) option Lwt.t =
  try
    let header = read_rpc_header channel in
    let%lwt header = header in
    match header with
    | None ->
        Lwt.return_none
    | Some header ->
    let size = Scanf.sscanf header "Content-Length: %d" (fun len -> len) in
    let%lwt body = read_rpc_body channel size in
    match body with
    | None ->
        Lwt.return_none
    | Some body ->
        Lwt.return (Some (size, body))
  with
  | Scanf.Scan_failure _ ->
      Lwt.return_none
