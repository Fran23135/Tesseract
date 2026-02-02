%{
    
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdbool.h>

#define VOID_RESULT_MARKER "__VOID_FUNCTION_RESULT__"
extern int yylineno;
typedef struct ast_node {
    char* type;
    char* value;
    struct ast_node* left;
    struct ast_node* right;
} ast_node;
typedef struct symbol {
    char *name;
    char* value;
    char* type;
    char* operation_str;
    struct symbol *next; // Para la lista enlazada por scope
    bool is_explicitly_typed;
} symbol;
typedef struct Scope {
    symbol *symbol_list;
    struct Scope *parent;  // Apuntador al scope padre (así se forma la pila)
} Scope;
typedef struct operations {
    char *op;
    int num;
} operations;

typedef struct {
    char* name;
    char* type;
} ParamSymbol;
typedef struct {
    char* name;
    char* return_value; // El último valor que retornó la función
    char* return_type;  // El tipo de dato que debe retornar
    ParamSymbol** params;  
    int param_count;
} FunctionSymbol;
ast_node* expression_node_stack[256];
int stack_tops = -1;
const char* g_output_path = "ast_output.txt";
FunctionSymbol func_tab[999];
int func_count = 0;
Scope *currentScope = NULL;
// Puntero para saber en qué función estamos actualmente durante el parseo
FunctionSymbol* current_function_being_parsed = NULL;
char* current_function_name = NULL;
int function_num= 0;
//symbol symtab[999];
operations expression_op[999];
int expression_num = 0;
//int symcount = 0;
int valid = 0;
char *concat_op;
int blockcode = 0;
char * comparison;
int longitud = 1;
int use_indent = 0; // Modo por defecto = bloques
int paren_num = 0;
char **global_arr;
int global_arr_size = 0;
char *con_op;
int compile_mode = 0;
// Funciones de ayuda para manejar el stack
ast_node* node_stack[256];
int node_stack_ptr = 0;

void set_default_mode(const char *mode) {
    if (strcmp(mode, "ident") == 0) {
        use_indent = 1;
    } else if (strcmp(mode, "block") == 0) {
        use_indent = 0;
    }
}
void yyerror(const char* s) {
    fprintf(stderr, "Error: %s\n", s);
}
// Función de hashing simple (djb2) para crear un nombre de archivo único
static unsigned long hash_string(const char *str) {
    unsigned long hash = 5381;
    int c;
    while ((c = *str++))
        hash = ((hash << 5) + hash) + c; /* hash * 33 + c */
    return hash;
}
/*void push_node(ast_node* node) {
    if (stack_tops < 255) {
        expression_node_stack[++stack_tops] = node;
    } else {
        yyerror("Error: Desbordamiento de la pila de expresiones.");
        exit(1);
    }
}*/
void push_node(ast_node* node) {
    if (node_stack_ptr < 256) {
        node_stack[node_stack_ptr++] = node;
    } else {
        yyerror("Desbordamiento del stack de nodos (Node stack overflow)");
        exit(1);
    }
}
/*ast_node* pop_node() {
      if (stack_tops > -1) {
        return expression_node_stack[stack_tops--];
    }
    // MEJORA: El mensaje de error ahora incluye la línea del parser.
    char error_msg[256];
    sprintf(error_msg, "Error en linea %d: Intento de pop en una pila de expresiones vacia.", yylineno);
    yyerror(error_msg);
    exit(1); // Es importante detener la ejecución aquí.
    return NULL;
}*/
ast_node* pop_node() {
    if (node_stack_ptr > 0) {
        return node_stack[--node_stack_ptr];
    } else {
        char error_msg[256];
        sprintf(error_msg, "Error en linea %d: Intento de pop en una pila de expresiones vacia.", yylineno);
        yyerror(error_msg);
        exit(1); // Es importante det
        return NULL; 
    }
}
// Obtiene la ruta completa del archivo de configuración
static const char* get_config_path() {
    static char path[1024];
    const char* filename_base = "compiler_config_default";
    unsigned long hashed_name = hash_string(filename_base);

    #ifdef _WIN32
        // En Windows, se guarda en %APPDATA% (ej: C:\Users\TuUsuario\AppData\Roaming)
        const char* appdata = getenv("APPDATA");
        if (appdata != NULL) {
            sprintf(path, "%s\\%lu", appdata, hashed_name);
        } else {
            // Fallback si APPDATA no está definido
            sprintf(path, "C:\\Temp\\%lu", hashed_name);
        }
    #else
        // En Linux/macOS, se guarda en el directorio HOME (ej: /home/tu_usuario/.config_default)
        const char* home = getenv("HOME");
        if (home != NULL) {
            sprintf(path, "%s/.%lu", home, hashed_name);
        } else {
            // Fallback si HOME no está definido
            sprintf(path, "/tmp/.%lu", hashed_name);
        }
    #endif

    return path;
}

// Carga la configuración por defecto desde el archivo
void load_default_mode(int* use_indent_ptr) {
    const char* path = get_config_path();
    FILE* file = fopen(path, "r");
    if (file == NULL) {
        // Si el archivo no existe, no hacemos nada. Se usará el default del programa.
        return;
    }

    char mode[10];
    if (fscanf(file, "%s", mode) == 1) {
        if (strcmp(mode, "ident") == 0) {
            *use_indent_ptr = 1;
        } else {
            *use_indent_ptr = 0;
        }
    }
    fclose(file);
}

// Guarda la configuración por defecto en el archivo
void save_default_mode(int use_indent) {
    const char* path = get_config_path();
    FILE* file = fopen(path, "w");
    if (file == NULL) {
        fprintf(stderr, "Advertencia: No se pudo guardar la configuración por defecto en %s\n", path);
        return;
    }

    if (use_indent) {
        fprintf(file, "ident");
    } else {
        fprintf(file, "block");
    }
    fclose(file);
    printf("Modo por defecto guardado en: %s\n", path);
}
char* trim_whitespace(char* str) {
    char* end;
    while (isspace((unsigned char)*str)) str++;
    if (*str == 0) return str;
    end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    *(end + 1) = 0;
    return str;
}
ast_node* create_node(char* type, char* value, ast_node* left, ast_node* right) {
    ast_node* new_node = (ast_node*) malloc(sizeof(ast_node));
    new_node->type = strdup(type);
    new_node->value = value ? strdup(value) : NULL;
    new_node->left = left;
    new_node->right = right;
    return new_node;
}
ast_node* concat_node(ast_node* left, ast_node* right){
    ast_node* new_node = (ast_node*) malloc(sizeof(ast_node));
    new_node->left = left;
    new_node->right = right;
    return new_node;
}
symbol* find_variable(char *name) {
    Scope *scope_iterator = currentScope;
    while (scope_iterator != NULL) {
        symbol *symbol_iterator = scope_iterator->symbol_list;
        while (symbol_iterator != NULL) {
            if (strcmp(symbol_iterator->name, name) == 0) {
                return symbol_iterator;
            }
            symbol_iterator = symbol_iterator->next;
        }
        scope_iterator = scope_iterator->parent;
    }
    return NULL;
}

// Reemplaza add_var con esta
void declare_var(char *name, char *value, char *tipo, bool is_explicit, const char* op_str) {
     symbol *s = currentScope->symbol_list; 
    while(s != NULL) { 
        if (strcmp(s->name, name) == 0) {
            char error_msg[256]; 
            sprintf(error_msg, "Error semantico en linea %d: La variable '%s' ya ha sido declarada en este ambito.", yylineno, name); 
            yyerror(error_msg);
            exit(1); // <-- ESTE ES EL CAMBIO. Reemplaza 'return;' por 'exit(1);'
        }
        s = s->next; 
    }

    // El resto de la función para crear la variable no cambia
    symbol *newSymbol = (symbol*) malloc(sizeof(symbol)); 
    newSymbol->name = strdup(name); 
    newSymbol->value = strdup(value);
    newSymbol->type = strdup(tipo);
    newSymbol->operation_str = op_str ? strdup(op_str) : NULL;
    newSymbol->is_explicitly_typed = is_explicit;
    newSymbol->next = currentScope->symbol_list; 
    currentScope->symbol_list = newSymbol;
}
char* determine_type(const char* str) {
  if (str == NULL) return "null";
    int len = strlen(str);

    // 1. Quitar espacios en blanco de los bordes para una detección precisa
    char* trimmed_str = trim_whitespace(strdup(str));
    if (strlen(trimmed_str) == 0) {
        free(trimmed_str);
        return "string"; // Un string vacío
    }

    // 2. Comprobar si es un Diccionario o Array/Tupla por el primer caracter
    char first_char = trimmed_str[0];
    char last_char = trimmed_str[strlen(trimmed_str) - 1];

    if (first_char == '{' && last_char == '}') {
        free(trimmed_str);
        return "Dict";
    }
    if (first_char == '(' && last_char == ')') {
        free(trimmed_str);
        return "Tuple";
    }
    if (first_char == '[' && last_char == ']') {
        free(trimmed_str);
        return "Array";
    }

    free(trimmed_str); // No olvides liberar la copia

    // 3. Si no es una colección, procede con las comprobaciones anteriores
    if (strcmp(str, "True") == 0 || strcmp(str, "False") == 0) {
        return "boolean";
    }
    if (strstr(str, "..") != NULL) {
        return "Range";
    }
    
    // ... (El resto de tu lógica para int, float y string no necesita cambiar) ...
    int has_dot = 0;
    int is_numeric = 1;
    const char* start_ptr = str;
    if (*start_ptr == '-' || *start_ptr == '+') start_ptr++;
    if (*start_ptr == '\0') is_numeric = 0;

    for (int i = 0; start_ptr[i] != '\0'; i++) {
        if (start_ptr[i] == '.') {
            if (has_dot) { is_numeric = 0; break; }
            has_dot = 1;
        } else if (!isdigit(start_ptr[i])) {
            is_numeric = 0;
            break;
        }
    }

    if (is_numeric) {
        return has_dot ? "float" : "int";
    }

    return "string";

}

// Reemplaza reassign_var con esta
void reassign_var(char *name, char *new_value, const char* op_str) {
  symbol* s = find_variable(name);
    if (s) {
       // 1. Determinamos el tipo del NUEVO valor
       char* new_type = determine_type(new_value);

       // 2. Comprobamos si hay conflictos con un tipado explícito previo
       if (s->is_explicitly_typed && strcmp(s->type, new_type) != 0) {
            char error_msg[512];
            sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, new_type, s->name, s->type);
            yyerror(error_msg);
            exit(1);
        }

        // 3. Actualizamos valor Y TIPO
        free(s->value);
        s->value = strdup(new_value);
        
        free(s->type);
        s->type = strdup(new_type); // <-- ESTA LÍNEA ES LA CLAVE

        // Actualizamos el string de la operación
        if (s->operation_str) free(s->operation_str);
        s->operation_str = op_str ? strdup(op_str) : NULL;

    } else {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, name);
        yyerror(error_msg);
        exit(1);
    }
}
void reassign_var_with_type(char *name, char *new_value, char *new_type) {
    symbol* s = find_variable(name);
    if (s) {
        free(s->value);
        s->value = strdup(new_value);
        
        free(s->type); // Liberamos el tipo antiguo
        s->type = strdup(new_type); // Asignamos el nuevo tipo
    } else {
        // ... (tu manejo de error)
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, name);
        yyerror(error_msg);
        exit(1);
    }
}
// Reemplaza get_var con esta
char* get_var(char *name) {
    symbol* s = find_variable(name);
    return s ? s->value : NULL;
}

// Reemplaza get_type con esta
char* get_type(char *name) {
    symbol* s = find_variable(name);
    return s ? s->type : NULL;
}


/*har* get_type(char *name) {
    // Recorremos la tabla de símbolos desde el inicio hasta el último elemento agregado.
    for (int i = 0; i < symcount; i++) {
        // Comparamos el nombre buscado con el nombre en la tabla actual.
        if (strcmp(symtab[i].name, name) == 0) {
            // Si se encuentra la variable, devolvemos su tipo.
            return symtab[i].type;
        }
    }
    // Si el bucle termina y no se encontró la variable, devolvemos NULL.
    return NULL;
}*/

void init_scope_manager() {
    currentScope = (Scope*) malloc(sizeof(Scope));
    if (!currentScope) { yyerror("Out of memory"); exit(1); }
    currentScope->symbol_list = NULL;
    currentScope->parent = NULL;
}

void enter_scope() {
    Scope *newScope = (Scope*) malloc(sizeof(Scope));
    if (!newScope) { yyerror("Out of memory"); exit(1); }
    newScope->symbol_list = NULL;
    newScope->parent = currentScope;
    currentScope = newScope;
}

void exit_scope() {
    if (currentScope->parent == NULL) { return; }

    Scope *scopeToFree = currentScope;
    currentScope = currentScope->parent;

    symbol *current_symbol = scopeToFree->symbol_list;
    while (current_symbol != NULL) {
        symbol *next = current_symbol->next;
        free(current_symbol->name);
        free(current_symbol->value);
        free(current_symbol->type);
        free(current_symbol);
        current_symbol = next;
    }
    free(scopeToFree);
}

void print_ast(ast_node* node, FILE* output, int level) {
    if (node == NULL) return;

    for (int i = 0; i < level; i++) {
        fprintf(output, "  "); // Indentar para el nivel actual
    }

    fprintf(output, "%s: %s\n", node->type, node->value ? node->value : "");

    if (node->left) {
        print_ast(node->left, output, level + 1);
    }

    if (node->right) {
        print_ast(node->right, output, level + 1);
    }
}

void generate_ast_file(ast_node* root) {
    if(blockcode <=0){
        /*
                 #ifdef _WIN32
            const char* temp_dir = getenv("TEMP");
            const char* temp_file = "\\ast_output.txt";  // Windows usa '\'
        #else
            const char* temp_dir = "/tmp";
            const char* temp_file = "/ast_output.txt";  // Unix usa '/'
        #endif

        char temp_path[1024];
        snprintf(temp_path, sizeof(temp_path), "%s%s", temp_dir, temp_file);

        // ---- Paso 1: Borrar el archivo anterior si existe ----
        if (access(temp_path, F_OK) == 0) {  // Verifica si el archivo existe
            #ifdef _WIN32
                _unlink(temp_path);  // Borrar en Windows
            #else
                unlink(temp_path);   // Borrar en Linux/macOS
            #endif
        }

        // ---- Paso 2: Crear un archivo nuevo en modo "w" (sobrescritura) ----
        FILE* file = fopen(temp_path, "w");
        if (!file) {
            fprintf(stderr, "Error: No se pudo crear el archivo AST en %s\n", temp_path);
            return;
        }

        // Escribir el AST desde cero
        fprintf(file, "Program\n");  // Cabecera
        print_ast(root, file, 1);    // Contenido
        fclose(file);

        printf("✅ AST generado en: %s\n", temp_path);  // Confirmación
    */

       
        // Abre el archivo en modo 'append' (añadir) usando la ruta global
        FILE* file = fopen(g_output_path, "a"); 
        if (file == NULL) {
            fprintf(stderr, "Error: no se puede abrir el archivo de salida %s\n", g_output_path);
            return;
        }
        print_ast(root, file, 1);
        fclose(file);
    

    }

}
char* floatToString(float numero) {
    // El tamaño del buffer puede variar según tus necesidades
    char* buffer = (char*)malloc(20 * sizeof(char));

    // Utilizamos snprintf para convertir el float a char*
    snprintf(buffer, 20, "%.2f", numero);

    return buffer;
}

char *to_string(int x) {
    char buf[100];
    sprintf(buf, "%d", x);
    return strdup(buf);
}
char *to_string_f(int x) {
    char buf[100];
    sprintf(buf, "%.2f", x);
    return strdup(buf);
}
float to_float(char* cadena) {
    char* end;
    float valor = strtof(cadena, &end);

    // Verificar si la conversión fue exitosa
    if (end == cadena) {
        printf("Error: no se pudo convertir '%s' a float.\n", cadena);
        return 0.0;
    }

    return valor;
}
char* removeParentheses(char* str) {
    int i = 0, j = 0;
    while (str[i]) {
        if (str[i] != '(' && str[i] != ')') {
            str[j++] = str[i];
        }
        i++;
    }
     str[j] = '\0';  // Añadimos el terminador de cadena
     return str;
}

/*int valid_expression(const char* expr) {
        int i = 0;
    int operador_anterior = 1;  // Para controlar que no haya operadores consecutivos o al inicio
    int operando_anterior = 0;  // Para controlar que no haya más de un operando sin operador entre ellos
    int decimal_en_numero = 0;  // Para controlar si ya hay un punto decimal en el número actual
    int operador_encontrado = 0;  // Para controlar que haya al menos un operador

    while (expr[i] != '\0') {
        char actual = expr[i];

        // Ignorar espacios en blanco
        if (actual == ' ') {
            i++;
            continue;
        }

        // Si es un dígito
        if (isdigit(actual)) {
            operando_anterior = 1;
            operador_anterior = 0;  // Se espera un operador después de un operando
        }
        // Si es una letra (variable)
        else if (isalpha(actual)) {
            if (operando_anterior) {
                // Si ya hay un operando, no puede haber otra variable sin un operador antes
                return 0;
            }
            operando_anterior = 1;
            operador_anterior = 0;  // Se espera un operador después de la variable
        }
        // Si es un punto decimal
        else if (actual == '.') {
            if (decimal_en_numero) {
                // Si ya hay un punto decimal en este número, es inválido
                return 0;
            }
            // Si el punto es al principio de un número, asumir que es 0. Ej: ".3" -> "0.3"
            if (operando_anterior == 0) {
                operando_anterior = 1;
            }
            decimal_en_numero = 1;
            operador_anterior = 0;
        }
        // Si es un operador válido (+, -, *, /)
        else if (actual == '+' || actual == '-' || actual == '*' || actual == '/') {
            if (operador_anterior) {
                // Si ya hay un operador antes de este o si el operador está al inicio, es inválido
                return 0;
            }
            operador_encontrado = 1;  // Encontramos al menos un operador
            operador_anterior = 1;
            operando_anterior = 0;  // Se espera un operando después del operador
            decimal_en_numero = 0;  // Reiniciar el control del decimal para el próximo número
        }
        // Si es un carácter inválido
        else {
            return 0;
        }

        i++;
    }

    // Si la expresión termina con un operador o un número con solo un punto decimal, es inválida
    if (operador_anterior || (decimal_en_numero == 1 && expr[i - 1] == '.')) {
        return 0;
    }

    // Si no se encontró ningún operador, significa que es solo un número o variable
    if (!operador_encontrado) {
        return 0;
    }

    return 1;
}*/
#include <ctype.h>

int valid_expression(const char* expr) {
    int i = 0;
    int operador_anterior = 1;       // Si hay operador antes
    int operando_anterior = 0;       // Si hubo operando antes
    int decimal_en_numero = 0;       // Punto decimal en el número actual
    int operador_encontrado = 0;     // Para saber si hubo al menos un operador
    int paren_balance = 0;           // Conteo de paréntesis

    while (expr[i] != '\0') {
        char actual = expr[i];

        // Ignorar espacios
        if (actual == ' ') {
            i++;
            continue;
        }

        // Abrir paréntesis
        if (actual == '(') {
            if (operando_anterior) return 0;  // No puede venir justo después de un operando
            paren_balance++;
            operador_anterior = 1;  // Se espera operando después
            i++;
            continue;
        }

        // Cerrar paréntesis
        if (actual == ')') {
            if (operador_anterior) return 0;  // No puede cerrar después de un operador
            if (paren_balance == 0) return 0; // No hay paréntesis que cerrar
            paren_balance--;
            operador_anterior = 0;
            operando_anterior = 1;
            i++;
            continue;
        }

        // Dígito
        if (isdigit(actual)) {
            operando_anterior = 1;
            operador_anterior = 0;
        }
        // Letra (variable)
        else if (isalpha(actual)) {
            if (operando_anterior) return 0;
            operando_anterior = 1;
            operador_anterior = 0;
        }
        // Punto decimal
        else if (actual == '.') {
            if (decimal_en_numero) return 0;
            if (!operando_anterior) operando_anterior = 1;
            decimal_en_numero = 1;
            operador_anterior = 0;
        }
        // Operadores
        else if (actual == '+' || actual == '-' || actual == '*' || actual == '/' || actual == '%') {
            if (operador_anterior) {
                // Permitir + o - solo si es al inicio o después de (
                if ((i == 0 || expr[i - 1] == '(') && (actual == '+' || actual == '-' || actual == '%')) {
                    i++;
                    continue;
                }
                return 0;
            }
            operador_encontrado = 1;
            operador_anterior = 1;
            operando_anterior = 0;
            decimal_en_numero = 0;
        }
        // Cualquier otro carácter no permitido
        else {
            return 0;
        }

        i++;
    }

    // No debe terminar con operador o punto decimal, ni quedar paréntesis abiertos
    if (operador_anterior || (decimal_en_numero && expr[i - 1] == '.') || paren_balance != 0) return 0;

    if (!operador_encontrado) return 0;

    return 1;
}




char *do_op(char *a, char op, char *b) {
    int x = atoi(a);
    int y = atoi(b);
    int z;
    switch (op) {
        case '+': z = x + y; break;
        case '-': z = x - y; break;
        case '*': z = x * y; break;
        case '/': z = x / y; break;
        default: z = 0; break;
    }

    return to_string(z);
}
char *removeQuotes(char* strs) {
    int len = strlen(strs);
    
    // Verifica si el string tiene comillas dobles al principio y al final
    if (len > 1 && strs[0] == '"' && strs[len - 1] == '"') {
        // Desplaza los caracteres para eliminar las comillas
        memmove(strs, strs + 1, len - 2);
        strs[len - 2] = '\0';  // Asegura que la cadena termine correctamente
        return strs;
    }
}

char *do_op_float(char *a, char op, char *b) {
    float x = to_float(a);
    float y = to_float(b);
    float z;
    switch (op) {
        case '+': z = x + y; break;
        case '-': z = x - y; break;
        case '*': z = x * y; break;
        case '/': z = x / y; break;
        default: z = 0; break;
    }

    return floatToString(z);
}
char* op_concat(char *a, char op, char *b) {
    // Calcular el tamaño de la cadena concatenada (+1 para el carácter op y +1 para el terminador nulo '\0')
    int len = strlen(a) + strlen(b) + 2;
    
    // Reservar memoria para la cadena resultante
    char* result = (char*) malloc(len * sizeof(char));
    
    if (result == NULL) {
        printf("Error al asignar memoria.\n");
        return NULL;
    }

    // Copiar la primera cadena a 'result'
    strcpy(result, a);
    
    // Concatenar el carácter 'op'
    result[strlen(a)] = op;
    result[strlen(a) + 1] = '\0';

    // Concatenar la segunda cadena
    strcat(result, b);

    return result;
}
char *concat_strings(char *a, char *b) {
    char buf[200];
    sprintf(buf, "%s%s", a, b);
    return strdup(buf);
}
char *concatenateComparison(const char *str1, const char *str2, const char *str3) {
    // Calcular la longitud total de la nueva cadena
    size_t length = strlen(str1) + strlen(str2) + strlen(str3) + 1; // +1 para el terminador nulo

    // Reservar memoria para la nueva cadena
    char *result = (char *)malloc(length);
    if (result == NULL) {
        fprintf(stderr, "Error al asignar memoria.\n");
        exit(1);
    }

    // Concatenar las cadenas
    strcpy(result, str1);
    strcat(result, str2);
    strcat(result, str3);

    return result;
}
char *concat_con_espacio(const char *str1, const char *str2) {
    const char *separador = " . ";
    size_t len1 = strlen(str1);
    size_t len2 = strlen(str2);
    size_t len_sep = strlen(separador);
    
    // Asignamos memoria para la nueva cadena
    char *resultado = malloc(len1 + len_sep + len2 + 1);
    if (!resultado) {
        return NULL; // Manejo de error si falla malloc
    }

    // Construimos la cadena concatenada
    strcpy(resultado, str1);
    strcat(resultado, separador);
    strcat(resultado, str2);

    return resultado;
}

char* ComillasDobles(const char* str) {
    // Calcular el tamaño del string original más 2 para las comillas
    size_t len = strlen(str);
    
    // Asignar memoria para el nuevo string (1 para el primer '"', len para el string, 1 para el segundo '"', y 1 para el '\0')
    char* resultado = (char*)malloc(len + 3); 
    
    if (resultado == NULL) {
        // Si no se puede asignar memoria, retornar NULL
        return NULL;
    }

    // Poner la primera comilla doble
    resultado[0] = '"';
    
    // Copiar el string original
    strcpy(resultado + 1, str);
    
    // Poner la segunda comilla doble al final
    resultado[len + 1] = '"';
    
    // Asegurarse de que el string termine con '\0'
    resultado[len + 2] = '\0';

    return resultado;
}
bool greaterRanges(const char *input) {
    int num1, num2;

    // Extraer los dos números usando sscanf
    if (sscanf(input, "%d..%d", &num1, &num2) == 2) {
        return num1 > num2; // Retorna true si el primer número es mayor
    } else {
        // Si el formato no es válido, podrías retornar false o manejarlo según lo necesario
        fprintf(stderr, "Error: Formato de cadena no válido.\n");
        return false;
    }
}
char* evaluate_logical_conditions(char *conditions) {
    // Separamos las condiciones por comas
    char *token = strtok(conditions, ",");
    int result = 1; // Default: True (1), False (0)
    
    while (token != NULL) {
        // El último valor de la cadena es el resultado lógico (True/False)
        char *logical_result = strrchr(token, '=');  // Buscamos el '=' para identificar el resultado lógico
        if (logical_result != NULL) {
            *logical_result = '\0';  // Separamos la comparación del resultado lógico
            logical_result++;        // Avanzamos al resultado lógico (True/False)

            // Evaluamos el resultado lógico (True = 1, False = 0)
            if (strcmp(logical_result, "True") == 0) {
                result = result && 1; // Si es True, mantenemos el valor lógico como True
            } else if (strcmp(logical_result, "False") == 0) {
                result = result && 0; // Si es False, lo ponemos como False
            }
        }
        
        // Conseguimos el siguiente token (separado por comas)
        token = strtok(NULL, ",");
    }

    // Retornamos el resultado lógico final como "True" o "False"
    return result == 1 ? "True" : "False";
}

/*char* process_conditions(const char *condition_with_result) {
    // Suponemos que `condition_with_result` está en el formato: "comparacion,result_logico"
    char* condition = strtok(strdup(condition_with_result), ",");  // Parte antes de la coma
    char* result_logical = strtok(NULL, "");  // Parte después de la coma

    // Si no conseguimos ambas partes, algo está mal
    if (!condition || !result_logical) {
        fprintf(stderr, "Error al procesar las condiciones y el resultado lógico.\n");
        exit(1);
    }

    // Concatenamos la condición y el resultado lógico de forma final
    char* final_result = malloc(strlen(condition) + strlen(result_logical) + 2); // +2 para la coma y terminador nulo
    sprintf(final_result, "%s,%s", condition, result_logical);

    return final_result;
}
*/
char* process_conditions(const char *input) {
 // Copiar la entrada a una cadena dinámica
    char *cadena = malloc(strlen(input) + 1);
    if (cadena == NULL) {
        printf("Error: no se pudo asignar memoria.\n");
        return NULL;
    }
    strcpy(cadena, input);

    // Variable para almacenar el resultado final
    char *resultado = malloc(strlen(cadena) + 1); // Inicialmente con el mismo tamaño
    if (resultado == NULL) {
        free(cadena);
        printf("Error: no se pudo asignar memoria para el resultado.\n");
        return NULL;
    }
    resultado[0] = '\0';  // Inicializar como una cadena vacía

    // Usar strtok para separar por comas
    char *condicion = strtok(cadena, ",");
    while (condicion != NULL) {
        // Eliminar "True" o "False" si aparecen
        char *true_pos = strstr(condicion, "True");
        if (true_pos != NULL) {
            memmove(true_pos, true_pos + 4, strlen(true_pos + 4) + 1); // Desplazar después de "True"
        }

        char *false_pos = strstr(condicion, "False");
        if (false_pos != NULL) {
            memmove(false_pos, false_pos + 5, strlen(false_pos + 5) + 1); // Desplazar después de "False"
        }

        // Verificar si hay algo válido en la condición (que no esté vacía)
        if (strlen(condicion) > 0) {
            // Concatenar al resultado, respetando los operadores lógicos
            if (strlen(resultado) > 0) {
               // strcat(resultado, ",");  // Añadir coma entre condiciones
            }
            strcat(resultado, condicion);
        }

        // Obtener la siguiente condición
        condicion = strtok(NULL, ",");
    }

    // Limpiar los operadores lógicos sobrantes en los bordes (si existen)
    int len = strlen(resultado);
    if (len > 2 && (strcmp(&resultado[len - 2], "&&") == 0 || strcmp(&resultado[len - 2], "||") == 0)) {
        resultado[len - 2] = '\0'; // Eliminar operador lógico al final
    }

    // Liberar la memoria usada para la cadena temporal
    free(cadena);

    return resultado;
}

char *add_quotes(const char *str) {
    size_t len = strlen(str);
    char *quoted_str = (char *)malloc(len + 3); // 2 comillas + 1 terminador null

    if (!quoted_str) {
        return NULL; // Manejo de error si malloc falla
    }

    quoted_str[0] = '"';
    strcpy(quoted_str + 1, str);
    quoted_str[len + 1] = '"';
    quoted_str[len + 2] = '\0';

    return quoted_str;
}

char *determineArrayType(char *input){
   char *copy = strdup(input);
    char *token = strtok(copy, ",");
    int has_int = 0, has_float = 0, has_str = 0, has_bool = 0;

    while (token) {
        while (isspace(*token)) token++; // quitar espacios al inicio
        int len = strlen(token);
        while (len > 0 && isspace(token[len - 1])) token[--len] = '\0'; // quitar espacios al final

        // Booleano
        if (strcmp(token, "True") == 0 || strcmp(token, "False") == 0) {
            has_bool = 1;
        }
        // String entre comillas
        else if (len >= 2 && token[0] == '"' && token[len - 1] == '"') {
            has_str = 1;
        }
        // Posible número
        else {
            int dots = 0, digits = 0, valid = 1;
            for (int i = 0; i < len; i++) {
                if (token[i] == '.') dots++;
                else if (!isdigit(token[i]) && !(i == 0 && (token[i] == '-' || token[i] == '+'))) {
                    valid = 0;
                    break;
                } else {
                    digits++;
                }
            }
            if (valid && digits > 0) {
                if (dots == 1) has_float = 1;
                else if (dots == 0) has_int = 1;
                else has_str = 1; // más de un punto → no válido
            } else {
                has_str = 1;
            }
        }

        token = strtok(NULL, ",");
    }

    free(copy);
    int total = has_int + has_float + has_str + has_bool;
    if (total > 1) return "MArr";
    if (has_int) return "int";
    if (has_float) return "float";
    if (has_str) return "string";
    if (has_bool) return "bool";
    
    return "MArr";
}

char** split_string(const char* cadena, const char* delimitador) {
    // Copia de la cadena para no modificar la original, ya que strtok lo hace.
    char* copia = strdup(cadena);
    if (copia == NULL) {
        perror("Fallo al duplicar la cadena");
        return NULL;
    }

    char** resultado = NULL;
    int contador = 0;
    char* token = strtok(copia, delimitador);

    while (token != NULL) {
        contador++;
        // Se redimensiona el array de punteros para el nuevo elemento.
        char** temp = realloc(resultado, sizeof(char*) * contador);
        if (temp == NULL) {
            // Manejo de error de realloc
            perror("Fallo de realloc");
            free(copia);
            // Liberar lo que ya se había asignado
            for (int i = 0; i < contador - 1; i++) free(resultado[i]);
            free(resultado);
            return NULL;
        }
        resultado = temp;
        
        // Se guarda una copia del token en el array.
        resultado[contador - 1] = strdup(token);
        if (resultado[contador - 1] == NULL) {
            perror("Fallo al duplicar token");
            // Liberar memoria en caso de fallo
            free(copia);
            for (int i = 0; i < contador - 1; i++) free(resultado[i]);
            free(resultado);
            return NULL;
        }

        token = strtok(NULL, delimitador);
    }

    // Se agrega el terminador NULL al final del array.
    char** temp = realloc(resultado, sizeof(char*) * (contador + 1));
     if (temp == NULL) {
        perror("Fallo final de realloc");
        // Liberar memoria en caso de fallo
        free(copia);
        for (int i = 0; i < contador; i++) free(resultado[i]);
        free(resultado);
        return NULL;
    }
    resultado = temp;
    resultado[contador] = NULL;
    
    free(copia); // Se libera la copia inicial.
    return resultado;
}
/*char* reconstruct_expression() {
    char* reconstruction_stack[100]; // Un stack temporal de strings
    int stack_ptr = 0;

    // Recorremos la "receta" que generó el parser, que ahora incluye los marcadores de paréntesis
    for (int i = 0; i < expression_num; i++) {
        operations current_op = expression_op[i];

        if (current_op.num == 0) { // Si es un Operando (ej. "5")
            // Simplemente lo metemos al stack
            reconstruction_stack[stack_ptr++] = strdup(current_op.op);
        } 
        else if (current_op.num == 1) { // Si es un Operador (ej. "+")
            // Sacamos los dos últimos operandos del stack
            char* right_str = reconstruction_stack[--stack_ptr];
            char* left_str = reconstruction_stack[--stack_ptr];
            
            // MODIFICACIÓN CLAVE: Creamos la sub-expresión SIN añadir paréntesis extras
            char new_expr_str[1024];
            sprintf(new_expr_str, "%s%s%s", left_str, current_op.op, right_str);

            // Metemos el resultado de vuelta al stack
            reconstruction_stack[stack_ptr++] = strdup(new_expr_str);

            free(left_str);
            free(right_str);
        }
        // --- LÓGICA AÑADIDA PARA TUS MARCADORES ---
        else if (current_op.num == 3) { // Si es un Paréntesis de Cierre (de paren_right)
            // Sacamos la última expresión construida del stack...
            char* inner_expr = reconstruction_stack[--stack_ptr];
            
            // ...y la envolvemos en paréntesis.
            char new_paren_str[1024];
            sprintf(new_paren_str, "(%s)", inner_expr);

            // Metemos la versión con paréntesis de vuelta al stack
            reconstruction_stack[stack_ptr++] = strdup(new_paren_str);
            free(inner_expr);
        }
        // El marcador de inicio de paréntesis (num == 2 de paren_left) se ignora aquí.
        // Su trabajo ya fue hecho en el parser para asegurar que el marcador de cierre
        // se colocara correctamente en la lista.
    }

    // Al final, el único elemento que queda en el stack es la cadena completa
    char* final_string = strdup(reconstruction_stack[--stack_ptr]);
    free(reconstruction_stack[stack_ptr]);
    
    // Limpiamos el array global para la siguiente operación
    // (Asegúrate de liberar la memoria de los 'op' en expression_op también)
    for (int i = 0; i < expression_num; i++) {
        free(expression_op[i].op); 
    }
    expression_num = 0;
    printf("Reconstructed expression: %s\n", final_string);
    return final_string;
}
*/
char* reconstruct_expression() {
    char* reconstruction_stack[100]; // Correcto: un stack de strings (char*).
    int stack_ptr = 0;

    // Recorremos la "receta" que generó el parser, que ahora incluye los paréntesis.
    for (int i = 0; i < expression_num; i++) {
        operations current_op = expression_op[i];

        if (current_op.num == 0) { // Si es un Operando (ej. "5")
            // Simplemente lo metemos al stack
            reconstruction_stack[stack_ptr++] = strdup(current_op.op);
        } 
        else if (current_op.num == 1) { // Si es un Operador (ej. "+")
            // Sacamos los dos últimos operandos del stack
            char* right_str = reconstruction_stack[--stack_ptr];
            char* left_str = reconstruction_stack[--stack_ptr];
            
            // Creamos la nueva sub-expresión SIN añadir paréntesis extras
            char new_expr_str[1024];
            sprintf(new_expr_str, "%s%s%s", left_str, current_op.op, right_str);

            // Metemos el resultado de vuelta al stack
            reconstruction_stack[stack_ptr++] = strdup(new_expr_str);

            free(left_str);
            free(right_str);
        }
       
        else if (current_op.num == 3) { // Si es un Paréntesis de Cierre (de tu regla paren_right)
            // Esta es la nueva lógica clave.
            // Sacamos la última expresión construida del stack...
            char* inner_expr = reconstruction_stack[--stack_ptr];
            
            // ...y la envolvemos en paréntesis.
            char new_paren_str[1024];
            sprintf(new_paren_str, "(%s)", inner_expr);

            // Metemos la versión con paréntesis de vuelta al stack
            reconstruction_stack[stack_ptr++] = strdup(new_paren_str);
            free(inner_expr);
        }
        // Nota: El marcador de inicio de paréntesis (num == 2) se ignora a propósito.
        // El marcador de cierre es el que nos dice cuándo agrupar.
    }

    // Al final, el único elemento que queda en el stack es la cadena completa.
    char* final_string = strdup(reconstruction_stack[--stack_ptr]);
    free(reconstruction_stack[stack_ptr]);

    // Limpiamos el array global para la siguiente operación
    expression_num = 0;
    printf("Reconstructed expression: %s\n", final_string);
    return final_string;
}


void free_split_string(char** array) {
    if (array == NULL) return;
    for (int i = 0; array[i] != NULL; i++) {
        free(array[i]); // Libera cada cadena individual.
    }
    free(array); // Libera el array de punteros.
}

// Coloca esto junto a tus otras funciones como do_op y do_op_float

char* do_division(char* a, char* b) {
    // 1. Convertir siempre a float para obtener un resultado preciso
    float x = to_float(a);
    float y = to_float(b);

    // 2. Manejar la división por cero
    if (y == 0.0) {
        yyerror("Error: División por cero");
        return "0";
    }

    float result_f = x / y;

    // 3. Comprobar si el resultado es un número entero
    //    (Comparando el float con su versión truncada a int)
    if (result_f == (int)result_f) {
        // Si son iguales, no hay decimales. Devolvemos como int.
        return to_string((int)result_f);
    } else {
        // Si son diferentes, hay decimales. Devolvemos como float.
        return floatToString(result_f);
    }
}

// Busca una función por su nombre
FunctionSymbol* lookup_function(char* name) {
    for (int i = 0; i < func_count; i++) {
        if (strcmp(func_tab[i].name, name) == 0) {
            return &func_tab[i];
        }
    }
    return NULL;
}
void parse_and_store_parameters(FunctionSymbol* func, char* param_string) {
    if (param_string == NULL || strlen(param_string) == 0) {
        func->param_count = 0;
        func->params = NULL;
        return;
    }

    char* copy = strdup(param_string);
    char* token = strtok(copy, ",");
    
    // Reiniciamos el conteo por si la función se está redefiniendo.
    // (Aquí faltaría liberar la memoria de los parámetros anteriores si fuera el caso,
    // pero para una primera definición esto es seguro).
    func->param_count = 0;
    
    while (token != NULL) {
        // 1. Aumentamos el tamaño del array de punteros en 1.
        func->param_count++;
        func->params = realloc(func->params, func->param_count * sizeof(ParamSymbol*));
        if (func->params == NULL) {
            yyerror("Out of memory");
            exit(1);
        }

        // 2. Creamos espacio para la nueva estructura del parámetro.
        ParamSymbol* new_param = (ParamSymbol*) malloc(sizeof(ParamSymbol));
        if (new_param == NULL) {
            yyerror("Out of memory");
            exit(1);
        }

        // 3. Parseamos el token para obtener tipo y nombre.
        while (isspace(*token)) token++; // Limpiar espacios
        char* type = "any";
        char* name = token;
        char* space = strchr(token, ' ');
        if (space != NULL) {
            *space = '\0';
            type = token;
            name = space + 1;
        }

        new_param->name = strdup(name);
        new_param->type = strdup(type);

        // 4. Guardamos el puntero a la nueva estructura en nuestro array.
        func->params[func->param_count - 1] = new_param;

        token = strtok(NULL, ",");
    }
    
    free(copy);
}
// Añade una función a la tabla (o la encuentra si ya existe)
// Guarda su nombre y el tipo de retorno esperado.
void add_or_find_function(char* name, char* return_type_str) {
     FunctionSymbol* func = lookup_function(name);
    if (func == NULL) { // Si la función no existe, la creamos
        if (func_count >= 999) {
            yyerror("Error: Limite de funciones alcanzado.");
            return;
            
        }

        func = &func_tab[func_count++];
        func->name = strdup(name);
        // ANTES: func->return_value = strdup("0");
        // AHORA: Inicializamos a NULL para saber que no se ha retornado nada.
        func->return_value = NULL;
        func->params = NULL; // <-- IMPORTANTE
        func->param_count = 0;   // <-- IMPORTANTE
    }
    func->return_type = strdup(return_type_str);
   //current_function_name = name; // La marcamos como la función actual
  // printf("function actual: %s\n", current_function_name);
}

// Guarda el valor del 'return' de la función actual
void set_function_return_value(FunctionSymbol* func, char* value_to_return) {
    if (func == NULL) {
        yyerror("Error: 'return' utilizado fuera de una funcion.");
        exit(1);
        
    }

    char* expr_type = determine_type(value_to_return);

    // Si el tipo de la función no se ha definido, lo inferimos del return.
    if (strcmp(func->return_type, "inferred") == 0) {
        free(func->return_type); // Liberamos "inferred"
        func->return_type = strdup(expr_type);
    }
    // Si el tipo ya está definido, comprobamos que coincidan.
    else if (strcmp(func->return_type, expr_type) != 0) {
        char err_msg[256];
        sprintf(err_msg, "Error: La funcion '%s' debe devolver '%s' pero retorna '%s'", func->name, func->return_type, expr_type);
        yyerror(err_msg);
        exit(1);
    }
    
    // Guardamos el valor del return
    free(func->return_value);
    func->return_value = strdup(value_to_return);
}

// Coloca esto en la sección %{...%} de semantic.y

void validate_function_call(char* func_name, char* arg_string) {
    // PASO 1: BUSCAR LA FUNCIÓN
    FunctionSymbol* func = lookup_function(func_name);
    if (!func) {
        char error_msg[256];
        sprintf(error_msg, "Line %d: Call to undefined function '%s'", yylineno, func_name);
        yyerror(error_msg);
        exit(1);
    }

    // PASO 2: OBTENER Y CONTAR LOS ARGUMENTOS
    char** args = split_string(arg_string ? arg_string : "", ",");
    int arg_count = 0;
    if (args) {
        for (int i = 0; args[i] != NULL; i++) arg_count++;
    }

    // PASO 3: VALIDACIÓN DE CANTIDAD
    if (arg_count != func->param_count) {
        char error_msg[256];
        sprintf(error_msg, "Line %d: Function '%s' expects %d arguments, but %d were given", yylineno, func->name, func->param_count, arg_count);
        yyerror(error_msg);
        free_split_string(args);
        exit(1);
    }

    // PASO 4: VALIDACIÓN DE TIPOS
    for (int i = 0; i < arg_count; i++) {
        char* expected_type = func->params[i]->type;
        char* arg_value = args[i];
        while(isspace(*arg_value)) arg_value++;

        if (strcmp(expected_type, "any") == 0 || strcmp(arg_value, "null") == 0) {
            continue;
        }

        char* actual_type = get_var(arg_value) ? get_type(get_var(arg_value)) : determine_type(arg_value);

        if (strcmp(expected_type, actual_type) != 0) {
            char error_msg[256];
            sprintf(error_msg, "Line %d: Type mismatch for argument %d in function '%s'. Expected '%s' but got '%s'", yylineno, i + 1, func->name, expected_type, actual_type);
            yyerror(error_msg);
            free_split_string(args);
            exit(1);
        }
    }

    free_split_string(args);
}

char* get_element_by_index(const char* list_string, int index) {
  if (!list_string || index < 0) return NULL;

    const char* p = list_string;
    // Nos saltamos el bracket/paréntesis inicial, si existe.
    if (*p == '[' || *p == '(') p++;

    const char* element_start = p;
    int current_index = 0;
    int level = 0; // Para manejar anidación

    while (*p != '\0') {
        if (*p == '{' || *p == '(' || *p == '[') level++;
        else if (*p == '}' || *p == ')' || *p == ']') level--;

        // Si encontramos una coma en el nivel principal (no anidada)
        if (*p == ',' && level == 0) {
            if (current_index == index) {
                int len = p - element_start;
                char* result = (char*)malloc(len + 1);
                strncpy(result, element_start, len);
                result[len] = '\0';
                return trim_whitespace(result);
            }
            current_index++;
            element_start = p + 1; // El siguiente elemento empieza después de la coma
        }
        p++;
    }

    // Si llegamos aquí, estamos en el último elemento de la lista
    if (current_index == index) {
        int len = p - element_start;
        // Corregimos para no cortar el último ']' o ')' del contenedor principal
        if (len > 0 && (*(p - 1) == ']' || *(p - 1) == ')')) {
             if(level == -1) len--;
        }
        char* result = (char*)malloc(len + 1);
        strncpy(result, element_start, len);
        result[len] = '\0';
        return trim_whitespace(result);
    }

    return NULL; // Índice no encontrado

}

char* get_value_by_key_from_array(const char* array_string, const char* key) {
   // ... el código de la función inteligente que ignora claves dentro de {} ...
    if (!array_string || !key) return NULL;
    const char* p = array_string;
    int level = 0;
    char* result = NULL;
    if (*p == '[' || *p == '(') p++;
    const char* element_start = p;
    while (*p != '\0' && result == NULL) {
        if (*p == '{' || *p == '(' || *p == '[') level++;
        else if (*p == '}' || *p == ')' || *p == ']') level--;
        if ((*p == ',' && level == 0) || *(p + 1) == '\0') {
            const char* element_end = p;
            if (*(p + 1) == '\0') element_end = p + 1;
            int len = element_end - element_start;
            char* current_element_str = malloc(len + 1);
            strncpy(current_element_str, element_start, len);
            current_element_str[len] = '\0';
            char* trimmed_element = trim_whitespace(current_element_str);
            char* colon_pos = strchr(trimmed_element, ':');
            if (colon_pos && *trimmed_element != '{' && *trimmed_element != '(' && *trimmed_element != '[') {
                *colon_pos = '\0';
                char* current_key = removeQuotes(trim_whitespace(trimmed_element));
                if (strcmp(current_key, key) == 0) {
                    result = strdup(trim_whitespace(colon_pos + 1));
                }
            }
            free(current_element_str);
            element_start = p + 1;
        }
        p++;
    }
    return result;
}

/**
 * Obtiene un subconjunto de elementos de un array usando un rango (ej. "1..3").
 * Devuelve un nuevo string de array, ej. "[elem2,elem3,elem4]".
 */
char* get_elements_by_range(const char* array_string, const char* range_expr) {
      if (array_string == NULL) return NULL;

    int start, end;
    if (sscanf(range_expr, "%d..%d", &start, &end) != 2 || start > end || start < 0) {
        return NULL; // Rango inválido
    }

    char result_buffer[4096] = "[";
    int first_element = 1;
    
    // Iteramos de 'start' a 'end' y usamos nuestra nueva función segura
    for (int i = start; i <= end; i++) {
        char* element = get_element_by_index(array_string, i);
        
        if (element != NULL) {
            if (!first_element) {
                strcat(result_buffer, ", ");
            }
            strcat(result_buffer, element);
            first_element = 0;
            free(element);
        } else {
            break;
        }
    }

    strcat(result_buffer, "]");
    
    if (first_element) {
        return strdup("[]");
    }

    return strdup(result_buffer);
}

char* remove_quotes_safe(const char* str) {
    if (!str) return NULL;
    int len = strlen(str);
    if (len > 1 && str[0] == '"' && str[len - 1] == '"') {
        // Asigna memoria para la nueva cadena (longitud - 2 comillas + 1 terminador)
        char* new_str = (char*)malloc(len - 1);
        if (!new_str) return NULL; // Falló malloc
        // Copia el contenido sin las comillas
        strncpy(new_str, str + 1, len - 2);
        new_str[len - 2] = '\0'; // Añade el terminador nulo
        return new_str;
    }
    // Si no tiene comillas, devuelve una copia para poder liberarla después sin problemas
    return strdup(str);
}
// Esta función se encarga de procesar la interpolación en el momento correcto.
char* process_string(const char* raw_string_with_quotes) {
  // Quitamos las comillas del string crudo
    char* raw_string = strdup(raw_string_with_quotes + 1);
    raw_string[strlen(raw_string) - 1] = '\0';

    char result_buffer[4096] = "";
    const char* current_pos = raw_string;
    char* hash_pos;

    while ((hash_pos = strstr(current_pos, "#(")) != NULL) {
        strncat(result_buffer, current_pos, hash_pos - current_pos);
        char* end_paren = strchr(hash_pos, ')');
        if (end_paren == NULL) { /* ... manejo de error ... */ break; }
        
        char expr_str[256];
        int expr_len = end_paren - (hash_pos + 2);
        strncpy(expr_str, hash_pos + 2, expr_len);
        expr_str[expr_len] = '\0';
        
        char* value_to_insert = NULL;

        // --- LÓGICA DE DECISIÓN MEJORADA ---

        char* open_bracket = strchr(expr_str, '[');
        char* close_bracket = strrchr(expr_str, ']');
        char* op_pos = NULL;
        char op = 0;

        // 1. PRIMERO, VERIFICAMOS SI ES ACCESO A UN ARRAY
        if (open_bracket && close_bracket && close_bracket > open_bracket) {
            char array_name[128], index_part[128];

            // Parseamos el nombre del array y la parte del índice
            strncpy(array_name, expr_str, open_bracket - expr_str);
            array_name[open_bracket - expr_str] = '\0';
            strncpy(index_part, open_bracket + 1, close_bracket - (open_bracket + 1));
            index_part[close_bracket - (open_bracket + 1)] = '\0';
            
            char* trimmed_array_name = trim_whitespace(array_name);
            char* trimmed_index_part = trim_whitespace(index_part);

            // Resolvemos el array y el índice (que puede ser una variable)
            char* array_data = get_var(trimmed_array_name);
            char* array_type = get_type(trimmed_array_name);
            char* resolved_index = get_var(trimmed_index_part) ? get_var(trimmed_index_part) : trimmed_index_part;
             printf("trimmed_array_name: %s, resolved_index: %s\n", trimmed_array_name, resolved_index);
            // Validamos y obtenemos el valor
            if (array_data == NULL || strcmp(array_type, "Array") != 0) {
                char error_msg[256];
                sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no es un array.", yylineno, trimmed_array_name);
                yyerror(error_msg);
                exit(1);
            } else {
                if (strstr(resolved_index, "..")) {
                    // Es un rango
                    value_to_insert = get_elements_by_range(array_data, resolved_index);
                    
                } else if (strcmp(determine_type(resolved_index), "int") == 0) {
                    // Es un índice único
                    int index = atoi(resolved_index);
                    value_to_insert = removeQuotes(get_element_by_index(array_data, index));
                    printf("value_to_insert: %s\n", value_to_insert);
                    if (value_to_insert == NULL) {
                        char error_msg[256];
                        sprintf(error_msg, "Error semantico en linea %d: Indice %d fuera de rango para el array '%s'.", yylineno, index, trimmed_array_name);
                        yyerror(error_msg);
                        exit(1);
                    }
                } else {
                    char error_msg[256];
                    sprintf(error_msg, "Error semantico en linea %d: El indice del array '%s' debe ser un entero o un rango.", yylineno, trimmed_array_name);
                    yyerror(error_msg);
                    exit(1);
                }
            }
        
        } else { // 2. SI NO, VERIFICAMOS SI ES UNA OPERACIÓN ARITMÉTICA
            for (int i = 0; expr_str[i] != '\0'; i++) {
                if (strchr("+-*/", expr_str[i])) { op = expr_str[i]; op_pos = &expr_str[i]; break; }
            }

            if (op_pos) {
                // ... (La lógica para aritmética que ya teníamos no cambia) ...
                char op1_str[128], op2_str[128];
                strncpy(op1_str, expr_str, op_pos - expr_str);
                op1_str[op_pos - expr_str] = '\0';
                strcpy(op2_str, op_pos + 1);
                char* trimmed_op1 = trim_whitespace(op1_str);
                char* trimmed_op2 = trim_whitespace(op2_str);
                char* val1 = get_var(trimmed_op1) ? get_var(trimmed_op1) : trimmed_op1;
                char* val2 = get_var(trimmed_op2) ? get_var(trimmed_op2) : trimmed_op2;
                
                if (val1 && val2) {
                    char* type1 = determine_type(val1);
                    char* type2 = determine_type(val2);
                    bool is_numeric1 = (strcmp(type1, "int") == 0 || strcmp(type1, "float") == 0);
                    bool is_numeric2 = (strcmp(type2, "int") == 0 || strcmp(type2, "float") == 0);
                    if (is_numeric1 && is_numeric2) {
                        if (op == '/') { value_to_insert = do_division(val1, val2); }
                        else if (strcmp(type1, "float") == 0 || strcmp(type2, "float") == 0) { value_to_insert = do_op_float(val1, op, val2); }
                        else { value_to_insert = do_op(val1, op, val2); }
                    } else {
                        char error_msg[512];
                        sprintf(error_msg, "Error semantico en linea %d: La operacion '%c' no esta soportada entre los tipos '%s' y '%s'.", yylineno, op, type1, type2);
                        yyerror(error_msg);
                        exit(1);
                    }
                }
            } else { // 3. SI NO, ES UNA VARIABLE SIMPLE
                char* trimmed_expr = trim_whitespace(expr_str);
                value_to_insert = get_var(trimmed_expr);
                if(value_to_insert) value_to_insert = strdup(value_to_insert);
            }
        }
        
        // ... (El resto de la función para insertar el valor no cambia) ...
        if (value_to_insert) {
            strcat(result_buffer, value_to_insert);
            free(value_to_insert);
        } else {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: La expresion '%s' no pudo ser resuelta.", yylineno, expr_str);
            yyerror(error_msg);
            exit(1);
        }
        current_pos = end_paren + 1;
    }

    strcat(result_buffer, current_pos);
    free(raw_string);
    return strdup(result_buffer);
}
char* get_default_value_for_type(const char* type_name) {
    if (strcmp(type_name, "int") == 0) return "0";
    if (strcmp(type_name, "float") == 0) return "0.0";
    if (strcmp(type_name, "string") == 0) return "\"\""; // Un string vacío
    if (strcmp(type_name, "bool") == 0) return "False";
    if (strcmp(type_name, "Array") == 0) return "[]";
    // Para otros tipos como Array o Range, un valor "null" o "[]" podría tener sentido
    return "null"; // Un valor por defecto general
}
char* get_value_by_key_from_dict(const char* dict_string, const char* key) {
    if (!dict_string || !key || dict_string[0] != '{') return NULL;

    // Preparamos la clave de búsqueda, ej: "arr":
    size_t key_len = strlen(key);
    // Usamos remove_quotes_safe para asegurar que la clave no tenga comillas
    char* clean_key = remove_quotes_safe(key);
    char* search_key = malloc(strlen(clean_key) + 4);
    if (!search_key) { free(clean_key); return NULL; }
    sprintf(search_key, "\"%s\":", clean_key);
    free(clean_key);

    const char* key_pos = strstr(dict_string, search_key);
    free(search_key);

    if (!key_pos) {
        return NULL; // La clave no se encontró
    }

    // Avanzamos el puntero hasta el inicio del valor
    const char* value_start = key_pos + strlen(search_key);
    value_start = trim_whitespace((char*)value_start);

    const char* value_end = value_start;
    int level = 0; // Para contar niveles de anidación

    // Si el valor es una estructura, buscamos su cierre
    if (*value_start == '[' || *value_start == '{' || *value_start == '(') {
        char open_char = *value_start;
        char close_char = (open_char == '[') ? ']' : ((open_char == '{') ? '}' : ')');
        level = 1;
        value_end++; // Empezamos a buscar desde el siguiente caracter
        while (*value_end != '\0' && level > 0) {
            if (*value_end == open_char) level++;
            if (*value_end == close_char) level--;
            value_end++;
        }
    } else { // Si es un valor simple, buscamos la próxima coma o llave de cierre
        while (*value_end != '\0' && *value_end != ',' && *value_end != '}') {
            value_end++;
        }
    }

    // Copiamos el valor encontrado a un nuevo string
    int len = value_end - value_start;
    char* result = (char*)malloc(len + 1);
    strncpy(result, value_start, len);
    result[len] = '\0';

    return trim_whitespace(result);
}

// REEMPLAZA TAMBIÉN ESTA OTRA FUNCIÓN COMPLETA
char* get_value_by_index_from_dict(const char* dict_string, int index) {
    if (!dict_string || index < 0 || dict_string[0] != '{') {
        return NULL;
    }

    char* copy = strdup(dict_string);
    if (!copy) return NULL;

    char* current_pos = copy + 1; // Empezamos después del '{'
    int current_index = 0;
    char* result = NULL;

    // Caso especial: diccionario vacío
    if (*trim_whitespace(current_pos) == '}') {
        free(copy);
        return NULL;
    }

    while (*current_pos != '\0' && *current_pos != '}') {
        // Encontramos el inicio del valor (después de los dos puntos)
        char* colon_pos = strchr(current_pos, ':');
        if (!colon_pos) break; // Mal formado, salimos

        // Si es el índice que buscamos
        if (current_index == index) {
            char* value_start = colon_pos + 1;
            char* value_end = strpbrk(value_start, ",}");
            
            if (value_end) {
                *value_end = '\0'; // Cortamos la cadena
            }
            
            result = strdup(trim_whitespace(value_start));
            break; // Encontramos el resultado, salimos del bucle
        }

        // Si no, avanzamos al siguiente elemento
        current_pos = strchr(colon_pos, ',');
        if (!current_pos) break; // No hay más comas, fin de la lista
        
        current_pos++; // Nos movemos después de la coma
        current_index++;
    }

    free(copy);
    return result; // Devolvemos el resultado (o NULL si no se encontró)
}
int array_has_keys(const char* array_string) {
    if (array_string == NULL) {
        return 0;
    }
    // Buscamos la primera ocurrencia de ':' en toda la cadena.
    // Es una forma rápida y eficiente de detectar un par clave:valor.
    if (strchr(array_string, ':') != NULL) {
        return 1; // Sí, contiene al menos una clave.
    }
    return 0; // No, es un array de solo valores.
}

char* access_collection_element(const char* var_name, const char* indexer_input) {
      char error_msg[512]; // Buffer para nuestros nuevos mensajes de error
    char* var_data = get_var((char*)var_name);
    char* var_type = get_type((char*)var_name);
    char* resolved_indexer = get_var((char*)indexer_input) ? get_var((char*)indexer_input) : (char*)indexer_input;
       // --- LÓGICA DE RESOLUCIÓN CORREGIDA ---
    // Si el indexer_input NO es un string literal (no tiene comillas),
    // SÍ intentamos resolverlo como una variable.
     // Primero, siempre intentamos obtener el valor del 'indexer_input' como si fuera una variable.
    char* value_from_var = get_var((char*)indexer_input);

    if (value_from_var != NULL) {
        // Si 'indexer_input' es el nombre de una variable (ej: "i"), usamos su valor (ej: "5").
        resolved_indexer = value_from_var;
    } else {
        // Si no se encontró como variable, significa que es un valor literal 
        // (como un número "0" o una clave de string "\"clave\""). Lo usamos directamente.
        resolved_indexer = (char*)indexer_input;
    }

    char* indexer_copy = strdup(resolved_indexer);
    char* current_element_str = strdup(var_data);
    char* current_element_type = strdup(var_type);
    char* single_index = strtok(indexer_copy, ":");

    while (single_index != NULL) {
        char* next_element_str = NULL;
        char* indexer_type = determine_type(single_index);

        if (strcmp(current_element_type, "Array") == 0 || strcmp(current_element_type, "Tuple") == 0) {
            if (strcmp(indexer_type, "int") == 0) {
                next_element_str = get_element_by_index(current_element_str, atoi(single_index));
            } else if (strcmp(indexer_type, "string") == 0) {
                char* key = remove_quotes_safe(single_index);
                next_element_str = get_value_by_key_from_array(current_element_str, key);
                free(key);
            } else {
                sprintf(error_msg, "Error en linea %d: Indice '%s' invalido para '%s'. Un Array o Tupla solo acepta indices enteros o claves de string.", yylineno, single_index, var_name);
                yyerror(error_msg);
                exit(1);
            }
        } else if (strcmp(current_element_type, "Dict") == 0) {
            if (strcmp(indexer_type, "int") == 0) {
                next_element_str = get_value_by_index_from_dict(current_element_str, atoi(single_index));
            } else if (strcmp(indexer_type, "string") == 0) {
                char* key = remove_quotes_safe(single_index);
                next_element_str = get_value_by_key_from_dict(current_element_str, key);
                free(key);
            } else {
                sprintf(error_msg, "Error en linea %d: Indice '%s' invalido para '%s'. Un Diccionario solo acepta indices enteros o claves de string.", yylineno, single_index, var_name);
                yyerror(error_msg);
                exit(1);
            }
        } else {
            // Este es el error de acceso profundo en un no-coleccionable
            sprintf(error_msg, "Error en linea %d: Intento de acceso profundo en '%s' con el indice '%s'. El elemento extraido no es una coleccion (es de tipo '%s').", yylineno, var_name, single_index, current_element_type);
            yyerror(error_msg);
            exit(1);
        }

        free(current_element_str);
        current_element_str = next_element_str;
        
        if (current_element_str == NULL) {
            // Este error ocurre si un índice intermedio no encuentra nada
            sprintf(error_msg, "Error en linea %d: El indice o clave '%s' no se encontro dentro de la estructura de '%s'.", yylineno, single_index, var_name);
            yyerror(error_msg);
            exit(1);
        }
        
        free(current_element_type);
        current_element_type = determine_type(current_element_str);
        single_index = strtok(NULL, ":");
    }

    free(indexer_copy);
    free(current_element_type);
    return current_element_str;
}

// AÑADE ESTA FUNCIÓN JUNTO A do_op y do_op_float
char* do_mod(char* a, char* b) {
    int x = atoi(a);
    int y = atoi(b);

    // Manejo de la división por cero
    if (y == 0) {
        yyerror("Error: Modulo por cero.");
        return "0";
    }

    int z = x % y;
    return to_string(z);
}
char* handle_increment_decrement(char* var_name, const char* op) {
    // 1. Buscar la variable
    symbol* s = find_variable(var_name);
    if (!s) {
        char error_msg[256];
        sprintf(error_msg, "Error en linea %d: La variable '%s' no ha sido declarada.", yylineno, var_name);
        yyerror(error_msg);
        //return NULL;
        exit(1);
    }

    // 2. Validar el tipo
    if (strcmp(s->type, "int") != 0 && strcmp(s->type, "float") != 0) {
        char error_msg[256];
        sprintf(error_msg, "Error de tipo en linea %d: La operacion '%s' solo se puede aplicar a variables de tipo int o float, no a '%s'.", yylineno, op, s->type);
        yyerror(error_msg);
       // return s->value; // Devolvemos el valor original sin modificar
        exit(1);
    }

    // 3. Realizar la operación
    char* new_value_str;
    if (strcmp(s->type, "int") == 0) {
        int value = atoi(s->value);
        if (strcmp(op, "++") == 0) {
            value++;
        } else { // "--"
            value--;
        }
        new_value_str = to_string(value);
    } else { // float
        float value = to_float(s->value);
        if (strcmp(op, "++") == 0) {
            value++;
        } else { // "--"
            value--;
        }
        new_value_str = floatToString(value);
    }

    // 4. Actualizar la variable en la tabla de símbolos
    free(s->value);
    s->value = new_value_str;
    // El tipo no cambia, no es necesario reasignarlo.
    // La operación se borra, ya que es una modificación directa.
    if (s->operation_str) {
        free(s->operation_str);
        s->operation_str = NULL;
    }

    return s->value; // Devuelve el nuevo valor
}

int is_truthy(const char* value_str) {
    if (value_str == NULL) return 0;

    char* type = determine_type(value_str);

    if (strcmp(type, "int") == 0) {
        return atoi(value_str) != 0;
    }
    if (strcmp(type, "float") == 0) {
        return to_float((char*)value_str) != 0.0;
    }
    if (strcmp(type, "string") == 0) {
        // Un string es truthy si no está vacío
        return strlen(remove_quotes_safe((char*)value_str)) > 0;
    }
    if (strcmp(type, "boolean") == 0) {
        return strcmp(value_str, "True") == 0;
    }
    // Las colecciones (Array, Dict, Tuple) son truthy si no están vacías
    if (strcmp(type, "Array") == 0) {
        return strcmp(value_str, "[]") != 0;
    }
    if (strcmp(type, "Dict") == 0) {
        return strcmp(value_str, "{}") != 0;
    }
    if (strcmp(type, "Tuple") == 0) {
        return strcmp(value_str, "()") != 0; // Asumiendo que () es una tupla vacía
    }

    return 0; // Por defecto, todo lo demás es falsy
}

ast_node* create_ast_from_literal_string(const char* literal_str);

// Función principal para parsear listas (contenidos de Arrays y Tuplas)
ast_node* create_elements_from_string(const char* content_str, int* element_count) {
    *element_count = 0;
    if (content_str == NULL || strlen(content_str) == 0) {
        return create_node("elements", NULL, NULL, NULL);
    }

    ast_node* elements_head = create_node("elements", NULL, NULL, NULL);
    ast_node* current_node_in_chain = NULL;
    
    const char* p_start = content_str;
    const char* p_end = content_str;
    int nesting_level = 0;

    while (*p_end != '\0') {
        if (*p_end == '[' || *p_end == '{' || *p_end == '(') nesting_level++;
        if (*p_end == ']' || *p_end == '}' || *p_end == ')') nesting_level--;

        // Encontramos un elemento completo cuando hay una coma a nivel 0, o al final del string.
        if ((*p_end == ',' && nesting_level == 0) || *(p_end + 1) == '\0') {
            int len;
            if (*(p_end + 1) == '\0') { // Último elemento
                len = (p_end - p_start) + 1;
            } else { // Elemento separado por coma
                len = p_end - p_start;
            }

            char* element_str = (char*) malloc(len + 1);
            strncpy(element_str, p_start, len);
            element_str[len] = '\0';

            // Llamada recursiva para construir el AST del elemento
            ast_node* new_element_node = create_ast_from_literal_string(element_str);
            free(element_str);

            // Enlazamos el nuevo nodo a la cadena de elementos
            if (current_node_in_chain == NULL) {
                elements_head->left = new_element_node;
            } else {
                current_node_in_chain->right = new_element_node;
            }
            current_node_in_chain = new_element_node;
            (*element_count)++;
            
            p_start = p_end + 1; // El siguiente elemento empieza después de la coma
        }
        p_end++;
    }
    return elements_head;
}

// Función principal para parsear los pares de un Diccionario
ast_node* create_properties_from_string(const char* content_str, int* prop_count) {
    *prop_count = 0;
    if (content_str == NULL || strlen(content_str) == 0) {
        return create_node("properties", NULL, NULL, NULL);
    }

    ast_node* properties_head = create_node("properties", NULL, NULL, NULL);
    ast_node* current_prop_in_chain = NULL;

    // Lógica similar a create_elements, pero buscando ":" para separar clave/valor
    // (Una implementación completa requeriría una lógica de parsing similar a la de arriba)
    // Por simplicidad para este ejemplo, usaremos una versión más básica que asume claves simples.
    // Una versión robusta usaría la misma técnica de "nesting_level".
    
    char* mutable_body = strdup(content_str);
    char* pair = strtok(mutable_body, ",");
    while(pair != NULL) {
        char* colon = strchr(pair, ':');
        if (colon) {
            *colon = '\0';
            char* key_str = trim_whitespace(pair);
            char* value_str = trim_whitespace(colon + 1);

            ast_node* key_node = create_node("key", NULL, create_ast_from_literal_string(key_str), NULL);
            ast_node* value_node = create_node("value", NULL, create_ast_from_literal_string(value_str), NULL);
            ast_node* new_prop = create_node("Property", NULL, key_node, value_node);
            (*prop_count)++;
            
            if (current_prop_in_chain == NULL) {
                properties_head->left = new_prop;
            } else {
                current_prop_in_chain->right = new_prop;
            }
            current_prop_in_chain = new_prop;
        }
        pair = strtok(NULL, ",");
    }
    free(mutable_body);

    return properties_head;
}

// Función "despachadora": decide qué tipo de nodo crear basado en el string.
ast_node* create_ast_from_literal_string(const char* literal_str) {
    char* trimmed = trim_whitespace(strdup(literal_str));
    char first_char = trimmed[0];
    char last_char = trimmed[strlen(trimmed)-1];

    if (first_char == '[' && last_char == ']') {
        int count = 0;
        char* content = strdup(trimmed + 1);
        content[strlen(content)-1] = '\0';
        ast_node* elements = create_elements_from_string(content, &count);
        free(content);

        ast_node* type_node = create_node("type", "Array", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(count), NULL, NULL);
        type_node->right = len_node;
        len_node->right = elements;
        ast_node* final_node = create_node("ArrayLiteral", NULL, type_node, NULL);
        free(trimmed);
        return final_node;
    } 
    else if (first_char == '{' && last_char == '}') {
        int count = 0;
        char* content = strdup(trimmed + 1);
        content[strlen(content)-1] = '\0';
        ast_node* properties = create_properties_from_string(content, &count);
        free(content);

        ast_node* type_node = create_node("type", "Dict", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(count), NULL, NULL);
        type_node->right = len_node;
        len_node->right = properties;
        ast_node* final_node = create_node("DictLiteral", NULL, type_node, NULL);
        free(trimmed);
        return final_node;
    }
    else if (first_char == '(' && last_char == ')') {
        int count = 0;
        char* content = strdup(trimmed + 1);
        content[strlen(content)-1] = '\0';
        ast_node* elements = create_elements_from_string(content, &count);
        free(content);

        ast_node* type_node = create_node("type", "Tuple", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(count), NULL, NULL);
        type_node->right = len_node;
        len_node->right = elements;
        ast_node* final_node = create_node("TupleLiteral", NULL, type_node, NULL);
        free(trimmed);
        return final_node;
    }
    else {
        // Es un literal simple (int, string, bool, etc.)
        char* type = determine_type(trimmed);
        ast_node* literal_node;
        if (strcmp(type, "int") == 0) literal_node = create_node("NumericLiteral", trimmed, NULL, NULL);
        else if (strcmp(type, "boolean") == 0) literal_node = create_node("BooleanLiteral", trimmed, NULL, NULL);
        else literal_node = create_node("StringLiteral", trimmed, NULL, NULL); // Default
        free(trimmed);
        return literal_node;
    }
}

%}
%union {
    int ival;
    char *sval;
    char **arrval;
    float fval;
    struct ast_node* node;
}

%type <node> var 
%type <sval> var_for
%token <sval> TEXT
%token <sval> STRING STRING_WITH_VARS
%token <ival> NUMBER INCREMENT DECREMENT
%token PRINT VAR PLUS MINUS TIMES DIVIDE EQUAL SEMICOLON READ  INSERTVALUE COLON 
%token DOT COM SHARP LSQUARE RSQUARE SQUARES_L_R ELSE ELSE_IF RANGE_SEMI_OPEN IFX 
%token EQUALC UNEQUAL GREATERTHAN LESSTHAN GREATERTHAN_EQUAL LESSTHAN_EQUAL //PARENTHESES
%token TRUE FALSE BOOL INDENT DEDENT  STRUCT
%token  TSTRING TINT TFLOAT TBOOL TVOID 
%token FOR IN RANGE  MAIN DOTYPE APPEND LENGHT WHILE IF PERFORM
%token BREAK RETURN  MOD 
%token FUNCTION FUNC  PARENS QUESTION_MARK
%token SWITCH CASE DEFAULT
%token <sval> startRace // llave de entrada 
%token <sval> endRace  // llave de cierre
%token <sval> OR AND
%token <fval> DECIMAL NEWLINE
%token IM IM_Math PI EQUATION
%type <node>    function_decl function_call array_decl array_assing   perform_while_loop //array   
%type <node> statement print read block  rlrace rbrace statements while_loop if_condition
%type <node> for_loop  condtional_stmt sentences tuples increment_decrement_stmt
%type <node> switch_cases case_list single_case switch_block 
%type <sval> expr term eqt bool variable range condition types logicals for_condition
%type <sval> comparison  parameter_list paren_left paren_right key_value_pair pair_list dict_body param_decl
%type <sval>   expr_list arith_expr argument_list array_indexer  list_item list_item_list 

//%type <sval> parameter_list
//%type <func> functio_decl 
%left COM RETURN 
%left DOT  NUMBER STRING
%left PLUS MINUS
%left TIMES DIVIDE MOD
%right QUESTION_MARK  COLON
%left IN
%right INCREMENT DECREMENT
%nonassoc EQUALC UNEQUAL GREATERTHAN LESSTHAN GREATERTHAN_EQUAL LESSTHAN_EQUAL
%nonassoc IFX
%nonassoc ELSE
%%

program: /* empty */
    | program statement
    ;
end_statement: SEMICOLON { if(use_indent) yyerror("Punto y coma innecesario en modo indentacion"); }
             | NEWLINE   { if(!use_indent) yyerror("Se esperaba un punto y coma en modo bloque"); }
             | /* empty, para la última línea del archivo */
 
statement: print end_statement 
    | var end_statement 
    | read end_statement 
    | for_loop 
    | function_decl
    | function_call
    | while_loop
    | perform_while_loop
    | if_condition
    | switch_cases
    | increment_decrement_stmt end_statement // <-- AÑADE ESTA LÍNEA
    //| array SEMICOLON
    | sentences end_statement
    ;  
print: PRINT '(' expr ')' {  
      // Crear el nodo para la instrucción print
      // Primero, verificamos si $3 es una variable declarada
      if(compile_mode){
       
      } else{
      symbol* s = find_variable($3);
      char* val1 = get_var($3) ? get_var($3) : $3;
      if (s) { // SI es una variable
          // Comprobamos si la variable tiene una operación guardada
          if (s->operation_str != NULL) {
              // Si la tiene, la usamos para crear el nodo
              $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("Operation", s->operation_str, NULL, create_node("variableName", s->name, NULL, NULL)));
          } else {
              // Si no, creamos el nodo simple
              $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("ParamType", s->type, NULL, create_node("variableName", s->name, NULL, NULL)));
          }
      } else { // NO es una variable (es un literal o una operación directa)
          if (valid == 1) {
              con_op = reconstruct_expression();
              $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("Operation", con_op, NULL, NULL));
              valid = 0;
          } else {
              $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("ParamType", determine_type($3), NULL, NULL));
          }
       }
      }
      generate_ast_file($$);
     }
     ;
increment_decrement_stmt: variable INCREMENT { // Post-incremento: x++
                              handle_increment_decrement($1, "++");
                              $$ = create_node("PostIncrementStatement", $1, NULL, NULL); generate_ast_file($$);
                          }
                        | variable DECREMENT { // Post-decremento: x--
                              handle_increment_decrement($1, "--");
                              $$ = create_node("PostDecrementStatement", $1, NULL, NULL); generate_ast_file($$);
                          }
                        | INCREMENT variable { // Pre-incremento: ++x
                              handle_increment_decrement($2, "++");
                              $$ = create_node("PreIncrementStatement", $2, NULL, NULL); generate_ast_file($$);
                          }
                        | DECREMENT variable { // Pre-decremento: --x
                              handle_increment_decrement($2, "--");
                              $$ = create_node("PreDecrementStatement", $2, NULL, NULL); generate_ast_file($$);
                          }
;


var: VAR TEXT { 
     if (compile_mode){
         
            declare_var($2,NULL,NULL,false,NULL);
            ast_node* expression_tree_root = create_node("Literal", "NULL", create_node("Type", "NULL", NULL, NULL), NULL);
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            $$ = create_node("VariableDeclaration", $2, initializer_node, NULL);   generate_ast_file($$);
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }
     }else{
      declare_var($2,"NULL","NULL",false,NULL);
      $$ = create_node("VariableDeclaration", $2, create_node("Value","NULL", create_node("Type","NULL",NULL,NULL),NULL), NULL); generate_ast_file($$);  }
   }
   | VAR TEXT EQUAL expr {
     if (compile_mode) {
         char * expr = determine_type($4);
            declare_var($2,$4,expr,false,NULL);
            ast_node* expression_tree_root = pop_node();
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            $$ = create_node("VariableDeclaration", $2, initializer_node, NULL);   generate_ast_file($$);
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }
        }else{
     // Crear el nodo para una asignación
      char * expr = determine_type($4);
      if (strcmp($4, VOID_RESULT_MARKER) == 0) {
           char error_msg[256];
           sprintf(error_msg, "Line %d: Cannot assign result of a void function to variable '%s'", yylineno, $2);
           yyerror(error_msg);
           exit(1);
       }else{
        
       
        
        if(valid==1){
             con_op = reconstruct_expression();
             declare_var($2,$4,expr,false,con_op);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file($$);
           valid = 0;
        }else if(valid==0){
            declare_var($2,$4,expr,false,NULL);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),NULL), NULL); generate_ast_file($$); 
        }

    }
    }
   }
   | VAR TEXT EQUAL startRace dict_body  endRace {
    
     if(compile_mode){
        
        int prop_count = 0;
        // 1. La nueva función crea el sub-árbol de "properties" a partir del string
        ast_node* properties_node = create_properties_from_string($5, &prop_count);

        // 2. Creamos los nodos "type" y "Longitud"
        ast_node* type_node = create_node("type", "Dict", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(prop_count), NULL, NULL);

        // 3. Enlazamos los nodos hijos en una cadena (type -> longitud -> properties)
        type_node->right = len_node;
        len_node->right = properties_node;

        // 4. Creamos el nodo principal "DictLiteral"
        ast_node* dict_literal_node = create_node("DictLiteral", NULL, type_node, NULL);

        // 5. Creamos el nodo de declaración final
        $$ = create_node("VariableDeclaration", $2, dict_literal_node, NULL);
        generate_ast_file($$);

     }else{
    char buffer[4096];
    sprintf(buffer, "{%s}", $5); // Envuelve el contenido con llaves
    declare_var($2, buffer, "Dict", false, NULL);
    $$ = create_node("VariableDeclaration", $2, create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
    generate_ast_file($$);
   }
   }
   | TEXT EQUAL startRace dict_body  endRace {
    if(compile_mode){
        int prop_count = 0;
        // 1. La nueva función crea el sub-árbol de "properties" a partir del string
        ast_node* properties_node = create_properties_from_string($5, &prop_count);

        // 2. Creamos los nodos "type" y "Longitud"
        ast_node* type_node = create_node("type", "Dict", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(prop_count), NULL, NULL);

        // 3. Enlazamos los nodos hijos en una cadena (type -> longitud -> properties)
        type_node->right = len_node;
        len_node->right = properties_node;

        // 4. Creamos el nodo principal "DictLiteral"
        ast_node* dict_literal_node = create_node("DictLiteral", NULL, type_node, NULL);

        // 5. Creamos el nodo de declaración final
        $$ = create_node("VariableAsignement", $1, dict_literal_node, NULL);
        generate_ast_file($$);
    }else{
    if(get_var($1)){
        char buffer[4096];
        sprintf(buffer, "{%s}", $4); // Envuelve el contenido con llaves
        reassign_var_with_type($1, buffer, "Dict");
        $$ = create_node("VariableAsignement", $1, create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
    } else {
        char error_msg[256];
        sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, $1);
        yyerror(error_msg);
        exit(1);
    }
    }
   }
   | VAR TEXT EQUAL range {
    if(compile_mode){
              // Parseamos el rango para crear un nodo estructurado
            int start_val, end_val;
            sscanf($4, "%d..%d", &start_val, &end_val);
            ast_node* start_node = create_node("NumericLiteral", to_string(start_val), NULL, NULL);
            ast_node* end_node = create_node("NumericLiteral", to_string(end_val), NULL, NULL);
            ast_node* start = create_node("Start", NULL, start_node, NULL);
            ast_node* end = create_node("End", NULL, end_node, NULL);
            ast_node* range_node = create_node("RangeExpression", NULL, start, end);
            $$ = create_node("VariableDeclaration", $2, range_node, NULL);
            generate_ast_file($$);
    }else{
     declare_var($2,$4,"Range",false, NULL);
     $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type","Range",NULL,NULL),NULL), NULL); generate_ast_file($$);
    }  
  }
   | TEXT EQUAL expr { 
        if (compile_mode) {
            ast_node* expression_tree_root = pop_node();
            ast_node* value_node = create_node("Value", NULL, expression_tree_root, NULL);
            $$ = create_node("VariableAssignment", $1, value_node, NULL);
            generate_ast_file($$);
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la asignacion.\n");
                stack_tops = -1;
            }
        } else{
       printf("assign: %s\n",$3);
        if (strcmp($3, VOID_RESULT_MARKER) == 0) {
           char error_msg[256];
           sprintf(error_msg, "Line %d: Cannot assign result of a void function to variable '%s'", yylineno, $1);
           yyerror(error_msg);
           exit(1);
       } else{
        if (find_variable($1)) {
             if (valid == 1) {
                 con_op = reconstruct_expression();
                 char * expr = determine_type($3);
                 reassign_var($1, $3, con_op);
                 $$ = create_node("VariableAsignement", $1, create_node("Value", $3, create_node("Type", expr, NULL, NULL), create_node("Operation", con_op, NULL, NULL)), NULL); 
                 generate_ast_file($$);
                 valid = 0;
             } else if (valid == 0) {
                 reassign_var($1, $3, NULL);
                 char * expr = determine_type($3);
                 $$ = create_node("VariableAsignement", $1, create_node("Value", $3, create_node("Type", expr, NULL, NULL), NULL), NULL); 
                 generate_ast_file($$);
             }
       }else{
         char error_msg[256];
         sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, $1);
         yyerror(error_msg);
         exit(1);
       }
     }
   }
   }

   | types TEXT {
    if(compile_mode){
        char* default_value = get_default_value_for_type($1);
         declare_var($2,default_value,$1,true, NULL);
       ast_node* expression_tree_root = create_node("Literal", default_value, create_node("Type", $1, NULL, NULL), NULL);
            ast_node* type_node = create_node("ExplicitType", $1, NULL, NULL);
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            $$ = create_node("VariableDeclaration", $2, initializer_node, type_node);
            generate_ast_file($$);
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }  
    }else{
      char* explicit_type = $1;
    // 2. Obtenemos el valor por defecto para ese tipo (ej. "0")
    char* default_value = get_default_value_for_type(explicit_type);
     declare_var($2,default_value,$1,true, NULL);
      $$ = create_node("VariableDeclaration", $2, create_node("Value",default_value, create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
    }
 }
   | types TEXT EQUAL expr {
     // Crear el nodo para una asignación
      
      if(compile_mode){
      ast_node* expression_tree_root = pop_node();
            ast_node* type_node = create_node("ExplicitType", $1, NULL, NULL);
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            $$ = create_node("VariableDeclaration", $2, initializer_node, type_node);
            generate_ast_file($$);
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }
      }else{
      char * expr = determine_type($4);
      printf("types es: %s\n",$4);
      if(strcmp($1,expr) == 0){
        if(valid==1){
           con_op = reconstruct_expression(); 
            declare_var($2,$4,$1,true,con_op);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,create_node("ExplicitType",$1,NULL,NULL)),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file($$);
           valid = 0;
        }else if(valid==0){
            declare_var($2,$4,$1,true,NULL);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$); 
        }
       }
       }
     }
    | array_decl
    | array_assing 
    | tuples
   
   ;  
tuples: VAR TEXT EQUAL paren_left  list_item_list  paren_right {
       if(compile_mode){
         char buffer[4096];
            sprintf(buffer, "(%s)", $5);
            // La nueva función despachadora también funciona para tuplas.
            ast_node* tuple_literal_node = create_ast_from_literal_string(buffer);
            $$ = create_node("VariableDeclaration", $2, tuple_literal_node, NULL);
            generate_ast_file($$);
       } else{
        char buffer[2048];
        sprintf(buffer, "(%s)", $5);
        declare_var($2, buffer, "Tuple", false,NULL);
        
        $$ = create_node("VariableDeclaration", $2, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
      }
}
   | VAR TEXT EQUAL paren_left list_item_list COM paren_right {
        char buffer[2048];
        sprintf(buffer, "(%s,)", $5);
        declare_var($2, buffer, "Tuple", false,NULL);
        $$ = create_node("VariableDeclaration", $2, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }    
    

   | TEXT EQUAL paren_left list_item_list paren_right {
         
        char buffer[2048];
        sprintf(buffer, "(%s)", $4);
       reassign_var($1, buffer,NULL);
        $$ = create_node("VariableAsignement", $1, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }
   | TEXT EQUAL paren_left list_item_list COM paren_right {
        
        char buffer[2048];
        sprintf(buffer, "(%s,)", $4);
       reassign_var($1, buffer,NULL);
        $$ = create_node("VariableAsignement", $1, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }   
   ;
array_decl: VAR TEXT EQUAL LSQUARE list_item_list  RSQUARE {
         if(compile_mode){
          char buffer[4096];
            sprintf(buffer, "[%s]", $5);
            // La nueva función despachadora hace todo el trabajo pesado.
            ast_node* array_literal_node = create_ast_from_literal_string(buffer);
            $$ = create_node("VariableDeclaration", $2, array_literal_node, NULL);
            generate_ast_file($$);
         }else{
          char buffer[2048];
           sprintf(buffer, "[%s]", $5);
           declare_var($2,buffer,"Array",false,NULL);
           $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
           longitud = 1;
           printf("%s\n",buffer);
           }
        }
          | VAR TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE list_item_list  RSQUARE {
            char buffer[2048];
          sprintf(buffer, "[%s]", $8);
            declare_var($2,buffer,"Array",false,NULL);
            $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
         }
         | types TEXT EQUAL LSQUARE list_item_list  RSQUARE {
            char buffer[2048];
          sprintf(buffer, "[%s]", $5);
           printf("types es: %s\n",determineArrayType($5));
           if(strcmp(determineArrayType($5),$1)== 0){
            declare_var($2,buffer,"Array",true,NULL);
            $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("ExplicitType",$1,NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
             fprintf(stderr, "Error valor inconpatible.\n"); 
            }
         }
         | types TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE list_item_list  RSQUARE {
           if(strcmp(determineArrayType($8),$1)== 0){  
            char buffer[2048];
           sprintf(buffer, "[%s]", $8);
           declare_var($2,buffer,"Array",true,NULL);
           $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",create_node("ExplicitType",$1,NULL,NULL),create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
           longitud = 1;
           }
         }
         | types TEXT LSQUARE NUMBER RSQUARE {
           if(strcmp($1,$1)== 0){  
           declare_var($2,NULL,"Array",true,NULL);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",create_node("ExplicitType",$1,NULL,NULL),create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           }
         }
         | types TEXT EQUAL SQUARES_L_R {
           if(strcmp($1,$1)== 0){
           declare_var($2,NULL,"Array",true,NULL);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",NULL,create_node("ExplicitType",$1,NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           }
         }
         ;
array_assing: TEXT EQUAL SQUARES_L_R {
             //char * expr = determine_type($3);
             $$ = create_node("VariableAsignement", $1, create_node("Value","[]", create_node("Type","Array",NULL ,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
             longitud = 0;
              reassign_var_with_type($1, "[]", "Array");
            }
            | TEXT EQUAL LSQUARE list_item_list RSQUARE {
             //if(strcmp(determineArrayType($4),$1)== 0){
             symbol* s = find_variable($1);
             char buffer[2048];
             sprintf(buffer, "[%s]", $4);
             // 2. Si no se encuentra, es un error semántico
              if (!s) {
               char error_msg[256];
               sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, $1);
               yyerror(error_msg);
               exit(1); // Detener el análisis
              }
               reassign_var_with_type($1, buffer, "Array");
                printf("entro\n");
                $$ = create_node("VariableAsignement", $1, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
                longitud = 1; 
             // } 
            }       
            ;
list_item: expr             { $$ = $1; } // Un elemento puede ser una expresión normal (1, "hola", x)
        // | key_value_pair   { $$ = $1; } // O puede ser un par clave-valor ("name":"jonh")
         | startRace dict_body endRace {
             // Un elemento ahora puede ser un diccionario literal
             char buffer[4096];
             sprintf(buffer, "{%s}", $2);
             $$ = strdup(buffer);
           }
         | paren_left expr_list paren_right {
             // Un elemento también puede ser una tupla literal
             char buffer[2048];
             sprintf(buffer, "(%s)", $2);
             $$ = strdup(buffer);
         }
         | paren_left expr_list COM paren_right {
             // Un elemento también puede ser una tupla literal
             char buffer[2048];
             sprintf(buffer, "(%s,)", $2);
             $$ = strdup(buffer);
         }
         | LSQUARE list_item_list RSQUARE {
          char buffer[4096];
          sprintf(buffer, "[%s]", $2);
          $$ = strdup(buffer);
         }
      
        // Un array literal (vacío) es un término
        | SQUARES_L_R {
         $$ = strdup("[]");
        }
        
list_item_list: list_item {
                    longitud = 1;
                    $$ = $1;
                }
              | list_item_list COM list_item {
                    // Tu lógica de concatenación para formar el string de la lista
                    char* tempList = concat_strings($1, ", ");
                    $$ = concat_strings(tempList, $3);
                    free(tempList);
                    longitud++;
                }
;
read: READ '('TEXT')' { 
        $$ = create_node("CallExpression", "read", create_node("Arguments", $3, NULL, NULL), create_node("Type",determine_type(get_var($3)),NULL,NULL)); generate_ast_file($$); 
     }
    ; 
var_for: VAR TEXT IN {  
     //declare_var($2,"0","int");
     $$ = $2;
    }
   ; 
range: expr RANGE expr { 
          char buffer[40]; 
          sprintf(buffer, "%s..%s", $1, $3); 
         $$ = strdup(buffer);   
     }
     | expr RANGE_SEMI_OPEN expr {
           char buffer[40];
           sprintf(buffer, "%s..<%s", $1, $3);
           $$ = strdup(buffer);
     }
;   
rlrace: startRace { $$ = create_node("BlockStart", NULL, NULL, NULL); blockcode++; }
       ;  

rbrace: endRace { $$ = create_node("BlockEnd", NULL, NULL, NULL); blockcode--; }  
       ;
sentences: BREAK { $$ = create_node("CallExpression", "Break", NULL, NULL); }   
         | RETURN  expr { 
            // Verificamos que estamos en un contexto de función válido
             if (blockcode > 0 && current_function_name != NULL) {
                 FunctionSymbol* func = lookup_function(current_function_name);

                 if (func) {
                     // REQUISITO 3: Validar que las funciones 'void' no retornen valores.
                     if (strcmp(func->return_type, "void") == 0) {
                        char error_msg[256];
                     // Formateamos el mensaje de error.
                      sprintf(error_msg, "Line %d: Function '%s' is void and cannot return a value", yylineno, func->name);
                     // Invocamos el error de parser, que detendrá el proceso.
                      yyerror(error_msg);
                      exit(1);
                     } else {
                         // REQUISITO 1: Comprobar la coincidencia de tipos.
                         char* actual_type = determine_type($2); // Tipo del valor retornado
                         
                         // Se permite 'inferred' para la primera asignación
                         if (strcmp(func->return_type, "inferred") == 0) {
                             // Si es la primera vez, el tipo de la función se infiere del retorno
                             free(func->return_type);
                             func->return_type = strdup(actual_type);
                         }
                         // Si los tipos no coinciden, lanzamos un error.
                         else if (strcmp(func->return_type, actual_type) != 0) {
                             fprintf(stderr, "Line %d: Error: Type mismatch in function '%s'. Expected return type '%s' but got '%s'.\n", yylineno, func->name, func->return_type, actual_type);
                         }

                         // Si todo está bien, guardamos el valor de retorno.
                         if (func->return_value) free(func->return_value);
                         func->return_value = strdup($2);
                     }
                 }
             } else {
                 yyerror("Error: 'return' used outside of a function."); exit(1);
             }

             // Creamos el nodo del AST para la sentencia 'return'.
             $$ = create_node("CallExpression", "Return", create_node("value", $2, NULL, NULL), NULL);
            }
        ;
     
block: rlrace { enter_scope(); } statements rbrace { exit_scope(); } { $$ = create_node("Block", "BlockStart", $3, create_node("Block", "BlockEnd", NULL, NULL));}
     | INDENT { enter_scope(); } statements DEDENT { exit_scope(); }  { $$ = create_node("Block", "BlockStart", $3, create_node("Block", "BlockEnd", NULL, NULL));}
     ;       
for_loop: FOR '(' var_for for_condition')' { 
     enter_scope();
     declare_var($3,$4,"int",false, NULL); 
      printf("for condition: %s\n",$4);
    }block {
         //declare_var($3,$4); 
         printf("for condition: %s\n",find_variable($3)->value);
     
         if(strcmp(get_type($3),"Range") == 0){
          $$ = create_node("ForLoop", $3, create_node("Range", "0..0", NULL, create_node("Condition", "false", NULL, NULL)), $7); generate_ast_file($$);         
         if (greaterRanges($4)){
            $$ = create_node("ForLoop", $3, create_node("Range", $4, NULL, create_node("Condition", "false", NULL, NULL)), $7); generate_ast_file($$);
           }else{
            $$ = create_node("ForLoop", $3, create_node("Range", $4, create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),$7); generate_ast_file($$);
           }
         }else{
          $$ = create_node("ForLoop", $3, create_node("Iterator", $4, create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),$7); generate_ast_file($$);
  
         }
         exit_scope();
  //printf("%s\n",determine_type(get_var($4)));
       }
   |  FOR '(' var_for for_condition')' COLON block {
         declare_var($3,$4,"int",false,NULL); 
         printf("for condition: %s\n",$4);
         if(strcmp(get_type($4),"Range") == 0){
          $$ = create_node("ForLoop", $3, create_node("Range", "0..0", NULL, create_node("Condition", "false", NULL, NULL)), $7); generate_ast_file($$);
           if (greaterRanges($4)){
            $$ = create_node("ForLoop", $3, create_node("Range", $4, NULL, create_node("Condition", "false", NULL, NULL)), $7); generate_ast_file($$);
           }else{
            $$ = create_node("ForLoop", $3, create_node("Range", $4, create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),$7); generate_ast_file($$);
           }
         }else{
          $$ = create_node("ForLoop", $3, create_node("Iterator", get_var($4), create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),$7); generate_ast_file($$);
  
         }
  //printf("%s\n",determine_type(get_var($4)));
       }

while_loop: WHILE'('condition')' block {
          if(!use_indent){
            char *comparison_str = strdup($3); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
           $$ = create_node("WhileLoop",comparison,create_node("ConditionIs",$3,NULL,NULL),$5); generate_ast_file($$);
          }
          }

          | WHILE'('condition')' COLON block {
            printf("ident\n");
             $$ = create_node("WhileLoop",comparison,create_node("ConditionIs",$3,NULL,NULL),$6); generate_ast_file($$);  
            
          }   
          ;
perform_while_loop: PERFORM block WHILE '(' condition ')' {
                        // $2 es el bloque de código que se ejecuta primero.
                        // $5 es la condición que se evalúa después.
                        char *comparison_str = strdup($5); // Clonar la cadena concatenada
                        char *result = strchr(comparison_str, ','); // Buscar la coma
                        if (result != NULL) {
                         *result = '\0'; // Separar comparación
                          result++;       // Apuntar al valor lógico
                        }
                        $$ = create_node("PerformWhileLoop", result, create_node("ConditionIs", comparison_str, NULL, NULL), $2);
                        generate_ast_file($$);
                  }
                  | PERFORM COLON block WHILE '(' condition ')' {
                        // $2 es el bloque de código que se ejecuta primero.
                        // $5 es la condición que se evalúa después.
                        char *comparison_str = strdup($6); // Clonar la cadena concatenada
                        char *result = strchr(comparison_str, ','); // Buscar la coma
                        if (result != NULL) {
                         *result = '\0'; // Separar comparación
                          result++;       // Apuntar al valor lógico
                        }
                        $$ = create_node("PerformWhileLoop", result, create_node("ConditionIs", comparison_str, NULL, NULL), $3);
                        generate_ast_file($$);
                  }
                  ;
          
if_condition: IF '('condition')' block %prec IFX {
             if (compile_mode) {
                          ast_node* body_node = $5;
                    // El árbol de la condición está esperando en la pila.
                    ast_node* condition_node = pop_node();
                    $$ = create_node("IfStatement", NULL,condition_node,body_node);
                    generate_ast_file($$);
                }else{
                char *comparison_str = strdup($3); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               $$ = create_node("if_Condition",result,NULL,$5); generate_ast_file($$);
               free(comparison_str);
               }
            }
            | IF '('condition')' COLON block %prec IFX {
                 if (compile_mode) {
                          ast_node* body_node = $6;
                    // El árbol de la condición está esperando en la pila.
                    ast_node* condition_node = pop_node();
                    $$ = create_node("IfStatement", NULL,condition_node,body_node);
                    generate_ast_file($$);
                }else{
                char *comparison_str = strdup($3); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               $$ = create_node("if_Condition",result,NULL,$6); generate_ast_file($$);
               free(comparison_str);
               }
           
            }
            | IF '('condition')' block condtional_stmt {
                 if (compile_mode) {
                    // El árbol de la condición está en la pila
                    ast_node* condition_node = pop_node();
                    // El árbol del 'else' o 'elseif' viene de $6
                    ast_node* else_node = $6;
                    // El árbol del bloque principal viene de $5
                    ast_node* body_node = $5;
                    
                    // Enlazamos el 'else' al 'body' para formar la cadena
                    body_node->right = else_node;
                    
                    // Creamos el nodo IfStatement final
                    $$ = create_node("IfStatement", NULL, condition_node, body_node);
                    generate_ast_file($$);

                 }else{
                //printf("%s\n",conditions[0]);
                char *comparison_str = strdup($3); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               // printf("%s\n",$3);
                $$ = create_node("if_Condition",result,$5,$6); generate_ast_file($$);
                free(comparison_str);
                }
            }
            | IF '('condition')' COLON block condtional_stmt COLON {
             if (compile_mode) {
                    // El árbol de la condición está en la pila
                    ast_node* condition_node = pop_node();
                    // El árbol del 'else' o 'elseif' viene de $6
                    ast_node* else_node = $7;
                    // El árbol del bloque principal viene de $5
                    ast_node* body_node = $6;
                    
                    // Enlazamos el 'else' al 'body' para formar la cadena
                    body_node->right = else_node;
                    
                    // Creamos el nodo IfStatement final
                    $$ = create_node("IfStatement", NULL, condition_node, body_node);
                    generate_ast_file($$);

                 }else{
                //printf("%s\n",conditions[0]);
                char *comparison_str = strdup($3); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               // printf("%s\n",$3);
                $$ = create_node("if_Condition",result,$6,$7); generate_ast_file($$);
                free(comparison_str);
                }
            }
            | IF '('condition')'  block ELSE_IF '('condition')' block %prec IFX  {
                  if (compile_mode) {
             // 1. Sacamos los nodos de la pila (el último en entrar es el primero en salir)
                   ast_node* else_if_condition_node = pop_node(); // Condición del ELSE_IF ($8)
                   ast_node* if_condition_node = pop_node();      // Condición del IF ($3)

             // 2. Obtenemos los nodos de los bloques de código
                    ast_node* if_body_node = $5;
                    ast_node* else_if_body_node = $10;

                    // 3. Creamos el nodo anidado para la parte "else if".
                   //    Lo tratamos como un IfStatement completo en sí mismo.
                   ast_node* else_if_statement_node = create_node("IfStatement", NULL, else_if_condition_node, else_if_body_node);

                    // 4. Siguiendo tu patrón, enlazamos la rama "else" al hijo derecho del bloque principal.
                    if_body_node->right = else_if_statement_node;

                  // 5. Creamos el nodo IfStatement principal
                      $$ = create_node("IfStatement", NULL, if_condition_node, if_body_node);
                     generate_ast_file($$);
                  }else{  
                   char *if_comparison_str = strdup($3);
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup($8);
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                $$ = create_node("if_Condition",if_result,$5,create_node("ElseIf", elseif_result, $10, NULL)); generate_ast_file($$);
              }
            }
            | IF '('condition')'  COLON block ELSE_IF '('condition')' COLON block %prec IFX{
                  if (compile_mode) {
             // 1. Sacamos los nodos de la pila (el último en entrar es el primero en salir)
                   ast_node* else_if_condition_node = pop_node(); // Condición del ELSE_IF ($9)
                   ast_node* if_condition_node = pop_node();      // Condición del IF ($3)

             // 2. Obtenemos los nodos de los bloques de código
                    ast_node* if_body_node = $6;
                    ast_node* else_if_body_node = $12;

                    // 3. Creamos el nodo anidado para la parte "else if".
                   //    Lo tratamos como un IfStatement completo en sí mismo.
                   ast_node* else_if_statement_node = create_node("IfStatement", NULL, else_if_condition_node, else_if_body_node);

                    // 4. Siguiendo tu patrón, enlazamos la rama "else" al hijo derecho del bloque principal.
                    if_body_node->right = else_if_statement_node;

                  // 5. Creamos el nodo IfStatement principal
                      $$ = create_node("IfStatement", NULL, if_condition_node, if_body_node);
                     generate_ast_file($$);
                  }else{
                 char *if_comparison_str = strdup($3);
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup($9);
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                $$ = create_node("if_Condition",if_comparison_str,$6,create_node("ElseIf", elseif_result, $12, NULL)); generate_ast_file($$);
            }
            }
            | IF '('condition')'  block ELSE_IF '('condition')' block  condtional_stmt {
                   if (compile_mode) {
                     // 1. Sacamos los nodos de la pila en orden inverso
                       ast_node* else_if_cond_node = pop_node(); // Condición del ELSE_IF ($8)
                       ast_node* if_cond_node = pop_node();      // Condición del IF ($3)

                       // 2. Obtenemos los nodos de los bloques
                       ast_node* if_body_node = $5;
                       ast_node* else_if_body_node = $10;
                      ast_node* final_else_node = $11; // Este es el 'condtional_stmt' (ElseStatement)

                     // 3. Construimos la cadena de adentro hacia afuera:
                    //    Primero, enlazamos el 'else' final al bloque del 'else if'
                    else_if_body_node->right = final_else_node;
    
                    // 4. Creamos el nodo para el 'else if' completo
                     ast_node* else_if_statement = create_node("ElseIfStatement", NULL, else_if_cond_node, else_if_body_node);

                    // 5. Enlazamos la cadena del 'else if' al bloque del 'if' principal
                   if_body_node->right = else_if_statement;
 
                   // 6. Creamos el nodo 'if' principal
                   $$ = create_node("IfStatement", NULL, if_cond_node, if_body_node);
                   generate_ast_file($$);
                  }else{
                   char *if_comparison_str = strdup($3);
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup($8);
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                $$ = create_node("if_Condition",if_comparison_str,$5,create_node("ElseIf", elseif_result, $10, $11)); generate_ast_file($$);
                }
            }
            | IF '('condition')'  COLON block ELSE_IF '('condition')' COLON block  condtional_stmt {
                    if (compile_mode) {
                     // 1. Sacamos los nodos de la pila en orden inverso
                       ast_node* else_if_cond_node = pop_node(); // Condición del ELSE_IF ($9)
                       ast_node* if_cond_node = pop_node();      // Condición del IF ($3)

                       // 2. Obtenemos los nodos de los bloques
                       ast_node* if_body_node = $6;
                       ast_node* else_if_body_node = $12;
                      ast_node* final_else_node = $13; // Este es el 'condtional_stmt' (ElseStatement)

                     // 3. Construimos la cadena de adentro hacia afuera:
                    //    Primero, enlazamos el 'else' final al bloque del 'else if'
                    else_if_body_node->right = final_else_node;
    
                    // 4. Creamos el nodo para el 'else if' completo
                     ast_node* else_if_statement = create_node("ElseIfStatement", NULL, else_if_cond_node, else_if_body_node);

                    // 5. Enlazamos la cadena del 'else if' al bloque del 'if' principal
                   if_body_node->right = else_if_statement;
 
                   // 6. Creamos el nodo 'if' principal
                   $$ = create_node("IfStatement", NULL, if_cond_node, if_body_node);
                   generate_ast_file($$);
                  }else{
                    char *if_comparison_str = strdup($3);
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup($9);
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                $$ = create_node("if_Condition",if_comparison_str,$6,create_node("ElseIf", elseif_result, $12, $13)); generate_ast_file($$);
            }
            }
            ;

condtional_stmt:ELSE block { 
                 if(compile_mode) {
                       $$ = create_node("ElseStatement", NULL, $2, NULL);
                   } else {
                       $$ = create_node("Else", NULL, $2, NULL);
                   }
                   
               }
               | ELSE COLON block  { 
                if(compile_mode) {
                       $$ = create_node("ElseStatement", NULL, $3, NULL);
                   } else {
                       $$ = create_node("Else", NULL, $3, NULL);
                   } 
                }
               ;   
switch_block: rlrace { enter_scope(); } case_list rbrace { exit_scope(); } { $$ = create_node("Block", "BlockStart", $3, create_node("Block", "BlockEnd", NULL, NULL));}
            | INDENT { enter_scope(); } case_list DEDENT { exit_scope(); }  { $$ = create_node("Block", "BlockStart", $3, create_node("Block", "BlockEnd", NULL, NULL));}

switch_cases: SWITCH '(' variable ')' switch_block{
             // $3 es la expresión a evaluar (ej. 'dia')
             //  $6 es la lista de todos los nodos de los casos
            $$ = create_node("SwitchStatement", $3, $5, NULL);
            generate_ast_file($$);
            }
            
            ;

case_list: single_case { $$ = $1; }
         | case_list single_case {
        // Esta es la lógica correcta para construir una lista plana
        ast_node* list_head = $1;
        ast_node* current = list_head;

        // Avanzamos hasta el final de la lista de casos
        while (current->right != NULL) {
            current = current->right;
        }
        // Y enlazamos el nuevo caso al final
        current->right = $2;
        
        $$ = list_head; // Devolvemos el inicio de la lista
    }
    ;

single_case:
    CASE expr COLON  statements {
        // $2 es el valor del caso (ej. '1')
        // $5 es el bloque de sentencias para ese caso
        $$ = create_node("Case", $2, $4, NULL);
    }
    | DEFAULT COLON statements {
        // $4 es el bloque de sentencias para el caso default
        $$ = create_node("DefaultCase", "default", $3, NULL);
    }
    ;
function_decl: FUNCTION TEXT '('parameter_list ')' {
               add_or_find_function($2, "inferred"); // Marcamos el tipo como "inferido"
              $<sval>$ = current_function_name;
            // Si al final no hubo 'return', su tipo es 'void'   
             printf("Function: %s\n", lookup_function($2)->return_value);
             current_function_name = $2;
              
               add_or_find_function($2, "inferred"); // Marcamos la función como "inferida" inicialmente.
              //$$ = create_node("Function", $2, create_node("Parameters", $4, NULL, NULL), $6); generate_ast_file($$);
               } block {   
                 enter_scope();
                FunctionSymbol* func = lookup_function(current_function_name);
                 parse_and_store_parameters(func, $4);
                 for (int i = 0; i < func->param_count; i++) {
                 declare_var(func->params[i]->name, "NULL", func->params[i]->type,false,NULL);
                 printf("Parameter: %s, Type: %s\n", func->params[i]->name, func->params[i]->type);
               }
               // 3. Si después de analizar el bloque, el tipo sigue siendo "inferido",
               //    significa que no hubo sentencia 'return', por lo tanto, es 'void'.
               if (func && strcmp(func->return_type, "inferred") == 0) {
                 free(func->return_type);
                 func->return_type = "void";
               }
                $$ = create_node("Function", $2, create_node("Parameters", $4, NULL, NULL), $7); generate_ast_file($$);
    //          $$ = create_node("Function", $3, create_node("Parameters", $5, NULL, create_node("Type", $1, NULL, NULL)), $7); generate_ast_file($$);
               current_function_name = $<sval>6;
               exit_scope();
             }
                
             | FUNC TEXT '('parameter_list')'{
              add_or_find_function($2, "inferred"); // Marcamos el tipo como "inferido"
               $<sval>$ = current_function_name;
              // Si al final no hubo 'return', su tipo es 'void'   
              // printf("Function: %s\n", lookup_function($2)->return_value);
    
             current_function_name = $2;
               add_or_find_function($2, "inferred"); // Marcamos la función como "inferida" inicialmente.
               } block {
                
                FunctionSymbol* func = lookup_function(current_function_name);
                parse_and_store_parameters(func, $4);
                for (int i = 0; i < func->param_count; i++) {
                declare_var(func->params[i]->name, "NULL", func->params[i]->type,false,NULL);
                }
               // 3. Si después de analizar el bloque, el tipo sigue siendo "inferido",
               //    significa que no hubo sentencia 'return', por lo tanto, es 'void'.
               if (func && strcmp(func->return_type, "inferred") == 0) {
                 free(func->return_type);
                 func->return_type = "void";
               }
                $$ = create_node("Function", $2, create_node("Parameters", $4, NULL, NULL), $7); generate_ast_file($$);
                current_function_name = $<sval>6;
               }
                
             | types FUNCTION TEXT '('parameter_list')' {
                // Misma lógica de contexto para funciones con tipo explícito.
                $<sval>$ = current_function_name; // 1. Guardar contexto anterior.
                current_function_name = $3;      // 2. Establecer contexto actual.
                add_or_find_function($3, $1);    //    Se añade con su tipo explícito.
             } block {
                FunctionSymbol* func = lookup_function($3);
                // Aquí podrías añadir una validación para asegurar que hubo un return si el tipo no es void.
                 for (int i = 0; i < func->param_count; i++) {
                 declare_var(func->params[i]->name, "NULL", func->params[i]->type,false,NULL);
                 
                 }
                // 3. Crear nodo AST.
                $$ = create_node("Function", $3, create_node("Parameters", $5, NULL, create_node("ExplicitType", $1, NULL, NULL)), $8);
                generate_ast_file($$);

                // 4. Restaurar contexto anterior.
                current_function_name = $<sval>7;
             }
             
            ;
function_call: TEXT'('')' { 
                validate_function_call($1, "");
              $$ = create_node("FunctionCall",$1,create_node("Paramenters",NULL,NULL,NULL),NULL); generate_ast_file($$)
             }  
             | TEXT '('argument_list')' {
                validate_function_call($1, $3);
              $$ = create_node("FunctionCall",$1,create_node("Paramenters",$3,NULL,NULL),NULL); generate_ast_file($$)
             }
            ;                
parameter_list:  /*nada*/ { $$ = NULL; }
    | param_decl { $$ = $1; }
    | parameter_list COM param_decl  {$$ = concat_strings($1,concat_strings(",",concat_strings(" ", $3))); }
param_decl: types TEXT { $$ = concat_strings($1,concat_strings(" ",$2)); }
          | TEXT      { $$ = $1; }
;

 
    ;
argument_list:  /*nada*/ { $$ = NULL; }
            | expr { $$ = $1; }
            | argument_list COM expr { concat_strings($1,concat_strings(",",concat_strings(" ",$3))); } 
            ;
types: TINT { $$ = "int"; }
    | TFLOAT { $$ = "float"; }
    | TSTRING { $$ = "string"; }
    | TBOOL { $$ = "bool"; }
    | TVOID { $$ = "void"; }
     ;    
statements: statements statement {  if (strcmp($1->type, "Statements") == 0) {
                                            // Si ya es "Statements", solo agregamos el nuevo statement
                                            ast_node* current = $1;
                                            while (current->right != NULL) {
                                                current = current->right;
                                            }
                                            current->right = $2;
                                            $$ = $1;
                                         } else {
                                            // Si no es "Statements", creamos el nodo
                                            $$ = create_node("Statements", NULL, $1, $2);
                                         }
                                        }
    | statement {$$ = $1}
    ;  
variable: TEXT {  
     if (compile_mode) {
            char* var_type = get_type($1) ? get_type($1) : "NULL";
            ast_node* type_node = create_node("Type", var_type, NULL, NULL);
            ast_node* var_ref_node = create_node("VariableReference", $1, type_node, NULL);
            push_node(var_ref_node);
        }else{ 
            // Crear el nodo para una variable
             // 1. Buscar el símbolo en la tabla de scopes
       symbol* s = find_variable($1);

    // 2. Si no se encuentra, es un error semántico
     if (!s) {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, $1);
        yyerror(error_msg);
        exit(1); // Detener el análisis
     }

         $$ = $1;  }     
}
    
     ;
      
expr: term 
    | arith_expr { $$ = $1; } 
     | expr DOT expr { 
          //  char* val1 = get_var($1) ? $1 : get_var($1);
           //char* val2 = get_var($3) ? $3 : get_var($3);

        $$ = concat_con_espacio($1,$3); 
     } 
     | eqt
     | comparison
     ;
     
paren_left: '(' { paren_num++; printf("paren abierta\n");
          expression_op[expression_num].op = "(";
          expression_op[expression_num].num = 2; // 2 = Inicio de Paréntesis
          expression_num++;

          }
paren_right: ')' { paren_num--; printf("paren cerrado\n"); 
              expression_op[expression_num].op = ")";
              expression_op[expression_num].num = 3; // 3 = Fin de Paréntesis
              expression_num++;
           }             
     ;
dict_body:      /* empty */ { 
                    longitud = 0; 
                    $$ = ""; 
                }
                |   pair_list   { 
                    $$ = $1; // Simplemente pasa el resultado de la lista de pares.
                }
;

// 2. La lista de pares: esta regla define la lista separada por comas.
pair_list:      key_value_pair { 
                    longitud = 1; 
                    $$ = $1; 
                }
                |   pair_list COM key_value_pair {
                    // Concatenación más segura usando malloc para evitar desbordamientos
                    size_t len1 = strlen($1);
                    size_t len2 = strlen($3);
                    char* result = malloc(len1 + 1 + len2 + 1); // str1 + coma + str2 + null
                    if (result) {
                        strcpy(result, $1);
                        strcat(result, ",");
                        strcat(result, $3);
                    }
                    $$ = result;
                    longitud++;
                }
;

// 3. El par clave-valor individual (esta regla no cambia).
key_value_pair: STRING COLON list_item_list {
    char buffer[1024];
    sprintf(buffer, "%s:%s", add_quotes($1), $3);
    $$ = strdup(buffer);
}  
arith_expr: paren_left expr paren_right {  $$ = $2; }
          | expr PLUS expr  {         

            concat_op = op_concat($1,'+',$3);
            valid = valid_expression(concat_op);
            char* val1 = get_var($1) ? get_var($1) : $1;
            char* val2 = get_var($3) ? get_var($3) : $3;
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            printf("valid: %d\n",valid);
           //printf("expr1S: %s, expr2S: : %s\n", $1, $3);
            if(valid==1){ 
              expression_op[expression_num].op = "+";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;         
              printf("val1: %s, val2: %s\n", val1, val2);
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             $$ = do_op_float(val1,'+',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             $$ = do_op(val1,'+',val2);
            }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '+' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
            exit(1); // Detener el análisis
             
            }
          }
               if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* op_node = create_node("BinaryExpression", "+", left, right);
                push_node(op_node);
            }
        }
          | expr MINUS expr { 
            concat_op = op_concat($1,'-',$3);
            valid = valid_expression(concat_op);
            //printf("valid: %d\n",valid);
            char* val1 = get_var($1) ? get_var($1) : $1;
            char* val2 = get_var($3) ? get_var($3) : $3;
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            if(valid==1){ 
             expression_op[expression_num].op = "-";
             expression_op[expression_num].num = 1; // 1 = Operador
             expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             $$ = do_op_float($1,'-',$3);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             $$ = do_op($1,'-',$3);
              }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '-' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
             exit(1); // Detener el análisis
            }
            }
           if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* op_node = create_node("BinaryExpression", "-", left, right);
                push_node(op_node);
            }
          }
          | expr TIMES expr {

            concat_op = op_concat($1,'*',$3);
            valid = valid_expression(concat_op);
            char* val1 = get_var($1) ? get_var($1) : $1;
            char* val2 = get_var($3) ? get_var($3) : $3;
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            //printf("valid: %d\n",valid);
           // printf("Texpr1: %s, Texpr2: : %s\n", $1, $3);
            if(valid==1){ 
              expression_op[expression_num].op = "*";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             $$ = do_op_float($1,'*',$3);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             $$ = do_op($1,'*',$3);
              }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '*' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
             exit(1); // Detener el análisis
            }
            }
            if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* op_node = create_node("BinaryExpression", "*", left, right);
                push_node(op_node);
            }
           }
          | expr DIVIDE expr { 
            concat_op = op_concat($1,'/',$3);
            valid = valid_expression(concat_op);
            char* val1 = get_var($1) ? get_var($1) : $1;
            char* val2 = get_var($3) ? get_var($3) : $3;
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            if(valid==1){ 
              expression_op[expression_num].op = "/";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             $$ = do_division($1,$3);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             $$ = do_division($1,$3);
            }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '/' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
             exit(1); // Detener el análisis
              }
             }
            if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* op_node = create_node("BinaryExpression", "/", left, right);
                push_node(op_node);
            }
            }
             | expr MOD expr {
                concat_op = op_concat($1, '%', $3);
                valid = valid_expression(concat_op);
                
                char* val1 = get_var($1) ? get_var($1) : $1;
                char* val2 = get_var($3) ? get_var($3) : $3;
                char* type1 = determine_type(val1);
                char* type2 = determine_type(val2);
                
                if (valid == 1) {
                    expression_op[expression_num].op = "%";
                    expression_op[expression_num].num = 1; // 1 = Operador
                    expression_num++;
                }

                // El módulo solo funciona con enteros
                if (strcmp(type1, "int") == 0 && strcmp(type2, "int") == 0) {
                    $$ = do_mod(val1, val2);
                } else {
                    char error_msg[256];
                    sprintf(error_msg, "Error semantico en linea %d: La operacion '%' solo esta soportada entre enteros (int), no entre '%s' y '%s'.", yylineno, type1, type2);
                    yyerror(error_msg);
                    exit(1); // Terminar el análisis si hay un error
                   // $$ = "0"; // Valor por defecto para que no se rompa el parser
                }
               if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* op_node = create_node("BinaryExpression", "/", left, right);
                push_node(op_node);
            }
            }
             ;

;
array_indexer: NUMBER   { $$ = to_string($1); }
             | range    { $$ = $1; }
             | variable { $$ = $1; }
             | STRING   { $$ = $1; } // Aseguramos que las claves de diccionario sean sin comillas
             | array_indexer COLON array_indexer { // Caso recursivo para el acceso profundo
                   char buffer[1024];
                   sprintf(buffer, "%s:%s", $1, $3);
                   $$ = strdup(buffer);
               }

             ;
bool: TRUE { $$ = "True"; }
    | FALSE { $$ = "False"; }     

    ;    
term: NUMBER { $$ = to_string($1);  
        if (compile_mode) {

            ast_node* type_node = create_node("Type", "int", NULL, NULL);
            ast_node* literal_node = create_node("Literal", to_string($1), type_node, NULL);
            push_node(literal_node);
        }
       expression_op[expression_num].op = strdup($$);
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    }
    | STRING { $$ = add_quotes($1);
     if (compile_mode) {
            ast_node* type_node = create_node("Type", "String", NULL, NULL);
            ast_node* literal_node = create_node("Literal", add_quotes($1), type_node, NULL);
            push_node(literal_node);
        }

    }
    | DECIMAL { $$ = floatToString($1); 
        expression_op[expression_num].op = strdup($$);
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
         if (compile_mode) {
            ast_node* type_node = create_node("Type", "float", NULL, NULL);
            ast_node* literal_node = create_node("Literal", floatToString($1), type_node, NULL);
            push_node(literal_node);
        }
    } 
     | variable LSQUARE array_indexer RSQUARE {
          // 1. Llamamos a nuestra nueva función orquestadora
          char* val1 = get_var($3) ? get_var($3) : $3;
    $$ = access_collection_element($1, val1);
    
    // 2. Manejamos el caso en que no se encuentre el elemento
    if ($$ == NULL) {
        char error_msg[256];
        sprintf(error_msg, "Error en linea %d: La clave o indice '%s' no se encontro o es invalido para '%s'.", yylineno, $3, $1);
        yyerror(error_msg);
        exit(1); // Detener el análisis
    }
  }
    | expr QUESTION_MARK expr COLON expr {
          // Resolvemos el valor de la condición
          char* condition_val = get_var($1) ? get_var($1) : $1;
          
          if (is_truthy(condition_val)) {
              // Si la condición es verdadera, el resultado es la expresión de la izquierda ($3)
              $$ = $3;
          } else {
              // Si la condición es falsa, el resultado es la expresión de la derecha ($5)
              $$ = $5;
          }
      }

    | STRING_WITH_VARS { 
            // Se llama a la nueva función en el momento correcto
           char* final_string = process_string($1);
           $$ = add_quotes(final_string);
          free(final_string); 
          ast_node* n = create_node("StringLiteral", add_quotes($1), NULL, NULL);
          push_node(n);
       // $$ = add_quotes(removeParentheses($1));
        }
    | variable 
    | bool {
         if (compile_mode) {
            ast_node* type_node = create_node("Type", "Bool", NULL, NULL);
            ast_node* literal_node = create_node("Literal", $1, type_node, NULL);
            push_node(literal_node);
        }
    }

    | TEXT '('argument_list')' { 
      FunctionSymbol* func = lookup_function($1);
              validate_function_call($1, $3);
            // TU LÓGICA DE INFERENCIA YA FUNCIONA AQUÍ:
            // Si una función no tuvo 'return', su func->return_type ya habrá sido
            // cambiado a "void" al final de su declaración.

            // 1. Verificamos el tipo final de la función.
            if (strcmp(func->return_type, "void") == 0) {
                // Si es void, devolvemos el marcador especial.
                $$ = VOID_RESULT_MARKER;
            } else {
                // 2. Si NO es void, aplicamos la lógica de retorno normal.
                if (func->return_value != NULL) {
                    // Tenía un 'return', usamos su valor.
                    $$ = strdup(func->return_value);
                } else {
                    // No tenía 'return' pero es tipada, usamos el default.
                    if (strcmp(func->return_type, "int") == 0) $$ = "0";
                    else if (strcmp(func->return_type, "float") == 0) $$ = "0.0";
                    else if (strcmp(func->return_type, "string") == 0) $$ = "\"\"";
                    else if (strcmp(func->return_type, "bool") == 0) $$ = "False";
                    else $$ = "NULL"; // Fallback
                }
            }
        //} 
    }
    ;
for_condition: range {$$ = $$;}
             | expr IN expr { 
                char *temp_str = concatenateComparison($1, " in ", $3); 
                $$ = concatenateComparison("",",",temp_str);
             }
             | variable {
                // Verificar si la variable existe
                if (get_var($1)) {
                    printf("type es: %s\n", get_type($1));
                    if(strcmp(get_type($1),"Array") == 0 || strcmp(get_type($1),"Range") == 0){ 
                        printf("Variable: %s\n", get_var($1)); 
                     $$ = $1;
                     }else{
                        $$ = NULL;
                     }
                }else{
                    fprintf(stderr, "Error: Variable '%s' no definida.\n", $1);
                    $$ = "NULL"; // Manejo de error, asignar un valor por defecto
                }    
             }
  
logicals: AND {$$ ="&&";}
        | OR {$$ = "||";}    
condition: comparison
         | expr IN expr { char *temp_str = concatenateComparison($1, " in ", $3); 
          $$ = concatenateComparison("",",",temp_str);}
         
         | condition logicals condition { 
             // Concatenamos las comparaciones y resultados
          if (compile_mode) {
                ast_node* right_node = pop_node();
                ast_node* left_node = pop_node();
                // Usamos el valor de $2 ("&&" o "||") para el operador
                ast_node* logical_node = create_node("LogicalExpression", $2, left_node, right_node);
                push_node(logical_node);
             }else{
    char *left = strdup($1);  // Comparación izquierda
    char *right = strdup($3); // Comparación derecha
    
    // Evaluamos la condición lógica de las comparaciones
    char *conditions = concatenateComparison(left, $2, right);  // Concatenamos las comparaciones con el operador lógico
    char * result = process_conditions(conditions);
    // Evaluamos el resultado lógico de todas las condiciones
    char *logical_result = evaluate_logical_conditions(conditions);
   // printf("%s\n",result);
    // Concatenamos la comparación con el resultado lógico final
    $$ = concatenateComparison(result, ",", logical_result);
    }
            }
comparison:  expr EQUALC expr {
              if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "==", left_mode, right_mode);
                push_node(op_node);
             }else{
            comparison = concatenateComparison($1,"==", $3);     
             if(strcmp($1, $3) == 0){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); } 
          }
          }
          | expr UNEQUAL expr {
             if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "!=", left_mode, right_mode); //generate_ast_file(op_node);
                push_node(op_node);
             }else{
            comparison = concatenateComparison($1,"!=", $3);
            if(atoi($1)  != atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }
             }
          }
          | expr GREATERTHAN expr {
                  if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", ">", left_mode, right_mode); //generate_ast_file(op_node);
                push_node(op_node);
                
             }else{

              comparison = concatenateComparison($1,">", $3);
              if(atoi($1) > atoi($3)){ $$ = concatenateComparison("True",",",comparison);}else{ $$ = concatenateComparison("False",",",comparison); }
             }
         }
          | expr LESSTHAN expr {
             if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "<", left_mode, right_mode);
                push_node(op_node);
             }else{
              comparison = concatenateComparison($1,"<", $3);
              if(atoi($1)  < atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }
             }
         } 
          | expr GREATERTHAN_EQUAL expr {
             if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", ">=", left_mode, right_mode);
                push_node(op_node);
             }else{
              comparison = concatenateComparison($1,">=", $3);
              if(atoi($1)  >= atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }      
             }
         }
          | expr LESSTHAN_EQUAL expr {
          if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "<=", left_mode, right_mode);
                push_node(op_node);
             }else{  
              comparison = concatenateComparison($1,"<=", $3);
              if(atoi($1)  <= atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }            
             }
         }
          ;

 expr_list: list_item  { longitud = 1; $$ = $1; }
          | expr_list COM list_item  { 
           // Un array con múltiples elementos.
                char* tempList = concat_strings($1, ",");
                $$ = concat_strings(tempList, $3);
                free(tempList); // Liberar memoria intermedia.
                longitud++;
         // printf("exprlist: %s\n",$$);
          }
          
             
         /* | LSQUARE expr COM expr RSQUARE {
              $$ = concat_strings($2, ",");
              $$ = concat_strings($$, $4);
              longitud++;
              printf("exprlistest: %s\n",$$); 
           }*/
              
             
 /*
array: VAR TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE expr RSQUARE { 
}
| VAR TEXT SQUARES_L_R EQUAL LSQUARE expr_list_arr RSQUARE {    
}
| VAR TEXT LSQUARE NUMBER RSQUARE {
}
|VAR TEXT LSQUARE NUMBER RSQUARE EQUAL types LSQUARE expr_list_arr RSQUARE {
}
| TEXT LSQUARE NUMBER RSQUARE INSERTVALUE expr ')' /*LSQUARE NUMBER RSQUARE EQUAL expr*//*{
}
| TEXT SQUARES_L_R EQUAL expr{
}
| TEXT SQUARES_L_R INSERTVALUE expr ')' {
}
 */
  
eqt: EQUATION '(' STRING ')' {
  }

%%
int main(int argc, char **argv) {
    int use_indent = 0; 
    load_default_mode(&use_indent);

    bool set_as_default = false;
    char* input_file = NULL;
    char* output_file_arg = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-ident") == 0 || strcmp(argv[i], "-i") == 0) {
            use_indent = 1;
        } else if (strcmp(argv[i], "-block") == 0 || strcmp(argv[i], "-b") == 0) {
            use_indent = 0;
        } else if (strcmp(argv[i], "-default") == 0 || strcmp(argv[i], "-d") == 0) {
            set_as_default = true;
        } else {
            if (input_file == NULL) input_file = argv[i];
            else if (output_file_arg == NULL) output_file_arg = argv[i];
        }
        if (strcmp(argv[i], "-compile") == 0 || strcmp(argv[i], "-c") == 0) {
            compile_mode = 1; // Activamos el modo compilador
        } 
    }

    if (input_file == NULL || output_file_arg == NULL) {
        fprintf(stderr, "Uso: %s [flags] <archivo_entrada> <archivo_salida_ast>\n", argv[0]);
        return 1;
    }

    if (set_as_default) {
        save_default_mode(use_indent);
    }

    extern FILE *yyin;
    yyin = fopen(input_file, "r");
    if (!yyin) {
        fprintf(stderr, "Error: No se pudo abrir el archivo de entrada %s\n", input_file);
        return 1;
    }

    // --- MODIFICACIÓN CLAVE ---
    // Asignamos la ruta de salida a nuestra variable global
    g_output_path = output_file_arg;

    FILE* outFile = fopen(g_output_path, "w"); // "w" para limpiar el archivo al inicio
    if (!outFile) {
        fprintf(stderr, "Error: No se pudo abrir el archivo de salida %s\n", g_output_path);
        fclose(yyin);
        return 1;
    }
    fprintf(outFile, "Program\n");
    fclose(outFile); 

    printf("Modo de analisis para esta sesion: %s\n", use_indent ? "Indentacion" : "Bloques con {}");
     printf("Modo de generacion de AST para esta sesion: %s\n", compile_mode ? "Compilador" : "Interprete");
    init_scope_manager();
    yyparse(); // Ya no se le pasa nada aquí

    printf("✅ AST generado en: %s\n", g_output_path);
    fclose(yyin);
 
    return 0;
}