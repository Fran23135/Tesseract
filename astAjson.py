#import json
import ujson as json
import re
import sys

class ASTNode:
    def __init__(self, node_type, value, indent):
        self.type = node_type
        self.value = value
        self.indent = indent
        self.children = []

def _reparent_metadata_nodes(nodes):
    """
    Post-procesa una lista de nodos para re-anidar metadatos (como ParamType)
    dentro de sus nodos padres correctos (como CallExpression).
    """
    if not nodes:
        return []

    METADATA_TYPES = {"ParamType", "Type", "ExplicitType", "Operation"}
    PARENT_TYPES = {"CallExpression", "VariableDeclaration", "VariableAsignement"}

    new_list = []
    i = 0
    while i < len(nodes):
        current_node = nodes[i]
        new_list.append(current_node)
        
        if current_node.type in PARENT_TYPES:
            j = i + 1
            while j < len(nodes) and nodes[j].type in METADATA_TYPES:
                metadata_node = nodes[j]
                current_node.children.append(metadata_node)
                j += 1
            i = j
        else:
            i += 1
            
    for node in new_list:
        if node.children:
            node.children = _reparent_metadata_nodes(node.children)
            
    return new_list

def parse_ast(file_path):
    """
    Parsea el archivo de texto del AST y lo convierte en una estructura de árbol de nodos.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: El archivo '{file_path}' no fue encontrado.")
        return None

    root = ASTNode("Program", "", -1)
    stack = [root]

    for line_num, line in enumerate(lines):
        if not line.strip() or (line_num == 0 and line.strip() == "Program"):
            continue
        
        indent = len(line) - len(line.lstrip(" "))
        line_stripped = line.strip()

        if ':' in line_stripped:
            parts = line_stripped.split(":", 1)
            node_type = parts[0].strip()
            value = parts[1].strip()
        else:
            node_type = line_stripped
            value = ""

        # IGNORAR BlockStart y BlockEnd durante el parseo
        if node_type == "Block" and value in ["BlockStart", "BlockEnd"]:
            continue

        node = ASTNode(node_type, value, indent)

        while stack and stack[-1].indent >= indent:
            stack.pop()
        
        if stack:
            stack[-1].children.append(node)
        else:
            print(f"Advertencia: Nodo '{node.type}' sin padre en la línea {line_num + 1}.")
            root.children.append(node)

        stack.append(node)
        
    root.children = _reparent_metadata_nodes(root.children)
        
    return root

def convert_value(v):
    """
    Convierte un valor de string a su tipo de dato más apropiado (int, float, bool, None).
    """
    v = v.strip()
    if v == "True": return True
    if v == "False": return False
    if v == "NULL": return None

    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
        
    try: return int(v)
    except ValueError: pass
    try: return float(v)
    except ValueError: pass
    
    return v

def extract_call_and_var_from_node(node):
    """
    Extrae CallExpression y VariableAsignement de un nodo de manera recursiva y plana.
    """
    call_expressions = []
    var_assignment = None
    
    i = 0
    while i < len(node.children):
        child = node.children[i]
        
        if child.type == "CallExpression":
            call_obj = {
                'function': convert_value(child.value)
            }
            
            # Extraer Arguments y ParamType directos
            for subchild in child.children:
                if subchild.type == "Arguments":
                    call_obj['arguments'] = {'value': convert_value(subchild.value)}
                elif subchild.type == "ParamType" or subchild.type == "Type":
                    call_obj['paramType'] = convert_value(subchild.value)
            
            call_expressions.append(call_obj)
            
            # Extraer CallExpression anidadas y VariableAsignement
            nested_calls, nested_var = extract_call_and_var_from_node(child)
            call_expressions.extend(nested_calls)
            if nested_var and not var_assignment:
                var_assignment = nested_var
                
        elif child.type == "VariableAsignement":
            if not var_assignment:
                props = {'name': convert_value(child.value)}
                for subchild in child.children:
                    if subchild.type == "Value":
                        value_obj = {'value': convert_value(subchild.value)}
                        for vchild in subchild.children:
                            if vchild.type == "Type":
                                value_obj['type'] = convert_value(vchild.value)
                        props['value'] = value_obj
                    elif subchild.type == "Operation":
                        props['operation'] = {'value': convert_value(subchild.value)}
                var_assignment = props
        
        i += 1
    
    return call_expressions, var_assignment

def transform_case(node):
    """
    Transforma un nodo Case a su formato correcto con casos anidados.
    """
    props = {
        'case': convert_value(node.value)
    }
    
    # Extraer CallExpression y VariableAsignement
    call_expressions, var_assignment = extract_call_and_var_from_node(node)
    
    if call_expressions:
        props['callExpression'] = call_expressions
    if var_assignment:
        props['variableAsignement'] = var_assignment
    
    # Buscar casos anidados y DefaultCase
    nested_cases = []
    default_case = None
    
    for child in node.children:
        if child.type == "Case":
            nested_case = transform_case(child)
            nested_cases.append(nested_case)
        elif child.type == "DefaultCase":
            default_case = transform_default_case(child)
    
    # Si hay casos anidados, agregarlos después de callExpression y variableAsignement
    if nested_cases:
        return [props] + nested_cases + ([default_case] if default_case else [])
    
    if default_case:
        return [props, default_case]
    
    return props

def transform_default_case(node):
    """
    Transforma un nodo DefaultCase a su formato correcto.
    """
    props = {
        'default': True
    }
    
    for child in node.children:
        if child.type == "CallExpression":
            call_obj = {
                'function': convert_value(child.value)
            }
            for subchild in child.children:
                if subchild.type == "Arguments":
                    call_obj['arguments'] = {'value': convert_value(subchild.value)}
                elif subchild.type == "ParamType" or subchild.type == "Type":
                    call_obj['paramType'] = convert_value(subchild.value)
            props['callExpression'] = call_obj
    
    return props

def transform_block_for_switch(node):
    """
    Transforma un nodo SwitchStatement extrayendo casos directamente de sus hijos.
    Maneja casos anidados correctamente y ACEPTA TODOS LOS TIPOS DE NODOS.
    """
    all_cases = []
    default_case = None
    
    # Buscar casos directamente en los hijos del SwitchStatement
    for child in node.children:
        if child.type == "Case":
            case_obj = {
                'case': convert_value(child.value),
                'block': []
            }
            
            # Procesar todas las instrucciones dentro del caso
            for case_child in child.children:
                if case_child.type == "CallExpression":
                    call_obj = {
                        'function': convert_value(case_child.value)
                    }
                    for subchild in case_child.children:
                        if subchild.type == "Arguments":
                            call_obj['arguments'] = {'value': convert_value(subchild.value)}
                        elif subchild.type == "ParamType" or subchild.type == "Type":
                            call_obj['paramType'] = convert_value(subchild.value)
                    
                    case_obj['block'].append({"CallExpression": call_obj})
                
                elif case_child.type == "Break":
                    case_obj['block'].append({"CallExpression": {"function": "Break"}})
                
                # NUEVA LÓGICA: Procesar CUALQUIER tipo de nodo
                elif case_child.type == "ForLoop":
                    ordered_for = build_ordered_for_loop(case_child)
                    repaired = repair_for_loop_structure(ordered_for)
                    final = fix_for_loop_iterator(repaired)
                    case_obj['block'].append(final)
                
                elif case_child.type == "WhileLoop":
                    nested_while = build_ordered_while_loop(case_child)
                    case_obj['block'].append(nested_while)
                
                elif case_child.type == "PerformWhileLoop":
                    transformed = transform_to_dict(case_child)
                    perform_while_obj = {"PerformWhileLoop": transformed if transformed else {}}
                    repaired_perform_while = repair_perform_while_structure(perform_while_obj)
                    case_obj['block'].append(repaired_perform_while)
                
                elif case_child.type == "if_Condition":
                    transformed = transform_to_dict(case_child)
                    struct = {"if_Condition": transformed if transformed else {}}
                    repaired = repair_if_structure_new(struct)
                    case_obj['block'].append(repaired)
                
                elif case_child.type == "VariableDeclaration":
                    transformed = transform_to_dict(case_child)
                    if transformed is not None:
                        case_obj['block'].append({"VariableDeclaration": transformed})
                
                elif case_child.type == "VariableAsignement":
                    transformed = transform_to_dict(case_child)
                    if transformed is not None:
                        case_obj['block'].append({"VariableAsignement": transformed})
                
                elif case_child.type == "FunctionCall":
                    transformed = transform_to_dict(case_child)
                    if transformed is not None:
                        case_obj['block'].append({"FunctionCall": transformed})
                
                # Procesar casos anidados dentro de este caso
                elif case_child.type == "Case":
                    nested_case = {
                        'case': convert_value(case_child.value),
                        'block': []
                    }
                    
                    for nested_child in case_child.children:
                        if nested_child.type == "CallExpression":
                            nested_call_obj = {
                                'function': convert_value(nested_child.value)
                            }
                            for subchild in nested_child.children:
                                if subchild.type == "Arguments":
                                    nested_call_obj['arguments'] = {'value': convert_value(subchild.value)}
                                elif subchild.type == "ParamType" or subchild.type == "Type":
                                    nested_call_obj['paramType'] = convert_value(subchild.value)
                            
                            nested_case['block'].append({"CallExpression": nested_call_obj})
                        
                        elif nested_child.type == "Break":
                            nested_case['block'].append({"CallExpression": {"function": "Break"}})
                        
                        # NUEVA LÓGICA: Procesar otros tipos de nodos en casos anidados
                        else:
                            transformed = transform_to_dict(nested_child)
                            if transformed is not None:
                                nested_case['block'].append({nested_child.type: transformed})
                    
                    all_cases.append(nested_case)
                
                # Procesar default case anidado
                elif case_child.type == "DefaultCase":
                    default_case = {
                        'default': True,
                        'block': []
                    }
                    
                    for default_child in case_child.children:
                        if default_child.type == "CallExpression":
                            default_call_obj = {
                                'function': convert_value(default_child.value)
                            }
                            for subchild in default_child.children:
                                if subchild.type == "Arguments":
                                    default_call_obj['arguments'] = {'value': convert_value(subchild.value)}
                                elif subchild.type == "ParamType" or subchild.type == "Type":
                                    default_call_obj['paramType'] = convert_value(subchild.value)
                            
                            default_case['block'].append({"CallExpression": default_call_obj})
                        
                        elif default_child.type == "Break":
                            default_case['block'].append({"CallExpression": {"function": "Break"}})
                        
                        # NUEVA LÓGICA: Procesar otros tipos de nodos en default case
                        else:
                            transformed = transform_to_dict(default_child)
                            if transformed is not None:
                                default_case['block'].append({default_child.type: transformed})
                
                # NUEVA LÓGICA: Capturar cualquier otro tipo de nodo no manejado explícitamente
                else:
                    transformed = transform_to_dict(case_child)
                    if transformed is not None:
                        case_obj['block'].append({case_child.type: transformed})
            
            all_cases.append(case_obj)
        
        elif child.type == "DefaultCase":
            default_case = {
                'default': True,
                'block': []
            }
            
            # Procesar todas las instrucciones dentro del default case
            for default_child in child.children:
                if default_child.type == "CallExpression":
                    call_obj = {
                        'function': convert_value(default_child.value)
                    }
                    for subchild in default_child.children:
                        if subchild.type == "Arguments":
                            call_obj['arguments'] = {'value': convert_value(subchild.value)}
                        elif subchild.type == "ParamType" or subchild.type == "Type":
                            call_obj['paramType'] = convert_value(subchild.value)
                    
                    default_case['block'].append({"CallExpression": call_obj})
                
                elif default_child.type == "Break":
                    default_case['block'].append({"CallExpression": {"function": "Break"}})
                
                # NUEVA LÓGICA: Procesar CUALQUIER tipo de nodo en default case
                elif default_child.type == "ForLoop":
                    ordered_for = build_ordered_for_loop(default_child)
                    repaired = repair_for_loop_structure(ordered_for)
                    final = fix_for_loop_iterator(repaired)
                    default_case['block'].append(final)
                
                elif default_child.type == "WhileLoop":
                    nested_while = build_ordered_while_loop(default_child)
                    default_case['block'].append(nested_while)
                
                elif default_child.type == "PerformWhileLoop":
                    transformed = transform_to_dict(default_child)
                    perform_while_obj = {"PerformWhileLoop": transformed if transformed else {}}
                    repaired_perform_while = repair_perform_while_structure(perform_while_obj)
                    default_case['block'].append(repaired_perform_while)
                
                elif default_child.type == "if_Condition":
                    transformed = transform_to_dict(default_child)
                    struct = {"if_Condition": transformed if transformed else {}}
                    repaired = repair_if_structure_new(struct)
                    default_case['block'].append(repaired)
                
                elif default_child.type == "VariableDeclaration":
                    transformed = transform_to_dict(default_child)
                    if transformed is not None:
                        default_case['block'].append({"VariableDeclaration": transformed})
                
                elif default_child.type == "VariableAsignement":
                    transformed = transform_to_dict(default_child)
                    if transformed is not None:
                        default_case['block'].append({"VariableAsignement": transformed})
                
                elif default_child.type == "FunctionCall":
                    transformed = transform_to_dict(default_child)
                    if transformed is not None:
                        default_case['block'].append({"FunctionCall": transformed})
                
                # NUEVA LÓGICA: Capturar cualquier otro tipo de nodo
                else:
                    transformed = transform_to_dict(default_child)
                    if transformed is not None:
                        default_case['block'].append({default_child.type: transformed})
    
    result = {}
    if all_cases:
        result['cases'] = all_cases
    if default_case:
        result['defaultCase'] = default_case
    
    return result
def transform_block_content(node):
    """
    Transforma un nodo Block extrayendo solo el contenido, ignorando BlockStart/BlockEnd
    y retornando un array en lugar de un objeto
    """
    instructions = []
    
    for child in node.children:
        if child.value in ["BlockStart", "BlockEnd"]:
            continue
            
        transformed = transform_to_dict(child)
        if transformed is not None:
            # Si es un if_Condition, buscar y procesar su bloque interno
            if child.type == "if_Condition":
                # Buscar el bloque del if en los hijos
                for subchild in child.children:
                    if subchild.type == "Block":
                        # Procesar el bloque interno del if
                        if_block_content = transform_block_content(subchild)
                        if if_block_content:
                            transformed["block"] = if_block_content
                        break
            
            # Crear objeto con el tipo como clave - CORREGIR: usar "CallExpression" con E mayúscula
            if child.type == "CallExpression":
                instruction_obj = {"CallExpression": transformed}
            else:
                instruction_obj = {child.type: transformed}
            instructions.append(instruction_obj)
                
    return instructions

def transform_to_dict(node):
    """
    Transforma un nodo del AST a un diccionario.
    """
    if node.type in ["BlockEnd", "BlockStart"]:
        return None

    props = {}
    mapping = {
        "VariableDeclaration": "name", "VariableAsignement": "name",
        "Function": "name", "FunctionCall": "function", "CallExpression": "function",
        "if_Condition": "condition", "ForLoop": "variable", "WhileLoop": "condition"
    }
    
    if node.type in mapping:
        if node.value: 
            props[mapping[node.type]] = convert_value(node.value)
    elif node.value:
        props['value'] = convert_value(node.value)

    # PARA VariableDeclaration SIEMPRE incluir value, incluso si es null
    # ESTO DEBE IR AL FINAL PARA QUE NO SE SOBREESCRIBA
    if node.type == "VariableDeclaration" and "value" not in props:
        props["value"] = {"value": None}

    # Lista para almacenar CallExpression anidadas
    nested_calls = []
    
    for child in node.children:
        key = child.type
          
        if child.type in ["ParamType", "Type", "ExplicitType"]:
            child_value = convert_value(child.value)
        else:
            child_value = transform_to_dict(child)
        
        if child_value is not None:
            # SI ES UNA CallExpression ANIDADA, GUARDARLA POR SEPARADO
            if key == "CallExpression" and node.type == "CallExpression":
                nested_calls.append(child_value)
                continue
                
            dict_key = key[0].lower() + key[1:]
            
            # MANEJO ESPECIAL PARA VariableDeclaration - los hijos van directo al value
            if node.type == "VariableDeclaration" and dict_key == "value":
                # Si es un Value dentro de VariableDeclaration, extraer sus propiedades
                if isinstance(child_value, dict) and "value" in child_value:
                    props["value"] = child_value
                continue
                
            # MANEJO ESPECIAL PARA CallExpression - NO convertir en array
            if dict_key == "callExpression" and isinstance(child_value, dict):
                # Si ya existe una callExpression, convertir a array
                if dict_key in props:
                    if not isinstance(props[dict_key], list):
                        props[dict_key] = [props[dict_key]]
                    props[dict_key].append(child_value)
                else:
                    props[dict_key] = child_value
            else:
                if dict_key in props:
                    if not isinstance(props[dict_key], list):
                        props[dict_key] = [props[dict_key]]
                    props[dict_key].append(child_value)
                else:
                    props[dict_key] = child_value
    
    # AGREGAR LAS CallExpression ANIDADAS AL PROPS PRINCIPAL
    if nested_calls:
        if "callExpression" in props:
            if not isinstance(props["callExpression"], list):
                props["callExpression"] = [props["callExpression"]]
            props["callExpression"].extend(nested_calls)
        else:
            props["callExpression"] = nested_calls
    
    # PARA VariableDeclaration: SI después de procesar hijos sigue sin value, agregarlo
    if node.type == "VariableDeclaration" and "value" not in props:
        props["value"] = {"value": None}
        
    return props

def extract_instructions_from_block(block_content):
    """
    Extrae todas las instrucciones de un bloque y las retorna como array
    """
    if not block_content:
        return []
    
    instructions = []
    
    # Si block_content ya es una lista, retornarla directamente
    if isinstance(block_content, list):
        return block_content
    
    # Si es un diccionario, buscar instrucciones en sus propiedades
    if isinstance(block_content, dict):
        # Buscar PostIncrementStatement
        if "postIncrementStatement" in block_content:
            post_inc = block_content["postIncrementStatement"]
            if isinstance(post_inc, dict) and "value" in post_inc:
                instructions.append({
                    "PostIncrementStatement": {
                        "value": post_inc.get("value", "")
                    }
                })
        
        # Buscar CallExpression - CORREGIR: usar "CallExpression" con E mayúscula
        if "callExpression" in block_content:
            call_expr = block_content["callExpression"]
            # Si es una lista, procesar cada elemento
            if isinstance(call_expr, list):
                for expr in call_expr:
                    instructions.append({
                        "CallExpression": {
                            "function": expr.get("function", ""),
                            "arguments": {"value": expr.get("arguments", {}).get("value", "")},
                            "paramType": expr.get("paramType", "")
                        }
                    })
            else:
                instructions.append({
                    "CallExpression": {
                        "function": call_expr.get("function", ""),
                        "arguments": {"value": call_expr.get("arguments", {}).get("value", "")},
                        "paramType": call_expr.get("paramType", "")
                    }
                })
        
        # Buscar if_Condition
        if "if_Condition" in block_content:
            if_cond = block_content["if_Condition"]
            repaired_if = repair_if_structure({"if_Condition": if_cond})
            instructions.append(repaired_if)
        
        # Buscar otras estructuras
        for key, value in block_content.items():
            if key in ["ForLoop", "WhileLoop"] and isinstance(value, dict):
                if key == "ForLoop":
                    instructions.append(repair_for_loop_structure({key: value}))
                elif key == "WhileLoop":
                    instructions.append(repair_while_loop_structure({key: value}))
    
    return instructions

def repair_if_structure(if_node):
    """
    Repara la estructura del if_Condition para quitar BlockStart/BlockEnd pero mantener el bloque
    """
    if not isinstance(if_node, dict) or "if_Condition" not in if_node:
        return if_node
    
    if_content = if_node["if_Condition"]
    
    # Si ya tiene el formato correcto, solo limpiar BlockStart/BlockEnd del bloque
    if isinstance(if_content.get("block"), list):
        # Filtrar para quitar BlockStart/BlockEnd pero mantener las instrucciones
        cleaned_block = []
        for item in if_content["block"]:
            if isinstance(item, dict) and "value" in item:
                if item["value"] in ["BlockStart", "BlockEnd"]:
                    continue
            # Mantener todas las instrucciones como CallExpression, etc.
            cleaned_block.append(item)
        
        if cleaned_block:
            if_content["block"] = cleaned_block
    
    return {"if_Condition": if_content}

def repair_else_if_structure(else_if_content):
    """
    Función auxiliar para reparar elseIf anidados recursivamente
    """
    if not isinstance(else_if_content, dict):
        return None
    
    repaired_else_if = {
        "condition": else_if_content.get("value", else_if_content.get("condition", ""))
    }
    
    # Reparar bloque del elseIf
    else_if_block = else_if_content.get("block", {})
    repaired_else_if_block = extract_instructions_from_block(else_if_block)
    if repaired_else_if_block:
        repaired_else_if["block"] = repaired_else_if_block
    
    # Procesar elseIf anidados recursivamente
    if "elseIf" in else_if_content:
        nested_else_if = repair_else_if_structure(else_if_content["elseIf"])
        if nested_else_if:
            repaired_else_if["elseIf"] = nested_else_if
    
    # Procesar else dentro de este elseIf
    if "else" in else_if_content:
        else_content = else_if_content["else"]
        else_block = else_content.get("block", {})
        repaired_else_block = extract_instructions_from_block(else_block)
        if repaired_else_block:
            repaired_else_if["else"] = {"block": repaired_else_block}
    
    return repaired_else_if

def repair_for_loop_structure(for_node):
    """
    Repara el formato del ForLoop para que coincida con json_correcto.json
    """
    if not isinstance(for_node, dict) or "ForLoop" not in for_node:
        return for_node
    
    for_content = for_node["ForLoop"]
    
    # SI hay callExpression en iterator, moverlos al block
    if "iterator" in for_content and "callExpression" in for_content["iterator"]:
        call_exprs = for_content["iterator"]["callExpression"]
        
        # Si no existe block, crearlo
        if "block" not in for_content:
            for_content["block"] = []
        
        # Mover los CallExpression al block
        if isinstance(call_exprs, list):
            for expr in call_exprs:
                for_content["block"].append({
                    "CallExpression": expr
                })
        else:
            for_content["block"].append({
                "CallExpression": call_exprs
            })
        
        # Eliminar callExpression del iterator
        del for_content["iterator"]["callExpression"]
    
    return for_node

def repair_while_loop_structure(while_node):
    """
    Repara el formato del WhileLoop para que coincida EXACTAMENTE con json_correcto.json
    """
    if not isinstance(while_node, dict) or "WhileLoop" not in while_node:
        return while_node
    
    while_content = while_node["WhileLoop"]
    
    # EL PROBLEMA: conditionIs no debería existir, todo debe ir en block
    if "conditionIs" in while_content:
        condition_is_content = while_content["conditionIs"]
        
        # Crear el bloque correctamente
        block_content = []
        
        # Extraer PostIncrementStatement
        if "postIncrementStatement" in condition_is_content:
            post_inc = condition_is_content["postIncrementStatement"]
            block_content.append({
                "PostIncrementStatement": {
                    "value": post_inc.get("value", "")
                }
            })
        
        # Extraer CallExpression
        if "callExpression" in condition_is_content:
            call_expr = condition_is_content["callExpression"]
            if isinstance(call_expr, list):
                for expr in call_expr:
                    block_content.append({
                        "CallExpression": expr
                    })
            else:
                block_content.append({
                    "CallExpression": call_expr
                })
        
        # Extraer if_Condition - CORREGIR: mover callExpression al block del if
        if "if_Condition" in condition_is_content:
            if_cond = condition_is_content["if_Condition"]
            
            # SI hay callExpression directo en el if, moverlo al block
            if "callExpression" in if_cond and isinstance(if_cond["callExpression"], dict):
                call_expr = if_cond["callExpression"]
                # Crear bloque si no existe
                if "block" not in if_cond:
                    if_cond["block"] = []
                # Agregar el CallExpression como objeto individual al bloque
                if_cond["block"].append({
                    "CallExpression": call_expr
                })
                # Eliminar el callExpression directo
                del if_cond["callExpression"]
            
            block_content.append({
                "if_Condition": if_cond
            })
        
        # Reemplazar conditionIs por block
        del while_content["conditionIs"]
        while_content["block"] = block_content
    
    return while_node
def _flatten_if_instructions(node_content):
    """
    Función auxiliar para tomar el contenido de un nodo (if, elseIf, else) 
    del formato incorrecto (ast_output.json) y aplanar sus instrucciones 
    en un 'block' array, tal como se ve en astjson.json.
    
    Extrae recursivamente 'callExpression' y 'variableAsignement' anidados.
    """
    instructions = []
    
    # 1. Buscar 'callExpression' de alto nivel
    if "callExpression" in node_content:
        calls = node_content["callExpression"]
        if not isinstance(calls, list):
            calls = [calls]
        
        for call in calls:
            # Añadir la llamada principal (copiando solo sus props, no sus hijos)
            main_call = {}
            for key, val in call.items():
                if key not in ["callExpression", "variableAsignement"]:
                    main_call[key] = val
            
            # Añadir solo si tiene contenido (p.ej. 'function')
            if "function" in main_call:
                instructions.append({"CallExpression": main_call})
            
            # 2. Buscar 'variableAsignement' anidado DENTRO de la llamada
            if "variableAsignement" in call:
                v_assign = call["variableAsignement"]
                if isinstance(v_assign, list):
                    for v in v_assign:
                         instructions.append({"VariableAsignement": v})
                else:
                    instructions.append({"VariableAsignement": v_assign})
            
            # 3. Buscar 'callExpression' anidada DENTRO de la llamada - CORREGIDO
            if "callExpression" in call:
                nested_calls_list = call["callExpression"]
                if not isinstance(nested_calls_list, list):
                    nested_calls_list = [nested_calls_list]
                
                for nested_call in nested_calls_list:
                    # Extraer recursivamente TODAS las llamadas anidadas
                    def extract_all_calls(call_node, extracted_list):
                        """Extrae recursivamente todas las callExpression"""
                        clean_call = {}
                        for key, val in call_node.items():
                            if key not in ["callExpression", "variableAsignement"]:
                                clean_call[key] = val
                        
                        if "function" in clean_call:
                            extracted_list.append({"CallExpression": clean_call})
                        
                        # Extraer variableAsignement si existe
                        if "variableAsignement" in call_node:
                            v_assign = call_node["variableAsignement"]
                            if isinstance(v_assign, list):
                                for v in v_assign:
                                    extracted_list.append({"VariableAsignement": v})
                            else:
                                extracted_list.append({"VariableAsignement": v_assign})
                        
                        # Extraer llamadas anidadas recursivamente
                        if "callExpression" in call_node:
                            deeper_calls = call_node["callExpression"]
                            if not isinstance(deeper_calls, list):
                                deeper_calls = [deeper_calls]
                            for deeper_call in deeper_calls:
                                extract_all_calls(deeper_call, extracted_list)
                    
                    # Extraer todas las llamadas anidadas recursivamente
                    all_nested_calls = []
                    extract_all_calls(nested_call, all_nested_calls)
                    instructions.extend(all_nested_calls)

    # 4. Buscar 'variableAsignement' de alto nivel (hermano de callExpression)
    if "variableAsignement" in node_content:
        v_assign = node_content["variableAsignement"]
        if isinstance(v_assign, list):
            for v in v_assign:
                 instructions.append({"VariableAsignement": v})
        else:
            instructions.append({"VariableAsignement": v_assign})
    # Lista de claves que YA procesamos o que son estructura (NO instrucciones)
    ignored_keys = ["condition", "elseIf", "else", "block", "value", "type", "callExpression", "variableAsignement"]
    
    # Recorrer cualquier otra clave que haya quedado en el nodo (ej: postIncrementStatement)
    for key, value in node_content.items():
        if key not in ignored_keys:
            # Convertir la clave a PascalCase (postIncrementStatement -> PostIncrementStatement)
            pascal_key = key[0].upper() + key[1:]
            
            # Si es una lista de instrucciones, agregarlas una por una
            if isinstance(value, list):
                for item in value:
                    instructions.append({pascal_key: item})
            # Si es un objeto único, agregarlo directo
            else:
                instructions.append({pascal_key: value})        
    return instructions

def _repair_if_recursive(node_content):
    """
    Función recursiva para reparar la estructura de if/elseIf/else.
    Toma el *contenido* de un nodo (el objeto JSON interno).
    """
    if not isinstance(node_content, dict):
        return node_content

    repaired_node = {}

    # 1. Renombrar 'value' a 'condition' (para elseIf) o mantener 'condition'
    if "condition" in node_content:
        repaired_node["condition"] = node_content["condition"]
    elif "value" in node_content:
        # El 'value' de 'elseIf' se convierte en 'condition'
        repaired_node["condition"] = node_content["value"]

    # 2. Aplanar las instrucciones
    repaired_node["block"] = _flatten_if_instructions(node_content)
    
    # 3. Procesar recursivamente 'elseIf' - CORREGIDO: manejar múltiples elseIf
    if "elseIf" in node_content:
        else_if_content = node_content["elseIf"]
        
        # Si hay múltiples elseIf anidados, procesarlos recursivamente
        if isinstance(else_if_content, dict) and "condition" in else_if_content:
            # Es un solo elseIf, procesarlo normalmente
            repaired_node["elseIf"] = _repair_if_recursive(else_if_content)
        else:
            # Manejar caso donde hay múltiples elseIf (no debería pasar con la nueva estructura)
            repaired_node["elseIf"] = _repair_if_recursive(else_if_content)
        
    # 4. Procesar recursivamente 'else'
    if "else" in node_content:
        # El 'else' no tiene 'condition', así que _repair_if_recursive
        # devolverá {'block': [...]}, lo cual es correcto.
        repaired_node["else"] = _repair_if_recursive(node_content["else"])

    # Si es un bloque 'else' (no tiene 'condition' ni 'value'),
    # debe devolver solo el bloque.
    if "condition" not in repaired_node and "value" not in repaired_node:
        if "block" in repaired_node:
            return {"block": repaired_node["block"]}
        else:
            return {"block": []}

    return repaired_node

def repair_if_structure_new(if_node):
    """
    Esta es la función principal que repara la estructura del if_Condition.
    Reemplaza la lógica de 'repair_if_structure' en el script original.
    
    Toma la entrada: {"if_Condition": ...nodo_incorrecto...}
    Devuelve la salida: {"if_Condition": ...nodo_reparado...}
    
    Esta función preserva la cadena lógica if-elseIf-else.
    """
    if not isinstance(if_node, dict) or "if_Condition" not in if_node:
        return if_node # No es lo que esperamos, devolver tal cual
    
    incorrect_if_content = if_node["if_Condition"]
    
    # Iniciar la reparación recursiva
    repaired_if_content = _repair_if_recursive(incorrect_if_content)
    
    return {"if_Condition": repaired_if_content}
# ----- FIN DEL CÓDIGO DE REPARACIÓN DEL IF -----
def fix_for_loop_iterator(for_obj):
    """
    Repara el error donde los incrementadores quedan en 'iterator'.
    CORRECCIÓN: Verifica si la instrucción ya está en el bloque (extraída correctamente)
    para no duplicarla ni moverla al final. Si ya está, solo la limpia del iterator.
    """
    if "ForLoop" not in for_obj:
        return for_obj
        
    loop_data = for_obj["ForLoop"]
    
    if "block" not in loop_data:
        loop_data["block"] = []
    elif not isinstance(loop_data["block"], list):
        loop_data["block"] = [loop_data["block"]]
        
    if "iterator" in loop_data and isinstance(loop_data["iterator"], dict):
        iter_data = loop_data["iterator"]
        keys_to_move = ["postIncrementStatement", "preIncrementStatement", 
                        "postDecrementStatement", "preDecrementStatement"]
        
        for key in keys_to_move:
            if key in iter_data:
                pascal_key = key[0].upper() + key[1:]
                stmt_obj = { pascal_key: iter_data[key] }
                
                # VERIFICACIÓN DE ORDEN:
                # Comprobamos si esta instrucción ya existe en el bloque 
                # (porque extract_block_from_node la sacó en su posición correcta).
                exists = False
                for item in loop_data["block"]:
                    if pascal_key in item:
                        # Comparamos valores para asegurar que es la misma instrucción
                        val1 = item[pascal_key].get("value")
                        val2 = stmt_obj[pascal_key].get("value")
                        if val1 == val2:
                            exists = True
                            break
                
                # Solo agregamos al final si NO existe ya en el bloque.
                # Si ya existe, significa que está en su lugar correcto (ej: en medio)
                if not exists:
                    loop_data["block"].append(stmt_obj)
                
                # Siempre borramos del iterator porque ahí no debe estar
                del iter_data[key]
                
    return for_obj

def extract_block_from_node(ast_node):
    """
    Busca explícitamente un hijo tipo 'Block' en el nodo AST y extrae su contenido 
    respetando el orden original secuencial.
    """
    for child in ast_node.children:
        if child.type == "Block":
            return transform_block_content(child)
    return []

def force_inject_block(repaired_node, extracted_block):
    """
    CORRECCIÓN: Sobreescribe el bloque del nodo con el bloque extraído del AST.
    Al sobreescribir en lugar de extender, garantizamos que se use el ORDEN REAL
    del archivo de texto y no el orden mezclado del diccionario.
    """
    if not extracted_block:
        return repaired_node
        
    # Detectar tipo de nodo (If, For, While)
    target_key = None
    if isinstance(repaired_node, dict):
        if "if_Condition" in repaired_node: target_key = "if_Condition"
        elif "ForLoop" in repaired_node: target_key = "ForLoop"
        elif "WhileLoop" in repaired_node: target_key = "WhileLoop"
    
    if target_key:
        node_content = repaired_node[target_key]
        # SOBREESCRIBIR: Usamos la lista ordenada del AST como la verdad absoluta
        node_content["block"] = extracted_block
            
    return repaired_node
def build_ordered_if(node):
    """
    Construye el objeto if_Condition iterando secuencialmente sus hijos.
    Esto garantiza que PostIncrementStatement se mantenga en su posición original
    (ej: entre dos CallExpression) y no sea movido al final por el diccionario.
    """
    # 1. Obtener la condición
    condition = convert_value(node.value)
    
    # 2. Construir el bloque respetando el orden absoluto de los hijos
    block_content = []
    
    # Tipos que NO son instrucciones del bloque (metadatos o estructura)
    ignored_types = ["Block", "Condition", "Value"] 
    
    for child in node.children:
        if child.type in ignored_types:
            continue
            
        # Procesar recursivamente si hay ifs anidados
        if child.type == "if_Condition":
            child_obj = build_ordered_if(child)
            block_content.append(child_obj)
        
        # Procesar recursivamente loops
        elif child.type == "ForLoop":
            # Para loops dentro de un if, usamos la lógica estándar + reparaciones
            loop_data = transform_to_dict(child)
            ctrl_obj = {"ForLoop": loop_data if loop_data else {}}
            repaired = repair_for_loop_structure(ctrl_obj)
            final = fix_for_loop_iterator(repaired)
            block_content.append(final)
            
        elif child.type == "WhileLoop":
            loop_data = transform_to_dict(child)
            ctrl_obj = {"WhileLoop": loop_data if loop_data else {}}
            repaired = repair_while_loop_structure(ctrl_obj)
            block_content.append(repaired)
            
        # Procesar instrucciones normales (Call, Increment, Assign)
        else:
            data = transform_to_dict(child)
            if data is not None:
                # Usar el tipo de nodo como clave (ej: PostIncrementStatement)
                key = child.type
                # Caso especial: CallExpression requiere mayúscula si transform devuelve minúscula
                if key == "CallExpression" and "callExpression" in data: 
                     # transform_to_dict a veces devuelve {callExpression: ...} o directo props
                     # Aquí simplificamos: usaremos el dict tal cual bajo la clave correcta
                     pass
                
                block_content.append({key: data})

    return {
        "if_Condition": {
            "condition": condition,
            "block": block_content
        }
    }
def build_ordered_for_loop(node):
    """
    Construye el ForLoop asegurando que 'iterator' aparezca ANTES que 'block' en el JSON.
    """
    # CORRECCIÓN: Definimos el orden exacto de las llaves aquí.
    # Al crear 'iterator' antes que 'block', Python respetará este orden en el JSON final.
    for_obj = {
        "variable": convert_value(node.value),
        "iterator": {},  # <--- AHORA ESTÁ PRIMERO
        "block": []      # <--- AHORA ESTÁ DESPUÉS
    }
    
    # Función interna (Misma lógica que ya funcionaba para sacar polizones)
    def process_node_to_obj(n):
        if n.type == "ForLoop":
            nested = build_ordered_for_loop(n)
            nested = repair_for_loop_structure(nested)
            nested = fix_for_loop_iterator(nested)
            return nested
        elif n.type == "WhileLoop":
            t = transform_to_dict(n)
            w = {"WhileLoop": t if t else {}}
            return repair_while_loop_structure(w)
        elif n.type == "if_Condition":
            t = transform_to_dict(n)
            struct = {"if_Condition": t if t else {}}
            return repair_if_structure_new(struct)
            
        t = transform_to_dict(n)
        if t is not None:
            key = n.type
            return {key: t}
        return None

    # Iteramos sobre los hijos
    for child in node.children:
        if child.type == "Iterator":
            # Lógica de Iterator (Mantenida igual, solo asignamos a la clave ya existente)
            if child.value: 
                for_obj["iterator"]["value"] = convert_value(child.value)
            
            valid_iter_keys = ["declared", "Condition", "ParamType", "Type"]
            
            for sub in child.children:
                if sub.type in valid_iter_keys:
                    k = "condition" if sub.type == "Condition" else sub.type
                    for_obj["iterator"][k] = transform_to_dict(sub)
                else:
                    # Instrucción mal ubicada -> Mover al Block
                    item = process_node_to_obj(sub)
                    if item: for_obj["block"].append(item)
        else:
            # Hijo directo -> Agregar al Block
            item = process_node_to_obj(child)
            if item: for_obj["block"].append(item)
            
    return {"ForLoop": for_obj}
def build_ordered_while_loop(node):
    """
    Construye el WhileLoop iterando secuencialmente sus hijos del AST,
    garantizando que las instrucciones aparezcan en el orden EXACTO
    en que fueron escritas en el archivo de texto original.
    """
    # Obtener la condición del while
    condition = convert_value(node.value)
    
    # Construir el bloque respetando el orden absoluto de los hijos
    block_content = []
    
    # Tipos que NO son instrucciones del bloque (metadatos o estructura)
    ignored_types = ["Block", "Condition", "ConditionIs"]
    
    def process_child_to_instruction(child):
        """Procesa un nodo hijo y lo convierte en instrucción"""
        if child.type in ignored_types:
            return None
            
        # Si es un nodo estructural (loops, ifs anidados)
        if child.type == "ForLoop":
            ordered_for = build_ordered_for_loop(child)
            repaired = repair_for_loop_structure(ordered_for)
            final = fix_for_loop_iterator(repaired)
            return final
            
        elif child.type == "WhileLoop":
            # Recursión para whiles anidados
            nested_while = build_ordered_while_loop(child)
            return nested_while
            
        elif child.type == "if_Condition":
            transformed = transform_to_dict(child)
            struct = {"if_Condition": transformed if transformed else {}}
            repaired = repair_if_structure_new(struct)
            return repaired
        
        # Para instrucciones normales (CallExpression, VariableDeclaration, etc.)
        else:
            data = transform_to_dict(child)
            if data is not None:
                return {child.type: data}
        
        return None
    
    # Iterar sobre TODOS los hijos del nodo While en orden secuencial
    for child in node.children:
        # Si encontramos un Block, procesamos sus hijos en orden
        if child.type == "Block":
            for block_child in child.children:
                instruction = process_child_to_instruction(block_child)
                if instruction:
                    block_content.append(instruction)
        
        # Si encontramos un ConditionIs, procesamos sus hijos en orden
        elif child.type == "ConditionIs":
            for cond_child in child.children:
                instruction = process_child_to_instruction(cond_child)
                if instruction:
                    block_content.append(instruction)
        
        # Cualquier otro hijo directo también se procesa
        else:
            instruction = process_child_to_instruction(child)
            if instruction:
                block_content.append(instruction)
    
    return {
        "WhileLoop": {
            "condition": condition,
            "block": block_content
        }
    }
def extract_function_block_instructions(node):
    """
    Extrae todas las instrucciones del bloque de una función desde el nodo AST.
    Procesa CallExpression, ParameterAsignement, Return y otras instrucciones.
    Retorna una lista ordenada de instrucciones.
    """
    instructions = []
    
    # Tipos que NO son instrucciones del bloque
    ignored_types = ["Parameters", "Value", "ExplicitType", "Type", "Block"]
    
    def process_instruction_node(child):
        """Convierte un nodo hijo en una instrucción"""
        if child.type in ignored_types:
            return None
        
        # Procesar ParameterAsignement
        if child.type == "ParameterAsignement":
            param_assign = {
                "name": convert_value(child.value)
            }
            for subchild in child.children:
                if subchild.type == "Value":
                    value_obj = {"value": convert_value(subchild.value)}
                    for vchild in subchild.children:
                        if vchild.type == "Type":
                            value_obj["type"] = convert_value(vchild.value)
                    param_assign["value"] = value_obj
            return {"ParameterAsignement": param_assign}
        
        # Procesar CallExpression (incluye Return)
        elif child.type == "CallExpression":
            call_obj = {
                "function": convert_value(child.value)
            }
            for subchild in child.children:
                if subchild.type == "Arguments":
                    call_obj["arguments"] = {"value": convert_value(subchild.value)}
                elif subchild.type == "value":
                    value_obj = {"value": convert_value(subchild.value)}
                    for vchild in subchild.children:
                        if vchild.type == "Type":
                            value_obj["type"] = convert_value(vchild.value)
                    call_obj["value"] = value_obj
                elif subchild.type == "ParamType" or subchild.type == "Type":
                    call_obj["paramType"] = convert_value(subchild.value)
            return {"CallExpression": call_obj}
        
        # Procesar estructuras de control anidadas
        elif child.type == "if_Condition":
            nested_if = build_ordered_if(child)
            return nested_if
        
        elif child.type == "ForLoop":
            nested_for = build_ordered_for_loop(child)
            repaired = repair_for_loop_structure(nested_for)
            final = fix_for_loop_iterator(repaired)
            return final
        
        elif child.type == "WhileLoop":
            nested_while = build_ordered_while_loop(child)
            return nested_while
        
        # Otras instrucciones genéricas
        else:
            data = transform_to_dict(child)
            if data is not None:
                return {child.type: data}
        
        return None
    
    # Iterar sobre los hijos del nodo Function
    for child in node.children:
        # Si hay un bloque explícito, procesar sus hijos
        if child.type == "Block":
            for block_child in child.children:
                instruction = process_instruction_node(block_child)
                if instruction:
                    instructions.append(instruction)
        
        # Si hay Parameters, procesar sus hijos (que son instrucciones mal ubicadas)
        elif child.type == "Parameters":
            for param_child in child.children:
                # Solo procesar nodos que NO sean metadata de parámetros
                if param_child.type not in ["Value", "ExplicitType", "Type"]:
                    instruction = process_instruction_node(param_child)
                    if instruction:
                        instructions.append(instruction)
        
        # Cualquier otro hijo directo también podría ser una instrucción
        elif child.type not in ignored_types:
            instruction = process_instruction_node(child)
            if instruction:
                instructions.append(instruction)
    
    return instructions

def build_ordered_function(node):
    """
    Construye el objeto Function iterando secuencialmente sus hijos del AST.
    Separa correctamente los parámetros de las instrucciones del bloque.
    """
    # Estructura base de la función
    func_obj = {
        "name": convert_value(node.value),
        "parameters": {}
    }
    
    # Extraer información de Parameters
    for child in node.children:
        if child.type == "Parameters":
            # Obtener el valor de los parámetros (la lista de params)
            if child.value:
                func_obj["parameters"]["value"] = convert_value(child.value)
            
            # Buscar ExplicitType si existe (puede estar en Parameters o como hijo directo)
            for param_child in child.children:
                if param_child.type == "ExplicitType":
                    func_obj["explicitType"] = convert_value(param_child.value)
        
        # ExplicitType también puede estar como hijo directo de Function
        elif child.type == "ExplicitType":
            func_obj["explicitType"] = convert_value(child.value)
    
    # Extraer el bloque de instrucciones
    block_instructions = extract_function_block_instructions(node)
    
    # Solo agregar el bloque si hay instrucciones
    if block_instructions:
        func_obj["block"] = block_instructions
    
    return {"Function": func_obj}

def repair_function_structure(func_node):
    """
    Repara la estructura de una Function que ya fue transformada por transform_to_dict.
    Esta función convierte el formato incorrecto al formato correcto.
    """
    if not isinstance(func_node, dict) or "Function" not in func_node:
        return func_node
    
    func_content = func_node["Function"]
    
    # Crear la estructura reparada
    repaired_func = {
        "name": func_content.get("name", ""),
        "parameters": {}
    }
    
    # Procesar parameters
    if "parameters" in func_content:
        params = func_content["parameters"]
        
        # Extraer el valor de los parámetros
        if isinstance(params, dict):
            if "value" in params:
                repaired_func["parameters"]["value"] = params["value"]
            
            # Mover explicitType si está dentro de parameters
            if "explicitType" in params:
                repaired_func["explicitType"] = params["explicitType"]
    
    # ExplicitType también puede estar al nivel de Function
    if "explicitType" in func_content:
        repaired_func["explicitType"] = func_content["explicitType"]
    
    # Extraer instrucciones del bloque
    block_instructions = []
    
    if "parameters" in func_content and isinstance(func_content["parameters"], dict):
        params = func_content["parameters"]
        
        # Buscar ParameterAsignement
        if "parameterAsignement" in params:
            param_assign_data = params["parameterAsignement"]
            if isinstance(param_assign_data, dict) and "value" in param_assign_data:
                # Formato: ["a", {"value": 2, "type": "int"}]
                if isinstance(param_assign_data["value"], list) and len(param_assign_data["value"]) == 2:
                    name = param_assign_data["value"][0]
                    value = param_assign_data["value"][1]
                    block_instructions.append({
                        "ParameterAsignement": {
                            "name": name,
                            "value": value
                        }
                    })
        
        # Buscar CallExpression (puede ser uno o varios)
        if "callExpression" in params:
            call_expr = params["callExpression"]
            
            if isinstance(call_expr, list):
                for expr in call_expr:
                    block_instructions.append({"CallExpression": expr})
            elif isinstance(call_expr, dict):
                block_instructions.append({"CallExpression": call_expr})
    
    # Agregar el bloque solo si hay instrucciones
    if block_instructions:
        repaired_func["block"] = block_instructions
    
    return {"Function": repaired_func}
def build_ordered_perform_while_loop(node):
    """
    Construye el PerformWhileLoop iterando secuencialmente sus hijos del AST,
    garantizando que las instrucciones aparezcan en el orden EXACTO
    en que fueron escritas en el archivo de texto original.
    """
    # Obtener la condición del perform while
    condition = convert_value(node.value)
    
    # Construir el bloque respetando el orden absoluto de los hijos
    block_content = []
    
    # Tipos que NO son instrucciones del bloque (metadatos o estructura)
    ignored_types = ["Block", "Condition", "ConditionIs"]
    
    def process_child_to_instruction(child):
        """Procesa un nodo hijo y lo convierte en instrucción"""
        if child.type in ignored_types:
            return None
            
        # Si es un nodo estructural (loops, ifs anidados)
        if child.type == "ForLoop":
            ordered_for = build_ordered_for_loop(child)
            repaired = repair_for_loop_structure(ordered_for)
            final = fix_for_loop_iterator(repaired)
            return final
            
        elif child.type == "WhileLoop":
            # Recursión para whiles anidados
            nested_while = build_ordered_while_loop(child)
            return nested_while
            
        elif child.type == "if_Condition":
            transformed = transform_to_dict(child)
            struct = {"if_Condition": transformed if transformed else {}}
            repaired = repair_if_structure_new(struct)
            return repaired
        
        # Para instrucciones normales (CallExpression, VariableDeclaration, etc.)
        else:
            data = transform_to_dict(child)
            if data is not None:
                return {child.type: data}
        
        return None
    
    # Iterar sobre TODOS los hijos del nodo PerformWhile en orden secuencial
    for child in node.children:
        # Si encontramos un Block, procesamos sus hijos en orden
        if child.type == "Block":
            for block_child in child.children:
                instruction = process_child_to_instruction(block_child)
                if instruction:
                    block_content.append(instruction)
        
        # Si encontramos un ConditionIs, procesamos sus hijos en orden
        elif child.type == "ConditionIs":
            for cond_child in child.children:
                instruction = process_child_to_instruction(cond_child)
                if instruction:
                    block_content.append(instruction)
        
        # Cualquier otro hijo directo también se procesa
        else:
            instruction = process_child_to_instruction(child)
            if instruction:
                block_content.append(instruction)
    
    return {
        "PerformWhileLoop": {
            "condition": condition,
            "block": block_content
        }
    }


def repair_perform_while_structure(perform_while_node):
    """
    Repara la estructura del PerformWhileLoop moviendo las CallExpression al block
    y manteniendo conditionIs al mismo nivel.
    """
    if not isinstance(perform_while_node, dict) or "PerformWhileLoop" not in perform_while_node:
        return perform_while_node
    
    perform_while_content = perform_while_node["PerformWhileLoop"]
    
    # Si hay callExpression en conditionIs, moverlos al block principal
    if ("conditionIs" in perform_while_content and 
        "callExpression" in perform_while_content["conditionIs"]):
        
        call_expr = perform_while_content["conditionIs"]["callExpression"]
        
        # Crear block si no existe
        if "block" not in perform_while_content:
            perform_while_content["block"] = []
        
        # Mover CallExpression al block como objetos individuales
        if isinstance(call_expr, list):
            for expr in call_expr:
                perform_while_content["block"].append({
                    "CallExpression": expr
                })
        else:
            perform_while_content["block"].append({
                "CallExpression": call_expr
            })
        
        # Eliminar callExpression de conditionIs
        del perform_while_content["conditionIs"]["callExpression"]
    
    return perform_while_node
def main():
    if len(sys.argv) != 3:
        print("Uso: python astAjson.py <ruta_del_txt_entrada> <ruta_del_json_salida>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # --- CÓDIGO DE LECTURA Y PARSEO (Mantenlo igual) ---
    # (Asumo que usas tu parse_ast o el bloque de lectura corregido)
    root = parse_ast(input_path)
    if not root: sys.exit(1)
    
    program_body = []
    
    i = 0
    while i < len(root.children):
        child = root.children[i]
        
        if child.type == "SwitchStatement":
            switch_obj = {'value': convert_value(child.value)}
    
            # Extraer casos directamente del SwitchStatement, sin buscar Block
            block_content = transform_block_for_switch(child)
            # Combinar el switch value con los casos
            switch_obj.update(block_content)
    
            program_body.append({"SwitchStatement": switch_obj})
        
        elif child.type == "ForLoop":
            # 1. CONSTRUCCIÓN ORDENADA (Rescata instrucciones del Iterator y ordena el bloque)
            ordered_for = build_ordered_for_loop(child)
            
            # 2. REPARACIÓN DE FORMATO (Tu requisito indispensable)
            # Como 'ordered_for' ya tiene la lista 'block' ordenada, repair solo ajustará claves.
            repaired_for = repair_for_loop_structure(ordered_for)
            
            # 3. LIMPIEZA FINAL (Por si quedó algo en iterator que repair no vió)
            final_for = fix_for_loop_iterator(repaired_for)
            
            program_body.append(final_for)
                
        elif child.type == "WhileLoop":
            transformed = transform_to_dict(child)
            control_obj = {"WhileLoop": transformed if transformed else {}}
            repaired_while = build_ordered_while_loop(child)
            program_body.append(repaired_while)

        elif child.type == "if_Condition":
            # LÓGICA ORIGINAL PARA EL IF (Como pediste, sin tocar)
            transformed = transform_to_dict(child)
            if_struct = {"if_Condition": transformed if transformed else {}}
            
            # Intentar extraer bloque si transform falló (lógica defensiva estándar)
            block_content = extract_block_from_node(child)
            if block_content:
                if_struct["if_Condition"]["block"] = block_content
            
            repaired_if = repair_if_structure_new(if_struct)
            program_body.append(repaired_if)
            
        elif child.type == "Block":
            block_content = transform_block_content(child)
            if block_content:
                program_body.append({"block": block_content})
        elif child.type == "Function":
            # USAR LA NUEVA LÓGICA PARA FUNCTIONS
            ordered_function = build_ordered_function(child)
            program_body.append(ordered_function)        
        elif child.type == "PerformWhileLoop":
            # NUEVA LÓGICA PARA PerformWhileLoop
            transformed = transform_to_dict(child)
            perform_while_obj = {"PerformWhileLoop": transformed if transformed else {}}
            repaired_perform_while = repair_perform_while_structure(perform_while_obj)
            program_body.append(repaired_perform_while)
        else:
            transformed = transform_to_dict(child)
            if transformed is not None:
                program_body.append({child.type: transformed})
        
        i += 1
    
    result = {"Program": program_body}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Conversión completada. Archivo guardado en: {output_path}")

if __name__ == '__main__':
    main()
