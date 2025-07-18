
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

let flush_out_channel (channel:t) : unit Lwt.t = Lwt_io.flush channel.out_channel

let flush_err_channel (channel:t) : unit Lwt.t = Lwt_io.flush channel.err_channel


let write_string_to_channel (channel : t) (str: string) =
  let %lwt _ = Lwt_io.write_chars channel.out_channel (Lwt_stream.of_string str) in
  flush_out_channel channel
let write_string_to_channel_err (channel : t) (str: string) =
  let %lwt _ = Lwt_io.write_chars channel.err_channel (Lwt_stream.of_string str) in
  flush_err_channel channel

let read_raw_line (channel:t) : string Lwt.t = Lwt_io.read_line channel.in_channel

let read_raw_chars (channel:t) (size:int) : string Lwt.t = Lwt_io.read ~count:size channel.in_channel

let read_file (filename: string) : string =
  let ic = open_in filename in
  let content = really_input_string ic (in_channel_length ic) in
  close_in ic;
  content