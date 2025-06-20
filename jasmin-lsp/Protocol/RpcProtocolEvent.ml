type t =
| Receive of Jsonrpc.Packet.t option
| Send of Yojson.Safe.t

let build_rpc_response (id : Jsonrpc.Id.t) (result : Yojson.Safe.t) =
  let response = Jsonrpc.Response.ok id result in
  let response_json = Jsonrpc.Packet.yojson_of_t (Jsonrpc.Packet.Response response)
  in response_json

let build_rpc_response_error (id : Jsonrpc.Id.t) (error : Jsonrpc.Response.Error.t) =
  let response = Jsonrpc.Response.error id error in
  let response_json = Jsonrpc.Packet.yojson_of_t (Jsonrpc.Packet.Response response)
  in response_json