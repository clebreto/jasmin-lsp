with import <nixpkgs> {};


let jasminLsp = import ./default.nix; in

pkgs.mkShell {
  inputsFrom = [ jasminLsp ];
  nativeBuildInputs = (with ocamlPackages; [ ocaml-lsp ocamlformat]) ;
}