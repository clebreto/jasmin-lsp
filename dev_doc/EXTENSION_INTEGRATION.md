# Extension Integration Guide

Quick reference for integrating Jasmin LSP with editor extensions.

## Master File Configuration

### Quick Setup (TypeScript/VSCode Extension)

```typescript
import * as vscode from 'vscode';
import { LanguageClient, NotificationType } from 'vscode-languageclient/node';

// 1. Define the custom notification type
const SetMasterFileNotification = new NotificationType<{ uri: string }>('jasmin/setMasterFile');

// 2. Send master file when configuration changes
vscode.workspace.onDidChangeConfiguration(e => {
  if (e.affectsConfiguration('jasmin-lsp.jasmin-root')) {
    updateMasterFile();
  }
});

function updateMasterFile() {
  const config = vscode.workspace.getConfiguration('jasmin-lsp');
  const masterFile = config.get<string>('jasmin-root');
  
  if (masterFile && client) {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
    const absolutePath = path.resolve(workspaceRoot, masterFile);
    const uri = vscode.Uri.file(absolutePath).toString();
    
    client.sendNotification(SetMasterFileNotification, { uri });
  }
}

// 3. Send on activation and when workspace opens
client.onReady().then(() => {
  updateMasterFile();
});
```

### Configuration Schema (package.json)

```json
{
  "contributes": {
    "configuration": {
      "title": "Jasmin",
      "properties": {
        "jasmin-lsp.jasmin-root": {
          "type": "string",
          "default": "",
          "markdownDescription": "Path to the master Jasmin file (entry point). Use `${workspaceFolder}` for relative paths.",
          "scope": "resource"
        }
      }
    }
  }
}
```

## Custom Notification Spec

### jasmin/setMasterFile

**Direction**: Client → Server  
**Type**: Notification (no response expected)  

**Parameters**:
```typescript
interface SetMasterFileParams {
  uri: string;  // File URI in LSP format (e.g., "file:///path/to/file.jazz")
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

## Alternative: Workspace Configuration

If you prefer using standard LSP configuration mechanism:

```typescript
// Extension should respond to workspace/configuration requests
connection.onInitialized(() => {
  connection.client.register(DidChangeConfigurationNotification.type);
});

// Handle configuration requests
connection.workspace.getConfiguration('jasmin-lsp').then(config => {
  // Server will automatically extract 'jasmin-root' from this response
  return config;
});
```

**Configuration format**:
```json
{
  "jasmin-lsp": {
    "jasmin-root": "./main.jazz",
    "arch": "x86"
  }
}
```

## Server Logs

Enable logging to verify master file is set:

```bash
# Run LSP server with stderr output
your-lsp-server 2> lsp.log
```

Look for:
```
[LOG] : Setting master file to: file:///path/to/main.jazz
[LOG] : Master file set to: file:///path/to/main.jazz
[LOG] : Using master file for dependency resolution: file:///path/to/main.jazz
```

## Testing

### Manual Test

1. Create test files:
   - `main.jazz` (master)
   - `lib/utils.jinc` (required by main)

2. Configure extension:
   ```json
   {
     "jasmin-lsp.jasmin-root": "${workspaceFolder}/main.jazz"
   }
   ```

3. Open `lib/utils.jinc`
4. Verify "Go to Definition" works for symbols defined in other files
5. Check LSP server logs confirm master file is set

### Automated Test

```typescript
import { expect } from 'chai';

describe('Master File', () => {
  it('should set master file via notification', async () => {
    await client.sendNotification(SetMasterFileNotification, {
      uri: 'file:///test/main.jazz'
    });
    
    // Verify by testing cross-file goto definition
    const definition = await client.sendRequest('textDocument/definition', {
      textDocument: { uri: 'file:///test/lib/utils.jinc' },
      position: { line: 5, character: 10 }
    });
    
    expect(definition).to.exist;
  });
});
```

## Common Issues

### Master file not working
- Check file paths are absolute or properly resolved
- Verify URI format uses `file://` scheme
- Confirm master file exists and parses correctly

### Symbols not found
- Ensure master file `require`s the necessary files
- Check require paths are relative to master file location
- Verify all required files exist and are syntactically valid

### Configuration not loading
- Implement `workspace/configuration` response handler
- Check configuration key matches: `jasmin-lsp.jasmin-root`
- Verify JSON format is correct

## Complete Example

See `examples/vscode-extension/` for a full working example of a VSCode extension with master file support.

## Questions?

See [MASTER_FILE_FEATURE.md](MASTER_FILE_FEATURE.md) for detailed documentation.
