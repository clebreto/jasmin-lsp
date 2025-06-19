# jasmin-lsp
An implementation of language server protocol for the Jasmin programming language.

This project is still in an highly early stage and nowhere near release point.

# install

## Dependancies

For the moment, this repo only support [nix](https://nixos.org/). We will also add an [opam](https://opam.ocaml.org/) support in future release.

### opam

<!-- You can install the project dependencies by using the following command on an empty switch (just ignore warning, this will be fixed later):
```
opam install ./jasmin-lsp.opam --deps-only
```

(NB : Each time you run `dune build`, this will generate an updated opam file with new dependencies) -->

Not working for the moment, will be repaired in the next jasmin release

### nix

Just use the command :
```nix-shell``` (or ```nix-shell dev.nix``` to have ocaml-lsp in your environments)

## Build

With your environment set up, run :

```dune build```

this will produce and executable located at `_build/default/jasmun-lsp/jasmin_lsp.exe`.

# Running the project

## On terminal

Just run the executable build in previous step. You can copy-paste rpc requests to test the behaviour of the server. This is mainly for debug purposes. We also provide a little shell script (`test.sh`) to test the server.

## On ide

### Vscode

Install the [Vsjazz](https://marketplace.visualstudio.com/items?itemName=jasmin-lang.vsjazz) extension and change the path to the server for your executable.

### Other IDE

Not supported / Not documented. It should work with ide that use the standard lsp protocol like [neovim](https://neovim.io/).

# Contribute : TODO

# Contributors
* [MrDaiki](https://github.com/MrDaiki) (Alexandre BOURBEILLON)
* [clebreto](https://github.com/clebreto) (Côme LE BRETON)