#include <stdio.h>
#include <string.h>
#include <tree_sitter/api.h>

extern const TSLanguage *tree_sitter_jasmin(void);

int main() {
    printf("Creating parser...\n");
    TSParser *parser = ts_parser_new();
    if (!parser) {
        fprintf(stderr, "Failed to create parser\n");
        return 1;
    }
    printf("Parser created: %p\n", (void*)parser);
    
    printf("\nGetting Jasmin language...\n");
    const TSLanguage *lang = tree_sitter_jasmin();
    if (!lang) {
        fprintf(stderr, "Failed to get language\n");
        return 1;
    }
    printf("Language pointer: %p\n", (void*)lang);
    
    printf("\nChecking ABI versions:\n");
    uint32_t lang_version = ts_language_abi_version(lang);
    printf("Language ABI version: %u\n", lang_version);
    printf("Expected ABI version: %u (TREE_SITTER_LANGUAGE_VERSION)\n", TREE_SITTER_LANGUAGE_VERSION);
    
    if (lang_version != TREE_SITTER_LANGUAGE_VERSION) {
        fprintf(stderr, "ERROR: ABI version mismatch!\n");
        fprintf(stderr, "  Language reports: %u\n", lang_version);
        fprintf(stderr, "  Library expects: %u\n", TREE_SITTER_LANGUAGE_VERSION);
        return 1;
    }
    
    printf("\nSetting language on parser...\n");
    bool success = ts_parser_set_language(parser, lang);
    printf("Set language result: %d\n", success);
    
    if (!success) {
        fprintf(stderr, "ERROR: Failed to set language!\n");
        return 1;
    }
    
    printf("\nParsing test code...\n");
    const char *source = "fn test() -> reg u64 { reg u64 x; return x; }";
    TSTree *tree = ts_parser_parse_string(parser, NULL, source, strlen(source));
    
    if (!tree) {
        fprintf(stderr, "ERROR: Parser returned NULL!\n");
        return 1;
    }
    
    printf("Parse succeeded! Tree: %p\n", (void*)tree);
    
    TSNode root = ts_tree_root_node(tree);
    const char *type = ts_node_type(root);
    printf("Root node type: %s\n", type);
    printf("Root has error: %d\n", ts_node_has_error(root));
    
    // Cleanup
    ts_tree_delete(tree);
    ts_parser_delete(parser);
    
    printf("\n✅ All tests passed!\n");
    return 0;
}
