(** Symbol Table - Analyzes tree-sitter syntax trees for symbols *)

open TreeSitter

type symbol_kind =
  | Function
  | Variable
  | Parameter
  | Type
  | Constant

type symbol = {
  name: string;
  kind: symbol_kind;
  range: TreeSitter.range;
  definition_range: TreeSitter.range;
  uri: Lsp.Types.DocumentUri.t;
  detail: string option;
}

type reference = {
  symbol_name: string;
  range: TreeSitter.range;
  uri: Lsp.Types.DocumentUri.t;
}

(** Helper: Convert point to LSP Position *)
let point_to_position point =
  Lsp.Types.Position.create 
    ~line:point.TreeSitter.row 
    ~character:point.TreeSitter.column

(** Extract required file paths from a document *)
let rec extract_requires_from_node uri source node acc =
  let node_type = TreeSitter.node_type node in
  
  let acc = match node_type with
  | "require" ->
      (* Find string_literal children which contain the filenames *)
      let child_count = TreeSitter.node_named_child_count node in
      let rec process_children i acc =
        if i >= child_count then acc
        else
          match TreeSitter.node_named_child node i with
          | None -> process_children (i + 1) acc
          | Some child ->
              let child_type = TreeSitter.node_type child in
              if child_type = "string_literal" then
                (* Extract the filename from string_literal -> string_content *)
                (match TreeSitter.node_child_by_field_name child "content" with
                | Some content_node ->
                    let filename = TreeSitter.node_text content_node source in
                    (* Resolve relative to current file *)
                    let current_path = Lsp.Uri.to_path uri in
                    let current_dir = Filename.dirname current_path in
                    let resolved_path = Filename.concat current_dir filename in
                    if Sys.file_exists resolved_path then
                      (Lsp.Uri.of_path resolved_path) :: acc
                    else
                      acc
                | None -> 
                    (* Fallback: try to get text directly *)
                    let filename = TreeSitter.node_text child source in
                    (* Remove quotes if present *)
                    let filename = 
                      if String.length filename >= 2 && 
                         String.get filename 0 = '"' && 
                         String.get filename (String.length filename - 1) = '"' 
                      then String.sub filename 1 (String.length filename - 2)
                      else filename
                    in
                    let current_path = Lsp.Uri.to_path uri in
                    let current_dir = Filename.dirname current_path in
                    let resolved_path = Filename.concat current_dir filename in
                    if Sys.file_exists resolved_path then
                      (Lsp.Uri.of_path resolved_path) :: acc
                    else
                      acc)
              else
                process_children (i + 1) acc
      in
      process_children 0 acc
  | _ -> acc
  in
  
  (* Recursively process children *)
  let child_count = TreeSitter.node_named_child_count node in
  let rec process_children i acc =
    if i >= child_count then acc
    else
      match TreeSitter.node_named_child node i with
      | None -> process_children (i + 1) acc
      | Some child -> process_children (i + 1) (extract_requires_from_node uri source child acc)
  in
  process_children 0 acc

let extract_required_files uri source tree =
  let root = TreeSitter.tree_root_node tree in
  extract_requires_from_node uri source root [] |> List.rev

(** Helper: Convert range to LSP Range *)
let range_to_lsp_range range =
  Lsp.Types.Range.create
    ~start:(point_to_position range.TreeSitter.start_point)
    ~end_:(point_to_position range.TreeSitter.end_point)

(** Helper: Convert symbol kind to LSP *)
let symbol_kind_to_lsp = function
  | Function -> Lsp.Types.SymbolKind.Function
  | Variable -> Lsp.Types.SymbolKind.Variable
  | Parameter -> Lsp.Types.SymbolKind.Variable
  | Type -> Lsp.Types.SymbolKind.Struct
  | Constant -> Lsp.Types.SymbolKind.Constant

(** Extract function name and parameters *)
let extract_function_info node source =
  match TreeSitter.node_child_by_field_name node "name" with
  | None -> None
  | Some name_node ->
      let name = TreeSitter.node_text name_node source in
      
      (* Get the full function signature text *)
      let full_text = TreeSitter.node_text node source in
      
      (* Extract parameters: find text between ( and ) *)
      let param_types = 
        match String.index_opt full_text '(', String.index_opt full_text ')' with
        | Some start_idx, Some end_idx when end_idx > start_idx + 1 ->
            let param_text = String.sub full_text (start_idx + 1) (end_idx - start_idx - 1) in
            String.trim param_text
        | _ -> ""
      in
      
      (* Extract return type: find text after -> *)
      let return_types =
        match String.index_from_opt full_text 0 '-' with
        | None -> ""
        | Some idx ->
            if idx + 1 < String.length full_text && String.get full_text (idx + 1) = '>' then
              (* Found ->, extract everything after it until { *)
              let after_arrow = String.sub full_text (idx + 2) (String.length full_text - idx - 2) in
              match String.index_opt after_arrow '{' with
              | Some brace_idx -> String.trim (String.sub after_arrow 0 brace_idx)
              | None -> String.trim after_arrow
            else
              ""
      in
      
      let detail = 
        if param_types = "" && return_types = "" then
          Some (Format.asprintf "fn %s()" name)
        else if return_types = "" then
          Some (Format.asprintf "fn %s(%s)" name param_types)
        else if param_types = "" then
          Some (Format.asprintf "fn %s() -> %s" name return_types)
        else
          Some (Format.asprintf "fn %s(%s) -> %s" name param_types return_types)
      in
      Some (name, detail)

(** Extract variable declaration info *)
let extract_variable_info node source =
  (* Strategy: Get text from start of var_decl to start of variable node
     This captures the complete type: "reg ptr u32[2]", "stack u64[8]", etc. *)
  let get_type_before_variable var_node =
    let node_range = TreeSitter.node_range node in
    let var_range = TreeSitter.node_range var_node in
    (* Extract text from start of declaration to start of variable *)
    let start_byte = node_range.TreeSitter.start_byte in
    let end_byte = var_range.TreeSitter.start_byte in
    if end_byte > start_byte then
      let type_text = String.sub source start_byte (end_byte - start_byte) in
      let trimmed = String.trim type_text in
      if String.length trimmed > 0 then Some trimmed else None
    else
      None
  in
  
  (* Get all variable names with their types *)
  let child_count = TreeSitter.node_child_count node in
  let rec collect_vars i acc =
    if i >= child_count then acc
    else
      match TreeSitter.node_child node i with
      | None -> collect_vars (i + 1) acc
      | Some child ->
          let node_type = TreeSitter.node_type child in
          if node_type = "variable" then
            let name = TreeSitter.node_text child source in
            let type_str = get_type_before_variable child in
            collect_vars (i + 1) ((name, type_str) :: acc)
          else
            collect_vars (i + 1) acc
  in
  collect_vars 0 []

(** Extract parameter info *)
let extract_parameter_info node source =
  let name_node = TreeSitter.node_child_by_field_name node "name" in
  let type_node = TreeSitter.node_child_by_field_name node "type" in
  
  match name_node with
  | None -> None
  | Some name_node ->
      let name = TreeSitter.node_text name_node source in
      let detail = 
        match type_node with
        | Some t -> Some (TreeSitter.node_text t source)
        | None -> None
      in
      Some (name, detail)

(** Extract parameter info from param_decl node - similar to var_decl *)
let extract_param_decl_info node source =
  (* Get type text from start of param_decl to start of parameter node *)
  let get_type_before_parameter param_node =
    let node_range = TreeSitter.node_range node in
    let param_range = TreeSitter.node_range param_node in
    (* Extract text from start of declaration to start of parameter *)
    let start_byte = node_range.TreeSitter.start_byte in
    let end_byte = param_range.TreeSitter.start_byte in
    if end_byte > start_byte then
      let type_text = String.sub source start_byte (end_byte - start_byte) in
      let trimmed = String.trim type_text in
      if String.length trimmed > 0 then Some trimmed else None
    else
      None
  in
  
  (* Get all parameter names with their types *)
  let child_count = TreeSitter.node_child_count node in
  let rec collect_params i acc =
    if i >= child_count then acc
    else
      match TreeSitter.node_child node i with
      | None -> collect_params (i + 1) acc
      | Some child ->
          let node_type = TreeSitter.node_type child in
          if node_type = "parameter" then
            let name = TreeSitter.node_text child source in
            let type_str = get_type_before_parameter child in
            collect_params (i + 1) ((name, type_str) :: acc)
          else
            collect_params (i + 1) acc
  in
  collect_params 0 []

(** Recursively extract symbols from a node *)
let rec extract_symbols_from_node uri source node acc =
  let node_type = TreeSitter.node_type node in
  let range = TreeSitter.node_range node in
  
  (* Extract symbol(s) based on node type *)
  let acc = match node_type with
  | "function_definition" ->
      (match extract_function_info node source with
      | Some (name, detail) ->
          {
            name;
            kind = Function;
            range;
            definition_range = range;
            uri;
            detail;
          } :: acc
      | None -> acc)
      
  | "variable_declaration" | "reg_declaration" | "stack_declaration" | "var_decl" ->
      let var_infos = extract_variable_info node source in
      List.fold_left (fun acc (name, detail) ->
        {
          name;
          kind = Variable;
          range;
          definition_range = range;
          uri;
          detail;
        } :: acc
      ) acc var_infos
      
  | "parameter" | "formal_arg" ->
      (match extract_parameter_info node source with
      | Some (name, detail) ->
          {
            name;
            kind = Parameter;
            range;
            definition_range = range;
            uri;
            detail;
          } :: acc
      | None -> acc)
      
  | "param_decl" ->
      let param_infos = extract_param_decl_info node source in
      List.fold_left (fun acc (name, detail) ->
        {
          name;
          kind = Parameter;
          range;
          definition_range = range;
          uri;
          detail;
        } :: acc
      ) acc param_infos
  
  (* Handle top-level param declarations: param int NAME = value; *)
  | "param" ->
      (match TreeSitter.node_child_by_field_name node "name" with
      | Some name_node ->
          let name = TreeSitter.node_text name_node source in
          let detail = 
            match TreeSitter.node_child_by_field_name node "type" with
            | Some type_node -> Some (TreeSitter.node_text type_node source)
            | None -> Some "param"
          in
          {
            name;
            kind = Constant;  (* params are compile-time constants *)
            range;
            definition_range = range;
            uri;
            detail;
          } :: acc
      | None -> acc)
  
  (* Handle global declarations: type NAME = value; *)
  | "global" ->
      (match TreeSitter.node_child_by_field_name node "name" with
      | Some name_node ->
          let name = TreeSitter.node_text name_node source in
          let detail =
            match TreeSitter.node_child_by_field_name node "type" with
            | Some type_node -> Some (TreeSitter.node_text type_node source)
            | None -> Some "global"
          in
          {
            name;
            kind = Variable;  (* globals are variables *)
            range;
            definition_range = range;
            uri;
            detail;
          } :: acc
      | None -> acc)
      
  | "type_definition" ->
      (match TreeSitter.node_child_by_field_name node "name" with
      | Some name_node ->
          let name = TreeSitter.node_text name_node source in
          {
            name;
            kind = Type;
            range;
            definition_range = range;
            uri;
            detail = Some "type";
          } :: acc
      | None -> acc)
      
  (* Note: We don't extract standalone "variable" nodes because they represent usages,
     not declarations. Type information comes from variable_declaration nodes. *)
  | _ -> acc
  in
  
  (* Recursively process children *)
  let child_count = TreeSitter.node_named_child_count node in
  let rec process_children i acc =
    if i >= child_count then acc
    else
      match TreeSitter.node_named_child node i with
      | None -> process_children (i + 1) acc
      | Some child -> process_children (i + 1) (extract_symbols_from_node uri source child acc)
  in
  process_children 0 acc

let extract_symbols uri source tree =
  let root = TreeSitter.tree_root_node tree in
  extract_symbols_from_node uri source root [] |> List.rev

(** Extract identifier references *)
let rec extract_references_from_node uri source node acc =
  let node_type = TreeSitter.node_type node in
  let range = TreeSitter.node_range node in
  
  let reference_opt = match node_type with
  | "identifier" | "variable_name" ->
      let name = TreeSitter.node_text node source in
      Some {
        symbol_name = name;
        range;
        uri;
      }
  | _ -> None
  in
  
  let acc = match reference_opt with
    | Some ref -> ref :: acc
    | None -> acc
  in
  
  (* Recursively process children *)
  let child_count = TreeSitter.node_named_child_count node in
  let rec process_children i acc =
    if i >= child_count then acc
    else
      match TreeSitter.node_named_child node i with
      | None -> process_children (i + 1) acc
      | Some child -> process_children (i + 1) (extract_references_from_node uri source child acc)
  in
  process_children 0 acc

let extract_references uri source tree =
  let root = TreeSitter.tree_root_node tree in
  extract_references_from_node uri source root [] |> List.rev

(** Find symbol at a specific position *)
let find_symbol_at_position (symbols : symbol list) (point : TreeSitter.point) : symbol option =
  List.find_opt (fun (sym : symbol) ->
    let { TreeSitter.start_point; end_point; _ } = sym.range in
    (point.TreeSitter.row > start_point.row || (point.row = start_point.row && point.column >= start_point.column)) &&
    (point.row < end_point.row || (point.row = end_point.row && point.column <= end_point.column))
  ) symbols

(** Find all references to a symbol by name *)
let find_references_to references name =
  List.filter (fun ref -> ref.symbol_name = name) references

(** Find definition by name *)
let find_definition symbols name =
  (* Prefer parameters, then variables, then other symbols *)
  (* This ensures we find parameter definitions before variable definitions with the same name *)
  let matching_symbols = List.filter (fun sym -> sym.name = name) symbols in
  match matching_symbols with
  | [] -> None
  | syms ->
      (* Try to find a parameter first *)
      match List.find_opt (fun sym -> sym.kind = Parameter) syms with
      | Some param -> Some param
      | None ->
          (* Then try variables *)
          match List.find_opt (fun sym -> sym.kind = Variable) syms with
          | Some var -> Some var
          | None ->
              (* Finally, return any matching symbol *)
              List.nth_opt syms 0

(** Convert to LSP SymbolInformation *)
let symbol_to_lsp symbol =
  Lsp.Types.SymbolInformation.create
    ~name:symbol.name
    ~kind:(symbol_kind_to_lsp symbol.kind)
    ~location:(Lsp.Types.Location.create
      ~uri:symbol.uri
      ~range:(range_to_lsp_range symbol.range))
    ()

(** Convert to LSP DocumentSymbol *)
let symbol_to_document_symbol symbol =
  Lsp.Types.DocumentSymbol.create
    ~name:symbol.name
    ~kind:(symbol_kind_to_lsp symbol.kind)
    ~range:(range_to_lsp_range symbol.range)
    ~selectionRange:(range_to_lsp_range symbol.definition_range)
    ?detail:symbol.detail
    ()
