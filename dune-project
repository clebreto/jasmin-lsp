(lang dune 3.8)
(version 0.0.1)
(license MIT)
(maintainers "Jasmin Compiler Team")
(authors "Jasmin Compiler Team")
(generate_opam_files true)

(package
 (name jasmin-lsp)
 (synopsis "Jasmin Language Server Protocol (LSP) implementation")
 (depends (ocaml (>= 5.3.0)) lwt yojson lsp ppx_yojson_conv lwt_ppx cmdliner batteries jasmin))
