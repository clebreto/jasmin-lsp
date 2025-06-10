
type t = {
  log_channel : Lwt_io.output_channel;
}

let std_logger = {
  log_channel = Lwt_io.stderr;
}

let log (logger: t) (str: string) =
  let log = Format.asprintf "\n[LOG] : %s\n" str in
  (* Use Lwt_io.write_chars to write the string to the log channel *)
  let u = Lwt.ignore_result (Lwt_io.write_chars logger.log_channel (Lwt_stream.of_string log));
  Lwt_io.flush logger.log_channel in
  ignore u
