with import <nixpkgs> {};


mkShell {
  packages = (with ocaml-ng.ocamlPackages; [
    ocaml
    findlib
    dune_3
    batteries
    cmdliner
    angstrom
    menhir
    yojson
    ppx_yojson_conv
    lsp
    lwt
    lwt_ppx
    jasmin-compiler
    ]);
}