
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
  | Token of Jasmin.Parser.token

and cst = {
  kind : tree_kind;
  children : syntax_tree list;
}



(**
Parsing events : track the state of parsing
*)
type parsing_event =
| Open of tree_kind
| Close
| Advance

type parser = {
  tokens : Jasmin.Parser.token list;
  pos : int;
  fuel : int;
  events : parsing_event list;
}

let parser_open parser =
  let mark = List.length parser.events in
  let events = Open Error :: parser.events in
  { parser with events}, mark

let parser_close parser markopened tree_kind =
  let rec sub events pos =
    match pos with
    | 0 -> (
      match events with
      | [] -> [Close]
      | t::l -> Close :: l
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


let parse_function parser = ()


let parse tokens =
  let event_stack = Stack.create in
  let tree_stack = Stack.create in

  while not (Stack.is_empty (event_stack ())) do
      let event = Stack.pop (event_stack ()) in
      match event with
      | Open tree_kind ->
        Stack.push (Tree {kind=tree_kind; children=[]}) (tree_stack ());
      | Close ->
        ()
      | Advance ->
        ()
  done;
  Stack.pop (tree_stack ())