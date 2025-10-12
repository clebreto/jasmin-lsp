(** Expression Evaluator - Evaluates constant expressions to their numeric values *)

[@@@ocaml.warning "-33"]
open TreeSitter
[@@@ocaml.warning "+33"]

(** Environment mapping constant names to their values *)
type const_env = (string * int) list

(** Result of expression evaluation *)
type eval_result =
  | Value of int
  | Error of string

(** Evaluate a tree-sitter node as a constant expression *)
let rec eval_expr env node source =
  let node_type = TreeSitter.node_type node in
  
  match node_type with
  (* Integer literals *)
  | "int_literal" | "integer_literal" | "number" ->
      let text = TreeSitter.node_text node source in
      (try
        (* Handle hex literals (0x...) *)
        if String.length text > 2 && String.sub text 0 2 = "0x" then
          let hex_part = String.sub text 2 (String.length text - 2) in
          Value (int_of_string ("0x" ^ hex_part))
        (* Handle binary literals (0b...) *)
        else if String.length text > 2 && String.sub text 0 2 = "0b" then
          let bin_part = String.sub text 2 (String.length text - 2) in
          Value (int_of_string ("0b" ^ bin_part))
        (* Regular decimal *)
        else
          Value (int_of_string text)
      with Failure _ -> Error ("Invalid integer literal: " ^ text))
  
  (* Variable/constant references *)
  | "variable" | "identifier" | "variable_name" ->
      let name = TreeSitter.node_text node source in
      (match List.assoc_opt name env with
      | Some value -> Value value
      | None -> Error ("Undefined constant: " ^ name))
  
  (* Binary operations *)
  | "bin_expr" | "binary_expression" | "binary_op" ->
      (match TreeSitter.node_child_by_field_name node "left",
             TreeSitter.node_child_by_field_name node "operator",
             TreeSitter.node_child_by_field_name node "right" with
      | Some left, Some op, Some right ->
          let op_text = TreeSitter.node_text op source in
          (match eval_expr env left source, eval_expr env right source with
          | Value l, Value r ->
              (match op_text with
              | "+" -> Value (l + r)
              | "-" -> Value (l - r)
              | "*" -> Value (l * r)
              | "/" -> if r = 0 then Error "Division by zero" else Value (l / r)
              | "%" -> if r = 0 then Error "Modulo by zero" else Value (l mod r)
              | "<<" -> Value (l lsl r)
              | ">>" -> Value (l lsr r)
              | "&" -> Value (l land r)
              | "|" -> Value (l lor r)
              | "^" -> Value (l lxor r)
              | _ -> Error ("Unsupported operator: " ^ op_text))
          | Error e, _ -> Error e
          | _, Error e -> Error e)
      | _ ->
          (* Fallback: try to get operator from child nodes *)
          let child_count = TreeSitter.node_named_child_count node in
          if child_count >= 3 then
            let left_opt = TreeSitter.node_named_child node 0 in
            let op_opt = TreeSitter.node_named_child node 1 in
            let right_opt = TreeSitter.node_named_child node 2 in
            (match left_opt, op_opt, right_opt with
            | Some left, Some op, Some right ->
                let op_text = TreeSitter.node_text op source in
                (match eval_expr env left source, eval_expr env right source with
                | Value l, Value r ->
                    (match op_text with
                    | "+" -> Value (l + r)
                    | "-" -> Value (l - r)
                    | "*" -> Value (l * r)
                    | "/" -> if r = 0 then Error "Division by zero" else Value (l / r)
                    | "%" -> if r = 0 then Error "Modulo by zero" else Value (l mod r)
                    | "<<" -> Value (l lsl r)
                    | ">>" -> Value (l lsr r)
                    | "&" -> Value (l land r)
                    | "|" -> Value (l lor r)
                    | "^" -> Value (l lxor r)
                    | _ -> Error ("Unsupported operator: " ^ op_text))
                | Error e, _ -> Error e
                | _, Error e -> Error e)
            | _ -> Error "Invalid binary expression structure")
          else
            Error "Invalid binary expression")
  
  (* Unary operations *)
  | "unary_expression" | "unary_op" ->
      (match TreeSitter.node_child_by_field_name node "operator",
             TreeSitter.node_child_by_field_name node "argument" with
      | Some op, Some arg ->
          let op_text = TreeSitter.node_text op source in
          (match eval_expr env arg source with
          | Value v ->
              (match op_text with
              | "-" -> Value (-v)
              | "+" -> Value v
              | "~" -> Value (lnot v)
              | "!" -> Value (if v = 0 then 1 else 0)
              | _ -> Error ("Unsupported unary operator: " ^ op_text))
          | Error e -> Error e)
      | _ -> Error "Invalid unary expression structure")
  
  (* Parenthesized expressions *)
  | "parenthesized_expression" | "paren_expr" ->
      let child_count = TreeSitter.node_named_child_count node in
      if child_count > 0 then
        match TreeSitter.node_named_child node 0 with
        | Some inner -> eval_expr env inner source
        | None -> Error "Empty parenthesized expression"
      else
        Error "Empty parenthesized expression"
  
  (* Type cast or similar constructs - try to evaluate the inner expression *)
  | "cast_expression" ->
      let child_count = TreeSitter.node_named_child_count node in
      if child_count > 0 then
        match TreeSitter.node_named_child node (child_count - 1) with
        | Some inner -> eval_expr env inner source
        | None -> Error "Invalid cast expression"
      else
        Error "Invalid cast expression"
  
  (* For other node types, try to recursively evaluate children *)
  | _ ->
      let child_count = TreeSitter.node_named_child_count node in
      if child_count = 1 then
        match TreeSitter.node_named_child node 0 with
        | Some child -> eval_expr env child source
        | None -> Error ("Cannot evaluate node type: " ^ node_type)
      else
        Error ("Cannot evaluate node type: " ^ node_type)

(** Evaluate a constant expression with the given environment *)
let evaluate_with_env env expr_node source =
  eval_expr env expr_node source

(** Format the evaluation result *)
let format_result = function
  | Value v -> Some (string_of_int v)
  | Error _ -> None
