


let name = "jasmin-lsp"
let version = "0.1.0"

let channels = Io.Channel.std_channel

let conf_request_id = max_int

let capabilities : Lsp.Types.ServerCapabilities.t =
  let text_document_sync = `TextDocumentSyncKind Lsp.Types.TextDocumentSyncKind.Incremental in
  Lsp.Types.ServerCapabilities.create
    ~textDocumentSync:text_document_sync
    ()