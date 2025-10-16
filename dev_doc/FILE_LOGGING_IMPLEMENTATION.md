# File Logging Implementation Summary

**Date:** October 16, 2025  
**Feature:** Persistent file logging for LSP server debugging

## Overview

Enhanced the Jasmin LSP server logging system to write logs to both stderr (existing behavior) and persistent log files on disk for easier debugging and analysis.

## Changes Made

### 1. Enhanced Logger Module (`jasmin-lsp/Io/Logger.ml`)

**New Functions:**
- `init_file_logging path` - Initialize file logging with session start marker
- `close_file_logging ()` - Clean shutdown with session end marker
- Enhanced `log str` - Now writes to both stderr and file with timestamps

**Features:**
- Timestamps in `HH:MM:SS` format for each log entry
- Session markers with full date/time stamps
- Graceful error handling (falls back to stderr on file write errors)
- Synchronous I/O with immediate flushing for reliability

### 2. Updated Main Entry Point (`jasmin-lsp/jasmin_lsp.ml`)

**Initialization:**
- Automatically creates log directory `~/.jasmin-lsp/` (or `/tmp/jasmin-lsp/` as fallback)
- Generates timestamped log file names: `jasmin-lsp-YYYYMMDD-HHMMSS.log`
- Sets up `at_exit` handler to cleanly close log file

**Log File Path Logic:**
1. Try `$HOME/.jasmin-lsp/` (primary)
2. Fallback to `/tmp/jasmin-lsp/` (if HOME not available)
3. Create directory if it doesn't exist

### 3. Helper Script (`view-log.sh`)

Convenient log viewing script with multiple modes:
```bash
./view-log.sh           # View in pager (less, starts at end)
./view-log.sh -f        # Follow mode (tail -f)
./view-log.sh -n 50     # Show last N lines
./view-log.sh -g "text" # Search/grep for pattern
```

### 4. Documentation

- **`dev_doc/FILE_LOGGING.md`** - Complete feature documentation
- **`README.md`** - Updated debugging section with new logging info

## Benefits

1. **Persistent History** - Logs survive server restarts
2. **Easy Analysis** - Standard file tools (grep, less, tail, etc.)
3. **Session Tracking** - Clear markers for server start/stop
4. **No Configuration** - Works out of the box
5. **Non-Intrusive** - Stderr output still works for existing workflows

## Log Format Examples

**Session Start:**
```
========== LSP Server Started: 2025-10-16 11:46:32 ==========
[LOG 11:46:32] : jasmin-lsp language server (Lwt loop) started
[LOG 11:46:32] : Log file: /Users/user/.jasmin-lsp/jasmin-lsp-20251016-114632.log
```

**Regular Log Entry:**
```
[LOG 11:46:45] : Received RPC packet: {"method":"initialize","id":1}
[LOG 11:46:45] : Server initialized
```

**Session End:**
```
========== LSP Server Stopped: 2025-10-16 12:30:15 ==========
```

## Usage Examples

### Real-time Monitoring
```bash
# Watch logs as they happen
./view-log.sh -f
```

### Debugging Specific Issues
```bash
# Find all errors
./view-log.sh -g "Error"

# Find all definition requests
./view-log.sh -g "Definition request"

# Find diagnostics events
./view-log.sh -g "diagnostics"
```

### Historical Analysis
```bash
# View last 100 lines
./view-log.sh -n 100

# Search across all log files
grep "crash" ~/.jasmin-lsp/*.log

# Find recent logs
ls -lt ~/.jasmin-lsp/
```

## Implementation Notes

### Thread Safety
- Uses synchronous I/O to avoid race conditions
- Flushes after every write to ensure data is persisted

### Error Handling
- File write failures are logged to stderr
- Server continues operating even if file logging fails
- Graceful degradation to stderr-only mode

### Performance
- Minimal overhead (synchronous file I/O)
- No buffering issues due to immediate flushing
- Log file handle reused across all log calls

### Memory Management
- Log file handle stored in module-level ref cell
- Properly closed via `at_exit` handler
- No memory leaks or resource exhaustion

## Future Enhancements

Possible improvements for future versions:
1. Configuration option to disable file logging
2. Custom log directory path via environment variable
3. Log rotation with size/count limits
4. Different log levels (DEBUG, INFO, WARN, ERROR)
5. Structured logging (JSON format)
6. Log file compression for old logs
7. Integration with system logging (syslog)

## Testing

### Manual Test
1. Start the LSP server
2. Check that log file is created in `~/.jasmin-lsp/`
3. Perform LSP operations (open file, hover, etc.)
4. Verify log entries appear in both stderr and file
5. Stop the server
6. Verify session end marker is written

### Verification Commands
```bash
# Check log file was created
ls -lth ~/.jasmin-lsp/jasmin-lsp-*.log | head -1

# Verify both session markers
grep "========" ~/.jasmin-lsp/jasmin-lsp-*.log | tail -2

# Count log entries
grep "^\[LOG" ~/.jasmin-lsp/jasmin-lsp-*.log | wc -l
```

## Compatibility

- **macOS**: ✅ Tested
- **Linux**: ✅ Should work (uses standard HOME env var)
- **Windows**: ⚠️ May need path adjustments (uses Unix paths)

## Related Files

- `jasmin-lsp/Io/Logger.ml` - Core logging implementation
- `jasmin-lsp/jasmin_lsp.ml` - Initialization code
- `view-log.sh` - Helper script
- `dev_doc/FILE_LOGGING.md` - User documentation
- `README.md` - Updated debugging section
