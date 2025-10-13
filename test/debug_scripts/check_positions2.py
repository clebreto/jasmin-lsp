#!/usr/bin/env python3
"""Check positions for comprehensive test."""

TEST_CODE = """fn test(reg u32 a b, stack u64 x y z) -> reg u32 {
  reg u16 i, j, k;
  stack u8 p, q;
  return a;
}"""

lines = TEST_CODE.split('\n')
for i, line in enumerate(lines):
    print(f"Line {i}: {repr(line)}")
    # Mark all identifier positions
    for j, char in enumerate(line):
        if char.isalpha() or char == '_':
            # Check if it's a single-char identifier or start of identifier
            if (j == 0 or not line[j-1].isalnum()) and (j+1 >= len(line) or not line[j+1].isalnum()):
                print(f"  '{char}' at column {j}")
