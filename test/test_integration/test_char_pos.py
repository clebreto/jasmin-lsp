test_code = """fn test(reg u32 a b, stack u64 x y z) -> reg u32 {
  reg u16 i, j, k;
  stack u8 p, q;
  return a;
}"""

for line_no, line in enumerate(test_code.split('\n')):
    print(f"Line {line_no}: {repr(line)}")
    for i, char in enumerate(line):
        print(f"  [{i:2d}] = {repr(char)}")
    print()
