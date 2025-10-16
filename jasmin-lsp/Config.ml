


open Ppx_yojson_conv_lib.Yojson_conv.Primitives

let name = "jasmin-lsp"
let version = "0.1.0"

let channels = Io.Channel.std_channel

let conf_request_id = max_int

type config = {
  jasmin_root : string;
  arch : string;
}[@@deriving yojson]

let config_value = ref None

let set_configuration (conf_path: string) =
  let conf_str = Io.Channel.read_file conf_path in
  try
    let config = config_of_yojson (Yojson.Safe.from_string conf_str) in
    config_value := Some config;
    Io.Logger.log (Format.asprintf "Configuration set: %s\n" conf_path)
  with
  |  _ ->
      Io.Logger.log (Format.asprintf "Failed to parse configuration\n");
      exit 1



let capabilities: Lsp.Types.ServerCapabilities.t =
  let open Lsp.Types in
  let jazz_pattern = FileOperationPattern.{
    glob = "**/*.jazz";
    matches = None;
    options = None;
  }
  in
  let jinc_pattern = FileOperationPattern.{
    glob = "**/*.jinc";
    matches = None;
    options = None;
  }
  in
  let jazz_filter = FileOperationFilter.{
    scheme = None;
    pattern = jazz_pattern;
  }
  in
  let jinc_filter = FileOperationFilter.{
    scheme = None;
    pattern = jinc_pattern;
  }
  in
  let filters = [jazz_filter; jinc_filter] in
  let fileOperationRegistrationOptions = FileOperationRegistrationOptions.{
    filters;
  }
  in
  let didCreate = fileOperationRegistrationOptions in
  let willCreate = fileOperationRegistrationOptions in
  let didRename = fileOperationRegistrationOptions in
  let willRename = fileOperationRegistrationOptions in
  let didDelete = fileOperationRegistrationOptions in
  let willDelete = fileOperationRegistrationOptions in
  let fileOperations = (FileOperationOptions.create
    ~didCreate ~willCreate ~didRename ~willRename ~didDelete ~willDelete ())
  in
  let textDocumentSync = `TextDocumentSyncOptions (TextDocumentSyncOptions.create
    ~openClose:true  (* This is crucial for didOpen/didClose notifications *)
    ~change:(TextDocumentSyncKind.Full)
    ()) in
  let hoverProvider = `Bool true in
  let definitionProvider = `Bool true in
  let referencesProvider = `Bool true in
  let documentSymbolProvider = `Bool true in
  let workspaceSymbolProvider = `Bool true in
  let renameProvider = `Bool true in
  let documentFormattingProvider = `Bool false in (* Not implemented yet *)
  let codeActionProvider = `Bool false in (* Not implemented yet *)
  let workspace = ServerCapabilities.create_workspace ~fileOperations () in
  Lsp.Types.ServerCapabilities.create
    ~textDocumentSync 
    ~hoverProvider 
    ~definitionProvider 
    ~referencesProvider
    ~documentSymbolProvider
    ~workspaceSymbolProvider
    ~renameProvider
    ~documentFormattingProvider
    ~codeActionProvider
    ~workspace ()
