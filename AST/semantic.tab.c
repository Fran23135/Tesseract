
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
int yylex(void);
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
    bool is_constant;
} symbol;
typedef struct Scope {
    symbol *symbol_list;
    struct Scope *parent;  // Apuntador al scope padre (así se forma la pila)
} Scope;
typedef struct operations {
    char *op;
    int num;
} operations;

typedef struct Parameter {
    char* name;
    char* type;
    char* value;
    char* function_name;  // Función a la que pertenece este parámetro
    struct Parameter* next;
} Parameter;

// Nodo temporal para validación de duplicados durante el parseo
typedef struct ParameterNode {
    char* name;
    struct ParameterNode* next;
} ParameterNode;

// Estructura simplificada para ParamSymbol (solo metadata)
typedef struct {
    char* name;
    char* type;
} ParamSymbol;

typedef struct {
    char* name;
    char* return_value;
    char* return_type;
   // ParamSymbol** params;  
    Parameter* param_list;
    int param_count;
    ParameterNode* temp_params_check; 
} FunctionSymbol;

const char* g_output_path = "ast_output.txt";
FunctionSymbol func_tab[999];
Parameter* global_params_list = NULL;
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

void set_default_mode(const char *mode) {
    if (strcmp(mode, "ident") == 0) {
        use_indent = 1;
    } else if (strcmp(mode, "block") == 0) {
        use_indent = 0;
    }
}
// Función para corregir la indentación del ForLoop en el archivo AST generado


// Función para corregir específicamente la indentación del ForLoop
// Función para corregir específicamente la indentación del ForLoop
void fix_forloop_indentation_in_file(const char* filename) {
    FILE* file = fopen(filename, "r");
    if (!file) return;

    // Leer todas las líneas
    char lines[1000][256];
    int line_count = 0;
    
    while (fgets(lines[line_count], sizeof(lines[0]), file) && line_count < 1000) {
        line_count++;
    }
    fclose(file);

    // Buscar el ForLoop
    for (int i = 0; i < line_count; i++) {
        if (strstr(lines[i], "ForLoop:")) {
            // Encontrar nivel de indentación del ForLoop
            int forloop_level = 0;
            for (int j = 0; lines[i][j] == ' '; j += 2) {
                forloop_level++;
            }

            int in_block = 0;
            int block_content_level = forloop_level + 2; // Nivel para TODO el contenido del bloque
            
            // Reconstruir la estructura correcta del ForLoop
            for (int j = i + 1; j < line_count; j++) {
                // Calcular nivel actual
                int current_level = 0;
                for (int k = 0; lines[j][k] == ' '; k += 2) {
                    current_level++;
                }

                // Si estamos fuera del ForLoop, terminar
                if (current_level <= forloop_level && !strstr(lines[j], "ForLoop:")) {
                    break;
                }

                // Detectar cuando entramos al bloque
                if (strstr(lines[j], "Block: BlockStart")) {
                    in_block = 1;
                    // Corregir BlockStart
                    char temp[256];
                    strcpy(temp, lines[j] + current_level * 2);
                    for (int k = 0; k < (forloop_level + 1) * 2; k++) {
                        lines[j][k] = ' ';
                    }
                    strcpy(lines[j] + (forloop_level + 1) * 2, temp);
                    continue;
                }
                
                // Detectar cuando salimos del bloque
                if (strstr(lines[j], "Block: BlockEnd")) {
                    in_block = 0;
                    // Corregir BlockEnd
                    char temp[256];
                    strcpy(temp, lines[j] + current_level * 2);
                    for (int k = 0; k < (forloop_level + 1) * 2; k++) {
                        lines[j][k] = ' ';
                    }
                    strcpy(lines[j] + (forloop_level + 1) * 2, temp);
                    continue;
                }

                // Si estamos dentro del bloque, aplicar indentación CORRECTA para TODOS los niveles
                if (in_block && current_level > forloop_level) {
                    char temp[256];
                    strcpy(temp, lines[j] + current_level * 2);
                    
                    // Calcular la diferencia de niveles y aplicar la indentación correcta
                    int level_difference = current_level - forloop_level;
                    int new_level = block_content_level + level_difference - 1;
                    
                    for (int k = 0; k < new_level * 2; k++) {
                        lines[j][k] = ' ';
                    }
                    strcpy(lines[j] + new_level * 2, temp);
                }
            }
            break;
        }
    }

    // Escribir el archivo corregido
    file = fopen(filename, "w");
    if (!file) return;
    
    for (int i = 0; i < line_count; i++) {
        fprintf(file, "%s", lines[i]);
    }
    fclose(file);
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

// Función para manejar accesos a array
symbol* handle_array_access(char *name) {
    char *open_bracket = strchr(name, '[');
    char *close_bracket = strchr(name, ']');
    
    if (open_bracket == name) {
        return NULL;
    }
    if (open_bracket && close_bracket && close_bracket > open_bracket) {
        // Extraer el nombre base del array
        char base_name[128];
        strncpy(base_name, name, open_bracket - name);
        base_name[open_bracket - name] = '\0';
        
        // Buscar la variable base
        Scope *scope_iterator = currentScope;
        while (scope_iterator != NULL) {
            symbol *symbol_iterator = scope_iterator->symbol_list;
            while (symbol_iterator != NULL) {
                if (strcmp(symbol_iterator->name, base_name) == 0) {
                    // Verificar que sea un array
                    if (strcmp(symbol_iterator->type, "Array") == 0) {
                        // Crear un símbolo temporal que represente el acceso al array
                        symbol *array_access = (symbol*)malloc(sizeof(symbol));
                        array_access->name = strdup(name); // "d[1]"
                        array_access->value = strdup(name); // "d[1]" en lugar del valor
                        array_access->type = strdup("ArrayAccess");
                        array_access->operation_str = NULL;
                        array_access->is_explicitly_typed = false;
                        array_access->next = NULL;
                        return array_access;
                    } else {
                        char error_msg[256];
                        sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no es un array.", yylineno, base_name);
                        yyerror(error_msg);
                        exit(1);
                    }
                }
                symbol_iterator = symbol_iterator->next;
            }
            scope_iterator = scope_iterator->parent;
        }
        
        // Si llegamos aquí, la variable base no existe
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, base_name);
        yyerror(error_msg);
        exit(1);
    }
   // printf("handle_array_access: No es acceso a array para '%s'\n", name);
    return NULL; // No es acceso a array
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
// Declarar un parámetro asociado a una función específica
void declare_parameter(char* param_name, char* param_type, char* func_name) {
    // 1. Buscamos la función a la que pertenece el parámetro
    FunctionSymbol* func = lookup_function(func_name);
    if (!func) {
        // Si por alguna razón no existe, no hacemos nada o lanzamos error
        return; 
    }
    
    // 2. Verificamos duplicados DENTRO de esa función específica
    Parameter* p = func->param_list;
    while (p != NULL) {
        if (strcmp(p->name, param_name) == 0) {
            char error_msg[256];
            sprintf(error_msg, "Error: El parametro '%s' ya existe en '%s'.", param_name, func_name);
            yyerror(error_msg);
            exit(1);
        }
        p = p->next;
    }
    
    // 3. Creamos el parámetro y lo agregamos al FINAL de la lista de la función
    // (Al final para preservar el orden de los argumentos)
    Parameter* new_param = (Parameter*)malloc(sizeof(Parameter));
    new_param->name = strdup(param_name);
    new_param->type = strdup(param_type);
    new_param->value = strdup("NULL");
    new_param->function_name = strdup(func_name); // Opcional, ya está en func
    new_param->next = NULL;

    if (func->param_list == NULL) {
        func->param_list = new_param;
    } else {
        Parameter* last = func->param_list;
        while (last->next != NULL) last = last->next;
        last->next = new_param;
    }
    
     printf("Parametro '%s' asociado a '%s'\n", param_name, func_name);
}

// Buscar un parámetro en el contexto de una función específica
Parameter* find_parameter(char* param_name, char* func_name) {
    FunctionSymbol* func = lookup_function(func_name);
    if (!func) return NULL;

    Parameter* p = func->param_list;
    while (p != NULL) {
        if (strcmp(p->name, param_name) == 0) {
            return p;
        }
        p = p->next;
    }
    return NULL;
}

// Obtener el valor de un parámetro
char* get_parameter_value(char* param_name, char* func_name) {
    Parameter* p = find_parameter(param_name, func_name);
    return p ? p->value : NULL;
}

// Obtener el tipo de un parámetro
char* get_parameter_type(char* param_name, char* func_name) {
    Parameter* p = find_parameter(param_name, func_name);
    return p ? p->type : NULL;
}

// Asignar valor a un parámetro
void set_parameter_value(char* param_name, char* func_name, char* new_value) {
    Parameter* p = find_parameter(param_name, func_name);
    if (p) {
        free(p->value);
        p->value = strdup(new_value);
    } else {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: El parametro '%s' no existe en la funcion '%s'.", 
                yylineno, param_name, func_name);
        yyerror(error_msg);
        exit(1);
    }

}

// Limpiar parámetros de una función específica
void clear_function_parameters(char* func_name) {
    FunctionSymbol* func = lookup_function(func_name);
    if (!func) return;

    Parameter* p = func->param_list;
    while (p != NULL) {
        // NO HACEMOS free(p). El parámetro sigue existiendo.
        // Solo limpiamos el valor de la ejecución anterior.
        if (p->value) {
            free(p->value);
            p->value = NULL; 
        }
        p = p->next;
    }
}

// Verificar si un nombre es un parámetro en el contexto actual
int is_parameter_in_current_function(char* name) {
    if (current_function_name == NULL) return 0;
    return find_parameter(name, current_function_name) != NULL;
}
// find_variable modificada
symbol* find_variable(char *name) {
    // Primero verificar si es acceso a array
    symbol* array_access = handle_array_access(name);
    if (current_function_name != NULL) {
        Parameter* param = find_parameter(name, current_function_name);
        if (param != NULL) {
            // Crear un símbolo temporal para compatibilidad
            symbol* temp_sym = (symbol*)malloc(sizeof(symbol));
            temp_sym->name = strdup(param->name);
            temp_sym->value = strdup(param->value);
            temp_sym->type = strdup(param->type);
            temp_sym->operation_str = NULL;
            temp_sym->is_explicitly_typed = true;
            temp_sym->next = NULL;
            return temp_sym;
        }
    }
    
    //printf("acesso: %s\n",handle_array_access("d"));
    if (array_access != NULL) {
        return array_access; 
    }
    
    // Caso normal: búsqueda de variable simple
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
// Reemplaza get_var con esta
char* get_var( char *name) {
    symbol* s = find_variable(name);
    return s ? s->value : NULL;
}

char* get_type(char *name) {
    symbol* s = find_variable(name);
    printf("get_type: Buscando tipo de '%s'\n", s->type);
    return s ? s->type : NULL;
}
char* determine_type(char* str) {
  if (str == NULL) return "null";
    char* val1 = get_var(str) ? get_var(str) : str;
    if(get_var(str)){
       return get_type(str);
    }
    //printf("determine_type: Analizando valor '%s'\n", v);
    int len = strlen(val1);
    // 1. Quitar espacios en blanco de los bordes para una detección precisa
    char* trimmed_str = trim_whitespace(strdup(val1));
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
    if (strcmp(val1, "True") == 0 || strcmp(val1, "False") == 0) {
        return "bool";
    }
    if (strstr(val1, "..") != NULL) {
        return "Range";
    }
    
    // ... (El resto de tu lógica para int, float y string no necesita cambiar) ...
    int has_dot = 0;
    int is_numeric = 1;
    const char* start_ptr = val1;
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
// Reemplaza add_var con esta
void declare_var(char *name, char *value, char *tipo, bool is_explicit, const char* op_str, bool is_const) {
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
    newSymbol->is_constant = is_const;
    newSymbol->next = currentScope->symbol_list; 
    currentScope->symbol_list = newSymbol;
}


float to_float(char* cadena) {
    char* end;
    
    float valor = strtof(cadena, &end);
     printf("end:%s and cadena: %s\n",end,cadena);
    // Verificar si la conversión fue exitosa
    if (end == cadena) {
        printf("Error: no se pudo convertir '%s' a float.\n", cadena);
        return 0.0;
    }

    return valor;
}
char* floatToString(float numero) {
    // El tamaño del buffer puede variar según tus necesidades
    char* buffer = (char*)malloc(20 * sizeof(char));

    // Utilizamos snprintf para convertir el float a char*
    snprintf(buffer, 20, "%.2f", numero);

    return buffer;
}
// Reemplaza reassign_var con esta
void reassign_var(char *name, char *new_value, const char* op_str) {
    if (current_function_name != NULL) {
        Parameter* p = find_parameter(name, current_function_name);
        if (p != NULL) {
            char* new_type = determine_type(new_value);
            
            // Lógica de Tipado para Parámetros:
            // Si el tipo es "any", permitimos TODO y NO cambiamos el tipo declarado.
            if (strcmp(p->type, "any") == 0) {
                if (p->value) free(p->value);
                p->value = strdup(new_value);
                // OJO: No actualizamos p->type. Si era "any", sigue siendo "any" 
                // para permitir futuras asignaciones de otros tipos.
                return; 
            }
            
            // Si tiene tipo explícito (ej: int a), validamos:
            if (strcmp(p->type, new_type) != 0) {
                // Excepción: float acepta int
                if (strcmp(p->type, "float") == 0 && strcmp(new_type, "int") == 0) {
                    float val = to_float(new_value);
                    char* sval = floatToString(val);
                    if (p->value) free(p->value);
                    p->value = sval;
                    return;
                } else {
                    // Error de tipo real
                    char error_msg[512];
                    sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, new_type, name, p->type);
                    yyerror(error_msg);
                    exit(1);
                }
            }
            
            // Si los tipos coinciden, asignamos
            if (p->value) free(p->value);
            p->value = strdup(new_value);
            return;
        }
    }
  symbol* s = find_variable(name);
if (s) {
       // 1. Determinamos el tipo del NUEVO valor (que es un string)
       // Ej: new_value = "10", new_type = "int"
       if (s->is_constant) {
           // Si el valor NO es NULL, significa que ya fue inicializada.
           // Nota: Comparamos con "NULL" string, asegúrate que declare_var use "NULL" para no inicializadas.
           if (strcmp(s->value, "NULL") != 0 || strcmp(s->value, "[]") != 0 || strcmp(s->value, "{}") != 0) {
               char error_msg[512];
               sprintf(error_msg, "Error semantico en linea %d: La constante '%s' ya tiene un valor asignado y no se puede modificar.", yylineno, s->name);
               yyerror(error_msg);
               exit(1);
           }
           // Si es "NULL", permitimos continuar (es la primera asignación).
       }
       char* new_type = determine_type(new_value);
       
       // Preparamos los strings finales
       char* final_value = strdup(new_value); // Ej: "10"
       char* final_type = strdup(new_type);   // Ej: "int"

       // 2. Comprobamos si la variable tiene un tipado explícito (estático)
       if (s->is_explicitly_typed) {
            
            // Si el tipo de la variable (s->type) ya es "float"
            // Y el tipo del nuevo valor (new_type) es "int"
            
            // *** ESTA ES LA ÚNICA EXCEPCIÓN QUE PEDISTE ***
            if (strcmp(s->type, "float") == 0 && strcmp(new_type, "int") == 0) {
      
                // 1. Convertimos el STRING "10" a un float 10.0
                //    usando tu función 
                float converted_val = to_float(new_value); 
                
                // 2. Convertimos el float 10.0 de vuelta a un STRING "10.00"
                //    usando tu función 
                char* converted_str = floatToString(converted_val); 
                
                // 3. Preparamos el *NUEVO STRING* para guardarlo
                free(final_value);
                final_value = converted_str; // final_value es ahora "10.00"
                
                free(final_type);
                final_type = strdup(s->type); // final_type es "float"
            } 
            else if (strcmp(s->type, "NULL") == 0 || strcmp(s->type, "Const") == 0) {
                 // Permitimos que tome el tipo del nuevo valor
                 // Esto ocurre cuando haces: const b; (tipo=NULL/Const) -> b = 2; (tipo=int)
                 free(final_type);
                 final_type = strdup(new_type);
            }
            // Si NO es la excepción float=int, y los tipos no coinciden,
            // (ej: s->type="string" y new_type="int")
            // se lanza el error que ya tenías.
            else if (strcmp(s->type, new_type) != 0) {
                char error_msg[512];
                sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, new_type, s->name, s->type);
                yyerror(error_msg);
                exit(1);
            }
            // Si los tipos son iguales (int=int, string=string), no hace nada
            // y usa los valores por defecto.
       }
       // Si no es explícita, es dinámica y acepta el nuevo tipo (tu lógica original)

        // 3. Actualizamos la variable con los STRINGS finales
        free(s->value);
        s->value = final_value; // Se guarda "10.00" (el string)
        
        free(s->type);
        s->type = final_type; // Se guarda "float" (el string)

        // ... (resto de la función) ...
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



// Reemplaza get_type con esta



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

// Pega esta función antes de print_ast
int is_main_node(const char* type) {
    if (type == NULL) return 0;

    const char* main_nodes[] = {
        "VariableDeclaration",
        "VariableAsignement",
        "CallExpression",
        "FunctionCall",
        "ForLoop",
        "WhileLoop",
        "PerformWhileLoop",
        "if_Condition",
        "SwitchStatement",
        "Case",
        "DefaultCase",
        "Function",
        "PostIncrementStatement",
        "PostDecrementStatement",
        "PreIncrementStatement",
        "PreDecrementStatement",
        //"Block",
        "ParamType",
        NULL // El terminador de la lista
    };

    for (int i = 0; main_nodes[i] != NULL; i++) {
        if (strcmp(type, main_nodes[i]) == 0) {
            return 1; // Es un nodo principal
        }
    }
    return 0; // Es un sub-nodo
}

// Reemplaza tu print_ast actual con esta
void print_ast(ast_node* node, FILE* output, int level) {
    ast_node* current = node;
 while (current != NULL) {
        // Imprimir el nodo actual con su indentación
        for (int i = 0; i < level; i++) {
            fprintf(output, "  ");
        }
        fprintf(output, "%s: %s\n", current->type, current->value ? current->value : "");

        // Los sub-nodos en 'left' siempre se indentan
        if (current->left) {
            print_ast(current->left, output, level + 1);
        }

        // --- LÓGICA CLAVE MODIFICADA ---
        if (current->right != NULL) {
            
            // CASO ESPECIAL: "Block: BlockStart"
            // Si el nodo actual es "Block: BlockStart",
            // sabemos que su 'right' es "Block: BlockEnd"
            // y debe imprimirse al MISMO NIVEL (level), no en (level+1).
            if (strcmp(current->type, "Block") == 0 && 
                current->value != NULL && 
                strcmp(current->value, "BlockStart") == 0) 
            {
                // Avanzamos el puntero. El bucle 'while' lo imprimirá
                // en el siguiente ciclo con el mismo 'level'.
                current = current->right; 
            }else if (!is_main_node(current->right->type)) {
                // No es un nodo principal, es un sub-nodo, indentar.
                print_ast(current->right, output, level + 1);
                current = NULL; // Rompemos la cadena
            } else {
                // Es un nodo principal (hermano), solo avanzar.
             current = current->right; 
            }
        } else {
            // No hay más nodos, salimos.
          current = NULL;
        }
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
        //fix_forloop_indentation_in_file(g_output_path);

    }

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
    int len = strlen(expr);
    // state 0 = esperando operando (número, variable, '(')
    // state 1 = esperando operador (+, -, '*', '/', ')')
    int state = 0; 
    int paren_balance = 0;
    int operador_encontrado = 0;

    while (i < len) {
        // Ignorar espacios en blanco
        if (isspace(expr[i])) {
            i++;
            continue;
        }

        // --- Si estamos esperando un OPERANDO ---
        if (state == 0) {
            if (expr[i] == '(') {
                paren_balance++;
                i++;
                continue;
            }
            
            if (isdigit(expr[i]) || expr[i] == '.') {
                while (i < len && (isdigit(expr[i]) || expr[i] == '.')) i++;
                state = 1; // Ahora esperamos un operador
                continue;
            }

            if (isalpha(expr[i]) || expr[i] == '_') {
                char var_name[256];
                int j = 0;
                // Extraemos el nombre completo de la variable
                while (i < len && (isalnum(expr[i]) || expr[i] == '_')) {
                    var_name[j++] = expr[i++];
                }
                var_name[j] = '\0';

                // Verificación semántica 1: ¿La variable existe? (SE MANTIENE)
                symbol* s = find_variable(var_name);
                if (!s) {
                    char error_msg[512];
                    sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, var_name);
                    yyerror(error_msg);
                    exit(1);
                }
                
                // Verificación semántica 2: ¿El tipo es numérico? (SE ELIMINA SEGÚN LO SOLICITADO)
                
                state = 1; // Variable válida, ahora esperamos un operador
                continue;
            }
            
            return 0; // Error de sintaxis
        }

        // --- Si estamos esperando un OPERADOR ---
        if (state == 1) {
            if (expr[i] == ')') {
                if (paren_balance <= 0) return 0; // Error, no hay paréntesis que cerrar
                paren_balance--;
                i++;
                continue;
            }

            if (strchr("+-*/%", expr[i])) {
                operador_encontrado = 1;
                state = 0; // Ahora esperamos un operando
                i++;
                continue;
            }

            return 0; // Error de sintaxis
        }
    }

    // Verificaciones finales
    if (state == 0) return 0;
    if (paren_balance != 0) return 0;
    if (!operador_encontrado) return 0;

    return 1; // La expresión es válida.
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




void parse_and_store_parameters(FunctionSymbol* func, char* param_string) {
    if (!param_string || strlen(param_string) == 0) return;

    // Hacemos una copia porque strtok destruye el string original
    char* copy = strdup(param_string);
    char* token = strtok(copy, ",");

    while (token != NULL) {
        // Limpiar espacios en blanco al inicio
        while(isspace(*token)) token++;
        
        char* type = "any"; // Tipo por defecto
        char* name = token;
        
        // Detectar si viene con tipo explícito (ej: "int a")
        char* space = strchr(token, ' ');
        if (space) {
            *space = '\0'; // Cortamos el string en el espacio
            type = token;
            name = space + 1;
            while(isspace(*name)) name++; // Limpiar espacios del nombre
        }
          
        // --- AQUÍ LA MAGIA: Guardamos en la función específica ---
        declare_parameter(name, type, func->name);
        func->param_count++;

        token = strtok(NULL, ",");
    }
    free(copy);
}
// Añade una función a la tabla (o la encuentra si ya existe)
// Guarda su nombre y el tipo de retorno esperado.
void add_or_find_function(char* name, char* type) {
    // 1. Buscar si la función ya existe
    for (int i = 0; i < func_count; i++) {
        if (strcmp(func_tab[i].name, name) == 0) {
            // Si ya existe, solo actualizamos el tipo si era 'inferred'
            // O manejamos lógica de redefinición si es necesario
            return; 
        }
    }

    // 2. Si no existe, creamos una nueva en la siguiente posición libre
    // (Asegúrate de no desbordar el array func_tab si tiene límite fijo)
    
    func_tab[func_count].name = strdup(name);
    
    // Si type es NULL o vacío, pon "inferred", sino usa el tipo
    if (type == NULL) func_tab[func_count].return_type = strdup("inferred");
    else func_tab[func_count].return_type = strdup(type);

    func_tab[func_count].return_value = NULL;

    // --- ¡ESTO ES LO IMPORTANTE QUE FALTABA! ---
    // Inicializar la lista enlazada en NULL para que no tenga basura
    func_tab[func_count].param_list = NULL; 
    func_tab[func_count].param_count = 0;
    // -------------------------------------------

    func_tab[func_count].temp_params_check = NULL; // Si usas esto, init en NULL también

    func_count++;
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
        sprintf(error_msg, "Error semantico en linea %d: La funcion '%s' no esta definida.", yylineno, func_name);
        yyerror(error_msg);
        exit(1);
    }
    
    // PASO 2: OBTENER Y CONTAR LOS ARGUMENTOS (solo para validar cantidad)
    char** args = split_string(arg_string ? arg_string : "", ",");
    int arg_count = 0;
    
    // Array para almacenar solo los VALORES (sin los nombres de parámetros)
    char** values_only = NULL;
    int values_count = 0;
    
    if (args) {
        // Primero contar cuántos argumentos hay
        for (int i = 0; args[i] != NULL; i++) {
            arg_count++;
        }
        
        // Crear array para valores
        values_only = malloc(sizeof(char*) * (arg_count + 1));
        
        for (int i = 0; i < arg_count; i++) {
            char* clean_arg = trim_whitespace(args[i]);
            
            // EXTRAER SOLO EL VALOR (lo que viene después del ':')
            char* colon_pos = strchr(clean_arg, ':');
            if (colon_pos) {
                // Formato "parametro: valor" - tomar solo el valor
                char* value_part = trim_whitespace(colon_pos + 1);
                values_only[values_count++] = strdup(value_part);
            } else {
                // Formato directo (solo valor)
                values_only[values_count++] = strdup(clean_arg);
            }
        }
        values_only[values_count] = NULL; // Terminador
    }

    // PASO 3: VALIDACIÓN SOLO DE CANTIDAD DE ARGUMENTOS
    if (values_count != func->param_count) {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La funcion '%s' espera %d argumentos, pero se le dieron %d.", 
                yylineno, func_name, func->param_count, values_count);
        yyerror(error_msg);
        if (args) free_split_string(args);
        if (values_only) free_split_string(values_only);
        exit(1);
    }
    
    // NOTA: La validación de tipos se hace en assign_arguments_to_parameters
    // No validamos tipos aquí
    
    // Limpiar memoria
    if (args) free_split_string(args);
    if (values_only) free_split_string(values_only);
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
        if (end_paren == NULL) {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: Interpolacion sin cerrar en string.", yylineno);
            yyerror(error_msg);
            free(raw_string);
            exit(1);
        }
        
        char expr_str[256];
        int expr_len = end_paren - (hash_pos + 2);
        strncpy(expr_str, hash_pos + 2, expr_len);
        expr_str[expr_len] = '\0';
        
        char* value_to_insert = NULL;

        // --- DETECCIÓN DE ACCESO A ARRAY MEJORADA ---
        char* open_bracket = strchr(expr_str, '[');
        char* close_bracket = strrchr(expr_str, ']');
        
        if (open_bracket && close_bracket && close_bracket > open_bracket) {
            // Es un acceso a array: extraer nombre del array y índice
            char array_name[128];
            strncpy(array_name, expr_str, open_bracket - expr_str);
            array_name[open_bracket - expr_str] = '\0';
            
            char index_str[128];
            strncpy(index_str, open_bracket + 1, close_bracket - (open_bracket + 1));
            index_str[close_bracket - (open_bracket + 1)] = '\0';
            
            char* clean_array_name = trim_whitespace(array_name);
            char* clean_index = trim_whitespace(index_str);
            
            printf("DEBUG: Acceso a array - nombre: '%s', indice: '%s'\n", clean_array_name, clean_index);
            
            // Buscar el array en la tabla de símbolos
            symbol* array_sym = find_variable(clean_array_name);
            if (!array_sym) {
                char error_msg[256];
                sprintf(error_msg, "Error semantico en linea %d: Array '%s' no declarado en interpolacion.", yylineno, clean_array_name);
                yyerror(error_msg);
                free(raw_string);
                exit(1);
            }
            
            if (strcmp(array_sym->type, "Array") != 0) {
                char error_msg[256];
                sprintf(error_msg, "Error semantico en linea %d: '%s' no es un array.", yylineno, clean_array_name);
                yyerror(error_msg);
                free(raw_string);
                exit(1);
            }
            
            // Obtener el valor del array usando el índice
            char* array_data = array_sym->value;
            
            // Verificar si el índice es un número
            if (strcmp(determine_type(clean_index), "int") == 0) {
                int index = atoi(clean_index);
                value_to_insert = get_element_by_index(array_data, index);
                
                if (value_to_insert == NULL) {
                    char error_msg[256];
                    sprintf(error_msg, "Error semantico en linea %d: Indice %d fuera de rango para array '%s'.", yylineno, index, clean_array_name);
                    yyerror(error_msg);
                    free(raw_string);
                    exit(1);
                }
                
                // Quitar comillas si el elemento es un string
                char* unquoted = remove_quotes_safe(value_to_insert);
                if (unquoted != value_to_insert) {
                    free(value_to_insert);
                    value_to_insert = unquoted;
                }
                
                printf("DEBUG: Valor extraido del array: '%s'\n", value_to_insert);
                
            } else {
                // El índice no es un número - podría ser una variable
                symbol* index_sym = find_variable(clean_index);
                if (index_sym && strcmp(index_sym->type, "int") == 0) {
                    int index = atoi(index_sym->value);
                    value_to_insert = get_element_by_index(array_data, index);
                    
                    if (value_to_insert == NULL) {
                        char error_msg[256];
                        sprintf(error_msg, "Error semantico en linea %d: Indice %d fuera de rango para array '%s'.", yylineno, index, clean_array_name);
                        yyerror(error_msg);
                        free(raw_string);
                        exit(1);
                    }
                    
                    // Quitar comillas si el elemento es un string
                    char* unquoted = remove_quotes_safe(value_to_insert);
                    if (unquoted != value_to_insert) {
                        free(value_to_insert);
                        value_to_insert = unquoted;
                    }
                } else {
                    char error_msg[256];
                    sprintf(error_msg, "Error semantico en linea %d: Indice de array '%s' debe ser entero.", yylineno, clean_index);
                    yyerror(error_msg);
                    free(raw_string);
                    exit(1);
                }
            }
            
        } else {
            // No es acceso a array - lógica original para variables simples
            char* trimmed_expr = trim_whitespace(expr_str);
            symbol* s = find_variable(trimmed_expr);
            if (s) {
                value_to_insert = strdup(s->value);
                // Quitar comillas si es string
                char* unquoted = remove_quotes_safe(value_to_insert);
                if (unquoted != value_to_insert) {
                    free(value_to_insert);
                    value_to_insert = unquoted;
                }
            } else {
                char error_msg[256];
                sprintf(error_msg, "Error semantico en linea %d: Variable '%s' no declarada en interpolacion.", yylineno, trimmed_expr);
                yyerror(error_msg);
                free(raw_string);
                exit(1);
            }
        }
        
        // Insertar el valor en el resultado
        if (value_to_insert) {
            strcat(result_buffer, value_to_insert);
            free(value_to_insert);
        } else {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: No se pudo resolver la expresion '%s' en interpolacion.", yylineno, expr_str);
            yyerror(error_msg);
            free(raw_string);
            exit(1);
        }
        
        current_pos = end_paren + 1;
    }

    // Agregar el resto del string después de la última interpolación
    strcat(result_buffer, current_pos);
    free(raw_string);
    
    printf("DEBUG: String despues de interpolacion: '%s'\n", result_buffer);
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
    char error_msg[512];

    
    // PASO : Verificación semántica estática (esto SÍ se hace aquí).
    symbol* s = find_variable((char*)var_name);
    if (!s) {
        sprintf(error_msg, "Error en linea %d: La variable de colección '%s' no ha sido declarada.", yylineno, var_name);
        yyerror(error_msg);
        exit(1);
    }

    // Verificamos que sea un tipo coleccionable.
    if (strcmp(s->type, "Array") != 0 && strcmp(s->type, "Tuple") != 0 && strcmp(s->type, "Dict") != 0) {
        sprintf(error_msg, "Error en linea %d: La variable '%s' es de tipo '%s' y no se puede indexar.", yylineno, var_name, s->type);
        yyerror(error_msg);
        exit(1);
    }

    // PASO 2: Construir la cadena de acceso para que el intérprete la resuelva.
    // No resolvemos el índice aquí, simplemente lo incluimos en el string.
    size_t len = strlen(var_name) + strlen(indexer_input) + 3; // para '[' ']' y '\0'
    char* result = malloc(len);
    if (!result) {
        yyerror("Out of memory");
        exit(1);
    }
    // El resultado será un string literal como "x[d]" o "miArray[2]"
    sprintf(result, "%s[%s]", var_name, indexer_input);

    return result;
}
char* legacy_access_collection_element(const char* var_name, const char* indexer_input) {
    // --- MODIFICACIÓN: Detección profunda de variables ---
    // Copiamos el input porque strtok modifica la cadena
    char* temp_indexer = strdup(indexer_input);
    char* token = strtok(temp_indexer, ":");
    int has_variable = 0;

    // Recorremos cada parte separada por ':' (ej: en "2:d" revisa "2" y luego "d")
    while (token != NULL) {
        // Limpiamos espacios por seguridad
        char* clean_token = trim_whitespace(token);
        
        // Verificamos si este token es una variable existente
        // Nota: Un número "2" o string ""texto"" NO será encontrado por find_variable,
        // pero una variable "d" o "i" SÍ.
        if (find_variable(clean_token)) {
            has_variable = 1;
            break; // Con encontrar UNA variable basta
        }
        
        token = strtok(NULL, ":");
    }
    free(temp_indexer);

    // SI ENCONTRAMOS UNA VARIABLE EN CUALQUIER PARTE DEL ÍNDICE:
    // Devolvemos la estructura cruda "nombre[indice]" para que se cree el ArrayAccess
    // y el intérprete maneje la lógica en tiempo de ejecución.
    if (has_variable) {
        size_t len = strlen(var_name) + strlen(indexer_input) + 3; // +3 para '[', ']' y '\0'
        char* result = malloc(len);
        if (!result) {
            yyerror("Out of memory");
            exit(1);
        }
        sprintf(result, "%s[%s]", var_name, indexer_input);
        return result; // Retorna algo como "d[i]" o "x[2:d]"
    }
    // -----------------------------------------------------
    
    // =======================================================================
    // LÓGICA ORIGINAL (Solo se ejecuta si NO hay variables en el índice)
    // =======================================================================
    char error_msg[512];
    char* var_data = get_var((char*)var_name);
    char* var_type = get_type((char*)var_name);
    
    // Si llegamos aquí, sabemos que no son variables, así que usamos el input directo como literal
    char* resolved_indexer = (char*)indexer_input;

    char* indexer_copy = strdup(resolved_indexer);
    char* current_element_str = strdup(var_data);
    char* current_element_type = strdup(var_type);
    char* single_index = strtok(indexer_copy, ":");
    if (strstr(indexer_input, "..")) {
        
        // Validar que sea un Array (solo arrays soportan rangos numéricos por ahora)
        if (strcmp(var_type, "Array") != 0) {
            char err[256];
            sprintf(err, "Error en linea %d: El slicing (..) solo esta permitido en Arrays, la variable '%s' es de tipo '%s'.", yylineno, var_name, var_type);
            yyerror(err);
            exit(1);
        }

        // --- A. Preparar el contenido del Array ---
        char* raw_content = strdup(var_data);
        // Quitar corchetes [ ... ] para poder separar
        if (raw_content[0] == '[') memmove(raw_content, raw_content+1, strlen(raw_content));
        int len_str = strlen(raw_content);
        if (len_str > 0 && raw_content[len_str-1] == ']') raw_content[len_str-1] = '\0';

        // Obtener elementos separados por coma
        char** elements = split_string(raw_content, ",");
        int arr_len = 0;
        while(elements && elements[arr_len] != NULL) arr_len++;

        // --- B. Detectar tipo de rango ---
        int is_exclusive = 0; // 0 = cerrado (..), 1 = semi-abierto (..<)
        char* delim = "..";
        if (strstr(indexer_input, "..<")) {
            is_exclusive = 1;
            delim = "..<";
        }

        // --- C. Parsear inicio y fin ---
        char* idx_copy = strdup(indexer_input);
        char* token_start = strstr(idx_copy, delim);
        
        if (!token_start) { 
            free(idx_copy); free(raw_content); 
            yyerror("Error interno procesando rango."); exit(1); 
        }
        
        *token_start = '\0'; // Cortamos el string en el delimitador
        char* start_str = idx_copy;
        char* end_str = token_start + strlen(delim); // Avanzamos puntero tras el delim

        int start = atoi(start_str);
        int end = atoi(end_str);
        free(idx_copy);

        // Calcular indice final efectivo
        // Si es 1..3 -> final_end = 3. Si es 1..<3 -> final_end = 2.
        int final_end = is_exclusive ? (end - 1) : end;

        // --- D. Validaciones ---
        if (start < 0) {
            char err[256];
            sprintf(err, "Error de Rango en linea %d: El inicio (%d) no puede ser negativo.", yylineno, start);
            yyerror(err);
            exit(1);
        }
        if (final_end >= arr_len) {
            char err[256];
            sprintf(err, "Error de Rango en linea %d: El limite final (%d) excede el tamaño del array (%d).", yylineno, final_end, arr_len);
            yyerror(err);
            exit(1);
        }
        if (start > final_end) {
             char err[256];
             sprintf(err, "Error de Rango en linea %d: Rango invalido, el inicio (%d) es mayor que el final efectivo (%d).", yylineno, start, final_end);
             yyerror(err);
             exit(1);
        }

        // --- E. Construir el Nuevo Array ---
        // Usamos un buffer grande para el resultado
        char* result_buffer = (char*)malloc(8192); 
        strcpy(result_buffer, "[");
        
        int first = 1;
        for (int i = start; i <= final_end; i++) {
            if (!first) strcat(result_buffer, ", ");
            
            char* val = elements[i];
            // Limpiar espacios del elemento extraido
            while(isspace(*val)) val++;
            
            strcat(result_buffer, val);
            first = 0;
        }
        strcat(result_buffer, "]");
        
        free(raw_content);
        // free_split_string(elements); // Usar si tienes la función para evitar leaks
        return result_buffer;
    }
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
            sprintf(error_msg, "Error en linea %d: Intento de acceso profundo en '%s' con el indice '%s'. El elemento extraido no es una coleccion (es de tipo '%s').", yylineno, var_name, single_index, current_element_type);
            yyerror(error_msg);
            exit(1);
        }

        free(current_element_str);
        current_element_str = next_element_str;
        if (current_element_str == NULL) {
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
        exit(1);
    }

    // ==========================================================
    // LÓGICA PARA VARIABLES ESTÁTICAS
    // ==========================================================
    if (s->is_explicitly_typed) {
        if (strcmp(s->type, "int") != 0 && strcmp(s->type, "float") != 0) {
            // ERROR: Tipo estático no numérico.
            char error_msg[256];
            sprintf(error_msg, "Error de tipo en linea %d: La operacion '%s' solo se puede aplicar a variables estaticas de tipo int o float, no a '%s'.", yylineno, op, s->type);
            yyerror(error_msg);
            exit(1);
        }
        // Si la variable es estática y numérica, la lógica de operación de abajo se encargará.
    }
    // ==========================================================
    // LÓGICA PARA VARIABLES DINÁMICAS
    // ==========================================================
    else {
        if (strcmp(s->type, "NULL") == 0) {
            int value = 0; // Se trata el valor NULL como 0
            if (strcmp(op, "++") == 0) { value++; } else { value--; }
            
            char* new_value_str = to_string(value);
            free(s->value);
            s->value = new_value_str;

            // La variable ahora contiene un número, actualizamos su tipo.
            free(s->type);
            s->type = strdup("int");
            return s->value;
        }
        if (strcmp(s->type, "string") == 0 || strcmp(s->type, "bool") == 0) {
            // ADVERTENCIA: Tipo dinámico no operable.
            fprintf(stderr, "Advertencia en linea %d: La operacion '%s' no se aplico sobre la variable dinamica '%s' porque su valor actual es de tipo '%s'.\n", yylineno, op, s->name, s->type);
            return s->value; // No se hace nada, se retorna el valor original.
        }
    }

    // ==========================================================
    // LÓGICA DE OPERACIÓN (Para estáticas numéricas y dinámicas numéricas)
    // ==========================================================
    char* new_value_str;
    if (strcmp(s->type, "int") == 0) {
        int value = atoi(s->value);
        if (strcmp(op, "++") == 0) { value++; } else { value--; }
        new_value_str = to_string(value);
    } else { // float
        float value = to_float(s->value);
        if (strcmp(op, "++") == 0) { value++; } else { value--; }
        new_value_str = floatToString(value);
    }

    // 4. Actualizar la variable en la tabla de símbolos
    free(s->value);
    s->value = new_value_str;
    if (s->operation_str) {
        free(s->operation_str);
        s->operation_str = NULL;
    }

    return s->value;
}
int is_truthy( char* value_str) {
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

// ESTA ES LA NUEVA FUNCIÓN QUE PEDISTE
ast_node* aplanar_bloque(ast_node* statements_node) {
    if (statements_node == NULL) {
        return NULL;
    }

    // 1. Extraemos las dos partes de tu estructura híbrida.
    ast_node* primera_sentencia = statements_node->left;
    ast_node* resto_de_la_lista = statements_node->right;

    // Liberamos el nodo "Statements" que ya no necesitamos.
    free(statements_node->type);
    free(statements_node);

    // 2. Si no hay una primera sentencia, el resto es la lista completa.
    if (primera_sentencia == NULL) {
        return resto_de_la_lista;
    }

    // 3. Enganchamos el resto de la lista al final de la primera sentencia.
    primera_sentencia->right = resto_de_la_lista;

    // 4. Devolvemos el inicio de la lista ahora 100% plana.
    return primera_sentencia;
}

char* convert_to_int(char* var_name) {
    // Obtener la variable usando tus funciones
    symbol* s = find_variable(var_name);
    if (!s) return NULL;
    
    // Verificar si la variable tiene tipado explícito
   /* if (s->is_explicitly_typed) {
        // Si ya es de tipo int, permitir la conversión
        if (strcmp(s->type, "int") == 0) {
            return strdup(s->value); // Ya es int, no hay cambio
        } else {
            // Tipo explícito diferente a int - ERROR
            return NULL;
        }
    }*/
    
    char* value = s->value;
    char* type = s->type;
    
    // Caso especial: variable NULL
    if (strcmp(value, "NULL") == 0 || strcmp(type, "NULL") == 0) {
        return strdup("0"); // Convertir NULL a 0
    }
    else if (strcmp(type, "int") == 0) {
        return strdup(value); // Ya es int
    }
    else if (strcmp(type, "float") == 0) {
        // Convertir float a int (truncar)
        float fval = to_float(value);
        return to_string((int)fval);
    }
    else if (strcmp(type, "boolean") == 0) {
        // Bool a int
        if (strcmp(value, "True") == 0) return strdup("1");
        else return strdup("0");
    }
    else if (strcmp(type, "string") == 0) {
        // String a int - verificar si es número entero válido
        char* clean_str = remove_quotes_safe(value);
        
        // Verificar formato de número entero
        char* endptr;
        long int num = strtol(clean_str, &endptr, 10);
        
        // Si no hay caracteres extra y al menos un dígito
        if (*endptr == '\0' && endptr != clean_str) {
            char* result = to_string((int)num);
            free(clean_str);
            return result;
        }
        free(clean_str);
    }
    
    return NULL; // Conversión no válida
}

// Añade esta función en la sección de funciones C
int is_array_access_with_variables(const char* value) {
    if (value == NULL) return 0;
    
    // Verificar estructura básica: texto[algo]
    char* open_bracket = strchr(value, '[');
    char* close_bracket = strrchr(value, ']');
    
    if (!open_bracket || !close_bracket || close_bracket <= open_bracket) {
        return 0; // No tiene estructura de array
    }
    
    // Extraer todo el contenido dentro de los corchetes
    int content_len = close_bracket - open_bracket - 1;
    if (content_len <= 0) return 0;
    
    char* content = malloc(content_len + 1);
    strncpy(content, open_bracket + 1, content_len);
    content[content_len] = '\0';
    
    // Dividir por dos puntos para acceso profundo
    char** parts = split_string(content, ":");
    int has_variables = 0;
    
    if (parts) {
        for (int i = 0; parts[i] != NULL; i++) {
            char* part = trim_whitespace(parts[i]);
            
            // Verificar si la parte contiene variables (no es solo numérica)
            if (strlen(part) > 0) {
                // Si no empieza con dígito y no es un número, es variable
                if (!isdigit(part[0])) {
                    has_variables = 1;
                    break;
                }
                
                // Verificar que todo el string sea numérico
                int all_digits = 1;
                for (int j = 0; part[j] != '\0'; j++) {
                    if (!isdigit(part[j])) {
                        all_digits = 0;
                        break;
                    }
                }
                if (!all_digits) {
                    has_variables = 1;
                    break;
                }
            }
        }
        free_split_string(parts);
    }
    
    free(content);
    return has_variables;
}

// Asignar valores de argumentos a parámetros en el orden correcto
void assign_arguments_to_parameters(char* func_name, char* arg_string) {
    // PASO 1: BUSCAR LA FUNCIÓN
    FunctionSymbol* func = lookup_function(func_name);
   
    if (!func) {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La funcion '%s' no esta definida.", yylineno, func_name);
        yyerror(error_msg);
        exit(1);
    }
    
    // PASO 2: OBTENER Y CONTAR LOS ARGUMENTOS
    char** args = split_string(arg_string ? arg_string : "", ",");
    int arg_count = 0;
    
    // Array para almacenar solo los VALORES (sin los nombres de parámetros)
    char** values_only = NULL;
    int values_count = 0;
    
    if (args) {
        // Primero contar cuántos argumentos hay
        for (int i = 0; args[i] != NULL; i++) {
            arg_count++;
        }
        
        // Crear array para valores
        values_only = malloc(sizeof(char*) * (arg_count + 1));
        
        for (int i = 0; i < arg_count; i++) {
            char* clean_arg = trim_whitespace(args[i]);
            
            // EXTRAER SOLO EL VALOR (lo que viene después del ':')
            char* colon_pos = strchr(clean_arg, ':');
            if (colon_pos) {
                // Formato "parametro: valor" - tomar solo el valor
                char* value_part = trim_whitespace(colon_pos + 1);
                values_only[values_count++] = strdup(value_part);
            } else {
                // Formato directo (solo valor)
                values_only[values_count++] = strdup(clean_arg);
            }
        }
        values_only[values_count] = NULL; // Terminador
    }

    // PASO 3: VALIDACIÓN DE CANTIDAD DE ARGUMENTOS
    if (values_count != func->param_count) {
        char error_msg[256];
        sprintf(error_msg, "Error semantico en linea %d: La funcion '%s' espera %d argumentos, pero se le dieron %d.", 
                yylineno, func_name, func->param_count, values_count);
        yyerror(error_msg);
        if (args) free_split_string(args);
        if (values_only) free_split_string(values_only);
        exit(1);
    }
    
    // PASO 4: ASIGNACIÓN Y VALIDACIÓN DE TIPOS (usando values_only)
    Parameter* param = func->param_list;
    int i = 0;
    
    while (param != NULL && values_only && values_only[i] != NULL) {
        char* arg_value = values_only[i];
        
        // Determinar el tipo REAL del argumento
        char* actual_type;
        
        // Primero verificar si es una variable existente
        symbol* var_sym = find_variable(arg_value);
        if (var_sym) {
            // Es una variable, usar su tipo declarado
            actual_type = var_sym->type;
        } else {
            // Es un literal, determinar su tipo
            actual_type = determine_type(arg_value);
        }
        
        printf("DEBUG: Argumento %d = '%s', tipo detectado = '%s', tipo esperado = '%s'\n", 
               i + 1, arg_value, actual_type, param->type);
        
        // Si el parámetro es tipo "any", acepta cualquier cosa
        if (strcmp(param->type, "any") == 0) {
            // Asignar valor al parámetro
            if (param->value) free(param->value);
            param->value = strdup(arg_value);
            
            param = param->next;
            i++;
            continue;
        }
        
        // Validar coincidencia de tipos
        if (strcmp(param->type, actual_type) != 0) {
            // EXCEPCIÓN: float acepta int
            if (strcmp(param->type, "float") == 0 && strcmp(actual_type, "int") == 0) {
                // Permitido - conversión implícita de int a float
                // Convertir el valor int a float
                float converted_val = to_float(arg_value);
                char* converted_str = floatToString(converted_val);
                
                // Asignar valor convertido al parámetro
                if (param->value) free(param->value);
                param->value = strdup(converted_str);
                
                param = param->next;
                i++;
                continue;
            } else {
                // Error de tipo real
                char error_msg[512];
                sprintf(error_msg, "Error de tipo en linea %d: El argumento %d de la funcion '%s' espera tipo '%s' pero recibio '%s' (valor: '%s').", 
                        yylineno, i + 1, func_name, param->type, actual_type, arg_value);
                yyerror(error_msg);
                if (args) free_split_string(args);
                if (values_only) free_split_string(values_only);
                exit(1);
            }
        }
        
        // Asignar valor al parámetro (tipos coinciden)
        if (param->value) free(param->value);
        param->value = strdup(arg_value);
        
        param = param->next;
        i++;
    }
    
    // Limpiar memoria
    if (args) free_split_string(args);
    if (values_only) free_split_string(values_only);
}

// --- AGREGA ESTO AL INICIO DE TU SECCIÓN DE CÓDIGO C (antes de las reglas gramaticales) ---
// O justo antes de la regla arith_expr si prefieres.

int is_current_func_param(char* name) {
    if (current_function_name == NULL) return 0;
    // Usamos tu función find_parameter que ya arreglamos para buscar en la struct
    if (find_parameter(name, current_function_name) != NULL) {
        return 1;
    }
    return 0;
}

int is_runtime_access_string(const char* str) {
    if (str == NULL) return 0;
    // Verifica si la cadena contiene corchetes, indicando un acceso diferido.
    // Esto cubre las cadenas retornadas por legacy_access_collection_element (ej: "d[i]").
    return strchr(str, '[') != NULL && strrchr(str, ']') != NULL;
}

// Función para formatear parámetros como "nombre:tipo"
char* format_parameters_as_string(char* func_name) {
    FunctionSymbol* func = lookup_function(func_name);
    if (!func || !func->param_list) {
        return strdup("\"\""); // String vacío entre comillas
    }
    
    char buffer[4096] = "";
    Parameter* param = func->param_list;
    int first = 1;
    
    while (param != NULL) {
        if (!first) {
            strcat(buffer, ", ");
        }
        
        char param_str[256];
        sprintf(param_str, "%s:%s", param->name, param->type);
        strcat(buffer, param_str);
        
        first = 0;
        param = param->next;
    }
    
    // Poner todo entre comillas
    char* result = malloc(strlen(buffer) + 3);
    sprintf(result, "\"%s\"", buffer);
    return result;
}
// Función para detectar si una expresión es un literal puro (sin variables)
int is_pure_literal_expression(const char* expr) {
    if (expr == NULL) return 1;
    
    // Si es un número (entero o decimal)
    if (isdigit(expr[0]) || (expr[0] == '-' && isdigit(expr[1])) || 
        (expr[0] == '+' && isdigit(expr[1]))) {
        int has_dot = 0;
        for (int i = (expr[0] == '-' || expr[0] == '+') ? 1 : 0; expr[i] != '\0'; i++) {
            if (expr[i] == '.') {
                if (has_dot) return 0;
                has_dot = 1;
            } else if (!isdigit(expr[i])) {
                return 0;
            }
        }
        return 1;
    }
    
    // Si es un string entre comillas
    if (expr[0] == '"' && expr[strlen(expr)-1] == '"') {
        return 1;
    }
    
    // Si es un booleano
    if (strcmp(expr, "True") == 0 || strcmp(expr, "False") == 0) {
        return 1;
    }
    
    // Si es un array/tupla/diccionario literal (solo con literales)
    if (expr[0] == '[' || expr[0] == '(' || expr[0] == '{') {
        // Análisis simple - asumimos que si empieza con estos caracteres es literal
        // Podrías hacer un análisis más complejo si necesitas
        return 1;
    }
    
    // Si es NULL
    if (strcmp(expr, "NULL") == 0) {
        return 1;
    }
    
    // Si contiene cualquier caracter alfabético que no sea en un string, probablemente es variable
    for (int i = 0; expr[i] != '\0'; i++) {
        if (isalpha(expr[i]) && expr[i] != 'T' && expr[i] != 'F') { // Excluir True/False
            // Verificar que no sea parte de un string
            int in_string = 0;
            for (int j = 0; j < i; j++) {
                if (expr[j] == '"' && (j == 0 || expr[j-1] != '\\')) {
                    in_string = !in_string;
                }
            }
            if (!in_string) {
                return 0; // Es una variable
            }
        }
    }
    
    return 1; // Es literal
}
void register_math_library() {
    // Funciones
    add_or_find_function("sqrt", "float");
    declare_parameter("x", "any", "sqrt");
    FunctionSymbol* func = lookup_function("sqrt");
    parse_and_store_parameters(func, "x:any");
    
    add_or_find_function("sin", "float");
    declare_parameter("x", "any", "sin");
    
    add_or_find_function("cos", "float");
    declare_parameter("x", "any", "cos");
    
    add_or_find_function("pow", "float");
    declare_parameter("base", "any", "pow");
    declare_parameter("exp", "any", "pow");
    
    // Constantes
    declare_var("mPI", "3.14159265", "float", true, NULL, true);
    declare_var("E", "2.71828182", "float", true, NULL, true);
}



/* Line 189 of yacc.c  */
#line 3066 "semantic.tab.c"

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
     CONST = 275,
     DOT = 276,
     COM = 277,
     SHARP = 278,
     LSQUARE = 279,
     RSQUARE = 280,
     SQUARES_L_R = 281,
     ELSE = 282,
     ELSE_IF = 283,
     RANGE_SEMI_OPEN = 284,
     IFX = 285,
     EQUALC = 286,
     UNEQUAL = 287,
     GREATERTHAN = 288,
     LESSTHAN = 289,
     GREATERTHAN_EQUAL = 290,
     LESSTHAN_EQUAL = 291,
     TRUE = 292,
     FALSE = 293,
     BOOL = 294,
     INDENT = 295,
     DEDENT = 296,
     STRUCT = 297,
     TSTRING = 298,
     TINT = 299,
     TFLOAT = 300,
     TBOOL = 301,
     TVOID = 302,
     DOTYPEINT = 303,
     FOR = 304,
     IN = 305,
     RANGE = 306,
     MAIN = 307,
     DOTYPE = 308,
     APPEND = 309,
     LENGHT = 310,
     WHILE = 311,
     IF = 312,
     PERFORM = 313,
     BREAK = 314,
     RETURN = 315,
     MOD = 316,
     CONTINUE = 317,
     NOT = 318,
     FUNCTION = 319,
     FUNC = 320,
     PARENS = 321,
     QUESTION_MARK = 322,
     SWITCH = 323,
     CASE = 324,
     DEFAULT = 325,
     startRace = 326,
     endRace = 327,
     OR = 328,
     AND = 329,
     DECIMAL = 330,
     NEWLINE = 331,
     IM = 332,
     IM_Math = 333,
     PI = 334,
     EQUATION = 335
   };
#endif



#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
typedef union YYSTYPE
{

/* Line 214 of yacc.c  */
#line 2992 "semantic.y"

    int ival;
    char *sval;
    char **arrval;
    float fval;
    struct ast_node* node;



/* Line 214 of yacc.c  */
#line 3192 "semantic.tab.c"
} YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define yystype YYSTYPE /* obsolescent; will be withdrawn */
# define YYSTYPE_IS_DECLARED 1
#endif


/* Copy the second part of user declarations.  */


/* Line 264 of yacc.c  */
#line 3204 "semantic.tab.c"

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
#define YYLAST   1043

/* YYNTOKENS -- Number of terminals.  */
#define YYNTOKENS  83
/* YYNNTS -- Number of nonterminals.  */
#define YYNNTS  74
/* YYNRULES -- Number of rules.  */
#define YYNRULES  209
/* YYNRULES -- Number of states.  */
#define YYNSTATES  412

/* YYTRANSLATE(YYLEX) -- Bison symbol number corresponding to YYLEX.  */
#define YYUNDEFTOK  2
#define YYMAXUTOK   335

#define YYTRANSLATE(YYX)						\
  ((unsigned int) (YYX) <= YYMAXUTOK ? yytranslate[YYX] : YYUNDEFTOK)

/* YYTRANSLATE[YYLEX] -- Bison symbol number corresponding to YYLEX.  */
static const yytype_uint8 yytranslate[] =
{
       0,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
      81,    82,     2,     2,     2,     2,     2,     2,     2,     2,
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
      75,    76,    77,    78,    79,    80
};

#if YYDEBUG
/* YYPRHS[YYN] -- Index of the first RHS symbol of rule number YYN in
   YYRHS.  */
static const yytype_uint16 yyprhs[] =
{
       0,     0,     3,     4,     7,     9,    11,    12,    15,    18,
      21,    23,    25,    28,    30,    32,    34,    36,    38,    41,
      44,    46,    51,    54,    57,    60,    63,    66,    71,    78,
      84,    89,    93,    96,   101,   103,   105,   107,   109,   111,
     113,   116,   121,   125,   131,   138,   145,   153,   160,   168,
     174,   181,   188,   196,   204,   213,   220,   230,   235,   241,
     248,   258,   264,   269,   276,   286,   291,   297,   305,   316,
     323,   329,   333,   339,   341,   345,   349,   354,   358,   360,
     362,   366,   371,   377,   381,   385,   389,   391,   393,   395,
     398,   399,   400,   406,   407,   408,   414,   415,   423,   431,
     437,   444,   451,   459,   465,   472,   479,   487,   493,   500,
     507,   515,   518,   522,   523,   524,   530,   531,   532,   538,
     544,   546,   549,   554,   558,   559,   567,   568,   576,   577,
     586,   587,   596,   597,   603,   604,   610,   611,   618,   619,
     626,   629,   634,   636,   640,   643,   645,   647,   651,   653,
     655,   657,   659,   661,   664,   667,   669,   671,   673,   675,
     679,   681,   683,   685,   687,   689,   690,   692,   694,   698,
     702,   706,   710,   714,   718,   722,   726,   728,   730,   732,
     734,   738,   740,   742,   744,   746,   748,   753,   759,   761,
     763,   765,   770,   772,   776,   778,   780,   782,   784,   788,
     790,   794,   798,   802,   806,   810,   814,   818,   820,   824
};

/* YYRHS -- A `-1'-separated list of the rules' RHS.  */
static const yytype_int16 yyrhs[] =
{
      84,     0,    -1,    -1,    84,    86,    -1,    16,    -1,    76,
      -1,    -1,    88,    85,    -1,    90,    85,    -1,    99,    85,
      -1,   110,    -1,   124,    -1,   133,    85,    -1,   112,    -1,
     113,    -1,   114,    -1,   121,    -1,    87,    -1,    89,    85,
      -1,   104,    85,    -1,    78,    -1,     9,    81,   141,    82,
      -1,   140,     7,    -1,   140,     8,    -1,     7,   140,    -1,
       8,   140,    -1,    10,     3,    -1,    10,     3,    15,   141,
      -1,    10,     3,    15,    71,   144,    72,    -1,     3,    15,
      71,   144,    72,    -1,    10,     3,    15,   101,    -1,     3,
      15,   141,    -1,   137,     3,    -1,   137,     3,    15,   141,
      -1,    94,    -1,    95,    -1,    96,    -1,    92,    -1,    93,
      -1,    91,    -1,    20,     3,    -1,    20,     3,    15,   141,
      -1,    20,   137,     3,    -1,    20,   137,     3,    15,   141,
      -1,    20,     3,    15,    71,   144,    72,    -1,    10,     3,
      15,   142,    98,   143,    -1,    10,     3,    15,   142,    98,
      22,   143,    -1,   137,     3,    15,   142,    98,   143,    -1,
     137,     3,    15,   142,    98,    22,   143,    -1,     3,    15,
     142,    98,   143,    -1,     3,    15,   142,    98,    22,   143,
      -1,    20,     3,    15,   142,    98,   143,    -1,    20,     3,
      15,   142,    98,    22,   143,    -1,    20,   137,     3,    15,
     142,    98,   143,    -1,    20,   137,     3,    15,   142,    98,
      22,   143,    -1,    10,     3,    15,    24,    98,    25,    -1,
      10,     3,    24,     6,    25,    15,    24,    98,    25,    -1,
      10,     3,    15,    26,    -1,    10,     3,    24,     6,    25,
      -1,   137,     3,    15,    24,    98,    25,    -1,   137,     3,
      24,     6,    25,    15,    24,    98,    25,    -1,   137,     3,
      24,     6,    25,    -1,   137,     3,    15,    26,    -1,    20,
       3,    15,    24,    98,    25,    -1,    20,     3,    24,     6,
      25,    15,    24,    98,    25,    -1,    20,     3,    15,    26,
      -1,    20,     3,    24,     6,    25,    -1,    20,   137,     3,
      15,    24,    98,    25,    -1,    20,   137,     3,    24,     6,
      25,    15,    24,    98,    25,    -1,    20,   137,     3,    24,
       6,    25,    -1,    20,   137,     3,    15,    26,    -1,     3,
      15,    26,    -1,     3,    15,    24,    98,    25,    -1,   141,
      -1,    71,   144,    72,    -1,   142,   155,   143,    -1,   142,
     155,    22,   143,    -1,    24,    98,    25,    -1,    26,    -1,
      97,    -1,    98,    22,    97,    -1,    17,    81,     3,    82,
      -1,    17,    81,     3,    82,    48,    -1,    10,     3,    50,
      -1,   141,    51,   141,    -1,   141,    29,   141,    -1,    71,
      -1,    72,    -1,    59,    -1,    60,   141,    -1,    -1,    -1,
     102,   106,   139,   103,   107,    -1,    -1,    -1,    40,   108,
     139,    41,   109,    -1,    -1,    49,    81,   100,   151,    82,
     111,   105,    -1,    49,    81,   100,   151,    82,    19,   105,
      -1,    56,    81,   153,    82,   105,    -1,    56,    81,   153,
      82,    19,   105,    -1,    58,   105,    56,    81,   153,    82,
      -1,    58,    19,   105,    56,    81,   153,    82,    -1,    57,
      81,   153,    82,   105,    -1,    57,    81,   153,    82,    19,
     105,    -1,    57,    81,   153,    82,   105,   115,    -1,    57,
      81,   153,    82,    19,   105,   115,    -1,    28,    81,   153,
      82,   105,    -1,    28,    81,   153,    82,    19,   105,    -1,
      28,    81,   153,    82,   105,   115,    -1,    28,    81,   153,
      82,    19,   105,   115,    -1,    27,   105,    -1,    27,    19,
     105,    -1,    -1,    -1,   102,   117,   122,   103,   118,    -1,
      -1,    -1,    40,   119,   122,    41,   120,    -1,    68,    81,
     140,    82,   116,    -1,   123,    -1,   122,   123,    -1,    69,
     141,    19,   139,    -1,    70,    19,   139,    -1,    -1,    64,
       3,    81,   134,    82,   125,   105,    -1,    -1,    65,     3,
      81,   134,    82,   126,   105,    -1,    -1,   137,    64,     3,
      81,   134,    82,   127,   105,    -1,    -1,   137,    65,     3,
      81,   134,    82,   128,   105,    -1,    -1,    64,     3,    66,
     129,   105,    -1,    -1,    65,     3,    66,   130,   105,    -1,
      -1,   137,    64,     3,    66,   131,   105,    -1,    -1,   137,
      65,     3,    66,   132,   105,    -1,     3,    66,    -1,     3,
      81,   136,    82,    -1,   135,    -1,   134,    22,   135,    -1,
     137,     3,    -1,     3,    -1,   141,    -1,   136,    22,   141,
      -1,    44,    -1,    45,    -1,    43,    -1,    46,    -1,    47,
      -1,   140,    48,    -1,   139,    86,    -1,    86,    -1,     3,
      -1,   150,    -1,   147,    -1,   141,    21,   141,    -1,   156,
      -1,   154,    -1,   138,    -1,    81,    -1,    82,    -1,    -1,
     145,    -1,   146,    -1,   145,    22,   146,    -1,     4,    19,
      97,    -1,   142,   141,   143,    -1,   141,    11,   141,    -1,
     141,    12,   141,    -1,   141,    13,   141,    -1,   141,    14,
     141,    -1,   141,    61,   141,    -1,     6,    -1,   101,    -1,
     140,    -1,     4,    -1,   148,    19,   148,    -1,    37,    -1,
      38,    -1,     6,    -1,     4,    -1,    75,    -1,   140,    24,
     148,    25,    -1,   141,    67,   141,    19,   141,    -1,     5,
      -1,   140,    -1,   149,    -1,     3,    81,   136,    82,    -1,
     101,    -1,   141,    50,   141,    -1,   140,    -1,    74,    -1,
      73,    -1,   154,    -1,   141,    50,   141,    -1,   149,    -1,
     153,   152,   153,    -1,   141,    31,   141,    -1,   141,    32,
     141,    -1,   141,    33,   141,    -1,   141,    34,   141,    -1,
     141,    35,   141,    -1,   141,    36,   141,    -1,    97,    -1,
     155,    22,    97,    -1,    80,    81,     4,    82,    -1
};

/* YYRLINE[YYN] -- source line where rule number YYN was defined.  */
static const yytype_uint16 yyrline[] =
{
       0,  3042,  3042,  3043,  3045,  3046,  3047,  3049,  3050,  3051,
    3052,  3053,  3054,  3055,  3056,  3057,  3058,  3059,  3060,  3062,
    3064,  3071,  3113,  3117,  3121,  3125,  3132,  3135,  3157,  3164,
    3182,  3186,  3225,  3243,  3265,  3266,  3267,  3268,  3269,  3270,
    3274,  3278,  3292,  3300,  3316,  3325,  3334,  3343,  3359,  3376,
    3389,  3403,  3412,  3421,  3437,  3456,  3464,  3471,  3478,  3485,
    3501,  3515,  3522,  3530,  3538,  3545,  3552,  3560,  3575,  3589,
    3596,  3604,  3614,  3637,  3639,  3645,  3651,  3657,  3664,  3668,
    3672,  3680,  3684,  3689,  3694,  3699,  3705,  3708,  3710,  3711,
    3775,  3775,  3775,  3776,  3776,  3776,  3778,  3778,  3800,  3817,
    3829,  3835,  3847,  3861,  3872,  3883,  3894,  3909,  3918,  3927,
    3936,  3945,  3948,  3952,  3952,  3952,  3953,  3953,  3953,  3955,
    3964,  3965,  3982,  3987,  3992,  3992,  4021,  4021,  4044,  4044,
    4063,  4063,  4081,  4081,  4100,  4100,  4122,  4122,  4140,  4140,
    4158,  4162,  4169,  4170,  4172,  4173,  4178,  4192,  4226,  4227,
    4228,  4229,  4230,  4236,  4263,  4273,  4275,  4293,  4294,  4295,
    4301,  4302,  4303,  4306,  4312,  4318,  4322,  4328,  4332,  4348,
    4353,  4354,  4390,  4420,  4458,  4486,  4519,  4520,  4521,  4522,
    4523,  4530,  4531,  4534,  4539,  4540,  4545,  4557,  4570,  4577,
    4582,  4584,  4627,  4628,  4632,  4648,  4649,  4650,  4651,  4653,
    4659,  4673,  4677,  4682,  4686,  4690,  4694,  4700,  4701,  4736
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
  "CONST", "DOT", "COM", "SHARP", "LSQUARE", "RSQUARE", "SQUARES_L_R",
  "ELSE", "ELSE_IF", "RANGE_SEMI_OPEN", "IFX", "EQUALC", "UNEQUAL",
  "GREATERTHAN", "LESSTHAN", "GREATERTHAN_EQUAL", "LESSTHAN_EQUAL", "TRUE",
  "FALSE", "BOOL", "INDENT", "DEDENT", "STRUCT", "TSTRING", "TINT",
  "TFLOAT", "TBOOL", "TVOID", "DOTYPEINT", "FOR", "IN", "RANGE", "MAIN",
  "DOTYPE", "APPEND", "LENGHT", "WHILE", "IF", "PERFORM", "BREAK",
  "RETURN", "MOD", "CONTINUE", "NOT", "FUNCTION", "FUNC", "PARENS",
  "QUESTION_MARK", "SWITCH", "CASE", "DEFAULT", "startRace", "endRace",
  "OR", "AND", "DECIMAL", "NEWLINE", "IM", "IM_Math", "PI", "EQUATION",
  "'('", "')'", "$accept", "program", "end_statement", "statement",
  "library_call", "print", "increment_decrement_stmt", "var", "const",
  "tuples", "tuples_const", "array_decl", "array_const_decl",
  "array_assing", "list_item", "list_item_list", "read", "var_for",
  "range", "rlrace", "rbrace", "sentences", "block", "$@1", "$@2", "$@3",
  "$@4", "for_loop", "$@5", "while_loop", "perform_while_loop",
  "if_condition", "condtional_stmt", "switch_block", "$@6", "$@7", "$@8",
  "$@9", "switch_cases", "case_list", "single_case", "function_decl",
  "@10", "@11", "@12", "@13", "@14", "@15", "@16", "@17", "function_call",
  "parameter_list", "param_decl", "argument_list", "types",
  "variable_conversion", "statements", "variable", "expr", "paren_left",
  "paren_right", "dict_body", "pair_list", "key_value_pair", "arith_expr",
  "array_indexer", "bool", "term", "for_condition", "logicals",
  "condition", "comparison", "expr_list", "eqt", 0
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
     325,   326,   327,   328,   329,   330,   331,   332,   333,   334,
     335,    40,    41
};
# endif

/* YYR1[YYN] -- Symbol number of symbol that rule YYN derives.  */
static const yytype_uint8 yyr1[] =
{
       0,    83,    84,    84,    85,    85,    85,    86,    86,    86,
      86,    86,    86,    86,    86,    86,    86,    86,    86,    86,
      87,    88,    89,    89,    89,    89,    90,    90,    90,    90,
      90,    90,    90,    90,    90,    90,    90,    90,    90,    90,
      91,    91,    91,    91,    91,    92,    92,    92,    92,    92,
      92,    93,    93,    93,    93,    94,    94,    94,    94,    94,
      94,    94,    94,    95,    95,    95,    95,    95,    95,    95,
      95,    96,    96,    97,    97,    97,    97,    97,    97,    98,
      98,    99,    99,   100,   101,   101,   102,   103,   104,   104,
     106,   107,   105,   108,   109,   105,   111,   110,   110,   112,
     112,   113,   113,   114,   114,   114,   114,   115,   115,   115,
     115,   115,   115,   117,   118,   116,   119,   120,   116,   121,
     122,   122,   123,   123,   125,   124,   126,   124,   127,   124,
     128,   124,   129,   124,   130,   124,   131,   124,   132,   124,
     133,   133,   134,   134,   135,   135,   136,   136,   137,   137,
     137,   137,   137,   138,   139,   139,   140,   141,   141,   141,
     141,   141,   141,   142,   143,   144,   144,   145,   145,   146,
     147,   147,   147,   147,   147,   147,   148,   148,   148,   148,
     148,   149,   149,   150,   150,   150,   150,   150,   150,   150,
     150,   150,   151,   151,   151,   152,   152,   153,   153,   153,
     153,   154,   154,   154,   154,   154,   154,   155,   155,   156
};

/* YYR2[YYN] -- Number of symbols composing right hand side of rule YYN.  */
static const yytype_uint8 yyr2[] =
{
       0,     2,     0,     2,     1,     1,     0,     2,     2,     2,
       1,     1,     2,     1,     1,     1,     1,     1,     2,     2,
       1,     4,     2,     2,     2,     2,     2,     4,     6,     5,
       4,     3,     2,     4,     1,     1,     1,     1,     1,     1,
       2,     4,     3,     5,     6,     6,     7,     6,     7,     5,
       6,     6,     7,     7,     8,     6,     9,     4,     5,     6,
       9,     5,     4,     6,     9,     4,     5,     7,    10,     6,
       5,     3,     5,     1,     3,     3,     4,     3,     1,     1,
       3,     4,     5,     3,     3,     3,     1,     1,     1,     2,
       0,     0,     5,     0,     0,     5,     0,     7,     7,     5,
       6,     6,     7,     5,     6,     6,     7,     5,     6,     6,
       7,     2,     3,     0,     0,     5,     0,     0,     5,     5,
       1,     2,     4,     3,     0,     7,     0,     7,     0,     8,
       0,     8,     0,     5,     0,     5,     0,     6,     0,     6,
       2,     4,     1,     3,     2,     1,     1,     3,     1,     1,
       1,     1,     1,     2,     2,     1,     1,     1,     1,     3,
       1,     1,     1,     1,     1,     0,     1,     1,     3,     3,
       3,     3,     3,     3,     3,     3,     1,     1,     1,     1,
       3,     1,     1,     1,     1,     1,     4,     5,     1,     1,
       1,     4,     1,     3,     1,     1,     1,     1,     3,     1,
       3,     3,     3,     3,     3,     3,     3,     1,     3,     4
};

/* YYDEFACT[STATE-NAME] -- Default rule to reduce with in state
   STATE-NUM when YYTABLE doesn't specify something else to do.  Zero
   means the default is an error.  */
static const yytype_uint8 yydefact[] =
{
       2,     0,     1,   156,     0,     0,     0,     0,     0,     0,
     150,   148,   149,   151,   152,     0,     0,     0,     0,    88,
       0,     0,     0,     0,    20,     3,    17,     6,     6,     6,
      39,    37,    38,    34,    35,    36,     6,     6,    10,    13,
      14,    15,    16,    11,     6,     0,     0,     0,   140,     0,
     156,    24,    25,     0,    26,     0,    40,     0,     0,     0,
       0,     0,    93,    86,    90,     0,   156,   184,   188,   183,
     181,   182,   185,     0,   163,   162,   189,    89,     0,   158,
     190,   157,   161,   160,     0,     0,     0,     4,     5,     7,
      18,     8,     9,    19,    12,    32,     0,     0,    22,    23,
       0,    71,   165,    31,     0,     0,   146,     0,     0,     0,
       0,     0,     0,    42,     0,     0,     0,   190,     0,   161,
       0,     0,     0,     0,     0,     0,     0,     0,   153,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,   132,     0,   134,     0,     0,     0,     0,
       0,     0,     0,    78,   165,    79,     0,    73,     0,     0,
       0,   166,   167,     0,    73,     0,   141,    21,     0,    57,
     165,    30,    27,     0,     0,    81,     0,    65,   165,    41,
       0,     0,     0,     0,     0,   192,   189,     0,     0,     0,
     196,   195,     0,     0,     0,     0,   155,     0,     0,     0,
       0,     0,   184,   183,   177,   189,     0,     0,   171,   172,
     173,   174,   159,   201,   202,   203,   204,   205,   206,   175,
       0,   164,   170,     0,   145,     0,   142,     0,     0,     0,
       0,     0,    62,    33,     0,     0,   136,     0,   138,     0,
       0,     0,     0,    72,   207,     0,     0,    29,     0,     0,
      49,   147,     0,     0,     0,     0,     0,    58,    82,     0,
       0,     0,    66,     0,    70,    43,     0,     0,    83,     0,
      96,   198,     0,    99,   200,     0,   103,     0,    94,   154,
      87,    91,     0,   191,   209,     0,   186,     0,   133,     0,
     124,   144,   135,   126,   116,   113,   119,     0,     0,    61,
       0,     0,     0,     0,    77,    74,    80,     0,    75,   169,
     168,    50,    55,    28,    85,    84,     0,    45,     0,    63,
      44,     0,    51,     0,     0,     0,    69,   193,     0,     0,
     100,   104,     0,     0,   105,     0,    95,    92,   101,   180,
     187,   143,     0,     0,     0,     0,    59,     0,    47,     0,
     137,   128,   139,   130,   208,    76,    46,     0,    52,     0,
      67,     0,    53,     0,    98,    97,   106,     0,   111,     0,
     102,   125,   127,     0,     0,     0,   120,     0,    48,     0,
       0,     0,     0,     0,    54,     0,   112,     0,     0,     0,
     117,   121,   114,     0,   129,   131,    56,    64,     0,     0,
       0,   123,   118,   115,    60,    68,     0,   107,   122,   108,
     109,   110
};

/* YYDEFGOTO[NTERM-NUM].  */
static const yytype_int16 yydefgoto[] =
{
      -1,     1,    89,   196,    26,    27,    28,    29,    30,    31,
      32,    33,    34,    35,   155,   156,    36,   115,   204,    64,
     281,    37,    65,   123,   337,   122,   336,    38,   329,    39,
      40,    41,   334,   296,   345,   403,   344,   402,    42,   375,
     376,    43,   342,   343,   380,   381,   223,   228,   300,   302,
      44,   225,   226,   105,    45,    75,   197,    76,   157,    78,
     222,   160,   161,   162,    79,   207,    80,    81,   188,   193,
     118,    82,   245,    83
};

/* YYPACT[STATE-NUM] -- Index in YYTABLE of the portion describing
   STATE-NUM.  */
#define YYPACT_NINF -319
static const yytype_int16 yypact[] =
{
    -319,   432,  -319,   -10,     5,     5,   -48,    39,   -28,   219,
    -319,  -319,  -319,  -319,  -319,    -9,    84,   108,    38,  -319,
     464,    80,   116,   137,  -319,  -319,  -319,     3,     3,     3,
    -319,  -319,  -319,  -319,  -319,  -319,     3,     3,  -319,  -319,
    -319,  -319,  -319,  -319,     3,     4,   146,    22,  -319,   464,
    -319,  -319,  -319,   464,    52,   175,    60,   228,   101,   464,
     464,   -17,  -319,  -319,  -319,   192,   180,  -319,  -319,  -319,
    -319,  -319,  -319,   195,  -319,  -319,    96,   962,   464,  -319,
    -319,  -319,  -319,  -319,    49,    82,     5,  -319,  -319,  -319,
    -319,  -319,  -319,  -319,  -319,   196,   247,   277,  -319,  -319,
     344,  -319,   284,   962,   344,    13,   962,   597,   456,   286,
     215,   509,   295,   217,   302,   464,   847,   165,   185,   234,
     240,   263,   724,   724,   229,   464,   326,   520,  -319,   464,
     464,   464,   464,   464,   464,   464,   464,   464,   464,   464,
     464,   464,   726,  -319,   318,  -319,   318,   257,   516,   334,
     104,   134,   344,  -319,   284,  -319,    48,   962,   344,   322,
     271,   333,  -319,    14,   726,   464,  -319,  -319,   344,  -319,
     284,  -319,   806,   344,   320,   308,   344,  -319,   284,   962,
     344,   341,   545,   361,   324,  -319,    26,   765,   291,   464,
    -319,  -319,    85,   464,   139,   298,  -319,   595,   658,   464,
      16,   311,    12,   127,  -319,   250,   806,   169,   173,   173,
     532,   532,   976,   541,   541,   541,   541,   541,   541,   532,
     888,  -319,  -319,   -17,  -319,    17,  -319,   395,   -17,    18,
      -6,   344,  -319,   962,   344,   376,  -319,   318,  -319,   318,
     204,   331,   344,  -319,  -319,    19,   344,  -319,   284,     6,
    -319,   962,   248,   336,   464,   464,    23,   391,  -319,   268,
     342,    25,   402,   344,  -319,   962,   344,   385,  -319,   464,
     404,   962,   -17,  -319,   -53,   -17,   186,   464,  -319,  -319,
    -319,  -319,   304,  -319,  -319,   520,  -319,   464,  -319,   318,
    -319,  -319,  -319,  -319,  -319,  -319,  -319,   287,    30,   406,
     -17,    36,   -17,    41,  -319,  -319,  -319,     6,  -319,  -319,
    -319,  -319,  -319,  -319,   962,   962,     6,  -319,   403,  -319,
    -319,     6,  -319,   405,   329,    42,   416,   962,   -17,   -17,
    -319,   186,   152,   352,  -319,   323,  -319,  -319,  -319,   415,
     532,  -319,   -17,   -17,   174,   174,  -319,     6,  -319,   412,
    -319,  -319,  -319,  -319,  -319,  -319,  -319,   344,  -319,   344,
    -319,     6,  -319,   413,  -319,  -319,  -319,   -17,  -319,   464,
    -319,  -319,  -319,   464,   419,   133,  -319,   254,  -319,   344,
     -17,   -17,   347,   358,  -319,   344,  -319,   338,   925,   724,
    -319,  -319,  -319,   362,  -319,  -319,  -319,  -319,   369,   153,
     724,   724,  -319,  -319,  -319,  -319,   -17,   186,   724,   186,
    -319,  -319
};

/* YYPGOTO[NTERM-NUM].  */
static const yytype_int16 yypgoto[] =
{
    -319,  -319,   300,     1,  -319,  -319,  -319,  -319,  -319,  -319,
    -319,  -319,  -319,  -319,   -30,   126,  -319,  -319,    75,   213,
      68,  -319,   -47,  -319,  -319,  -319,  -319,  -319,  -319,  -319,
    -319,  -319,  -318,  -319,  -319,  -319,  -319,  -319,  -319,   102,
    -211,  -319,  -319,  -319,  -319,  -319,  -319,  -319,  -319,  -319,
    -319,  -145,   157,   325,    15,  -319,  -117,    -1,     2,    69,
      97,   -88,  -319,   203,  -319,   168,   -44,  -319,  -319,  -319,
     -31,   -42,  -319,  -319
};

/* YYTABLE[YYPACT[STATE-NUM]].  What to do in state STATE-NUM.  If
   positive, shift that token.  If negative, reduce the rule which
   number is the opposite.  If zero, do what YYDEFACT says.
   If YYTABLE_NINF, syntax error.  */
#define YYTABLE_NINF -200
static const yytype_int16 yytable[] =
{
      46,   229,    25,    51,    52,    47,   198,    95,    50,    66,
      67,    68,    69,   366,   121,   117,   117,   119,   119,    87,
     190,   191,    77,    62,    57,    66,    67,    68,    69,   120,
     152,  -179,   153,    53,   294,   165,   249,  -179,   165,   289,
     289,   307,    54,    70,    71,   316,   100,   321,   101,   103,
     127,   106,   347,    55,    63,   107,    48,    61,   289,    70,
      71,   116,   116,   289,   361,    63,   241,   108,    96,    97,
     242,    49,    58,   243,   128,   111,   109,   154,    62,    88,
     142,    72,   253,    84,   112,   147,    73,    74,   221,   410,
     260,   411,   301,   102,   303,   166,   221,    72,   283,   290,
     293,   221,    73,    74,   272,   221,   164,   221,  -194,    63,
     172,   114,   221,   179,   186,   143,   104,   187,   351,    85,
     127,    46,    46,   353,   221,    62,   205,   106,   244,   206,
     144,   208,   209,   210,   211,   212,   213,   214,   215,   216,
     217,   218,   219,   220,   128,   273,  -176,   276,   145,   117,
     233,   119,  -176,    98,    99,   117,    63,   119,   275,   227,
     164,   227,   274,   146,   391,    59,   391,   251,   282,   158,
     236,   367,   406,   158,   390,   164,   288,   173,   110,    62,
     180,   292,   164,   171,   265,   237,   131,   132,   285,    60,
     185,   271,    62,    62,   286,   116,    46,    46,   279,   279,
     238,   116,   373,   374,   134,   135,   136,   137,   138,   139,
      63,   148,   306,   332,   333,   239,   309,   234,    86,   306,
     149,   158,    56,    63,    63,   330,   242,   158,   331,   304,
     163,   113,   182,   117,   140,   119,   164,   158,  -199,  -199,
     141,   183,   158,   373,   374,   158,   335,  -199,   124,   158,
     150,   266,   227,   350,   227,   352,   314,   315,   190,   191,
     250,   125,    10,    11,    12,    13,    14,   192,   164,  -178,
     242,   327,   401,   312,   127,  -178,   126,   354,   240,   116,
     151,   364,   365,   408,   205,   368,   306,   206,   159,   340,
     242,   306,   174,   319,   252,   371,   372,   175,   128,   256,
     158,   181,   259,   158,   227,   184,   261,  -197,  -197,   242,
     199,   158,   346,   190,   191,   158,  -197,   306,   158,   195,
     386,   224,   194,   373,   374,   117,   280,   119,    90,    91,
     201,   306,   158,   394,   395,   158,    92,    93,   387,   230,
     235,   246,   308,   247,    94,   257,   311,    66,    67,    68,
      69,   242,   407,   317,   360,   248,   258,   297,   322,   409,
     298,    10,    11,    12,    13,    14,   262,   267,   152,   242,
     153,   116,   396,   270,   268,   388,   158,   190,   191,   277,
     242,    70,    71,   397,   242,   158,   338,   404,    46,   324,
     158,   242,   325,   284,   405,   348,   190,   191,   291,    46,
      46,   299,   279,   305,   355,   370,   318,    46,   313,   279,
     326,   190,   191,   356,   320,   154,   158,   323,   358,    72,
     399,   349,   362,   328,    73,    74,   158,   357,   158,   359,
     158,   363,     2,   369,   285,     3,   379,   385,   389,     4,
       5,     6,     7,   295,   378,   392,   341,   377,   158,     8,
     200,   310,     9,   339,   158,     0,     0,     0,   384,    66,
      67,    68,    69,     0,     0,     0,     0,    66,    67,    68,
      69,     0,     0,     0,     0,    10,    11,    12,    13,    14,
     168,    15,   169,   382,     0,   383,     0,     0,    16,    17,
      18,    19,    20,    70,    71,     0,    21,    22,     0,     0,
      23,    70,    71,     0,     0,   393,     0,     0,     0,     0,
      24,   398,    66,    67,    68,    69,     0,     0,     0,    66,
      67,    68,    69,    66,   202,    68,   203,   170,     0,     0,
       0,    72,     0,   176,     0,   177,    73,    74,     0,    72,
     231,     0,   232,     0,    73,    74,    70,    71,    66,    67,
      68,    69,     0,    70,    71,     0,     0,    70,    71,     0,
       0,     0,     0,   134,   135,   136,   137,   138,   139,   263,
       0,   264,  -200,  -200,  -200,  -200,  -200,  -200,     0,     0,
     178,     0,    70,    71,    72,     0,     0,     0,     0,    73,
      74,    72,     0,     0,     0,    72,    73,    74,     3,   141,
      73,    74,     4,     5,     6,     7,     0,     0,   129,   130,
     131,   132,     8,     0,     0,     9,     0,     0,   133,     0,
      72,     0,     0,     0,     0,    73,    74,     0,   134,   135,
     136,   137,   138,   139,     0,     0,   278,     0,    10,    11,
      12,    13,    14,     0,    15,     0,     0,     0,     0,     0,
       0,    16,    17,    18,    19,    20,     0,     0,   140,    21,
      22,     3,     0,    23,   141,     4,     5,     6,     7,     0,
       0,     0,     0,    24,     0,     8,     0,     0,     9,   167,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,    10,    11,    12,    13,    14,     0,    15,     0,     0,
       0,     0,     0,     0,    16,    17,    18,    19,    20,     0,
       0,     0,    21,    22,     0,     0,    23,     3,     0,     0,
     280,     4,     5,     6,     7,     0,    24,   129,   130,   131,
     132,     8,     0,     0,     9,     0,     0,   133,     0,     0,
       0,     0,     0,     0,     0,     0,     0,   134,   135,   136,
     137,   138,   139,     0,     0,     0,     0,    10,    11,    12,
      13,    14,     0,    15,     0,     0,   129,   130,   131,   132,
      16,    17,    18,    19,    20,     0,   133,   140,    21,    22,
       0,     0,    23,   141,   254,     0,   134,   135,   136,   137,
     138,   139,    24,     0,     0,     0,     0,     0,   221,     0,
       0,     0,     0,     0,     0,   269,   255,   129,   130,   131,
     132,     0,     0,     0,     0,     0,   140,   133,     0,     0,
       0,     0,   141,     0,     0,   254,     0,   134,   135,   136,
     137,   138,   139,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,   255,   129,   130,
     131,   132,     0,     0,     0,     0,     0,   140,   133,     0,
       0,     0,     0,   141,     0,     0,     0,     0,   134,   135,
     136,   137,   138,   139,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,   189,     0,   129,
     130,   131,   132,     0,     0,     0,     0,   287,   140,   133,
       0,     0,     0,     0,   141,     0,     0,     0,     0,   134,
     135,   136,   137,   138,   139,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,   129,   130,   131,   132,
       0,     0,     0,     0,   400,     0,   133,     0,     0,   140,
       0,     0,     0,     0,     0,   141,   134,   135,   136,   137,
     138,   139,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,   129,   130,   131,   132,     0,     0,     0,
       0,     0,     0,   133,     0,     0,   140,   129,   130,   131,
     132,     0,   141,   134,   135,   136,   137,   138,   139,     0,
       0,     0,     0,     0,     0,     0,     0,   134,   135,   136,
     137,   138,   139,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,   140,     0,     0,     0,     0,     0,   141,
       0,     0,     0,     0,     0,     0,     0,   140,     0,     0,
       0,     0,     0,   141
};

static const yytype_int16 yycheck[] =
{
       1,   146,     1,     4,     5,    15,   123,     3,     3,     3,
       4,     5,     6,   331,    61,    59,    60,    59,    60,    16,
      73,    74,    20,    40,     9,     3,     4,     5,     6,    60,
      24,    19,    26,    81,    40,    22,    22,    25,    22,    22,
      22,    22,     3,    37,    38,    22,    24,    22,    26,    47,
      24,    49,    22,    81,    71,    53,    66,    19,    22,    37,
      38,    59,    60,    22,    22,    71,   154,    15,    64,    65,
      22,    81,    81,    25,    48,    15,    24,    71,    40,    76,
      78,    75,   170,     3,    24,    86,    80,    81,    82,   407,
     178,   409,   237,    71,   239,    82,    82,    75,    82,    82,
      82,    82,    80,    81,    19,    82,   104,    82,    82,    71,
     108,    10,    82,   111,   115,    66,    47,   115,    82,     3,
      24,   122,   123,    82,    82,    40,   127,   125,   158,   127,
      81,   129,   130,   131,   132,   133,   134,   135,   136,   137,
     138,   139,   140,   141,    48,   192,    19,   194,    66,   193,
     148,   193,    25,     7,     8,   199,    71,   199,    19,   144,
     158,   146,   193,    81,   375,    81,   377,   165,   199,   100,
      66,    19,    19,   104,    41,   173,   223,   108,     3,    40,
     111,   228,   180,   108,   182,    81,    13,    14,    19,    81,
     115,   189,    40,    40,    25,   193,   197,   198,   197,   198,
      66,   199,    69,    70,    31,    32,    33,    34,    35,    36,
      71,    15,   242,    27,    28,    81,   246,   148,    81,   249,
      24,   152,     3,    71,    71,   272,    22,   158,   275,    25,
     104,     3,    15,   277,    61,   277,   234,   168,    73,    74,
      67,    24,   173,    69,    70,   176,   277,    82,    56,   180,
       3,   182,   237,   300,   239,   302,   254,   255,    73,    74,
     163,    81,    43,    44,    45,    46,    47,    82,   266,    19,
      22,   269,   389,    25,    24,    25,    81,   307,   152,   277,
       3,   328,   329,   400,   285,   332,   316,   285,     4,   287,
      22,   321,     6,    25,   168,   342,   343,    82,    48,   173,
     231,     6,   176,   234,   289,     3,   180,    73,    74,    22,
      81,   242,    25,    73,    74,   246,    82,   347,   249,    56,
     367,     3,    82,    69,    70,   369,    72,   369,    28,    29,
       4,   361,   263,   380,   381,   266,    36,    37,   369,    82,
       6,    19,   245,    72,    44,    25,   249,     3,     4,     5,
       6,    22,   399,   256,    25,    22,    48,   231,   261,   406,
     234,    43,    44,    45,    46,    47,    25,     6,    24,    22,
      26,   369,    25,    82,    50,   373,   307,    73,    74,    81,
      22,    37,    38,    25,    22,   316,    82,    25,   389,   263,
     321,    22,   266,    82,    25,   298,    73,    74,     3,   400,
     401,    25,   401,    72,   307,    82,    15,   408,    72,   408,
      25,    73,    74,   316,    72,    71,   347,    15,   321,    75,
      82,    15,   325,    19,    80,    81,   357,    24,   359,    24,
     361,    15,     0,    81,    19,     3,    24,    24,    19,     7,
       8,     9,    10,   230,   347,   377,   289,   345,   379,    17,
     125,   248,    20,   285,   385,    -1,    -1,    -1,   361,     3,
       4,     5,     6,    -1,    -1,    -1,    -1,     3,     4,     5,
       6,    -1,    -1,    -1,    -1,    43,    44,    45,    46,    47,
      24,    49,    26,   357,    -1,   359,    -1,    -1,    56,    57,
      58,    59,    60,    37,    38,    -1,    64,    65,    -1,    -1,
      68,    37,    38,    -1,    -1,   379,    -1,    -1,    -1,    -1,
      78,   385,     3,     4,     5,     6,    -1,    -1,    -1,     3,
       4,     5,     6,     3,     4,     5,     6,    71,    -1,    -1,
      -1,    75,    -1,    24,    -1,    26,    80,    81,    -1,    75,
      24,    -1,    26,    -1,    80,    81,    37,    38,     3,     4,
       5,     6,    -1,    37,    38,    -1,    -1,    37,    38,    -1,
      -1,    -1,    -1,    31,    32,    33,    34,    35,    36,    24,
      -1,    26,    31,    32,    33,    34,    35,    36,    -1,    -1,
      71,    -1,    37,    38,    75,    -1,    -1,    -1,    -1,    80,
      81,    75,    -1,    -1,    -1,    75,    80,    81,     3,    67,
      80,    81,     7,     8,     9,    10,    -1,    -1,    11,    12,
      13,    14,    17,    -1,    -1,    20,    -1,    -1,    21,    -1,
      75,    -1,    -1,    -1,    -1,    80,    81,    -1,    31,    32,
      33,    34,    35,    36,    -1,    -1,    41,    -1,    43,    44,
      45,    46,    47,    -1,    49,    -1,    -1,    -1,    -1,    -1,
      -1,    56,    57,    58,    59,    60,    -1,    -1,    61,    64,
      65,     3,    -1,    68,    67,     7,     8,     9,    10,    -1,
      -1,    -1,    -1,    78,    -1,    17,    -1,    -1,    20,    82,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    43,    44,    45,    46,    47,    -1,    49,    -1,    -1,
      -1,    -1,    -1,    -1,    56,    57,    58,    59,    60,    -1,
      -1,    -1,    64,    65,    -1,    -1,    68,     3,    -1,    -1,
      72,     7,     8,     9,    10,    -1,    78,    11,    12,    13,
      14,    17,    -1,    -1,    20,    -1,    -1,    21,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    31,    32,    33,
      34,    35,    36,    -1,    -1,    -1,    -1,    43,    44,    45,
      46,    47,    -1,    49,    -1,    -1,    11,    12,    13,    14,
      56,    57,    58,    59,    60,    -1,    21,    61,    64,    65,
      -1,    -1,    68,    67,    29,    -1,    31,    32,    33,    34,
      35,    36,    78,    -1,    -1,    -1,    -1,    -1,    82,    -1,
      -1,    -1,    -1,    -1,    -1,    50,    51,    11,    12,    13,
      14,    -1,    -1,    -1,    -1,    -1,    61,    21,    -1,    -1,
      -1,    -1,    67,    -1,    -1,    29,    -1,    31,    32,    33,
      34,    35,    36,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    51,    11,    12,
      13,    14,    -1,    -1,    -1,    -1,    -1,    61,    21,    -1,
      -1,    -1,    -1,    67,    -1,    -1,    -1,    -1,    31,    32,
      33,    34,    35,    36,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    50,    -1,    11,
      12,    13,    14,    -1,    -1,    -1,    -1,    19,    61,    21,
      -1,    -1,    -1,    -1,    67,    -1,    -1,    -1,    -1,    31,
      32,    33,    34,    35,    36,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    11,    12,    13,    14,
      -1,    -1,    -1,    -1,    19,    -1,    21,    -1,    -1,    61,
      -1,    -1,    -1,    -1,    -1,    67,    31,    32,    33,    34,
      35,    36,    -1,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    11,    12,    13,    14,    -1,    -1,    -1,
      -1,    -1,    -1,    21,    -1,    -1,    61,    11,    12,    13,
      14,    -1,    67,    31,    32,    33,    34,    35,    36,    -1,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    31,    32,    33,
      34,    35,    36,    -1,    -1,    -1,    -1,    -1,    -1,    -1,
      -1,    -1,    -1,    61,    -1,    -1,    -1,    -1,    -1,    67,
      -1,    -1,    -1,    -1,    -1,    -1,    -1,    61,    -1,    -1,
      -1,    -1,    -1,    67
};

/* YYSTOS[STATE-NUM] -- The (internal number of the) accessing
   symbol of state STATE-NUM.  */
static const yytype_uint8 yystos[] =
{
       0,    84,     0,     3,     7,     8,     9,    10,    17,    20,
      43,    44,    45,    46,    47,    49,    56,    57,    58,    59,
      60,    64,    65,    68,    78,    86,    87,    88,    89,    90,
      91,    92,    93,    94,    95,    96,    99,   104,   110,   112,
     113,   114,   121,   124,   133,   137,   140,    15,    66,    81,
       3,   140,   140,    81,     3,    81,     3,   137,    81,    81,
      81,    19,    40,    71,   102,   105,     3,     4,     5,     6,
      37,    38,    75,    80,    81,   138,   140,   141,   142,   147,
     149,   150,   154,   156,     3,     3,    81,    16,    76,    85,
      85,    85,    85,    85,    85,     3,    64,    65,     7,     8,
      24,    26,    71,   141,   142,   136,   141,   141,    15,    24,
       3,    15,    24,     3,    10,   100,   141,   149,   153,   154,
     153,   105,   108,   106,    56,    81,    81,    24,    48,    11,
      12,    13,    14,    21,    31,    32,    33,    34,    35,    36,
      61,    67,   141,    66,    81,    66,    81,   140,    15,    24,
       3,     3,    24,    26,    71,    97,    98,   141,   142,     4,
     144,   145,   146,    98,   141,    22,    82,    82,    24,    26,
      71,   101,   141,   142,     6,    82,    24,    26,    71,   141,
     142,     6,    15,    24,     3,   101,   140,   141,   151,    50,
      73,    74,    82,   152,    82,    56,    86,   139,   139,    81,
     136,     4,     4,     6,   101,   140,   141,   148,   141,   141,
     141,   141,   141,   141,   141,   141,   141,   141,   141,   141,
     141,    82,   143,   129,     3,   134,   135,   137,   130,   134,
      82,    24,    26,   141,   142,     6,    66,    81,    66,    81,
      98,   144,    22,    25,    97,   155,    19,    72,    22,    22,
     143,   141,    98,   144,    29,    51,    98,    25,    48,    98,
     144,    98,    25,    24,    26,   141,   142,     6,    50,    50,
      82,   141,    19,   105,   153,    19,   105,    81,    41,    86,
      72,   103,   153,    82,    82,    19,    25,    19,   105,    22,
      82,     3,   105,    82,    40,   102,   116,    98,    98,    25,
     131,   134,   132,   134,    25,    72,    97,    22,   143,    97,
     146,   143,    25,    72,   141,   141,    22,   143,    15,    25,
      72,    22,   143,    15,    98,    98,    25,   141,    19,   111,
     105,   105,    27,    28,   115,   153,   109,   107,    82,   148,
     141,   135,   125,   126,   119,   117,    25,    22,   143,    15,
     105,    82,   105,    82,    97,   143,   143,    24,   143,    24,
      25,    22,   143,    15,   105,   105,   115,    19,   105,    81,
      82,   105,   105,    69,    70,   122,   123,   122,   143,    24,
     127,   128,    98,    98,   143,    24,   105,   153,   141,    19,
      41,   123,   103,    98,   105,   105,    25,    25,    98,    82,
      19,   139,   120,   118,    25,    25,    19,   105,   139,   105,
     115,   115
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
#line 3045 "semantic.y"
    { if(use_indent) yyerror("Punto y coma innecesario en modo indentacion"); ;}
    break;

  case 5:

/* Line 1455 of yacc.c  */
#line 3046 "semantic.y"
    { if(!use_indent) yyerror("Se esperaba un punto y coma en modo bloque"); ;}
    break;

  case 20:

/* Line 1455 of yacc.c  */
#line 3064 "semantic.y"
    {
      // Crear el nodo para la llamada a la función de la biblioteca 
      register_math_library();
      (yyval.node) = create_node("LibraryCall", "Math", NULL, NULL);
      generate_ast_file((yyval.node));
     ;}
    break;

  case 21:

/* Line 1455 of yacc.c  */
#line 3071 "semantic.y"
    {  
      // Crear el nodo para la instrucción print
      // Primero, verificamos si $3 es una variable declarada
      symbol* s = find_variable((yyvsp[(3) - (4)].sval));
      printf("s en print: %p\n", (void*)s);
      char* val1 = get_var((yyvsp[(3) - (4)].sval)) ? get_var((yyvsp[(3) - (4)].sval)) : (yyvsp[(3) - (4)].sval);
      printf("Valor recibido para imprimir: %s\n", val1);
      //printf("Valor a imprimir: %s\n", s->value);
      if (s) { // SI es una variable
          // Comprobamos si la variable tiene una operación guardada
          printf("variable name: %s\n", s->name);
          if (s->operation_str != NULL) {
              
              (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", (yyvsp[(3) - (4)].sval), NULL, NULL), create_node("Operation", s->operation_str, NULL, create_node("variableName", s->name, NULL, NULL)));
          } else {
              // Si no, creamos el nodo simple
             int vals = is_array_access_with_variables(s->value);
             printf("tipo %d\n", vals);
              if(vals){
               (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", (yyvsp[(3) - (4)].sval), NULL, create_node("ParamType", "ArrayAccess", NULL, create_node("variableName", s->name, NULL, NULL))), NULL);
              }else{
                
               (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", (yyvsp[(3) - (4)].sval), NULL, create_node("ParamType",determine_type(get_var((yyvsp[(3) - (4)].sval))) , NULL, create_node("variableName", s->name, create_node("val",val1,NULL,NULL), NULL))), NULL);
              }
              
                                                                                                                                                    
             // printf("Tipo de la variable '%s' es '%s'\n", s->name, s->type);
         }
      } else { // NO es una variable (es un literal o una operación directa)
          if (valid == 1) {
              con_op = reconstruct_expression();
              (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("Operation", con_op, NULL, NULL));
              valid = 0;
          } else {
             // $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("ParamType", determine_type($3), NULL, NULL));
                (yyval.node) = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, create_node("ParamType", determine_type((yyvsp[(3) - (4)].sval)), NULL, NULL)), NULL);
                
          }
      }
      generate_ast_file((yyval.node));
     ;}
    break;

  case 22:

/* Line 1455 of yacc.c  */
#line 3113 "semantic.y"
    { // Post-incremento: x++
                              handle_increment_decrement((yyvsp[(1) - (2)].sval), "++");
                              (yyval.node) = create_node("PostIncrementStatement", (yyvsp[(1) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 23:

/* Line 1455 of yacc.c  */
#line 3117 "semantic.y"
    { // Post-decremento: x--
                              handle_increment_decrement((yyvsp[(1) - (2)].sval), "--");
                              (yyval.node) = create_node("PostDecrementStatement", (yyvsp[(1) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 24:

/* Line 1455 of yacc.c  */
#line 3121 "semantic.y"
    { // Pre-incremento: ++x
                              handle_increment_decrement((yyvsp[(2) - (2)].sval), "++");
                              (yyval.node) = create_node("PreIncrementStatement", (yyvsp[(2) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 25:

/* Line 1455 of yacc.c  */
#line 3125 "semantic.y"
    { // Pre-decremento: --x
                              handle_increment_decrement((yyvsp[(2) - (2)].sval), "--");
                              (yyval.node) = create_node("PreDecrementStatement", (yyvsp[(2) - (2)].sval), NULL, NULL); generate_ast_file((yyval.node));
                          ;}
    break;

  case 26:

/* Line 1455 of yacc.c  */
#line 3132 "semantic.y"
    { 
      declare_var((yyvsp[(2) - (2)].sval),"NULL","NULL",false,NULL,false);
      (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (2)].sval), create_node("Value","NULL", create_node("Type","NULL",NULL,NULL),NULL), NULL); generate_ast_file((yyval.node));  ;}
    break;

  case 27:

/* Line 1455 of yacc.c  */
#line 3135 "semantic.y"
    {
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
             declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,con_op,false);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file((yyval.node));
           valid = 0;
        }else if(valid==0){
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,NULL,false);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),NULL), NULL); generate_ast_file((yyval.node)); 
         }
       }
    
   ;}
    break;

  case 28:

/* Line 1455 of yacc.c  */
#line 3157 "semantic.y"
    {
    char buffer[4096];
    sprintf(buffer, "{%s}", (yyvsp[(5) - (6)].sval)); // Envuelve el contenido con llaves
    declare_var((yyvsp[(2) - (6)].sval), buffer, "Dict", false, NULL,false);
    (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
    generate_ast_file((yyval.node));
   ;}
    break;

  case 29:

/* Line 1455 of yacc.c  */
#line 3164 "semantic.y"
    {
             char* node_type = "VariableAsignement";
            if (is_current_func_param((yyvsp[(1) - (5)].sval))) {
                node_type = "ParameterAsignement";
            }
    if(get_var((yyvsp[(1) - (5)].sval))){
        char buffer[4096];
        sprintf(buffer, "{%s}", (yyvsp[(4) - (5)].sval)); // Envuelve el contenido con llaves
        reassign_var_with_type((yyvsp[(1) - (5)].sval), buffer, "Dict");
        (yyval.node) = create_node(node_type, (yyvsp[(1) - (5)].sval), create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
    } else {
        char error_msg[256];
        sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, (yyvsp[(1) - (5)].sval));
        yyerror(error_msg);
        exit(1);
    }
   ;}
    break;

  case 30:

/* Line 1455 of yacc.c  */
#line 3182 "semantic.y"
    {
     declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),"Range",false,NULL,false);
   (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type","Range",NULL,NULL),NULL), NULL); generate_ast_file((yyval.node));
   ;}
    break;

  case 31:

/* Line 1455 of yacc.c  */
#line 3186 "semantic.y"
    {
       printf("assign: %s\n",(yyvsp[(3) - (3)].sval));
        if (strcmp((yyvsp[(3) - (3)].sval), VOID_RESULT_MARKER) == 0) {
           char error_msg[256];
           sprintf(error_msg, "Line %d: Cannot assign result of a void function to variable '%s'", yylineno, (yyvsp[(1) - (3)].sval));
           yyerror(error_msg);
           exit(1);
       }else{
        if (find_variable((yyvsp[(1) - (3)].sval))) {
            char* node_type = "VariableAsignement";
                if (is_current_func_param((yyvsp[(1) - (3)].sval))) {
                node_type = "ParameterAsignement";
                }
             if (valid == 1) {
                
                 con_op = reconstruct_expression();
                 char * expr = determine_type((yyvsp[(3) - (3)].sval));
                 
                 reassign_var((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval), con_op);
                 (yyval.node) = create_node(node_type, (yyvsp[(1) - (3)].sval), create_node("Value", (yyvsp[(3) - (3)].sval), create_node("Type", expr, NULL, NULL), create_node("Operation", con_op, NULL, NULL)), NULL); 
                 generate_ast_file((yyval.node));
                 valid = 0;
             } else if (valid == 0) {
                 reassign_var((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval), NULL);
                 char * expr = determine_type((yyvsp[(3) - (3)].sval));
                 
                 (yyval.node) = create_node(node_type, (yyvsp[(1) - (3)].sval), create_node("Value", (yyvsp[(3) - (3)].sval), create_node("Type", expr, NULL, NULL), NULL), NULL); 
                 generate_ast_file((yyval.node));
             }
       }else{
         char error_msg[256];
         sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, (yyvsp[(1) - (3)].sval));
         yyerror(error_msg);
         exit(1);
       }
     }
   
   ;}
    break;

  case 32:

/* Line 1455 of yacc.c  */
#line 3225 "semantic.y"
    {
      char* explicit_type = (yyvsp[(1) - (2)].sval);
    // 2. Obtenemos el valor por defecto para ese tipo (ej. "0")
    char* default_value = get_default_value_for_type(explicit_type);
     declare_var((yyvsp[(2) - (2)].sval),default_value,(yyvsp[(1) - (2)].sval),true, NULL,false);
      (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (2)].sval), create_node("Value",default_value, create_node("Type",(yyvsp[(1) - (2)].sval),NULL,NULL),create_node("ExplicitType",(yyvsp[(1) - (2)].sval),NULL,NULL)), NULL); generate_ast_file((yyval.node));
   /*  if($2 == "Int"){
      $$ = create_node("VariableDeclaration", $2, create_node("Value","0", create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
     }else if($2 == "Float"){
      $$ = create_node("VariableDeclaration", $2, create_node("Value","0.0", create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
     }else  if($2 == "String"){
      $$ = create_node("VariableDeclaration", $2, create_node("Value","\"\"", create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
     }else if($2 == "Bool"){
      $$ = create_node("VariableDeclaration", $2, create_node("Value","False", create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
     }else{   
      $$ = create_node("VariableDeclaration", $2, create_node("Value","NULL", create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
     }*/
   ;}
    break;

  case 33:

/* Line 1455 of yacc.c  */
#line 3243 "semantic.y"
    {
     // Crear el nodo para una asignación
      char * expr = determine_type((yyvsp[(4) - (4)].sval));
      printf("types es: %s\n",(yyvsp[(4) - (4)].sval));
      if(strcmp((yyvsp[(1) - (4)].sval),expr) == 0){
        if(valid==1){
           con_op = reconstruct_expression(); 
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),(yyvsp[(1) - (4)].sval),true,con_op,false);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,create_node("ExplicitType",(yyvsp[(1) - (4)].sval),NULL,NULL)),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file((yyval.node));
           valid = 0;
        }else if(valid==0){
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),(yyvsp[(1) - (4)].sval),true,NULL,false);
          (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),create_node("ExplicitType",(yyvsp[(1) - (4)].sval),NULL,NULL)), NULL); generate_ast_file((yyval.node)); 
        }
       }else{
        char error_msg[512];
        sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(4) - (4)].sval), expr, (yyvsp[(2) - (4)].sval), (yyvsp[(1) - (4)].sval));
        yyerror(error_msg);
        exit(1);
    
       }
     ;}
    break;

  case 40:

/* Line 1455 of yacc.c  */
#line 3274 "semantic.y"
    {
        declare_var((yyvsp[(2) - (2)].sval),"NULL","NULL",true,NULL,true);
        (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (2)].sval), create_node("Value",(yyvsp[(2) - (2)].sval), create_node("Type","NULL",NULL,NULL),NULL), NULL); generate_ast_file((yyval.node)); 
    ;}
    break;

  case 41:

/* Line 1455 of yacc.c  */
#line 3278 "semantic.y"
    {
      char * expr = determine_type((yyvsp[(4) - (4)].sval));
      //declare_var($2,$4,expr,true,NULL,true);
    
       if(valid==1){
             con_op = reconstruct_expression();
             declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,con_op,true);
          (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file((yyval.node));
           valid = 0;
        }else if(valid==0){
            declare_var((yyvsp[(2) - (4)].sval),(yyvsp[(4) - (4)].sval),expr,false,NULL,true);
          (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value",(yyvsp[(4) - (4)].sval), create_node("Type",expr,NULL,NULL),NULL), NULL); generate_ast_file((yyval.node));  
        }
    ;}
    break;

  case 42:

/* Line 1455 of yacc.c  */
#line 3292 "semantic.y"
    {
        char* explicit_type = (yyvsp[(2) - (3)].sval);
    // 2. Obtenemos el valor por defecto para ese tipo (ej. "0")
      char* default_value = get_default_value_for_type(explicit_type);
      declare_var((yyvsp[(3) - (3)].sval),"NULL",(yyvsp[(2) - (3)].sval),true, NULL,true);
      (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (3)].sval), create_node("Value","NULL", create_node("Type",(yyvsp[(2) - (3)].sval),NULL,NULL),create_node("ExplicitType",(yyvsp[(2) - (3)].sval),NULL,NULL)), NULL); generate_ast_file((yyval.node));

    ;}
    break;

  case 43:

/* Line 1455 of yacc.c  */
#line 3300 "semantic.y"
    {
      // Crear el nodo para una asignación
      char * expr = determine_type((yyvsp[(5) - (5)].sval));
      //printf("types es: %s\n",$4);
      if(strcmp((yyvsp[(2) - (5)].sval),expr) == 0){
        if(valid==1){
           con_op = reconstruct_expression(); 
            declare_var((yyvsp[(3) - (5)].sval),(yyvsp[(5) - (5)].sval),(yyvsp[(2) - (5)].sval),true,con_op,true);
          (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (5)].sval), create_node("Value",(yyvsp[(5) - (5)].sval), create_node("Type",expr,NULL,create_node("ExplicitType",(yyvsp[(2) - (5)].sval),NULL,NULL)),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file((yyval.node));
           valid = 0;
        }else if(valid==0){
            declare_var((yyvsp[(3) - (5)].sval),(yyvsp[(5) - (5)].sval),(yyvsp[(2) - (5)].sval),true,NULL,true);
          (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (5)].sval), create_node("Value",(yyvsp[(5) - (5)].sval), create_node("Type",expr,NULL,NULL),create_node("ExplicitType",(yyvsp[(2) - (5)].sval),NULL,NULL)), NULL); generate_ast_file((yyval.node)); 
        }
       }
     ;}
    break;

  case 44:

/* Line 1455 of yacc.c  */
#line 3316 "semantic.y"
    {
     char buffer[4096];
     sprintf(buffer, "{%s}", (yyvsp[(5) - (6)].sval)); // Envuelve el contenido con llaves
     declare_var((yyvsp[(2) - (6)].sval), buffer, "Dict", false, NULL,true);
     (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
     generate_ast_file((yyval.node));
    ;}
    break;

  case 45:

/* Line 1455 of yacc.c  */
#line 3325 "semantic.y"
    {
        char buffer[2048];
        sprintf(buffer, "(%s)", (yyvsp[(5) - (6)].sval));
        declare_var((yyvsp[(2) - (6)].sval), buffer, "Tuple", false,NULL,false);
        
        (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
   ;}
    break;

  case 46:

/* Line 1455 of yacc.c  */
#line 3334 "semantic.y"
    {
        char buffer[2048];
        sprintf(buffer, "(%s,)", (yyvsp[(5) - (7)].sval));
        declare_var((yyvsp[(2) - (7)].sval), buffer, "Tuple", false,NULL,false);
        (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (7)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 47:

/* Line 1455 of yacc.c  */
#line 3343 "semantic.y"
    {
         char buffer[2048];
         char * expr = determineArrayType((yyvsp[(5) - (6)].sval));
          sprintf(buffer, "(%s)", (yyvsp[(5) - (6)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(5) - (6)].sval)));
           if(strcmp(determineArrayType((yyvsp[(5) - (6)].sval)),(yyvsp[(1) - (6)].sval))== 0){
            declare_var((yyvsp[(2) - (6)].sval),buffer,"Tuple",true,NULL,false);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",(yyvsp[(1) - (6)].sval),NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor  de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, expr, (yyvsp[(2) - (6)].sval), (yyvsp[(1) - (6)].sval));
             yyerror(error_msg);
             exit(1);
            }
   ;}
    break;

  case 48:

/* Line 1455 of yacc.c  */
#line 3359 "semantic.y"
    {
        char buffer[2048];
         char * expr = determineArrayType((yyvsp[(5) - (7)].sval));
          sprintf(buffer, "(%s,)", (yyvsp[(5) - (7)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(5) - (7)].sval)));
           if(strcmp(determineArrayType((yyvsp[(5) - (7)].sval)),(yyvsp[(1) - (7)].sval))== 0){
            declare_var((yyvsp[(2) - (7)].sval),buffer,"Tuple",true,NULL,false);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (7)].sval), create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",(yyvsp[(1) - (7)].sval),NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(5) - (7)].sval), expr, (yyvsp[(2) - (7)].sval), (yyvsp[(1) - (7)].sval));
             yyerror(error_msg);
             exit(1);
            }
        
   ;}
    break;

  case 49:

/* Line 1455 of yacc.c  */
#line 3376 "semantic.y"
    {
         char* node_type = "VariableAsignement";
                if (is_current_func_param((yyvsp[(1) - (5)].sval))) {
                node_type = "ParameterAsignement";
                }
        char buffer[2048];
        sprintf(buffer, "(%s)", (yyvsp[(4) - (5)].sval));
       reassign_var((yyvsp[(1) - (5)].sval), buffer,NULL);
        (yyval.node) = create_node(node_type, (yyvsp[(1) - (5)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 50:

/* Line 1455 of yacc.c  */
#line 3389 "semantic.y"
    {
        char* node_type = "VariableAsignement";
            if (is_current_func_param((yyvsp[(1) - (6)].sval))) {
                node_type = "ParameterAsignement";
            }
        char buffer[2048];
        sprintf(buffer, "(%s,)", (yyvsp[(4) - (6)].sval));
       reassign_var((yyvsp[(1) - (6)].sval), buffer,NULL);
        (yyval.node) = create_node(node_type, (yyvsp[(1) - (6)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 51:

/* Line 1455 of yacc.c  */
#line 3403 "semantic.y"
    {
        char buffer[2048];
        sprintf(buffer, "(%s)", (yyvsp[(5) - (6)].sval));
        declare_var((yyvsp[(2) - (6)].sval), buffer, "Tuple", false,NULL,true);
        
        (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
   ;}
    break;

  case 52:

/* Line 1455 of yacc.c  */
#line 3412 "semantic.y"
    {
        char buffer[2048];
        sprintf(buffer, "(%s,)", (yyvsp[(5) - (7)].sval));
        declare_var((yyvsp[(2) - (7)].sval), buffer, "Tuple", false,NULL,true);
        (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (7)].sval), create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file((yyval.node));
        longitud = 1;
        
   ;}
    break;

  case 53:

/* Line 1455 of yacc.c  */
#line 3421 "semantic.y"
    {
         char buffer[2048];
         char * expr = determineArrayType((yyvsp[(6) - (7)].sval));
          sprintf(buffer, "(%s)", (yyvsp[(6) - (7)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(6) - (7)].sval)));
           if(strcmp(determineArrayType((yyvsp[(6) - (7)].sval)),(yyvsp[(2) - (7)].sval))== 0){
            declare_var((yyvsp[(3) - (7)].sval),buffer,"Tuple",true,NULL,true);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(3) - (7)].sval), create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",(yyvsp[(2) - (7)].sval),NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor  de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, expr, (yyvsp[(3) - (7)].sval), (yyvsp[(2) - (7)].sval));
             yyerror(error_msg);
             exit(1);
            }
   ;}
    break;

  case 54:

/* Line 1455 of yacc.c  */
#line 3437 "semantic.y"
    {
        char buffer[2048];
         char * expr = determineArrayType((yyvsp[(6) - (8)].sval));
          sprintf(buffer, "(%s,)", (yyvsp[(6) - (8)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(6) - (8)].sval)));
           if(strcmp(determineArrayType((yyvsp[(6) - (8)].sval)),(yyvsp[(2) - (8)].sval))== 0){
            declare_var((yyvsp[(3) - (8)].sval),buffer,"Tuple",true,NULL,true);
            (yyval.node) = create_node("VariableDeclaration",(yyvsp[(3) - (8)].sval), create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",(yyvsp[(2) - (8)].sval),NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(6) - (8)].sval), expr, (yyvsp[(3) - (8)].sval), (yyvsp[(2) - (8)].sval));
             yyerror(error_msg);
             exit(1);
            }
        
    ;}
    break;

  case 55:

/* Line 1455 of yacc.c  */
#line 3456 "semantic.y"
    {
          char buffer[2048];
           sprintf(buffer, "[%s]", (yyvsp[(5) - (6)].sval));
           declare_var((yyvsp[(2) - (6)].sval),buffer,"Array",false,NULL,false);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 1;
           printf("%s\n",buffer);
          ;}
    break;

  case 56:

/* Line 1455 of yacc.c  */
#line 3464 "semantic.y"
    {
            char buffer[2048];
          sprintf(buffer, "[%s]", (yyvsp[(8) - (9)].sval));
            declare_var((yyvsp[(2) - (9)].sval),buffer,"Array",false,NULL,false);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (9)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("Limit",to_string((yyvsp[(4) - (9)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
         ;}
    break;

  case 57:

/* Line 1455 of yacc.c  */
#line 3471 "semantic.y"
    {
          // if(strcmp($2,$2)== 0){
           declare_var((yyvsp[(2) - (4)].sval),NULL,"Array",false,NULL,false);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value","[]", create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           //}
         ;}
    break;

  case 58:

/* Line 1455 of yacc.c  */
#line 3478 "semantic.y"
    {
           //if(strcmp($1,$1)== 0){  
           declare_var((yyvsp[(2) - (5)].sval),NULL,"Array",false,NULL,false);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (5)].sval), create_node("Value","[]", create_node("Type","Array",NULL,create_node("Limit",to_string((yyvsp[(4) - (5)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
        //   }
         ;}
    break;

  case 59:

/* Line 1455 of yacc.c  */
#line 3485 "semantic.y"
    {
            char buffer[2048];
          sprintf(buffer, "[%s]", (yyvsp[(5) - (6)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(5) - (6)].sval)));
           char* expr = determineArrayType((yyvsp[(5) - (6)].sval));
           if(strcmp(expr,(yyvsp[(1) - (6)].sval))== 0){
            declare_var((yyvsp[(2) - (6)].sval),buffer,"Array",true,NULL,false);
            (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("ExplicitType",(yyvsp[(1) - (6)].sval),NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(5) - (6)].sval), expr, (yyvsp[(2) - (6)].sval), (yyvsp[(1) - (6)].sval));
             yyerror(error_msg);
             exit(1);
            }
         ;}
    break;

  case 60:

/* Line 1455 of yacc.c  */
#line 3501 "semantic.y"
    {
           if(strcmp(determineArrayType((yyvsp[(8) - (9)].sval)),(yyvsp[(1) - (9)].sval))== 0){  
            char buffer[2048];
           sprintf(buffer, "[%s]", (yyvsp[(8) - (9)].sval));
           declare_var((yyvsp[(2) - (9)].sval),buffer,"Array",true,NULL,false);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (9)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",create_node("ExplicitType",(yyvsp[(1) - (9)].sval),NULL,NULL),create_node("Limit",to_string((yyvsp[(4) - (9)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 1;
           }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(8) - (9)].sval), determineArrayType((yyvsp[(8) - (9)].sval)), (yyvsp[(2) - (9)].sval), (yyvsp[(1) - (9)].sval));
             yyerror(error_msg);
             exit(1);
           }
         ;}
    break;

  case 61:

/* Line 1455 of yacc.c  */
#line 3515 "semantic.y"
    {
           if(strcmp((yyvsp[(1) - (5)].sval),(yyvsp[(1) - (5)].sval))== 0){  
           declare_var((yyvsp[(2) - (5)].sval),NULL,"Array",true,NULL,false);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (5)].sval), create_node("Value","[]", create_node("Type","Array",create_node("ExplicitType",(yyvsp[(1) - (5)].sval),NULL,NULL),create_node("Limit",to_string((yyvsp[(4) - (5)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           }
         ;}
    break;

  case 62:

/* Line 1455 of yacc.c  */
#line 3522 "semantic.y"
    {
           if(strcmp((yyvsp[(1) - (4)].sval),(yyvsp[(1) - (4)].sval))== 0){
           declare_var((yyvsp[(2) - (4)].sval),NULL,"Array",true,NULL,false);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value","[]", create_node("Type","Array",NULL,create_node("ExplicitType",(yyvsp[(1) - (4)].sval),NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           }
         ;}
    break;

  case 63:

/* Line 1455 of yacc.c  */
#line 3530 "semantic.y"
    {
          char buffer[2048];
           sprintf(buffer, "[%s]", (yyvsp[(5) - (6)].sval));
           declare_var((yyvsp[(2) - (6)].sval),buffer,"Array",false,NULL,true);
           (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (6)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 1;
           printf("%s\n",buffer);
          ;}
    break;

  case 64:

/* Line 1455 of yacc.c  */
#line 3538 "semantic.y"
    {
            char buffer[2048];
          sprintf(buffer, "[%s]", (yyvsp[(8) - (9)].sval));
            declare_var((yyvsp[(2) - (9)].sval),buffer,"Array",false,NULL,true);
            (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(2) - (9)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("Limit",to_string((yyvsp[(4) - (9)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
         ;}
    break;

  case 65:

/* Line 1455 of yacc.c  */
#line 3545 "semantic.y"
    {
          // if(strcmp($2,$2)== 0){
           declare_var((yyvsp[(2) - (4)].sval),NULL,"Array",false,NULL,true);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (4)].sval), create_node("Value","[]", create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           //}
         ;}
    break;

  case 66:

/* Line 1455 of yacc.c  */
#line 3552 "semantic.y"
    {
         //  if(strcmp($1,$1)== 0){  
           declare_var((yyvsp[(2) - (5)].sval),NULL,"Array",false,NULL,true);
           (yyval.node) = create_node("VariableDeclaration", (yyvsp[(2) - (5)].sval), create_node("Value","[]", create_node("Type","Array",NULL,create_node("Limit",to_string((yyvsp[(4) - (5)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
          // }
         ;}
    break;

  case 67:

/* Line 1455 of yacc.c  */
#line 3560 "semantic.y"
    {
            char buffer[2048];
          sprintf(buffer, "[%s]", (yyvsp[(6) - (7)].sval));
           printf("types es: %s\n",determineArrayType((yyvsp[(6) - (7)].sval)));
           if(strcmp(determineArrayType((yyvsp[(6) - (7)].sval)),(yyvsp[(2) - (7)].sval))== 0){
            declare_var((yyvsp[(3) - (7)].sval),buffer,"Array",true,NULL,true);
            (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (7)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("ExplicitType",(yyvsp[(2) - (7)].sval),NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
            longitud = 1;
            }else{
                char error_msg[512];
                sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(6) - (7)].sval), determineArrayType((yyvsp[(6) - (7)].sval)), (yyvsp[(3) - (7)].sval), (yyvsp[(2) - (7)].sval));
                yyerror(error_msg);
                exit(1);
            }
         ;}
    break;

  case 68:

/* Line 1455 of yacc.c  */
#line 3575 "semantic.y"
    {
           if(strcmp(determineArrayType((yyvsp[(9) - (10)].sval)),(yyvsp[(2) - (10)].sval))== 0){  
            char buffer[2048];
           sprintf(buffer, "[%s]", (yyvsp[(9) - (10)].sval));
           declare_var((yyvsp[(3) - (10)].sval),buffer,"Array",true,NULL,true);
           (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (10)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",create_node("ExplicitType",(yyvsp[(2) - (10)].sval),NULL,NULL),create_node("Limit",to_string((yyvsp[(5) - (10)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 1;
           }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, (yyvsp[(9) - (10)].sval), determineArrayType((yyvsp[(9) - (10)].sval)), (yyvsp[(3) - (10)].sval), (yyvsp[(2) - (10)].sval));
             yyerror(error_msg);
             exit(1);
           }
         ;}
    break;

  case 69:

/* Line 1455 of yacc.c  */
#line 3589 "semantic.y"
    {
           if(strcmp((yyvsp[(2) - (6)].sval),(yyvsp[(2) - (6)].sval))== 0){  
           declare_var((yyvsp[(3) - (6)].sval),NULL,"Array",true,NULL,true);
           (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (6)].sval), create_node("Value","[]", create_node("Type","Array",create_node("ExplicitType",(yyvsp[(2) - (6)].sval),NULL,NULL),create_node("Limit",to_string((yyvsp[(5) - (6)].ival)),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           }
         ;}
    break;

  case 70:

/* Line 1455 of yacc.c  */
#line 3596 "semantic.y"
    {
           if(strcmp((yyvsp[(2) - (5)].sval),(yyvsp[(2) - (5)].sval))== 0){
           declare_var((yyvsp[(3) - (5)].sval),NULL,"Array",true,NULL,true);
           (yyval.node) = create_node("ConstantDeclaration", (yyvsp[(3) - (5)].sval), create_node("Value","[]", create_node("Type","Array",NULL,create_node("ExplicitType",(yyvsp[(2) - (5)].sval),NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
           longitud = 0;
           }
         ;}
    break;

  case 71:

/* Line 1455 of yacc.c  */
#line 3604 "semantic.y"
    {
             //char * expr = determine_type($3);
             char* node_type = "VariableAsignement";
            if (is_current_func_param((yyvsp[(1) - (3)].sval))) {
                node_type = "ParameterAsignement";
            }
             (yyval.node) = create_node(node_type, (yyvsp[(1) - (3)].sval), create_node("Value","[]", create_node("Type","Array",NULL ,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file((yyval.node));
             longitud = 0;
              reassign_var_with_type((yyvsp[(1) - (3)].sval), "[]", "Array");
            ;}
    break;

  case 72:

/* Line 1455 of yacc.c  */
#line 3614 "semantic.y"
    {
             //if(strcmp(determineArrayType($4),$1)== 0){
             char* node_type = "VariableAsignement";
             if (is_current_func_param((yyvsp[(1) - (5)].sval))) {
                node_type = "ParameterAsignement";
             }
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
                (yyval.node) = create_node(node_type, (yyvsp[(1) - (5)].sval), create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file((yyval.node));
                longitud = 1; 
             // } 
            ;}
    break;

  case 73:

/* Line 1455 of yacc.c  */
#line 3637 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 74:

/* Line 1455 of yacc.c  */
#line 3639 "semantic.y"
    {
             // Un elemento ahora puede ser un diccionario literal
             char buffer[4096];
             sprintf(buffer, "{%s}", (yyvsp[(2) - (3)].sval));
             (yyval.sval) = strdup(buffer);
           ;}
    break;

  case 75:

/* Line 1455 of yacc.c  */
#line 3645 "semantic.y"
    {
             // Un elemento también puede ser una tupla literal
             char buffer[2048];
             sprintf(buffer, "(%s)", (yyvsp[(2) - (3)].sval));
             (yyval.sval) = strdup(buffer);
         ;}
    break;

  case 76:

/* Line 1455 of yacc.c  */
#line 3651 "semantic.y"
    {
             // Un elemento también puede ser una tupla literal
             char buffer[2048];
             sprintf(buffer, "(%s,)", (yyvsp[(2) - (4)].sval));
             (yyval.sval) = strdup(buffer);
         ;}
    break;

  case 77:

/* Line 1455 of yacc.c  */
#line 3657 "semantic.y"
    {
          char buffer[4096];
          sprintf(buffer, "[%s]", (yyvsp[(2) - (3)].sval));
          (yyval.sval) = strdup(buffer);
         ;}
    break;

  case 78:

/* Line 1455 of yacc.c  */
#line 3664 "semantic.y"
    {
         (yyval.sval) = strdup("[]");
        ;}
    break;

  case 79:

/* Line 1455 of yacc.c  */
#line 3668 "semantic.y"
    {
                    longitud = 1;
                    (yyval.sval) = (yyvsp[(1) - (1)].sval);
                ;}
    break;

  case 80:

/* Line 1455 of yacc.c  */
#line 3672 "semantic.y"
    {
                    // Tu lógica de concatenación para formar el string de la lista
                    char* tempList = concat_strings((yyvsp[(1) - (3)].sval), ", ");
                    (yyval.sval) = concat_strings(tempList, (yyvsp[(3) - (3)].sval));
                    free(tempList);
                    longitud++;
                ;}
    break;

  case 81:

/* Line 1455 of yacc.c  */
#line 3680 "semantic.y"
    { 
        (yyval.node) = create_node("CallExpression", "read", create_node("Arguments", (yyvsp[(3) - (4)].sval), NULL, create_node("Type",determine_type(get_var((yyvsp[(3) - (4)].sval))),NULL,NULL)), NULL); generate_ast_file((yyval.node)); 
         
    ;}
    break;

  case 82:

/* Line 1455 of yacc.c  */
#line 3684 "semantic.y"
    {
    //$$ = create_node("CallExpression", "ReadTypeInt", read_node, create_node("TypeConversion", "Int", NULL, NULL));generate_ast_file($$);
      (yyval.node) = create_node("CallExpression", "read", create_node("Arguments", (yyvsp[(3) - (5)].sval), NULL, create_node("ParamType", "Int", NULL, create_node("Type",determine_type(get_var((yyvsp[(3) - (5)].sval))),NULL,NULL))), NULL); generate_ast_file((yyval.node)); 
    ;}
    break;

  case 83:

/* Line 1455 of yacc.c  */
#line 3689 "semantic.y"
    {  
     //declare_var($2,"0","int");
     (yyval.sval) = (yyvsp[(2) - (3)].sval);
    ;}
    break;

  case 84:

/* Line 1455 of yacc.c  */
#line 3694 "semantic.y"
    { 
          char buffer[40]; 
          sprintf(buffer, "%s..%s", (yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval)); 
         (yyval.sval) = strdup(buffer);   
     ;}
    break;

  case 85:

/* Line 1455 of yacc.c  */
#line 3699 "semantic.y"
    {
           char buffer[40];
           sprintf(buffer, "%s..<%s", (yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval));
           (yyval.sval) = strdup(buffer);
     ;}
    break;

  case 86:

/* Line 1455 of yacc.c  */
#line 3705 "semantic.y"
    { (yyval.node) = create_node("BlockStart", NULL, NULL, NULL); blockcode++; ;}
    break;

  case 87:

/* Line 1455 of yacc.c  */
#line 3708 "semantic.y"
    { (yyval.node) = create_node("BlockEnd", NULL, NULL, NULL); blockcode--; ;}
    break;

  case 88:

/* Line 1455 of yacc.c  */
#line 3710 "semantic.y"
    { (yyval.node) = create_node("CallExpression", "Break", NULL, NULL); ;}
    break;

  case 89:

/* Line 1455 of yacc.c  */
#line 3711 "semantic.y"
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
                     } else if (strcmp(func->return_type, "inferred") != 0) {
                         // Solo validar tipos para funciones con tipo explícito
                         // y solo cuando el return es un LITERAL (no variable/expresión)
                         
                         // Función para detectar si es un literal puro (sin variables)
                         int is_pure_literal = is_pure_literal_expression((yyvsp[(2) - (2)].sval));
                         
                         if (is_pure_literal) {
                             // Si es literal, podemos validar el tipo
                             char* actual_type = determine_type((yyvsp[(2) - (2)].sval));
                             
                             if (strcmp(func->return_type, actual_type) != 0) {
                                 char error_msg[512];
                                 sprintf(error_msg, "Line %d: Error: Type mismatch in function '%s'. Expected return type '%s' but got '%s'.\n", 
                                         yylineno, func->name, func->return_type, actual_type);
                                 yyerror(error_msg);
                                 exit(1);
                             }
                         }
                         // Si contiene variables, NO validamos - se resuelve en runtime
                     }
                     
                     // Para funciones "inferred", inferimos del primer return (si es literal)
                     if (strcmp(func->return_type, "inferred") == 0) {
                         int is_pure_literal = is_pure_literal_expression((yyvsp[(2) - (2)].sval));
                         if (is_pure_literal) {
                             char* actual_type = determine_type((yyvsp[(2) - (2)].sval));
                             free(func->return_type);
                             func->return_type = strdup(actual_type);
                         } else {
                             // Si no es literal, ponemos un tipo por defecto y dejamos que se resuelva en runtime
                             free(func->return_type);
                             func->return_type = strdup("dynamic");
                         }
                     }

                     // Guardamos el valor de retorno (siempre)
                     if (func->return_value) free(func->return_value);
                     func->return_value = strdup((yyvsp[(2) - (2)].sval));
                 }
             } else {
                 yyerror("Error: 'return' used outside of a function."); 
                 exit(1);
             }

             // Creamos el nodo del AST para la sentencia 'return'.
             (yyval.node) = create_node("CallExpression", "Return", create_node("value", (yyvsp[(2) - (2)].sval), NULL, NULL), NULL);
            ;}
    break;

  case 90:

/* Line 1455 of yacc.c  */
#line 3775 "semantic.y"
    { enter_scope(); ;}
    break;

  case 91:

/* Line 1455 of yacc.c  */
#line 3775 "semantic.y"
    { exit_scope(); ;}
    break;

  case 92:

/* Line 1455 of yacc.c  */
#line 3775 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 93:

/* Line 1455 of yacc.c  */
#line 3776 "semantic.y"
    { enter_scope(); ;}
    break;

  case 94:

/* Line 1455 of yacc.c  */
#line 3776 "semantic.y"
    { exit_scope(); ;}
    break;

  case 95:

/* Line 1455 of yacc.c  */
#line 3776 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 96:

/* Line 1455 of yacc.c  */
#line 3778 "semantic.y"
    { 
     enter_scope();
     declare_var((yyvsp[(3) - (5)].sval),(yyvsp[(4) - (5)].sval),"int",false, NULL,false); 
      printf("for condition: %s\n",(yyvsp[(4) - (5)].sval));
    ;}
    break;

  case 97:

/* Line 1455 of yacc.c  */
#line 3782 "semantic.y"
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

  case 98:

/* Line 1455 of yacc.c  */
#line 3800 "semantic.y"
    {
         declare_var((yyvsp[(3) - (7)].sval),(yyvsp[(4) - (7)].sval),"int",false,NULL,false); 
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

  case 99:

/* Line 1455 of yacc.c  */
#line 3817 "semantic.y"
    {
          if(!use_indent){
            char *comparison_str = strdup((yyvsp[(3) - (5)].sval)); // Clonar la cadena concatenada
                char *result = strchr(comparison_str, ','); // Buscar la coma
                 if (result != NULL) {
                 *result = '\0'; // Separar comparación
                  result++;       // Apuntar al valor lógico
                }
           (yyval.node) = create_node("WhileLoop",result,create_node("ConditionIs",comparison_str,NULL,NULL),(yyvsp[(5) - (5)].node)); generate_ast_file((yyval.node));
          }
          ;}
    break;

  case 100:

/* Line 1455 of yacc.c  */
#line 3829 "semantic.y"
    {
            printf("ident\n");
             (yyval.node) = create_node("WhileLoop",comparison,create_node("ConditionIs",(yyvsp[(3) - (6)].sval),NULL,NULL),(yyvsp[(6) - (6)].node)); generate_ast_file((yyval.node));  
            
          ;}
    break;

  case 101:

/* Line 1455 of yacc.c  */
#line 3835 "semantic.y"
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

  case 102:

/* Line 1455 of yacc.c  */
#line 3847 "semantic.y"
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

  case 103:

/* Line 1455 of yacc.c  */
#line 3861 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (5)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("if_Condition", comparison_str, NULL, (yyvsp[(5) - (5)].node));
        generate_ast_file((yyval.node));
        free(comparison_str);
    ;}
    break;

  case 104:

/* Line 1455 of yacc.c  */
#line 3872 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (6)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("if_Condition", comparison_str, NULL, (yyvsp[(6) - (6)].node));
        generate_ast_file((yyval.node));
        free(comparison_str);
    ;}
    break;

  case 105:

/* Line 1455 of yacc.c  */
#line 3883 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (6)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("if_Condition", comparison_str, (yyvsp[(5) - (6)].node), (yyvsp[(6) - (6)].node));
        generate_ast_file((yyval.node));
        free(comparison_str);
    ;}
    break;

  case 106:

/* Line 1455 of yacc.c  */
#line 3894 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (7)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("if_Condition", comparison_str, (yyvsp[(6) - (7)].node), (yyvsp[(7) - (7)].node));
        generate_ast_file((yyval.node));
        free(comparison_str);
    ;}
    break;

  case 107:

/* Line 1455 of yacc.c  */
#line 3909 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (5)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("ElseIf", comparison_str, (yyvsp[(5) - (5)].node), NULL);
    ;}
    break;

  case 108:

/* Line 1455 of yacc.c  */
#line 3918 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (6)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("ElseIf", comparison_str, (yyvsp[(6) - (6)].node), NULL);
    ;}
    break;

  case 109:

/* Line 1455 of yacc.c  */
#line 3927 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (6)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("ElseIf", comparison_str, (yyvsp[(5) - (6)].node), (yyvsp[(6) - (6)].node));
    ;}
    break;

  case 110:

/* Line 1455 of yacc.c  */
#line 3936 "semantic.y"
    {
        char *comparison_str = strdup((yyvsp[(3) - (7)].sval));
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        (yyval.node) = create_node("ElseIf", comparison_str, (yyvsp[(6) - (7)].node), (yyvsp[(7) - (7)].node));
    ;}
    break;

  case 111:

/* Line 1455 of yacc.c  */
#line 3945 "semantic.y"
    {
        (yyval.node) = create_node("Else", NULL, (yyvsp[(2) - (2)].node), NULL);
    ;}
    break;

  case 112:

/* Line 1455 of yacc.c  */
#line 3948 "semantic.y"
    {
        (yyval.node) = create_node("Else", NULL, (yyvsp[(3) - (3)].node), NULL);
    ;}
    break;

  case 113:

/* Line 1455 of yacc.c  */
#line 3952 "semantic.y"
    { enter_scope(); ;}
    break;

  case 114:

/* Line 1455 of yacc.c  */
#line 3952 "semantic.y"
    { exit_scope(); ;}
    break;

  case 115:

/* Line 1455 of yacc.c  */
#line 3952 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 116:

/* Line 1455 of yacc.c  */
#line 3953 "semantic.y"
    { enter_scope(); ;}
    break;

  case 117:

/* Line 1455 of yacc.c  */
#line 3953 "semantic.y"
    { exit_scope(); ;}
    break;

  case 118:

/* Line 1455 of yacc.c  */
#line 3953 "semantic.y"
    { (yyval.node) = create_node("Block", "BlockStart", (yyvsp[(3) - (5)].node), create_node("Block", "BlockEnd", NULL, NULL));;}
    break;

  case 119:

/* Line 1455 of yacc.c  */
#line 3955 "semantic.y"
    {
             // $3 es la expresión a evaluar (ej. 'dia')
             //  $6 es la lista de todos los nodos de los casos
            (yyval.node) = create_node("SwitchStatement", (yyvsp[(3) - (5)].sval), (yyvsp[(5) - (5)].node), NULL);
            generate_ast_file((yyval.node));
            ;}
    break;

  case 120:

/* Line 1455 of yacc.c  */
#line 3964 "semantic.y"
    { (yyval.node) = (yyvsp[(1) - (1)].node); ;}
    break;

  case 121:

/* Line 1455 of yacc.c  */
#line 3965 "semantic.y"
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

  case 122:

/* Line 1455 of yacc.c  */
#line 3982 "semantic.y"
    {
        // $2 es el valor del caso (ej. '1')
        // $5 es el bloque de sentencias para ese caso
        (yyval.node) = create_node("Case", (yyvsp[(2) - (4)].sval), (yyvsp[(4) - (4)].node), NULL);
    ;}
    break;

  case 123:

/* Line 1455 of yacc.c  */
#line 3987 "semantic.y"
    {
        // $4 es el bloque de sentencias para el caso default
        (yyval.node) = create_node("DefaultCase", "default", (yyvsp[(3) - (3)].node), NULL);
    ;}
    break;

  case 124:

/* Line 1455 of yacc.c  */
#line 3992 "semantic.y"
    {
               add_or_find_function((yyvsp[(2) - (5)].sval), "inferred");
               (yyval.sval) = current_function_name;
               current_function_name = (yyvsp[(2) - (5)].sval);
                FunctionSymbol* func = lookup_function(current_function_name);
                 parse_and_store_parameters(func, (yyvsp[(4) - (5)].sval));
             ;}
    break;

  case 125:

/* Line 1455 of yacc.c  */
#line 3998 "semantic.y"
    {   
             //  enter_scope();
             
               FunctionSymbol* func = lookup_function(current_function_name);
               //parse_and_store_parameters(func, $4);
               
               // YA NO declaramos en la tabla de símbolos normal
               // Los parámetros están en global_params_list
               
               if (func && strcmp(func->return_type, "inferred") == 0) {
                 free(func->return_type);
                 func->return_type = "void";
               }
               char* formatted_params = format_parameters_as_string((yyvsp[(2) - (7)].sval));
               (yyval.node) = create_node("Function", (yyvsp[(2) - (7)].sval), create_node("Parameters", formatted_params, NULL, NULL), (yyvsp[(7) - (7)].node));
               generate_ast_file((yyval.node));
               current_function_name = (yyvsp[(6) - (7)].sval);
               
               // Limpiar parámetros al salir de la función
              // clear_function_parameters($2);
              // exit_scope();
             ;}
    break;

  case 126:

/* Line 1455 of yacc.c  */
#line 4021 "semantic.y"
    {
               add_or_find_function((yyvsp[(2) - (5)].sval), "inferred");
               (yyval.sval) = current_function_name;
               current_function_name = (yyvsp[(2) - (5)].sval);
               FunctionSymbol* func = lookup_function(current_function_name);
               parse_and_store_parameters(func, (yyvsp[(4) - (5)].sval));
             ;}
    break;

  case 127:

/* Line 1455 of yacc.c  */
#line 4027 "semantic.y"
    {
               enter_scope();
               FunctionSymbol* func = lookup_function(current_function_name);
        
               if (func && strcmp(func->return_type, "inferred") == 0) {
               free(func->return_type);
               func->return_type = "void";
               }
              char* formatted_params = format_parameters_as_string((yyvsp[(2) - (7)].sval));
              (yyval.node) = create_node("Function", (yyvsp[(2) - (7)].sval), create_node("Parameters", formatted_params, NULL, NULL), (yyvsp[(7) - (7)].node));
              generate_ast_file((yyval.node));
        
              clear_function_parameters((yyvsp[(2) - (7)].sval));
              current_function_name = (yyvsp[(6) - (7)].sval);
              exit_scope();
             ;}
    break;

  case 128:

/* Line 1455 of yacc.c  */
#line 4044 "semantic.y"
    {
                // Misma lógica de contexto para funciones con tipo explícito.
                (yyval.sval) = current_function_name;
                current_function_name = (yyvsp[(3) - (6)].sval);
                add_or_find_function((yyvsp[(3) - (6)].sval), (yyvsp[(1) - (6)].sval));
                FunctionSymbol* func = lookup_function((yyvsp[(3) - (6)].sval));
                parse_and_store_parameters(func, (yyvsp[(5) - (6)].sval))
               ;}
    break;

  case 129:

/* Line 1455 of yacc.c  */
#line 4051 "semantic.y"
    {
                enter_scope();
                FunctionSymbol* func = lookup_function((yyvsp[(3) - (8)].sval));
                 
                char* formatted_params = format_parameters_as_string((yyvsp[(3) - (8)].sval));
                (yyval.node) = create_node("Function", (yyvsp[(3) - (8)].sval), create_node("Parameters", formatted_params, NULL, create_node("ExplicitType", (yyvsp[(1) - (8)].sval), NULL, NULL)), (yyvsp[(8) - (8)].node));
                generate_ast_file((yyval.node));
        
                clear_function_parameters((yyvsp[(3) - (8)].sval));
                current_function_name = (yyvsp[(7) - (8)].sval);
                exit_scope();
             ;}
    break;

  case 130:

/* Line 1455 of yacc.c  */
#line 4063 "semantic.y"
    {
                (yyval.sval) = current_function_name;
                current_function_name = (yyvsp[(3) - (6)].sval);
                add_or_find_function((yyvsp[(3) - (6)].sval), (yyvsp[(1) - (6)].sval));
                FunctionSymbol* func = lookup_function((yyvsp[(3) - (6)].sval));
                parse_and_store_parameters(func, (yyvsp[(5) - (6)].sval));
               printf("Function: %d\n", lookup_function((yyvsp[(3) - (6)].sval))->return_value);
            ;}
    break;

  case 131:

/* Line 1455 of yacc.c  */
#line 4070 "semantic.y"
    {
                enter_scope();
                FunctionSymbol* func = lookup_function((yyvsp[(3) - (8)].sval));      
                char* formatted_params = format_parameters_as_string((yyvsp[(3) - (8)].sval));
                (yyval.node) = create_node("Function", (yyvsp[(3) - (8)].sval), create_node("Parameters", (yyvsp[(5) - (8)].sval), NULL, create_node("ExplicitType", (yyvsp[(1) - (8)].sval), NULL, NULL)), (yyvsp[(8) - (8)].node));
                generate_ast_file((yyval.node));
          
                clear_function_parameters((yyvsp[(3) - (8)].sval));
                current_function_name = (yyvsp[(7) - (8)].sval);
                exit_scope();
             ;}
    break;

  case 132:

/* Line 1455 of yacc.c  */
#line 4081 "semantic.y"
    {
               // Función sin parámetros
               add_or_find_function((yyvsp[(2) - (3)].sval), "inferred");
               (yyval.sval) = current_function_name;
               current_function_name = (yyvsp[(2) - (3)].sval);
                FunctionSymbol* func = lookup_function(current_function_name);
                parse_and_store_parameters(func, ""); // String vacío = sin parámetros
            ;}
    break;

  case 133:

/* Line 1455 of yacc.c  */
#line 4088 "semantic.y"
    {   
             FunctionSymbol* func = lookup_function((yyvsp[(2) - (5)].sval));
        if (func && strcmp(func->return_type, "inferred") == 0) {
            free(func->return_type);
            func->return_type = strdup("void");
        }

        (yyval.node) = create_node("Function", (yyvsp[(2) - (5)].sval), create_node("Parameters", "", NULL, NULL), (yyvsp[(5) - (5)].node));
        generate_ast_file((yyval.node));

        current_function_name = (yyvsp[(4) - (5)].sval);
             ;}
    break;

  case 134:

/* Line 1455 of yacc.c  */
#line 4100 "semantic.y"
    {
                add_or_find_function((yyvsp[(2) - (3)].sval), "inferred");
                (yyval.sval) = current_function_name;
                current_function_name = (yyvsp[(2) - (3)].sval);
              
             ;}
    break;

  case 135:

/* Line 1455 of yacc.c  */
#line 4105 "semantic.y"
    {
               enter_scope();
               FunctionSymbol* func = lookup_function(current_function_name);
               parse_and_store_parameters(func, ""); // Sin parámetros
        
                if (func && strcmp(func->return_type, "inferred") == 0) {
                free(func->return_type);
                func->return_type = "void";
                }
        
               (yyval.node) = create_node("Function", (yyvsp[(2) - (5)].sval), create_node("Parameters", "", NULL, NULL), (yyvsp[(5) - (5)].node));
               generate_ast_file((yyval.node));
        
              clear_function_parameters((yyvsp[(2) - (5)].sval));
              current_function_name = (yyvsp[(4) - (5)].sval);
              exit_scope();
             ;}
    break;

  case 136:

/* Line 1455 of yacc.c  */
#line 4122 "semantic.y"
    {
               // Función con tipo explícito sin parámetros
               (yyval.sval) = current_function_name;
               current_function_name = (yyvsp[(3) - (4)].sval);
               add_or_find_function((yyvsp[(3) - (4)].sval), (yyvsp[(1) - (4)].sval));
             ;}
    break;

  case 137:

/* Line 1455 of yacc.c  */
#line 4127 "semantic.y"
    {
                enter_scope();
                FunctionSymbol* func = lookup_function((yyvsp[(3) - (6)].sval));
                parse_and_store_parameters(func, ""); // Sin parámetros
        
                (yyval.node) = create_node("Function", (yyvsp[(3) - (6)].sval), create_node("Parameters", "", NULL, create_node("ExplicitType", (yyvsp[(1) - (6)].sval), NULL, NULL)), (yyvsp[(6) - (6)].node));
                generate_ast_file((yyval.node));
        
                clear_function_parameters((yyvsp[(3) - (6)].sval));
                current_function_name = (yyvsp[(5) - (6)].sval);
                exit_scope();
             ;}
    break;

  case 138:

/* Line 1455 of yacc.c  */
#line 4140 "semantic.y"
    {
              (yyval.sval) = current_function_name;
              current_function_name = (yyvsp[(3) - (4)].sval);
              add_or_find_function((yyvsp[(3) - (4)].sval), (yyvsp[(1) - (4)].sval));
             ;}
    break;

  case 139:

/* Line 1455 of yacc.c  */
#line 4144 "semantic.y"
    {
              enter_scope();
              FunctionSymbol* func = lookup_function((yyvsp[(3) - (6)].sval));
              parse_and_store_parameters(func, ""); // Sin parámetros
        
              (yyval.node) = create_node("Function", (yyvsp[(3) - (6)].sval), create_node("Parameters", "", NULL, create_node("ExplicitType", (yyvsp[(1) - (6)].sval), NULL, NULL)), (yyvsp[(6) - (6)].node));
              generate_ast_file((yyval.node));
        
              clear_function_parameters((yyvsp[(3) - (6)].sval));
              current_function_name = (yyvsp[(5) - (6)].sval);
               exit_scope();
              ;}
    break;

  case 140:

/* Line 1455 of yacc.c  */
#line 4158 "semantic.y"
    { 
                validate_function_call((yyvsp[(1) - (2)].sval), "");
              (yyval.node) = create_node("FunctionCall",(yyvsp[(1) - (2)].sval),create_node("Paramenters",NULL,NULL,NULL),NULL); generate_ast_file((yyval.node))
             ;}
    break;

  case 141:

/* Line 1455 of yacc.c  */
#line 4162 "semantic.y"
    {
                validate_function_call((yyvsp[(1) - (4)].sval), (yyvsp[(3) - (4)].sval));
                assign_arguments_to_parameters((yyvsp[(1) - (4)].sval), (yyvsp[(3) - (4)].sval));
                printf("parameters: %s\n", (yyvsp[(3) - (4)].sval));
              (yyval.node) = create_node("FunctionCall",(yyvsp[(1) - (4)].sval),create_node("Paramenters",add_quotes((yyvsp[(3) - (4)].sval)),NULL,NULL),NULL); generate_ast_file((yyval.node))
             ;}
    break;

  case 142:

/* Line 1455 of yacc.c  */
#line 4169 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 143:

/* Line 1455 of yacc.c  */
#line 4170 "semantic.y"
    {(yyval.sval) = concat_strings((yyvsp[(1) - (3)].sval),concat_strings(",",concat_strings(" ", (yyvsp[(3) - (3)].sval)))); ;}
    break;

  case 144:

/* Line 1455 of yacc.c  */
#line 4172 "semantic.y"
    { (yyval.sval) = concat_strings((yyvsp[(1) - (2)].sval),concat_strings(" ",(yyvsp[(2) - (2)].sval))); printf("param_decl: %s\n", (yyval.sval)); ;}
    break;

  case 145:

/* Line 1455 of yacc.c  */
#line 4173 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 146:

/* Line 1455 of yacc.c  */
#line 4178 "semantic.y"
    { 
                 // Buscar la función del contexto anterior ($<sval>0 es el TEXT de function_call)
                char* func_name = (yyvsp[(0) - (1)].sval);
                 FunctionSymbol* func = lookup_function(func_name);
                
                 if (func && func->param_list) {
                    char buffer[2048];
                    sprintf(buffer, "%s: %s", func->param_list->name, (yyvsp[(1) - (1)].sval));
                    (yyval.sval) = strdup(buffer);
                 } else {
                    (yyval.sval) = (yyvsp[(1) - (1)].sval);
                 }; 

                ;}
    break;

  case 147:

/* Line 1455 of yacc.c  */
#line 4192 "semantic.y"
    { 
                //$$ = concat_strings($1,concat_strings(",",concat_strings(" ",$3))); 
                 char* func_name = (yyvsp[(0) - (3)].sval);
                 FunctionSymbol* func = lookup_function(func_name);
                
                 if (func) {
                    // Contar cuántos parámetros llevamos
                    int current_index = 0;
                    char* temp = strdup((yyvsp[(1) - (3)].sval));
                    char* p = temp;
                    while (*p) {
                        if (*p == ',') current_index++;
                        p++;
                    }
                    free(temp);
                    current_index++; // El siguiente parámetro
                    
                    // Buscar el parámetro en esa posición
                    Parameter* param = func->param_list;
                    for (int i = 0; i < current_index && param != NULL; i++) {
                        param = param->next;
                    }
                    
                    if (param) {
                        char buffer[2048];
                        sprintf(buffer, "%s, %s: %s", (yyvsp[(1) - (3)].sval), param->name, (yyvsp[(3) - (3)].sval));
                        (yyval.sval) = strdup(buffer);
                        
                    } 
                 } else {
                    //$$ = concat_strings($1, concat_strings(", ", $3));
                 }
                ;}
    break;

  case 148:

/* Line 1455 of yacc.c  */
#line 4226 "semantic.y"
    { (yyval.sval) = "int"; ;}
    break;

  case 149:

/* Line 1455 of yacc.c  */
#line 4227 "semantic.y"
    { (yyval.sval) = "float"; ;}
    break;

  case 150:

/* Line 1455 of yacc.c  */
#line 4228 "semantic.y"
    { (yyval.sval) = "string"; ;}
    break;

  case 151:

/* Line 1455 of yacc.c  */
#line 4229 "semantic.y"
    { (yyval.sval) = "bool"; ;}
    break;

  case 152:

/* Line 1455 of yacc.c  */
#line 4230 "semantic.y"
    { (yyval.sval) = "void"; ;}
    break;

  case 153:

/* Line 1455 of yacc.c  */
#line 4236 "semantic.y"
    {
    char* var_name = (yyvsp[(1) - (2)].sval);
        symbol* s = find_variable(var_name);
        if (!s) {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, var_name);
            yyerror(error_msg);
            exit(1);
        }
        
        // Convertir el valor de la variable
        char* converted_value = convert_to_int((yyvsp[(1) - (2)].sval));
        if (converted_value == NULL) {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: No se puede convertir '%s' de tipo '%s' a int.", yylineno, s->value, s->type);
            yyerror(error_msg);
            exit(1);
        }
        
        (yyval.sval) = converted_value; // Devuelve el valor convertido
        //eassign_var($1, converted_value, NULL); 
;}
    break;

  case 154:

/* Line 1455 of yacc.c  */
#line 4263 "semantic.y"
    {   
               ast_node* list = (yyvsp[(1) - (2)].node);
              // Navega hasta el final de la lista de sentencias (hermanos)
              while (list->right != NULL) {
                  list = list->right;
              }
              // Enlaza la nueva sentencia como el siguiente hermano
              list->right = (yyvsp[(2) - (2)].node);
              (yyval.node) = (yyvsp[(1) - (2)].node); // Devuelve el inicio de la lista
         ;}
    break;

  case 155:

/* Line 1455 of yacc.c  */
#line 4273 "semantic.y"
    {(yyval.node) = (yyvsp[(1) - (1)].node);}
    break;

  case 156:

/* Line 1455 of yacc.c  */
#line 4275 "semantic.y"
    {   
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

         (yyval.sval) = (yyvsp[(1) - (1)].sval);       
;}
    break;

  case 158:

/* Line 1455 of yacc.c  */
#line 4294 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 159:

/* Line 1455 of yacc.c  */
#line 4295 "semantic.y"
    { 
          //  char* val1 = get_var($1) ? $1 : get_var($1);
           //char* val2 = get_var($3) ? $3 : get_var($3);

        (yyval.sval) = concat_con_espacio((yyvsp[(1) - (3)].sval),(yyvsp[(3) - (3)].sval)); 
     ;}
    break;

  case 163:

/* Line 1455 of yacc.c  */
#line 4306 "semantic.y"
    { paren_num++; printf("paren abierta\n");
          expression_op[expression_num].op = "(";
          expression_op[expression_num].num = 2; // 2 = Inicio de Paréntesis
          expression_num++;

          ;}
    break;

  case 164:

/* Line 1455 of yacc.c  */
#line 4312 "semantic.y"
    { paren_num--; printf("paren cerrado\n"); 
              expression_op[expression_num].op = ")";
              expression_op[expression_num].num = 3; // 3 = Fin de Paréntesis
              expression_num++;
           ;}
    break;

  case 165:

/* Line 1455 of yacc.c  */
#line 4318 "semantic.y"
    { 
                    longitud = 0; 
                    (yyval.sval) = ""; 
                ;}
    break;

  case 166:

/* Line 1455 of yacc.c  */
#line 4322 "semantic.y"
    { 
                    (yyval.sval) = (yyvsp[(1) - (1)].sval); // Simplemente pasa el resultado de la lista de pares.
                ;}
    break;

  case 167:

/* Line 1455 of yacc.c  */
#line 4328 "semantic.y"
    { 
                    longitud = 1; 
                    (yyval.sval) = (yyvsp[(1) - (1)].sval); 
                ;}
    break;

  case 168:

/* Line 1455 of yacc.c  */
#line 4332 "semantic.y"
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

  case 169:

/* Line 1455 of yacc.c  */
#line 4348 "semantic.y"
    {
    char buffer[1024];
    sprintf(buffer, "%s:%s", add_quotes((yyvsp[(1) - (3)].sval)), (yyvsp[(3) - (3)].sval));
    (yyval.sval) = strdup(buffer);
;}
    break;

  case 170:

/* Line 1455 of yacc.c  */
#line 4353 "semantic.y"
    {  (yyval.sval) = (yyvsp[(2) - (3)].sval); ;}
    break;

  case 171:

/* Line 1455 of yacc.c  */
#line 4354 "semantic.y"
    {         
            concat_op = op_concat((yyvsp[(1) - (3)].sval),'+',(yyvsp[(3) - (3)].sval));
            if (is_current_func_param((yyvsp[(1) - (3)].sval)) || is_current_func_param((yyvsp[(3) - (3)].sval)) || is_runtime_access_string((yyvsp[(1) - (3)].sval)) || is_runtime_access_string((yyvsp[(3) - (3)].sval)) ) {
                (yyval.sval) = concat_op; 
                valid = 0; // Invalidamos para que rules superiores no intenten parsearlo como número
            }else{
            valid = valid_expression(concat_op);
            char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
            char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);

            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            printf("valid: %d\n",valid);
           //printf("expr1S: %s, expr2S: : %s\n", $1, $3);
          //  if(valid==1){ 
              expression_op[expression_num].op = "+";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;         
              printf("val1: %s, val2: %s\n", val1, val2);
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             (yyval.sval) = do_op_float(val1,'+',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             (yyval.sval) = do_op(val1,'+',val2);
            }/*else if(strcmp(expr1, "string") == 0 || strcmp(expr2, "string") == 0){
              $$ = op_concat(val1, '+', val2);

            }*/else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '+' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
         //   exit(1); // Detener el análisis
             
            }
         }
         
        ;}
    break;

  case 172:

/* Line 1455 of yacc.c  */
#line 4390 "semantic.y"
    { 
            concat_op = op_concat((yyvsp[(1) - (3)].sval),'-',(yyvsp[(3) - (3)].sval));
            if (is_current_func_param((yyvsp[(1) - (3)].sval)) || is_current_func_param((yyvsp[(3) - (3)].sval)) || is_runtime_access_string((yyvsp[(1) - (3)].sval)) || is_runtime_access_string((yyvsp[(3) - (3)].sval))) {
                (yyval.sval) = concat_op; 
                valid = 0; 
            }else{
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
             (yyval.sval) = do_op_float(val1,'-',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             (yyval.sval) = do_op(val1,'-',val2);
              }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '-' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
          //   exit(1); // Detener el análisis
             }
            }
          }
          ;}
    break;

  case 173:

/* Line 1455 of yacc.c  */
#line 4420 "semantic.y"
    {

            concat_op = op_concat((yyvsp[(1) - (3)].sval),'*',(yyvsp[(3) - (3)].sval));
           if (is_current_func_param((yyvsp[(1) - (3)].sval)) || is_current_func_param((yyvsp[(3) - (3)].sval)) || is_runtime_access_string((yyvsp[(1) - (3)].sval)) || is_runtime_access_string((yyvsp[(3) - (3)].sval))) {
                (yyval.sval) = concat_op; 
                valid = 0; 
            }else{
            valid = valid_expression(concat_op);
            char* val1 = get_var((yyvsp[(1) - (3)].sval)) ? get_var((yyvsp[(1) - (3)].sval)) : (yyvsp[(1) - (3)].sval);
            char* val2 = get_var((yyvsp[(3) - (3)].sval)) ? get_var((yyvsp[(3) - (3)].sval)) : (yyvsp[(3) - (3)].sval);
            char *expr1 = determine_type(val1);
            char *expr2 = determine_type(val2);
            printf("val1: %s, val2: %s\n", val1, val2);
            printf("op_concat: %s\n", concat_op);
            //printf("valid: %d\n",valid);
           // printf("Texpr1: %s, Texpr2: : %s\n", $1, $3);
            //if(valid==1){   
              expression_op[expression_num].op = "*";
              expression_op[expression_num].num = 1; // 1 = Operador
              expression_num++;
            if(strcmp(expr1, "float") == 0 || strcmp(expr2, "float") == 0){
             (yyval.sval) = do_op_float(val1,'*',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
              printf("do_op: %s\n", do_op(val1,'*',val2));
             (yyval.sval) = do_op(val1,'*',val2);
              
            }else if(strcmp(expr1, "string") == 0 && strcmp(expr2, "string") == 0){
              (yyval.sval) = do_op(val1, '*', val2);

            }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '*' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
           //  exit(1); // Detener el análisis
          //  }
             }
            } 
           ;}
    break;

  case 174:

/* Line 1455 of yacc.c  */
#line 4458 "semantic.y"
    { 
            concat_op = op_concat((yyvsp[(1) - (3)].sval),'/',(yyvsp[(3) - (3)].sval));
            if (is_current_func_param((yyvsp[(1) - (3)].sval)) || is_current_func_param((yyvsp[(3) - (3)].sval)) || is_runtime_access_string((yyvsp[(1) - (3)].sval)) || is_runtime_access_string((yyvsp[(3) - (3)].sval))) {
                (yyval.sval) = concat_op; 
                valid = 0; 
            }else{ 
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
          //   exit(1); // Detener el análisis
              }
             }
             }
            ;}
    break;

  case 175:

/* Line 1455 of yacc.c  */
#line 4486 "semantic.y"
    {
                concat_op = op_concat((yyvsp[(1) - (3)].sval), '%', (yyvsp[(3) - (3)].sval));
                if (is_current_func_param((yyvsp[(1) - (3)].sval)) || is_current_func_param((yyvsp[(3) - (3)].sval)) || is_runtime_access_string((yyvsp[(1) - (3)].sval)) || is_runtime_access_string((yyvsp[(3) - (3)].sval))) {
                (yyval.sval) = concat_op; 
                valid = 0; 
            }else{
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
                    sprintf(error_msg, "Error semantico en linea %d: La operacion '%%' solo esta soportada entre enteros (int), no entre '%s' y '%s'.", yylineno, type1, type2);
                    yyerror(error_msg);
               //     exit(1); // Terminar el análisis si hay un error
                   // $$ = "0"; // Valor por defecto para que no se rompa el parser
                }
              }
            ;}
    break;

  case 176:

/* Line 1455 of yacc.c  */
#line 4519 "semantic.y"
    { (yyval.sval) = to_string((yyvsp[(1) - (1)].ival)); ;}
    break;

  case 177:

/* Line 1455 of yacc.c  */
#line 4520 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 178:

/* Line 1455 of yacc.c  */
#line 4521 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 179:

/* Line 1455 of yacc.c  */
#line 4522 "semantic.y"
    { (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 180:

/* Line 1455 of yacc.c  */
#line 4523 "semantic.y"
    { // Caso recursivo para el acceso profundo
                   char buffer[1024];
                   sprintf(buffer, "%s:%s", (yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval));
                   (yyval.sval) = strdup(buffer);
               ;}
    break;

  case 181:

/* Line 1455 of yacc.c  */
#line 4530 "semantic.y"
    { (yyval.sval) = "True"; ;}
    break;

  case 182:

/* Line 1455 of yacc.c  */
#line 4531 "semantic.y"
    { (yyval.sval) = "False"; ;}
    break;

  case 183:

/* Line 1455 of yacc.c  */
#line 4534 "semantic.y"
    { (yyval.sval) = to_string((yyvsp[(1) - (1)].ival));  
       expression_op[expression_num].op = strdup((yyval.sval));
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    ;}
    break;

  case 184:

/* Line 1455 of yacc.c  */
#line 4539 "semantic.y"
    { (yyval.sval) = add_quotes((yyvsp[(1) - (1)].sval));;}
    break;

  case 185:

/* Line 1455 of yacc.c  */
#line 4540 "semantic.y"
    { (yyval.sval) = floatToString((yyvsp[(1) - (1)].fval)); 
        expression_op[expression_num].op = strdup((yyval.sval));
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    ;}
    break;

  case 186:

/* Line 1455 of yacc.c  */
#line 4545 "semantic.y"
    {
          // 1. Llamamos a nuestra nueva función orquestadora
    (yyval.sval) = legacy_access_collection_element((yyvsp[(1) - (4)].sval), (yyvsp[(3) - (4)].sval));
    // printf("access_collection_element result: %s\n", legacy_access_collection_element($1, $3));
    // 2. Manejamos el caso en que no se encuentre el elemento
    if ((yyval.sval) == NULL) {
        char error_msg[256];
        sprintf(error_msg, "Error en linea %d: La clave o indice '%s' no se encontro o es invalido para '%s'.", yylineno, (yyvsp[(3) - (4)].sval), (yyvsp[(1) - (4)].sval));
        yyerror(error_msg);
        exit(1); // Detener el análisis
    }
  ;}
    break;

  case 187:

/* Line 1455 of yacc.c  */
#line 4557 "semantic.y"
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

  case 188:

/* Line 1455 of yacc.c  */
#line 4570 "semantic.y"
    { 
            // Se llama a la nueva función en el momento correcto
           char* final_string = process_string((yyvsp[(1) - (1)].sval));
           (yyval.sval) = add_quotes(final_string);
          free(final_string); 
       // $$ = add_quotes(removeParentheses($1));
        ;}
    break;

  case 189:

/* Line 1455 of yacc.c  */
#line 4577 "semantic.y"
    {
        expression_op[expression_num].op = strdup((yyval.sval));
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    ;}
    break;

  case 191:

/* Line 1455 of yacc.c  */
#line 4584 "semantic.y"
    { 
      FunctionSymbol* func = lookup_function((yyvsp[(1) - (4)].sval));
              //validate_function_call($1, $3);
              char* func_call_str;
        if ((yyvsp[(3) - (4)].sval) && strlen((yyvsp[(3) - (4)].sval)) > 0) {
            // Hay argumentos: "funcion(arg1, arg2)"
            size_t len = strlen((yyvsp[(1) - (4)].sval)) + strlen((yyvsp[(3) - (4)].sval)) + 4; // +4 para "()" y null terminator
            func_call_str = malloc(len);
            sprintf(func_call_str, "%s(%s)", (yyvsp[(1) - (4)].sval), (yyvsp[(3) - (4)].sval));
        } else {
            // Sin argumentos: "funcion()"
            size_t len = strlen((yyvsp[(1) - (4)].sval)) + 3; // +3 para "()" y null terminator
            func_call_str = malloc(len);
            sprintf(func_call_str, "%s()", (yyvsp[(1) - (4)].sval));
        }
        (yyval.sval) = func_call_str;
              printf("parameters: %s\n", (yyvsp[(3) - (4)].sval));
            // TU LÓGICA DE INFERENCIA YA FUNCIONA AQUÍ:
            // Si una función no tuvo 'return', su func->return_type ya habrá sido
            // cambiado a "void" al final de su declaración.

            // 1. Verificamos el tipo final de la función.
           /* if (strcmp(func->return_type, "void") == 0) {
                // Si es void, devolvemos el marcador especial.
                $$ = VOID_RESULT_MARKER;
            } else {
                // 2. Si NO es void, aplicamos la lógica de retorno normal.
                if (func->return_value != NULL) {
                    // Tenía un 'return', usamos su valor.
                    
                    $$ = func_call_str;
                } else {
                    // No tenía 'return' pero es tipada, usamos el default.
                    if (strcmp(func->return_type, "int") == 0) $$ = "0";
                    else if (strcmp(func->return_type, "float") == 0) $$ = "0.0";
                    else if (strcmp(func->return_type, "string") == 0) $$ = "\"\"";
                    else if (strcmp(func->return_type, "bool") == 0) $$ = "False";
                    else $$ = "NULL"; // Fallback
                }
            }*/
        //} 
    ;}
    break;

  case 192:

/* Line 1455 of yacc.c  */
#line 4627 "semantic.y"
    {(yyval.sval) = (yyval.sval);;}
    break;

  case 193:

/* Line 1455 of yacc.c  */
#line 4628 "semantic.y"
    { 
                char *temp_str = concatenateComparison((yyvsp[(1) - (3)].sval), " in ", (yyvsp[(3) - (3)].sval)); 
                (yyval.sval) = concatenateComparison("",",",temp_str);
             ;}
    break;

  case 194:

/* Line 1455 of yacc.c  */
#line 4632 "semantic.y"
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

  case 195:

/* Line 1455 of yacc.c  */
#line 4648 "semantic.y"
    {(yyval.sval) ="&&";;}
    break;

  case 196:

/* Line 1455 of yacc.c  */
#line 4649 "semantic.y"
    {(yyval.sval) = "||";;}
    break;

  case 198:

/* Line 1455 of yacc.c  */
#line 4651 "semantic.y"
    { char *temp_str = concatenateComparison((yyvsp[(1) - (3)].sval), " in ", (yyvsp[(3) - (3)].sval)); 
           (yyval.sval) = concatenateComparison("",",",temp_str);;}
    break;

  case 200:

/* Line 1455 of yacc.c  */
#line 4659 "semantic.y"
    { 
             // Concatenamos las comparaciones y resultados
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
            ;}
    break;

  case 201:

/* Line 1455 of yacc.c  */
#line 4673 "semantic.y"
    {    
            comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"==", (yyvsp[(3) - (3)].sval));           
             if(strcmp((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval)) == 0){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); } 
          ;}
    break;

  case 202:

/* Line 1455 of yacc.c  */
#line 4677 "semantic.y"
    {
            comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"!=", (yyvsp[(3) - (3)].sval));
            if(strcmp((yyvsp[(1) - (3)].sval), (yyvsp[(3) - (3)].sval)) == 0){ (yyval.sval) = concatenateComparison("False",",",comparison); }else{ (yyval.sval) = concatenateComparison("True",",",comparison); }
             
          ;}
    break;

  case 203:

/* Line 1455 of yacc.c  */
#line 4682 "semantic.y"
    {
             comparison = concatenateComparison((yyvsp[(1) - (3)].sval),">", (yyvsp[(3) - (3)].sval));
            if(atoi((yyvsp[(1) - (3)].sval)) > atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison);}else{ (yyval.sval) = concatenateComparison("False",",",comparison); }
          ;}
    break;

  case 204:

/* Line 1455 of yacc.c  */
#line 4686 "semantic.y"
    {
             comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"<", (yyvsp[(3) - (3)].sval));
            if(atoi((yyvsp[(1) - (3)].sval))  < atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }
          ;}
    break;

  case 205:

/* Line 1455 of yacc.c  */
#line 4690 "semantic.y"
    {
            comparison = concatenateComparison((yyvsp[(1) - (3)].sval),">=", (yyvsp[(3) - (3)].sval));
            if(atoi((yyvsp[(1) - (3)].sval))  >= atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }      
          ;}
    break;

  case 206:

/* Line 1455 of yacc.c  */
#line 4694 "semantic.y"
    {
            comparison = concatenateComparison((yyvsp[(1) - (3)].sval),"<=", (yyvsp[(3) - (3)].sval));
            if(atoi((yyvsp[(1) - (3)].sval))  <= atoi((yyvsp[(3) - (3)].sval))){ (yyval.sval) = concatenateComparison("True",",",comparison); }else{ (yyval.sval) = concatenateComparison("False",",",comparison); }            
          ;}
    break;

  case 207:

/* Line 1455 of yacc.c  */
#line 4700 "semantic.y"
    { longitud = 1; (yyval.sval) = (yyvsp[(1) - (1)].sval); ;}
    break;

  case 208:

/* Line 1455 of yacc.c  */
#line 4701 "semantic.y"
    { 
           // Un array con múltiples elementos.
                char* tempList = concat_strings((yyvsp[(1) - (3)].sval), ",");
                (yyval.sval) = concat_strings(tempList, (yyvsp[(3) - (3)].sval));
                free(tempList); // Liberar memoria intermedia.
                longitud++;
         // printf("exprlist: %s\n",$$);
          ;}
    break;

  case 209:

/* Line 1455 of yacc.c  */
#line 4736 "semantic.y"
    {
  ;}
    break;



/* Line 1455 of yacc.c  */
#line 7551 "semantic.tab.c"
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
#line 4739 "semantic.y"

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
            //compile_mode = 1; // Activamos el modo compilador
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
    
    init_scope_manager();
    yyparse(); // Ya no se le pasa nada aquí

    printf("✅ AST generado en: %s\n", g_output_path);
    fclose(yyin);
 
    return 0;
}
