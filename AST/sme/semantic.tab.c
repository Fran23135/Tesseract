
/* A Bison parser, made by GNU Bison 2.4.1.  */

/* Skeleton implementation for Bison's Yacc-like parsers in C
   
      Copyright (C) 1984, 1989, 1990, 2000, 2001, 2002, 2003, 2004, 2005, 2006
   Free Software Foundation, Inc.
   
   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.
   
   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* C LALR(1) parser skeleton written by Richard Stallman, by
   simplifying the original so-called "semantic" parser.  */

/* All symbols defined below should begin with yy or YY, to avoid
   infringing on user name space.  This should be done even for local
   variables, as they might otherwise be expanded by user macros.
   There are some unavoidable exceptions within include files to
   define necessary library symbols; they are noted "INFRINGES ON
   USER NAME SPACE" below.  */

/* Identify Bison output.  */
#define YYBISON 1

/* Bison version.  */
#define YYBISON_VERSION "2.4.1"

/* Skeleton name.  */
#define YYSKELETON_NAME "yacc.c"

/* Pure parsers.  */
#define YYPURE 0

/* Push parsers.  */
#define YYPUSH 0

/* Pull parsers.  */
#define YYPULL 1

/* Using locations.  */
#define YYLSP_NEEDED 0



/* Copy the first part of user declarations.  */

/* Line 189 of yacc.c  */
#line 1 "semantic.y"

    
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



/* Line 189 of yacc.c  */
#line 2200 "semantic.tab.c"

/* Enabling traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif

/* Enabling verbose error messages.  */
#ifdef YYERROR_VERBOSE
# undef YYERROR_VERBOSE
# define YYERROR_VERBOSE 1
#else
# define YYERROR_VERBOSE 0
#endif

/* Enabling the token table.  */
#ifndef YYTOKEN_TABLE
# define YYTOKEN_TABLE 0
#endif


/* Tokens.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
   /* Put the tokens into the symbol table, so that GDB and other debuggers
      know about them.  */
   enum yytokentype {
     TEXT = 258,
     STRING = 259,
     STRING_WITH_VARS = 260,
     NUMBER = 261,
     INCREMENT = 262,
     DECREMENT = 263,
     PRINT = 264,
     VAR = 265,
     PLUS = 266,
     MINUS = 267,
     TIMES = 268,
     DIVIDE = 269,
     EQUAL = 270,
     SEMICOLON = 271,
     READ = 272,
     INSERTVALUE = 273,
     COLON = 274,
     DOT = 275,
     COM = 276,
     SHARP = 277,
     LSQUARE = 278,
     RSQUARE = 279,
     SQUARES_L_R = 280,
     ELSE = 281,
     ELSE_IF = 282,
     RANGE_SEMI_OPEN = 283,
     IFX = 284,
     EQUALC = 285,
     UNEQUAL = 286,
     GREATERTHAN = 287,
     LESSTHAN = 288,
     GREATERTHAN_EQUAL = 289,
     LESSTHAN_EQUAL = 290,
     TRUE = 291,
     FALSE = 292,
     BOOL = 293,
     INDENT = 294,
     DEDENT = 295,
     STRUCT = 296,
     TSTRING = 297,
     TINT = 298,
     TFLOAT = 299,
     TBOOL = 300,
     TVOID = 301,
     FOR = 302,
     IN = 303,
     RANGE = 304,
     MAIN = 305,
     DOTYPE = 306,
     APPEND = 307,
     LENGHT = 308,
     WHILE = 309,
     IF = 310,
     PERFORM = 311,
     BREAK = 312,
     RETURN = 313,
     MOD = 314,
     FUNCTION = 315,
     FUNC = 316,
     PARENS = 317,
     QUESTION_MARK = 318,
     SWITCH = 319,
     CASE = 320,
     DEFAULT = 321,
     startRace = 322,
     endRace = 323,
     OR = 324,
     AND = 325,
     DECIMAL = 326,
     NEWLINE = 327,
     IM = 328,
     IM_Math = 329,
     PI = 330,
     EQUATION = 331
   };
#endif



#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
typedef union YYSTYPE
{

/* Line 214 of yacc.c  */
#line 2126 "semantic.y"

    int ival;
    char *sval;
    char **arrval;
    float fval;
    struct ast_node* node;



/* Line 214 of yacc.c  */
#line 2322 "semantic.tab.c"
} YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define yystype YYSTYPE /* obsolescent; will be withdrawn */
# define YYSTYPE_IS_DECLARED 1
#endif


/* Copy the second part of user declarations.  */


/* Line 264 of yacc.c  */
#line 2334 "semantic.tab.c"

#ifdef short
# undef short
#endif

#ifdef YYTYPE_UINT8
typedef YYTYPE_UINT8 yytype_uint8;
#else
typedef unsigned char yytype_uint8;
#endif

#ifdef YYTYPE_INT8
typedef YYTYPE_INT8 yytype_int8;
#elif (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
typedef signed char yytype_int8;
#else
typedef short int yytype_int8;
#endif

#ifdef YYTYPE_UINT16
typedef YYTYPE_UINT16 yytype_uint16;
#else
typedef unsigned short int yytype_uint16;
#endif

#ifdef YYTYPE_INT16
typedef YYTYPE_INT16 yytype_int16;
#else
typedef short int yytype_int16;
#endif

#ifndef YYSIZE_T
# ifdef __SIZE_TYPE__
#  define YYSIZE_T __SIZE_TYPE__
# elif defined size_t
#  define YYSIZE_T size_t
# elif ! defined YYSIZE_T && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
#  include <stddef.h> /* INFRINGES ON USER NAME SPACE */
#  define YYSIZE_T size_t
# else
#  define YYSIZE_T unsigned int
# endif
#endif

#define YYSIZE_MAXIMUM ((YYSIZE_T) -1)

#ifndef YY_
# if YYENABLE_NLS
#  if ENABLE_NLS
#   include <libintl.h> /* INFRINGES ON USER NAME SPACE */
#   define YY_(msgid) dgettext ("bison-runtime", msgid)
#  endif
# endif
# ifndef YY_
#  define YY_(msgid) msgid
# endif
#endif

/* Suppress unused-variable warnings by "using" E.  */
#if ! defined lint || defined __GNUC__
# define YYUSE(e) ((void) (e))
#else
# define YYUSE(e) /* empty */
#endif

/* Identity function, used to suppress warnings about constant conditions.  */
#ifndef lint
# define YYID(n) (n)
#else
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static int
YYID (int yyi)
#else
static int
YYID (yyi)
    int yyi;
#endif
{
  return yyi;
}
#endif

#if ! defined yyoverflow || YYERROR_VERBOSE

/* The parser invokes alloca or malloc; define the necessary symbols.  */

# ifdef YYSTACK_USE_ALLOCA
#  if YYSTACK_USE_ALLOCA
#   ifdef __GNUC__
#    define YYSTACK_ALLOC __builtin_alloca
#   elif defined __BUILTIN_VA_ARG_INCR
#    include <alloca.h> /* INFRINGES ON USER NAME SPACE */
#   elif defined _AIX
#    define YYSTACK_ALLOC __alloca
#   elif defined _MSC_VER
#    include <malloc.h> /* INFRINGES ON USER NAME SPACE */
#    define alloca _alloca
#   else
#    define YYSTACK_ALLOC alloca
#    if ! defined _ALLOCA_H && ! defined _STDLIB_H && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
#     include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
#     ifndef _STDLIB_H
#      define _STDLIB_H 1
#     endif
#    endif
#   endif
#  endif
# endif

# ifdef YYSTACK_ALLOC
   /* Pacify GCC's `empty if-body' warning.  */
#  define YYSTACK_FREE(Ptr) do { /* empty */; } while (YYID (0))
#  ifndef YYSTACK_ALLOC_MAXIMUM
    /* The OS might guarantee only one guard page at the bottom of the stack,
       and a page size can be as small as 4096 bytes.  So we cannot safely
       invoke alloca (N) if N exceeds 4096.  Use a slightly smaller number
       to allow for a few compiler-allocated temporary stack slots.  */
#   define YYSTACK_ALLOC_MAXIMUM 4032 /* reasonable circa 2006 */
#  endif
# else
#  define YYSTACK_ALLOC YYMALLOC
#  define YYSTACK_FREE YYFREE
#  ifndef YYSTACK_ALLOC_MAXIMUM
#   define YYSTACK_ALLOC_MAXIMUM YYSIZE_MAXIMUM
#  endif
#  if (defined __cplusplus && ! defined _STDLIB_H \
       && ! ((defined YYMALLOC || defined malloc) \
	     && (defined YYFREE || defined free)))
#   include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
#   ifndef _STDLIB_H
#    define _STDLIB_H 1
#   endif
#  endif
#  ifndef YYMALLOC
#   define YYMALLOC malloc
#   if ! defined malloc && ! defined _STDLIB_H && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
void *malloc (YYSIZE_T); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
#  ifndef YYFREE
#   define YYFREE free
#   if ! defined free && ! defined _STDLIB_H && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
void free (void *); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
# endif
#endif /* ! defined yyoverflow || YYERROR_VERBOSE */


#if (! defined yyoverflow \
     && (! defined __cplusplus \
	 || (defined YYSTYPE_IS_TRIVIAL && YYSTYPE_IS_TRIVIAL)))

/* A type that is properly aligned for any stack member.  */
union yyalloc
{
  yytype_int16 yyss_alloc;
  YYSTYPE yyvs_alloc;
};

/* The size of the maximum gap between one aligned stack and the next.  */
# define YYSTACK_GAP_MAXIMUM (sizeof (union yyalloc) - 1)

/* The size of an array large to enough to hold all stacks, each with
   N elements.  */
# define YYSTACK_BYTES(N) \
     ((N) * (sizeof (yytype_int16) + sizeof (YYSTYPE)) \
      + YYSTACK_GAP_MAXIMUM)

/* Copy COUNT objects from FROM to TO.  The source and destination do
   not overlap.  */
# ifndef YYCOPY
#  if defined __GNUC__ && 1 < __GNUC__
#   define YYCOPY(To, From, Count) \
      __builtin_memcpy (To, From, (Count) * sizeof (*(From)))
#  else
#   define YYCOPY(To, From, Count)		\
      do					\
	{					\
	  YYSIZE_T yyi;				\
	  for (yyi = 0; yyi < (Count); yyi++)	\
	    (To)[yyi] = (From)[yyi];		\
	}					\
      while (YYID (0))
#  endif
# endif

/* Relocate STACK from its old location to the new one.  The
   local variables YYSIZE and YYSTACKSIZE give the old and new number of
   elements in the stack, and YYPTR gives the new location of the
   stack.  Advance YYPTR to a properly aligned location for the next
   stack.  */
# define YYSTACK_RELOCATE(Stack_alloc, Stack)				\
    do									\
      {									\
	YYSIZE_T yynewbytes;						\
	YYCOPY (&yyptr->Stack_alloc, Stack, yysize);			\
	Stack = &yyptr->Stack_alloc;					\
	yynewbytes = yystacksize * sizeof (*Stack) + YYSTACK_GAP_MAXIMUM; \
	yyptr += yynewbytes / sizeof (*yyptr);				\
      }									\
    while (YYID (0))

#endif

/* YYFINAL -- State number of the termination state.  */
#define YYFINAL  2
/* YYLAST -- Last index in YYTABLE.  */
#define YYLAST   862

/* YYNTOKENS -- Number of terminals.  */
#define YYNTOKENS  79
/* YYNNTS -- Number of nonterminals.  */
#define YYNNTS  64
/* YYNRULES -- Number of rules.  */
#define YYNRULES  171
/* YYNRULES -- Number of states.  */
#define YYNSTATES  339

/* YYTRANSLATE(YYLEX) -- Bison symbol number corresponding to YYLEX.  */
#define YYUNDEFTOK  2
#define YYMAXUTOK   331

#define YYTRANSLATE(YYX)						\
  ((unsigned int) (YYX) <= YYMAXUTOK ? yytranslate[YYX] : YYUNDEFTOK)

/* YYTRANSLATE[YYLEX] -- Bison symbol number corresponding to YYLEX.  */
static const yytype_uint8 yytranslate[] =
{
       0,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
      77,    78,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     1,     2,     3,     4,
       5,     6,     7,     8,     9,    10,    11,    12,    13,    14,
      15,    16,    17,    18,    19,    20,    21,    22,    23,    24,
      25,    26,    27,    28,    29,    30,    31,    32,    33,    34,
      35,    36,    37,    38,    39,    40,    41,    42,    43,    44,
      45,    46,    47,    48,    49,    50,    51,    52,    53,    54,
      55,    56,    57,    58,    59,    60,    61,    62,    63,    64,
      65,    66,    67,    68,    69,    70,    71,    72,    73,    74,
      75,    76
};

#if YYDEBUG
/* YYPRHS[YYN] -- Index of the first RHS symbol of rule number YYN in
   YYRHS.  */
static const yytype_uint16 yyprhs[] =
{
       0,     0,     3,     4,     7,     9,    11,    12,    15,    18,
      21,    23,    25,    27,    29,    31,    33,    35,    38,    41,
      46,    49,    52,    55,    58,    61,    66,    73,    79,    84,
      88,    91,    96,    98,   100,   102,   109,   117,   123,   130,
     137,   147,   154,   164,   170,   175,   179,   185,   187,   191,
     195,   200,   204,   206,   208,   212,   217,   221,   225,   229,
     231,   233,   235,   238,   239,   240,   246,   247,   248,   254,
     255,   263,   271,   277,   284,   291,   299,   305,   312,   319,
     328,   339,   352,   364,   378,   381,   385,   386,   387,   393,
     394,   395,   401,   407,   409,   412,   417,   421,   422,   430,
     431,   439,   440,   449,   453,   458,   459,   461,   465,   468,
     470,   471,   473,   477,   479,   481,   483,   485,   487,   490,
     492,   494,   496,   498,   502,   504,   506,   508,   510,   511,
     513,   515,   519,   523,   527,   531,   535,   539,   543,   547,
     549,   551,   553,   555,   559,   561,   563,   565,   567,   569,
     574,   580,   582,   584,   586,   591,   593,   597,   599,   601,
     603,   605,   609,   613,   617,   621,   625,   629,   633,   637,
     639,   643
};

/* YYRHS -- A `-1'-separated list of the rules' RHS.  */
static const yytype_int16 yyrhs[] =
{
      80,     0,    -1,    -1,    80,    82,    -1,    16,    -1,    72,
      -1,    -1,    83,    81,    -1,    85,    81,    -1,    91,    81,
      -1,   102,    -1,   116,    -1,   120,    -1,   104,    -1,   105,
      -1,   106,    -1,   113,    -1,    84,    81,    -1,    96,    81,
      -1,     9,    77,   127,    78,    -1,   126,     7,    -1,   126,
       8,    -1,     7,   126,    -1,     8,   126,    -1,    10,     3,
      -1,    10,     3,    15,   127,    -1,    10,     3,    15,    67,
     130,    68,    -1,     3,    15,    67,   130,    68,    -1,    10,
       3,    15,    93,    -1,     3,    15,   127,    -1,   124,     3,
      -1,   124,     3,    15,   127,    -1,    87,    -1,    88,    -1,
      86,    -1,    10,     3,    15,   128,    90,   129,    -1,    10,
       3,    15,   128,    90,    21,   129,    -1,     3,    15,   128,
      90,   129,    -1,     3,    15,   128,    90,    21,   129,    -1,
      10,     3,    15,    23,    90,    24,    -1,    10,     3,    23,
       6,    24,    15,    23,    90,    24,    -1,   124,     3,    15,
      23,    90,    24,    -1,   124,     3,    23,     6,    24,    15,
      23,    90,    24,    -1,   124,     3,    23,     6,    24,    -1,
     124,     3,    15,    25,    -1,     3,    15,    25,    -1,     3,
      15,    23,    90,    24,    -1,   127,    -1,    67,   130,    68,
      -1,   128,   141,   129,    -1,   128,   141,    21,   129,    -1,
      23,    90,    24,    -1,    25,    -1,    89,    -1,    90,    21,
      89,    -1,    17,    77,     3,    78,    -1,    10,     3,    48,
      -1,   127,    49,   127,    -1,   127,    28,   127,    -1,    67,
      -1,    68,    -1,    57,    -1,    58,   127,    -1,    -1,    -1,
      94,    98,   125,    95,    99,    -1,    -1,    -1,    39,   100,
     125,    40,   101,    -1,    -1,    47,    77,    92,   137,    78,
     103,    97,    -1,    47,    77,    92,   137,    78,    19,    97,
      -1,    54,    77,   139,    78,    97,    -1,    54,    77,   139,
      78,    19,    97,    -1,    56,    97,    54,    77,   139,    78,
      -1,    56,    19,    97,    54,    77,   139,    78,    -1,    55,
      77,   139,    78,    97,    -1,    55,    77,   139,    78,    19,
      97,    -1,    55,    77,   139,    78,    97,   107,    -1,    55,
      77,   139,    78,    19,    97,   107,    19,    -1,    55,    77,
     139,    78,    97,    27,    77,   139,    78,    97,    -1,    55,
      77,   139,    78,    19,    97,    27,    77,   139,    78,    19,
      97,    -1,    55,    77,   139,    78,    97,    27,    77,   139,
      78,    97,   107,    -1,    55,    77,   139,    78,    19,    97,
      27,    77,   139,    78,    19,    97,   107,    -1,    26,    97,
      -1,    26,    19,    97,    -1,    -1,    -1,    94,   109,   114,
      95,   110,    -1,    -1,    -1,    39,   111,   114,    40,   112,
      -1,    64,    77,   126,    78,   108,    -1,   115,    -1,   114,
     115,    -1,    65,   127,    19,   125,    -1,    66,    19,   125,
      -1,    -1,    60,     3,    77,   121,    78,   117,    97,    -1,
      -1,    61,     3,    77,   121,    78,   118,    97,    -1,    -1,
     124,    60,     3,    77,   121,    78,   119,    97,    -1,     3,
      77,    78,    -1,     3,    77,   123,    78,    -1,    -1,   122,
      -1,   121,    21,   122,    -1,   124,     3,    -1,     3,    -1,
      -1,   127,    -1,   123,    21,   127,    -1,    43,    -1,    44,
      -1,    42,    -1,    45,    -1,    46,    -1,   125,    82,    -1,
      82,    -1,     3,    -1,   136,    -1,   133,    -1,   127,    20,
     127,    -1,   142,    -1,   140,    -1,    77,    -1,    78,    -1,
      -1,   131,    -1,   132,    -1,   131,    21,   132,    -1,     4,
      19,    90,    -1,   128,   127,   129,    -1,   127,    11,   127,
      -1,   127,    12,   127,    -1,   127,    13,   127,    -1,   127,
      14,   127,    -1,   127,    59,   127,    -1,     6,    -1,    93,
      -1,   126,    -1,     4,    -1,   134,    19,   134,    -1,    36,
      -1,    37,    -1,     6,    -1,     4,    -1,    71,    -1,   126,
      23,   134,    24,    -1,   127,    63,   127,    19,   127,    -1,
       5,    -1,   126,    -1,   135,    -1,     3,    77,   123,    78,
      -1,    93,    -1,   127,    48,   127,    -1,   126,    -1,    70,
      -1,    69,    -1,   140,    -1,   127,    48,   127,    -1,   139,
     138,   139,    -1,   127,    30,   127,    -1,   127,    31,   127,
      -1,   127,    32,   127,    -1,   127,    33,   127,    -1,   127,
      34,   127,    -1,   127,    35,   127,    -1,    89,    -1,   141,
      21,    89,    -1,    76,    77,     4,    78,    -1
};

/* YYRLINE[YYN] -- source line where rule number YYN was defined.  */
static const yytype_uint16 yyrline[] =
{
       0,  2175,  2175,  2176,  2178,  2179,  2180,  2182,  2183,  2184,
    2185,  2186,  2187,  2188,  2189,  2190,  2191,  2192,  2194,  2196,
    2226,  2230,  2234,  2238,  2245,  2260,  2296,  2327,  2362,  2379,
    2421,  2442,  2471,  2472,  2473,  2476,  2494,  2505,  2515,  2526,
    2543,  2550,  2562,  2571,  2578,  2586,  2592,  2611,  2613,  2619,
    2625,  2631,  2638,  2642,  2646,  2654,  2658,  2663,  2668,  2674,
    2677,  2679,  2680,  2723,  2723,  2723,  2724,  2724,  2724,  2726,
    2726,  2748,  2765,  2777,  2783,  2795,  2809,  2827,  2846,  2875,
    2904,  2942,  2980,  3022,  3066,  3074,  3082,  3082,  3082,  3083,
    3083,  3083,  3085,  3094,  3095,  3112,  3117,  3122,  3122,  3151,
    3151,  3176,  3176,  3197,  3201,  3206,  3207,  3208,  3209,  3210,
    3215,  3216,  3217,  3219,  3220,  3221,  3222,  3223,  3225,  3238,
    3240,  3264,  3265,  3266,  3272,  3273,  3276,  3282,  3288,  3292,
    3298,  3302,  3318,  3323,  3324,  3358,  3388,  3420,  3449,  3484,
    3485,  3486,  3487,  3488,  3495,  3496,  3499,  3510,  3518,  3528,
    3541,  3554,  3563,  3564,  3572,  3600,  3601,  3605,  3621,  3622,
    3623,  3624,  3627,  3649,  3662,  3675,  3690,  3703,  3716,  3731,
    3732,  3767
};
#endif

#if YYDEBUG || YYERROR_VERBOSE || YYTOKEN_TABLE
/* YYTNAME[SYMBOL-NUM] -- String name of the symbol SYMBOL-NUM.
   First, the terminals, then, starting at YYNTOKENS, nonterminals.  */
static const char *const yytname[] =
{
  "$end", "error", "$undefined", "TEXT", "STRING", "STRING_WITH_VARS",
  "NUMBER", "INCREMENT", "DECREMENT", "PRINT", "VAR", "PLUS", "MINUS",
  "TIMES", "DIVIDE", "EQUAL", "SEMICOLON", "READ", "INSERTVALUE", "COLON",
  "DOT", "COM", "SHARP", "LSQUARE", "RSQUARE", "SQUARES_L_R", "ELSE",
  "ELSE_IF", "RANGE_SEMI_OPEN", "IFX", "EQUALC", "UNEQUAL", "GREATERTHAN",
  "LESSTHAN", "GREATERTHAN_EQUAL", "LESSTHAN_EQUAL", "TRUE", "FALSE",
  "BOOL", "INDENT", "DEDENT", "STRUCT", "TSTRING", "TINT", "TFLOAT",
  "TBOOL", "TVOID", "FOR", "IN", "RANGE", "MAIN", "DOTYPE", "APPEND",
  "LENGHT", "WHILE", "IF", "PERFORM", "BREAK", "RETURN", "MOD", "FUNCTION",
  "FUNC", "PARENS", "QUESTION_MARK", "SWITCH", "CASE", "DEFAULT",
  "startRace", "endRace", "OR", "AND", "DECIMAL", "NEWLINE", "IM",
  "IM_Math", "PI", "EQUATION", "'('", "')'", "$accept", "program",
  "end_statement", "statement", "print", "increment_decrement_stmt", "var",
  "tuples", "array_decl", "array_assing", "list_item", "list_item_list",
  "read", "var_for", "range", "rlrace", "rbrace", "sentences", "block",
  "$@1", "$@2", "$@3", "$@4", "for_loop", "$@5", "while_loop",
  "perform_while_loop", "if_condition", "condtional_stmt", "switch_block",
  "$@6", "$@7", "$@8", "$@9", "switch_cases", "case_list", "single_case",
  "function_decl", "@10", "@11", "@12", "function_call", "parameter_list",
  "param_decl", "argument_list", "types", "statements", "variable", "expr",
  "paren_left", "paren_right", "dict_body", "pair_list", "key_value_pair",
  "arith_expr", "array_indexer", "bool", "term", "for_condition",
  "logicals", "condition", "comparison", "expr_list", "eqt", 0
};
#endif

# ifdef YYPRINT
/* YYTOKNUM[YYLEX-NUM] -- Internal token number corresponding to
   token YYLEX-NUM.  */
static const yytype_uint16 yytoknum[] =
{
       0,   256,   257,   258,   259,   260,   261,   262,   263,   264,
     265,   266,   267,   268,   269,   270,   271,   272,   273,   274,
     275,   276,   277,   278,   279,   280,   281,   282,   283,   284,
     285,   286,   287,   288,   289,   290,   291,   292,   293,   294,
     295,   296,   297,   298,   299,   300,   301,   302,   303,   304,
     305,   306,   307,   308,   309,   310,   311,   312,   313,   314,
     315,   316,   317,   318,   319,   320,   321,   322,   323,   324,
     325,   326,   327,   328,   329,   330,   331,    40,    41
};
# endif

/* YYR1[YYN] -- Symbol number of symbol that rule YYN derives.  */
static const yytype_uint8 yyr1[] =
{
       0,    79,    80,    80,    81,    81,    81,    82,    82,    82,
      82,    82,    82,    82,    82,    82,    82,    82,    82,    83,
      84,    84,    84,    84,    85,    85,    85,    85,    85,    85,
      85,    85,    85,    85,    85,    86,    86,    86,    86,    87,
      87,    87,    87,    87,    87,    88,    88,    89,    89,    89,
      89,    89,    89,    90,    90,    91,    92,    93,    93,    94,
      95,    96,    96,    98,    99,    97,   100,   101,    97,   103,
     102,   102,   104,   104,   105,   105,   106,   106,   106,   106,
     106,   106,   106,   106,   107,   107,   109,   110,   108,   111,
     112,   108,   113,   114,   114,   115,   115,   117,   116,   118,
     116,   119,   116,   120,   120,   121,   121,   121,   122,   122,
     123,   123,   123,   124,   124,   124,   124,   124,   125,   125,
     126,   127,   127,   127,   127,   127,   128,   129,   130,   130,
     131,   131,   132,   133,   133,   133,   133,   133,   133,   134,
     134,   134,   134,   134,   135,   135,   136,   136,   136,   136,
     136,   136,   136,   136,   136,   137,   137,   137,   138,   138,
     139,   139,   139,   140,   140,   140,   140,   140,   140,   141,
     141,   142
};

/* YYR2[YYN] -- Number of symbols composing right hand side of rule YYN.  */
static const yytype_uint8 yyr2[] =
{
       0,     2,     0,     2,     1,     1,     0,     2,     2,     2,
       1,     1,     1,     1,     1,     1,     1,     2,     2,     4,
       2,     2,     2,     2,     2,     4,     6,     5,     4,     3,
       2,     4,     1,     1,     1,     6,     7,     5,     6,     6,
       9,     6,     9,     5,     4,     3,     5,     1,     3,     3,
       4,     3,     1,     1,     3,     4,     3,     3,     3,     1,
       1,     1,     2,     0,     0,     5,     0,     0,     5,     0,
       7,     7,     5,     6,     6,     7,     5,     6,     6,     8,
      10,    12,    11,    13,     2,     3,     0,     0,     5,     0,
       0,     5,     5,     1,     2,     4,     3,     0,     7,     0,
       7,     0,     8,     3,     4,     0,     1,     3,     2,     1,
       0,     1,     3,     1,     1,     1,     1,     1,     2,     1,
       1,     1,     1,     3,     1,     1,     1,     1,     0,     1,
       1,     3,     3,     3,     3,     3,     3,     3,     3,     1,
       1,     1,     1,     3,     1,     1,     1,     1,     1,     4,
       5,     1,     1,     1,     4,     1,     3,     1,     1,     1,
       1,     3,     3,     3,     3,     3,     3,     3,     3,     1,
       3,     4
};

/* YYDEFACT[STATE-NAME] -- Default rule to reduce with in state
   STATE-NUM when YYTABLE doesn't specify something else to do.  Zero
   means the default is an error.  */
static const yytype_uint8 yydefact[] =
{
       2,     0,     1,   120,     0,     0,     0,     0,     0,   115,
     113,   114,   116,   117,     0,     0,     0,     0,    61,     0,
       0,     0,     0,     3,     6,     6,     6,    34,    32,    33,
       6,     6,    10,    13,    14,    15,    16,    11,    12,     0,
       0,     0,   110,   120,    22,    23,     0,    24,     0,     0,
       0,     0,     0,    66,    59,    63,     0,   120,   147,   151,
     146,   144,   145,   148,     0,   126,   152,    62,     0,   122,
     153,   121,   125,   124,     0,     0,     0,     4,     5,     7,
      17,     8,     9,    18,    30,     0,    20,    21,     0,    45,
     128,    29,     0,   103,     0,   111,     0,     0,     0,     0,
       0,     0,     0,     0,   125,     0,     0,     0,     0,     0,
     110,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,   105,   105,     0,
       0,     0,     0,     0,    52,   128,    53,     0,    47,     0,
       0,     0,   129,   130,     0,    47,     0,   104,    19,     0,
     128,    28,    25,     0,     0,    55,     0,   155,   152,     0,
       0,     0,   159,   158,     0,     0,     0,     0,   119,     0,
       0,     0,     0,     0,   147,   146,   140,   152,     0,     0,
     134,   135,   136,   137,   123,   163,   164,   165,   166,   167,
     168,   138,     0,   127,   133,   109,     0,   106,     0,     0,
       0,     0,    44,    31,     0,   105,     0,     0,     0,    46,
     169,     0,     0,    27,     0,     0,    37,   112,     0,     0,
       0,     0,     0,     0,    56,     0,    69,   161,     0,    72,
     162,     0,    76,     0,    67,   118,    60,    64,     0,   154,
     171,     0,   149,     0,     0,    97,   108,    99,    89,    86,
      92,     0,    43,     0,    51,    48,    54,     0,    49,   132,
     131,    38,    39,    26,    58,    57,     0,    35,     0,   156,
       0,     0,    73,    77,     0,     0,    78,     0,    68,    65,
      74,   143,   150,   107,     0,     0,     0,     0,    41,     0,
     101,   170,    50,    36,     0,    71,    70,     0,     0,     0,
      84,     0,    75,    98,   100,     0,     0,     0,    93,     0,
       0,     0,     0,     0,    79,    85,     0,     0,     0,    90,
      94,    87,     0,   102,    40,     0,     0,     0,    96,    91,
      88,    42,     0,    80,    95,     0,    82,    81,    83
};

/* YYDEFGOTO[NTERM-NUM].  */
static const yytype_int16 yydefgoto[] =
{
      -1,     1,    79,   168,    24,    25,    26,    27,    28,    29,
     136,   137,    30,   101,   176,    55,   237,    31,    56,   108,
     279,   107,   278,    32,   271,    33,    34,    35,   276,   250,
     287,   330,   286,   329,    36,   307,   308,    37,   284,   285,
     311,    38,   196,   197,    94,    39,   169,    66,   138,    68,
     194,   141,   142,   143,    69,   179,    70,    71,   160,   165,
     103,    72,   211,    73
};

/* YYPACT[STATE-NUM] -- Index in YYTABLE of the portion describing
   STATE-NUM.  */
#define YYPACT_NINF -262
static const yytype_int16 yypact[] =
{
    -262,   526,  -262,     0,    15,    15,   -49,    48,   -14,  -262,
    -262,  -262,  -262,  -262,    31,    53,    74,   117,  -262,   356,
      82,    89,    87,  -262,    25,    25,    25,  -262,  -262,  -262,
      25,    25,  -262,  -262,  -262,  -262,  -262,  -262,  -262,     7,
     221,   154,     3,  -262,  -262,  -262,   356,     9,   175,   173,
     356,   356,   -17,  -262,  -262,  -262,   139,   122,  -262,  -262,
    -262,  -262,  -262,  -262,   124,  -262,   189,   789,   356,  -262,
    -262,  -262,  -262,  -262,   149,   167,    15,  -262,  -262,  -262,
    -262,  -262,  -262,  -262,    39,   246,  -262,  -262,   305,  -262,
     254,   789,   305,  -262,   -10,   789,   387,   183,   255,   185,
     274,   356,   482,   164,   177,   187,   230,   608,   608,   239,
     356,   290,   360,   356,   356,   356,   356,   356,   356,   356,
     356,   356,   356,   356,   356,   356,   427,    14,    14,   218,
     333,   292,   241,   305,  -262,   254,  -262,    21,   789,   305,
     295,   264,   300,  -262,    -5,   427,   356,  -262,  -262,   305,
     254,  -262,   687,   305,   310,  -262,   298,  -262,    23,   647,
     262,   356,  -262,  -262,   127,   356,   135,   273,  -262,   549,
     464,   356,     4,   277,    45,    86,  -262,    42,   687,   156,
     421,   421,   237,   237,   799,   353,   353,   353,   353,   353,
     353,   237,   721,  -262,  -262,  -262,     5,  -262,   348,     8,
     -12,   305,  -262,   789,   343,    14,   141,   289,   305,  -262,
    -262,    12,   305,  -262,   254,   276,  -262,   789,   161,   303,
     356,   356,    17,   358,  -262,   356,   349,   789,   -17,  -262,
     222,   -17,   278,   356,  -262,  -262,  -262,  -262,   205,  -262,
    -262,   360,  -262,   356,    14,  -262,  -262,  -262,  -262,  -262,
    -262,   179,   359,    26,  -262,  -262,  -262,   276,  -262,  -262,
    -262,  -262,  -262,  -262,   789,   789,   276,  -262,   352,   789,
     -17,   -17,  -262,   318,   142,   301,  -262,   217,  -262,  -262,
    -262,   361,   237,  -262,   -17,   -17,   283,   283,  -262,   354,
    -262,  -262,  -262,  -262,   305,  -262,  -262,   302,   370,   -17,
    -262,   356,  -262,  -262,  -262,   356,   371,   152,  -262,   148,
     305,   -17,   186,   356,  -262,  -262,   219,   755,   608,  -262,
    -262,  -262,   215,  -262,  -262,   253,   -17,   608,   608,  -262,
    -262,  -262,   372,   368,   608,   -17,  -262,   368,  -262
};

/* YYPGOTO[NTERM-NUM].  */
static const yytype_int16 yypgoto[] =
{
    -262,  -262,   294,     1,  -262,  -262,  -262,  -262,  -262,  -262,
    -119,   -62,  -262,  -262,    75,   195,    93,  -262,   -33,  -262,
    -262,  -262,  -262,  -262,  -262,  -262,  -262,  -262,  -261,  -262,
    -262,  -262,  -262,  -262,  -262,   116,  -167,  -262,  -262,  -262,
    -262,  -262,  -127,   162,   304,   -92,  -103,    -1,     2,    -4,
    -113,  -101,  -262,   191,  -262,   170,  -262,  -262,  -262,  -262,
     -28,   -37,  -262,  -262
};

/* YYTABLE[YYPACT[STATE-NUM]].  What to do in state STATE-NUM.  If
   positive, shift that token.  If negative, reduce the rule which
   number is the opposite.  If zero, do what YYDEFACT says.
   If YYTABLE_NINF, syntax error.  */
#define YYTABLE_NINF -161
static const yytype_int16 yytable[] =
{
      40,   199,    23,    44,    45,   170,    57,    58,    59,    60,
      84,   146,   298,   104,   104,    41,   215,   195,    43,   106,
     210,    67,    53,   105,    97,   146,   244,   248,    46,   244,
     144,   216,    98,   257,   207,   198,   198,    92,   266,    61,
      62,    77,   208,    91,    95,   209,   112,   244,    96,   219,
      54,    47,   102,   102,   130,    54,     9,    10,    11,    12,
      13,  -141,   131,    48,  -142,   112,  -141,    85,   147,  -142,
     126,   206,   336,   193,    63,   129,   338,    42,   253,    64,
      65,    93,   239,   245,   139,    74,   247,   218,   139,   256,
     193,   222,    75,   153,   145,   193,   256,    78,   258,   152,
     158,  -157,   261,   159,   290,  -139,    40,    40,    49,   267,
    -139,   177,    95,   198,   178,   180,   181,   182,   183,   184,
     185,   186,   187,   188,   189,   190,   191,   192,   104,   139,
      50,   229,   203,   232,   104,   139,    52,   230,   291,   251,
     320,   145,   320,   238,   292,   139,   228,   256,   217,   139,
     259,    51,   198,   293,   231,   145,    53,    57,    58,    59,
      60,   299,   208,   227,    76,   254,    53,   102,    40,    40,
     235,   235,   151,   102,    53,   241,   157,    88,    99,    89,
     242,    53,   208,   100,    54,   262,    57,    58,    59,    60,
      61,    62,   319,   109,    54,   272,   104,   139,   273,   110,
     208,   111,    54,   288,   139,   277,   149,   208,   139,    54,
     324,   139,   112,   305,   306,   328,   236,   305,   306,    61,
      62,    90,   264,   265,   334,    63,   127,   269,    86,    87,
      64,    65,   312,   162,   163,   102,   208,   295,   296,   331,
     177,   300,   164,   178,   128,   282,  -160,  -160,   322,   132,
     150,   303,   304,   139,    63,  -160,   162,   163,   140,    64,
      65,   154,   139,   155,   104,   166,   315,   118,   119,   120,
     121,   122,   123,   316,   162,   163,   104,   156,   323,    57,
      58,    59,    60,   280,   167,   325,   162,   163,   162,   163,
     139,   162,   163,   333,   173,   302,   200,   326,   204,   133,
     125,   134,   337,   102,   274,   275,   139,   317,    57,    58,
      59,    60,    61,    62,   212,   102,   171,    40,   205,    80,
      81,   214,   162,   163,    82,    83,    40,    40,   133,   235,
     134,   332,   213,    40,   223,   235,    57,    58,    59,    60,
     226,    61,    62,   135,   274,   297,   224,    63,   305,   306,
     233,   246,    64,    65,   193,   240,   201,   255,   202,    57,
      58,    59,    60,    57,   174,    59,   175,   252,   270,    61,
      62,   263,   135,   268,   289,   294,    63,   310,   301,   313,
     241,    64,    65,  -161,  -161,  -161,  -161,  -161,  -161,   314,
     318,   335,    61,    62,   274,   249,    61,    62,   113,   114,
     115,   116,   321,   309,    63,   260,   283,   117,     0,    64,
      65,   281,     0,     0,   172,     0,     0,   118,   119,   120,
     121,   122,   123,     0,     0,     0,     0,    63,     0,     0,
       0,    63,    64,    65,   115,   116,    64,    65,   113,   114,
     115,   116,     0,     0,     0,     0,   124,   117,     0,     0,
     125,   118,   119,   120,   121,   122,   123,   118,   119,   120,
     121,   122,   123,     0,     0,   148,     0,     3,     0,     0,
       0,     4,     5,     6,     7,     0,     0,     0,     0,     0,
     124,     8,     0,     0,   125,     0,   124,     0,     0,     0,
     125,     0,     0,   113,   114,   115,   116,     0,     0,     0,
       0,     0,   117,     0,     0,   193,     9,    10,    11,    12,
      13,    14,   118,   119,   120,   121,   122,   123,    15,    16,
      17,    18,    19,     0,    20,    21,     2,     0,    22,     3,
     161,     0,   236,     4,     5,     6,     7,     0,     0,     0,
       0,   124,     0,     8,     0,   125,     0,     0,     0,     0,
       0,     0,     3,     0,     0,     0,     4,     5,     6,     7,
       0,     0,     0,     0,     0,     0,     8,     0,     9,    10,
      11,    12,    13,    14,     0,     0,     0,     0,     0,     0,
      15,    16,    17,    18,    19,     0,    20,    21,     0,   234,
      22,     9,    10,    11,    12,    13,    14,     0,     0,     0,
       0,     0,     0,    15,    16,    17,    18,    19,     0,    20,
      21,     3,     0,    22,     0,     4,     5,     6,     7,     0,
       0,     0,     0,     0,     0,     8,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       9,    10,    11,    12,    13,    14,     0,     0,   113,   114,
     115,   116,    15,    16,    17,    18,    19,   117,    20,    21,
       0,     0,    22,     0,     0,   220,     0,   118,   119,   120,
     121,   122,   123,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,   225,   221,     0,   113,   114,
     115,   116,     0,     0,     0,     0,   124,   117,     0,     0,
     125,     0,     0,     0,     0,   220,     0,   118,   119,   120,
     121,   122,   123,     0,     0,     0,     0,     0,     0,     0,
       0,     0,   113,   114,   115,   116,   221,     0,     0,     0,
     243,   117,     0,     0,     0,     0,   124,     0,     0,     0,
     125,   118,   119,   120,   121,   122,   123,     0,     0,     0,
       0,     0,     0,     0,     0,     0,   113,   114,   115,   116,
       0,     0,     0,     0,   327,   117,     0,     0,     0,     0,
     124,     0,     0,     0,   125,   118,   119,   120,   121,   122,
     123,     0,     0,     0,     0,     0,     0,     0,     0,     0,
     113,   114,   115,   116,     0,     0,     0,     0,     0,   117,
     113,   114,   115,   116,   124,     0,     0,     0,   125,   118,
     119,   120,   121,   122,   123,     0,     0,     0,     0,   118,
     119,   120,   121,   122,   123,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,   124,     0,
       0,     0,   125,     0,     0,     0,     0,     0,   124,     0,
       0,     0,   125
};

static const yytype_int16 yycheck[] =
{
       1,   128,     1,     4,     5,   108,     3,     4,     5,     6,
       3,    21,   273,    50,    51,    15,    21,     3,     3,    52,
     139,    19,    39,    51,    15,    21,    21,    39,    77,    21,
      92,   144,    23,    21,   135,   127,   128,    41,    21,    36,
      37,    16,    21,    41,    42,    24,    23,    21,    46,   150,
      67,     3,    50,    51,    15,    67,    42,    43,    44,    45,
      46,    19,    23,    77,    19,    23,    24,    60,    78,    24,
      68,   133,   333,    78,    71,    76,   337,    77,   205,    76,
      77,    78,    78,    78,    88,     3,    78,   149,    92,   208,
      78,   153,     3,    97,    92,    78,   215,    72,   211,    97,
     101,    78,   215,   101,    78,    19,   107,   108,    77,   222,
      24,   112,   110,   205,   112,   113,   114,   115,   116,   117,
     118,   119,   120,   121,   122,   123,   124,   125,   165,   133,
      77,   164,   130,   166,   171,   139,    19,   165,   257,   201,
     307,   139,   309,   171,   257,   149,    19,   266,   146,   153,
     212,    77,   244,   266,    19,   153,    39,     3,     4,     5,
       6,    19,    21,   161,    77,    24,    39,   165,   169,   170,
     169,   170,    97,   171,    39,    19,   101,    23,     3,    25,
      24,    39,    21,    10,    67,    24,     3,     4,     5,     6,
      36,    37,    40,    54,    67,   228,   233,   201,   231,    77,
      21,    77,    67,    24,   208,   233,    23,    21,   212,    67,
      24,   215,    23,    65,    66,   318,    68,    65,    66,    36,
      37,    67,   220,   221,   327,    71,    77,   225,     7,     8,
      76,    77,   294,    69,    70,   233,    21,   270,   271,    24,
     241,   274,    78,   241,    77,   243,    69,    70,   310,     3,
      67,   284,   285,   257,    71,    78,    69,    70,     4,    76,
      77,     6,   266,    78,   301,    78,   299,    30,    31,    32,
      33,    34,    35,   301,    69,    70,   313,     3,   311,     3,
       4,     5,     6,    78,    54,   313,    69,    70,    69,    70,
     294,    69,    70,   326,     4,    78,    78,    78,     6,    23,
      63,    25,   335,   301,    26,    27,   310,   305,     3,     4,
       5,     6,    36,    37,    19,   313,    77,   318,    77,    25,
      26,    21,    69,    70,    30,    31,   327,   328,    23,   328,
      25,    78,    68,   334,    24,   334,     3,     4,     5,     6,
      78,    36,    37,    67,    26,    27,    48,    71,    65,    66,
      77,     3,    76,    77,    78,    78,    23,    68,    25,     3,
       4,     5,     6,     3,     4,     5,     6,    24,    19,    36,
      37,    68,    67,    15,    15,    23,    71,    23,    77,    77,
      19,    76,    77,    30,    31,    32,    33,    34,    35,    19,
      19,    19,    36,    37,    26,   200,    36,    37,    11,    12,
      13,    14,   309,   287,    71,   214,   244,    20,    -1,    76,
      77,   241,    -1,    -1,   110,    -1,    -1,    30,    31,    32,
      33,    34,    35,    -1,    -1,    -1,    -1,    71,    -1,    -1,
      -1,    71,    76,    77,    13,    14,    76,    77,    11,    12,
      13,    14,    -1,    -1,    -1,    -1,    59,    20,    -1,    -1,
      63,    30,    31,    32,    33,    34,    35,    30,    31,    32,
      33,    34,    35,    -1,    -1,    78,    -1,     3,    -1,    -1,
      -1,     7,     8,     9,    10,    -1,    -1,    -1,    -1,    -1,
      59,    17,    -1,    -1,    63,    -1,    59,    -1,    -1,    -1,
      63,    -1,    -1,    11,    12,    13,    14,    -1,    -1,    -1,
      -1,    -1,    20,    -1,    -1,    78,    42,    43,    44,    45,
      46,    47,    30,    31,    32,    33,    34,    35,    54,    55,
      56,    57,    58,    -1,    60,    61,     0,    -1,    64,     3,
      48,    -1,    68,     7,     8,     9,    10,    -1,    -1,    -1,
      -1,    59,    -1,    17,    -1,    63,    -1,    -1,    -1,    -1,
      -1,    -1,     3,    -1,    -1,    -1,     7,     8,     9,    10,
      -1,    -1,    -1,    -1,    -1,    -1,    17,    -1,    42,    43,
      44,    45,    46,    47,    -1,    -1,    -1,    -1,    -1,    -1,
      54,    55,    56,    57,    58,    -1,    60,    61,    -1,    40,
      64,    42,    43,    44,    45,    46,    47,    -1,    -1,    -1,
      -1,    -1,    -1,    54,    55,    56,    57,    58,    -1,    60,
      61,     3,    -1,    64,    -1,     7,     8,     9,    10,    -1,
      -1,    -1,    -1,    -1,    -1,    17,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      42,    43,    44,    45,    46,    47,    -1,    -1,    11,    12,
      13,    14,    54,    55,    56,    57,    58,    20,    60,    61,
      -1,    -1,    64,    -1,    -1,    28,    -1,    30,    31,    32,
      33,    34,    35,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    48,    49,    -1,    11,    12,
      13,    14,    -1,    -1,    -1,    -1,    59,    20,    -1,    -1,
      63,    -1,    -1,    -1,    -1,    28,    -1,    30,    31,    32,
      33,    34,    35,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    11,    12,    13,    14,    49,    -1,    -1,    -1,
      19,    20,    -1,    -1,    -1,    -1,    59,    -1,    -1,    -1,
      63,    30,    31,    32,    33,    34,    35,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    11,    12,    13,    14,
      -1,    -1,    -1,    -1,    19,    20,    -1,    -1,    -1,    -1,
      59,    -1,    -1,    -1,    63,    30,    31,    32,    33,    34,
      35,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      11,    12,    13,    14,    -1,    -1,    -1,    -1,    -1,    20,
      11,    12,    13,    14,    59,    -1,    -1,    -1,    63,    30,
      31,    32,    33,    34,    35,    -1,    -1,    -1,    -1,    30,
      31,    32,    33,    34,    35,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    59,    -1,
      -1,    -1,    63,    -1,    -1,    -1,    -1,    -1,    59,    -1,
      -1,    -1,    63
};

/* YYSTOS[STATE-NUM] -- The (internal number of the) accessing
   symbol of state STATE-NUM.  */
static const yytype_uint8 yystos[] =
{
       0,    80,     0,     3,     7,     8,     9,    10,    17,    42,
      43,    44,    45,    46,    47,    54,    55,    56,    57,    58,
      60,    61,    64,    82,    83,    84,    85,    86,    87,    88,
      91,    96,   102,   104,   105,   106,   113,   116,   120,   124,
     126,    15,    77,     3,   126,   126,    77,     3,    77,    77,
      77,    77,    19,    39,    67,    94,    97,     3,     4,     5,
       6,    36,    37,    71,    76,    77,   126,   127,   128,   133,
     135,   136,   140,   142,     3,     3,    77,    16,    72,    81,
      81,    81,    81,    81,     3,    60,     7,     8,    23,    25,
      67,   127,   128,    78,   123,   127,   127,    15,    23,     3,
      10,    92,   127,   139,   140,   139,    97,   100,    98,    54,
      77,    77,    23,    11,    12,    13,    14,    20,    30,    31,
      32,    33,    34,    35,    59,    63,   127,    77,    77,   126,
      15,    23,     3,    23,    25,    67,    89,    90,   127,   128,
       4,   130,   131,   132,    90,   127,    21,    78,    78,    23,
      67,    93,   127,   128,     6,    78,     3,    93,   126,   127,
     137,    48,    69,    70,    78,   138,    78,    54,    82,   125,
     125,    77,   123,     4,     4,     6,    93,   126,   127,   134,
     127,   127,   127,   127,   127,   127,   127,   127,   127,   127,
     127,   127,   127,    78,   129,     3,   121,   122,   124,   121,
      78,    23,    25,   127,     6,    77,    90,   130,    21,    24,
      89,   141,    19,    68,    21,    21,   129,   127,    90,   130,
      28,    49,    90,    24,    48,    48,    78,   127,    19,    97,
     139,    19,    97,    77,    40,    82,    68,    95,   139,    78,
      78,    19,    24,    19,    21,    78,     3,    78,    39,    94,
     108,    90,    24,   121,    24,    68,    89,    21,   129,    90,
     132,   129,    24,    68,   127,   127,    21,   129,    15,   127,
      19,   103,    97,    97,    26,    27,   107,   139,   101,    99,
      78,   134,   127,   122,   117,   118,   111,   109,    24,    15,
      78,    89,   129,   129,    23,    97,    97,    27,   107,    19,
      97,    77,    78,    97,    97,    65,    66,   114,   115,   114,
      23,   119,    90,    77,    19,    97,   139,   127,    19,    40,
     115,    95,    90,    97,    24,   139,    78,    19,   125,   112,
     110,    24,    78,    97,   125,    19,   107,    97,   107
};

#define yyerrok		(yyerrstatus = 0)
#define yyclearin	(yychar = YYEMPTY)
#define YYEMPTY		(-2)
#define YYEOF		0

#define YYACCEPT	goto yyacceptlab
#define YYABORT		goto yyabortlab
#define YYERROR		goto yyerrorlab


/* Like YYERROR except do call yyerror.  This remains here temporarily
   to ease the transition to the new meaning of YYERROR, for GCC.
   Once GCC version 2 has supplanted version 1, this can go.  */

#define YYFAIL		goto yyerrlab

#define YYRECOVERING()  (!!yyerrstatus)

#define YYBACKUP(Token, Value)					\
do								\
  if (yychar == YYEMPTY && yylen == 1)				\
    {								\
      yychar = (Token);						\
      yylval = (Value);						\
      yytoken = YYTRANSLATE (yychar);				\
      YYPOPSTACK (1);						\
      goto yybackup;						\
    }								\
  else								\
    {								\
      yyerror (YY_("syntax error: cannot back up")); \
      YYERROR;							\
    }								\
while (YYID (0))


#define YYTERROR	1
#define YYERRCODE	256


/* YYLLOC_DEFAULT -- Set CURRENT to span from RHS[1] to RHS[N].
   If N is 0, then set CURRENT to the empty location which ends
   the previous symbol: RHS[0] (always defined).  */

#define YYRHSLOC(Rhs, K) ((Rhs)[K])
#ifndef YYLLOC_DEFAULT
# define YYLLOC_DEFAULT(Current, Rhs, N)				\
    do									\
      if (YYID (N))                                                    \
	{								\
	  (Current).first_line   = YYRHSLOC (Rhs, 1).first_line;	\
	  (Current).first_column = YYRHSLOC (Rhs, 1).first_column;	\
	  (Current).last_line    = YYRHSLOC (Rhs, N).last_line;		\
	  (Current).last_column  = YYRHSLOC (Rhs, N).last_column;	\
	}								\
      else								\
	{								\
	  (Current).first_line   = (Current).last_line   =		\
	    YYRHSLOC (Rhs, 0).last_line;				\
	  (Current).first_column = (Current).last_column =		\
	    YYRHSLOC (Rhs, 0).last_column;				\
	}								\
    while (YYID (0))
#endif


/* YY_LOCATION_PRINT -- Print the location on the stream.
   This macro was not mandated originally: define only if we know
   we won't break user code: when these are the locations we know.  */

#ifndef YY_LOCATION_PRINT
# if YYLTYPE_IS_TRIVIAL
#  define YY_LOCATION_PRINT(File, Loc)			\
     fprintf (File, "%d.%d-%d.%d",			\
	      (Loc).first_line, (Loc).first_column,	\
	      (Loc).last_line,  (Loc).last_column)
# else
#  define YY_LOCATION_PRINT(File, Loc) ((void) 0)
# endif
#endif


/* YYLEX -- calling `yylex' with the right arguments.  */

#ifdef YYLEX_PARAM
# define YYLEX yylex (YYLEX_PARAM)
#else
# define YYLEX yylex ()
#endif

/* Enable debugging if requested.  */
#if YYDEBUG

# ifndef YYFPRINTF
#  include <stdio.h> /* INFRINGES ON USER NAME SPACE */
#  define YYFPRINTF fprintf
# endif

# define YYDPRINTF(Args)			\
do {						\
  if (yydebug)					\
    YYFPRINTF Args;				\
} while (YYID (0))

# define YY_SYMBOL_PRINT(Title, Type, Value, Location)			  \
do {									  \
  if (yydebug)								  \
    {									  \
      YYFPRINTF (stderr, "%s ", Title);					  \
      yy_symbol_print (stderr,						  \
		  Type, Value); \
      YYFPRINTF (stderr, "\n");						  \
    }									  \
} while (YYID (0))


/*--------------------------------.
| Print this symbol on YYOUTPUT.  |
`--------------------------------*/

/*ARGSUSED*/
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_symbol_value_print (FILE *yyoutput, int yytype, YYSTYPE const * const yyvaluep)
#else
static void
yy_symbol_value_print (yyoutput, yytype, yyvaluep)
    FILE *yyoutput;
    int yytype;
    YYSTYPE const * const yyvaluep;
#endif
{
  if (!yyvaluep)
    return;
# ifdef YYPRINT
  if (yytype < YYNTOKENS)
    YYPRINT (yyoutput, yytoknum[yytype], *yyvaluep);
# else
  YYUSE (yyoutput);
# endif
  switch (yytype)
    {
      default:
	break;
    }
}


/*--------------------------------.
| Print this symbol on YYOUTPUT.  |
`--------------------------------*/

#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_symbol_print (FILE *yyoutput, int yytype, YYSTYPE const * const yyvaluep)
#else
static void
yy_symbol_print (yyoutput, yytype, yyvaluep)
    FILE *yyoutput;
    int yytype;
    YYSTYPE const * const yyvaluep;
#endif
{
  if (yytype < YYNTOKENS)
    YYFPRINTF (yyoutput, "token %s (", yytname[yytype]);
  else
    YYFPRINTF (yyoutput, "nterm %s (", yytname[yytype]);

  yy_symbol_value_print (yyoutput, yytype, yyvaluep);
  YYFPRINTF (yyoutput, ")");
}

/*------------------------------------------------------------------.
| yy_stack_print -- Print the state stack from its BOTTOM up to its |
| TOP (included).                                                   |
`------------------------------------------------------------------*/

#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_stack_print (yytype_int16 *yybottom, yytype_int16 *yytop)
#else
static void
yy_stack_print (yybottom, yytop)
    yytype_int16 *yybottom;
    yytype_int16 *yytop;
#endif
{
  YYFPRINTF (stderr, "Stack now");
  for (; yybottom <= yytop; yybottom++)
    {
      int yybot = *yybottom;
      YYFPRINTF (stderr, " %d", yybot);
    }
  YYFPRINTF (stderr, "\n");
}

# define YY_STACK_PRINT(Bottom, Top)				\
do {								\
  if (yydebug)							\
    yy_stack_print ((Bottom), (Top));				\
} while (YYID (0))


/*------------------------------------------------.
| Report that the YYRULE is going to be reduced.  |
`------------------------------------------------*/

#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_reduce_print (YYSTYPE *yyvsp, int yyrule)
#else
static void
yy_reduce_print (yyvsp, yyrule)
    YYSTYPE *yyvsp;
    int yyrule;
#endif
{
  int yynrhs = yyr2[yyrule];
  int yyi;
  unsigned long int yylno = yyrline[yyrule];
  YYFPRINTF (stderr, "Reducing stack by rule %d (line %lu):\n",
	     yyrule - 1, yylno);
  /* The symbols being reduced.  */
  for (yyi = 0; yyi < yynrhs; yyi++)
    {
      YYFPRINTF (stderr, "   $%d = ", yyi + 1);
      yy_symbol_print (stderr, yyrhs[yyprhs[yyrule] + yyi],
		       &(yyvsp[(yyi + 1) - (yynrhs)])
		       		       );
      YYFPRINTF (stderr, "\n");
    }
}

# define YY_REDUCE_PRINT(Rule)		\
do {					\
  if (yydebug)				\
    yy_reduce_print (yyvsp, Rule); \
} while (YYID (0))

/* Nonzero means print parse trace.  It is left uninitialized so that
   multiple parsers can coexist.  */
int yydebug;
#else /* !YYDEBUG */
# define YYDPRINTF(Args)
# define YY_SYMBOL_PRINT(Title, Type, Value, Location)
# define YY_STACK_PRINT(Bottom, Top)
# define YY_REDUCE_PRINT(Rule)
#endif /* !YYDEBUG */


/* YYINITDEPTH -- initial size of the parser's stacks.  */
#ifndef	YYINITDEPTH
# define YYINITDEPTH 200
#endif

/* YYMAXDEPTH -- maximum size the stacks can grow to (effective only
   if the built-in stack extension method is used).

   Do not make this value too large; the results are undefined if
   YYSTACK_ALLOC_MAXIMUM < YYSTACK_BYTES (YYMAXDEPTH)
   evaluated with infinite-precision integer arithmetic.  */

#ifndef YYMAXDEPTH
# define YYMAXDEPTH 10000
#endif



#if YYERROR_VERBOSE

# ifndef yystrlen
#  if defined __GLIBC__ && defined _STRING_H
#   define yystrlen strlen
#  else
/* Return the length of YYSTR.  */
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static YYSIZE_T
yystrlen (const char *yystr)
#else
static YYSIZE_T
yystrlen (yystr)
    const char *yystr;
#endif
{
  YYSIZE_T yylen;
  for (yylen = 0; yystr[yylen]; yylen++)
    continue;
  return yylen;
}
#  endif
# endif

# ifndef yystpcpy
#  if defined __GLIBC__ && defined _STRING_H && defined _GNU_SOURCE
#   define yystpcpy stpcpy
#  else
/* Copy YYSRC to YYDEST, returning the address of the terminating '\0' in
   YYDEST.  */
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static char *
yystpcpy (char *yydest, const char *yysrc)
#else
static char *
yystpcpy (yydest, yysrc)
    char *yydest;
    const char *yysrc;
#endif
{
  char *yyd = yydest;
  const char *yys = yysrc;

  while ((*yyd++ = *yys++) != '\0')
    continue;

  return yyd - 1;
}
#  endif
# endif

# ifndef yytnamerr
/* Copy to YYRES the contents of YYSTR after stripping away unnecessary
   quotes and backslashes, so that it's suitable for yyerror.  The
   heuristic is that double-quoting is unnecessary unless the string
   contains an apostrophe, a comma, or backslash (other than
   backslash-backslash).  YYSTR is taken from yytname.  If YYRES is
   null, do not copy; instead, return the length of what the result
   would have been.  */
static YYSIZE_T
yytnamerr (char *yyres, const char *yystr)
{
  if (*yystr == '"')
    {
      YYSIZE_T yyn = 0;
      char const *yyp = yystr;

      for (;;)
	switch (*++yyp)
	  {
	  case '\'':
	  case ',':
	    goto do_not_strip_quotes;

	  case '\\':
	    if (*++yyp != '\\')
	      goto do_not_strip_quotes;
	    /* Fall through.  */
	  default:
	    if (yyres)
	      yyres[yyn] = *yyp;
	    yyn++;
	    break;

	  case '"':
	    if (yyres)
	      yyres[yyn] = '\0';
	    return yyn;
	  }
    do_not_strip_quotes: ;
    }

  if (! yyres)
    return yystrlen (yystr);

  return yystpcpy (yyres, yystr) - yyres;
}
# endif

/* Copy into YYRESULT an error message about the unexpected token
   YYCHAR while in state YYSTATE.  Return the number of bytes copied,
   including the terminating null byte.  If YYRESULT is null, do not
   copy anything; just return the number of bytes that would be
   copied.  As a special case, return 0 if an ordinary "syntax error"
   message will do.  Return YYSIZE_MAXIMUM if overflow occurs during
   size calculation.  */
static YYSIZE_T
yysyntax_error (char *yyresult, int yystate, int yychar)
{
  int yyn = yypact[yystate];

  if (! (YYPACT_NINF < yyn && yyn <= YYLAST))
    return 0;
  else
    {
      int yytype = YYTRANSLATE (yychar);
      YYSIZE_T yysize0 = yytnamerr (0, yytname[yytype]);
      YYSIZE_T yysize = yysize0;
      YYSIZE_T yysize1;
      int yysize_overflow = 0;
      enum { YYERROR_VERBOSE_ARGS_MAXIMUM = 5 };
      char const *yyarg[YYERROR_VERBOSE_ARGS_MAXIMUM];
      int yyx;

# if 0
      /* This is so xgettext sees the translatable formats that are
	 constructed on the fly.  */
      YY_("syntax error, unexpected %s");
      YY_("syntax error, unexpected %s, expecting %s");
      YY_("syntax error, unexpected %s, expecting %s or %s");
      YY_("syntax error, unexpected %s, expecting %s or %s or %s");
      YY_("syntax error, unexpected %s, expecting %s or %s or %s or %s");
# endif
      char *yyfmt;
      char const *yyf;
      static char const yyunexpected[] = "syntax error, unexpected %s";
      static char const yyexpecting[] = ", expecting %s";
      static char const yyor[] = " or %s";
      char yyformat[sizeof yyunexpected
		    + sizeof yyexpecting - 1
		    + ((YYERROR_VERBOSE_ARGS_MAXIMUM - 2)
		       * (sizeof yyor - 1))];
      char const *yyprefix = yyexpecting;

      /* Start YYX at -YYN if negative to avoid negative indexes in
	 YYCHECK.  */
      int yyxbegin = yyn < 0 ? -yyn : 0;

      /* Stay within bounds of both yycheck and yytname.  */
      int yychecklim = YYLAST - yyn + 1;
      int yyxend = yychecklim < YYNTOKENS ? yychecklim : YYNTOKENS;
      int yycount = 1;

      yyarg[0] = yytname[yytype];
      yyfmt = yystpcpy (yyformat, yyunexpected);

      for (yyx = yyxbegin; yyx < yyxend; ++yyx)
	if (yycheck[yyx + yyn] == yyx && yyx != YYTERROR)
	  {
	    if (yycount == YYERROR_VERBOSE_ARGS_MAXIMUM)
	      {
		yycount = 1;
		yysize = yysize0;
		yyformat[sizeof yyunexpected - 1] = '\0';
		break;
	      }
	    yyarg[yycount++] = yytname[yyx];
	    yysize1 = yysize + yytnamerr (0, yytname[yyx]);
	    yysize_overflow |= (yysize1 < yysize);
	    yysize = yysize1;
	    yyfmt = yystpcpy (yyfmt, yyprefix);
	    yyprefix = yyor;
	  }

      yyf = YY_(yyformat);
      yysize1 = yysize + yystrlen (yyf);
      yysize_overflow |= (yysize1 < yysize);
      yysize = yysize1;

      if (yysize_overflow)
	return YYSIZE_MAXIMUM;

      if (yyresult)
	{
	  /* Avoid sprintf, as that infringes on the user's name space.
	     Don't have undefined behavior even if the translation
	     produced a string with the wrong number of "%s"s.  */
	  char *yyp = yyresult;
	  int yyi = 0;
	  while ((*yyp = *yyf) != '\0')
	    {
	      if (*yyp == '%' && yyf[1] == 's' && yyi < yycount)
		{
		  yyp += yytnamerr (yyp, yyarg[yyi++]);
		  yyf += 2;
		}
	      else
		{
		  yyp++;
		  yyf++;
		}
	    }
	}
      return yysize;
    }
}
#endif /* YYERROR_VERBOSE */


/*-----------------------------------------------.
| Release the memory associated to this symbol.  |
`-----------------------------------------------*/

/*ARGSUSED*/
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yydestruct (const char *yymsg, int yytype, YYSTYPE *yyvaluep)
#else
static void
yydestruct (yymsg, yytype, yyvaluep)
    const char *yymsg;
    int yytype;
    YYSTYPE *yyvaluep;
#endif
{
  YYUSE (yyvaluep);

  if (!yymsg)
    yymsg = "Deleting";
  YY_SYMBOL_PRINT (yymsg, yytype, yyvaluep, yylocationp);

  switch (yytype)
    {

      default:
	break;
    }
}

/* Prevent warnings from -Wmissing-prototypes.  */
#ifdef YYPARSE_PARAM
#if defined __STDC__ || defined __cplusplus
int yyparse (void *YYPARSE_PARAM);
#else
int yyparse ();
#endif
#else /* ! YYPARSE_PARAM */
#if defined __STDC__ || defined __cplusplus
int yyparse (void);
#else
int yyparse ();
#endif
#endif /* ! YYPARSE_PARAM */


/* The lookahead symbol.  */
int yychar;

/* The semantic value of the lookahead symbol.  */
YYSTYPE yylval;

/* Number of syntax errors so far.  */
int yynerrs;



/*-------------------------.
| yyparse or yypush_parse.  |
`-------------------------*/

#ifdef YYPARSE_PARAM
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
int
yyparse (void *YYPARSE_PARAM)
#else
int
yyparse (YYPARSE_PARAM)
    void *YYPARSE_PARAM;
#endif
#else /* ! YYPARSE_PARAM */
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
int
yyparse (void)
#else
int
yyparse ()

#endif
#endif
{


    int yystate;
    /* Number of tokens to shift before error messages enabled.  */
    int yyerrstatus;

    /* The stacks and their tools:
       `yyss': related to states.
       `yyvs': related to semantic values.

       Refer to the stacks thru separate pointers, to allow yyoverflow
       to reallocate them elsewhere.  */

    /* The state stack.  */
    yytype_int16 yyssa[YYINITDEPTH];
    yytype_int16 *yyss;
    yytype_int16 *yyssp;

    /* The semantic value stack.  */
    YYSTYPE yyvsa[YYINITDEPTH];
    YYSTYPE *yyvs;
    YYSTYPE *yyvsp;

    YYSIZE_T yystacksize;

  int yyn;
  int yyresult;
  /* Lookahead token as an internal (translated) token number.  */
  int yytoken;
  /* The variables used to return semantic value and location from the
     action routines.  */
  YYSTYPE yyval;

#if YYERROR_VERBOSE
  /* Buffer for error messages, and its allocated size.  */
  char yymsgbuf[128];
  char *yymsg = yymsgbuf;
  YYSIZE_T yymsg_alloc = sizeof yymsgbuf;
#endif

#define YYPOPSTACK(N)   (yyvsp -= (N), yyssp -= (N))

  /* The number of symbols on the RHS of the reduced rule.
     Keep to zero when no symbol should be popped.  */
  int yylen = 0;

  yytoken = 0;
  yyss = yyssa;
  yyvs = yyvsa;
  yystacksize = YYINITDEPTH;

  YYDPRINTF ((stderr, "Starting parse\n"));

  yystate = 0;
  yyerrstatus = 0;
  yynerrs = 0;
  yychar = YYEMPTY; /* Cause a token to be read.  */

  /* Initialize stack pointers.
     Waste one element of value and location stack
     so that they stay on the same level as the state stack.
     The wasted elements are never initialized.  */
  yyssp = yyss;
  yyvsp = yyvs;

  goto yysetstate;

/*------------------------------------------------------------.
| yynewstate -- Push a new state, which is found in yystate.  |
`------------------------------------------------------------*/
 yynewstate:
  /* In all cases, when you get here, the value and location stacks
     have just been pushed.  So pushing a state here evens the stacks.  */
  yyssp++;

 yysetstate:
  *yyssp = yystate;

  if (yyss + yystacksize - 1 <= yyssp)
    {
      /* Get the current used size of the three stacks, in elements.  */
      YYSIZE_T yysize = yyssp - yyss + 1;

#ifdef yyoverflow
      {
	/* Give user a chance to reallocate the stack.  Use copies of
	   these so that the &'s don't force the real ones into
	   memory.  */
	YYSTYPE *yyvs1 = yyvs;
	yytype_int16 *yyss1 = yyss;

	/* Each stack pointer address is followed by the size of the
	   data in use in that stack, in bytes.  This used to be a
	   conditional around just the two extra args, but that might
	   be undefined if yyoverflow is a macro.  */
	yyoverflow (YY_("memory exhausted"),
		    &yyss1, yysize * sizeof (*yyssp),
		    &yyvs1, yysize * sizeof (*yyvsp),
		    &yystacksize);

	yyss = yyss1;
	yyvs = yyvs1;
      }
#else /* no yyoverflow */
# ifndef YYSTACK_RELOCATE
      goto yyexhaustedlab;
# else
      /* Extend the stack our own way.  */
      if (YYMAXDEPTH <= yystacksize)
	goto yyexhaustedlab;
      yystacksize *= 2;
      if (YYMAXDEPTH < yystacksize)
	yystacksize = YYMAXDEPTH;

      {
	yytype_int16 *yyss1 = yyss;
	union yyalloc *yyptr =
	  (union yyalloc *) YYSTACK_ALLOC (YYSTACK_BYTES (yystacksize));
	if (! yyptr)
	  goto yyexhaustedlab;
	YYSTACK_RELOCATE (yyss_alloc, yyss);
	YYSTACK_RELOCATE (yyvs_alloc, yyvs);
#  undef YYSTACK_RELOCATE
	if (yyss1 != yyssa)
	  YYSTACK_FREE (yyss1);
      }
# endif
#endif /* no yyoverflow */

      yyssp = yyss + yysize - 1;
      yyvsp = yyvs + yysize - 1;

      YYDPRINTF ((stderr, "Stack size increased to %lu\n",
		  (unsigned long int) yystacksize));

      if (yyss + yystacksize - 1 <= yyssp)
	YYABORT;
    }

  YYDPRINTF ((stderr, "Entering state %d\n", yystate));

  if (yystate == YYFINAL)
    YYACCEPT;

  goto yybackup;

/*-----------.
| yybackup.  |
`-----------*/
yybackup:

  /* Do appropriate processing given the current state.  Read a
     lookahead token if we need one and don't already have one.  */

  /* First try to decide what to do without reference to lookahead token.  */
  yyn = yypact[yystate];
  if (yyn == YYPACT_NINF)
    goto yydefault;

  /* Not known => get a lookahead token if don't already have one.  */

  /* YYCHAR is either YYEMPTY or YYEOF or a valid lookahead symbol.  */
  if (yychar == YYEMPTY)
    {
      YYDPRINTF ((stderr, "Reading a token: "));
      yychar = YYLEX;
    }

  if (yychar <= YYEOF)
    {
      yychar = yytoken = YYEOF;
      YYDPRINTF ((stderr, "Now at end of input.\n"));
    }
  else
    {
      yytoken = YYTRANSLATE (yychar);
      YY_SYMBOL_PRINT ("Next token is", yytoken, &yylval, &yylloc);
    }

  /* If the proper action on seeing token YYTOKEN is to reduce or to
     detect an error, take that action.  */
  yyn += yytoken;
  if (yyn < 0 || YYLAST < yyn || yycheck[yyn] != yytoken)
    goto yydefault;
  yyn = yytable[yyn];
  if (yyn <= 0)
    {
      if (yyn == 0 || yyn == YYTABLE_NINF)
	goto yyerrlab;
      yyn = -yyn;
      goto yyreduce;
    }

  /* Count tokens shifted since error; after three, turn off error
     status.  */
  if (yyerrstatus)
    yyerrstatus--;

  /* Shift the lookahead token.  */
  YY_SYMBOL_PRINT ("Shifting", yytoken, &yylval, &yylloc);

  /* Discard the shifted token.  */
  yychar = YYEMPTY;

  yystate = yyn;
  *++yyvsp = yylval;

  goto yynewstate;


/*-----------------------------------------------------------.
| yydefault -- do the default action for the current state.  |
`-----------------------------------------------------------*/
yydefault:
  yyn = yydefact[yystate];
  if (yyn == 0)
    goto yyerrlab;
  goto yyreduce;


/*-----------------------------.
| yyreduce -- Do a reduction.  |
`-----------------------------*/
yyreduce:
  /* yyn is the number of a rule to reduce with.  */
  yylen = yyr2[yyn];

  /* If YYLEN is nonzero, implement the default value of the action:
     `$$ = $1'.

     Otherwise, the following line sets YYVAL to garbage.
     This behavior is undocumented and Bison
     users should not rely upon it.  Assigning to YYVAL
     unconditionally makes the parser a bit smaller, and it avoids a
     GCC warning that YYVAL may be used uninitialized.  */
  yyval = yyvsp[1-yylen];


  YY_REDUCE_PRINT (yyn);
  switch (yyn)
    {
        case 4:

/* Line 1455 of yacc.c  */
#line 2178 "semantic.y"
    { if(use_indent) yyerror("Punto y coma innecesario en modo indentacion"); ;}
    break;

  case 5:

/* Line 1455 of yacc.c  */
#line 2179 "semantic.y"
    { if(!use_indent) yyerror("Se esperaba un punto y coma en modo bloque"); ;}
    break;

  case 19:

/* Line 1455 of yacc.c  */
#line 2196 "semantic.y"
    {  
      // Crear el nodo para la instrucción print
      // Primero, verificamos si $3 es una variable declarada
      if(compile_mode){
       
      } else{
      symbol* s = find_variable((yyvsp[(3) - (4)].sval));
      char* val1 = get_var((yyvsp[(3) - (4)].sval)) ? get_var((yyvsp[(3) - (4)].sval)) : (yyvsp[(3) - (4)].sval);
      if (s) { // SI es una variable
          // Comprobamos si la variable tiene una operación guardada
          if (s->operation_str != NULL) {
              // Si la tiene, la usamos para crear el nodo
              (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("Operation", s->operation_str, NULL, create_node("variableName", s->name, NULL, NULL)));
          } else {
              // Si no, creamos el nodo simple
              (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("ParamType", s->type, NULL, create_node("variableName", s->name, NULL, NULL)));
          }
      } else { // NO es una variable (es un literal o una operación directa)
          if (valid == 1) {
              con_op = reconstruct_expression();
              (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("Operation", con_op, NULL, NULL));
              valid = 0;
          } else {
              (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("ParamType", determine_type((yyvsp[(3) - (4)].sval)), NULL, NULL));
          }
       }
      }
      generate_ast_file((yyval.node));
     ;}
    break;

  case 20:

/* Line 1455 of yacc.c  */
#line 2226 "semantic.y"
    { // Post-incremento: x++
                              handle_increment_decrement((yyvsp[(1) - (2)].sval), "++");
                              (yyval.node) = create_node("PostIncrementStatement", (yyvsp[(1) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 21:

/* Line 1455 of yacc.c  */
#line 2230 "semantic.y"
    { // Post-decremento: x--
                              handle_increment_decrement((yyvsp[(1) - (2)].sval), "--");
                              (yyval.node) = create_node("PostDecrementStatement", (yyvsp[(1) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 22:

/* Line 1455 of yacc.c  */
#line 2234 "semantic.y"
    { // Pre-incremento: ++x
                              handle_increment_decrement((yyvsp[(2) - (2)].sval), "++");
                              (yyval.node) = create_node("PreIncrementStatement", (yyvsp[(2) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 23:

/* Line 1455 of yacc.c  */
#line 2238 "semantic.y"
    { // Pre-decremento: --x
                              handle_increment_decrement((yyvsp[(2) - (2)].sval), "--");
                              (yyval.node) = create_node("PreDecrementStatement", (yyvsp[(2) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 24:

/* Line 1455 of yacc.c  */
#line 2245 "semantic.y"
    { 
     if (compile_mode){
         
            declare_var((yyvsp[(2) - (2)].sval),NULL,NULL,false,NULL);
            ast_node* expression_tree_root = create_node("Literal", "NULL", create_node("Type", "NULL", NULL, NULL), NULL);
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (2)].sval), initializer_node, NULL);   generate_ast_file((yyval.node));
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }
     }else{
      declare_var((yyvsp[(2) - (2)].sval),"NULL","NULL",false,NULL);
      (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (2)].sval), create_node("Value","NULL", create_node("Type","NULL",NULL,NULL),NULL), NULL); generate_ast_file((yyval.node));  }
   ;}
    break;

  case 25:

/* Line 1455 of yacc.c  */
#line 2260 "semantic.y"
    {
     if (compile_mode) {
         char * expr = determine_type((yyvsp[(4) - (4)].sval));
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,NULL);
            ast_node* expression_tree_root = pop_node();
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), initializer_node, NULL);   generate_ast_file((yyval.node));
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }
        }else{
     // Crear el nodo para una asignación
      char * expr = determine_type((yyvsp[(4) - (4)].sval));
      if (strcmp((yyvsp[(4) - (4)].sval), VOID_RESULT_MARKER) == 0) {
           char error_msg[256];
           sprintf(error_msg, "Line %d: Cannot assign result of a void function to variable '%s'", yylineno, (yyvsp[(2) - (4)].sval));
           yyerror(error_msg);
           exit(1);
       }else{
        
       
        
        if(valid==1){
             con_op = reconstruct_expression();
             declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,con_op);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file((yyval.node));
           valid = 0;
        }else if(valid==0){
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,NULL);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),NULL), NULL); generate_ast_file((yyval.node)); 
        }

    }
    }
   ;}
    break;

  case 26:

/* Line 1455 of yacc.c  */
#line 2296 "semantic.y"
    {
    
     if(compile_mode){
        
        int prop_count = 0;
        // 1. La nueva función crea el sub-árbol de "properties" a partir del string
        ast_node* properties_node = create_properties_from_string((yyvsp[(5) - (6)].sval), &prop_count);

        // 2. Creamos los nodos "type" y "Longitud"
        ast_node* type_node = create_node("type", "Dict", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(prop_count), NULL, NULL);

        // 3. Enlazamos los nodos hijos en una cadena (type -> longitud -> properties)
        type_node->right = len_node;
        len_node->right = properties_node;

        // 4. Creamos el nodo principal "DictLiteral"
        ast_node* dict_literal_node = create_node("DictLiteral", NULL, type_node, NULL);

        // 5. Creamos el nodo de declaración final
        (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), dict_literal_node, NULL);
        generate_ast_file((yyval.node));

     }else{
    char buffer[4096];
    sprintf(buffer, "{%s}", (yyvsp[(5) - (6)].sval)); // Envuelve el contenido con llaves
    declare_var((yyvsp[(2) - (6)].sval), buffer, "Dict", false, NULL);
    (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
    generate_ast_file((yyval.node));
   }
   ;}
    break;

  case 27:

/* Line 1455 of yacc.c  */
#line 2327 "semantic.y"
    {
    if(compile_mode){
        int prop_count = 0;
        // 1. La nueva función crea el sub-árbol de "properties" a partir del string
        ast_node* properties_node = create_properties_from_string((yyvsp[(5) - (5)].sval), &prop_count);

        // 2. Creamos los nodos "type" y "Longitud"
        ast_node* type_node = create_node("type", "Dict", NULL, NULL);
        ast_node* len_node = create_node("Longitud", to_string(prop_count), NULL, NULL);

        // 3. Enlazamos los nodos hijos en una cadena (type -> longitud -> properties)
        type_node->right = len_node;
        len_node->right = properties_node;

        // 4. Creamos el nodo principal "DictLiteral"
        ast_node* dict_literal_node = create_node("DictLiteral", NULL, type_node, NULL);

        // 5. Creamos el nodo de declaración final
        (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (5)].sval), dict_literal_node, NULL);
        generate_ast_file((yyval.node));
    }else{
    if(get_var((yyvsp[(1) - (5)].sval))){
        char buffer[4096];
        sprintf(buffer, "{%s}", (yyvsp[(4) - (5)].sval)); // Envuelve el contenido con llaves
        reassign_var_with_type((yyvsp[(1) - (5)].sval), buffer, "Dict");
        (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (5)].sval), create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
    } else {
        char error_msg[256];
        sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, (yyvsp[(1) - (5)].sval));
        yyerror(error_msg);
        exit(1);
    }
    }
   ;}
    break;

  case 28:

/* Line 1455 of yacc.c  */
#line 2362 "semantic.y"
    {
    if(compile_mode){
              // Parseamos el rango para crear un nodo estructurado
            int start_val, end_val;
            sscanf((yyvsp[(4) - (4)].sval), "%d..%d", &start_val, &end_val);
            ast_node* start_node = create_node("NumericLiteral", to_string(start_val), NULL, NULL);
            ast_node* end_node = create_node("NumericLiteral", to_string(end_val), NULL, NULL);
            ast_node* start = create_node("Start", NULL, start_node, NULL);
            ast_node* end = create_node("End", NULL, end_node, NULL);
            ast_node* range_node = create_node("RangeExpression", NULL, start, end);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), range_node, NULL);
            generate_ast_file((yyval.node));
    }else{
     declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),"Range",false, NULL);
     (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type","Range",NULL,NULL),NULL), NULL); generate_ast_file((yyval.node));
    }  
  ;}
    break;

  case 29:

/* Line 1455 of yacc.c  */
#line 2379 "semantic.y"
    { 
        if (compile_mode) {
            ast_node* expression_tree_root = pop_node();
            ast_node* value_node = create_node("Value", NULL, expression_tree_root, NULL);
            (yyval.node) = create_node("VariableAssignment", (yyvsp[(1) - (3)].sval), value_node, NULL);
            generate_ast_file((yyval.node));
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la asignacion.\n");
                stack_tops = -1;
            }
        } else{
       printf("assign: %s\n",(yyvsp[(3) - (3)].sval));
        if (strcmp((yyvsp[(3) - (3)].sval), VOID_RESULT_MARKER) == 0) {
           char error_msg[256];
           sprintf(error_msg, "Line %d: Cannot assign result of a void function to variable '%s'", yylineno, (yyvsp[(1) - (3)].sval));
           yyerror(error_msg);
           exit(1);
       } else{
        if (find_variable((yyvsp[(1) - (3)].sval))) {
             if (valid == 1) {
                 con_op = reconstruct_expression();
                 char * expr = determine_type((yyvsp[(3) - (3)].sval));
                 reassign_var((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval), con_op);
                 (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (3)].sval), create_node("Value", (yyvsp[(3) - (3)].sval), create_node("Type", expr, NULL, NULL), create_node("Operation", con_op, NULL, NULL)), NULL); 
                 generate_ast_file((yyval.node));
                 valid = 0;
             } else if (valid == 0) {
                 reassign_var((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval), NULL);
                 char * expr = determine_type((yyvsp[(3) - (3)].sval));
                 (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (3)].sval), create_node("Value", (yyvsp[(3) - (3)].sval), create_node("Type", expr, NULL, NULL), NULL), NULL); 
                 generate_ast_file((yyval.node));
             }
       }else{
         char error_msg[256];
         sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, (yyvsp[(1) - (3)].sval));
         yyerror(error_msg);
         exit(1);
       }
     }
   }
   ;}
    break;

  case 30:

/* Line 1455 of yacc.c  */
#line 2421 "semantic.y"
    {
    if(compile_mode){
        char* default_value = get_default_value_for_type((yyvsp[(1) - (2)].sval));
         declare_var((yyvsp[(2) - (2)].sval),default_value,(yyvsp[(1) - (2)].sval),true, NULL);
       ast_node* expression_tree_root = create_node("Literal", default_value, create_node("Type", (yyvsp[(1) - (2)].sval), NULL, NULL), NULL);
            ast_node* type_node = create_node("ExplicitType", (yyvsp[(1) - (2)].sval), NULL, NULL);
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (2)].sval), initializer_node, type_node);
            generate_ast_file((yyval.node));
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }  
    }else{
      char* explicit_type = (yyvsp[(1) - (2)].sval);
    // 2. Obtenemos el valor por defecto para ese tipo (ej. "0")
    char* default_value = get_default_value_for_type(explicit_type);
     declare_var((yyvsp[(2) - (2)].sval),default_value,(yyvsp[(1) - (2)].sval),true, NULL);
      (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (2)].sval), create_node("Value",default_value, create_node("Type",(yyvsp[(1) - (2)].sval),NULL,NULL),create_node("ExplicitType",(yyvsp[(1) - (2)].sval),NULL,NULL)), NULL); generate_ast_file((yyval.node));
    }
 ;}
    break;

  case 31:

/* Line 1455 of yacc.c  */
#line 2442 "semantic.y"
    {
     // Crear el nodo para una asignación
      
      if(compile_mode){
      ast_node* expression_tree_root = pop_node();
            ast_node* type_node = create_node("ExplicitType", (yyvsp[(1) - (4)].sval), NULL, NULL);
            ast_node* initializer_node = create_node("Initializer", NULL, expression_tree_root, NULL);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), initializer_node, type_node);
            generate_ast_file((yyval.node));
            if (stack_tops != -1) {
                fprintf(stderr, "Advertencia: La pila de nodos no quedo vacia despues de la declaracion.\n");
                stack_tops = -1;
            }
      }else{
      char * expr = determine_type((yyvsp[(4) - (4)].sval));
      printf("types es: %s\n",(yyvsp[(4) - (4)].sval));
      if(strcmp((yyvsp[(1) - (4)].sval),expr) == 0){
        if(valid==1){
           con_op = reconstruct_expression(); 
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),(yyvsp[(1) - (4)].sval),true,con_op);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,create_node("ExplicitType",(yyvsp[(1) - (4)].sval),NULL,NULL)),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file((yyval.node));
           valid = 0;
        }else if(valid==0){
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),(yyvsp[(1) - (4)].sval),true,NULL);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),create_node("ExplicitType",(yyvsp[(1) - (4)].sval),NULL,NULL)), NULL); generate_ast_file((yyval.node)); 
        }
       }
       }
     ;}
    break;

  case 35:

/* Line 1455 of yacc.c  */
#line 2476 "semantic.y"
    {
       if(compile_mode){
         char buffer[4096];
            sprintf(buffer, "(%s)", (yyvsp[(5) - (6)].sval));
            // La nueva función despachadora también funciona para tuplas.
            ast_node* tuple_literal_node = create_ast_from_literal_string(buffer);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), tuple_literal_node, NULL);
            generate_ast_file((yyval.node));
       } else{
        char buffer[2048];
        sprintf(buffer, "(%s)", (yyvsp[(5) - (6)].sval));
        declare_var((yyvsp[(2) - (6)].sval), buffer, "Tuple", false,NULL);
        
        (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
      }
;}
    break;

  case 36:

/* Line 1455 of yacc.c  */
#line 2494 "semantic.y"
    {
        char buffer[2048];
        sprintf(buffer, "(%s,)", (yyvsp[(5) - (7)].sval));
        declare_var((yyvsp[(2) - (7)].sval), buffer, "Tuple", false,NULL);
        (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (7)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 37:

/* Line 1455 of yacc.c  */
#line 2505 "semantic.y"
    {
         
        char buffer[2048];
        sprintf(buffer, "(%s)", (yyvsp[(4) - (5)].sval));
       reassign_var((yyvsp[(1) - (5)].sval), buffer,NULL);
        (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (5)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 38:

/* Line 1455 of yacc.c  */
#line 2515 "semantic.y"
    {
        
        char buffer[2048];
        sprintf(buffer, "(%s,)", (yyvsp[(4) - (6)].sval));
       reassign_var((yyvsp[(1) - (6)].sval), buffer,NULL);
        (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (6)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 39:

/* Line 1455 of yacc.c  */
#line 2526 "semantic.y"
    {
         if(compile_mode){
          char buffer[4096];
            sprintf(buffer, "[%s]", (yyvsp[(5) - (6)].sval));
            // La nueva función despachadora hace todo el trabajo pesado.
            ast_node* array_literal_node = create_ast_from_literal_string(buffer);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), array_literal_node, NULL);
            generate_ast_file((yyval.node));
         }else{
          char buffer[2048];
           sprintf(buffer, "[%s]", (yyvsp[(5) - (6)].sval));
           declare_var((yyvsp[(2) - (6)].sval),buffer,"Array",false,NULL);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 1;
           printf("%s\n",buffer);
           }
        ;}
    break;

  case 40:

/* Line 1455 of yacc.c  */
#line 2543 "semantic.y"
    {
            char buffer[2048];
          sprintf(buffer, "[%s]", (yyvsp[(8) - (9)].sval));
            declare_var((yyvsp[(2) - (9)].sval),buffer,"Array",false,NULL);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (9)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("Limit",to_string((yyvsp[(4) - (9)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
         ;}
    break;

  case 41:

/* Line 1455 of yacc.c  */
#line 2550 "semantic.y"
    {
            char buffer[2048];
          sprintf(buffer, "[%s]", (yyvsp[(5) - (6)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(5) - (6)].sval)));
           if(strcmp(determineArrayType((yyvsp[(5) - (6)].sval)),(yyvsp[(1) - (6)].sval))== 0){
            declare_var((yyvsp[(2) - (6)].sval),buffer,"Array",true,NULL);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("ExplicitType",(yyvsp[(1) - (6)].sval),NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
             fprintf(stderr, "Error valor inconpatible.\n"); 
            }
         ;}
    break;

  case 42:

/* Line 1455 of yacc.c  */
#line 2562 "semantic.y"
    {
           if(strcmp(determineArrayType((yyvsp[(8) - (9)].sval)),(yyvsp[(1) - (9)].sval))== 0){  
            char buffer[2048];
           sprintf(buffer, "[%s]", (yyvsp[(8) - (9)].sval));
           declare_var((yyvsp[(2) - (9)].sval),buffer,"Array",true,NULL);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (9)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",create_node("ExplicitType",(yyvsp[(1) - (9)].sval),NULL,NULL),create_node("Limit",to_string((yyvsp[(4) - (9)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 1;
           }
         ;}
    break;

  case 43:

/* Line 1455 of yacc.c  */
#line 2571 "semantic.y"
    {
           if(strcmp((yyvsp[(1) - (5)].sval),(yyvsp[(1) - (5)].sval))== 0){  
           declare_var((yyvsp[(2) - (5)].sval),NULL,"Array",true,NULL);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (5)].sval), create_node("Value","[]", create_node("Type","Array",create_node("ExplicitType",(yyvsp[(1) - (5)].sval),NULL,NULL),create_node("Limit",to_string((yyvsp[(4) - (5)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           }
         ;}
    break;

  case 44:

/* Line 1455 of yacc.c  */
#line 2578 "semantic.y"
    {
           if(strcmp((yyvsp[(1) - (4)].sval),(yyvsp[(1) - (4)].sval))== 0){
           declare_var((yyvsp[(2) - (4)].sval),NULL,"Array",true,NULL);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value","[]", create_node("Type","Array",NULL,create_node("ExplicitType",(yyvsp[(1) - (4)].sval),NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           }
         ;}
    break;

  case 45:

/* Line 1455 of yacc.c  */
#line 2586 "semantic.y"
    {
             //char * expr = determine_type($3);
             (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (3)].sval), create_node("Value","[]", create_node("Type","Array",NULL ,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
             longitud = 0;
              reassign_var_with_type((yyvsp[(1) - (3)].sval), "[]", "Array");
            ;}
    break;

  case 46:

/* Line 1455 of yacc.c  */
#line 2592 "semantic.y"
    {
             //if(strcmp(determineArrayType($4),$1)== 0){
             symbol* s = find_variable((yyvsp[(1) - (5)].sval));
             char buffer[2048];
             sprintf(buffer, "[%s]", (yyvsp[(4) - (5)].sval));
             // 2. Si no se encuentra, es un error semántico
              if (!s) {
               char error_msg[256];
               sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, (yyvsp[(1) - (5)].sval));
               yyerror(error_msg);
               exit(1); // Detener el análisis
              }
               reassign_var_with_type((yyvsp[(1) - (5)].sval), buffer, "Array");
                printf("entro\n");
                (yyval.node) = create_node("VariableAsignement", (yyvsp[(1) - (5)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
                longitud = 1; 
             // } 
            ;}
    break;

  case 47:

/* Line 1455 of yacc.c  */
#line 2611 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 48:

/* Line 1455 of yacc.c  */
#line 2613 "semantic.y"
    {
             // Un elemento ahora puede ser un diccionario literal
             char buffer[4096];
             sprintf(buffer, "{%s}", (yyvsp[(2) - (3)].sval));
             (yyval.sval) = strdup(buffer);
           ;}
    break;

  case 49:

/* Line 1455 of yacc.c  */
#line 2619 "semantic.y"
    {
             // Un elemento también puede ser una tupla literal
             char buffer[2048];
             sprintf(buffer, "(%s)", (yyvsp[(2) - (3)].sval));
             (yyval.sval) = strdup(buffer);
         ;}
    break;

  case 50:

/* Line 1455 of yacc.c  */
#line 2625 "semantic.y"
    {
             // Un elemento también puede ser una tupla literal
             char buffer[2048];
             sprintf(buffer, "(%s,)", (yyvsp[(2) - (4)].sval));
             (yyval.sval) = strdup(buffer);
         ;}
    break;

  case 51:

/* Line 1455 of yacc.c  */
#line 2631 "semantic.y"
    {
          char buffer[4096];
          sprintf(buffer, "[%s]", (yyvsp[(2) - (3)].sval));
          (yyval.sval) = strdup(buffer);
         ;}
    break;

  case 52:

/* Line 1455 of yacc.c  */
#line 2638 "semantic.y"
    {
         (yyval.sval) = strdup("[]");
        ;}
    break;

  case 53:

/* Line 1455 of yacc.c  */
#line 2642 "semantic.y"
    {
                    longitud = 1;
                    (yyval.sval) = (yyvsp[(1) - (1)].sval);
                ;}
    break;

  case 54:

/* Line 1455 of yacc.c  */
#line 2646 "semantic.y"
    {
                    // Tu lógica de concatenación para formar el string de la lista
                    char* tempList = concat_strings((yyvsp[(1) - (3)].sval), ", ");
                    (yyval.sval) = concat_strings(tempList, (yyvsp[(3) - (3)].sval));
                    free(tempList);
                    longitud++;
                ;}
    break;

  case 55:

/* Line 1455 of yacc.c  */
#line 2654 "semantic.y"
    { 
        (yyval.node) = create_node("CallExpression", "read", create_node("Arguments", (yyvsp[(3) - (4)].sval), NULL, NULL), create_node("Type",determine_type(get_var((yyvsp[(3) - (4)].sval))),NULL,NULL)); generate_ast_file((yyval.node)); 
     ;}
    break;

  case 56:

/* Line 1455 of yacc.c  */
#line 2658 "semantic.y"
    {  
     //declare_var($2,"0","int");
     (yyval.sval) = (yyvsp[(2) - (3)].sval);
    ;}
    break;

  case 57:

/* Line 1455 of yacc.c  */
#line 2663 "semantic.y"
    { 
          char buffer[40]; 
          sprintf(buffer, "%s..%s", (yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval)); 
         (yyval.sval) = strdup(buffer);   
     ;}
    break;

  case 58:

/* Line 1455 of yacc.c  */
#line 2668 "semantic.y"
    {
           char buffer[40];
           sprintf(buffer, "%s..<%s", (yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval));
           (yyval.sval) = strdup(buffer);
     ;}
    break;

  case 59:

/* Line 1455 of yacc.c  */
#line 2674 "semantic.y"
    { (yyval.node) = create_node("BlockStart", NULL, NULL, NULL); blockcode++; ;}
    break;

  case 60:

/* Line 1455 of yacc.c  */
#line 2677 "semantic.y"
    { (yyval.node) = create_node("BlockEnd", NULL, NULL, NULL); blockcode--; ;}
    break;

  case 61:

/* Line 1455 of yacc.c  */
#line 2679 "semantic.y"
    { (yyval.node) = create_node("CallExpression", "Break", NULL, NULL); ;}
    break;

  case 62:

/* Line 1455 of yacc.c  */
#line 2680 "semantic.y"
    { 
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
                         char* actual_type = determine_type((yyvsp[(2) - (2)].sval)); // Tipo del valor retornado
                         
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
                         func->return_value = strdup((yyvsp[(2) - (2)].sval));
                     }
                 }
             } else {
                 yyerror("Error: 'return' used outside of a function."); exit(1);
             }

             // Creamos el nodo del AST para la sentencia 'return'.
             (yyval.node) = create_node("CallExpression", "Return", create_node("value", (yyvsp[(2) - (2)].sval), NULL, NULL), NULL);
            ;}
    break;

  case 63:

/* Line 1455 of yacc.c  */
#line 2723 "semantic.y"
    { enter_scope(); ;}
    break;

  case 64:

/* Line 1455 of yacc.c  */
#line 2723 "semantic.y"
    { exit_scope(); ;}
    break;

  case 65:

/* Line 1455 of yacc.c  */
#line 2723 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 66:

/* Line 1455 of yacc.c  */
#line 2724 "semantic.y"
    { enter_scope(); ;}
    break;

  case 67:

/* Line 1455 of yacc.c  */
#line 2724 "semantic.y"
    { exit_scope(); ;}
    break;

  case 68:

/* Line 1455 of yacc.c  */
#line 2724 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 69:

/* Line 1455 of yacc.c  */
#line 2726 "semantic.y"
    { 
     enter_scope();
     declare_var((yyvsp[(3) - (5)].sval),(yyvsp[(4) - (5)].sval),"int",false, NULL); 
      printf("for condition: %s\n",(yyvsp[(4) - (5)].sval));
    ;}
    break;

  case 70:

/* Line 1455 of yacc.c  */
#line 2730 "semantic.y"
    {
         //declare_var($3,$4); 
         printf("for condition: %s\n",find_variable((yyvsp[(3) - (7)].sval))->value);
     
         if(strcmp(get_type((yyvsp[(3) - (7)].sval)),"Range") == 0){
          (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Range", "0..0", NULL, create_node("Condition", "false", NULL, NULL)), (yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));         
         if (greaterRanges((yyvsp[(4) - (7)].sval))){
            (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Range", (yyvsp[(4) - (7)].sval), NULL, create_node("Condition", "false", NULL, NULL)), (yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
           }else{
            (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Range", (yyvsp[(4) - (7)].sval), create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),(yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
           }
         }else{
          (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Iterator", (yyvsp[(4) - (7)].sval), create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),(yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
  
         }
         exit_scope();
  //printf("%s\n",determine_type(get_var($4)));
       ;}
    break;

  case 71:

/* Line 1455 of yacc.c  */
#line 2748 "semantic.y"
    {
         declare_var((yyvsp[(3) - (7)].sval),(yyvsp[(4) - (7)].sval),"int",false,NULL); 
         printf("for condition: %s\n",(yyvsp[(4) - (7)].sval));
         if(strcmp(get_type((yyvsp[(4) - (7)].sval)),"Range") == 0){
          (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Range", "0..0", NULL, create_node("Condition", "false", NULL, NULL)), (yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
           if (greaterRanges((yyvsp[(4) - (7)].sval))){
            (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Range", (yyvsp[(4) - (7)].sval), NULL, create_node("Condition", "false", NULL, NULL)), (yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
           }else{
            (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Range", (yyvsp[(4) - (7)].sval), create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),(yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
           }
         }else{
          (yyval.node) = create_node("ForLoop", (yyvsp[(3) - (7)].sval), create_node("Iterator", get_var((yyvsp[(4) - (7)].sval)), create_node("declared","true",NULL, create_node("Condition", "true", NULL, NULL)), NULL),(yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
  
         }
  //printf("%s\n",determine_type(get_var($4)));
       ;}
    break;

  case 72:

/* Line 1455 of yacc.c  */
#line 2765 "semantic.y"
    {
          if(!use_indent){
            char *comparison_str = strdup((yyvsp[(3) - (5)].sval)); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
           (yyval.node) = create_node("WhileLoop",comparison,create_node("ConditionIs",(yyvsp[(3) - (5)].sval),NULL,NULL),(yyvsp[(5) - (5)].node)); generate_ast_file((yyval.node));
          }
          ;}
    break;

  case 73:

/* Line 1455 of yacc.c  */
#line 2777 "semantic.y"
    {
            printf("ident\n");
             (yyval.node) = create_node("WhileLoop",comparison,create_node("ConditionIs",(yyvsp[(3) - (6)].sval),NULL,NULL),(yyvsp[(6) - (6)].node)); generate_ast_file((yyval.node));  
            
          ;}
    break;

  case 74:

/* Line 1455 of yacc.c  */
#line 2783 "semantic.y"
    {
                        // $2 es el bloque de código que se ejecuta primero.
                        // $5 es la condición que se evalúa después.
                        char *comparison_str = strdup((yyvsp[(5) - (6)].sval)); // Clonar la cadena concatenada
                        char *result = strchr(comparison_str, ','); // Buscar la coma
                        if (result != NULL) {
                         *result = '\0'; // Separar comparación
                          result++;       // Apuntar al valor lógico
                        }
                        (yyval.node) = create_node("PerformWhileLoop", result, create_node("ConditionIs", comparison_str, NULL, NULL), (yyvsp[(2) - (6)].node));
                        generate_ast_file((yyval.node));
                  ;}
    break;

  case 75:

/* Line 1455 of yacc.c  */
#line 2795 "semantic.y"
    {
                        // $2 es el bloque de código que se ejecuta primero.
                        // $5 es la condición que se evalúa después.
                        char *comparison_str = strdup((yyvsp[(6) - (7)].sval)); // Clonar la cadena concatenada
                        char *result = strchr(comparison_str, ','); // Buscar la coma
                        if (result != NULL) {
                         *result = '\0'; // Separar comparación
                          result++;       // Apuntar al valor lógico
                        }
                        (yyval.node) = create_node("PerformWhileLoop", result, create_node("ConditionIs", comparison_str, NULL, NULL), (yyvsp[(3) - (7)].node));
                        generate_ast_file((yyval.node));
                  ;}
    break;

  case 76:

/* Line 1455 of yacc.c  */
#line 2809 "semantic.y"
    {
             if (compile_mode) {
                          ast_node* body_node = (yyvsp[(5) - (5)].node);
                    // El árbol de la condición está esperando en la pila.
                    ast_node* condition_node = pop_node();
                    (yyval.node) = create_node("IfStatement", NULL,condition_node,body_node);
                    generate_ast_file((yyval.node));
                }else{
                char *comparison_str = strdup((yyvsp[(3) - (5)].sval)); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               (yyval.node) = create_node("if_Condition",result,NULL,(yyvsp[(5) - (5)].node)); generate_ast_file((yyval.node));
               free(comparison_str);
               }
            ;}
    break;

  case 77:

/* Line 1455 of yacc.c  */
#line 2827 "semantic.y"
    {
                 if (compile_mode) {
                          ast_node* body_node = (yyvsp[(6) - (6)].node);
                    // El árbol de la condición está esperando en la pila.
                    ast_node* condition_node = pop_node();
                    (yyval.node) = create_node("IfStatement", NULL,condition_node,body_node);
                    generate_ast_file((yyval.node));
                }else{
                char *comparison_str = strdup((yyvsp[(3) - (6)].sval)); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               (yyval.node) = create_node("if_Condition",result,NULL,(yyvsp[(6) - (6)].node)); generate_ast_file((yyval.node));
               free(comparison_str);
               }
           
            ;}
    break;

  case 78:

/* Line 1455 of yacc.c  */
#line 2846 "semantic.y"
    {
                 if (compile_mode) {
                    // El árbol de la condición está en la pila
                    ast_node* condition_node = pop_node();
                    // El árbol del 'else' o 'elseif' viene de $6
                    ast_node* else_node = (yyvsp[(6) - (6)].node);
                    // El árbol del bloque principal viene de $5
                    ast_node* body_node = (yyvsp[(5) - (6)].node);
                    
                    // Enlazamos el 'else' al 'body' para formar la cadena
                    body_node->right = else_node;
                    
                    // Creamos el nodo IfStatement final
                    (yyval.node) = create_node("IfStatement", NULL, condition_node, body_node);
                    generate_ast_file((yyval.node));

                 }else{
                //printf("%s\n",conditions[0]);
                char *comparison_str = strdup((yyvsp[(3) - (6)].sval)); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               // printf("%s\n",$3);
                (yyval.node) = create_node("if_Condition",result,(yyvsp[(5) - (6)].node),(yyvsp[(6) - (6)].node)); generate_ast_file((yyval.node));
                free(comparison_str);
                }
            ;}
    break;

  case 79:

/* Line 1455 of yacc.c  */
#line 2875 "semantic.y"
    {
             if (compile_mode) {
                    // El árbol de la condición está en la pila
                    ast_node* condition_node = pop_node();
                    // El árbol del 'else' o 'elseif' viene de $6
                    ast_node* else_node = (yyvsp[(7) - (8)].node);
                    // El árbol del bloque principal viene de $5
                    ast_node* body_node = (yyvsp[(6) - (8)].node);
                    
                    // Enlazamos el 'else' al 'body' para formar la cadena
                    body_node->right = else_node;
                    
                    // Creamos el nodo IfStatement final
                    (yyval.node) = create_node("IfStatement", NULL, condition_node, body_node);
                    generate_ast_file((yyval.node));

                 }else{
                //printf("%s\n",conditions[0]);
                char *comparison_str = strdup((yyvsp[(3) - (8)].sval)); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
               // printf("%s\n",$3);
                (yyval.node) = create_node("if_Condition",result,(yyvsp[(6) - (8)].node),(yyvsp[(7) - (8)].node)); generate_ast_file((yyval.node));
                free(comparison_str);
                }
            ;}
    break;

  case 80:

/* Line 1455 of yacc.c  */
#line 2904 "semantic.y"
    {
                  if (compile_mode) {
             // 1. Sacamos los nodos de la pila (el último en entrar es el primero en salir)
                   ast_node* else_if_condition_node = pop_node(); // Condición del ELSE_IF ($8)
                   ast_node* if_condition_node = pop_node();      // Condición del IF ($3)

             // 2. Obtenemos los nodos de los bloques de código
                    ast_node* if_body_node = (yyvsp[(5) - (10)].node);
                    ast_node* else_if_body_node = (yyvsp[(10) - (10)].node);

                    // 3. Creamos el nodo anidado para la parte "else if".
                   //    Lo tratamos como un IfStatement completo en sí mismo.
                   ast_node* else_if_statement_node = create_node("IfStatement", NULL, else_if_condition_node, else_if_body_node);

                    // 4. Siguiendo tu patrón, enlazamos la rama "else" al hijo derecho del bloque principal.
                    if_body_node->right = else_if_statement_node;

                  // 5. Creamos el nodo IfStatement principal
                      (yyval.node) = create_node("IfStatement", NULL, if_condition_node, if_body_node);
                     generate_ast_file((yyval.node));
                  }else{  
                   char *if_comparison_str = strdup((yyvsp[(3) - (10)].sval));
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup((yyvsp[(8) - (10)].sval));
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                (yyval.node) = create_node("if_Condition",if_result,(yyvsp[(5) - (10)].node),create_node("ElseIf", elseif_result, (yyvsp[(10) - (10)].node), NULL)); generate_ast_file((yyval.node));
              }
            ;}
    break;

  case 81:

/* Line 1455 of yacc.c  */
#line 2942 "semantic.y"
    {
                  if (compile_mode) {
             // 1. Sacamos los nodos de la pila (el último en entrar es el primero en salir)
                   ast_node* else_if_condition_node = pop_node(); // Condición del ELSE_IF ($9)
                   ast_node* if_condition_node = pop_node();      // Condición del IF ($3)

             // 2. Obtenemos los nodos de los bloques de código
                    ast_node* if_body_node = (yyvsp[(6) - (12)].node);
                    ast_node* else_if_body_node = (yyvsp[(12) - (12)].node);

                    // 3. Creamos el nodo anidado para la parte "else if".
                   //    Lo tratamos como un IfStatement completo en sí mismo.
                   ast_node* else_if_statement_node = create_node("IfStatement", NULL, else_if_condition_node, else_if_body_node);

                    // 4. Siguiendo tu patrón, enlazamos la rama "else" al hijo derecho del bloque principal.
                    if_body_node->right = else_if_statement_node;

                  // 5. Creamos el nodo IfStatement principal
                      (yyval.node) = create_node("IfStatement", NULL, if_condition_node, if_body_node);
                     generate_ast_file((yyval.node));
                  }else{
                 char *if_comparison_str = strdup((yyvsp[(3) - (12)].sval));
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup((yyvsp[(9) - (12)].sval));
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                (yyval.node) = create_node("if_Condition",if_comparison_str,(yyvsp[(6) - (12)].node),create_node("ElseIf", elseif_result, (yyvsp[(12) - (12)].node), NULL)); generate_ast_file((yyval.node));
            }
            ;}
    break;

  case 82:

/* Line 1455 of yacc.c  */
#line 2980 "semantic.y"
    {
                   if (compile_mode) {
                     // 1. Sacamos los nodos de la pila en orden inverso
                       ast_node* else_if_cond_node = pop_node(); // Condición del ELSE_IF ($8)
                       ast_node* if_cond_node = pop_node();      // Condición del IF ($3)

                       // 2. Obtenemos los nodos de los bloques
                       ast_node* if_body_node = (yyvsp[(5) - (11)].node);
                       ast_node* else_if_body_node = (yyvsp[(10) - (11)].node);
                      ast_node* final_else_node = (yyvsp[(11) - (11)].node); // Este es el 'condtional_stmt' (ElseStatement)

                     // 3. Construimos la cadena de adentro hacia afuera:
                    //    Primero, enlazamos el 'else' final al bloque del 'else if'
                    else_if_body_node->right = final_else_node;
    
                    // 4. Creamos el nodo para el 'else if' completo
                     ast_node* else_if_statement = create_node("ElseIfStatement", NULL, else_if_cond_node, else_if_body_node);

                    // 5. Enlazamos la cadena del 'else if' al bloque del 'if' principal
                   if_body_node->right = else_if_statement;
 
                   // 6. Creamos el nodo 'if' principal
                   (yyval.node) = create_node("IfStatement", NULL, if_cond_node, if_body_node);
                   generate_ast_file((yyval.node));
                  }else{
                   char *if_comparison_str = strdup((yyvsp[(3) - (11)].sval));
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup((yyvsp[(8) - (11)].sval));
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                (yyval.node) = create_node("if_Condition",if_comparison_str,(yyvsp[(5) - (11)].node),create_node("ElseIf", elseif_result, (yyvsp[(10) - (11)].node), (yyvsp[(11) - (11)].node))); generate_ast_file((yyval.node));
                }
            ;}
    break;

  case 83:

/* Line 1455 of yacc.c  */
#line 3022 "semantic.y"
    {
                    if (compile_mode) {
                     // 1. Sacamos los nodos de la pila en orden inverso
                       ast_node* else_if_cond_node = pop_node(); // Condición del ELSE_IF ($9)
                       ast_node* if_cond_node = pop_node();      // Condición del IF ($3)

                       // 2. Obtenemos los nodos de los bloques
                       ast_node* if_body_node = (yyvsp[(6) - (13)].node);
                       ast_node* else_if_body_node = (yyvsp[(12) - (13)].node);
                      ast_node* final_else_node = (yyvsp[(13) - (13)].node); // Este es el 'condtional_stmt' (ElseStatement)

                     // 3. Construimos la cadena de adentro hacia afuera:
                    //    Primero, enlazamos el 'else' final al bloque del 'else if'
                    else_if_body_node->right = final_else_node;
    
                    // 4. Creamos el nodo para el 'else if' completo
                     ast_node* else_if_statement = create_node("ElseIfStatement", NULL, else_if_cond_node, else_if_body_node);

                    // 5. Enlazamos la cadena del 'else if' al bloque del 'if' principal
                   if_body_node->right = else_if_statement;
 
                   // 6. Creamos el nodo 'if' principal
                   (yyval.node) = create_node("IfStatement", NULL, if_cond_node, if_body_node);
                   generate_ast_file((yyval.node));
                  }else{
                    char *if_comparison_str = strdup((yyvsp[(3) - (13)].sval));
                    char *if_result = strchr(if_comparison_str, ',');
                    if (if_result != NULL) {
                    *if_result = '\0';
                     if_result++;
                    }

                     char *elseif_comparison_str = strdup((yyvsp[(9) - (13)].sval));
                     char *elseif_result = strchr(elseif_comparison_str, ',');
                     if (elseif_result != NULL) {
                    *elseif_result = '\0';
                      elseif_result++;
                     }
                //printf("%s\n",$3);
                (yyval.node) = create_node("if_Condition",if_comparison_str,(yyvsp[(6) - (13)].node),create_node("ElseIf", elseif_result, (yyvsp[(12) - (13)].node), (yyvsp[(13) - (13)].node))); generate_ast_file((yyval.node));
            }
            ;}
    break;

  case 84:

/* Line 1455 of yacc.c  */
#line 3066 "semantic.y"
    { 
                 if(compile_mode) {
                       (yyval.node) = create_node("ElseStatement", NULL, (yyvsp[(2) - (2)].node), NULL);
                   } else {
                       (yyval.node) = create_node("Else", NULL, (yyvsp[(2) - (2)].node), NULL);
                   }
                   
               ;}
    break;

  case 85:

/* Line 1455 of yacc.c  */
#line 3074 "semantic.y"
    { 
                if(compile_mode) {
                       (yyval.node) = create_node("ElseStatement", NULL, (yyvsp[(3) - (3)].node), NULL);
                   } else {
                       (yyval.node) = create_node("Else", NULL, (yyvsp[(3) - (3)].node), NULL);
                   } 
                ;}
    break;

  case 86:

/* Line 1455 of yacc.c  */
#line 3082 "semantic.y"
    { enter_scope(); ;}
    break;

  case 87:

/* Line 1455 of yacc.c  */
#line 3082 "semantic.y"
    { exit_scope(); ;}
    break;

  case 88:

/* Line 1455 of yacc.c  */
#line 3082 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 89:

/* Line 1455 of yacc.c  */
#line 3083 "semantic.y"
    { enter_scope(); ;}
    break;

  case 90:

/* Line 1455 of yacc.c  */
#line 3083 "semantic.y"
    { exit_scope(); ;}
    break;

  case 91:

/* Line 1455 of yacc.c  */
#line 3083 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 92:

/* Line 1455 of yacc.c  */
#line 3085 "semantic.y"
    {
             // $3 es la expresión a evaluar (ej. 'dia')
             //  $6 es la lista de todos los nodos de los casos
            (yyval.node) = create_node("SwitchStatement", (yyvsp[(3) - (5)].sval), (yyvsp[(5) - (5)].node), NULL);
            generate_ast_file((yyval.node));
            ;}
    break;

  case 93:

/* Line 1455 of yacc.c  */
#line 3094 "semantic.y"
    { (yyval.node) = (yyvsp[(1) - (1)].node); ;}
    break;

  case 94:

/* Line 1455 of yacc.c  */
#line 3095 "semantic.y"
    {
        // Esta es la lógica correcta para construir una lista plana
        ast_node* list_head = (yyvsp[(1) - (2)].node);
        ast_node* current = list_head;

        // Avanzamos hasta el final de la lista de casos
        while (current->right != NULL) {
            current = current->right;
        }
        // Y enlazamos el nuevo caso al final
        current->right = (yyvsp[(2) - (2)].node);
        
        (yyval.node) = list_head; // Devolvemos el inicio de la lista
    ;}
    break;

  case 95:

/* Line 1455 of yacc.c  */
#line 3112 "semantic.y"
    {
        // $2 es el valor del caso (ej. '1')
        // $5 es el bloque de sentencias para ese caso
        (yyval.node) = create_node("Case", (yyvsp[(2) - (4)].sval), (yyvsp[(4) - (4)].node), NULL);
    ;}
    break;

  case 96:

/* Line 1455 of yacc.c  */
#line 3117 "semantic.y"
    {
        // $4 es el bloque de sentencias para el caso default
        (yyval.node) = create_node("DefaultCase", "default", (yyvsp[(3) - (3)].node), NULL);
    ;}
    break;

  case 97:

/* Line 1455 of yacc.c  */
#line 3122 "semantic.y"
    {
               add_or_find_function((yyvsp[(2) - (5)].sval), "inferred"); // Marcamos el tipo como "inferido"
              (yyval.sval) = current_function_name;
            // Si al final no hubo 'return', su tipo es 'void'   
             printf("Function: %s\n", lookup_function((yyvsp[(2) - (5)].sval))->return_value);
             current_function_name = (yyvsp[(2) - (5)].sval);
              
               add_or_find_function((yyvsp[(2) - (5)].sval), "inferred"); // Marcamos la función como "inferida" inicialmente.
              //$$ = create_node("Function", $2, create_node("Parameters", $4, NULL, NULL), $6); generate_ast_file($$);
               ;}
    break;

  case 98:

/* Line 1455 of yacc.c  */
#line 3131 "semantic.y"
    {   
                 enter_scope();
                FunctionSymbol* func = lookup_function(current_function_name);
                 parse_and_store_parameters(func, (yyvsp[(4) - (7)].sval));
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
                (yyval.node) = create_node("Function", (yyvsp[(2) - (7)].sval), create_node("Parameters", (yyvsp[(4) - (7)].sval), NULL, NULL), (yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
    //          $$ = create_node("Function", $3, create_node("Parameters", $5, NULL, create_node("Type", $1, NULL, NULL)), $7); generate_ast_file($$);
               current_function_name = (yyvsp[(6) - (7)].sval);
               exit_scope();
             ;}
    break;

  case 99:

/* Line 1455 of yacc.c  */
#line 3151 "semantic.y"
    {
              add_or_find_function((yyvsp[(2) - (5)].sval), "inferred"); // Marcamos el tipo como "inferido"
               (yyval.sval) = current_function_name;
              // Si al final no hubo 'return', su tipo es 'void'   
              // printf("Function: %s\n", lookup_function($2)->return_value);
    
             current_function_name = (yyvsp[(2) - (5)].sval);
               add_or_find_function((yyvsp[(2) - (5)].sval), "inferred"); // Marcamos la función como "inferida" inicialmente.
               ;}
    break;

  case 100:

/* Line 1455 of yacc.c  */
#line 3159 "semantic.y"
    {
                
                FunctionSymbol* func = lookup_function(current_function_name);
                parse_and_store_parameters(func, (yyvsp[(4) - (7)].sval));
                for (int i = 0; i < func->param_count; i++) {
                declare_var(func->params[i]->name, "NULL", func->params[i]->type,false,NULL);
                }
               // 3. Si después de analizar el bloque, el tipo sigue siendo "inferido",
               //    significa que no hubo sentencia 'return', por lo tanto, es 'void'.
               if (func && strcmp(func->return_type, "inferred") == 0) {
                 free(func->return_type);
                 func->return_type = "void";
               }
                (yyval.node) = create_node("Function", (yyvsp[(2) - (7)].sval), create_node("Parameters", (yyvsp[(4) - (7)].sval), NULL, NULL), (yyvsp[(7) - (7)].node)); generate_ast_file((yyval.node));
                current_function_name = (yyvsp[(6) - (7)].sval);
               ;}
    break;

  case 101:

/* Line 1455 of yacc.c  */
#line 3176 "semantic.y"
    {
                // Misma lógica de contexto para funciones con tipo explícito.
                (yyval.sval) = current_function_name; // 1. Guardar contexto anterior.
                current_function_name = (yyvsp[(3) - (6)].sval);      // 2. Establecer contexto actual.
                add_or_find_function((yyvsp[(3) - (6)].sval), (yyvsp[(1) - (6)].sval));    //    Se añade con su tipo explícito.
             ;}
    break;

  case 102:

/* Line 1455 of yacc.c  */
#line 3181 "semantic.y"
    {
                FunctionSymbol* func = lookup_function((yyvsp[(3) - (8)].sval));
                // Aquí podrías añadir una validación para asegurar que hubo un return si el tipo no es void.
                 for (int i = 0; i < func->param_count; i++) {
                 declare_var(func->params[i]->name, "NULL", func->params[i]->type,false,NULL);
                 
                 }
                // 3. Crear nodo AST.
                (yyval.node) = create_node("Function", (yyvsp[(3) - (8)].sval), create_node("Parameters", (yyvsp[(5) - (8)].sval), NULL, create_node("ExplicitType", (yyvsp[(1) - (8)].sval), NULL, NULL)), (yyvsp[(8) - (8)].node));
                generate_ast_file((yyval.node));

                // 4. Restaurar contexto anterior.
                current_function_name = (yyvsp[(7) - (8)].sval);
             ;}
    break;

  case 103:

/* Line 1455 of yacc.c  */
#line 3197 "semantic.y"
    { 
                validate_function_call((yyvsp[(1) - (3)].sval), "");
              (yyval.node) = create_node("FunctionCall",(yyvsp[(1) - (3)].sval),create_node("Paramenters",NULL,NULL,NULL),NULL); generate_ast_file((yyval.node))
             ;}
    break;

  case 104:

/* Line 1455 of yacc.c  */
#line 3201 "semantic.y"
    {
                validate_function_call((yyvsp[(1) - (4)].sval), (yyvsp[(3) - (4)].sval));
              (yyval.node) = create_node("FunctionCall",(yyvsp[(1) - (4)].sval),create_node("Paramenters",(yyvsp[(3) - (4)].sval),NULL,NULL),NULL); generate_ast_file((yyval.node))
             ;}
    break;

  case 105:

/* Line 1455 of yacc.c  */
#line 3206 "semantic.y"
    { (yyval.sval) = NULL; ;}
    break;

  case 106:

/* Line 1455 of yacc.c  */
#line 3207 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 107:

/* Line 1455 of yacc.c  */
#line 3208 "semantic.y"
    {(yyval.sval) = concat_strings((yyvsp[(1) - (3)].sval),concat_strings(",",concat_strings(" ", (yyvsp[(3) - (3)].sval)))); ;}
    break;

  case 108:

/* Line 1455 of yacc.c  */
#line 3209 "semantic.y"
    { (yyval.sval) = concat_strings((yyvsp[(1) - (2)].sval),concat_strings(" ",(yyvsp[(2) - (2)].sval))); ;}
    break;

  case 109:

/* Line 1455 of yacc.c  */
#line 3210 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 110:

/* Line 1455 of yacc.c  */
#line 3215 "semantic.y"
    { (yyval.sval) = NULL; ;}
    break;

  case 111:

/* Line 1455 of yacc.c  */
#line 3216 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 112:

/* Line 1455 of yacc.c  */
#line 3217 "semantic.y"
    { concat_strings((yyvsp[(1) - (3)].sval),concat_strings(",",concat_strings(" ",(yyvsp[(3) - (3)].sval)))); ;}
    break;

  case 113:

/* Line 1455 of yacc.c  */
#line 3219 "semantic.y"
    { (yyval.sval) = "int"; ;}
    break;

  case 114:

/* Line 1455 of yacc.c  */
#line 3220 "semantic.y"
    { (yyval.sval) = "float"; ;}
    break;

  case 115:

/* Line 1455 of yacc.c  */
#line 3221 "semantic.y"
    { (yyval.sval) = "string"; ;}
    break;

  case 116:

/* Line 1455 of yacc.c  */
#line 3222 "semantic.y"
    { (yyval.sval) = "bool"; ;}
    break;

  case 117:

/* Line 1455 of yacc.c  */
#line 3223 "semantic.y"
    { (yyval.sval) = "void"; ;}
    break;

  case 118:

/* Line 1455 of yacc.c  */
#line 3225 "semantic.y"
    {  if (strcmp((yyvsp[(1) - (2)].node)->type, "Statements") == 0) {
                                            // Si ya es "Statements", solo agregamos el nuevo statement
                                            ast_node* current = (yyvsp[(1) - (2)].node);
                                            while (current->right != NULL) {
                                                current = current->right;
                                            }
                                            current->right = (yyvsp[(2) - (2)].node);
                                            (yyval.node) = (yyvsp[(1) - (2)].node);
                                         } else {
                                            // Si no es "Statements", creamos el nodo
                                            (yyval.node) = create_node("Statements", NULL, (yyvsp[(1) - (2)].node), (yyvsp[(2) - (2)].node));
                                         }
                                        ;}
    break;

  case 119:

/* Line 1455 of yacc.c  */
#line 3238 "semantic.y"
    {(yyval.node) = (yyvsp[(1) - (1)].node);}
    break;

  case 120:

/* Line 1455 of yacc.c  */
#line 3240 "semantic.y"
    {  
     if (compile_mode) {
            char* var_type = get_type((yyvsp[(1) - (1)].sval)) ? get_type((yyvsp[(1) - (1)].sval)) : "NULL";
            ast_node* type_node = create_node("Type", var_type, NULL, NULL);
            ast_node* var_ref_node = create_node("VariableReference", (yyvsp[(1) - (1)].sval), type_node, NULL);
            push_node(var_ref_node);
        }else{ 
            // Crear el nodo para una variable
             // 1. Buscar el símbolo en la tabla de scopes
       symbol* s = find_variable((yyvsp[(1) - (1)].sval));

    // 2. Si no se encuentra, es un error semántico
     if (!s) {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, (yyvsp[(1) - (1)].sval));
        yyerror(error_msg);
        exit(1); // Detener el análisis
     }

         (yyval.sval) = (yyvsp[(1) - (1)].sval);  }     
;}
    break;

  case 122:

/* Line 1455 of yacc.c  */
#line 3265 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 123:

/* Line 1455 of yacc.c  */
#line 3266 "semantic.y"
    { 
          //  char* val1 = get_var($1) ? $1 : get_var($1);
           //char* val2 = get_var($3) ? $3 : get_var($3);

        (yyval.sval) = concat_con_espacio((yyvsp[(1) - (3)].sval),(yyvsp[(3) - (3)].sval)); 
     ;}
    break;

  case 126:

/* Line 1455 of yacc.c  */
#line 3276 "semantic.y"
    { paren_num++; printf("paren abierta\n");
          expression_op[expression_num].op = "(";
          expression_op[expression_num].num = 2; // 2 = Inicio de Paréntesis
          expression_num++;

          ;}
    break;

  case 127:

/* Line 1455 of yacc.c  */
#line 3282 "semantic.y"
    { paren_num--; printf("paren cerrado\n"); 
              expression_op[expression_num].op = ")";
              expression_op[expression_num].num = 3; // 3 = Fin de Paréntesis
              expression_num++;
           ;}
    break;

  case 128:

/* Line 1455 of yacc.c  */
#line 3288 "semantic.y"
    { 
                    longitud = 0; 
                    (yyval.sval) = ""; 
                ;}
    break;

  case 129:

/* Line 1455 of yacc.c  */
#line 3292 "semantic.y"
    { 
                    (yyval.sval) = (yyvsp[(1) - (1)].sval); // Simplemente pasa el resultado de la lista de pares.
                ;}
    break;

  case 130:

/* Line 1455 of yacc.c  */
#line 3298 "semantic.y"
    { 
                    longitud = 1; 
                    (yyval.sval) = (yyvsp[(1) - (1)].sval); 
                ;}
    break;

  case 131:

/* Line 1455 of yacc.c  */
#line 3302 "semantic.y"
    {
                    // Concatenación más segura usando malloc para evitar desbordamientos
                    size_t len1 = strlen((yyvsp[(1) - (3)].sval));
                    size_t len2 = strlen((yyvsp[(3) - (3)].sval));
                    char* result = malloc(len1 + 1 + len2 + 1); // str1 + coma + str2 + null
                    if (result) {
                        strcpy(result, (yyvsp[(1) - (3)].sval));
                        strcat(result, ",");
                        strcat(result, (yyvsp[(3) - (3)].sval));
                    }
                    (yyval.sval) = result;
                    longitud++;
                ;}
    break;

  case 132:

/* Line 1455 of yacc.c  */
#line 3318 "semantic.y"
    {
    char buffer[1024];
    sprintf(buffer, "%s:%s", add_quotes((yyvsp[(1) - (3)].sval)), (yyvsp[(3) - (3)].sval));
    (yyval.sval) = strdup(buffer);
;}
    break;

  case 133:

/* Line 1455 of yacc.c  */
#line 3323 "semantic.y"
    {  (yyval.sval) = (yyvsp[(2) - (3)].sval); ;}
    break;

  case 134:

/* Line 1455 of yacc.c  */
#line 3324 "semantic.y"
    {         

            concat_op = op_concat((yyvsp[(1) - (3)].sval),'+',(yyvsp[(3) - (3)].sval));
            valid = valid_expression(concat_op);
            char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
            char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);
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
             (yyval.sval) = do_op_float(val1,'+',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             (yyval.sval) = do_op(val1,'+',val2);
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
        ;}
    break;

  case 135:

/* Line 1455 of yacc.c  */
#line 3358 "semantic.y"
    { 
            concat_op = op_concat((yyvsp[(1) - (3)].sval),'-',(yyvsp[(3) - (3)].sval));
            valid = valid_expression(concat_op);
            //printf("valid: %d\n",valid);
            char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
            char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            if(valid==1){ 
             expression_op[expression_num].op = "-";
             expression_op[expression_num].num = 1; // 1 = Operador
             expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             (yyval.sval) = do_op_float((yyvsp[(1) - (3)].sval),'-',(yyvsp[(3) - (3)].sval));
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             (yyval.sval) = do_op((yyvsp[(1) - (3)].sval),'-',(yyvsp[(3) - (3)].sval));
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
          ;}
    break;

  case 136:

/* Line 1455 of yacc.c  */
#line 3388 "semantic.y"
    {

            concat_op = op_concat((yyvsp[(1) - (3)].sval),'*',(yyvsp[(3) - (3)].sval));
            valid = valid_expression(concat_op);
            char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
            char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            //printf("valid: %d\n",valid);
           // printf("Texpr1: %s, Texpr2: : %s\n", $1, $3);
            if(valid==1){ 
              expression_op[expression_num].op = "*";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             (yyval.sval) = do_op_float((yyvsp[(1) - (3)].sval),'*',(yyvsp[(3) - (3)].sval));
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             (yyval.sval) = do_op((yyvsp[(1) - (3)].sval),'*',(yyvsp[(3) - (3)].sval));
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
           ;}
    break;

  case 137:

/* Line 1455 of yacc.c  */
#line 3420 "semantic.y"
    { 
            concat_op = op_concat((yyvsp[(1) - (3)].sval),'/',(yyvsp[(3) - (3)].sval));
            valid = valid_expression(concat_op);
            char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
            char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            if(valid==1){ 
              expression_op[expression_num].op = "/";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             (yyval.sval) = do_division((yyvsp[(1) - (3)].sval),(yyvsp[(3) - (3)].sval));
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             (yyval.sval) = do_division((yyvsp[(1) - (3)].sval),(yyvsp[(3) - (3)].sval));
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
            ;}
    break;

  case 138:

/* Line 1455 of yacc.c  */
#line 3449 "semantic.y"
    {
                concat_op = op_concat((yyvsp[(1) - (3)].sval), '%', (yyvsp[(3) - (3)].sval));
                valid = valid_expression(concat_op);
                
                char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
                char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);
                char* type1 = determine_type(val1);
                char* type2 = determine_type(val2);
                
                if (valid == 1) {
                    expression_op[expression_num].op = "%";
                    expression_op[expression_num].num = 1; // 1 = Operador
                    expression_num++;
                }

                // El módulo solo funciona con enteros
                if (strcmp(type1, "int") == 0 && strcmp(type2, "int") == 0) {
                    (yyval.sval) = do_mod(val1, val2);
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
            ;}
    break;

  case 139:

/* Line 1455 of yacc.c  */
#line 3484 "semantic.y"
    { (yyval.sval) = to_string((yyvsp[(1) - (1)].ival)); ;}
    break;

  case 140:

/* Line 1455 of yacc.c  */
#line 3485 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 141:

/* Line 1455 of yacc.c  */
#line 3486 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 142:

/* Line 1455 of yacc.c  */
#line 3487 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 143:

/* Line 1455 of yacc.c  */
#line 3488 "semantic.y"
    { // Caso recursivo para el acceso profundo
                   char buffer[1024];
                   sprintf(buffer, "%s:%s", (yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval));
                   (yyval.sval) = strdup(buffer);
               ;}
    break;

  case 144:

/* Line 1455 of yacc.c  */
#line 3495 "semantic.y"
    { (yyval.sval) = "True"; ;}
    break;

  case 145:

/* Line 1455 of yacc.c  */
#line 3496 "semantic.y"
    { (yyval.sval) = "False"; ;}
    break;

  case 146:

/* Line 1455 of yacc.c  */
#line 3499 "semantic.y"
    { (yyval.sval) = to_string((yyvsp[(1) - (1)].ival));  
        if (compile_mode) {

            ast_node* type_node = create_node("Type", "int", NULL, NULL);
            ast_node* literal_node = create_node("Literal", to_string((yyvsp[(1) - (1)].ival)), type_node, NULL);
            push_node(literal_node);
        }
       expression_op[expression_num].op = strdup((yyval.sval));
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    ;}
    break;

  case 147:

/* Line 1455 of yacc.c  */
#line 3510 "semantic.y"
    { (yyval.sval) = add_quotes((yyvsp[(1) - (1)].sval));
     if (compile_mode) {
            ast_node* type_node = create_node("Type", "String", NULL, NULL);
            ast_node* literal_node = create_node("Literal", add_quotes((yyvsp[(1) - (1)].sval)), type_node, NULL);
            push_node(literal_node);
        }

    ;}
    break;

  case 148:

/* Line 1455 of yacc.c  */
#line 3518 "semantic.y"
    { (yyval.sval) = floatToString((yyvsp[(1) - (1)].fval)); 
        expression_op[expression_num].op = strdup((yyval.sval));
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
         if (compile_mode) {
            ast_node* type_node = create_node("Type", "float", NULL, NULL);
            ast_node* literal_node = create_node("Literal", floatToString((yyvsp[(1) - (1)].fval)), type_node, NULL);
            push_node(literal_node);
        }
    ;}
    break;

  case 149:

/* Line 1455 of yacc.c  */
#line 3528 "semantic.y"
    {
          // 1. Llamamos a nuestra nueva función orquestadora
          char* val1 = get_var((yyvsp[(3) - (4)].sval)) ? get_var((yyvsp[(3) - (4)].sval)) : (yyvsp[(3) - (4)].sval);
    (yyval.sval) = access_collection_element((yyvsp[(1) - (4)].sval), val1);
    
    // 2. Manejamos el caso en que no se encuentre el elemento
    if ((yyval.sval) == NULL) {
        char error_msg[256];
        sprintf(error_msg, "Error en linea %d: La clave o indice '%s' no se encontro o es invalido para '%s'.", yylineno, (yyvsp[(3) - (4)].sval), (yyvsp[(1) - (4)].sval));
        yyerror(error_msg);
        exit(1); // Detener el análisis
    }
  ;}
    break;

  case 150:

/* Line 1455 of yacc.c  */
#line 3541 "semantic.y"
    {
          // Resolvemos el valor de la condición
          char* condition_val = get_var((yyvsp[(1) - (5)].sval)) ? get_var((yyvsp[(1) - (5)].sval)) : (yyvsp[(1) - (5)].sval);
          
          if (is_truthy(condition_val)) {
              // Si la condición es verdadera, el resultado es la expresión de la izquierda ($3)
              (yyval.sval) = (yyvsp[(3) - (5)].sval);
          } else {
              // Si la condición es falsa, el resultado es la expresión de la derecha ($5)
              (yyval.sval) = (yyvsp[(5) - (5)].sval);
          }
      ;}
    break;

  case 151:

/* Line 1455 of yacc.c  */
#line 3554 "semantic.y"
    { 
            // Se llama a la nueva función en el momento correcto
           char* final_string = process_string((yyvsp[(1) - (1)].sval));
           (yyval.sval) = add_quotes(final_string);
          free(final_string); 
          ast_node* n = create_node("StringLiteral", add_quotes((yyvsp[(1) - (1)].sval)), NULL, NULL);
          push_node(n);
       // $$ = add_quotes(removeParentheses($1));
        ;}
    break;

  case 153:

/* Line 1455 of yacc.c  */
#line 3564 "semantic.y"
    {
         if (compile_mode) {
            ast_node* type_node = create_node("Type", "Bool", NULL, NULL);
            ast_node* literal_node = create_node("Literal", (yyvsp[(1) - (1)].sval), type_node, NULL);
            push_node(literal_node);
        }
    ;}
    break;

  case 154:

/* Line 1455 of yacc.c  */
#line 3572 "semantic.y"
    { 
      FunctionSymbol* func = lookup_function((yyvsp[(1) - (4)].sval));
              validate_function_call((yyvsp[(1) - (4)].sval), (yyvsp[(3) - (4)].sval));
            // TU LÓGICA DE INFERENCIA YA FUNCIONA AQUÍ:
            // Si una función no tuvo 'return', su func->return_type ya habrá sido
            // cambiado a "void" al final de su declaración.

            // 1. Verificamos el tipo final de la función.
            if (strcmp(func->return_type, "void") == 0) {
                // Si es void, devolvemos el marcador especial.
                (yyval.sval) = VOID_RESULT_MARKER;
            } else {
                // 2. Si NO es void, aplicamos la lógica de retorno normal.
                if (func->return_value != NULL) {
                    // Tenía un 'return', usamos su valor.
                    (yyval.sval) = strdup(func->return_value);
                } else {
                    // No tenía 'return' pero es tipada, usamos el default.
                    if (strcmp(func->return_type, "int") == 0) (yyval.sval) = "0";
                    else if (strcmp(func->return_type, "float") == 0) (yyval.sval) = "0.0";
                    else if (strcmp(func->return_type, "string") == 0) (yyval.sval) = "\"\"";
                    else if (strcmp(func->return_type, "bool") == 0) (yyval.sval) = "False";
                    else (yyval.sval) = "NULL"; // Fallback
                }
            }
        //} 
    ;}
    break;

  case 155:

/* Line 1455 of yacc.c  */
#line 3600 "semantic.y"
    {(yyval.sval) = (yyval.sval);;}
    break;

  case 156:

/* Line 1455 of yacc.c  */
#line 3601 "semantic.y"
    { 
                char *temp_str = concatenateComparison((yyvsp[(1) - (3)].sval), " in ", (yyvsp[(3) - (3)].sval)); 
                (yyval.sval) = concatenateComparison("",",",temp_str);
             ;}
    break;

  case 157:

/* Line 1455 of yacc.c  */
#line 3605 "semantic.y"
    {
                // Verificar si la variable existe
                if (get_var((yyvsp[(1) - (1)].sval))) {
                    printf("type es: %s\n", get_type((yyvsp[(1) - (1)].sval)));
                    if(strcmp(get_type((yyvsp[(1) - (1)].sval)),"Array") == 0 || strcmp(get_type((yyvsp[(1) - (1)].sval)),"Range") == 0){ 
                        printf("Variable: %s\n", get_var((yyvsp[(1) - (1)].sval))); 
                     (yyval.sval) = (yyvsp[(1) - (1)].sval);
                     }else{
                        (yyval.sval) = NULL;
                     }
                }else{
                    fprintf(stderr, "Error: Variable '%s' no definida.\n", (yyvsp[(1) - (1)].sval));
                    (yyval.sval) = "NULL"; // Manejo de error, asignar un valor por defecto
                }    
             ;}
    break;

  case 158:

/* Line 1455 of yacc.c  */
#line 3621 "semantic.y"
    {(yyval.sval) ="&&";;}
    break;

  case 159:

/* Line 1455 of yacc.c  */
#line 3622 "semantic.y"
    {(yyval.sval) = "||";;}
    break;

  case 161:

/* Line 1455 of yacc.c  */
#line 3624 "semantic.y"
    { char *temp_str = concatenateComparison((yyvsp[(1) - (3)].sval), " in ", (yyvsp[(3) - (3)].sval)); 
          (yyval.sval) = concatenateComparison("",",",temp_str);;}
    break;

  case 162:

/* Line 1455 of yacc.c  */
#line 3627 "semantic.y"
    { 
             // Concatenamos las comparaciones y resultados
          if (compile_mode) {
                ast_node* right_node = pop_node();
                ast_node* left_node = pop_node();
                // Usamos el valor de $2 ("&&" o "||") para el operador
                ast_node* logical_node = create_node("LogicalExpression", (yyvsp[(2) - (3)].sval), left_node, right_node);
                push_node(logical_node);
             }else{
    char *left = strdup((yyvsp[(1) - (3)].sval));  // Comparación izquierda
    char *right = strdup((yyvsp[(3) - (3)].sval)); // Comparación derecha
    
    // Evaluamos la condición lógica de las comparaciones
    char *conditions = concatenateComparison(left, (yyvsp[(2) - (3)].sval), right);  // Concatenamos las comparaciones con el operador lógico
    char * result = process_conditions(conditions);
    // Evaluamos el resultado lógico de todas las condiciones
    char *logical_result = evaluate_logical_conditions(conditions);
   // printf("%s\n",result);
    // Concatenamos la comparación con el resultado lógico final
    (yyval.sval) = concatenateComparison(result, ",", logical_result);
    }
            ;}
    break;

  case 163:

/* Line 1455 of yacc.c  */
#line 3649 "semantic.y"
    {
              if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "==", left_mode, right_mode);
                push_node(op_node);
             }else{
            comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"==", (yyvsp[(3) - (3)].sval));     
             if(strcmp((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval)) == 0){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); } 
          }
          ;}
    break;

  case 164:

/* Line 1455 of yacc.c  */
#line 3662 "semantic.y"
    {
             if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "!=", left_mode, right_mode); //generate_ast_file(op_node);
                push_node(op_node);
             }else{
            comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"!=", (yyvsp[(3) - (3)].sval));
            if(atoi((yyvsp[(1) - (3)].sval))  != atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }
             }
          ;}
    break;

  case 165:

/* Line 1455 of yacc.c  */
#line 3675 "semantic.y"
    {
                  if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", ">", left_mode, right_mode); //generate_ast_file(op_node);
                push_node(op_node);
                
             }else{

              comparison = concatenateComparison((yyvsp[(1) - (3)].sval),">", (yyvsp[(3) - (3)].sval));
              if(atoi((yyvsp[(1) - (3)].sval)) > atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison);}else{ (yyval.sval) = concatenateComparison("False",",",comparison); }
             }
         ;}
    break;

  case 166:

/* Line 1455 of yacc.c  */
#line 3690 "semantic.y"
    {
             if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "<", left_mode, right_mode);
                push_node(op_node);
             }else{
              comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"<", (yyvsp[(3) - (3)].sval));
              if(atoi((yyvsp[(1) - (3)].sval))  < atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }
             }
         ;}
    break;

  case 167:

/* Line 1455 of yacc.c  */
#line 3703 "semantic.y"
    {
             if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", ">=", left_mode, right_mode);
                push_node(op_node);
             }else{
              comparison = concatenateComparison((yyvsp[(1) - (3)].sval),">=", (yyvsp[(3) - (3)].sval));
              if(atoi((yyvsp[(1) - (3)].sval))  >= atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }      
             }
         ;}
    break;

  case 168:

/* Line 1455 of yacc.c  */
#line 3716 "semantic.y"
    {
          if (compile_mode) {
                ast_node* right = pop_node();
                ast_node* left = pop_node();
                ast_node* left_mode = create_node("left",NULL,left,NULL);
                ast_node* right_mode = create_node("right",NULL,NULL,right);
                ast_node* op_node = create_node("BinaryExpression", "<=", left_mode, right_mode);
                push_node(op_node);
             }else{  
              comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"<=", (yyvsp[(3) - (3)].sval));
              if(atoi((yyvsp[(1) - (3)].sval))  <= atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }            
             }
         ;}
    break;

  case 169:

/* Line 1455 of yacc.c  */
#line 3731 "semantic.y"
    { longitud = 1; (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 170:

/* Line 1455 of yacc.c  */
#line 3732 "semantic.y"
    { 
           // Un array con múltiples elementos.
                char* tempList = concat_strings((yyvsp[(1) - (3)].sval), ",");
                (yyval.sval) = concat_strings(tempList, (yyvsp[(3) - (3)].sval));
                free(tempList); // Liberar memoria intermedia.
                longitud++;
         // printf("exprlist: %s\n",$$);
          ;}
    break;

  case 171:

/* Line 1455 of yacc.c  */
#line 3767 "semantic.y"
    {
  ;}
    break;



/* Line 1455 of yacc.c  */
#line 6316 "semantic.tab.c"
      default: break;
    }
  YY_SYMBOL_PRINT ("-> $$ =", yyr1[yyn], &yyval, &yyloc);

  YYPOPSTACK (yylen);
  yylen = 0;
  YY_STACK_PRINT (yyss, yyssp);

  *++yyvsp = yyval;

  /* Now `shift' the result of the reduction.  Determine what state
     that goes to, based on the state we popped back to and the rule
     number reduced by.  */

  yyn = yyr1[yyn];

  yystate = yypgoto[yyn - YYNTOKENS] + *yyssp;
  if (0 <= yystate && yystate <= YYLAST && yycheck[yystate] == *yyssp)
    yystate = yytable[yystate];
  else
    yystate = yydefgoto[yyn - YYNTOKENS];

  goto yynewstate;


/*------------------------------------.
| yyerrlab -- here on detecting error |
`------------------------------------*/
yyerrlab:
  /* If not already recovering from an error, report this error.  */
  if (!yyerrstatus)
    {
      ++yynerrs;
#if ! YYERROR_VERBOSE
      yyerror (YY_("syntax error"));
#else
      {
	YYSIZE_T yysize = yysyntax_error (0, yystate, yychar);
	if (yymsg_alloc < yysize && yymsg_alloc < YYSTACK_ALLOC_MAXIMUM)
	  {
	    YYSIZE_T yyalloc = 2 * yysize;
	    if (! (yysize <= yyalloc && yyalloc <= YYSTACK_ALLOC_MAXIMUM))
	      yyalloc = YYSTACK_ALLOC_MAXIMUM;
	    if (yymsg != yymsgbuf)
	      YYSTACK_FREE (yymsg);
	    yymsg = (char *) YYSTACK_ALLOC (yyalloc);
	    if (yymsg)
	      yymsg_alloc = yyalloc;
	    else
	      {
		yymsg = yymsgbuf;
		yymsg_alloc = sizeof yymsgbuf;
	      }
	  }

	if (0 < yysize && yysize <= yymsg_alloc)
	  {
	    (void) yysyntax_error (yymsg, yystate, yychar);
	    yyerror (yymsg);
	  }
	else
	  {
	    yyerror (YY_("syntax error"));
	    if (yysize != 0)
	      goto yyexhaustedlab;
	  }
      }
#endif
    }



  if (yyerrstatus == 3)
    {
      /* If just tried and failed to reuse lookahead token after an
	 error, discard it.  */

      if (yychar <= YYEOF)
	{
	  /* Return failure if at end of input.  */
	  if (yychar == YYEOF)
	    YYABORT;
	}
      else
	{
	  yydestruct ("Error: discarding",
		      yytoken, &yylval);
	  yychar = YYEMPTY;
	}
    }

  /* Else will try to reuse lookahead token after shifting the error
     token.  */
  goto yyerrlab1;


/*---------------------------------------------------.
| yyerrorlab -- error raised explicitly by YYERROR.  |
`---------------------------------------------------*/
yyerrorlab:

  /* Pacify compilers like GCC when the user code never invokes
     YYERROR and the label yyerrorlab therefore never appears in user
     code.  */
  if (/*CONSTCOND*/ 0)
     goto yyerrorlab;

  /* Do not reclaim the symbols of the rule which action triggered
     this YYERROR.  */
  YYPOPSTACK (yylen);
  yylen = 0;
  YY_STACK_PRINT (yyss, yyssp);
  yystate = *yyssp;
  goto yyerrlab1;


/*-------------------------------------------------------------.
| yyerrlab1 -- common code for both syntax error and YYERROR.  |
`-------------------------------------------------------------*/
yyerrlab1:
  yyerrstatus = 3;	/* Each real token shifted decrements this.  */

  for (;;)
    {
      yyn = yypact[yystate];
      if (yyn != YYPACT_NINF)
	{
	  yyn += YYTERROR;
	  if (0 <= yyn && yyn <= YYLAST && yycheck[yyn] == YYTERROR)
	    {
	      yyn = yytable[yyn];
	      if (0 < yyn)
		break;
	    }
	}

      /* Pop the current state because it cannot handle the error token.  */
      if (yyssp == yyss)
	YYABORT;


      yydestruct ("Error: popping",
		  yystos[yystate], yyvsp);
      YYPOPSTACK (1);
      yystate = *yyssp;
      YY_STACK_PRINT (yyss, yyssp);
    }

  *++yyvsp = yylval;


  /* Shift the error token.  */
  YY_SYMBOL_PRINT ("Shifting", yystos[yyn], yyvsp, yylsp);

  yystate = yyn;
  goto yynewstate;


/*-------------------------------------.
| yyacceptlab -- YYACCEPT comes here.  |
`-------------------------------------*/
yyacceptlab:
  yyresult = 0;
  goto yyreturn;

/*-----------------------------------.
| yyabortlab -- YYABORT comes here.  |
`-----------------------------------*/
yyabortlab:
  yyresult = 1;
  goto yyreturn;

#if !defined(yyoverflow) || YYERROR_VERBOSE
/*-------------------------------------------------.
| yyexhaustedlab -- memory exhaustion comes here.  |
`-------------------------------------------------*/
yyexhaustedlab:
  yyerror (YY_("memory exhausted"));
  yyresult = 2;
  /* Fall through.  */
#endif

yyreturn:
  if (yychar != YYEMPTY)
     yydestruct ("Cleanup: discarding lookahead",
		 yytoken, &yylval);
  /* Do not reclaim the symbols of the rule which action triggered
     this YYABORT or YYACCEPT.  */
  YYPOPSTACK (yylen);
  YY_STACK_PRINT (yyss, yyssp);
  while (yyssp != yyss)
    {
      yydestruct ("Cleanup: popping",
		  yystos[*yyssp], yyvsp);
      YYPOPSTACK (1);
    }
#ifndef yyoverflow
  if (yyss != yyssa)
    YYSTACK_FREE (yyss);
#endif
#if YYERROR_VERBOSE
  if (yymsg != yymsgbuf)
    YYSTACK_FREE (yymsg);
#endif
  /* Make sure YYID is used.  */
  return YYID (yyresult);
}



/* Line 1675 of yacc.c  */
#line 3770 "semantic.y"

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
