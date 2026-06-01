import ujson as json
import sys
import os
import re

def fix_scientific_notation(json_str):
    return re.sub(
        r'(?<!["\w])-?\d+\.?\d*[eE][+-]?\d+',
        lambda m: f'{float(m.group(0)):.15f}'.rstrip('0').rstrip('.'),
        json_str
    )
def parse(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [l.replace('\r', '').rstrip() for l in f.readlines()]
    
    idx = [0]

    def val(s):
        if not s: return s
        s = s.strip()
        if s == 'null' or s == 'NULL': return 'null'
        if s == 'True': return True
        if s == 'False': return False
        if s.startswith('"') and s.endswith('"'): return s
        try:
            if '.' in s:
                f = float(s)
        
                return float(f'{f:.15f}'.rstrip('0').rstrip('.') or '0')
            else:
                return int(s)
        except:
            return s
    
    def info(line):
        line = line.strip()
        brace = line.endswith('{')
        bracket = line.endswith('[')
        clean = line[:-1].strip() if (brace or bracket) else line
        if ':' in clean:
            p = clean.split(':', 1)
            return p[0].strip(), p[1].strip(), brace, bracket
        return clean, None, brace, bracket
    
    def read_block(start_char):
        close = '}' if start_char == '{' else ']'
        count = 1
        content = []
        while idx[0] < len(lines) and count > 0:
            idx[0] += 1
            if idx[0] >= len(lines): break
            line = lines[idx[0]]
            count += line.count(start_char) - line.count(close)
            if count > 0:
                content.append(line)
        return content
    
    def obj(content):
        result = {}
        i = 0
        
        while i < len(content):
            line = content[i].strip()
            if not line or line in ['}', ']']:
                i += 1
                continue
            
            k, v, brace, bracket = info(line)
            
            if bracket:
                i += 1
                arr_lines = []
                bc = 1
                while i < len(content) and bc > 0:
                    bc += content[i].count('[') - content[i].count(']')
                    if bc > 0: arr_lines.append(content[i])
                    i += 1
                result['block'] = arr(arr_lines)
            
            elif brace:
                i += 1
                nested = []
                bc = 1
                while i < len(content) and bc > 0:
                    bc += content[i].count('{') - content[i].count('}')
                    if bc > 0: nested.append(content[i])
                    i += 1
                
                sub = obj(nested)
                
                # REGLAS
                if k == 'Value':
                    result['value'] = {'value': val(v)}
                    result['value'].update(sub)
                
                elif k == 'Type':
                    result['type'] = v
                    # NO agregar nada de sub (ignora ExplicitType, Limit)
                
                elif k == 'Arguments':
                    result['arguments'] = {'value': val(v)}
                    if 'Type' in sub:
                        result['arguments']['type'] = sub['Type']
                    for sk in sub:
                        if sk not in ['Type']:
                            result['arguments'][sk] = sub[sk]
                
                elif k == 'Parameters' or k == 'Paramenters':
                    result['paramenters' if k == 'Paramenters' else 'parameters'] = {'value': v}
                
                elif k == 'Iterator':
                    result['iterator'] = {'value': v}
                    if 'declared' in sub:
                        result['iterator']['declared'] = {'value': str(sub['declared']).lower()}
                        if 'Condition' in sub:
                            result['iterator']['declared']['condition'] = {'value': str(sub['Condition']).lower()}
                
                elif k == 'ElseIf':
                    # Si ElseIf tiene Else anidado, condition = false
                    if 'Else' in sub or 'else' in sub:
                        result['elseIf'] = {'condition': val(v)}
                    else:
                        result['elseIf'] = {'condition': val(v) if v == 'False' else val(v)}
                    result['elseIf'].update(sub)
                
                elif k == 'Else' or k == '} Else':
                    result['else'] = sub
                   
                
                elif k == 'variableName':
                    # variableName se ignora completamente
                    pass
                
                elif k == 'declared':
                    result['declared'] = {'value': str(v).lower()}
                    if 'Condition' in sub:
                        result['declared']['condition'] = {'value': str(sub['Condition']).lower()}
                
                elif k in ['Operation', 'ConditionIs', 'Dinamic', 'Longitud', 'longitud']:
                    result[k.lower()] = {'value': val(v)}
                
                elif k == 'ParamType':
                    result['paramType'] = v
                
                elif k in ['ExplicitType', 'Limit', 'Condition', 'val']:
                    # Estos se ignoran o ya se manejaron
                    pass
                
                else:
                    result[k] = sub if sub else v
            
            else:
                if k in ['Type', 'ExplicitType', 'ParamType']:
                    result[k.lower() if k == 'Type' else ('explicitType' if k == 'ExplicitType' else 'paramType')] = v
                elif k in ['Dinamic', 'Longitud', 'longitud', 'Operation', 'ConditionIs']:
                    result[k.lower()] = {'value': val(v)}
                elif k in ['Arguments']:
                    result['Arguments'] = v  # Se convertirá en make()
                elif k in ['Parameters', 'Paramenters']:
                    result[k] = v  # Se convertirá en make()
                elif k in ['Limit']:
                    pass
                else:
                    result[k] = val(v)
                i += 1
        
        return result
    
    def arr(content):
        result = []
        i = 0
        while i < len(content):
            line = content[i].strip()
            if not line or line in ['}', ']']:
                i += 1
                continue
            nt, nv, brace, bracket = info(line)
            if brace:
                i += 1
                nested = []
                bc = 1
                while i < len(content) and bc > 0:
                    bc += content[i].count('{') - content[i].count('}')
                    if bc > 0: nested.append(content[i])
                    i += 1
                node = make(nt, nv, nested)
                if node: result.append(node)
            else:
                node = make(nt, nv, [])
                if node: result.append(node)
                i += 1
        return result
    
    def make(nt, nv, content):
        if nt == 'VariableDeclaration':
            n = {'VariableDeclaration': {'name': nv}}
            if content:
                parsed = obj(content)
                # Mover: explicitType, dinamic, operation, longitud DENTRO de value
                if 'value' in parsed:
                    for key in ['explicitType', 'dinamic', 'operation', 'longitud']:
                        if key in parsed:
                            parsed['value'][key] = parsed.pop(key)
                
                # Asegurar orden: value, longitud
                ordered = {}
                if 'value' in parsed:
                    ordered['value'] = parsed.pop('value')
                if 'longitud' in parsed:
                    ordered['longitud'] = parsed.pop('longitud')
                ordered.update(parsed)
                
                n['VariableDeclaration'].update(ordered)
            return n
        elif nt == 'ConstantDeclaration':
            n = {'ConstantDeclaration': {'name': nv}}
            if content:
                parsed = obj(content)
                if 'value' in parsed:
                    for key in ['explicitType', 'dinamic', 'operation', 'longitud']:
                        if key in parsed:
                            parsed['value'][key] = parsed.pop(key)
        
            ordered = {}
            if 'value' in parsed:
                ordered['value'] = parsed.pop('value')
            if 'longitud' in parsed:
                ordered['longitud'] = parsed.pop('longitud')
            ordered.update(parsed)
        
            n['ConstantDeclaration'].update(ordered)
            return n
        elif nt == 'VariableAsignement':
            n = {'VariableAsignement': {'name': nv}}
            if content:
                parsed = obj(content)
                if 'value' in parsed and 'operation' in parsed:
                    parsed['value']['operation'] = parsed.pop('operation')
                n['VariableAsignement'].update(parsed)
            return n
        
        elif nt == 'CallExpression':
            n = {'CallExpression': {'function': nv}}
            print(f"Procesando CallExpression: {nv} con contenido: {content}")
            if content:
                parsed = obj(content)
                
                # Si tiene "value" simple, convertir a {"value": ...}
                if 'value' in parsed and not isinstance(parsed['value'], dict):
                    parsed['value'] = {'value': parsed['value']}
                # Si tiene "Arguments" simple, convertir a "arguments": {"value": ...}
                if 'Arguments' in parsed:
                    parsed['arguments'] = {'value': val(parsed.pop('Arguments'))}
                # Si tiene "Parameters" simple, convertir
                if 'Parameters' in parsed:
                    parsed['parameters'] = {'value': val(parsed.pop('Parameters'))}
                
                # Mover type dentro de arguments SI:
                # - hay arguments
                # - NO hay paramType (si hay paramType, type se ignora)
                if 'type' in parsed and 'arguments' in parsed and 'paramType' not in parsed:
                    parsed['arguments']['type'] = parsed.pop('type')
                elif 'type' in parsed and 'paramType' in parsed:
                    # Si hay paramType, ignorar type
                    parsed.pop('type')
                
                # Asegurar orden: arguments/value, paramType
                ordered = {}
                if 'arguments' in parsed:
                    ordered['arguments'] = parsed.pop('arguments')
                if 'value' in parsed:
                    ordered['value'] = parsed.pop('value')
                if 'paramType' in parsed:
                    ordered['paramType'] = parsed.pop('paramType')
                # Resto
                ordered.update(parsed)
                
                n['CallExpression'].update(ordered)
            return n
        
        elif nt == 'FunctionCall':
            n = {'FunctionCall': {'function': nv}}
            if content:
                parsed = obj(content)
                # Paramenters (typo) -> paramenters: {"value": ...}
                if 'Paramenters' in parsed:
                    parsed['paramenters'] = {'value': val(parsed.pop('Paramenters'))}
                n['FunctionCall'].update(parsed)
            return n
        
        elif nt == 'Function':
            n = {'Function': {'name': nv}}
            if content:
                parsed = obj(content)
                # Parameters debe tener formato {"value": "..."}
                if 'Parameters' in parsed:
                    parsed['parameters'] = {'value': val(parsed.pop('Parameters'))}
                elif 'parameters' in parsed and not isinstance(parsed['parameters'], dict):
                    parsed['parameters'] = {'value': val(parsed['parameters'])}
                
                # Asegurar orden: parameters, explicitType, block
                ordered = {}
                if 'parameters' in parsed:
                    ordered['parameters'] = parsed.pop('parameters')
                if 'explicitType' in parsed:
                    ordered['explicitType'] = parsed.pop('explicitType')
                if 'Target' in parsed:
                    ordered['target'] = parsed.pop('Target')
                if 'block' in parsed:
                    ordered['block'] = parsed.pop('block')
                # Agregar cualquier otra propiedad
                ordered.update(parsed)
                
                n['Function'].update(ordered)
            return n
        
        elif nt == 'if_Condition':
            n = {'if_Condition': {'condition': nv}}
            if content:
                parsed = obj(content)
                # Orden: condition, block, elseIf
                ordered = {}
                if 'block' in parsed:
                    ordered['block'] = parsed.pop('block')
                if 'elseIf' in parsed:
                    ordered['elseIf'] = parsed.pop('elseIf')
                ordered.update(parsed)
                n['if_Condition'].update(ordered)
            return n
        
        elif nt == 'WhileLoop':
            n = {'WhileLoop': {'condition': nv}}
            if content:
                parsed = obj(content)
                # Orden: condition, block
                # NO incluir conditionIs
                ordered = {}
                if 'block' in parsed:
                    ordered['block'] = parsed.pop('block')
                # Ignorar conditionis/conditionIs
                if 'conditionis' in parsed:
                    parsed.pop('conditionis')
                if 'conditionIs' in parsed:
                    parsed.pop('conditionIs')
                ordered.update(parsed)
                n['WhileLoop'].update(ordered)
            return n
        
        elif nt == 'PerformWhileLoop':
            n = {'PerformWhileLoop': {}}
            if content:
                if nv:
                 n['PerformWhileLoop']['value'] = nv
                parsed = obj(content)
                # Orden: conditionIs, block
                # Arreglar conditionis -> conditionIs
                if 'conditionis' in parsed:
                    parsed['conditionIs'] = parsed.pop('conditionis')
                
                ordered = {}
                if 'conditionIs' in parsed:
                    ordered['conditionIs'] = parsed.pop('conditionIs')
                if 'block' in parsed:
                    ordered['block'] = parsed.pop('block')
                ordered.update(parsed)
                n['PerformWhileLoop'].update(ordered)
            return n
        
        elif nt == 'ForLoop':
            n = {'ForLoop': {'variable': nv}}
            if content:
                parsed = obj(content)
                # Orden: variable, iterator, block
                ordered = {}
                if 'iterator' in parsed:
                    ordered['iterator'] = parsed.pop('iterator')
                if 'block' in parsed:
                    ordered['block'] = parsed.pop('block')
                ordered.update(parsed)
                n['ForLoop'].update(ordered)
            return n
        
        elif nt == 'SwitchStatement':
            n = {'SwitchStatement': {'value': nv}}
            if content:
                cases, defcase = switch(content)
                if cases:
                    n['SwitchStatement']['cases'] = cases
                if defcase:
                    n['SwitchStatement']['defaultCase'] = defcase
            return n
        
        elif nt in ['PostIncrementStatement', 'PreIncrementStatement',
                    'PostDecrementStatement', 'PreDecrementStatement']:
            return {nt: {'value': nv}}
        elif nt == 'LibraryCall':
            n = {'LibraryCall': {'module': nv}}
            if content:
                parsed = obj(content)

                # Alias de módulo: library math as m
                if 'Alias' in parsed:
                    n['LibraryCall']['alias'] = str(parsed['Alias'])

                # Funciones específicas: from math use pi, sqrt
                if 'Functions' in parsed:
                    raw = str(parsed['Functions'])
                    n['LibraryCall']['functions'] = [f.strip() for f in raw.split(',')]

                # Aliases posicionales: is p, raiz  (al final de la lista)
                if 'FunctionAliases' in parsed:
                    raw = str(parsed['FunctionAliases'])
                    n['LibraryCall']['functionAliases'] = [a.strip() for a in raw.split(',')]

                # Sintaxis "on": library math on pi, sqrt is p, raiz
                if 'On' in parsed:
                    raw = str(parsed['On'])
                    n['LibraryCall']['on'] = [f.strip() for f in raw.split(',')]

                if 'OnAliases' in parsed:
                    raw = str(parsed['OnAliases'])
                    n['LibraryCall']['onAliases'] = [a.strip() for a in raw.split(',')]

            return n
        else:
            return {nt: nv}
        
    
    def switch(content):
        cases = []
        defcase = None
        i = 0
        while i < len(content):
            line = content[i].strip()
            if not line or line in ['}', ']'] or line.startswith('Block:'):
                i += 1
                continue
            nt, nv, brace, _ = info(line)

            if nt == 'Case':
                case = {'case': val(nv), 'block': []}
                if brace:
                    i += 1
                    case_lines = []
                    bc = 1
                    while i < len(content):
                        inner = content[i].strip()
                        bc += inner.count('{') - inner.count('}')
                        if bc == 0:
                            i += 1
                            break
                        if inner.startswith('Case:') or inner.startswith('DefaultCase:'):
                            break
                        case_lines.append(content[i])
                        i += 1
                    case['block'] = arr(case_lines)
                cases.append(case)

            elif nt == 'DefaultCase':
                defcase = {'default': True, 'block': []}
                if brace:
                    i += 1
                    def_lines = []
                    bc = 1
                    while i < len(content):
                        inner = content[i].strip()
                        bc += inner.count('{') - inner.count('}')
                        if bc == 0:
                            i += 1
                            break
                        def_lines.append(content[i])
                        i += 1
                    defcase['block'] = arr(def_lines)
            else:
                i += 1

        return cases, defcase
    if lines[0].strip() != 'Program':
        return {}
    
    program = []
    idx[0] = 1
    
    while idx[0] < len(lines):
        line = lines[idx[0]].strip()
        if not line or line in ['}', ']']:
            idx[0] += 1
            continue
        
        if line.startswith('Longitud:'):
            if program:
                nt, nv, _, _ = info(line)
                last_node = program[-1]
                node_type = list(last_node.keys())[0]
                last_node[node_type]['longitud'] = {'value': val(nv)}
            idx[0] += 1
            continue
        
        nt, nv, brace, bracket = info(line)
        if brace or bracket:
            content = read_block('{' if brace else '[')
            node = make(nt, nv, content)
            if node: program.append(node)
        else:
            node = make(nt, nv, [])
            if node: program.append(node)
            idx[0] += 1
    
    return {'Program': program}
def main():
 # Verificar argumentos
 if len(sys.argv) != 3:
    print("Uso: python AstJson.py <archivo_ast_output.txt> <output_file.json>")
    sys.exit(1)
    

 # Obtener archivo de entrada
 input_file = sys.argv[1]
 output_file = sys.argv[2]
 # Verificar que existe
 if not os.path.exists(input_file):
    print(f"Error: El archivo '{input_file}' no existe")
    sys.exit(1)

 # Generar nombre de salida
 # Intentar en el mismo directorio, si falla usar directorio actual


 # Parsear
 result = parse(input_file)

 # Guardar (intentar en el directorio del input, sino en el actual)
 try:
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(fix_scientific_notation(json.dumps(result, indent=2, ensure_ascii=False)))
 except (OSError, PermissionError):
    # Si falla, guardar en el directorio actual
    output_file = "ast_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(fix_scientific_notation(json.dumps(result, indent=2, ensure_ascii=False)))

 print(f" Conversión exitosa")
 print(f" Archivo generado: {output_file}")
 #print(f"✓ Total de nodos: {len(result['Program'])}")

if __name__ == "__main__":
    main()