
type t = {
  log_channel : Lwt_io.output_channel;
}

let std_logger = {
  log_channel = Lwt_io.stderr;
}

let log (logger: t) (str: string) =
  ignore(Lwt_io.write_chars logger.log_channel (Lwt_stream.of_string str))