






type position = (int * int)

type file_position = (string * position) (* position in a file *)


(* a request for a given variable should look like :
 GoToDefinition ("x",("file.jazz", (3,2)))
 => We need to be able to find the correct x corresponding to the file and position :

```
//file.jazz

fn test() {
  reg u64 x = 1;
  return x;
}

fn false_test() {
  reg u64 x = 2; // this x is not the same as the previous one
  return x;
}
```
we thus need a map of the form :
for each variable name, a list of file positions and the corresponding variable in jasmin (which contains definition )

*)
let empty = BatMap.empty

let position_included pos (locval: Jasmin.Location.t) =
  let open Jasmin.Location in
  let {loc_start; loc_end; loc_fname; _} = locval in
  let file,pos = pos in
  if (loc_start < pos && pos < loc_end && file = loc_fname) then
    true
  else
    false

let find_variable (value) (locals: Jasmin.Prog.Sv.t) =
  Jasmin.Prog.Sv.find_first_opt (fun v -> v.v_name = value) locals

let find_definition (name, pos) ((_,funcs):('info,'asm) Jasmin.Prog.prog) =
  let open Jasmin.Prog in
  let var_func = List.find_opt (fun f -> position_included pos f.f_loc) funcs in
  match var_func with
  | None -> None
  | Some f ->
    let var = find_variable name (Jasmin.Prog.locals f) in
    match var with
    | None -> None
    | Some v -> 
      let v_loc = v.v_dloc in
      let (line_start,character_start) = v_loc.loc_start in
      let (line_end,character_end) = v_loc.loc_end in
      Some (
        Lsp.Types.Position.create ~character:(character_start) ~line:(line_start),
        Lsp.Types.Position.create ~character:(character_end) ~line:(line_end),
        Lsp.Types.DocumentUri.of_string v_loc.loc_fname
      )

