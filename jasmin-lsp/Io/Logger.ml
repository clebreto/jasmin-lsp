let log (str: string) =
  let log = Format.asprintf "\n[LOG] : %s\n" str in
  (* Use synchronous stderr output instead of Lwt #TODO : fix *)
  output_string stderr log;
  flush stderr