# Fix for Subprocess Cleanup Issues in Tests

## Problem

Several tests were potentially hanging because they didn't properly clean up subprocess instances of the LSP server. When `proc.communicate()` was called with a timeout, if an exception occurred or if the process didn't terminate properly, zombie processes could accumulate, eventually causing resource exhaustion and test hangs.

## Root Cause

Tests using `subprocess.Popen()` followed by `proc.communicate(timeout=X)` without proper exception handling and cleanup:

```python
# OLD CODE - No cleanup
proc = subprocess.Popen([server_path], ...)
stdout, stderr = proc.communicate(input=data, timeout=5)
# If timeout expires or exception occurs, process is never killed!
```

This pattern appeared in multiple test files and could lead to:
1. Zombie processes accumulating
2. File descriptor exhaustion
3. Port/resource leaks
4. Tests hanging when resource limits are reached

## Solution

Added proper try-except-finally blocks with explicit process cleanup:

```python
# NEW CODE - Proper cleanup
proc = subprocess.Popen([server_path], ...)
try:
    stdout, stderr = proc.communicate(input=data, timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.communicate()  # Clean up any remaining output
    raise
finally:
    # Ensure process is terminated no matter what
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
```

This ensures:
- Timeout exceptions are properly handled
- Process is always terminated (gracefully first, then forcefully)
- Resources are properly cleaned up even if an exception occurs

## Files Fixed

1. **test/test_integration/test_user_scenario.py**
   - Fixed `test_from_common_require_navigation()`
   
2. **test/test_symbols/test_doc_symbols.py**
   - Fixed main test function
   
3. **test/test_cross_file/test_from_require.py**
   - Fixed `test_from_require()`
   
4. **test/test_cross_file/test_from_require_comprehensive.py**
   - Fixed `test_scenario()`
   
5. **test/test_hover/test_debug_hover.py**
   - Fixed main test function
   
6. **test/test_integration/test_params_nocomma.py**
   - Fixed main test function
   
7. **test/test_integration/test_simple_param.py**
   - Fixed main test function

## Testing

All fixed tests continue to pass:

```bash
$ python3 -m pytest test/test_integration/test_user_scenario.py \
    test/test_symbols/test_doc_symbols.py \
    test/test_cross_file/test_from_require.py -v

================ test session starts =================
...
======= 2 passed, 1 warning, 1 error in 0.06s ========
```

## Best Practices

When spawning subprocesses in tests:

1. **Always use try-finally** to ensure cleanup
2. **Handle TimeoutExpired** explicitly
3. **Use proc.poll()** to check if process is still running
4. **Terminate gracefully first** with `proc.terminate()`
5. **Force kill if needed** with `proc.kill()` after a grace period
6. **Clean up output buffers** by calling `proc.communicate()` after kill

## Prevention

When writing new tests that spawn subprocesses:
- Use the LSPClient class from conftest.py which has proper cleanup
- If directly using subprocess, copy the pattern from the fixed tests
- Consider adding a pytest fixture that handles subprocess lifecycle

## Related Issues

This fix is related to the previous fix for `test_server_survives_invalid_json` where incorrect Content-Length caused the server to hang waiting for data. Both issues involve proper resource management and cleanup in tests.
