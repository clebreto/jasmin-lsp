(** SemanticTokens - Extract semantic tokens for syntax highlighting *)

(** LSP Semantic Token Types *)
type token_type =
  | Namespace
  | Type
  | Class
  | Enum
  | Interface
  | Struct
  | TypeParameter
  | Parameter
  | Variable
  | Property
  | EnumMember
  | Event
  | Function
  | Method
  | Macro
  | Keyword
  | Modifier
  | Comment
  | String
  | Number
  | Regexp
  | Operator
  | Decorator

(** LSP Semantic Token Modifiers *)
type token_modifier =
  | Declaration
  | Definition
  | Readonly
  | Static
  | Deprecated
  | Abstract
  | Async
  | Modification
  | Documentation
  | DefaultLibrary

(** Token information for a single token *)
type token = {
  line: int;
  start_char: int;
  length: int;
  token_type: token_type;
  token_modifiers: token_modifier list;
}

(** Get list of all token type strings for legend *)
val token_types_legend : string list

(** Get list of all token modifier strings for legend *)
val token_modifiers_legend : string list

(** Extract all semantic tokens from a document 
    @param source The source code text
    @param tree The tree-sitter parse tree
    @return List of tokens sorted by position
*)
val extract_semantic_tokens : string -> TreeSitter.tree -> token list

(** Encode tokens into LSP semantic tokens data format
    
    The data is a flat array of integers in groups of 5:
    [deltaLine, deltaStartChar, length, tokenType, tokenModifiers, ...]
    
    @param tokens List of tokens to encode
    @return Flat list of integers for LSP response
*)
val encode_tokens : token list -> int list
