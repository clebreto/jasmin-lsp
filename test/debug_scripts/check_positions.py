#!/usr/bin/env python3
"""Check positions in test code."""

TEST_CODE = """fn test() {
  reg u32 i, j;
  stack u64 x, y, z;
  i = 1;
  j = 2;
  x = 3;
  y = 4;
  z = 5;
}"""

lines = TEST_CODE.split('\n')
for i, line in enumerate(lines):
    print(f"Line {i}: {repr(line)}")
    for j, char in enumerate(line):
        if char in 'ijxyz' and j > 0 and line[j-1] in ' ,':
            print(f"  '{char}' is at column {j}")
