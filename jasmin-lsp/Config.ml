


let name = "jasmin-lsp"
let version = "0.1.0"

let channels = Io.Channel.std_channel

let conf_request_id = max_int


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
  let completionProvider = CompletionOptions.create () in
  let hoverProvider = `Bool false in
  let definitionProvider = `Bool true in
  let workspace = ServerCapabilities.create_workspace ~fileOperations () in
  Lsp.Types.ServerCapabilities.create
    ~textDocumentSync ~completionProvider ~hoverProvider ~definitionProvider ~workspace ()
