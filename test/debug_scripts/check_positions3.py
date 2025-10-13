#!/usr/bin/env python3
"""Check positions for multi param test."""

TEST_CODE = """fn test(reg u32 a, b, stack u64 x, y, z) -> reg u32 {
  return a;
}"""

lines = TEST_CODE.split('\n')
for i, line in enumerate(lines):
    print(f"Line {i}: {repr(line)}")
    # Mark all single-char identifiers
    for j, char in enumerate(line):
        if char in 'abxyz' and (j == 0 or not line[j-1].isalnum()) and (j+1 >= len(line) or not line[j+1].isalnum()):
            print(f"  '{char}' at column {j}")
