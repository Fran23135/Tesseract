import json
import sys
import os
import re
from llvmlite import ir, binding

# ------------------------------------------------------------------------------
# Clases Auxiliares para Símbolos
# ------------------------------------------------------------------------------
class Variable:
    """Contenedor para una variable en la tabla de símbolos."""
    def __init__(self, pointer, type):
        self.pointer = pointer
        self.type = type

class Funcion:
    """Contenedor para una función en la tabla de símbolos."""
    def __init__(self, llvm_function_obj, return_type):
        self.function = llvm_function_obj
        self.return_type = return_type

# ------------------------------------------------------------------------------
# Clase Principal del Compilador
# ------------------------------------------------------------------------------
class LLVMCompiler:
    def __init__(self):
        # --- Configuración de LLVM ---
        self.binding = binding
        self.binding.initialize()
        self.binding.initialize_native_target()
        self.binding.initialize_native_asmprinter()

        # --- Módulo y Constructor Principal ---
        self.module = ir.Module(name="main_module")
        self.module.triple = self.binding.get_default_triple()
        self.builder = None # Se inicializará dentro de cada función

        # --- Tipos Personalizados ---
        self.range_type = ir.LiteralStructType([ir.IntType(32), ir.IntType(32)])

        # --- Tablas de Símbolos ---
        # Usamos una pila de diccionarios para manejar los scopes
        self.symbol_table_stack = [{}] 
        self.function_table = {}

        # --- Contexto de Control de Flujo ---
        self.loop_exit_blocks = [] # Pila para saber a dónde saltar en un 'break'
        self.current_function = None

        # --- Prototipos de Funciones Externas (de C) ---
        self._declare_runtime_functions()

    # --------------------------------------------------------------------------
    # Sección de Configuración y Helpers
    # --------------------------------------------------------------------------
    def _declare_runtime_functions(self):
        """Declara funciones de C para poder llamarlas desde LLVM."""
        voidptr_t = ir.IntType(8).as_pointer()
        # printf
        printf_type = ir.FunctionType(ir.IntType(32), [voidptr_t], var_arg=True)
        self.printf = ir.Function(self.module, printf_type, name="printf")
        # strcmp
        strcmp_type = ir.FunctionType(ir.IntType(32), [voidptr_t, voidptr_t])
        self.strcmp = ir.Function(self.module, strcmp_type, name="strcmp")
        # scanf
        scanf_type = ir.FunctionType(ir.IntType(32), [voidptr_t], var_arg=True)
        self.scanf = ir.Function(self.module, scanf_type, name="scanf")
        # malloc
        malloc_type = ir.FunctionType(voidptr_t, [ir.IntType(32)])
        self.malloc = ir.Function(self.module, malloc_type, name="malloc")

    def enter_scope(self):
        self.symbol_table_stack.append({})

    def exit_scope(self):
        self.symbol_table_stack.pop()

    def _find_variable(self, name):
        """Busca una variable desde el scope actual hacia afuera."""
        for scope in reversed(self.symbol_table_stack):
            if name in scope:
                return scope[name]
        return None

    def _get_llvm_type(self, type_str, size=0):
        if type_str == "float": return ir.DoubleType()
        if type_str == "string": return ir.IntType(8).as_pointer()
        if type_str == "boolean": return ir.IntType(1)
        if type_str == "Range": return self.range_type
        if type_str == "Array": return ir.ArrayType(ir.IntType(32), size)
        return ir.IntType(32)

    def _create_global_string(self, text, name_hint=""):
        """Crea una cadena de texto global constante."""
        name = f".str_{name_hint}_{abs(hash(text))}"
        if name in self.module.globals:
            return self.module.get_global(name)

        c_string = ir.Constant(ir.ArrayType(ir.IntType(8), len(text)), bytearray(text.encode("utf8")))
        global_var = ir.GlobalVariable(self.module, c_string.type, name=name)
        global_var.initializer = c_string
        global_var.linkage = 'internal'
        return global_var

    # --------------------------------------------------------------------------
    # Compilación Principal
    # --------------------------------------------------------------------------
    def compile(self, ast):
        """Punto de entrada para compilar el AST completo."""
        # Función 'main' donde empieza la ejecución
        func_type = ir.FunctionType(ir.IntType(32), [], False)
        self.main_function = ir.Function(self.module, func_type, name="main")
        self.current_function = self.main_function
        
        entry_block = self.main_function.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)

        if "Program" in ast:
            for node in ast["Program"]:
                self._compile_node(node)
        
        # 'main' debe terminar con 'return 0'
        self.builder.ret(ir.Constant(ir.IntType(32), 0))

    def _compile_node(self, node):
        if not node: return
        node_type = list(node.keys())[0]
        handler = getattr(self, f"handle_{node_type}", self.handle_unknown)
        return handler(node[node_type])

    # --------------------------------------------------------------------------
    # Compilador de Expresiones y Condiciones
    # --------------------------------------------------------------------------
    def _compile_expression(self, expr_str):
        expr_str = str(expr_str).strip()
        match = re.match(r"^\s*(-?[\w\.]+)\s*([+\-*/%])\s*(-?[\w\.]+)\s*$", expr_str)
        
        if not match: # Literal o variable
            var = self._find_variable(expr_str)
            if var: return self.builder.load(var.pointer, name=f"load_{expr_str}")
            else:
                if expr_str.lower() == 'true': return ir.Constant(ir.IntType(1), 1)
                if expr_str.lower() == 'false': return ir.Constant(ir.IntType(1), 0)
                try: return ir.Constant(ir.IntType(32), int(expr_str))
                except ValueError:
                    try: return ir.Constant(ir.DoubleType(), float(expr_str))
                    except ValueError:
                        if expr_str.startswith('"') and expr_str.endswith('"'): expr_str = expr_str[1:-1]
                        str_ptr = self._create_global_string(expr_str + '\0')
                        return str_ptr.gep([ir.Constant(ir.IntType(32), 0)] * 2)

        lhs_str, op, rhs_str = match.groups()
        lhs_val = self._compile_expression(lhs_str)
        rhs_val = self._compile_expression(rhs_str)
        
        is_float = isinstance(lhs_val.type, ir.DoubleType) or isinstance(rhs_val.type, ir.DoubleType)
        if is_float:
            if isinstance(lhs_val.type, ir.IntType): lhs_val = self.builder.sitofp(lhs_val, ir.DoubleType())
            if isinstance(rhs_val.type, ir.IntType): rhs_val = self.builder.sitofp(rhs_val, ir.DoubleType())

        if op == '+': return self.builder.fadd(lhs_val, rhs_val, 'add_f') if is_float else self.builder.add(lhs_val, rhs_val, 'add_i')
        if op == '-': return self.builder.fsub(lhs_val, rhs_val, 'sub_f') if is_float else self.builder.sub(lhs_val, rhs_val, 'sub_i')
        if op == '*': return self.builder.fmul(lhs_val, rhs_val, 'mul_f') if is_float else self.builder.mul(lhs_val, rhs_val, 'mul_i')
        if op == '/':
            if not is_float: # Promover a float para divisiones
                lhs_val = self.builder.sitofp(lhs_val, ir.DoubleType())
                rhs_val = self.builder.sitofp(rhs_val, ir.DoubleType())
            return self.builder.fdiv(lhs_val, rhs_val, 'div_f')
        if op == '%': return self.builder.srem(lhs_val, rhs_val, 'mod_i')
        raise Exception(f"Operador no soportado: {op}")

    def _compile_condition(self, condition_str):
        if "&&" in condition_str:
            lhs_str, rhs_str = condition_str.split("&&", 1)
            rhs_block = self.current_function.append_basic_block("cond_rhs")
            end_block = self.current_function.append_basic_block("cond_end")
            lhs_val = self._compile_condition(lhs_str)
            lhs_end_block = self.builder.block
            self.builder.cbranch(lhs_val, rhs_block, end_block)
            self.builder.position_at_end(rhs_block)
            rhs_val = self._compile_condition(rhs_str)
            rhs_end_block = self.builder.block
            self.builder.branch(end_block)
            self.builder.position_at_end(end_block)
            phi = self.builder.phi(ir.IntType(1), "and_res")
            phi.add_incoming(ir.Constant(ir.IntType(1), 0), lhs_end_block)
            phi.add_incoming(rhs_val, rhs_end_block)
            return phi
        elif "||" in condition_str:
            lhs_str, rhs_str = condition_str.split("||", 1)
            rhs_block = self.current_function.append_basic_block("cond_rhs")
            end_block = self.current_function.append_basic_block("cond_end")
            lhs_val = self._compile_condition(lhs_str)
            lhs_end_block = self.builder.block
            self.builder.cbranch(lhs_val, end_block, rhs_block) # Invertido para OR
            self.builder.position_at_end(rhs_block)
            rhs_val = self._compile_condition(rhs_str)
            rhs_end_block = self.builder.block
            self.builder.branch(end_block)
            self.builder.position_at_end(end_block)
            phi = self.builder.phi(ir.IntType(1), "or_res")
            phi.add_incoming(ir.Constant(ir.IntType(1), 1), lhs_end_block)
            phi.add_incoming(rhs_val, rhs_end_block)
            return phi
        else:
            match = re.match(r"^\s*(.+?)\s*(==|>|<|>=|<=|!=)\s*(.+?)\s*$", condition_str.strip())
            if not match: return self._compile_expression(condition_str) # Para condiciones truthy/falsy
            lhs_str, op, rhs_str = match.groups()
            lhs_val = self._compile_expression(lhs_str)
            rhs_val = self._compile_expression(rhs_str)
            is_string = isinstance(lhs_val.type, ir.PointerType) and isinstance(rhs_val.type, ir.PointerType)
            if is_string:
                strcmp_res = self.builder.call(self.strcmp, [lhs_val, rhs_val])
                zero = ir.Constant(ir.IntType(32), 0)
                return self.builder.icmp_signed(op, strcmp_res, zero)
            is_float = isinstance(lhs_val.type, ir.DoubleType) or isinstance(rhs_val.type, ir.DoubleType)
            if is_float:
                if isinstance(lhs_val.type, ir.IntType): lhs_val = self.builder.sitofp(lhs_val, ir.DoubleType())
                if isinstance(rhs_val.type, ir.IntType): rhs_val = self.builder.sitofp(rhs_val, ir.DoubleType())
                return self.builder.fcmp_ordered(op, lhs_val, rhs_val)
            else:
                return self.builder.icmp_signed(op, lhs_val, rhs_val)

    # --------------------------------------------------------------------------
    # MANEJADORES DE NODOS DEL AST
    # --------------------------------------------------------------------------
    
    def handle_VariableDeclaration(self, node):
        var_name = node["name"]
        value_node = node.get("value", {})
        explicit_type_str = value_node.get("type")
        initial_value = value_node.get("value")
        operation = value_node.get("operation")
        type_str = explicit_type_str
        if not type_str:
            if operation: type_str = "float" if '.' in operation else "int"
            elif isinstance(initial_value, str): type_str = "string"
            elif isinstance(initial_value, float): type_str = "float"
            elif isinstance(initial_value, bool): type_str = "boolean"
            else: type_str = "int"
        
        value_to_store = None
        if operation: value_to_store = self._compile_expression(operation)
        elif initial_value is not None: value_to_store = self._compile_expression(initial_value)

        final_llvm_type = self._get_llvm_type(type_str)
        if explicit_type_str and value_to_store and final_llvm_type != value_to_store.type:
            can_cast = isinstance(final_llvm_type, ir.DoubleType) and isinstance(value_to_store.type, ir.IntType)
            if not can_cast: raise TypeError(f"Conflicto de tipos: no se puede asignar '{value_to_store.type}' a la variable '{var_name}' declarada como '{explicit_type_str}'")

        var_ptr = self.builder.alloca(final_llvm_type, name=var_name)
        self.symbol_table_stack[-1][var_name] = Variable(pointer=var_ptr, type=final_llvm_type)
        if value_to_store:
            if final_llvm_type != value_to_store.type and isinstance(final_llvm_type, ir.DoubleType):
                value_to_store = self.builder.sitofp(value_to_store, ir.DoubleType(), 'i2f_cast')
            self.builder.store(value_to_store, var_ptr)

    def handle_VariableAsignement(self, node):
        var_name = node["name"]
        var = self._find_variable(var_name)
        if not var: raise Exception(f"Error: variable no declarada '{var_name}'")

        value_node = node.get("value", {})
        value_to_store = self._compile_expression(value_node.get("operation") or value_node.get("value"))
        
        is_var_bool = isinstance(var.type, ir.IntType) and var.type.width == 1
        is_val_int = isinstance(value_to_store.type, ir.IntType) and value_to_store.type.width == 32
        if is_var_bool and is_val_int:
            zero = ir.Constant(ir.IntType(32), 0)
            value_to_store = self.builder.icmp_signed('!=', value_to_store, zero, 'i32_to_bool')
        elif isinstance(var.type, ir.DoubleType) and isinstance(value_to_store.type, ir.IntType):
            value_to_store = self.builder.sitofp(value_to_store, ir.DoubleType(), 'i2f_cast_assign')
        
        if value_to_store.type != var.type: raise TypeError(f"Conflicto de tipos: no se puede asignar '{value_to_store.type}' a la variable '{var_name}' de tipo '{var.type}'")
        self.builder.store(value_to_store, var.pointer)

    def handle_CallExpression(self, node):
        
        function_name = node["function"]
        if function_name == "print":
            value_to_print = self._compile_expression(node["arguments"])
            value_type = value_to_print.type
            if isinstance(value_type, ir.DoubleType): format_str = "%f\n\0"
            elif isinstance(value_type, ir.IntType) and value_type.width > 1: format_str = "%d\n\0"
            elif isinstance(value_type, ir.IntType) and value_type.width == 1: format_str = "%d\n\0" # Imprimir bool como 0 o 1
            elif isinstance(value_type, ir.PointerType): format_str = "%s\n\0"
            else: format_str = "Valor desconocido\n\0"
            format_str_ptr = self._create_global_string(format_str).gep([ir.Constant(ir.IntType(32), 0)] * 2)
            self.builder.call(self.printf, [format_str_ptr, value_to_print])
        elif function_name == "read":
            var_name = node["arguments"]
            var = self._find_variable(var_name)
            if not var: raise Exception(f"Variable '{var_name}' no declarada para 'read'")
            # Simplificación: solo leemos enteros
            format_str = self._create_global_string("%d\0").gep([ir.Constant(ir.IntType(32), 0)]*2)
            self.builder.call(self.scanf, [format_str, var.pointer])

    def handle_if_Condition(self, node):
        condition_val = self._compile_condition(node["condition"])
        then_block = self.current_function.append_basic_block("if_then")
        merge_block = self.current_function.append_basic_block("if_merge")
        else_block = merge_block
        if node.get("elseIf") or node.get("else"): else_block = self.current_function.append_basic_block("if_else")
        self.builder.cbranch(condition_val, then_block, else_block)
        self.builder.position_at_end(then_block)
        if node.get("block"): self.execute_block(node["block"])
        if not self.builder.block.is_terminated: self.builder.branch(merge_block)
        if else_block != merge_block:
            self.builder.position_at_end(else_block)
            # Simplificación: solo maneja 'else', no 'else if' anidado.
            if node.get("else"): self.execute_block(node["else"]["block"])
            elif node.get("elseIf"): self.execute_block(node["elseIf"]["block"]) # Placeholder
            if not self.builder.block.is_terminated: self.builder.branch(merge_block)
        self.builder.position_at_end(merge_block)

    def handle_ForLoop(self, node):
        self.enter_scope()
        var_name = node["variable"]
        start_str, end_str = node["iterator"]["value"].split("..")
        start_val = ir.Constant(ir.IntType(32), int(start_str))
        end_val = ir.Constant(ir.IntType(32), int(end_str.replace("<", "")))
        loop_header = self.current_function.append_basic_block("loop_header")
        loop_body = self.current_function.append_basic_block("loop_body")
        loop_exit = self.current_function.append_basic_block("loop_exit")
        self.loop_exit_blocks.append(loop_exit)
        loop_var_ptr = self.builder.alloca(ir.IntType(32), name=var_name)
        self.builder.store(start_val, loop_var_ptr)
        self.symbol_table_stack[-1][var_name] = Variable(pointer=loop_var_ptr, type=ir.IntType(32))
        self.builder.branch(loop_header)
        self.builder.position_at_end(loop_header)
        current_val = self.builder.load(loop_var_ptr)
        cond = self.builder.icmp_signed("<=", current_val, end_val, "loop_cond")
        self.builder.cbranch(cond, loop_body, loop_exit)
        self.builder.position_at_end(loop_body)
        if node.get("block"): self.execute_block(node["block"])
        current_val_body = self.builder.load(loop_var_ptr)
        next_val = self.builder.add(current_val_body, ir.Constant(ir.IntType(32), 1))
        self.builder.store(next_val, loop_var_ptr)
        self.builder.branch(loop_header)
        self.builder.position_at_end(loop_exit)
        self.loop_exit_blocks.pop()
        self.exit_scope()

    def handle_WhileLoop(self, node):
        loop_header = self.current_function.append_basic_block("while_header")
        loop_body = self.current_function.append_basic_block("while_body")
        loop_exit = self.current_function.append_basic_block("while_exit")
        self.loop_exit_blocks.append(loop_exit)
        self.builder.branch(loop_header)
        self.builder.position_at_end(loop_header)
        cond = self._compile_condition(node["condition"])
        self.builder.cbranch(cond, loop_body, loop_exit)
        self.builder.position_at_end(loop_body)
        if node.get("block"): self.execute_block(node["block"])
        self.builder.branch(loop_header)
        self.builder.position_at_end(loop_exit)
        self.loop_exit_blocks.pop()

    def handle_PerformWhileLoop(self, node):
        loop_body = self.current_function.append_basic_block("perform_body")
        loop_header = self.current_function.append_basic_block("perform_header")
        loop_exit = self.current_function.append_basic_block("perform_exit")
        self.loop_exit_blocks.append(loop_exit)
        self.builder.branch(loop_body)
        self.builder.position_at_end(loop_body)
        if node.get("block"): self.execute_block(node["block"])
        self.builder.branch(loop_header) # Ir a comprobar la condición
        self.builder.position_at_end(loop_header)
        cond = self._compile_condition(node["value"]) # El AST usa "value" para la condición
        self.builder.cbranch(cond, loop_body, loop_exit)
        self.builder.position_at_end(loop_exit)
        self.loop_exit_blocks.pop()

    def handle_SwitchStatement(self, node):
        switch_val = self._compile_expression(node["value"])
        default_block = self.current_function.append_basic_block("sw_default")
        exit_block = self.current_function.append_basic_block("sw_exit")
        self.loop_exit_blocks.append(exit_block)

        # Crear el switch y añadir el caso default
        switch = self.builder.switch(switch_val, default_block)
        
        # Iterar sobre los casos y añadirlos
        cases = node.get("block", {}).get("case", [])
        if not isinstance(cases, list): cases = [cases] # Asegurar que sea una lista
        
        for case_node in cases:
            case_val = ir.Constant(ir.IntType(32), int(case_node["value"]))
            case_block = self.current_function.append_basic_block(f"case_{case_node['value']}")
            switch.add_case(case_val, case_block)
            self.builder.position_at_end(case_block)
            self.execute_block({"statements": case_node.get("statements", {})})
            if not self.builder.block.is_terminated: self.builder.branch(exit_block)

        # Rellenar el bloque default
        self.builder.position_at_end(default_block)
        default_node = node.get("block", {}).get("defaultCase", {})
        if default_node: self.execute_block({"statements": default_node.get("statements", {})})
        if not self.builder.block.is_terminated: self.builder.branch(exit_block)

        self.builder.position_at_end(exit_block)
        self.loop_exit_blocks.pop()

    def handle_Break(self, node):
        if not self.loop_exit_blocks: raise Exception("'break' fuera de un bucle o switch")
        self.builder.branch(self.loop_exit_blocks[-1])
        
    def execute_block(self, block_node):
        if not block_node: return
        executable_keys = ["callExpression", "variableDeclaration", "variableAsignement", "postIncrementStatement", "break"]
        if "statements" in block_node:
            for key, value in block_node["statements"].items():
                if key in executable_keys:
                    self._compile_node({key[0].upper() + key[1:]: value})
        else: # Bloques simples
            for key, value in block_node.items():
                if key in executable_keys:
                    self._compile_node({key[0].upper() + key[1:]: value})
    
    def handle_unknown(self, node_content):
        # Ignorar nodos no ejecutables que pueden aparecer en los bloques
        if isinstance(node_content, str) and node_content in ["BlockStart", "BlockEnd"]:
            return
        print(f"ADVERTENCIA: No se ha implementado la generación de LLVM para el nodo: {node_content}")

# ------------------------------------------------------------------------------
# Punto de Entrada del Script
# ------------------------------------------------------------------------------
def main():
    if len(sys.argv) != 2:
        print("Uso: python compiler.py <ruta_al_archivo_json>")
        sys.exit(1)
        
    json_file_path = sys.argv[1]
    output_file_path = "input.ll"

    try:
        with open(json_file_path, "r", encoding="utf-8") as f: ast_data = json.load(f)
    except Exception as e: print(f"Error al leer el archivo JSON: {e}"); return

    compiler = LLVMCompiler()
    compiler.compile(ast_data)
    llvm_ir_code = str(compiler.module)
    
    with open(output_file_path, "w") as f:
        f.write(llvm_ir_code)

    print(f"✅ Compilación a LLVM IR completada. Código guardado en: {output_file_path}")

if __name__ == "__main__":
    main()