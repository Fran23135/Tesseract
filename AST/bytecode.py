class ASTNode:
    pass

class VariableDeclaration(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class CallExpression(ASTNode):
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class IntermediateInstruction:
    def __init__(self, operation, operands):
        self.operation = operation
        self.operands = operands

    def __str__(self):
        return f"{self.operation} {' '.join(self.operands)}"

class CodeGenerator:
    def __init__(self):
        self.instructions = []

    def visit(self, node):
        if isinstance(node, VariableDeclaration):
            self.handle_variable_declaration(node)
        elif isinstance(node, CallExpression):
            self.handle_call_expression(node)

    def handle_variable_declaration(self, node):
        self.instructions.append(IntermediateInstruction("assign", [node.name, node.value]))

    def handle_call_expression(self, node):
        self.instructions.append(IntermediateInstruction("call", [node.name, *node.arguments]))

def parse_ast(lines):
    ast = []
    current_node = None

    for line in lines:
        if line.startswith("VariableDeclaration:"):
            var_name = line.split(":")[1].strip()
            # Leer el siguiente valor
            value_line = next(lines)
            value = value_line.split(":")[1].strip()
            current_node = VariableDeclaration(var_name, value)
            ast.append(current_node)
        elif line.startswith("CallExpression:"):
            func_name = line.split(":")[1].strip()
            # Leer argumentos
            arg_line = next(lines)
            arg_name = arg_line.split(":")[1].strip()
            current_node = CallExpression(func_name, [arg_name])
            ast.append(current_node)

    return ast

def read_ast_from_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    return [line.strip() for line in lines]

# Leer el AST desde un archivo
ast_lines = read_ast_from_file('ast_output.txt')  # Asegúrate de que este archivo existe

# Parsear el AST y generar código intermedio
ast = parse_ast(iter(ast_lines))
generator = CodeGenerator()

for node in ast:
    generator.visit(node)

intermediate_code = generator.instructions

# Guardar el código intermedio en un archivo
intermediate_code_file_path = 'intermediate_code.txt'  # Cambia la ruta según sea necesario
with open(intermediate_code_file_path, 'w') as f:
    for instruction in intermediate_code:
        f.write(str(instruction) + "\n")

print(f"Código intermedio guardado en {intermediate_code_file_path}")
