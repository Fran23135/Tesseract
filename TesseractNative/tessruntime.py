# =============================================================================
# tessruntime.py — Tesseract Compiler Frontend
# =============================================================================
# Hace exactamente lo mismo que interpre.py al recorrer el JSON:
# construye tablas de símbolos, resuelve tipos, parsea TODAS las expresiones,
# maneja scopes, funciones, módulos, arrays, dicts, concatenaciones,
# llamadas embebidas, accesos profundos, rangos, switch, etc.
#
# La diferencia con interpre.py: en lugar de ejecutar cada nodo,
# produce estructuras de datos (ExprNode, ValueInfo, TessSymbol, etc.)
# que tesscodegen.py usa para emitir LLVM IR exacto.
#
# CUBRE TODO LO QUE interpre.py cubre. Sin simplificaciones.
# =============================================================================

from __future__ import annotations
from ast import expr

import re
import os
import ujson as json
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


# =============================================================================
# TIPOS DE TESSERACT
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
    TUPLE   = "tuple"
    def _tess_type_tag(self, ttype: Optional[TessType]) -> int:
     """Retorna el tag numérico de TessValue para un TessType dado.
        -1 significa dinámico (sin restricción de tipo)."""
     if ttype is None:               return -1
     mapping = {
        TessType.NULL:    0,
        TessType.INT:     1,
        TessType.FLOAT:   2,
        TessType.BOOL:    3,
        TessType.STRING:  4,
        TessType.ARRAY:   5,
        TessType.DICT:    6,
        TessType.TUPLE:   7,
        TessType.DYNAMIC: -1,
     }
     return mapping.get(ttype, -1)

    @staticmethod
    def from_str(s: str) -> "TessType":
        m = {
            "int": TessType.INT, "float": TessType.FLOAT,
            "bool": TessType.BOOL, "string": TessType.STRING,
            "array": TessType.ARRAY, "dict": TessType.DICT,
            "null": TessType.NULL, "any": TessType.DYNAMIC,
            "dynamic": TessType.DYNAMIC, "void": TessType.VOID,
            "inferred": TessType.DYNAMIC, "tuple": TessType.TUPLE
            
        }
        return m.get(s.strip().lower(), TessType.DYNAMIC)

    def is_numeric(self) -> bool:
        return self in (TessType.INT, TessType.FLOAT)

    def is_static(self) -> bool:
        return self not in (TessType.DYNAMIC,)


# =============================================================================
# ÁRBOL DE EXPRESIONES
# Reemplaza el eval() de interpre.py con nodos concretos que tesscodegen
# puede recorrer y emitir IR instrucción por instrucción.
# =============================================================================

class ExprNode:
    """Nodo base de expresión."""
    pass
# AGREGAR después del dataclass DictLiteralNode existente:

@dataclass
class NewObjectNode(ExprNode):
    """new ClassName(args)"""
    class_name: str
    args:       List[ExprNode]

@dataclass
class MethodCallNode(ExprNode):
    """instancia.metodo(args)"""
    obj:    str           # nombre de la variable del objeto
    method: str
    args:   List[ExprNode]

@dataclass
class AttrAccessNode(ExprNode):
    """instancia.atributo (lectura)"""
    obj:  str
    attr: str

@dataclass
class ThisAccessNode(ExprNode):
    """this.campo"""
    field: str

@dataclass
class ThisCallNode(ExprNode):
    """this.metodo(args)"""
    method: str
    args:   List[ExprNode]

@dataclass
class SuperCallNode(ExprNode):
    """super.metodo(args)"""
    method: str
    args:   List[ExprNode]

@dataclass
class TryCatchNode(ExprNode):
    """Nodo informativo de try-catch para el codegen."""
    try_block:   List[dict]
    catch_var:   Optional[str]
    catch_type:  Optional[str]
    catch_block: List[dict]
    finally_block: Optional[List[dict]]

# AGREGAR después de TessModule:

@dataclass
class TessAttribute:
    name:     str
    ttype:    TessType
    modifier: str  = "public"   # public | private | protected
    is_const: bool = False
    default:  Any  = None

@dataclass
class TessMethod:
    name:        str
    params:      Dict[str, TessType]
    return_type: TessType
    body:        List[dict]
    modifier:    str  = "public"
    is_async:    bool = False

@dataclass
class TessClass:
    name:        str
    parent:      Optional[str]       = None
    interfaces:  List[str]           = field(default_factory=list)
    modifier:    Optional[str]       = None   # abstract | final | None
    attributes:  Dict[str, TessAttribute] = field(default_factory=dict)
    methods:     Dict[str, TessMethod]    = field(default_factory=dict)
    constructor: Optional[TessMethod]     = None
    ir_type:     Any = None   # llvmlite identified struct type (lo llena codegen)

@dataclass
class TessInterface:
    name:    str
    methods: Dict[str, TessMethod] = field(default_factory=dict)
@dataclass
class LiteralNode(ExprNode):
    """Literal: int, float, bool, string, null."""
    value: Any
    ttype: TessType

@dataclass
class VarNode(ExprNode):
    """Referencia a variable o parámetro de función."""
    name: str

@dataclass
class BinOpNode(ExprNode):
    """Operación binaria: + - * / % == != < > <= >="""
    op:    str
    left:  ExprNode
    right: ExprNode

@dataclass
class UnaryNode(ExprNode):
    """Negación unaria: -x   o   !x"""
    op:      str  # '-' o '!'
    operand: ExprNode

@dataclass
class LogicalNode(ExprNode):
    """Operadores lógicos: && ||"""
    op:    str   # '&&' o '||'
    left:  ExprNode
    right: ExprNode

@dataclass
class ConcatNode(ExprNode):
    """
    Concatenación con operador punto de Tesseract: "hola" . var . expr
    Misma semántica que _evaluate_concatenated_string en interpre.py.
    Cada parte puede ser string literal, variable, expresión aritmética o llamada a función.
    """
    parts: List[ExprNode]

@dataclass
class FuncCallNode(ExprNode):
    """Llamada a función Tesseract: myfunc(a: 1, b: 2) o myfunc(5)"""
    name: str
    args: List[ExprNode]

@dataclass
class ModCallNode(ExprNode):
    """Llamada a función de módulo: math.sqrt(x)"""
    module: str
    func:   str
    args:   List[ExprNode]
# ── Después de ModCallNode (línea ~222) ──────────────────────────────────────

@dataclass
class CoreCallNode(ExprNode):
    """
    Llamada a método del tipo core: var.toUpperCase() o var.push(x).mut
    var      — nombre de la variable origen
    chain    — lista de pasos [(method_name, [args_ExprNode]), ...]
                 el campo 'method' puede ser 'mut' con args=[]
    mut      — True si el último paso es .mut
    """
    var:   str
    chain: List[Tuple[str, List['ExprNode']]]
    mut:   bool = False
@dataclass
class ModVarNode(ExprNode):
    """Acceso a variable de módulo: math.PI"""
    module: str
    var:    str

@dataclass
class ArrayAccessNode(ExprNode):
    """
    Acceso a array o dict con soporte de acceso profundo.
    arr[i]  →  indices = [VarNode('i')]
    mat[0:j] → indices = [LiteralNode(0), VarNode('j')]
    Misma semántica que _evaluate_array_access en interpre.py.
    """
    array:   str
    indices: List[ExprNode]

@dataclass
class ArrayLiteralNode(ExprNode):
    """Array literal: [1, 2, 3] o [a, b, c]"""
    elements: List[ExprNode]

@dataclass
class DictLiteralNode(ExprNode):
    """Dict literal: {clave: valor, ...}"""
    pairs: List[Tuple[ExprNode, ExprNode]]

@dataclass
class NullNode(ExprNode):
    """Valor null explícito."""
    pass


# =============================================================================
# CLASIFICACIÓN DE EXPRESIONES
# Le dice al codegen qué camino tomar para emitir IR.
# =============================================================================

class ExprKind(Enum):
    LITERAL        = auto()   # int, float, bool, string, null directos
    VARIABLE       = auto()   # nombre de variable
    PARAMETER      = auto()   # parámetro de función actual
    ARITHMETIC     = auto()   # operación aritmética +,-,*,/,%
    COMPARISON     = auto()   # ==, !=, <, >, <=, >=
    LOGICAL        = auto()   # &&, ||
    UNARY          = auto()   # -, !
    STRING_CONCAT  = auto()   # "hola" . var — operador punto de Tesseract
    FUNCTION_CALL  = auto()   # myfunc(args)
    MODULE_CALL    = auto()   # mod.func(args)
    MODULE_VAR     = auto()   # mod.VAR
    ARRAY_ACCESS   = auto()   # arr[i] o arr[i:j]
    ARRAY_LITERAL  = auto()   # [1,2,3]
    DICT_LITERAL   = auto()   # {k:v}
    EMBEDDED_CALLS = auto()   # expresión con llamadas embebidas resueltas
    UNKNOWN        = auto()   # no clasificado — codegen usará runtime dinámico


# =============================================================================
# INFORMACIÓN COMPLETA DE UN VALOR/EXPRESIÓN DEL AST
# Todo lo que tesscodegen necesita saber sobre un valor antes de emitir IR.
# =============================================================================

@dataclass
class ValueInfo:
    """
    Encapsula toda la información de un nodo value del AST,
    exactamente como interpre.py la procesa en handle_VariableDeclaration,
    handle_VariableAsignement, handle_CallExpression, etc.
    """
    raw:       Any             # valor crudo del JSON
    ast_type:  str             # "string", "ModuleVariable", "function", "NULL", etc.
    ttype:     TessType        # tipo inferido
    kind:      ExprKind        # clasificación para el codegen
    expr:      Optional[ExprNode] = None   # árbol de expresión parseado
    param_type: str = ""       # paramType del CallExpression (ArrayAccess, expression, string…)


# =============================================================================
# PARSER DE EXPRESIONES
# Convierte strings del AST en árboles ExprNode.
# Cubre TODO lo que interpre.py maneja en:
#   - resolve_expression
#   - evaluate_expression
#   - _evaluate_arithmetic_operation
#   - _evaluate_concatenated_string
#   - _resolve_embedded_function_calls
#   - _evaluate_array_access
# =============================================================================
# =============================================================================
# TABLA DE MÉTODOS DEL CORE POR TIPO
# Espeja _CORE_TYPE_METHODS de interpre.py.
# Valor: número de parámetros extra (self no cuenta).
# =============================================================================

_CORE_METHODS: Dict[str, Dict[str, int]] = {
    'string': {
        'length': 0, 'isEmpty': 0, 'isArray': 0, 'isString': 0,
        'isInt': 0, 'isFloat': 0, 'isBool': 0, 'type': 0,
        'toUpperCase': 0, 'toLowerCase': 0, 'trim': 0,
        'trimStart': 0, 'trimEnd': 0, 'reverse': 0,
        'repeat': 1, 'replace': 2, 'slice': 2, 'charAt': 1,
        'contains': 1, 'startsWith': 1, 'endsWith': 1,
        'indexOf': 1, 'padStart': 2, 'padEnd': 2, 'split': 1,
        'typeInt': 0, 'typeFloat': 0, 'typeString': 0, 'typeBool': 0,
    },
    'int': {
        'length': 0, 'isEmpty': 0, 'isArray': 0, 'isString': 0,
        'isInt': 0, 'isFloat': 0, 'isBool': 0, 'type': 0,
        'abs': 0, 'clamp': 2, 'pow': 1, 'max': 1, 'min': 1,
        'isEven': 0, 'isOdd': 0, 'isPositive': 0, 'isNegative': 0,
        'typeFloat': 0, 'typeString': 0, 'typeBool': 0, 'typeInt': 0,
    },
    'float': {
        'length': 0, 'isEmpty': 0, 'isArray': 0, 'isString': 0,
        'isInt': 0, 'isFloat': 0, 'isBool': 0, 'type': 0,
        'abs': 0, 'round': 1, 'floor': 0, 'ceil': 0,
        'clamp': 2, 'pow': 1, 'isNaN': 0, 'isInfinite': 0,
        'typeInt': 0, 'typeString': 0, 'typeBool': 0, 'typeFloat': 0,
    },
    'bool': {
        'type': 0, 'isArray': 0, 'isString': 0, 'isInt': 0,
        'isFloat': 0, 'isBool': 0, 'toggle': 0,
        'typeInt': 0, 'typeFloat': 0, 'typeString': 0, 'typeBool': 0,
    },
    'array': {
        'length': 0, 'isEmpty': 0, 'isArray': 0, 'isString': 0,
        'isInt': 0, 'isFloat': 0, 'isBool': 0, 'type': 0,
        'first': 0, 'last': 0,
        'push': 1, 'pop': 0, 'shift': 0, 'unshift': 1,
        'insert': 2, 'remove': 1, 'clear': 0,
        'sort': 0, 'reverse': 0, 'slice': 2, 'concat': 1,
        'contains': 1, 'indexOf': 1, 'join': 1,
        'unique': 0, 'flatten': 0, 'typeString': 0,
        'filter': 0, 'map': 0,   # manejados en interpre; en codegen → no-op
    },
    'null': {
        'isNull': 0, 'isArray': 0, 'isString': 0, 'isInt': 0,
        'isFloat': 0, 'isBool': 0, 'type': 0, 'typeString': 0,
    },
}

# Métodos que mutan el valor por defecto (no necesitan .mut)
_CORE_MUTABLE_DEFAULT: set = {
    'push', 'pop', 'shift', 'unshift', 'insert', 'remove', 'clear',
}

def _is_core_method(type_name: str, method_name: str) -> bool:
    return method_name in _CORE_METHODS.get(type_name, {})
class ExpressionParser:

    # Palabras que nunca son nombres de función llamable
    _RESERVED = {'if', 'while', 'for', 'perform', 'return', 'print', 'read',
                 'true', 'false', 'null', 'and', 'or', 'not', 'break'}

    def __init__(self, known_functions: set = None, known_modules: set = None, known_var_types: Dict[str, str] = None):
        # Se pasan desde el CompileContext para que el parser sepa qué
        # identificadores son funciones y cuáles son módulos, igual que
        # interpre.py consulta symbol_table.get_function() y module_loader.is_loaded()
        self.known_functions = known_functions or set()
        self.known_modules   = known_modules   or set()
        # mapa variable → tipo tesseract ('string','int','float','bool','array','null')
        self.known_var_types: Dict[str, str] = known_var_types or {}


    def update(self, known_functions, known_modules,
           known_var_types: Dict[str, str] = None):
        self.known_functions = known_functions
        self.known_modules   = known_modules
        if known_var_types is not None:
            self.known_var_types = known_var_types
    def _try_parse_core_chain(self, expr: str) -> Optional['CoreCallNode']:
     """
     Detecta: identifier.method[(args)][.method[(args)]...][.mut]
     Solo si identifier está en known_var_types con un tipo que tenga
     ese primer método en _CORE_METHODS.
     """
     # Debe empezar con un identificador seguido de punto
     m = re.match(r'^([A-Za-z_]\w*)\.(.+)$', expr, re.DOTALL)
     if not m:
        return None
     var_name = m.group(1)
     rest     = m.group(2).strip()

     # El identificador no puede ser un módulo cargado
     if var_name in self.known_modules:
        return None

     # Averiguar el tipo — si no lo conocemos intentamos por el primer método
     var_type = self.known_var_types.get(var_name)

    # Parsear la cadena de pasos: "toUpper().trim().slice(0,3).mut"
     steps = self._split_chain_steps(rest)
     if not steps:
        return None

     # Verificar que el PRIMER paso es un método core válido
     first_method = steps[0][0]
     if var_type:
        if not _is_core_method(var_type, first_method):
            return None
     else:
        # Sin tipo conocido: buscar si el método existe en ALGÚN tipo core
        found = any(first_method in methods
                    for methods in _CORE_METHODS.values())
        if not found:
            return None

     # Construir la lista de pasos [(name, [args]), ...]
     chain   = []
     mut_flag = False
     for step_name, raw_args in steps:
        if step_name == 'mut' and not raw_args:
            mut_flag = True
            continue
        args = self._parse_arg_list(raw_args) if raw_args is not None else []
        chain.append((step_name, args))

     if not chain:
        return None
     return CoreCallNode(var=var_name, chain=chain, mut=mut_flag)
    def _split_chain_steps(self, chain_str: str) -> List[Tuple[str, Optional[str]]]:
     """
     Divide "toUpperCase().trim().slice(0,3).mut" en
     [('toUpperCase', ''), ('trim', ''), ('slice', '0,3'), ('mut', None)]
     Respeta paréntesis anidados.
     """
     steps = []
     s     = chain_str
     while s:
        # Primer identificador
        m = re.match(r'^([A-Za-z_]\w*)', s)
        if not m:
            break
        name = m.group(1)
        s = s[len(name):]

        # ¿Tiene paréntesis de argumentos?
        if s.startswith('('):
            depth   = 0
            i       = 0
            for i, c in enumerate(s):
                if c == '(':  depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        break
            raw_args = s[1:i]   # contenido entre ( y )
            s = s[i+1:]
        else:
            raw_args = None     # propiedad sin paréntesis (como 'mut' o 'length')

        steps.append((name, raw_args))

        # Consumir el punto separador
        if s.startswith('.'):
            s = s[1:]
        elif s:
            break   # sintaxis inesperada
     return steps
    # ── Punto de entrada principal ────────────────────────────────────────────
    def parse(self, expr: str) -> ExprNode:
        """
        Parsea una expresión string → ExprNode.
        Sigue la misma jerarquía de decisión que resolve_expression:
          1. ¿Es llamada a módulo? (mod.func)       → ModCallNode / ModVarNode
          2. ¿Es llamada a función simple?           → FuncCallNode
          3. ¿Contiene llamadas embebidas?           → resuelve recursivamente
          4. ¿Contiene operador . (no decimal)?      → ConcatNode
          5. ¿Es expresión aritmética válida?        → árbol BinOpNode
          6. ¿Es expresión booleana/comparación?    → árbol BinOpNode/LogicalNode
          7. Resto                                   → VarNode / LiteralNode
        """
        
        if not isinstance(expr, str):
            return self._literal_from_python(expr)
            expr = expr.strip()
        expr = expr.strip()
        if not expr:
            return NullNode()
        
        expr = self._strip_outer_parens(expr)
        # ── CASO 0: encadenamiento de tipo core  var.metodo(args).metodo2.mut ───
        core_node = self._try_parse_core_chain(expr)
        if core_node:
            return core_node

        # 1. Llamada completa de módulo: mod.func(args)
        m = re.match(r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\((.*)?\)$', expr, re.DOTALL)
        if m:
            mod, func, raw_args = m.groups()
            if mod in self.known_modules or not self.known_modules:
                args = self._parse_arg_list(raw_args or "")
                return ModCallNode(mod, func, args)

        # 2. Variable de módulo: mod.VAR (sin paréntesis)
        m = re.match(r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)$', expr)
        if m:
            mod, var = m.groups()
            if mod in self.known_modules or not self.known_modules:
                return ModVarNode(mod, var)

        # 3. Llamada a función simple: func(args)
        m = re.match(r'^([A-Za-z_]\w*)\s*\((.*)?\)$', expr, re.DOTALL)
        if m:
            name, raw_args = m.groups()
            if name not in self._RESERVED:
                args = self._parse_arg_list(raw_args or "")
                return FuncCallNode(name, args)

        # 4. Acceso a array / dict: arr[...] con posible acceso profundo arr[i:j]
        m = re.match(r'^([A-Za-z_]\w*)\[(.+)\]$', expr)
        if m:
            name, raw_idx = m.groups()
            indices = [self.parse(i.strip()) for i in raw_idx.split(':')]
            return ArrayAccessNode(name, indices)

        # 5. Null / bool literals
        if expr.lower() == 'null':
            return NullNode()
        if expr.lower() == 'true':
            return LiteralNode(True, TessType.BOOL)
        if expr.lower() == 'false':
            return LiteralNode(False, TessType.BOOL)

        # 6. String literal
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return LiteralNode(expr[1:-1], TessType.STRING)

        # 7. Número
        try:
            if '.' in expr:
                return LiteralNode(float(expr), TessType.FLOAT)
        except ValueError:
            pass
        try:
            return LiteralNode(int(expr), TessType.INT)
        except ValueError:
            pass

        # 8. Contiene punto de concatenación (no decimal, no acceso módulo)
        #    Mismo criterio que resolve_expression: re.search(r'(?<!\d)\.(?!\d)')
        if self._has_concat_dot(expr):
            return self._parse_concat(expr)

        # 9. Expresiones con operadores lógicos (&&, ||)
        node = self._try_parse_logical(expr)
        if node:
            return node

        # 10. Expresiones con comparadores
        node = self._try_parse_comparison(expr)
        if node:
            return node

        # 11. Expresiones aritméticas (+, -, *, /, %)
        #     Mismo criterio que _is_valid_arithmetic_format
        if self._has_arithmetic(expr):
            node = self._try_parse_additive(expr)
            if node:
                return node

        # 11.5 — Unario: -x, !x  (antes caía al fallback DYNAMIC → null)
        node = self._try_parse_unary(expr)
        if node:
            return node

        # 12. Identificador simple (variable o parámetro)
        if re.match(r'^[A-Za-z_]\w*$', expr):
            return VarNode(expr)

        # 13. Fallback: expresión dinámica no parseada → nodo literal DYNAMIC
        return LiteralNode(expr, TessType.DYNAMIC)

    # ── Concat: "hola" . var . expr ─────────────────────────────────────────

    def _has_concat_dot(self, expr: str) -> bool:
     in_str   = False
     str_char = ''
     depth    = 0
     for i, c in enumerate(expr):
        if not in_str:
            if c in ('"', "'"):
                in_str = True; str_char = c
            elif c in '([{': depth += 1
            elif c in ')]}': depth -= 1
            elif c == '.' and depth == 0:
                prev = expr[i-1] if i > 0       else ''
                nxt  = expr[i+1] if i+1 < len(expr) else ''
                # punto decimal: dígito antes o después
                if prev.isdigit() or nxt.isdigit():
                    continue
                # acceso a módulo: word.word sin espacios → NO es concat
                if (prev.isalnum() or prev == '_') and (nxt.isalpha() or nxt == '_'):
                    continue
                return True
        elif c == str_char:
            in_str = False
     return False

    def _parse_concat(self, expr: str) -> ExprNode:
        """
        Divide la expresión por el punto de concatenación respetando:
        - Decimales: 3.14 no se parte
        - Llamadas de módulo: math.sqrt(x) no se parte
        - Paréntesis anidados
        Misma lógica que _evaluate_concatenated_string en interpre.py.
        """
        parts = self._split_concat_dot(expr)
        if len(parts) == 1:
            # No era concatenación real — parsear como expresión
            return self._parse_expr_fallback(expr)
        nodes = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Cada parte puede ser: string literal, variable, expresión aritmética,
            # llamada a función, o llamada a módulo
            nodes.append(self.parse(part))
        return ConcatNode(nodes)

    def _split_concat_dot(self, expr: str) -> List[str]:
        """
        Divide por el operador punto de concatenación, ignorando:
        - decimales (dígito.dígito)
        - llamadas mod.func (identificador.identificador seguido de '(')
        """
        parts = []
        current = []
        depth = 0
        i = 0
        while i < len(expr):
            c = expr[i]
            if c in '([{':
                depth += 1
            elif c in ')]}':
                depth -= 1

            if c == '.' and depth == 0:
                prev = expr[i - 1] if i > 0 else ''
                nxt  = expr[i + 1] if i + 1 < len(expr) else ''

                # Decimal: dígito.dígito
                if prev.isdigit() and nxt.isdigit():
                    current.append(c)
                    i += 1
                    continue

                # Acceso de módulo: letra.letra (sin espacio), seguido posiblemente de '('
                # Se detecta si el lado izquierdo y derecho son identificadores
                left_part  = ''.join(current).strip()
                rest       = expr[i + 1:].strip()
                is_mod_dot = (bool(re.match(r'^[A-Za-z_]\w*$', left_part)) and
                              bool(re.match(r'^[A-Za-z_]', rest)))
                # Si el módulo está en known_modules, es acceso de módulo
                if is_mod_dot and (left_part in self.known_modules or not self.known_modules):
                    current.append(c)
                    i += 1
                    continue

                # Es operador de concatenación
                parts.append(''.join(current))
                current = []
                i += 1
                continue

            current.append(c)
            i += 1

        parts.append(''.join(current))
        return [p for p in parts if p.strip()]

    # ── Lógicos ──────────────────────────────────────────────────────────────

    def _try_parse_logical(self, expr: str) -> Optional[ExprNode]:
        for op in ['||', '&&']:
            res = self._split_right(expr, op)
            if res:
                left_str, right_str = res
                left  = self.parse(left_str)
                right = self.parse(right_str)
                return LogicalNode(op, left, right)
        return None

    # ── Comparaciones ────────────────────────────────────────────────────────

    def _try_parse_comparison(self, expr: str) -> Optional[ExprNode]:
        for op in ['==', '!=', '<=', '>=', '<', '>']:
            res = self._split_right(expr, op)
            if res:
                left_str, right_str = res
                return BinOpNode(op, self.parse(left_str), self.parse(right_str))
        return None

    # ── Aritmética ───────────────────────────────────────────────────────────

    def _has_arithmetic(self, expr: str) -> bool:
        return any(op in expr for op in ['+', '-', '*', '/', '%'])

    def _try_parse_additive(self, expr: str) -> Optional[ExprNode]:
        res = self._split_right(expr, '+') or self._split_right(expr, '-')
        if res:
            left_str, right_str = res
            op = '+' if '+' in expr[:expr.index(right_str)] else '-'
            # Encontrar cuál operador fue
            for o in ['+', '-']:
                r = self._split_right(expr, o)
                if r:
                    left  = self._try_parse_multiplicative(r[0]) or self.parse(r[0])
                    right = self._try_parse_multiplicative(r[1]) or self.parse(r[1])
                    return BinOpNode(o, left, right)
        return self._try_parse_multiplicative(expr)

    def _try_parse_multiplicative(self, expr: str) -> Optional[ExprNode]:
        for op in ['*', '/', '%']:
            res = self._split_right(expr, op)
            if res:
                left  = self.parse(res[0])
                right = self.parse(res[1])
                return BinOpNode(op, left, right)
        return None

    # ── Unario ───────────────────────────────────────────────────────────────

    def _try_parse_unary(self, expr: str) -> Optional[ExprNode]:
        expr = expr.strip()
        if expr.startswith('!'):
            return UnaryNode('!', self.parse(expr[1:]))
        if expr.startswith('-') and len(expr) > 1:
            rest = expr[1:].strip()
            if rest and not rest[0].isdigit():
                return UnaryNode('-', self.parse(rest))
        return None

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _parse_expr_fallback(self, expr: str) -> ExprNode:
        node = (self._try_parse_logical(expr) or
                self._try_parse_comparison(expr) or
                self._try_parse_additive(expr))
        return node or LiteralNode(expr, TessType.DYNAMIC)

    # ── Helpers de división respetando paréntesis ────────────────────────────

    def _split_right(self, expr: str, op: str) -> Optional[Tuple[str, str]]:
        """
        Divide expr por la última aparición de op fuera de paréntesis.
        Asociatividad izquierda: recorre de derecha a izquierda.
        """
        depth = 0
        i = len(expr) - 1
        op_len = len(op)
        while i >= 0:
            c = expr[i]
            if c in ')]}':
                depth += 1
            elif c in '([{':
                depth -= 1
            if depth == 0:
                if expr[i:i + op_len] == op:
                    left  = expr[:i].strip()
                    right = expr[i + op_len:].strip()
                    if left and right:
                        return left, right
                # Para operadores de un carácter, también buscar atrás
                if op_len == 1 and i >= 0 and expr[i] == op[0]:
                    left  = expr[:i].strip()
                    right = expr[i + 1:].strip()
                    if left and right:
                        return left, right
            i -= 1
        return None

    def _literal_from_python(self, val: Any) -> ExprNode:
        if val is None:
            return NullNode()
        if isinstance(val, bool):
            return LiteralNode(val, TessType.BOOL)
        if isinstance(val, int):
            return LiteralNode(val, TessType.INT)
        if isinstance(val, float):
            return LiteralNode(val, TessType.FLOAT)
        if isinstance(val, str):
            return LiteralNode(val, TessType.STRING)
        if isinstance(val, list):
            return ArrayLiteralNode([self._literal_from_python(e) for e in val])
        if isinstance(val, dict):
            pairs = [(LiteralNode(str(k), TessType.STRING), self._literal_from_python(v))
                     for k, v in val.items()]
            return DictLiteralNode(pairs)
        return NullNode()

    # ── Parser de lista de argumentos ────────────────────────────────────────

    def _parse_arg_list(self, raw: str) -> List[ExprNode]:
        """
        Parsea "a: 1, b: 5, c: 5" o "1, 5, 5" o ""
        Misma lógica que _parse_call_parameters_from_string en interpre.py.
        """
        if not raw.strip():
            return []
        args = []
        for part in self._split_args(raw):
            part = part.strip()
            if not part:
                continue
            # Formato "nombre: valor" — solo el valor importa para la emisión IR
            is_literal_str = (part.startswith('"') and part.endswith('"')) or \
                             (part.startswith("'") and part.endswith("'"))
            if ':' in part and not is_literal_str:
                _, val_part = part.split(':', 1)
                part = val_part.strip()
            args.append(self.parse(part))
        return args

    def _split_args(self, raw: str) -> List[str]:
        """Divide argumentos por coma respetando paréntesis y strings."""
        parts = []
        current = []
        depth = 0
        in_str = False
        str_char = ''
        for c in raw:
            if not in_str and c in ('"', "'"):
                in_str = True
                str_char = c
            elif in_str and c == str_char:
                in_str = False
            if not in_str:
                if c in '([{':
                    depth += 1
                elif c in ')]}':
                    depth -= 1
                if c == ',' and depth == 0:
                    parts.append(''.join(current))
                    current = []
                    continue
            current.append(c)
        if current:
            parts.append(''.join(current))
        return parts
    def _strip_outer_parens(self, expr: str) -> str:
     """Quita paréntesis externos si toda la expresión está envuelta en ellos."""
     while expr.startswith('(') and expr.endswith(')'):
        depth = 0
        matched = False
        for i, c in enumerate(expr):
            if c == '(':   depth += 1
            elif c == ')': depth -= 1
            if depth == 0:
                if i == len(expr) - 1:
                    # el ( inicial y ) final son pareja — quitar y repetir
                    expr = expr[1:-1].strip()
                    matched = True
                break
        if not matched:
            break
     return expr


# =============================================================================
# INFERENCIA DE TIPOS
# Misma lógica que _infer_type, _get_type_name, y la detección de tipos
# en handle_VariableDeclaration de interpre.py.
# =============================================================================

class TypeInferrer:

    @staticmethod
    def from_python(val: Any) -> TessType:
        if val is None:                         return TessType.NULL
        if isinstance(val, bool):               return TessType.BOOL
        if isinstance(val, int):                return TessType.INT
        if isinstance(val, float):              return TessType.FLOAT
        if isinstance(val, str):                return TessType.STRING
        if isinstance(val, list):               return TessType.ARRAY
        if isinstance(val, dict):               return TessType.DICT
        return TessType.DYNAMIC

    @staticmethod
    def from_value_node(value_node: dict) -> TessType:
        """
        Lee un nodo value del AST y determina el tipo.
        Cubre todos los casos de handle_VariableDeclaration:
        - explicitType
        - ast_type: NULL, string, ModuleVariable, function, ArrayAccess, expression
        - valor crudo Python (int, float, bool, list, dict)
        - string que parece número
        """
        explicit = value_node.get("explicitType")
        if explicit:
            return TessType.from_str(explicit)

        ast_type = value_node.get("type", "")
        raw      = value_node.get("value")

        if ast_type == "NULL" or raw == "null":
            return TessType.NULL
        if ast_type == "string":
            # Puede ser string puro o concatenación con variables
            return TessType.STRING
        if ast_type in ("ModuleVariable",):
            return TessType.DYNAMIC  # resultado de mod.VAR
        if ast_type == "function":
            # Puede ser llamada a función de módulo (mod.func) o función propia
            return TessType.DYNAMIC
        if ast_type == "ArrayAccess":
            return TessType.DYNAMIC  # resultado de acceso a array
        if ast_type == "expression":
            return TessType.DYNAMIC  # expresión arbitraria

        # Inferir desde el valor Python crudo
        if isinstance(raw, bool):   return TessType.BOOL
        if isinstance(raw, int):    return TessType.INT
        if isinstance(raw, float):  return TessType.FLOAT
        if isinstance(raw, list):   return TessType.ARRAY
        if isinstance(raw, dict):   return TessType.DICT

        if isinstance(raw, str):
            lo = raw.strip().lower()
            if lo == 'true' or lo == 'false':  return TessType.BOOL
            if lo == 'null':                   return TessType.NULL
            # String literal con comillas → STRING
            if (raw.startswith('"') and raw.endswith('"')) or \
               (raw.startswith("'") and raw.endswith("'")):
                return TessType.STRING
            # Número como string
            try: int(raw);   return TessType.INT
            except ValueError: pass
            try: float(raw); return TessType.FLOAT
            except ValueError: pass
            # Expresión con operadores → resultado puede ser numérico o string
            if any(op in raw for op in ['+', '-', '*', '/', '%']):
                return TessType.DYNAMIC
            # Tiene punto de concatenación → STRING
            if re.search(r'(?<!\d)\.(?!\d)', raw):
                return TessType.STRING

        return TessType.DYNAMIC

    @staticmethod
    def from_expr_node(node: ExprNode, ctx: "CompileContext" = None) -> TessType:
     if isinstance(node, LiteralNode):
        return node.ttype
     if isinstance(node, NullNode):
        return TessType.NULL
     if isinstance(node, VarNode):
        if ctx:
            sym = ctx.symbol_table.lookup(node.name)
            if sym:
                return sym.ttype
        return TessType.DYNAMIC
     if isinstance(node, BinOpNode):
        if node.op in ('==', '!=', '<', '>', '<=', '>='):
            return TessType.BOOL
        l = TypeInferrer.from_expr_node(node.left, ctx)
        r = TypeInferrer.from_expr_node(node.right, ctx)
        if l == TessType.FLOAT or r == TessType.FLOAT:
            return TessType.FLOAT
        if l == TessType.INT and r == TessType.INT:
            return TessType.INT
        return TessType.DYNAMIC
     if isinstance(node, LogicalNode):
        return TessType.BOOL
     if isinstance(node, UnaryNode):
        if node.op == '!':
            return TessType.BOOL
        return TypeInferrer.from_expr_node(node.operand, ctx)
     if isinstance(node, ConcatNode):
        return TessType.STRING
     if isinstance(node, ArrayLiteralNode):
        return TessType.ARRAY
     if isinstance(node, DictLiteralNode):
        return TessType.DICT
     # FuncCallNode, ModCallNode, ArrayAccessNode → DYNAMIC por defecto
     return TessType.DYNAMIC  # VarNode, FuncCallNode, ModCallNode, ArrayAccessNode


# =============================================================================
# CLASIFICADOR DE EXPRESIONES
# Le dice al codegen qué tipo de IR emitir para cada valor del AST.
# =============================================================================

class ExprClassifier:

    @staticmethod
    def classify_value_node(value_node: dict) -> ExprKind:
        """
        Clasifica el tipo de expresión de un nodo value del AST.
        Cubre todos los casos de handle_VariableDeclaration y handle_VariableAsignement.
        """
        ast_type  = value_node.get("type", "")
        raw       = value_node.get("value")

        if ast_type == "NULL" or raw == "null":
            return ExprKind.LITERAL

        if ast_type == "ModuleVariable":
            return ExprKind.MODULE_VAR

        if ast_type == "function":
            if isinstance(raw, str) and '.' in raw:
                if '(' in raw:
                    return ExprKind.MODULE_CALL
                return ExprKind.MODULE_VAR
            return ExprKind.FUNCTION_CALL

        if ast_type == "ArrayAccess":
            return ExprKind.ARRAY_ACCESS

        if ast_type == "expression":
            return ExprKind.COMPARISON

        if isinstance(raw, (bool, int, float)):
            return ExprKind.LITERAL

        if isinstance(raw, list):
            return ExprKind.ARRAY_LITERAL

        if isinstance(raw, dict):
            return ExprKind.DICT_LITERAL

        if isinstance(raw, str):
            # Literal con comillas
            if (raw.startswith('"') and raw.endswith('"')) or \
               (raw.startswith("'") and raw.endswith("'")):
                return ExprKind.LITERAL

            # Llamada a función: func(...)
            if re.match(r'^[A-Za-z_]\w*\s*\(.*\)$', raw, re.DOTALL):
                if '.' in raw.split('(')[0]:
                    return ExprKind.MODULE_CALL
                return ExprKind.FUNCTION_CALL

            # Acceso a array: arr[...]
            if re.match(r'^[A-Za-z_]\w*\[.+\]$', raw):
                return ExprKind.ARRAY_ACCESS

            # Concatenación con punto (no decimal)
            if re.search(r'(?<!\d)\.(?!\d)', raw):
                # Puede ser concatenación o acceso a módulo
                if '(' in raw:
                    return ExprKind.MODULE_CALL
                # Si tiene punto entre identificadores → módulo o concat
                return ExprKind.STRING_CONCAT

            # Operadores lógicos
            if '&&' in raw or '||' in raw:
                return ExprKind.LOGICAL

            # Operadores de comparación
            for op in ['==', '!=', '<=', '>=', '<', '>']:
                if op in raw:
                    return ExprKind.COMPARISON

            # Operadores aritméticos
            if any(op in raw for op in ['+', '-', '*', '/', '%']):
                return ExprKind.ARITHMETIC

            # Variable simple
            if re.match(r'^[A-Za-z_]\w*$', raw):
                return ExprKind.VARIABLE

            # Literal numérico como string
            try: int(raw);   return ExprKind.LITERAL
            except ValueError: pass
            try: float(raw); return ExprKind.LITERAL
            except ValueError: pass

        return ExprKind.UNKNOWN

    @staticmethod
    def classify_expr_node(node: ExprNode) -> ExprKind:
        if isinstance(node, LiteralNode):     return ExprKind.LITERAL
        if isinstance(node, NullNode):        return ExprKind.LITERAL
        if isinstance(node, VarNode):         return ExprKind.VARIABLE
        if isinstance(node, BinOpNode):
            if node.op in ('==','!=','<','>','<=','>='):
                return ExprKind.COMPARISON
            return ExprKind.ARITHMETIC
        if isinstance(node, LogicalNode):     return ExprKind.LOGICAL
        if isinstance(node, UnaryNode):       return ExprKind.UNARY
        if isinstance(node, ConcatNode):      return ExprKind.STRING_CONCAT
        if isinstance(node, FuncCallNode):    return ExprKind.FUNCTION_CALL
        if isinstance(node, ModCallNode):     return ExprKind.MODULE_CALL
        if isinstance(node, ModVarNode):      return ExprKind.MODULE_VAR
        if isinstance(node, ArrayAccessNode): return ExprKind.ARRAY_ACCESS
        if isinstance(node, ArrayLiteralNode):return ExprKind.ARRAY_LITERAL
        if isinstance(node, DictLiteralNode): return ExprKind.DICT_LITERAL
        return ExprKind.UNKNOWN


# =============================================================================
# SÍMBOLO DE COMPILACIÓN
# =============================================================================
# AGREGAR justo antes del dataclass TessSymbol:

@dataclass
class TessTypeInfo:
    """
    Tipo recursivo para colecciones anidadas.
    array<array<int>>  → TessTypeInfo(ARRAY, inner=TessTypeInfo(ARRAY, inner=TessTypeInfo(INT)))
    dict<string, int>  → TessTypeInfo(DICT, key_type=TessTypeInfo(STRING), val_type=TessTypeInfo(INT))
    """
    tag:      TessType
    inner:    Optional['TessTypeInfo'] = None   # elemento para array/tuple
    key_type: Optional['TessTypeInfo'] = None   # clave para dict
    val_type: Optional['TessTypeInfo'] = None   # valor para dict
    limit:    int = -1                           # -1 = sin límite

    def is_dynamic(self) -> bool:
        return self.tag == TessType.DYNAMIC

    def __repr__(self):
        if self.tag == TessType.DICT:
            return f"dict<{self.key_type},{self.val_type}>"
        if self.inner:
            s = f"{self.tag.value}<{self.inner}>"
        else:
            s = self.tag.value
        if self.limit >= 0:
            s += f"[{self.limit}]"
        return s


def parse_type_info(s: str, limit: int = -1) -> TessTypeInfo:
    """
    Parsea strings de tipo anidado → TessTypeInfo.
    Ejemplos:
      "int"                    → TessTypeInfo(INT)
      "array<int>"             → TessTypeInfo(ARRAY, inner=TessTypeInfo(INT))
      "array<array<int>>"      → TessTypeInfo(ARRAY, inner=TessTypeInfo(ARRAY, inner=TessTypeInfo(INT)))
      "dict<string,int>"       → TessTypeInfo(DICT, key=TessTypeInfo(STRING), val=TessTypeInfo(INT))
      "dict<string,array<int>>"→ TessTypeInfo(DICT, key=STRING, val=TessTypeInfo(ARRAY,inner=INT))
      "tuple<float>"           → TessTypeInfo(TUPLE, inner=TessTypeInfo(FLOAT))
    """
    s = s.strip()
    if not s:
        return TessTypeInfo(TessType.DYNAMIC, limit=limit)

    # Detectar tipo con parámetros: nombre<...>
    m = re.match(r'^(\w+)\s*<(.+)>$', s)
    if not m:
        # Tipo simple
        return TessTypeInfo(TessType.from_str(s), limit=limit)

    outer_name = m.group(1).strip().lower()
    inner_str  = m.group(2).strip()
    outer_type = TessType.from_str(outer_name)

    if outer_type == TessType.DICT:
        # Dividir K, V respetando anidamiento
        key_str, val_str = _split_type_params(inner_str)
        return TessTypeInfo(
            TessType.DICT,
            key_type=parse_type_info(key_str),
            val_type=parse_type_info(val_str),
            limit=limit
        )
    else:
        # array<X> o tuple<X>
        return TessTypeInfo(
            outer_type,
            inner=parse_type_info(inner_str),
            limit=limit
        )


def _split_type_params(s: str) -> tuple:
    """Divide 'K, V' en ('K', 'V') respetando < > anidados."""
    depth = 0
    for i, c in enumerate(s):
        if c == '<': depth += 1
        elif c == '>': depth -= 1
        elif c == ',' and depth == 0:
            return s[:i].strip(), s[i+1:].strip()
    return s.strip(), ''
@dataclass
class TessSymbol:
    name:        str
    ttype:       TessType
    is_const:    bool = False
    const_value: Any  = None   # valor constante conocido en compilación
    ir_ref:      Any  = None   # AllocaInstr de llvmlite (lo llena tesscodegen)
    type_info:   Optional[TessTypeInfo] = None 
    is_tuple:    bool = False
    is_explicit_type: bool = False  # si el tipo fue declarado explícitamente

    # ── Metadata de colecciones (array, tuple, dict) ──────────────────────────
    elem_type:        Optional[TessType] = None  # tipo de elemento si explicitType
    limit:            Optional[int]      = None  # límite máximo si tiene nodo limit
    key_type:         Optional[TessType] = None  # tipo de clave para dict tipado
    val_type:         Optional[TessType] = None  # tipo de valor para dict tipado
    is_tuple:         bool               = False # True si es tupla


@dataclass
class TessFunction:
    name:        str
    params:      Dict[str, TessType]     # nombre → tipo
    return_type: TessType
    body:        List[dict]              # nodos JSON del bloque
    ir_func:     Any = None              # ir.Function (lo llena tesscodegen)
    is_explicit_return: bool = False     # si la función tiene return con tipo explícito
    is_entry_point:     bool = False    # si la función es el punto de entrada (main)


# REEMPLAZAR el dataclass TessModule con:
@dataclass
class TessModuleExport:
    name:       str
    value:      Any
    ttype:      TessType
    is_const:   bool = True

@dataclass
class TessModuleFunction:
    name:       str
    params:     Dict[str, TessType]
    return_type: TessType
    is_native:  bool = True
    block:       List[dict] = field(default_factory=list) 

@dataclass
class TessModuleClass:
    name:     str
    methods:  Dict[str, TessModuleFunction] = field(default_factory=dict)
    # ir_type: el struct LLVM (lo llena tesscodegen)
    ir_type:  Any = None

@dataclass
class TessModule:
    name:         str
    is_source:    bool
    path:         str  = ""
    alias:        str  = ""
    functions:    List[str]              = field(default_factory=list)
    func_aliases: Dict[str, str]         = field(default_factory=dict)
    # Contenido real del .tmd — poblado por load_tmd_metadata
    exports:      Dict[str, TessModuleExport]   = field(default_factory=dict)
    mod_functions: Dict[str, TessModuleFunction] = field(default_factory=dict)
    classes:      Dict[str, TessModuleClass]    = field(default_factory=dict)
    # Ruta real al .tmd encontrado
    tmd_path:     str  = ""

# AGREGAR después del dataclass TessModule:

def _get_libs_dir() -> str:
    """Misma lógica que module_loader._get_libs_dir()."""
    import sys, os
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.path.join(home, ".local", "share")
    return os.path.join(base, "Tess", "libs")


def _find_tmd(module_name: str, extra_paths: List[str] = None) -> Optional[str]:
    """Busca el .tmd igual que ModuleLoader._find_tmd()."""
    paths = [_get_libs_dir()]
    if extra_paths:
        paths = list(extra_paths) + paths
    for path in paths:
        full = os.path.join(path, module_name + ".tmd")
        if os.path.isfile(full):
            return full
    return None


def load_tmd_metadata(module_name: str,
                      extra_paths: List[str] = None,
                      debug: bool = False) -> Optional['TessModule']:
    """
    Lee el .tmd y construye un TessModule con todo el contenido:
    exports, funciones libres y clases con sus métodos.
    No ejecuta nada — solo extrae metadata de tipos para el compilador.
    """
    tmd_path = _find_tmd(module_name, extra_paths)
    if not tmd_path:
        if debug:
            print(f"[tessruntime] .tmd no encontrado para '{module_name}'")
        return None

    try:
        with open(tmd_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        if debug:
            print(f"[tessruntime] Error leyendo '{tmd_path}': {e}")
        return None

    mod = TessModule(
        name=module_name, is_source=False,
        path=module_name, tmd_path=tmd_path
    )

    # ── Exports ───────────────────────────────────────────────────────────────
    for ename, edef in data.get("exports", {}).items():
        ttype = TessType.from_str(edef.get("type", "dynamic"))
        mod.exports[ename] = TessModuleExport(
            name=ename, value=edef.get("value"),
            ttype=ttype, is_const=edef.get("const", True)
        )

    # ── Funciones libres ─────────────────────────────────────────────────────
    for fname, fdef in data.get("functions", {}).items():
        params  = _parse_tmd_params(fdef.get("params", {}))
        ret     = TessType.from_str(fdef.get("return_type", "dynamic"))
        mod.mod_functions[fname] = TessModuleFunction(
            name=fname, params=params, return_type=ret,
            is_native=fdef.get("native", False),
            block=fdef.get("block", []) 
        )

    # ── Clases ────────────────────────────────────────────────────────────────
    for cname, cdef in data.get("classes", {}).items():
        cls = TessModuleClass(name=cname)
        # Constructor como método especial __init__
        ctor_def = cdef.get("constructor", {})
        if ctor_def:
            cparams = _parse_tmd_params(ctor_def.get("params", {}))
            cls.methods["__init__"] = TessModuleFunction(
                name="__init__", params=cparams,
                return_type=TessType.DYNAMIC,
                is_native=ctor_def.get("native", False)
            )
        # Métodos
        for mname, mdef in cdef.get("methods", {}).items():
            mparams = _parse_tmd_params(mdef.get("params", {}))
            mret    = TessType.from_str(mdef.get("return_type", "dynamic"))
            cls.methods[mname] = TessModuleFunction(
                name=mname, params=mparams, return_type=mret,
                is_native=mdef.get("native", False)
            )
        mod.classes[cname] = cls

    if debug:
        print(f"[tessruntime] Módulo '{module_name}' cargado desde '{tmd_path}'")
        print(f"  exports={list(mod.exports)}")
        print(f"  functions={list(mod.mod_functions)}")
        print(f"  classes={list(mod.classes)}")

    return mod


def _parse_tmd_params(params_node) -> Dict[str, TessType]:
    """Parsea el campo params de una función del .tmd → {nombre: TessType}."""
    result = {}
    if isinstance(params_node, dict) and "value" in params_node:
        raw = params_node["value"]
        if raw:
            for part in raw.split(','):
                part = part.strip()
                if ':' in part:
                    pname, ptype = part.split(':', 1)
                    result[pname.strip()] = TessType.from_str(ptype.strip())
                else:
                    result[part] = TessType.DYNAMIC
    elif isinstance(params_node, dict):
        # Formato alternativo: {nombre: tipo}
        for pname, ptype in params_node.items():
            result[pname] = TessType.from_str(str(ptype))
    return result
# =============================================================================
# TABLA DE SÍMBOLOS DE COMPILACIÓN
# Mismo stack de scopes que SymbolTable en interpre.py.
# =============================================================================

class CompileSymbolTable:

    def __init__(self):
        self._scopes:    List[Dict[str, TessSymbol]]  = [{}]
        self._functions: Dict[str, TessFunction]       = {}
        self._modules:   Dict[str, TessModule]         = {}
        self._classes:    Dict[str, "TessClass"]        = {}
        self._interfaces: Dict[str, "TessInterface"]    = {}

    # ── scopes ───────────────────────────────────────────────────────────────

    def push_scope(self, label: str = ""):
        self._scopes.append({})

    def pop_scope(self, label: str = ""):
        if len(self._scopes) > 1:
            self._scopes.pop()

    # ── variables ────────────────────────────────────────────────────────────

    def declare(self, sym: TessSymbol):
        self._scopes[-1][sym.name] = sym

    def lookup(self, name: str) -> Optional[TessSymbol]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def update_ir_ref(self, name: str, ir_ref: Any):
        sym = self.lookup(name)
        if sym:
            sym.ir_ref = ir_ref

    # ── funciones ────────────────────────────────────────────────────────────

    def declare_function(self, fn: TessFunction):
        self._functions[fn.name] = fn

    def lookup_function(self, name: str) -> Optional[TessFunction]:
        return self._functions.get(name)

    def has_function(self, name: str) -> bool:
        return name in self._functions

    # ── módulos ──────────────────────────────────────────────────────────────

    def register_module(self, mod: TessModule):
        self._modules[mod.name] = mod
        # Si tiene alias, registrar también bajo el alias
        if mod.alias and mod.alias != mod.name:
            self._modules[mod.alias] = mod

    def is_module_loaded(self, name: str) -> bool:
        return name in self._modules

    def get_module(self, name: str) -> Optional[TessModule]:
        return self._modules.get(name)
     
    # ── Clases ──────────────────────────────────────────────────────────────
    def declare_class(self, cls: 'TessClass'):
        if not hasattr(self, '_classes'):
            self._classes: Dict[str, 'TessClass'] = {}
        self._classes[cls.name] = cls

    def lookup_class(self, name: str) -> Optional['TessClass']:
        if not hasattr(self, '_classes'):
            return None
        return self._classes.get(name)

    def has_class(self, name: str) -> bool:
        return name in self._classes

    def all_classes(self) -> Dict[str, 'TessClass']:
        return dict(self._classes)

    def declare_interface(self, iface: 'TessInterface'):
        if not hasattr(self, '_interfaces'):
            self._interfaces: Dict[str, 'TessInterface'] = {}
        self._interfaces[iface.name] = iface

    def lookup_interface(self, name: str) -> Optional['TessInterface']:
        if not hasattr(self, '_interfaces'):
            return None
        return self._interfaces.get(name)

    def lookup_method_in_hierarchy(self, class_name: str, method_name: str) -> Optional[Tuple['TessClass', 'TessMethod']]:
        """Busca un método subiendo por la cadena de herencia."""
        visited = set()
        current = class_name
        while current and current not in visited:
            visited.add(current)
            cls = self.lookup_class(current)
            if cls:
                if method_name in cls.methods:
                    return cls, cls.methods[method_name]
                current = cls.parent
            else:
                break
        return None

    # ── acceso a todos los elementos ─────────────────────────────────────────

    def all_globals(self) -> Dict[str, TessSymbol]:
        return dict(self._scopes[0])

    def all_functions(self) -> Dict[str, TessFunction]:
        return dict(self._functions)

    def all_modules(self) -> Dict[str, TessModule]:
        return dict(self._modules)

    def known_function_names(self) -> set:
        return set(self._functions.keys())

    def known_module_names(self) -> set:
        return set(self._modules.keys())


# =============================================================================
# ANALIZADOR DE NODOS DE VALOR
# Convierte el nodo value del AST en un ValueInfo completo.
# Cubre TODOS los casos de handle_VariableDeclaration, handle_VariableAsignement,
# handle_CallExpression (paramType), etc. en interpre.py.
# =============================================================================

class ValueNodeAnalyzer:

    def __init__(self, parser: ExpressionParser, ctx: CompileContext = None):
        self.parser = parser
        self.ctx = ctx

    def analyze(self, value_node: dict, param_type: str = "") -> ValueInfo:
        """
        Analiza un nodo value y retorna ValueInfo con:
        - raw: valor crudo
        - ast_type: tipo declarado en el AST
        - ttype: tipo inferido
        - kind: clasificación ExprKind
        - expr: árbol ExprNode parseado
        - param_type: paramType del CallExpression si aplica
        """
        ast_type = value_node.get("type", "")
        raw = value_node.get("value")

        ttype = TypeInferrer.from_value_node(value_node)
        kind = ExprClassifier.classify_value_node(value_node)

        expr = self._build_expr(raw, ast_type, param_type, kind)

        if expr is not None:
            expr_ttype = TypeInferrer.from_expr_node(expr, ctx=self.ctx)
            if expr_ttype != TessType.DYNAMIC:
                ttype = expr_ttype

        return ValueInfo(
            raw=raw, ast_type=ast_type, ttype=ttype,
            kind=kind, expr=expr, param_type=param_type
        )


    def analyze_raw(self, raw: Any, ast_type: str = "", param_type: str = "") -> ValueInfo:
        """Analiza directamente raw + ast_type sin el dict value_node."""
        return self.analyze({"value": raw, "type": ast_type}, param_type=param_type)

    def _build_expr(self, raw: Any, ast_type: str, param_type: str, kind: ExprKind) -> Optional[ExprNode]:
        """
        Construye el ExprNode según la misma lógica de decisión que
        handle_VariableDeclaration usa para resolver el valor inicial.
        """
        # NULL
        if ast_type == "NULL" or raw == "null" or raw is None:
            return NullNode()

        # Literales Python directos
        if isinstance(raw, bool):   return LiteralNode(raw, TessType.BOOL)
        if isinstance(raw, int):    return LiteralNode(raw, TessType.INT)
        if isinstance(raw, float):  return LiteralNode(raw, TessType.FLOAT)

        # Arrays y dicts literales
        if isinstance(raw, list):
            elems = []
            for elem in raw:
                if isinstance(elem, dict):
                    elems.append(self._build_expr(elem.get("value"), elem.get("type",""), "", ExprKind.UNKNOWN) or NullNode())
                else:
                    elems.append(LiteralNode(elem, TypeInferrer.from_python(elem)))
            return ArrayLiteralNode(elems)

        if isinstance(raw, dict) and ast_type not in ("string", "ModuleVariable", "function"):
            pairs = []
            for k, v in raw.items():
                key_node = LiteralNode(str(k), TessType.STRING)
                val_node = LiteralNode(v, TypeInferrer.from_python(v)) if not isinstance(v, dict) \
                           else (self._build_expr(v.get("value"), v.get("type",""), "", ExprKind.UNKNOWN) or NullNode())
                pairs.append((key_node, val_node))
            return DictLiteralNode(pairs)

        if not isinstance(raw, str):
            return NullNode()

        # A partir de aquí raw es str

        # ── ModuleVariable: math.PI ───────────────────────────────────────────
        if ast_type == "ModuleVariable":
            return self.parser.parse(raw)

        # ── function con punto: math.sqrt(9) ─────────────────────────────────
        if ast_type == "function" and '.' in raw:
            return self.parser.parse(raw)

        # ── ArrayAccess ───────────────────────────────────────────────────────
        if ast_type == "ArrayAccess" or param_type == "ArrayAccess":
            return self.parser.parse(raw)

        # ── expression explícita ──────────────────────────────────────────────
        if ast_type == "expression" or param_type == "expression":
            return self.parser.parse(raw)

        # ── String literal con comillas ────────────────────────────────────────
        if raw.startswith('"') and raw.endswith('"'):
            inner = raw[1:-1]
            return LiteralNode(inner, TessType.STRING)
        if raw.startswith("'") and raw.endswith("'"):
            inner = raw[1:-1]
            return LiteralNode(inner, TessType.STRING)

        # ── ast_type == "string" → puede ser concatenación o variable ─────────
        if ast_type == "string":
            # Si contiene operadores aritméticos → expresión
            if any(op in raw for op in ['+', '-', '*', '/', '%', '(', ')']):
                return self.parser.parse(raw)
            # Si contiene punto de concatenación → concat
            if re.search(r'(?<!\d)\.(?!\d)', raw) and not raw.replace('.', '', 1).isdigit():
                return self.parser.parse(raw)
            # Si es identificador → variable
            if re.match(r'^[A-Za-z_]\w*$', raw):
                return VarNode(raw)
            # Si es booleano
            if raw.lower() == 'true':  return LiteralNode(True,  TessType.BOOL)
            if raw.lower() == 'false': return LiteralNode(False, TessType.BOOL)
            # Número
            try: return LiteralNode(int(raw),   TessType.INT)
            except ValueError: pass
            try: return LiteralNode(float(raw), TessType.FLOAT)
            except ValueError: pass
            # Cadena de texto pura
            return LiteralNode(raw, TessType.STRING)

        # ── Llamada a función embebida: func(args) ────────────────────────────
        if re.match(r'^[A-Za-z_]\w*\s*\(.*\)$', raw, re.DOTALL):
            return self.parser.parse(raw)

        # ── Sin tipo explícito del AST — aplicar la misma lógica de
        #    _is_identifier + resolve_expression en interpre.py ─────────────────
        # Si parece un identificador simple → variable
        if re.match(r'^[A-Za-z_]\w*$', raw):
            return VarNode(raw)

        # Cualquier expresión restante → parsear
        return self.parser.parse(raw)


# =============================================================================
# CONTEXTO DE COMPILACIÓN
# Recorre el JSON AST igual que interpre.py pero poblando tablas en vez de ejecutar.
# Cubre TODOS los nodos que interpre.py maneja.
# =============================================================================

class CompileContext:

    def __init__(self, debug: bool = False):
        self.symbol_table     = CompileSymbolTable()
        self.expr_parser      = ExpressionParser()
        self.type_inferrer    = TypeInferrer()
        self.classifier       = ExprClassifier()
        self.value_analyzer   = ValueNodeAnalyzer(self.expr_parser,ctx=self)
        self.debug            = debug
        self._current_func:   Optional[str] = None

    def _log(self, msg: str):
        if self.debug:
            print(f"[CompileCtx] {msg}")

    def _refresh_parser(self):
     """Actualiza el parser con funciones, módulos y tipos de variables conocidos."""
     var_types = {}
     for name, sym in self.symbol_table.all_globals().items():
        tname = sym.ttype.value  # 'string', 'int', 'float', 'bool', 'array', 'null'
        if tname in _CORE_METHODS:
            var_types[name] = tname
     # También recorrer el scope actual (variables locales)
     for scope in self.symbol_table._scopes:
        for name, sym in scope.items():
            tname = sym.ttype.value
            if tname in _CORE_METHODS:
                var_types[name] = tname

     self.expr_parser.update(
        self.symbol_table.known_function_names(),
        self.symbol_table.known_module_names(),
        var_types,
     )

    # ── Punto de entrada ─────────────────────────────────────────────────────

    def analyze(self, ast: dict):
        if "Program" not in ast:
            raise ValueError("El AST debe tener un nodo raíz 'Program'.")

        program_nodes = ast["Program"]
        i = 0
        while i < len(program_nodes):
            node      = program_nodes[i]
            node_type = list(node.keys())[0]

            # WhileLoop: puede tener el bloque como nodo hermano
            if node_type == "WhileLoop":
                if i + 1 < len(program_nodes) and "Block" in program_nodes[i + 1]:
                    node["WhileLoop"]["block"] = program_nodes[i + 1]["Block"]
                    self.analyze_node(node)
                    i += 2
                    continue

            # SwitchStatement: puede tener su bloque como nodo hermano
            if node_type == "SwitchStatement":
                if i + 1 < len(program_nodes) and "block" in program_nodes[i + 1]:
                    sw = node["SwitchStatement"]
                    blk = program_nodes[i + 1]["block"]
                    sw["cases"]       = blk.get("cases", [])
                    sw["defaultCase"] = blk.get("defaultCase")
                    self.analyze_node(node)
                    i += 2
                    continue

            self.analyze_node(node)
            i += 1

    def analyze_node(self, node: dict):
        if not node:
            return
        node_type = list(node.keys())[0]
        self._log(f"analyze_node: {node_type}")
        handler = getattr(self, f"_analyze_{node_type}", self._analyze_unknown)
        handler(node[node_type])

    def analyze_block(self, block):
     """Analiza una lista de nodos o un dict de bloque."""
     if isinstance(block, list):
        for stmt in block:
            self.analyze_node(stmt)
     elif isinstance(block, dict):
        # Los bloques tipo dict pueden tener claves en camelCase minúscula
        # (ej: "variableDeclaration", "callExpression").
        # Igual que execute_block en interpre.py, se normaliza a PascalCase
        # para que el dispatcher _analyze_X los encuentre correctamente.
        EXECUTABLE_KEYS = {
            "variableDeclaration", "variableAsignement", "callExpression",
            "switchStatement", "function", "functionCall", "parameterAsignement",
            "postIncrementStatement", "postDecrementStatement",
            "preIncrementStatement", "preDecrementStatement", "tryCatch", "throw",
            "newObject", "classDeclaration", "interfaceDeclaration",
            "thisAccess", "thisCall", "thisAssignment",
            "superAccess", "superCall", "superAssignment", "superConstructorCall",
            "methodDeclaration", "attributeDeclaration",
            "attributeConstantDeclaration", "constantAttributeDeclaration",
            "if_Condition", "forLoop", "whileLoop", "performWhileLoop",
        }
        items = list(block.items())
        i = 0
        while i < len(items):
            key, content = items[i]
            # Normalizar a PascalCase para el dispatcher _analyze_X
            node_type = key[0].upper() + key[1:]

            # Nodos que en interpre.py tienen su bloque como hermano
            NODES_TO_REPAIR = {"if_Condition", "forLoop", "whileLoop", "performWhileLoop"}
            if key in NODES_TO_REPAIR:
                if i + 1 < len(items) and items[i + 1][0] == "block":
                    content["block"] = items[i + 1][1]
                    i += 1  # saltar el nodo block hermano
                self.analyze_node({node_type: content})
            elif key in EXECUTABLE_KEYS or key[0].isupper():
                if isinstance(content, list):
                    for item in content:
                        self.analyze_node({node_type: item})
                else:
                    self.analyze_node({node_type: content})
            i += 1
    # ── Analizadores por nodo — cubre todo interpre.py ───────────────────────

    # REEMPLAZAR _analyze_VariableDeclaration completo con:
    # REEMPLAZAR _analyze_VariableDeclaration con:
    def _analyze_VariableDeclaration(self, node: dict):
     name       = node["name"]
     value_node = node.get("value", {})
     vinfo      = self.value_analyzer.analyze(value_node)
     ttype      = vinfo.ttype

     is_const  = False
     const_val = None
     raw       = value_node.get("value")
     if vinfo.kind == ExprKind.LITERAL and isinstance(raw, (int, float, bool, str)):
        const_val = raw

     is_explicit = "explicitType" in value_node
     is_tuple    = value_node.get("collectionType", "") == "tuple"

     # Construir TessTypeInfo desde explicitType + limit
     type_info = None
     explicit_raw = value_node.get("explicitType", "")
     raw_limit    = value_node.get("limit")
     limit        = -1
     if raw_limit is not None:
        try:    limit = int(raw_limit)
        except: limit = -1

     if explicit_raw:
        type_info = parse_type_info(str(explicit_raw), limit=limit)
     elif limit >= 0:
        # Tiene límite pero sin tipo → dinámico con límite
        type_info = TessTypeInfo(ttype, limit=limit)

     sym = TessSymbol(
        name=name, ttype=ttype, is_const=is_const, const_value=const_val,
        is_explicit_type=is_explicit, type_info=type_info, is_tuple=is_tuple
     )
     self.symbol_table.declare(sym)
     self._refresh_parser()
     self._log(f"VarDecl '{name}' tipo={ttype.value} type_info={type_info}")

    def _analyze_VariableAsignement(self, node: dict):
        """
        Mismo recorrido que handle_VariableAsignement.
        Detecta reasignación, declaración implícita, ModuleVariable,
        función de módulo, llamada a función, operación, string.
        """
        name       = node["name"]
        value_node = node.get("value", {})
        sym        = self.symbol_table.lookup(name)
        vinfo = self.value_analyzer.analyze(value_node)

        if sym is None:
            # Declaración implícita
            ttype = vinfo.ttype
            sym   = TessSymbol(name=name, ttype=ttype)
            self.symbol_table.declare(sym)
            self._refresh_parser()

        
        self._log(f"VarAssign '{name}' kind={vinfo.kind.name}")

    def _analyze_ConstantDeclaration(self, node: dict):
     """Mismo recorrido que handle_ConstantDeclaration."""
     name       = node["name"]
     value_node = node.get("value", {})
     vinfo      = self.value_analyzer.analyze(value_node)  # ← DESPUÉS de value_node
     ttype      = vinfo.ttype
     raw        = value_node.get("value")
     const_val  = raw if isinstance(raw, (int, float, bool, str)) else None
     is_explicit = "explicitType" in value_node

     sym = TessSymbol(
        name=name, ttype=ttype, is_const=True,
        const_value=const_val, is_explicit_type=is_explicit
     )
     self.symbol_table.declare(sym)
     self._refresh_parser()
     self._log(f"ConstDecl '{name}' tipo={ttype.value}")
    def _analyze_Function(self, node: dict):
        """
        Mismo recorrido que handle_Function + _parse_function_parameters.
        Registra la función, analiza su cuerpo, declara parámetros como símbolos.
        """
        name   = node["name"]
        params = self._parse_function_params(node.get("parameters", {}))
        ret    = TessType.from_str(node.get("explicitType", "dynamic"))
        body   = node.get("block", [])
        is_explicit_return = "explicitType" in node
        
        target     = node.get("target", "")
        is_entry   = str(target).strip().lower() == "main"
        fn = TessFunction(name=name, params=params, return_type=ret, body=body,
                  is_explicit_return=is_explicit_return, is_entry_point=is_entry)
        
        self.symbol_table.declare_function(fn)
        self._refresh_parser()
        self._log(f"Function '{name}' params={list(params.keys())} ret={ret.value}")

        # Analizar cuerpo con scope propio
        old_func = self._current_func
        self._current_func = name
        self.symbol_table.push_scope(label=f"Función '{name}'")
        # Declarar parámetros como símbolos en el scope de la función
        for pname, ptype in params.items():
            psym = TessSymbol(name=pname, ttype=ptype)
            self.symbol_table.declare(psym)
        self.analyze_block(body)
        self.symbol_table.pop_scope(label=f"Función '{name}'")
        self._current_func = old_func

    def _analyze_FunctionCall(self, node: dict):
        """
        Mismo recorrido que handle_FunctionCall.
        Valida la llamada, analiza los parámetros.
        """
        fname  = node["function"]
        params = node.get("paramenters", {})
        self._analyze_call_params(params)
        self._log(f"FunctionCall '{fname}'")

    def _analyze_CallExpression(self, node: dict):
        """
        Mismo recorrido completo que handle_CallExpression.
        Cubre: mod.func(), Break, Return, print, read, ArrayAccess,
        expression, string con concat, ModuleVariable, function con punto.
        """
        fname      = node.get("function", "")
        args_node  = node.get("arguments", {})
        param_type = node.get("paramType", "")
        raw_arg    = args_node.get("value") if isinstance(args_node, dict) else args_node
        actual_pt  = param_type.get("value") if isinstance(param_type, dict) else param_type

        self._log(f"CallExpression '{fname}' paramType={actual_pt}")

        # mod.func()
        if isinstance(fname, str) and '.' in fname:
            self._log(f"  → llamada de módulo")
            return

        # Break / Return
        if fname in ("Break", "Return"):
            if fname == "Return":
                ret_node = node.get("value") or node.get("arguments") or {}
                if "value" in ret_node:
                    self._analyze_return_value(ret_node["value"])
            return

        # Analizar el argumento según paramType
        if raw_arg is not None:
            vinfo = self.value_analyzer.analyze_raw(raw_arg, ast_type="", param_type=actual_pt or "")
            self._log(f"  argumento kind={vinfo.kind.name} ttype={vinfo.ttype.value}")

    def _analyze_return_value(self, raw_value: Any):
        """
        Analiza el valor de un Return, igual que handle_CallExpression para Return.
        """
        if isinstance(raw_value, str):
            if re.match(r'^[A-Za-z_]\w*\s*\(.*\)$', raw_value, re.DOTALL):
                self._log(f"  Return: llamada a función '{raw_value}'")
            elif any(op in raw_value for op in ['+', '-', '*', '/', '%', '.']):
                expr = self.expr_parser.parse(raw_value)
                self._log(f"  Return: expresión '{raw_value}' → {type(expr).__name__}")
            else:
                self._log(f"  Return: variable/literal '{raw_value}'")

    # REEMPLAZAR _analyze_LibraryCall con:
    def _analyze_LibraryCall(self, node: dict):
     module_raw     = node["module"]
     alias          = node.get("alias")
     functions      = node.get("functions")
     func_aliases   = node.get("functionAliases", [])
     inline_aliases = node.get("inlineAliases", {})
     on_names       = node.get("on", [])
     on_aliases     = node.get("onAliases", [])

     is_source = module_raw.strip('"\'').lower().endswith('.tss')
     if is_source:
        base_name = os.path.splitext(os.path.basename(module_raw.strip('"\'')))[0]
        mod_name  = alias if alias else base_name
     else:
        mod_name  = alias if alias else module_raw

     fa_map: Dict[str, str] = dict(inline_aliases)
     if functions and func_aliases:
        for orig, falias in zip(functions, func_aliases):
            fa_map[orig] = falias
     if on_names and on_aliases:
        for orig, falias in zip(on_names, on_aliases):
            fa_map[orig] = falias

     if is_source:
        # Módulo fuente .tss — metadata mínima
        mod = TessModule(
            name=mod_name, is_source=True, path=module_raw,
            alias=alias or "",
            functions=list(functions) if functions else [],
            func_aliases=fa_map,
        )
     else:
        # Módulo nativo — cargar metadata del .tmd
        mod = load_tmd_metadata(module_raw, debug=self.debug)
        if mod is None:
            # .tmd no encontrado — crear entrada mínima para no bloquear
            mod = TessModule(
                name=mod_name, is_source=False, path=module_raw,
                alias=alias or "",
                functions=list(functions) if functions else [],
                func_aliases=fa_map,
            )
        else:
            mod.name         = mod_name
            mod.alias        = alias or ""
            mod.functions    = list(functions) if functions else []
            mod.func_aliases = fa_map

     self.symbol_table.register_module(mod)
     self._refresh_parser()
     self._log(
        f"LibraryCall '{mod_name}' source={is_source} "
        f"exports={list(mod.exports)} "
        f"functions={list(mod.mod_functions)} "
        f"classes={list(mod.classes)}"
     )
    def _analyze_if_Condition(self, node: dict):
        """
        Mismo recorrido que handle_if_Condition.
        Analiza condición, bloque then, cadena elseIf, bloque else.
        """
        condition = node.get("condition", "")
        self._log(f"if_Condition cond='{condition}'")

        self.symbol_table.push_scope(label="if")
        self.analyze_block(node.get("block", []))
        self.symbol_table.pop_scope(label="if")

        # Cadena elseIf (puede estar anidada)
        if "elseIf" in node:
            self._analyze_elseif_chain(node["elseIf"])

        if "else" in node:
            self.symbol_table.push_scope(label="else")
            self.analyze_block(node["else"].get("block", []))
            self.symbol_table.pop_scope(label="else")

    def _analyze_elseif_chain(self, node: dict):
        cond = node.get("condition") or node.get("value", "")
        self._log(f"elseIf cond='{cond}'")
        self.symbol_table.push_scope(label="elseIf")
        self.analyze_block(node.get("block", []))
        self.symbol_table.pop_scope(label="elseIf")
        if "elseIf" in node:
            self._analyze_elseif_chain(node["elseIf"])
        if "else" in node:
            self.symbol_table.push_scope(label="else")
            self.analyze_block(node["else"].get("block", []))
            self.symbol_table.pop_scope(label="else")

    def _analyze_ForLoop(self, node: dict):
        """
        Mismo recorrido que handle_ForLoop.
        Registra la variable iteradora, parsea el rango, analiza el bloque.
        """
        var_name   = node["variable"]
        iterator   = node.get("iterator", {})
        range_str  = iterator.get("value", "")
        is_local   = iterator.get("declared") is not None

        self._log(f"ForLoop var='{var_name}' rango='{range_str}'")

        if is_local:
            self.symbol_table.push_scope(label="for-iterador")

        # Registrar la variable iteradora
        sym = self.symbol_table.lookup(var_name)
        if sym is None:
            sym = TessSymbol(name=var_name, ttype=TessType.INT)
            self.symbol_table.declare(sym)

        # Parsear los límites del rango
        if ".." in range_str:
            parts = range_str.split("..")
            start_expr = self.expr_parser.parse(parts[0].strip())
            end_expr   = self.expr_parser.parse(parts[1].strip())
            self._log(f"  rango: {type(start_expr).__name__} .. {type(end_expr).__name__}")

        self.symbol_table.push_scope(label="for")
        self.analyze_block(node.get("block", []))
        self.symbol_table.pop_scope(label="for")

        if is_local:
            self.symbol_table.pop_scope(label="for-iterador")

    def _analyze_WhileLoop(self, node: dict):
        """Mismo recorrido que handle_WhileLoop."""
        condition = node.get("condition", "")
        self._log(f"WhileLoop cond='{condition}'")
        self.symbol_table.push_scope(label="while")
        self.analyze_block(node.get("block", []))
        self.symbol_table.pop_scope(label="while")

    def _analyze_PerformWhileLoop(self, node: dict):
        """Mismo recorrido que handle_PerformWhileLoop (do-while)."""
        condition = node.get("value", "")
        self._log(f"PerformWhileLoop cond='{condition}'")
        self.symbol_table.push_scope(label="perform-while")
        self.analyze_block(node.get("block", []))
        self.symbol_table.pop_scope(label="perform-while")

    def _analyze_SwitchStatement(self, node: dict):
        """
        Mismo recorrido que handle_SwitchStatement.
        Analiza cada case y el defaultCase.
        """
        var_name = node.get("value", "")
        self._log(f"SwitchStatement var='{var_name}'")

        for case in node.get("cases", []):
            case_val = case.get("case")
            self._log(f"  case {case_val}")
            self.symbol_table.push_scope(label=f"switch case {case_val}")
            self.analyze_block(case.get("block", []))
            self.symbol_table.pop_scope(label=f"switch case {case_val}")

        default = node.get("defaultCase")
        if default:
            self._log("  default")
            self.symbol_table.push_scope(label="switch default")
            self.analyze_block(default.get("block", []))
            self.symbol_table.pop_scope(label="switch default")

    def _analyze_PostIncrementStatement(self, node: dict):
        var = node.get("value", "")
        self._log(f"PostIncrement '{var}'")

    def _analyze_PostDecrementStatement(self, node: dict):
        var = node.get("value", "")
        self._log(f"PostDecrement '{var}'")

    def _analyze_PreIncrementStatement(self, node: dict):
        var = node.get("value", "")
        self._log(f"PreIncrement '{var}'")

    def _analyze_PreDecrementStatement(self, node: dict):
        var = node.get("value", "")
        self._log(f"PreDecrement '{var}'")

    def _analyze_ParameterAsignement(self, node: dict):
        """
        Mismo recorrido que handle_ParameterAsignement.
        Reasignación de un parámetro dentro de una función.
        """
        pname      = node["name"]
        value_node = node.get("value", {})
        vinfo      = self.value_analyzer.analyze(value_node)
        self._log(f"ParameterAsignement '{pname}' kind={vinfo.kind.name}")

    # AGREGAR en CompileContext después de _analyze_ParameterAsignement:

    def _analyze_ClassDeclaration(self, node: dict):
        """Mismo recorrido que handle_ClassDeclaration."""
        name       = node.get('name', '')
        parent     = node.get('extends')
        impl_raw   = node.get('implements', '')
        modifier   = node.get('modifier')
        interfaces = [i.strip() for i in impl_raw.split(',')] if isinstance(impl_raw, str) and impl_raw else []

        cls = TessClass(name=name, parent=parent, interfaces=interfaces, modifier=modifier)

        for member in node.get('members', []):
            self._process_class_member_compile(member, cls)

        self.symbol_table.declare_class(cls)
        # Registrar el nombre de la clase como tipo conocido
        self._refresh_parser()
        self._log(f"ClassDecl '{name}' parent={parent} methods={list(cls.methods.keys())}")

    def _process_class_member_compile(self, member: dict, cls: 'TessClass'):
        """Procesa un miembro de clase para compilación."""
        if 'ClassMember' in member:
            inner = member['ClassMember']
            for key, content in inner.items():
                self._process_class_member_compile({key: content}, cls)
            return

        # Atributo
        attr_kinds = {'AttributeDeclaration', 'AttributeConstantDeclaration',
                      'ConstantAttributeDeclaration'}
        matched = attr_kinds & set(member.keys())
        if matched:
            kind     = matched.pop()
            anode    = member[kind]
            aname    = anode.get('name', '')
            val_node = anode.get('value', {})
            ttype    = TypeInferrer.from_value_node(val_node)
            mod      = anode.get('modifier', 'public')
            is_const = 'Constant' in kind or 'constant' in kind.lower()
            cls.attributes[aname] = TessAttribute(
                name=aname, ttype=ttype, modifier=mod, is_const=is_const)
            return

        # Método
        if 'MethodDeclaration' in member:
            mnode    = member['MethodDeclaration']
            mname    = mnode.get('name', '')
            params   = self._parse_function_params(mnode.get('parameters', {}))
            ret      = TessType.from_str(mnode.get('explicitType', 'dynamic'))
            mod      = mnode.get('modifier', 'public')
            is_async = bool(mnode.get('async') or mnode.get('isAsync'))
            body     = mnode.get('block', [])
            cls.methods[mname] = TessMethod(
                name=mname, params=params, return_type=ret,
                body=body, modifier=mod, is_async=is_async)
            return

        # Constructor
        if 'ConstructorDeclaration' in member:
            cnode  = member['ConstructorDeclaration']
            params = self._parse_function_params(cnode.get('parameters', {}))
            mod    = cnode.get('modifier', 'public')
            body   = cnode.get('block', [])
            cls.constructor = TessMethod(
                name='__init__', params=params, return_type=TessType.VOID,
                body=body, modifier=mod)

    def _analyze_InterfaceDeclaration(self, node: dict):
        name  = node.get('name', '')
        iface = TessInterface(name=name)
        for m in node.get('methods', []):
            if 'MethodDeclaration' in m:
                mn    = m['MethodDeclaration']
                mname = mn.get('name', '')
                params = self._parse_function_params(mn.get('parameters', {}))
                ret    = TessType.from_str(mn.get('explicitType', 'dynamic'))
                iface.methods[mname] = TessMethod(
                    name=mname, params=params, return_type=ret, body=[])
        self.symbol_table.declare_interface(iface)
        self._log(f"InterfaceDecl '{name}'")

    def _analyze_NewObject(self, node: dict):
        class_name = node.get('class', '')
        self._log(f"NewObject '{class_name}'")

    def _analyze_TryCatch(self, node: dict):
        """Analiza los bloques try/catch/finally."""
        self.symbol_table.push_scope(label="try")
        self.analyze_block(node.get('tryBlock') or node.get('block', []))
        self.symbol_table.pop_scope(label="try")

        catch = node.get('catchClause', {})
        if catch:
            exc_var = catch.get('exception') or catch.get('name')
            self.symbol_table.push_scope(label="catch")
            if exc_var:
                sym = TessSymbol(name=exc_var, ttype=TessType.STRING)
                self.symbol_table.declare(sym)
            self.analyze_block(catch.get('block', []))
            self.symbol_table.pop_scope(label="catch")

        finally_node = node.get('finallyBlock') or (
            catch.get('finallyBlock') if isinstance(catch, dict) else None)
        if finally_node:
            self.symbol_table.push_scope(label="finally")
            self.analyze_block(finally_node.get('block', []))
            self.symbol_table.pop_scope(label="finally")

    def _analyze_Throw(self, node: dict):
        exc = node.get('exception', 'Error')
        self._log(f"Throw '{exc}'")

    def _analyze_ThisAccess(self, node: dict): pass
    def _analyze_ThisCall(self, node: dict): pass
    def _analyze_ThisAssignment(self, node: dict): pass
    def _analyze_SuperAccess(self, node: dict): pass
    def _analyze_SuperCall(self, node: dict): pass
    def _analyze_SuperAssignment(self, node: dict): pass
    def _analyze_SuperConstructorCall(self, node: dict): pass
    def _analyze_ArrayAccess(self, node: dict):
        """
        Mismo recorrido que handle_ArrayAccess.
        Acceso simple a array: array_name[index].
        """
        array_name = node.get("array", "")
        index      = node.get("index", "")
        self._log(f"ArrayAccess '{array_name}[{index}]'")

    def _analyze_unknown(self, node_content):
        self._log(f"ADVERTENCIA: nodo desconocido: {type(node_content)}")

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _parse_function_params(self, params_node: dict) -> Dict[str, TessType]:
        """
        Misma lógica que _parse_function_parameters en interpre.py.
        Parsea "a:any, b:float, c:float" → {a: DYNAMIC, b: FLOAT, c: FLOAT}
        """
        result = {}
        if "value" in params_node:
            raw = params_node["value"]
            if raw:
                for part in raw.split(','):
                    part = part.strip()
                    if not part:
                        continue
                    if ':' in part:
                        pname, ptype = part.split(':', 1)
                        result[pname.strip()] = TessType.from_str(ptype.strip())
                    else:
                        result[part] = TessType.DYNAMIC
        return result

    def _analyze_call_params(self, params_node: dict):
        """
        Misma lógica que _parse_call_parameters en interpre.py.
        Analiza los argumentos de una llamada.
        """
        if not params_node:
            return
        raw = params_node.get("value", "") if isinstance(params_node, dict) else str(params_node)
        if not raw:
            return
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            is_literal_str = (part.startswith('"') and part.endswith('"')) or \
                             (part.startswith("'") and part.endswith("'"))
            if ':' in part and not is_literal_str:
                _, val = part.split(':', 1)
                part = val.strip()
            expr = self.expr_parser.parse(part)
            self._log(f"  call_param: {part!r} → {type(expr).__name__}")

    # ── API pública para tesscodegen.py ──────────────────────────────────────
    # AGREGAR en la sección "API pública para tesscodegen.py":

    def get_all_classes(self) -> Dict[str, 'TessClass']:
        return self.symbol_table.all_classes()

    def get_class(self, name: str) -> Optional['TessClass']:
        return self.symbol_table.lookup_class(name)
    def parse_expression(self, expr_str: str) -> ExprNode:
        """Parsea una expresión string → ExprNode listo para emitir IR."""
        return self.expr_parser.parse(expr_str)

    def analyze_value_node(self, value_node: dict, param_type: str = "") -> ValueInfo:
        """Analiza un nodo value completo → ValueInfo listo para tesscodegen."""
        return self.value_analyzer.analyze(value_node, param_type=param_type)

    def resolve_var_type(self, name: str) -> TessType:
        sym = self.symbol_table.lookup(name)
        return sym.ttype if sym else TessType.DYNAMIC

    def get_function(self, name: str) -> Optional[TessFunction]:
        return self.symbol_table.lookup_function(name)

    def get_all_functions(self) -> Dict[str, TessFunction]:
        return self.symbol_table.all_functions()

    def get_all_globals(self) -> Dict[str, TessSymbol]:
        return self.symbol_table.all_globals()

    def is_module_loaded(self, name: str) -> bool:
        return self.symbol_table.is_module_loaded(name)

    def classify_kind(self, node: ExprNode) -> ExprKind:
        return ExprClassifier.classify_expr_node(node)


# =============================================================================
# Funciones de entrada
# =============================================================================

def analyze_ast(ast_json: dict, debug: bool = False) -> CompileContext:
    ctx = CompileContext(debug=debug)
    ctx.analyze(ast_json)
    return ctx


def analyze_ast_file(path: str, debug: bool = False) -> CompileContext:
    with open(path, 'r', encoding='utf-8') as f:
        ast_data = json.load(f)
    return analyze_ast(ast_data, debug=debug)

def dump_symbol_tables(ctx: CompileContext, output_file: str) -> None:
    """
    Genera un archivo de texto con todas las tablas de símbolos del contexto:
    - Variables globales (nombre, tipo, const, valor constante)
    - Funciones (nombre, parámetros, retorno)
    - Módulos (nombre, tipo, funciones importadas, alias)
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("TESSERACT SYMBOL TABLES DUMP\n")
        f.write("=" * 80 + "\n\n")

        # Variables globales
        f.write("=== GLOBAL VARIABLES ===\n")
        globals_dict = ctx.get_all_globals()
        if globals_dict:
            # Ordenar por nombre
            for name in sorted(globals_dict.keys()):
                sym = globals_dict[name]
                const_str = " [const]" if sym.is_const else ""
                val_str = f" = {sym.const_value}" if sym.const_value is not None else ""
                explicit_str = " [explicit]" if sym.is_explicit_type else ""
                f.write(f"  {name}: {sym.ttype.value}{const_str}{val_str}\n")
        else:
            f.write("  (none)\n")
        f.write("\n")

        # Funciones
        f.write("=== FUNCTIONS ===\n")
        funcs_dict = ctx.get_all_functions()
        if funcs_dict:
            for name in sorted(funcs_dict.keys()):
                fn = funcs_dict[name]
                params_str = ", ".join(f"{p}:{t.value}" for p, t in fn.params.items())
                explicit_ret = " [explicit return]" if fn.is_explicit_return else ""
                f.write(f"  {name}({params_str}) -> {fn.return_type.value}\n")
        else:
            f.write("  (none)\n")
        f.write("\n")

        # Módulos
        f.write("=== MODULES ===\n")
        mods_dict = ctx.symbol_table.all_modules()
        if mods_dict:
            for name in sorted(mods_dict.keys()):
                mod = mods_dict[name]
                kind = "source (.tss)" if mod.is_source else "native"
                f.write(f"  {name} [{kind}]\n")
                if mod.functions:
                    f.write(f"    imported functions: {', '.join(mod.functions)}\n")
                if mod.func_aliases:
                    alias_str = ", ".join(f"{orig}→{alias}" for orig, alias in mod.func_aliases.items())
                    f.write(f"    aliases: {alias_str}\n")
                if mod.alias and mod.alias != mod.name:
                    f.write(f"    alias: {mod.alias}\n")
        else:
            f.write("  (none)\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("END OF DUMP\n")
        f.write("=" * 80 + "\n")

    print(f"[tessruntime] Symbol tables written to {output_file}")
# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    import argparse

    # Opciones simples: argumento posicional (AST) y flags
    parser = argparse.ArgumentParser(description="Tesseract AST Analyzer")
    parser.add_argument("ast", help="Path to the JSON AST file")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-out", "--output", help="Write symbol tables to this file")
    args = parser.parse_args()

    # Analizar el AST
    ctx = analyze_ast_file(args.ast, debug=args.debug)

    # Si se pidió volcar las tablas, hacerlo y terminar
    if args.output:
        dump_symbol_tables(ctx, args.output)
        sys.exit(0)

    # Si no, imprimir en consola como antes
    print("\n=== TABLA DE SÍMBOLOS GLOBALES ===")
    for name, sym in ctx.get_all_globals().items():
        cv = f" = {sym.const_value}" if sym.const_value is not None else ""
        c  = " [const]" if sym.is_const else ""
        e  = " [explicit]" if sym.is_explicit_type else ""
        print(f"  {name}: {sym.ttype.value}{e}{c}{cv}")


    print("\n=== FUNCIONES ===")
    for name, fn in ctx.get_all_functions().items():
        params_str = ", ".join(f"{p}:{t.value}" for p, t in fn.params.items())
        er = " [explicit return]" if fn.is_explicit_return else ""
        print(f"  {name}({params_str}) -> {fn.return_type.value}{er}")

    print("\n=== MÓDULOS ===")
    for name, mod in ctx.symbol_table.all_modules().items():
        kind = "fuente (.tss)" if mod.is_source else "nativo"
        fns  = f" funciones={mod.functions}" if mod.functions else ""
        als  = f" aliases={mod.func_aliases}" if mod.func_aliases else ""
        print(f"  {name} [{kind}]{fns}{als}")

    # Opcionalmente, probar el parser de expresiones
    print("\n=== PRUEBA DEL PARSER DE EXPRESIONES ===")
    test_exprs = [
        'b*b-4*a*c',
        '(-b+math.sqrt(discriminante))/(2*a)',
        '"Dos soluciones: " . x1 . " y " . x2',
        'discriminante > 0',
        'a == 0',
        'math.PI',
        'myfunc(a: 1, b: 2)',
        'arr[i:j]',
        'x && y || z',
        '"valor: " . x1',
    ]
    for e in test_exprs:
        node = ctx.parse_expression(e)
        kind = ctx.classify_kind(node)
        print(f"  {e!r:45s} → {type(node).__name__} [{kind.name}]")
        