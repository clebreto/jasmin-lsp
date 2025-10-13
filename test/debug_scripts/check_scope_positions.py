#!/usr/bin/env python3
"""Check line positions in scope bug test."""

test_content = """export fn first_function(
    #public reg ptr u8[32] sig
) -> #public reg u32
{
    reg u32 status;
    
    status = 0;
    
    return status;
}

export fn second_function(
    #public reg ptr u8[64] data
) -> #public reg u32 {
    reg u32 status;
    
    status = 1;
    status = status;
    
    return status;
}
"""

lines = test_content.split('\n')
for i, line in enumerate(lines):
    if 'status' in line:
        print(f"Line {i}: {repr(line)}")
        for j, char in enumerate(line):
            if j == 0 or (line[j:j+6] == 'status' and (j == 0 or not line[j-1].isalnum())):
                if line[j:j+6] == 'status':
                    print(f"  'status' starts at column {j}")
