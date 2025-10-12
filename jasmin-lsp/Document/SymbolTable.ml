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
      (* Check if there's a 'from' clause with a namespace *)
      let namespace_opt = 
        let child_count = TreeSitter.node_named_child_count node in
        let rec find_from i =
          if i >= child_count then None
          else
            match TreeSitter.node_named_child node i with
            | None -> find_from (i + 1)
            | Some child ->
                if TreeSitter.node_type child = "from" then
                  (* Extract the namespace identifier from the 'from' node *)
                  match TreeSitter.node_child_by_field_name child "id" with
                  | Some id_node -> Some (TreeSitter.node_text id_node source)
                  | None -> find_from (i + 1)
                else
                  find_from (i + 1)
        in
        find_from 0
      in
      
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
                let filename_opt = match TreeSitter.node_child_by_field_name child "content" with
                  | Some content_node -> Some (TreeSitter.node_text content_node source)
                  | None -> 
                      (* Fallback: try to get text directly *)
                      let filename = TreeSitter.node_text child source in
                      (* Remove quotes if present *)
                      if String.length filename >= 2 && 
                         String.get filename 0 = '"' && 
                         String.get filename (String.length filename - 1) = '"' 
                      then Some (String.sub filename 1 (String.length filename - 2))
                      else Some filename
                in
                
                (match filename_opt with
                | Some filename ->
                    let current_path = Lsp.Uri.to_path uri in
                    let current_dir = Filename.dirname current_path in
                    
                    (* If there's a namespace, we need to search for it *)
                    let resolved_path = match namespace_opt with
                      | Some ns ->
                          (* Search for namespace directory in current dir and parent dirs *)
                          (* Try lowercase version of namespace (e.g., "Common" -> "common") *)
                          let ns_lower = String.lowercase_ascii ns in
                          
                          (* Try: current_dir/namespace/filename *)
                          let try1 = Filename.concat (Filename.concat current_dir ns) filename in
                          let try2 = Filename.concat (Filename.concat current_dir ns_lower) filename in
                          
                          (* Try: parent_dir/namespace/filename (for sibling directories) *)
                          let parent_dir = Filename.dirname current_dir in
                          let try3 = Filename.concat (Filename.concat parent_dir ns) filename in
                          let try4 = Filename.concat (Filename.concat parent_dir ns_lower) filename in
                          
                          (* Try: grandparent_dir/namespace/filename *)
                          let grandparent_dir = Filename.dirname parent_dir in
                          let try5 = Filename.concat (Filename.concat grandparent_dir ns) filename in
                          let try6 = Filename.concat (Filename.concat grandparent_dir ns_lower) filename in
                          
                          Io.Logger.log (Format.asprintf "Resolving: from %s require \"%s\"" ns filename);
                          Io.Logger.log (Format.asprintf "  Current dir: %s" current_dir);
                          Io.Logger.log (Format.asprintf "  Trying: %s -> %s" "current/ns" (if Sys.file_exists try1 then "FOUND" else "not found"));
                          Io.Logger.log (Format.asprintf "  Trying: %s -> %s" "current/ns_lower" (if Sys.file_exists try2 then "FOUND" else "not found"));
                          Io.Logger.log (Format.asprintf "  Trying: %s -> %s" "parent/ns" (if Sys.file_exists try3 then "FOUND" else "not found"));
                          Io.Logger.log (Format.asprintf "  Trying: %s -> %s" "parent/ns_lower" (if Sys.file_exists try4 then "FOUND" else "not found"));
                          
                          (* Return first existing path *)
                          if Sys.file_exists try1 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try1); Some try1)
                          else if Sys.file_exists try2 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try2); Some try2)
                          else if Sys.file_exists try3 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try3); Some try3)
                          else if Sys.file_exists try4 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try4); Some try4)
                          else if Sys.file_exists try5 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try5); Some try5)
                          else if Sys.file_exists try6 then (Io.Logger.log (Format.asprintf "  Resolved to: %s" try6); Some try6)
                          else (Io.Logger.log "  NOT FOUND in any location"; None)
                      | None ->
                          (* No namespace, resolve relative to current dir *)
                          let path = Filename.concat current_dir filename in
                          if Sys.file_exists path then Some path
                          else None
                    in
                    
                    (match resolved_path with
                    | Some path -> (Lsp.Uri.of_path path) :: acc
                    | None -> acc)
                | None -> acc)
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
  (* Strategy: Get text from start of var_decl to start of FIRST variable node
     This captures the complete type: "reg ptr u32[2]", "stack u64[8]", etc.
     For declarations like "reg u32 i, j;", all variables share the same type. *)
  
  (* First, find all variable nodes *)
  let child_count = TreeSitter.node_child_count node in
  let rec find_variables i acc =
    if i >= child_count then List.rev acc
    else
      match TreeSitter.node_child node i with
      | None -> find_variables (i + 1) acc
      | Some child ->
          let node_type = TreeSitter.node_type child in
          if node_type = "variable" then
            find_variables (i + 1) (child :: acc)
          else
            find_variables (i + 1) acc
  in
  
  let variables = find_variables 0 [] in
  
  (* Extract type from start of declaration to first variable *)
  let type_str = match variables with
    | [] -> None
    | first_var :: _ ->
        let node_range = TreeSitter.node_range node in
        let var_range = TreeSitter.node_range first_var in
        let start_byte = node_range.TreeSitter.start_byte in
        let end_byte = var_range.TreeSitter.start_byte in
        if end_byte > start_byte then
          let type_text = String.sub source start_byte (end_byte - start_byte) in
          let trimmed = String.trim type_text in
          if String.length trimmed > 0 then Some trimmed else None
        else
          None
  in
  
  (* Return all variables with the same type AND their individual ranges *)
  List.map (fun var_node ->
    let name = TreeSitter.node_text var_node source in
    let var_range = TreeSitter.node_range var_node in
    (name, type_str, var_range)
  ) variables

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
  (* Strategy: Get text from start of param_decl to start of FIRST parameter node
     For declarations like "reg u32 x, y", all parameters share the same type. *)
  
  (* First, find all parameter nodes *)
  let child_count = TreeSitter.node_child_count node in
  let rec find_parameters i acc =
    if i >= child_count then List.rev acc
    else
      match TreeSitter.node_child node i with
      | None -> find_parameters (i + 1) acc
      | Some child ->
          let node_type = TreeSitter.node_type child in
          if node_type = "parameter" then
            find_parameters (i + 1) (child :: acc)
          else
            find_parameters (i + 1) acc
  in
  
  let parameters = find_parameters 0 [] in
  
  (* Extract type from start of declaration to first parameter *)
  let type_str = match parameters with
    | [] -> None
    | first_param :: _ ->
        let node_range = TreeSitter.node_range node in
        let param_range = TreeSitter.node_range first_param in
        let start_byte = node_range.TreeSitter.start_byte in
        let end_byte = param_range.TreeSitter.start_byte in
        if end_byte > start_byte then
          let type_text = String.sub source start_byte (end_byte - start_byte) in
          let trimmed = String.trim type_text in
          if String.length trimmed > 0 then Some trimmed else None
        else
          None
  in
  
  (* Return all parameters with the same type AND their individual ranges *)
  List.map (fun param_node ->
    let name = TreeSitter.node_text param_node source in
    let param_range = TreeSitter.node_range param_node in
    (name, type_str, param_range)
  ) parameters

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
      List.fold_left (fun acc (name, detail, var_range) ->
        {
          name;
          kind = Variable;
          range = var_range;
          definition_range = var_range;
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
      List.fold_left (fun acc (name, detail, param_range) ->
        {
          name;
          kind = Parameter;
          range = param_range;
          definition_range = param_range;
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
            match TreeSitter.node_child_by_field_name node "type",
                  TreeSitter.node_child_by_field_name node "value" with
            | Some type_node, Some value_node ->
                let type_text = TreeSitter.node_text type_node source in
                let value_text = TreeSitter.node_text value_node source in
                Some (Format.asprintf "%s = %s" type_text value_text)
            | Some type_node, None ->
                Some (TreeSitter.node_text type_node source)
            | None, Some value_node ->
                let value_text = TreeSitter.node_text value_node source in
                Some (Format.asprintf "= %s" value_text)
            | None, None -> Some "param"
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

(** Build environment of constant values from source map 
    Returns a list of (name, value) pairs for successfully evaluated constants
    Uses multiple passes to resolve constants that depend on other constants *)
let build_const_env source_map =
  (* Collect all param nodes from all files *)
  let all_params = Hashtbl.fold (fun uri (source, tree) acc ->
    let root = TreeSitter.tree_root_node tree in
    let rec find_params node acc =
      let node_type = TreeSitter.node_type node in
      let acc = 
        if node_type = "param" then
          match TreeSitter.node_child_by_field_name node "name",
                TreeSitter.node_child_by_field_name node "value" with
          | Some name_node, Some value_node ->
              let name = TreeSitter.node_text name_node source in
              (name, value_node, source) :: acc
          | _ -> acc
        else acc
      in
      (* Recursively process children *)
      let child_count = TreeSitter.node_named_child_count node in
      let rec process_children i acc =
        if i >= child_count then acc
        else
          match TreeSitter.node_named_child node i with
          | None -> process_children (i + 1) acc
          | Some child -> process_children (i + 1) (find_params child acc)
      in
      process_children 0 acc
    in
    find_params root acc
  ) source_map [] in
  
  (* Evaluate constants in multiple passes until no more can be evaluated *)
  let rec evaluate_passes env remaining max_passes =
    if max_passes = 0 || remaining = [] then
      env
    else
      let newly_evaluated, still_remaining = List.partition_map (fun (name, value_node, source) ->
        match ExprEvaluator.evaluate_with_env env value_node source with
        | ExprEvaluator.Value v -> Either.Left (name, v)
        | ExprEvaluator.Error _ -> Either.Right (name, value_node, source)
      ) remaining in
      
      if newly_evaluated = [] then
        (* No progress made, stop *)
        env
      else
        (* Add newly evaluated constants to environment and continue *)
        let new_env = List.rev_append newly_evaluated env in
        evaluate_passes new_env still_remaining (max_passes - 1)
  in
  
  let final_env = evaluate_passes [] all_params 10 in  (* Max 10 passes *)
  final_env

(** Enhance constant symbols with computed values *)
let enhance_constants_with_values symbols source_map =
  (* Build environment of constant values *)
  let env = build_const_env source_map in
  
  (* Update each constant symbol with computed value *)
  List.map (fun sym ->
    if sym.kind = Constant then
      (* Find the param node for this symbol *)
      match Hashtbl.find_opt source_map sym.uri with
      | None -> sym
      | Some (source, tree) ->
          let rec find_param_node node =
            let node_type = TreeSitter.node_type node in
            if node_type = "param" then
              match TreeSitter.node_child_by_field_name node "name" with
              | Some name_node ->
                  if TreeSitter.node_text name_node source = sym.name then
                    Some node
                  else None
              | None -> None
            else
              let child_count = TreeSitter.node_named_child_count node in
              let rec check_children i =
                if i >= child_count then None
                else
                  match TreeSitter.node_named_child node i with
                  | None -> check_children (i + 1)
                  | Some child ->
                      match find_param_node child with
                      | Some n -> Some n
                      | None -> check_children (i + 1)
              in
              check_children 0
          in
          
          let root = TreeSitter.tree_root_node tree in
          (match find_param_node root with
          | None -> sym
          | Some param_node ->
              match TreeSitter.node_child_by_field_name param_node "value" with
              | None -> sym
              | Some value_node ->
                  (* Try to evaluate the expression *)
                  match ExprEvaluator.evaluate_with_env env value_node source with
                  | ExprEvaluator.Value computed_value ->
                      (* Update detail to include computed value *)
                      let new_detail = match sym.detail with
                        | Some detail_str -> Some (detail_str ^ " = " ^ string_of_int computed_value)
                        | None -> Some ("= " ^ string_of_int computed_value)
                      in
                      { sym with detail = new_detail }
                  | ExprEvaluator.Error _ -> sym)
    else
      sym
  ) symbols

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

(** Find definition by name, scoped to the function containing the given position *)
let find_definition_at_position symbols name position =
  Io.Logger.log (Format.asprintf "find_definition_at_position for '%s' at (%d,%d)" 
    name position.row position.column);
  
  (* Find which function contains the requested position *)
  let containing_function = 
    List.find_opt (fun sym ->
      sym.kind = Function &&
      let start_point = sym.range.start_point in
      let end_point = sym.range.end_point in
      (position.row > start_point.row || 
       (position.row = start_point.row && position.column >= start_point.column)) &&
      (position.row < end_point.row || 
       (position.row = end_point.row && position.column <= end_point.column))
    ) symbols
  in
  
  (match containing_function with
  | Some func -> 
      Io.Logger.log (Format.asprintf "Position is within function: %s" func.name)
  | None -> 
      Io.Logger.log "Position is not within any function");
  
  (* Filter symbols matching the name *)
  let matching_symbols = List.filter (fun sym -> sym.name = name) symbols in
  
  Io.Logger.log (Format.asprintf "Found %d symbols with name '%s'" 
    (List.length matching_symbols) name);
  List.iter (fun sym ->
    let kind_str = match sym.kind with
      | Function -> "Function"
      | Variable -> "Variable"
      | Parameter -> "Parameter"
      | Type -> "Type"
      | Constant -> "Constant"
    in
    Io.Logger.log (Format.asprintf "  - %s %s at line %d" 
      kind_str sym.name sym.definition_range.start_point.row)
  ) matching_symbols;
  
  match matching_symbols with
  | [] -> None
  | syms ->
      (* If we're inside a function, filter variables/parameters to only those in the same function *)
      let scoped_syms = match containing_function with
        | Some func when List.exists (fun s -> s.kind = Variable || s.kind = Parameter) syms ->
            (* Filter to variables/parameters within the function's range *)
            List.filter (fun sym ->
              match sym.kind with
              | Variable | Parameter ->
                  let def_line = sym.definition_range.start_point.row in
                  let func_start = func.range.start_point.row in
                  let func_end = func.range.end_point.row in
                  let in_scope = def_line >= func_start && def_line <= func_end in
                  Io.Logger.log (Format.asprintf "  Checking if %s '%s' (line %d) is in function '%s' (lines %d-%d): %b"
                    (if sym.kind = Variable then "variable" else "parameter")
                    sym.name def_line func.name func_start func_end in_scope);
                  in_scope
              | _ -> true (* Keep non-variable symbols *)
            ) syms
        | _ -> syms
      in
      
      Io.Logger.log (Format.asprintf "After scope filtering: %d candidates" 
        (List.length scoped_syms));
      
      (* Prioritize: parameters > variables > other symbols *)
      match List.find_opt (fun sym -> sym.kind = Parameter) scoped_syms with
      | Some param -> 
          Io.Logger.log (Format.asprintf "Returning parameter '%s' at line %d" 
            param.name param.definition_range.start_point.row);
          Some param
      | None ->
          match List.find_opt (fun sym -> sym.kind = Variable) scoped_syms with
          | Some var -> 
              Io.Logger.log (Format.asprintf "Returning variable '%s' at line %d" 
                var.name var.definition_range.start_point.row);
              Some var
          | None ->
              List.nth_opt scoped_syms 0

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
