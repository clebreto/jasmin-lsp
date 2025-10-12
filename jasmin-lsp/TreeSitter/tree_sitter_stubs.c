#include <stdio.h>
#include <string.h>
#include <tree_sitter/api.h>
#include <caml/mlvalues.h>
#include <caml/memory.h>
#include <caml/alloc.h>
#include <caml/custom.h>
#include <caml/fail.h>

// External declaration for the Jasmin language
extern const TSLanguage *tree_sitter_jasmin(void);

// Custom block operations for tree-sitter objects
#define Val_none Val_int(0)

static inline value Val_some(value v) {
  CAMLparam1(v);
  CAMLlocal1(some);
  some = caml_alloc(1, 0);
  Store_field(some, 0, v);
  CAMLreturn(some);
}

// Parser custom operations
static void parser_finalize(value v) {
  TSParser *parser = (TSParser *)Data_custom_val(v);
  if (parser != NULL) {
    ts_parser_delete(parser);
  }
}

static struct custom_operations parser_ops = {
  "tree_sitter_parser",
  parser_finalize,
  custom_compare_default,
  custom_hash_default,
  custom_serialize_default,
  custom_deserialize_default,
  custom_compare_ext_default,
  custom_fixed_length_default
};

#define Parser_val(v) (*((TSParser **)Data_custom_val(v)))

static value alloc_parser(TSParser *parser) {
  CAMLparam0();
  CAMLlocal1(v);
  v = caml_alloc_custom(&parser_ops, sizeof(TSParser *), 0, 1);
  Parser_val(v) = parser;
  CAMLreturn(v);
}

// Tree custom operations
static void tree_finalize(value v) {
  TSTree **tree_ptr = (TSTree **)Data_custom_val(v);
  if (tree_ptr != NULL && *tree_ptr != NULL) {
    TSTree *tree = *tree_ptr;
    *tree_ptr = NULL;  // Clear the pointer BEFORE deletion to prevent double-free
    ts_tree_delete(tree);
  }
}

static struct custom_operations tree_ops = {
  "tree_sitter_tree",
  tree_finalize,
  custom_compare_default,
  custom_hash_default,
  custom_serialize_default,
  custom_deserialize_default,
  custom_compare_ext_default,
  custom_fixed_length_default
};

#define Tree_val(v) (*((TSTree **)Data_custom_val(v)))

static value alloc_tree(TSTree *tree) {
  CAMLparam0();
  CAMLlocal1(v);
  v = caml_alloc_custom(&tree_ops, sizeof(TSTree *), 0, 1);
  Tree_val(v) = tree;
  CAMLreturn(v);
}

// Node operations (nodes are lightweight, stored by value)
static value alloc_node(TSNode node) {
  CAMLparam0();
  CAMLlocal1(v);
  v = caml_alloc(6, 0);  // 4 context + 1 id + 1 tree pointer
  Store_field(v, 0, caml_copy_int32(node.context[0]));
  Store_field(v, 1, caml_copy_int32(node.context[1]));
  Store_field(v, 2, caml_copy_int32(node.context[2]));
  Store_field(v, 3, caml_copy_int32(node.context[3]));
  Store_field(v, 4, caml_copy_nativeint((intnat)node.id));
  Store_field(v, 5, caml_copy_nativeint((intnat)node.tree));
  CAMLreturn(v);
}

static TSNode node_val(value v) {
  TSNode node;
  node.context[0] = (uint32_t)Int32_val(Field(v, 0));
  node.context[1] = (uint32_t)Int32_val(Field(v, 1));
  node.context[2] = (uint32_t)Int32_val(Field(v, 2));
  node.context[3] = (uint32_t)Int32_val(Field(v, 3));
  node.id = (const void *)Nativeint_val(Field(v, 4));
  node.tree = (const TSTree *)Nativeint_val(Field(v, 5));
  return node;
}

// Point operations
static value alloc_point(TSPoint point) {
  CAMLparam0();
  CAMLlocal1(v);
  v = caml_alloc(2, 0);
  Store_field(v, 0, Val_int(point.row));
  Store_field(v, 1, Val_int(point.column));
  CAMLreturn(v);
}

static TSPoint point_val(value v) {
  TSPoint point;
  point.row = Int_val(Field(v, 0));
  point.column = Int_val(Field(v, 1));
  return point;
}

// Range operations
static value alloc_range(TSNode node) {
  CAMLparam0();
  CAMLlocal1(v);
  v = caml_alloc(4, 0);
  Store_field(v, 0, alloc_point(ts_node_start_point(node)));
  Store_field(v, 1, alloc_point(ts_node_end_point(node)));
  Store_field(v, 2, Val_int(ts_node_start_byte(node)));
  Store_field(v, 3, Val_int(ts_node_end_byte(node)));
  CAMLreturn(v);
}

// Language (just a pointer, no finalization needed)
#define Language_val(v) (*((const TSLanguage **)Data_custom_val(v)))

static struct custom_operations language_ops = {
  "tree_sitter_language",
  custom_finalize_default,
  custom_compare_default,
  custom_hash_default,
  custom_serialize_default,
  custom_deserialize_default,
  custom_compare_ext_default,
  custom_fixed_length_default
};

static value alloc_language(const TSLanguage *lang) {
  CAMLparam0();
  CAMLlocal1(v);
  v = caml_alloc_custom(&language_ops, sizeof(TSLanguage *), 0, 1);
  *((const TSLanguage **)Data_custom_val(v)) = lang;
  CAMLreturn(v);
}

// Stub implementations
CAMLprim value caml_ts_parser_new(value unit) {
  CAMLparam1(unit);
  TSParser *parser = ts_parser_new();
  CAMLreturn(alloc_parser(parser));
}

CAMLprim value caml_ts_parser_delete(value v_parser) {
  CAMLparam1(v_parser);
  TSParser *parser = Parser_val(v_parser);
  ts_parser_delete(parser);
  Parser_val(v_parser) = NULL;
  CAMLreturn(Val_unit);
}

CAMLprim value caml_ts_parser_set_language(value v_parser, value v_language) {
  CAMLparam2(v_parser, v_language);
  TSParser *parser = Parser_val(v_parser);
  const TSLanguage *language = Language_val(v_language);
  fprintf(stderr, "[C DEBUG] Setting language %p on parser %p\n", (void*)language, (void*)parser);
  fprintf(stderr, "[C DEBUG] Language ABI version: %u\n", ts_language_abi_version(language));
  fprintf(stderr, "[C DEBUG] Expected ABI version: %u\n", TREE_SITTER_LANGUAGE_VERSION);
  bool success = ts_parser_set_language(parser, language);
  fprintf(stderr, "[C DEBUG] Set language result: %d\n", success);
  if (!success) {
    fprintf(stderr, "[C DEBUG] ERROR: Failed to set language! ABI version mismatch?\n");
  }
  CAMLreturn(Val_unit);
}

CAMLprim value caml_ts_language_jasmin(value unit) {
  CAMLparam1(unit);
  fprintf(stderr, "[C DEBUG] Getting Jasmin language\n");
  const TSLanguage *lang = tree_sitter_jasmin();
  fprintf(stderr, "[C DEBUG] Jasmin language pointer: %p\n", (void*)lang);
  CAMLreturn(alloc_language(lang));
}

CAMLprim value caml_ts_parser_parse_string(value v_parser, value v_string) {
  CAMLparam2(v_parser, v_string);
  CAMLlocal1(v_result);
  
  TSParser *parser = Parser_val(v_parser);
  const char *source = String_val(v_string);
  uint32_t length = caml_string_length(v_string);
  
  TSTree *tree = ts_parser_parse_string(parser, NULL, source, length);
  
  if (tree == NULL) {
    CAMLreturn(Val_none);
  }
  
  v_result = Val_some(alloc_tree(tree));
  CAMLreturn(v_result);
}

CAMLprim value caml_ts_parser_parse_string_with_tree(value v_parser, value v_old_tree, value v_string) {
  CAMLparam3(v_parser, v_old_tree, v_string);
  CAMLlocal1(v_result);
  
  TSParser *parser = Parser_val(v_parser);
  const char *source = String_val(v_string);
  uint32_t length = caml_string_length(v_string);
  
  fprintf(stderr, "[C DEBUG] Parsing %d bytes\n", length);
  
  TSTree *old_tree = NULL;
  if (Is_block(v_old_tree)) {
    old_tree = Tree_val(Field(v_old_tree, 0));
    fprintf(stderr, "[C DEBUG] Using old tree\n");
  }
  
  TSTree *tree = ts_parser_parse_string(parser, old_tree, source, length);
  
  if (tree == NULL) {
    fprintf(stderr, "[C DEBUG] Parser returned NULL!\n");
    CAMLreturn(Val_none);
  }
  
  fprintf(stderr, "[C DEBUG] Parser succeeded, creating OCaml value\n");
  v_result = Val_some(alloc_tree(tree));
  CAMLreturn(v_result);
}

CAMLprim value caml_ts_tree_root_node(value v_tree) {
  CAMLparam1(v_tree);
  TSTree *tree = Tree_val(v_tree);
  if (tree == NULL) {
    fprintf(stderr, "[C DEBUG] ERROR: tree_root_node called on NULL tree!\n");
    fflush(stderr);
    caml_failwith("tree_root_node: NULL tree");
  }
  TSNode root = ts_tree_root_node(tree);
  CAMLreturn(alloc_node(root));
}

CAMLprim value caml_ts_tree_delete(value v_tree) {
  CAMLparam1(v_tree);
  TSTree *tree = Tree_val(v_tree);
  if (tree != NULL) {
    fprintf(stderr, "[C DEBUG] Manually deleting tree %p\n", (void*)tree);
    fflush(stderr);
    ts_tree_delete(tree);
    Tree_val(v_tree) = NULL;
  }
  CAMLreturn(Val_unit);
}

CAMLprim value caml_ts_tree_copy(value v_tree) {
  CAMLparam1(v_tree);
  TSTree *tree = Tree_val(v_tree);
  TSTree *copy = ts_tree_copy(tree);
  CAMLreturn(alloc_tree(copy));
}

CAMLprim value caml_ts_node_type(value v_node) {
  CAMLparam1(v_node);
  
  // Wrap in error handling
  const char *result = "error";
  
  // Check if node is null before accessing
  TSNode node = node_val(v_node);
  if (ts_node_is_null(node)) {
    fprintf(stderr, "[C DEBUG] node_type: node is null!\n");
    fflush(stderr);
    CAMLreturn(caml_copy_string("null"));
  }
  
  // Try to get node type - this might crash if tree was freed
  const char *type = ts_node_type(node);
  if (type == NULL) {
    fprintf(stderr, "[C DEBUG] WARNING: ts_node_type returned NULL!\n");
    fflush(stderr);
    CAMLreturn(caml_copy_string("unknown"));
  }
  
  CAMLreturn(caml_copy_string(type));
}

CAMLprim value caml_ts_node_symbol(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  TSSymbol symbol = ts_node_symbol(node);
  CAMLreturn(Val_int(symbol));
}

CAMLprim value caml_ts_node_is_named(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(Val_bool(ts_node_is_named(node)));
}

CAMLprim value caml_ts_node_has_error(value v_node) {
  CAMLparam1(v_node);
  fprintf(stderr, "[C DEBUG] node_has_error called\n");
  fflush(stderr);
  TSNode node = node_val(v_node);
  fprintf(stderr, "[C DEBUG] got TSNode, checking if null\n");
  fflush(stderr);
  if (ts_node_is_null(node)) {
    fprintf(stderr, "[C DEBUG] node is null!\n");
    fflush(stderr);
    CAMLreturn(Val_bool(false));
  }
  fprintf(stderr, "[C DEBUG] node is valid, calling ts_node_has_error\n");
  fflush(stderr);
  bool has_error = ts_node_has_error(node);
  fprintf(stderr, "[C DEBUG] ts_node_has_error returned: %d\n", has_error);
  fflush(stderr);
  CAMLreturn(Val_bool(has_error));
}

CAMLprim value caml_ts_node_is_missing(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(Val_bool(ts_node_is_missing(node)));
}

CAMLprim value caml_ts_node_range(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(alloc_range(node));
}

CAMLprim value caml_ts_node_start_point(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(alloc_point(ts_node_start_point(node)));
}

CAMLprim value caml_ts_node_end_point(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(alloc_point(ts_node_end_point(node)));
}

CAMLprim value caml_ts_node_start_byte(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(Val_int(ts_node_start_byte(node)));
}

CAMLprim value caml_ts_node_end_byte(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(Val_int(ts_node_end_byte(node)));
}

CAMLprim value caml_ts_node_child_count(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(Val_int(ts_node_child_count(node)));
}

CAMLprim value caml_ts_node_child(value v_node, value v_index) {
  CAMLparam2(v_node, v_index);
  TSNode node = node_val(v_node);
  uint32_t index = Int_val(v_index);
  TSNode child = ts_node_child(node, index);
  
  if (ts_node_is_null(child)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(child)));
}

CAMLprim value caml_ts_node_named_child_count(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  CAMLreturn(Val_int(ts_node_named_child_count(node)));
}

CAMLprim value caml_ts_node_named_child(value v_node, value v_index) {
  CAMLparam2(v_node, v_index);
  TSNode node = node_val(v_node);
  uint32_t index = Int_val(v_index);
  TSNode child = ts_node_named_child(node, index);
  
  if (ts_node_is_null(child)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(child)));
}

CAMLprim value caml_ts_node_child_by_field_name(value v_node, value v_field_name) {
  CAMLparam2(v_node, v_field_name);
  TSNode node = node_val(v_node);
  const char *field_name = String_val(v_field_name);
  uint32_t field_name_length = caml_string_length(v_field_name);
  TSNode child = ts_node_child_by_field_name(node, field_name, field_name_length);
  
  if (ts_node_is_null(child)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(child)));
}

CAMLprim value caml_ts_node_parent(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  TSNode parent = ts_node_parent(node);
  
  if (ts_node_is_null(parent)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(parent)));
}

CAMLprim value caml_ts_node_next_sibling(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  TSNode sibling = ts_node_next_sibling(node);
  
  if (ts_node_is_null(sibling)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(sibling)));
}

CAMLprim value caml_ts_node_prev_sibling(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  TSNode sibling = ts_node_prev_sibling(node);
  
  if (ts_node_is_null(sibling)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(sibling)));
}

CAMLprim value caml_ts_node_next_named_sibling(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  TSNode sibling = ts_node_next_named_sibling(node);
  
  if (ts_node_is_null(sibling)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(sibling)));
}

CAMLprim value caml_ts_node_prev_named_sibling(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  TSNode sibling = ts_node_prev_named_sibling(node);
  
  if (ts_node_is_null(sibling)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(sibling)));
}

CAMLprim value caml_ts_node_text(value v_node, value v_source) {
  CAMLparam2(v_node, v_source);
  CAMLlocal1(v_result);
  
  TSNode node = node_val(v_node);
  const char *source = String_val(v_source);
  
  uint32_t start = ts_node_start_byte(node);
  uint32_t end = ts_node_end_byte(node);
  uint32_t length = end - start;
  
  v_result = caml_alloc_string(length);
  memcpy((char *)String_val(v_result), source + start, length);
  
  CAMLreturn(v_result);
}

CAMLprim value caml_ts_node_descendant_for_point_range(value v_node, value v_start, value v_end) {
  CAMLparam3(v_node, v_start, v_end);
  TSNode node = node_val(v_node);
  TSPoint start = point_val(v_start);
  TSPoint end = point_val(v_end);
  
  TSNode descendant = ts_node_descendant_for_point_range(node, start, end);
  
  if (ts_node_is_null(descendant)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(descendant)));
}

CAMLprim value caml_ts_node_named_descendant_for_point_range(value v_node, value v_start, value v_end) {
  CAMLparam3(v_node, v_start, v_end);
  TSNode node = node_val(v_node);
  TSPoint start = point_val(v_start);
  TSPoint end = point_val(v_end);
  
  TSNode descendant = ts_node_named_descendant_for_point_range(node, start, end);
  
  if (ts_node_is_null(descendant)) {
    CAMLreturn(Val_none);
  }
  
  CAMLreturn(Val_some(alloc_node(descendant)));
}

CAMLprim value caml_ts_node_is_error(value v_node) {
  CAMLparam1(v_node);
  TSNode node = node_val(v_node);
  const char *type = ts_node_type(node);
  CAMLreturn(Val_bool(strcmp(type, "ERROR") == 0));
}
