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

(** Convert token type to LSP index *)
let token_type_to_index = function
  | Namespace -> 0
  | Type -> 1
  | Class -> 2
  | Enum -> 3
  | Interface -> 4
  | Struct -> 5
  | TypeParameter -> 6
  | Parameter -> 7
  | Variable -> 8
  | Property -> 9
  | EnumMember -> 10
  | Event -> 11
  | Function -> 12
  | Method -> 13
  | Macro -> 14
  | Keyword -> 15
  | Modifier -> 16
  | Comment -> 17
  | String -> 18
  | Number -> 19
  | Regexp -> 20
  | Operator -> 21
  | Decorator -> 22

(** Convert token type to LSP string *)
let token_type_to_string = function
  | Namespace -> "namespace"
  | Type -> "type"
  | Class -> "class"
  | Enum -> "enum"
  | Interface -> "interface"
  | Struct -> "struct"
  | TypeParameter -> "typeParameter"
  | Parameter -> "parameter"
  | Variable -> "variable"
  | Property -> "property"
  | EnumMember -> "enumMember"
  | Event -> "event"
  | Function -> "function"
  | Method -> "method"
  | Macro -> "macro"
  | Keyword -> "keyword"
  | Modifier -> "modifier"
  | Comment -> "comment"
  | String -> "string"
  | Number -> "number"
  | Regexp -> "regexp"
  | Operator -> "operator"
  | Decorator -> "decorator"

(** Get list of all token type strings for legend *)
let token_types_legend = [
  "namespace"; "type"; "class"; "enum"; "interface"; "struct";
  "typeParameter"; "parameter"; "variable"; "property"; "enumMember";
  "event"; "function"; "method"; "macro"; "keyword"; "modifier";
  "comment"; "string"; "number"; "regexp"; "operator"; "decorator"
]

(** Convert token modifier to bit mask *)
let token_modifier_to_mask = function
  | Declaration -> 1 lsl 0
  | Definition -> 1 lsl 1
  | Readonly -> 1 lsl 2
  | Static -> 1 lsl 3
  | Deprecated -> 1 lsl 4
  | Abstract -> 1 lsl 5
  | Async -> 1 lsl 6
  | Modification -> 1 lsl 7
  | Documentation -> 1 lsl 8
  | DefaultLibrary -> 1 lsl 9

(** Convert token modifier to LSP string *)
let token_modifier_to_string = function
  | Declaration -> "declaration"
  | Definition -> "definition"
  | Readonly -> "readonly"
  | Static -> "static"
  | Deprecated -> "deprecated"
  | Abstract -> "abstract"
  | Async -> "async"
  | Modification -> "modification"
  | Documentation -> "documentation"
  | DefaultLibrary -> "defaultLibrary"

(** Get list of all token modifier strings for legend *)
let token_modifiers_legend = [
  "declaration"; "definition"; "readonly"; "static"; "deprecated";
  "abstract"; "async"; "modification"; "documentation"; "defaultLibrary"
]

(** Calculate modifiers bitmask from list *)
let calculate_modifiers_mask modifiers =
  List.fold_left (fun acc m -> acc lor (token_modifier_to_mask m)) 0 modifiers

(** Check if node type is a Jasmin keyword *)
let is_keyword node_type =
  match node_type with
  | "fn" | "inline" | "export" | "return" | "if" | "else" | "while" | "for"
  | "require" | "from" | "param" | "global" | "reg" | "stack" | "const"
  | "to" | "downto" -> true
  | _ -> false

(** Check if node type is a Jasmin type *)
let is_type_keyword node_type =
  match node_type with
  | "u8" | "u16" | "u32" | "u64" | "u128" | "u256"
  | "i8" | "i16" | "i32" | "i64" | "i128" | "i256"
  | "bool" | "int" -> true
  | _ -> false

(** Check if node type is a storage class *)
let is_storage_class node_type =
  match node_type with
  | "reg" | "stack" | "inline" -> true
  | _ -> false

(** Extract semantic tokens from a syntax tree *)
let rec extract_tokens_from_node source node acc =
  let node_type = TreeSitter.node_type node in
  let range = TreeSitter.node_range node in
  let start_point = range.TreeSitter.start_point in
  let end_point = range.TreeSitter.end_point in
  let text = TreeSitter.node_text node source in
  
  (* Calculate token length *)
  let length = 
    if start_point.row = end_point.row then
      end_point.column - start_point.column
    else
      String.length text
  in
  
  (* Determine token type and add to accumulator *)
  let acc = match node_type with
    (* Comments *)
    | "comment" ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = Comment;
          token_modifiers = [];
        } in
        token :: acc
    
    (* Keywords *)
    | "fn" | "inline" | "export" | "return" | "if" | "else" | "while" | "for"
    | "require" | "from" | "param" | "global" | "const" | "to" | "downto" ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = Keyword;
          token_modifiers = [];
        } in
        token :: acc
    
    (* Storage class keywords (reg, stack, inline) *)
    | "reg" | "stack" ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = Keyword;
          token_modifiers = [];
        } in
        token :: acc
    
    (* Type keywords *)
    | "type" when is_type_keyword text ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = Type;
          token_modifiers = [];
        } in
        token :: acc
    
    (* Function declarations *)
    | "function_definition" ->
        (match TreeSitter.node_child_by_field_name node "name" with
        | Some name_node ->
            let name_range = TreeSitter.node_range name_node in
            let name_start = name_range.TreeSitter.start_point in
            let name_text = TreeSitter.node_text name_node source in
            let token = {
              line = name_start.row;
              start_char = name_start.column;
              length = String.length name_text;
              token_type = Function;
              token_modifiers = [Declaration; Definition];
            } in
            token :: acc
        | None -> acc)
    
    (* Function calls *)
    | "call" ->
        (match TreeSitter.node_child_by_field_name node "function" with
        | Some func_node ->
            let func_range = TreeSitter.node_range func_node in
            let func_start = func_range.TreeSitter.start_point in
            let func_text = TreeSitter.node_text func_node source in
            let token = {
              line = func_start.row;
              start_char = func_start.column;
              length = String.length func_text;
              token_type = Function;
              token_modifiers = [];
            } in
            token :: acc
        | None -> acc)
    
    (* Parameter declarations *)
    | "parameter" ->
        (match TreeSitter.node_child_by_field_name node "name" with
        | Some name_node ->
            let name_range = TreeSitter.node_range name_node in
            let name_start = name_range.TreeSitter.start_point in
            let name_text = TreeSitter.node_text name_node source in
            let token = {
              line = name_start.row;
              start_char = name_start.column;
              length = String.length name_text;
              token_type = Parameter;
              token_modifiers = [Declaration];
            } in
            token :: acc
        | None -> acc)
    
    (* Variable declarations *)
    | "variable_declaration" ->
        (match TreeSitter.node_child_by_field_name node "name" with
        | Some name_node ->
            let name_range = TreeSitter.node_range name_node in
            let name_start = name_range.TreeSitter.start_point in
            let name_text = TreeSitter.node_text name_node source in
            let token = {
              line = name_start.row;
              start_char = name_start.column;
              length = String.length name_text;
              token_type = Variable;
              token_modifiers = [Declaration];
            } in
            token :: acc
        | None -> acc)
    
    (* Global and param declarations (constants) *)
    | "global_declaration" | "param_declaration" ->
        (match TreeSitter.node_child_by_field_name node "name" with
        | Some name_node ->
            let name_range = TreeSitter.node_range name_node in
            let name_start = name_range.TreeSitter.start_point in
            let name_text = TreeSitter.node_text name_node source in
            let token = {
              line = name_start.row;
              start_char = name_start.column;
              length = String.length name_text;
              token_type = Variable;
              token_modifiers = [Declaration; Readonly];
            } in
            token :: acc
        | None -> acc)
    
    (* Identifiers (variables, parameters in expressions) *)
    | "identifier" ->
        (* Only add if not already handled by parent node *)
        let parent = TreeSitter.node_parent node in
        (match parent with
        | Some p ->
            let parent_type = TreeSitter.node_type p in
            (* Skip if parent already handled this identifier *)
            if parent_type = "function_definition" || 
               parent_type = "parameter" || 
               parent_type = "variable_declaration" ||
               parent_type = "global_declaration" ||
               parent_type = "param_declaration" ||
               parent_type = "call" then
              acc
            else
              let token = {
                line = start_point.row;
                start_char = start_point.column;
                length;
                token_type = Variable;
                token_modifiers = [];
              } in
              token :: acc
        | None -> acc)
    
    (* Number literals *)
    | "number" | "integer_literal" ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = Number;
          token_modifiers = [];
        } in
        token :: acc
    
    (* String literals *)
    | "string" | "string_literal" ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = String;
          token_modifiers = [];
        } in
        token :: acc
    
    (* Operators *)
    | "+" | "-" | "*" | "/" | "%" | "<<" | ">>" | "&" | "|" | "^"
    | "==" | "!=" | "<" | ">" | "<=" | ">=" | "&&" | "||" | "!" | "~"
    | "=" | "+=" | "-=" | "*=" | "/=" ->
        let token = {
          line = start_point.row;
          start_char = start_point.column;
          length;
          token_type = Operator;
          token_modifiers = [];
        } in
        token :: acc
    
    | _ -> acc
  in
  
  (* Recursively process child nodes *)
  let child_count = TreeSitter.node_child_count node in
  let rec process_children i acc =
    if i >= child_count then acc
    else
      match TreeSitter.node_child node i with
      | Some child ->
          let acc = extract_tokens_from_node source child acc in
          process_children (i + 1) acc
      | None -> process_children (i + 1) acc
  in
  process_children 0 acc

(** Extract all semantic tokens from a document *)
let extract_semantic_tokens source tree =
  let root = TreeSitter.tree_root_node tree in
  let tokens = extract_tokens_from_node source root [] in
  (* Sort tokens by position (line, then character) *)
  List.sort (fun t1 t2 ->
    let line_cmp = compare t1.line t2.line in
    if line_cmp <> 0 then line_cmp
    else compare t1.start_char t2.start_char
  ) tokens

(** Encode tokens into LSP semantic tokens data format
    
    The data is a flat array of integers in groups of 5:
    [deltaLine, deltaStartChar, length, tokenType, tokenModifiers, ...]
    
    Each group represents a token with:
    - deltaLine: Line number relative to previous token (0 for first token)
    - deltaStartChar: Start character relative to previous token on same line, or absolute if different line
    - length: Token length
    - tokenType: Index into legend.tokenTypes
    - tokenModifiers: Bitmask of modifiers
*)
let encode_tokens tokens =
  let rec encode prev_line prev_char tokens acc =
    match tokens with
    | [] -> List.rev acc
    | token :: rest ->
        let delta_line = token.line - prev_line in
        let delta_char = 
          if delta_line = 0 then
            token.start_char - prev_char
          else
            token.start_char
        in
        let token_type_index = token_type_to_index token.token_type in
        let modifiers_mask = calculate_modifiers_mask token.token_modifiers in
        
        let encoded = [
          delta_line;
          delta_char;
          token.length;
          token_type_index;
          modifiers_mask;
        ] in
        
        encode token.line token.start_char rest (List.rev_append encoded acc)
  in
  encode 0 0 tokens []
