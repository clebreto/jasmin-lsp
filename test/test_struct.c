#include <stdio.h>
#include <tree_sitter/api.h>
#include <stdint.h>

extern const TSLanguage *tree_sitter_jasmin(void);

// Try to access the TSLanguage struct directly
// The struct should have .abi_version as first field

int main() {
    const TSLanguage *lang = tree_sitter_jasmin();
    printf("Language pointer: %p\n", (void*)lang);
    
    // Try to read the first uint32_t (should be abi_version)
    const uint32_t *ptr = (const uint32_t *)lang;
    printf("First uint32_t at offset 0: %u (0x%08X)\n", ptr[0], ptr[0]);
    printf("Second uint32_t at offset 4: %u (0x%08X)\n", ptr[1], ptr[1]);
    printf("Third uint32_t at offset 8: %u (0x%08X)\n", ptr[2], ptr[2]);
    
    // What does the API function say?
    uint32_t reported_version = ts_language_abi_version(lang);
    printf("\nts_language_abi_version() returns: %u (0x%08X)\n", reported_version, reported_version);
    printf("Expected: %u\n", TREE_SITTER_LANGUAGE_VERSION);
    
    // Try to see what the struct looks like
    printf("\nMemory dump of first 64 bytes:\n");
    const unsigned char *bytes = (const unsigned char *)lang;
    for (int i = 0; i < 64; i++) {
        printf("%02X ", bytes[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }
    
    return 0;
}
