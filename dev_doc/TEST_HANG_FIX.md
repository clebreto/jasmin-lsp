# Fix for Test Hanging Issue

## Problem

The test suite was hanging at 11% when running `test_crash/test_multi_file_crash.py::test_multi_file_project`.

## Root Cause

The hang wasn't actually in `test_multi_file_project` - that test was passing fine. The issue was in the **next test** that ran after it: `test_server_survives_invalid_json` in `test_crash/test_robustness.py`.

### The Bug

In `test_server_survives_invalid_json`, line 17 had:

```python
client.process.stdin.write(b"Content-Length: 20\r\n\r\n{invalid json here}")
```

The problem:
- The Content-Length header claimed the message was **20 bytes**
- The actual content `{invalid json here}` is only **18 bytes**
- The LSP server would read the header, then wait indefinitely for 20 bytes
- It only received 18 bytes, so it **blocked forever** waiting for the missing 2 bytes

When the test tried to call `client.initialize()` next, it couldn't proceed because the server was stuck waiting for data, causing the entire test suite to hang.

## Solution

Fixed the test to calculate the correct Content-Length:

```python
# Send invalid JSON with correct Content-Length
invalid_json = b"{invalid json here}"
content_length = len(invalid_json)
client.process.stdin.write(f"Content-Length: {content_length}\r\n\r\n".encode('utf-8'))
client.process.stdin.write(invalid_json)
client.process.stdin.flush()
```

Now:
- Content-Length is calculated dynamically: **18 bytes**
- Exactly 18 bytes are sent
- The server receives all expected data and can process the invalid JSON properly
- The test continues without hanging

## Verification

All 18 crash tests now pass without hanging:

```bash
$ python3 -m pytest test/test_crash/ -v
...
========== 18 passed, 3 warnings in 37.98s ===========
```

## Key Lesson

When working with LSP (or any protocol with Content-Length headers), **always ensure the Content-Length matches the actual content size**. A mismatch will cause the reader to block indefinitely waiting for data that will never arrive.

## Files Modified

- `test/test_crash/test_robustness.py` - Fixed `test_server_survives_invalid_json`
