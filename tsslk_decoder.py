"""
tsslk_decoder.py
================
Decodifica un archivo .tsslk (bytecode de Tesseract) y produce exactamente
el mismo formato de AST dict que interpre.py espera (igual que ast_output.json).

Uso:
    from tsslk_decoder import decode_tsslk
    ast_data = decode_tsslk("programa.tsslk")
    interpreter.interpret(ast_data)

El decoder reconstruye cada nodo opcode→dict con el mismo esquema que
el compilador de Tesseract (.tss → JSON AST).

REGLAS DE FIDELIDAD (de ast_output.json):
  - Enteros se ponen como int:   "value": 2    (NO "value": "2")
  - Floats se ponen como float:  "value": 2.5  (NO "value": "2.5")
  - Strings del código llevan comillas en value: "value": '"Ana"'
  - null se pone como string:    "value": "null",  "type": "NULL"
  - Tipos nativos en minúsculas: int, float, string, bool, array, tuple, dict, range
  - Tipos personalizados (struct/class) se ponen tal cual como "type" y "explicitType"
  - explicitType solo aparece si la variable es tipada (DECL_HAS_TYPE)
  - dinamic solo aparece si DECL_IS_DYNAMIC
"""

import struct
import sys
from tss_bytemap import *


# ════════════════════════════════════════════════════════════════════════
#  LECTOR DE BYTES
# ════════════════════════════════════════════════════════════════════════
class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos  = 0

    def eof(self):        return self.pos >= len(self.data)
    def remaining(self):  return len(self.data) - self.pos
    def peek(self):       return self.data[self.pos] if not self.eof() else -1

    def read(self, n: int) -> bytes:
        chunk = self.data[self.pos:self.pos+n]
        self.pos += n
        return chunk

    def ru8(self)  -> int:   return struct.unpack(">B", self.read(1))[0]
    def ru16(self) -> int:   return struct.unpack(">H", self.read(2))[0]
    def ru32(self) -> int:   return struct.unpack(">I", self.read(4))[0]
    def ri64(self) -> int:   return struct.unpack(">q", self.read(8))[0]
    def rf64(self) -> float: return struct.unpack(">d", self.read(8))[0]

    def rpstr(self) -> str:
        n = self.ru8()
        return self.read(n).decode("utf-8", errors="replace")

    def rwstr(self) -> str:
        n = self.ru16()
        return self.read(n).decode("utf-8", errors="replace")

    def rtype_str(self) -> str:
        """
        Lee un type code con payload y devuelve el string de tipo
        tal como aparece en el AST (ej: 'int', 'array', 'range', 'persona').
        """
        tc = self.ru8()
        if tc == TYPE_ARRAY:
            inner = TYPE_NAMES.get(self.ru8(), 'any')
            return 'array'   # el AST solo guarda 'array', no el inner type
        if tc == TYPE_TUPLE:
            cnt = self.ru8()
            for _ in range(cnt): self.ru8()
            return 'tuple'
        if tc == TYPE_DICT:
            self.ru8(); self.ru8()
            return 'dict'
        if tc == TYPE_STRUCT:
            sname = self.rpstr()
            return sname   # tipo personalizado → nombre del struct
        return TYPE_NAMES.get(tc, 'dynamic')


# ════════════════════════════════════════════════════════════════════════
#  HELPERS DE CONSTRUCCIÓN DE NODOS
# ════════════════════════════════════════════════════════════════════════

def _parse_literal(raw_str: str):
    """
    Convierte un string de valor bytecode al tipo Python correcto.
    Enteros → int, floats → float, strings con comillas → str (con comillas),
    null/NULL → string "null", booleans → string "true"/"false" para el AST.
    """
    if raw_str is None: return "null"
    s = str(raw_str).strip()
    if not s: return None
    if s in ('null', 'NULL', 'None'): return "null"
    if s == 'true':  return True   # bool en dict AST puede ser bool o string
    if s == 'false': return False
    # String literal con comillas → dejar las comillas (así lo espera interpre.py)
    if ((s.startswith('"') and s.endswith('"')) or
            (s.startswith("'") and s.endswith("'"))):
        return s   # mantener comillas: '"Ana"'
    # Entero
    try:
        iv = int(s)
        return iv
    except ValueError:
        pass
    # Float
    try:
        fv = float(s)
        return fv
    except ValueError:
        pass
    # Cualquier otro string
    return s


def _value_node(raw_value, dtype_str: str, flags: int,
                op_str: str = None, length_str: str = None, limit_str: str = None):
    """
    Construye el sub-dict 'value' de un nodo de declaración,
    exactamente como aparece en ast_output.json.
    """
    node = {}

    # Valor principal
    val = _parse_literal(raw_value)
    node["value"] = val

    # Tipo base
    node["type"] = dtype_str if dtype_str else "dynamic"

    # explicitType — solo si la variable es tipada (DECL_HAS_TYPE)
    if flags & DECL_HAS_TYPE:
        node["explicitType"] = dtype_str

    # dinamic — solo si DECL_IS_DYNAMIC
    if flags & DECL_IS_DYNAMIC:
        node["dinamic"] = {"value": True}

    # operation — si hay operador compuesto
    if flags & DECL_HAS_OPERATION and op_str:
        node["operation"] = {"value": op_str}

    # longitud
    if flags & DECL_HAS_LENGTH and length_str:
        try:    lv = int(length_str)
        except: lv = length_str
        node["longitud"] = {"value": lv}

    # limit
    if flags & DECL_HAS_LIMIT and limit_str:
        try:    lv = int(limit_str)
        except: lv = limit_str
        node["limit"] = {"value": lv}

    return node


def _read_decl_payload(r: Reader):
    """
    Lee el payload de declaración y retorna
    (flags, dtype_str, raw_value, op_str, length_str, limit_str)
    """
    flags      = r.ru8()
    dtype_str  = r.rtype_str() if flags & DECL_HAS_TYPE else "dynamic"
    raw_value  = r.rwstr()     if flags & DECL_HAS_VALUE else None
    op_str     = r.rwstr()     if flags & DECL_HAS_OPERATION else None
    length_str = r.rwstr()     if flags & DECL_HAS_LENGTH else None
    limit_str  = r.rwstr()     if flags & DECL_HAS_LIMIT else None
    return flags, dtype_str, raw_value, op_str, length_str, limit_str


# ════════════════════════════════════════════════════════════════════════
#  DECODIFICADOR DE INSTRUCCIONES → NODOS AST
# ════════════════════════════════════════════════════════════════════════

def _fix_null_type(vnode: dict, raw_val, dtype_str: str, flags: int):
    """
    Regla de tipo en el AST de Tesseract:
    - Si el tipo declarado es un tipo real (nativo o personalizado) →
        type = dtype_str, explicitType = dtype_str (si DECL_HAS_TYPE)
        El valor puede ser null, pero el tipo sigue siendo el declarado.
        interpre.py se encarga de instanciar structs, clases o lo que sea.
    - Si no hay tipo declarado y el valor es null →
        type = "NULL"  (así lo produce el compilador .tss → JSON)
    """
    null_val = raw_val in ('null', 'NULL', None, '') or                (isinstance(raw_val, str) and raw_val.strip() in ('null', 'NULL', ''))

    has_real_type = (dtype_str and dtype_str not in ('dynamic', 'any', ''))

    if null_val:
        vnode["value"] = "null"
        if has_real_type:
            # Tipo personalizado o nativo con valor null →
            # poner el tipo tal cual y dejar que interpre.py decida
            vnode["type"] = dtype_str
            # explicitType ya lo pone _value_node si DECL_HAS_TYPE
        else:
            # Sin tipo → NULL
            vnode["type"] = "NULL"


def decode_block(r: Reader, stop_ops: set = None) -> list:
    """
    Lee instrucciones del reader y las convierte en lista de nodos AST dict.
    stop_ops: conjunto de opcodes que terminan el bloque (sin consumirlos).
    """
    nodes = []
    if stop_ops is None:
        stop_ops = set()

    while not r.eof():
        if r.peek() in stop_ops:
            break
        op = r.ru8()
        node = decode_op(op, r)
        if node is not None:
            if isinstance(node, list):
                nodes.extend(node)
            else:
                nodes.append(node)

    return nodes


def decode_op(op: int, r: Reader):
    """
    Decodifica una instrucción y devuelve el nodo AST dict correspondiente.
    """

    # ── NOP ─────────────────────────────────────────────────────────────
    if op == OP_NOP:
        return None

    # ── FUNC_DEF ─────────────────────────────────────────────────────────
    elif op == OP_FUNC_DEF:
        fname  = r.rpstr()
        pcount = r.ru8()
        params = []
        param_types = {}
        for _ in range(pcount):
            pname = r.rpstr()
            ptype = r.rtype_str()
            params.append(pname)
            if ptype and ptype != 'any':
                param_types[pname] = ptype

        flags = r.ru8()
        ret   = r.rtype_str() if flags & METHOD_HAS_RETURN else None

        # Leer cuerpo
        bsize = r.ru32()
        body_data = r.read(bsize)
        r.ru8()   # OP_FUNC_END

        br    = Reader(body_data)
        block = decode_block(br)

        # Construir nodo Function
        func_node = {
            "name": fname,
            "parameters": {"value": ",".join(
                f"{p}:{param_types[p]}" if p in param_types else p
                for p in params
            )},
            "block": block,
        }
        if ret and ret != 'dynamic':
            func_node["explicitType"] = ret

        return {"Function": func_node}

    # ── VAR_DECL ──────────────────────────────────────────────────────────
    elif op == OP_VAR_DECL:
        name = r.rpstr()
        flags, dtype_str, raw_val, op_str, len_str, lim_str = _read_decl_payload(r)
        vnode = _value_node(raw_val, dtype_str, flags, op_str, len_str, lim_str)
        _fix_null_type(vnode, raw_val, dtype_str, flags)
        return {"VariableDeclaration": {"name": name, "value": vnode}}

    # ── CONST_DECL ────────────────────────────────────────────────────────
    elif op == OP_CONST_DECL:
        name = r.rpstr()
        flags, dtype_str, raw_val, op_str, len_str, lim_str = _read_decl_payload(r)
        vnode = _value_node(raw_val, dtype_str, flags, op_str, len_str, lim_str)
        _fix_null_type(vnode, raw_val, dtype_str, flags)
        return {"ConstantDeclaration": {"name": name, "value": vnode}}

    # ── VAR_DECL_STRUCT ───────────────────────────────────────────────────
    elif op == OP_VAR_DECL_STRUCT:
        name = r.rpstr()
        flags, dtype_str, raw_val, op_str, len_str, lim_str = _read_decl_payload(r)
        vnode = _value_node(raw_val, dtype_str, flags, op_str, len_str, lim_str)
        _fix_null_type(vnode, raw_val, dtype_str, flags)
        return {"VariableDeclarationStruct": {"name": name, "value": vnode}}

    # ── CONST_DECL_STRUCT ─────────────────────────────────────────────────
    elif op == OP_CONST_DECL_STRUCT:
        name = r.rpstr()
        flags, dtype_str, raw_val, op_str, len_str, lim_str = _read_decl_payload(r)
        vnode = _value_node(raw_val, dtype_str, flags, op_str, len_str, lim_str)
        _fix_null_type(vnode, raw_val, dtype_str, flags)
        return {"ConstantDeclarationStruct": {"name": name, "value": vnode}}

    # ── ATTR_DECL / ATTR_CONST_DECL ──────────────────────────────────────
    elif op in (OP_ATTR_DECL, OP_ATTR_CONST_DECL):
        name = r.rpstr()
        flags, dtype_str, raw_val, op_str, len_str, lim_str = _read_decl_payload(r)
        vnode = _value_node(raw_val, dtype_str, flags, op_str, len_str, lim_str)
        ntype = "AttributeDeclaration" if op == OP_ATTR_DECL else "AttributeConstantDeclaration"
        return {ntype: {"name": name, "value": vnode}}

    # ── VAR_ASSIGN ────────────────────────────────────────────────────────
    elif op == OP_VAR_ASSIGN:
        name   = r.rpstr()
        flags  = r.ru8()
        op_str = r.rwstr() if flags & DECL_HAS_OPERATION else None
        val_s  = r.rwstr()
        vnode  = {"value": _parse_literal(val_s)}
        if op_str:
            vnode["operation"] = {"value": op_str}
        return {"VariableAsignement": {"name": name, "value": vnode}}

    # ── MOD_ASSIGN ────────────────────────────────────────────────────────
    elif op == OP_MOD_ASSIGN:
        name   = r.rpstr()
        flags  = r.ru8()
        op_str = r.rwstr() if flags & DECL_HAS_OPERATION else None
        val_s  = r.rwstr()
        vnode  = {"value": _parse_literal(val_s)}
        if op_str:
            vnode["operation"] = {"value": op_str}
        return {"ModuleAsignement": {"name": name, "value": vnode}}

    # ── CALL_EXPR ─────────────────────────────────────────────────────────
    elif op == OP_CALL_EXPR:
        fn_expr  = r.rwstr()
        has_a    = r.ru8()
        args_str = r.rwstr() if has_a else ""
        has_pt   = r.ru8()
        pt       = r.rpstr() if has_pt else ""

        node = {"function": fn_expr}
        if args_str.strip():
            node["arguments"] = {"value": args_str}
        if pt:
            node["paramType"] = pt
        return {"CallExpression": node}

    # ── FUNC_CALL ─────────────────────────────────────────────────────────
    elif op == OP_FUNC_CALL:
        fn_expr  = r.rwstr()
        has_p    = r.ru8()
        args_str = r.rwstr() if has_p else ""
        node = {"function": fn_expr}
        if args_str.strip():
            node["paramenters"] = {"value": args_str}
        return {"FunctionCall": node}

    # ── RETURN ────────────────────────────────────────────────────────────
    elif op == OP_RETURN:
        has_v = r.ru8()
        val_s = r.rwstr() if has_v else ""
        return {"Return": _parse_literal(val_s) if val_s.strip() else None}

    # ── IF ────────────────────────────────────────────────────────────────
    elif op == OP_IF:
        cond_str = r.rwstr()
        # Leer cuerpo hasta ELSE_IF / ELSE / END_IF al nivel 0
        if_block, else_node = _read_if_body(r)
        node = {
            "condition": cond_str,
            "block": if_block,
        }
        if else_node is not None:
            node["elseIf"] = else_node
        return {"if_Condition": node}

    # ── ELSE_IF / ELSE / END_IF — marcadores, manejados en _read_if_body
    elif op in (OP_ELSE_IF, OP_ELSE, OP_END_IF):
        return None

    # ── WHILE ─────────────────────────────────────────────────────────────
    elif op == OP_WHILE:
        cond_str  = r.rwstr()
        body_data = _read_block_bytes(r, OP_WHILE, OP_END_WHILE)
        br        = Reader(body_data)
        block     = decode_block(br)
        return {"WhileLoop": {"condition": cond_str, "block": block}}

    elif op == OP_END_WHILE: return None

    # ── DO-WHILE ──────────────────────────────────────────────────────────
    elif op == OP_DO_WHILE:
        body_data, cond_str = _read_do_while_bytes(r)
        br    = Reader(body_data)
        block = decode_block(br)
        return {"PerformWhileLoop": {"value": cond_str, "block": block}}

    elif op in (OP_DO_WHILE_COND, OP_END_DO_WHILE): return None

    # ── FOR ───────────────────────────────────────────────────────────────
    elif op == OP_FOR:
        var_str  = r.rpstr()
        iter_str = r.rwstr()
        is_decl  = r.ru8()
        body_data = _read_block_bytes(r, OP_FOR, OP_END_FOR)
        br    = Reader(body_data)
        block = decode_block(br)
        iter_node = {"value": iter_str}
        if is_decl:
            iter_node["declared"] = {"value": "true"}
        return {"ForLoop": {"variable": var_str, "iterator": iter_node, "block": block}}

    elif op == OP_END_FOR: return None

    # ── SWITCH ────────────────────────────────────────────────────────────
    elif op == OP_SWITCH:
        val_str = r.rwstr()
        cases, default_block = _read_switch_body(r)
        node = {"value": val_str, "cases": cases}
        if default_block is not None:
            node["defaultCase"] = {"block": default_block}
        return {"SwitchStatement": node}

    elif op in (OP_CASE, OP_DEFAULT_CASE, OP_END_SWITCH): return None

    # ── BREAK / CONTINUE ─────────────────────────────────────────────────
    elif op == OP_BREAK:    return {"CallExpression": {"function": "Break"}}
    elif op == OP_CONTINUE: return {"CallExpression": {"function": "Continue"}}

    # ── INCREMENTOS ───────────────────────────────────────────────────────
    elif op == OP_POST_INC:
        return {"PostIncrementStatement": {"value": r.rpstr()}}
    elif op == OP_PRE_INC:
        return {"PreIncrementStatement":  {"value": r.rpstr()}}
    elif op == OP_POST_DEC:
        return {"PostDecrementStatement": {"value": r.rpstr()}}
    elif op == OP_PRE_DEC:
        return {"PreDecrementStatement":  {"value": r.rpstr()}}

    # ── STRUCT_DECL ───────────────────────────────────────────────────────
    elif op == OP_STRUCT_DECL:
        sname     = r.rpstr()
        body_data = _read_block_bytes(r, OP_STRUCT_DECL, OP_STRUCT_END)
        br        = Reader(body_data)
        block     = decode_block(br)
        return {"StructDeclaration": {"name": sname, "block": block}}

    elif op == OP_STRUCT_END: return None

    # ── CLASS_DECL ────────────────────────────────────────────────────────
    elif op == OP_CLASS_DECL:
        cname = r.rpstr()
        flags = r.ru8()
        mod   = r.rpstr() if flags & CLASS_HAS_MODIFIER   else None
        ext   = r.rpstr() if flags & CLASS_HAS_EXTENDS    else None
        impl  = r.rpstr() if flags & CLASS_HAS_IMPLEMENTS else None
        body_data = _read_block_bytes(r, OP_CLASS_DECL, OP_CLASS_END)
        br    = Reader(body_data)
        block = decode_block(br)
        node  = {"name": cname, "members": block}
        if mod:  node["modifier"]    = mod
        if ext:  node["extends"]     = ext
        if impl: node["implements"]  = impl
        return {"ClassDeclaration": node}

    elif op == OP_CLASS_END: return None

    # ── INTERFACE_DECL ────────────────────────────────────────────────────
    elif op == OP_INTERFACE_DECL:
        iname = r.rpstr()
        flags = r.ru8()
        ext   = r.rpstr() if flags & CLASS_HAS_EXTENDS else None
        body_data = _read_block_bytes(r, OP_INTERFACE_DECL, OP_INTERFACE_END)
        br    = Reader(body_data)
        block = decode_block(br)
        node  = {"name": iname, "members": block}
        if ext: node["extends"] = ext
        return {"InterfaceDeclaration": node}

    elif op == OP_INTERFACE_END: return None

    # ── METHOD_DECL ───────────────────────────────────────────────────────
    elif op == OP_METHOD_DECL:
        mname  = r.rpstr()
        flags  = r.ru8()
        pcount = r.ru8()
        params = []
        ptypes = {}
        for _ in range(pcount):
            pn = r.rpstr(); pt = r.rtype_str()
            params.append(pn)
            if pt and pt != 'any': ptypes[pn] = pt
        mod = r.rpstr() if flags & METHOD_HAS_MODIFIER else None
        ret = r.rtype_str() if flags & METHOD_HAS_RETURN else None
        bsz = r.ru32(); body_data = r.read(bsz); r.ru8()
        br    = Reader(body_data)
        block = decode_block(br)
        node  = {
            "name": mname,
            "parameters": {"value": ",".join(
                f"{p}:{ptypes[p]}" if p in ptypes else p for p in params
            )},
            "block": block,
        }
        if mod: node["modifier"]    = mod
        if ret: node["explicitType"] = ret
        return {"MethodDeclaration": node}

    elif op == OP_METHOD_END: return None

    # ── CTOR_DECL ─────────────────────────────────────────────────────────
    elif op == OP_CTOR_DECL:
        cname  = r.rpstr()
        pcount = r.ru8()
        params = []
        ptypes = {}
        for _ in range(pcount):
            pn = r.rpstr(); pt = r.rtype_str()
            params.append(pn)
            if pt and pt != 'any': ptypes[pn] = pt
        bsz = r.ru32(); body_data = r.read(bsz); r.ru8()
        br    = Reader(body_data)
        block = decode_block(br)
        return {"ConstructorDeclaration": {
            "name": cname,
            "parameters": {"value": ",".join(
                f"{p}:{ptypes[p]}" if p in ptypes else p for p in params
            )},
            "block": block,
        }}

    elif op == OP_CTOR_END: return None

    # ── NEW_OBJECT ────────────────────────────────────────────────────────
    elif op == OP_NEW_OBJECT:
        cls   = r.rpstr()
        has_a = r.ru8()
        args  = r.rwstr() if has_a else ""
        return {"NewObject": {"class": cls, "arguments": {"value": args} if args else {}}}

    # ── THIS / SUPER ──────────────────────────────────────────────────────
    elif op == OP_THIS_ACCESS:  return {"ThisAccess":  {"value": r.rpstr()}}
    elif op == OP_SUPER_ACCESS: return {"SuperAccess": {"value": r.rpstr()}}

    elif op == OP_THIS_CALL:
        m = r.rpstr(); has_a = r.ru8(); args = r.rwstr() if has_a else ""
        return {"ThisCall": {"value": m, "arguments": {"value": args} if args else {}}}

    elif op == OP_SUPER_CALL:
        m = r.rpstr(); has_a = r.ru8(); args = r.rwstr() if has_a else ""
        return {"SuperCall": {"value": m, "arguments": {"value": args} if args else {}}}

    elif op == OP_THIS_ASSIGN:
        m = r.rpstr(); val = r.rwstr()
        return {"ThisAssignment": {"value": m, "assigned": {"value": _parse_literal(val)}}}

    elif op == OP_SUPER_ASSIGN:
        m = r.rpstr(); val = r.rwstr()
        return {"SuperAssignment": {"value": m, "assigned": {"value": _parse_literal(val)}}}

    elif op == OP_SUPER_CTOR:
        has_a = r.ru8(); args = r.rwstr() if has_a else ""
        return {"SuperConstructorCall": {"arguments": {"value": args} if args else {}}}

    # ── TRY/CATCH/FINALLY ─────────────────────────────────────────────────
    elif op == OP_TRY:
        # Leer todo hasta CATCH / FINALLY / END_TRY
        try_body, catch_info, finally_body = _read_try_body(r)
        node = {"tryBlock": try_body}
        if catch_info:
            node["catchClause"] = catch_info
        if finally_body:
            node["finallyBlock"] = {"block": finally_body}
        return {"TryCatch": node}

    elif op in (OP_CATCH, OP_FINALLY, OP_END_TRY): return None

    # ── THROW ─────────────────────────────────────────────────────────────
    elif op == OP_THROW:
        exc = r.rwstr()
        return {"Throw": {"exception": exc}}

    # ── LIB_CALL ──────────────────────────────────────────────────────────
    elif op == OP_LIB_CALL:
        mod_name = r.rpstr()
        flags    = r.ru8()
        alias    = r.rpstr() if flags & LIB_HAS_ALIAS else None
        funcs    = []
        if flags & LIB_HAS_FUNCTIONS:
            cnt = r.ru8()
            funcs = [r.rpstr() for _ in range(cnt)]
        func_aliases = []
        if flags & LIB_HAS_FUNC_ALIASES:
            cnt = r.ru8()
            func_aliases = [r.rpstr() for _ in range(cnt)]
        node = {"module": mod_name}
        if alias:        node["alias"]          = alias
        if funcs:        node["functions"]       = funcs
        if func_aliases: node["functionAliases"] = func_aliases
        return {"LibraryCall": node}

    # ── Opcodes sin contenido ─────────────────────────────────────────────
    elif op in (OP_FUNC_END, OP_ELSE, OP_END_IF, OP_END_WHILE,
                OP_END_DO_WHILE, OP_END_FOR, OP_END_SWITCH,
                OP_DEFAULT_CASE, OP_CLASS_END, OP_INTERFACE_END,
                OP_STRUCT_END, OP_METHOD_END, OP_CTOR_END,
                OP_FINALLY, OP_END_TRY):
        return None

    else:
        # Opcode desconocido — no podemos continuar (no sabemos el payload)
        print(f"[DECODER WARN] Opcode desconocido 0x{op:02X} en pos {r.pos-1}",
              file=sys.stderr)
        return None


# ════════════════════════════════════════════════════════════════════════
#  HELPERS DE LECTURA DE BLOQUES
# ════════════════════════════════════════════════════════════════════════

def _skip_payload(op: int, r: Reader):
    """Salta el payload de un opcode sin decodificarlo."""
    if op == OP_FUNC_DEF:
        r.rpstr(); pcount = r.ru8()
        for _ in range(pcount): r.rpstr(); r.rtype_str()
        flags = r.ru8()
        if flags & METHOD_HAS_RETURN: r.rtype_str()
        bsz = r.ru32(); r.read(bsz); r.ru8()
    elif op in (OP_VAR_DECL, OP_CONST_DECL, OP_VAR_DECL_STRUCT,
                OP_CONST_DECL_STRUCT, OP_ATTR_DECL, OP_ATTR_CONST_DECL):
        r.rpstr(); flags = r.ru8()
        if flags & DECL_HAS_TYPE:      r.rtype_str()
        if flags & DECL_HAS_VALUE:     r.rwstr()
        if flags & DECL_HAS_OPERATION: r.rwstr()
        if flags & DECL_HAS_LENGTH:    r.rwstr()
        if flags & DECL_HAS_LIMIT:     r.rwstr()
    elif op in (OP_VAR_ASSIGN, OP_MOD_ASSIGN):
        r.rpstr(); flags = r.ru8()
        if flags & DECL_HAS_OPERATION: r.rwstr()
        r.rwstr()
    elif op == OP_CALL_EXPR:
        r.rwstr(); has_a = r.ru8()
        if has_a: r.rwstr()
        has_pt = r.ru8()
        if has_pt: r.rpstr()
    elif op == OP_FUNC_CALL:
        r.rwstr(); has_p = r.ru8()
        if has_p: r.rwstr()
    elif op == OP_RETURN:
        has_v = r.ru8()
        if has_v: r.rwstr()
    elif op in (OP_IF, OP_ELSE_IF, OP_WHILE, OP_DO_WHILE_COND,
                OP_SWITCH, OP_CASE, OP_THROW): r.rwstr()
    elif op == OP_FOR: r.rpstr(); r.rwstr(); r.ru8()
    elif op in (OP_POST_INC, OP_PRE_INC, OP_POST_DEC, OP_PRE_DEC,
                OP_STRUCT_DECL): r.rpstr()
    elif op == OP_CLASS_DECL:
        r.rpstr(); flags = r.ru8()
        if flags & CLASS_HAS_MODIFIER:   r.rpstr()
        if flags & CLASS_HAS_EXTENDS:    r.rpstr()
        if flags & CLASS_HAS_IMPLEMENTS: r.rpstr()
    elif op == OP_INTERFACE_DECL:
        r.rpstr(); flags = r.ru8()
        if flags & CLASS_HAS_EXTENDS: r.rpstr()
    elif op == OP_METHOD_DECL:
        r.rpstr(); flags = r.ru8(); pcount = r.ru8()
        for _ in range(pcount): r.rpstr(); r.rtype_str()
        if flags & METHOD_HAS_MODIFIER: r.rpstr()
        if flags & METHOD_HAS_RETURN:   r.rtype_str()
        bsz = r.ru32(); r.read(bsz); r.ru8()
    elif op == OP_CTOR_DECL:
        r.rpstr(); pcount = r.ru8()
        for _ in range(pcount): r.rpstr(); r.rtype_str()
        bsz = r.ru32(); r.read(bsz); r.ru8()
    elif op == OP_NEW_OBJECT:
        r.rpstr(); has_a = r.ru8()
        if has_a: r.rwstr()
    elif op in (OP_THIS_ACCESS, OP_SUPER_ACCESS): r.rpstr()
    elif op in (OP_THIS_CALL, OP_SUPER_CALL):
        r.rpstr(); has_a = r.ru8()
        if has_a: r.rwstr()
    elif op in (OP_THIS_ASSIGN, OP_SUPER_ASSIGN): r.rpstr(); r.rwstr()
    elif op == OP_SUPER_CTOR:
        has_a = r.ru8()
        if has_a: r.rwstr()
    elif op == OP_CATCH:
        has_t = r.ru8()
        if has_t: r.rpstr()
        has_v = r.ru8()
        if has_v: r.rpstr()
    elif op == OP_LIB_CALL:
        r.rpstr(); flags = r.ru8()
        if flags & LIB_HAS_ALIAS: r.rpstr()
        if flags & LIB_HAS_FUNCTIONS:
            cnt = r.ru8()
            for _ in range(cnt): r.rpstr()
        if flags & LIB_HAS_FUNC_ALIASES:
            cnt = r.ru8()
            for _ in range(cnt): r.rpstr()
    # Opcodes sin payload: NOP, FUNC_END, ELSE, END_IF, END_WHILE, etc.


def _read_block_bytes(r: Reader, open_op: int, close_op: int) -> bytes:
    """Lee bytes hasta encontrar close_op al nivel 0."""
    body = bytearray(); depth = 1
    while not r.eof() and depth > 0:
        op = r.data[r.pos]
        if op == open_op:  depth += 1
        elif op == close_op:
            depth -= 1
            if depth == 0: r.pos += 1; break
        start = r.pos; r.pos += 1
        _skip_payload(op, r)
        body.extend(r.data[start:r.pos])
    return bytes(body)


def _read_do_while_bytes(r: Reader):
    """Lee el cuerpo y condición de DO-WHILE."""
    body = bytearray(); cond_str = ''; depth = 1
    while not r.eof():
        op = r.data[r.pos]
        if op == OP_DO_WHILE:
            depth += 1
            start = r.pos; r.pos += 1; _skip_payload(op, r)
            body.extend(r.data[start:r.pos])
        elif op == OP_DO_WHILE_COND and depth == 1:
            r.pos += 1; tmp = Reader(r.data[r.pos:]); cond_str = tmp.rwstr(); r.pos += tmp.pos
            if not r.eof() and r.data[r.pos] == OP_END_DO_WHILE: r.pos += 1
            break
        elif op == OP_END_DO_WHILE:
            depth -= 1; r.pos += 1
            if depth == 0: break
        else:
            start = r.pos; r.pos += 1; _skip_payload(op, r)
            body.extend(r.data[start:r.pos])
    return bytes(body), cond_str


def _read_if_body(r: Reader):
    """
    Lee el cuerpo de un IF y retorna (block, else_node).
    else_node puede ser None, un nodo ELSE_IF, o un nodo ELSE (condition="False").
    """
    current_body = bytearray()
    depth = 1

    while not r.eof() and depth > 0:
        op = r.data[r.pos]

        if op == OP_IF:
            depth += 1
            start = r.pos; r.pos += 1; r.rwstr()  # skip cond
            current_body.extend(r.data[start:r.pos])
            continue

        if op == OP_END_IF:
            depth -= 1
            if depth == 0:
                r.pos += 1
                # Decodificar el cuerpo acumulado
                br = Reader(bytes(current_body))
                block = decode_block(br)
                return block, None
            # Nested end-if
            start = r.pos; r.pos += 1
            current_body.extend(r.data[start:r.pos])
            continue

        if op == OP_ELSE_IF and depth == 1:
            r.pos += 1
            ei_cond = r.rwstr()
            # Decodificar cuerpo acumulado
            br = Reader(bytes(current_body))
            block = decode_block(br)
            # Leer recursivamente el ELSE_IF
            ei_block, ei_else = _read_if_body(r)
            else_node = {"condition": ei_cond, "block": ei_block}
            if ei_else is not None:
                else_node["elseIf"] = ei_else
            return block, else_node

        if op == OP_ELSE and depth == 1:
            r.pos += 1
            br = Reader(bytes(current_body))
            block = decode_block(br)
            # Leer el cuerpo del else
            else_body = bytearray()
            while not r.eof():
                inner_op = r.data[r.pos]
                if inner_op == OP_END_IF:
                    depth -= 1
                    if depth == 0: r.pos += 1; break
                    start = r.pos; r.pos += 1
                    else_body.extend(r.data[start:r.pos])
                    continue
                start = r.pos; r.pos += 1; _skip_payload(inner_op, r)
                else_body.extend(r.data[start:r.pos])
            br2 = Reader(bytes(else_body))
            else_block = decode_block(br2)
            # else se representa como condition=False en el AST
            else_node = {"condition": "False", "block": else_block}
            return block, else_node

        # Acumular instrucción
        start = r.pos; r.pos += 1; _skip_payload(op, r)
        current_body.extend(r.data[start:r.pos])

    br = Reader(bytes(current_body))
    return decode_block(br), None


def _read_switch_body(r: Reader):
    """Lee los casos de un switch."""
    cases = []; default_block = None
    depth = 1
    cur_case_val = None; cur_body = bytearray()
    in_case = False; in_default = False

    while not r.eof() and depth > 0:
        op = r.data[r.pos]
        if op == OP_SWITCH:
            depth += 1
            start = r.pos; r.pos += 1; _skip_payload(op, r)
            if in_case or in_default: cur_body.extend(r.data[start:r.pos])
            continue
        if op == OP_END_SWITCH:
            depth -= 1
            if depth == 0:
                r.pos += 1
                if in_case:
                    br = Reader(bytes(cur_body)); cases.append({"case": cur_case_val, "block": decode_block(br)})
                if in_default:
                    br = Reader(bytes(cur_body)); default_block = decode_block(br)
                break
            start = r.pos; r.pos += 1
            if in_case or in_default: cur_body.extend(r.data[start:r.pos])
            continue
        if op == OP_CASE and depth == 1:
            if in_case: br = Reader(bytes(cur_body)); cases.append({"case": cur_case_val, "block": decode_block(br)})
            if in_default: br = Reader(bytes(cur_body)); default_block = decode_block(br)
            r.pos += 1; cur_case_val = r.rwstr()
            cur_body = bytearray(); in_case = True; in_default = False; continue
        if op == OP_DEFAULT_CASE and depth == 1:
            if in_case: br = Reader(bytes(cur_body)); cases.append({"case": cur_case_val, "block": decode_block(br)})
            if in_default: br = Reader(bytes(cur_body)); default_block = decode_block(br)
            r.pos += 1; cur_body = bytearray(); in_case = False; in_default = True; continue
        start = r.pos; r.pos += 1; _skip_payload(op, r)
        if in_case or in_default: cur_body.extend(r.data[start:r.pos])

    return cases, default_block


def _read_try_body(r: Reader):
    """Lee bloques try/catch/finally."""
    try_body = bytearray(); catch_info = None; finally_body = None
    in_try = True; in_catch = False; in_finally = False
    catch_body = bytearray(); fin_body = bytearray()

    while not r.eof():
        op = r.data[r.pos]
        if op == OP_CATCH and in_try:
            in_try = False; in_catch = True; r.pos += 1
            has_t = r.ru8(); et = r.rpstr() if has_t else ""
            has_v = r.ru8(); ev = r.rpstr() if has_v else ""
            catch_info = {}
            if et: catch_info["type"] = et
            if ev: catch_info["exception"] = ev
            continue
        if op == OP_FINALLY:
            in_catch = False; in_finally = True; r.pos += 1; continue
        if op == OP_END_TRY:
            r.pos += 1; break
        start = r.pos; r.pos += 1; _skip_payload(op, r)
        chunk = r.data[start:r.pos]
        if in_try:     try_body.extend(chunk)
        elif in_catch: catch_body.extend(chunk)
        elif in_finally: fin_body.extend(chunk)

    br = Reader(bytes(try_body))
    try_block = decode_block(br)
    if catch_info is not None:
        br2 = Reader(bytes(catch_body))
        catch_info["block"] = decode_block(br2)
    if fin_body:
        br3 = Reader(bytes(fin_body))
        finally_body = decode_block(br3)
    return try_block, catch_info, finally_body


# ════════════════════════════════════════════════════════════════════════
#  DECODIFICADOR PRINCIPAL DE .tsslk
# ════════════════════════════════════════════════════════════════════════

def decode_tsslk(path: str) -> dict:
    """
    Lee un archivo .tsslk/.tbc (bytecode Tesseract) y retorna el AST dict
    {"Program": [...]} listo para pasar a interpre.py interpreter.interpret().
    """
    with open(path, "rb") as f:
        data = f.read()

    r = Reader(data)

    # ── Header ──────────────────────────────────────────────────────────
    magic = r.read(5)
    if magic != MAGIC_TSSLK:
        raise ValueError(
            f"Magic inválido: {magic!r}. "
            f"¿Es un archivo .tsslk/.tbc válido? (esperado {MAGIC_TSSLK!r})"
        )

    r.ru8()             # format version
    mode_flags = r.ru8()
    has_entry  = bool(mode_flags & 0x01)
    entry_pt   = r.rpstr() if has_entry else ""

    sym_count  = r.ru16()
    symbols    = []     # [(sym_type, sym_name, sym_data_bytes)]

    for _ in range(sym_count):
        sym_type = r.ru8()
        sym_name = r.rpstr()
        sym_size = r.ru32()
        sym_data = r.read(sym_size)
        symbols.append((sym_type, sym_name, sym_data))

    # ── Reconstruir Program ──────────────────────────────────────────────
    # El símbolo __init__ contiene TODO el código nivel raíz en orden.
    program_nodes = []
    init_sym = None

    for sym_type, sym_name, sym_data in symbols:
        if sym_name == "__init__":
            init_sym = sym_data
            break

    if init_sym is not None:
        br = Reader(init_sym)
        program_nodes = decode_block(br)
    else:
        for sym_type, sym_name, sym_data in symbols:
            br = Reader(sym_data)
            nodes = decode_block(br)
            program_nodes.extend(nodes)

    program_nodes = [n for n in program_nodes if n is not None]
    return {"Program": program_nodes}


# Alias público para la extensión .tbc (mismo contenido, distinto nombre de archivo)
decode_tbc = decode_tsslk


# ════════════════════════════════════════════════════════════════════════
#  ENTRY POINT (para testing)
# ════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("Uso: python tsslk_decoder.py <archivo.tsslk|.tbc>")
        sys.exit(1)
    ast = decode_tbc(sys.argv[1])
    print(json.dumps(ast, indent=2, ensure_ascii=False))