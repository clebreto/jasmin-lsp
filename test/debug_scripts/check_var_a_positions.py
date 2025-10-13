#!/usr/bin/env python3
"""Check the exact line/column for variable 'a'."""

REFERENCES_CODE = """fn helper(reg u64 x) -> reg u64 {
  return x + 1;
}

fn main() {
  reg u64 a;
  reg u64 b;
  a = helper(5);
  b = helper(10);
  return a + b;
}
"""

lines = REFERENCES_CODE.split('\n')
for i, line in enumerate(lines):
    if 'a' in line and 'main' not in line:
        print(f"Line {i}: {repr(line)}")
        for j, char in enumerate(line):
            if char == 'a' and (j == 0 or not line[j-1].isalnum()) and (j+1 >= len(line) or not line[j+1].isalnum()):
                print(f"  'a' at column {j}")
