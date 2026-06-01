# =============================================================================
# tessruntimeweb.py — Tesseract Web IR Emitter
# =============================================================================
# Lee el JSON AST de Tesseract y emite un IR intermedio optimizado (WebIR)
# que runtime.js puede leer y transpilar a JavaScript final.
#
# Pipeline:
#   Parser -> AST JSON -> tessruntimeweb.py -> WebIR JSON -> runtime.js -> JS
#
# El WebIR es:
#   - Compacto: claves cortas, sin ruido del AST original
#   - Tipado: cada expr y decl carga su tipo inferido
#   - Plano: sin anidamiento profundo innecesario
#   - Extensible: preparado para objetos, eventos, UI
#
# Cubre TODOS los nodos de tessruntime.py mas extension web:
#   VariableDeclaration, VariableAsignement, ConstantDeclaration,
#   Function, FunctionCall, CallExpression (print/read/return/break/mod),
#   LibraryCall, if_Condition (elif/else), ForLoop, WhileLoop,
#   PerformWhileLoop, SwitchStatement, Post/Pre Increment/Decrement,
#   ParameterAsignement, ArrayAccess
#
# Preparado para futuro:
#   ObjDeclaration, EventBind, UIElement, ComponentDef
# =============================================================================

from __future__ import annotations
import re, os, sys
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# WebIR Version
# =============================================================================

WEBIR_VERSION = "1.0"


# =============================================================================
# Sistema de Tipos (mismo que tessruntime.py)
# =============================================================================

class TessType(Enum):
    INT     = "int"
    FLOAT   = "float"
    BOOL    = "bool"
    STRING  = "string"
    ARRAY   = "array"
    DICT    = "dict"
    NULL    = "null"
    DYNAMIC = "dynamic"
    VOID    = "void"
    # Preparado para futuro
    OBJECT  = "object"
    EVENT   = "event"
    ELEMENT = "element"

    @staticmethod
    def from_str(s: str) -> "TessType":
        m = {
            "int":     "int",
            "float":   "float",
            "bool":    "bool",
            "string":  "string",
            "array":   "array",
            "dict":    "dict",
            "null":    "null",
            "any":     "dynamic",
            "dynamic": "dynamic",
            "void":    "void",
            "inferred":"dynamic",
            "object":  "object",
            "event":   "event",
            "element": "element",
        }
        key = s.lower().strip()
        val = m.get(key, "dynamic")
        return TessType(val)

    def is_numeric(self): return self in (TessType.INT, TessType.FLOAT)
    def is_static(self):  return self not in (TessType.DYNAMIC, TessType.ARRAY, TessType.DICT)
    def to_js(self) -> str:
        """Mapeo de tipo Tess a tipo JS para el WebIR."""
        MAP = {
            "int":     "number",
            "float":   "number",
            "bool":    "boolean",
            "string":  "string",
            "array":   "Array",
            "dict":    "Object",
            "null":    "null",
            "dynamic": "any",
            "void":    "void",
            "object":  "Object",
            "event":   "Event",
            "element": "Element",
        }
        return MAP.get(self.value, "any")


# =============================================================================
# Arbol de Expresiones (mismo que tessruntime.py)
# =============================================================================

class ExprNode: pass

@dataclass
class LiteralNode(ExprNode):
    value: Any
    ttype: TessType

@dataclass
class VarNode(ExprNode):
    name: str

@dataclass
class BinOpNode(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode

@dataclass
class LogicalNode(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode

@dataclass
class UnaryNode(ExprNode):
    op: str
    operand: ExprNode

@dataclass
class ConcatNode(ExprNode):
    parts: List[ExprNode]

@dataclass
class FuncCallNode(ExprNode):
    name: str
    args: List[ExprNode]

@dataclass
class ModCallNode(ExprNode):
    module: str
    func: str
    args: List[ExprNode]

@dataclass
class ModVarNode(ExprNode):
    module: str
    var: str

@dataclass
class ArrayAccessNode(ExprNode):
    array: str
    indices: List[ExprNode]

@dataclass
class RangeNode(ExprNode):
    start: ExprNode
    end: ExprNode
    range_type: str  # 'int' | 'float' | 'string'

@dataclass
class MethodCallNode(ExprNode):
    """Llamada a metodo de tipo core (ej: myStr.toUpperCase(), myArr.push(x)).
    Extraido del sistema de tipos de interpre.py (_core_*_methods)."""
    obj: str
    method: str
    args: List[ExprNode]

@dataclass
class PropAccessNode(ExprNode):
    """Acceso a propiedad de tipo core (ej: myStr.length, myArr.isEmpty).
    Extraido del sistema de tipos de interpre.py (_core_*_methods cat='first')."""
    obj: str
    prop: str


# =============================================================================
# Core Type Methods & Properties
# Extraidos de interpre.py: _core_string_methods, _core_int_methods,
# _core_float_methods, _core_bool_methods, _core_array_methods, _core_null_methods
# Usados por ExpressionParser para distinguir llamadas a tipo-core de
# llamadas a modulos, emitiendo nodos MethodCallNode / PropAccessNode en
# lugar de ModCallNode / ModVarNode.
# =============================================================================

CORE_TYPE_METHODS = frozenset({
    # Conversores de tipo (todos los tipos)
    'typeInt', 'typeFloat', 'typeBool', 'typeString',
    # String — cat: chainable
    'toUpperCase', 'toLowerCase', 'trim', 'trimStart', 'trimEnd',
    'reverse', 'repeat', 'replace', 'split', 'slice', 'charAt',
    'contains', 'startsWith', 'endsWith', 'indexOf', 'padStart', 'padEnd',
    # Number int/float — cat: chainable
    'abs', 'clamp', 'pow', 'max', 'min',
    'round', 'floor', 'ceil',
    # Bool — cat: chainable
    'toggle',
    # Array — cat: chainable / mutable_default
    'push', 'pop', 'shift', 'unshift', 'insert', 'remove', 'clear',
    'sort', 'filter', 'map', 'concat', 'join', 'unique', 'flatten',
    # Null
    'typeString',
})

CORE_TYPE_PROPS = frozenset({
    # Comunes a todos los tipos — cat: first
    'length', 'isEmpty', 'isArray', 'isString', 'isInt', 'isFloat',
    'isBool', 'isNull', 'type',
    # Int / Float — cat: first
    'isEven', 'isOdd', 'isPositive', 'isNegative', 'isNaN', 'isInfinite',
    # Array — cat: first
    'first', 'last',
})


# =============================================================================
# Tokenizer (mismo que tessruntime.py)
# =============================================================================

class ExprTokenizer:
    TOKEN_PATTERNS = [
        ('RANGE_DOT',    r'\.\.'),
        ('NUMBER_FLOAT', r'\d+\.\d+'),
        ('NUMBER_INT',   r'\d+'),
        ('STRING_DQ',    r'"(?:[^"\\]|\\.)*"'),
        ('STRING_SQ',    r"'(?:[^'\\]|\\.)*'"),
        ('TRUE',         r'\btrue\b'),
        ('FALSE',        r'\bfalse\b'),
        ('NULL_KW',      r'\bnull\b'),
        ('AND',          r'&&'),
        ('OR',           r'\|\|'),
        ('NEQ',          r'!='),
        ('EQ',           r'=='),
        ('LTE',          r'<='),
        ('GTE',          r'>='),
        ('NOT',          r'!'),
        ('LT',           r'<'),
        ('GT',           r'>'),
        ('PLUS',         r'\+'),
        ('MINUS',        r'-'),
        ('STAR',         r'\*'),
        ('SLASH',        r'/'),
        ('PERCENT',      r'%'),
        ('LPAREN',       r'\('),
        ('RPAREN',       r'\)'),
        ('LBRACKET',     r'\['),
        ('RBRACKET',     r'\]'),
        ('COLON',        r':'),
        ('COMMA',        r','),
        ('CONCAT_DOT',   r'\.'),
        ('IDENT',        r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('WS',           r'\s+'),
    ]
    _re = None

    @classmethod
    def _master(cls):
        if cls._re is None:
            cls._re = re.compile('|'.join(f'(?P<{n}>{p})' for n, p in cls.TOKEN_PATTERNS))
        return cls._re

    @classmethod
    def tokenize(cls, expr: str) -> List[Tuple[str, str]]:
        return [(m.lastgroup, m.group()) for m in cls._master().finditer(expr)
                if m.lastgroup != 'WS']


# =============================================================================
# Parser de Expresiones (Recursive Descent) (mismo que tessruntime.py)
# =============================================================================

class ExpressionParser:
    def _has_range_op_outside_quotes(self, expr: str) -> bool:
        in_str, str_ch = False, ''
        i = 0
        while i < len(expr):
            c = expr[i]
            if not in_str and c in ('"', "'"):
                in_str, str_ch = True, c
            elif in_str:
                if c == str_ch and (i == 0 or expr[i-1] != '\\'):
                    in_str = False
            elif c == '.' and i + 1 < len(expr) and expr[i+1] == '.':
                return True
            i += 1
        return False
    def parse(self, expr: str) -> ExprNode:
        expr = expr.strip()
        if not expr:
            return LiteralNode(None, TessType.NULL)
        if '..' in expr and self._has_range_op_outside_quotes(expr):
            return self._parse_range_expr(expr)
        self._tokens = ExprTokenizer.tokenize(expr)
        self._pos = 0
        return self._parse_or()

    def _parse_or(self):
        left = self._parse_and()
        while self._peek_is('OR'):
            self._consume()
            left = LogicalNode('||', left, self._parse_and())
        return left

    def _parse_and(self):
        left = self._parse_comparison()
        while self._peek_is('AND'):
            self._consume()
            left = LogicalNode('&&', left, self._parse_comparison())
        return left

    def _parse_comparison(self):
        left = self._parse_concat()
        ops  = {'EQ':'==','NEQ':'!=','LTE':'<=','GTE':'>=','LT':'<','GT':'>'}
        while self._peek_kind() in ops:
            op = ops[self._consume()[0]]
            left = BinOpNode(op, left, self._parse_concat())
        return left

    def _parse_concat(self):
        left  = self._parse_additive()
        parts = [left]
        while self._peek_is('CONCAT_DOT'):
            self._consume()
            parts.append(self._parse_additive())
        return left if len(parts) == 1 else ConcatNode(parts)

    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self._peek_kind() in ('PLUS', 'MINUS'):
            op   = '+' if self._consume()[0] == 'PLUS' else '-'
            left = BinOpNode(op, left, self._parse_multiplicative())
        return left

    def _parse_multiplicative(self):
        left = self._parse_unary()
        ops  = {'STAR':'*','SLASH':'/','PERCENT':'%'}
        while self._peek_kind() in ops:
            op   = ops[self._consume()[0]]
            left = BinOpNode(op, left, self._parse_unary())
        return left

    def _parse_unary(self):
        if self._peek_is('MINUS'):
            self._consume(); return UnaryNode('-', self._parse_unary())
        if self._peek_is('NOT'):
            self._consume(); return UnaryNode('!', self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self):
        tok = self._peek()
        if tok is None: return LiteralNode(None, TessType.NULL)
        kind, val = tok

        if kind == 'LPAREN':
            self._consume()
            inner = self._parse_or()
            if self._peek_is('RPAREN'): self._consume()
            return inner

        if kind == 'NUMBER_FLOAT': self._consume(); return LiteralNode(float(val), TessType.FLOAT)
        if kind == 'NUMBER_INT':   self._consume(); return LiteralNode(int(val),   TessType.INT)
        if kind == 'STRING_DQ':    self._consume(); return LiteralNode(val[1:-1],  TessType.STRING)
        if kind == 'STRING_SQ':    self._consume(); return LiteralNode(val[1:-1],  TessType.STRING)
        if kind == 'TRUE':         self._consume(); return LiteralNode(True,        TessType.BOOL)
        if kind == 'FALSE':        self._consume(); return LiteralNode(False,       TessType.BOOL)
        if kind == 'NULL_KW':      self._consume(); return LiteralNode(None,        TessType.NULL)

        if kind == 'IDENT':
            self._consume()
            name = val

            if self._peek_is('LPAREN'):
                self._consume()
                args = self._parse_arg_list()
                if self._peek_is('RPAREN'): self._consume()
                return FuncCallNode(name, args)

            if self._peek_is('CONCAT_DOT'):
                saved = self._pos
                self._consume()
                if self._peek_is('IDENT'):
                    _, member = self._consume()
                    if self._peek_is('LPAREN'):
                        self._consume()
                        args = self._parse_arg_list()
                        if self._peek_is('RPAREN'): self._consume()
                        # Distingue metodo de tipo core vs llamada a modulo
                        if member in CORE_TYPE_METHODS:
                            return MethodCallNode(name, member, args)
                        return ModCallNode(name, member, args)
                    # Acceso a propiedad: distingue prop core vs variable de modulo
                    if member in CORE_TYPE_PROPS:
                        return PropAccessNode(name, member)
                    return ModVarNode(name, member)
                self._pos = saved
                return VarNode(name)

            if self._peek_is('LBRACKET'):
                self._consume()
                indices = self._parse_array_indices()
                if self._peek_is('RBRACKET'): self._consume()
                return ArrayAccessNode(name, indices)

            return VarNode(name)

        self._consume()
        return LiteralNode(None, TessType.NULL)

    def _parse_arg_list(self):
        args = []
        if self._peek_is('RPAREN'): return args
        while True:
            if (self._peek_is('IDENT') and
                    self._pos + 1 < len(self._tokens) and
                    self._tokens[self._pos + 1][0] == 'COLON'):
                self._consume(); self._consume()
            args.append(self._parse_or())
            if not self._peek_is('COMMA'): break
            self._consume()
        return args

    def _parse_array_indices(self):
        indices = []
        if self._peek_is('RBRACKET'): return indices
        while True:
            indices.append(self._parse_or())
            if not self._peek_is('COLON'): break
            self._consume()
        return indices

    def _parse_range_expr(self, expr: str) -> RangeNode:
        parts = expr.split('..', 1)
        s = self.parse(parts[0].strip())
        e = self.parse(parts[1].strip())
        rt = 'int'
        for n in (s, e):
            if isinstance(n, LiteralNode):
                if n.ttype == TessType.FLOAT:  rt = 'float';  break
                if n.ttype == TessType.STRING: rt = 'string'; break
        return RangeNode(s, e, rt)

    def _peek(self):
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _peek_kind(self):
        t = self._peek(); return t[0] if t else None

    def _peek_is(self, kind):
        t = self._peek(); return t is not None and t[0] == kind

    def _consume(self):
        t = self._tokens[self._pos]; self._pos += 1; return t

    def parse_concatenated_string(self, arg_str: str) -> ExprNode:
        parts = self._split_concat_dot(arg_str)
        nodes = [self.parse(p) for p in parts if p.strip()]
        if not nodes:       return LiteralNode("", TessType.STRING)
        if len(nodes) == 1: return nodes[0]
        return ConcatNode(nodes)

    def _split_concat_dot(self, expr: str) -> List[str]:
        parts, cur = [], []
        depth, in_str, str_ch = 0, False, ''
        i = 0
        while i < len(expr):
            c = expr[i]
            if not in_str and c in ('"', "'"):
                in_str, str_ch = True, c
                cur.append(c); i += 1; continue
            if in_str:
                cur.append(c)
                if c == str_ch and (i == 0 or expr[i-1] != '\\'): in_str = False
                i += 1; continue
            if c in '([{': depth += 1; cur.append(c); i += 1; continue
            if c in ')]}': depth -= 1; cur.append(c); i += 1; continue
            if c == '.' and depth == 0:
                nxt  = expr[i+1] if i+1 < len(expr) else ''
                prev = expr[i-1] if i > 0 else ''
                if nxt == '.':  cur.append(c); i += 1; continue
                if prev.isdigit() and nxt.isdigit(): cur.append(c); i += 1; continue
                if (prev.isalnum() or prev == '_') and (nxt.isalpha() or nxt == '_'):
                    cur.append(c); i += 1; continue
                parts.append(''.join(cur)); cur = []; i += 1; continue
            cur.append(c); i += 1
        parts.append(''.join(cur))
        return [p for p in parts if p.strip()]


# =============================================================================
# ValueAnalyzer (mismo que tessruntime.py)
# =============================================================================

@dataclass
class ValueDescriptor:
    ttype:        TessType
    const_val:    Any               = None
    expr_node:    Optional[ExprNode] = None
    ast_type_tag: str               = ""
    raw_value:    Any               = None


class ValueAnalyzer:
    def __init__(self, parser: ExpressionParser):
        self._p = parser

    def analyze(self, vn: dict) -> ValueDescriptor:
        if not vn or vn == {}:
            return ValueDescriptor(ttype=TessType.DYNAMIC)
        if not vn:
            return ValueDescriptor(ttype=TessType.NULL)
        at  = vn.get("type", "")
        raw = vn.get("value")
        d   = ValueDescriptor(ttype=TessType.NULL, ast_type_tag=at, raw_value=raw)

        if at == "ModuleVariable":
            d.ttype = TessType.DYNAMIC
            d.expr_node = self._p.parse(str(raw)) if raw else None
            return d

        if at == "function" and isinstance(raw, str) and '.' in raw:
            d.ttype = TessType.DYNAMIC
            d.expr_node = self._p.parse(raw)
            return d

        if at == "function" and isinstance(raw, str):
            d.ttype = TessType.DYNAMIC
            d.expr_node = self._p.parse(raw)
            return d

        if at == "NULL" or raw == "null":
            d.ttype = TessType.NULL
            return d

        if "operation" in vn:
            op = vn["operation"]
            es = op.get("value") if isinstance(op, dict) else str(op)
            d.ttype = TessType.DYNAMIC
            d.expr_node = self._p.parse(str(es))
            return d

        if isinstance(raw, bool):  d.ttype=TessType.BOOL;  d.const_val=raw; return d
        if isinstance(raw, int):   d.ttype=TessType.INT;   d.const_val=raw; return d
        if isinstance(raw, float): d.ttype=TessType.FLOAT; d.const_val=raw; return d
        if isinstance(raw, list):  d.ttype=TessType.ARRAY; d.const_val=raw; return d
        if isinstance(raw, dict):  d.ttype=TessType.DICT;  d.const_val=raw; return d

        # ── type-tag explícito: array/tuple/dict aunque raw sea str o None ───
        at_low = (at or "").lower()
        if at_low in ("array", "tuple"):
            if isinstance(raw, str) and raw.strip():
                parsed = self._try_parse_collection(raw)
                if isinstance(parsed, list):
                    d.ttype = TessType.ARRAY; d.const_val = parsed; return d
            # buscar elementos en claves alternas del nodo
            for alt_key in ("elements", "items", "content", "values"):
                alt = vn.get(alt_key)
                if isinstance(alt, list):
                    d.ttype = TessType.ARRAY; d.const_val = alt; return d
                if isinstance(alt, str) and alt.strip().startswith('['):
                    parsed = self._try_parse_collection(alt)
                    if isinstance(parsed, list):
                        d.ttype = TessType.ARRAY; d.const_val = parsed; return d
            d.ttype = TessType.ARRAY; d.const_val = []; return d

        if at_low in ("dict", "map", "object", "hashmap"):
            if isinstance(raw, str) and raw.strip():
                parsed = self._try_parse_collection(raw)
                if isinstance(parsed, dict):
                    d.ttype = TessType.DICT; d.const_val = parsed; return d
            for alt_key in ("entries", "pairs", "fields"):
                alt = vn.get(alt_key)
                if isinstance(alt, dict):
                    d.ttype = TessType.DICT; d.const_val = alt; return d
            d.ttype = TessType.DICT; d.const_val = {}; return d

        if isinstance(raw, str):
            return self._analyze_str(raw, at, d)

        return d

    @staticmethod
    def _try_parse_collection(s: str):
        """Parsea un string como JSON. Fallback: comillas simples -> dobles.
        Replica la logica de interpre.py (json.loads con replace)."""
        import json as _json
        s = s.strip()
        if not s:
            return None
        try:
            return _json.loads(s)
        except Exception:
            pass
        try:
            return _json.loads(s.replace("'", '"'))
        except Exception:
            pass
        return None

    def _analyze_str(self, raw: str, at: str, d: ValueDescriptor) -> ValueDescriptor:
        stripped = raw.strip()

        # ── Array literal: ["a","b",...] o ['a','b',...] ─────────────────
        if stripped.startswith('[') and stripped.endswith(']'):
            parsed = self._try_parse_collection(stripped)
            if isinstance(parsed, list):
                d.ttype = TessType.ARRAY; d.const_val = parsed; return d
            d.ttype = TessType.ARRAY; d.const_val = []; return d

        # ── Dict/Map literal: {"k":"v",...} ──────────────────────────────────
        if stripped.startswith('{') and stripped.endswith('}'):
            parsed = self._try_parse_collection(stripped)
            if isinstance(parsed, dict):
                d.ttype = TessType.DICT; d.const_val = parsed; return d
            d.ttype = TessType.DICT; d.const_val = {}; return d

        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            d.ttype = TessType.STRING
            d.const_val = raw[1:-1]
            return d

        if raw.lower() == "true":  d.ttype=TessType.BOOL; d.const_val=True;  return d
        if raw.lower() == "false": d.ttype=TessType.BOOL; d.const_val=False; return d

        try:    v=int(raw);   d.ttype=TessType.INT;   d.const_val=v; return d
        except: pass
        try:    v=float(raw); d.ttype=TessType.FLOAT; d.const_val=v; return d
        except: pass

        if at == "string" and any(op in raw for op in ['+','-','*','/','%','(',')']) :
            d.ttype = TessType.DYNAMIC
            d.expr_node = self._p.parse(raw)
            return d

        if at == "string" and '.' in raw and not raw.replace('.','',1).isdigit():
            d.ttype = TessType.STRING
            d.expr_node = self._p.parse_concatenated_string(raw)
            return d

        if at == "string":
            if re.match(r'^[a-zA-Z_]\w*$', raw):
                d.ttype = TessType.DYNAMIC
                d.expr_node = VarNode(raw)
            else:
                d.ttype = TessType.STRING
                d.const_val = raw
            return d

        if re.match(r'^[a-zA-Z_]\w*\s*\(', raw):
            d.ttype = TessType.DYNAMIC
            d.expr_node = self._p.parse(raw)
            return d

        if re.match(r'^[a-zA-Z_]\w*$', raw):
            d.ttype = TessType.DYNAMIC
            d.expr_node = VarNode(raw)
            return d

        if re.search(r'(?<!\d)\.(?!\d)', raw):
            d.ttype = TessType.STRING
            d.expr_node = self._p.parse_concatenated_string(raw)
            return d

        d.ttype = TessType.DYNAMIC
        d.expr_node = self._p.parse(raw)
        return d


# =============================================================================
# ExprNode -> WebIR dict
# Convierte el arbol de expresiones en un dict compacto para el IR
# =============================================================================

def expr_to_ir(node: ExprNode) -> dict:
    """
    Convierte un ExprNode en un dict IR compacto.
    Claves estandar:
      k  = kind (tipo de nodo)
      v  = value literal
      t  = tipo Tess
      n  = nombre de variable/funcion
      op = operador
      l  = left
      r  = right
      e  = operando unario
      p  = partes (concat)
      a  = args
      m  = modulo
      fn = funcion de modulo
      idx = indices de array
      s  = start de rango
      end = end de rango
      rt = range_type
    """
    if node is None:
        return {"k": "null"}

    if isinstance(node, LiteralNode):
        return {"k": "lit", "v": node.value, "t": node.ttype.value}

    if isinstance(node, VarNode):
        return {"k": "var", "n": node.name}

    if isinstance(node, BinOpNode):
        return {
            "k":  "binop",
            "op": node.op,
            "l":  expr_to_ir(node.left),
            "r":  expr_to_ir(node.right),
        }

    if isinstance(node, LogicalNode):
        return {
            "k":  "logical",
            "op": node.op,
            "l":  expr_to_ir(node.left),
            "r":  expr_to_ir(node.right),
        }

    if isinstance(node, UnaryNode):
        return {
            "k":  "unary",
            "op": node.op,
            "e":  expr_to_ir(node.operand),
        }

    if isinstance(node, ConcatNode):
        return {
            "k": "concat",
            "p": [expr_to_ir(part) for part in node.parts],
        }

    if isinstance(node, FuncCallNode):
        return {
            "k":  "call",
            "n":  node.name,
            "a":  [expr_to_ir(arg) for arg in node.args],
        }

    if isinstance(node, ModCallNode):
        return {
            "k":  "mcall",
            "m":  node.module,
            "fn": node.func,
            "a":  [expr_to_ir(arg) for arg in node.args],
        }

    if isinstance(node, ModVarNode):
        return {
            "k": "mvar",
            "m": node.module,
            "n": node.var,
        }

    if isinstance(node, ArrayAccessNode):
        return {
            "k":   "arr_get",
            "n":   node.array,
            "idx": [expr_to_ir(i) for i in node.indices],
        }

    if isinstance(node, RangeNode):
        return {
            "k":  "range",
            "s":  expr_to_ir(node.start),
            "end":expr_to_ir(node.end),
            "rt": node.range_type,
        }

    if isinstance(node, MethodCallNode):
        return {
            "k":   "method",
            "obj": node.obj,
            "fn":  node.method,
            "a":   [expr_to_ir(arg) for arg in node.args],
        }

    if isinstance(node, PropAccessNode):
        return {
            "k":   "prop",
            "obj": node.obj,
            "n":   node.prop,
        }

    return {"k": "unknown"}


def value_desc_to_ir(desc: ValueDescriptor) -> dict:
    """
    Convierte un ValueDescriptor en un dict IR.
    Si tiene valor constante lo incluye directamente.
    Si tiene ExprNode lo serializa.
    """
    if desc is None:
        return {"k": "null"}
    if desc.const_val is not None and desc.expr_node is None:
        return {"k": "lit", "v": desc.const_val, "t": desc.ttype.value}
    if desc.expr_node is not None:
        return expr_to_ir(desc.expr_node)
    return {"k": "null"}


# =============================================================================
# WebIR Emitter
# Recorre el AST y emite instrucciones IR para cada nodo
# =============================================================================

class WebIREmitter:
    """
    Recorre el JSON AST de Tesseract con la misma logica que tessruntime.py
    pero en lugar de solo analizar, EMITE instrucciones WebIR.

    Cada instruccion es un dict con:
      op   = operacion (DECL, ASSIGN, CONST, CALL, PRINT, READ, IF, FOR,
                        WHILE, DO_WHILE, SWITCH, FUNC, RETURN, BREAK,
                        INC_POST, DEC_POST, INC_PRE, DEC_PRE, IMPORT,
                        PARAM_ASSIGN, ARR_ACCESS)
      + campos especificos segun el op

    Preparado para extension futura:
      OBJ_DECL, OBJ_SET, OBJ_GET, EVENT_BIND, EVENT_EMIT,
      UI_CREATE, UI_APPEND, UI_SET_PROP, COMPONENT_DEF
    """

    def __init__(self, debug: bool = False):
        self.expr_parser    = ExpressionParser()
        self.value_analyzer = ValueAnalyzer(self.expr_parser)
        self.debug          = debug
        # Tabla de modulos para el runtime.js
        self._modules: List[dict] = []
        # Tabla de funciones definidas
        self._functions: List[dict] = []

    def _log(self, msg):
        if self.debug: print(f"[WebIR] {msg}", file=sys.stderr)

    # -------------------------------------------------------------------------
    # Punto de entrada
    # -------------------------------------------------------------------------

    def emit(self, ast: dict) -> dict:
        """
        Emite el WebIR completo desde el AST.
        Retorna un dict con estructura:
          {
            "tess_web_ir": "1.0",
            "modules":   [...],   <- imports declarados
            "functions": [...],   <- funciones definidas
            "main":      [...]    <- instrucciones del cuerpo principal
          }
        """
        if "Program" not in ast:
            raise ValueError("El AST debe tener un nodo raiz 'Program'.")

        main_ir = self._emit_node_list(ast["Program"])

        return {
            "tess_web_ir": WEBIR_VERSION,
            "modules":     self._modules, 
            "main":        main_ir,
        }

    # -------------------------------------------------------------------------
    # Emision de listas de nodos (nivel programa o bloque)
    # -------------------------------------------------------------------------

    def _emit_node_list(self, nodes: list) -> list:
        """Emite instrucciones para una lista de nodos del AST."""
        result = []
        i = 0
        while i < len(nodes):
            node = nodes[i]
            nt   = list(node.keys())[0]

            # WhileLoop puede tener su Block en el siguiente nodo
            if nt == "WhileLoop":
                if i+1 < len(nodes) and "Block" in nodes[i+1]:
                    node["WhileLoop"]["block"] = nodes[i+1]["Block"]
                    i += 2
                    instr = self._emit_node(node)
                    if instr: result.append(instr)
                    continue
                instr = self._emit_node(node)
                if instr: result.append(instr)
                i += 1
                continue

            # SwitchStatement puede tener su block en el siguiente nodo
            if nt == "SwitchStatement":
                if i+1 < len(nodes) and "block" in nodes[i+1]:
                    nx = nodes[i+1]
                    node["SwitchStatement"]["cases"]       = nx.get("cases", [])
                    node["SwitchStatement"]["defaultCase"] = nx.get("defaultCase")
                    i += 2
                    instr = self._emit_node(node)
                    if instr: result.append(instr)
                    continue
                instr = self._emit_node(node)
                if instr: result.append(instr)
                i += 1
                continue

            instr = self._emit_node(node)
            if instr: result.append(instr)
            i += 1

        return result

    def _emit_node(self, node: dict) -> Optional[dict]:
        """Emite una instruccion IR para un nodo del AST."""
        if not node: return None
        nt = list(node.keys())[0]
        self._log(f"emit_node: {nt}")
        handler = getattr(self, f"_emit_{nt}", self._emit_unknown)
        return handler(node[nt])

    def _emit_block(self, block) -> list:
        """Emite instrucciones para un bloque (list o dict)."""
        if isinstance(block, list):
            result = []
            for stmt in block:
                instr = self._emit_node(stmt)
                if instr: result.append(instr)
            return result
        if isinstance(block, dict):
            return self._emit_block_dict(block)
        return []

    def _emit_block_dict(self, block: dict) -> list:
        """Emite instrucciones para un bloque en formato dict (igual que tessruntime.py)."""
        result = []
        items = list(block.items())
        REPAIR = {"if_Condition","forLoop","whileLoop","performWhileLoop"}
        EXEC   = {
            "variableDeclaration","variableAsignement","callExpression",
            "switchStatement","function","functionCall","parameterAsignement",
            "postIncrementStatement","postDecrementStatement",
            "preIncrementStatement","preDecrementStatement",
            "constantDeclaration", "libraryCall", "arrayAccess",
        }
        i = 0
        while i < len(items):
            key, content = items[i]
            if key in REPAIR:
                if i+1 < len(items) and items[i+1][0] == "block":
                    content["block"] = items[i+1][1]; i += 1
                nt = key[0].upper() + key[1:]
                instr = self._emit_node({nt: content})
                if instr: result.append(instr)
            elif key in EXEC:
                nt = key[0].upper() + key[1:]
                if isinstance(content, list):
                    for item in content:
                        instr = self._emit_node({nt: item})
                        if instr: result.append(instr)
                else:
                    instr = self._emit_node({nt: content})
                    if instr: result.append(instr)
            i += 1
        return result

    # -------------------------------------------------------------------------
    # Handlers por tipo de nodo
    # -------------------------------------------------------------------------

    def _emit_VariableDeclaration(self, node: dict) -> dict:
     name     = node["name"]
     val_node = node.get("value")
     if val_node is None or val_node == {}:
        desc   = ValueDescriptor(ttype=TessType.DYNAMIC)
        val_ir = {"k": "undefined"}
     else:
        desc = self.value_analyzer.analyze(val_node)
        # Si analyze() no pudo resolver el valor (null/dynamic sin expr),
        # buscar claves alternas de colección directamente en el nodo raíz
        # (algunos parsers ponen los elementos fuera del sub-nodo "value")
        if desc.const_val is None and desc.expr_node is None:
            for alt_key in ("elements", "items", "content", "values", "entries"):
                alt_raw = node.get(alt_key)
                if isinstance(alt_raw, list):
                    desc.ttype = TessType.ARRAY; desc.const_val = alt_raw; break
                if isinstance(alt_raw, str) and alt_raw.strip().startswith('['):
                    parsed = ValueAnalyzer._try_parse_collection(alt_raw)
                    if isinstance(parsed, list):
                        desc.ttype = TessType.ARRAY; desc.const_val = parsed; break
                if isinstance(alt_raw, dict):
                    desc.ttype = TessType.DICT; desc.const_val = alt_raw; break
        val_ir = value_desc_to_ir(desc)

     return {
        "op":   "DECL",
        "n":    name,
        "t":    desc.ttype.value,
        "jst":  desc.ttype.to_js(),
        "val":  val_ir,
    }

    def _emit_VariableAsignement(self, node: dict) -> dict:
        name     = node["name"]
        val_node = node.get("value", {})
        desc     = self.value_analyzer.analyze(val_node)
        if desc.const_val is None and desc.expr_node is None:
            for alt_key in ("elements", "items", "content", "values", "entries"):
                alt_raw = node.get(alt_key)
                if isinstance(alt_raw, list):
                    desc.ttype = TessType.ARRAY; desc.const_val = alt_raw; break
                if isinstance(alt_raw, dict):
                    desc.ttype = TessType.DICT; desc.const_val = alt_raw; break
        val_ir = value_desc_to_ir(desc)
        self._log(f"ASSIGN '{name}'")

        # Detectar asignacion de indice de array (arr[i] = val)
        index = node.get("index")
        if index is not None:
            idx_expr = self.expr_parser.parse(str(index))
            return {
                "op":  "ARR_SET",
                "n":   name,
                "idx": expr_to_ir(idx_expr),
                "val": val_ir,
            }

        return {
            "op":  "ASSIGN",
            "n":   name,
            "t":   desc.ttype.value,
            "val": val_ir,
        }

    def _emit_ConstantDeclaration(self, node: dict) -> dict:
        name     = node["name"]
        val_node = node.get("value", {})
        desc     = self.value_analyzer.analyze(val_node)
        if desc.const_val is None and desc.expr_node is None:
            for alt_key in ("elements", "items", "content", "values", "entries"):
                alt_raw = node.get(alt_key)
                if isinstance(alt_raw, list):
                    desc.ttype = TessType.ARRAY; desc.const_val = alt_raw; break
                if isinstance(alt_raw, dict):
                    desc.ttype = TessType.DICT; desc.const_val = alt_raw; break
        val_ir = value_desc_to_ir(desc)
        self._log(f"CONST '{name}' tipo={desc.ttype.value}")
        return {
            "op":   "CONST",
            "n":    name,
            "t":    desc.ttype.value,
            "jst":  desc.ttype.to_js(),
            "val":  val_ir,
        }

    def _emit_Function(self, node: dict) -> Optional[dict]:
        name   = node["name"]
        params = self._parse_params(node.get("parameters", {}))
        ret    = TessType.from_str(node.get("explicitType", "dynamic"))
        body   = node.get("block", [])
        body_ir = self._emit_block(body)
    
        # Devolvemos una instrucción que define la función en el flujo
        self._log(f"FUNC '{name}' params={list(params.keys())} ret={ret.value}")
        return {
        "op":   "FUNC",
        "name": name,
        "params": [{"n": pn, "t": pt.value, "jst": pt.to_js()} for pn, pt in params.items()],
        "ret":  ret.value,
        "jret": ret.to_js(),
        "body": body_ir,
        }
        #self._functions.append(fn_ir)
        
        # No emite instruccion en el cuerpo principal, la funcion va a _functions
        #return None

    def _emit_FunctionCall(self, node: dict) -> dict:
        fname = node.get("function", "")
        raw   = node.get("paramenters", {})
        pstr  = raw.get("value", "") if isinstance(raw, dict) else ""
        args  = self._parse_call_args(pstr)
        self._log(f"FUNC_CALL '{fname}'")
        return {
            "op": "CALL",
            "n":  fname,
            "a":  args,
        }

    def _emit_CallExpression(self, node: dict) -> Optional[dict]:
        """
        Replica handle_CallExpression completo:
        Break, Return, mod.func(), print (todos los casos), read, funciones usuario.
        """
        fname = node.get("function", "")

        # -- Break --
        if fname == "Break":
            return {"op": "BREAK"}

        # -- Return --
        if fname == "Return":
            rv = node.get("value") or node.get("arguments") or {}
            ret_expr = None
            if rv and "value" in rv:
                r = rv["value"]
                if isinstance(r, str) and r:
                    ret_expr = expr_to_ir(self.expr_parser.parse(r))
            return {"op": "RETURN", "val": ret_expr}

        # -- mod.func(...) --
        if isinstance(fname, str) and '.' in fname:
            an   = node.get("arguments", {})
            raws = an.get("value", "") if isinstance(an, dict) else ""
            args = self._parse_call_args(raws)
            parts = fname.split('.', 1)
            return {
                "op": "CALL",
                "k":  "mcall",
                "m":  parts[0],
                "fn": parts[1],
                "a":  args,
            }

        an     = node.get("arguments", {})
        pt     = node.get("paramType", "")
        ra     = an.get("value") if isinstance(an, dict) else an
        pt_str = pt if isinstance(pt, str) else (pt.get("value","") if isinstance(pt, dict) else "")

        # -- print --
        if fname == "print" and ra is not None:
            val_ir = self._resolve_print_arg(ra, pt_str, node)
            return {"op": "PRINT", "val": val_ir}

        # -- read --
        # Replica exactamente handle_CallExpression de interpre.py:
        #   arguments_node.get("value")  -> nombre de la variable a asignar (raw_argument)
        #   paramType.get("value")       -> tipo de conversion ('Int','Float','string','bool')
        if fname == "read":
            # target: la variable donde se guarda la entrada (= raw_argument en interpre.py)
            target = ra if isinstance(ra, str) else ""
            # conv: mapeo del tipo Tesseract al codigo que usa runtimeweb.js
            CONV_MAP = {
                "Int":    "int",
                "int":    "int",
                "Float":  "float",
                "float":  "float",
                "Bool":   "bool",
                "bool":   "bool",
                "String": "",
                "string": "",
            }
            conv   = CONV_MAP.get(pt_str, pt_str.lower() if pt_str else "")
            prompt = node.get("prompt", "")
            return {
                "op":     "READ",
                "target": target,
                "conv":   conv,
                "prompt": prompt,
            }

        # -- funcion usuario --
        args_ir = []
        if ra is not None and isinstance(ra, str):
            args_ir = self._parse_call_args(ra)
        elif ra is not None and isinstance(ra, list):
            for item in ra:
                if isinstance(item, dict):
                    desc = self.value_analyzer.analyze(item)
                    args_ir.append(value_desc_to_ir(desc))

        return {
            "op": "CALL",
            "n":  fname,
            "a":  args_ir,
        }

    def _emit_LibraryCall(self, node: dict) -> Optional[dict]:
        """
        Replica handle_LibraryCall completo.
        Registra el modulo en self._modules para el runtime.js.
        """
        mr  = node["module"]
        al  = node.get("alias")
        fns = node.get("functions")
        fa  = node.get("functionAliases", [])
        ia  = node.get("inlineAliases", {})
        on  = node.get("on", [])
        oa  = node.get("onAliases", [])

        is_src = mr.strip("\"'").lower().endswith('.tss')
        if is_src:
            rp   = mr.strip("\"'")
            deft = os.path.splitext(os.path.basename(rp))[0]
            mn   = al if al else deft
        else:
            mn = al if al else mr

        imported: Dict[str, str] = {}
        if fns:
            for idx, orig in enumerate(fns):
                exp = ia.get(orig) or (fa[idx] if idx < len(fa) else orig)
                imported[exp] = orig
        if on:
            for idx, orig in enumerate(on):
                exp = oa[idx] if idx < len(oa) else orig
                imported[exp] = orig

        mod_ir = {
            "name":    mn,
            "src":     is_src,
            "path":    mr,
            "alias":   al or "",
            "imports": imported,
        }
        self._modules.append(mod_ir)
        self._log(f"IMPORT '{mn}' src={is_src} imports={imported}")
        # No emite instruccion en main, va a _modules
        return None

    def _emit_if_Condition(self, node: dict) -> dict:
        """Emite IF con cadena elseif y else."""
        cond_ir = expr_to_ir(self.expr_parser.parse(node.get("condition", "false")))
        then_ir = self._emit_block(node.get("block", []))

        elif_list = []
        cur = node
        while "elseIf" in cur:
            ei      = cur["elseIf"]
            ei_cond = str(ei.get("condition") or ei.get("value", "false"))
            elif_list.append({
                "cond": expr_to_ir(self.expr_parser.parse(ei_cond)),
                "body": self._emit_block(ei.get("block", [])),
            })
            cur = ei

        else_ir = None
        if "else" in node:
            else_ir = self._emit_block(node["else"].get("block", []))

        ir = {
            "op":   "IF",
            "cond": cond_ir,
            "then": then_ir,
        }
        if elif_list:
            ir["elif"] = elif_list
        if else_ir is not None:
            ir["else"] = else_ir
        return ir

    def _emit_ForLoop(self, node: dict) -> dict:
        """Emite FOR con rango y cuerpo."""
        vn  = node["variable"]
        it  = node.get("iterator", {})
        its = it.get("value", "0..0")

        rn   = self.expr_parser.parse(its)
        rn_ir = expr_to_ir(rn)

        # Tipo de la variable iteradora
        iter_type = TessType.INT
        if isinstance(rn, RangeNode):
            if rn.range_type == 'float':  iter_type = TessType.FLOAT
            elif rn.range_type == 'string': iter_type = TessType.STRING

        body_ir = self._emit_block(node.get("block", []))
        self._log(f"FOR '{vn}' range='{its}' tipo={iter_type.value}")
        return {
            "op":   "FOR",
            "var":  vn,
            "t":    iter_type.value,
            "iter": rn_ir,
            "body": body_ir,
        }

    def _emit_WhileLoop(self, node: dict) -> dict:
        cond_ir = expr_to_ir(self.expr_parser.parse(node.get("condition", "false")))
        body_ir = self._emit_block(node.get("block", []))
        return {
            "op":   "WHILE",
            "cond": cond_ir,
            "body": body_ir,
        }

    def _emit_PerformWhileLoop(self, node: dict) -> dict:
        """do-while. Condicion en node['value']."""
        cond_ir = expr_to_ir(self.expr_parser.parse(node.get("value", "false")))
        body_ir = self._emit_block(node.get("block", []))
        return {
            "op":   "DO_WHILE",
            "cond": cond_ir,
            "body": body_ir,
        }

    def _emit_SwitchStatement(self, node: dict) -> dict:
        """Emite SWITCH con cases y default, soporta fall-through."""
        val_ir  = expr_to_ir(self.expr_parser.parse(str(node.get("value", ""))))
        cases   = []
        for case in node.get("cases", []):
            case_val = case.get("case")
            # El valor del case puede ser literal o expresion
            if isinstance(case_val, str):
                cv_ir = expr_to_ir(self.expr_parser.parse(case_val))
            else:
                cv_ir = {"k": "lit", "v": case_val, "t": "dynamic"}
            cases.append({
                "val":  cv_ir,
                "body": self._emit_block(case.get("block", [])),
                "fall": case.get("fallthrough", False),
            })

        default_ir = None
        default    = node.get("defaultCase")
        if default:
            default_ir = self._emit_block(default.get("block", []))

        return {
            "op":      "SWITCH",
            "val":     val_ir,
            "cases":   cases,
            "default": default_ir,
        }

    def _emit_PostIncrementStatement(self, node: dict) -> dict:
        name = node.get("value", "")
        return {"op": "INC_POST", "n": name}

    def _emit_PostDecrementStatement(self, node: dict) -> dict:
        name = node.get("value", "")
        return {"op": "DEC_POST", "n": name}

    def _emit_PreIncrementStatement(self, node: dict) -> dict:
        name = node.get("value", "")
        return {"op": "INC_PRE", "n": name}

    def _emit_PreDecrementStatement(self, node: dict) -> dict:
        name = node.get("value", "")
        return {"op": "DEC_PRE", "n": name}

    def _emit_ParameterAsignement(self, node: dict) -> dict:
        """Reasignacion de parametro dentro de una funcion."""
        pn   = node.get("name", "")
        desc = self.value_analyzer.analyze(node.get("value", {}))
        return {
            "op":  "PARAM_ASSIGN",
            "n":   pn,
            "t":   desc.ttype.value,
            "val": value_desc_to_ir(desc),
        }

    def _emit_ArrayAccess(self, node: dict) -> dict:
        """Acceso a array como expresion-statement."""
        arr = node.get("array", "")
        idx = node.get("index", "0")
        idx_ir = expr_to_ir(self.expr_parser.parse(str(idx)))
        return {
            "op":  "ARR_ACCESS",
            "n":   arr,
            "idx": idx_ir,
        }

    def _emit_unknown(self, node_content) -> Optional[dict]:
        self._log(f"ADVERTENCIA nodo sin handler: {node_content}")
        return None

    # -------------------------------------------------------------------------
    # Helpers de Extension Futura (objetos, eventos, UI)
    # Estan definidos pero vacios — cuando el lenguaje los implemente
    # solo hay que llenarlos, el IR ya los soporta en runtime.js
    # -------------------------------------------------------------------------

    def _emit_ObjDeclaration(self, node: dict) -> dict:
        """
        FUTURO: Declaracion de objeto.
        IR: {"op": "OBJ_DECL", "n": name, "fields": [...], "methods": [...]}
        """
        return {
            "op":      "OBJ_DECL",
            "n":       node.get("name", ""),
            "fields":  [],
            "methods": [],
        }

    def _emit_EventBind(self, node: dict) -> dict:
        """
        FUTURO: Bindear evento a elemento o funcion.
        IR: {"op": "EVENT_BIND", "target": name, "event": "click", "handler": fn_name}
        """
        return {
            "op":      "EVENT_BIND",
            "target":  node.get("target", ""),
            "event":   node.get("event", ""),
            "handler": node.get("handler", ""),
        }

    def _emit_UIElement(self, node: dict) -> dict:
        """
        FUTURO: Creacion de elemento UI (boton, input, div, etc).
        IR: {"op": "UI_CREATE", "tag": "button", "id": name, "props": {...}}
        """
        return {
            "op":   "UI_CREATE",
            "tag":  node.get("tag", "div"),
            "id":   node.get("name", ""),
            "props":{},
        }

    def _emit_ComponentDef(self, node: dict) -> dict:
        """
        FUTURO: Definicion de componente reutilizable.
        IR: {"op": "COMPONENT_DEF", "name": name, "props": [...], "body": [...]}
        """
        return {
            "op":   "COMPONENT_DEF",
            "name": node.get("name", ""),
            "props":[],
            "body": [],
        }

    # -------------------------------------------------------------------------
    # Helpers internos
    # -------------------------------------------------------------------------

    def _parse_params(self, pn: dict) -> Dict[str, TessType]:
        """Parsea parametros de funcion: 'a: int, b: float' -> {a: INT, b: FLOAT}"""
        r = {}
        if "value" not in pn: return r
        for p in pn["value"].split(','):
            p = p.strip()
            if not p: continue
            if ':' in p:
                n, t = p.split(':', 1)
                r[n.strip()] = TessType.from_str(t.strip())
            else:
                r[p] = TessType.DYNAMIC
        return r

    def _parse_call_args(self, args_str: str) -> list:
        """
        Parsea argumentos de llamada a funcion.
        Soporta 'nombre: valor' (argumentos nombrados de Tesseract).
        Retorna lista de IR de expresiones.
        """
        if not args_str or not args_str.strip():
            return []
        result = []
        for p in args_str.split(','):
            p = p.strip()
            if not p: continue
            # Argumento nombrado: ignorar el nombre
            if ':' in p and not p.startswith('"') and not p.startswith("'"):
                parts = p.split(':', 1)
                p = parts[1].strip()
            if p:
                result.append(expr_to_ir(self.expr_parser.parse(p)))
        return result

    def _resolve_print_arg(self, ra: Any, pt_str: str, node: dict) -> dict:
        """
        Replica la logica completa de print en interpre.py.
        Cubre todos los casos: ArrayAccess, ModuleVariable, function con punto,
        llamada a funcion, concatenacion con punto, aritmetica, variable simple.
        """
        if not isinstance(ra, str):
            # Si es lista u otro tipo
            if isinstance(ra, list):
                parts = [expr_to_ir(self.expr_parser.parse(str(x))) for x in ra]
                return {"k": "concat", "p": parts}
            return {"k": "lit", "v": str(ra), "t": "string"}

        if pt_str == "ArrayAccess":
            idx_node = node.get("arguments", {}).get("index", "0")
            arr_name = node.get("arguments", {}).get("array", ra)
            return {
                "k":   "arr_get",
                "n":   arr_name,
                "idx": [expr_to_ir(self.expr_parser.parse(str(idx_node)))],
            }

        if pt_str == "ModuleVariable":
            return expr_to_ir(self.expr_parser.parse(ra))

        if pt_str == "function" and '.' in ra:
            return expr_to_ir(self.expr_parser.parse(ra))

        if re.match(r'^[a-zA-Z_]\w*\s*\(', ra):
            return expr_to_ir(self.expr_parser.parse(ra))

        if pt_str == "string" and '.' in ra and not ra.replace('.', '', 1).isdigit():
            return expr_to_ir(self.expr_parser.parse_concatenated_string(ra))

        if pt_str == "string" and any(op in ra for op in ['+', '-', '*', '/', '%', '(', ')']):
            return expr_to_ir(self.expr_parser.parse(ra))

        if '.' in ra and not ra.replace('.', '', 1).isdigit():
            return expr_to_ir(self.expr_parser.parse_concatenated_string(ra))

        if any(op in ra for op in ['+', '-', '*', '/', ',', '(', ')']):
            return expr_to_ir(self.expr_parser.parse(ra))

        # Variable simple o string literal
        return expr_to_ir(self.expr_parser.parse(ra))


# =============================================================================
# Puntos de entrada publicos
# =============================================================================

def emit_webir(ast_json: dict, debug: bool = False) -> dict:
    """Emite el WebIR desde un dict AST."""
    emitter = WebIREmitter(debug=debug)
    return emitter.emit(ast_json)

def emit_webir_file(ast_path: str, out_path: str = None, debug: bool = False) -> dict:
    """
    Lee un archivo AST JSON y emite el WebIR.
    Si out_path se proporciona, guarda el resultado en ese archivo.
    Retorna el dict WebIR.
    """
    with open(ast_path, 'r', encoding='utf-8') as f:
        ast_data = json.load(f)

    ir = emit_webir(ast_data, debug=debug)

    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(ir, f, ensure_ascii=False, separators=(',', ':'))
        print(f"[tessruntimeweb] WebIR escrito en: {out_path}")
    else:
        print(json.dumps(ir, ensure_ascii=False, separators=(',', ':')))

    return ir


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="tessruntimeweb.py — Tesseract Web IR Emitter"
    )
    ap.add_argument("ast",  help="Archivo AST JSON de entrada")
    ap.add_argument("-o",   metavar="out", help="Archivo WebIR de salida (default: stdout)")
    ap.add_argument("-d",   action="store_true", help="Debug: muestra nodos procesados en stderr")
    ap.add_argument("--pretty", action="store_true", help="Pretty print del JSON de salida")
    args = ap.parse_args()

    with open(args.ast, 'r', encoding='utf-8') as f:
        ast_data = json.load(f)

    ir = emit_webir(ast_data, debug=args.d)

    indent = 2 if args.pretty else None
    sep    = (',', ': ') if args.pretty else (',', ':')
    out_str = json.dumps(ir, ensure_ascii=False, indent=indent, separators=sep)

    if args.o:
        with open(args.o, 'w', encoding='utf-8') as f:
            f.write(out_str)
        print(f"[tessruntimeweb] WebIR -> {args.o}", file=sys.stderr)
    else:
        print(out_str)