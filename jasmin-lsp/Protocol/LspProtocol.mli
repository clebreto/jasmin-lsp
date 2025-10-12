val receive_lsp_request :
  Jsonrpc.Id.t -> Lsp.Client_request.packed -> ('len,'asm) Jasmin.Prog.prog option -> (Priority.t * RpcProtocolEvent.t) list

val receive_lsp_notification :
  Lsp.Client_notification.t -> (Priority.t * RpcProtocolEvent.t) list

val receive_set_master_file_notification :
  Lsp.Types.DocumentUri.t -> (Priority.t * RpcProtocolEvent.t) list