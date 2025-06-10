type t =
| Next
| High
| Low

let (>=) (p1) (p2) =
  match (p1, p2) with
  | (Next, Next) -> true
  | (Next, _) -> false
  | (High, Next) -> true
  | (High, High) -> true
  | (High, Low) -> true
  | (Low, Next) -> false
  | (Low, High) -> false
  | (Low, Low) -> true

let (>) (p1) (p2) =
  match (p1, p2) with
  | (Next, Next) -> false
  | (Next, _) -> false
  | (High, Next) -> true
  | (High, High) -> false
  | (High, Low) -> true
  | (Low, Next) -> false
  | (Low, High) -> false
  | (Low, Low) -> false

let (<=) (p1) (p2) = not (p1 > p2)

let (<) (p1) (p2) = not (p1 >= p2)

let compare (p1) (p2) =
  if p1 > p2 then 1
  else if p1 < p2 then -1
  else 0

type comparable_event =
| Pack : t * ('event) -> comparable_event

let compare_event : comparable_event -> comparable_event -> int =
  fun (Pack (p1, _)) (Pack (p2, _)) ->
    compare p1 p2
