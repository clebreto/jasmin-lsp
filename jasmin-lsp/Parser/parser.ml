(* Legacy parser module - no longer used after switching to tree-sitter *)
(* Stubbed out to remove Jasmin dependency *)

type tree_kind =
  | FunctionDef
  | TypeDef
  | Annotation
  | ParamDef
  | FunParamDef
  | VarDecl
  | For
  | While
  | If
  | Error

type syntax_tree =
  | Tree of cst
  | Token of unit  (* Was: Jasmin.Parser.token *)

and cst = {
  kind : tree_kind;
  children : syntax_tree list;
}

type parsing_event =
| Open of tree_kind
| Close
| Advance

type parser = {
  tokens : unit list;  (* Was: Jasmin.Parser.token list *)
  pos : int;
  fuel : int;
  events : parsing_event list;
}

(* Stubbed implementations *)
let parser_open parser =
  let mark = List.length parser.events in
  let events = Open Error :: parser.events in
  { parser with events}, mark

let parser_close parser markopened _tree_kind =
  let rec sub events pos =
    match pos with
    | 0 -> (
      match events with
      | [] -> [Close]
      | _t::l -> Close :: l
    )
    | _ ->
      match events with
      | [] -> []
      | t::l ->
        t :: sub l (pos - 1)
  in
  let events = sub parser.events markopened in
  {parser with events}

let advance parser =
  let events = Advance :: parser.events in
  { parser with events; pos = parser.pos + 1; fuel = 256 }

let parse_function _parser = ()

let parse _tokens =
  Tree {kind=Error; children=[]}
