# Master File Feature

## Overview

The Jasmin LSP server now supports the concept of a **master file** (also called "root file" or "entry point"). This is essential for proper symbol resolution in Jasmin programs, which use a dependency system based on `require` directives.

## The Problem

In Jasmin, programs are structured hierarchically:
- A **master file** (e.g., `main.jazz`) is given to the compiler
- This file may `require` other files
- Those files may `require` additional files, forming a dependency tree
- Symbol visibility follows this dependency tree

Without knowing which file is the entry point, the LSP server cannot determine:
- Which symbols are actually available in a given context
- The complete set of dependencies to analyze
- The proper scope for symbol resolution

## The Solution

The LSP server now tracks a master file URI and uses it as the starting point for all symbol resolution operations.

### How It Works

1. **Master File Storage**: The `ServerState` maintains an optional `master_file` URI
2. **Setting the Master File**: Can be done in two ways:
   - **Via configuration**: Automatically loaded from workspace configuration (`jasmin-root` field)
   - **Via custom notification**: The extension sends `jasmin/setMasterFile` notification

3. **Symbol Resolution**: When resolving symbols (goto definition, hover, references):
   - If a master file is set: traverse dependencies starting from the master file
   - If no master file: fallback to using all open files as entry points

### Dependency Traversal

```
Master File (e.g., main.jazz)
  │
  ├─ require "crypto/kyber.jinc"
  │    │
  │    ├─ require "common/types.jinc"
  │    └─ require "common/utils.jinc"
  │
  └─ require "signatures/dilithium.jinc"
       └─ require "common/types.jinc"  (deduplicated)
```

The LSP server:
1. Starts at the master file
2. Recursively follows all `require` statements
3. Collects all reachable files (deduplicating to avoid cycles)
4. Makes symbols from these files available for resolution

## Extension Integration

### Method 1: Workspace Configuration (Recommended)

The extension should configure the workspace settings:

```json
{
  "jasmin-lsp": {
    "jasmin-root": "./src/main.jazz",
    "arch": "x86"
  }
}
```

When the LSP server initializes, it sends a `workspace/configuration` request. The extension responds with the configuration, and the server automatically sets the master file from the `jasmin-root` field.

**Implementation Example (TypeScript):**

```typescript
connection.onInitialized(() => {
  // Register for configuration changes
  connection.client.register(DidChangeConfigurationNotification.type);
});

connection.onDidChangeConfiguration(change => {
  // Update cached configuration
  documentSettings.clear();
});

connection.workspace.onDidChangeConfiguration(params => {
  // Get updated configuration
  connection.workspace.getConfiguration('jasmin-lsp').then(config => {
    if (config['jasmin-root']) {
      // Configuration will be sent automatically when server requests it
    }
  });
});
```

### Method 2: Custom Notification

The extension can explicitly set the master file using a custom notification:

**Notification Format:**
- **Method**: `jasmin/setMasterFile`
- **Params**: `{ "uri": "file:///path/to/master.jazz" }`

**Implementation Example (TypeScript):**

```typescript
import { NotificationType } from 'vscode-languageserver-protocol';

// Define the notification type
const SetMasterFileNotification = new NotificationType<{ uri: string }>('jasmin/setMasterFile');

// Send the notification
async function setMasterFile(fileUri: string) {
  await client.sendNotification(SetMasterFileNotification, { uri: fileUri });
}

// Example: Set master file when workspace is opened
vscode.workspace.onDidOpenTextDocument(document => {
  if (document.languageId === 'jasmin') {
    const config = vscode.workspace.getConfiguration('jasmin-lsp');
    const masterFile = config.get<string>('jasmin-root');
    if (masterFile) {
      const absolutePath = path.resolve(vscode.workspace.rootPath || '', masterFile);
      const uri = vscode.Uri.file(absolutePath).toString();
      setMasterFile(uri);
    }
  }
});
```

### Method 3: Automatic Detection (Future Enhancement)

A future enhancement could automatically detect the master file by:
- Looking for a `.jasmin` or `jasmin.json` project file
- Analyzing which file requires others but is not required itself
- Using heuristics (e.g., files named `main.jazz`)

## Configuration File Format

The `config.json` file (or workspace settings) should specify:

```json
{
  "jasmin-root": "./path/to/master.jazz",
  "arch": "x86"
}
```

Where:
- `jasmin-root`: Path to the master file (relative or absolute)
- `arch`: Target architecture (required for Jasmin compilation)

## Benefits

### With Master File Set

✅ **Accurate symbol resolution**: Only symbols from the master file's dependency tree are visible  
✅ **Proper scope**: Symbols are resolved according to the actual program structure  
✅ **Performance**: Only necessary files are parsed and analyzed  
✅ **Correct diagnostics**: Errors are based on the actual compilation context  

### Without Master File (Fallback)

⚠️ **Best-effort resolution**: Uses all open files as entry points  
⚠️ **May include irrelevant symbols**: Symbols from unrelated files might appear  
⚠️ **Less accurate**: May not match actual compilation behavior  

## Implementation Details

### Server State

```ocaml
type t = {
  document_store: Document.DocumentStore.t;
  prog: (unit, unit) Jasmin.Prog.prog option ref;
  master_file: Lsp.Types.DocumentUri.t option ref;
}
```

### Setting Master File

```ocaml
val set_master_file : t -> Lsp.Types.DocumentUri.t -> unit
```

Logs the operation and stores the master file URI.

### Symbol Resolution

```ocaml
let get_all_relevant_files uri =
  match ServerState.get_master_file (!server_state) with
  | Some master_uri ->
      (* Start from master file *)
      collect_required_files_recursive master_uri []
  | None ->
      (* Fallback: use all open files *)
      (* ... existing logic ... *)
```

### Custom Notification Handler

The RPC protocol layer intercepts `jasmin/setMasterFile` notifications before standard LSP processing:

```ocaml
let receive_rpc_notification (notif : Jsonrpc.Notification.t) =
  let method_name = notif.method_ in
  if method_name = "jasmin/setMasterFile" then
    (* Extract URI from params and set master file *)
    LspProtocol.receive_set_master_file_notification uri
  else
    (* Standard LSP notification *)
    (* ... *)
```

### Configuration Response Handler

When the server receives a response to its `workspace/configuration` request:

```ocaml
let receive_rpc_response (resp : Jsonrpc.Response.t) =
  match resp.id with
  | `Int id when id = Config.conf_request_id ->
      (* Extract jasmin-root from configuration *)
      let root_path = (* parse from response *) in
      let uri = Lsp.Uri.of_path root_path in
      LspProtocol.receive_set_master_file_notification uri
  | _ -> []
```

## Testing

### Manual Testing

1. Create a test project:
   ```
   test_project/
     ├── main.jazz          (master file)
     ├── lib/
     │   ├── crypto.jinc
     │   └── utils.jinc
     └── config.json
   ```

2. Set `config.json`:
   ```json
   {
     "jasmin-root": "./main.jazz",
     "arch": "x86"
   }
   ```

3. Open files in the editor
4. Test goto definition across files
5. Verify only reachable symbols are found

### Automated Testing

```python
# Test setting master file via notification
def test_set_master_file():
    send_notification("jasmin/setMasterFile", {"uri": "file:///test/main.jazz"})
    # Verify symbol resolution uses the master file
    
# Test configuration-based master file
def test_config_master_file():
    send_initialize()
    # Server requests configuration
    respond_to_config({"jasmin-root": "./main.jazz"})
    # Verify master file is set
```

## Future Enhancements

1. **Multiple Master Files**: Support projects with multiple entry points
2. **Master File Auto-Detection**: Intelligent detection of entry points
3. **Project Files**: Support for `.jasmin-project` configuration files
4. **Master File Validation**: Verify master file exists and parses correctly
5. **Master File Change Notification**: Re-index when master file changes
6. **Dependency Graph Visualization**: Show the require dependency tree

## Troubleshooting

### Symbols Not Found

**Problem**: Goto definition doesn't work across files

**Solutions**:
1. Verify master file is set (check LSP server logs)
2. Ensure master file `require`s the needed files
3. Check file paths are correct (relative to master file location)
4. Confirm files are syntactically valid

### Wrong Master File Set

**Problem**: Incorrect master file is being used

**Solutions**:
1. Check workspace configuration (`jasmin-root` setting)
2. Update configuration and restart LSP server
3. Manually send `jasmin/setMasterFile` notification
4. Verify file path is absolute or correctly resolved

### Master File Not Loading

**Problem**: Master file configuration is ignored

**Solutions**:
1. Check LSP server logs for configuration response
2. Verify JSON format in configuration
3. Ensure extension implements `workspace/configuration` handler
4. Try using the custom notification method instead

## Example: VSCode Extension Configuration

### settings.json (User/Workspace)

```json
{
  "jasmin-lsp": {
    "jasmin-root": "${workspaceFolder}/src/main.jazz",
    "arch": "x86"
  }
}
```

### Extension Package Configuration

```json
{
  "contributes": {
    "configuration": {
      "title": "Jasmin LSP",
      "properties": {
        "jasmin-lsp.jasmin-root": {
          "type": "string",
          "default": "",
          "description": "Path to the master Jasmin file (entry point for compilation)"
        },
        "jasmin-lsp.arch": {
          "type": "string",
          "default": "x86",
          "enum": ["x86", "arm"],
          "description": "Target architecture"
        }
      }
    }
  }
}
```

## Conclusion

The master file feature is essential for accurate symbol resolution in Jasmin projects. Extension authors should implement configuration support to automatically provide the master file to the LSP server, ensuring users get the best possible IDE experience.
