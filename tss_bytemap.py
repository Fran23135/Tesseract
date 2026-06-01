"""
tss_bytemap.py — Mapa completo de bytes del sistema Tesseract.

═══════════════════════════════════════════════════════════════
 TYPE CODES  (u8)
═══════════════════════════════════════════════════════════════
  0x00  any
  0x01  int
  0x02  float
  0x03  string
  0x04  bool
  0x05  array    → [u8 elem_type]  +  [wstr limit_expr] si DECL_HAS_LENGTH
  0x06  range
  0x07  tuple    → [u8 count] [u8 type]*
  0x08  dict     → [u8 key_type] [u8 val_type]
  0x09  struct   → [pstr struct_name]
  0x0A  void
  0x0B  null
  0xFF  none/untyped

═══════════════════════════════════════════════════════════════
 EXPORT FLAGS  (u8 bitmask)
═══════════════════════════════════════════════════════════════
  bit 0  0x01  const

═══════════════════════════════════════════════════════════════
 FUNCTION FLAGS (.tmc)  (u8 bitmask)
═══════════════════════════════════════════════════════════════
  bit 0  0x01  native
  bit 1  0x02  has_id
  bit 2  0x04  has_return

═══════════════════════════════════════════════════════════════
 SYMBOL TYPES (.tsslk)
═══════════════════════════════════════════════════════════════
  0x01  function
  0x02  variable
  0x03  constant
  0x04  struct        ← struct es su propia categoría, NO function
  0x05  class

═══════════════════════════════════════════════════════════════
 DECL FLAGS  (u8 bitmask)  — para declaraciones de variable
═══════════════════════════════════════════════════════════════
  bit 0  0x01  has_type      tiene explicitType → variable TIPADA
  bit 1  0x02  is_dynamic    sin explicitType  → variable DINÁMICA
  bit 2  0x04  has_value     tiene expresión de valor
  bit 3  0x08  has_operation tiene operador (+=, etc)
  bit 4  0x10  has_length    tiene longitud: cantidad de elementos del array/dict/tuple
  bit 5  0x20  has_limit     tiene limit: array declarado con tamaño fijo (e.g. array[10])
                             Puede aparecer en cualquier VariableDeclaration, NO solo en structs

REGLA CRÍTICA sobre has_type vs is_dynamic:
  - Si value.explicitType existe   → has_type=1, is_dynamic=0
  - Si value.explicitType ausente  → has_type=0, is_dynamic=1
  Nunca ambos a la vez.

═══════════════════════════════════════════════════════════════
 CLASS/METHOD FLAGS  (u8 bitmask)
═══════════════════════════════════════════════════════════════
  CLASS:
    bit 0  0x01  has_modifier
    bit 1  0x02  has_extends
    bit 2  0x04  has_implements

  METHOD:
    bit 0  0x01  has_modifier
    bit 1  0x02  has_return_type
    bit 2  0x04  has_explicit_type

═══════════════════════════════════════════════════════════════
 LIB FLAGS  (u8 bitmask)
═══════════════════════════════════════════════════════════════
  bit 0  0x01  has_alias
  bit 1  0x02  has_functions
  bit 2  0x04  has_func_aliases

═══════════════════════════════════════════════════════════════
 OPCODES
═══════════════════════════════════════════════════════════════
  0x00  NOP
  0x01  FUNC_DEF       pstr name, u8 param_count, [pstr pname, type]*, u8 flags, [type return]?
  0x02  FUNC_END

  0x10  VAR_DECL       pstr name, decl_payload
  0x11  CONST_DECL     pstr name, decl_payload
  0x12  VAR_ASSIGN     pstr name, u8 flags, [wstr op]?, wstr value_expr
  0x13  VAR_DECL_STRUCT  pstr name, decl_payload
  0x14  CONST_DECL_STRUCT pstr name, decl_payload
  0x15  MOD_ASSIGN     pstr name, u8 flags, [wstr op]?, wstr value_expr

  decl_payload:
    u8 flags
    [type]?          si has_type
    [wstr value]?    si has_value
    [wstr op]?       si has_operation
    [wstr length]?   si has_length
    [wstr limit]?    si has_limit

  0x20  IF             wstr condition
  0x21  ELSE_IF        wstr condition
  0x22  ELSE
  0x23  END_IF
  0x24  WHILE          wstr condition
  0x25  END_WHILE
  0x26  DO_WHILE
  0x27  DO_WHILE_COND  wstr condition
  0x28  END_DO_WHILE
  0x29  FOR            pstr var, wstr iterator_expr, u8 is_declared
  0x2A  END_FOR
  0x2B  SWITCH         wstr value_expr
  0x2C  CASE           wstr case_value
  0x2D  DEFAULT_CASE
  0x2E  END_SWITCH
  0x2F  BREAK
  0x30  CONTINUE

  0x31  CALL_EXPR      wstr function, u8 has_args, [wstr args]?, u8 has_param_type, [pstr param_type]?
  0x32  FUNC_CALL      wstr function, u8 has_params, [wstr params]?
  0x33  RETURN         u8 has_value, [wstr value]?

  0x40  POST_INC       pstr name
  0x41  PRE_INC        pstr name
  0x42  POST_DEC       pstr name
  0x43  PRE_DEC        pstr name

  0x50  CLASS_DECL     pstr name, u8 flags, [pstr mod]?, [pstr extends]?, [pstr implements]?
  0x51  CLASS_END
  0x52  INTERFACE_DECL pstr name, u8 flags, [pstr extends]?
  0x53  INTERFACE_END
  0x54  STRUCT_DECL    pstr name
  0x55  STRUCT_END
  0x56  METHOD_DECL    pstr name, u8 flags, u8 param_count, [pstr pname, type]*, [pstr mod]?, [type ret]?
  0x57  METHOD_END
  0x58  CTOR_DECL      pstr name, u8 param_count, [pstr pname, type]*
  0x59  CTOR_END
  0x5A  ATTR_DECL      pstr name, decl_payload
  0x5B  ATTR_CONST_DECL pstr name, decl_payload
  0x5C  NEW_OBJECT     pstr class_name, u8 has_args, [wstr args]?
  0x5D  THIS_ACCESS    pstr member
  0x5E  THIS_CALL      pstr member, u8 has_args, [wstr args]?
  0x5F  THIS_ASSIGN    pstr member, wstr value_expr
  0x60  SUPER_ACCESS   pstr member
  0x61  SUPER_CALL     pstr member, u8 has_args, [wstr args]?
  0x62  SUPER_ASSIGN   pstr member, wstr value_expr
  0x63  SUPER_CTOR     u8 has_args, [wstr args]?

  0x70  TRY
  0x71  CATCH          u8 has_type, [pstr exc_type]?, u8 has_var, [pstr exc_var]?
  0x72  FINALLY
  0x73  END_TRY
  0x74  THROW          wstr exception_expr

  0x80  LIB_CALL       pstr module, u8 flags, [pstr alias]?, [u8 count, pstr*]?, [u8 count, pstr*]?
"""

import struct

MAGIC_TMC   = b"TSMC"
MAGIC_TSSLK = b"TSSLK"
FORMAT_VER  = 0x01

# TYPE CODES
TYPE_ANY    = 0x00
TYPE_INT    = 0x01
TYPE_FLOAT  = 0x02
TYPE_STRING = 0x03
TYPE_BOOL   = 0x04
TYPE_ARRAY  = 0x05
TYPE_RANGE  = 0x06
TYPE_TUPLE  = 0x07
TYPE_DICT   = 0x08
TYPE_STRUCT = 0x09
TYPE_VOID   = 0x0A
TYPE_NULL   = 0x0B
TYPE_NONE   = 0xFF

TYPE_NAMES = {
    TYPE_ANY:"any", TYPE_INT:"int", TYPE_FLOAT:"float", TYPE_STRING:"string",
    TYPE_BOOL:"bool", TYPE_ARRAY:"array", TYPE_RANGE:"range", TYPE_TUPLE:"tuple",
    TYPE_DICT:"dict", TYPE_STRUCT:"struct", TYPE_VOID:"void", TYPE_NULL:"null",
    TYPE_NONE:"none",
}
TYPES = {v: k for k, v in TYPE_NAMES.items()}

# FUNCTION FLAGS (.tmc)
FLAG_NATIVE     = 0x01
FLAG_HAS_ID     = 0x02
FLAG_HAS_RETURN = 0x04

# SYMBOL TYPES (.tsslk)
SYM_FUNCTION = 0x01
SYM_VARIABLE = 0x02
SYM_CONSTANT = 0x03
SYM_STRUCT   = 0x04   # struct es su propia categoría
SYM_CLASS    = 0x05

SYM_NAMES = {
    SYM_FUNCTION:"function", SYM_VARIABLE:"variable",
    SYM_CONSTANT:"constant", SYM_STRUCT:"struct", SYM_CLASS:"class",
}

# DECL FLAGS
DECL_HAS_TYPE      = 0x01   # explicitType presente → tipada
DECL_IS_DYNAMIC    = 0x02   # explicitType ausente  → dinámica
DECL_HAS_VALUE     = 0x04
DECL_HAS_OPERATION = 0x08
DECL_HAS_LENGTH    = 0x10   # longitud: cantidad de elementos actuales del array/dict/tuple
DECL_HAS_LIMIT     = 0x20   # limit: array declarado con tamaño fijo (array[10]) — cualquier VarDecl

# CLASS FLAGS
CLASS_HAS_MODIFIER   = 0x01
CLASS_HAS_EXTENDS    = 0x02
CLASS_HAS_IMPLEMENTS = 0x04

# METHOD FLAGS
METHOD_HAS_MODIFIER  = 0x01
METHOD_HAS_RETURN    = 0x02
METHOD_HAS_EXPL_TYPE = 0x04

# LIB FLAGS
LIB_HAS_ALIAS        = 0x01
LIB_HAS_FUNCTIONS    = 0x02
LIB_HAS_FUNC_ALIASES = 0x04

# TMC CLASS SECTION FLAGS  (u8, en la sección CLASSES del .tmc)
#   Indica qué secciones tiene una clase en el binario público.
TMC_CLASS_HAS_CTOR    = 0x01   # tiene bloque constructor
TMC_CLASS_HAS_METHODS = 0x02   # tiene métodos

# ═══════════════════════════════════════════════════════════════
#  MAIN.TBC — Orquestador de versiones para Klein / intérprete
# ═══════════════════════════════════════════════════════════════
#
#  Formato binario:
#
#    MAGIC      6 bytes   b"TSORCH"
#    VER        u8        0x01
#    ── Header ──────────────────────────────────────────────────
#    pstr       module_name
#    ── Version seleccionada (variable física editable) ──────────
#    pstr       version        versión que el usuario define en specs.tlib
#                              → se usa para construir el path:
#                                libs/<module>/versions/<version>/
#                              Klein puede sobrescribir este campo al
#                              cambiar la versión activa sin recompilar.
#    ── Contador de compilación (v_count) ────────────────────────
#    pstr       v_count        contador automático de build, independiente
#                              del nombre de versión del usuario.
#                              Empieza en "1.0.0" y sube:
#                                1.0.0 → 1.0.1 → … → 1.0.9
#                                      → 1.1.0 → … → 1.9.9
#                                      → 2.0.0 → …
#                              Klein usa este campo para saber cuál
#                              instalación es realmente la más reciente,
#                              independientemente del nombre que le ponga
#                              el autor a su versión.
#    ── Referencias de archivos ─────────────────────────────────
#    u8         file_count       número de referencias
#    per file:
#      u8       ref_type         tipo (REF_LINKER | REF_MODULE | REF_DEPS)
#      pstr     rel_path         ruta relativa desde libs/<module>/
#                                construida como: versions/<version>/<file>
#    ── Info de carga para el intérprete ────────────────────────
#    u8         load_flags       bitmask (LOAD_*)
#    [pstr      entry_point]?    solo si LOAD_HAS_ENTRY
#
MAGIC_ORCH = b"TSORCH"

# MAIN.TBC — Tipos de referencia  (u8)
REF_LINKER = 0x01   # linker.tbc  — bytecode compilado del código fuente
REF_MODULE = 0x02   # .tmc        — interfaz pública del módulo
REF_DEPS   = 0x03   # deps/       — carpeta de dependencias externas

REF_NAMES = {
    REF_LINKER: "linker",
    REF_MODULE: "module",
    REF_DEPS:   "deps",
}

# MAIN.TBC — Flags de carga  (u8 bitmask)
#   bit 0  0x01  has_entry_point  tiene entry point explícito (pstr a continuación)
#   bit 1  0x02  preload          precargar todos los exports al cargar la librería
#   bit 2  0x04  lazy             carga diferida: solo al primer uso
LOAD_HAS_ENTRY = 0x01
LOAD_PRELOAD   = 0x02
LOAD_LAZY      = 0x04


def increment_v_count(v: str) -> str:
    """
    Incrementa el contador de compilación v_count.

    Formato: "MAJOR.MINOR.PATCH"  (cada componente 0-9)
      1.0.0 → 1.0.1
      1.0.9 → 1.1.0
      1.9.9 → 2.0.0
    """
    try:
        parts = [int(x) for x in str(v).split(".")]
        if len(parts) != 3:
            return "1.0.1"
        major, minor, patch = parts
        patch += 1
        if patch > 9:
            patch = 0
            minor += 1
        if minor > 9:
            minor = 0
            major += 1
        return f"{major}.{minor}.{patch}"
    except (ValueError, AttributeError):
        return "1.0.1"


def read_v_count(main_tbc_path) -> str:
    """
    Lee el v_count del main.tbc existente.
    Si el archivo no existe o está corrupto, retorna "1.0.0"
    (primer build → el siguiente incrementará a 1.0.1 antes de escribir).
    
    Offset del v_count en el binario:
      6 (MAGIC) + 1 (VER) + 1+len(module_name) + 1+len(version) + 1 = posición del string
    """
    from pathlib import Path as _Path
    p = _Path(main_tbc_path)
    if not p.exists():
        return "1.0.0"
    try:
        data = p.read_bytes()
        pos  = 7                              # saltar MAGIC(6) + VER(1)
        name_len = data[pos]; pos += 1 + name_len   # saltar module_name
        ver_len  = data[pos]; pos += 1 + ver_len    # saltar version
        vc_len   = data[pos]; pos += 1
        return data[pos:pos + vc_len].decode("utf-8", errors="replace")
    except Exception:
        return "1.0.0"

# TMC CLASS SECTION FLAGS  (u8, en la sección CLASSES del .tmc)
#   Indica qué secciones tiene una clase en el binario público.
TMC_CLASS_HAS_CTOR    = 0x01   # tiene bloque constructor
TMC_CLASS_HAS_METHODS = 0x02   # tiene métodos

# OPCODES
OP_NOP=0x00; OP_FUNC_DEF=0x01; OP_FUNC_END=0x02
OP_VAR_DECL=0x10; OP_CONST_DECL=0x11; OP_VAR_ASSIGN=0x12
OP_VAR_DECL_STRUCT=0x13; OP_CONST_DECL_STRUCT=0x14; OP_MOD_ASSIGN=0x15
OP_IF=0x20; OP_ELSE_IF=0x21; OP_ELSE=0x22; OP_END_IF=0x23
OP_WHILE=0x24; OP_END_WHILE=0x25; OP_DO_WHILE=0x26
OP_DO_WHILE_COND=0x27; OP_END_DO_WHILE=0x28
OP_FOR=0x29; OP_END_FOR=0x2A; OP_SWITCH=0x2B; OP_CASE=0x2C
OP_DEFAULT_CASE=0x2D; OP_END_SWITCH=0x2E; OP_BREAK=0x2F; OP_CONTINUE=0x30
OP_CALL_EXPR=0x31; OP_FUNC_CALL=0x32; OP_RETURN=0x33
OP_POST_INC=0x40; OP_PRE_INC=0x41; OP_POST_DEC=0x42; OP_PRE_DEC=0x43
OP_CLASS_DECL=0x50; OP_CLASS_END=0x51; OP_INTERFACE_DECL=0x52; OP_INTERFACE_END=0x53
OP_STRUCT_DECL=0x54; OP_STRUCT_END=0x55; OP_METHOD_DECL=0x56; OP_METHOD_END=0x57
OP_CTOR_DECL=0x58; OP_CTOR_END=0x59; OP_ATTR_DECL=0x5A; OP_ATTR_CONST_DECL=0x5B
OP_NEW_OBJECT=0x5C; OP_THIS_ACCESS=0x5D; OP_THIS_CALL=0x5E; OP_THIS_ASSIGN=0x5F
OP_SUPER_ACCESS=0x60; OP_SUPER_CALL=0x61; OP_SUPER_ASSIGN=0x62; OP_SUPER_CTOR=0x63
OP_TRY=0x70; OP_CATCH=0x71; OP_FINALLY=0x72; OP_END_TRY=0x73; OP_THROW=0x74
OP_LIB_CALL=0x80

OPCODE_NAMES = {
    0x00:"NOP",0x01:"FUNC_DEF",0x02:"FUNC_END",
    0x10:"VAR_DECL",0x11:"CONST_DECL",0x12:"VAR_ASSIGN",
    0x13:"VAR_DECL_STRUCT",0x14:"CONST_DECL_STRUCT",0x15:"MOD_ASSIGN",
    0x20:"IF",0x21:"ELSE_IF",0x22:"ELSE",0x23:"END_IF",
    0x24:"WHILE",0x25:"END_WHILE",0x26:"DO_WHILE",0x27:"DO_WHILE_COND",0x28:"END_DO_WHILE",
    0x29:"FOR",0x2A:"END_FOR",0x2B:"SWITCH",0x2C:"CASE",
    0x2D:"DEFAULT_CASE",0x2E:"END_SWITCH",0x2F:"BREAK",0x30:"CONTINUE",
    0x31:"CALL_EXPR",0x32:"FUNC_CALL",0x33:"RETURN",
    0x40:"POST_INC",0x41:"PRE_INC",0x42:"POST_DEC",0x43:"PRE_DEC",
    0x50:"CLASS_DECL",0x51:"CLASS_END",0x52:"INTERFACE_DECL",0x53:"INTERFACE_END",
    0x54:"STRUCT_DECL",0x55:"STRUCT_END",0x56:"METHOD_DECL",0x57:"METHOD_END",
    0x58:"CTOR_DECL",0x59:"CTOR_END",0x5A:"ATTR_DECL",0x5B:"ATTR_CONST_DECL",
    0x5C:"NEW_OBJECT",0x5D:"THIS_ACCESS",0x5E:"THIS_CALL",0x5F:"THIS_ASSIGN",
    0x60:"SUPER_ACCESS",0x61:"SUPER_CALL",0x62:"SUPER_ASSIGN",0x63:"SUPER_CTOR",
    0x70:"TRY",0x71:"CATCH",0x72:"FINALLY",0x73:"END_TRY",0x74:"THROW",
    0x80:"LIB_CALL",
}

# ─── I/O helpers ─────────────────────────────────────────────────────────
def u8(v):  return struct.pack(">B", int(v) & 0xFF)
def u16(v): return struct.pack(">H", int(v) & 0xFFFF)
def u32(v): return struct.pack(">I", int(v) & 0xFFFFFFFF)
def i64(v): return struct.pack(">q", int(v))
def f64(v): return struct.pack(">d", float(v))

def pstr(text: str) -> bytes:
    enc = str(text).encode("utf-8")[:255]
    return u8(len(enc)) + enc

def wstr(text: str) -> bytes:
    enc = str(text).encode("utf-8")[:65535]
    return u16(len(enc)) + enc

def parse_type_code(ts: str) -> int:
    ts = str(ts).lower().strip().split("<")[0].split(":")[0].split(" ")[0]
    return TYPES.get(ts, TYPE_ANY)

def encode_type(type_str: str) -> bytes:
    """
    Codifica un tipo con su payload extendido.
    array<int>         → TYPE_ARRAY + TYPE_INT
    tuple<int,float>   → TYPE_TUPLE + count + types
    dict<string,int>   → TYPE_DICT + key_type + val_type
    struct:MyStruct    → TYPE_STRUCT + pstr(name)
    int/float/etc      → solo type code
    """
    ts = str(type_str).lower().strip()

    if ts.startswith("array"):
        inner = "any"
        if "<" in ts:
            inner = ts[ts.index("<")+1 : ts.rindex(">")].strip()
        return u8(TYPE_ARRAY) + u8(parse_type_code(inner))

    if ts.startswith("tuple"):
        parts = []
        if "<" in ts:
            inner = ts[ts.index("<")+1 : ts.rindex(">")]
            parts = [p.strip() for p in inner.split(",") if p.strip()]
        return u8(TYPE_TUPLE) + u8(len(parts)) + b"".join(u8(parse_type_code(p)) for p in parts)

    if ts.startswith("dict"):
        kt, vt = "any", "any"
        if "<" in ts:
            inner = ts[ts.index("<")+1 : ts.rindex(">")]
            kv = [p.strip() for p in inner.split(",")]
            if len(kv) >= 2: kt, vt = kv[0], kv[1]
        return u8(TYPE_DICT) + u8(parse_type_code(kt)) + u8(parse_type_code(vt))

    if ts.startswith("struct"):
        sname = ts.split(":", 1)[-1].strip() if ":" in ts else ts.split(" ", 1)[-1].strip()
        return u8(TYPE_STRUCT) + pstr(sname)
    prim = parse_type_code(ts)
    if prim != TYPE_ANY:
        return u8(prim)
    return u8(TYPE_STRUCT) + pstr(ts)
    #return u8(parse_type_code(ts))

def parse_params_str(params_value: str) -> list:
    """'x:float,y:int' → [('x','float'), ('y','int')]"""
    if not params_value or not str(params_value).strip():
        return []
    result = []
    for part in str(params_value).split(","):
        part = part.strip()
        if not part: continue
        if ":" in part:
            pname, ptype = part.split(":", 1)
            result.append((pname.strip(), ptype.strip()))
        else:
            result.append((part, "any"))
    return result