# Master File Implementation Summary

## Overview

Successfully implemented master file support for the Jasmin LSP server. This feature enables proper symbol resolution by tracking the compilation entry point and traversing dependencies from there.

## Changes Made

### 1. Server State (`jasmin-lsp/ServerState.ml`)

**Added**:
- `master_file: Lsp.Types.DocumentUri.t option ref` field to track the master file
- `get_master_file` function to retrieve the current master file
- `set_master_file` function to set the master file with logging

**Purpose**: Centralized storage of the master file URI that persists throughout the server session.

### 2. Protocol Layer (`jasmin-lsp/Protocol/LspProtocol.ml`)

**Added**:
- `receive_set_master_file_notification` function to handle custom notification
- Exported the function in `LspProtocol.mli`

**Modified**:
- `get_all_relevant_files` function to:
  - Check if master file is set
  - If set: traverse dependencies starting from master file
  - If not set: fallback to old behavior (all open files)
  - Always include the current file being analyzed
  - Log which strategy is being used

**Purpose**: Core logic for using the master file in symbol resolution operations.

### 3. RPC Protocol Layer (`jasmin-lsp/Protocol/RpcProtocol.ml`)

**Modified**:
- `receive_rpc_notification` function to:
  - Intercept custom `jasmin/setMasterFile` notifications
  - Parse URI from notification parameters
  - Call handler before standard LSP notification processing
  
- `receive_rpc_response` function to:
  - Detect responses to `workspace/configuration` requests
  - Extract `jasmin-root` from configuration
  - Convert path to URI and set as master file
  - Handle parsing errors gracefully

**Purpose**: Bridge between JSON-RPC messages and LSP protocol handlers.

## How It Works

### Setting Master File

#### Method 1: Custom Notification (Direct)

```
Extension → Server: jasmin/setMasterFile notification
  {
    "method": "jasmin/setMasterFile",
    "params": { "uri": "file:///path/to/main.jazz" }
  }

Server: 
  1. RpcProtocol intercepts notification
  2. Extracts URI from params
  3. Calls receive_set_master_file_notification
  4. ServerState.set_master_file updates state
  5. Logs "Master file set to: ..."
```

#### Method 2: Workspace Configuration (Automatic)

```
Extension → Server: initialize request

Server → Extension: workspace/configuration request
  {
    "id": max_int,
    "method": "workspace/configuration",
    "params": { "items": [{ "section": "jasmin-lsp" }] }
  }

Extension → Server: configuration response
  {
    "id": max_int,
    "result": [{ "jasmin-root": "./main.jazz", "arch": "x86" }]
  }

Server:
  1. RpcProtocol.receive_rpc_response detects conf_request_id
  2. Extracts "jasmin-root" from response
  3. Converts path to URI
  4. Calls receive_set_master_file_notification
  5. ServerState.set_master_file updates state
```

### Using Master File for Symbol Resolution

When any LSP operation needs symbols (goto definition, hover, references):

```ocaml
let get_all_relevant_files uri =
  match ServerState.get_master_file (!server_state) with
  | Some master_uri ->
      (* Start dependency traversal from master file *)
      let all_files = collect_required_files_recursive master_uri [] in
      (* Include current file if not in tree *)
      if List.mem uri all_files then all_files else uri :: all_files
      
  | None ->
      (* Fallback: use all open files *)
      let open_files = DocumentStore.get_all_uris ... in
      (* ... existing logic ... *)
```

**Benefit**: Only files reachable from the master file are searched, matching actual compilation behavior.

## API Specification

### Custom Notification: jasmin/setMasterFile

**Direction**: Client → Server  
**Type**: Notification (no response)  

**Parameters**:
```typescript
interface SetMasterFileParams {
  uri: string;  // LSP URI format (file://...)
}
```

**Example**:
```json
{
  "jsonrpc": "2.0",
  "method": "jasmin/setMasterFile",
  "params": {
    "uri": "file:///home/user/project/main.jazz"
  }
}
```

### Configuration Schema

**Section**: `jasmin-lsp`  
**Fields**:
- `jasmin-root` (string): Path to master file (relative or absolute)
- `arch` (string): Target architecture

**Example**:
```json
{
  "jasmin-lsp": {
    "jasmin-root": "./main.jazz",
    "arch": "x86"
  }
}
```

## Benefits

### Before (No Master File)

- Symbol resolution searched all open files
- Could find symbols from unrelated files
- No concept of compilation entry point
- Potentially slower (more files to search)
- Behavior didn't match compiler

### After (With Master File)

✅ Only searches files reachable from master file  
✅ Matches actual Jasmin compilation behavior  
✅ Faster (fewer files to search)  
✅ More accurate symbol resolution  
✅ Proper handling of require dependencies  
✅ Graceful fallback if no master file set  

## Extension Integration

Extensions should implement one or both methods:

### Method 1: Configuration (Recommended)

```typescript
// In package.json
{
  "contributes": {
    "configuration": {
      "properties": {
        "jasmin-lsp.jasmin-root": {
          "type": "string",
          "description": "Path to master Jasmin file"
        }
      }
    }
  }
}

// In extension code
connection.workspace.getConfiguration('jasmin-lsp').then(config => {
  // Server automatically extracts jasmin-root
});
```

### Method 2: Custom Notification

```typescript
const SetMasterFileNotification = 
  new NotificationType<{ uri: string }>('jasmin/setMasterFile');

async function setMasterFile(path: string) {
  const uri = vscode.Uri.file(path).toString();
  await client.sendNotification(SetMasterFileNotification, { uri });
}
```

## Testing

### Manual Testing

1. Build the server: `dune build`
2. Create test files with requires
3. Set master file via notification or config
4. Verify symbol resolution works across files
5. Check logs for "Master file set to: ..." message

### Automated Testing

See `test_master_file.py` for a basic test that:
- Starts the LSP server
- Sends initialize request
- Sends jasmin/setMasterFile notification
- Verifies the master file is set (via logs)

## Logging

The server logs master file operations:

```
[LOG] : Received jasmin/setMasterFile notification
[LOG] : Setting master file to: file:///path/to/main.jazz
[LOG] : Master file set to: file:///path/to/main.jazz
[LOG] : Using master file for dependency resolution: file:///path/to/main.jazz
[LOG] : Total files from master file: 5
```

Or if no master file:

```
[LOG] : No master file set, using all open files as entry points
[LOG] : Starting with 3 open files
[LOG] : Total files including dependencies: 8
```

## Future Enhancements

1. **Master File Validation**: Verify file exists and parses correctly
2. **Multiple Master Files**: Support projects with multiple entry points
3. **Auto-Detection**: Automatically detect master file from project structure
4. **Change Notifications**: Re-index when master file changes
5. **Status Bar**: Show master file in IDE status bar
6. **Quick Picker**: UI for selecting/changing master file

## Files Modified

- `jasmin-lsp/ServerState.ml` - Added master file storage
- `jasmin-lsp/Protocol/LspProtocol.ml` - Added handler and modified symbol resolution
- `jasmin-lsp/Protocol/LspProtocol.mli` - Exported new function
- `jasmin-lsp/Protocol/RpcProtocol.ml` - Added custom notification and config handling

## Documentation Created

- `MASTER_FILE_FEATURE.md` - Comprehensive feature documentation
- `EXTENSION_INTEGRATION.md` - Quick reference for extension developers
- `test_master_file.py` - Basic functionality test
- Updated `README.md` with master file information

## Conclusion

The master file feature is fully implemented and ready for use. Extension developers can integrate it using either workspace configuration (automatic) or custom notifications (explicit). The feature provides accurate symbol resolution that matches Jasmin's compilation model while maintaining backward compatibility through graceful fallback.

---

**Implementation Date**: October 11, 2025  
**Status**: ✅ Complete and tested  
**Build**: ✅ Compiles successfully with `dune build`
