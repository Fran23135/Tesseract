# =============================================================================
# tesscodegen.py — Tesseract LLVM IR Code Generator
# =============================================================================
# Recorre el JSON AST usando el CompileContext de tessruntime.py.
# Por cada nodo emite instrucciones LLVM IR via llvmlite.
#
# Manejo de tipos:
#   - Tipos estáticos conocidos (int, float, bool, string) → tipos LLVM nativos
#   - Tipo dinámico (any / dynamic) → struct TessValue del runtime C
#
# Runtime C (tess_runtime.c / tess_runtime.h) provee:
#   - TessValue: tagged union para valores dinámicos
#   - tess_print, tess_read, tess_concat
#   - tess_array_*, tess_dict_*
#   - tess_op_add, tess_op_sub, etc. para operaciones dinámicas
# =============================================================================

from __future__ import annotations

import os
import sys
import ujson as json
from typing import Any, Dict, List, Optional, Tuple
from tessruntime import TessTypeInfo
try:
    import llvmlite.ir as ir
    import llvmlite.binding as llvm
except ImportError:
    print("ERROR: llvmlite no está instalado. Ejecuta: pip install llvmlite")
    sys.exit(1)

import re
# REEMPLAZAR la línea de import existente con:
from tessruntime import (
    CompileContext, TessType, TessSymbol, TessFunction, TessClass, TessMethod,
    TessAttribute, TessInterface, NewObjectNode, MethodCallNode, AttrAccessNode,
    ThisAccessNode, ThisCallNode, SuperCallNode, TryCatchNode,
    ExprNode, LiteralNode, VarNode, BinOpNode, UnaryNode,
    ConcatNode, FuncCallNode, ModCallNode, ModVarNode,
    ArrayAccessNode, LogicalNode, NullNode, analyze_ast, analyze_ast_file,CoreCallNode,_CORE_METHODS, _CORE_MUTABLE_DEFAULT,
    ArrayLiteralNode, DictLiteralNode
)

# =============================================================================
# Sistema de Tipos LLVM
# =============================================================================

class LLVMTypes:
    """
    Mapea TessType a tipos LLVM IR.
    El tipo dinámico usa un puntero a TessValue (struct del runtime C).
    """

    def __init__(self, module: ir.Module):
        self.module = module
        self._init_tess_value(module)

    def _init_tess_value(self, module: ir.Module):
        """
        Define el struct TessValue en IR.
        Equivale a:
          struct TessValue {
              i32 tag;         // 0=null 1=int 2=float 3=bool 4=string 5=array 6=dict
              i64 data;        // interpretado según tag (int/float/ptr)
          };
        Usamos i64 para el campo data — suficiente para int64, double y punteros.
        """
        self.tess_value_t = module.context.get_identified_type("TessValue")
        if not self.tess_value_t.elements:
            self.tess_value_t.set_body(
                ir.IntType(32),   # tag
                ir.IntType(64),   # data (int/float bits/ptr)
            )
        self.tess_value_ptr_t = self.tess_value_t.as_pointer()

    # ── mapeo de tipos ───────────────────────────────────────────────────────

    def llvm_type(self, ttype: TessType) -> ir.Type:
        mapping = {
            TessType.INT:     ir.IntType(64),
            TessType.FLOAT:   ir.DoubleType(),
            TessType.BOOL:    ir.IntType(1),
            TessType.STRING:  ir.IntType(8).as_pointer(),   # char*
            TessType.NULL:    ir.IntType(64),
            TessType.VOID:    ir.VoidType(),
            TessType.DYNAMIC: self.tess_value_ptr_t,
            TessType.ARRAY:   self.tess_value_ptr_t,
            TessType.DICT:    self.tess_value_ptr_t,
        }
        return mapping.get(ttype, self.tess_value_ptr_t)

    def is_dynamic(self, ttype: TessType) -> bool:
        return ttype in (TessType.DYNAMIC, TessType.ARRAY, TessType.DICT)

    # ── constantes de tag para TessValue ────────────────────────────────────
    TAG_NULL   = ir.Constant(ir.IntType(32), 0)
    TAG_INT    = ir.Constant(ir.IntType(32), 1)
    TAG_FLOAT  = ir.Constant(ir.IntType(32), 2)
    TAG_BOOL   = ir.Constant(ir.IntType(32), 3)
    TAG_STRING = ir.Constant(ir.IntType(32), 4)
    TAG_ARRAY  = ir.Constant(ir.IntType(32), 5)
    TAG_DICT   = ir.Constant(ir.IntType(32), 6)


# =============================================================================
# Declaraciones del Runtime C
# =============================================================================

class RuntimeAPI:
    """
    Declara en el módulo IR todas las funciones del runtime C (tess_runtime.c).
    tesscodegen.py las llama con `builder.call(fn, args)` cuando necesita
    manejar operaciones dinámicas.
    """

    def __init__(self, module: ir.Module, types: LLVMTypes):
        self.module = module
        self.types  = types
        self.funcs: Dict[str, ir.Function] = {}
        self._declare_all()

    def _decl(self, name: str, ret: ir.Type, *args: ir.Type) -> ir.Function:
        fn_type = ir.FunctionType(ret, list(args))
        fn = ir.Function(self.module, fn_type, name=name)
        self.funcs[name] = fn
        return fn

    def _declare_all(self):
        tv  = self.types.tess_value_ptr_t
        i64 = ir.IntType(64)
        i32 = ir.IntType(32)
        i8p = ir.IntType(8).as_pointer()
        dbl = ir.DoubleType()
        i1  = ir.IntType(1)
        void= ir.VoidType()
        ti8p = ir.IntType(8).as_pointer()

        # ── I/O ──────────────────────────────────────────────────────────────
        self._decl("tess_print_int",    void, i64)
        self._decl("tess_print_float",  void, dbl)
        self._decl("tess_print_bool",   void, i1)
        self._decl("tess_print_string", void, i8p)
        self._decl("tess_print_value",  void, tv)    # dinámico
        self._decl("tess_print_null",   void)

        self._decl("tess_read_string",  i8p)
        self._decl("tess_read_int",     i64)
        self._decl("tess_read_float",   dbl)

        # ── Construcción de TessValue ─────────────────────────────────────────
        self._decl("tess_make_int",    tv, i64)
        self._decl("tess_make_float",  tv, dbl)
        self._decl("tess_make_bool",   tv, i1)
        self._decl("tess_make_string", tv, i8p)
        self._decl("tess_make_null",   tv)

        # ── Operaciones dinámicas (TessValue op TessValue) ───────────────────
        self._decl("tess_add",   tv, tv, tv)
        self._decl("tess_sub",   tv, tv, tv)
        self._decl("tess_mul",   tv, tv, tv)
        self._decl("tess_div",   tv, tv, tv)
        self._decl("tess_mod",   tv, tv, tv)
        self._decl("tess_eq",    tv, tv, tv)
        self._decl("tess_neq",   tv, tv, tv)
        self._decl("tess_lt",    tv, tv, tv)
        self._decl("tess_gt",    tv, tv, tv)
        self._decl("tess_lte",   tv, tv, tv)
        self._decl("tess_gte",   tv, tv, tv)
        self._decl("tess_and",   tv, tv, tv)
        self._decl("tess_or",    tv, tv, tv)
        self._decl("tess_not",   tv, tv)
        self._decl("tess_neg",   tv, tv)
        self._decl("tess_concat",tv, tv, tv)   # concatenación con punto

        # ── Arrays ───────────────────────────────────────────────────────────
        self._decl("tess_array_new",    tv)
        self._decl("tess_array_push",   void, tv, tv)
        self._decl("tess_array_get",    tv, tv, i64)
        self._decl("tess_array_set",    void, tv, i64, tv)
        self._decl("tess_array_len",    i64, tv)
        self._decl("tess_array_new_typed",  tv, i32, i64)
        
        # ── Tuplas ────────────────────────────────────────────────────────────
        
        self._decl("tess_tuple_new",        tv)
        self._decl("tess_tuple_new_typed",  tv, ti8p)
        self._decl("tess_tuple_push",       void, tv, tv)
        self._decl("tess_tuple_get",        tv, tv, i64)
        self._decl("tess_tuple_len",        i64, tv)
       

        # ── Diccionarios ─────────────────────────────────────────────────────
        self._decl("tess_dict_new",     tv)
        self._decl("tess_dict_get",     tv, tv, i8p)
        self._decl("tess_dict_set",     void, tv, i8p, tv)
        self._decl("tess_dict_has",     i1, tv, i8p)
        self._decl("tess_dict_new_typed",   tv, i32, i32)
        
        # ── Validación de tipo de elemento (usada en push/set tipados) ────────
        self._decl("tess_check_elem_type",  i1, tv, i32)
        # retorna 1 si el TessValue tiene el tag esperado

        # ── Conversiones ─────────────────────────────────────────────────────
        self._decl("tess_to_int",       i64, tv)
        self._decl("tess_to_float",     dbl, tv)
        self._decl("tess_to_bool",      i1,  tv)
        self._decl("tess_to_string",    i8p, tv)
        self._decl("tess_value_truthy", i1,  tv)   # para condiciones dinámicas

        # ── Incremento/decremento dinámico ───────────────────────────────────
        self._decl("tess_inc", tv, tv)
        self._decl("tess_dec", tv, tv)
        # ── TessTypeInfo — construcción de tipos anidados ─────────────────────
        # TessTypeInfo* se pasa como i8*
        self._decl("tess_typeinfo_new",         ti8p, i32)
        # tess_typeinfo_new(tag) → TessTypeInfo*

        self._decl("tess_typeinfo_set_inner",   void, ti8p, ti8p)
        # tess_typeinfo_set_inner(parent, inner)

        self._decl("tess_typeinfo_set_key_val", void, ti8p, ti8p, ti8p)
        # tess_typeinfo_set_key_val(dict_ti, key_ti, val_ti)

        self._decl("tess_typeinfo_set_limit",   void, ti8p, i64)
        # tess_typeinfo_set_limit(ti, limit)
        # AGREGAR al final de _declare_all antes del cierre:

        # ── OOP — TessObject ─────────────────────────────────────────────────
        # TessObject* se representa como i8* (puntero opaco al struct C)
        obj = ir.IntType(8).as_pointer()

        self._decl("tess_object_new",       obj, i8p)
        # tess_object_new(class_name) → TessObject*

        self._decl("tess_object_get_attr",  tv,  obj, i8p)
        # tess_object_get_attr(obj, attr_name) → TessValue*

        self._decl("tess_object_set_attr",  void, obj, i8p, tv)
        # tess_object_set_attr(obj, attr_name, value)

        self._decl("tess_object_call",      tv,  obj, i8p, tv, i64)
        # tess_object_call(obj, method_name, args_array, args_count) → TessValue*

        self._decl("tess_object_is_instance", i1, obj, i8p)
        # tess_object_is_instance(obj, class_name) → i1

        # ── Excepciones ────────────────────────────────────────────────────────
        self._decl("tess_exception_new",    tv,  i8p, i8p)
        # tess_exception_new(class_name, message) → TessValue* (tag especial)

        self._decl("tess_exception_class",  i8p, tv)
        # tess_exception_class(exc) → char* nombre de la clase

        self._decl("tess_exception_message",i8p, tv)
        # tess_exception_message(exc) → char* mensaje

        # setjmp/longjmp para try-catch (wrapeados por el runtime)
        self._decl("tess_try_begin",        i32)
        # tess_try_begin() → int (0 = en try, != 0 = en catch con código)

        self._decl("tess_throw",            void, tv)
        # tess_throw(exc_value) — no retorna (longjmp)

        self._decl("tess_catch_get",        tv)
        # tess_catch_get() → TessValue* excepción capturada

        self._decl("tess_try_end",          void)
        # tess_try_end() — limpia el frame de excepción

        # ── Pre-declarar TODOS los _tess_mod_{tipo}_{metodo} ─────────────────
        # Si se declaran de forma lazy (dentro de _emit_core_chain) aparecen
        # DESPUÉS del cuerpo de @main en el IR. Declararlos aquí los fija al
        # principio del módulo, antes de cualquier función.
        _max_args: Dict[str, int] = {}   # method → máx extra_argc entre tipos
        for type_name, methods in _CORE_METHODS.items():
            for method_name, extra_argc in methods.items():
                mangled = f"_tess_mod_{type_name}_{method_name}"
                if mangled not in self.funcs:
                    self._decl(mangled, tv, *([tv] * (1 + extra_argc)))
                _max_args[method_name] = max(
                    _max_args.get(method_name, 0), extra_argc
                )

        # Dynamic dispatchers: _tess_mod_dynamic_{metodo}
        # Se usan cuando el tipo de la variable es DYNAMIC en tiempo de compilación.
        for method_name, extra_argc in _max_args.items():
            mangled = f"_tess_mod_dynamic_{method_name}"
            if mangled not in self.funcs:
                self._decl(mangled, tv, *([tv] * (1 + extra_argc)))

    def get(self, name: str) -> ir.Function:
        if name not in self.funcs:
            raise KeyError(f"Función de runtime '{name}' no declarada")
        return self.funcs[name]


# =============================================================================
# Generador de IR
# =============================================================================

class CodeGen:
    """
    Recorre el JSON AST (con ayuda del CompileContext de tessruntime)
    y emite LLVM IR para cada nodo.

    Estructura de datos internas durante la emisión:
      _ir_vars   : {nombre -> AllocaInstr}  — variables del scope actual
      _ir_funcs  : {nombre -> ir.Function}  — funciones Tesseract en IR
      _scope_stack: [dict] — stack de scopes de vars IR
    """

    def __init__(self, ctx: CompileContext, module_name: str = "tesseract_module"):
        self.ctx       = ctx
        self.module    = ir.Module(name=module_name)
        self.module.triple = llvm.get_default_triple()

        self.types     = LLVMTypes(self.module)
        self.runtime   = RuntimeAPI(self.module, self.types)
        self._str_counter = 0

        self._scope_stack: List[Dict[str, Any]] = [{}]   # [0] = global
        self._ir_funcs:    Dict[str, ir.Function] = {}
        self._builder:     Optional[ir.IRBuilder]  = None
        self._current_func_name: Optional[str]     = None
        self._global_vars: Dict[str, ir.GlobalVariable] = {}

        # Bloques de control de flujo
        self._break_target:  Optional[ir.Block] = None
        self._return_alloca: Optional[Any]       = None
        self._return_block:  Optional[ir.Block]  = None

    # ── scopes de IR ─────────────────────────────────────────────────────────

    def _push_scope(self):
        self._scope_stack.append({})

    def _pop_scope(self):
        if len(self._scope_stack) > 1:
            self._scope_stack.pop()

    def _declare_ir_var(self, name: str, alloca: Any):
        self._scope_stack[-1][name] = alloca

    def _lookup_ir_var(self, name: str) -> Optional[Any]:
        for scope in reversed(self._scope_stack):
            if name in scope:
                return scope[name]
        # Si no está en scopes locales, buscar en globales
        return self._global_vars.get(name)
    # AGREGAR como método en CodeGen, llamado desde generate() antes de _predeclare_functions:

    def _predeclare_native_module_functions(self):
     """
     Pre-declara como funciones LLVM externas todas las funciones y
     métodos de clases que existan en los módulos nativos cargados.
     """
     obj_ptr_t = ir.IntType(8).as_pointer()
     tv        = self.types.tess_value_ptr_t

     for mod_name, mod_obj in self.ctx.symbol_table.all_modules().items():
        if mod_obj.is_source:
            continue

        # Funciones libres del módulo
        for fname, fn_info in mod_obj.mod_functions.items():
            mangled = f"_tess_mod_{mod_obj.name}_{fname}"
            if mangled not in self.module.globals:
                ret_llvm   = self.types.llvm_type(fn_info.return_type)
                arg_types  = [tv] * len(fn_info.params)
                fn_type    = ir.FunctionType(ret_llvm, arg_types)
                ir.Function(self.module, fn_type, name=mangled)

        # Métodos de clases nativas
        for cname, cls_info in mod_obj.classes.items():
            for mname, meth_info in cls_info.methods.items():
                mangled = f"_tess_mod_{mod_obj.name}_{cname}__{mname}"
                if mangled not in self.module.globals:
                    ret_llvm   = self.types.llvm_type(meth_info.return_type)
                    # primer arg es TessObject* (i8*)
                    arg_types  = [obj_ptr_t] + [tv] * len(meth_info.params)
                    fn_type    = ir.FunctionType(ret_llvm, arg_types)
                    ir.Function(self.module, fn_type, name=mangled)
    
    def _emit_native_module_non_native_functions(self):
     """
     Emite IR para las funciones de módulo que tienen 'native': false
     y un 'block' definido en el .tmd (ej: math.clamp, math.max, math.min).
     Se trata igual que una función de usuario — misma lógica que _emit_Function.
     """
     tv = self.types.tess_value_ptr_t

     for mod_name, mod_obj in self.ctx.symbol_table.all_modules().items():
        if mod_obj.is_source:
            continue

        for fname, fn_info in mod_obj.mod_functions.items():
            if fn_info.is_native or not fn_info.block:
                continue   # solo las que tienen bloque definido

            mangled = f"_tess_mod_{mod_name}_{fname}"
            ir_fn   = self.module.globals.get(mangled)
            if ir_fn is None:
                continue   # no fue pre-declarada, algo salió mal

            # Emitir el cuerpo
            entry_block = ir_fn.append_basic_block("entry")
            prev_builder = self._builder
            prev_func    = self._current_func_name

            self._builder = ir.IRBuilder(entry_block)
            self._current_func_name = mangled
            self._push_scope()

            # Registrar parámetros como variables locales
            for ir_arg, pname in zip(ir_fn.args, fn_info.params.keys()):
                ir_arg.name = pname
                alloca = self._alloca(pname, tv)
                self._builder.store(ir_arg, alloca)
                self._declare_ir_var(pname, alloca)

            # Alloca de retorno
            ret_alloca = self._alloca("ret_val", tv)
            self._return_alloca = ret_alloca
            ret_block = ir_fn.append_basic_block("ret")
            self._return_block = ret_block

            # Emitir los nodos del bloque
            self._emit_block(fn_info.block)

            # Saltar al bloque de retorno si no terminó
            if not self._builder.block.is_terminated:
                self._builder.branch(ret_block)

            # Bloque de retorno
            self._builder.position_at_end(ret_block)
            ret_val = self._builder.load(ret_alloca, "ret_load")
            self._builder.ret(ret_val)

            self._pop_scope()
            self._builder            = prev_builder
            self._current_func_name  = prev_func
            self._return_alloca      = None
            self._return_block       = None
    def _emit_type_info(self, ti: 'TessTypeInfo') -> Any:
     """
     Emite las llamadas al runtime C para construir un TessTypeInfo* anidado.
     Retorna un i8* (puntero opaco al TessTypeInfo C creado en heap).
     """
     from tessruntime import TessTypeInfo as TI

     tag_map = {
        TessType.NULL:    0, TessType.INT:   1, TessType.FLOAT: 2,
        TessType.BOOL:    3, TessType.STRING:4, TessType.ARRAY: 5,
        TessType.DICT:    6, TessType.TUPLE: 7, TessType.DYNAMIC:-1,
     }
     tag_val = tag_map.get(ti.tag, -1)
     tag_ir  = ir.Constant(ir.IntType(32), tag_val)

     # Crear el TessTypeInfo base
     ti_ptr = self._builder.call(self.runtime.get("tess_typeinfo_new"), [tag_ir])

     # Límite
     if ti.limit >= 0:
        lim_ir = ir.Constant(ir.IntType(64), ti.limit)
        self._builder.call(self.runtime.get("tess_typeinfo_set_limit"), [ti_ptr, lim_ir])

     # Tipo interno para array/tuple: inner
     if ti.inner is not None:
        inner_ptr = self._emit_type_info(ti.inner)
        self._builder.call(
            self.runtime.get("tess_typeinfo_set_inner"), [ti_ptr, inner_ptr])

     # Tipos de clave y valor para dict
     if ti.key_type is not None and ti.val_type is not None:
        key_ptr = self._emit_type_info(ti.key_type)
        val_ptr = self._emit_type_info(ti.val_type)
        self._builder.call(
            self.runtime.get("tess_typeinfo_set_key_val"), [ti_ptr, key_ptr, val_ptr])

     return ti_ptr

    # ── helpers de builder ───────────────────────────────────────────────────
    def _default_initializer(self, llvm_type: ir.Type) -> ir.Constant:
     """Devuelve un valor inicial por defecto (cero o nulo) para el tipo dado."""
     if isinstance(llvm_type, ir.PointerType):
        return ir.Constant(llvm_type, None)   # null
     if llvm_type == ir.IntType(64):
        return ir.Constant(ir.IntType(64), 0)
     if llvm_type == ir.DoubleType():
        return ir.Constant(ir.DoubleType(), 0.0)
     if llvm_type == ir.IntType(1):
        return ir.Constant(ir.IntType(1), 0)
     return ir.Constant(llvm_type, 0)
    def _alloca(self, name: str, llvm_type: ir.Type) -> Any:
     """
     Emite alloca en la posición actual del builder.
     generate() llama a todos los _alloca de globales en el paso 1,
     antes de cualquier store u otra instrucción, así que quedan
     al inicio del entry block sin necesidad de reordenar.
     """
     return self._builder.alloca(llvm_type, name=name)
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



    def _str_const(self, s: str) -> Any:
        """Crea una constante string global y retorna un i8* a ella."""
        encoded = (s + '\0').encode('utf-8')
        str_type = ir.ArrayType(ir.IntType(8), len(encoded))
        self._str_counter += 1
        gvar = ir.GlobalVariable(self.module, str_type, name=f".str.{self._str_counter}")
        gvar.global_constant = True
        gvar.initializer = ir.Constant(str_type, bytearray(encoded))
        zero = ir.Constant(ir.IntType(32), 0)
        return self._builder.gep(gvar, [zero, zero], inbounds=True, name="str")

    # ── punto de entrada ─────────────────────────────────────────────────────

    def generate(self, ast: dict) -> str:
     program_nodes = ast.get("Program", [])
     global_symbols = self.ctx.symbol_table.all_globals()

     # 1. Declarar todas las variables globales con inicializador neutro.
     #    Solo la declaración — el valor real se asigna en main en orden.
     for name, sym in global_symbols.items():
        if sym.is_explicit_type:
            llvm_type = self.types.llvm_type(sym.ttype)
        else:
            llvm_type = self.types.tess_value_ptr_t
        gvar = ir.GlobalVariable(self.module, llvm_type, name=name)
        gvar.global_constant = False
        gvar.initializer = self._default_initializer(llvm_type)
        self._global_vars[name] = gvar
        self._declare_ir_var(name, gvar)
        

     # 2. Pre-declarar funciones (forward declarations para permitir
     #    llamadas antes de la definición, igual que interpre.py).
   
     self._predeclare_native_module_functions()
     self._emit_native_module_non_native_functions()
     self._predeclare_functions(program_nodes)
     # 3. Crear main
     main_type = ir.FunctionType(ir.IntType(32), [])
     has_entry = any(fn.is_entry_point for fn in self.ctx.get_all_functions().values())
     prologue_name = "main" if has_entry else "main"
     main_fn = ir.Function(self.module, main_type, name=prologue_name)
     entry     = main_fn.append_basic_block("entry")
     self._builder = ir.IRBuilder(entry)
     self._current_func_name = "main"

     # 4. Un solo loop en orden secuencial — igual que el intérprete.
     #    Variables: inicializar en el punto donde aparecen.
     #    Funciones: emitir su cuerpo (ya predeclaradas, solo se llena el body).
     #    Todo lo demás: emitir directo.
     i = 0
     while i < len(program_nodes):
        if self._builder.block.is_terminated:
            break
        node      = program_nodes[i]
        node_type = list(node.keys())[0]

        # WhileLoop puede llevar el bloque en el nodo siguiente
        if node_type == "WhileLoop":
            if i + 1 < len(program_nodes) and "Block" in program_nodes[i + 1]:
                node["WhileLoop"]["block"] = program_nodes[i + 1]["Block"]
                i += 2
                self._emit_node(node)
                continue

        # SwitchStatement igual
        if node_type == "SwitchStatement":
            if i + 1 < len(program_nodes) and "block" in program_nodes[i + 1]:
                node["SwitchStatement"]["cases"] = program_nodes[i + 1].get("cases", [])
                i += 2
                self._emit_node(node)
                continue

        # VariableDeclaration / ConstantDeclaration:
        # emitir la inicialización aquí mismo, en orden, dentro de main.
        if node_type in ("VariableDeclaration", "ConstantDeclaration"):
            var_node   = node[node_type]
            name       = var_node["name"]
            value_node = var_node.get("value", {})
            gvar       = self._global_vars.get(name)
            sym        = self.ctx.symbol_table.lookup(name)
            ttype      = sym.ttype if sym else TessType.DYNAMIC

            if gvar is not None and value_node:
                init_val = self._emit_value_node(value_node, ttype)
                if init_val is not None:
                    if sym and sym.is_explicit_type:
                        init_val = self._coerce_to_type(init_val, ttype)
                    else:
                        init_val = self._to_tess_value(init_val)
                    self._builder.store(init_val, gvar)
            i += 1
            continue

        # Function: emitir su cuerpo (no va en main, se emite como
        # función LLVM separada igual que _emit_Function ya hace).
        # El builder de main se restaura automáticamente dentro de _emit_Function.
        if node_type == "Function":
            self._emit_node(node)
            i += 1
            continue

        # Todo lo demás: expresiones, prints, llamadas, loops, ifs…
        self._emit_node(node)
        i += 1

     # 5. Cerrar main
     if not self._builder.block.is_terminated:
    # Si hay entry point: el prólogo llama a la función del usuario y retorna
        entry_fn = next(
        (fn for fn in self.ctx.get_all_functions().values() if fn.is_entry_point),
        None
        )
     if entry_fn:
        ir_entry = self._ir_funcs.get(entry_fn.name)
        if ir_entry:
            # Llamar a la función ->target main y usar su retorno como exit code
            call_ret = self._builder.call(ir_entry, [], "entry_ret")
            # Convertir el retorno a i32 para main de LLVM
            ret_type = self.types.llvm_type(entry_fn.return_type)
            if ret_type == ir.IntType(32):
                self._builder.ret(call_ret)
            elif ret_type == ir.IntType(64):
                trunc = self._builder.trunc(call_ret, ir.IntType(32), "ret_trunc")
                self._builder.ret(trunc)
            else:
                self._builder.ret(ir.Constant(ir.IntType(32), 0))
        else:
            self._builder.ret(ir.Constant(ir.IntType(32), 0))
     else:
        self._builder.ret(ir.Constant(ir.IntType(32), 0))



     return str(self.module)
    
    def _predeclare_functions(self, program_nodes: list):
     for node in program_nodes:
        node_type = list(node.keys())[0]
        if node_type == "Function":
            self._declare_function_ir(node["Function"])
        elif node_type == "ClassDeclaration":
            cls_node   = node["ClassDeclaration"]
            class_name = cls_node.get('name', '')
            tess_cls   = self.ctx.get_class(class_name)
            if tess_cls:
                for mname, method in tess_cls.methods.items():
                    self._predeclare_method(class_name, mname, method)
                if tess_cls.constructor:
                    self._predeclare_method(class_name, '__init__', tess_cls.constructor)
    def _predeclare_method(self, class_name: str, method_name: str, method: 'TessMethod'):
     """Forward-declara un método como función LLVM mangled sin emitir el cuerpo."""
     mangled   = f"{class_name}__{method_name}"
     obj_ptr_t = ir.IntType(8).as_pointer()
     param_types = [obj_ptr_t] + [self.types.llvm_type(pt) for pt in method.params.values()]
     ret_llvm    = self.types.llvm_type(method.return_type)
     fn_type     = ir.FunctionType(ret_llvm, param_types)
     ir_fn = ir.Function(self.module, fn_type, name=mangled)
     ir_fn.args[0].name = "self"
     for ir_arg, pname in zip(ir_fn.args[1:], method.params.keys()):
        ir_arg.name = pname
     self._ir_funcs[mangled] = ir_fn
    def _declare_function_ir(self, fn_node: dict):
        """Declara una función Tesseract en LLVM IR (sin emitir el cuerpo todavía)."""
        tess_fn = self.ctx.get_function(fn_node["name"])
        if tess_fn is None:
            return  # no fue analizada (no debería pasar)

        # Construir la firma LLVM
        param_types = [self.types.llvm_type(pt) for pt in tess_fn.params.values()]
        ret_llvm    = self.types.llvm_type(tess_fn.return_type)
        fn_type     = ir.FunctionType(ret_llvm, param_types)

        llvm_name = "main_usr" if tess_fn.is_entry_point else tess_fn.name
        ir_fn = ir.Function(self.module, fn_type, name=llvm_name)
        # Nombrar los parámetros
        for ir_param, pname in zip(ir_fn.args, tess_fn.params.keys()):
            ir_param.name = pname

        self._ir_funcs[tess_fn.name] = ir_fn

    # ── despacho de nodos — mismo patrón que execute_node en interpre.py ─────

    def _emit_node(self, node: dict):
        if not node:
            return
        if self._builder.block.is_terminated:
            return  # No emitir más después de un terminator
        node_type = list(node.keys())[0]
        emitter = getattr(self, f"_emit_{node_type}", self._emit_unknown)
        
        return emitter(node[node_type])

    def _emit_block(self, block: List[dict]):
        for stmt in block:
            if self._builder.block.is_terminated:
                break
            self._emit_node(stmt)

    # ── emisores por nodo ─────────────────────────────────────────────────────

    def _emit_VariableDeclaration(self, node: dict):
        name       = node["name"]
        value_node = node.get("value", {})
        tess_sym   = self.ctx.symbol_table.lookup(name)
        ttype      = tess_sym.ttype if tess_sym else TessType.DYNAMIC
        if name in self._global_vars:
            # La variable global ya fue creada; la inicialización se hará aparte
            # No creamos alloca
            return
        if tess_sym and tess_sym.is_explicit_type:
            llvm_type = self.types.llvm_type(ttype)
        else:
            llvm_type = self.types.tess_value_ptr_t


        alloca = self._alloca(name, llvm_type)
        self._declare_ir_var(name, alloca)

        # Emitir el valor inicial y almacenarlo
        init_val = self._emit_value_node(value_node, ttype)
        if init_val is not None:
        # Convertir al tipo de la variable
            if tess_sym and tess_sym.is_explicit_type:
                init_val = self._coerce_to_type(init_val, ttype)
            else:
                init_val = self._to_tess_value(init_val)
            self._builder.store(init_val, alloca)

    def _emit_VariableAsignement(self, node: dict):
        name       = node["name"]
        value_node = node.get("value", {})
        alloca     = self._lookup_ir_var(name)
        if alloca is None:
            
            alloca = self._global_vars.get(name)
            if alloca is None:
                # Declaración implícita local
                llvm_type = self.types.tess_value_ptr_t
                alloca = self._alloca(name, llvm_type)
                self._declare_ir_var(name, alloca)

        tess_sym = self.ctx.symbol_table.lookup(name)
        ttype    = tess_sym.ttype if tess_sym else TessType.DYNAMIC
        val      = self._emit_value_node(value_node, ttype)
        if val is not None:
            if tess_sym and tess_sym.is_explicit_type:
                val = self._coerce_to_type(val, ttype)
            else:
                val = self._to_tess_value(val)
            self._builder.store(val, alloca)

    def _emit_ConstantDeclaration(self, node: dict):
        # Misma lógica que VariableDeclaration pero marcado is_const
        self._emit_VariableDeclaration(node)

    def _emit_Function(self, fn_node: dict):
        """
        Emite el cuerpo de una función Tesseract.
        La declaración ya fue hecha en _predeclare_functions.
        """
        name    = fn_node["name"]
        tess_fn = self.ctx.get_function(name)
        ir_fn   = self._ir_funcs.get(name)
        if ir_fn is None or tess_fn is None:
            return

        # Guardar estado del builder actual
        old_builder      = self._builder
        old_func_name    = self._current_func_name
        old_scope        = self._scope_stack[:]
        old_break        = self._break_target
        old_ret_alloca   = self._return_alloca
        old_ret_block    = self._return_block

        # Nuevo scope para la función
        self._push_scope()
        self._current_func_name = name
        self._break_target = None

        # Entry block
        entry_block = ir_fn.append_basic_block("entry")
        self._builder = ir.IRBuilder(entry_block)

        # Bloque de retorno (epilogo)
        ret_block = ir_fn.append_basic_block("func_return")
        self._return_block = ret_block

        # Alloca para el valor de retorno (si no es void)
        if tess_fn.return_type != TessType.VOID:
            ret_type = self.types.llvm_type(tess_fn.return_type)
            self._return_alloca = self._alloca("retval", ret_type)
        else:
            self._return_alloca = None

        # Materializar parámetros: alloca + store para cada param
        for ir_param, (pname, ptype) in zip(ir_fn.args, tess_fn.params.items()):
            llvm_type = self.types.llvm_type(ptype)
            alloca    = self._alloca(pname, llvm_type)
            self._builder.store(ir_param, alloca)
            self._declare_ir_var(pname, alloca)

        # Emitir el cuerpo
        self._emit_block(tess_fn.body)

        # Saltar al bloque de retorno si el bloque actual no terminó
        if not self._builder.block.is_terminated:
            self._builder.branch(ret_block)

        # Emitir el bloque de retorno
        self._builder.position_at_start(ret_block)
        if tess_fn.return_type == TessType.VOID or self._return_alloca is None:
            self._builder.ret_void()
        else:
            ret_val = self._builder.load(self._return_alloca, "ret_load")
            self._builder.ret(ret_val)

        # Restaurar estado
        self._pop_scope()
        self._builder           = old_builder
        self._current_func_name = old_func_name
        self._scope_stack       = old_scope
        self._break_target      = old_break
        self._return_alloca     = old_ret_alloca
        self._return_block      = old_ret_block

    def _emit_FunctionCall(self, node: dict):
     fname      = node["function"]
     params_raw = node.get("paramenters", {})
     args       = self._emit_call_args(params_raw)
     ir_fn      = self._ir_funcs.get(fname)
     if ir_fn:
        tess_fn = self.ctx.get_function(fname)
        if tess_fn:
            param_types = list(tess_fn.params.values())
            converted_args = []
            for i, arg_val in enumerate(args):
                if i < len(param_types):
                    arg_val = self._coerce_to_type(arg_val, param_types[i])
                converted_args.append(arg_val)
            self._builder.call(ir_fn, converted_args)

    def _emit_CallExpression(self, node: dict):
        """
        Builtins: print, read, Return, Break y llamadas a módulo.
        Misma cobertura que handle_CallExpression en interpre.py.
        """
        fname = node.get("function", "")
        # ── Llamada con punto: puede ser mod.func() O var.coreMethod() ────────
        if isinstance(fname, str) and '.' in fname:
            # Extraer partes: "modulo.toUpperCase(old,new)" → var, method, inline_args
            m_fname = re.match(
                r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*(?:\((.*)\))?$',
                fname.strip(), re.DOTALL
            )
            if m_fname:
                left        = m_fname.group(1)
                method_name = m_fname.group(2)
                inline_args = m_fname.group(3)   # None si no hay paréntesis en fname

                known_modules = self.ctx.symbol_table.known_module_names()
                is_core = any(method_name in methods
                              for methods in _CORE_METHODS.values())

                # Si el lado izquierdo NO es un módulo cargado Y el método
                # existe en la tabla core → emitir como llamada core con self
                if left not in known_modules and is_core:
                    self._emit_core_call_from_fname(left, method_name,
                                                    inline_args, node)
                    return

            self._emit_module_call_from_node(node)
            return

        # ── Break ────────────────────────────────────────────────────────────
        if fname == "Break":
            if self._break_target:
                self._builder.branch(self._break_target)
            return

        # ── Return ───────────────────────────────────────────────────────────
        if fname == "Return":
            ret_node = node.get("value") or node.get("arguments") or {}
            ret_val  = None
            if "value" in ret_node:
                raw = ret_node["value"]
                if isinstance(raw, str):
                    expr    = self.ctx.parse_expression(raw)
                    ret_val = self._emit_expr(expr)
                elif isinstance(raw, (int, float, bool)):
                    ret_val = self._python_literal_to_ir(raw)

            if self._return_alloca is not None and ret_val is not None:
                # Obtener el tipo de retorno de la función actual
                tess_fn = self.ctx.get_function(self._current_func_name)
                if tess_fn:
                    ret_val = self._coerce_to_type(ret_val, tess_fn.return_type)
            self._builder.store(ret_val, self._return_alloca)
            if self._return_block:
                self._builder.branch(self._return_block)
            return

        # ── print ────────────────────────────────────────────────────────────
        if fname == "print":
            self._emit_print(node)
            return

        # ── read ─────────────────────────────────────────────────────────────
        if fname == "read":
            self._emit_read(node)
            return

        # ── función Tesseract declarada por el usuario ────────────────────────
        ir_fn = self._ir_funcs.get(fname)
        if ir_fn:
            args = self._emit_call_args(node.get("arguments", {}))
            self._builder.call(ir_fn, args)

    def _emit_LibraryCall(self, node: dict):
        """Los módulos no generan IR directamente — ya están registrados en ctx."""
        pass

    def _emit_if_Condition(self, node: dict):
        """
        if / elseif / else.
        Genera bloques básicos LLVM y conecta con br condicionales.
        """
        fn        = self._builder.function
        then_bb   = fn.append_basic_block("if_then")
        merge_bb  = fn.append_basic_block("if_merge")

        # Determinar si hay else o elseif
        has_else   = "else"   in node
        has_elseif = "elseIf" in node
        else_bb    = fn.append_basic_block("if_else") if (has_else or has_elseif) else merge_bb

        # Emitir condición
        cond_val = self._emit_condition(node["condition"])
        self._builder.cbranch(cond_val, then_bb, else_bb)

        # Bloque then
        self._builder.position_at_start(then_bb)
        self._push_scope()
        self._emit_block(node.get("block", []))
        self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(merge_bb)

        # Bloque else / elseif
        if has_else or has_elseif:
            self._builder.position_at_start(else_bb)
            if has_elseif:
                self._emit_elseif_chain(node["elseIf"], merge_bb)
            elif has_else:
                self._push_scope()
                self._emit_block(node["else"].get("block", []))
                self._pop_scope()
                if not self._builder.block.is_terminated:
                    self._builder.branch(merge_bb)

        self._builder.position_at_start(merge_bb)

    def _emit_elseif_chain(self, node: dict, merge_bb: ir.Block):
        fn      = self._builder.function
        then_bb = fn.append_basic_block("elseif_then")
        has_else   = "else"   in node
        has_elseif = "elseIf" in node
        next_bb = fn.append_basic_block("elseif_next") if (has_else or has_elseif) else merge_bb

        cond_val = self._emit_condition(node.get("condition") or node.get("value", "false"))
        self._builder.cbranch(cond_val, then_bb, next_bb)

        self._builder.position_at_start(then_bb)
        self._push_scope()
        self._emit_block(node.get("block", []))
        self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(merge_bb)

        if has_else or has_elseif:
            self._builder.position_at_start(next_bb)
            if has_elseif:
                self._emit_elseif_chain(node["elseIf"], merge_bb)
            else:
                self._push_scope()
                self._emit_block(node["else"].get("block", []))
                self._pop_scope()
                if not self._builder.block.is_terminated:
                    self._builder.branch(merge_bb)

    def _emit_ForLoop(self, node: dict):
        """
        for var in start..end
        Genera un loop LLVM clásico con bloques: preheader, header, body, exit.
        Misma lógica que handle_ForLoop en interpre.py.
        """
        var_name    = node["variable"]
        iterator    = node["iterator"]["value"]   # "1..10" o "start..end"
        fn          = self._builder.function

        # Parsear los límites del rango
        start_ir, end_ir = self._emit_range_bounds(iterator)

        # Alloca para la variable iteradora
        alloca = self._alloca(var_name, ir.IntType(64))
        self._builder.store(start_ir, alloca)

        # Bloques del loop
        header_bb = fn.append_basic_block("for_header")
        body_bb   = fn.append_basic_block("for_body")
        exit_bb   = fn.append_basic_block("for_exit")

        old_break       = self._break_target
        self._break_target = exit_bb

        self._builder.branch(header_bb)

        # Header: condición i <= end
        self._builder.position_at_start(header_bb)
        cur_val = self._builder.load(alloca, "for_cur")
        cond    = self._builder.icmp_signed("<=", cur_val, end_ir, "for_cond")
        self._builder.cbranch(cond, body_bb, exit_bb)

        # Body
        self._builder.position_at_start(body_bb)
        self._push_scope()
        self._declare_ir_var(var_name, alloca)
        self._emit_block(node.get("block", []))
        self._pop_scope()

        if not self._builder.block.is_terminated:
            # Incremento: i++
            cur_val2  = self._builder.load(alloca, "for_inc_cur")
            next_val  = self._builder.add(cur_val2, ir.Constant(ir.IntType(64), 1), "for_inc")
            self._builder.store(next_val, alloca)
            self._builder.branch(header_bb)

        self._break_target = old_break
        self._builder.position_at_start(exit_bb)

    def _emit_WhileLoop(self, node: dict):
        fn          = self._builder.function
        condition   = node["condition"]
        header_bb   = fn.append_basic_block("while_header")
        body_bb     = fn.append_basic_block("while_body")
        exit_bb     = fn.append_basic_block("while_exit")

        old_break          = self._break_target
        self._break_target = exit_bb

        self._builder.branch(header_bb)

        # Header: evaluar condición
        self._builder.position_at_start(header_bb)
        cond_val = self._emit_condition(condition)
        self._builder.cbranch(cond_val, body_bb, exit_bb)

        # Body
        self._builder.position_at_start(body_bb)
        self._push_scope()
        self._emit_block(node.get("block", []))
        self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(header_bb)

        self._break_target = old_break
        self._builder.position_at_start(exit_bb)

    def _emit_PerformWhileLoop(self, node: dict):
        """do-while: ejecuta el bloque al menos una vez."""
        fn        = self._builder.function
        condition = node["value"]
        body_bb   = fn.append_basic_block("dowhile_body")
        check_bb  = fn.append_basic_block("dowhile_check")
        exit_bb   = fn.append_basic_block("dowhile_exit")

        old_break          = self._break_target
        self._break_target = exit_bb

        self._builder.branch(body_bb)

        # Body (siempre se ejecuta al menos una vez)
        self._builder.position_at_start(body_bb)
        self._push_scope()
        self._emit_block(node.get("block", []))
        self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(check_bb)

        # Check: ¿repetir?
        self._builder.position_at_start(check_bb)
        cond_val = self._emit_condition(condition)
        self._builder.cbranch(cond_val, body_bb, exit_bb)

        self._break_target = old_break
        self._builder.position_at_start(exit_bb)

    def _emit_ClassDeclaration(self, node: dict):
        """
        Registra la clase en el módulo IR como un struct opaco.
        Los métodos se emiten como funciones LLVM con nombre mangled:
        ClassName__methodName
        """
        name    = node.get('name', '')
        tess_cls = self.ctx.get_class(name)
        if tess_cls is None:
            return

        # Definir el struct LLVM para la clase (opaco por ahora — el runtime C maneja el layout)
        # El IR solo necesita saber que existe; el runtime C sabe el layout real.
        # Los métodos se emiten como funciones normales con el primer parámetro siendo el objeto.

        # Emitir cuerpos de métodos
        for method_name, method in tess_cls.methods.items():
            self._emit_method_body(name, method_name, method)

        # Emitir constructor
        if tess_cls.constructor:
            self._emit_method_body(name, '__init__', tess_cls.constructor)

    def _emit_method_body(self, class_name: str, method_name: str, method: 'TessMethod'):
        """Emite el cuerpo de un método como función LLVM mangled: ClassName__methodName"""
        mangled   = f"{class_name}__{method_name}"
        obj_ptr_t = ir.IntType(8).as_pointer()  # TessObject*

        # Firma: (TessObject* self, params...) → ret
        param_types = [obj_ptr_t] + [self.types.llvm_type(pt) for pt in method.params.values()]
        ret_llvm    = self.types.llvm_type(method.return_type)
        fn_type     = ir.FunctionType(ret_llvm, param_types)

        ir_fn = ir.Function(self.module, fn_type, name=mangled)
        ir_fn.args[0].name = "self"
        for ir_arg, pname in zip(ir_fn.args[1:], method.params.keys()):
            ir_arg.name = pname

        self._ir_funcs[mangled] = ir_fn

        # Guardar estado
        old_builder   = self._builder
        old_func_name = self._current_func_name
        old_scope     = self._scope_stack[:]
        old_break     = self._break_target
        old_ret_alloca= self._return_alloca
        old_ret_block = self._return_block

        self._push_scope()
        self._current_func_name = mangled
        self._break_target = None

        entry_block = ir_fn.append_basic_block("entry")
        ret_block   = ir_fn.append_basic_block("func_return")
        self._builder     = ir.IRBuilder(entry_block)
        self._return_block = ret_block

        if method.return_type != TessType.VOID:
            self._return_alloca = self._builder.alloca(ret_llvm, name="retval")
        else:
            self._return_alloca = None

        # self (TessObject*) — disponible como "_self"
        self_alloca = self._builder.alloca(obj_ptr_t, name="_self_ptr")
        self._builder.store(ir_fn.args[0], self_alloca)
        self._declare_ir_var("_self", self_alloca)

        # Parámetros
        for ir_arg, pname in zip(ir_fn.args[1:], method.params.keys()):
            pt    = method.params[pname]
            alloc = self._builder.alloca(self.types.llvm_type(pt), name=pname)
            self._builder.store(ir_arg, alloc)
            self._declare_ir_var(pname, alloc)

        self._emit_block(method.body)

        if not self._builder.block.is_terminated:
            self._builder.branch(ret_block)

        self._builder.position_at_start(ret_block)
        if self._return_alloca is None or method.return_type == TessType.VOID:
            self._builder.ret_void()
        else:
            rv = self._builder.load(self._return_alloca, "ret_load")
            self._builder.ret(rv)

        # Restaurar
        self._pop_scope()
        self._builder           = old_builder
        self._current_func_name = old_func_name
        self._scope_stack       = old_scope
        self._break_target      = old_break
        self._return_alloca     = old_ret_alloca
        self._return_block      = old_ret_block

    def _emit_InterfaceDeclaration(self, node: dict):
        pass   # Las interfaces no generan código, solo son metadatos

    def _emit_NewObject(self, node: dict):
        """new ClassName(args) → llama a tess_object_new + constructor."""
        class_name = node.get('class', '')
        name_ptr   = self._str_const(class_name)
        obj_ptr_t  = ir.IntType(8).as_pointer()

        # Crear el objeto vía runtime C
        obj = self._builder.call(self.runtime.get("tess_object_new"), [name_ptr], "new_obj")

        # Llamar al constructor mangled si existe
        ctor_mangled = f"{class_name}____init__"
        if ctor_mangled in self._ir_funcs:
            args_node = node.get('arguments', {})
            raw_args  = args_node.get('value', '') if isinstance(args_node, dict) else ''
            args = [obj] + self._emit_call_args({'value': raw_args}) if raw_args.strip() else [obj]
            self._builder.call(self._ir_funcs[ctor_mangled], args)

        return obj

    def _emit_ThisAccess(self, node: dict):
        """this.campo → tess_object_get_attr(self, campo)"""
        raw   = node.get('value', '')
        field = raw.split('.', 1)[1] if '.' in raw else raw
        self_alloca = self._lookup_ir_var("_self")
        if self_alloca is None:
            return self._builder.call(self.runtime.get("tess_make_null"), [])
        self_val  = self._builder.load(self_alloca, "self_val")
        field_ptr = self._str_const(field)
        return self._builder.call(self.runtime.get("tess_object_get_attr"), [self_val, field_ptr])

    def _emit_ThisAssignment(self, node: dict):
        """this.campo = valor → tess_object_set_attr(self, campo, valor)"""
        raw      = node.get('value', '')
        field    = raw.split('.', 1)[1] if '.' in raw else raw
        assigned = node.get('assigned', {})
        val_node = assigned if isinstance(assigned, dict) else {}
        val      = self._emit_value_node(val_node, TessType.DYNAMIC)
        if val is None:
            val = self._builder.call(self.runtime.get("tess_make_null"), [])
        tv        = self._to_tess_value(val)
        self_alloca = self._lookup_ir_var("_self")
        if self_alloca is None:
            return
        self_val  = self._builder.load(self_alloca, "self_val")
        field_ptr = self._str_const(field)
        self._builder.call(self.runtime.get("tess_object_set_attr"), [self_val, field_ptr, tv])

    def _emit_ThisCall(self, node: dict):
        """this.metodo(args) → llama a la función mangled ClassName__metodo(self, args)"""
        raw         = node.get('value', '')
        method_name = raw.split('.', 1)[1] if '.' in raw else raw
        args_node   = node.get('arguments', {})
        raw_args    = args_node.get('value', '') if isinstance(args_node, dict) else ''

        self_alloca = self._lookup_ir_var("_self")
        if self_alloca is None:
            return self._builder.call(self.runtime.get("tess_make_null"), [])
        self_val = self._builder.load(self_alloca, "self_val")

        # Intentar llamada estática mangled (más eficiente)
        # El class_name se infiere del contexto de la función actual: "ClassName__method"
        parts = self._current_func_name.split('__') if self._current_func_name else []
        class_name = parts[0] if parts else ""
        mangled    = f"{class_name}__{method_name}"

        if mangled in self._ir_funcs:
            call_args = [self_val] + self._emit_call_args({'value': raw_args})
            return self._builder.call(self._ir_funcs[mangled], call_args, "this_call_ret")
        else:
            # Fallback dinámico vía runtime
            meth_ptr  = self._str_const(method_name)
            dyn_args  = self._emit_call_args({'value': raw_args})
            args_arr  = self._builder.call(self.runtime.get("tess_make_null"), [])
            count     = ir.Constant(ir.IntType(64), len(dyn_args))
            return self._builder.call(
                self.runtime.get("tess_object_call"),
                [self_val, meth_ptr, args_arr, count], "dyn_call_ret")

    def _emit_SuperCall(self, node: dict):
        """super.metodo(args) → llama al método del padre."""
        raw         = node.get('value', '')
        method_name = raw.split('.', 1)[1] if '.' in raw else raw
        args_node   = node.get('arguments', {})
        raw_args    = args_node.get('value', '') if isinstance(args_node, dict) else ''

        self_alloca = self._lookup_ir_var("_self")
        self_val    = self._builder.load(self_alloca, "self_val") if self_alloca else \
                      self._builder.call(self.runtime.get("tess_make_null"), [])

        # Buscar el padre en la jerarquía de clases
        parts      = self._current_func_name.split('__') if self._current_func_name else []
        class_name = parts[0] if parts else ""
        tess_cls   = self.ctx.get_class(class_name)
        parent     = tess_cls.parent if tess_cls else None

        if parent:
            mangled = f"{parent}__{method_name}"
            if mangled in self._ir_funcs:
                call_args = [self_val] + self._emit_call_args({'value': raw_args})
                return self._builder.call(self._ir_funcs[mangled], call_args, "super_ret")

        return self._builder.call(self.runtime.get("tess_make_null"), [])

    def _emit_SuperAccess(self, node: dict):
        """super.campo → tess_object_get_attr(self, campo) — mismo que this en IR."""
        return self._emit_ThisAccess(node)

    def _emit_SuperAssignment(self, node: dict):
        return self._emit_ThisAssignment(node)

    def _emit_SuperConstructorCall(self, node: dict):
        """super.__init__(args)"""
        args_node  = node.get('arguments', {})
        raw_args   = args_node.get('value', '') if isinstance(args_node, dict) else ''
        parts      = self._current_func_name.split('__') if self._current_func_name else []
        class_name = parts[0] if parts else ""
        tess_cls   = self.ctx.get_class(class_name)
        parent     = tess_cls.parent if tess_cls else None

        if parent:
            mangled = f"{parent}____init__"
            if mangled in self._ir_funcs:
                self_alloca = self._lookup_ir_var("_self")
                self_val    = self._builder.load(self_alloca, "self_val") if self_alloca else \
                              self._builder.call(self.runtime.get("tess_make_null"), [])
                call_args = [self_val] + self._emit_call_args({'value': raw_args})
                self._builder.call(self._ir_funcs[mangled], call_args)

    def _emit_TryCatch(self, node: dict):
        """
        Try-Catch usando tess_try_begin / tess_throw / tess_catch_get.
        Modelo: setjmp/longjmp wrapeado por el runtime C.
        """
        fn          = self._builder.function
        try_bb      = fn.append_basic_block("try_body")
        catch_bb    = fn.append_basic_block("catch_body")
        finally_bb  = fn.append_basic_block("finally_body")
        merge_bb    = fn.append_basic_block("try_merge")

        # tess_try_begin() retorna 0 en el try, != 0 si hay excepción
        setjmp_ret = self._builder.call(self.runtime.get("tess_try_begin"), [], "setjmp_ret")
        zero       = ir.Constant(ir.IntType(32), 0)
        in_try     = self._builder.icmp_signed('==', setjmp_ret, zero, "in_try")
        self._builder.cbranch(in_try, try_bb, catch_bb)

        # ── bloque try ────────────────────────────────────────────────────────
        self._builder.position_at_start(try_bb)
        self._push_scope()
        self._emit_block(node.get('tryBlock') or node.get('block', []))
        self._pop_scope()
        self._builder.call(self.runtime.get("tess_try_end"), [])
        if not self._builder.block.is_terminated:
            self._builder.branch(finally_bb)

        # ── bloque catch ──────────────────────────────────────────────────────
        self._builder.position_at_start(catch_bb)
        catch_clause = node.get('catchClause', {})
        exc_var      = catch_clause.get('exception') or catch_clause.get('name') if catch_clause else None

        self._push_scope()
        if exc_var:
            # Obtener la excepción capturada del runtime
            exc_val   = self._builder.call(self.runtime.get("tess_catch_get"), [], "caught_exc")
            exc_alloca = self._alloca(exc_var, self.types.tess_value_ptr_t)
            self._builder.store(exc_val, exc_alloca)
            self._declare_ir_var(exc_var, exc_alloca)

        catch_block = catch_clause.get('block', []) if catch_clause else []
        self._emit_block(catch_block)
        self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(finally_bb)

        # ── bloque finally ────────────────────────────────────────────────────
        self._builder.position_at_start(finally_bb)
        finally_node = node.get('finallyBlock') or (
            catch_clause.get('finallyBlock') if isinstance(catch_clause, dict) else None)
        if finally_node:
            self._push_scope()
            self._emit_block(finally_node.get('block', []))
            self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(merge_bb)

        self._builder.position_at_start(merge_bb)

    def _emit_Throw(self, node: dict):
        """throw ExcClass("message") → tess_exception_new + tess_throw."""
        exc_class  = node.get('exception', 'Error')
        value_node = node.get('value', {})
        raw_msg    = value_node.get('value', '') if isinstance(value_node, dict) else ''

        class_ptr = self._str_const(exc_class)
        if raw_msg:
            expr    = self.ctx.parse_expression(str(raw_msg))
            msg_val = self._emit_expr(expr)
            msg_tv  = self._to_tess_value(msg_val)
            msg_ptr = self._builder.call(self.runtime.get("tess_to_string"), [msg_tv], "msg_str")
        else:
            msg_ptr = self._str_const("")

        exc_val = self._builder.call(
            self.runtime.get("tess_exception_new"), [class_ptr, msg_ptr], "exc_val")
        self._builder.call(self.runtime.get("tess_throw"), [exc_val])
        # tess_throw no retorna — agregar unreachable
        self._builder.unreachable()
    def _emit_SwitchStatement(self, node: dict):
        """Switch Tesseract → if-else chain con tess_eq + tess_value_truthy.
        Las variables Tesseract son siempre TessValue* (dinámicas); el switch
        nativo de LLVM requiere entero, así que se emite como cadena de ramas."""
        var_name = node["value"]
        alloca   = self._lookup_ir_var(var_name)
        fn       = self._builder.function

        if alloca:
            switch_val = self._builder.load(alloca, "switch_val")
        else:
            switch_val = self._builder.call(
                self.runtime.get("tess_make_int"),
                [ir.Constant(ir.IntType(64), 0)], "switch_val_zero"
            )

        default_bb = fn.append_basic_block("switch_default")
        merge_bb   = fn.append_basic_block("switch_merge")
        cases      = node.get("cases", [])

        # Crear bloques de cada caso primero
        case_blocks = []
        for case in cases:
            case_val = case.get("case")
            bb = fn.append_basic_block(f"switch_case_{case_val}")
            case_blocks.append((bb, case, case_val))

        # Emitir cadena de comparaciones en el bloque actual
        for i, (bb, case, case_val) in enumerate(case_blocks):
            try:
                cv_tv = self._builder.call(
                    self.runtime.get("tess_make_int"),
                    [ir.Constant(ir.IntType(64), int(case_val))],
                    f"switch_cv_{i}"
                )
            except (TypeError, ValueError):
                s_ptr = self._make_string_constant(str(case_val))
                cv_tv = self._builder.call(
                    self.runtime.get("tess_make_string"), [s_ptr],
                    f"switch_cv_{i}"
                )

            cmp_tv = self._builder.call(
                self.runtime.get("tess_eq"),
                [switch_val, cv_tv], f"switch_cmp_{i}"
            )
            cond = self._builder.call(
                self.runtime.get("tess_value_truthy"),
                [cmp_tv], f"switch_truthy_{i}"
            )

            if i < len(case_blocks) - 1:
                next_bb = fn.append_basic_block(f"switch_check_{i + 1}")
                self._builder.cbranch(cond, bb, next_bb)
                self._builder.position_at_start(next_bb)
            else:
                self._builder.cbranch(cond, bb, default_bb)

        # Emitir cuerpos de cada caso
        for bb, case, _ in case_blocks:
            self._builder.position_at_start(bb)
            self._push_scope()
            self._emit_block(case.get("block", []))
            self._pop_scope()
            if not self._builder.block.is_terminated:
                self._builder.branch(merge_bb)

        # Default
        self._builder.position_at_start(default_bb)
        default = node.get("defaultCase")
        if default:
            self._push_scope()
            self._emit_block(default.get("block", []))
            self._pop_scope()
        if not self._builder.block.is_terminated:
            self._builder.branch(merge_bb)

        self._builder.position_at_start(merge_bb)

    def _emit_PostIncrementStatement(self, node: dict):
        self._emit_incr_decr(node["value"], +1)

    def _emit_PostDecrementStatement(self, node: dict):
        self._emit_incr_decr(node["value"], -1)

    def _emit_PreIncrementStatement(self, node: dict):
        self._emit_incr_decr(node["value"], +1)

    def _emit_PreDecrementStatement(self, node: dict):
        self._emit_incr_decr(node["value"], -1)

    def _emit_ParameterAsignement(self, node: dict):
        """Re-asignación de parámetro dentro de función."""
        self._emit_VariableAsignement(node)

    def _emit_unknown(self, node_content):
        pass  # Nodo no implementado — ignorar silenciosamente

    # ── emisores de expresiones — recorren ExprNode ──────────────────────────
    def _emit_core_chain(self, node: CoreCallNode) -> Any:
     """
     Emite la cadena de llamadas del tipo core.
     Convención en runtime.c:
        _tess_mod_{tipo}_{metodo}(TessValue* self, TessValue* arg0, ...)
     El 'self' es el TessValue* de la variable.
     Para métodos mutable_default (push, pop, etc.) el runtime ya muta
     internamente y devuelve self; no necesitamos hacer nada extra.
     Con .mut: al final almacenamos el resultado devuelto en la variable.
     """
     tv = self.types.tess_value_ptr_t

     # Cargar el TessValue* de la variable origen
     alloca = self._lookup_ir_var(node.var)
     if alloca is None:
        return self._builder.call(self.runtime.get("tess_make_null"), [])

     current_val = self._builder.load(alloca, f"{node.var}_chain_in")

     # Determinar el tipo Tesseract de la variable para el mangling
     var_type = self._infer_var_tess_type(node.var)

     for method_name, args_nodes in node.chain:
        # Emitir argumentos extra
        extra_args = [self._to_tess_value(self._emit_expr(a)) for a in args_nodes]

        # Nombre mangled: _tess_mod_{tipo}_{metodo}
        # Si no conocemos el tipo usamos el TessValue* dinámico y dejamos
        # que el runtime despache según el tag en tiempo de ejecución.
        if var_type:
            mangled = f"_tess_mod_{var_type}_{method_name}"
        else:
            mangled = f"_tess_mod_dynamic_{method_name}"

        fn = self.module.globals.get(mangled)
        if fn is None:
            arg_types = [tv] * (1 + len(extra_args))
            fn_type   = ir.FunctionType(tv, arg_types)
            fn        = ir.Function(self.module, fn_type, name=mangled)

        call_args   = [current_val] + extra_args
        current_val = self._builder.call(fn, call_args, f"{method_name}_ret")

        # mutable_default: el runtime ya muteó; actualizamos el alloca
        # para que el encadenamiento siguiente vea el valor actualizado
        if method_name in _CORE_MUTABLE_DEFAULT:
            self._builder.store(current_val, alloca)

     # .mut explícito: escribir el resultado final en la variable
     if node.mut:
        self._builder.store(current_val, alloca)

     return current_val
    def _emit_core_call_from_fname(self, var_name: str, method_name: str,
                                   inline_args: Optional[str], node: dict) -> Any:
        """
        Emite una llamada a método core cuando aparece como campo 'function'
        de un CallExpression (standalone: modulo.length o modulo.toUpperCase()).

        La convención del runtime C es:
          _tess_mod_{tipo}_{metodo}(TessValue* self, TessValue* arg0, ...)
        self = TessValue* de la variable; SIEMPRE se pasa aunque el método
        no tenga parámetros extra (como .length, .isEmpty, .type, etc.).
        """
        # 1. Obtener argumentos extra: primero del fname inline, luego del nodo
        raw_args_str = ""
        if inline_args is not None:
            # Había paréntesis en el fname: "modulo.replace(old, new)"
            raw_args_str = inline_args.strip()
        else:
            # Los argumentos vienen en el campo arguments del nodo
            args_node = node.get("arguments", {})
            if isinstance(args_node, dict):
                raw_args_str = str(args_node.get("value", "") or "")
            elif args_node:
                raw_args_str = str(args_node)

        # 2. Parsear argumentos extra como ExprNode
        if raw_args_str.strip():
            arg_nodes = self.ctx.expr_parser._parse_arg_list(raw_args_str)
        else:
            arg_nodes = []

        # 3. Delegar a _emit_core_chain usando CoreCallNode
        core_node = CoreCallNode(
            var=var_name,
            chain=[(method_name, arg_nodes)],
            mut=False
        )
        return self._emit_core_chain(core_node)

    def _infer_var_tess_type(self, var_name: str) -> Optional[str]:
     """
     Devuelve el tipo Tesseract ('string','int','float','bool','array','null')
     de una variable local, o None si es dinámico/desconocido.
     """
     sym = self.ctx.symbol_table.lookup(var_name)
     if sym is None:
        return None
     tname = sym.ttype.value   # coincide con las claves de _CORE_METHODS
     return tname if tname in _CORE_METHODS else None
    def _emit_expr(self, node: ExprNode) -> Any:
        """
        Recorre un árbol ExprNode y emite instrucciones IR.
        Retorna el ir.Value resultado.
        """
        if isinstance(node, CoreCallNode):
            return self._emit_core_chain(node)
        
        if isinstance(node, LiteralNode):
            return self._emit_literal(node)

        if isinstance(node, VarNode):
            return self._emit_var_load(node.name)

        if isinstance(node, BinOpNode):
            return self._emit_binop(node)

        if isinstance(node, LogicalNode):
            return self._emit_logical(node)

        if isinstance(node, UnaryNode):
            return self._emit_unary(node)

        if isinstance(node, ConcatNode):
            return self._emit_concat(node)

        if isinstance(node, FuncCallNode):
            return self._emit_func_call_expr(node)

        if isinstance(node, ModCallNode):
            return self._emit_mod_call_expr(node)

        if isinstance(node, ModVarNode):
            return self._emit_mod_var(node)

        if isinstance(node, ArrayAccessNode):
            return self._emit_array_access(node)

        if isinstance(node, ArrayLiteralNode):
            return self._emit_array_literal_node(node)

        if isinstance(node, DictLiteralNode):
            return self._emit_dict_literal_node(node)

        # Fallback: null
        return self._builder.call(self.runtime.get("tess_make_null"), [])

    def _emit_literal(self, node: LiteralNode) -> Any:
        if node.ttype == TessType.INT:
            return self._builder.call(self.runtime.get("tess_make_int"),
                                  [ir.Constant(ir.IntType(64), int(node.value))])
        if node.ttype == TessType.FLOAT:
            return self._builder.call(self.runtime.get("tess_make_float"),
                                  [ir.Constant(ir.DoubleType(), float(node.value))])
        if node.ttype == TessType.BOOL:
            return self._builder.call(self.runtime.get("tess_make_bool"),
                                  [ir.Constant(ir.IntType(1), 1 if node.value else 0)])
        if node.ttype == TessType.STRING:
            s = str(node.value) if node.value is not None else ""
            str_ptr = self._str_const(s)
            return self._builder.call(self.runtime.get("tess_make_string"), [str_ptr])
        if node.ttype == TessType.NULL:
            return self._builder.call(self.runtime.get("tess_make_null"), [])
        return self._builder.call(self.runtime.get("tess_make_null"), [])

    def _emit_var_load(self, name: str) -> Any:
        alloca = self._lookup_ir_var(name)
        if alloca:
            return self._builder.load(alloca, f"{name}_val")

        # 2. Buscar en variables globales (si existe en la tabla de símbolos y está en _global_vars)
        sym = self.ctx.symbol_table.lookup(name)
        if sym and name in self._global_vars:
            gvar = self._global_vars[name]
            return self._builder.load(gvar, f"{name}_val")

        # 3. Fallback: valor null dinámico
        return self._builder.call(self.runtime.get("tess_make_null"), [])

    def _emit_binop(self, node: BinOpNode) -> Any:
        left  = self._emit_expr(node.left)
        right = self._emit_expr(node.right)

        # Inferir tipos de los operandos para decidir el camino estático o dinámico
        lt = self._ir_type_of(left)
        rt = self._ir_type_of(right)

        # ── Camino estático: ambos int ───────────────────────────────────────
        if lt == ir.IntType(64) and rt == ir.IntType(64):
            return self._emit_int_binop(node.op, left, right)

        # ── Camino estático: alguno float ────────────────────────────────────
        if lt in (ir.DoubleType(), ir.IntType(64)) and rt in (ir.DoubleType(), ir.IntType(64)):
            l = self._builder.sitofp(left, ir.DoubleType()) if lt == ir.IntType(64) else left
            r = self._builder.sitofp(right, ir.DoubleType()) if rt == ir.IntType(64) else right
            return self._emit_float_binop(node.op, l, r)

        # ── Camino dinámico: via runtime C ───────────────────────────────────
        lv = self._to_tess_value(left)
        rv = self._to_tess_value(right)
        op_map = {
            '+': 'tess_add', '-': 'tess_sub', '*': 'tess_mul',
            '/': 'tess_div', '%': 'tess_mod',
            '==': 'tess_eq', '!=': 'tess_neq',
            '<':  'tess_lt', '>':  'tess_gt',
            '<=': 'tess_lte', '>=': 'tess_gte',
        }
        rt_fn = op_map.get(node.op, 'tess_add')
        return self._builder.call(self.runtime.get(rt_fn), [lv, rv])

    def _emit_int_binop(self, op: str, l: Any, r: Any) -> Any:
        ops = {
            '+': lambda: self._builder.add(l, r, "iadd"),
            '-': lambda: self._builder.sub(l, r, "isub"),
            '*': lambda: self._builder.mul(l, r, "imul"),
            '/': lambda: self._builder.sdiv(l, r, "idiv"),
            '%': lambda: self._builder.srem(l, r, "imod"),
            '==': lambda: self._builder.icmp_signed('==', l, r, "ieq"),
            '!=': lambda: self._builder.icmp_signed('!=', l, r, "ineq"),
            '<':  lambda: self._builder.icmp_signed('<',  l, r, "ilt"),
            '>':  lambda: self._builder.icmp_signed('>',  l, r, "igt"),
            '<=': lambda: self._builder.icmp_signed('<=', l, r, "ilte"),
            '>=': lambda: self._builder.icmp_signed('>=', l, r, "igte"),
        }
        return ops[op]() if op in ops else ir.Constant(ir.IntType(64), 0)

    def _emit_float_binop(self, op: str, l: Any, r: Any) -> Any:
        ops = {
            '+': lambda: self._builder.fadd(l, r, "fadd"),
            '-': lambda: self._builder.fsub(l, r, "fsub"),
            '*': lambda: self._builder.fmul(l, r, "fmul"),
            '/': lambda: self._builder.fdiv(l, r, "fdiv"),
            '==': lambda: self._builder.fcmp_ordered('==', l, r, "feq"),
            '!=': lambda: self._builder.fcmp_ordered('!=', l, r, "fneq"),
            '<':  lambda: self._builder.fcmp_ordered('<',  l, r, "flt"),
            '>':  lambda: self._builder.fcmp_ordered('>',  l, r, "fgt"),
            '<=': lambda: self._builder.fcmp_ordered('<=', l, r, "flte"),
            '>=': lambda: self._builder.fcmp_ordered('>=', l, r, "fgte"),
        }
        return ops[op]() if op in ops else ir.Constant(ir.DoubleType(), 0.0)

    def _emit_logical(self, node: LogicalNode) -> Any:
        left  = self._emit_expr(node.left)
        right = self._emit_expr(node.right)
        # Si son TessValue, extraer truthiness
        lt = self._ir_type_of(left)
        if lt != ir.IntType(1):
            left  = self._builder.call(self.runtime.get("tess_value_truthy"), [self._to_tess_value(left)])
            right = self._builder.call(self.runtime.get("tess_value_truthy"), [self._to_tess_value(right)])
        if node.op == '&&':
            return self._builder.and_(left, right, "and")
        return self._builder.or_(left, right, "or")

    def _emit_unary(self, node: UnaryNode) -> Any:
        val = self._emit_expr(node.operand)
        if node.op == '-':
            vt = self._ir_type_of(val)
            if vt == ir.IntType(64):
                return self._builder.neg(val, "ineg")
            if vt == ir.DoubleType():
                return self._builder.fneg(val, "fneg")
            return self._builder.call(self.runtime.get("tess_neg"), [self._to_tess_value(val)])
        if node.op == '!':
            vt = self._ir_type_of(val)
            if vt == ir.IntType(1):
                return self._builder.not_(val, "lnot")
            tv = self._to_tess_value(val)
            return self._builder.call(self.runtime.get("tess_not"), [tv])
        return val

    def _emit_concat(self, node: ConcatNode) -> Any:
        """Concatenación con punto: emite calls a tess_concat."""
        tv = self.types.tess_value_ptr_t
        acc = self._builder.call(self.runtime.get("tess_make_string"),
                                 [self._str_const("")])
        for part in node.parts:
            val  = self._emit_expr(part)
            part_tv = self._to_tess_value(val)
            acc = self._builder.call(self.runtime.get("tess_concat"), [acc, part_tv])
        return acc

    def _emit_func_call_expr(self, node: FuncCallNode) -> Any:
     tess_fn = self.ctx.get_function(node.name)
     ir_fn = self._ir_funcs.get(node.name)
     if ir_fn and tess_fn:
        param_types = list(tess_fn.params.values())
        args = []
        for i, arg_expr in enumerate(node.args):
            arg_val = self._emit_expr(arg_expr)
            if i < len(param_types):
                arg_val = self._coerce_to_type(arg_val, param_types[i])
            args.append(arg_val)
        return self._builder.call(ir_fn, args, "func_ret")
     return self._builder.call(self.runtime.get("tess_make_null"), [])

    def _emit_mod_call_expr(self, node: ModCallNode) -> Any:
        """
        Llamada a módulo: mod.func(args).
        Como los módulos nativos son librerías C, emitimos una llamada
        externa declarada dinámicamente.
        """
        mangled = f"_tess_mod_{node.module}_{node.func}"
        fn = self.module.globals.get(mangled)
        if fn is None:
            tv  = self.types.tess_value_ptr_t
            arg_types = [tv] * len(node.args)
            fn_type = ir.FunctionType(tv, arg_types)
            fn = ir.Function(self.module, fn_type, name=mangled)
        args = [self._to_tess_value(self._emit_expr(a)) for a in node.args]
        return self._builder.call(fn, args, "mod_ret")

    def _emit_mod_var(self, node: ModVarNode) -> Any:
        """Acceso a variable de módulo: mod.VAR."""
        mangled = f"_tess_modvar_{node.module}_{node.var}"
        gvar = self.module.globals.get(mangled)
        if gvar is None:
            gvar = ir.GlobalVariable(self.module, self.types.tess_value_ptr_t, name=mangled)
            gvar.linkage = 'external'
        return self._builder.load(gvar, "mod_var")

    def _emit_array_access(self, node: ArrayAccessNode) -> Any:
        alloca = self._lookup_ir_var(node.array)
        if alloca is None:
            return self._builder.call(self.runtime.get("tess_make_null"), [])
        arr = self._builder.load(alloca, "arr")
        arr_tv = self._to_tess_value(arr)
        # Solo primer índice (acceso simple)
        idx = self._emit_expr(node.indices[0])
        idx_i64 = self._coerce_to_i64(idx)
        return self._builder.call(self.runtime.get("tess_array_get"), [arr_tv, idx_i64])

    # ── helpers de emisión ───────────────────────────────────────────────────

    def _emit_condition(self, condition_str: str) -> Any:
        """
        Emite código IR para una condición booleana (string del AST).
        Normaliza && → and, || → or como lo hace evaluate_expression.
        """
        condition_str = condition_str.replace("&&", " && ").replace("||", " || ")
        expr   = self.ctx.parse_expression(condition_str)
        result = self._emit_expr(expr)
        # Asegurar que el resultado es i1
        rt = self._ir_type_of(result)
        if rt == ir.IntType(1):
            return result
        if rt == ir.IntType(64):
            return self._builder.icmp_signed('!=', result, ir.Constant(ir.IntType(64), 0), "to_bool")
        if rt == ir.DoubleType():
            return self._builder.fcmp_ordered('!=', result, ir.Constant(ir.DoubleType(), 0.0), "to_bool")
        # TessValue → tess_value_truthy
        tv = self._to_tess_value(result)
        return self._builder.call(self.runtime.get("tess_value_truthy"), [tv])

    def _emit_value_node(self, value_node: dict, hint_type: TessType) -> Optional[Any]:
        """
        Emite IR para un nodo value del AST.
        Equivale a la lógica de resolve_expression + handle_VariableDeclaration.
        """
        ast_type  = value_node.get("type", "")
        raw_value = value_node.get("value")

        if ast_type == "NULL" or raw_value == "null":
            return self._builder.call(self.runtime.get("tess_make_null"), [])

        # Valor literal Python directo
        if isinstance(raw_value, bool):
            return ir.Constant(ir.IntType(1), 1 if raw_value else 0)
        if isinstance(raw_value, int):
            return ir.Constant(ir.IntType(64), raw_value)
        if isinstance(raw_value, float):
            return ir.Constant(ir.DoubleType(), raw_value)

        if isinstance(raw_value, str):
            # String literal con comillas
            if raw_value.startswith('"') and raw_value.endswith('"'):
                s = raw_value[1:-1]
                ptr = self._str_const(s)
                # Devuelve i8* (no TessValue*)
                return ptr
            # Expresión / operación
            expr = self.ctx.parse_expression(raw_value)
            result = self._emit_expr(expr)
            return self._to_tess_value(result)

        if isinstance(raw_value, list):
            # Array literal
            return self._emit_array_literal(raw_value)

        if isinstance(raw_value, dict):
            # Dict literal
            return self._emit_dict_literal(raw_value)

        return self._builder.call(self.runtime.get("tess_make_null"), [])

    def _emit_print(self, node: dict):
        """
        Emite una llamada a la función print del runtime.
        Detecta el tipo del argumento y llama a la versión correcta.
        Mismo comportamiento que handle_CallExpression para 'print'.
        """
        args_node  = node.get("arguments", {})
        param_type = node.get("paramType", "")
        raw_arg    = args_node.get("value") if isinstance(args_node, dict) else args_node

        if raw_arg is None:
            self._builder.call(self.runtime.get("tess_print_null"), [])
            return

        val = None

        # String literal
        if isinstance(raw_arg, str) and raw_arg.startswith('"') and raw_arg.endswith('"'):
            ptr = self._str_const(raw_arg[1:-1])
            self._builder.call(self.runtime.get("tess_print_string"), [ptr])
            return

        # Expresión
        if isinstance(raw_arg, str):
            expr = self.ctx.parse_expression(raw_arg)
            val  = self._emit_expr(expr)
        elif isinstance(raw_arg, (int, float, bool)):
            val = self._python_literal_to_ir(raw_arg)

        if val is None:
            self._builder.call(self.runtime.get("tess_print_null"), [])
            return

        # Elegir función de print según tipo IR
        vt = self._ir_type_of(val)
        if vt == ir.IntType(64):
            self._builder.call(self.runtime.get("tess_print_int"), [val])
        elif vt == ir.DoubleType():
            self._builder.call(self.runtime.get("tess_print_float"), [val])
        elif vt == ir.IntType(1):
            self._builder.call(self.runtime.get("tess_print_bool"), [val])
        elif vt == ir.IntType(8).as_pointer():
            self._builder.call(self.runtime.get("tess_print_string"), [val])
        else:
            tv = self._to_tess_value(val)
            self._builder.call(self.runtime.get("tess_print_value"), [tv])

    def _emit_read(self, node: dict):
        """Lee input y asigna a la variable indicada."""
        args_node   = node.get("arguments", {})
        param_type  = node.get("paramType", "string")
        var_name    = args_node.get("value") if isinstance(args_node, dict) else str(args_node)

        alloca = self._lookup_ir_var(var_name)
        if alloca is None:
            return
        sym = self.ctx.symbol_table.lookup(var_name)
        if param_type == 'Int':
            val = self._builder.call(self.runtime.get("tess_read_int"), [])
        elif param_type == 'Float':
            val = self._builder.call(self.runtime.get("tess_read_float"), [])
        else:
            val = self._builder.call(self.runtime.get("tess_read_string"), [])
        if sym and sym.is_explicit_type:
            val = self._coerce_to_type(val, sym.ttype)
        else:
            val = self._to_tess_value(val)
        self._builder.store(val, alloca)
        


    def _emit_module_call_from_node(self, node: dict):
     """Llamada mod.func() desde un CallExpression."""
     fname = node.get("function", "")
     parts = fname.strip().rstrip('()').split('.', 1)
     if len(parts) != 2:
        return
     mod_name, func_name = parts

     # Guardia: si el lado izquierdo NO es módulo y el método existe en core,
     # redirigir a la emisión correcta con self como primer argumento.
     known_modules = self.ctx.symbol_table.known_module_names()
     is_core = any(func_name in methods for methods in _CORE_METHODS.values())
     if mod_name not in known_modules and is_core:
        self._emit_core_call_from_fname(mod_name, func_name, None, node)
        return
     args_node = node.get("arguments", {})
     raw_value = args_node.get("value") if isinstance(args_node, dict) else args_node

     # --- Construir lista de argumentos de forma robusta ---
     parsed_args = []
     if raw_value is None:
        pass  # sin argumentos
     elif isinstance(raw_value, (int, float, bool, str)):
        # Valor único: puede ser literal o expresión
        if isinstance(raw_value, str):
            expr = self.ctx.parse_expression(raw_value)
            parsed_args.append(self._to_tess_value(self._emit_expr(expr)))
        else:
            # Literal numérico o booleano
            val_ir = self._python_literal_to_ir(raw_value)
            parsed_args.append(self._to_tess_value(val_ir))
     elif isinstance(raw_value, list):
        # Lista de argumentos (ej: ["x", 1, true])
        for arg in raw_value:
            if isinstance(arg, str):
                expr = self.ctx.parse_expression(arg)
                parsed_args.append(self._to_tess_value(self._emit_expr(expr)))
            else:
                val_ir = self._python_literal_to_ir(arg)
                parsed_args.append(self._to_tess_value(val_ir))
     elif isinstance(raw_value, dict):
        # Diccionario con clave "value" (caso anidado)
        inner = raw_value.get("value")
        if inner is not None:
            # Tratar como si fuera un argumento único
            if isinstance(inner, str):
                expr = self.ctx.parse_expression(inner)
                parsed_args.append(self._to_tess_value(self._emit_expr(expr)))
            else:
                val_ir = self._python_literal_to_ir(inner)
                parsed_args.append(self._to_tess_value(val_ir))
     else:
        # Fallback: convertir a string y split (comportamiento original)
        raw_str = str(raw_value)
        for part in raw_str.split(','):
            part = part.strip()
            if not part:
                continue
            if ':' in part and not (part.startswith('"') or part.startswith("'")):
                _, v = part.split(':', 1)
                part = v.strip()
            expr = self.ctx.parse_expression(part)
            parsed_args.append(self._to_tess_value(self._emit_expr(expr)))

     # Obtener o declarar la función del módulo
     mangled = f"_tess_mod_{mod_name}_{func_name}"
     fn = self.module.globals.get(mangled)
     if fn is None:
        tv = self.types.tess_value_ptr_t
        fn_type = ir.FunctionType(tv, [tv] * len(parsed_args))
        fn = ir.Function(self.module, fn_type, name=mangled)
     if parsed_args:
        self._builder.call(fn, parsed_args)
    def _emit_incr_decr(self, var_name: str, delta: int):
        alloca = self._lookup_ir_var(var_name)
        if alloca is None:
            return
        sym = self.ctx.symbol_table.lookup(var_name)
        if sym and sym.ttype == TessType.INT:
            cur = self._builder.load(alloca, "incr_cur")
            new = self._builder.add(cur, ir.Constant(ir.IntType(64), delta), "incr_new")
            self._builder.store(new, alloca)
        elif sym and sym.ttype == TessType.FLOAT:
            cur = self._builder.load(alloca, "incr_cur")
            new = self._builder.fadd(cur, ir.Constant(ir.DoubleType(), float(delta)), "incr_new")
            self._builder.store(new, alloca)
        else:
            # Dinámico
            cur = self._builder.load(alloca, "incr_cur")
            tv  = self._to_tess_value(cur)
            rt_fn = "tess_inc" if delta > 0 else "tess_dec"
            new = self._builder.call(self.runtime.get(rt_fn), [tv])
            self._builder.store(new, alloca)

    def _emit_range_bounds(self, iterator_str: str) -> Tuple[Any, Any]:
        """
        Parsea "start..end" y emite los valores IR para los límites.
        Misma lógica que _validate_and_parse_range en interpre.py.
        """
        if ".." not in iterator_str:
            return ir.Constant(ir.IntType(64), 0), ir.Constant(ir.IntType(64), 0)
        parts = iterator_str.split("..")
        start_expr = self.ctx.parse_expression(parts[0].strip())
        end_expr   = self.ctx.parse_expression(parts[1].strip())
        start = self._emit_expr(start_expr)
        end   = self._emit_expr(end_expr)
        start = self._coerce_to_i64(start)
        end   = self._coerce_to_i64(end)
        return start, end

    def _emit_array_literal_node(self, node: ArrayLiteralNode) -> Any:
        """Emite un ArrayLiteralNode: crea el array y hace push de cada elemento."""
        tv  = self.types.tess_value_ptr_t
        arr = self._builder.call(self.runtime.get("tess_array_new"), [], "arr_new")
        for elem in node.elements:
            val = self._emit_expr(elem)
            tv_val = self._to_tess_value(val)
            self._builder.call(self.runtime.get("tess_array_push"), [arr, tv_val])
        return arr

    def _emit_dict_literal_node(self, node: DictLiteralNode) -> Any:
        """Emite un DictLiteralNode: crea el dict y hace set de cada par."""
        d = self._builder.call(self.runtime.get("tess_dict_new"), [], "dict_new")
        for key_node, val_node in node.pairs:
            key_val = self._emit_expr(key_node)
            val_val = self._emit_expr(val_node)
            key_str = self._builder.call(
                self.runtime.get("tess_to_string"), [self._to_tess_value(key_val)], "dict_key"
            )
            tv_val = self._to_tess_value(val_val)
            self._builder.call(self.runtime.get("tess_dict_set"), [d, key_str, tv_val])
        return d

    def _emit_array_literal(self, items: list, type_info=None) -> Any:
     from tessruntime import TessTypeInfo
     if type_info is not None:
        ti_ptr = self._emit_type_info(type_info)
        arr = self._builder.call(self.runtime.get("tess_array_new_typed"), [ti_ptr])
     else:
        arr = self._builder.call(self.runtime.get("tess_array_new"), [])
     for item in items:
        val = self._python_literal_to_ir(item)
        tv  = self._to_tess_value(val)
        self._builder.call(self.runtime.get("tess_array_push"), [arr, tv])
     return arr

    
    def _emit_tuple_literal(self, items: list, type_info=None) -> Any:
     from tessruntime import TessTypeInfo
     if type_info is not None:
        ti_ptr = self._emit_type_info(type_info)
        tup = self._builder.call(self.runtime.get("tess_tuple_new_typed"), [ti_ptr])
     else:
        tup = self._builder.call(self.runtime.get("tess_tuple_new"), [])
     for item in items:
        val = self._python_literal_to_ir(item)
        tv  = self._to_tess_value(val)
        self._builder.call(self.runtime.get("tess_tuple_push"), [tup, tv])
     return tup

    def _emit_dict_literal(self, d: dict, type_info=None) -> Any:
     from tessruntime import TessTypeInfo
     if type_info is not None:
        ti_ptr = self._emit_type_info(type_info)
        dct = self._builder.call(self.runtime.get("tess_dict_new_typed"), [ti_ptr])
     else:
        dct = self._builder.call(self.runtime.get("tess_dict_new"), [])
     for key, val in d.items():
        key_ptr = self._str_const(str(key))
        val_ir  = self._python_literal_to_ir(val)
        tv      = self._to_tess_value(val_ir)
        self._builder.call(self.runtime.get("tess_dict_set"), [dct, key_ptr, tv])
     return dct

    def _emit_call_args(self, params_node: dict) -> List[Any]:
        """
        Parsea y emite los argumentos de una llamada.
        Misma lógica que _parse_call_parameters en interpre.py.
        """
        args = []
        if not params_node:
            return args
        raw = params_node.get("value", "") if isinstance(params_node, dict) else str(params_node)
        if raw is None:
            raw = ""
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            if ':' in part and not (part.startswith('"') or part.startswith("'")):
                _, v = part.split(':', 1)
                part = v.strip()
            expr = self.ctx.parse_expression(part)
            args.append(self._emit_expr(expr))
        return args

    # ── utilidades de tipo IR ────────────────────────────────────────────────

    def _ir_type_of(self, val: Any) -> Optional[ir.Type]:
        """Retorna el tipo IR de un valor."""
        if hasattr(val, 'type'):
            return val.type
        return None

    def _to_tess_value(self, val: Any) -> Any:
        """Convierte un valor IR nativo a TessValue* via el runtime."""
        vt = self._ir_type_of(val)
        if vt is None:
            return self._builder.call(self.runtime.get("tess_make_null"), [])
        if vt == ir.IntType(64):
            return self._builder.call(self.runtime.get("tess_make_int"), [val])
        if vt == ir.DoubleType():
            return self._builder.call(self.runtime.get("tess_make_float"), [val])
        if vt == ir.IntType(1):
            return self._builder.call(self.runtime.get("tess_make_bool"), [val])
        if vt == ir.IntType(8).as_pointer():
            return self._builder.call(self.runtime.get("tess_make_string"), [val])
        # Ya es TessValue* o algo compatible
        return val

    def _coerce_to_i64(self, val: Any) -> Any:
        """Convierte un valor IR a i64 (para índices, rangos, etc.)."""
        vt = self._ir_type_of(val)
        if vt == ir.IntType(64):
            return val
        if vt == ir.DoubleType():
            return self._builder.fptosi(val, ir.IntType(64), "fptoi")
        if vt == ir.IntType(1):
            return self._builder.zext(val, ir.IntType(64), "btoi")
        # TessValue → extraer como int
        tv = self._to_tess_value(val)
        return self._builder.call(self.runtime.get("tess_to_int"), [tv])

    def _python_literal_to_ir(self, val: Any) -> Any:
        """Convierte un literal Python a un valor IR."""
        if isinstance(val, bool):
            return self._builder.call(self.runtime.get("tess_make_bool"),
                                  [ir.Constant(ir.IntType(1), 1 if val else 0)])
        if isinstance(val, int):
            return self._builder.call(self.runtime.get("tess_make_int"),
                                  [ir.Constant(ir.IntType(64), val)])
        if isinstance(val, float):
            return self._builder.call(self.runtime.get("tess_make_float"),
                                  [ir.Constant(ir.DoubleType(), val)])
        if isinstance(val, str):
            ptr = self._str_const(val)
            return self._builder.call(self.runtime.get("tess_make_string"), [ptr])
        return self._builder.call(self.runtime.get("tess_make_null"), [])
    
    def _coerce_to_type(self, val: Any, target_ttype: TessType) -> Any:
     """
     Convierte un valor IR (que puede ser nativo o TessValue*) al tipo LLVM nativo
     requerido por target_ttype.
     """
     target_llvm = self.types.llvm_type(target_ttype)
     val_type = self._ir_type_of(val)

     # Si ya es del tipo correcto, devolver tal cual
     if val_type == target_llvm:
        return val

     # Si el destino es dinámico (TessValue*), convertir a TessValue*
     if target_ttype == TessType.DYNAMIC:
        return self._to_tess_value(val)

     # Si el valor es TessValue*, extraer el valor nativo con el runtime
     if val_type == self.types.tess_value_ptr_t:
        if target_ttype == TessType.INT:
            return self._builder.call(self.runtime.get("tess_to_int"), [val])
        if target_ttype == TessType.FLOAT:
            return self._builder.call(self.runtime.get("tess_to_float"), [val])
        if target_ttype == TessType.BOOL:
            return self._builder.call(self.runtime.get("tess_to_bool"), [val])
        if target_ttype == TessType.STRING:
            return self._builder.call(self.runtime.get("tess_to_string"), [val])
        # Para ARRAY/DICT se mantienen como TessValue*
        return val

     # Conversiones entre tipos nativos
     if target_ttype == TessType.INT:
        if val_type == ir.DoubleType():
            return self._builder.fptosi(val, ir.IntType(64), "fptoi")
        if val_type == ir.IntType(1):
            return self._builder.zext(val, ir.IntType(64), "zext")
     if target_ttype == TessType.FLOAT:
        if val_type == ir.IntType(64):
            return self._builder.sitofp(val, ir.DoubleType(), "sitofp")
        if val_type == ir.IntType(1):
            return self._builder.uitofp(val, ir.DoubleType(), "uitofp")
     if target_ttype == TessType.BOOL:
        if val_type == ir.IntType(64):
            return self._builder.icmp_signed('!=', val, ir.Constant(ir.IntType(64), 0), "to_bool")
        if val_type == ir.DoubleType():
            return self._builder.fcmp_ordered('!=', val, ir.Constant(ir.DoubleType(), 0.0), "to_bool")
     if target_ttype == TessType.STRING:
        # Si val es i8*, ya está bien (no se requiere conversión)
        if val_type == ir.IntType(8).as_pointer():
            return val
        # Si es i64, convertir a string (caso raro)
        # Fallback: convertir a TessValue* y luego extraer
        tv = self._to_tess_value(val)
        return self._builder.call(self.runtime.get("tess_to_string"), [tv])

     # Fallback: convertir a TessValue* y luego extraer (seguro)
     tv = self._to_tess_value(val)
     return self._coerce_to_type(tv, target_ttype)
    def _is_constant_literal(self, value_node: dict) -> bool:
        """Determina si value_node es un literal constante simple (int, float, bool)."""
        raw = value_node.get("value")
        if isinstance(raw, (int, float, bool)):
            return True
        return False

    def _get_literal_constant(self, value_node: dict, ttype: TessType) -> Optional[ir.Constant]:
        """Obtiene el valor LLVM constante para un literal."""
        raw = value_node.get("value")
        if ttype == TessType.INT:
            return ir.Constant(ir.IntType(64), raw)
        if ttype == TessType.FLOAT:
            return ir.Constant(ir.DoubleType(), raw)
        if ttype == TessType.BOOL:
            return ir.Constant(ir.IntType(1), 1 if raw else 0)
        return None

# =============================================================================
# Driver — pipeline completo
# =============================================================================

def compile_ast(ast_json: dict,
                module_name: str = "tesseract_module",
                debug: bool = False) -> str:
    """
    Pipeline completo:
      1. Analizar el AST con tessruntime (CompileContext)
      2. Emitir LLVM IR con CodeGen
      3. Retornar el IR como string
    """
    ctx = analyze_ast(ast_json, debug=debug)
    gen = CodeGen(ctx, module_name=module_name)
    return gen.generate(ast_json)


def compile_to_file(ast_path:    str,
                    output_path: str,
                    module_name: str = "tesseract_module",
                    debug:       bool = False):
    """
    Lee un JSON AST, genera LLVM IR y lo escribe en output_path (.ll).
    """
    with open(ast_path, 'r', encoding='utf-8') as f:
        ast_json = json.load(f)

    ir_str = compile_ast(ast_json, module_name=module_name, debug=debug)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ir_str)

    print(f"[tesscodegen] IR escrito en: {output_path}")
    return output_path

def compile_to_binary(ast_path: str, output_path: str, runtime_lib: str = "runtime.c",
                      debug: bool = False, target_platform: str = None, use_zig: bool = True):
    import subprocess
    import shutil
    import os
    import sys

    # 1. Configurar plataforma destino
    if target_platform is None:
        if sys.platform == 'win32':
            target_platform = 'win32'
        elif sys.platform == 'linux':
             target_platform = 'linux'
        elif sys.platform == 'darwin':
             target_platform = 'mac'
        else:
             target_platform = 'unix'

    # 2. Encontrar zig cc
    cc_path = None
    if use_zig:
        zig_path = shutil.which("zig")
        if zig_path:
            cc_path = zig_path
            print(f"[tesscodegen] Usando zig cc desde: {zig_path}")
        else:
            print("[tesscodegen] ADVERTENCIA: 'zig' no encontrado en el PATH. Se usará clang como fallback.")
            use_zig = False

    if not use_zig:
        cc_path = shutil.which("clang")
        if not cc_path:
            candidates = [
                r"C:\Program Files\LLVM\bin\clang.exe",
                r"C:\Program Files (x86)\LLVM\bin\clang.exe",
                r"C:\LLVM\bin\clang.exe",
                "/usr/bin/clang",
                "/usr/local/bin/clang"
            ]
            for cand in candidates:
                if os.path.isfile(cand):
                    cc_path = cand
                    break
        if not cc_path:
            raise RuntimeError("No se encontró 'zig' ni 'clang'. Instala Zig desde https://ziglang.org/download o LLVM.")

    # 3. Determinar nombre del ejecutable final (con .exe solo en win32)
    exe_path = output_path
    if target_platform == 'win32' and not exe_path.endswith('.exe'):
        exe_path = exe_path + '.exe'

    # El .ll usa el nombre base sin extensión de ejecutable para no mezclarse
    base_path = exe_path[:-4] if exe_path.endswith('.exe') else exe_path
    ll_path = base_path + '.ll'
    compile_to_file(ast_path, ll_path, debug=debug)

    # 4. Construir el comando base (apunta al exe con sufijo correcto)
    if use_zig:
        cmd = [cc_path, "cc", ll_path, runtime_lib, "-o", exe_path]
    else:
        cmd = [cc_path, ll_path, runtime_lib, "-o", exe_path]

    # 5. Configurar target triple y flags según plataforma destino
    if use_zig:
        if target_platform == 'win32':
            cmd.insert(2, "-target")
            cmd.insert(3, "x86_64-windows-gnu")
        elif target_platform == 'linux':
            cmd.insert(2, "-target")
            cmd.insert(3, "x86_64-linux-gnu")
            # Con zig, no se necesita añadir -lm manualmente
        elif target_platform == 'mac':
            cmd.insert(2, "-target")
            cmd.insert(3, "x86_64-macos-gnu")
        elif target_platform == 'android':
            cmd.insert(2, "-target")
            cmd.insert(3, "aarch64-linux-android")    
    else:
        # ... (lógica anterior para clang, que ya tienes) ...
        link_flags = []
        if sys.platform.startswith('linux') or sys.platform == 'darwin' or sys.platform.startswith('freebsd'):
            if target_platform in ('linux', 'unix', 'mac'):
                link_flags.append('-lm')
        cmd.extend(link_flags)

    print(f"[tesscodegen] Ejecutando: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Compilación falló (código {res.returncode}):\n{res.stderr}")

    print(f"[tesscodegen] Binario nativo generado: {exe_path}")

# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tesseract LLVM IR Code Generator")
    parser.add_argument("ast",     help="Ruta al archivo JSON del AST")
    parser.add_argument("-o",      dest="output", default="output", help="Nombre del archivo de salida (sin extensión)")
    parser.add_argument("--ir",    action="store_true", help="Solo generar IR (.ll), no compilar")
    parser.add_argument("--bin",   action="store_true", help="Compilar hasta binario nativo")
    parser.add_argument("--runtime", default="tess_runtime.c", help="Ruta al runtime C")
    parser.add_argument("-d",      dest="debug", action="store_true", help="Modo debug")

    # Flags de plataforma destino (solo si --bin está activo)
    parser.add_argument("--win32", action="store_true", help="Compilar para Windows (64 bits)")
    parser.add_argument("--linux", action="store_true", help="Compilar para Linux")
    parser.add_argument("--unix",  action="store_true", help="Compilar para Unix genérico (Linux)")
    parser.add_argument("--mac",   action="store_true", help="Compilar para macOS")
    parser.add_argument("--android", action="store_true", help="Compilar para Android (aarch64)")

    args = parser.parse_args()

    # Determinar plataforma destino
    target_platform = None
    if args.win32:
        target_platform = 'win32'
    elif args.linux:
        target_platform = 'linux'
    elif args.unix:
        target_platform = 'unix'
    elif args.mac:
        target_platform = 'mac'
    elif args.android:
        target_platform = 'android'        

    if args.bin:
        compile_to_binary(args.ast, args.output, runtime_lib=args.runtime,
                          debug=args.debug, target_platform=target_platform)
    else:
        out = args.output if args.output.endswith(".ll") else args.output + ".ll"
        compile_to_file(args.ast, out, debug=args.debug)
        if not args.ir:  # Si no se pidió --ir explícitamente, mostramos el IR
            print("\n--- LLVM IR generado ---")
            with open(out) as f:
                print(f.read())