# Jasmin-LSP: Exhaustive Project Description

## Overview

**Jasmin-LSP** is a Language Server Protocol (LSP) implementation for the Jasmin programming language, written in OCaml. The project is in early development (version 0.0.1) and provides IDE support for Jasmin files (`.jazz` and `.jinc` extensions) through the standard LSP specification.

**Repository:** jasmin-lsp (MrDaiki)  
**License:** MIT  
**Primary Contributors:** Alexandre BOURBEILLON (MrDaiki), Côme LE BRETON (clebreto)  
**Language:** OCaml (>= 5.3.0)

---

## Architecture Overview

The architecture follows an **event-driven, priority-queue based design** using the Lwt cooperative threading library for asynchronous I/O operations. The system is structured in distinct layers, each with well-defined responsibilities.

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     IDE/Editor Client                        │
│                   (VSCode, Neovim, etc.)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ JSON-RPC over stdio
                         │ (LSP Protocol)
┌────────────────────────▼────────────────────────────────────┐
│                    I/O Layer (Channel)                       │
│              - Raw input/output operations                   │
│              - Lwt-based async I/O                          │
│              - stdin/stdout/stderr handling                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   RPC Protocol Layer                         │
│       - Header parsing (Content-Length, Content-Type)        │
│       - JSON-RPC packet serialization/deserialization        │
│       - Request/Response/Notification routing                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   LSP Protocol Layer                         │
│         - LSP-specific request handlers                      │
│         - Initialize, TextDocumentDefinition, etc.           │
│         - Notification handlers                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Event Processing Core                       │
│       - Priority-based event queue (Min-Heap)               │
│       - Event handler abstraction                            │
│       - Main server loop                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 Document/Analysis Layer                      │
│       - AST indexing and navigation                         │
│       - Symbol definition lookup                             │
│       - Jasmin compiler integration                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Architectural Components

### 1. **Core Event System** (`jasmin_lsp.ml`)

The heart of the architecture is an event-driven system built around a priority queue using Lwt for asynchronous execution.

#### 1.1 EventHandler Module Type
Defines the contract for event handlers:
```ocaml
module type EventHandler = sig
  type event
  val receive_event : ('len,'asm) Jasmin.Prog.prog option -> 
                      ((Priority.t * event) list, EventError.t) result Lwt.t
  val handle_event : event -> ('len,'asm) Jasmin.Prog.prog option -> 
                     (Priority.t * event) list Lwt.t
end
```

**Key responsibilities:**
- **receive_event**: Blocks until new events arrive from external sources (stdin)
- **handle_event**: Processes a single event and may generate new events

#### 1.2 RpcHandler Implementation
Concrete implementation of EventHandler for JSON-RPC:
- Receives RPC packets from stdin
- Routes packets to appropriate handlers
- Generates response events

#### 1.3 Event Processing Loop
The `Make` functor creates a parameterized server:

```ocaml
module Make (Handler : EventHandler) = struct
  module EventHeap = Batteries.Heap.Make (PE)
  
  let rec server_loop (event_queue : EventHeap.t) 
                      (prog : ('len,'asm) Jasmin.Prog.prog option) = ...
end
```

**Event Loop Algorithm:**
1. Check if the priority queue has events
2. If empty, wait for new events via `receive_event`
3. If not empty, pop the highest priority event
4. Handle the event (may produce new events)
5. Merge new events into the queue
6. Recurse

**Error Handling:**
- `EndOfFile`: Gracefully exits the server loop
- `ParseError`: Logs error and continues waiting for valid events

---

### 2. **Priority System** (`Priority.ml`)

A three-level priority system for event scheduling:

```ocaml
type t = Next | High | Low
```

**Priority Semantics:**
- **Next**: Immediate processing (e.g., sending responses)
- **High**: Important but not immediate
- **Low**: Background/deferred processing (e.g., configuration requests)

The system implements a total ordering with comparison functions (`>`, `>=`, `<`, `<=`, `compare`).

**Design Rationale:**
- Ensures responses are sent before processing new requests
- Allows background tasks without blocking critical operations
- Uses min-heap implementation from Batteries library

---

### 3. **I/O Layer** (`Io/Channel.ml`, `Io/Logger.ml`)

#### 3.1 Channel Module
Abstracts low-level I/O operations using Lwt:

```ocaml
type t = {
  in_channel : Lwt_io.input_channel;
  out_channel : Lwt_io.output_channel;
  err_channel : Lwt_io.output_channel;
}
```

**Key Functions:**
- `write_string_to_channel`: Write to stdout with automatic flushing
- `read_raw_line`: Read a single line (for headers)
- `read_raw_chars`: Read exact byte count (for message body)
- `read_file`: Synchronous file reading

**Design Choice:** Uses Lwt streams for efficient character-by-character reading when needed.

#### 3.2 Logger Module
Simple synchronous stderr logging:
```ocaml
let log (str: string) = 
  output_string stderr (Format.asprintf "\n[LOG] : %s\n" str);
  flush stderr
```

**Note:** Currently synchronous; marked as TODO for Lwt conversion.

---

### 4. **RPC Protocol Layer** (`Protocol/RpcProtocol.ml`)

Handles JSON-RPC 2.0 specification compliance.

#### 4.1 Header Parsing

**Supported Headers:**
- `Content-Length`: Required for message boundary detection
- `Content-Type`: Optional (supports vscode-jsonrpc and application/json)
- Custom headers: Stored but not processed

**Parsing Strategy:**
1. Read lines until empty line (header terminator)
2. Parse each header with `String.split_on_char ':'`
3. Accumulate in `request_headers` record
4. Validate `Content-Length` presence

#### 4.2 Body Reading

```ocaml
let read_rpc_body (size : int) : (string,EventError.t) result Lwt.t
```

Uses Lwt streams to read exactly `size` bytes:
1. Create a stream that reads chunks until size reached
2. Collect all chunks into a list
3. Concatenate into final body string

**Correctness:** Ensures exact byte count to prevent message boundary issues.

#### 4.3 Packet Routing

```ocaml
let handle_rpc_packet (packet : Jsonrpc.Packet.t) (prog) = 
  match packet with
  | Request req -> receive_rpc_request req prog
  | Notification notif -> receive_rpc_notification notif
  | Response resp -> receive_rpc_response resp
  | Batch_response batch_resp -> receive_rpc_batch_response batch_resp
  | Batch_call batch_call -> receive_rpc_batch_call batch_call
```

**Packet Types:**
- **Request**: Requires response (routed to LSP layer)
- **Notification**: Fire-and-forget (routed to LSP layer)
- **Response**: From server to client (currently unimplemented)
- **Batch**: Multiple packets (currently unimplemented)

#### 4.4 Response Writing

```ocaml
let write_json_rpc (json: Yojson.Safe.t) =
  let content = Yojson.Safe.pretty_to_string ~std:true json in
  let size = String.length content in
  let message = Format.asprintf"Content-Length: %d\r\n\r\n%s" size content in
  Io.Channel.write_string_to_channel Config.channels message
```

**Format Compliance:**
- Uses `\r\n` line endings per LSP specification
- Calculates exact Content-Length in bytes
- Double newline separates headers from body

---

### 5. **LSP Protocol Layer** (`Protocol/LspProtocol.ml`)

Bridges JSON-RPC to LSP-specific semantics using the `lsp` OCaml library.

#### 5.1 Initialization Sequence

```ocaml
let receive_initialize_request (params : Lsp.Types.InitializeParams.t) =
  let initialize_response = get_initialize_response params in
  let config = configuration_request in
  Ok(initialize_response), [(Priority.Low, Send config)]
```

**Flow:**
1. Client sends `initialize` request
2. Server responds with capabilities
3. Server immediately sends `workspace/configuration` request
4. Client sends `initialized` notification

**Capabilities Declared:**
- `textDocumentSync`: Full document sync with open/close tracking
- `definitionProvider`: Go-to-definition support
- `completionProvider`: Code completion (placeholder)
- `hoverProvider`: Currently disabled
- `workspace.fileOperations`: Monitors `.jazz` and `.jinc` files

#### 5.2 Go-to-Definition

```ocaml
let receive_text_document_definition_request (params : Lsp.Types.DefinitionParams.t) (prog)
```

**Implementation:**
1. Extract symbol name from `partialResultToken` (non-standard usage)
2. Get cursor position from `params.position`
3. Call `Document.AstIndex.find_definition` with Jasmin AST
4. Convert Jasmin location to LSP Range/Location
5. Return as `Location` array

**Current Limitation:** Expects symbol name in `partialResultToken` which is a workaround.

#### 5.3 Request Routing

```ocaml
let receive_lsp_request_inner : type a. Jsonrpc.Id.t -> a Lsp.Client_request.t -> 
  ('info,'asm) Jasmin.Prog.prog option -> (a,string) result * (Priority.t * RpcProtocolEvent.t) list
```

Uses GADTs from the `lsp` library for type-safe request handling:
- `Initialize` → `receive_initialize_request`
- `TextDocumentDefinition` → `receive_text_document_definition_request`
- Others → "Unsupported request" error

**Type Safety:** The `type a.` ensures the response type matches the request type.

---

### 6. **Event Types** (`Protocol/RpcProtocolEvent.ml`, `Protocol/EventError.ml`)

#### 6.1 Protocol Events
```ocaml
type t =
| Receive of Jsonrpc.Packet.t option
| Send of Yojson.Safe.t
```

**Semantics:**
- `Receive None`: No packet available (shouldn't occur with blocking I/O)
- `Receive (Some packet)`: New packet to process
- `Send json`: Outgoing response to write

#### 6.2 Error Types
```ocaml
type t = ParseError | EndOfFile
```

**Usage:**
- `ParseError`: Malformed JSON, invalid headers, or decoding failures
- `EndOfFile`: stdin closed (triggers graceful shutdown)

---

### 7. **Document Analysis Layer** (`Document/AstIndex.ml`)

Provides symbol resolution using the Jasmin compiler's AST.

#### 7.1 Position Representation

```ocaml
type position = (int * int)  (* (character, line) *)
type file_position = (string * position)
```

#### 7.2 Definition Lookup Algorithm

```ocaml
let find_definition (name, pos) ((_,funcs):('info,'asm) Jasmin.Prog.prog)
```

**Algorithm:**
1. Find function containing the cursor position:
   ```ocaml
   List.find_opt (fun f -> position_included pos f.f_loc) funcs
   ```
2. Get local variables of that function:
   ```ocaml
   Jasmin.Prog.locals f
   ```
3. Find variable with matching name:
   ```ocaml
   Jasmin.Prog.Sv.find_first_opt (fun v -> v.v_name = value) locals
   ```
4. Extract definition location from `v.v_dloc`
5. Convert to LSP Position and DocumentUri

**Scope Handling:**
- Only searches within the containing function's scope
- Prevents cross-function variable confusion
- Uses Jasmin's scoped variable set (`Sv.t`)

**Limitations:**
- No global variable support
- No cross-file references
- No imported symbol resolution

---

### 8. **Configuration System** (`Config.ml`)

#### 8.1 Server Metadata
```ocaml
let name = "jasmin-lsp"
let version = "0.1.0"
let channels = Io.Channel.std_channel
let conf_request_id = max_int
```

#### 8.2 Configuration File Format
```json
{
    "jasmin-root": "./test.jazz",
    "arch": "x86"
}
```

**Schema:**
- `jasmin_root`: Path to root Jasmin file
- `arch`: Target architecture (x86, arm, etc.)

**Loading:**
```ocaml
let set_configuration (conf_path: string) =
  let conf_str = Io.Channel.read_file conf_path in
  let config = config_of_yojson (Yojson.Safe.from_string conf_str) in
  config_value := Some config
```

Uses `ppx_yojson_conv` for automatic JSON serialization.

#### 8.3 Capability Declaration

Extensive `ServerCapabilities` declaration including:
- **File operation filters**: `.jazz` and `.jinc` glob patterns
- **Text document sync**: Full document sync mode
- **didCreate/willCreate/didRename/willRename/didDelete/willDelete**: Complete file operation lifecycle

---

### 9. **Architecture Definition** (`ArchDef.ml`)

Configures Jasmin compiler for specific CPU architectures:

```ocaml
module Arch =
  ( val let use_set0 = true and use_lea = false in
        let call_conv = Jasmin.Glob_options.Linux in
        let module C : Jasmin.Arch_full.Core_arch =
          (val Jasmin.CoreArchFactory.core_arch_x86 ~use_lea ~use_set0 call_conv)
        in
        (module Jasmin.Arch_full.Arch_from_Core_arch (C) : Jasmin.Arch_full.Arch) )
```

**Current Configuration:**
- **Architecture**: x86
- **Calling Convention**: Linux
- **Optimizations**: `use_set0=true`, `use_lea=false`

**Design Note:** Uses first-class modules for flexible architecture selection.

---

### 10. **Parser Layer** (`Parser/parser.ml`)

**Status:** Incomplete implementation for incremental parsing.

#### 10.1 Syntax Tree Representation
```ocaml
type tree_kind = FunctionDef | TypeDef | Annotation | ParamDef | ...
type syntax_tree = Tree of cst | Token of Jasmin.Parser.token
and cst = { kind : tree_kind; children : syntax_tree list; }
```

#### 10.2 Event-Driven Parsing
```ocaml
type parsing_event = Open of tree_kind | Close | Advance
```

**Design Goal:** Build a CST (Concrete Syntax Tree) from a flat event stream for error-resilient parsing.

**Current State:** Skeleton implementation; not integrated with main server.

---

## Data Flow Analysis

### Initialization Flow

```
Client                    Server
  |                         |
  |--- initialize --------->|
  |                         | (parse headers)
  |                         | (parse JSON-RPC)
  |                         | (decode LSP request)
  |                         | (build capabilities)
  |<-- initialize response -|
  |                         |
  |<-- workspace/config req-| (Priority.Low event)
  |                         |
  |--- initialized -------->|
  |                         | (log "Server initialized")
```

### Go-to-Definition Flow

```
Client                    Server                    Jasmin AST
  |                         |                            |
  |--- textDocument/defn -->|                            |
  |  (uri, position, name)  |                            |
  |                         |--- find_definition ------->|
  |                         |  (name, file_pos)          |
  |                         |                            |
  |                         |<--- Some(loc_start, ...) --|
  |                         | (convert to LSP Range)     |
  |<-- definition response -|                            |
  |  (Location[])           |                            |
```

### Event Priority Scheduling

```
Event Queue (Min-Heap)
┌──────────────────────────────────┐
│ Priority.Next: Send response     │ <- Processed first
├──────────────────────────────────┤
│ Priority.High: Parse request     │
├──────────────────────────────────┤
│ Priority.Low: Config request     │ <- Processed last
└──────────────────────────────────┘
```

---

## Dependency Analysis

### Core OCaml Libraries
- **lwt**: Cooperative threading and async I/O
- **lwt.unix**: Unix-specific Lwt bindings
- **lwt_ppx**: Syntax extension for `let%lwt` notation
- **yojson**: JSON parsing and serialization
- **ppx_yojson_conv**: Automatic JSON converters
- **lsp**: LSP types and protocol implementation
- **cmdliner**: Command-line argument parsing (unused in current code)
- **batteries**: Extended standard library (Heap, Map)
- **jasmin**: Jasmin compiler library

### Build System
- **dune**: Build system (>= 3.8)
- **opam**: Package manager
- **nix**: Alternative package management (recommended)

### External Tools
- **pixi**: Cross-platform package manager (for C dependencies)
- **gmp, mpfr, ppl, pkgconf**: Required by Jasmin compiler

---

## Design Patterns and Principles

### 1. **Functor-Based Modularity**
The `Make` functor parameterizes the server over any `EventHandler`:
```ocaml
module Make (Handler : EventHandler)
```
**Benefit:** Easy to add new event sources (file watchers, network sockets).

### 2. **Priority Queue Event Loop**
Uses a min-heap for scheduling:
**Benefit:** Prevents priority inversion; ensures timely responses.

### 3. **Result Type Error Handling**
Pervasive use of `result Lwt.t`:
```ocaml
val receive_event : ... -> ((Priority.t * event) list, EventError.t) result Lwt.t
```
**Benefit:** Explicit error handling; composable with Lwt.

### 4. **Type-Safe Protocol Handling**
Uses GADTs from `lsp` library:
```ocaml
let receive_lsp_request_inner : type a. Jsonrpc.Id.t -> a Lsp.Client_request.t -> ...
```
**Benefit:** Compile-time guarantee that responses match requests.

### 5. **Separation of Concerns**
Clear layering:
- I/O ← RPC ← LSP ← Event Core ← Document Analysis

**Benefit:** Each layer testable in isolation.

---

## Current Limitations and Future Work

### Implemented Features
✅ LSP server initialization  
✅ Go-to-definition for local variables  
✅ JSON-RPC 2.0 message handling  
✅ Priority-based event scheduling  
✅ Async I/O with Lwt  

### Missing Features
❌ Hover information  
❌ Code completion  
❌ Diagnostics (syntax/semantic errors)  
❌ Document synchronization (didOpen/didChange)  
❌ Global symbol resolution  
❌ Cross-file references  
❌ Incremental parsing  
❌ Batch request handling  
❌ Configuration response handling  

### Known Issues
- Parser module is incomplete
- Logger uses synchronous I/O
- Configuration not dynamically updated
- No error recovery for malformed LSP requests
- `partialResultToken` misused for symbol name

---

## Testing and Development

### Build Commands
```bash
# Using nix
nix-shell
dune build

# Executable location
_build/default/jasmin-lsp/jasmin_lsp.exe
```

### Testing
- **Manual**: Run executable and send JSON-RPC via stdin
- **Script**: `test.sh` uses named pipes for testing
- **IDE**: VSCode extension (Vsjazz) configured to use executable

### Development Tools
- `dev.nix`: Includes `ocaml-lsp` for IDE support
- `dune watch`: Continuous rebuilding (not configured)

---

## Module Dependency Graph

```
jasmin_lsp.ml (Main Entry Point)
    ├── Protocol/RpcProtocol.ml
    │   ├── Protocol/RpcProtocolEvent.ml
    │   ├── Protocol/EventError.ml
    │   ├── Protocol/LspProtocol.ml
    │   │   └── Document/AstIndex.ml
    │   ├── Io/Channel.ml
    │   └── Io/Logger.ml
    ├── Priority.ml
    ├── Config.ml
    │   └── Io/Channel.ml
    └── ArchDef.ml (Not directly used yet)

Parser/parser.ml (Standalone, not integrated)
```

---

## Conclusion

Jasmin-LSP demonstrates a well-architected, layered design with:
- **Clean separation**: I/O, protocol, LSP, analysis layers
- **Asynchronous processing**: Lwt for non-blocking I/O
- **Type safety**: GADTs and Result types
- **Extensibility**: Functor-based architecture
- **Standards compliance**: JSON-RPC 2.0 and LSP 3.x

The project is early-stage but has a solid foundation for incremental feature additions. The priority queue event system is particularly elegant, allowing complex request scheduling without blocking. Future work should focus on completing document synchronization, implementing diagnostics, and expanding symbol resolution beyond local variables.

The architecture's modularity makes it straightforward to add new LSP features while maintaining code quality and testability. The use of OCaml's advanced type system (functors, GADTs, first-class modules) provides strong compile-time guarantees while keeping the code flexible and maintainable.
