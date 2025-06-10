type t =
| Receive of Jsonrpc.Packet.t option
| Send of Yojson.Safe.t