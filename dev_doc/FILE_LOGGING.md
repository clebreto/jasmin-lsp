# File Logging Feature

## Overview

The Jasmin LSP server now writes logs to both stderr (as before) and to a persistent log file for easier debugging and analysis.

## Log File Location

Log files are automatically created in:
- **macOS/Linux**: `~/.jasmin-lsp/jasmin-lsp-YYYYMMDD-HHMMSS.log`
- **Fallback**: `/tmp/jasmin-lsp/jasmin-lsp-YYYYMMDD-HHMMSS.log`

Each time the LSP server starts, it creates a new log file with a timestamp in the filename.

## Log Format

Each log entry includes:
- Timestamp in `HH:MM:SS` format
- The log message

Example:
```
[LOG 14:23:45] : jasmin-lsp language server (Lwt loop) started
[LOG 14:23:45] : Log file: /Users/username/.jasmin-lsp/jasmin-lsp-20251016-142345.log
[LOG 14:23:46] : Server initialized
```

## Session Markers

Each log file includes session markers:
- **Start**: `========== LSP Server Started: YYYY-MM-DD HH:MM:SS ==========`
- **Stop**: `========== LSP Server Stopped: YYYY-MM-DD HH:MM:SS ==========`

These markers help identify multiple server restarts in the same log file.

## Benefits

1. **Persistent Logs**: Logs are saved to disk and survive server restarts
2. **Easy Analysis**: Log files can be searched, filtered, and analyzed with standard tools
3. **Debugging**: Easier to trace issues across multiple requests/responses
4. **History**: Keep track of server behavior over time

## Viewing Logs

### Tail the current log (real-time monitoring):
```bash
tail -f ~/.jasmin-lsp/jasmin-lsp-*.log
```

### View the most recent log:
```bash
ls -t ~/.jasmin-lsp/jasmin-lsp-*.log | head -1 | xargs less
```

### Search for specific messages:
```bash
grep "Error" ~/.jasmin-lsp/jasmin-lsp-*.log
grep "Definition request" ~/.jasmin-lsp/jasmin-lsp-*.log
```

### Clean up old logs:
```bash
# Remove logs older than 7 days
find ~/.jasmin-lsp -name "jasmin-lsp-*.log" -mtime +7 -delete
```

## Implementation Details

The logging system:
- Uses synchronous I/O to avoid race conditions
- Flushes after each write to ensure messages are saved immediately
- Handles errors gracefully (falls back to stderr-only if file writing fails)
- Automatically closes the log file on server exit

## Configuration

Currently, file logging is always enabled and cannot be disabled. The log directory is automatically determined based on the environment.

Future enhancements could include:
- Configuration option to disable file logging
- Custom log directory path
- Log rotation/size limits
- Different log levels (debug, info, warning, error)
