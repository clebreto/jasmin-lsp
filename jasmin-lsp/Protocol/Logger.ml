
let log (str: string) =
  let log = Format.asprintf "\n[LOG] : %s\n" str in
  (* Use Lwt_io.write_chars to write the string to the log channel *)
  let u = Lwt.ignore_result (Io.Channel.write_string_to_channel_err Config.channels log);
  Io.Channel.flush_err_channel Config.channels in
  ignore u
