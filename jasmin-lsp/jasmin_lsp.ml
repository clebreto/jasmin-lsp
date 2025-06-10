open Protocol

module type EventHandler = sig
  type event

  val receive_event : Channel.t -> (Priority.t * event) list option Lwt.t

  val handle_event : event -> (Priority.t * event) list Lwt.t
end

module RpcHandler : EventHandler = struct

  type event = RpcProtocolEvent.t

  let receive_event (channel : Channel.t) : (Priority.t * event) list option Lwt.t = RpcProtocol.receive_rpc_packet channel

  let handle_event (event : event) : (Priority.t * event) list Lwt.t =
    match event with
    | RpcProtocolEvent.Receive None -> Lwt.return []
    | RpcProtocolEvent.Receive (Some packet) ->
        let new_events = RpcProtocol.handle_rpc_packet packet in
        Lwt.return new_events
    | RpcProtocolEvent.Send json ->
        let%lwt () =  RpcProtocol.write_json_rpc Channel.std_channel json in
        Lwt.return []

end

module Make (Handler : EventHandler) = struct

  module PE = struct
      type t = Priority.t * Handler.event

    let compare (p1, _) (p2, _) =
      Priority.compare p1 p2
  end

  module EventHeap = Batteries.Heap.Make (PE)

  let rec server_loop (channel : Channel.t) (event_queue : EventHeap.t) =
    let next_event =
      try
        Some(EventHeap.find_min event_queue)
      with
      | Invalid_argument _ -> None
    in
    match next_event with
    | None ->
      let%lwt new_events = Handler.receive_event channel in
      begin
      match new_events with
      | None ->
          (* If we didn't receive any new events, we log and exit the server loop, it indicated that input is closed *)
          Logger.log Logger.std_logger "No events received, input stream may be closed. Exiting server loop.\n";
          Lwt.return_unit
      | Some new_events ->
      (* If we received new events, we need to add them to the event queue *)
        let new_events = EventHeap.of_list new_events in
        server_loop channel new_events
      end
    | Some (_,event) ->
      let event_queue = EventHeap.del_min event_queue in (* We need to delete the first element since priority queue doesn't have a pop method*)
      let%lwt new_events = Handler.handle_event event in
      let event_queue = EventHeap.merge event_queue (EventHeap.of_list new_events) in
      server_loop channel event_queue
end

module BasicServer = Make(RpcHandler)

let () =
  Logger.log Logger.std_logger (Format.asprintf "%s language server (Lwt loop) started\n\n" Config.name);
  Lwt_main.run (
    let channel = Channel.std_channel in
    BasicServer.server_loop channel BasicServer.EventHeap.empty
  )