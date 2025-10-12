(** Symbol Table - Analyzes tree-sitter syntax trees for symbols *)

(** Symbol kinds *)
type symbol_kind =
  | Function
  | Variable
  | Parameter
  | Type
  | Constant

(** Symbol information *)
type symbol = {
  name: string;
  kind: symbol_kind;
  range: TreeSitter.range;
  definition_range: TreeSitter.range;
  uri: Lsp.Types.DocumentUri.t;
  detail: string option; (* Type information or signature *)
}

(** Reference information *)
type reference = {
  symbol_name: string;
  range: TreeSitter.range;
  uri: Lsp.Types.DocumentUri.t;
}

(** Extract all symbols from a syntax tree *)
val extract_symbols : Lsp.Types.DocumentUri.t -> string -> TreeSitter.tree -> symbol list

(** Enhance constant symbols with computed values 
    @param symbols List of symbols to enhance
    @param source_map Hashtable mapping URIs to (source, tree) pairs
    @return Enhanced symbol list with computed constant values *)
val enhance_constants_with_values : symbol list -> (Lsp.Types.DocumentUri.t, string * TreeSitter.tree) Hashtbl.t -> symbol list

(** Extract required file URIs from a syntax tree *)
val extract_required_files : Lsp.Types.DocumentUri.t -> string -> TreeSitter.tree -> Lsp.Types.DocumentUri.t list

(** Extract all references from a syntax tree *)
val extract_references : Lsp.Types.DocumentUri.t -> string -> TreeSitter.tree -> reference list

(** Find the symbol at a given position *)
val find_symbol_at_position : symbol list -> TreeSitter.point -> symbol option

(** Find all references to a symbol *)
val find_references_to : reference list -> string -> reference list

(** Find the definition of a symbol by name *)
val find_definition : symbol list -> string -> symbol option

(** Convert symbol to LSP SymbolInformation *)
val symbol_to_lsp : symbol -> Lsp.Types.SymbolInformation.t

(** Convert symbol to LSP DocumentSymbol *)
val symbol_to_document_symbol : symbol -> Lsp.Types.DocumentSymbol.t

(** Convert symbol kind to LSP SymbolKind *)
val symbol_kind_to_lsp : symbol_kind -> Lsp.Types.SymbolKind.t

(** Convert TreeSitter point to LSP Position *)
val point_to_position : TreeSitter.point -> Lsp.Types.Position.t

(** Convert TreeSitter range to LSP Range *)
val range_to_lsp_range : TreeSitter.range -> Lsp.Types.Range.t
