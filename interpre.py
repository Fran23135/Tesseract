from platform import node

import ujson as json
import re
import sys
import os
import asyncio
import threading
from module_loader import ModuleLoader, ModuleError, ModuleInstance

# Aumentar límite de recursión para soportar programas Tesseract complejos
sys.setrecursionlimit(5000)

# Justo después de los imports, antes de las clases:
_UNRESOLVED = object()

# ==============================================================================
# Manejo de Errores (Sin cambios)
# ==============================================================================
class InterpreterError(Exception):
    pass
class UndeclaredVariableError(InterpreterError):
    def __init__(self, name):
        super().__init__(f"Error: La variable '{name}' no ha sido declarada.")
class InvalidOperationError(InterpreterError):
    def __init__(self, message):
        super().__init__(f"Error de operación inválida: {message}")
class Symbol:
    """Contenedor para la información completa de una variable."""
    def __init__(self, value, declared_type='dynamic', is_const=False):
        self.value = value
        self.declared_type = declared_type
        self.is_const = is_const

    def __repr__(self):
        val = (lambda s: s + '0' if s.endswith('.') else s)(f'{self.value:.15f}'.rstrip('0')) if isinstance(self.value, float) else self.value
        return f"Symbol(value={val}, type={self.declared_type})"

class ThrowSignal(Exception):
    def __init__(self, exception_class, message=None):
        self.exception_class = exception_class
        self.message = message
        super().__init__(f"[{exception_class}] {message}" if message else f"[{exception_class}]")

# ==============================================================================
# OOP — Definición de Clase
# ==============================================================================
class ClassDefinition:
    def __init__(self, name, parent=None, interfaces=None, modifier=None):
        self.name       = name
        self.parent     = parent           # str: nombre clase padre
        self.interfaces = interfaces or [] # list[str]
        self.modifier   = modifier         # 'abstract' | 'final' | None
        # name -> {value, type, modifier, is_const}
        self.attributes: dict = {}
        # name -> {node, params, modifier, explicit_type, is_async}
        self.methods: dict    = {}
        # {node, params, modifier} | None
        self.constructor       = None

    def __repr__(self):
        s = f"ClassDef({self.name}"
        if self.parent:     s += f" extends {self.parent}"
        if self.interfaces: s += f" implements {', '.join(self.interfaces)}"
        if self.modifier:   s += f" [{self.modifier}]"
        return s + ")"

# ==============================================================================
# OOP — Instancia de Clase
# ==============================================================================
class ClassInstance:
    _counter = 0
    def __init__(self, class_name: str, class_def: ClassDefinition):
        ClassInstance._counter += 1
        self._id        = ClassInstance._counter
        self.class_name = class_name
        self.class_def  = class_def
        self.attributes: dict = {}
        # Copiar valores por defecto de los atributos de clase
        self._init_attributes(class_def)

    def _init_attributes(self, class_def: ClassDefinition):
        for attr_name, attr_info in class_def.attributes.items():
            self.attributes[attr_name] = attr_info.get('value')

    def get_attribute(self, name: str):
        if name in self.attributes:
            return self.attributes[name]
        raise InterpreterError(
            f"Atributo '{name}' no existe en instancia de '{self.class_name}'."
        )

    def set_attribute(self, name: str, value):
        self.attributes[name] = value

    def __repr__(self):
        return f"<{self.class_name}#{self._id} attrs={list(self.attributes.keys())}>"

# ==============================================================================
# OOP — Tabla de Símbolos dedicada a objetos
# ==============================================================================
class ObjectSymbolTable:
    def __init__(self):
        self.class_definitions:     dict = {}   # str -> ClassDefinition
        self.interface_definitions: dict = {}   # str -> dict

    # ── Clases ─────────────────────────────────────────────────────────────
    def declare_class(self, name: str, class_def: ClassDefinition):
        self.class_definitions[name] = class_def

    def has_class(self, name: str) -> bool:
        return name in self.class_definitions

    def get_class(self, name: str) -> ClassDefinition:
        if name not in self.class_definitions:
            raise InterpreterError(f"Clase '{name}' no está declarada.")
        return self.class_definitions[name]

    # ── Interfaces ──────────────────────────────────────────────────────────
    def declare_interface(self, name: str, iface_def: dict):
        self.interface_definitions[name] = iface_def

    # ── Instanciación ───────────────────────────────────────────────────────
    def instantiate(self, class_name: str) -> ClassInstance:
        return ClassInstance(class_name, self.get_class(class_name))

    # ── Polimorfismo: búsqueda de método en jerarquía ───────────────────────
    def lookup_method(self, class_name: str, method_name: str):
        """Busca un método subiendo por la cadena de herencia."""
        visited = set()
        current = class_name
        while current and current not in visited:
            visited.add(current)
            if current in self.class_definitions:
                cls = self.class_definitions[current]
                if method_name in cls.methods:
                    return cls.methods[method_name], current
                current = cls.parent
            else:
                break
        raise InterpreterError(
            f"Método '{method_name}' no encontrado en '{class_name}' ni en su jerarquía."
        )

    # ── Búsqueda de atributo en jerarquía ───────────────────────────────────
    def lookup_attribute_def(self, class_name: str, attr_name: str):
        visited = set()
        current = class_name
        while current and current not in visited:
            visited.add(current)
            if current in self.class_definitions:
                cls = self.class_definitions[current]
                if attr_name in cls.attributes:
                    return cls.attributes[attr_name]
                current = cls.parent
            else:
                break
        return None

    # ── isinstance lógico ───────────────────────────────────────────────────
    def is_instance_of(self, class_name: str, target: str) -> bool:
        visited = set()
        current = class_name
        while current and current not in visited:
            visited.add(current)
            if current == target:
                return True
            if current in self.class_definitions:
                current = self.class_definitions[current].parent
            else:
                break
        return False

    # ── Debug ────────────────────────────────────────────────────────────────
    def __str__(self):
        if not self.class_definitions and not self.interface_definitions:
            return "  [Sin clases ni interfaces declaradas]"
        lines = []
        for name, cls in self.class_definitions.items():
            lines.append(f"  Clase '{name}':")
            if cls.parent:      lines.append(f"    ↳ Extiende   : {cls.parent}")
            if cls.interfaces:  lines.append(f"    ↳ Implementa : {', '.join(cls.interfaces)}")
            if cls.modifier:    lines.append(f"    ↳ Modificador: {cls.modifier}")
            attrs = {k: v.get('value') for k, v in cls.attributes.items()}
            lines.append(f"    ↳ Atributos  : {attrs}")
            methods_info = {k: v.get('modifier', 'public') for k, v in cls.methods.items()}
            lines.append(f"    ↳ Métodos    : {methods_info}")
            if cls.constructor:
                params = list(cls.constructor.get('params', {}).keys())
                lines.append(f"    ↳ Constructor: ✔ params={params}")
        for name in self.interface_definitions:
            lines.append(f"  Interfaz '{name}'")
        return "\n".join(lines)

# ==============================================================================
# STRUCT SYSTEM — Tipos C-style (StructDefinition, StructInstance, StructSymbolTable)
# ==============================================================================

class StructFieldDef:
    """Define un campo dentro de una definición de struct."""
    PRIMITIVE_TYPES = frozenset({'int', 'float', 'string', 'bool'})
    COLLECTION_TYPES = frozenset({'array', 'tuple', 'dict'})

    def __init__(self, name, declared_type='dynamic', is_const=False,
                 initial_value=None, limit=None, is_dynamic=True):
        self.name          = name
        self.declared_type = declared_type  # 'dynamic'|'int'|'float'|'string'|'bool'|
                                             # 'array'|'tuple'|'dict'|<struct_name>
        self.is_const      = is_const
        self.initial_value = initial_value
        self.limit         = limit          # int|None — límite de elementos para colecciones
        self.is_dynamic    = is_dynamic

    def __repr__(self):
        mod  = "const " if self.is_const else ""
        lim  = f"[{self.limit}]" if self.limit is not None else ""
        return f"StructFieldDef({mod}{self.declared_type}{lim} {self.name} = {self.initial_value!r})"


class StructDefinition:
    """Plano (blueprint) de un tipo struct."""
    def __init__(self, name: str):
        self.name   = name
        self.fields: dict = {}  # OrderedDict implícito en Python 3.7+

    def add_field(self, fdef: 'StructFieldDef'):
        self.fields[fdef.name] = fdef

    def __repr__(self):
        return f"StructDef({self.name}, fields={list(self.fields.keys())})"


class StructInstance:
    """Instancia concreta de un struct (semántica de valor, como en C)."""
    _counter = 0

    def __init__(self, struct_name: str, struct_def: 'StructDefinition',
                 interpreter: 'object'):
        StructInstance._counter += 1
        self._id         = StructInstance._counter
        self.struct_name = struct_name
        self.struct_def  = struct_def
        # field_name -> {'value': <val>, 'const_assigned': bool}
        self.fields: dict = {}
        self._init_fields(struct_def, interpreter)

    def _init_fields(self, struct_def: 'StructDefinition', interpreter):
        import copy
        for fname, fdef in struct_def.fields.items():
            dtype = fdef.declared_type
            # ¿Es un tipo struct anidado?
            if (dtype and dtype not in ('dynamic', 'int', 'float', 'string', 'bool',
                                         'array', 'tuple', 'dict', 'null', 'NULL', None)
                    and hasattr(interpreter, 'struct_table')
                    and interpreter.struct_table.has_definition(dtype)):
                nested_def  = interpreter.struct_table.get_definition(dtype)
                nested_inst = StructInstance(dtype, nested_def, interpreter)
                self.fields[fname] = {'value': nested_inst, 'const_assigned': False}
                interpreter._log(
                    f"[STRUCT:INIT]   ↳ campo '{fname}' = struct anidado "
                    f"'{dtype}' (instancia #{nested_inst._id})")
            else:
                iv = fdef.initial_value
                if isinstance(iv, (list, dict)):
                    iv = copy.deepcopy(iv)
                self.fields[fname] = {'value': iv, 'const_assigned': False}
                mod = "const " if fdef.is_const else ""
                lim = f"[{fdef.limit}]" if fdef.limit is not None else ""
                interpreter._log(
                    f"[STRUCT:INIT]   ↳ campo '{mod}{fdef.declared_type}{lim} {fname}'"
                    f" = {iv!r}")

    # ── acceso a campos ──────────────────────────────────────────────────────
    def get_field(self, name: str):
        if name not in self.fields:
            raise InterpreterError(
                f"El campo '{name}' no existe en struct '{self.struct_name}'.")
        return self.fields[name]['value']

    def set_field(self, name: str, value, fdef: 'StructFieldDef' = None):
        if name not in self.fields:
            raise InterpreterError(
                f"El campo '{name}' no existe en struct '{self.struct_name}'.")
        info = self.fields[name]
        if fdef is None:
            fdef = self.struct_def.fields.get(name)
        if fdef and fdef.is_const:
            if info['const_assigned']:
                raise InvalidOperationError(
                    f"No se puede reasignar la constante '{name}' "
                    f"en struct '{self.struct_name}'.")
            info['const_assigned'] = True
        info['value'] = value
    # ── formato de impresión (azúcar sintáctico) ─────────────────────────────
    def format_print(self, path_prefix: str) -> str:
        """persona<p1.name=null, p1.edad=0, ...> — en orden de declaración."""
        parts = []
        for fname, info in self.fields.items():
            val  = info['value']
            fpath = f"{path_prefix}.{fname}"
            if isinstance(val, StructInstance):
                fval = val.format_print(fpath)
            elif val is None:
                fval = "null"
            elif isinstance(val, bool):
                fval = "true" if val else "false"
            elif isinstance(val, float):
                s = f'{val:.15f}'.rstrip('0')
                fval = s if not s.endswith('.') else s + '0'
            elif isinstance(val, list):
                fval = '[' + ', '.join(_fmt_val(i) for i in val) + ']'
            elif isinstance(val, tuple):
                fval = '(' + ', '.join(_fmt_val(i) for i in val) + ')'
            elif isinstance(val, dict):
                fval = '{' + ', '.join(f"{k}:{_fmt_val(v)}" for k, v in val.items()) + '}'
            else:
                fval = str(val)
            parts.append(f"{fpath}={fval}")
        return f"{self.struct_name}<{', '.join(parts)}>"

    def __repr__(self):
        return f"<StructInstance {self.struct_name}#{self._id}>"


class StructSymbolTable:
    """Tabla de símbolos dedicada a definiciones de struct."""
    def __init__(self):
        self.definitions: dict = {}   # name -> StructDefinition

    def declare(self, name: str, sdef: 'StructDefinition'):
        self.definitions[name] = sdef

    def has_definition(self, name: str) -> bool:
        return name in self.definitions

    def get_definition(self, name: str, raise_if_missing=True) -> 'StructDefinition':
        if name not in self.definitions:
            if not raise_if_missing:
                return None
            raise InterpreterError(f"Struct '{name}' no está declarada.")
        return self.definitions[name]

    def __str__(self):
        if not self.definitions:
            return "  [Sin structs declaradas]"
        lines = []
        for sname, sdef in self.definitions.items():
            lines.append(f"  Struct '{sname}':")
            for fname, fdef in sdef.fields.items():
                mod  = "const " if fdef.is_const else ""
                lim  = f"[{fdef.limit}]" if fdef.limit is not None else ""
                lines.append(
                    f"    ↳ {mod}{fdef.declared_type}{lim} {fname} "
                    f"(default={fdef.initial_value!r})")
        return "\n".join(lines)

# ==============================================================================
# Core Type Methods — librería interna oculta
# Cada tipo tiene su tabla de métodos con tres categorías:
#   'first'      — solo después del origen directo
#   'chainable'  — primera y encadenable
#   'chain_only' — solo en cadena (no sobre el origen directo)
#   'mutable_default' — muta sin necesidad de .mut (solo colecciones)
# ==============================================================================

def _core_string_methods():
    return {
        # ── first ────────────────────────────────────────────────────────────
        'length':      {'cat': 'first',     'fn': lambda v, args: len(str(v))},
        'isEmpty':     {'cat': 'first',     'fn': lambda v, args: len(str(v)) == 0},
        'isArray':     {'cat': 'first',     'fn': lambda v, args: False},
        'isString':    {'cat': 'first',     'fn': lambda v, args: True},
        'isInt':       {'cat': 'first',     'fn': lambda v, args: False},
        'isFloat':     {'cat': 'first',     'fn': lambda v, args: False},
        'isBool':      {'cat': 'first',     'fn': lambda v, args: False},
        'type':        {'cat': 'first',     'fn': lambda v, args: 'string'},
        # ── chainable ────────────────────────────────────────────────────────
        'toUpperCase': {'cat': 'chainable', 'fn': lambda v, args: str(v).upper()},
        'toLowerCase': {'cat': 'chainable', 'fn': lambda v, args: str(v).lower()},
        'UpperFirst':  {'cat': 'chainable', 'fn': lambda v, args: (
            str(v)[0].upper() + str(v)[1:] if str(v) and str(v)[0].isalpha() else str(v))},
        'trim':        {'cat': 'chainable', 'fn': lambda v, args: str(v).strip()},
        'trimStart':   {'cat': 'chainable', 'fn': lambda v, args: str(v).lstrip()},
        'trimEnd':     {'cat': 'chainable', 'fn': lambda v, args: str(v).rstrip()},
        'reverse':     {'cat': 'chainable', 'fn': lambda v, args: str(v)[::-1]},
        'repeat':      {'cat': 'chainable', 'fn': lambda v, args: str(v) * int(args[0]) if args else str(v)},
        'replace':     {'cat': 'chainable', 'fn': lambda v, args: str(v).replace(str(args[0]), str(args[1])) if len(args) >= 2 else str(v)},
        'split':       {'cat': 'chainable', 'fn': lambda v, args: str(v).split(str(args[0])) if args else list(str(v))},
        'slice':       {'cat': 'chainable', 'fn': lambda v, args: str(v)[int(args[0]):int(args[1])] if len(args) >= 2 else str(v)[int(args[0]):]},
        'charAt':      {'cat': 'chainable', 'fn': lambda v, args: str(v)[int(args[0])] if args and 0 <= int(args[0]) < len(str(v)) else ''},
        'contains':    {'cat': 'chainable', 'fn': lambda v, args: str(args[0]) in str(v) if args else False},
        'startsWith':  {'cat': 'chainable', 'fn': lambda v, args: str(v).startswith(str(args[0])) if args else False},
        'endsWith':    {'cat': 'chainable', 'fn': lambda v, args: str(v).endswith(str(args[0])) if args else False},
        'indexOf':     {'cat': 'chainable', 'fn': lambda v, args: str(v).find(str(args[0])) if args else -1},
        'padStart':    {'cat': 'chainable', 'fn': lambda v, args: str(v).rjust(int(args[0]), str(args[1]) if len(args) > 1 else ' ')},
        'padEnd':      {'cat': 'chainable', 'fn': lambda v, args: str(v).ljust(int(args[0]), str(args[1]) if len(args) > 1 else ' ')},
        # ── conversores (chainable, inmutables por defecto) ───────────────────
        'typeInt':     {'cat': 'chainable', 'fn': lambda v, args: int(float(str(v))) if str(v).replace('.','',1).lstrip('-').isdigit() else 0},
        'typeFloat':   {'cat': 'chainable', 'fn': lambda v, args: float(str(v)) if str(v).replace('.','',1).lstrip('-').isdigit() else 0.0},
        'typeBool':    {'cat': 'chainable', 'fn': lambda v, args: len(str(v)) > 0 and str(v).lower() not in ('false','0','')},
        'typeString':  {'cat': 'chainable', 'fn': lambda v, args: str(v)},
        'binary':      {'cat': 'chainable', 'fn': lambda v, args: _binary_value(v, args)},
    }

def _core_int_methods():
    return {
        'length':      {'cat': 'first',     'fn': lambda v, args: len(str(int(v)))},
        'isEmpty':     {'cat': 'first',     'fn': lambda v, args: False},
        'isArray':     {'cat': 'first',     'fn': lambda v, args: False},
        'isString':    {'cat': 'first',     'fn': lambda v, args: False},
        'isInt':       {'cat': 'first',     'fn': lambda v, args: True},
        'isFloat':     {'cat': 'first',     'fn': lambda v, args: False},
        'isBool':      {'cat': 'first',     'fn': lambda v, args: False},
        'type':        {'cat': 'first',     'fn': lambda v, args: 'int'},
        'abs':         {'cat': 'chainable', 'fn': lambda v, args: abs(int(v))},
        'clamp':       {'cat': 'chainable', 'fn': lambda v, args: max(int(args[0]), min(int(v), int(args[1]))) if len(args) >= 2 else int(v)},
        'pow':         {'cat': 'chainable', 'fn': lambda v, args: int(v) ** int(args[0]) if args else int(v)},
        'max':         {'cat': 'chainable', 'fn': lambda v, args: max(int(v), int(args[0])) if args else int(v)},
        'min':         {'cat': 'chainable', 'fn': lambda v, args: min(int(v), int(args[0])) if args else int(v)},
        'isEven':      {'cat': 'first',     'fn': lambda v, args: int(v) % 2 == 0},
        'isOdd':       {'cat': 'first',     'fn': lambda v, args: int(v) % 2 != 0},
        'isPositive':  {'cat': 'first',     'fn': lambda v, args: int(v) > 0},
        'isNegative':  {'cat': 'first',     'fn': lambda v, args: int(v) < 0},
        'typeFloat':   {'cat': 'chainable', 'fn': lambda v, args: float(v)},
        'typeString':  {'cat': 'chainable', 'fn': lambda v, args: str(v)},
        'typeBool':    {'cat': 'chainable', 'fn': lambda v, args: int(v) != 0},
        'typeInt':     {'cat': 'chainable', 'fn': lambda v, args: int(v)},
        'binary':      {'cat': 'chainable', 'fn': lambda v, args: _binary_value(v, args)},
    }

def _core_float_methods():
    return {
        'length':      {'cat': 'first',     'fn': lambda v, args: len(str(v))},
        'isEmpty':     {'cat': 'first',     'fn': lambda v, args: False},
        'isArray':     {'cat': 'first',     'fn': lambda v, args: False},
        'isString':    {'cat': 'first',     'fn': lambda v, args: False},
        'isInt':       {'cat': 'first',     'fn': lambda v, args: False},
        'isFloat':     {'cat': 'first',     'fn': lambda v, args: True},
        'isBool':      {'cat': 'first',     'fn': lambda v, args: False},
        'type':        {'cat': 'first',     'fn': lambda v, args: 'float'},
        'abs':         {'cat': 'chainable', 'fn': lambda v, args: abs(float(v))},
        'round':       {'cat': 'chainable', 'fn': lambda v, args: round(float(v), int(args[0])) if args else round(float(v))},
        'floor':       {'cat': 'chainable', 'fn': lambda v, args: int(float(v) // 1)},
        'ceil':        {'cat': 'chainable', 'fn': lambda v, args: int(-(-float(v) // 1))},
        'clamp':       {'cat': 'chainable', 'fn': lambda v, args: max(float(args[0]), min(float(v), float(args[1]))) if len(args) >= 2 else float(v)},
        'pow':         {'cat': 'chainable', 'fn': lambda v, args: float(v) ** float(args[0]) if args else float(v)},
        'isNaN':       {'cat': 'first',     'fn': lambda v, args: float(v) != float(v)},
        'isInfinite':  {'cat': 'first',     'fn': lambda v, args: float(v) in (float('inf'), float('-inf'))},
        'typeInt':     {'cat': 'chainable', 'fn': lambda v, args: int(float(v))},
        'typeString':  {'cat': 'chainable', 'fn': lambda v, args: str(float(v))},
        'typeBool':    {'cat': 'chainable', 'fn': lambda v, args: float(v) != 0.0},
        'typeFloat':   {'cat': 'chainable', 'fn': lambda v, args: float(v)},
        'binary':      {'cat': 'chainable', 'fn': lambda v, args: _binary_value(v, args)},
    }

def _core_bool_methods():
    return {
        'type':        {'cat': 'first',     'fn': lambda v, args: 'bool'},
        'isArray':     {'cat': 'first',     'fn': lambda v, args: False},
        'isString':    {'cat': 'first',     'fn': lambda v, args: False},
        'isInt':       {'cat': 'first',     'fn': lambda v, args: False},
        'isFloat':     {'cat': 'first',     'fn': lambda v, args: False},
        'isBool':      {'cat': 'first',     'fn': lambda v, args: True},
        'toggle':      {'cat': 'chainable', 'fn': lambda v, args: not bool(v)},
        'typeInt':     {'cat': 'chainable', 'fn': lambda v, args: 1 if v else 0},
        'typeString':  {'cat': 'chainable', 'fn': lambda v, args: 'true' if v else 'false'},
        'typeFloat':   {'cat': 'chainable', 'fn': lambda v, args: 1.0 if v else 0.0},
        'typeBool':    {'cat': 'chainable', 'fn': lambda v, args: bool(v)},
    }

def _core_array_methods():
    import copy
    return {
        'length':      {'cat': 'first',     'fn': lambda v, args: len(v) if isinstance(v, list) else 0},
        'isEmpty':     {'cat': 'first',     'fn': lambda v, args: len(v) == 0 if isinstance(v, list) else True},
        'isArray':     {'cat': 'first',     'fn': lambda v, args: True},
        'isString':    {'cat': 'first',     'fn': lambda v, args: False},
        'isInt':       {'cat': 'first',     'fn': lambda v, args: False},
        'isFloat':     {'cat': 'first',     'fn': lambda v, args: False},
        'isBool':      {'cat': 'first',     'fn': lambda v, args: False},
        'type':        {'cat': 'first',     'fn': lambda v, args: 'array'},
        'first':       {'cat': 'first',     'fn': lambda v, args: v[0] if isinstance(v, list) and v else None},
        'last':        {'cat': 'first',     'fn': lambda v, args: v[-1] if isinstance(v, list) and v else None},
        # ── mutables por defecto ──────────────────────────────────────────────
        'push':        {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: v + [args[0]] if isinstance(v, list) and args else v},
        'pop':         {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: v[:-1] if isinstance(v, list) and v else v},
        'shift':       {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: v[1:] if isinstance(v, list) and v else v},
        'unshift':     {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: [args[0]] + v if isinstance(v, list) and args else v},
        'insert':      {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: v[:int(args[0])] + [args[1]] + v[int(args[0]):] if isinstance(v, list) and len(args) >= 2 else v},
        'remove':      {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: [x for x in v if x != args[0]] if isinstance(v, list) and args else v},
        'clear':       {'cat': 'chainable', 'mutable_default': True,
                        'fn': lambda v, args: []},
        # ── inmutables (necesitan .mut para mutar) ────────────────────────────
        'sort':        {'cat': 'chainable', 'fn': lambda v, args: sorted(v) if isinstance(v, list) else v},
        'reverse':     {'cat': 'chainable', 'fn': lambda v, args: list(reversed(v)) if isinstance(v, list) else v},
        'filter':      {'cat': 'chainable', 'fn': lambda v, args: v},   # args lo evalúa el handler
        'map':         {'cat': 'chainable', 'fn': lambda v, args: v},
        'slice':       {'cat': 'chainable', 'fn': lambda v, args: v[int(args[0]):int(args[1])] if isinstance(v, list) and len(args) >= 2 else v[int(args[0]):] if args else v},
        'concat':      {'cat': 'chainable', 'fn': lambda v, args: v + (args[0] if isinstance(args[0], list) else [args[0]]) if isinstance(v, list) and args else v},
        'contains':    {'cat': 'chainable', 'fn': lambda v, args: args[0] in v if isinstance(v, list) and args else False},
        'indexOf':     {'cat': 'chainable', 'fn': lambda v, args: v.index(args[0]) if isinstance(v, list) and args and args[0] in v else -1},
        'join':        {'cat': 'chainable', 'fn': lambda v, args: str(args[0]).join(str(x) for x in v) if isinstance(v, list) else str(v)},
        'unique':      {'cat': 'chainable', 'fn': lambda v, args: list(dict.fromkeys(v)) if isinstance(v, list) else v},
        'flatten':     {'cat': 'chainable', 'fn': lambda v, args: [x for sub in v for x in (sub if isinstance(sub, list) else [sub])] if isinstance(v, list) else v},
        'typeString':  {'cat': 'chainable', 'fn': lambda v, args: str(v)},
        # ── solo encadenables (chain_only) ────────────────────────────────────
        'mut':         {'cat': 'chain_only','fn': None},  # manejado por el dispatcher
    }

def _core_null_methods():
    return {
        'isNull':   {'cat': 'first', 'fn': lambda v, args: True},
        'isArray':  {'cat': 'first', 'fn': lambda v, args: False},
        'isString': {'cat': 'first', 'fn': lambda v, args: False},
        'isInt':    {'cat': 'first', 'fn': lambda v, args: False},
        'isFloat':  {'cat': 'first', 'fn': lambda v, args: False},
        'isBool':   {'cat': 'first', 'fn': lambda v, args: False},
        'type':     {'cat': 'first', 'fn': lambda v, args: 'null'},
        'typeString': {'cat': 'chainable', 'fn': lambda v, args: 'null'},
    }

def _core_tuple_methods():
    return {
        'length':  {'cat': 'first', 'fn': lambda v, args: len(v) if isinstance(v, tuple) else 0},
        'isEmpty': {'cat': 'first', 'fn': lambda v, args: len(v) == 0 if isinstance(v, tuple) else True},
        'isArray': {'cat': 'first', 'fn': lambda v, args: False},
        'isString':{'cat': 'first', 'fn': lambda v, args: False},
        'isInt':   {'cat': 'first', 'fn': lambda v, args: False},
        'isFloat': {'cat': 'first', 'fn': lambda v, args: False},
        'isBool':  {'cat': 'first', 'fn': lambda v, args: False},
        'type':    {'cat': 'first', 'fn': lambda v, args: 'tuple'},
        'first':   {'cat': 'first', 'fn': lambda v, args: v[0] if isinstance(v, tuple) and v else None},
        'last':    {'cat': 'first', 'fn': lambda v, args: v[-1] if isinstance(v, tuple) and v else None},
        'typeString': {'cat': 'chainable', 'fn': lambda v, args: str(v)},
    }

def _core_dict_methods():
    return {
        'length':  {'cat': 'first', 'fn': lambda v, args: len(v) if isinstance(v, dict) else 0},
        'isEmpty': {'cat': 'first', 'fn': lambda v, args: len(v) == 0 if isinstance(v, dict) else True},
        'isArray': {'cat': 'first', 'fn': lambda v, args: False},
        'isString':{'cat': 'first', 'fn': lambda v, args: False},
        'isInt':   {'cat': 'first', 'fn': lambda v, args: False},
        'isFloat': {'cat': 'first', 'fn': lambda v, args: False},
        'isBool':  {'cat': 'first', 'fn': lambda v, args: False},
        'type':    {'cat': 'first', 'fn': lambda v, args: 'dict'},
        'keys':    {'cat': 'chainable', 'fn': lambda v, args: list(v.keys()) if isinstance(v, dict) else []},
        'values':  {'cat': 'chainable', 'fn': lambda v, args: list(v.values()) if isinstance(v, dict) else []},
        'items':   {'cat': 'chainable', 'fn': lambda v, args: [[k, vv] for k, vv in v.items()] if isinstance(v, dict) else []},
        'typeString': {'cat': 'chainable', 'fn': lambda v, args: str(v)},
    }

# Mapa global tipo → tabla de métodos
def _binary_value(v, args) -> str:
    """
    Convierte un valor escalar (int, float, str) a binario de n_bytes bytes.
    binary(n_bytes=1, signed=False)
    No muta el valor original.
    """
    import struct as _struct
    n_bytes = int(args[0]) if args else 1
    signed  = bool(args[1]) if len(args) > 1 else False
    bits    = n_bytes * 8
    try:
        if isinstance(v, bool):
            return format(int(v), f'0{bits}b')[-bits:]
        if isinstance(v, int):
            i_val = v
            if signed and i_val < 0:
                i_val = i_val & ((1 << bits) - 1)
            return format(i_val, f'0{bits}b')[-bits:]
        if isinstance(v, float):
            raw    = _struct.pack('>d', v)         # 8 bytes IEEE 754 big-endian
            padded = raw[:n_bytes].ljust(n_bytes, b'\x00')
            return ''.join(f'{b:08b}' for b in padded)
        if isinstance(v, str):
            raw    = v.encode('utf-8')
            padded = raw[:n_bytes].ljust(n_bytes, b'\x00')
            return ''.join(f'{b:08b}' for b in padded)
    except Exception:
        pass
    return '0' * bits


_CORE_TYPE_METHODS = {
    'string':  _core_string_methods(),
    'int':     _core_int_methods(),
    'float':   _core_float_methods(),
    'bool':    _core_bool_methods(),
    'array':   _core_array_methods(),
    'null':    _core_null_methods(),
    'tuple':   _core_tuple_methods(),
    'dict':    _core_dict_methods(),
}

# ==============================================================================
# RANGE SYSTEM
# ==============================================================================
import decimal as _decimal

class RangeValue:
    """
    Tipo 'range' del lenguaje.  Representa un rango perezoso [start..end].
    Tipos soportados: int, float (1 decimal), string/unicode, null.

    Reglas:
      - start <= end  (siempre)
      - Tipos homogéneos excepto int+float (se promociona a float)
      - null..null  → rango nulo
      - Paso (step) por defecto: 1 para int/string, 0.1 para float
    """
    _KIND_INT    = 'int'
    _KIND_FLOAT  = 'float'
    _KIND_STRING = 'string'
    _KIND_NULL   = 'null'

    def __init__(self, start, end, step=None, half_open: bool = False):
        self.start     = start
        self.end       = end
        self.half_open = half_open   # True → excluye end (1..<5 = 1,2,3,4)
        self._kind     = self._infer_kind(start, end)
        self._step     = step

    # ── Inferencia de tipo ────────────────────────────────────────────────────
    @staticmethod
    def _infer_kind(start, end):
        if start is None and end is None:
            return RangeValue._KIND_NULL
        if isinstance(start, float) or isinstance(end, float):
            return RangeValue._KIND_FLOAT
        if isinstance(start, int) and isinstance(end, int):
            return RangeValue._KIND_INT
        if isinstance(start, str) and isinstance(end, str):
            return RangeValue._KIND_STRING
        return RangeValue._KIND_INT

    @property
    def kind(self):
        return self._kind

    # ── Paso efectivo ─────────────────────────────────────────────────────────
    @property
    def effective_step(self):
        if self._step is not None:
            return self._step
        return 0.1 if self._kind == self._KIND_FLOAT else 1

    # ── Expansión bajo demanda ────────────────────────────────────────────────
    def expand(self) -> list:
        """Genera la lista de valores del rango."""
        if self._kind == self._KIND_NULL:
            return []
        if self._kind == self._KIND_INT:
            end = self.end if not self.half_open else self.end - 1
            return list(range(self.start, end + 1,
                              max(1, int(self.effective_step))))
        if self._kind == self._KIND_FLOAT:
            import decimal as _dec
            step = _dec.Decimal(str(self.effective_step))
            cur  = _dec.Decimal(str(self.start))
            stop = _dec.Decimal(str(self.end))
            if self.half_open:
                # excluir end
                result = []
                while cur < stop:
                    result.append(float(cur))
                    cur += step
                return result
            result = []
            while cur <= stop:
                result.append(float(cur))
                cur += step
            if result and _dec.Decimal(str(result[-1])) < stop:
                result.append(float(stop))
            return result
        if self._kind == self._KIND_STRING:
            s_cp = ord(self.start)
            e_cp = ord(self.end) if not self.half_open else ord(self.end) - 1
            step = max(1, int(self.effective_step))
            return [chr(cp) for cp in range(s_cp, e_cp + 1, step)]
        return []

    # ── Longitud ──────────────────────────────────────────────────────────────
    def length(self) -> int:
        return len(self.expand())

    # ── Representación ────────────────────────────────────────────────────────
    def format_display(self) -> str:
        """Range<0,1,2,3>"""
        if self._kind == self._KIND_NULL:
            return 'Range<null>'
        items = self.expand()
        inner = ','.join(str(v) for v in items)
        return f'Range<{inner}>'

    def format_short(self) -> str:
        """start..end  (forma compacta)"""
        if self._kind == self._KIND_NULL:
            return 'null..null'
        s = f'"{self.start}"' if self._kind == self._KIND_STRING else str(self.start)
        e = f'"{self.end}"'   if self._kind == self._KIND_STRING else str(self.end)
        sep = '..<' if self.half_open else '..'
        return f'{s}{sep}{e}'

    def __repr__(self):
        return f'RangeValue({self.format_short()})'


def _core_range_methods():
    def _must_be_range(v):
        if not isinstance(v, RangeValue):
            raise Exception(f"Se esperaba un rango, se recibió {type(v).__name__}")

    def _get_start(v, args): _must_be_range(v); return v.start
    def _get_end(v, args):   _must_be_range(v); return v.end
    def _get_length(v, args):_must_be_range(v); return v.length()

    def _set_step(v, args):
        _must_be_range(v)
        if not args: raise Exception("step() requiere un argumento numérico")
        try: new_step = float(args[0])
        except (TypeError, ValueError): raise Exception(f"step() requiere número")
        return RangeValue(v.start, v.end, step=new_step, half_open=v.half_open)

    def _to_array(v, args): _must_be_range(v); return v.expand()
    def _to_tuple(v, args): _must_be_range(v); return tuple(v.expand())
    def _type_fn(v, args):  return 'range'
    def _is_empty(v, args): _must_be_range(v); return v.length() == 0

    def _uni(v, args):
        """
        Devuelve los valores unicode (codepoints) del rango como lista de strings.
        Para rangos string: en vez de caracteres, devuelve 'U+XXXX'.
        Para rangos int/float: devuelve la representación en memoria (hex del int/float).
        No muta.
        """
        _must_be_range(v)
        items = v.expand()
        if v.kind == RangeValue._KIND_STRING:
            return [f'U+{ord(c):04X}' for c in items]
        elif v.kind == RangeValue._KIND_INT:
            return [hex(i) for i in items]
        elif v.kind == RangeValue._KIND_FLOAT:
            import struct
            return [hex(struct.unpack('<Q', struct.pack('<d', f))[0]) for f in items]
        return []

    def _binary(v, args):
        """
        binary(n_bytes=1, type='int', signed=False)
        Convierte cada elemento del rango a binario real de n_bytes bytes.
        No muta.
        """
        _must_be_range(v)
        n_bytes = int(args[0]) if args else 1
        typ     = str(args[1]).strip().strip("'\"") if len(args) > 1 else 'int'
        signed  = bool(args[2]) if len(args) > 2 else False
        bits    = n_bytes * 8
        items   = v.expand()
        result  = []
        for item in items:
            try:
                if isinstance(item, str):
                    # UTF-8: cada byte como binario, pad hasta n_bytes
                    raw = item.encode('utf-8')
                    # Tomar hasta n_bytes, rellenar con ceros si es más corto
                    padded = raw[:n_bytes].ljust(n_bytes, b'\x00')
                    result.append(''.join(f'{b:08b}' for b in padded))
                elif isinstance(item, float):
                    import struct
                    # Double IEEE 754 → 8 bytes, recortar/pad a n_bytes
                    raw = struct.pack('>d', item)
                    padded = raw[:n_bytes].ljust(n_bytes, b'\x00')
                    result.append(''.join(f'{b:08b}' for b in padded))
                else:
                    i_val = int(item)
                    if signed and i_val < 0:
                        # Complemento a dos
                        i_val = i_val & ((1 << bits) - 1)
                    # format con el número exacto de bits (cero-padded)
                    result.append(format(i_val, f'0{bits}b')[-bits:])
            except Exception:
                result.append('0' * bits)
        return result

    return {
        'start':    {'cat': 'first',     'fn': _get_start},
        'end':      {'cat': 'first',     'fn': _get_end},
        'length':   {'cat': 'first',     'fn': _get_length},
        'step':     {'cat': 'chainable', 'fn': _set_step},
        'toarray':  {'cat': 'chainable', 'fn': _to_array},
        'totuple':  {'cat': 'chainable', 'fn': _to_tuple},
        'type':     {'cat': 'first',     'fn': _type_fn},
        'isEmpty':  {'cat': 'first',     'fn': _is_empty},
        'uni':      {'cat': 'chainable', 'fn': _uni},
        'binary':   {'cat': 'chainable', 'fn': _binary},
        'typeString': {'cat': 'chainable', 'fn': lambda v, a: v.format_short()},
    }

_CORE_TYPE_METHODS['range'] = _core_range_methods()

# ==============================================================================
# RANGE PARSING HELPERS (module-level, usados desde el intérprete)
# ==============================================================================

_RANGE_LITERAL_RE = re.compile(
    r'^'
    r'(-?\d+\.\d+|-?\d+|'           # int o float
    r'"[^"]*"|\'[^\']*\'|'           # string con comillas dobles o simples
    r'null|'                         # null
    r'u[0-9A-Fa-f]{4,6})'           # unicode literal u0041
    r'\.\.'
    r'(-?\d+\.\d+|-?\d+|'
    r'"[^"]*"|\'[^\']*\'|'
    r'null|'
    r'u[0-9A-Fa-f]{4,6})'
    r'$'
)

def _parse_range_endpoint(raw: str, half_open: bool = False):
    """
    Convierte un endpoint de rango a su valor Python.
    Retorna (value, kind) donde kind ∈ {'int','float','string','null'}.

    Unicode SOLO entre comillas: "u0041" → chr(0x41) = 'A'
    Sin comillas: u0041 es un identificador, no unicode.
    """
    raw = raw.strip()
    if raw == 'null':
        return None, 'null'
    # String entre comillas (incluyendo unicode entre comillas)
    if (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")):
        s = raw[1:-1]
        # Unicode dentro de comillas: "u0041" → 'A'
        if re.fullmatch(r'u[0-9A-Fa-f]{4,6}', s):
            cp = int(s[1:], 16)
            return chr(cp), 'string'
        if len(s) != 1:
            raise ValueError(
                f"Endpoint de rango string debe ser un solo carácter, se recibió {raw!r}")
        return s, 'string'
    # Float
    if re.fullmatch(r'-?\d+\.\d+', raw):
        return float(raw), 'float'
    # Int
    if re.fullmatch(r'-?\d+', raw):
        return int(raw), 'int'
    raise ValueError(f"Endpoint de rango inválido: {raw!r}")


def _build_range(raw_start: str, raw_end: str, half_open: bool = False) -> 'RangeValue':
    """
    Construye y valida un RangeValue desde sus endpoints en texto.
    half_open=True → excluye el endpoint final (1..<5 = 1,2,3,4).
    Lanza ValueError con mensaje descriptivo si algo es inválido.
    """
    s_val, s_kind = _parse_range_endpoint(raw_start)
    e_val, e_kind = _parse_range_endpoint(raw_end)

    # Rango nulo
    if s_kind == 'null' and e_kind == 'null':
        return RangeValue(None, None, half_open=half_open)

    if s_kind == 'null' or e_kind == 'null':
        raise ValueError("Solo se permite null..null, no null mezclado con otro tipo")

    # Promoción int→float
    if s_kind == 'float' and e_kind == 'int':
        e_val = float(e_val); e_kind = 'float'
    if e_kind == 'float' and s_kind == 'int':
        s_val = float(s_val); s_kind = 'float'

    if s_kind != e_kind:
        raise ValueError(
            f"Tipos incompatibles en rango: {s_kind} .. {e_kind}. "
            f"Solo se pueden combinar int+float.")

    # Validar start <= end (para half_open: start < end)
    if s_kind == 'string':
        limit = ord(e_val) - (1 if half_open else 0)
        if ord(s_val) > limit:
            raise ValueError(
                f"Rango inválido: el inicio '{s_val}' (U+{ord(s_val):04X}) "
                f"es mayor que el fin efectivo")
    else:
        limit = e_val - (1 if half_open and s_kind == 'int' else 0)
        if s_val > (e_val if not half_open  or s_val == e_val else e_val - 1e-12):
            raise ValueError(
                f"Rango inválido: el inicio {s_val} es mayor que el fin {e_val}")

    # Validar flotante de 1 decimal
    if s_kind == 'float':
        def _check_decimal(v, name):
            s = str(v)
            if '.' in s and len(s.split('.')[1]) > 1:
                raise ValueError(
                    f"Rango float: {name} '{v}' tiene más de 1 decimal. "
                    f"Solo se permite 1 decimal (ej. 0.5..1.5)")
        _check_decimal(s_val, 'start')
        _check_decimal(e_val, 'end')

    # Validar string: no mezclar mayúsculas/minúsculas
    if s_kind == 'string':
        sl, el = s_val.islower(), e_val.islower()
        su, eu = s_val.isupper(), e_val.isupper()
        if (sl and eu) or (su and el):
            raise ValueError(
                f"Rango string: no se pueden combinar mayúsculas y minúsculas "
                f"('{s_val}'..'{e_val}')")

    return RangeValue(s_val, e_val, half_open=half_open)


def _expand_collection_items(items: list) -> list:
    """
    Expande RangeValues dentro de una lista de items (para arrays/tuplas).
    [1..3, 4, 5..6]  →  [1, 2, 3, 4, 5, 6]
    """
    result = []
    for item in items:
        if isinstance(item, RangeValue):
            result.extend(item.expand())
        else:
            result.append(item)
    return result


# Tipos nativos del lenguaje (actualizado con range)
_NATIVE_TYPES = frozenset({
    'dynamic', 'int', 'float', 'string', 'bool',
    'array', 'tuple', 'dict', 'null', 'NULL', 'any', 'range'
})

def _get_value_type(value) -> str:
    """Infiere el tipo Tesseract de un valor Python."""
    if value is None:                    return 'null'
    if isinstance(value, RangeValue):    return 'range'
    if isinstance(value, bool):          return 'bool'
    if isinstance(value, int):           return 'int'
    if isinstance(value, float):         return 'float'
    if isinstance(value, str):           return 'string'
    if isinstance(value, tuple):         return 'tuple'
    if isinstance(value, list):          return 'array'
    if isinstance(value, dict):          return 'dict'
    return 'dynamic'

def _fmt_val(v) -> str:
    """Formatea un valor Python al estilo del lenguaje."""
    if v is None:                    return 'null'
    if isinstance(v, RangeValue):    return v.format_display()
    if isinstance(v, bool):          return 'true' if v else 'false'
    if isinstance(v, float):
        s = f'{v:.15f}'.rstrip('0')
        return s if not s.endswith('.') else s + '0'
    if isinstance(v, tuple):
        return '(' + ', '.join(_fmt_val(i) for i in v) + ')'
    if isinstance(v, list):
        return '[' + ', '.join(_fmt_val(i) for i in v) + ']'
    if isinstance(v, dict):
        return '{' + ', '.join(f"{k}:{_fmt_val(vv)}" for k, vv in v.items()) + '}'
    return str(v)
# ==============================================================================
# Tabla de Símbolos (Sin cambios)
# ==============================================================================
class SymbolTable:
    def __init__(self):
        self.symbols = [{}]
        self.function_symbols = {}
        self.function_params = {}
        self.function_param_values = {}
        self.scope_history = {}
        self._context_stack = []  # stack de labels activos
    @staticmethod
    def _normalize_value(value):
        if isinstance(value, float):
            return float(f'{value:.15g}'.rstrip('0').rstrip('.') or '0')
        return value
    def push_scope(self, label=""):
        """Crea un nuevo scope local."""
        self.symbols.append({})
        self._context_stack.append(label)

    def pop_scope(self, label=""):
        if len(self.symbols) > 1:
            scope = self.symbols[-1]
            if scope:
                ctx = self._context_stack[:-1]  # contexto padre
                path = " > ".join(c for c in ctx if c) 
                lbl = f"{path} > {label}" if path else label
                self.scope_history[lbl] = {k: v.value for k, v in scope.items()}
            if self._context_stack:
                self._context_stack.pop()
            self.symbols.pop()

    def _debug_log(self, message):
        """Log interno de la tabla, activado desde el intérprete."""
        if getattr(self, '_debug_mode', False):
            print(message)
    def declare(self, name, symbol):
        """Declara un nuevo símbolo."""
        self.symbols[-1][name] = symbol

    def set_value(self, name, value):
        for scope in reversed(self.symbols):
            if name in scope:
                sym = scope[name]
                if sym.is_const and sym.value is not None:
                    raise InvalidOperationError(f"No se puede reasignar la constante '{name}'.")
                sym.value = value
                return
        raise UndeclaredVariableError(name)

    def get_value(self, name):
        """Obtiene el valor actual de un símbolo."""
        for scope in reversed(self.symbols):
            if name in scope:
                return scope[name].value
        if str(name).lower() == 'true': return True
        if str(name).lower() == 'false': return False
        try: return int(name)
        except ValueError:
            try: return float(name)
            except ValueError: raise UndeclaredVariableError(name)
    def push_function_frame(self, func_name):
        """Crea un nuevo frame para una llamada recursiva."""
        if func_name not in self.function_param_values:
            self.function_param_values[func_name] = []
        self.function_param_values[func_name].append({})

    def pop_function_frame(self, func_name):
        """Elimina el frame actual al retornar de la función."""
        if func_name in self.function_param_values and self.function_param_values[func_name]:
            self.function_param_values[func_name].pop() 
    def get_symbol(self, name):
        """Obtiene el objeto Symbol completo."""
        for scope in reversed(self.symbols):
            if name in scope:
                return scope[name]
        raise UndeclaredVariableError(name)
    def declare_function(self, name, function_node):
        """Declara una nueva función."""
        self.function_symbols[name] = function_node

    def declare_function_params(self, func_name, params):
        """Declara los parámetros de una función."""
        self.function_params[func_name] = params

    def get_function(self, name):
        """Obtiene la definición de una función."""
        if name not in self.function_symbols:
            raise UndeclaredVariableError(f"Función '{name}' no ha sido declarada.")
        return self.function_symbols[name]

    def get_function_params(self, func_name):
        """Obtiene los parámetros de una función."""
        return self.function_params.get(func_name, {})
    def declare_function_param_value(self, func_name, param_name, value):
        """Guarda el valor de un parámetro para una función específica"""
        if func_name not in self.function_param_values:
            self.function_param_values[func_name] = [{}]
        self.function_param_values[func_name][-1][param_name] = value

    def get_function_param_value(self, func_name, param_name):
        """Obtiene el valor de un parámetro de una función"""
        if (func_name in self.function_param_values and 
            self.function_param_values[func_name] and
            param_name in self.function_param_values[func_name][-1]):
            return self.function_param_values[func_name][-1][param_name]
        raise UndeclaredVariableError(f"Parámetro '{param_name}' no tiene valor en función '{func_name}'")
    def __str__(self):
     # Variables normales
     def _fmt(v):
        if isinstance(v, float):
            s = f'{v:.15f}'.rstrip('0')
            return s if not s.endswith('.') else s + '0'
        return v
     scopes_list = []
     for i, scope in enumerate(self.symbols):
         label = "Global" if i == 0 else f"Local {i}"
         scopes_list.append(f"{label}: { {k: _fmt(v.value) for k, v in scope.items()} }")
     symbols_str = f"Variables:\n    " + "\n    ".join(scopes_list)
    
     # Funciones declaradas
     functions_str = f"Funciones: {list(self.function_symbols.keys())}"
    
     # Parámetros CON SUS VALORES CORRECTOS
     params_with_values = {}
     for func_name, params_info in self.function_params.items():
        func_params = {}
        for param_name, param_type in params_info.items():
            # Buscar en la tabla específica de valores de parámetros
            if (func_name in self.function_param_values and 
                param_name in self.function_param_values[func_name]):
                param_value = self.function_param_values[func_name][param_name]
                func_params[param_name] = f"{param_type} = {param_value}"
            else:
                func_params[param_name] = f"{param_type} = <null>"
        params_with_values[func_name] = func_params
    
     params_str = f"Parámetros: {params_with_values}"
     history_str = ""
     if self.scope_history:
         history_lines = ["Variables Locales (historial):"]
         for lbl, vars in self.scope_history.items():
             history_lines.append(f"    [{lbl}]: {vars}")
         history_str = "\n  " + "\n  ".join(history_lines)

     return f"Tabla de Símbolos:\n  {symbols_str}\n  {functions_str}\n  {params_str}{history_str}"
     #return f"Tabla de Símbolos:\n  {symbols_str}\n  {functions_str}\n  {params_str}"

# ==============================================================================
# Intérprete Principal
# ==============================================================================
class FunctionContext:
    """Contexto para ejecución de funciones con su propia tabla de símbolos temporal"""
    def __init__(self, interpreter, function_name, parameters):
        self.interpreter = interpreter
        self.function_name = function_name
        self.parameters = parameters
        self.local_symbols = {}
        
    def set_parameter_value(self, param_name, value):
        """Establece el valor de un parámetro en el contexto local"""
        self.local_symbols[param_name] = value
        
    def get_parameter_value(self, param_name):
        """Obtiene el valor de un parámetro del contexto local"""
        return self.local_symbols.get(param_name)
        
    def execute_function(self):
     function_def = self.interpreter.symbol_table.get_function(self.function_name)
     self.interpreter.symbol_table.push_scope(label=f"Función '{self.function_name}'")
     function_params = self.interpreter.symbol_table.get_function_params(self.function_name)
    
     # ASIGNAR PARÁMETROS A LA TABLA ESPECÍFICA
     
     self.interpreter.symbol_table.push_function_frame(self.function_name)
     self._assign_received_parameters(function_params)
     old_function = self.interpreter._current_function  # guardar la función padre
     # Establecer función actual
     self.interpreter._current_function = self.function_name
    
     # Ejecutar bloque
     if "block" in function_def:
        self.interpreter._log(f"-> Ejecutando función '{self.function_name}'")
        
        old_break_flag = self.interpreter.break_flag
        result = None
        
        self.interpreter.return_flag = False
        self.interpreter.return_value = None
        for statement in function_def["block"]:
            if self.interpreter.break_flag or self.interpreter.return_flag:
                break
            self.interpreter.execute_node(statement)
            if self.interpreter.return_flag:
                result = self.interpreter.return_value
                break

        # Limpiar el flag al salir de la función
        self.interpreter.return_flag = False
        self.interpreter.return_value = None
        
        self.interpreter.break_flag = old_break_flag
        self.interpreter._current_function = old_function
        self.interpreter.symbol_table.pop_scope(label=f"Función '{self.function_name}'")
        self.interpreter.symbol_table.pop_function_frame(self.function_name)
        self.interpreter._log(f"<- Finalizada función '{self.function_name}'")
        
        return result
    
     self.interpreter._current_function = old_function
     self.interpreter.symbol_table.pop_scope(label=f"Función '{self.function_name}'")
     self.interpreter.symbol_table.pop_function_frame(self.function_name)
     return None
    def _assign_received_parameters(self, function_params):
        param_names = list(function_params.keys())
        
        for i, param_name in enumerate(param_names):
            if i < len(self.parameters):
                param_value = self.parameters[i]
                # GUARDAR EN TABLA ESPECÍFICA DE PARÁMETROS
                self.interpreter.symbol_table.declare_function_param_value(
                    self.function_name, param_name, param_value
                )
                self.interpreter._log(f"  Asignado parámetro '{param_name}': {param_value}")
    def _validate_parameter_types(self, function_params):
        """Valida que los tipos de los parámetros coincidan"""
        param_names = list(function_params.keys())
        
        for i, (param_name, expected_type) in enumerate(function_params.items()):
            if i < len(self.parameters):
                param_value = self.parameters[i]
                actual_type = self._get_type_name(param_value)
                
                if expected_type != "any" and expected_type != actual_type:
                    raise InvalidOperationError(
                        f"Error de tipo en parámetro '{param_name}': "
                        f"se esperaba '{expected_type}', se recibió '{actual_type}'"
                    )
    
    def _get_type_name(self, value):
        """Obtiene el nombre del tipo de un valor"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int" 
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        else:
            return "any"
    
    def _execute_block_with_context(self, block):
        """Ejecuta un bloque usando el contexto local de la función"""
        # Para cada nodo en el bloque
        for statement in block:
            if self.interpreter.break_flag:
                break
                
            node_type = list(statement.keys())[0]
            node_content = statement[node_type]
            
            # Manejar asignación de parámetros de forma especial
            if node_type == "ParameterAsignement":
                self._handle_parameter_assignment(node_content)
            else:
                # Para otros nodos, usar el ejecutor normal pero con contexto local
                self.interpreter.execute_node(statement)
                
    def _handle_parameter_assignment(self, node):
        """Maneja la asignación de parámetros dentro de la función"""
        param_name = node["name"]
        value_node = node.get("value", {})
        
        # Evaluar el valor a asignar
        if "operation" in value_node:
            operation_node = value_node["operation"]
            expression_str = operation_node.get("value") if isinstance(operation_node, dict) else operation_node
            final_value = self.interpreter.resolve_expression(expression_str)
        else:
            raw_value = value_node.get("value")
            final_value = raw_value
            
        # Validar tipo si el parámetro está tipado
        function_params = self.interpreter.symbol_table.get_function_params(self.function_name)
        if param_name in function_params and function_params[param_name] != "any":
            expected_type = function_params[param_name]
            actual_type = self._get_type_name(final_value)
            
            if expected_type != actual_type:
                raise InvalidOperationError(
                    f"Error de tipo en asignación de parámetro '{param_name}': "
                    f"se esperaba '{expected_type}', se recibió '{actual_type}'"
                )
        
        # Asignar el valor al parámetro en el contexto local
        self.set_parameter_value(param_name, final_value)
        self.interpreter._log(f"  Asignado parámetro '{param_name}': {final_value}")
# ==============================================================================
# OOP — Contexto de ejecución de métodos
# ==============================================================================
class MethodContext:
    """Equivalente a FunctionContext pero para métodos de clase con acceso a 'this'."""
    def __init__(self, interpreter, method_info: dict,
                 instance: ClassInstance, class_origin: str, parameters: list):
        self.interpreter  = interpreter
        self.method_info  = method_info    # {node, params, modifier, is_async}
        self.instance     = instance
        self.class_origin = class_origin
        self.parameters   = parameters

    def execute(self):
        interp      = self.interpreter
        method_node = self.method_info['node']
        method_name = method_node.get('name', '<método>')
        func_params = self.method_info.get('params', {})
        frame_key   = f"{self.class_origin}.{method_name}"

        interp._log(f"[OOP] -> Método '{method_name}' en '{self.class_origin}' args={self.parameters}")

        # Guardar contexto previo
        old_function = interp._current_function
        old_instance = interp._current_instance

        interp._current_function = frame_key
        interp._current_instance = self.instance

        interp.symbol_table.push_function_frame(frame_key)
        interp.symbol_table.push_scope(label=f"Método '{method_name}'")

        # Asignar parámetros
        param_names = list(func_params.keys())
        for i, pname in enumerate(param_names):
            if i < len(self.parameters):
                interp.symbol_table.declare_function_param_value(
                    frame_key, pname, self.parameters[i]
                )
                interp._log(f"[OOP]   param '{pname}' = {self.parameters[i]}")

        old_break  = interp.break_flag
        old_ret    = interp.return_flag
        old_retval = interp.return_value
        interp.return_flag  = False
        interp.return_value = None
        result = None

        block = method_node.get('block', [])
        if isinstance(block, list):
            for stmt in block:
                if interp.break_flag or interp.return_flag:
                    break
                interp.execute_node(stmt)
                if interp.return_flag:
                    result = interp.return_value
                    break

        # Restaurar contexto
        interp.break_flag        = old_break
        interp.return_flag       = old_ret
        interp.return_value      = old_retval
        interp._current_function = old_function
        interp._current_instance = old_instance
        interp.symbol_table.pop_scope(label=f"Método '{method_name}'")
        interp.symbol_table.pop_function_frame(frame_key)

        interp._log(f"[OOP] <- Método '{method_name}' resultado={result}")
        return result
debug_mode_g = False

# ==============================================================================
# Sistema de carga de archivos fuente (.tss)
# ==============================================================================

class SourceFunctionWrapper:
    """
    Envuelve una función declarada en un módulo fuente (.tss) para que exponga
    la misma interfaz .call(args, caller_interpreter) que usan los módulos nativos.
    """
    def __init__(self, func_name: str, proxy: 'SourceModuleProxy'):
        self.func_name = func_name
        self.proxy     = proxy

    def call(self, args, caller_interpreter):
        iso = self.proxy._isolated_interpreter
        ctx = FunctionContext(iso, self.func_name, args)
        return ctx.execute_function()


class SourceModuleProxy:
    """
    Envuelve un Interpreter aislado (que ejecutó un archivo .tss) y expone
    sus símbolos con la misma interfaz que usa el ModuleLoader nativo.
    """
    def __init__(self, isolated_interpreter: 'Interpreter', module_name: str):
        self._isolated_interpreter = isolated_interpreter
        self._module_name          = module_name
        # alias_name → original_name
        self._aliases: dict = {}

    # ── aliases ────────────────────────────────────────────────────────────
    def apply_member_alias(self, original: str, alias: str):
        self._aliases[alias] = original

    def _real_name(self, name: str) -> str:
        return self._aliases.get(name, name)

    # ── acceso a funciones ─────────────────────────────────────────────────
    def get_function(self, func_name: str) -> SourceFunctionWrapper:
        real = self._real_name(func_name)
        iso  = self._isolated_interpreter
        try:
            iso.symbol_table.get_function(real)
        except UndeclaredVariableError:
            raise ModuleError(
                f"La función '{real}' no existe en el módulo fuente '{self._module_name}'."
            )
        return SourceFunctionWrapper(real, self)

    # ── acceso a variables / constantes ────────────────────────────────────
    def get_export(self, var_name: str):
        real = self._real_name(var_name)
        iso  = self._isolated_interpreter
        try:
            return iso.symbol_table.get_value(real)
        except UndeclaredVariableError:
            raise ModuleError(
                f"La variable '{real}' no existe en el módulo fuente '{self._module_name}'."
            )

    def has_function(self, name: str) -> bool:
        try:
            self._isolated_interpreter.symbol_table.get_function(self._real_name(name))
            return True
        except UndeclaredVariableError:
            return False

    def has_export(self, name: str) -> bool:
        try:
            self._isolated_interpreter.symbol_table.get_value(self._real_name(name))
            return True
        except UndeclaredVariableError:
            return False

    def all_symbols(self) -> dict:
        """Devuelve todas las variables del scope global del módulo."""
        iso = self._isolated_interpreter
        result = {}
        if iso.symbol_table.symbols:
            for name, sym in iso.symbol_table.symbols[0].items():
                result[name] = sym.value
        return result

    def all_functions(self) -> list:
        return list(self._isolated_interpreter.symbol_table.function_symbols.keys())


class Interpreter:
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode or debug_mode_g
        self.symbol_table = SymbolTable()
        self.symbol_table._debug_mode = self.debug_mode
        self.break_flag = False
        self.return_flag = False
        self.return_value = None
        self.switch_fall_through = False
        self._current_function = None
        self._current_instance: 'ClassInstance | None' = None   # contexto OOP
        self._path_stack = []
        self.module_loader = ModuleLoader(debug=self.debug_mode)
        self._source_modules: dict = {}
        self._base_dir: str = ""
        # ── OOP ──────────────────────────────────────────────────────────────
        self.object_table = ObjectSymbolTable()
        self.struct_table = StructSymbolTable()   # ← tabla dedicada a structs
        self._main_function = None               # ← función marcada como punto de entrada
        self._async_functions: set = set()     # nombres de funciones async
        # ── Event Loop (para UI / async) ──────────────────────────────────────
        self._event_loop: 'asyncio.AbstractEventLoop | None' = None
        self._async_tasks: list = []
        self._setup_source_module_hooks()
    
    def _register_native_classes(self, module_name: str):
     """
     Registra en self.object_table las clases nativas que el ModuleLoader
     haya cargado desde el módulo 'module_name'.
     """
     ml = self.module_loader
     # Intenta obtener las clases del módulo. Se asume que ModuleLoader tiene
     # un método get_classes(module_name) que devuelve dict {nombre: ClassDefinition}
     if hasattr(ml, 'get_classes'):
        classes = ml.get_classes(module_name)
        for class_name, class_def in classes.items():
            if not self.object_table.has_class(class_name):
                self.object_table.declare_class(class_name, class_def)
                self._log(f"[OOP] Clase nativa '{class_name}' registrada desde módulo '{module_name}'")
     else:
        # Fallback: si no existe get_classes, intenta acceder a un atributo interno común
        # (ajusta según la implementación real de ModuleLoader)
        if hasattr(ml, '_native_classes') and module_name in ml._native_classes:
            for class_name, class_def in ml._native_classes[module_name].items():
                if not self.object_table.has_class(class_name):
                    self.object_table.declare_class(class_name, class_def)
                    self._log(f"[OOP] Clase nativa '{class_name}' registrada (fallback)") 
    def _setup_source_module_hooks(self):
        """
        Extiende el ModuleLoader nativo para que también consulte _source_modules
        de forma transparente, sin modificar module_loader.py.
        """
        interp              = self
        ml                  = self.module_loader
        _orig_is_loaded     = ml.is_loaded
        _orig_get_function  = ml.get_function
        _orig_get_export    = ml.get_export_value

        def _is_loaded(name):
            return _orig_is_loaded(name) or name in interp._source_modules

        def _get_function(mod_name, func_name):
            if mod_name in interp._source_modules:
                return interp._source_modules[mod_name].get_function(func_name)
            return _orig_get_function(mod_name, func_name)

        def _get_export_value(mod_name, var_name):
            if mod_name in interp._source_modules:
                return interp._source_modules[mod_name].get_export(var_name)
            return _orig_get_export(mod_name, var_name)

        ml.is_loaded        = _is_loaded
        ml.get_function     = _get_function
        ml.get_export_value = _get_export_value

    def _log(self, message):
        """Función interna para imprimir mensajes solo si el modo debug está activo."""
        if self.debug_mode:
            print(message)        
    def interpret(self, ast, source_path: str = ""):
        
     import native_registry
     native_registry._current_interpreter = self
     # Actualizar directorio base para resolver rutas relativas en imports
     if source_path:
         self._base_dir = os.path.dirname(os.path.abspath(source_path))
         base_dir = os.path.dirname(os.path.abspath(source_path))
         self._path_stack.append(base_dir)
     elif not self._base_dir:
         self._base_dir = os.getcwd()
     if "Program" not in ast:
        raise InterpreterError("El AST debe tener un nodo raíz 'Program'.")

     program_nodes = ast["Program"]
     i = 0
     while i < len(program_nodes):
        node = program_nodes[i]
        node_type = list(node.keys())[0]

        # Lógica especial para el WhileLoop
        if node_type == "WhileLoop":
            # Asumimos que el siguiente nodo es el bloque del bucle
            if i + 1 < len(program_nodes) and "Block" in program_nodes[i + 1]:
                while_node_content = node["WhileLoop"]
                block_node_content = program_nodes[i + 1]["Block"]
                
                # Le pasamos el bloque directamente al manejador
                self.handle_WhileLoop(while_node_content, block_node_content)
                
                i += 2 # Saltamos el WhileLoop y su Bloque ya procesados
                continue
            else:
                # Si no hay bloque, lo ejecutamos sin cuerpo y avanzamos
                self.handle_WhileLoop(node["WhileLoop"], None) 
                i += 1
        elif node_type == "SwitchStatement":
            # Asumimos que el siguiente nodo es el bloque del bucle
            if i + 1 < len(program_nodes) and "block" in program_nodes[i + 1]:
                switch_node_content = node["SwitchStatement"]
                block_node_content = program_nodes[i + 1]["block"]
                
                # Inyectamos el bloque en el nodo para que el handler lo reciba
                switch_node_content["block"] = block_node_content
                
                self.handle_SwitchStatement(switch_node_content)
                
                i += 2 # Saltamos el SwitchStatement y su Bloque ya procesados
                continue
            else:
                # Un switch sin bloque no se puede ejecutar
                self.handle_SwitchStatement(node["SwitchStatement"]) 
                i += 1
        # Para todos los demás nodos, el comportamiento es el normal
        else:
            self.execute_node(node)
            i += 1

     if source_path and self._path_stack:
         self._path_stack.pop()

     # ── Punto de entrada ->main: llamar tras registrar todo ───────────────
     if self._main_function:
         self._log(f"[MAIN] Ejecutando punto de entrada: '{self._main_function}'")
         try:
             ctx = FunctionContext(self, self._main_function, {})
             ctx.execute_function()
         except Exception as e:
             raise InterpreterError(
                 f"[MAIN] Error en función de entrada '{self._main_function}': {e}")

    def execute_node(self, node):
        if not node: return
        node_type = list(node.keys())[0]
        self._log(f"DEBUG: node_type = '{node_type}'")
        # Normalizar variantes camelCase de increment/decrement
        _REMAP = {
            'postIncrementStatement': 'PostIncrementStatement',
            'postDecrementStatement': 'PostDecrementStatement',
            'preIncrementStatement':  'PreIncrementStatement',
            'preDecrementStatement':  'PreDecrementStatement',
        }
        lookup = _REMAP.get(node_type, node_type)
        handler = getattr(self, f"handle_{lookup}", self.handle_unknown)
        return handler(node[node_type])

    # ==========================================================================
    # ¡CORRECCIÓN 1: Manejo de claves inconsistentes en el AST!
    # ==========================================================================
    def execute_block(self, block_node):
     if not isinstance(block_node, dict):
        return

     items = list(block_node.items())
     i = 0
     while i < len(items):
        if self.break_flag: return

        key, content = items[i]
        
        # Nodos que tienen su bloque como hermano en el AST y necesitan ser reparados
        NODES_TO_REPAIR = {"if_Condition", "forLoop", "whileLoop", "performWhileLoop"}

        if key in NODES_TO_REPAIR:
            # Mira hacia adelante para ver si el siguiente nodo es el bloque que le corresponde
            if i + 1 < len(items) and items[i + 1][0] == "block":
                # ¡Esta es la corrección! Inyecta el bloque en el nodo actual.
                content["block"] = items[i + 1][1]
                i += 1 # Incrementa el índice para saltar el nodo 'block' ya procesado
            
            # Ahora, ejecuta el nodo ya reparado
            node_type = key[0].upper() + key[1:]
            self.execute_node({node_type: content})

        else:
            # Lógica para todos los demás nodos que no necesitan reparación
            EXECUTABLE_KEYS = {
                "variableDeclaration", "variableAsignement", "callExpression",
                "switchStatement", "function", "functionCall", "parameterAsignement",
                "postIncrementStatement", "postDecrementStatement",
                "preIncrementStatement", "preDecrementStatement", "tryCatch", "throw", "newObject",
            "classDeclaration", "interfaceDeclaration",
            "thisAccess", "thisCall", "thisAssignment",
            "superAccess", "superCall", "superAssignment", "superConstructorCall",
            "methodDeclaration", "attributeDeclaration",
            "attributeConstantDeclaration", "constantAttributeDeclaration"
            }
            if key in EXECUTABLE_KEYS:
                node_type = key[0].upper() + key[1:]
                if isinstance(content, list):
                    for item in content:
                        if self.break_flag: break
                        self.execute_node({node_type: item})
                else:
                    self.execute_node({node_type: content})
        i += 1
    def handle_ArrayAccess(self, node):
     """Maneja acceso a arrays como d[i]"""
     array_name = node.get("array")
     index = node.get("index")
    
     try:
        array_value = self.symbol_table.get_value(array_name)
        index_value = self.symbol_table.get_value(index)
        
        # Convertir string de array a lista Python
        if isinstance(array_value, str) and array_value.startswith('[') and array_value.endswith(']'):
            try:
                array_list = json.loads(array_value.replace("'", '"'))
                if isinstance(array_list, list) and 0 <= index_value < len(array_list):
                    return array_list[index_value]
            except:
                pass
        
        return f"<Error: No se puede acceder a {array_name}[{index_value}]>"
     except UndeclaredVariableError:
        return f"<Error: Variable no definida>"    
    def _evaluate_array_access(self, array_expression):
        """
        Evalúa accesos indexados simples y profundos sobre arrays, tuplas, dicts,
        campos de struct, y variables normales.

        Sintaxis:
          variable[i]           → acceso simple
          variable[i:j]         → acceso profundo nivel 2
          variable[i:j:k]       → acceso profundo nivel 3
          p1.field[i]           → acceso sobre campo de struct
          p1.field[i:j]         → acceso profundo sobre campo de struct

        Índices permitidos:
          - Entero literal      0, 1, 42
          - String literal      "clave", 'clave'
          - Variable            i, j, k
          (Para dicts se puede usar entero como posición O string como clave.)
        """
        self._log(f"  [INDEX] Evaluando acceso: {array_expression!r}")

        # ── 1. Separar nombre base y contenido del bracket ────────────────────
        # Soporta: var[…], var.field[…], p1.dir.campo[…]
        bracket_match = re.match(r'^([\w.]+)\[(.+)\]$', array_expression, re.DOTALL)
        if not bracket_match:
            return f"<Error: Sintaxis inválida: {array_expression!r}>"

        base_expr = bracket_match.group(1).strip()     # "arr" / "p1.hobbies"
        raw_index_str = bracket_match.group(2).strip() # "0" / "0:1" / '"clave"'

        # ── 2. Resolver el valor base ─────────────────────────────────────────
        try:
            if '.' in base_expr:
                # Puede ser struct.field o módulo.var
                root = base_expr.split('.')[0]
                rest = '.'.join(base_expr.split('.')[1:])
                try:
                    root_val = self.symbol_table.get_value(root)
                    if isinstance(root_val, StructInstance):
                        current_structure = self._get_struct_field_by_path(root_val, rest)
                    else:
                        current_structure = self.resolve_expression(base_expr)
                except UndeclaredVariableError:
                    current_structure = self.resolve_expression(base_expr)
            else:
                current_structure = self.symbol_table.get_value(base_expr)
        except UndeclaredVariableError:
            return f"<Error: Variable base '{base_expr}' no existe>"

        # JSON-string fallback
        if isinstance(current_structure, str):
            stripped = current_structure.strip()
            if (stripped.startswith('[') and stripped.endswith(']')) or \
               (stripped.startswith('{') and stripped.endswith('}')):
                try:
                    current_structure = json.loads(stripped.replace("'", '"'))
                except Exception:
                    return f"<Error: Estructura corrupta en '{base_expr}'>"

        # ── 3. Dividir índices por ':' (respetando strings y brackets) ────────
        indices_list = self._split_index_parts(raw_index_str)
        self._log(f"  [INDEX] Índices: {indices_list}")

        # ── 4. Navegar nivel a nivel ──────────────────────────────────────────
        for level, raw_index in enumerate(indices_list):
            raw_index = raw_index.strip()

            # ── Resolver el índice (maneja strings, ints, vars, x[0], rangos) ──
            try:
                index_value = self._resolve_index_value(raw_index)
            except InterpreterError as e:
                return f"<Error: {e}>"

            # ── Si el índice es un RangeValue → retornar slice ────────────────
            if isinstance(index_value, RangeValue):
                result = self._apply_range_to_structure(index_value, current_structure)
                if isinstance(result, str) and result.startswith('<Error'):
                    return result
                if level < len(indices_list) - 1:
                    current_structure = result
                    continue
                return result

            self._log(f"  [INDEX] nivel {level}: índice={index_value!r} sobre {type(current_structure).__name__}")

            # Validar que la estructura es indexable
            if not isinstance(current_structure, (list, tuple, dict)):
                return (f"<Error: El valor en nivel {level} es de tipo "
                        f"'{type(current_structure).__name__}' y no es indexable>")

            # Navegar
            try:
                if isinstance(current_structure, dict):
                    # Dict: primero por clave directa, luego por posición
                    if index_value in current_structure:
                        current_structure = current_structure[index_value]
                    elif isinstance(index_value, int):
                        keys = list(current_structure.keys())
                        if 0 <= index_value < len(keys):
                            current_structure = current_structure[keys[index_value]]
                        else:
                            return (f"<Error: Índice posicional {index_value} fuera de "
                                    f"límites del dict (0..{len(keys)-1})>")
                    else:
                        return f"<Error: Clave '{index_value}' no existe en el dict>"

                elif isinstance(current_structure, (list, tuple)):
                    # Array / Tupla: necesita entero
                    if not isinstance(index_value, int):
                        try:
                            index_value = int(index_value)
                        except (TypeError, ValueError):
                            return (f"<Error: Array/tupla requiere índice entero, "
                                    f"se recibió '{index_value}'>")
                    length = len(current_structure)
                    # Soporte de índice negativo (Python-style)
                    if -length <= index_value < length:
                        current_structure = current_structure[index_value]
                    else:
                        return (f"<Error: Índice {index_value} fuera de límites "
                                f"(0..{length-1})>")
            except Exception as e:
                return f"<Error interno en nivel {level}: {e}>"

        self._log(f"  [INDEX] Resultado: {current_structure!r}")
        return current_structure

    def _apply_range_to_structure(self, rng: 'RangeValue', structure) -> object:
        """
        Aplica un RangeValue como índice posicional sobre array, tupla o dict.
        Devuelve el mismo tipo de contenedor que la entrada:
          list  → list   (corchetes)
          tuple → tuple  (paréntesis)
          dict  → dict   (llaves, preservando claves originales)
        """
        if not isinstance(structure, (list, tuple, dict)):
            return (f"<Error: Acceso por rango no válido sobre tipo "
                    f"'{type(structure).__name__}'>")

        expanded = rng.expand()
        if not expanded:
            # Devolver el contenedor vacío del mismo tipo
            return {} if isinstance(structure, dict) else (
                tuple() if isinstance(structure, tuple) else [])

        for idx in expanded:
            if not isinstance(idx, int):
                return f"<Error: El rango de índices debe ser de enteros, se encontró '{idx}'>"

        length = len(structure)

        if isinstance(structure, dict):
            keys = list(structure.keys())
            result = {}
            for idx in expanded:
                if idx < 0 or idx >= length:
                    return (f"<Error: Índice de rango {idx} fuera de límites del dict "
                            f"(0..{length-1})>")
                k = keys[idx]
                result[k] = structure[k]
            return result

        # list / tuple — misma lógica, distinto contenedor
        items = []
        for idx in expanded:
            if idx < 0 or idx >= length:
                return (f"<Error: Índice de rango {idx} fuera de límites "
                        f"(0..{length-1})>")
            items.append(structure[idx])

        return tuple(items) if isinstance(structure, tuple) else items

    def _resolve_index_value(self, raw_index: str):
        """
        Resuelve un token de índice a su valor Python.
        Maneja todos los casos en orden:
          1. String literal  "clave" / 'clave'  → str
          2. Int literal     -3, 0, 42          → int
          3. Float literal   0.5                → float  (poco común, pero válido para dict keys)
          4. Rango literal   1..5               → RangeValue  (para arr[1..3])
          5. Acceso indexado x[0], arr[1:2]     → valor del sub-acceso
          6. Variable simple x, i, j            → symbol_table lookup
          7. Expresión general                  → resolve_expression
        """
        raw = raw_index.strip()

        # 1. String literal
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw[1:-1]

        # 2. Int literal (incluyendo negativo)
        if re.fullmatch(r'-?\d+', raw):
            return int(raw)

        # 3. Float literal
        if re.fullmatch(r'-?\d+\.\d+', raw):
            return float(raw)

        # 4. Rango literal
        if '..' in raw:
            rng = self._try_parse_range(raw)
            if rng is not None:
                return rng

        # 5. Acceso indexado sobre otra variable: x[0], arr[1:2], p1.tags[0]
        if re.search(r'\[', raw):
            return self._evaluate_array_access(raw)

        # 6. Variable simple → symbol_table
        if re.fullmatch(r'[A-Za-z_]\w*', raw):
            try:
                return self.symbol_table.get_value(raw)
            except UndeclaredVariableError:
                raise InterpreterError(
                    f"Variable índice '{raw}' no declarada")

        # 7. Expresión general
        try:
            return self.resolve_expression(raw)
        except Exception as e:
            raise InterpreterError(
                f"No se pudo resolver el índice '{raw}': {e}")
        """
        Aplica acceso indexado (simple o profundo) directamente sobre un valor Python,
        sin buscarlo en la tabla de símbolos.
        """
        indices_list = self._split_index_parts(raw_index_str)
        current = value

        for level, raw_index in enumerate(indices_list):
            raw_index = raw_index.strip()

            try:
                index_value = self._resolve_index_value(raw_index)
            except InterpreterError as e:
                return f"<Error: {e}>"

            # Si el índice es un RangeValue → retornar slice
            if isinstance(index_value, RangeValue):
                result = self._apply_range_to_structure(index_value, current)
                if isinstance(result, str) and result.startswith('<Error'):
                    return result
                if level < len(indices_list) - 1:
                    current = result
                    continue
                return result

            if not isinstance(current, (list, tuple, dict)):
                return (f"<Error: '{label}' nivel {level} es de tipo "
                        f"'{type(current).__name__}' y no es indexable>")
            try:
                if isinstance(current, dict):
                    if index_value in current:
                        current = current[index_value]
                    elif isinstance(index_value, int):
                        keys = list(current.keys())
                        if 0 <= index_value < len(keys):
                            current = current[keys[index_value]]
                        else:
                            return f"<Error: Índice {index_value} fuera de límites del dict>"
                    else:
                        return f"<Error: Clave '{index_value}' no existe en dict>"
                else:
                    if not isinstance(index_value, int):
                        try:
                            index_value = int(index_value)
                        except (TypeError, ValueError):
                            return f"<Error: Índice debe ser entero para array/tupla>"
                    length = len(current)
                    if -length <= index_value < length:
                        current = current[index_value]
                    else:
                        return f"<Error: Índice {index_value} fuera de límites (0..{length-1})>"
            except Exception as e:
                return f"<Error interno nivel {level}: {e}>"

        return current

    def _split_index_parts(self, raw: str) -> list:
        """
        Divide 'a:b:c' por ':' respetando strings y brackets anidados.
        '0:"clave":2'  → ['0', '"clave"', '2']
        '"key":0'      → ['"key"', '0']
        """
        parts, buf, depth, in_str, str_char = [], [], 0, False, '"'
        i = 0
        while i < len(raw):
            ch = raw[i]
            if in_str:
                buf.append(ch)
                if ch == str_char and (i == 0 or raw[i-1] != '\\'):
                    in_str = False
            elif ch in ('"', "'"):
                in_str = True; str_char = ch; buf.append(ch)
            elif ch in ('(', '[', '{'):
                depth += 1; buf.append(ch)
            elif ch in (')', ']', '}'):
                depth -= 1; buf.append(ch)
            elif ch == ':' and depth == 0:
                parts.append(''.join(buf).strip()); buf = []
            else:
                buf.append(ch)
            i += 1
        if buf:
            parts.append(''.join(buf).strip())
        return [p for p in parts if p]
    def _resolve_embedded_function_calls(self, expression_str):
        """
        Resuelve llamadas embebidas dentro de una expresión.
        Primero resuelve mod.func() (módulos), luego funciones declaradas.
        Guard de re-entrada: si ya estamos dentro de esta función para la misma
        expresión, devolvemos la expresión tal cual para cortar la recursión.
        """
        # Guard de re-entrada simple con contador de profundidad
        if not hasattr(self, '_embedded_depth'):
            self._embedded_depth = 0
        if self._embedded_depth > 20:
            return expression_str
        self._embedded_depth += 1
        try:
            return self._resolve_embedded_function_calls_impl(expression_str)
        finally:
            self._embedded_depth -= 1

    def _resolve_embedded_function_calls_impl(self, expression_str):
        # Patrón módulo: mod.func(args)  — se resuelve PRIMERO
        mod_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\(([^()]*)\)'

        def replace_mod_call(match):
            mod_name  = match.group(1)
            func_name = match.group(2)
            raw_args  = match.group(3)
            if not self.module_loader.is_loaded(mod_name):
                return match.group(0)
            args = self._parse_call_parameters({"value": raw_args}) if raw_args.strip() else []
            try:
                fn     = self.module_loader.get_function(mod_name, func_name)
                result = fn.call(args, self)
                return str(result)
            except Exception:
                return match.group(0)

        prev = None
        while prev != expression_str:
            prev = expression_str
            expression_str = re.sub(mod_pattern, replace_mod_call, expression_str)
        """Detecta llamadas a función dentro de una expresión y las reemplaza por su valor."""
        
        # Patrón: nombre_funcion(argumentos)
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\(([^()]*)\)'
    
        def replace_call(match):
            full_match = match.group(0)
            func_name = match.group(1)
            # Ignorar palabras que no son funciones del lenguaje
            if func_name in ['if', 'while', 'for', 'perform', 'return', 'print', 'read']:
                return full_match
            # Verificar que existe como función declarada
            try:
                self.symbol_table.get_function(func_name)
            except UndeclaredVariableError:
                return full_match
            # Ejecutar la función y retornar su valor
            result = self._execute_function_call_from_string(full_match)
            return str(result)
    
        # Resolver de adentro hacia afuera (puede haber recursión anidada)
        prev = None
        while prev != expression_str:
            prev = expression_str
            expression_str = re.sub(pattern, replace_call, expression_str)
    
        return expression_str
     
    def evaluate_expression(self, expression_str):
     """
     Evalúa expresiones booleanas y lógicas.
     Reemplaza variables y parámetros por sus valores antes de evaluar.
     """
     # ── NUEVO: resolver mod.func() ANTES de reemplazar variables ──────
     mod_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\(([^()]*)\)'

     def replace_mod(match):
        mod_name  = match.group(1)
        func_name = match.group(2)
        raw_args  = match.group(3)
        if not self.module_loader.is_loaded(mod_name):
            return match.group(0)
        args = self._parse_call_parameters({"value": raw_args}) if raw_args.strip() else []
        try:
            fn = self.module_loader.get_function(mod_name, func_name)
            return str(fn.call(args, self))
        except Exception:
            return match.group(0)

     prev = None
     while prev != expression_str:
        prev = expression_str
        expression_str = re.sub(mod_pattern, replace_mod, expression_str)
     # ===== INICIALIZAR function_params para evitar NameError =====
     expression_str = self._resolve_embedded_function_calls(expression_str)
     function_params = {}
     # ===== BUSCAR EN PARÁMETROS DE FUNCIÓN SI ESTAMOS EN UNA =====
     if hasattr(self, '_current_function') and self._current_function:
        function_params = self.symbol_table.get_function_params(self._current_function)
        
        for param_name in function_params.keys():
            # Buscar el parámetro como palabra completa en la expresión
            if re.search(r'\b' + param_name + r'\b', expression_str):
                try:
                    param_value = self.symbol_table.get_function_param_value(
                        self._current_function, param_name
                    )
                    # Reemplazar solo si el parámetro existe como palabra completa
                    _pv = str(param_value)
                    expression_str = re.sub(r'\b' + re.escape(param_name) + r'\b',
                                            lambda m, s=_pv: s, expression_str)
                    self._log(f"  Reemplazado parámetro '{param_name}': {param_value}")
                except UndeclaredVariableError:
                    pass  # Parámetro sin valor
     # El regex ahora captura también el grupo de argumentos opcionales (\(…\))
     # para que m.group(0) incluya la llamada completa: arr.contains("Dog")
     # y no solo arr.contains — lo que dejaba ("Dog") huérfano en la expresión.
     inst_dot = re.compile(
         r'\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(\((?:[^()]*|\([^()]*\))*\))?'
     )
     def _replace_inst_field(m):
         obj_n     = m.group(1)
         field_n   = m.group(2)
         args_part = m.group(3) or ''          # '("Dog")' o ''
         full_expr = m.group(0)                # 'arr.contains("Dog")' o 'arr.length'
         try:
             obj = self.symbol_table.get_value(obj_n)
             # ── StructInstance field access ──────────────────────────────────
             if isinstance(obj, StructInstance):
                 rest_path = field_n + args_part
                 try:
                     val = self._get_struct_field_by_path(obj, rest_path)
                     if isinstance(val, StructInstance):
                         return val.format_print(f"{obj_n}.{field_n}")
                     return json.dumps(val) if isinstance(val, str) else str(val)
                 except Exception:
                     pass
             if isinstance(obj, ClassInstance):
                 if not args_part:              # acceso a atributo puro
                     try:
                         val = obj.get_attribute(field_n)
                         return json.dumps(val) if isinstance(val, str) else str(val)
                     except Exception:
                         pass
                 # Llamada a método OOP → dejar que _resolve_dot_chain lo maneje
             # Resolver métodos de tipo core (arr.contains("Dog"), arr.length, etc.)
             resolved = self._resolve_dot_chain(full_expr)
             if resolved is not _UNRESOLVED:
                 return json.dumps(resolved) if isinstance(resolved, str) else str(resolved)
         except (UndeclaredVariableError, InterpreterError, Exception):
             pass
         return m.group(0)
     expression_str = inst_dot.sub(_replace_inst_field, expression_str)
     # ===== BUSCAR VARIABLES NORMALES (EXCEPTO PARÁMETROS YA REEMPLAZADOS) =====
     variable_names = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', expression_str)
     value_str = ""
     for var in set(variable_names):
        # Evitar reemplazar palabras reservadas y parámetros ya procesados
        if var not in ['true', 'false', 'and', 'or', 'not'] and var not in function_params.keys():
            try:
                value = self.symbol_table.get_value(var)
                # Si es string, agregar comillas para la evaluación
                if isinstance(value, str):
                    # Si el valor guardado tiene comillas envolventes, quitarlas primero
                        value_str = json.dumps(value)
                else:
                    value_str = str(value)        
                expression_str = re.sub(r'\b' + re.escape(var) + r'\b',
                                lambda m, s=value_str: s, expression_str)
                self._log(f"  Reemplazada variable '{var}': {value}")
            except UndeclaredVariableError: 
                pass  # Variable no declarada, dejar como está
    
     # ===== REEMPLAZAR OPERADORES LÓGICOS DESPUÉS DE LAS VARIABLES =====
     expression_str = expression_str.replace("&&", " and ").replace("||", " or ")
    
     self._log(f"  Evaluando expresión: {expression_str}")
    
     try:
        result = eval(expression_str, {"__builtins__": {}}, {})
        self._log(f"  Resultado: {result}")
        return result
     except Exception as e:
        self._log(f"  Error al evaluar expresión: {e}")
        return False
    
    def _is_function_call(self, expression_str):
     """Detecta si una cadena es una llamada a función del formato NombreFuncion(argv)"""
     pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)$'
     return re.match(pattern, expression_str.strip()) is not None

    def _execute_function_call_from_string(self, function_call_str):
     """Ejecuta una llamada a función desde un string y retorna su resultado"""
     try:
        # Extraer nombre de función y argumentos
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)$', function_call_str.strip())
        if not match:
            raise InvalidOperationError(f"Formato de llamada a función inválido: {function_call_str}")
        
        function_name = match.group(1)
        args_str = match.group(2).strip()
        
        self._log(f"  Ejecutando llamada a función: '{function_name}' con args: '{args_str}'")
        
        # Parsear argumentos
        call_parameters = self._parse_call_parameters({"value": args_str}) if args_str.strip() else []
        
        # Crear contexto y ejecutar función
        function_context = FunctionContext(self, function_name, call_parameters)
        result = function_context.execute_function()
        
        self._log(f"  Resultado de '{function_call_str}': {result}")
        return result
        
     except Exception as e:
        self._log(f"  Error ejecutando función '{function_call_str}': {e}")
        return f"<Error en {function_call_str}>"

    # _parse_call_parameters: definición canónica más abajo (una sola versión unificada)

    def _is_valid_arithmetic_format(self, expression_str):
        """
        Valida que una expresión tenga el formato de una operación aritmética válida
        (ej. lado*2, 2+x, (lado+2)*x) y que contenga al menos una variable.
        Usa expresiones regulares como herramienta principal.
        """
        # 1. Patrones de las piezas (usando expresiones regulares)
        VAR_PATTERN = r'[a-zA-Z_][a-zA-Z0-9_]*'
        NUM_PATTERN = r'\d+\.?\d*'
        OP_PATTERN = r'[+\-*/%]'
        
        # Primero, una comprobación rápida de paréntesis balanceados
        if expression_str.count('(') != expression_str.count(')'):
            return False

        # 2. Tokenización: Convertimos el string en una lista de piezas
        token_pattern = f'({VAR_PATTERN}|{NUM_PATTERN}|{OP_PATTERN}|[()])'
        tokens = re.findall(token_pattern, expression_str.replace(" ", ""))
        if not tokens:
            return False

        # 3. Validación de la secuencia y del requisito de la variable
        has_variable = False
        # Estado esperado: 0 para operando o '(', 1 para operador o ')'
        expected_state = 0 
        paren_level = 0

        for token in tokens:
            if re.fullmatch(VAR_PATTERN, token):
                if expected_state != 0: return False # Error de secuencia
                has_variable = True
                expected_state = 1
            elif re.fullmatch(NUM_PATTERN, token):
                if expected_state != 0: return False # Error de secuencia
                expected_state = 1
            elif re.fullmatch(OP_PATTERN, token):
                if expected_state != 1: return False # Error de secuencia
                expected_state = 0
            elif token == '(':
                if expected_state != 0: return False # Error de secuencia
                paren_level += 1
            elif token == ')':
                if expected_state != 1: return False # Error de secuencia
                paren_level -= 1
            else:
                return False # Token desconocido

            if paren_level < 0: return False # Cierre de paréntesis sin apertura

        # 4. Verificación final
        # Debe terminar esperando un operador y con paréntesis balanceados
        if expected_state == 1 and paren_level == 0 and has_variable:
            return True
        
        return False
    def _evaluate_arithmetic_operation(self, expression_str):
        if not expression_str:
            return
        self._log(f"  Calculando (con jerarquía) la operación: '{expression_str}'")
        self._log(self._current_function)
        if hasattr(self, '_current_function') and self._current_function:
         function_params = self.symbol_table.get_function_params(self._current_function)
        
        # Solo reemplazar si la variable ES un parámetro de la función
         for param_name in function_params.keys():
            # Verificar que el parámetro aparece como palabra completa en la expresión
            if re.search(r'\b' + param_name + r'\b', expression_str):
                try:
                    param_value = self.symbol_table.get_function_param_value(
                        self._current_function, param_name
                    )
                    _pv2 = str(param_value)
                    expression_str = re.sub(r'\b' + re.escape(param_name) + r'\b',
                                            lambda m, s=_pv2: s, expression_str)
                    self._log(f"  Reemplazado parámetro '{param_name}': {param_value}")
                except UndeclaredVariableError:
                    # Si el parámetro no tiene valor, continuar sin reemplazar
                    pass
        
        
        # SEGUNDO: Procesar parámetros de función si estamos en una función           
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d*|\.\d+|\d+|[+\-*/%()]', expression_str)
        resolved_tokens = []

        def _resolve_tok(tok):
            """Devuelve el valor numérico de un token identificador o literal."""
            if re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', tok):
                try:
                    val = self.symbol_table.get_value(tok)
                except UndeclaredVariableError:
                    raise InvalidOperationError(f"Variable '{tok}' no declarada en la operación.")
                if isinstance(val, (int, float)):
                    return val
                if isinstance(val, str):
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        raise InvalidOperationError(
                            f"La variable '{tok}' contiene un string no numérico ('{val}').")
                raise InvalidOperationError(
                    f"La variable '{tok}' es de tipo no numérico ({type(val).__name__}).")
            return float(tok)  # literal

        idx = 0
        while idx < len(tokens):
            tok = tokens[idx]

            if tok == '-':
                # Menos unario: al inicio, o precedido por operador o '('
                prev = tokens[idx - 1] if idx > 0 else None
                is_unary = (prev is None or prev in ('+', '-', '*', '/', '%', '('))
                if is_unary and idx + 1 < len(tokens):
                    idx += 1
                    try:
                        resolved_tokens.append(-_resolve_tok(tokens[idx]))
                    except (ValueError, TypeError):
                        raise InvalidOperationError(
                            f"No se puede negar el token '{tokens[idx]}'.")
                else:
                    resolved_tokens.append('-')

            elif re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', tok):
                resolved_tokens.append(_resolve_tok(tok))

            else:
                try:
                    resolved_tokens.append(float(tok))
                except ValueError:
                    resolved_tokens.append(tok)   # operador o paréntesis

            idx += 1
        values = []
        ops = []
        precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '%': 2}
        def apply_op():
            right_val = values.pop()
            left_val = values.pop()
            op = ops.pop()
            if not isinstance(left_val, (int, float)) or not isinstance(right_val, (int, float)):
                raise InvalidOperationError(f"Operación '{op}' inválida entre tipos no numéricos ({type(left_val).__name__}, {type(right_val).__name__}).")
            if op == '+': values.append(left_val + right_val)
            elif op == '-': values.append(left_val - right_val)
            elif op == '*': values.append(left_val * right_val)
            elif op == '/':
                if right_val == 0: raise InvalidOperationError("División por cero.")
                values.append(left_val / right_val)
            elif op == '%':
                if right_val == 0: raise InvalidOperationError("Módulo por cero.")
                values.append(left_val % right_val)
        for token in resolved_tokens:
            if isinstance(token, (int, float)):
                values.append(token)
            elif token == '(':
                ops.append(token)
            elif token == ')':
                while ops and ops[-1] != '(':
                    apply_op()
                if not ops or ops.pop() != '(':
                    raise InvalidOperationError("Paréntesis no balanceados.")
            else:
                while (ops and ops[-1] != '(' and precedence.get(ops[-1], 0) >= precedence.get(token, 0)):
                    apply_op()
                ops.append(token)
        while ops:
            apply_op()
        if not values: raise InvalidOperationError("Expresión inválida o vacía.")
        result = values[0]
        if result == int(result):
            return int(result)
        return result
    # AÑADIR este método nuevo en el Interpreter:

    def resolve_expression(self, expression_str, _depth=0):
        """
        Resolvedor unificado. Maneja TODOS los casos en orden de prioridad:
          1.  Valor Python no-string               -> devolver tal cual
          2.  Vacio/None                           -> None
          3.  null / NULL / None literal           -> None
          4.  true / false literal                 -> bool
          5.  Entero literal                       -> int
          6.  Decimal literal                      -> float (ANTES del check de punto)
          7.  String literal "..." / '...'         -> str (escapes procesados)
          8.  Array literal [...]                  -> list
          9.  new ClassName(args)                  -> instanciacion OOP
         10.  Expresion con punto (NO float)       -> _resolve_dot_chain
         11.  Llamada a funcion simple name(args)  -> _execute_function_call_from_string
         12.  Identificador simple                 -> param o symbol_table
         13.  Aritmetica pura (sin comparaciones)  -> _evaluate_arithmetic_operation
         14.  Todo lo demas                        -> evaluate_expression

        _depth: protección interna contra recursión infinita.
        """
        # Guard anti-recursión
        if _depth > 80:
            self._log(f"  [WARN] resolve_expression: profundidad {_depth} alcanzada para: {str(expression_str)[:80]!r}")
            return expression_str
        # 1. Valor Python no-string
        if not isinstance(expression_str, str):
            return expression_str

        expr = expression_str.strip()

        # 2. Vacio
        if not expr:
            return None

        # 3. null literal
        if expr in ('null', 'NULL', 'None'):
            return None

        # 3.5. Range literal:  start..end
        #      Debe revisarse antes de intentar float/int para que 1..5 no confunda
        if '..' in expr:
            rng = self._try_parse_range(expr)
            if rng is not None:
                return rng

        # 4. bool literals
        if expr == 'true':  return True
        if expr == 'false': return False

        # 5. Entero literal (incluyendo negativo sin espacios)
        try:
            return int(expr)
        except ValueError:
            pass

        # 6. Decimal literal — ANTES del check de punto para que 3.14 no vaya
        #    a _resolve_dot_chain. Excluir si contiene '..' (rango) o '(' (expresión)
        try:
            if '.' in expr and '..' not in expr and '(' not in expr and ')' not in expr:
                return float(expr)
        except ValueError:
            pass

        # 7. String literal (doble o simple comilla) — solo si no es concatenación
        if ((expr.startswith('"') and expr.endswith('"')) or
                (expr.startswith("'") and expr.endswith("'"))) and \
                ' . ' not in expr:
            inner = expr[1:-1]
            return (inner.replace('\\n', '\n').replace('\\t', '\t')
                         .replace('\\r', '\r').replace('\\"', '"')
                         .replace("\\'", "'").replace('\\\\', '\\'))

        # 8. Array literal [...]
        if expr.startswith('[') and expr.endswith(']'):
            inner = expr[1:-1].strip()
            if not inner:
                return []
            raw_items = [self.resolve_expression(i.strip(), _depth + 1)
                         for i in self._split_args_respecting_brackets(inner)]
            return _expand_collection_items(raw_items)

        # 8.4. (expr).method  — e.g. (0..10).length, (1..5).toarray()
        #      Detectar antes del check de tupla para no confundirlos
        if expr.startswith('(') and ').' in expr:
            # Encontrar el ) que cierra la expresión principal
            close = self._find_matching_close(expr, 0)
            if close is not None and close < len(expr) - 1 and expr[close + 1] == '.':
                inner_expr = expr[1:close]
                tail_chain = expr[close + 2:]   # método(s) tras el punto
                try:
                    inner_val = self.resolve_expression(inner_expr, _depth + 1)
                    if inner_val is not None and tail_chain:
                        val_type = _get_value_type(inner_val)
                        first_m  = tail_chain.split('(')[0]
                        if val_type in _CORE_TYPE_METHODS and \
                                first_m in _CORE_TYPE_METHODS[val_type]:
                            result, _ = self._execute_type_method_chain(
                                inner_expr, tail_chain, inner_val, False)
                            return result
                        # No es un type-method conocido — devolver el valor interior
                        return inner_val
                except Exception:
                    pass  # no es este patrón, seguir

        # 8.5. Tuple literal (val1, val2, ...)
        if expr.startswith('(') and expr.endswith(')'):
            inner = expr[1:-1].strip()
            if inner:
                items = self._split_args_respecting_brackets(inner)
                if len(items) > 1 or inner.endswith(','):
                    try:
                        raw_items = [self.resolve_expression(it.strip(), _depth + 1) for it in items]
                        return tuple(_expand_collection_items(raw_items))
                    except Exception:
                        pass

        # 8.6. Dict literal {...}
        if expr.startswith('{') and expr.endswith('}'):
            inner = expr[1:-1].strip()
            if not inner:
                return {}
            try:
                import ujson as _uj
                return _uj.loads(expr)
            except Exception:
                pass

        # 9.5. Acceso indexado: var[i], var[i:j], p1.field[i], p1.field[i:j]
        #      También soporta encadenado: var[i].type  var[i:j].length()
        idx_match = re.match(r'^([\w]+(?:\.[\w]+)*)\[(.+)\](\.[\w.()]+)?$', expr, re.DOTALL)
        if idx_match:
            base_with_field = idx_match.group(1)
            bracket_content = idx_match.group(2)
            tail_chain      = idx_match.group(3)  # e.g. ".type" o ".length()" o None

            # Verificar que el bracket_content no contiene '[' sin cerrar (evitar falsos positivos)
            # Solo si la base existe como variable o campo de struct
            base_root = base_with_field.split('.')[0]
            base_known = False
            try:
                self.symbol_table.get_value(base_root)
                base_known = True
            except UndeclaredVariableError:
                pass

            if base_known:
                result = self._evaluate_array_access(f"{base_with_field}[{bracket_content}]")
                # Si hay cadena de tipo (.type, .length(), etc.) aplicarla
                if tail_chain:
                    chain = tail_chain[1:]  # quitar el punto inicial
                    val_type = _get_value_type(result)
                    if val_type in _CORE_TYPE_METHODS:
                        first_m = chain.split('(')[0]
                        if first_m in _CORE_TYPE_METHODS[val_type]:
                            result, _ = self._execute_type_method_chain(
                                base_with_field, chain, result, False)
                return result

        # 9. new ClassName(args)
        new_m = re.match(r'^new\s+([A-Za-z_]\w*)\s*\((.*)\)$', expr, re.DOTALL)
        if new_m:
            raw_args = new_m.group(2).strip()
            args = self._parse_call_parameters({'value': raw_args}) if raw_args else []
            return self._instantiate_object(new_m.group(1), args)

        # 10. Expresion con punto (modulo, OOP, tipo core, concatenacion)
        #     Solo si hay punto Y no es decimal ya manejado en paso 6
        if '.' in expr:
            resolved = self._resolve_dot_chain(expr)
            if resolved is not _UNRESOLVED:
                return resolved

        # 11. Llamada a funcion simple name(args)
        if self._is_function_call(expr):
            return self._execute_function_call_from_string(expr)

        # 12. Identificador simple -> param de funcion o symbol_table
        if re.fullmatch(r'[A-Za-z_]\w*', expr):
            if hasattr(self, '_current_function') and self._current_function:
                fps = self.symbol_table.get_function_params(self._current_function)
                if expr in fps:
                    try:
                        return self.symbol_table.get_function_param_value(
                            self._current_function, expr)
                    except UndeclaredVariableError:
                        pass
            try:
                return self.symbol_table.get_value(expr)
            except UndeclaredVariableError:
                pass
            return expr  # identificador desconocido -> devolver como string

        # 13. Resolver llamadas embebidas primero
        expr_w = self._resolve_embedded_function_calls(expr)

        # 14. Aritmetica pura (shunting-yard, sin eval)
        if self._is_valid_arithmetic_format(expr_w):
            return self._evaluate_arithmetic_operation(expr_w)

        # 15. Comparaciones, logica, expresiones complejas -> evaluate_expression
        return self.evaluate_expression(expr_w)
    
    def _resolve_dot_chain(self, expr: str):
     """
     Resuelve cualquier expresión que contenga punto.
     Orden de prioridad estricto:
      1. ModuleInstance.method(args)   — instancia nativa en variable
      2. mod.func(args)                — módulo cargado con función
      3. mod.VAR                       — módulo cargado con export
      4. ClassInstance.field           — atributo de objeto OOP
      5. ClassInstance.method(args)    — método de objeto OOP
      6. var.typeMethod().chain        — interfaz de tipo (CORE)
      7. Concatenación con punto       — último recurso
     """
     expr = expr.strip()

     # ── Detectar la parte izquierda del primer punto ───────────────────────
     # Extraer nombre antes del primer punto fuera de paréntesis
     left = self._extract_left_of_dot(expr)
     # SOLO estas líneas 1610-1612:

     if not left:
        # Verificar si hay una llamada a módulo cargado embebida dentro de la expresión
        # Ej: (-b + math.sqrt(discriminante)) / (2*a)
        mod_embedded = re.search(
            r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', expr)
        if mod_embedded and self.module_loader.is_loaded(mod_embedded.group(1)):
            resolved = self._resolve_embedded_function_calls(expr)
            # Sustituir parámetros de función
            if hasattr(self, '_current_function') and self._current_function:
                for p in self.symbol_table.get_function_params(self._current_function):
                    try:
                        v = self.symbol_table.get_function_param_value(self._current_function, p)
                        _pv3 = str(v)
                        resolved = re.sub(r'\b' + re.escape(p) + r'\b',
                                          lambda m, s=_pv3: s, resolved)
                    except Exception:
                        pass
            # Sustituir variables normales del scope
            for var in set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', resolved)):
                try:
                    v = self.symbol_table.get_value(var)
                    if isinstance(v, (int, float)):
                        _pv4 = str(v)
                        resolved = re.sub(r'\b' + re.escape(var) + r'\b',
                                          lambda m, s=_pv4: s, resolved)
                except Exception:
                    pass
            # eval maneja doble negativo (--3) correctamente, a diferencia del tokenizador
            try:
                result = eval(resolved, {"__builtins__": {}}, {})
                if isinstance(result, float) and result == int(result):
                    return int(result)
                return result
            except Exception:
                pass
        # Sin módulo embebido → es concatenación real, comportamiento original
        # No hay identificador claro a la izquierda → concatenación
        return self._evaluate_concatenated_string(expr)

     rest = expr[len(left) + 1:]  # lo que sigue después del primer punto

     # ── 1. ModuleInstance en variable ─────────────────────────────────────
     try:
        obj = self.symbol_table.get_value(left)
        if isinstance(obj, ModuleInstance):
            # Parsear el método y args del resto
            m = re.match(r'^([A-Za-z_]\w*)\s*\((.*)\)(.*)$', rest, re.DOTALL)
            if m:
                method_name = m.group(1)
                raw_args    = m.group(2)
                tail        = m.group(3).strip()
                args = self._parse_call_parameters({"value": raw_args}) if raw_args.strip() else []
                args = [a.native_obj if isinstance(a, ModuleInstance) else a for a in args]
                result = obj.call_method(method_name, args, self)
                # Si hay más cadena después (.algo) seguir resolviendo
                if tail and tail.startswith('.'):
                    return self._resolve_dot_chain(f"__r__.{tail[1:]}".replace(
                        '__r__', str(result)))
                return result
     except (UndeclaredVariableError, InterpreterError, AttributeError):
        pass

     # ── 2. mod.func(args) — módulo con función ────────────────────────────
     mod_call = re.match(
        r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\((.*)\)$', expr, re.DOTALL)
     if mod_call:
        mod_name, func_name, raw_args = mod_call.groups()
        if self.module_loader.is_loaded(mod_name):
            args = self._parse_call_parameters({"value": raw_args}) if raw_args.strip() else []
            try:
                fn = self.module_loader.get_function(mod_name, func_name)
                return fn.call(args, self)
            except ModuleError as e:
                raise InterpreterError(str(e))

     # ── 3. mod.VAR — módulo con export ────────────────────────────────────
     mod_var = re.match(r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)$', expr)
     if mod_var:
        mod_name, var_name = mod_var.groups()
        if self.module_loader.is_loaded(mod_name):
            try:
                return self.module_loader.get_export_value(mod_name, var_name)
            except ModuleError:
                pass  # no exporta eso — seguir al siguiente caso

     # ── 3.5. StructInstance.field o StructInstance.field.subfield ───────────
     try:
        obj = self.symbol_table.get_value(left)
        if isinstance(obj, StructInstance):
            # Puede ser: "field", "field.subfield", "field[i]", "field[i:j]", "field.sub[i]"
            # Separar la parte de bracket si existe
            bracket_m = re.match(r'^([\w.]+)(\[.+\])(\.[\w.()]+)?$', rest)
            if bracket_m:
                field_path_part  = bracket_m.group(1)
                bracket_part     = bracket_m.group(2)
                tail_part        = bracket_m.group(3)
                # Navegar al campo
                field_val = self._get_struct_field_by_path(obj, field_path_part)
                # Aplicar acceso indexado
                inner_content = bracket_part[1:-1]  # quitar [ ]
                result = self._evaluate_array_access_on_value(
                    field_val, inner_content, f"{left}.{field_path_part}")
                if tail_part:
                    chain = tail_part[1:]
                    val_type = _get_value_type(result)
                    if val_type in _CORE_TYPE_METHODS:
                        result, _ = self._execute_type_method_chain(
                            f"{left}.{field_path_part}", chain, result, False)
                return result
            return self._get_struct_field_by_path(obj, rest)
     except (UndeclaredVariableError, InterpreterError):
        pass

     # ── 4 & 5. ClassInstance.field o ClassInstance.method(args) ───────────
     try:
        obj = self.symbol_table.get_value(left)
        if isinstance(obj, ClassInstance):
            # ¿Es llamada a método?
            m = re.match(r'^([A-Za-z_]\w*)\s*\((.*)\)$', rest, re.DOTALL)
            if m:
                method_name = m.group(1)
                raw_args    = m.group(2)
                args = self._parse_call_parameters({"value": raw_args}) if raw_args.strip() else []
                from interpre import MethodContext
                method_info, origin = self.object_table.lookup_method(
                    obj.class_name, method_name)
                return MethodContext(self, method_info, obj, origin, args).execute()
            # ¿Es acceso a atributo?
            field_m = re.match(r'^([A-Za-z_]\w*)$', rest)
            if field_m:
                return obj.get_attribute(field_m.group(1))
     except (UndeclaredVariableError, InterpreterError):
        pass

     # ── 6. Interfaz de tipo (CORE) ────────────────────────────────────────
     # Solo si el lado izquierdo es una variable con valor conocido
     # y el primer método existe en la tabla del tipo
     try:
        sym          = self.symbol_table.get_symbol(left)
        origin_value = sym.value
        is_const     = sym.is_const
        value_type   = _get_value_type(origin_value)
        first_method = rest.split('(')[0].split('.')[0]

        if first_method in _CORE_TYPE_METHODS.get(value_type, {}):
            result, _ = self._execute_type_method_chain(
                left, rest, origin_value, is_const)
            self._log(f"[TypeMethod] {left}.{rest} = {result}")
            return result
     except (UndeclaredVariableError, InvalidOperationError, AttributeError):
        pass

     # También buscar en parámetros de función
     if hasattr(self, '_current_function') and self._current_function:
        try:
            origin_value = self.symbol_table.get_function_param_value(
                self._current_function, left)
            value_type   = _get_value_type(origin_value)
            first_method = rest.split('(')[0].split('.')[0]
            if first_method in _CORE_TYPE_METHODS.get(value_type, {}):
                result, _ = self._execute_type_method_chain(
                    left, rest, origin_value, False)
                return result
        except (UndeclaredVariableError, InvalidOperationError):
            pass

     # ── 7. Último recurso: concatenación con punto ────────────────────────
     return self._evaluate_concatenated_string(expr)
    
    def _extract_left_of_dot(self, expr: str) -> str:
     """
     Extrae el identificador a la izquierda del primer punto fuera de paréntesis.
     'math.sqrt(x)' → 'math'
     'obj.field'    → 'obj'
     '"hola".upper' → '' (no es identificador)
     """
     m = re.match(r'^([A-Za-z_]\w*)\.', expr)
     if m:
        return m.group(1)
     return ''

    def _resolve_range_value(self, value_str):
     """
     Resuelve un valor que puede ser una variable o un literal.
     Retorna el valor resuelto.
     """
     value_str = value_str.strip()
    
     # Si es un string literal con comillas, quitarlas
     if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    
     # Intentar obtener como variable
     try:
        return self.symbol_table.get_value(value_str)
     except UndeclaredVariableError:
        pass
    
     # Intentar obtener como parámetro de función actual
     if hasattr(self, '_current_function') and self._current_function:
        try:
            return self.symbol_table.get_function_param_value(
                self._current_function, value_str
            )
        except UndeclaredVariableError:
            pass
    
     # Intentar convertir a número
     try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
     except ValueError:
        pass

     # Intentar resolver como expresión compuesta (ej: arr.length, obj.campo, func())
     try:
        resolved = self.resolve_expression(value_str)
        if resolved is not None and not isinstance(resolved, str):
            return resolved
        # Si devolvió un string distinto al original, también es útil
        if isinstance(resolved, str) and resolved != value_str:
            return resolved
     except Exception:
        pass

     # Si no es nada de lo anterior, retornar como string
     return value_str

    def _validate_and_parse_range(self, range_str, for_loop=False):
     """
     Valida y parsea un rango, soportando variables.
    
     Args:
        range_str: String del rango (ej: "1..10", "start..end", "a..z")
        for_loop: Si True, solo permite rangos int (no float ni string)
    
     Returns:
        tuple: (start, end, range_type) donde range_type es 'int', 'float' o 'string'
    
     Raises:
        ValueError: Si el rango no es válido
     """
     if ".." not in range_str:
        raise ValueError(f"Formato de rango inválido: '{range_str}' (debe contener '..')")
    
     parts = range_str.split("..")
     if len(parts) != 2:
        raise ValueError(f"Formato de rango inválido: '{range_str}' (debe tener exactamente dos valores)")
    
     # Resolver los valores (pueden ser variables)
     start_value = self._resolve_range_value(parts[0])
     end_value = self._resolve_range_value(parts[1])
    
     # Determinar el tipo de rango
     start_type = type(start_value).__name__
     end_type = type(end_value).__name__
    
     # VALIDACIÓN 1: Ambos valores deben ser del mismo tipo base
     if isinstance(start_value, (int, float)) and isinstance(end_value, (int, float)):
        # Rango numérico
        if isinstance(start_value, float) or isinstance(end_value, float):
            range_type = 'float'
            start_value = float(start_value)
            end_value = float(end_value)
        else:
            range_type = 'int'
            start_value = int(start_value)
            end_value = int(end_value)
        
        # Validar que start <= end
        if start_value > end_value:
            raise ValueError(f"Rango inválido: el inicio ({start_value}) es mayor que el fin ({end_value})")
    
     elif isinstance(start_value, str) and isinstance(end_value, str):
        # Rango de strings (caracteres)
        range_type = 'string'
        
        # Validar que sean caracteres únicos
        if len(start_value) != 1 or len(end_value) != 1:
            raise ValueError(f"Rango de string inválido: '{start_value}'..'{end_value}' (deben ser caracteres únicos)")
        
        # Validar que start <= end en orden alfabético
        if ord(start_value) > ord(end_value):
            raise ValueError(f"Rango de string inválido: '{start_value}' viene después de '{end_value}' en el alfabeto")
    
     else:
        raise ValueError(f"Rango inválido: tipos incompatibles ({start_type} .. {end_type})")
    
     # VALIDACIÓN 2: Si es para un for loop, solo permitir int
     if for_loop and range_type != 'int':
        raise ValueError(f"Rango inválido para bucle 'for': solo se permiten rangos de enteros (int), no '{range_type}'")
    
     return start_value, end_value, range_type

    def _generate_range_values(self, start, end, range_type):
     """
     Genera los valores de un rango según su tipo.
    
     Returns:
        list: Lista de valores en el rango
     """
     if range_type == 'int':
        return list(range(start, end + 1))
    
     elif range_type == 'float':
        # Rango con paso de 0.1
        values = []
        current = start
        step = 0.1
        
        # Redondear para evitar problemas de precisión
        while round(current, 10) <= round(end, 10):
            values.append(round(current, 1))
            current += step
        
        return values
    
     elif range_type == 'string':
        # Rango de caracteres
        values = []
        for code in range(ord(start), ord(end) + 1):
            values.append(chr(code))
        return values
    
     return [] 
    def handle_VariableDeclaration(self, node):
        name          = node["name"]
        value_node    = node.get("value", {})
        declared_type = value_node.get("explicitType") or 'dynamic'
        ast_type      = value_node.get("type")
        raw_value     = value_node.get("value")

        # ── STRUCT INSTANTIATION ─────────────────────────────────────────────
        # Si el tipo explícito o el tipo AST es una struct conocida, instanciarla
        effective_type = declared_type if declared_type != 'dynamic' else (ast_type or 'dynamic')
        if (effective_type and effective_type not in _NATIVE_TYPES
                and self.struct_table.has_definition(effective_type)):
            struct_def = self.struct_table.get_definition(effective_type)
            self._log(f"[STRUCT:NEW] ──────────────────────────────────────")
            self._log(f"[STRUCT:NEW] Instanciando struct '{effective_type}' → variable '{name}'")
            instance   = StructInstance(effective_type, struct_def, self)
            new_symbol = Symbol(value=instance, declared_type=effective_type)
            self.symbol_table.declare(name, new_symbol)
            self._log(f"[STRUCT:NEW] Instancia #{instance._id} creada y guardada en '{name}'")
            self._log(f"[STRUCT:NEW] ──────────────────────────────────────")
            return
        # ────────────────────────────────────────────────────────────────────

        # Nodo de operacion explicita (operation)
        if "operation" in value_node:
            op_node = value_node["operation"]
            expr_s  = op_node.get("value") if isinstance(op_node, dict) else op_node
            initial_value = self.resolve_expression(str(expr_s) if expr_s is not None else '')

        # NULL explicito
        elif ast_type == "NULL":
            initial_value = None

        # String AST: quitar comillas si las tiene; resolver si tiene operadores
        elif ast_type == "string" and isinstance(raw_value, str):
            needs_resolve = (
                any(op in raw_value for op in ['+', '-', '*', '/', '%', '(', ')']) or
                ('.' in raw_value and not raw_value.replace('.', '', 1).isdigit())
            )
            if needs_resolve:
                initial_value = self.resolve_expression(raw_value)
            elif ((raw_value.startswith('"') and raw_value.endswith('"')) or
                  (raw_value.startswith("'") and raw_value.endswith("'"))):
                initial_value = raw_value[1:-1]
            else:
                initial_value = raw_value

        # Cualquier otro caso: resolve_expression maneja todo
        # (new, modulos, OOP, funciones, variables, literales, aritmetica...)
        else:
            initial_value = self.resolve_expression(raw_value)

        new_symbol = Symbol(value=initial_value, declared_type=declared_type)
        self.symbol_table.declare(name, new_symbol)
        self._log(f"Declarada variable '{name}'. Símbolo: {new_symbol}")
    
    def handle_VariableAsignement(self, node):
        name       = node["name"]
        value_node = node.get("value", {})
        ast_type   = value_node.get("type")
        raw_value  = value_node.get("value")

        # Asignacion de atributo OOP: obj.campo = valor
        if isinstance(name, str) and '.' in name:
            parts = name.split('.', 1)
            obj_name, field = parts
            try:
                obj = self.symbol_table.get_value(obj_name)
                if isinstance(obj, ClassInstance):
                    final_value = self._resolve_assignment_value(value_node)
                    obj.set_attribute(field, final_value)
                    self._log(f"[OOP] {obj_name}.{field} = {final_value}")
                    return
            except UndeclaredVariableError:
                pass

        # Nodo de operacion explicita
        if "operation" in value_node:
            op_node = value_node["operation"]
            expr_s  = op_node.get("value") if isinstance(op_node, dict) else op_node
            final_value = self.resolve_expression(str(expr_s) if expr_s is not None else '')

        # NULL explicito
        elif ast_type == "NULL":
            final_value = None

        # String AST
        elif ast_type == "string" and isinstance(raw_value, str):
            needs_resolve = (
                any(op in raw_value for op in ['+', '-', '*', '/', '%', '(', ')']) or
                ('.' in raw_value and not raw_value.replace('.', '', 1).isdigit())
            )
            if needs_resolve:
                final_value = self.resolve_expression(raw_value)
            elif ((raw_value.startswith('"') and raw_value.endswith('"')) or
                  (raw_value.startswith("'") and raw_value.endswith("'"))):
                final_value = raw_value[1:-1]
            else:
                final_value = raw_value

        # Cualquier otro caso
        else:
            final_value = self.resolve_expression(raw_value)

        self.symbol_table.set_value(name, final_value)
        self._log(f"Asignado nuevo valor a '{name}': {final_value}")
    # ==========================================================================
    # ¡CORRECCIÓN 2: Impresión inteligente de variables!
    # ==========================================================================
    def _resolve_assignment_value(self, value_node: dict):
        """Resuelve el valor de cualquier asignación (helper compartido)."""
        if "operation" in value_node:
            op = value_node["operation"]
            expr = op.get("value") if isinstance(op, dict) else op
            return self.resolve_expression(expr)
        raw  = value_node.get("value")
        atype = value_node.get("type")
        if isinstance(raw, str) and self._is_function_call(raw):
            return self._execute_function_call_from_string(raw)
        if isinstance(raw, str) and not (raw.startswith('"') and raw.endswith('"')):
            try:
                return self.resolve_expression(raw)
            except:
                return raw
        return raw
    def handle_ConstantDeclaration(self, node):
        name          = node["name"]
        value_node    = node.get("value", {})
        declared_type = value_node.get("explicitType") or 'dynamic'
        ast_type      = value_node.get("type")
        raw_value     = value_node.get("value")

        # Nodo de operacion explicita
        if "operation" in value_node:
            op_node = value_node["operation"]
            expr_s  = op_node.get("value") if isinstance(op_node, dict) else op_node
            initial_value = self.resolve_expression(str(expr_s) if expr_s is not None else '')

        # NULL explicito
        elif ast_type == "NULL":
            initial_value = None

        # String AST
        elif ast_type == "string" and isinstance(raw_value, str):
            needs_resolve = (
                any(op in raw_value for op in ['+', '-', '*', '/', '%', '(', ')']) or
                ('.' in raw_value and not raw_value.replace('.', '', 1).isdigit())
            )
            if needs_resolve:
                initial_value = self.resolve_expression(raw_value)
            elif ((raw_value.startswith('"') and raw_value.endswith('"')) or
                  (raw_value.startswith("'") and raw_value.endswith("'"))):
                initial_value = raw_value[1:-1]
            else:
                initial_value = raw_value

        # Cualquier otro caso
        else:
            initial_value = self.resolve_expression(raw_value)

        new_symbol = Symbol(value=initial_value, declared_type=declared_type, is_const=True)
        self.symbol_table.declare(name, new_symbol)
        self._log(f"Declarada constante '{name}'. Símbolo: {new_symbol}")

    # ==========================================================================
    # STRUCT — Declaración y Asignación de Módulo
    # ==========================================================================
    def handle_StructDeclaration(self, node):
        """Registra un struct en la tabla de structs."""
        struct_name = node["name"]
        block       = node.get("block", [])
        struct_def  = StructDefinition(struct_name)

        for member in block:
            if not isinstance(member, dict):
                continue
            node_type = list(member.keys())[0]
            content   = member[node_type]
            is_const  = node_type == "ConstantDeclarationStruct"

            field_name = content["name"]
            value_node = content.get("value", {})

            # Tipo declarado (explícito o inferido del AST)
            declared_type = (value_node.get("explicitType")
                             or value_node.get("type")
                             or "dynamic")
            if declared_type in ("NULL", "null"):
                declared_type = "dynamic"
            declared_type = declared_type.lower() if isinstance(declared_type, str) else "dynamic"

            # Límite de colección [N] — puede estar en content o dentro de value_node
            limit_node = content.get("limit") or value_node.get("limit")
            limit = (limit_node.get("value")
                     if isinstance(limit_node, dict)
                     else limit_node)

            # Es dinámica (sin tipo explícito fijo)
            din_node   = value_node.get("dinamic")
            is_dynamic = (din_node.get("value") if isinstance(din_node, dict) else True)
            if is_dynamic is None:
                is_dynamic = True

            # Valor inicial
            raw_v    = value_node.get("value")
            ast_type = value_node.get("type", "")
            if ast_type in ("NULL", "null") or raw_v in (None, "null"):
                initial_value = None
            elif raw_v == "[]":
                initial_value = []
            elif raw_v == "{}":
                initial_value = {}
            elif isinstance(raw_v, bool):
                initial_value = raw_v
            elif isinstance(raw_v, (int, float)):
                initial_value = raw_v
            elif isinstance(raw_v, str) and raw_v.startswith('[') and raw_v.endswith(']'):
                try:
                    initial_value = self.resolve_expression(raw_v)
                except Exception:
                    initial_value = []
            else:
                initial_value = None

            fdef = StructFieldDef(
                name          = field_name,
                declared_type = declared_type,
                is_const      = is_const,
                initial_value = initial_value,
                limit         = limit,
                is_dynamic    = is_dynamic,
            )
            struct_def.add_field(fdef)

        self.struct_table.declare(struct_name, struct_def)
        field_count = len(struct_def.fields)
        self._log(f"[STRUCT:DEF] ══════════════════════════════════════")
        self._log(f"[STRUCT:DEF] Struct '{struct_name}' registrada ({field_count} campo(s)):")
        for fname, fdef in struct_def.fields.items():
            mod  = "const " if fdef.is_const else ""
            lim  = f"[{fdef.limit}]" if fdef.limit is not None else ""
            dyn  = " (dinámico)" if fdef.is_dynamic else ""
            self._log(f"[STRUCT:DEF]   {mod}{fdef.declared_type}{lim} {fname}"
                      f" = {fdef.initial_value!r}{dyn}")
        self._log(f"[STRUCT:DEF] ══════════════════════════════════════")

    def handle_ModuleAsignement(self, node):
        """
        Maneja asignaciones con punto: p1.name = "Ana", p1.dir.calle = "Madrid".
        Aplica las reglas de tipado y límite de cada campo de la struct.
        """
        full_name  = node["name"]   # e.g. "p1.name" o "p1.dir.calle"
        value_node = node.get("value", {})
        longitud_node = node.get("longitud")

        parts     = full_name.split(".")
        root_name = parts[0]
        field_path = parts[1:]  # ["name"] o ["dir", "calle"]

        if not field_path:
            raise InterpreterError(
                f"ModuleAsignement: '{full_name}' no contiene un campo de acceso.")

        # ── Resolver el valor a asignar ───────────────────────────────────────
        ast_type  = value_node.get("type", "")
        raw_value = value_node.get("value", "")
        final_value = self._resolve_struct_assignment_value(value_node, ast_type, raw_value)

        # ── Obtener la variable raíz ─────────────────────────────────────────
        try:
            root_val = self.symbol_table.get_value(root_name)
        except UndeclaredVariableError:
            raise InterpreterError(
                f"[Struct] Variable '{root_name}' no declarada.")

        if not isinstance(root_val, StructInstance):
            # Fallback: podría ser una clase OOP u otro objeto
            # Delegar al manejador OOP existente
            try:
                sym = self.symbol_table.get_symbol(root_name)
                if isinstance(sym.value, ClassInstance):
                    self._oop_set_field(sym.value, field_path, final_value)
                    return
            except Exception:
                pass
            raise InterpreterError(
                f"[Struct] '{root_name}' no es una instancia de struct "
                f"(tipo: {type(root_val).__name__}).")

        # ── Navegar structs anidados hasta el penúltimo campo ────────────────
        instance = root_val
        for field in field_path[:-1]:
            nested = instance.get_field(field)
            if not isinstance(nested, StructInstance):
                raise InterpreterError(
                    f"[Struct] '{field}' no es una struct anidada; "
                    f"no se puede navegar más profundo.")
            instance = nested

        target_field = field_path[-1]
        fdef = instance.struct_def.fields.get(target_field)
        if fdef is None:
            raise InterpreterError(
                f"[Struct] Campo '{target_field}' no existe en struct "
                f"'{instance.struct_name}'.")

        # ── Validar tipo ─────────────────────────────────────────────────────
        self._validate_struct_field_value(final_value, fdef, target_field,
                                          instance.struct_name)

        # ── Validar límite contra longitud reportada por el AST ──────────────
        if longitud_node is not None and isinstance(final_value, (list, tuple, dict)):
            ast_len = (longitud_node.get("value")
                       if isinstance(longitud_node, dict) else longitud_node)
            if fdef.limit is not None and ast_len > fdef.limit:
                raise InvalidOperationError(
                    f"[Struct] Campo '{target_field}' tiene límite {fdef.limit}, "
                    f"se intentó asignar {ast_len} elementos.")

        # ── Asignar ──────────────────────────────────────────────────────────
        old_val = instance.fields[target_field]['value']
        instance.set_field(target_field, final_value, fdef)
        const_tag = " [const → bloqueado para reasignación]" if fdef.is_const else ""
        self._log(
            f"[STRUCT:SET] {full_name} :: {fdef.declared_type}"
            f"{'['+str(fdef.limit)+']' if fdef.limit else ''}"
            f" | {old_val!r} → {final_value!r}{const_tag}")

    def _resolve_struct_assignment_value(self, value_node, ast_type, raw_value):
        """
        Resuelve el valor a asignar a un campo de struct.
        Sigue las mismas reglas que handle_VariableDeclaration:
          - strings  → desquota  "Ana" → Ana
          - arrays   → resuelve el literal
          - tuples   → parsea la tupla
          - dicts    → parsea el dict JSON
          - otros    → resolve_expression general
        """
        ast_type_lower = ast_type.lower() if isinstance(ast_type, str) else ""

        # Operación explícita
        if "operation" in value_node:
            op = value_node["operation"]
            expr = op.get("value") if isinstance(op, dict) else op
            return self.resolve_expression(str(expr) if expr is not None else '')

        # NULL
        if ast_type in ("NULL", "null") or raw_value in (None, "null"):
            return None

        # String → desquotar igual que VariableDeclaration
        if ast_type_lower == "string" and isinstance(raw_value, str):
            needs_resolve = (
                any(op in raw_value for op in ['+', '%', '(', ')']) or
                ('.' in raw_value and not raw_value.replace('.', '', 1).isdigit())
            )
            if needs_resolve:
                return self.resolve_expression(raw_value)
            if ((raw_value.startswith('"') and raw_value.endswith('"')) or
                    (raw_value.startswith("'") and raw_value.endswith("'"))):
                return raw_value[1:-1]
            return raw_value

        # Tuple literal: "(val1, val2)"
        if ast_type_lower == "tuple" and isinstance(raw_value, str):
            return self._parse_tuple_literal(raw_value)

        # Dict literal: '{"k":"v"}'
        if ast_type_lower == "dict" and isinstance(raw_value, str):
            try:
                import ujson as _uj
                return _uj.loads(raw_value)
            except Exception:
                return {}

        # Array literal: "[1,2,3]"
        if ast_type_lower == "array" and isinstance(raw_value, str):
            try:
                return self.resolve_expression(raw_value)
            except Exception:
                return []

        # Bool, int, float nativos de Python
        if isinstance(raw_value, bool):  return raw_value
        if isinstance(raw_value, int):   return raw_value
        if isinstance(raw_value, float): return raw_value

        # Caso general
        if isinstance(raw_value, str):
            try:
                return self.resolve_expression(raw_value)
            except Exception:
                return raw_value

        return raw_value

    def _parse_tuple_literal(self, raw: str) -> tuple:
        """Parsea '("stat1", "stat2")' → Python tuple."""
        raw = raw.strip()
        if raw.startswith('(') and raw.endswith(')'):
            inner = raw[1:-1].strip()
            if not inner:
                return tuple()
            items = self._split_args_respecting_brackets(inner)
            return tuple(self.resolve_expression(it.strip()) for it in items)
        raise InterpreterError(f"[Struct] No es una tupla válida: '{raw}'")

    def _validate_struct_field_value(self, value, fdef: 'StructFieldDef',
                                     field_name: str, struct_name: str):
        """Valida que `value` sea compatible con el tipo declarado del campo."""
        dtype = fdef.declared_type
        limit = fdef.limit

        if dtype in ('dynamic', None, 'null'):
            return  # sin restricción de tipo

        def _cat(v):
            if v is None:                 return 'null'
            if isinstance(v, RangeValue): return 'range'
            if isinstance(v, bool):       return 'bool'
            if isinstance(v, int):        return 'int'
            if isinstance(v, float):      return 'float'
            if isinstance(v, str):        return 'string'
            if isinstance(v, tuple):      return 'tuple'
            if isinstance(v, list):       return 'array'
            if isinstance(v, dict):       return 'dict'
            return 'unknown'

        actual = _cat(value)
        self._log(
            f"[STRUCT:TYPECHECK] campo '{field_name}' en '{struct_name}': "
            f"esperado={dtype}"
            f"{'['+str(limit)+']' if limit else ''}, recibido={actual}"
            f"{'(len='+str(len(value))+')' if isinstance(value, (list,tuple,dict)) else ''}")

        def _type_error(expected):
            raise InvalidOperationError(
                f"[Struct] Error de tipo en campo '{field_name}' de struct "
                f"'{struct_name}': se esperaba '{expected}', "
                f"se recibió '{actual}'.")

        def _limit_error(got):
            raise InvalidOperationError(
                f"[Struct] Error de límite en campo '{field_name}' de struct "
                f"'{struct_name}': límite={limit}, recibido={got} elementos.")

        # Rango tipado
        if dtype == 'range':
            if actual != 'range':
                _type_error('range')
            return

        if dtype == 'array':
            if actual != 'array':
                _type_error('array')
            if limit is not None and len(value) > limit:
                _limit_error(len(value))

        elif dtype == 'tuple':
            if actual != 'tuple':
                _type_error('tuple')
            if limit is not None and len(value) > limit:
                _limit_error(len(value))

        elif dtype == 'dict':
            if actual != 'dict':
                _type_error('dict')
            if limit is not None and len(value) > limit:
                _limit_error(len(value))

        elif dtype in ('int', 'float', 'string', 'bool'):
            if limit is not None:
                # Tipo primitivo con límite → espera una colección de ese tipo
                if actual not in ('array', 'tuple', 'dict'):
                    _type_error(f"{dtype}[{limit}] (colección)")
                if len(value) > limit:
                    _limit_error(len(value))
                # Validar elementos individuales
                for elem in (value.values() if isinstance(value, dict) else value):
                    ea = _cat(elem)
                    if ea != dtype:
                        raise InvalidOperationError(
                            f"[Struct] El campo '{field_name}' espera elementos de tipo "
                            f"'{dtype}', pero contiene '{ea}'.")
            else:
                if actual != dtype:
                    # Permitir promoción int→float
                    if not (dtype == 'float' and actual == 'int'):
                        _type_error(dtype)

        # Tipo struct anidado: ya gestionado en _init_fields; se ignora aquí

    def _oop_set_field(self, instance: 'ClassInstance', field_path: list, value):
        """Helper: asigna un campo en una ClassInstance vía lista de partes."""
        obj = instance
        for part in field_path[:-1]:
            obj = obj.get_attribute(part)
        obj.set_attribute(field_path[-1], value)

    def _get_struct_field_by_path(self, instance: 'StructInstance', path: str):
        """
        Navega un path de puntos a través de StructInstances anidadas.
        Cuando se agota la cadena de structs, el resto se delega a
        _execute_type_method_chain para compatibilidad con la interfaz de tipos.

        Ejemplos:
          "name"                    → instance.name  (valor final)
          "dir.calle"               → instance.dir.calle
          "name.type"               → type-method 'type' sobre el valor de name
          "name.length()"           → type-method 'length' sobre el valor de name
          "name.slice(0,3)"         → type-method 'slice' con args sobre name
          "dir.calle.toUpperCase()" → type-method sobre campo anidado
          "hobbies.contains(\"dev\")" → type-method array sobre campo anidado
        """
        # Split por puntos respetando paréntesis
        parts = self._split_dot_path_smart(path)
        current = instance
        resolved_parts = []   # partes ya navegadas como structs

        for i, part in enumerate(parts):
            if isinstance(current, StructInstance):
                # nombre del campo sin args (slice(0,3) → slice)
                field_name = re.match(r'^([A-Za-z_]\w*)', part)
                field_name = field_name.group(1) if field_name else part

                # ¿Es un campo del struct actual?
                if field_name in current.struct_def.fields:
                    resolved_parts.append(field_name)
                    self._log(
                        f"[STRUCT:GET] navegar '{field_name}' en struct "
                        f"'{current.struct_name}' → "
                        f"{current.fields[field_name]['value']!r}")
                    current = current.get_field(field_name)
                else:
                    # No es campo → debe ser type-method sobre el struct mismo
                    remaining_chain = self._join_dot_parts(parts[i:])
                    val_type = _get_value_type(current)
                    first_m  = field_name

                    if first_m in _CORE_TYPE_METHODS.get(val_type, {}):
                        self._log(
                            f"[STRUCT:GET] '{part}' no es campo de struct "
                            f"'{current.struct_name}'; delegando type-method "
                            f"'{remaining_chain}' sobre valor tipo '{val_type}'")
                        result, _ = self._execute_type_method_chain(
                            ".".join(resolved_parts), remaining_chain, current, False)
                        return result

                    raise InterpreterError(
                        f"[Struct] El campo '{field_name}' no existe en struct "
                        f"'{current.struct_name}'.")
            else:
                # Ya salimos de los structs — el resto son type-methods
                remaining_chain = self._join_dot_parts(parts[i:])
                val_type = _get_value_type(current)
                first_m  = re.match(r'^([A-Za-z_]\w*)', part)
                first_m  = first_m.group(1) if first_m else part

                if val_type in _CORE_TYPE_METHODS and \
                        first_m in _CORE_TYPE_METHODS[val_type]:
                    self._log(
                        f"[STRUCT:GET] aplicando type-method '{remaining_chain}' "
                        f"sobre valor tipo '{val_type}' = {current!r}")
                    result, _ = self._execute_type_method_chain(
                        ".".join(resolved_parts), remaining_chain, current, False)
                    return result

                raise InterpreterError(
                    f"[Struct] No se puede acceder a '{part}' "
                    f"en un valor de tipo '{val_type}'; "
                    f"no es un campo de struct ni un método del tipo.")

        return current

    def _split_dot_path_smart(self, path: str) -> list:
        """
        Divide 'a.b.slice(0,3).c' por puntos sin romper dentro de paréntesis.
        Resultado: ['a', 'b', 'slice(0,3)', 'c']
        """
        parts  = []
        depth  = 0
        buf    = []
        for ch in path:
            if ch in ('(', '[', '{'):
                depth += 1
                buf.append(ch)
            elif ch in (')', ']', '}'):
                depth -= 1
                buf.append(ch)
            elif ch == '.' and depth == 0:
                if buf:
                    parts.append(''.join(buf))
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append(''.join(buf))
        return parts

    def _join_dot_parts(self, parts: list) -> str:
        """Reconstruye una cadena de dot-parts de forma segura."""
        return ".".join(parts)

    # ===========================================================================
    # RANGE HELPERS
    # ===========================================================================
    def _try_parse_range(self, expr: str):
        """
        Intenta parsear expr como range literal, soportando:
          1..5        → cerrado
          1..<5       → semi-abierto (excluye end)
          "a".."z"    → string (unicode en comillas: "u0041".."u007f")
          null..null  → rango nulo
        Retorna RangeValue o None. Lanza InterpreterError si es inválido.
        """
        expr = expr.strip()
        if '..' not in expr:
            return None
        parts, half_open = self._split_by_dotdot(expr)
        if len(parts) != 2:
            return None
        raw_s = self._resolve_range_endpoint_var(parts[0].strip())
        raw_e = self._resolve_range_endpoint_var(parts[1].strip())
        if raw_s is None or raw_e is None:
            return None
        try:
            return _build_range(raw_s, raw_e, half_open=half_open)
        except ValueError as e:
            raise InvalidOperationError(f"Rango inválido '{expr}': {e}")
        except Exception:
            return None

    def _find_matching_close(self, s: str, open_pos: int) -> int:
        """
        Dado que s[open_pos] == '(', devuelve el índice del ')' que lo cierra.
        Respeta strings anidados y paréntesis anidados. Retorna None si no encontrado.
        """
        depth = 0; in_str = False; str_ch = '"'
        for i in range(open_pos, len(s)):
            ch = s[i]
            if in_str:
                if ch == str_ch: in_str = False
                continue
            if ch in ('"', "'"):
                in_str = True; str_ch = ch; continue
            if ch == '(':  depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return i
        return None

    def _split_by_dotdot(self, expr: str):
        """
        Divide por '..' o '..<' respetando paréntesis/corchetes/llaves y strings.
        Solo divide cuando la profundidad de brackets es 0.
          '1..5'             → (['1','5'], False)
          '1..<5'            → (['1','5'], True)
          '(0..x.length)..5' → (['(0..x.length)','5'], False)  ← no parte dentro de ()
        """
        i = 0; parts = []; buf = []; in_str = False; str_ch = '"'; depth = 0
        while i < len(expr):
            ch = expr[i]
            if in_str:
                buf.append(ch)
                if ch == str_ch: in_str = False
                i += 1; continue
            if ch in ('"', "'"):
                in_str = True; str_ch = ch; buf.append(ch); i += 1; continue
            if ch in ('(', '[', '{'):
                depth += 1; buf.append(ch); i += 1; continue
            if ch in (')', ']', '}'):
                depth -= 1; buf.append(ch); i += 1; continue
            # Solo partir cuando depth == 0
            if depth == 0 and ch == '.' and i + 2 < len(expr) \
                    and expr[i+1] == '.' and expr[i+2] == '<':
                parts.append(''.join(buf)); buf = []
                i += 3
                parts.append(expr[i:].strip())
                return parts, True
            if depth == 0 and ch == '.' and i + 1 < len(expr) and expr[i+1] == '.':
                parts.append(''.join(buf)); buf = []; i += 2; continue
            buf.append(ch); i += 1
        parts.append(''.join(buf))
        return parts, False

    def _resolve_range_endpoint_var(self, raw: str):
        """
        Resuelve un endpoint de rango a su representación en texto.
        Acepta: literales, variables simples, y expresiones complejas (x.length, arr[0], etc.)
        Retorna None si el resultado no es usable como endpoint de rango.
        """
        raw = raw.strip()
        # Literales directos — devolver tal cual sin evaluar
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw
        if raw == 'null': return raw
        if re.fullmatch(r'-?\d+\.\d+|-?\d+', raw): return raw

        # Cualquier otra cosa → resolver como expresión
        try:
            val = self.resolve_expression(raw)
            if val is None:            return 'null'
            if isinstance(val, bool):  return None   # bool no válido en rango
            if isinstance(val, int):   return str(val)
            if isinstance(val, float): return str(val)
            if isinstance(val, str):
                # Carácter único → endpoint string válido
                if len(val) == 1:      return f'"{val}"'
                return None            # string de >1 char no es endpoint válido
        except Exception:
            return None
        return None

    def handle_CallExpression(self, node):
        function_name = node.get("function")
        if isinstance(function_name, str) and '.' in function_name:
            clean = function_name.strip().rstrip('()')
            parts = clean.split('.', 1)
            if len(parts) == 2:
                left, right = parts

                # --- comprobación de instancias de clase (existente) ---
                # --- comprobación de módulos (existente) ---

                # ===== NUEVO: métodos de tipos primitivos (array, string, etc.) =====
                try:
                    obj = self.symbol_table.get_value(left)
                    val_type = _get_value_type(obj)
                    if val_type in _CORE_TYPE_METHODS:
                        # Construir la cadena de llamada completa y delegar en resolve_expression
                        args_node = node.get("arguments", {})
                        raw_args = args_node.get("value", "") if isinstance(args_node, dict) else ""
                        call_str = f"{function_name}({raw_args})"
                        self._log(f"[CoreMethod] Delegando a resolve_expression: {call_str}")
                        result = self.resolve_expression(call_str)
                        return result
                except (UndeclaredVariableError, InterpreterError):
                    pass

        # ── await func() ─────────────────────────────────────────────────────
        if isinstance(function_name, str) and function_name.startswith('await '):
            actual_fn = function_name[6:].strip()
            self._log(f"[Async] await detectado → '{actual_fn}'")
            return self._execute_async_call(actual_fn, node)

        # ── instance.method() o module.func() ────────────────────────────────
        if isinstance(function_name, str) and '.' in function_name:
            clean = function_name.strip().rstrip('()')
            parts = clean.split('.', 1)
            if len(parts) == 2:
                left, right = parts

                # Primero: ¿es una instancia de clase?
                try:
                    obj = self.symbol_table.get_value(left)
                    if isinstance(obj, ClassInstance):
                        args_node = node.get("arguments", {})
                        raw_args  = args_node.get("value", "") if isinstance(args_node, dict) else ""
                        args = self._parse_call_parameters({"value": raw_args}) if str(raw_args).strip() else []
                        self._log(f"[OOP] Llamada instancia: {left}.{right}({args})")
                        method_info, origin = self.object_table.lookup_method(obj.class_name, right)
                        ctx = MethodContext(self, method_info, obj, origin, args)
                        return ctx.execute()
                    if isinstance(obj, ModuleInstance):
                        args_node = node.get("arguments", {})
                        raw_args  = args_node.get("value", "") if isinstance(args_node, dict) else ""
                        args = self._parse_call_parameters({"value": raw_args}) if str(raw_args).strip() else []
                        args = [a.native_obj if isinstance(a, ModuleInstance) else a for a in args]
                        self._log(f"[Native] Llamada nativa: {left}.{right}({args})")
                        try:
                            return obj.call_method(right, args, self)
                        except Exception as e:
                            #raise InterpreterError(str(e))
                            self._log(f"\n❌ ERROR en método nativo '{right}': {e}")
                            return None
                except (UndeclaredVariableError, InterpreterError):
                    pass

                # Segundo: ¿es un módulo (función libre)?
                if self.module_loader.is_loaded(left):
                    arguments_node = node.get("arguments", {})
                    raw_args = arguments_node.get("value", "") if isinstance(arguments_node, dict) else ""
                    args = self._parse_call_parameters({"value": raw_args}) if raw_args.strip() else []
                    try:
                        fn = self.module_loader.get_function(left, right)
                        return fn.call(args, self)
                    except ModuleError as e:
                        raise InterpreterError(str(e))

        if function_name == "Break":
            self.break_flag = True
            return

        if function_name == "Return":
            return_value_node = node.get("value") or node.get("arguments") or {}
            return_value = None

            if "value" in return_value_node:
                raw = return_value_node["value"]
                # resolve_expression maneja todos los casos:
                # params, variables, literales, expresiones, OOP, modulos...
                return_value = self.resolve_expression(raw)

            self._log(f"[TRACE]   Return valor={return_value}")
            self.return_flag  = True
            self.return_value = return_value
            return return_value

        # ── NATIVE CORE: print / read ─────────────────────────────────────────
        # arguments.value contiene TODOS los args como un solo string.
        # Ej: '"Hello, World!", end=""'  -> hay que partirlo antes de resolver.
        if function_name in ('print', 'read'):
            _args_node = node.get('arguments') or {}
            _raw_all   = _args_node.get('value', '') if isinstance(_args_node, dict) else (_args_node or '')
            _raw_all   = str(_raw_all).strip()
            _parts     = self._split_args_respecting_brackets(_raw_all) if _raw_all else []
            _parts     = [p.strip() for p in _parts if p.strip()]
            _ph        = (node.get('paramType') or {})
            _ph        = _ph.get('value') if isinstance(_ph, dict) else _ph
            if function_name == 'print':
                return self._handle_print_args(_parts, _ph)
            else:
                return self._handle_read_args(_parts)
        arguments_node   = node.get("arguments")
        param_type_node  = node.get("paramType")
        raw_argument     = arguments_node.get("value") if isinstance(arguments_node, dict) else arguments_node
        actual_param_type = param_type_node.get("value") if isinstance(param_type_node, dict) else param_type_node

        value_to_process = None

        if actual_param_type == "ModuleVariable":
            value_to_process = self.resolve_expression(raw_argument)
        elif actual_param_type == "function" and isinstance(raw_argument, str) and '.' in raw_argument:
            value_to_process = self.resolve_expression(raw_argument)
        elif function_name == "print" and isinstance(raw_argument, str) and self._is_function_call(raw_argument):
            self._log(f"[TRACE]   print con llamada a función: '{raw_argument}'")
            value_to_process = self.resolve_expression(raw_argument)
        elif actual_param_type == "ArrayAccess":
            if isinstance(raw_argument, str) and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', raw_argument):
                try:
                    variable_value = self.symbol_table.get_value(raw_argument)
                    if isinstance(variable_value, str) and '[' in variable_value:
                        value_to_process = self._evaluate_array_access(variable_value)
                    else:
                        value_to_process = variable_value
                except UndeclaredVariableError:
                    value_to_process = f"<Error: Variable '{raw_argument}' no definida>"
            else:
                value_to_process = self._evaluate_array_access(raw_argument)
        elif actual_param_type == "expression":
            value_to_process = self.evaluate_expression(raw_argument)
        elif isinstance(raw_argument, str):
            if actual_param_type == 'string':
                if raw_argument.startswith('"') and raw_argument.endswith('"'):
                    value_to_process = raw_argument[1:-1]
                elif any(op in raw_argument for op in ['+', '-', '*', '/', '%', '(', ')']):
                    value_to_process = self.resolve_expression(raw_argument)
                elif '.' in raw_argument and not raw_argument.replace('.', '', 1).isdigit():
                    value_to_process = self.resolve_expression(raw_argument)
                else:
                    if hasattr(self, '_current_function') and self._current_function:
                        function_params = self.symbol_table.get_function_params(self._current_function)
                        if raw_argument in function_params:
                            try:
                                value_to_process = self.symbol_table.get_function_param_value(
                                    self._current_function, raw_argument)
                            except UndeclaredVariableError:
                                pass
                    if value_to_process is None:
                        try:
                            value_to_process = self.symbol_table.get_value(raw_argument)
                        except UndeclaredVariableError:
                            value_to_process = raw_argument
            elif any(op in raw_argument for op in ['+', '-', '*', '/', '%']):
                value_to_process = self.resolve_expression(raw_argument)
            elif '.' in raw_argument:
                value_to_process = self.resolve_expression(raw_argument)
            else:
                if hasattr(self, '_current_function') and self._current_function:
                    function_params = self.symbol_table.get_function_params(self._current_function)
                    if raw_argument in function_params:
                        try:
                            value_to_process = self.symbol_table.get_function_param_value(
                                self._current_function, raw_argument)
                        except UndeclaredVariableError:
                            pass
                if value_to_process is None:
                    try:
                        value_to_process = self.symbol_table.get_value(raw_argument)
                    except UndeclaredVariableError:
                        value_to_process = raw_argument
        else:
            value_to_process = raw_argument

        # (print y read interceptados arriba - no llegan aqui)

    # ==========================================================================
    # Funciones nativas core: print y read
    # ==========================================================================

    def _handle_print_args(self, parts, type_hint=None):
        """
        Maneja print() con los argumentos ya partidos por coma de nivel 0.

        print(<expr>)
        print(<expr>, end="...")
        print()                     <- solo salto de linea

        Segundo arg puede ser posicional o named (end=...).
        """
        if not parts:
            print()
            return
        value = self._resolve_print_value(parts[0], type_hint)
        end = '\n'
        for part in parts[1:]:
            p = part.strip()
            m = re.match(r'(?i)^end\s*=\s*(.+)$', p)
            end_val = m.group(1).strip() if m else p
            if (end_val.startswith('"') and end_val.endswith('"')) or \
               (end_val.startswith("'") and end_val.endswith("'")):
                end_val = end_val[1:-1]
            end = (end_val.replace('\\n', '\n')
                          .replace('\\t', '\t')
                          .replace('\\r', '\r')
                          .replace('\\\\', '\\'))
            break   # solo el primero extra es end
        self._do_print(value, end)

    def _resolve_print_value(self, raw, type_hint=None):
        """
        Resuelve el primer argumento de print() a su valor Python.
        Orden: string literal -> bool/null -> numero -> variable -> expresion.
        """
        if raw is None:
            return None
        raw = str(raw).strip()
        if not raw:
            return None

        # Literal string — solo si NO contiene separador de concatenación
        # '"a" . "b"' empieza y termina con " pero es concatenación
        is_simple_string = (
            ((raw.startswith('"') and raw.endswith('"')) or
             (raw.startswith("'") and raw.endswith("'")))
            and ' . ' not in raw  # no es concatenación con espacios
        )
        if is_simple_string:
            inner = raw[1:-1]
            return (inner.replace('\\n', '\n')
                         .replace('\\t', '\t')
                         .replace('\\r', '\r')
                         .replace('\\\""', '"')
                         .replace("\\'", "'")
                         .replace('\\\\', '\\'))

        if raw == 'true':           return True
        if raw == 'false':          return False
        if raw in ('null', 'None'): return None

        try:
            return float(raw) if '.' in raw else int(raw)
        except (ValueError, TypeError):
            pass

        # Identificador simple: params de funcion primero, luego symbol_table
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', raw):
            if hasattr(self, '_current_function') and self._current_function:
                fps = self.symbol_table.get_function_params(self._current_function)
                if raw in fps:
                    try:
                        return self.symbol_table.get_function_param_value(
                            self._current_function, raw)
                    except UndeclaredVariableError:
                        pass
            try:
                val = self.symbol_table.get_value(raw)
                # ── AZÚCAR: print(p1) → persona<p1.name=null, ...> ──────────
                if isinstance(val, StructInstance):
                    return val.format_print(raw)
                return val
            except UndeclaredVariableError:
                pass
            return raw

        # Expresion compleja
        try:
            val = self.resolve_expression(raw)
            # ── AZÚCAR: print(p1.dir) → direccion<p1.dir.calle=null, ...> ──
            if isinstance(val, StructInstance):
                return val.format_print(raw)
            return val
        except Exception:
            return raw

    def _do_print(self, value, end='\n'):
        """
        Formatea e imprime con el estilo del lenguaje.
          None  -> null
          bool  -> true / false
          float -> sin ceros finales superfluos
          list  -> [a, b, c]
          str   -> sin comillas envolventes, escapes procesados
        """
        def _fmt(v):
            if v is None:                 return 'null'
            if isinstance(v, RangeValue): return v.format_display()
            if isinstance(v, bool):       return 'true' if v else 'false'
            if isinstance(v, float):
                s = f'{v:.15f}'.rstrip('0')
                return s if not s.endswith('.') else s + '0'
            if isinstance(v, tuple):
                return '(' + ', '.join(_fmt(i) for i in v) + ')'
            if isinstance(v, list):
                return '[' + ', '.join(_fmt(i) for i in v) + ']'
            if isinstance(v, dict):
                return '{' + ', '.join(f"{k}:{_fmt(vv)}" for k, vv in v.items()) + '}'
            if isinstance(v, str):
                return v
            return str(v)

        if value is None:
            out = 'null'
        elif isinstance(value, RangeValue):
            out = value.format_display()
        elif isinstance(value, bool):
            out = 'true' if value else 'false'
        elif isinstance(value, float):
            s = f'{value:.15f}'.rstrip('0')
            out = s if not s.endswith('.') else s + '0'
        elif isinstance(value, StructInstance):
            # Safety net: format_print should have been called already in _resolve_print_value
            out = repr(value)
        elif isinstance(value, tuple):
            out = '(' + ', '.join(_fmt_val(i) for i in value) + ')'
        elif isinstance(value, list):
            out = '[' + ', '.join(_fmt(i) for i in value) + ']'
        elif isinstance(value, dict):
            out = '{' + ', '.join(f"{k}:{_fmt(v)}" for k, v in value.items()) + '}'
        elif isinstance(value, str):
            s = value
            if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or
                                 (s[0] == "'" and s[-1] == "'")):
                s = s[1:-1]
            out = s
        else:
            out = str(value)
        print(out, end=end)

    def _handle_read_args(self, parts):
        """
        Maneja read() con los argumentos ya partidos por coma de nivel 0.

        read(<var>)
        read(<var>, <tipo>)
        read(<var>, <tipo>, <msg>)
        read(<var>, <msg>)              <- msg detectado como string literal
        read(void)
        read(void, <msg>)
        read(<var>, void)               <- tipo void = descartar entrada
        read(<var>, type=int, msg="texto:")

        Tipos: int  float  bool  string (default)  void
        Bool:  \\true  \\false  true  false  1  0
        """
        VALID_TYPES = {'int', 'float', 'bool', 'string', 'void'}

        if not parts:
            raise InterpreterError("read() requiere al menos un argumento (variable o void).")

        entry_val  = None
        input_type = 'string'
        message    = ''
        is_void    = False

        for i, part in enumerate(parts):
            p = part.strip()

            # Named: type=...
            m = re.match(r'(?i)^type\s*=\s*(.+)$', p)
            if m:
                t = m.group(1).strip().lower()
                if t not in VALID_TYPES:
                    raise InterpreterError(
                        f"read: tipo invalido '{t}'. Valores validos: int, float, bool, string, void.")
                if t == 'void': is_void = True
                else:           input_type = t
                continue

            # Named: msg=...
            m = re.match(r'(?i)^msg\s*=\s*(.+)$', p)
            if m:
                v = m.group(1).strip()
                if (v.startswith('"') and v.endswith('"')) or \
                   (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                message = (v.replace('\\n', '\n').replace('\\t', '\t')
                             .replace('\\\""', '"').replace("\\'", "'")
                             .replace('\\\\', '\\'))
                continue

            # Posicional 0: variable o void
            if i == 0:
                if p == 'void':
                    is_void = True
                else:
                    entry_val = p
                continue

            # Posicional resto: tipo conocido
            if p.lower() in VALID_TYPES:
                t = p.lower()
                if t == 'void': is_void = True
                else:           input_type = t
                continue

            # Posicional resto: string literal -> mensaje
            if (p.startswith('"') and p.endswith('"')) or \
               (p.startswith("'") and p.endswith("'")):
                v = p[1:-1]
                message = (v.replace('\\n', '\n').replace('\\t', '\t')
                             .replace('\\\""', '"').replace("\\'", "'")
                             .replace('\\\\', '\\'))
                continue

            # Posicional resto: variable que contiene el mensaje
            try:
                resolved = self.symbol_table.get_value(p)
                if isinstance(resolved, str):
                    message = resolved
            except Exception:
                pass

        try:
            user_input = input(message)
        except EOFError:
            user_input = ''

        if is_void:
            self._log("[read/void] entrada descartada")
            return

        final_value = self._convert_read_input(user_input, input_type)

        if entry_val:
            try:
                self.symbol_table.set_value(entry_val, final_value)
            except UndeclaredVariableError:
                self.symbol_table.declare(entry_val, Symbol(final_value, 'dynamic'))
            self._log(f"[read] '{entry_val}' = {final_value!r} (tipo: {input_type})")

    def _convert_read_input(self, raw_str, input_type):
        """Convierte el string leido de consola al tipo indicado."""
        s = raw_str.strip()
        if input_type == 'int':
            try:
                return int(float(s))
            except (ValueError, TypeError):
                raise InterpreterError(f"read: no se pudo convertir '{s}' a int.")
        if input_type == 'float':
            try:
                return float(s)
            except (ValueError, TypeError):
                raise InterpreterError(f"read: no se pudo convertir '{s}' a float.")
        if input_type == 'bool':
            norm = s.lower().lstrip('\\')
            if norm in ('true', '1'):  return True
            if norm in ('false', '0'): return False
            raise InterpreterError("read: valor bool invalido. Usa \\true, \\false, 1 o 0.")
        return raw_str

    def _infer_type(self, value):
     """Infiere el tipo de un valor"""
     if isinstance(value, bool):
        return "bool"
     elif isinstance(value, int):
        return "int"
     elif isinstance(value, float):
        return "float" 
     elif isinstance(value, str):
        return "string"
     else:
        return "any" 
    def handle_Function(self, node):
        name = node["name"]
        parameters_info = self._parse_function_parameters(node.get("parameters", {}))
        is_async = bool(node.get('async') or node.get('isAsync'))

        # ── Punto de entrada: function myfunc() -> main {} ────────────────
        target = node.get("target", "")
        if target == "main":
            if self._main_function is not None:
                raise InterpreterError(
                    f"Solo puede haber una función de entrada (->main). "
                    f"Ya existe '{self._main_function}', se encontró otra en '{name}'.")
            self._main_function = name
            self._log(f"[MAIN] Función de entrada registrada: '{name}'")

        self.symbol_table.declare_function(name, node)
        self.symbol_table.declare_function_params(name, parameters_info)

        if is_async:
            self._async_functions.add(name)
            self._log(f"[Async] Función async '{name}' registrada.")

        return_type = node.get("explicitType", "inferred")
        self._log(f"[TRACE] Función '{name}' declarada | params={parameters_info} | retorno={return_type} | async={is_async} | target={target or 'none'}")
    def _parse_function_parameters(self, parameters_node):
     """Parsea la información de parámetros de una función"""
     params_info = {}
    
     if "value" in parameters_node:
        params_str = parameters_node["value"]
        
        # Procesar parámetros como "a:any, b:int, name:string"
        param_parts = [p.strip() for p in params_str.split(',') if p.strip()]
        
        for param_part in param_parts:
            if ':' in param_part:
                param_name, param_type = param_part.split(':', 1)
                params_info[param_name.strip()] = param_type.strip()
            else:
                # Si no tiene tipo explícito, asumir "any"
                params_info[param_part.strip()] = "any"
                
     return params_info
    
    def handle_FunctionCall(self, node):
     function_name = node["function"]
    
     self._log(f"Intentando llamar a la función: '{function_name}'")
     
     # Obtener argumentos de la llamada
     call_parameters = self._parse_call_parameters(node.get("paramenters", {}))
    
     # Crear contexto de función y ejecutar
     function_context = FunctionContext(self, function_name, call_parameters)
     result = function_context.execute_function()
    
     # ===== PROCESAR VALOR DE RETORNO =====
     if result is not None:
        if isinstance(result, str):
            # Verificar si es una llamada a función anidada
            if self._is_function_call(result):
                result = self._execute_function_call_from_string(result)
            # Verificar si NO es un literal string
            elif not (result.startswith('"') and result.endswith('"')):
                # Intentar como expresión si tiene operadores
                if any(op in result for op in ['+', '-', '*', '/', '%', '.']):
                    result = self.resolve_expression(result)
                else:
                    # Intentar obtener como variable
                    try:
                        result = self.symbol_table.get_value(result)
                    except UndeclaredVariableError:
                        # Mantener valor original
                        pass
        
        self._log(f"Función '{function_name}' retornó: {result}")
        return result
    
     self._log(f"Función '{function_name}' ejecutada sin retorno explícito")
     return None
    def _split_args_respecting_brackets(self, args_str):
     """Divide por comas respetando [], (), {}, y strings entre comillas."""
     parts, current, depth, in_str, str_char = [], [], 0, False, '"'
     i = 0
     while i < len(args_str):
        ch = args_str[i]
        if in_str:
            current.append(ch)
            if ch == str_char and (i == 0 or args_str[i-1] != '\\'):
                in_str = False
        elif ch in ('"', "'"):
            in_str = True
            str_char = ch
            current.append(ch)
        elif ch in ('(', '[', '{'):
            depth += 1; current.append(ch)
        elif ch in (')', ']', '}'):
            depth -= 1; current.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(current)); current = []
        else:
            current.append(ch)
        i += 1
     if current:
        parts.append(''.join(current))
     return [p.strip() for p in parts if p.strip()]
    def _parse_call_parameters(self, parameters_node):
     """
     Versión canónica unificada.
     Maneja:
       - Lista Python del AST  → evalúa cada elemento directamente
       - Escalar no-string     → devuelve [valor]
       - String vacío          → []
       - String con args       → divide por coma, respeta [], (), {}, strings
     El formato "nombre:valor" (tipado Tesseract) extrae solo el valor.
     """
     params = []
     if "value" not in parameters_node:
        return params

     params_str = parameters_node["value"]

     # Vacío
     if params_str is None or params_str == "" or params_str == []:
        return params

     # Lista Python presuelta por el AST
     if isinstance(params_str, list):
        for item in params_str:
            if isinstance(item, (int, float, bool)) or item is None:
                params.append(item)
            elif isinstance(item, str):
                params.append(self._evaluate_parameter_value(item))
            else:
                params.append(item)
        return params

     # Escalar no-string (int, float, bool directo del AST)
     if not isinstance(params_str, str):
        return [params_str]

     if not params_str.strip():
        return params

     param_parts = self._split_args_respecting_brackets(params_str)
     for param_part in param_parts:
        param_part = param_part.strip()
        if not param_part:
            continue
        is_literal_string = (param_part.startswith('"') and param_part.endswith('"')) or \
                             (param_part.startswith("'") and param_part.endswith("'"))
        if ':' in param_part and not is_literal_string:
            _, value_part = param_part.split(':', 1)
            param_value = self._evaluate_parameter_value(value_part.strip())
        else:
            param_value = self._evaluate_parameter_value(param_part)
        params.append(param_value)
     return params
    def handle_LibraryCall(self, node):
        module_raw  = node["module"]
        alias       = node.get("alias")
        functions   = node.get("functions")
        func_aliases = node.get("functionAliases", [])
        inline_aliases = node.get("inlineAliases", {})
        on_names    = node.get("on", [])
        on_aliases  = node.get("onAliases", [])

        # ── ¿Es un archivo fuente .tss? ────────────────────────────────────
        if self._is_source_file_import(module_raw):
            self._load_source_file(module_raw, alias, functions,
                                   func_aliases, inline_aliases)
            return

        # ── Módulo nativo (comportamiento original) ────────────────────────
        module_name = module_raw
        self._log(f"Cargando módulo nativo '{module_name}'")
        try:
            if functions:
                # from math use PI, sqrt  → cargar solo lo pedido
                self.module_loader.load_selective(module_name, functions)
            else:
                # library math  → cargar todo
                self.module_loader.load(module_name)
            self._register_native_classes(module_name)
        except ModuleError as e:
            raise InterpreterError(str(e))

        if alias:
            self.module_loader.apply_alias(module_name, alias)

        if functions:
            if func_aliases:
                self.module_loader.apply_member_aliases_positional(
                    module_name, functions, func_aliases
                )
            else:
                for fname, falias in inline_aliases.items():
                    self.module_loader.apply_member_alias_inline(
                        module_name, fname, falias
                    )
            # ── Inyección selectiva: from math use PI, sqrt ───────────────
            # Solo inyectar los miembros pedidos en la tabla de símbolos
            self._inject_native_module_symbols(module_name, functions,
                                               inline_aliases, func_aliases)
        if on_names:
            self.module_loader.apply_on_aliases(module_name, on_names, on_aliases)

        self._log(f"Módulo nativo '{module_name}' listo.")
    def _inject_native_module_symbols(self, module_name: str, members: list,
                                       inline_aliases: dict, func_aliases: list):
        """
        Inyecta en la tabla de símbolos principal solo los miembros pedidos
        de un módulo nativo.
          from math use PI           → PI disponible directamente
          from math use sqrt al sqr  → sqr disponible directamente
        """
        pos_alias = dict(zip(members, func_aliases)) if func_aliases else {}
        mod = self.module_loader.get_module(module_name)

        for orig_name in members:
            exposed = (inline_aliases.get(orig_name)
                       or pos_alias.get(orig_name)
                       or orig_name)

            # ¿Es una función del módulo?
            try:
                mf = mod.get_function(orig_name)
                # Registrar como función en la tabla
                # Creamos un nodo sintético compatible con declare_function
                fake_node = {
                    'name': exposed,
                    'parameters': mf.params,
                    'block': mf.block if mf.kind == 'script' else [],
                    '_native_module': module_name,
                    '_native_fn_name': orig_name,
                }
                # Guardamos referencia directa al ModuleFunction para llamarla
                self.symbol_table.declare(
                    exposed,
                    Symbol(value=mf, declared_type='function'))
                self._log(f"  Importada función nativa '{orig_name}' como '{exposed}'")
                continue
            except Exception:
                pass

            # ¿Es un export (variable/constante)?
            try:
                exp = mod.get_export(orig_name)
                sym = Symbol(value=exp.value,
                             declared_type=exp.export_type or 'dynamic',
                             is_const=exp.is_const)
                self.symbol_table.declare(exposed, sym)
                self._log(f"  Importado export '{orig_name}' = {exp.value!r} como '{exposed}'")
                continue
            except Exception:
                pass

            self._log(f"  ADVERTENCIA: '{orig_name}' no encontrado en módulo '{module_name}'")

    # ==========================================================================
    # OOP — Declaración de Clase
    # ==========================================================================
    def handle_ClassDeclaration(self, node):
        class_name = node.get('name')
        self._log(f"[OOP] === Declarando clase '{class_name}' ===")

        parent     = node.get('extends')
        impl_raw   = node.get('implements')
        modifier   = node.get('modifier')
        interfaces = [i.strip() for i in impl_raw.split(',')] if isinstance(impl_raw, str) else []

        class_def = ClassDefinition(
            name=class_name, parent=parent,
            interfaces=interfaces, modifier=modifier
        )

        members = node.get('members', [])
        self._log(f"[OOP] Procesando {len(members)} miembros de '{class_name}'")
        for member in members:
            self._process_class_member(member, class_def)

        self.object_table.declare_class(class_name, class_def)
        self._log(f"[OOP] Clase registrada: {class_def}")

    def _process_class_member(self, member: dict, class_def: ClassDefinition):
        """Parsea un miembro (atributo, método o constructor) y lo añade a class_def."""
        # Desenvolver ClassMember wrapper si existe
        if 'ClassMember' in member:
            inner = member['ClassMember']
            for key, content in inner.items():
                self._process_class_member({key: content}, class_def)
            return

        # ── Atributo ────────────────────────────────────────────────────────
        attr_kinds = {'AttributeDeclaration', 'AttributeConstantDeclaration',
                      'ConstantAttributeDeclaration'}
        matched = attr_kinds & set(member.keys())
        if matched:
            kind      = matched.pop()
            attr_node = member[kind]
            attr_name = attr_node.get('name')
            val_node  = attr_node.get('value', {})
            raw_val   = val_node.get('value') if isinstance(val_node, dict) else None
            modifier  = attr_node.get('modifier', 'public')
            is_const  = 'Constant' in kind or 'constant' in kind.lower()
            attr_type = val_node.get('type') if isinstance(val_node, dict) else None

            default_value = None
            if raw_val is not None:
                try:
                    default_value = (self.resolve_expression(str(raw_val))
                                     if isinstance(raw_val, str) else raw_val)
                except Exception:
                    default_value = raw_val

            class_def.attributes[attr_name] = {
                'value':    default_value,
                'type':     attr_type,
                'modifier': modifier,
                'is_const': is_const,
            }
            self._log(f"[OOP]   Atributo '{attr_name}' ({modifier}) default={default_value}")
            return

        # ── Método ──────────────────────────────────────────────────────────
        if 'MethodDeclaration' in member:
            mnode       = member['MethodDeclaration']
            method_name = mnode.get('name')
            is_async    = bool(mnode.get('async') or mnode.get('isAsync'))
            params_info = self._parse_function_parameters(mnode.get('parameters', {}))
            mod         = mnode.get('modifier', 'public')
            etype       = mnode.get('explicitType')

            class_def.methods[method_name] = {
                'node':          mnode,
                'params':        params_info,
                'modifier':      mod,
                'explicit_type': etype,
                'is_async':      is_async,
            }
            self._log(f"[OOP]   Método '{method_name}' ({mod}) params={list(params_info.keys())} async={is_async}")
            return

        # ── Constructor ─────────────────────────────────────────────────────
        if 'ConstructorDeclaration' in member:
            cnode       = member['ConstructorDeclaration']
            params_info = self._parse_function_parameters(cnode.get('parameters', {}))
            mod         = cnode.get('modifier', 'public')
            class_def.constructor = {
                'node':   cnode,
                'params': params_info,
                'modifier': mod,
            }
            self._log(f"[OOP]   Constructor ({mod}) params={list(params_info.keys())}")
            return

    # ==========================================================================
    # OOP — Declaración de Interfaz
    # ==========================================================================
    def handle_InterfaceDeclaration(self, node):
        name = node.get('name')
        self._log(f"[OOP] Declarando interfaz '{name}'")
        self.object_table.declare_interface(name, node)

    # ==========================================================================
    # OOP — new ClassName(args)
    # ==========================================================================
    def handle_NewObject(self, node):
        class_name = node.get('class')
        args_node  = node.get('arguments', {})
        raw_args   = args_node.get('value', '') if isinstance(args_node, dict) else ''
        args = self._parse_call_parameters({'value': raw_args}) if str(raw_args).strip() else []
        return self._instantiate_object(class_name, args)

    def _instantiate_object(self, class_name: str, args: list):
        """Instancia una clase (TSS o nativa)."""
        # 1. Clase definida en TSS
        if self.object_table.has_class(class_name):
            instance = self.object_table.instantiate(class_name)
            ctor = self._find_constructor(class_name)
            if ctor:
                self._execute_constructor(ctor, instance, args)
            elif args:
                self._log(f"[OOP] ADVERTENCIA: '{class_name}' sin constructor, args ignorados.")
            self._log(f"[OOP] Instancia TSS: {instance}")
            return instance

        # 2. Clase nativa (cargada por ModuleLoader)
        if self.module_loader.has_class(class_name):
            return self._instantiate_native_class(class_name, args)

        raise InterpreterError(f"Clase '{class_name}' no declarada.")

    def _instantiate_native_class(self, class_name: str, args: list):
        mod_name, module_class = self.module_loader.get_class_info(class_name)
        self._log(f"[OOP] Instanciando clase nativa '{class_name}' desde módulo '{mod_name}'")
        instance = self.module_loader.instantiate(mod_name, class_name, args, self)
        # Parche para labels: forzar un tamaño mínimo
        if class_name == "Label":
            try:
                instance.call_method("setSize", [100, 25], self)
            except Exception:
                pass
        return instance

    def _find_constructor(self, class_name: str):
        """Busca constructor subiendo por la jerarquía."""
        visited, current = set(), class_name
        while current and current not in visited:
            visited.add(current)
            if current in self.object_table.class_definitions:
                cls = self.object_table.class_definitions[current]
                if cls.constructor:
                    return cls.constructor
                current = cls.parent
            else:
                break
        return None

    def _execute_constructor(self, ctor_info: dict, instance: ClassInstance, args: list):
        ctor_node  = ctor_info['node']
        func_params = ctor_info['params']
        class_name = instance.class_name
        frame_key  = f"{class_name}.__construct__"

        old_fn   = self._current_function
        old_inst = self._current_instance
        self._current_function = frame_key
        self._current_instance = instance

        self.symbol_table.push_function_frame(frame_key)
        self.symbol_table.push_scope(label=f"Constructor '{class_name}'")

        param_names = list(func_params.keys())
        for i, pname in enumerate(param_names):
            if i < len(args):
                self.symbol_table.declare_function_param_value(frame_key, pname, args[i])
                self._log(f"[OOP]   ctor param '{pname}' = {args[i]}")

        old_ret = self.return_flag
        self.return_flag = False
        block = ctor_node.get('block', [])
        if isinstance(block, list):
            for stmt in block:
                if self.return_flag: break
                self.execute_node(stmt)

        self.return_flag       = old_ret
        self._current_function = old_fn
        self._current_instance = old_inst
        self.symbol_table.pop_scope(label=f"Constructor '{class_name}'")
        self.symbol_table.pop_function_frame(frame_key)
        self._log(f"[OOP] Constructor '{class_name}' finalizado.")

    # ==========================================================================
    # OOP — this / super
    # ==========================================================================
    def _require_instance(self, keyword='this'):
        if not self._current_instance:
            raise InterpreterError(f"'{keyword}' usado fuera de un método de clase.")

    def handle_ThisAccess(self, node):
        self._require_instance('this')
        raw   = node.get('value', '')
        field = raw.split('.', 1)[1] if '.' in raw else raw
        val   = self._current_instance.get_attribute(field)
        self._log(f"[OOP] this.{field} = {val}")
        return val

    def handle_ThisCall(self, node):
        self._require_instance('this')
        raw         = node.get('value', '')
        method_name = raw.split('.', 1)[1] if '.' in raw else raw
        args_node   = node.get('arguments', {})
        raw_args    = args_node.get('value', '') if isinstance(args_node, dict) else ''
        args = self._parse_call_parameters({'value': raw_args}) if str(raw_args).strip() else []
        self._log(f"[OOP] this.{method_name}({args})")
        method_info, origin = self.object_table.lookup_method(
            self._current_instance.class_name, method_name)
        return MethodContext(self, method_info, self._current_instance, origin, args).execute()

    def handle_ThisAssignment(self, node):
        self._require_instance('this')
        raw      = node.get('value', '')
        field    = raw.split('.', 1)[1] if '.' in raw else raw
        assigned = node.get('assigned', {})
        raw_val  = assigned.get('value') if isinstance(assigned, dict) else None
        value    = None
        if raw_val is not None:
            try:
                value = self.resolve_expression(str(raw_val)) if isinstance(raw_val, str) else raw_val
            except Exception:
                value = raw_val
        self._current_instance.set_attribute(field, value)
        self._log(f"[OOP] this.{field} = {value}")

    def handle_SuperAccess(self, node):
        self._require_instance('super')
        raw   = node.get('value', '')
        field = raw.split('.', 1)[1] if '.' in raw else raw
        parent = self.object_table.class_definitions[self._current_instance.class_name].parent
        if not parent:
            raise InterpreterError(f"'{self._current_instance.class_name}' no tiene clase padre.")
        val = self._current_instance.attributes.get(field)
        self._log(f"[OOP] super.{field} = {val}")
        return val

    def handle_SuperCall(self, node):
        self._require_instance('super')
        raw         = node.get('value', '')
        method_name = raw.split('.', 1)[1] if '.' in raw else raw
        args_node   = node.get('arguments', {})
        raw_args    = args_node.get('value', '') if isinstance(args_node, dict) else ''
        args = self._parse_call_parameters({'value': raw_args}) if str(raw_args).strip() else []
        parent = self.object_table.class_definitions[self._current_instance.class_name].parent
        if not parent:
            raise InterpreterError(f"'{self._current_instance.class_name}' no tiene clase padre.")
        self._log(f"[OOP] super.{method_name}({args})")
        method_info, origin = self.object_table.lookup_method(parent, method_name)
        return MethodContext(self, method_info, self._current_instance, origin, args).execute()

    def handle_SuperAssignment(self, node):
        self._require_instance('super')
        raw      = node.get('value', '')
        field    = raw.split('.', 1)[1] if '.' in raw else raw
        assigned = node.get('assigned', {})
        raw_val  = assigned.get('value') if isinstance(assigned, dict) else None
        value    = None
        if raw_val is not None:
            try:
                value = self.resolve_expression(str(raw_val)) if isinstance(raw_val, str) else raw_val
            except Exception:
                value = raw_val
        self._current_instance.set_attribute(field, value)
        self._log(f"[OOP] super.{field} = {value}")

    def handle_SuperConstructorCall(self, node):
        self._require_instance('super')
        args_node = node.get('arguments', {})
        raw_args  = args_node.get('value', '') if isinstance(args_node, dict) else ''
        args = self._parse_call_parameters({'value': raw_args}) if str(raw_args).strip() else []
        parent = self.object_table.class_definitions[self._current_instance.class_name].parent
        if not parent:
            raise InterpreterError(f"'{self._current_instance.class_name}' no tiene clase padre.")
        self._log(f"[OOP] super.__construct__({args})")
        ctor = self._find_constructor(parent)
        if ctor:
            self._execute_constructor(ctor, self._current_instance, args)
        else:
            self._log(f"[OOP] Clase padre '{parent}' no tiene constructor.")

    # ==========================================================================
    # Try-Catch-Finally
    # ==========================================================================
    def handle_TryCatch(self, node):
        self._log("[TryCatch] Iniciando bloque try")
        try_block      = node.get('tryBlock') or node.get('block', [])
        catch_clause   = node.get('catchClause', {})
        finally_node   = node.get('finallyBlock')
        # El finally puede estar anidado dentro del catchClause
        if not finally_node and isinstance(catch_clause, dict):
            finally_node = catch_clause.get('finallyBlock')

        try:
            self._exec_try_block(try_block)
        except ThrowSignal as e:
            self._log(f"[TryCatch] ThrowSignal capturada: {e}")
            self._exec_catch_block(catch_clause, e)
        except InterpreterError as e:
            self._log(f"[TryCatch] InterpreterError capturado: {e}")
            self._exec_catch_block(catch_clause, ThrowSignal("RuntimeError", str(e)))
        except Exception as e:
            self._log(f"[TryCatch] Excepción Python capturada: {e}")
            self._exec_catch_block(catch_clause, ThrowSignal("Exception", str(e)))
        finally:
            if finally_node:
                self._log("[TryCatch] Ejecutando finally")
                self._exec_finally_block(finally_node)
        self._log("[TryCatch] Bloque try-catch finalizado")

    def _exec_try_block(self, block):
        self.symbol_table.push_scope(label="try")
        if isinstance(block, list):
            for stmt in block:
                if self.break_flag or self.return_flag: break
                self.execute_node(stmt)
        self.symbol_table.pop_scope(label="try")

    def _exec_catch_block(self, catch_clause: dict, signal: ThrowSignal):
        if not catch_clause:
            return
        exc_var      = catch_clause.get('exception') or catch_clause.get('name')
        catch_type   = catch_clause.get('catchType', {})
        expected     = catch_type.get('type') if isinstance(catch_type, dict) else None

        # Filtrar por tipo (catch (e as TipoError))
        if expected and expected != signal.exception_class:
            self._log(f"[TryCatch] Tipo no coincide: esperado '{expected}', recibido '{signal.exception_class}' — re-lanzando")
            raise signal

        self.symbol_table.push_scope(label="catch")
        if exc_var:
            self.symbol_table.declare(exc_var, Symbol(value=str(signal), declared_type='string'))
            self._log(f"[TryCatch] Excepción en '{exc_var}': {signal}")

        block = catch_clause.get('block', [])
        if isinstance(block, list):
            for stmt in block:
                if self.break_flag or self.return_flag: break
                self.execute_node(stmt)
        self.symbol_table.pop_scope(label="catch")

    def _exec_finally_block(self, finally_node: dict):
        self.symbol_table.push_scope(label="finally")
        block = finally_node.get('block', []) if isinstance(finally_node, dict) else []
        if isinstance(block, list):
            for stmt in block:
                if self.break_flag or self.return_flag: break
                self.execute_node(stmt)
        self.symbol_table.pop_scope(label="finally")

    # ==========================================================================
    # Throw
    # ==========================================================================
    def handle_Throw(self, node):
        exc_class  = node.get('exception', 'Error')
        value_node = node.get('value', {})
        message    = None
        if isinstance(value_node, dict):
            raw = value_node.get('value')
            if raw:
                try:    message = self.resolve_expression(str(raw))
                except: message = str(raw)
        self._log(f"[Throw] [{exc_class}]: {message}")
        raise ThrowSignal(exc_class, message)

    # ==========================================================================
    # Async / Event Loop
    # ==========================================================================
    def _execute_async_call(self, function_name: str, node: dict):
        """Ejecuta una función async usando asyncio."""
        args_node = node.get('arguments', {})
        raw_args  = args_node.get('value', '') if isinstance(args_node, dict) else ''
        args = self._parse_call_parameters({'value': raw_args}) if str(raw_args).strip() else []

        interp = self
        async def _coro():
            ctx = FunctionContext(interp, function_name, args)
            return ctx.execute_function()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._log(f"[Async] Loop activo → agendando '{function_name}' como tarea")
                task = asyncio.ensure_future(_coro())
                self._async_tasks.append(task)
                return None   # resultado diferido
            else:
                self._log(f"[Async] Ejecutando '{function_name}' en loop")
                return loop.run_until_complete(_coro())
        except RuntimeError:
            return asyncio.run(_coro())

    def start_event_loop(self):
     """Inicia el event loop en un hilo NO demonio."""
     if self._event_loop is not None and self._event_loop.is_running():
        return
     self._log("[EventLoop] Iniciando event loop en hilo background (no demonio)")
     self._event_loop = asyncio.new_event_loop()
     self._loop_thread = threading.Thread(target=self._run_loop, daemon=False)
     self._loop_thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._event_loop)
        self._event_loop.run_forever()

    def stop_event_loop(self):
        """Detiene el event loop."""
        if self._event_loop and self._event_loop.is_running():
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        self._log("[EventLoop] Señal de parada enviada.")
    def wait_event_loop(self):
        """Espera a que el event loop termine (bloquea hasta que se llame a stop_event_loop)."""
        if not self._event_loop or not self._event_loop.is_running():
            self._log("[EventLoop] No hay loop corriendo, nada que esperar.")
            return
        self._log("[EventLoop] Esperando a que el event loop termine...")
        if hasattr(self, '_loop_thread') and self._loop_thread.is_alive():
            self._loop_thread.join()
        self._log("[EventLoop] Event loop terminado.")

    def schedule_async(self, coro):
        """Agenda una corrutina en el event loop activo (para UI)."""
        if self._event_loop and self._event_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._event_loop)
            self._async_tasks.append(future)
            self._log(f"[Async] Corrutina agendada en event loop.")
            return future
        raise InterpreterError("Event loop no está activo. Llama start_event_loop() primero.")
    # ==========================================================================
    # Helpers: carga de archivos fuente (.tss)
    # ==========================================================================

    @staticmethod
    def _is_source_file_import(module_str: str) -> bool:
        """
        Detecta si el nodo LibraryCall apunta a un archivo fuente (.tss).
        El parser puede dejar las comillas o quitarlas; ambos casos se manejan.
        """
        clean = module_str.strip('"\'')
        return clean.lower().endswith('.tss')

    @staticmethod
    def _normalize_file_path(raw: str, base_dir: str) -> str:
        """
        Normaliza una ruta de archivo para Linux, Windows y macOS.
        • Elimina comillas envolventes
        • Convierte separadores de Windows (\\ o /) al separador del SO actual
        • Resuelve rutas relativas contra base_dir
        • Aplica normpath para eliminar '..', '.' redundantes
        """
        path = raw.strip('"\'')
        # Unificar separadores: \\ y / → os.sep
        path = path.replace('\\\\', os.sep).replace('\\', os.sep).replace('/', os.sep)
        # Rutas relativas → resolver contra el directorio base
        if not os.path.isabs(path):
            path = os.path.join(base_dir, path)
        return os.path.normpath(path)

    @staticmethod
    def _derive_module_name(file_path: str) -> str:
        """
        Deriva el nombre de módulo a partir de la ruta del archivo:
        '/path/to/mycode.tss' → 'mycode'
        """
        print(os.path.splitext(os.path.basename(file_path))[0])
        return os.path.splitext(os.path.basename(file_path))[0]

    def _run_compiler_pipeline(self, file_path: str) -> dict:
        """
        Ejecuta el pipeline completo sobre un archivo .tss:
          1. compiler.exe <file>       → archivo intermedio (.txt)
          2. astAjson.py <intermediate>→ JSON
        Devuelve el AST como diccionario Python.
        """
        COMPILER_EXE_PATH = r"C:\Users\Panch\Escritorio\Tess\compiler.exe"      # <- Cambia aquí
        AST_AJSON_PATH    = r"C:\Users\Panch\Escritorio\Tess\astAjson.py"        # <- Cambia aquí
        import subprocess, tempfile, ujson as _json, os

        # Usa las rutas globales definidas al inicio del archivo
        compiler = COMPILER_EXE_PATH
        ast_script = AST_AJSON_PATH

        # Verifica que existan
        if not os.path.isfile(compiler):
            raise InterpreterError(f"No se encuentra compiler.exe en: {compiler}")
        if not os.path.isfile(ast_script):
            raise InterpreterError(f"No se encuentra astAjson.py en: {ast_script}")

        fd1, tmp_ast = tempfile.mkstemp(suffix=".txt")
        fd2, tmp_json = tempfile.mkstemp(suffix=".json")
        os.close(fd1); os.close(fd2)

        try:
            # Etapa 1: compilar .tss → AST intermedio
            res1 = subprocess.run(
                [compiler,"-b", file_path, tmp_ast],
                capture_output=True, text=True
            )
            if res1.returncode != 0:
                raise InterpreterError(
                    f"Error compilando '{file_path}':\n{res1.stderr.strip()}"
                )

            # Etapa 2: AST intermedio → JSON
            res2 = subprocess.run(
                ["python.exe", ast_script, tmp_ast, tmp_json],
                capture_output=True, text=True
            )
            print(f"Comando ejecutado: python.exe {ast_script} {tmp_ast} {tmp_json}")
           # input("Presiona enter para continuar")
            if res2.returncode != 0:
                raise InterpreterError(
                    f"Error al convertir AST de '{file_path}':\n{res2.stderr.strip()}"
                )

            # Leer y validar JSON
            if not os.path.isfile(tmp_json):
                raise InterpreterError(f"No se generó el archivo JSON: {tmp_json}")
            if os.path.getsize(tmp_json) == 0:
                raise InterpreterError(f"El archivo JSON {tmp_json} está vacío.")

            with open(tmp_json, "r", encoding="utf-8") as f:
                try:
                    data = _json.load(f)
                except _json.JSONDecodeError as e:
                    with open(tmp_json, "r", encoding="utf-8") as f2:
                        content = f2.read()
                    preview = content[:500] + ("..." if len(content) > 500 else "")
                    raise InterpreterError(
                        f"JSON inválido en {tmp_json}:\n{e}\nContenido:\n{preview}"
                    )
            return data

        finally:
            for p in (tmp_ast, tmp_json):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _load_source_file(self,
                          module_raw:     str,
                          alias:          'str | None',
                          functions:      'list | None',
                          func_aliases:   list,
                          inline_aliases: dict):
        """
        Carga un archivo .tss como módulo:
          1. Normaliza la ruta
          2. Ejecuta el pipeline compiler → astAjson → JSON
          3. Crea un Interpreter aislado y ejecuta el JSON
          4. Registra el módulo en _source_modules bajo el nombre efectivo
          5. Aplica alias de módulo (as) y alias de miembros (al / use)
          6. Si hay 'from ... use', inyecta símbolos en la tabla principal
        """
        import os

        # 1. Ruta normalizada
        # Prioridad de búsqueda:
        #   1. Relativa al archivo fuente actual (donde está el código que hace el import)
        #   2. Relativa al directorio de trabajo actual
        #   3. _path_stack (fallback)
        source_dir = None
        if self._path_stack:
            source_dir = self._path_stack[-1]

        # Intentar resolver la ruta en orden de prioridad
        raw_stripped = module_raw.strip('"\'')
        candidates = []
        if source_dir:
            candidates.append(self._normalize_file_path(module_raw, source_dir))
        candidates.append(self._normalize_file_path(module_raw, os.getcwd()))

        file_path = None
        for candidate in candidates:
            if os.path.isfile(candidate):
                file_path = candidate
                break

        if file_path is None:
            searched = ', '.join(f"'{c}'" for c in candidates)
            raise InterpreterError(
                f"No se encontró el archivo de módulo '{raw_stripped}'. "
                f"Rutas buscadas: {searched}"
            )

        # Nombre de módulo: alias de módulo > nombre derivado del archivo
        default_name = self._derive_module_name(file_path)
        module_name  = alias if alias else default_name

        self._log(f"Cargando módulo fuente '{module_name}' desde '{file_path}'")

        # 2. Si ya está cargado con este nombre, no reejecutar
        if module_name not in self._source_modules:
            # Pipeline: .tss → JSON AST
            ast_data = self._run_compiler_pipeline(file_path)

            # 3. Intérprete aislado (scope propio)
            iso = Interpreter(debug_mode=self.debug_mode)
            iso._base_dir = os.path.dirname(file_path)
            iso.interpret(ast_data, source_path=file_path)

            # 4. Registrar el proxy
            proxy = SourceModuleProxy(iso, module_name)
            self._source_modules[module_name] = proxy
            self._log(f"Módulo fuente '{module_name}' ejecutado y registrado.")
        else:
            proxy = self._source_modules[module_name]

        # 5a. Aliases de miembros (from … use x al myX)
        #     inline_aliases: {original_name: alias_name}
        for orig, mem_alias in inline_aliases.items():
            proxy.apply_member_alias(orig, mem_alias)

        # 5b. Aliases posicionales (from … use x, y al a, b)
        if functions and func_aliases:
            for orig, mem_alias in zip(functions, func_aliases):
                proxy.apply_member_alias(orig, mem_alias)

        # 6. "from … use …": inyectar símbolos específicos en la tabla principal
        if functions:
            self._inject_source_symbols(proxy, functions, inline_aliases, func_aliases)
        
        self._log(f"Módulo fuente '{module_name}' listo.")

    def _inject_source_symbols(self,
                                proxy:          SourceModuleProxy,
                                functions:      list,
                                inline_aliases: dict,
                                func_aliases:   list):
        """
        Para 'from "file.tss" use x, y al myY':
        Inyecta los símbolos solicitados directamente en la tabla principal.

        Resolución de nombre expuesto (prioridad):
          1. inline_aliases[original]  → "x al myX"
          2. func_aliases[i]           → "use x, y al a, b"
          3. original_name             → sin alias
        """
        pos_alias = {orig: fa for orig, fa in zip(functions, func_aliases)} if func_aliases else {}

        for orig_name in functions:
            # Nombre que tendrá en la tabla principal
            exposed = (inline_aliases.get(orig_name)
                       or pos_alias.get(orig_name)
                       or orig_name)

            iso = proxy._isolated_interpreter

            # ¿Es función?
            try:
                func_node   = iso.symbol_table.get_function(orig_name)
                func_params = iso.symbol_table.get_function_params(orig_name)
                # Declarar función con su nombre expuesto en la tabla principal
                self.symbol_table.declare_function(exposed, func_node)
                self.symbol_table.declare_function_params(exposed, func_params)
                self._log(f"  Importada función '{orig_name}' como '{exposed}'")
                continue
            except UndeclaredVariableError:
                pass

            # ¿Es variable/constante?
            try:
                sym = iso.symbol_table.get_symbol(orig_name)
                import copy
                new_sym = Symbol(value=sym.value,
                                 declared_type=sym.declared_type,
                                 is_const=sym.is_const)
                self.symbol_table.declare(exposed, new_sym)
                self._log(f"  Importada variable '{orig_name}' como '{exposed}'")
                continue
            except UndeclaredVariableError:
                pass

            raise InterpreterError(
                f"El símbolo '{orig_name}' no existe en el módulo fuente."
            )
    def _evaluate_parameter_value(self, value_str):
     """Evalúa el valor de un parámetro (puede ser variable, expresión o literal)"""
     # Si ya es un valor Python nativo (int, float, bool, list, etc.), devolverlo directo
     if not isinstance(value_str, str):
        return value_str
     value_str = value_str.strip()

     # Array literal [...]
     if value_str.startswith('[') and value_str.endswith(']'):
        inner = value_str[1:-1].strip()
        if not inner:
            return []
        items = self._split_args_respecting_brackets(inner)
        return [self._evaluate_parameter_value(i.strip()) for i in items]

     try:
        # Llamada a función
        if self._is_function_call(value_str):
            return self._execute_function_call_from_string(value_str)

        # Expresión con operaciones (pero no arrays ni strings con punto)
        if any(op in value_str for op in ['+', '-', '*', '/', '%']) and \
                not (value_str.startswith('"') and value_str.endswith('"')):
            return self.resolve_expression(value_str)

        # Acceso a módulo/instancia con punto: mod.VALOR o inst.metodo()
        if '.' in value_str and not value_str.replace('.', '', 1).isdigit():
            return self.resolve_expression(value_str)

        # Variable
        return self.symbol_table.get_value(value_str)

     except UndeclaredVariableError:
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        try:
            return int(value_str)
        except ValueError:
            try:
                return float(value_str)
            except ValueError:
                if value_str.startswith('"') and value_str.endswith('"'):
                    return value_str[1:-1]
                return value_str
    def handle_ParameterAsignement(self, node):
     if not hasattr(self, '_current_function') or not self._current_function:
        self._log("ADVERTENCIA: ParameterAsignement fuera de función")
        return

     param_name = node["name"]
     value_node = node.get("value", {})
    
     # Evaluar valor
     if "operation" in value_node:
        operation_node = value_node["operation"]
        expression_str = operation_node.get("value") if isinstance(operation_node, dict) else operation_node
        final_value = self.resolve_expression(expression_str)
     else:
        raw_value = value_node.get("value")
        if isinstance(raw_value, str) and not (raw_value.startswith('"') and raw_value.endswith('"')):
            try:
                final_value = self.symbol_table.get_value(raw_value)
            except UndeclaredVariableError:
                final_value = raw_value
        else:
            final_value = raw_value
    
     # ASIGNAR A TABLA ESPECÍFICA DE PARÁMETROS
     self.symbol_table.declare_function_param_value(
        self._current_function, param_name, final_value
     )
     self._log(f"  Asignado parámetro '{param_name}': {final_value}")
    def handle_if_Condition(self, node):
     self._log("Iniciando bloque If-Condition.")

     # 1. Comprueba la condición principal del IF
     if self.evaluate_expression(node["condition"]):
        self._log("  Condición 'if' es VERDADERA. Ejecutando su bloque.")
        if "block" in node:
            self.symbol_table.push_scope(label="if")
            for statement in node["block"]:
                if self.break_flag or self.return_flag:
                    break
                self.execute_node(statement)
                if self.return_flag:
                    self.symbol_table.pop_scope(label="if")
                    return
            self.symbol_table.pop_scope(label="if")
        self._log("Finalizado bloque if-Condition.")
        return

     # 2. Procesar elseIf si existe
     current_node = node
     while "elseIf" in current_node:
        else_if_node = current_node["elseIf"]
        condition = else_if_node.get("condition") or else_if_node.get("value")
        
        if condition and self.evaluate_expression(condition):
            self._log(f"  Condición 'elseIf' ({condition}) es VERDADERA. Ejecutando su bloque.")
            self.symbol_table.push_scope(label="elseIf")
            if "block" in else_if_node:
                for statement in else_if_node["block"]:
                    if self.break_flag or self.return_flag:
                        break
                    self.execute_node(statement)
                    if self.return_flag:
                        self.symbol_table.pop_scope(label="elseIf")
                        return
            self.symbol_table.pop_scope(label="elseIf")
            self._log("Finalizado bloque if-Condition.")
            return
        
        # Moverse al siguiente nivel de anidación
        current_node = else_if_node

     # 3. Procesar else si existe
     if "else" in node:
        self._log("  Ninguna condición anterior fue verdadera. Ejecutando bloque 'else'.")
        else_node = node["else"]
        if "block" in else_node:
            self.symbol_table.push_scope(label="else")
            for statement in else_node["block"]:
                if self.break_flag or self.return_flag:
                    break
                self.execute_node(statement)
                if self.return_flag:
                    self.symbol_table.pop_scope(label="else")
                    return
            self.symbol_table.pop_scope(label="else")

     self._log("Finalizado bloque if-Condition.")
    def handle_ForLoop(self, node):
        """
        Maneja todas las variantes del for:

        ESTILO C:
          for(int i = 0; i < 10; i++)   → iterator.value = "int i = 0; i<10; i++"
          for(var i = 0; i < n; i += 2) → id.

        MODERNO (for-in):
          for(var i in 1..10)            → variable="var i", iterator="1..10"
          for(var i in arr)              → itera array/tupla/dict(valores)/rango
          for(var i in dict.keys())      → itera claves del dict
          for(var i in x >= 10)          → condicional (infinito detectado → error)
          for(var i in i < 10)           → condicional con propia variable

        MULTI-VARIABLE:
          for(var i, var z in 1..10; arr) → variable="var i, var z", iterator="1..10; arr"
        """
        variable_str  = node.get("variable", "")
        iterator_node = node.get("iterator", {})
        iterator_str  = iterator_node.get("value", "") if isinstance(iterator_node, dict) else str(iterator_node)
        block         = node.get("block", [])

        self._log(f"[FOR] variable='{variable_str}' iterator='{iterator_str}'")

        # ── Detectar estilo ──────────────────────────────────────────────────
        is_c_style = self._for_is_c_style(iterator_str)

        if is_c_style:
            self._for_execute_c_style(iterator_str, block)
        else:
            # Parsear declaraciones de variable(s)
            # Soporta: "var i = 0 in cond" → extraer init del variable_str si contiene 'in'
            actual_var_str = variable_str
            var_defs  = self._for_parse_var_defs(actual_var_str)
            iter_parts = self._for_split_iterators(iterator_str)

            if len(var_defs) == 1:
                self._for_execute_modern(var_defs[0], iter_parts[0] if iter_parts else '', block)
            else:
                # Multi-variable: exactamente 2
                iter1 = iter_parts[0] if len(iter_parts) > 0 else ''
                iter2 = iter_parts[1] if len(iter_parts) > 1 else ''
                self._for_execute_multi(var_defs[0], var_defs[1], iter1, iter2, block)

    # ─────────────────────────────────────────────────────────────────────────
    # FOR helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _for_is_c_style(self, iterator_str: str) -> bool:
        """
        Heurística: es estilo C si el iterator tiene exactamente 2 ';'
        y el primero contiene '=' (inicialización).
        Ej: "int i = 0; i<10; i++"
        """
        parts = [p.strip() for p in iterator_str.split(';')]
        if len(parts) != 3:
            return False
        init = parts[0]
        return '=' in init or re.search(r'\bvar\b|\bint\b|\bfloat\b|\bstring\b|\bbool\b', init)

    def _for_parse_var_defs(self, variable_str: str) -> list:
        """
        Parsea 'var i', 'var i, var z', 'int i = 0', 'c, var z' etc.
        Retorna lista de dicts: [{'name': 'i', 'declare': True, 'type': 'dynamic', 'init': None}, ...]
        """
        result = []
        parts  = [p.strip() for p in variable_str.split(',')]
        for part in parts:
            d = self._for_parse_single_var(part.strip())
            result.append(d)
        return result if result else [{'name': variable_str.strip(), 'declare': False,
                                       'type': 'dynamic', 'init': None}]

    def _for_parse_single_var(self, s: str) -> dict:
        """
        Parsea una declaración de variable de for:
          'var i'        → declare=True, name='i', type='dynamic', init=None
          'var i = 5'    → declare=True, name='i', type='dynamic', init=5
          'int i = 0'    → declare=True, name='i', type='int',     init=0
          'int i'        → declare=True, name='i', type='int',     init=0
          'i'            → declare=False (buscar en tabla de símbolos)
          'x = 0'        → declare=False, name='x', init=0
        """
        s = s.strip()

        # Con tipo/var explícito (con o sin init)
        m = re.match(r'^(var|int|float|string|bool|array|tuple|dict|range|dynamic|any)\s+'
                     r'([A-Za-z_]\w*)\s*(?:=\s*(.+))?$', s)
        if m:
            kw, name, init_str = m.group(1), m.group(2), m.group(3)
            typ = 'dynamic' if kw == 'var' else kw
            if init_str:
                try:
                    init = self.resolve_expression(init_str.strip())
                except Exception:
                    init = None
            else:
                # Default por tipo
                defaults = {'int': 0, 'float': 0.0, 'bool': False, 'string': '', 'dynamic': None, 'any': None}
                init = defaults.get(typ, None)
            return {'name': name, 'declare': True, 'type': typ, 'init': init}

        # Sin tipo pero con asignación: "x = 0"
        m2 = re.match(r'^([A-Za-z_]\w*)\s*=\s*(.+)$', s)
        if m2:
            name, init_str = m2.group(1), m2.group(2)
            try:
                init = self.resolve_expression(init_str.strip())
            except Exception:
                init = None
            return {'name': name, 'declare': False, 'type': 'dynamic', 'init': init}

        # Solo nombre → buscar en tabla de símbolos
        if re.fullmatch(r'[A-Za-z_]\w*', s):
            return {'name': s, 'declare': False, 'type': 'dynamic', 'init': None}

        return {'name': s, 'declare': False, 'type': 'dynamic', 'init': None}

    def _for_split_iterators(self, iterator_str: str) -> list:
        """Divide por ';' los iteradores del for moderno/multi."""
        return [p.strip() for p in iterator_str.split(';') if p.strip()]

    def _for_resolve_iterable(self, iter_str: str):
        """
        Convierte el string del iterador en una lista iterable de Python.
        Soporta: rango, array, tupla, dict, variable, condición, NULL.
        Retorna (iterable_list, is_conditional, condition_str)
        """
        s = iter_str.strip()

        # NULL / null → vacío
        if s.upper() == 'NULL':
            return [], False, None

        # Rango (incluyendo half-open)
        if '..' in s:
            rng = self._try_parse_range(s)
            if rng is not None:
                return rng.expand(), False, None

        # Condición: contiene operadores de comparación pero no es literal
        COND_OPS = ('>=', '<=', '!=', '==', '>', '<')
        has_cond = any(op in s for op in COND_OPS) and not s.startswith('[') and \
                   not s.startswith('(') and not s.startswith('{') and \
                   not s.startswith('"') and not s.startswith("'")
        if has_cond:
            return None, True, s

        # Literal o variable
        try:
            val = self.resolve_expression(s)
        except Exception:
            val = None

        if val is None:
            return [], False, None
        if isinstance(val, RangeValue):
            return val.expand(), False, None
        if isinstance(val, (list, tuple)):
            return list(val), False, None
        if isinstance(val, dict):
            return list(val.values()), False, None   # por defecto: valores
        # Escalar → no iterable
        return [], False, None

    def _evaluate_condition(self, cond_str: str) -> bool:
        """
        Evalúa una condición de bucle.
        Maneja: 'true'/'false' literales, y delega al evaluador de expresiones.
        """
        s = cond_str.strip().lower()
        if s in ('true', '1'):   return True
        if s in ('false', '0', 'null'): return False
        try:
            return bool(self.evaluate_expression(cond_str))
        except Exception:
            try:
                return bool(self.resolve_expression(cond_str))
            except Exception:
                return False

    def _for_check_infinite(self, cond_str, var_name, block=None):
        return self._detect_infinite_loop(cond_str, block or [], var_name)

    def _detect_infinite_loop(self, cond_str, block, iter_var=""):
        cond_lower = cond_str.strip().lower()
        if cond_lower in ("false", "0", "null"): return False
        cond_vars = set(re.findall(r"[A-Za-z_]\w*", cond_str))
        for kw in ("true","false","null","and","or","not","if","else"): cond_vars.discard(kw)
        has_exit, mod_vars = self._block_analysis(block or [])
        if has_exit: return False
        # La variable de iteración es modificada externamente por el for (auto-increment)
        if iter_var: mod_vars.add(iter_var)
        if cond_lower in ("true", "1"): return True
        if cond_vars and not (cond_vars & mod_vars): return True
        return False

    def _block_analysis(self, block):
        """
        Analiza un bloque estáticamente.
        Retorna (has_exit: bool, modified_vars: set)

        Break y Return son CallExpression con function="Break"/"Return".
        i++/i-- son IncrementDecrement con value=varname.
        i += n es VariableAsignement con name=varname.
        """
        has_exit = False
        mod_vars = set()
        nodes = block if isinstance(block, list) else ([block] if isinstance(block, dict) else [])

        for node in nodes:
            if not isinstance(node, dict):
                continue
            ntype   = list(node.keys())[0]
            content = node.get(ntype, {})
            if not isinstance(content, dict):
                content = {}

            # ── Break / Return (ambos son CallExpression) ─────────────────
            if ntype == 'CallExpression':
                fn = content.get('function', '')
                if fn in ('Break', 'Return'):
                    has_exit = True
                    continue

            # ── Asignaciones: VariableAsignement, ModuleAsignement ─────────
            if ntype in ('VariableAsignement', 'ModuleAsignement'):
                name = content.get('name', '')
                if name:
                    mod_vars.add(name.split('.')[0])

            # ── Incremento/decremento: i++ / i-- / ++i / --i ──────────────
            if ntype in ('IncrementDecrement', 'IncrementStatement',
                         'DecrementStatement', 'Increment', 'Decrement',
                         'postIncrementStatement', 'postDecrementStatement',
                         'preIncrementStatement',  'preDecrementStatement'):
                name = (content.get('value', '') or content.get('name', '')
                        if isinstance(content, dict) else '')
                if name:
                    mod_vars.add(name)

            # ── Buscar recursivamente en sub-bloques ───────────────────────
            for key in ('block', 'body', 'thenBlock', 'elseBlock', 'ifBlock',
                        'Block', 'then', 'else'):
                sub = content.get(key)
                if sub:
                    sub_e, sub_v = self._block_analysis(sub)
                    if sub_e:
                        has_exit = True
                    mod_vars |= sub_v

        return has_exit, mod_vars

    def _for_run_block(self, block):
        """Ejecuta el bloque del for. Retorna True si se debe salir (break/return)."""
        if isinstance(block, list):
            self.symbol_table.push_scope(label="for-body")
            for stmt in block:
                if self.break_flag or self.return_flag:
                    break
                self.execute_node(stmt)
            self.symbol_table.pop_scope(label="for-body")
        elif isinstance(block, dict):
            self.execute_block(block)
        return self.break_flag or self.return_flag

    def _for_set_var(self, vdef: dict, value):
        """Asigna el valor a la variable de iteración respetando tipo si está declarado."""
        name  = vdef['name']
        typ   = vdef.get('type', 'dynamic')
        actual = _get_value_type(value)

        if typ not in ('dynamic', 'any') and actual not in ('dynamic', 'null', 'any'):
            # Permisión int→float
            ok = (typ == actual) or (typ == 'float' and actual == 'int')
            if not ok:
                raise InterpreterError(
                    f"[FOR] Error de tipo en iteración: variable '{name}' "
                    f"declarada como '{typ}' pero recibió '{actual}' ({value!r})")
        try:
            self.symbol_table.set_value(name, value)
        except UndeclaredVariableError:
            self.symbol_table.declare(name, Symbol(value=value, declared_type=typ))

    MAX_FOR_ITERATIONS = 100_000  # seguridad anti-infinito

    def _for_execute_c_style(self, iterator_str: str, block):
        """
        Estilo C: "int i = 0; i<10; i++"
        Partes: [init, condition, update]
        """
        parts = [p.strip() for p in iterator_str.split(';')]
        if len(parts) != 3:
            raise InterpreterError(f"[FOR] Estilo C mal formado: '{iterator_str}'")

        init_str, cond_str, upd_str = parts

        self.symbol_table.push_scope(label="for-c")

        # Inicialización
        self._for_c_init(init_str)

        # Extraer variables modificadas por el update (i++, i+=2, i=i+1, etc.)
        upd_vars = set(re.findall(r'[A-Za-z_]\w*', upd_str.split('=')[0].split('+')[0].split('-')[0].strip()))

        # Detectar posible bucle infinito — el update modifica vars implícitamente
        has_exit, block_mod_vars = self._block_analysis(block)
        all_mod_vars = block_mod_vars | upd_vars
        cond_vars = set(re.findall(r'[A-Za-z_]\w*', cond_str))
        cond_lower = cond_str.strip().lower()
        if (not has_exit
                and not (cond_vars & all_mod_vars)
                and cond_lower not in ('false', '0', 'null')):
            self.symbol_table.pop_scope(label="for-c")
            raise InterpreterError(
                f"[FOR] Bucle infinito detectado (condición: '{cond_str}'). "
                f"Usa 'break' o 'return' para salir, o asegura que el update "
                f"modifique las variables de la condición.")

        n = 0
        while True:
            # Evaluar condición
            try:
                cond_val = self._evaluate_condition(cond_str)
            except Exception as e:
                self.symbol_table.pop_scope(label="for-c")
                raise InterpreterError(f"[FOR] Error evaluando condición '{cond_str}': {e}")

            if not cond_val:
                break

            n += 1
            if False:  # sin límite de iteraciones
                self.symbol_table.pop_scope(label="for-c")
                raise InterpreterError(
                    f"[FOR] Bucle excedió {self.MAX_FOR_ITERATIONS} iteraciones. "
                    f"Usa 'break' o 'return' para salir de bucles largos.")

            if self._for_run_block(block):
                break

            if self.return_flag:
                break

            # Actualización
            try:
                self._for_c_update(upd_str)
            except Exception as e:
                self.symbol_table.pop_scope(label="for-c")
                raise InterpreterError(f"[FOR] Error en actualización '{upd_str}': {e}")

        self.break_flag = False
        self.symbol_table.pop_scope(label="for-c")
        self._log(f"[FOR] Estilo C finalizado tras {n} iteraciones.")

    def _for_c_init(self, init_str: str):
        """Ejecuta la inicialización del for C: 'int i = 0' o 'i = 0'."""
        init_str = init_str.strip()
        m = re.match(
            r'^(?:(?:var|int|float|string|bool|array|tuple|dict|dynamic|any)\s+)?'
            r'([A-Za-z_]\w*)\s*=\s*(.+)$', init_str)
        if m:
            name, val_str = m.group(1), m.group(2)
            val = self.resolve_expression(val_str.strip())
            # Detectar tipo
            type_m = re.match(r'^(var|int|float|string|bool|array|tuple|dict|dynamic|any)\s+', init_str)
            typ = 'dynamic' if not type_m or type_m.group(1) == 'var' else type_m.group(1)
            self.symbol_table.declare(name, Symbol(value=val, declared_type=typ))
        else:
            # Puede ser solo "i++" o similar, ignorar
            pass

    def _for_c_update(self, upd_str: str):
        """Ejecuta la actualización del for C: 'i++', 'i--', 'i += 2', 'i = i + 1'."""
        upd_str = upd_str.strip()
        # i++
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*\+\+', upd_str)
        if m:
            n = m.group(1); v = self.symbol_table.get_value(n)
            self.symbol_table.set_value(n, v + 1); return
        # i--
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*--', upd_str)
        if m:
            n = m.group(1); v = self.symbol_table.get_value(n)
            self.symbol_table.set_value(n, v - 1); return
        # i += expr
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*\+=\s*(.+)', upd_str)
        if m:
            n, expr = m.group(1), m.group(2)
            v = self.symbol_table.get_value(n)
            self.symbol_table.set_value(n, v + self.resolve_expression(expr)); return
        # i -= expr
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*-=\s*(.+)', upd_str)
        if m:
            n, expr = m.group(1), m.group(2)
            v = self.symbol_table.get_value(n)
            self.symbol_table.set_value(n, v - self.resolve_expression(expr)); return
        # i *= expr
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*\*=\s*(.+)', upd_str)
        if m:
            n, expr = m.group(1), m.group(2)
            v = self.symbol_table.get_value(n)
            self.symbol_table.set_value(n, v * self.resolve_expression(expr)); return
        # i = expr
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*=\s*(.+)', upd_str)
        if m:
            n, expr = m.group(1), m.group(2)
            self.symbol_table.set_value(n, self.resolve_expression(expr)); return
        # Desconocido: intentar como expresión
        try:
            self.resolve_expression(upd_str)
        except Exception:
            pass

    def _for_execute_modern(self, vdef: dict, iter_str: str, block):
        """
        For moderno de una variable: for(var i in 1..10) / for(var i in arr) etc.
        """
        name     = vdef['name']
        declare  = vdef['declare']
        typ      = vdef.get('type', 'dynamic')
        init_val = vdef.get('init')

        self.symbol_table.push_scope(label="for-modern")

        # Detectar si el iterador es condicional ANTES de declarar la variable
        # para saber si necesitamos un valor inicial por defecto
        iterable, is_cond, cond_str = self._for_resolve_iterable(iter_str)

        # Determinar el valor inicial
        if init_val is None and is_cond:
            # Condicional sin init explícito → intentar leer valor existente,
            # o usar 0 como default para tipos numéricos
            try:
                existing = self.symbol_table.get_value(name)
                init_val = existing
            except UndeclaredVariableError:
                init_val = 0 if typ in ('int', 'float', 'dynamic', 'any') else None

        if declare:
            self.symbol_table.declare(name,
                Symbol(value=init_val, declared_type=typ))
        else:
            # Buscar variable existente
            try:
                sym = self.symbol_table.get_symbol(name)
                # Si tenía init_val por default, actualizarla
                if init_val is not None and sym.value is None:
                    self.symbol_table.set_value(name, init_val)
            except UndeclaredVariableError:
                self.symbol_table.declare(name,
                    Symbol(value=init_val, declared_type=typ))

        if is_cond:
            # Forma condicional: for(var i in i < 10)
            # Auto-incrementa la variable de iteración tras cada iteración del cuerpo.
            if self._for_check_infinite(cond_str, name, block):
                self.symbol_table.pop_scope(label="for-modern")
                raise InterpreterError(
                    f"[FOR] Bucle potencialmente infinito (condición: '{cond_str}'). "
                    f"Usa 'break' o 'return'.")
            n = 0
            while True:
                try:
                    cond_val = self._evaluate_condition(cond_str)
                except Exception as e:
                    self.symbol_table.pop_scope(label="for-modern")
                    raise InterpreterError(f"[FOR] Error en condición '{cond_str}': {e}")
                if not cond_val:
                    break
                n += 1
                if False:  # sin límite de iteraciones
                    self.symbol_table.pop_scope(label="for-modern")
                    raise InterpreterError(
                        f"[FOR] Bucle excedió {self.MAX_FOR_ITERATIONS} iteraciones. "
                        f"Usa 'break' o 'return'.")
                if self._for_run_block(block):
                    break
                if self.return_flag:
                    break
                # Auto-incrementar la variable de iteración
                self._for_auto_increment(name, typ)
        else:
            # Iteración sobre colección / rango
            for item in iterable:
                try:
                    self._for_set_var(vdef, item)
                except InterpreterError as e:
                    # Error de tipo → detener con mensaje
                    self.symbol_table.pop_scope(label="for-modern")
                    print(f"[FOR] Iteración detenida: {e}")
                    self.break_flag = False
                    return
                self._log(f"[FOR] {name} = {item!r}")
                if self._for_run_block(block):
                    break
                if self.return_flag:
                    break

        self.break_flag = False
        self.symbol_table.pop_scope(label="for-modern")

    def _for_auto_increment(self, name: str, typ: str):
        """
        Auto-incrementa la variable de iteración condicional:
          int/float/dynamic → +1
          string            → siguiente carácter unicode
        Si la variable no existe o no es incrementable, no hace nada.
        """
        try:
            val = self.symbol_table.get_value(name)
        except UndeclaredVariableError:
            return
        try:
            if isinstance(val, int):
                self.symbol_table.set_value(name, val + 1)
            elif isinstance(val, float):
                import decimal as _dec
                new_val = float(_dec.Decimal(str(val)) + _dec.Decimal('0.1'))
                self.symbol_table.set_value(name, new_val)
            elif isinstance(val, str) and len(val) == 1:
                self.symbol_table.set_value(name, chr(ord(val) + 1))
            # bool, array, dict, etc → no auto-increment, el cuerpo debe manejarlo
        except Exception:
            pass

    def _for_execute_multi(self, vdef1: dict, vdef2: dict,
                           iter1_str: str, iter2_str: str, block):
        """
        Multi-variable: for(var i, var z in 1..10; arr)
        La primera iteración decide cuándo acaba.
        """
        self.symbol_table.push_scope(label="for-multi")

        # Declarar variables
        for vd in (vdef1, vdef2):
            name = vd['name']; typ = vd.get('type', 'dynamic')
            init = vd.get('init')
            if vd['declare']:
                self.symbol_table.declare(name, Symbol(value=init, declared_type=typ))
            else:
                try:
                    self.symbol_table.get_symbol(name)
                except UndeclaredVariableError:
                    self.symbol_table.declare(name, Symbol(value=None, declared_type=typ))

        iterable1, _, _ = self._for_resolve_iterable(iter1_str)
        iterable2, _, _ = self._for_resolve_iterable(iter2_str)

        iter2_gen = iter(iterable2)

        for item1 in iterable1:
            try:
                self._for_set_var(vdef1, item1)
            except InterpreterError as e:
                print(f"[FOR] Iteración detenida en var 1: {e}")
                break

            # Intentar avanzar el segundo iterador
            try:
                item2 = next(iter2_gen)
                try:
                    self._for_set_var(vdef2, item2)
                except InterpreterError as e:
                    print(f"[FOR] Iteración detenida en var 2: {e}")
                    break
            except StopIteration:
                # El segundo iterador terminó, seguimos con el primero
                # pero la variable 2 conserva su último valor
                pass

            self._log(f"[FOR-MULTI] {vdef1['name']}={item1!r}, "
                      f"{vdef2['name']}={self.symbol_table.get_value(vdef2['name']) if True else '?'}")
            if self._for_run_block(block):
                break
            if self.return_flag:
                break

        self.break_flag = False
        self.symbol_table.pop_scope(label="for-multi")

    def handle_WhileLoop(self, node, block_node=None):
     """Maneja WhileLoop con bloque integrado"""
     condition_str = node["condition"]
     self._log(f"Iniciando bucle 'while' con condición: {condition_str}")
     self.break_flag = False

     if "block" in node:
        block_content = node["block"]

        # ── Detección de bucle infinito ───────────────────────────────────
        if self._detect_infinite_loop(condition_str, block_content):
            raise InterpreterError(
                f"[WHILE] Bucle infinito detectado (condición: '{condition_str}'). "
                f"Asegúrate de que alguna variable de la condición se modifique "
                f"dentro del bloque, o usa 'break' / 'return' para salir.")

        while self._evaluate_condition(condition_str):
            self._log("  Condición 'while' es VERDADERA. Ejecutando bloque.")
            
            # Ejecutar el bloque integrado
            if isinstance(block_content, list):
                self.symbol_table.push_scope(label="while")
                for statement in block_content:
                    if self.break_flag or self.return_flag:
                        break
                    self.execute_node(statement)
                    if self.return_flag:
                        self.symbol_table.pop_scope(label="while")
                        return
                self.symbol_table.pop_scope(label="while")
            elif isinstance(block_content, dict):
                self.execute_block(block_content)
            
            if self.break_flag:
                self._log("  Instrucción 'Break' detectada. Saliendo del bucle 'while'.")
                break
            if self.return_flag:
                
                self._log("  Instrucción 'Return' detectada. Saliendo del bucle 'while'.")
                break    
     else:
        self._log("  Advertencia: WhileLoop sin bloque de código")
    
     self.break_flag = False
     self._log(f"Finalizado bucle 'while'.")

    def handle_unknown(self, node_content):
        print(f"ADVERTENCIA CRÍTICA: No hay manejador para este tipo de nodo. Contenido: {node_content}")
        
    def _handle_increment_decrement(self, node, amount):
        var_name = node['value']
        op_type = "incremento" if amount > 0 else "decremento"
        
        try:
            symbol = self.symbol_table.get_symbol(var_name)
            declared_type = symbol.declared_type
            current_value = symbol.value

            # ==========================================================
            # LÓGICA PARA VARIABLES ESTÁTICAS
            # ==========================================================
            if declared_type != 'dynamic':
                if declared_type in ['int', 'float']:
                    # Es un tipo estático numérico, la operación es válida.
                    # Hacemos una comprobación extra por si el valor actual no es un número.
                    if not isinstance(current_value, (int, float)):
                        self._log(f"ERROR: La variable estática '{var_name}' (tipo {declared_type}) contiene un valor no numérico: '{current_value}'.")
                        return

                    # Éxito para estáticas numéricas
                    new_value = current_value + amount
                    self.symbol_table.set_value(var_name, new_value)
                    self._log(f"  Operación de {op_type}: '{var_name}' ahora es {new_value}")

                else:
                    # Es un tipo estático NO numérico (string, boolean, etc.). Error.
                    self._log(f"ERROR: No se puede aplicar {op_type} a la variable '{var_name}' porque su tipo estático es '{declared_type}'.")
                return

            # ==========================================================
            # LÓGICA PARA VARIABLES DINÁMICAS
            # ==========================================================
            else:
                start_value = None
                
                # Si es NULL (None en Python), se permite y empieza en 0.
                if current_value is None:
                    start_value = 0
                # Si es un número, se permite.
                elif isinstance(current_value, (int, float)):
                    start_value = current_value
                
                # Si start_value tiene un valor, la operación es válida.
                if start_value is not None:
                    new_value = start_value + amount
                    self.symbol_table.set_value(var_name, new_value)
                    self._log(f"  Operación de {op_type}: '{var_name}' ahora es {new_value}")
                else:
                    # Si no, es porque el valor es string, boolean, etc. Advertencia.
                    self._log(f"ADVERTENCIA: No se puede aplicar {op_type} a la variable dinámica '{var_name}'. Su valor actual ('{current_value}') no es válido para esta operación.")
                return

        except UndeclaredVariableError as e:
            self._log(e)

    def handle_PostIncrementStatement(self, node):
        self._handle_increment_decrement(node, 1)

    def handle_PostDecrementStatement(self, node):
        self._handle_increment_decrement(node, -1)

    def handle_PreIncrementStatement(self, node):
        self._handle_increment_decrement(node, 1)

    def handle_PreDecrementStatement(self, node):
        self._handle_increment_decrement(node, -1)            
    def _evaluate_concatenated_string(self, arg_str):
        """
        Evalúa cadenas con variables concatenadas: "hola " . var . p1.name
        El separador es ' . ' (punto rodeado de espacios) para no confundir
        con accesos de struct/módulo (p1.name) ni con floats (3.14).
        """
        # Guard: número puro
        stripped = arg_str.strip()
        try:
            return int(stripped)
        except (ValueError, AttributeError):
            pass
        try:
            if '.' in stripped and '..' not in stripped:
                return float(stripped)
        except (ValueError, AttributeError):
            pass

        # Dividir por ' . ' (punto con espacios) respetando strings
        parts = self._split_concat_parts(arg_str)

        # ---------------------------------------------------------
        # FIX: GUARD PARA EVITAR RECURSIÓN INFINITA
        # Si la división devuelve exactamente 1 elemento y es igual 
        # a la entrada original, NO hubo concatenación.
        # ---------------------------------------------------------
        if len(parts) == 1 and parts[0] == arg_str:
            return _UNRESOLVED

        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            val = self.resolve_expression(part)
            if isinstance(val, StructInstance):
                # Si la expresión resolvió a StructInstance completo sin campo → error
                result.append(val.format_print(part))
            else:
                result.append(_fmt_val(val))

        return ''.join(result)

    def _split_concat_parts(self, s: str) -> list:
        """
        Divide por ' . ' (punto con al menos un espacio en algún lado)
        respetando strings entre comillas. No parte por puntos sin espacios
        (p1.name, 3.14, arr.length).
        Ejemplos:
          '"hola" . p1.name . x'   → ['"hola"', 'p1.name', 'x']
          '"a" . "b"'              → ['"a"', '"b"']
          'p1.name'                → ['p1.name']  (sin espacios, no parte)
        """
        parts  = []
        buf    = []
        in_str = False
        str_ch = '"'
        i      = 0
        while i < len(s):
            ch = s[i]
            if in_str:
                buf.append(ch)
                if ch == str_ch:
                    in_str = False
                i += 1
                continue
            if ch in ('"', "'"):
                in_str = True
                str_ch = ch
                buf.append(ch)
                i += 1
                continue
            # Detectar ' . ' — punto con espacio en algún lado,
            # O punto entre cierre de string y siguiente token
            if ch == '.':
                before = buf[-1] if buf else ''
                after  = s[i+1] if i+1 < len(s) else ''
                # Es separador si:
                # 1. Hay espacio antes o después del punto
                # 2. El carácter anterior es cierre de string ('" o ')
                is_sep = (before in (' ', '"', "'") or after == ' ')
                if is_sep:
                    if buf and buf[-1] == ' ':
                        buf.pop()
                    parts.append(''.join(buf))
                    buf = []
                    if after == ' ':
                        i += 2
                    else:
                        i += 1
                    continue
            buf.append(ch)
            i += 1
        if buf:
            parts.append(''.join(buf))
        return [p for p in parts if p.strip()]
    
    def _execute_type_method_chain(self, var_name: str, chain_str: str,
                                origin_value, is_const: bool = False):
     """
     Ejecuta una cadena de métodos/atributos sobre un valor de tipo primitivo.
     Soporta:
      - Métodos con args:   x.toUpperCase()  x.slice(0,3)
      - Atributos:          x.length  x.type
      - .mut al final:      x.toUpperCase().mut
      - Encadenamiento:     x.trim().toUpperCase().slice(0,3).mut

     Retorna (result, mutated: bool)
     """
     # Dividir la cadena en pasos respetando paréntesis
     steps = self._split_method_chain(chain_str)
     if not steps:
        return origin_value, False

     current_value  = origin_value
     current_type   = _get_value_type(current_value)
     should_mut     = False
     origin_var     = var_name
     chain_position = 0  # 0 = primera posición

     for step in steps:
        step = step.strip()

        # ── .mut — terminador de cadena ────────────────────────────────────
        if step == 'mut':
            if chain_position == 0:
                raise InvalidOperationError(
                    "'.mut' no puede usarse directamente sobre el origen sin una operación previa.")
            if is_const:
                raise InvalidOperationError(
                    f"No se puede mutar la constante '{origin_var}' con '.mut'.")
            should_mut = True
            continue   # .mut no cambia current_value, solo activa la mutación

        # ── Parsear nombre del método y argumentos ─────────────────────────
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?$', step, re.DOTALL)
        if not m:
            raise InvalidOperationError(f"Método inválido en cadena: '{step}'")

        method_name = m.group(1)
        raw_args_str = m.group(2)  # None si es atributo sin paréntesis

        # Parsear argumentos
        method_args = []
        if raw_args_str is not None and raw_args_str.strip():
            method_args = self._parse_call_parameters({'value': raw_args_str})

        # ── Buscar en la tabla del tipo actual ─────────────────────────────
        current_type = _get_value_type(current_value)
        type_methods = _CORE_TYPE_METHODS.get(current_type, {})

        if method_name not in type_methods:
            raise InvalidOperationError(
                f"El tipo '{current_type}' no tiene el método o atributo '{method_name}'.")

        method_def = type_methods[method_name]
        cat        = method_def['cat']

        # ── Validar posición ───────────────────────────────────────────────
        if cat == 'chain_only' and chain_position == 0:
            raise InvalidOperationError(
                f"'{method_name}' solo puede usarse encadenado, no directamente sobre el origen.")

        # ── Validar que first no se encadena después de otra operación ─────
        # 'first' sí puede ir en posición 0 Y también producir resultado para
        # encadenar si el resultado tiene tipo con métodos. No se bloquea.

        # ── Ejecutar el método ─────────────────────────────────────────────
        fn = method_def.get('fn')
        if fn is None:
            # Método especial sin fn directa (como mut ya manejado arriba)
            chain_position += 1
            continue

        try:
            current_value = fn(current_value, method_args)
        except Exception as e:
            raise InvalidOperationError(
                f"Error ejecutando '{method_name}' sobre '{current_type}': {e}")

        # ── Mutables por defecto (push, pop, etc.) ─────────────────────────
        if method_def.get('mutable_default') and not is_const:
            # Mutar inmediatamente sin necesitar .mut
            try:
                self.symbol_table.set_value(origin_var, current_value)
            except UndeclaredVariableError:
                pass  # si es parámetro o temporal, no mutar

        chain_position += 1

    # ── Aplicar .mut si fue solicitado ─────────────────────────────────────
     if should_mut:
        try:
            self.symbol_table.set_value(origin_var, current_value)
            self._log(f"[TypeMethod] .mut aplicado: '{origin_var}' = {current_value}")
        except UndeclaredVariableError:
            raise InvalidOperationError(
                f"No se puede mutar '{origin_var}': variable no encontrada.")

     return current_value, should_mut
    def _split_method_chain(self, chain_str: str) -> list:
     """
     Divide 'toUpperCase().trim().slice(0,3).mut' en
     ['toUpperCase()', 'trim()', 'slice(0,3)', 'mut']
     respetando paréntesis anidados.
     """
     steps   = []
     current = []
     depth   = 0
     i       = 0
     s       = chain_str.strip()

     while i < len(s):
        c = s[i]
        if c == '(':
            depth += 1
            current.append(c)
        elif c == ')':
            depth -= 1
            current.append(c)
        elif c == '.' and depth == 0:
            part = ''.join(current).strip()
            if part:
                steps.append(part)
            current = []
        else:
            current.append(c)
        i += 1

     part = ''.join(current).strip()
     if part:
        steps.append(part)

     return steps
    def handle_PerformWhileLoop(self, node):
        condition_str = node["value"]
        self._log(f"Iniciando bucle 'perform-while' (do-while). La condición a chequear es: {condition_str}")
        self.break_flag = False
        
        while True:
            self._log("  Ejecutando bloque del perform-while (al menos una vez).")
            
            # CORRECCIÓN: Manejar tanto listas (formato actual del AST) como diccionarios
            block_content = node["block"]
            
            if isinstance(block_content, list):
                self.symbol_table.push_scope(label="perform-while")
                for statement in block_content:
                    if self.break_flag or self.return_flag:
                        break
                    self.execute_node(statement)
                    if self.return_flag:
                        self.symbol_table.pop_scope(label="perform-while")
                        return
                self.symbol_table.pop_scope(label="perform-while")  
            elif isinstance(block_content, dict):
                self.execute_block(block_content)
            
            # Verificación de Break
            if self.break_flag:
                self._log("  'Break' detectado. Saliendo del bucle.")
                break
            if self.return_flag:
                
                self._log("  'Return' detectado. Saliendo del bucle.")
                break
            # Evaluar la condición para decidir si repetir
            if not self.evaluate_expression(condition_str):
                self._log(f"  La condición '{condition_str}' ahora es falsa. Saliendo del bucle.")
                break
                
        self.break_flag = False
        self._log("Finalizado bucle 'perform-while'.")
        
    def handle_SwitchStatement(self, node):
     switch_var_name = node["value"]
     switch_value = None
     if hasattr(self, '_current_function') and self._current_function:
        try:
            switch_value = self.symbol_table.get_function_param_value(
                self._current_function, switch_var_name
            )
        except UndeclaredVariableError:
            pass
     if switch_value is None:
        switch_value = self.symbol_table.get_value(switch_var_name)
     self._log(f"Iniciando 'switch' para la variable '{switch_var_name}' (valor: {switch_value})")
     self.break_flag = False
     self.switch_fall_through = False
    
    # NUEVA LÓGICA: Los casos están directamente en el nodo SwitchStatement
     cases = node.get("cases", [])
     default_case = node.get("defaultCase")
    
     a_case_matched = False
    
     # Procesar todos los casos
     for case_node in cases:
        case_value = case_node.get("case")
        
        # Si encontramos coincidencia o estamos en fall-through
        if not self.switch_fall_through and str(case_value) == str(switch_value):
            self._log(f"  Coincidencia encontrada en 'case {case_value}'. Ejecutando bloque.")
            self.switch_fall_through = True
            a_case_matched = True
        
        # Ejecutar el bloque del caso si estamos en fall-through
        if self.switch_fall_through:
            # Ejecutar todas las instrucciones del bloque del caso
            block_content = case_node.get("block", [])

            self.symbol_table.push_scope(label=f"switch case {case_value}")
            for statement in block_content:
                if self.break_flag or self.return_flag:
                    break
                self.execute_node(statement)
                if self.return_flag:
                    self.symbol_table.pop_scope(label=f"switch case {case_value}")
                    return
            self.symbol_table.pop_scope(label=f"switch case {case_value}")

            
            if self.break_flag:
                self._log("  'Break' detectado en 'switch'. Saliendo.")
                self.break_flag = False
                self.switch_fall_through = False
                self._log("Finalizado 'switch'.")
                return
    
     # Procesar caso default si no hubo coincidencia o estamos en fall-through
     if default_case and (self.switch_fall_through or not a_case_matched):
        self._log(f"  Ejecutando bloque 'default'.")
        block_content = default_case.get("block", [])
        self.symbol_table.push_scope(label="switch default")
        for statement in block_content:
            if self.break_flag or self.return_flag:
                break
            self.execute_node(statement)
            if self.return_flag:
                self.symbol_table.pop_scope(label="switch default")
                return
        self.symbol_table.pop_scope(label="switch default")
    
     self.break_flag = False
     self.switch_fall_through = False
     self._log("Finalizado 'switch'.")
def main():
    global debug_mode_g

    # Parsear argumentos: -d activa debug, lo demás es el archivo
    json_file_path = None
    for arg in sys.argv[1:]:
        if arg in ('-d', '--d', '--debug'):
            debug_mode_g = True
        elif json_file_path is None:
            json_file_path = arg

    if json_file_path is None:
        print("Uso: python interpre.py [-d] <ruta_al_archivo_json|.tsslk|.tbc>")
        sys.exit(1)

    # ── Cargar AST según la extensión del archivo ─────────────────────────
    if json_file_path.endswith('.tsslk') or json_file_path.endswith('.tbc'):
        # Bytecode Tesseract → decodificar con tsslk_decoder
        try:
            from tsslk_decoder import decode_tbc
            ast_data = decode_tbc(json_file_path)
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo '{json_file_path}'.")
            return
        except Exception as e:
            print(f"Error al decodificar bytecode: {e}")
            import traceback; traceback.print_exc()
            return
    else:
        # JSON AST normal
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                ast_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo '{json_file_path}'.")
            return
        except json.JSONDecodeError:
            print(f"Error: El archivo JSON en '{json_file_path}' está mal formado.")
            return
 
    interpreter = Interpreter(debug_mode=debug_mode_g)
    import time
    inicio = time.perf_counter()  # Usar perf_counter para mayor precisión
    
    try:
        interpreter.interpret(ast_data, source_path=json_file_path)
        
        # Calcular tiempo transcurrido
        fin = time.perf_counter()
        tiempo_transcurrido = fin - inicio
        if interpreter.debug_mode: 
        # Mostrar tiempo de ejecución con diferentes niveles de precisión
         print(f"\n⏱️  Tiempo de ejecución total:")
        
         if tiempo_transcurrido < 0.001:  # Menos de 1 milisegundo
            microsegundos = tiempo_transcurrido * 1_000_000
            print(f"   {microsegundos:.2f} microsegundos")
         elif tiempo_transcurrido < 1:  # Menos de 1 segundo
            milisegundos = tiempo_transcurrido * 1_000
            print(f"   {milisegundos:.2f} milisegundos")
         else:
            # Para tiempos mayores a 1 segundo, mostrar formato completo
            horas = int(tiempo_transcurrido // 3600)
            minutos = int((tiempo_transcurrido % 3600) // 60)
            segundos = tiempo_transcurrido % 60
            
            if horas > 0:
                print(f"   {horas}h {minutos}m {segundos:.3f}s")
            elif minutos > 0:
                print(f"   {minutos}m {segundos:.3f}s")
            else:
                print(f"   {segundos:.6f} segundos")
        
         # Mostrar siempre el total en segundos con alta precisión
         print(f"   (Total: {tiempo_transcurrido:.9f} segundos)")
        
         if interpreter.debug_mode:
            print("\n==============================================")
            print("--- Estado final de la Tabla de Símbolos ---")
            print("==============================================")
            print(interpreter.symbol_table)
            print("\n==============================================")
            print("--- Tabla de Structs ---")
            print("==============================================")
            print(interpreter.struct_table)
            # Mostrar instancias de struct en el scope global
            _struct_instances_found = False
            for scope_i, scope in enumerate(interpreter.symbol_table.symbols):
                for vname, sym in scope.items():
                    if isinstance(sym.value, StructInstance):
                        if not _struct_instances_found:
                            print("\n  Instancias de Struct (scope global):")
                            _struct_instances_found = True
                        print(f"    [{vname}] → {sym.value.format_print(vname)}")
            print("\n==============================================")
            print("--- Tabla de Objetos (OOP) ---")
            print("==============================================")
            print(interpreter.object_table)
            if interpreter._async_functions:
                print("\n--- Funciones Async declaradas ---")
                print(" ", sorted(interpreter._async_functions))
            if interpreter._async_tasks:
                print(f"\n--- Tareas async pendientes: {len(interpreter._async_tasks)} ---")
            
    except InterpreterError as e:
        # También mostrar tiempo incluso si hay error
        fin = time.perf_counter()
        tiempo_transcurrido = fin - inicio
        
        print(f"\n❌ ERROR DURANTE LA EJECUCIÓN: {e}")
        print(f"⏱️  Tiempo transcurrido hasta el error: {tiempo_transcurrido:.6f} segundos")
        print("==============================================")
        print("--- Estado final de la Tabla de Símbolos ---")
        print("==============================================")
        print(interpreter.symbol_table)

if __name__ == "__main__":
    main()