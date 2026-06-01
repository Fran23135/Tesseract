/* =============================================================================
 * runtime.h — Tesseract Runtime Library (Interfaz Pública)
 * =============================================================================
 * Este archivo debe ser incluido por el código generado por tesscodegen.py
 * y por cualquier otro código que interactúe con el runtime.
 *
 * Todas las funciones implementadas en runtime.c se declaran aquí.
 *
 * Compilación: No requiere nada especial, solo incluir este header.
 * ============================================================================= */

#ifndef TESSERACT_RUNTIME_H
#define TESSERACT_RUNTIME_H
#define TESS_NORETURN __attribute__((noreturn))
#include <stdint.h>
#include <setjmp.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =============================================================================
 * TAGS PARA TESSVALUE
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
#define TESS_EXCEPTION 8   /* solo para uso interno del runtime */

/* =============================================================================
 * ESTRUCTURAS PÚBLICAS (opacas o completamente definidas)
 * ============================================================================= */

/* Estructura base de todo valor Tesseract (coincide con el IR) */
typedef struct {
    int32_t  tag;
    int64_t  data;   /* El compilador añade padding de 4 bytes antes de data */
} TessValue;

/* Información de tipo para arrays, tuplas y diccionarios tipados */
typedef struct TessTypeInfo {
    int32_t                tag;       /* TESS_* tag, -1 = dinámico */
    struct TessTypeInfo*   inner;     /* para array<X> y tuple<X> */
    struct TessTypeInfo*   key_ti;    /* para dict<K,V> — clave */
    struct TessTypeInfo*   val_ti;    /* para dict<K,V> — valor */
    int64_t                limit;     /* -1 = sin límite */
} TessTypeInfo;

/* =============================================================================
 * CONSTRUCTORES DE TessValue
 * ============================================================================= */
TessValue* tess_make_int(int64_t v);
TessValue* tess_make_float(double v);
TessValue* tess_make_bool(int v);          /* v != 0 → true */
TessValue* tess_make_string(char* s);      /* se copia internamente */
TessValue* tess_make_null(void);

/* =============================================================================
 * I/O BÁSICO (impresión directa, sin crear TessValue)
 * ============================================================================= */
void tess_print_int(int64_t v);
void tess_print_float(double v);
void tess_print_bool(int v);
void tess_print_string(char* s);
void tess_print_null(void);
void tess_print_value(TessValue* tv);

/* =============================================================================
 * LECTURA DESDE STDIN
 * ============================================================================= */
char*     tess_read_string(void);   /* retorna heap string, liberar con free */
int64_t   tess_read_int(void);
double    tess_read_float(void);

/* =============================================================================
 * CONVERSIONES DE TessValue A TIPOS NATIVOS
 * ============================================================================= */
int64_t  tess_to_int(TessValue* tv);
double   tess_to_float(TessValue* tv);
int      tess_to_bool(TessValue* tv);      /* truthy → 1, falsy → 0 */
char*    tess_to_string(TessValue* tv);    /* retorna buffer interno estático */
int      tess_value_truthy(TessValue* tv); /* igual que tess_to_bool */

/* =============================================================================
 * OPERACIONES ARITMÉTICAS
 * ============================================================================= */
TessValue* tess_add(TessValue* a, TessValue* b);
TessValue* tess_sub(TessValue* a, TessValue* b);
TessValue* tess_mul(TessValue* a, TessValue* b);
TessValue* tess_div(TessValue* a, TessValue* b);
TessValue* tess_mod(TessValue* a, TessValue* b);

/* =============================================================================
 * COMPARACIONES (retornan TessValue* con tag TESS_BOOL)
 * ============================================================================= */
TessValue* tess_eq(TessValue* a, TessValue* b);
TessValue* tess_neq(TessValue* a, TessValue* b);
TessValue* tess_lt(TessValue* a, TessValue* b);
TessValue* tess_gt(TessValue* a, TessValue* b);
TessValue* tess_lte(TessValue* a, TessValue* b);
TessValue* tess_gte(TessValue* a, TessValue* b);

/* =============================================================================
 * OPERACIONES LÓGICAS Y UNARIAS
 * ============================================================================= */
TessValue* tess_and(TessValue* a, TessValue* b);  /* cortocircuito */
TessValue* tess_or(TessValue* a, TessValue* b);   /* cortocircuito */
TessValue* tess_not(TessValue* a);
TessValue* tess_neg(TessValue* a);                /* -a */
TessValue* tess_inc(TessValue* a);                /* a + 1 */
TessValue* tess_dec(TessValue* a);                /* a - 1 */

/* =============================================================================
 * CONCATENACIÓN DE STRINGS (operador .)
 * ============================================================================= */
TessValue* tess_concat(TessValue* a, TessValue* b);

/* =============================================================================
 * ARRAYS DINÁMICOS
 * ============================================================================= */
TessValue* tess_array_new(void);                        /* array dinámico sin tipo */
TessValue* tess_array_new_typed(TessTypeInfo* ti);      /* array con tipo estático */
void       tess_array_push(TessValue* arr_tv, TessValue* item);
TessValue* tess_array_get(TessValue* arr_tv, int64_t idx);  /* soporta índices negativos */
void       tess_array_set(TessValue* arr_tv, int64_t idx, TessValue* val);
int64_t    tess_array_len(TessValue* arr_tv);

/* =============================================================================
 * TUPLAS (inmutables en construcción)
 * ============================================================================= */
TessValue* tess_tuple_new(void);                        /* tuple dinámica */
TessValue* tess_tuple_new_typed(TessTypeInfo* ti);      /* tuple con tipo estático */
void       tess_tuple_push(TessValue* tup_tv, TessValue* item);
TessValue* tess_tuple_get(TessValue* tup_tv, int64_t idx);
int64_t    tess_tuple_len(TessValue* tup_tv);

/* =============================================================================
 * DICCIONARIOS (hash table con cadenas como clave)
 * ============================================================================= */
TessValue* tess_dict_new(void);                         /* dict dinámico */
TessValue* tess_dict_new_typed(TessTypeInfo* ti);       /* dict con tipos estáticos */
TessValue* tess_dict_get(TessValue* dict_tv, char* key);
void       tess_dict_set(TessValue* dict_tv, char* key, TessValue* val);
int        tess_dict_has(TessValue* dict_tv, char* key);   /* retorna 0/1 */

/* =============================================================================
 * INFORMACIÓN DE TIPOS (para tipado estático opcional)
 * ============================================================================= */
TessTypeInfo* tess_typeinfo_new(int32_t tag);
void          tess_typeinfo_set_inner(TessTypeInfo* parent, TessTypeInfo* inner);
void          tess_typeinfo_set_key_val(TessTypeInfo* ti,
                                        TessTypeInfo* key_ti, TessTypeInfo* val_ti);
void          tess_typeinfo_set_limit(TessTypeInfo* ti, int64_t limit);
int           tess_typeinfo_check(TessValue* tv, TessTypeInfo* ti); /* 1 si cumple */

/* =============================================================================
 * OBJETOS Y OOP (básico)
 * ============================================================================= */
/* Estructura opaca para objetos */
typedef struct TessObject TessObject;

TessObject* tess_object_new(char* class_name);
TessValue*  tess_object_get_attr(TessObject* obj, char* attr_name);
void        tess_object_set_attr(TessObject* obj, char* attr_name, TessValue* val);
TessValue*  tess_object_call(TessObject* obj, char* method_name,
                             TessValue* args_arr, int64_t args_count);
int         tess_object_is_instance(TessObject* obj, char* class_name);

/* =============================================================================
 * EXCEPCIONES (con setjmp/longjmp)
 * ============================================================================= */
TessValue* tess_exception_new(char* class_name, char* message);
char*      tess_exception_class(TessValue* exc);
char*      tess_exception_message(TessValue* exc);

/* Uso: if (tess_try_begin() == 0) { ... } else { manejar excepción } */
int        tess_try_begin(void);          /* retorna 0 en bloque try, 1 en catch */
void       tess_throw(TessValue* exc) __attribute__((noreturn));
TessValue* tess_catch_get(void);           /* obtiene la excepción capturada */
void       tess_try_end(void);             /* sale del bloque try */

/* =============================================================================
 * FUNCIONES AUXILIARES (validación de tipos)
 * ============================================================================= */
int tess_check_elem_type(TessValue* tv, int32_t expected_tag);

#ifdef __cplusplus
}
#endif

#endif /* TESSERACT_RUNTIME_H */