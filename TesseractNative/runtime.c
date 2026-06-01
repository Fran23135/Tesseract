/* =============================================================================
 * tess_runtime.c — Tesseract Runtime Library
 * =============================================================================
 * Implementa todas las funciones declaradas en el LLVM IR generado por
 * tesscodegen.py. Se compila como librería C y se linkea con el objeto
 * producido por llc para generar el ejecutable nativo final.
 *
 * Compilar con:
 *   clang -c tess_runtime.c -o tess_runtime.o -O2
 *   gcc   -c tess_runtime.c -o tess_runtime.o -O2
 *
 * Linkear con el programa:
 *   clang programa.o tess_runtime.o -o programa -lm
 *   gcc   programa.o tess_runtime.o -o programa -lm
 * =============================================================================
 *
 * ESTRUCTURA TessValue  (debe coincidir exactamente con el IR):
 *   %"TessValue" = type {i32, i64}
 *   campo 0: tag   (i32)  — tipo del valor
 *   campo 1: data  (i64)  — el dato (int directo, bits de double, puntero a char* /TessArray* /TessDict*)*/
/**
 * TAGS:
 *   0 = TESS_NULL
 *   1 = TESS_INT    — data = int64_t
 *   2 = TESS_FLOAT  — data = bits del double (via memcpy)
 *   3 = TESS_BOOL   — data = 0 o 1
 *   4 = TESS_STRING — data = (int64_t)(uintptr_t)char*
 *   5 = TESS_ARRAY  — data = (int64_t)(uintptr_t)TessArray*
 *   6 = TESS_DICT   — data = (int64_t)(uintptr_t)TessDict*
 * ============================================================================= */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <inttypes.h>
#include <ctype.h>
/* --------------------------------------------------------------------------
 * Compatibilidad Windows / Linux / macOS
 * -------------------------------------------------------------------------- */
#ifdef _WIN32
  #include <io.h>
  #define strdup _strdup
#else
  #include <unistd.h>
#endif

/* =============================================================================
 * TAGS Y ESTRUCTURA TessValue
 * ============================================================================= */

#define TESS_NULL   0
#define TESS_INT    1
#define TESS_FLOAT  2
#define TESS_BOOL   3
#define TESS_STRING 4
#define TESS_ARRAY  5
#define TESS_DICT   6
#define TESS_TUPLE  7
#define TESS_OBJECT  9
/* Debe coincidir byte a byte con %"TessValue" = type {i32, i64} del IR.
 * El compilador normalmente inserta 4 bytes de padding entre i32 e i64,
 * pero en x86-64 {i32, i64} queda como: [tag:4][pad:4][data:8] = 16 bytes.
 * El atributo packed NO se usa aquí — dejamos que el ABI decida, igual que LLVM. */
typedef struct {
    int32_t  tag;
    int64_t  data;   /* el compilador añadirá 4 bytes de padding antes de data */
} TessValue;

typedef struct TessTypeInfo {
    int32_t           tag;       /* TESS_* tag, -1 = dinámico */
    struct TessTypeInfo* inner;  /* para array<X> y tuple<X> */
    struct TessTypeInfo* key_ti; /* para dict<K,V> — clave */
    struct TessTypeInfo* val_ti; /* para dict<K,V> — valor */
    int64_t           limit;     /* -1 = sin límite */
} TessTypeInfo;

/* =============================================================================
 * ESTRUCTURAS INTERNAS — NO EXPUESTAS AL IR
 * ============================================================================= */

/* Array dinámico */
typedef struct {
    TessValue** items;
    int64_t     len;
    int64_t     cap;
    int32_t     elem_tag;  /* -1 = dinámico, 1=int, 2=float, etc. */
    int64_t     limit;     /* -1 = sin límite */
    TessTypeInfo* type_info; /* NULL = dinámico */
} TessArray;

typedef struct {
    TessValue** items;
    int64_t     len;
    int64_t     cap;
    int32_t     elem_tag;  /* -1 = dinámico */
    int64_t     limit;     /* -1 = sin límite */
    TessTypeInfo* type_info;
} TessTuple;

/* Entrada de hash table para diccionario */
typedef struct TessDictEntry {
    char*                key;
    TessValue*           value;
    struct TessDictEntry* next;
} TessDictEntry;

/* Diccionario con hash table de encadenamiento */
#define DICT_INIT_BUCKETS 16
typedef struct {
    TessDictEntry** buckets;
    int64_t         num_buckets;
    int64_t         size;
    int32_t         key_tag;   /* -1 = dinámico */
    int32_t         val_tag;   /* -1 = dinámico */
    TessTypeInfo*   type_info;
} TessDict;




/* =============================================================================
 * HELPERS INTERNOS
 * ============================================================================= */

/* Convierte double ↔ int64_t sin violar strict aliasing (via memcpy) */
static inline int64_t f64_to_bits(double d) {
    int64_t b; memcpy(&b, &d, 8); return b;
}
static inline double bits_to_f64(int64_t b) {
    double d; memcpy(&d, &b, 8); return d;
}

/* Convierte puntero ↔ int64_t */
static inline int64_t ptr_to_i64(const void* p) {
    return (int64_t)(uintptr_t)p;
}
static inline void* i64_to_ptr(int64_t v) {
    return (void*)(uintptr_t)(uint64_t)v;
}
static int tess_typeinfo_check(TessValue* tv, TessTypeInfo* ti);
/* Formatea un double para impresión como Tesseract lo haría:
 * sin ceros innecesarios, pero siempre al menos un decimal. */
static char* fmt_double(double v) {
    static char buf[64];
    /* Si es un entero exacto y no es inf/nan */
    if (!isinf(v) && !isnan(v) && v == (double)(int64_t)v
        && v >= -9007199254740992.0 && v <= 9007199254740992.0) {
        snprintf(buf, sizeof(buf), "%" PRId64 ".0", (int64_t)v);
    } else {
        snprintf(buf, sizeof(buf), "%.15g", v);
        /* Eliminar ceros finales innecesarios pero conservar al menos un decimal */
        char* dot = strchr(buf, '.');
        if (dot) {
            char* end = buf + strlen(buf) - 1;
            while (end > dot + 1 && *end == '0') *end-- = '\0';
        }
    }
    return buf;
}
/* =============================================================================
 * VALIDACIÓN DE TIPO DE ELEMENTO
 * ============================================================================= */

int tess_check_elem_type(TessValue* tv, int32_t expected_tag) {
    if (!tv) return 0;
    if (expected_tag < 0) return 1;   /* sin restricción */
    return tv->tag == expected_tag ? 1 : 0;
}

static void type_error_elem(const char* container, int32_t expected, int32_t got) {
    const char* tag_names[] = {"null","int","float","bool","string","array","dict","tuple"};
    const char* exp_name = (expected >= 0 && expected <= 7) ? tag_names[expected] : "?";
    const char* got_name = (got     >= 0 && got     <= 7) ? tag_names[got]      : "?";
    fprintf(stderr,
        "Error de tipo en %s: se esperaba '%s', se recibio '%s'\n",
        container, exp_name, got_name);
}

static void limit_error(const char* container, int64_t limit) {
    fprintf(stderr,
        "Error: %s ha alcanzado su limite maximo de %" PRId64 " elementos\n",
        container, limit);
}
/* =============================================================================
 * VALIDACIÓN DE TIPO DE ELEMENTO
 * ============================================================================= */



/*static void type_error_elem(const char* container, int32_t expected, int32_t got) {
    const char* tag_names[] = {"null","int","float","bool","string","array","dict","tuple"};
    const char* exp_name = (expected >= 0 && expected <= 7) ? tag_names[expected] : "?";
    const char* got_name = (got     >= 0 && got     <= 7) ? tag_names[got]      : "?";
    fprintf(stderr,
        "Error de tipo en %s: se esperaba '%s', se recibio '%s'\n",
        container, exp_name, got_name);
}*/

/*static void limit_error(const char* container, int64_t limit) {
    fprintf(stderr,
        "Error: %s ha alcanzado su limite maximo de %" PRId64 " elementos\n",
        container, limit);
}*/
/* Forward declarations necesarias */
static int        tess_is_truthy(TessValue* tv);
static char*      tess_val_to_cstr(TessValue* tv, char* buf, size_t bufsz);
static char*      tess_val_to_cstr_heap(TessValue* tv);

/* =============================================================================
 * CONVERSIÓN INTERNA A STRING (puede retornar estático o heap)
 * Cuando se usa para concatenación se debe usar tess_val_to_cstr_heap
 * que SIEMPRE retorna memoria heap (el llamador debe liberar).
 * ============================================================================= */

static char* tess_val_to_cstr(TessValue* tv, char* buf, size_t bufsz) {
    if (!tv) { strncpy(buf, "null", bufsz); return buf; }
    switch (tv->tag) {
        case TESS_NULL:   strncpy(buf, "null",  bufsz); return buf;
        case TESS_BOOL:   strncpy(buf, tv->data ? "true" : "false", bufsz); return buf;
        case TESS_INT:    snprintf(buf, bufsz, "%" PRId64, tv->data); return buf;
        case TESS_FLOAT:  strncpy(buf, fmt_double(bits_to_f64(tv->data)), bufsz); return buf;
        case TESS_STRING: return (char*)i64_to_ptr(tv->data);   /* puntero interno */
        case TESS_ARRAY: {
            TessArray* arr = (TessArray*)i64_to_ptr(tv->data);
            /* Representación básica para debugging */
            int pos = 0;
            pos += snprintf(buf + pos, bufsz - pos, "[");
            for (int64_t i = 0; i < arr->len && (size_t)pos < bufsz - 4; i++) {
                if (i > 0) pos += snprintf(buf + pos, bufsz - pos, ", ");
                char tmp[128];
                char* s = tess_val_to_cstr(arr->items[i], tmp, sizeof(tmp));
                pos += snprintf(buf + pos, bufsz - pos, "%s", s);
            }
            snprintf(buf + pos, bufsz - pos, "]");
            return buf;
        }
        case TESS_DICT: {
            TessDict* d = (TessDict*)i64_to_ptr(tv->data);
            int pos = 0, first = 1;
            pos += snprintf(buf + pos, bufsz - pos, "{");
            for (int64_t b = 0; b < d->num_buckets && (size_t)pos < bufsz - 8; b++) {
                for (TessDictEntry* e = d->buckets[b]; e; e = e->next) {
                    if (!first) pos += snprintf(buf + pos, bufsz - pos, ", ");
                    char tmp[128];
                    char* vs = tess_val_to_cstr(e->value, tmp, sizeof(tmp));
                    pos += snprintf(buf + pos, bufsz - pos, "%s: %s", e->key, vs);
                    first = 0;
                }
            }
            snprintf(buf + pos, bufsz - pos, "}");
            return buf;
        }
        default: strncpy(buf, "null", bufsz); return buf;
    }
}

static char* tess_val_to_cstr_heap(TessValue* tv) {
    char buf[2048];
    char* s = tess_val_to_cstr(tv, buf, sizeof(buf));
    return strdup(s);
}

/* =============================================================================
 * TRUTHINESS
 * ============================================================================= */

static int tess_is_truthy(TessValue* tv) {
    if (!tv) return 0;
    switch (tv->tag) {
        case TESS_NULL:   return 0;
        case TESS_INT:    return tv->data != 0;
        case TESS_FLOAT:  return bits_to_f64(tv->data) != 0.0;
        case TESS_BOOL:   return tv->data != 0;
        case TESS_STRING: {
            char* s = (char*)i64_to_ptr(tv->data);
            return s && s[0] != '\0';
        }
        case TESS_ARRAY: {
            TessArray* a = (TessArray*)i64_to_ptr(tv->data);
            return a && a->len > 0;
        }
        case TESS_DICT: {
            TessDict* d = (TessDict*)i64_to_ptr(tv->data);
            return d && d->size > 0;
        }
        default: return 0;
    }
}

/* =============================================================================
 * CONSTRUCCIÓN DE TESSVALUE
 * Cada función alloca un TessValue en heap y lo rellena.
 * ============================================================================= */

TessValue* tess_make_int(int64_t v) {
    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_INT;
    tv->data = v;
    return tv;
}

TessValue* tess_make_float(double v) {
    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_FLOAT;
    tv->data = f64_to_bits(v);
    return tv;
}

/* El IR pasa i1 como int (zero-extended a 32 bits en el ABI de x86-64) */
TessValue* tess_make_bool(int v) {
    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_BOOL;
    tv->data = v ? 1 : 0;
    return tv;
}

/* El string se copia a heap para que TessValue sea el propietario */
TessValue* tess_make_string(char* s) {
    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_STRING;
    tv->data = ptr_to_i64(s ? strdup(s) : strdup(""));
    return tv;
}

TessValue* tess_make_null(void) {
    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_NULL;
    tv->data = 0;
    return tv;
}

/* =============================================================================
 * MÓDULO MATH — Funciones nativas de math.tmd
 * Compilar con -lm para enlazar libm.
 * ============================================================================= */

/* --- Constantes exportadas --- */
TessValue* math_PI(void)  { return tess_make_float(3.141592653589793); }
TessValue* math_E(void)   { return tess_make_float(2.718281828459045); }
TessValue* math_TAU(void) { return tess_make_float(6.283185307179586); }
TessValue* math_INF(void) { return tess_make_float(1e308); }

/* --- Helpers internos --- */
static inline double tv_to_double(TessValue* tv) {
    if (!tv) return 0.0;
    if (tv->tag == TESS_FLOAT) return bits_to_f64(tv->data);
    if (tv->tag == TESS_INT)   return (double)tv->data;
    return 0.0;
}

/* --- sqrt(x: float) → float --- */
TessValue* _tess_mod_math_sqrt(TessValue* x) {
    return tess_make_float(sqrt(tv_to_double(x)));
}

/* --- abs(x: any) → int | float --- */
TessValue* _tess_mod_math_abs(TessValue* x) {
    if (!x) return tess_make_int(0);
    if (x->tag == TESS_INT)   return tess_make_int(x->data < 0 ? -x->data : x->data);
    if (x->tag == TESS_FLOAT) return tess_make_float(fabs(bits_to_f64(x->data)));
    return tess_make_null();
}

/* --- pow(x: float, y: float) → float --- */
TessValue* _tess_mod_math_pow(TessValue* x, TessValue* y) {
    return tess_make_float(pow(tv_to_double(x), tv_to_double(y)));
}

/* --- floor(x: float) → float --- */
TessValue* _tess_mod_math_floor(TessValue* x) {
    return tess_make_float(floor(tv_to_double(x)));
}

/* --- ceil(x: float) → float --- */
TessValue* _tess_mod_math_ceil(TessValue* x) {
    return tess_make_float(ceil(tv_to_double(x)));
}

/* --- log(x: float) → float  (logaritmo natural) --- */
TessValue* _tess_mod_math_log(TessValue* x) {
    return tess_make_float(log(tv_to_double(x)));
}

/* --- log2(x: float) → float --- */
TessValue* _tess_mod_math_log2(TessValue* x) {
    return tess_make_float(log2(tv_to_double(x)));
}

/* --- sin(x: float) → float --- */
TessValue* _tess_mod_math_sin(TessValue* x) {
    return tess_make_float(sin(tv_to_double(x)));
}

/* --- cos(x: float) → float --- */
TessValue* _tess_mod_math_cos(TessValue* x) {
    return tess_make_float(cos(tv_to_double(x)));
}

/* --- tan(x: float) → float --- */
TessValue* _tess_mod_math_tan(TessValue* x) {
    return tess_make_float(tan(tv_to_double(x)));
}

/* --- round(x: float) → float --- */
TessValue* _tess_mod_math_round(TessValue* x) {
    return tess_make_float(round(tv_to_double(x)));
}

/* =============================================================================
 * I/O — PRINT
 * Cada función imprime el valor con un salto de línea al final,
 * igual que el comportamiento de print en interpre.py.
 * ============================================================================= */

void tess_print_int(int64_t v) {
    printf("%" PRId64 "\n", v);
}

void tess_print_float(double v) {
    printf("%s\n", fmt_double(v));
}

/* i1 llega como int zero-extended */
void tess_print_bool(int v) {
    printf("%s\n", v ? "true" : "false");
}

void tess_print_string(char* s) {
    printf("%s\n", s ? s : "null");
}

void tess_print_null(void) {
    printf("null\n");
}

void tess_print_value(TessValue* tv) {
    if (!tv) { printf("null\n"); return; }
    switch (tv->tag) {
        case TESS_NULL:
            printf("null\n");
            break;
        case TESS_INT:
            printf("%" PRId64 "\n", tv->data);
            break;
        case TESS_FLOAT:
            printf("%s\n", fmt_double(bits_to_f64(tv->data)));
            break;
        case TESS_BOOL:
            printf("%s\n", tv->data ? "true" : "false");
            break;
        case TESS_STRING:
            printf("%s\n", (char*)i64_to_ptr(tv->data));
            break;
        case TESS_ARRAY: {
            TessArray* arr = (TessArray*)i64_to_ptr(tv->data);
            printf("[");
            for (int64_t i = 0; i < arr->len; i++) {
                if (i > 0) printf(", ");
                char buf[256];
                printf("%s", tess_val_to_cstr(arr->items[i], buf, sizeof(buf)));
            }
            printf("]\n");
            break;
        }
        case TESS_DICT: {
            TessDict* d = (TessDict*)i64_to_ptr(tv->data);
            int first = 1;
            printf("{");
            for (int64_t b = 0; b < d->num_buckets; b++) {
                for (TessDictEntry* e = d->buckets[b]; e; e = e->next) {
                    if (!first) printf(", ");
                    char buf[256];
                    printf("%s: %s", e->key,
                           tess_val_to_cstr(e->value, buf, sizeof(buf)));
                    first = 0;
                }
            }
            printf("}\n");
            break;
        }
        default:
            printf("null\n");
            break;
    }
}

/* =============================================================================
 * I/O — READ
 * ============================================================================= */

/* Lee una línea de stdin y retorna heap string (sin \n) */
char* tess_read_string(void) {
    char buf[4096];
    if (!fgets(buf, sizeof(buf), stdin)) {
        char* empty = (char*)malloc(1);
        empty[0] = '\0';
        return empty;
    }
    size_t len = strlen(buf);
    if (len > 0 && buf[len - 1] == '\n') buf[--len] = '\0';
    if (len > 0 && buf[len - 1] == '\r') buf[--len] = '\0';
    return strdup(buf);
}

int64_t tess_read_int(void) {
    char* s = tess_read_string();
    int64_t v = (int64_t)strtoll(s, NULL, 10);
    free(s);
    return v;
}

double tess_read_float(void) {
    char* s = tess_read_string();
    double v = strtod(s, NULL);
    free(s);
    return v;
}

/* =============================================================================
 * CONVERSIONES DESDE TessValue
 * ============================================================================= */

int64_t tess_to_int(TessValue* tv) {
    if (!tv) return 0;
    switch (tv->tag) {
        case TESS_INT:    return tv->data;
        case TESS_FLOAT:  return (int64_t)bits_to_f64(tv->data);
        case TESS_BOOL:   return tv->data;
        case TESS_STRING: {
            char* s = (char*)i64_to_ptr(tv->data);
            return s ? (int64_t)strtoll(s, NULL, 10) : 0;
        }
        default: return 0;
    }
}

double tess_to_float(TessValue* tv) {
    if (!tv) return 0.0;
    switch (tv->tag) {
        case TESS_INT:    return (double)tv->data;
        case TESS_FLOAT:  return bits_to_f64(tv->data);
        case TESS_BOOL:   return (double)tv->data;
        case TESS_STRING: {
            char* s = (char*)i64_to_ptr(tv->data);
            return s ? strtod(s, NULL) : 0.0;
        }
        default: return 0.0;
    }
}

/* Retorna i1 (pasado como int en el ABI x86-64) */
int tess_to_bool(TessValue* tv) {
    return tess_is_truthy(tv) ? 1 : 0;
}

/* Retorna puntero a string del valor.
 * ATENCIÓN: el string puede ser estático (buf local) — usar solo para leer. */
char* tess_to_string(TessValue* tv) {
    static char buf[2048];
    return tess_val_to_cstr(tv, buf, sizeof(buf));
}

/* Retorna i1: 1 si el valor es "truthy" en semántica Tesseract */
int tess_value_truthy(TessValue* tv) {
    return tess_is_truthy(tv) ? 1 : 0;
}

/* =============================================================================
 * OPERACIONES ARITMÉTICAS DINÁMICAS
 * Siguen las mismas reglas que interpre.py:
 *   int op int  → int  (excepto división que siempre da float)
 *   float op *  → float
 *   string + *  → concatenación (solo para tess_add)
 * ============================================================================= */

static int is_numeric(TessValue* tv) {
    return tv && (tv->tag == TESS_INT || tv->tag == TESS_FLOAT);
}

static int both_numeric(TessValue* a, TessValue* b) {
    return is_numeric(a) && is_numeric(b);
}

static int any_float(TessValue* a, TessValue* b) {
    return (a && a->tag == TESS_FLOAT) || (b && b->tag == TESS_FLOAT);
}

TessValue* tess_add(TessValue* a, TessValue* b) {
    if (!a || !b) return tess_make_null();

    /* Numérico + Numérico */
    if (both_numeric(a, b)) {
        if (any_float(a, b))
            return tess_make_float(tess_to_float(a) + tess_to_float(b));
        return tess_make_int(a->data + b->data);
    }

    /* Cualquier cosa + string → concatenar como strings */
    if (a->tag == TESS_STRING || b->tag == TESS_STRING) {
        char* sa = tess_val_to_cstr_heap(a);
        char* sb = tess_val_to_cstr_heap(b);
        size_t la = strlen(sa), lb = strlen(sb);
        char* res = (char*)malloc(la + lb + 1);
        memcpy(res, sa, la);
        memcpy(res + la, sb, lb + 1);
        free(sa); free(sb);
        TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
        tv->tag  = TESS_STRING;
        tv->data = ptr_to_i64(res);
        return tv;
    }

    return tess_make_null();
}

TessValue* tess_sub(TessValue* a, TessValue* b) {
    if (!a || !b || !both_numeric(a, b)) return tess_make_null();
    if (any_float(a, b))
        return tess_make_float(tess_to_float(a) - tess_to_float(b));
    return tess_make_int(a->data - b->data);
}

TessValue* tess_mul(TessValue* a, TessValue* b) {
    if (!a || !b || !both_numeric(a, b)) return tess_make_null();
    if (any_float(a, b))
        return tess_make_float(tess_to_float(a) * tess_to_float(b));
    return tess_make_int(a->data * b->data);
}

TessValue* tess_div(TessValue* a, TessValue* b) {
    if (!a || !b || !both_numeric(a, b)) return tess_make_null();
    double db = tess_to_float(b);
    if (db == 0.0) {
        fprintf(stderr, "Error: Division por cero\n");
        return tess_make_null();
    }
    /* La division siempre produce float, igual que Python / en interpre.py */
    return tess_make_float(tess_to_float(a) / db);
}

TessValue* tess_mod(TessValue* a, TessValue* b) {
    if (!a || !b || !both_numeric(a, b)) return tess_make_null();
    if (any_float(a, b)) {
        double db = tess_to_float(b);
        if (db == 0.0) { fprintf(stderr, "Error: Modulo por cero\n"); return tess_make_null(); }
        return tess_make_float(fmod(tess_to_float(a), db));
    }
    if (b->data == 0) { fprintf(stderr, "Error: Modulo por cero\n"); return tess_make_null(); }
    return tess_make_int(a->data % b->data);
}

/* =============================================================================
 * OPERACIONES DE COMPARACIÓN
 * Retornan TessValue* con tag TESS_BOOL.
 * ============================================================================= */

TessValue* tess_eq(TessValue* a, TessValue* b) {
    if (!a && !b) return tess_make_bool(1);
    if (!a || !b) return tess_make_bool(0);
    if (a->tag == TESS_NULL && b->tag == TESS_NULL) return tess_make_bool(1);
    if (a->tag == TESS_NULL || b->tag == TESS_NULL) return tess_make_bool(0);
    if (both_numeric(a, b)) {
        if (any_float(a, b))
            return tess_make_bool(tess_to_float(a) == tess_to_float(b));
        return tess_make_bool(a->data == b->data);
    }
    if (a->tag == TESS_STRING && b->tag == TESS_STRING)
        return tess_make_bool(strcmp((char*)i64_to_ptr(a->data),
                                     (char*)i64_to_ptr(b->data)) == 0);
    if (a->tag == TESS_BOOL && b->tag == TESS_BOOL)
        return tess_make_bool(a->data == b->data);
    return tess_make_bool(0);
}

TessValue* tess_neq(TessValue* a, TessValue* b) {
    TessValue* eq = tess_eq(a, b);
    int res = !eq->data;
    free(eq);
    return tess_make_bool(res);
}

TessValue* tess_lt(TessValue* a, TessValue* b) {
    if (!a || !b) return tess_make_bool(0);
    if (both_numeric(a, b)) {
        if (any_float(a, b)) return tess_make_bool(tess_to_float(a) < tess_to_float(b));
        return tess_make_bool(a->data < b->data);
    }
    if (a->tag == TESS_STRING && b->tag == TESS_STRING)
        return tess_make_bool(strcmp((char*)i64_to_ptr(a->data),
                                     (char*)i64_to_ptr(b->data)) < 0);
    return tess_make_bool(0);
}

TessValue* tess_gt(TessValue* a, TessValue* b) {
    if (!a || !b) return tess_make_bool(0);
    if (both_numeric(a, b)) {
        if (any_float(a, b)) return tess_make_bool(tess_to_float(a) > tess_to_float(b));
        return tess_make_bool(a->data > b->data);
    }
    if (a->tag == TESS_STRING && b->tag == TESS_STRING)
        return tess_make_bool(strcmp((char*)i64_to_ptr(a->data),
                                     (char*)i64_to_ptr(b->data)) > 0);
    return tess_make_bool(0);
}

TessValue* tess_lte(TessValue* a, TessValue* b) {
    if (!a || !b) return tess_make_bool(0);
    if (both_numeric(a, b)) {
        if (any_float(a, b)) return tess_make_bool(tess_to_float(a) <= tess_to_float(b));
        return tess_make_bool(a->data <= b->data);
    }
    if (a->tag == TESS_STRING && b->tag == TESS_STRING)
        return tess_make_bool(strcmp((char*)i64_to_ptr(a->data),
                                     (char*)i64_to_ptr(b->data)) <= 0);
    return tess_make_bool(0);
}

TessValue* tess_gte(TessValue* a, TessValue* b) {
    if (!a || !b) return tess_make_bool(0);
    if (both_numeric(a, b)) {
        if (any_float(a, b)) return tess_make_bool(tess_to_float(a) >= tess_to_float(b));
        return tess_make_bool(a->data >= b->data);
    }
    if (a->tag == TESS_STRING && b->tag == TESS_STRING)
        return tess_make_bool(strcmp((char*)i64_to_ptr(a->data),
                                     (char*)i64_to_ptr(b->data)) >= 0);
    return tess_make_bool(0);
}

/* =============================================================================
 * OPERACIONES LÓGICAS
 * tess_and / tess_or usan short-circuit semántico igual que interpre.py:
 *   and: retorna el primer valor falsy o el último valor si todos son truthy
 *   or:  retorna el primer valor truthy o el último valor
 * ============================================================================= */

TessValue* tess_and(TessValue* a, TessValue* b) {
    if (!a) return tess_make_bool(0);
    /* Si a es falsy → retornar a (cortocircuito) */
    if (!tess_is_truthy(a)) return a;
    /* Si a es truthy → retornar b */
    return b ? b : tess_make_null();
}

TessValue* tess_or(TessValue* a, TessValue* b) {
    /* Si a es truthy → retornar a (cortocircuito) */
    if (a && tess_is_truthy(a)) return a;
    /* Si no → retornar b */
    return b ? b : tess_make_null();
}

TessValue* tess_not(TessValue* a) {
    return tess_make_bool(!tess_is_truthy(a));
}

/* Negación unaria: -x */
TessValue* tess_neg(TessValue* a) {
    if (!a) return tess_make_null();
    if (a->tag == TESS_INT)   return tess_make_int(-(a->data));
    if (a->tag == TESS_FLOAT) return tess_make_float(-(bits_to_f64(a->data)));
    return tess_make_null();
}

/* =============================================================================
 * CONCATENACIÓN CON PUNTO (operador . de Tesseract)
 * Convierte ambos operandos a string y los une.
 * Resultado siempre es TESS_STRING.
 * ============================================================================= */

TessValue* tess_concat(TessValue* a, TessValue* b) {
    /* Copiar a en heap antes de convertir b (tess_to_string usa buffer estático) */
    char* sa = tess_val_to_cstr_heap(a);
    char* sb = tess_val_to_cstr_heap(b);

    size_t la = strlen(sa);
    size_t lb = strlen(sb);
    char* res = (char*)malloc(la + lb + 1);
    memcpy(res, sa, la);
    memcpy(res + la, sb, lb + 1);   /* incluye el '\0' */
    free(sa);
    free(sb);

    /* Creamos el TessValue directamente para NO duplicar res (ya es heap) */
    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_STRING;
    tv->data = ptr_to_i64(res);
    return tv;
}

/* =============================================================================
 * ARRAYS DINÁMICOS
 * ============================================================================= */

/*TessValue* tess_array_new(void) {
    TessArray* arr = (TessArray*)malloc(sizeof(TessArray));
    arr->cap   = 8;
    arr->len   = 0;
    arr->items = (TessValue**)malloc(arr->cap * sizeof(TessValue*));

    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_ARRAY;
    tv->data = ptr_to_i64(arr);
    return tv;
}
*/
TessValue* tess_array_new_typed(TessTypeInfo* ti) {
    TessArray* arr   = (TessArray*)malloc(sizeof(TessArray));
    arr->cap         = 8;
    arr->len         = 0;
    arr->items       = (TessValue**)malloc(arr->cap * sizeof(TessValue*));
    arr->type_info   = ti;
    TessValue* tv    = (TessValue*)malloc(sizeof(TessValue));
    tv->tag          = TESS_ARRAY;
    tv->data         = ptr_to_i64(arr);
    return tv;
}
TessValue* tess_array_new(void) {
    return tess_array_new_typed(NULL);
}


void tess_array_push(TessValue* arr_tv, TessValue* item) {
    if (!arr_tv || arr_tv->tag != TESS_ARRAY) return;
    TessArray* arr = (TessArray*)i64_to_ptr(arr_tv->data);
    TessTypeInfo* ti = arr->type_info;

    /* Verificar límite */
    if (ti && ti->limit >= 0 && arr->len >= ti->limit) {
        fprintf(stderr, "Error: array ha alcanzado su limite de %" PRId64
                " elementos\n", ti->limit);
        return;
    }
    /* Verificar tipo recursivo del elemento */
    if (ti && ti->inner && !tess_typeinfo_check(item, ti->inner)) {
        fprintf(stderr, "Error de tipo en array: elemento no coincide con %d\n",
                ti->inner->tag);
        return;
    }

    if (arr->len >= arr->cap) {
        arr->cap *= 2;
        arr->items = (TessValue**)realloc(arr->items, arr->cap * sizeof(TessValue*));
    }
    arr->items[arr->len++] = item;
}
TessValue* tess_array_get(TessValue* arr_tv, int64_t idx) {
    if (!arr_tv || arr_tv->tag != TESS_ARRAY) return tess_make_null();
    TessArray* arr = (TessArray*)i64_to_ptr(arr_tv->data);
    /* Índices negativos: -1 = último elemento */
    if (idx < 0) idx = arr->len + idx;
    if (idx < 0 || idx >= arr->len) {
        fprintf(stderr, "Error: Indice %" PRId64 " fuera de limites (0..%" PRId64 ")\n",
                idx, arr->len - 1);
        return tess_make_null();
    }
    return arr->items[idx];
}

void tess_array_set(TessValue* arr_tv, int64_t idx, TessValue* val) {
    if (!arr_tv || arr_tv->tag != TESS_ARRAY) return;
    TessArray* arr = (TessArray*)i64_to_ptr(arr_tv->data);
    if (idx < 0) idx = arr->len + idx;
    if (idx < 0 || idx >= arr->len) {
        fprintf(stderr, "Error: indice %" PRId64 " fuera de limites\n", idx);
        return;
    }
    TessTypeInfo* ti = arr->type_info;
    if (ti && ti->inner && !tess_typeinfo_check(val, ti->inner)) {
        fprintf(stderr, "Error de tipo en array set\n");
        return;
    }
    arr->items[idx] = val;
}
int64_t tess_array_len(TessValue* arr_tv) {
    if (!arr_tv || arr_tv->tag != TESS_ARRAY) return 0;
    return ((TessArray*)i64_to_ptr(arr_tv->data))->len;
}


TessValue* tess_tuple_new_typed(TessTypeInfo* ti) {
    TessTuple* t   = (TessTuple*)malloc(sizeof(TessTuple));
    t->cap         = 8;
    t->len         = 0;
    t->items       = (TessValue**)malloc(t->cap * sizeof(TessValue*));
    t->type_info   = ti;
    TessValue* tv  = (TessValue*)malloc(sizeof(TessValue));
    tv->tag        = TESS_TUPLE;
    tv->data       = ptr_to_i64(t);
    return tv;
}
TessValue* tess_tuple_new(void) {
    return tess_tuple_new_typed(NULL);
}
void tess_tuple_push(TessValue* tup_tv, TessValue* item) {
    if (!tup_tv || tup_tv->tag != TESS_TUPLE) return;
    TessTuple* t     = (TessTuple*)i64_to_ptr(tup_tv->data);
    TessTypeInfo* ti = t->type_info;

    if (ti && ti->limit >= 0 && t->len >= ti->limit) {
        fprintf(stderr, "Error: tuple ha alcanzado su limite de %" PRId64
                " elementos\n", ti->limit);
        return;
    }
    if (ti && ti->inner && !tess_typeinfo_check(item, ti->inner)) {
        fprintf(stderr, "Error de tipo en tuple\n");
        return;
    }
    if (t->len >= t->cap) {
        t->cap *= 2;
        t->items = (TessValue**)realloc(t->items, t->cap * sizeof(TessValue*));
    }
    t->items[t->len++] = item;
}

TessValue* tess_tuple_get(TessValue* tup_tv, int64_t idx) {
    if (!tup_tv || tup_tv->tag != TESS_TUPLE) return tess_make_null();
    TessTuple* t = (TessTuple*)i64_to_ptr(tup_tv->data);
    if (idx < 0) idx = t->len + idx;
    if (idx < 0 || idx >= t->len) {
        fprintf(stderr, "Error: indice %" PRId64 " fuera de limites en tuple\n", idx);
        return tess_make_null();
    }
    return t->items[idx];
}



int64_t tess_tuple_len(TessValue* tup_tv) {
    if (!tup_tv || tup_tv->tag != TESS_TUPLE) return 0;
    return ((TessTuple*)i64_to_ptr(tup_tv->data))->len;
}

/* =============================================================================
 * DICCIONARIOS — hash table con encadenamiento (FNV-1a)
 * ============================================================================= */

static uint64_t fnv1a(const char* key) {
    uint64_t h = 14695981039346656037ULL;
    while (*key) { h ^= (uint8_t)*key++; h *= 1099511628211ULL; }
    return h;
}

TessValue* tess_dict_new_typed(TessTypeInfo* ti) {
    TessDict* d     = (TessDict*)malloc(sizeof(TessDict));
    d->num_buckets  = DICT_INIT_BUCKETS;
    d->size         = 0;
    d->buckets      = (TessDictEntry**)calloc(d->num_buckets, sizeof(TessDictEntry*));
    d->type_info    = ti;
    TessValue* tv   = (TessValue*)malloc(sizeof(TessValue));
    tv->tag         = TESS_DICT;
    tv->data        = ptr_to_i64(d);
    return tv;
}
TessValue* tess_dict_new(void) {
    return tess_dict_new_typed(NULL);
}

/*TessValue* tess_dict_new(void) {
    TessDict* d = (TessDict*)malloc(sizeof(TessDict));
    d->num_buckets = DICT_INIT_BUCKETS;
    d->size        = 0;
    d->buckets     = (TessDictEntry**)calloc(d->num_buckets, sizeof(TessDictEntry*));

    TessValue* tv = (TessValue*)malloc(sizeof(TessValue));
    tv->tag  = TESS_DICT;
    tv->data = ptr_to_i64(d);
    return tv;
}
*/
TessValue* tess_dict_get(TessValue* dict_tv, char* key) {
    if (!dict_tv || dict_tv->tag != TESS_DICT || !key) return tess_make_null();
    TessDict* d   = (TessDict*)i64_to_ptr(dict_tv->data);
    uint64_t  idx = fnv1a(key) % (uint64_t)d->num_buckets;
    for (TessDictEntry* e = d->buckets[idx]; e; e = e->next)
        if (strcmp(e->key, key) == 0) return e->value;
    return tess_make_null();
}

void tess_dict_set(TessValue* dict_tv, char* key, TessValue* val) {
    if (!dict_tv || dict_tv->tag != TESS_DICT || !key) return;
    TessDict* d      = (TessDict*)i64_to_ptr(dict_tv->data);
    TessTypeInfo* ti = d->type_info;

    /* Verificar tipo de valor recursivamente */
    if (ti && ti->val_ti && !tess_typeinfo_check(val, ti->val_ti)) {
        fprintf(stderr, "Error de tipo en dict: valor no coincide con tipo declarado\n");
        return;
    }

    uint64_t idx = fnv1a(key) % (uint64_t)d->num_buckets;
    for (TessDictEntry* e = d->buckets[idx]; e; e = e->next) {
        if (strcmp(e->key, key) == 0) { e->value = val; return; }
    }
    TessDictEntry* ne = (TessDictEntry*)malloc(sizeof(TessDictEntry));
    ne->key           = strdup(key);
    ne->value         = val;
    ne->next          = d->buckets[idx];
    d->buckets[idx]   = ne;
    d->size++;
}
/* Retorna i1 (int 0/1) */
int tess_dict_has(TessValue* dict_tv, char* key) {
    if (!dict_tv || dict_tv->tag != TESS_DICT || !key) return 0;
    TessDict* d   = (TessDict*)i64_to_ptr(dict_tv->data);
    uint64_t  idx = fnv1a(key) % (uint64_t)d->num_buckets;
    for (TessDictEntry* e = d->buckets[idx]; e; e = e->next)
        if (strcmp(e->key, key) == 0) return 1;
    return 0;
}

/* =============================================================================
 * INCREMENTO / DECREMENTO DINÁMICO
 * ============================================================================= */

TessValue* tess_inc(TessValue* tv) {
    if (!tv) return tess_make_null();
    if (tv->tag == TESS_INT)   return tess_make_int(tv->data + 1);
    if (tv->tag == TESS_FLOAT) return tess_make_float(bits_to_f64(tv->data) + 1.0);
    return tess_make_null();
}

TessValue* tess_dec(TessValue* tv) {
    if (!tv) return tess_make_null();
    if (tv->tag == TESS_INT)   return tess_make_int(tv->data - 1);
    if (tv->tag == TESS_FLOAT) return tess_make_float(bits_to_f64(tv->data) - 1.0);
    return tess_make_null();
}
TessTypeInfo* tess_typeinfo_new(int32_t tag) {
    TessTypeInfo* ti = (TessTypeInfo*)malloc(sizeof(TessTypeInfo));
    ti->tag   = tag;
    ti->inner = NULL;
    ti->key_ti= NULL;
    ti->val_ti= NULL;
    ti->limit = -1;
    return ti;
}

void tess_typeinfo_set_inner(TessTypeInfo* parent, TessTypeInfo* inner) {
    if (parent) parent->inner = inner;
}

void tess_typeinfo_set_key_val(TessTypeInfo* ti,
                                TessTypeInfo* key, TessTypeInfo* val) {
    if (ti) { ti->key_ti = key; ti->val_ti = val; }
}

void tess_typeinfo_set_limit(TessTypeInfo* ti, int64_t limit) {
    if (ti) ti->limit = limit;
}

static int tess_typeinfo_check(TessValue* tv, TessTypeInfo* ti) {
    if (!ti || ti->tag < 0) return 1;   /* dinámico — siempre ok */
    if (!tv) return ti->tag == TESS_NULL;
    if (tv->tag != ti->tag) return 0;   /* tag de primer nivel no coincide */

    /* Verificación recursiva para array */
    if (ti->tag == TESS_ARRAY && ti->inner) {
        TessArray* arr = (TessArray*)i64_to_ptr(tv->data);
        for (int64_t i = 0; i < arr->len; i++) {
            if (!tess_typeinfo_check(arr->items[i], ti->inner)) return 0;
        }
    }

    /* Verificación recursiva para tuple */
    if (ti->tag == TESS_TUPLE && ti->inner) {
        TessTuple* t = (TessTuple*)i64_to_ptr(tv->data);
        for (int64_t i = 0; i < t->len; i++) {
            if (!tess_typeinfo_check(t->items[i], ti->inner)) return 0;
        }
    }

    /* Verificación recursiva para dict */
    if (ti->tag == TESS_DICT && (ti->key_ti || ti->val_ti)) {
        TessDict* d = (TessDict*)i64_to_ptr(tv->data);
        for (int64_t b = 0; b < d->num_buckets; b++) {
            for (TessDictEntry* e = d->buckets[b]; e; e = e->next) {
                if (ti->val_ti && !tess_typeinfo_check(e->value, ti->val_ti))
                    return 0;
            }
        }
    }
    return 1;
}
/* =============================================================================
 * OBJETOS (OOP)
 * TessObject es un dict especializado que además conoce su clase.
 * ============================================================================= */

#define TESS_EXCEPTION 8   /* tag para TessValue que contiene una excepción */

typedef struct {
    char*      class_name;
    TessDict*  attrs;       /* atributos de instancia */
} TessObject;

typedef struct {
    char* class_name;
    char* message;
} TessExceptionData;

TessObject* tess_object_new(char* class_name) {
    TessObject* obj  = (TessObject*)malloc(sizeof(TessObject));
    obj->class_name  = strdup(class_name);
    obj->attrs       = (TessDict*)malloc(sizeof(TessDict));
    obj->attrs->num_buckets = DICT_INIT_BUCKETS;
    obj->attrs->size        = 0;
    obj->attrs->buckets     = (TessDictEntry**)calloc(DICT_INIT_BUCKETS, sizeof(TessDictEntry*));
    obj->attrs->type_info   = NULL;
    return obj;
}

TessValue* tess_object_get_attr(TessObject* obj, char* attr_name) {
    if (!obj || !attr_name) return tess_make_null();
    uint64_t idx = fnv1a(attr_name) % (uint64_t)obj->attrs->num_buckets;
    for (TessDictEntry* e = obj->attrs->buckets[idx]; e; e = e->next)
        if (strcmp(e->key, attr_name) == 0) return e->value;
    return tess_make_null();
}

void tess_object_set_attr(TessObject* obj, char* attr_name, TessValue* val) {
    if (!obj || !attr_name) return;
    TessValue wrapper;
    wrapper.tag  = TESS_DICT;
    wrapper.data = ptr_to_i64(obj->attrs);
    tess_dict_set(&wrapper, attr_name, val);
}

/* tess_object_call: despacho dinámico — se implementa por el runtime de módulos UI.
 * Para código Tesseract compilado, los métodos se llaman directamente via mangling. */
TessValue* tess_object_call(TessObject* obj, char* method_name,
                             TessValue* args_arr, int64_t args_count) {
    /* Placeholder — el despacho real lo hace el código IR compilado o el runtime UI */
    fprintf(stderr, "tess_object_call: '%s' no tiene despacho dinamico.\n", method_name);
    return tess_make_null();
}

int tess_object_is_instance(TessObject* obj, char* class_name) {
    if (!obj || !class_name) return 0;
    return strcmp(obj->class_name, class_name) == 0 ? 1 : 0;
}

/* =============================================================================
 * EXCEPCIONES — setjmp/longjmp
 * ============================================================================= */

#include <setjmp.h>

#define TESS_EXCEPTION_STACK_MAX 64
static jmp_buf   _tess_jmp_stack[TESS_EXCEPTION_STACK_MAX];
static TessValue* _tess_caught_exc[TESS_EXCEPTION_STACK_MAX];
static int        _tess_exc_depth = -1;

TessValue* tess_exception_new(char* class_name, char* message) {
    TessExceptionData* data = (TessExceptionData*)malloc(sizeof(TessExceptionData));
    data->class_name = strdup(class_name ? class_name : "Error");
    data->message    = strdup(message    ? message    : "");
    TessValue* tv    = (TessValue*)malloc(sizeof(TessValue));
    tv->tag          = TESS_EXCEPTION;
    tv->data         = ptr_to_i64(data);
    return tv;
}

char* tess_exception_class(TessValue* exc) {
    if (!exc || exc->tag != TESS_EXCEPTION) return "Error";
    return ((TessExceptionData*)i64_to_ptr(exc->data))->class_name;
}

char* tess_exception_message(TessValue* exc) {
    if (!exc || exc->tag != TESS_EXCEPTION) return "";
    return ((TessExceptionData*)i64_to_ptr(exc->data))->message;
}

int tess_try_begin(void) {
    _tess_exc_depth++;
    if (_tess_exc_depth >= TESS_EXCEPTION_STACK_MAX) {
        fprintf(stderr, "Error: demasiados try anidados\n");
        _tess_exc_depth--;
        return -1;
    }
    _tess_caught_exc[_tess_exc_depth] = NULL;
    return setjmp(_tess_jmp_stack[_tess_exc_depth]);
}

void tess_throw(TessValue* exc) {
    if (_tess_exc_depth < 0) {
        /* Sin try activo — error fatal */
        char* cls = exc ? tess_exception_class(exc) : "Error";
        char* msg = exc ? tess_exception_message(exc) : "";
        fprintf(stderr, "Excepcion no capturada [%s]: %s\n", cls, msg);
        exit(1);
    }
    _tess_caught_exc[_tess_exc_depth] = exc;
    longjmp(_tess_jmp_stack[_tess_exc_depth], 1);
}

TessValue* tess_catch_get(void) {
    if (_tess_exc_depth < 0 || !_tess_caught_exc[_tess_exc_depth])
        return tess_make_null();
    return _tess_caught_exc[_tess_exc_depth];
}

void tess_try_end(void) {
    if (_tess_exc_depth >= 0) {
        _tess_caught_exc[_tess_exc_depth] = NULL;
        _tess_exc_depth--;
    }
}
/* =============================================================================
 * CORE TYPE INTERFACE — _tess_mod_{tipo}_{metodo}
 * Generado por tesscodegen como ModCallNode con module = nombre del tipo.
 * Convención: primer arg = self (el TessValue del valor), args extra = parámetros.
 * ============================================================================= */

/* ---------------------------------------------------------------------------
 * STRING
 * ------------------------------------------------------------------------- */
TessValue* _tess_mod_string_length(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    return tess_make_int((int64_t)strlen(s));
}
TessValue* _tess_mod_string_isEmpty(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    return tess_make_bool(s[0] == '\0');
}
TessValue* _tess_mod_string_isArray(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_string_isString(TessValue* self) { return tess_make_bool(1); }
TessValue* _tess_mod_string_isInt(TessValue* self)    { return tess_make_bool(0); }
TessValue* _tess_mod_string_isFloat(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_string_isBool(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_string_type(TessValue* self)     { return tess_make_string(strdup("string")); }

TessValue* _tess_mod_string_toUpperCase(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* r = strdup(s);
    for (char* p = r; *p; p++) *p = (char)toupper((unsigned char)*p);
    return tess_make_string(r);
}
TessValue* _tess_mod_string_toLowerCase(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* r = strdup(s);
    for (char* p = r; *p; p++) *p = (char)tolower((unsigned char)*p);
    return tess_make_string(r);
}
TessValue* _tess_mod_string_trim(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r') s++;
    char* r = strdup(s);
    int len = (int)strlen(r);
    while (len > 0 && (r[len-1]==' '||r[len-1]=='\t'||r[len-1]=='\n'||r[len-1]=='\r')) r[--len]='\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_trimStart(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r') s++;
    return tess_make_string(strdup(s));
}
TessValue* _tess_mod_string_trimEnd(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* r = strdup(s);
    int len = (int)strlen(r);
    while (len > 0 && (r[len-1]==' '||r[len-1]=='\t'||r[len-1]=='\n'||r[len-1]=='\r')) r[--len]='\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_reverse(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int len = (int)strlen(s);
    char* r = malloc(len + 1);
    for (int i = 0; i < len; i++) r[i] = s[len - 1 - i];
    r[len] = '\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_repeat(TessValue* self, TessValue* n) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int64_t times = (n && n->tag == TESS_INT) ? n->data : 0;
    if (times <= 0) return tess_make_string(strdup(""));
    int slen = (int)strlen(s);
    char* r = malloc((size_t)(slen * times + 1));
    r[0] = '\0';
    for (int64_t i = 0; i < times; i++) memcpy(r + i * slen, s, (size_t)slen);
    r[slen * times] = '\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_replace(TessValue* self, TessValue* from, TessValue* to) {
    char* s   = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* f   = (from && from->tag == TESS_STRING) ? (char*)i64_to_ptr(from->data) : "";
    char* t   = (to   && to->tag   == TESS_STRING) ? (char*)i64_to_ptr(to->data)   : "";
    int flen  = (int)strlen(f), tlen = (int)strlen(t), slen = (int)strlen(s);
    if (flen == 0) return tess_make_string(strdup(s));
    /* count occurrences */
    int count = 0;
    for (char* p = s; (p = strstr(p, f)); p += flen) count++;
    char* r = malloc((size_t)(slen + count * (tlen - flen) + 1));
    char* w = r;
    for (char* p = s;;) {
        char* q = strstr(p, f);
        if (!q) { strcpy(w, p); break; }
        memcpy(w, p, (size_t)(q - p)); w += q - p;
        memcpy(w, t, (size_t)tlen);    w += tlen;
        p = q + flen;
    }
    return tess_make_string(r);
}
TessValue* _tess_mod_string_slice(TessValue* self, TessValue* a, TessValue* b) {
    char* s   = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int len   = (int)strlen(s);
    int start = (a && a->tag == TESS_INT) ? (int)a->data : 0;
    int end   = (b && b->tag == TESS_INT) ? (int)b->data : len;
    if (start < 0) start = 0;
    if (end   > len) end = len;
    if (start >= end) return tess_make_string(strdup(""));
    char* r = malloc((size_t)(end - start + 1));
    memcpy(r, s + start, (size_t)(end - start));
    r[end - start] = '\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_charAt(TessValue* self, TessValue* idx) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int len = (int)strlen(s);
    int i   = (idx && idx->tag == TESS_INT) ? (int)idx->data : 0;
    if (i < 0 || i >= len) return tess_make_string(strdup(""));
    char* r = malloc(2); r[0] = s[i]; r[1] = '\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_contains(TessValue* self, TessValue* sub) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* u = (sub  && sub->tag  == TESS_STRING) ? (char*)i64_to_ptr(sub->data)  : "";
    return tess_make_bool(strstr(s, u) != NULL);
}
TessValue* _tess_mod_string_startsWith(TessValue* self, TessValue* pre) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* p = (pre  && pre->tag  == TESS_STRING) ? (char*)i64_to_ptr(pre->data)  : "";
    return tess_make_bool(strncmp(s, p, strlen(p)) == 0);
}
TessValue* _tess_mod_string_endsWith(TessValue* self, TessValue* suf) {
    char* s   = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* sf  = (suf  && suf->tag  == TESS_STRING) ? (char*)i64_to_ptr(suf->data)  : "";
    int slen  = (int)strlen(s), sflen = (int)strlen(sf);
    if (sflen > slen) return tess_make_bool(0);
    return tess_make_bool(strcmp(s + slen - sflen, sf) == 0);
}
TessValue* _tess_mod_string_indexOf(TessValue* self, TessValue* sub) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* u = (sub  && sub->tag  == TESS_STRING) ? (char*)i64_to_ptr(sub->data)  : "";
    char* p = strstr(s, u);
    return tess_make_int(p ? (int64_t)(p - s) : -1LL);
}
TessValue* _tess_mod_string_padStart(TessValue* self, TessValue* n, TessValue* ch) {
    char* s   = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int64_t w = (n  && n->tag  == TESS_INT)    ? n->data    : 0;
    char*   c = (ch && ch->tag == TESS_STRING) ? (char*)i64_to_ptr(ch->data) : " ";
    int slen  = (int)strlen(s), clen = (int)strlen(c);
    if (clen == 0 || w <= slen) return tess_make_string(strdup(s));
    int pad   = (int)(w - slen);
    char* r   = malloc((size_t)(w + 1));
    for (int i = 0; i < pad; i++) r[i] = c[i % clen];
    memcpy(r + pad, s, (size_t)slen); r[w] = '\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_padEnd(TessValue* self, TessValue* n, TessValue* ch) {
    char* s   = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int64_t w = (n  && n->tag  == TESS_INT)    ? n->data    : 0;
    char*   c = (ch && ch->tag == TESS_STRING) ? (char*)i64_to_ptr(ch->data) : " ";
    int slen  = (int)strlen(s), clen = (int)strlen(c);
    if (clen == 0 || w <= slen) return tess_make_string(strdup(s));
    int pad   = (int)(w - slen);
    char* r   = malloc((size_t)(w + 1));
    memcpy(r, s, (size_t)slen);
    for (int i = 0; i < pad; i++) r[slen + i] = c[i % clen];
    r[w] = '\0';
    return tess_make_string(r);
}
TessValue* _tess_mod_string_typeInt(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "0";
    return tess_make_int((int64_t)(int64_t)strtoll(s, NULL, 10));
}
TessValue* _tess_mod_string_typeFloat(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "0";
    return tess_make_float(strtod(s, NULL));
}
TessValue* _tess_mod_string_typeString(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    return tess_make_string(strdup(s));
}
TessValue* _tess_mod_string_typeBool(TessValue* self) {
    char* s = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    int b = strlen(s) > 0 && strcmp(s,"false") != 0 && strcmp(s,"0") != 0;
    return tess_make_bool(b);
}
/* split devuelve un TessValue array */
TessValue* _tess_mod_string_split(TessValue* self, TessValue* sep) {
    char* s    = (self && self->tag == TESS_STRING) ? (char*)i64_to_ptr(self->data) : "";
    char* delim= (sep  && sep->tag  == TESS_STRING) ? (char*)i64_to_ptr(sep->data)  : "";
    TessValue* arr = tess_array_new();
    TessArray* a   = (TessArray*)i64_to_ptr(arr->data);
    if (strlen(delim) == 0) {
        for (char* p = s; *p; p++) {
            char ch[2] = {*p, '\0'};
            TessValue* item = tess_make_string(strdup(ch));
            if (a->len == a->cap) {
                a->cap = a->cap ? a->cap * 2 : 8;
                a->items = realloc(a->items, (size_t)a->cap * sizeof(TessValue*));
            }
            a->items[a->len++] = item;
        }
    } else {
        char* copy = strdup(s);
        char* tok  = strtok(copy, delim);
        while (tok) {
            TessValue* item = tess_make_string(strdup(tok));
            if (a->len == a->cap) {
                a->cap = a->cap ? a->cap * 2 : 8;
                a->items = realloc(a->items, (size_t)a->cap * sizeof(TessValue*));
            }
            a->items[a->len++] = item;
            tok = strtok(NULL, delim);
        }
        free(copy);
    }
    return arr;
}

/* ---------------------------------------------------------------------------
 * INT
 * ------------------------------------------------------------------------- */
TessValue* _tess_mod_int_length(TessValue* self) {
    char buf[32];
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    snprintf(buf, sizeof(buf), "%" PRId64, v);
    return tess_make_int((int64_t)strlen(buf));
}
TessValue* _tess_mod_int_isEmpty(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_int_isArray(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_int_isString(TessValue* self) { return tess_make_bool(0); }
TessValue* _tess_mod_int_isInt(TessValue* self)    { return tess_make_bool(1); }
TessValue* _tess_mod_int_isFloat(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_int_isBool(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_int_type(TessValue* self)     { return tess_make_string(strdup("int")); }
TessValue* _tess_mod_int_isEven(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_bool(v % 2 == 0);
}
TessValue* _tess_mod_int_isOdd(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_bool(v % 2 != 0);
}
TessValue* _tess_mod_int_isPositive(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_bool(v > 0);
}
TessValue* _tess_mod_int_isNegative(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_bool(v < 0);
}
TessValue* _tess_mod_int_abs(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_int(v < 0 ? -v : v);
}
TessValue* _tess_mod_int_clamp(TessValue* self, TessValue* lo, TessValue* hi) {
    int64_t v  = (self && self->tag == TESS_INT) ? self->data : 0;
    int64_t mn = (lo   && lo->tag   == TESS_INT) ? lo->data   : v;
    int64_t mx = (hi   && hi->tag   == TESS_INT) ? hi->data   : v;
    if (v < mn) v = mn; if (v > mx) v = mx;
    return tess_make_int(v);
}
TessValue* _tess_mod_int_pow(TessValue* self, TessValue* exp) {
    int64_t base = (self && self->tag == TESS_INT) ? self->data : 0;
    int64_t e    = (exp  && exp->tag  == TESS_INT) ? exp->data  : 1;
    double  r    = pow((double)base, (double)e);
    return tess_make_int((int64_t)r);
}
TessValue* _tess_mod_int_max(TessValue* self, TessValue* other) {
    int64_t a = (self  && self->tag  == TESS_INT) ? self->data  : 0;
    int64_t b = (other && other->tag == TESS_INT) ? other->data : a;
    return tess_make_int(a > b ? a : b);
}
TessValue* _tess_mod_int_min(TessValue* self, TessValue* other) {
    int64_t a = (self  && self->tag  == TESS_INT) ? self->data  : 0;
    int64_t b = (other && other->tag == TESS_INT) ? other->data : a;
    return tess_make_int(a < b ? a : b);
}
TessValue* _tess_mod_int_typeFloat(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_float((double)v);
}
TessValue* _tess_mod_int_typeInt(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_int(v);
}
TessValue* _tess_mod_int_typeString(TessValue* self) {
    char buf[32];
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    snprintf(buf, sizeof(buf), "%" PRId64, v);
    return tess_make_string(strdup(buf));
}
TessValue* _tess_mod_int_typeBool(TessValue* self) {
    int64_t v = (self && self->tag == TESS_INT) ? self->data : 0;
    return tess_make_bool(v != 0);
}

/* ---------------------------------------------------------------------------
 * FLOAT
 * ------------------------------------------------------------------------- */
TessValue* _tess_mod_float_length(TessValue* self) {
    char buf[64];
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    snprintf(buf, sizeof(buf), "%g", v);
    return tess_make_int((int64_t)strlen(buf));
}
TessValue* _tess_mod_float_isEmpty(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_float_isArray(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_float_isString(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_float_isInt(TessValue* self)     { return tess_make_bool(0); }
TessValue* _tess_mod_float_isFloat(TessValue* self)   { return tess_make_bool(1); }
TessValue* _tess_mod_float_isBool(TessValue* self)    { return tess_make_bool(0); }
TessValue* _tess_mod_float_type(TessValue* self)      { return tess_make_string(strdup("float")); }
TessValue* _tess_mod_float_abs(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_float(fabs(v));
}
TessValue* _tess_mod_float_round(TessValue* self, TessValue* decimals) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    if (decimals && decimals->tag == TESS_INT) {
        double factor = pow(10.0, (double)decimals->data);
        return tess_make_float(round(v * factor) / factor);
    }
    return tess_make_float(round(v));
}
TessValue* _tess_mod_float_floor(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_int((int64_t)floor(v));
}
TessValue* _tess_mod_float_ceil(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_int((int64_t)ceil(v));
}
TessValue* _tess_mod_float_clamp(TessValue* self, TessValue* lo, TessValue* hi) {
    double v  = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    double mn = (lo   && lo->tag   == TESS_FLOAT) ? bits_to_f64(lo->data)   : v;
    double mx = (hi   && hi->tag   == TESS_FLOAT) ? bits_to_f64(hi->data)   : v;
    if (v < mn) v = mn; if (v > mx) v = mx;
    return tess_make_float(v);
}
TessValue* _tess_mod_float_pow(TessValue* self, TessValue* exp) {
    double base = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    double e    = (exp  && exp->tag  == TESS_FLOAT) ? bits_to_f64(exp->data)  : 1.0;
    return tess_make_float(pow(base, e));
}
TessValue* _tess_mod_float_isNaN(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_bool(isnan(v));
}
TessValue* _tess_mod_float_isInfinite(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_bool(isinf(v));
}
TessValue* _tess_mod_float_typeInt(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_int((int64_t)v);
}
TessValue* _tess_mod_float_typeFloat(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_float(v);
}
TessValue* _tess_mod_float_typeString(TessValue* self) {
    char buf[64];
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    snprintf(buf, sizeof(buf), "%g", v);
    return tess_make_string(strdup(buf));
}
TessValue* _tess_mod_float_typeBool(TessValue* self) {
    double v = (self && self->tag == TESS_FLOAT) ? bits_to_f64(self->data) : 0.0;
    return tess_make_bool(v != 0.0);
}

/* ---------------------------------------------------------------------------
 * BOOL
 * ------------------------------------------------------------------------- */
TessValue* _tess_mod_bool_type(TessValue* self)      { return tess_make_string(strdup("bool")); }
TessValue* _tess_mod_bool_isArray(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_bool_isString(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_bool_isInt(TessValue* self)     { return tess_make_bool(0); }
TessValue* _tess_mod_bool_isFloat(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_bool_isBool(TessValue* self)    { return tess_make_bool(1); }
TessValue* _tess_mod_bool_toggle(TessValue* self) {
    int v = (self && self->tag == TESS_BOOL) ? (int)self->data : 0;
    return tess_make_bool(!v);
}
TessValue* _tess_mod_bool_typeInt(TessValue* self) {
    int v = (self && self->tag == TESS_BOOL) ? (int)self->data : 0;
    return tess_make_int(v ? 1 : 0);
}
TessValue* _tess_mod_bool_typeFloat(TessValue* self) {
    int v = (self && self->tag == TESS_BOOL) ? (int)self->data : 0;
    return tess_make_float(v ? 1.0 : 0.0);
}
TessValue* _tess_mod_bool_typeString(TessValue* self) {
    int v = (self && self->tag == TESS_BOOL) ? (int)self->data : 0;
    return tess_make_string(strdup(v ? "true" : "false"));
}
TessValue* _tess_mod_bool_typeBool(TessValue* self) {
    int v = (self && self->tag == TESS_BOOL) ? (int)self->data : 0;
    return tess_make_bool(v);
}

/* ---------------------------------------------------------------------------
 * ARRAY
 * Nota: push/pop/shift/unshift/insert/remove/clear mutan en sitio (mutable_default).
 * Retornan el mismo TessValue* del array para permitir encadenamiento.
 * ------------------------------------------------------------------------- */
TessValue* _tess_modvar_arr_length(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_int(0);
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    return tess_make_int(a->len);
}
TessValue* _tess_mod_array_isEmpty(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_bool(1);
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    return tess_make_bool(a->len == 0);
}
TessValue* _tess_mod_array_isArray(TessValue* self)  { return tess_make_bool(1); }
TessValue* _tess_mod_array_isString(TessValue* self) { return tess_make_bool(0); }
TessValue* _tess_mod_array_isInt(TessValue* self)    { return tess_make_bool(0); }
TessValue* _tess_mod_array_isFloat(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_array_isBool(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_array_type(TessValue* self)     { return tess_make_string(strdup("array")); }
TessValue* _tess_mod_array_first(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_null();
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    return (a->len > 0) ? a->items[0] : tess_make_null();
}
TessValue* _tess_mod_array_last(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_null();
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    return (a->len > 0) ? a->items[a->len - 1] : tess_make_null();
}
/* mutable_default: push muta self y lo devuelve */
//_tess_mod_arr_push
TessValue* _tess_mod_arr_push(TessValue* self, TessValue* item) {
    tess_array_push(self, item);   /* reutiliza la función interna ya existente */
    return self;
}
TessValue* _tess_mod_array_pop(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    if (a->len > 0) a->len--;
    return self;
}
TessValue* _tess_mod_array_shift(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    if (a->len > 0) {
        memmove(a->items, a->items + 1, (size_t)(a->len - 1) * sizeof(TessValue*));
        a->len--;
    }
    return self;
}
TessValue* _tess_mod_array_unshift(TessValue* self, TessValue* item) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    if (a->len == a->cap) {
        a->cap = a->cap ? a->cap * 2 : 8;
        a->items = realloc(a->items, (size_t)a->cap * sizeof(TessValue*));
    }
    memmove(a->items + 1, a->items, (size_t)a->len * sizeof(TessValue*));
    a->items[0] = item;
    a->len++;
    return self;
}
TessValue* _tess_mod_array_insert(TessValue* self, TessValue* idx, TessValue* item) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    int64_t i    = (idx && idx->tag == TESS_INT) ? idx->data : 0;
    if (i < 0) i = 0; if (i > a->len) i = a->len;
    if (a->len == a->cap) {
        a->cap = a->cap ? a->cap * 2 : 8;
        a->items = realloc(a->items, (size_t)a->cap * sizeof(TessValue*));
    }
    memmove(a->items + i + 1, a->items + i, (size_t)(a->len - i) * sizeof(TessValue*));
    a->items[i] = item;
    a->len++;
    return self;
}
TessValue* _tess_mod_array_remove(TessValue* self, TessValue* val) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    for (int64_t i = 0; i < a->len; i++) {
        TessValue* eq = tess_eq(a->items[i], val);
        if (eq && eq->tag == TESS_BOOL && eq->data) {
            memmove(a->items + i, a->items + i + 1, (size_t)(a->len - i - 1) * sizeof(TessValue*));
            a->len--;
            break;
        }
    }
    return self;
}
TessValue* _tess_mod_array_clear(TessValue* self) {
    if (self && self->tag == TESS_ARRAY) {
        TessArray* a = (TessArray*)i64_to_ptr(self->data);
        a->len = 0;
    }
    return self;
}
TessValue* _tess_mod_array_sort(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    /* Bubble sort sencillo — suficiente para arrays de tamaño normal */
    for (int64_t i = 0; i < a->len - 1; i++) {
        for (int64_t j = 0; j < a->len - 1 - i; j++) {
            TessValue* lt = tess_lt(a->items[j+1], a->items[j]);
            if (lt && lt->tag == TESS_BOOL && lt->data) {
                TessValue* tmp  = a->items[j];
                a->items[j]     = a->items[j+1];
                a->items[j+1]   = tmp;
            }
        }
    }
    return self;
}
TessValue* _tess_mod_array_reverse(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return self;
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    for (int64_t i = 0, j = a->len - 1; i < j; i++, j--) {
        TessValue* tmp = a->items[i];
        a->items[i]    = a->items[j];
        a->items[j]    = tmp;
    }
    return self;
}
TessValue* _tess_mod_array_slice(TessValue* self, TessValue* a_tv, TessValue* b_tv) {
    if (!self || self->tag != TESS_ARRAY) return tess_array_new();
    TessArray* a    = (TessArray*)i64_to_ptr(self->data);
    int64_t start   = (a_tv && a_tv->tag == TESS_INT) ? a_tv->data : 0;
    int64_t end     = (b_tv && b_tv->tag == TESS_INT) ? b_tv->data : a->len;
    if (start < 0) start = 0; if (end > a->len) end = a->len;
    TessValue* out  = tess_array_new();
    for (int64_t i = start; i < end; i++) tess_array_push(out, a->items[i]);
    return out;
}
TessValue* _tess_mod_array_concat(TessValue* self, TessValue* other) {
    TessValue* out = tess_array_new();
    if (self && self->tag == TESS_ARRAY) {
        TessArray* a = (TessArray*)i64_to_ptr(self->data);
        for (int64_t i = 0; i < a->len; i++) tess_array_push(out, a->items[i]);
    }
    if (other && other->tag == TESS_ARRAY) {
        TessArray* b = (TessArray*)i64_to_ptr(other->data);
        for (int64_t i = 0; i < b->len; i++) tess_array_push(out, b->items[i]);
    }
    return out;
}
TessValue* _tess_mod_array_contains(TessValue* self, TessValue* val) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_bool(0);
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    for (int64_t i = 0; i < a->len; i++) {
        TessValue* eq = tess_eq(a->items[i], val);
        if (eq && eq->tag == TESS_BOOL && eq->data) return tess_make_bool(1);
    }
    return tess_make_bool(0);
}
TessValue* _tess_mod_array_indexOf(TessValue* self, TessValue* val) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_int(-1);
    TessArray* a = (TessArray*)i64_to_ptr(self->data);
    for (int64_t i = 0; i < a->len; i++) {
        TessValue* eq = tess_eq(a->items[i], val);
        if (eq && eq->tag == TESS_BOOL && eq->data) return tess_make_int(i);
    }
    return tess_make_int(-1);
}
TessValue* _tess_mod_array_join(TessValue* self, TessValue* sep_tv) {
    if (!self || self->tag != TESS_ARRAY) return tess_make_string(strdup(""));
    TessArray* a   = (TessArray*)i64_to_ptr(self->data);
    char* sep      = (sep_tv && sep_tv->tag == TESS_STRING) ? (char*)i64_to_ptr(sep_tv->data) : "";
    int seplen     = (int)strlen(sep);
    /* calcular tamaño total */
    size_t total   = 0;
    char** parts   = malloc((size_t)a->len * sizeof(char*));
    for (int64_t i = 0; i < a->len; i++) {
        parts[i] = tess_val_to_cstr_heap(a->items[i]);
        total   += strlen(parts[i]) + (i > 0 ? (size_t)seplen : 0);
    }
    char* r = malloc(total + 1); r[0] = '\0';
    for (int64_t i = 0; i < a->len; i++) {
        if (i > 0) strcat(r, sep);
        strcat(r, parts[i]);
        free(parts[i]);
    }
    free(parts);
    return tess_make_string(r);
}
TessValue* _tess_mod_array_unique(TessValue* self) {
    if (!self || self->tag != TESS_ARRAY) return tess_array_new();
    TessArray* a   = (TessArray*)i64_to_ptr(self->data);
    TessValue* out = tess_array_new();
    for (int64_t i = 0; i < a->len; i++) {
        TessValue* found = _tess_mod_array_contains(out, a->items[i]);
        if (!found || !found->data) tess_array_push(out, a->items[i]);
    }
    return out;
}
TessValue* _tess_mod_array_flatten(TessValue* self) {
    TessValue* out = tess_array_new();
    if (!self || self->tag != TESS_ARRAY) return out;
    TessArray* a   = (TessArray*)i64_to_ptr(self->data);
    for (int64_t i = 0; i < a->len; i++) {
        TessValue* item = a->items[i];
        if (item && item->tag == TESS_ARRAY) {
            TessArray* sub = (TessArray*)i64_to_ptr(item->data);
            for (int64_t j = 0; j < sub->len; j++) tess_array_push(out, sub->items[j]);
        } else {
            tess_array_push(out, item);
        }
    }
    return out;
}
TessValue* _tess_mod_array_typeString(TessValue* self) {
    return tess_make_string(tess_val_to_cstr_heap(self));
}

/* ---------------------------------------------------------------------------
 * NULL
 * ------------------------------------------------------------------------- */
TessValue* _tess_mod_null_isNull(TessValue* self)    { return tess_make_bool(1); }
TessValue* _tess_mod_null_isArray(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_null_isString(TessValue* self)  { return tess_make_bool(0); }
TessValue* _tess_mod_null_isInt(TessValue* self)     { return tess_make_bool(0); }
TessValue* _tess_mod_null_isFloat(TessValue* self)   { return tess_make_bool(0); }
TessValue* _tess_mod_null_isBool(TessValue* self)    { return tess_make_bool(0); }
TessValue* _tess_mod_null_type(TessValue* self)      { return tess_make_string(strdup("null")); }
TessValue* _tess_mod_null_typeString(TessValue* self){ return tess_make_string(strdup("null")); }
/* ---------------------------------------------------------------------------
 * DYNAMIC dispatchers — _tess_mod_dynamic_{metodo}
 * Usados cuando el tipo de la variable es DYNAMIC en tiempo de compilación.
 * Despachan al método correcto según el tag del TessValue en tiempo de ejecución.
 * ------------------------------------------------------------------------- */

TessValue* _tess_mod_dynamic_contains(TessValue* self, TessValue* val) {
    if (!self) return tess_make_bool(0);
    if (self->tag == TESS_ARRAY)  return _tess_mod_array_contains(self, val);
    if (self->tag == TESS_STRING) return _tess_mod_string_contains(self, val);
    return tess_make_bool(0);
}

TessValue* _tess_mod_dynamic_indexOf(TessValue* self, TessValue* val) {
    if (!self) return tess_make_int(-1);
    if (self->tag == TESS_ARRAY)  return _tess_mod_array_indexOf(self, val);
    if (self->tag == TESS_STRING) return _tess_mod_string_indexOf(self, val);
    return tess_make_int(-1);
}

TessValue* _tess_mod_dynamic_length(TessValue* self) {
    if (!self) return tess_make_int(0);
    if (self->tag == TESS_ARRAY)  return tess_make_int(((TessArray*)i64_to_ptr(self->data))->len);
    if (self->tag == TESS_STRING) return _tess_mod_string_length(self);
    return tess_make_int(0);
}

TessValue* _tess_mod_dynamic_typeInt(TessValue* self) {
    if (!self) return tess_make_int(0);
    if (self->tag == TESS_STRING) return _tess_mod_string_typeInt(self);
    if (self->tag == TESS_INT)    return self;
    if (self->tag == TESS_FLOAT)  return tess_make_int((int64_t)bits_to_f64(self->data));
    if (self->tag == TESS_BOOL)   return tess_make_int(self->data ? 1 : 0);
    return tess_make_int(0);
}

TessValue* _tess_mod_dynamic_typeFloat(TessValue* self) {
    if (!self) return tess_make_float(0.0);
    if (self->tag == TESS_STRING) return _tess_mod_string_typeFloat(self);
    if (self->tag == TESS_INT)    return tess_make_float((double)self->data);
    if (self->tag == TESS_FLOAT)  return self;
    return tess_make_float(0.0);
}

TessValue* _tess_mod_dynamic_typeString(TessValue* self) {
    if (!self) return tess_make_string(strdup("null"));
    if (self->tag == TESS_STRING) return self;
    if (self->tag == TESS_ARRAY)  return _tess_mod_array_typeString(self);
    return tess_make_string(tess_val_to_cstr_heap(self));
}

TessValue* _tess_mod_dynamic_typeBool(TessValue* self) {
    if (!self) return tess_make_bool(0);
    if (self->tag == TESS_STRING) return _tess_mod_string_typeBool(self);
    return tess_make_bool(tess_value_truthy(self));
}

TessValue* _tess_mod_dynamic_isEmpty(TessValue* self) {
    if (!self) return tess_make_bool(1);
    if (self->tag == TESS_ARRAY)  return _tess_mod_array_isEmpty(self);
    if (self->tag == TESS_STRING) return _tess_mod_string_isEmpty(self);
    return tess_make_bool(0);
}

TessValue* _tess_mod_dynamic_type(TessValue* self) {
    if (!self) return tess_make_string(strdup("null"));
    if (self->tag == TESS_INT)    return tess_make_string(strdup("int"));
    if (self->tag == TESS_FLOAT)  return tess_make_string(strdup("float"));
    if (self->tag == TESS_BOOL)   return tess_make_string(strdup("bool"));
    if (self->tag == TESS_STRING) return tess_make_string(strdup("string"));
    if (self->tag == TESS_ARRAY)  return tess_make_string(strdup("array"));
    if (self->tag == TESS_DICT)   return tess_make_string(strdup("dict"));
    if (self->tag == TESS_NULL)   return tess_make_string(strdup("null"));
    return tess_make_string(strdup("dynamic"));
}

TessValue* _tess_mod_dynamic_isArray(TessValue* self)  { return tess_make_bool(self && self->tag == TESS_ARRAY); }
TessValue* _tess_mod_dynamic_isString(TessValue* self) { return tess_make_bool(self && self->tag == TESS_STRING); }
TessValue* _tess_mod_dynamic_isInt(TessValue* self)    { return tess_make_bool(self && self->tag == TESS_INT); }
TessValue* _tess_mod_dynamic_isFloat(TessValue* self)  { return tess_make_bool(self && self->tag == TESS_FLOAT); }
TessValue* _tess_mod_dynamic_isBool(TessValue* self)   { return tess_make_bool(self && self->tag == TESS_BOOL); }

TessValue* _tess_mod_dynamic_reverse(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY)  return _tess_mod_array_reverse(self);
    if (self->tag == TESS_STRING) return _tess_mod_string_reverse(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_first(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_array_first(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_last(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_array_last(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_push(TessValue* self, TessValue* val) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_arr_push(self, val);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_pop(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_array_pop(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_join(TessValue* self, TessValue* sep) {
    if (!self) return tess_make_string(strdup(""));
    if (self->tag == TESS_ARRAY) return _tess_mod_array_join(self, sep);
    return tess_make_string(strdup(""));
}

TessValue* _tess_mod_dynamic_slice(TessValue* self, TessValue* a, TessValue* b) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY)  return _tess_mod_array_slice(self, a, b);
    if (self->tag == TESS_STRING) return _tess_mod_string_slice(self, a, b);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_toUpperCase(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_STRING) return _tess_mod_string_toUpperCase(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_toLowerCase(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_STRING) return _tess_mod_string_toLowerCase(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_trim(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_STRING) return _tess_mod_string_trim(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_split(TessValue* self, TessValue* sep) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_STRING) return _tess_mod_string_split(self, sep);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_sort(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_array_sort(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_unique(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_array_unique(self);
    return tess_make_null();
}

TessValue* _tess_mod_dynamic_flatten(TessValue* self) {
    if (!self) return tess_make_null();
    if (self->tag == TESS_ARRAY) return _tess_mod_array_flatten(self);
    return tess_make_null();
}