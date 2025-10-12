# Example: VSCode Extension Integration

This example shows how to integrate the master file feature in a VSCode extension for Jasmin.

## package.json Configuration

```json
{
  "name": "jasmin-vscode",
  "displayName": "Jasmin Language Support",
  "contributes": {
    "configuration": {
      "title": "Jasmin",
      "properties": {
        "jasmin.lsp.path": {
          "type": "string",
          "default": "",
          "description": "Path to jasmin-lsp executable"
        },
        "jasmin-lsp.jasmin-root": {
          "type": "string",
          "default": "",
          "markdownDescription": "Path to the master Jasmin file (compilation entry point). Supports `${workspaceFolder}` variable.",
          "scope": "resource"
        },
        "jasmin-lsp.arch": {
          "type": "string",
          "default": "x86",
          "enum": ["x86", "arm"],
          "description": "Target architecture"
        }
      }
    },
    "commands": [
      {
        "command": "jasmin.setMasterFile",
        "title": "Jasmin: Set Master File"
      }
    ]
  }
}
```

## Extension Code (extension.ts)

```typescript
import * as vscode from 'vscode';
import * as path from 'path';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  NotificationType
} from 'vscode-languageclient/node';

// Define the custom notification type
const SetMasterFileNotification = new NotificationType<{ uri: string }>('jasmin/setMasterFile');

let client: LanguageClient | undefined;

export function activate(context: vscode.ExtensionContext) {
  // Start the LSP client
  startLanguageServer(context);

  // Register command to manually set master file
  context.subscriptions.push(
    vscode.commands.registerCommand('jasmin.setMasterFile', async () => {
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
      if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
      }

      // Show file picker for .jazz files
      const fileUri = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        canSelectMany: false,
        filters: {
          'Jasmin Files': ['jazz']
        },
        defaultUri: workspaceFolder.uri
      });

      if (fileUri && fileUri[0]) {
        await setMasterFile(fileUri[0].toString());
        vscode.window.showInformationMessage(`Master file set to: ${fileUri[0].fsPath}`);
      }
    })
  );

  // Watch for configuration changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(e => {
      if (e.affectsConfiguration('jasmin-lsp.jasmin-root')) {
        updateMasterFileFromConfig();
      }
    })
  );
}

function startLanguageServer(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration('jasmin');
  const lspPath = config.get<string>('lsp.path');

  if (!lspPath) {
    vscode.window.showErrorMessage('Please configure jasmin.lsp.path in settings');
    return;
  }

  const serverOptions: ServerOptions = {
    command: lspPath,
    args: []
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: 'file', language: 'jasmin' }
    ],
    synchronize: {
      // Notify server about configuration changes
      configurationSection: 'jasmin-lsp'
    }
  };

  client = new LanguageClient(
    'jasmin-lsp',
    'Jasmin Language Server',
    serverOptions,
    clientOptions
  );

  client.start().then(() => {
    console.log('Jasmin LSP client started');
    
    // Set master file from configuration once server is ready
    updateMasterFileFromConfig();
  });

  context.subscriptions.push(client);
}

async function updateMasterFileFromConfig() {
  if (!client) return;

  const config = vscode.workspace.getConfiguration('jasmin-lsp');
  const masterFile = config.get<string>('jasmin-root');

  if (masterFile) {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
      // Resolve relative paths and variables
      let resolvedPath = masterFile.replace('${workspaceFolder}', workspaceFolder.uri.fsPath);
      
      if (!path.isAbsolute(resolvedPath)) {
        resolvedPath = path.resolve(workspaceFolder.uri.fsPath, resolvedPath);
      }

      const uri = vscode.Uri.file(resolvedPath).toString();
      await setMasterFile(uri);
    }
  }
}

async function setMasterFile(uri: string) {
  if (!client) return;

  try {
    await client.sendNotification(SetMasterFileNotification, { uri });
    console.log(`Master file set to: ${uri}`);
  } catch (error) {
    console.error('Failed to set master file:', error);
    vscode.window.showErrorMessage(`Failed to set master file: ${error}`);
  }
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
```

## User Settings (.vscode/settings.json)

```json
{
  "jasmin.lsp.path": "/path/to/jasmin-lsp/_build/default/jasmin-lsp/jasmin_lsp.exe",
  "jasmin-lsp.jasmin-root": "${workspaceFolder}/src/main.jazz",
  "jasmin-lsp.arch": "x86"
}
```

## Workspace Settings (for a specific project)

```json
{
  "jasmin-lsp": {
    "jasmin-root": "./main.jazz",
    "arch": "x86"
  }
}
```

## Usage

### Automatic (via Configuration)

1. Open a Jasmin project in VSCode
2. Configure `jasmin-lsp.jasmin-root` in settings
3. The extension automatically sets the master file when:
   - The server starts
   - Configuration changes
   - Workspace is opened

### Manual (via Command)

1. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Jasmin: Set Master File"
3. Select the master .jazz file from the file picker
4. The extension sends the notification to the server

## Testing

### Test Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Extension",
      "type": "extensionHost",
      "request": "launch",
      "runtimeExecutable": "${execPath}",
      "args": [
        "--extensionDevelopmentPath=${workspaceFolder}",
        "${workspaceFolder}/test-workspace"
      ],
      "outFiles": ["${workspaceFolder}/out/**/*.js"]
    }
  ]
}
```

### Test Workspace Structure

```
test-workspace/
  ├── main.jazz           # Master file
  ├── lib/
  │   ├── crypto.jinc
  │   └── utils.jinc
  └── .vscode/
      └── settings.json   # With jasmin-root config
```

### Verification

1. Launch extension in debug mode
2. Open test workspace
3. Check debug console for: "Master file set to: ..."
4. Test goto definition across files
5. Verify only symbols from master file's dependency tree appear

## Advanced: Multi-Root Workspace

For multi-root workspaces, configure per folder:

```json
{
  "folders": [
    {
      "path": "project1",
      "settings": {
        "jasmin-lsp.jasmin-root": "./main.jazz"
      }
    },
    {
      "path": "project2",
      "settings": {
        "jasmin-lsp.jasmin-root": "./app.jazz"
      }
    }
  ]
}
```

## Troubleshooting

### Master file not set

Check:
1. Configuration syntax is correct
2. Path uses forward slashes (even on Windows)
3. `${workspaceFolder}` variable is resolved
4. LSP server is running (check Output panel)

### Relative paths not working

Use absolute paths or `${workspaceFolder}`:
```json
{
  "jasmin-lsp.jasmin-root": "${workspaceFolder}/src/main.jazz"
}
```

### Configuration not updating

Try:
1. Reload window (`Cmd+Shift+P` → "Reload Window")
2. Restart LSP server (`Cmd+Shift+P` → "Restart Language Server")
3. Check LSP server logs for configuration response

## Complete Example Repository

See the full working example at:
- GitHub: [jasmin-vscode-example](https://github.com/jasmin-lang/jasmin-vscode-example)
- Contains: Extension code, test workspace, and usage guide

## Related Documentation

- [MASTER_FILE_FEATURE.md](../MASTER_FILE_FEATURE.md) - Detailed feature documentation
- [EXTENSION_INTEGRATION.md](../EXTENSION_INTEGRATION.md) - Quick integration reference
- [VSCode Extension API](https://code.visualstudio.com/api) - VSCode extension development
