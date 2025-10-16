(** Log file configuration *)
let log_file_path = ref (None : string option)
let log_file_channel = ref (None : out_channel option)

(** Initialize file logging *)
let init_file_logging path =
  try
    (* Close existing log file if any *)
    (match !log_file_channel with
    | Some ch -> close_out ch; log_file_channel := None
    | None -> ());
    
    (* Open new log file in append mode *)
    let ch = open_out_gen [Open_creat; Open_append; Open_text] 0o644 path in
    log_file_channel := Some ch;
    log_file_path := Some path;
    
    (* Write startup marker *)
    let timestamp = Unix.time () |> Unix.localtime in
    let startup_msg = Printf.sprintf "\n========== LSP Server Started: %04d-%02d-%02d %02d:%02d:%02d ==========\n"
      (timestamp.tm_year + 1900)
      (timestamp.tm_mon + 1)
      timestamp.tm_mday
      timestamp.tm_hour
      timestamp.tm_min
      timestamp.tm_sec
    in
    output_string ch startup_msg;
    flush ch;
    
    Printf.eprintf "[LOG] : File logging initialized: %s\n" path;
    flush stderr
  with e ->
    Printf.eprintf "[LOG] : Failed to initialize file logging: %s\n" (Printexc.to_string e);
    flush stderr

(** Close file logging *)
let close_file_logging () =
  match !log_file_channel with
  | Some ch ->
      (try
        let timestamp = Unix.time () |> Unix.localtime in
        let shutdown_msg = Printf.sprintf "========== LSP Server Stopped: %04d-%02d-%02d %02d:%02d:%02d ==========\n\n"
          (timestamp.tm_year + 1900)
          (timestamp.tm_mon + 1)
          timestamp.tm_mday
          timestamp.tm_hour
          timestamp.tm_min
          timestamp.tm_sec
        in
        output_string ch shutdown_msg;
        flush ch;
        close_out ch
      with _ -> ());
      log_file_channel := None;
      log_file_path := None
  | None -> ()

(** Log a message to both stderr and file (if configured) *)
let log (str: string) =
  let timestamp = Unix.time () |> Unix.localtime in
  let time_str = Printf.sprintf "%02d:%02d:%02d"
    timestamp.tm_hour
    timestamp.tm_min
    timestamp.tm_sec
  in
  let log_msg = Format.asprintf "\n[LOG %s] : %s\n" time_str str in
  
  (* Always log to stderr *)
  output_string stderr log_msg;
  flush stderr;
  
  (* Also log to file if configured *)
  (match !log_file_channel with
  | Some ch ->
      (try
        output_string ch log_msg;
        flush ch
      with e ->
        Printf.eprintf "[LOG] : Error writing to log file: %s\n" (Printexc.to_string e);
        flush stderr)
  | None -> ())