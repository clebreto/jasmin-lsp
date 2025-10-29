# Multi-stage Dockerfile for building, testing and producing a runtime image for jasmin-lsp
# Optimized for Apple's container tool and other OCI-compliant runtimes
# Stages:
#  - builder : installs OCaml/opam, build dependencies, builds tree-sitter and the LSP
#  - tester  : runs pytest-based tests
#  - runtime : minimal image containing only the LSP executable and runtime libs

ARG OCAML_IMAGE=ocaml/opam:ubuntu-24.04-ocaml-5.3
FROM ${OCAML_IMAGE} AS builder
LABEL stage=builder

# Install system packages required for building tree-sitter and OCaml native libs
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    m4 \
    pkg-config \
    libgmp-dev \
    libmpfr-dev \
    libppl-dev \
    libpcre3-dev \
    ca-certificates \
    git \
    curl \
    python3 \
    python3-pip \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Switch back to opam user for builds
USER opam
WORKDIR /home/opam

# Install tree-sitter Python bindings (NOTE: not the CLI, but needed for pip cache)
RUN pip3 install --user --break-system-packages tree-sitter

# Set up opam environment and install dependencies
RUN opam update && \
    opam repo add coq-released https://coq.inria.fr/opam/released || true && \
    opam update && \
    opam install -y \
    dune \
    lwt \
    yojson \
    lsp \
    ppx_yojson_conv \
    lwt_ppx \
    cmdliner \
    batteries

# Install Coq 9.0.1 specifically (jasmin requires this version)
RUN opam install -y coq.9.0.1 coq-elpi

# Install jasmin compiler (pinned to compatible version)
RUN opam pin add -n jasmin https://github.com/jasmin-lang/jasmin.git && \
    opam install -y jasmin

# NOW build tree-sitter from source and install CLI (after expensive cached layers)
RUN npm install tree-sitter-cli && \
    git clone --depth=1 --branch=v0.25.10 https://github.com/tree-sitter/tree-sitter.git && \
    cd tree-sitter && \
    make && \
    sudo make install && \
    sudo ldconfig && \
    ls -la /usr/local/lib/libtree-sitter.* && \
    echo "Tree-sitter installed successfully"

# Copy source code
COPY --chown=opam:opam . jasmin-lsp/

WORKDIR /home/opam/jasmin-lsp

# Initialize and build tree-sitter-jasmin
RUN cd tree-sitter-jasmin && \
    /home/opam/node_modules/.bin/tree-sitter generate && \
    make clean && \
    make

# Build jasmin-lsp with proper library paths
RUN eval $(opam env) && \
    export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH && \
    export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH && \
    export LIBRARY_PATH=/usr/local/lib:$LIBRARY_PATH && \
    cd jasmin-lsp && \
    ldconfig -p | grep tree-sitter && \
    dune clean && \
    dune build --verbose 2>&1 | tee /tmp/dune-build.log || (cat /tmp/dune-build.log && exit 1)

############################################
FROM builder AS tester
LABEL stage=tester

# Install Python testing dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-pytest && \
    rm -rf /var/lib/apt/lists/*

USER opam
WORKDIR /home/opam/jasmin-lsp

# Install additional Python test dependencies
RUN pip3 install --user --break-system-packages \
    pytest>=7.0.0 \
    pytest-timeout>=2.1.0 \
    pytest-cov>=4.0.0

# Set up environment for running tests
ENV PATH="/home/opam/.local/bin:$PATH"
ENV LD_LIBRARY_PATH="/home/opam/jasmin-lsp/tree-sitter-jasmin:$LD_LIBRARY_PATH"

# Run tests as the default command
CMD ["bash", "-c", "eval $(opam env) && python3 -m pytest test -v --tb=short"]

############################################
FROM ubuntu:24.04 AS runtime
LABEL stage=runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libgmp10 \
    libmpfr6 \
    libppl14 \
    && rm -rf /var/lib/apt/lists/*

# Create runtime user
RUN useradd -m -s /bin/bash jasmin

WORKDIR /opt/jasmin-lsp

# Copy built executable and runtime libraries from builder
COPY --from=builder /home/opam/jasmin-lsp/_build/default/jasmin-lsp/jasmin_lsp.exe /usr/local/bin/jasmin-lsp
COPY --from=builder /home/opam/jasmin-lsp/tree-sitter-jasmin/libtree-sitter-jasmin.so /usr/local/lib/

RUN chmod +x /usr/local/bin/jasmin-lsp

# Set library path
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

USER jasmin
WORKDIR /home/jasmin

# Default command: run LSP server
ENTRYPOINT ["/usr/local/bin/jasmin-lsp"]

# Health check: verify executable exists and is runnable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["test", "-x", "/usr/local/bin/jasmin-lsp"]
