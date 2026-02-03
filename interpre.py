import json
import re
import sys
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
    def __init__(self, value, declared_type='dynamic'):
        self.value = value
        self.declared_type = declared_type

    def __repr__(self):
        return f"Symbol(value={self.value}, type={self.declared_type})"
# ==============================================================================
# Tabla de Símbolos (Sin cambios)
# ==============================================================================
class SymbolTable:
    def __init__(self):
        self.symbols = {}
        self.function_symbols = {}
        self.function_params = {}
        self.function_param_values = {}
    def declare(self, name, symbol):
        """Declara un nuevo símbolo."""
        self.symbols[name] = symbol

    def set_value(self, name, value):
        """Asigna un nuevo valor a un símbolo existente."""
        if name in self.symbols:
            self.symbols[name].value = value
        else:
            raise UndeclaredVariableError(name)

    def get_value(self, name):
        """Obtiene el valor actual de un símbolo."""
        if name not in self.symbols:
            # Tu lógica para manejar literales como 'true', '123', etc.
            if str(name).lower() == 'true': return True
            if str(name).lower() == 'false': return False
            try: return int(name)
            except ValueError:
                try: return float(name)
                except ValueError: raise UndeclaredVariableError(name)
        return self.symbols[name].value

    def get_symbol(self, name):
        """Obtiene el objeto Symbol completo."""
        if name not in self.symbols:
            raise UndeclaredVariableError(name)
        return self.symbols[name]
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
            self.function_param_values[func_name] = {}
        self.function_param_values[func_name][param_name] = value

    def get_function_param_value(self, func_name, param_name):
        """Obtiene el valor de un parámetro de una función"""
        if (func_name in self.function_param_values and 
            param_name in self.function_param_values[func_name]):
            return self.function_param_values[func_name][param_name]
        raise UndeclaredVariableError(f"Parámetro '{param_name}' no tiene valor en función '{func_name}'")
    def __str__(self):
     # Variables normales
     symbols_str = f"Variables: { {k: v.value for k, v in self.symbols.items()} }"
    
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
    
     return f"Tabla de Símbolos:\n  {symbols_str}\n  {functions_str}\n  {params_str}"

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
     function_params = self.interpreter.symbol_table.get_function_params(self.function_name)
    
     # ASIGNAR PARÁMETROS A LA TABLA ESPECÍFICA
     self._assign_received_parameters(function_params)
    
     # Establecer función actual
     self.interpreter._current_function = self.function_name
    
     # Ejecutar bloque
     if "block" in function_def:
        self.interpreter._log(f"-> Ejecutando función '{self.function_name}'")
        
        old_break_flag = self.interpreter.break_flag
        result = None
        
        for statement in function_def["block"]:
            if self.interpreter.break_flag:
                break
            
            # Ejecutar el statement y capturar el resultado si es un return
            statement_result = self.interpreter.execute_node(statement)
            
            # Si el statement es un return, capturar el valor y salir
            if (isinstance(statement, dict) and "CallExpression" in statement and 
                statement["CallExpression"].get("function") == "Return"):
                result = statement_result
                break
        
        self.interpreter.break_flag = old_break_flag
        self.interpreter._current_function = None
        
        self.interpreter._log(f"<- Finalizada función '{self.function_name}'")
        return result
    
     self.interpreter._current_function = None
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

class Interpreter:
    def __init__(self):
        self.debug_mode = True 
        self.symbol_table = SymbolTable()
        self.break_flag = False
        self.switch_fall_through = False
        self._current_function = None
    def _log(self, message):
        """Función interna para imprimir mensajes solo si el modo debug está activo."""
        if self.debug_mode:
            print(message)        
    def interpret(self, ast):
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

    def execute_node(self, node):
        if not node: return
        node_type = list(node.keys())[0]
       # print(f"DEBUG: node_type = '{node_type}'")
        handler = getattr(self, f"handle_{node_type}", self.handle_unknown)
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
                "preIncrementStatement", "preDecrementStatement"
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
        Evalúa accesos profundos mixtos (variables y literales).
        Soporta: matriz[0:i], data["clave":j], arr[i:0], etc.
        """
        self._log(f"  Evaluando acceso general: {array_expression}")

        # 1. Regex: Captura nombre y contenido interno sin importar qué caracteres tenga
        match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\[(.*?)\]', array_expression)

        if not match:
            return f"<Error: Sintaxis inválida: {array_expression}>"

        array_name = match.group(1)
        raw_indices_content = match.group(2) # Ejemplo: "0:i" o '"id":k'

        try:
            # 2. Obtener la estructura base (Array o Diccionario)
            current_structure = self.symbol_table.get_value(array_name)

            # Parseo de JSON stringificado si es necesario
            if isinstance(current_structure, str):
                if (current_structure.startswith('[') and current_structure.endswith(']')) or \
                   (current_structure.startswith('{') and current_structure.endswith('}')):
                    try:
                        current_structure = json.loads(current_structure.replace("'", '"'))
                    except json.JSONDecodeError:
                        return f"<Error: Estructura corrupta en '{array_name}'>"

            # 3. Dividir los índices por ':'
            # Esto separa niveles. Ej: "0:i" -> ["0", "i"]
            indices_list = raw_indices_content.split(':')

            # 4. Recorrer y resolver CADA índice individualmente
            for raw_index in indices_list:
                raw_index = raw_index.strip()
                index_value = None

                # === LÓGICA HÍBRIDA DE RESOLUCIÓN ===
                
                # CASO A: Literal de String (entre comillas) -> "clave"
                if (raw_index.startswith('"') and raw_index.endswith('"')) or \
                   (raw_index.startswith("'") and raw_index.endswith("'")):
                    index_value = raw_index[1:-1]
                
                # CASO B: Literal Numérico -> 0, 15, etc.
                elif raw_index.isdigit():
                    index_value = int(raw_index)
                
                # CASO C: Variable -> i, j, k
                else:
                    try:
                        # Buscamos en la tabla de símbolos. 
                        # Esto hace que funcione en For, While, If, etc.
                        index_value = self.symbol_table.get_value(raw_index)
                    except UndeclaredVariableError:
                        return f"<Error: Variable '{raw_index}' no definida en este contexto>"

                self._log(f"    -> Nivel resuelto: '{raw_index}' es {index_value} ({type(index_value).__name__})")

                # === NAVEGACIÓN EN LA ESTRUCTURA ===
                try:
                    if isinstance(current_structure, list):
                        # Es un Array: necesitamos un entero
                        if not isinstance(index_value, int):
                            # Intento final de conversión si vino como string numérico
                            try: 
                                index_value = int(index_value)
                            except:
                                return f"<Error: Array requiere índice entero, se recibió '{index_value}'>"
                        
                        if 0 <= index_value < len(current_structure):
                            current_structure = current_structure[index_value]
                        else:
                            return f"<Error: Índice {index_value} fuera de límites (0..{len(current_structure)-1})>"
                    
                    elif isinstance(current_structure, dict):
                        # Es un Diccionario: usamos la clave tal cual
                        if index_value in current_structure:
                            current_structure = current_structure[index_value]
                        else:
                            return f"<Error: Clave '{index_value}' no existe>"
                    else:
                        return f"<Error: Tipo no indexable: {type(current_structure).__name__}>"

                except Exception as e:
                    return f"<Error interno de acceso: {e}>"

            # Valor final tras profundizar
            return current_structure

        except UndeclaredVariableError:
            return f"<Error: Variable base '{array_name}' no existe>"        
     
    def evaluate_expression(self, expression_str):
     """
     Evalúa expresiones booleanas y lógicas.
     Reemplaza variables y parámetros por sus valores antes de evaluar.
     """
     # ===== INICIALIZAR function_params para evitar NameError =====
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
                    expression_str = re.sub(r'\b' + param_name + r'\b', str(param_value), expression_str)
                    self._log(f"  Reemplazado parámetro '{param_name}': {param_value}")
                except UndeclaredVariableError:
                    pass  # Parámetro sin valor

     # ===== BUSCAR VARIABLES NORMALES (EXCEPTO PARÁMETROS YA REEMPLAZADOS) =====
     variable_names = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', expression_str)
     for var in set(variable_names):
        # Evitar reemplazar palabras reservadas y parámetros ya procesados
        if var not in ['true', 'false', 'and', 'or', 'not'] and var not in function_params.keys():
            try:
                value = self.symbol_table.get_value(var)
                # Si es string, agregar comillas para la evaluación
                value_str = f'"{value}"' if isinstance(value, str) else str(value)
                expression_str = re.sub(r'\b' + var + r'\b', value_str, expression_str)
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
        call_parameters = self._parse_call_parameters_from_string(args_str)
        
        # Crear contexto y ejecutar función
        function_context = FunctionContext(self, function_name, call_parameters)
        result = function_context.execute_function()
        
        self._log(f"  Resultado de '{function_call_str}': {result}")
        return result
        
     except Exception as e:
        self._log(f"  Error ejecutando función '{function_call_str}': {e}")
        return f"<Error en {function_call_str}>"

    def _parse_call_parameters_from_string(self, args_str):
     """Parsea parámetros de llamada a función desde string"""
     if not args_str.strip():
        return []
    
     params = []
     # Procesar parámetros como "a: 1, b: 5, c: 5"
     param_parts = [p.strip() for p in args_str.split(',') if p.strip()]
    
     for param_part in param_parts:
        if ':' in param_part:
            # Formato "nombre: valor"
            _, value_part = param_part.split(':', 1)
            param_value = self._evaluate_parameter_value(value_part.strip())
        else:
            # Formato simple "valor"
            param_value = self._evaluate_parameter_value(param_part.strip())
            
        params.append(param_value)
        
     return params

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
        self._log(f"  Calculando (con jerarquía) la operación: '{expression_str}'")
        print(self._current_function)
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
                    expression_str = re.sub(r'\b' + param_name + r'\b', str(param_value), expression_str)
                    self._log(f"  Reemplazado parámetro '{param_name}': {param_value}")
                except UndeclaredVariableError:
                    # Si el parámetro no tiene valor, continuar sin reemplazar
                    pass
        
        
        # PRIMERO: Procesar parámetros de función si estamos en una función           
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d*|\.\d+|\d+|[+\-*/%()]', expression_str)
        resolved_tokens = []
        for token in tokens:
            if re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', token):
                try:
                    value = self.symbol_table.get_value(token)
                    numeric_value = None
                    if isinstance(value, (int, float)):
                        numeric_value = value
                    elif isinstance(value, str):
                        try:
                            numeric_value = float(value)
                        except (ValueError, TypeError):
                            raise InvalidOperationError(f"La variable '{token}' contiene un string no numérico ('{value}') y no puede usarse en un cálculo.")
                    else:
                        raise InvalidOperationError(f"La variable '{token}' es de un tipo no numérico ('{type(value).__name__}') y no puede usarse en un cálculo.")
                    resolved_tokens.append(numeric_value)
                except UndeclaredVariableError as e:
                    raise InvalidOperationError(f"Variable '{token}' no declarada en la operación.")
            else:
                try:
                    resolved_tokens.append(float(token))
                except ValueError:
                    resolved_tokens.append(token)
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
    
    def resolve_expression(self, expression_str):
     """
     Función principal que decide qué evaluador usar, basándose en tu diseño.
     """
     # Primero verificar si es una llamada a función
     if self._is_function_call(expression_str):
        return self._execute_function_call_from_string(expression_str)
    
     # Luego manejar parámetros de función si estamos en una función
     if hasattr(self, '_current_function') and self._current_function:
        function_params = self.symbol_table.get_function_params(self._current_function)
        for param_name in function_params.keys():
            if param_name in expression_str:
                # Si hay parámetros, usar el evaluador de expresiones que los maneja
                return self.evaluate_expression(expression_str)
    
     # Finalmente decidir entre aritmética y expresiones booleanas
     if self._is_valid_arithmetic_format(expression_str):
        return self._evaluate_arithmetic_operation(expression_str)
     else:
        return self.evaluate_expression(expression_str)

    def handle_VariableDeclaration(self, node):
     name = node["name"]
     value_node = node.get("value", {})
     declared_type = value_node.get("explicitType") or 'dynamic'
     initial_value = None
    
     raw_value = value_node.get("value")
    
     # ===== DETECTAR Y EJECUTAR LLAMADAS A FUNCIÓN =====
     if isinstance(raw_value, str) and self._is_function_call(raw_value):
        self._log(f"Declarando '{name}' con llamada a función: '{raw_value}'")
        initial_value = self._execute_function_call_from_string(raw_value)
     elif "operation" in value_node:
        operation_node = value_node["operation"]
        expression_str = operation_node.get("value") if isinstance(operation_node, dict) else operation_node
        self._log(f"Declarando '{name}' con operación: '{expression_str}'")
        initial_value = self.resolve_expression(expression_str)
     else:
        raw_value = value_node.get("value")
        ast_type = value_node.get("type")
        
        is_unresolved_variable = (
            ast_type == "string" and 
            isinstance(raw_value, str) and 
            not (raw_value.startswith('"') and raw_value.endswith('"'))
        )
        
        if is_unresolved_variable:
            try:
                initial_value = self.symbol_table.get_value(raw_value)
            except UndeclaredVariableError:
                initial_value = raw_value
        else:
            initial_value = raw_value

     new_symbol = Symbol(value=initial_value, declared_type=declared_type)
     self.symbol_table.declare(name, new_symbol)
     self._log(f"Declarada variable '{name}'. Símbolo: {new_symbol}")
    
    def handle_VariableAsignement(self, node):
     name = node["name"]
     value_node = node.get("value", {})
     final_value = None
     raw_value = value_node.get("value")
    
     # ===== DETECTAR Y EJECUTAR LLAMADAS A FUNCIÓN =====
     if isinstance(raw_value, str) and self._is_function_call(raw_value):
        self._log(f"Asignando a '{name}' con llamada a función: '{raw_value}'")
        final_value = self._execute_function_call_from_string(raw_value)
     elif "operation" in value_node:
        operation_node = value_node["operation"]
        expression_str = operation_node.get("value") if isinstance(operation_node, dict) else operation_node
        self._log(f"Asignando a '{name}' con operación: '{expression_str}'")
        final_value = self.resolve_expression(expression_str)
     else:
        raw_value = value_node.get("value")
        ast_type = value_node.get("type")
        
        is_unresolved_variable = (
            ast_type == "string" and 
            isinstance(raw_value, str) and 
            not (raw_value.startswith('"') and raw_value.endswith('"'))
        )
        
        if is_unresolved_variable:
            try:
                final_value = self.symbol_table.get_value(raw_value)
            except UndeclaredVariableError:
                final_value = raw_value
        else:
            final_value = raw_value
            
     self.symbol_table.set_value(name, final_value)
     self._log(f"Asignado nuevo valor a '{name}': {final_value}")
    # ==========================================================================
    # ¡CORRECCIÓN 2: Impresión inteligente de variables!
    # ==========================================================================
    def handle_CallExpression(self, node):
        function_name = node.get("function")
        if function_name == "Break":
            self.break_flag = True
            return

        if function_name == "Return":
         return_value_node = node.get("value", {})
         return_value = None
        
         if "value" in return_value_node:
            raw_value = return_value_node["value"]
            
            # Si es una llamada a función, ejecutarla
            if isinstance(raw_value, str) and self._is_function_call(raw_value):
                return_value = self._execute_function_call_from_string(raw_value)
            # Si es una variable o expresión
            elif isinstance(raw_value, str) and not (raw_value.startswith('"') and raw_value.endswith('"')):
                # ===== CORRECCIÓN CRÍTICA: BUSCAR EN PARÁMETROS PRIMERO =====
                if hasattr(self, '_current_function') and self._current_function:
                    function_params = self.symbol_table.get_function_params(self._current_function)
                    if raw_value in function_params:
                        try:
                            return_value = self.symbol_table.get_function_param_value(
                                self._current_function, raw_value
                            )
                            self._log(f"  Return usando parámetro '{raw_value}': {return_value}")
                        except UndeclaredVariableError:
                            pass
                
                # Si no se encontró como parámetro, continuar con la lógica normal
                if return_value is None:
                    if any(op in raw_value for op in ['+', '-', '*', '/', '%', '.']):
                        return_value = self.resolve_expression(raw_value)
                    else:
                        try:
                            return_value = self.symbol_table.get_value(raw_value)
                        except UndeclaredVariableError:
                            return_value = raw_value
            else:
                # Es un literal
                return_value = raw_value
                
         self._log(f"  Return con valor: {return_value}")
         return return_value

        arguments_node = node.get("arguments")
        param_type_node = node.get("paramType")
        raw_argument = arguments_node.get("value") if isinstance(arguments_node, dict) else arguments_node
        actual_param_type = param_type_node.get("value") if isinstance(param_type_node, dict) else param_type_node

        value_to_process = None
        if function_name == "print" and isinstance(raw_argument, str) and self._is_function_call(raw_argument):
         self._log(f"  Detectada llamada a función en print: '{raw_argument}'")
         value_to_process = self.resolve_expression(raw_argument)
        # 1. Acceso a Arrays
        elif actual_param_type == "ArrayAccess":
            if isinstance(raw_argument, str) and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', raw_argument):
                try:
                    variable_value = self.symbol_table.get_value(raw_argument)
                    if isinstance(variable_value, str) and '[' in variable_value and ']' in variable_value:
                        value_to_process = self._evaluate_array_access(variable_value)
                    else:
                        value_to_process = variable_value
                except UndeclaredVariableError:
                    value_to_process = f"<Error: Variable '{raw_argument}' no definida>"
            else:
                value_to_process = self._evaluate_array_access(raw_argument)

        # 2. Expresiones explícitas
        elif actual_param_type == "expression":
            value_to_process = self.evaluate_expression(raw_argument)

        # 3. Manejo de Strings y Operaciones
        elif isinstance(raw_argument, str):
            # --- CORRECCIÓN CRÍTICA AQUÍ ---
            
            # CASO A: Es explícitamente un STRING según el AST
            if actual_param_type == 'string':
                # Solo verificamos concatenación (con punto .), ignoramos +, -, *, /
                if '.' in raw_argument and not raw_argument.replace('.', '', 1).isdigit(): 
                    value_to_process = self._evaluate_concatenated_string(raw_argument)
                else:
                   if hasattr(self, '_current_function') and self._current_function:
                    function_params = self.symbol_table.get_function_params(self._current_function)
                    if raw_argument in function_params:
                        try:
                            value_to_process = self.symbol_table.get_function_param_value(
                                self._current_function, raw_argument
                            )
                            self._log(f"  Print usando parámetro '{raw_argument}': {value_to_process}")
                        except UndeclaredVariableError:
                            pass
                   if value_to_process is None:
                     try:
                        if " " not in raw_argument:
                            value_to_process = self.symbol_table.get_value(raw_argument)
                        else:
                            value_to_process = raw_argument
                     except UndeclaredVariableError:
                        value_to_process = raw_argument     
            # CASO B: NO es string explícito, chequeamos si es operación matemática
            elif any(op in raw_argument for op in ['+', '-', '*', '/', '%']):
                value_to_process = self.resolve_expression(raw_argument)
            
            # CASO C: Concatenación implícita
            elif '.' in raw_argument:
                value_to_process = self._evaluate_concatenated_string(raw_argument)
            
            # CASO D: Variable o Literal simple
            else:

                if hasattr(self, '_current_function') and self._current_function:
                 function_params = self.symbol_table.get_function_params(self._current_function)
                 if raw_argument in function_params:
                    try:
                        value_to_process = self.symbol_table.get_function_param_value(
                            self._current_function, raw_argument
                        )
                        self._log(f"  Print usando parámetro '{raw_argument}': {value_to_process}")
                    except UndeclaredVariableError:
                        pass
            
            # Si no es parámetro, buscar como variable normal
                if value_to_process is None:
                 try:
                    value_to_process = self.symbol_table.get_value(raw_argument)
                 except UndeclaredVariableError:
                    value_to_process = raw_argument
        else:
            value_to_process = raw_argument

        # Ejecución de la función (print, read, etc.)
        if function_name == "print":
            print(value_to_process)
        elif function_name == "read":
            variable_name = raw_argument
            user_input = input()
            final_value = user_input
            if actual_param_type == 'Int':
                try:
                    final_value = int(user_input)
                except (ValueError, TypeError):
                    self._log(f"Advertencia: no se pudo convertir '{user_input}' a int.")
                    final_value = 0
            elif actual_param_type == 'Float':
                try:
                    final_value = float(user_input)
                except (ValueError, TypeError):
                    self._log(f"Advertencia: no se pudo convertir '{user_input}' a float.")
                    final_value = 0.0
            elif actual_param_type == 'string':
                 final_value = user_input # Read string debe guardar el string, no convertir a bool
            
            self.symbol_table.set_value(variable_name, final_value)
            self._log(f"Leído '{final_value}' y asignado a la variable '{variable_name}'")
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
    
     # Extraer y procesar parámetros
     parameters_info = self._parse_function_parameters(node.get("parameters", {}))
    
     # Guardar la definición de la función
     self.symbol_table.declare_function(name, node)
    
     # Guardar información de parámetros
     self.symbol_table.declare_function_params(name, parameters_info)
    
     # Guardar tipo de retorno si existe
     return_type = node.get("explicitType", "inferred")
     self._log(f"Función '{name}' declarada. Parámetros: {parameters_info}, Retorno: {return_type}")

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

    def _parse_call_parameters(self, parameters_node):
     """Parsea los parámetros de una llamada a función"""
     params = []
    
     if "value" in parameters_node:
        params_str = parameters_node["value"]
        
        # Procesar parámetros como "a: 1, b: 5, c: 5"
        param_parts = [p.strip() for p in params_str.split(',') if p.strip()]
        
        for param_part in param_parts:
            if ':' in param_part:
                # Formato "nombre: valor"
                _, value_part = param_part.split(':', 1)
                param_value = self._evaluate_parameter_value(value_part.strip())
            else:
                # Formato simple "valor"
                param_value = self._evaluate_parameter_value(param_part.strip())
                
            params.append(param_value)
            
     return params

    def _evaluate_parameter_value(self, value_str):
     """Evalúa el valor de un parámetro (puede ser variable, expresión o literal)"""
     try:
        # Primero verificar si es una llamada a función
        if self._is_function_call(value_str):
            return self._execute_function_call_from_string(value_str)
        
        # Verificar si es una expresión con operaciones
        if any(op in value_str for op in ['+', '-', '*', '/', '%', '.']):
            return self.resolve_expression(value_str)
            
        # Intentar obtener como variable
        return self.symbol_table.get_value(value_str)
     except UndeclaredVariableError:
        # Si no es variable, tratar como literal
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
                # Es un string
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
            for statement in node["block"]:
                if self.break_flag:
                    break
                self.execute_node(statement)
        self._log("Finalizado bloque if-Condition.")
        return

     # 2. Procesar elseIf si existe
     current_node = node
     while "elseIf" in current_node:
        else_if_node = current_node["elseIf"]
        condition = else_if_node.get("condition") or else_if_node.get("value")
        
        if condition and self.evaluate_expression(condition):
            self._log(f"  Condición 'elseIf' ({condition}) es VERDADERA. Ejecutando su bloque.")
            if "block" in else_if_node:
                for statement in else_if_node["block"]:
                    if self.break_flag:
                        break
                    self.execute_node(statement)
            self._log("Finalizado bloque if-Condition.")
            return
        
        # Moverse al siguiente nivel de anidación
        current_node = else_if_node

     # 3. Procesar else si existe
     if "else" in current_node:
        self._log("  Ninguna condición anterior fue verdadera. Ejecutando bloque 'else'.")
        else_node = current_node["else"]
        if "block" in else_node:
            for statement in else_node["block"]:
                if self.break_flag:
                    break
                self.execute_node(statement)

     self._log("Finalizado bloque if-Condition.")
    def handle_ForLoop(self, node):
     iterator_str = node["iterator"]["value"]
     try:
        start, end = map(int, iterator_str.split(".."))
        variable_name = node["variable"]
        self._log(f"Iniciando bucle 'for' para '{variable_name}' desde {start} hasta {end}")
        
        # Asegurarse de que la variable de bucle exista en la tabla de símbolos
        try:
            self.symbol_table.get_symbol(variable_name)
        except UndeclaredVariableError:
            # Si no existe, la declaramos como un símbolo dinámico
            loop_var_symbol = Symbol(value=start, declared_type='dynamic')
            self.symbol_table.declare(variable_name, loop_var_symbol)

        for i in range(start, end + 1):
            self.symbol_table.set_value(variable_name, i)
            self._log(f"  Iteración: {variable_name} = {i}")
            
            # EJECUTAR DIRECTAMENTE LAS INSTRUCCIONES DEL BLOQUE
            block_content = node["block"]
            if isinstance(block_content, list):
                # Si el bloque es una lista de instrucciones, ejecutar cada una
                for statement in block_content:
                    if self.break_flag:
                        break
                    self.execute_node(statement)
            elif isinstance(block_content, dict):
                # Si el bloque es un diccionario (formato antiguo), usar execute_block
                self.execute_block(block_content)
                
        self._log(f"Finalizado bucle 'for' para '{variable_name}'.")
     except ValueError:
        self._log(f"Error: El iterador del bucle for '{iterator_str}' no es válido.")

    def handle_WhileLoop(self, node, block_node):
     """Maneja WhileLoop con bloque integrado"""
     condition_str = node["condition"]
     self._log(f"Iniciando bucle 'while' con condición: {condition_str}")
     self.break_flag = False
    
    # Verificar si el bloque está integrado en el nodo
     if "block" in node:
        block_content = node["block"]
        self._log("  Bloque encontrado dentro del WhileLoop")
        
        while self.evaluate_expression(condition_str):
            self._log("  Condición 'while' es VERDADERA. Ejecutando bloque.")
            
            # Ejecutar el bloque integrado
            if isinstance(block_content, list):
                for statement in block_content:
                    if self.break_flag:
                        break
                    self.execute_node(statement)
            elif isinstance(block_content, dict):
                self.execute_block(block_content)
            
            if self.break_flag:
                self._log("  Instrucción 'Break' detectada. Saliendo del bucle 'while'.")
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
        """Evalúa cadenas con variables concatenadas, como "hola " . var."""
        parts = [p.strip() for p in arg_str.split('.')]
        result = []
        for part in parts:
            if part.startswith('"') and part.endswith('"'):
                result.append(part[1:-1]) # Añade el literal de la cadena
            elif self._is_function_call(part):
             # --- NUEVA LÓGICA: Ejecutar función y usar su resultado ---
             function_result = self._execute_function_call_from_string(part)
             result.append(str(function_result))
            else:
                try:
                    # Intenta obtener el valor de la variable
                    result.append(str(self.symbol_table.get_value(part)))
                except UndeclaredVariableError:
                    result.append(f"<{part} no definida>") # Error si la variable no existe
        return "".join(result)

    def handle_PerformWhileLoop(self, node):
        condition_str = node["value"]
        self._log(f"Iniciando bucle 'perform-while' (do-while). La condición a chequear es: {condition_str}")
        self.break_flag = False
        
        while True:
            self._log("  Ejecutando bloque del perform-while (al menos una vez).")
            
            # CORRECCIÓN: Manejar tanto listas (formato actual del AST) como diccionarios
            block_content = node["block"]
            
            if isinstance(block_content, list):
                # Si es una lista, iteramos y ejecutamos nodo por nodo
                for statement in block_content:
                    if self.break_flag:
                        break
                    self.execute_node(statement)
            elif isinstance(block_content, dict):
                # Si es un diccionario (formato legacy), usamos execute_block
                self.execute_block(block_content)
            
            # Verificación de Break
            if self.break_flag:
                self._log("  'Break' detectado. Saliendo del bucle.")
                break
            
            # Evaluar la condición para decidir si repetir
            if not self.evaluate_expression(condition_str):
                self._log(f"  La condición '{condition_str}' ahora es falsa. Saliendo del bucle.")
                break
                
        self.break_flag = False
        self._log("Finalizado bucle 'perform-while'.")
        
    def handle_SwitchStatement(self, node):
     switch_var_name = node["value"]
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
            for statement in block_content:
                if self.break_flag:
                    break
                self.execute_node(statement)
            
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
        for statement in block_content:
            if self.break_flag:
                break
            self.execute_node(statement)
    
     self.break_flag = False
     self.switch_fall_through = False
     self._log("Finalizado 'switch'.")
def main():
    if len(sys.argv) != 2:
        print("Uso: python interpre.py <ruta_al_archivo_json>")
        sys.exit(1)
        
    json_file_path = sys.argv[1]
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            ast_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{json_file_path}'.")
        return
    except json.JSONDecodeError:
        print(f"Error: El archivo JSON en '{json_file_path}' está mal formado.")
        return

    interpreter = Interpreter()
    import time
    inicio = time.perf_counter()  # Usar perf_counter para mayor precisión
    
    try:
        interpreter.interpret(ast_data)
        
        # Calcular tiempo transcurrido
        fin = time.perf_counter()
        tiempo_transcurrido = fin - inicio
        
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
            
    except InterpreterError as e:
        # También mostrar tiempo incluso si hay error
        fin = time.perf_counter()
        tiempo_transcurrido = fin - inicio
        
        print(f"\n❌ ERROR DURANTE LA EJECUCIÓN: {e}")
        print(f"⏱️  Tiempo transcurrido hasta el error: {tiempo_transcurrido:.6f} segundos")
if __name__ == "__main__":
    main()