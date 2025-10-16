open Protocol

module type EventHandler = sig
  type event

  val receive_event : ('len,'asm) Jasmin.Prog.prog option -> ((Priority.t * event) list, EventError.t) result Lwt.t

  (**
    Event handler function : should return a list of new events to be processed.
    The events should be ordered by priority, with the highest priority first.
  *)
  val handle_event : event -> ('len,'asm) Jasmin.Prog.prog option -> (Priority.t * event) list Lwt.t
end

module RpcHandler : EventHandler = struct

  type event = RpcProtocolEvent.t

  let receive_event : ('len,'asm) Jasmin.Prog.prog option -> ((Priority.t * event) list, EventError.t) result Lwt.t = RpcProtocol.receive_rpc_packet

  let handle_event (event : event) (prog: ('len,'asm) Jasmin.Prog.prog option) : (Priority.t * event) list Lwt.t =
    match event with
    | RpcProtocolEvent.Receive None -> Lwt.return []
    | RpcProtocolEvent.Receive (Some packet) ->
        let new_events = RpcProtocol.handle_rpc_packet packet prog in
        Lwt.return new_events
    | RpcProtocolEvent.Send json ->
        let%lwt () =  RpcProtocol.write_json_rpc json in
        Lwt.return []

end

module Make (Handler : EventHandler) = struct

  module PE = struct
      type t = Priority.t * Handler.event

    let compare (p1, _) (p2, _) =
      Priority.compare p1 p2
  end

  module EventHeap = Batteries.Heap.Make (PE)

  let rec server_loop (event_queue : EventHeap.t) (prog : ('len,'asm) Jasmin.Prog.prog option) =
    let next_event =
      try
        Some(EventHeap.find_min event_queue) (* Retrieve the element with the most negative priority *)
      with
      | Invalid_argument _ -> None
    in
    match next_event with
    | None ->
      let%lwt new_events = Handler.receive_event prog in
      begin
      match new_events with
      | Error EndOfFile ->
          (* If we didn't receive any new events, we log and exit the server loop, it indicated that input is closed *)
          Io.Logger.log "No events received, input stream may be closed. Exiting server loop.\n";
          Lwt.return_unit
      | Error (ParseError) ->
          (* We received an incorrect input, but the stream doesn't close, we continue waiting for events*)
          server_loop event_queue prog
      | Ok new_events ->
          (* If we received new events, we add them to the event queue *)
          let event_queue = EventHeap.merge event_queue (EventHeap.of_list new_events) in
          server_loop event_queue prog
      end
    | Some (_,event) ->
      let event_queue = EventHeap.del_min event_queue in (* We need to delete the first element since priority queue doesn't have a pop method*)
      let%lwt new_events = Handler.handle_event event prog in
      let event_queue = EventHeap.merge event_queue (EventHeap.of_list new_events) in
      server_loop event_queue prog
end

module BasicServer = Make(RpcHandler)

let () =
  (* Initialize file logging *)
  let log_dir = 
    try
      let home = Sys.getenv "HOME" in
      Filename.concat home ".jasmin-lsp"
    with Not_found ->
      "/tmp/jasmin-lsp"
  in
  (* Create log directory if it doesn't exist *)
  (try
    if not (Sys.file_exists log_dir) then
      Unix.mkdir log_dir 0o755
  with _ -> ());
  
  let timestamp = Unix.time () |> Unix.gmtime in
  let log_filename = Printf.sprintf "jasmin-lsp-%04d%02d%02d-%02d%02d%02d.log"
    (timestamp.tm_year + 1900)
    (timestamp.tm_mon + 1)
    timestamp.tm_mday
    timestamp.tm_hour
    timestamp.tm_min
    timestamp.tm_sec
  in
  let log_path = Filename.concat log_dir log_filename in
  Io.Logger.init_file_logging log_path;
  
  (* Set up cleanup handler to close log file on exit *)
  at_exit (fun () ->
    Io.Logger.close_file_logging ()
  );
  
  Io.Logger.log (Format.asprintf "%s language server (Lwt loop) started" Config.name);
  Io.Logger.log (Format.asprintf "Log file: %s" log_path);
  
  Lwt_main.run (
    BasicServer.server_loop BasicServer.EventHeap.empty None
  )