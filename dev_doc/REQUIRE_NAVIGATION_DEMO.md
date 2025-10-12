# Quick Demo: Require File Navigation

## What You Can Do Now

In your Jasmin code, when you have:

```jasmin
require "crypto/aes.jazz"
require "utils/math.jazz"
```

You can now **click on the filename** to jump directly to that file!

## How to Use

### Method 1: Ctrl+Click (Cmd+Click on Mac)
1. Hold Ctrl (or Cmd on Mac)
2. Click on `"crypto/aes.jazz"` 
3. The file opens instantly!

### Method 2: Right-Click Menu
1. Right-click on the filename in the require statement
2. Select "Go to Definition"
3. File opens!

### Method 3: Keyboard Shortcut
1. Place cursor on the filename
2. Press **F12** (Windows/Linux) or **Cmd+F12** (Mac)
3. File opens!

### Method 4: Peek Definition
1. Place cursor on the filename
2. Press **Alt+F12** (Windows/Linux) or **Option+F12** (Mac)
3. File content appears inline without leaving your current file!

## Example Workflow

```jasmin
// main.jazz
require "crypto/sha256.jazz"
require "utils/arrays.jazz"

export fn compute_hash(reg u64[8] data) -> reg u64[4] {
  reg u64[4] hash;
  
  // Want to see how sha256_block works?
  // Just Ctrl+Click on "crypto/sha256.jazz" above!
  hash = sha256_block(data);
  
  return hash;
}
```

**Before this feature:**
1. See `require "crypto/sha256.jazz"`
2. Manually navigate file tree to find crypto/sha256.jazz
3. Open it manually

**After this feature:**
1. See `require "crypto/sha256.jazz"`
2. Ctrl+Click on the filename
3. Done! ✨

## What Files You Can Navigate To

- ✅ Relative paths: `require "lib.jazz"`
- ✅ Subdirectories: `require "crypto/aes.jazz"`
- ✅ Parent directories: `require "../common/util.jazz"`
- ✅ Multiple requires: Each filename is clickable
- ✅ Namespaced requires: `from CRYPTO require "aes.jazz"`

## Real-World Example

### Project Structure
```
my-jasmin-project/
├── main.jazz
├── crypto/
│   ├── aes.jazz
│   ├── sha256.jazz
│   └── common.jazz
└── utils/
    ├── arrays.jazz
    └── math.jazz
```

### main.jazz
```jasmin
require "crypto/aes.jazz"
require "crypto/sha256.jazz"
require "utils/arrays.jazz"

export fn encrypt_and_hash(
  reg u64[16] plaintext,
  reg u64[4] key
) -> reg u64[4] {
  reg u64[16] ciphertext;
  reg u64[4] hash;
  
  // Click "crypto/aes.jazz" to see AES implementation
  ciphertext = aes_encrypt(plaintext, key);
  
  // Click "crypto/sha256.jazz" to see SHA256 implementation  
  hash = sha256(ciphertext);
  
  return hash;
}
```

Now you can explore the entire codebase just by clicking on require statements!

## Tips & Tricks

### 1. Quick Library Inspection
When using a function from a library:
```jasmin
require "math_lib.jazz"

fn use_math() {
  reg u64 x;
  x = square(#10);  // What does square do?
  // Just Ctrl+Click on "math_lib.jazz" above to check!
}
```

### 2. Navigate Through Dependency Chain
```jasmin
// main.jazz
require "crypto.jazz"  // Click to open crypto.jazz

// crypto.jazz (after clicking)
require "primitives.jazz"  // Click to see low-level crypto

// primitives.jazz (after clicking)
// Now you're at the lowest level!
```

### 3. Verify File Paths
Not sure if your require path is correct? 
- Try to navigate to it with Ctrl+Click
- If it works, the path is correct!
- If it doesn't work, check the file path

### 4. Combine with Symbol Navigation
1. Ctrl+Click on `"math_lib.jazz"` to open the file
2. Then use Ctrl+F to find a specific function
3. Or use Ctrl+Shift+O to see outline of all symbols

## Error Messages

### "Required file not found"
- The file doesn't exist at the specified path
- Check the path is relative to your current file
- Verify the filename spelling

### Example:
```jasmin
require "typo_lib.jazz"  // File doesn't exist
//       ^^^^^^^^^^^^^^
//       Ctrl+Click here shows: "Required file not found"
```

## IDE Comparison

This feature brings Jasmin LSP on par with other languages:

| Language | Include Syntax | Can Navigate? |
|----------|---------------|---------------|
| C/C++ | `#include "file.h"` | ✅ Yes |
| Python | `import module` | ✅ Yes |
| TypeScript | `import './file'` | ✅ Yes |
| Rust | `mod file;` | ✅ Yes |
| Go | `import "package"` | ✅ Yes |
| **Jasmin** | `require "file.jazz"` | ✅ **YES!** |

## Testing It Out

Want to try it right now?

1. Open `test/fixtures/main_program.jazz` in VS Code
2. Look at line 4: `require "math_lib.jazz"`
3. Ctrl+Click on `"math_lib.jazz"`
4. Watch it open `math_lib.jazz`! 🎉

## Video Demo (Imagined)

```
[00:00] Opening main_program.jazz
[00:03] Hovering over "math_lib.jazz" - Ctrl key shows it's clickable
[00:05] Ctrl+Click on the filename
[00:06] BOOM! math_lib.jazz opens
[00:08] Reading the square() function implementation
[00:12] Going back to main_program.jazz (Ctrl+Tab)
[00:14] Seamless navigation! ✨
```

## Feedback

Love this feature? Have ideas for improvements?
- File an issue on GitHub
- Suggest enhancements
- Report any bugs

This is just the beginning - imagine all the navigation improvements we can build on top of this foundation!

---

**Implemented:** October 10, 2025  
**Status:** ✅ Fully Working  
**Test Status:** ✅ All Tests Passing
