open Protocol

module type EventHandler = sig
  type event

  val receive_event : unit -> ((Priority.t * event) list, EventError.t) result Lwt.t

  (**
    Event handler function : should return a list of new events to be processed.
    The events should be ordered by priority, with the highest priority first.
  *)
  val handle_event : event -> (Priority.t * event) list Lwt.t
end

module RpcHandler : EventHandler = struct

  type event = RpcProtocolEvent.t

  let receive_event : unit -> ((Priority.t * event) list, EventError.t) result Lwt.t = RpcProtocol.receive_rpc_packet

  let handle_event (event : event) : (Priority.t * event) list Lwt.t =
    match event with
    | RpcProtocolEvent.Receive None -> Lwt.return []
    | RpcProtocolEvent.Receive (Some packet) ->
        let new_events = RpcProtocol.handle_rpc_packet packet in
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

  let rec server_loop (event_queue : EventHeap.t) =
    let next_event =
      try
        Some(EventHeap.find_min event_queue) (* Retrieve the element with the most negative priority *)
      with
      | Invalid_argument _ -> None
    in
    match next_event with
    | None ->
      let%lwt new_events = Handler.receive_event () in
      begin
      match new_events with
      | Error EndOfFile ->
          (* If we didn't receive any new events, we log and exit the server loop, it indicated that input is closed *)
          Logger.log "No events received, input stream may be closed. Exiting server loop.\n";
          Lwt.return_unit
      | Error (ParseError) ->
          (* We received an incorrect input, but the stream doesn't close, we continue waiting for events*)
          server_loop event_queue
      | Ok new_events ->
          (* If we received new events, we add them to the event queue *)
          let event_queue = EventHeap.merge event_queue (EventHeap.of_list new_events) in
          server_loop event_queue
      end
    | Some (_,event) ->
      let event_queue = EventHeap.del_min event_queue in (* We need to delete the first element since priority queue doesn't have a pop method*)
      let%lwt new_events = Handler.handle_event event in
      let event_queue = EventHeap.merge event_queue (EventHeap.of_list new_events) in
      server_loop event_queue
end

module BasicServer = Make(RpcHandler)

let () =
  Logger.log (Format.asprintf "%s language server (Lwt loop) started\n\n" Config.name);
  Lwt_main.run (
    BasicServer.server_loop BasicServer.EventHeap.empty
  )