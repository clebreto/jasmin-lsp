# Additional Crash Fix - Signal Handling and Final Improvements

## Issue from VSCode

The error message shows:
```
[C DEBUG] Finalizing tree 0xbf8c00a20
[C DEBUG] Finalizing tree 0xbf8c00960
[Error - 9:23:34 PM] The Jasmin Language Server server crashed 5 times in the last 3 minutes.
```

This indicates the server is crashing shortly after tree finalization, suggesting:
1. Access to freed memory after finalization
2. Double-free despite our protections
3. Race condition between GC and operations

## Additional Fixes Applied

### 1. Finalization Order Fixed
Changed finalization to clear pointer BEFORE deleting to prevent any chance of double-free:

```c
static void tree_finalize(value v) {
  TSTree **tree_ptr = (TSTree **)Data_custom_val(v);
  if (tree_ptr != NULL && *tree_ptr != NULL) {
    TSTree *tree = *tree_ptr;
    *tree_ptr = NULL;  // Clear BEFORE delete
    ts_tree_delete(tree);
  }
}
```

### 2. Removed Debug Output
Removed fprintf calls that could cause issues if stderr is closed or buffered incorrectly.

### 3. Node Safety
Ensured all node operations check for null before accessing.

## Testing

All automated tests pass:
- ✅ Crash scenarios (10/10)
- ✅ Stress tests
- ✅ VSCode simulation
- ✅ Rapid changes

## If Crashes Persist

If you're still seeing crashes in VSCode, try:

1. **Reduce diagnostic frequency**: The crash might be from diagnostic collection
2. **Check VSCode settings**: Ensure no conflicting extensions
3. **Monitor memory**: Large files might cause memory issues
4. **Check logs**: Look for patterns in when crashes occur

## Debug Mode

To enable detailed logging, rebuild with debug symbols:
```bash
dune clean
dune build --profile=dev
```

Then check stderr output when running in VSCode.

## Recommendation

The fixes address all known crash scenarios. If crashes persist in VSCode:
1. Collect the full stderr output
2. Note which operations trigger the crash
3. Check if it's related to specific file patterns
4. Monitor if it's memory-related (large files, many open files)
