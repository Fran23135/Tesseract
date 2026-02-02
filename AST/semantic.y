%{
    
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

%}
%union {
    int ival;
    char *sval;
    char **arrval;
    float fval;
    struct ast_node* node;
}

%type <node> var const
%type <sval> var_for
%token <sval> TEXT
%token <sval> STRING STRING_WITH_VARS
%token <ival> NUMBER INCREMENT DECREMENT
%token PRINT VAR PLUS MINUS TIMES DIVIDE EQUAL SEMICOLON READ  INSERTVALUE COLON CONST
%token DOT COM SHARP LSQUARE RSQUARE SQUARES_L_R ELSE ELSE_IF RANGE_SEMI_OPEN IFX 
%token EQUALC UNEQUAL GREATERTHAN LESSTHAN GREATERTHAN_EQUAL LESSTHAN_EQUAL //PARENTHESES
%token TRUE FALSE BOOL INDENT DEDENT  STRUCT
%token TSTRING TINT TFLOAT TBOOL TVOID DOTYPEINT   
%token FOR IN RANGE  MAIN DOTYPE APPEND LENGHT WHILE IF PERFORM
%token BREAK RETURN  MOD CONTINUE NOT 
%token FUNCTION FUNC  PARENS QUESTION_MARK
%token SWITCH CASE DEFAULT
%token <sval> startRace // llave de entrada 
%token <sval> endRace  // llave de cierre
%token <sval> OR AND
%token <fval> DECIMAL NEWLINE
%token IM IM_Math PI EQUATION
%type <node> function_decl function_call array_decl array_assing   perform_while_loop array_const_decl //array   
%type <node> statement print read block  rlrace rbrace statements while_loop if_condition 
%type <node> for_loop  condtional_stmt sentences tuples increment_decrement_stmt tuples_const
%type <node> switch_cases case_list single_case switch_block  library_call
%type <sval>  variable_conversion 
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
    | function_call end_statement
    | while_loop
    | perform_while_loop
    | if_condition
    | switch_cases
    | library_call
    | increment_decrement_stmt end_statement // <-- AÑADE ESTA LÍNEA
    //| array SEMICOLON
    | sentences end_statement
    ;  
library_call: IM_Math {
      // Crear el nodo para la llamada a la función de la biblioteca 
      register_math_library();
      $$ = create_node("LibraryCall", "Math", NULL, NULL);
      generate_ast_file($$);
     }
     ;    
print: PRINT '(' expr ')' {  
      // Crear el nodo para la instrucción print
      // Primero, verificamos si $3 es una variable declarada
      symbol* s = find_variable($3);
      printf("s en print: %p\n", (void*)s);
      char* val1 = get_var($3) ? get_var($3) : $3;
      printf("Valor recibido para imprimir: %s\n", val1);
      //printf("Valor a imprimir: %s\n", s->value);
      if (s) { // SI es una variable
          // Comprobamos si la variable tiene una operación guardada
          printf("variable name: %s\n", s->name);
          if (s->operation_str != NULL) {
              
              $$ = create_node("CallExpression", "print", create_node("Arguments", $3, NULL, NULL), create_node("Operation", s->operation_str, NULL, create_node("variableName", s->name, NULL, NULL)));
          } else {
              // Si no, creamos el nodo simple
             int vals = is_array_access_with_variables(s->value);
             printf("tipo %d\n", vals);
              if(vals){
               $$ = create_node("CallExpression", "print", create_node("Arguments", $3, NULL, create_node("ParamType", "ArrayAccess", NULL, create_node("variableName", s->name, NULL, NULL))), NULL);
              }else{
                
               $$ = create_node("CallExpression", "print", create_node("Arguments", $3, NULL, create_node("ParamType",determine_type(get_var($3)) , NULL, create_node("variableName", s->name, create_node("val",val1,NULL,NULL), NULL))), NULL);
              }
              
                                                                                                                                                    
             // printf("Tipo de la variable '%s' es '%s'\n", s->name, s->type);
         }
      } else { // NO es una variable (es un literal o una operación directa)
          if (valid == 1) {
              con_op = reconstruct_expression();
              $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("Operation", con_op, NULL, NULL));
              valid = 0;
          } else {
             // $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, NULL), create_node("ParamType", determine_type($3), NULL, NULL));
                $$ = create_node("CallExpression", "print", create_node("Arguments", val1, NULL, create_node("ParamType", determine_type($3), NULL, NULL)), NULL);
                
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
      declare_var($2,"NULL","NULL",false,NULL,false);
      $$ = create_node("VariableDeclaration", $2, create_node("Value","NULL", create_node("Type","NULL",NULL,NULL),NULL), NULL); generate_ast_file($$);  }
   | VAR TEXT EQUAL expr {
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
             declare_var($2,$4,expr,false,con_op,false);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file($$);
           valid = 0;
        }else if(valid==0){
            declare_var($2,$4,expr,false,NULL,false);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),NULL), NULL); generate_ast_file($$); 
         }
       }
    
   }
   | VAR TEXT EQUAL startRace dict_body  endRace {
    char buffer[4096];
    sprintf(buffer, "{%s}", $5); // Envuelve el contenido con llaves
    declare_var($2, buffer, "Dict", false, NULL,false);
    $$ = create_node("VariableDeclaration", $2, create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
    generate_ast_file($$);
   } 
   | TEXT EQUAL startRace dict_body  endRace {
             char* node_type = "VariableAsignement";
            if (is_current_func_param($1)) {
                node_type = "ParameterAsignement";
            }
    if(get_var($1)){
        char buffer[4096];
        sprintf(buffer, "{%s}", $4); // Envuelve el contenido con llaves
        reassign_var_with_type($1, buffer, "Dict");
        $$ = create_node(node_type, $1, create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
    } else {
        char error_msg[256];
        sprintf(error_msg, "Line %d: Variable '%s' not declared", yylineno, $1);
        yyerror(error_msg);
        exit(1);
    }
   }
   | VAR TEXT EQUAL range {
     declare_var($2,$4,"Range",false,NULL,false);
   $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type","Range",NULL,NULL),NULL), NULL); generate_ast_file($$);
   }
   | TEXT EQUAL expr {
       printf("assign: %s\n",$3);
        if (strcmp($3, VOID_RESULT_MARKER) == 0) {
           char error_msg[256];
           sprintf(error_msg, "Line %d: Cannot assign result of a void function to variable '%s'", yylineno, $1);
           yyerror(error_msg);
           exit(1);
       }else{
        if (find_variable($1)) {
            char* node_type = "VariableAsignement";
                if (is_current_func_param($1)) {
                node_type = "ParameterAsignement";
                }
             if (valid == 1) {
                
                 con_op = reconstruct_expression();
                 char * expr = determine_type($3);
                 
                 reassign_var($1, $3, con_op);
                 $$ = create_node(node_type, $1, create_node("Value", $3, create_node("Type", expr, NULL, NULL), create_node("Operation", con_op, NULL, NULL)), NULL); 
                 generate_ast_file($$);
                 valid = 0;
             } else if (valid == 0) {
                 reassign_var($1, $3, NULL);
                 char * expr = determine_type($3);
                 
                 $$ = create_node(node_type, $1, create_node("Value", $3, create_node("Type", expr, NULL, NULL), NULL), NULL); 
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

   | types TEXT {
      char* explicit_type = $1;
    // 2. Obtenemos el valor por defecto para ese tipo (ej. "0")
    char* default_value = get_default_value_for_type(explicit_type);
     declare_var($2,default_value,$1,true, NULL,false);
      $$ = create_node("VariableDeclaration", $2, create_node("Value",default_value, create_node("Type",$1,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$);
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
   }
   | types TEXT EQUAL expr {
     // Crear el nodo para una asignación
      char * expr = determine_type($4);
      printf("types es: %s\n",$4);
      if(strcmp($1,expr) == 0){
        if(valid==1){
           con_op = reconstruct_expression(); 
            declare_var($2,$4,$1,true,con_op,false);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,create_node("ExplicitType",$1,NULL,NULL)),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file($$);
           valid = 0;
        }else if(valid==0){
            declare_var($2,$4,$1,true,NULL,false);
          $$ = create_node("VariableDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),create_node("ExplicitType",$1,NULL,NULL)), NULL); generate_ast_file($$); 
        }
       }else{
        char error_msg[512];
        sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $4, expr, $2, $1);
        yyerror(error_msg);
        exit(1);
    
       }
     }
    | array_decl
    | array_const_decl
    | array_assing 
    | tuples
    | tuples_const
    | const
   
   ;  

const: CONST TEXT {
        declare_var($2,"NULL","NULL",true,NULL,true);
        $$ = create_node("ConstantDeclaration", $2, create_node("Value",$2, create_node("Type","NULL",NULL,NULL),NULL), NULL); generate_ast_file($$); 
    } 
    | CONST TEXT EQUAL expr {
      char * expr = determine_type($4);
      //declare_var($2,$4,expr,true,NULL,true);
    
       if(valid==1){
             con_op = reconstruct_expression();
             declare_var($2,$4,expr,false,con_op,true);
          $$ = create_node("ConstantDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file($$);
           valid = 0;
        }else if(valid==0){
            declare_var($2,$4,expr,false,NULL,true);
          $$ = create_node("ConstantDeclaration", $2, create_node("Value",$4, create_node("Type",expr,NULL,NULL),NULL), NULL); generate_ast_file($$);  
        }
    }  
    | CONST types TEXT {
        char* explicit_type = $2;
    // 2. Obtenemos el valor por defecto para ese tipo (ej. "0")
      char* default_value = get_default_value_for_type(explicit_type);
      declare_var($3,"NULL",$2,true, NULL,true);
      $$ = create_node("ConstantDeclaration", $3, create_node("Value","NULL", create_node("Type",$2,NULL,NULL),create_node("ExplicitType",$2,NULL,NULL)), NULL); generate_ast_file($$);

    }
    | CONST types TEXT EQUAL expr {
      // Crear el nodo para una asignación
      char * expr = determine_type($5);
      //printf("types es: %s\n",$4);
      if(strcmp($2,expr) == 0){
        if(valid==1){
           con_op = reconstruct_expression(); 
            declare_var($3,$5,$2,true,con_op,true);
          $$ = create_node("ConstantDeclaration", $3, create_node("Value",$5, create_node("Type",expr,NULL,create_node("ExplicitType",$2,NULL,NULL)),create_node("Operation",con_op,NULL,NULL)), NULL); generate_ast_file($$);
           valid = 0;
        }else if(valid==0){
            declare_var($3,$5,$2,true,NULL,true);
          $$ = create_node("ConstantDeclaration", $3, create_node("Value",$5, create_node("Type",expr,NULL,NULL),create_node("ExplicitType",$2,NULL,NULL)), NULL); generate_ast_file($$); 
        }
       }
     }
    | CONST TEXT EQUAL startRace dict_body  endRace {
     char buffer[4096];
     sprintf(buffer, "{%s}", $5); // Envuelve el contenido con llaves
     declare_var($2, buffer, "Dict", false, NULL,true);
     $$ = create_node("ConstantDeclaration", $2, create_node("Value", buffer, create_node("Type", "Dict", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
     generate_ast_file($$);
    }
    ;

tuples: VAR TEXT EQUAL paren_left  list_item_list  paren_right {
        char buffer[2048];
        sprintf(buffer, "(%s)", $5);
        declare_var($2, buffer, "Tuple", false,NULL,false);
        
        $$ = create_node("VariableDeclaration", $2, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
   }
   | VAR TEXT EQUAL paren_left list_item_list COM paren_right {
        char buffer[2048];
        sprintf(buffer, "(%s,)", $5);
        declare_var($2, buffer, "Tuple", false,NULL,false);
        $$ = create_node("VariableDeclaration", $2, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }    
   | types TEXT EQUAL paren_left  list_item_list  paren_right {
         char buffer[2048];
         char * expr = determineArrayType($5);
          sprintf(buffer, "(%s)", $5);
           printf("types es: %s\n",determineArrayType($5));
           if(strcmp(determineArrayType($5),$1)== 0){
            declare_var($2,buffer,"Tuple",true,NULL,false);
            $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",$1,NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor  de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, expr, $2, $1);
             yyerror(error_msg);
             exit(1);
            }
   }   
   | types TEXT EQUAL paren_left list_item_list COM paren_right {
        char buffer[2048];
         char * expr = determineArrayType($5);
          sprintf(buffer, "(%s,)", $5);
           printf("types es: %s\n",determineArrayType($5));
           if(strcmp(determineArrayType($5),$1)== 0){
            declare_var($2,buffer,"Tuple",true,NULL,false);
            $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",$1,NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $5, expr, $2, $1);
             yyerror(error_msg);
             exit(1);
            }
        
   }
   | TEXT EQUAL paren_left list_item_list paren_right {
         char* node_type = "VariableAsignement";
                if (is_current_func_param($1)) {
                node_type = "ParameterAsignement";
                }
        char buffer[2048];
        sprintf(buffer, "(%s)", $4);
       reassign_var($1, buffer,NULL);
        $$ = create_node(node_type, $1, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }
   | TEXT EQUAL paren_left list_item_list COM paren_right {
        char* node_type = "VariableAsignement";
            if (is_current_func_param($1)) {
                node_type = "ParameterAsignement";
            }
        char buffer[2048];
        sprintf(buffer, "(%s,)", $4);
       reassign_var($1, buffer,NULL);
        $$ = create_node(node_type, $1, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }   
   ;
tuples_const: CONST TEXT EQUAL paren_left  list_item_list  paren_right {
        char buffer[2048];
        sprintf(buffer, "(%s)", $5);
        declare_var($2, buffer, "Tuple", false,NULL,true);
        
        $$ = create_node("ConstantDeclaration", $2, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
   }
   | CONST TEXT EQUAL paren_left list_item_list COM paren_right {
        char buffer[2048];
        sprintf(buffer, "(%s,)", $5);
        declare_var($2, buffer, "Tuple", false,NULL,true);
        $$ = create_node("ConstantDeclaration", $2, create_node("Value", strdup(buffer), create_node("Type", "Tuple", NULL, NULL), create_node("longitud", to_string(longitud), NULL, NULL)), NULL);
        generate_ast_file($$);
        longitud = 1;
        
   }        
   | CONST types TEXT EQUAL paren_left  list_item_list  paren_right {
         char buffer[2048];
         char * expr = determineArrayType($6);
          sprintf(buffer, "(%s)", $6);
           printf("types es: %s\n",determineArrayType($6));
           if(strcmp(determineArrayType($6),$2)== 0){
            declare_var($3,buffer,"Tuple",true,NULL,true);
            $$ = create_node("VariableDeclaration", $3, create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",$2,NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor  de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, expr, $3, $2);
             yyerror(error_msg);
             exit(1);
            }
   }   
   | CONST types TEXT EQUAL paren_left list_item_list COM paren_right {
        char buffer[2048];
         char * expr = determineArrayType($6);
          sprintf(buffer, "(%s,)", $6);
           printf("types es: %s\n",determineArrayType($6));
           if(strcmp(determineArrayType($6),$2)== 0){
            declare_var($3,buffer,"Tuple",true,NULL,true);
            $$ = create_node("VariableDeclaration",$3, create_node("Value",strdup(buffer), create_node("Type","Tuple",NULL,create_node("ExplicitType",$2,NULL,NULL)),NULL), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $6, expr, $3, $2);
             yyerror(error_msg);
             exit(1);
            }
        
    }  
    ;

array_decl: VAR TEXT EQUAL LSQUARE list_item_list  RSQUARE {
          char buffer[2048];
           sprintf(buffer, "[%s]", $5);
           declare_var($2,buffer,"Array",false,NULL,false);
           $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
           longitud = 1;
           printf("%s\n",buffer);
          }
          | VAR TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE list_item_list  RSQUARE {
            char buffer[2048];
          sprintf(buffer, "[%s]", $8);
            declare_var($2,buffer,"Array",false,NULL,false);
            $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
         }
         | VAR TEXT EQUAL SQUARES_L_R{
          // if(strcmp($2,$2)== 0){
           declare_var($2,NULL,"Array",false,NULL,false);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           //}
         }
         | VAR TEXT LSQUARE NUMBER RSQUARE {
           //if(strcmp($1,$1)== 0){  
           declare_var($2,NULL,"Array",false,NULL,false);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",NULL,create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
        //   }
         }
         | types TEXT EQUAL LSQUARE list_item_list  RSQUARE {
            char buffer[2048];
          sprintf(buffer, "[%s]", $5);
           printf("types es: %s\n",determineArrayType($5));
           char* expr = determineArrayType($5);
           if(strcmp(expr,$1)== 0){
            declare_var($2,buffer,"Array",true,NULL,false);
            $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("ExplicitType",$1,NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $5, expr, $2, $1);
             yyerror(error_msg);
             exit(1);
            }
         }
         | types TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE list_item_list  RSQUARE {
           if(strcmp(determineArrayType($8),$1)== 0){  
            char buffer[2048];
           sprintf(buffer, "[%s]", $8);
           declare_var($2,buffer,"Array",true,NULL,false);
           $$ = create_node("VariableDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",create_node("ExplicitType",$1,NULL,NULL),create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
           longitud = 1;
           }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $8, determineArrayType($8), $2, $1);
             yyerror(error_msg);
             exit(1);
           }
         }
         | types TEXT LSQUARE NUMBER RSQUARE {
           if(strcmp($1,$1)== 0){  
           declare_var($2,NULL,"Array",true,NULL,false);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",create_node("ExplicitType",$1,NULL,NULL),create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           }
         }
         | types TEXT EQUAL SQUARES_L_R {
           if(strcmp($1,$1)== 0){
           declare_var($2,NULL,"Array",true,NULL,false);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",NULL,create_node("ExplicitType",$1,NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           }
         }
         ;
array_const_decl: CONST TEXT EQUAL LSQUARE list_item_list  RSQUARE {
          char buffer[2048];
           sprintf(buffer, "[%s]", $5);
           declare_var($2,buffer,"Array",false,NULL,true);
           $$ = create_node("ConstantDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
           longitud = 1;
           printf("%s\n",buffer);
          }
          | CONST TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE list_item_list  RSQUARE {
            char buffer[2048];
          sprintf(buffer, "[%s]", $8);
            declare_var($2,buffer,"Array",false,NULL,true);
            $$ = create_node("ConstantDeclaration", $2, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
         }
         | CONST TEXT EQUAL SQUARES_L_R{
          // if(strcmp($2,$2)== 0){
           declare_var($2,NULL,"Array",false,NULL,true);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           //}
         }
         | CONST TEXT LSQUARE NUMBER RSQUARE {
         //  if(strcmp($1,$1)== 0){  
           declare_var($2,NULL,"Array",false,NULL,true);
           $$ = create_node("VariableDeclaration", $2, create_node("Value","[]", create_node("Type","Array",NULL,create_node("Limit",to_string($4),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
          // }
         }

         | CONST types TEXT EQUAL LSQUARE list_item_list  RSQUARE {
            char buffer[2048];
          sprintf(buffer, "[%s]", $6);
           printf("types es: %s\n",determineArrayType($6));
           if(strcmp(determineArrayType($6),$2)== 0){
            declare_var($3,buffer,"Array",true,NULL,true);
            $$ = create_node("ConstantDeclaration", $3, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,create_node("ExplicitType",$2,NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
            longitud = 1;
            }else{
                char error_msg[512];
                sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $6, determineArrayType($6), $3, $2);
                yyerror(error_msg);
                exit(1);
            }
         }
         | CONST types TEXT LSQUARE NUMBER RSQUARE EQUAL LSQUARE list_item_list  RSQUARE {
           if(strcmp(determineArrayType($9),$2)== 0){  
            char buffer[2048];
           sprintf(buffer, "[%s]", $9);
           declare_var($3,buffer,"Array",true,NULL,true);
           $$ = create_node("ConstantDeclaration", $3, create_node("Value",strdup(buffer), create_node("Type","Array",create_node("ExplicitType",$2,NULL,NULL),create_node("Limit",to_string($5),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
           longitud = 1;
           }else{
             char error_msg[512];
             sprintf(error_msg, "Error de Tipo en linea %d: No se puede asignar un valor '%s' de tipo '%s' a la variable '%s' que fue declarada como '%s'.", yylineno, $9, determineArrayType($9), $3, $2);
             yyerror(error_msg);
             exit(1);
           }
         }
         | CONST types TEXT LSQUARE NUMBER RSQUARE {
           if(strcmp($2,$2)== 0){  
           declare_var($3,NULL,"Array",true,NULL,true);
           $$ = create_node("ConstantDeclaration", $3, create_node("Value","[]", create_node("Type","Array",create_node("ExplicitType",$2,NULL,NULL),create_node("Limit",to_string($5),NULL,NULL)),create_node("Dinamic","False",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           }
         }
         | CONST types TEXT EQUAL SQUARES_L_R {
           if(strcmp($2,$2)== 0){
           declare_var($3,NULL,"Array",true,NULL,true);
           $$ = create_node("ConstantDeclaration", $3, create_node("Value","[]", create_node("Type","Array",NULL,create_node("ExplicitType",$2,NULL,NULL)),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
           longitud = 0;
           }
         }

array_assing: TEXT EQUAL SQUARES_L_R {
             //char * expr = determine_type($3);
             char* node_type = "VariableAsignement";
            if (is_current_func_param($1)) {
                node_type = "ParameterAsignement";
            }
             $$ = create_node(node_type, $1, create_node("Value","[]", create_node("Type","Array",NULL ,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(0),NULL,NULL)); generate_ast_file($$);
             longitud = 0;
              reassign_var_with_type($1, "[]", "Array");
            }
            | TEXT EQUAL LSQUARE list_item_list RSQUARE {
             //if(strcmp(determineArrayType($4),$1)== 0){
             char* node_type = "VariableAsignement";
             if (is_current_func_param($1)) {
                node_type = "ParameterAsignement";
             }
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
                $$ = create_node(node_type, $1, create_node("Value",strdup(buffer), create_node("Type","Array",NULL,NULL),create_node("Dinamic","True",NULL,NULL)), create_node("Longitud",to_string(longitud),NULL,NULL)); generate_ast_file($$);
                longitud = 1; 
             // } 
            }       
            ;
list_item: expr { $$ = $1; } // Un elemento puede ser una expresión normal (1, "hola", x)
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
        $$ = create_node("CallExpression", "read", create_node("Arguments", $3, NULL, create_node("Type",determine_type(get_var($3)),NULL,NULL)), NULL); generate_ast_file($$); 
         
    }
    | READ '(' TEXT ')' DOTYPEINT {
    //$$ = create_node("CallExpression", "ReadTypeInt", read_node, create_node("TypeConversion", "Int", NULL, NULL));generate_ast_file($$);
      $$ = create_node("CallExpression", "read", create_node("Arguments", $3, NULL, create_node("ParamType", "Int", NULL, create_node("Type",determine_type(get_var($3)),NULL,NULL))), NULL); generate_ast_file($$); 
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
                     } else if (strcmp(func->return_type, "inferred") != 0) {
                         // Solo validar tipos para funciones con tipo explícito
                         // y solo cuando el return es un LITERAL (no variable/expresión)
                         
                         // Función para detectar si es un literal puro (sin variables)
                         int is_pure_literal = is_pure_literal_expression($2);
                         
                         if (is_pure_literal) {
                             // Si es literal, podemos validar el tipo
                             char* actual_type = determine_type($2);
                             
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
                         int is_pure_literal = is_pure_literal_expression($2);
                         if (is_pure_literal) {
                             char* actual_type = determine_type($2);
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
                     func->return_value = strdup($2);
                 }
             } else {
                 yyerror("Error: 'return' used outside of a function."); 
                 exit(1);
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
     declare_var($3,$4,"int",false, NULL,false); 
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
         declare_var($3,$4,"int",false,NULL,false); 
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
           $$ = create_node("WhileLoop",result,create_node("ConditionIs",comparison_str,NULL,NULL),$5); generate_ast_file($$);
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
          
if_condition: IF '(' condition ')' block %prec IFX {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("if_Condition", comparison_str, NULL, $5);
        generate_ast_file($$);
        free(comparison_str);
    }
    | IF '(' condition ')' COLON block %prec IFX {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("if_Condition", comparison_str, NULL, $6);
        generate_ast_file($$);
        free(comparison_str);
    }
    | IF '(' condition ')' block condtional_stmt %prec IFX {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("if_Condition", comparison_str, $5, $6);
        generate_ast_file($$);
        free(comparison_str);
    }
    | IF '(' condition ')' COLON block condtional_stmt %prec IFX {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("if_Condition", comparison_str, $6, $7);
        generate_ast_file($$);
        free(comparison_str);
    }
    ;

            ;

condtional_stmt:ELSE_IF '(' condition ')' block {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("ElseIf", comparison_str, $5, NULL);
    }
    | ELSE_IF '(' condition ')' COLON block {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("ElseIf", comparison_str, $6, NULL);
    }
    | ELSE_IF '(' condition ')' block condtional_stmt {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("ElseIf", comparison_str, $5, $6);
    }
    | ELSE_IF '(' condition ')' COLON block condtional_stmt {
        char *comparison_str = strdup($3);
        char *result = strchr(comparison_str, ',');
        if (result != NULL) {
            *result = '\0';
            result++;
        }
        $$ = create_node("ElseIf", comparison_str, $6, $7);
    }
    | ELSE block {
        $$ = create_node("Else", NULL, $2, NULL);
    }
    | ELSE COLON block {
        $$ = create_node("Else", NULL, $3, NULL);
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
               add_or_find_function($2, "inferred");
               $<sval>$ = current_function_name;
               current_function_name = $2;
                FunctionSymbol* func = lookup_function(current_function_name);
                 parse_and_store_parameters(func, $4);
             } block {   
             //  enter_scope();
             
               FunctionSymbol* func = lookup_function(current_function_name);
               //parse_and_store_parameters(func, $4);
               
               // YA NO declaramos en la tabla de símbolos normal
               // Los parámetros están en global_params_list
               
               if (func && strcmp(func->return_type, "inferred") == 0) {
                 free(func->return_type);
                 func->return_type = "void";
               }
               char* formatted_params = format_parameters_as_string($2);
               $$ = create_node("Function", $2, create_node("Parameters", formatted_params, NULL, NULL), $7);
               generate_ast_file($$);
               current_function_name = $<sval>6;
               
               // Limpiar parámetros al salir de la función
              // clear_function_parameters($2);
              // exit_scope();
             }
                
             | FUNC TEXT '('parameter_list')' {
               add_or_find_function($2, "inferred");
               $<sval>$ = current_function_name;
               current_function_name = $2;
               FunctionSymbol* func = lookup_function(current_function_name);
               parse_and_store_parameters(func, $4);
             } block {
               enter_scope();
               FunctionSymbol* func = lookup_function(current_function_name);
        
               if (func && strcmp(func->return_type, "inferred") == 0) {
               free(func->return_type);
               func->return_type = "void";
               }
              char* formatted_params = format_parameters_as_string($2);
              $$ = create_node("Function", $2, create_node("Parameters", formatted_params, NULL, NULL), $7);
              generate_ast_file($$);
        
              clear_function_parameters($2);
              current_function_name = $<sval>6;
              exit_scope();
             }
                 
             | types FUNCTION TEXT '('parameter_list')' {
                // Misma lógica de contexto para funciones con tipo explícito.
                $<sval>$ = current_function_name;
                current_function_name = $3;
                add_or_find_function($3, $1);
                FunctionSymbol* func = lookup_function($3);
                parse_and_store_parameters(func, $5)
               } block {
                enter_scope();
                FunctionSymbol* func = lookup_function($3);
                 
                char* formatted_params = format_parameters_as_string($3);
                $$ = create_node("Function", $3, create_node("Parameters", formatted_params, NULL, create_node("ExplicitType", $1, NULL, NULL)), $8);
                generate_ast_file($$);
        
                clear_function_parameters($3);
                current_function_name = $<sval>7;
                exit_scope();
             }
             | types FUNC TEXT '('parameter_list')' {
                $<sval>$ = current_function_name;
                current_function_name = $3;
                add_or_find_function($3, $1);
                FunctionSymbol* func = lookup_function($3);
                parse_and_store_parameters(func, $5);
               printf("Function: %d\n", lookup_function($3)->return_value);
            } block {
                enter_scope();
                FunctionSymbol* func = lookup_function($3);      
                char* formatted_params = format_parameters_as_string($3);
                $$ = create_node("Function", $3, create_node("Parameters", $5, NULL, create_node("ExplicitType", $1, NULL, NULL)), $8);
                generate_ast_file($$);
          
                clear_function_parameters($3);
                current_function_name = $<sval>7;
                exit_scope();
             }
             | FUNCTION TEXT PARENS {
               // Función sin parámetros
               add_or_find_function($2, "inferred");
               $<sval>$ = current_function_name;
               current_function_name = $2;
                FunctionSymbol* func = lookup_function(current_function_name);
                parse_and_store_parameters(func, ""); // String vacío = sin parámetros
            } block {   
             FunctionSymbol* func = lookup_function($2);
        if (func && strcmp(func->return_type, "inferred") == 0) {
            free(func->return_type);
            func->return_type = strdup("void");
        }

        $$ = create_node("Function", $2, create_node("Parameters", "", NULL, NULL), $5);
        generate_ast_file($$);

        current_function_name = $<sval>4;
             }
             | FUNC TEXT PARENS {
                add_or_find_function($2, "inferred");
                $<sval>$ = current_function_name;
                current_function_name = $2;
              
             } block {
               enter_scope();
               FunctionSymbol* func = lookup_function(current_function_name);
               parse_and_store_parameters(func, ""); // Sin parámetros
        
                if (func && strcmp(func->return_type, "inferred") == 0) {
                free(func->return_type);
                func->return_type = "void";
                }
        
               $$ = create_node("Function", $2, create_node("Parameters", "", NULL, NULL), $5);
               generate_ast_file($$);
        
              clear_function_parameters($2);
              current_function_name = $<sval>4;
              exit_scope();
             }
             | types FUNCTION TEXT PARENS {
               // Función con tipo explícito sin parámetros
               $<sval>$ = current_function_name;
               current_function_name = $3;
               add_or_find_function($3, $1);
             } block {
                enter_scope();
                FunctionSymbol* func = lookup_function($3);
                parse_and_store_parameters(func, ""); // Sin parámetros
        
                $$ = create_node("Function", $3, create_node("Parameters", "", NULL, create_node("ExplicitType", $1, NULL, NULL)), $6);
                generate_ast_file($$);
        
                clear_function_parameters($3);
                current_function_name = $<sval>5;
                exit_scope();
             }
                
             | types FUNC TEXT PARENS {
              $<sval>$ = current_function_name;
              current_function_name = $3;
              add_or_find_function($3, $1);
             } block {
              enter_scope();
              FunctionSymbol* func = lookup_function($3);
              parse_and_store_parameters(func, ""); // Sin parámetros
        
              $$ = create_node("Function", $3, create_node("Parameters", "", NULL, create_node("ExplicitType", $1, NULL, NULL)), $6);
              generate_ast_file($$);
        
              clear_function_parameters($3);
              current_function_name = $<sval>5;
               exit_scope();
              }
             
            ;
function_call: TEXT PARENS { 
                validate_function_call($1, "");
              $$ = create_node("FunctionCall",$1,create_node("Paramenters",NULL,NULL,NULL),NULL); generate_ast_file($$)
             }  
             | TEXT '('argument_list')' {
                validate_function_call($1, $3);
                assign_arguments_to_parameters($1, $3);
                printf("parameters: %s\n", $3);
              $$ = create_node("FunctionCall",$1,create_node("Paramenters",add_quotes($3),NULL,NULL),NULL); generate_ast_file($$)
             }
            ;                
parameter_list: param_decl { $$ = $1; }
              | parameter_list COM param_decl  {$$ = concat_strings($1,concat_strings(",",concat_strings(" ", $3))); }
              ;
param_decl: types TEXT { $$ = concat_strings($1,concat_strings(" ",$2)); printf("param_decl: %s\n", $$); }
          | TEXT { $$ = $1; }
          ;

 
    
argument_list: expr { 
                 // Buscar la función del contexto anterior ($<sval>0 es el TEXT de function_call)
                char* func_name = $<sval>0;
                 FunctionSymbol* func = lookup_function(func_name);
                
                 if (func && func->param_list) {
                    char buffer[2048];
                    sprintf(buffer, "%s: %s", func->param_list->name, $1);
                    $$ = strdup(buffer);
                 } else {
                    $$ = $1;
                 }; 

                }
            | argument_list COM expr { 
                //$$ = concat_strings($1,concat_strings(",",concat_strings(" ",$3))); 
                 char* func_name = $<sval>0;
                 FunctionSymbol* func = lookup_function(func_name);
                
                 if (func) {
                    // Contar cuántos parámetros llevamos
                    int current_index = 0;
                    char* temp = strdup($1);
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
                        sprintf(buffer, "%s, %s: %s", $1, param->name, $3);
                        $$ = strdup(buffer);
                        
                    } 
                 } else {
                    //$$ = concat_strings($1, concat_strings(", ", $3));
                 }
                } 
            ;
types: TINT { $$ = "int"; }
    | TFLOAT { $$ = "float"; }
    | TSTRING { $$ = "string"; }
    | TBOOL { $$ = "bool"; }
    | TVOID { $$ = "void"; }
     ; 



// Para variables
variable_conversion: variable DOTYPEINT {
    char* var_name = $1;
        symbol* s = find_variable(var_name);
        if (!s) {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: La variable '%s' no ha sido declarada.", yylineno, var_name);
            yyerror(error_msg);
            exit(1);
        }
        
        // Convertir el valor de la variable
        char* converted_value = convert_to_int($1);
        if (converted_value == NULL) {
            char error_msg[256];
            sprintf(error_msg, "Error semantico en linea %d: No se puede convertir '%s' de tipo '%s' a int.", yylineno, s->value, s->type);
            yyerror(error_msg);
            exit(1);
        }
        
        $$ = converted_value; // Devuelve el valor convertido
        //eassign_var($1, converted_value, NULL); 
}
;

// Para read

;        
statements: statements statement {   
               ast_node* list = $1;
              // Navega hasta el final de la lista de sentencias (hermanos)
              while (list->right != NULL) {
                  list = list->right;
              }
              // Enlaza la nueva sentencia como el siguiente hermano
              list->right = $2;
              $$ = $1; // Devuelve el inicio de la lista
         }
         | statement {$$ = $1}
    ;  
variable: TEXT {   
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

         $$ = $1;       
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
     | variable_conversion
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
key_value_pair: STRING COLON list_item {
    char buffer[1024];
    sprintf(buffer, "%s:%s", add_quotes($1), $3);
    $$ = strdup(buffer);
}  
arith_expr: paren_left expr paren_right {  $$ = $2; }
          | expr PLUS expr  {         
            concat_op = op_concat($1,'+',$3);
            if (is_current_func_param($1) || is_current_func_param($3) || is_runtime_access_string($1) || is_runtime_access_string($3) ) {
                $$ = concat_op; 
                valid = 0; // Invalidamos para que rules superiores no intenten parsearlo como número
            }else{
            valid = valid_expression(concat_op);
            char* val1 = get_var($1) ? get_var($1) : $1;
            char* val2 = get_var($3) ? get_var($3) : $3;

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
             $$ = do_op_float(val1,'+',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             $$ = do_op(val1,'+',val2);
            }/*else if(strcmp(expr1, "string") == 0 || strcmp(expr2, "string") == 0){
              $$ = op_concat(val1, '+', val2);

            }*/else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '+' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
         //   exit(1); // Detener el análisis
             
            }
         }
         
        }
          | expr MINUS expr { 
            concat_op = op_concat($1,'-',$3);
            if (is_current_func_param($1) || is_current_func_param($3) || is_runtime_access_string($1) || is_runtime_access_string($3)) {
                $$ = concat_op; 
                valid = 0; 
            }else{
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
             $$ = do_op_float(val1,'-',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
             $$ = do_op(val1,'-',val2);
              }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '-' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
          //   exit(1); // Detener el análisis
             }
            }
          }
          }

          | expr TIMES expr {

            concat_op = op_concat($1,'*',$3);
           if (is_current_func_param($1) || is_current_func_param($3) || is_runtime_access_string($1) || is_runtime_access_string($3)) {
                $$ = concat_op; 
                valid = 0; 
            }else{
            valid = valid_expression(concat_op);
            char* val1 = get_var($1) ? get_var($1) : $1;
            char* val2 = get_var($3) ? get_var($3) : $3;
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
             $$ = do_op_float(val1,'*',val2);
            }else if(strcmp(expr1, "int") == 0 && strcmp(expr2, "int") == 0){
              printf("do_op: %s\n", do_op(val1,'*',val2));
             $$ = do_op(val1,'*',val2);
              
            }else if(strcmp(expr1, "string") == 0 && strcmp(expr2, "string") == 0){
              $$ = do_op(val1, '*', val2);

            }else{
             char error_msg[256];
             sprintf(error_msg, "Error semantico en linea %d: La operacion '*' no esta soportada entre los tipos '%s' y '%s'.", yylineno, expr1, expr1);
             yyerror(error_msg);
           //  exit(1); // Detener el análisis
          //  }
             }
            } 
           }
          | expr DIVIDE expr { 
            concat_op = op_concat($1,'/',$3);
            if (is_current_func_param($1) || is_current_func_param($3) || is_runtime_access_string($1) || is_runtime_access_string($3)) {
                $$ = concat_op; 
                valid = 0; 
            }else{ 
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
          //   exit(1); // Detener el análisis
              }
             }
             }
            }
             | expr MOD expr {
                concat_op = op_concat($1, '%', $3);
                if (is_current_func_param($1) || is_current_func_param($3) || is_runtime_access_string($1) || is_runtime_access_string($3)) {
                $$ = concat_op; 
                valid = 0; 
            }else{
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
                    sprintf(error_msg, "Error semantico en linea %d: La operacion '%%' solo esta soportada entre enteros (int), no entre '%s' y '%s'.", yylineno, type1, type2);
                    yyerror(error_msg);
               //     exit(1); // Terminar el análisis si hay un error
                   // $$ = "0"; // Valor por defecto para que no se rompa el parser
                }
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
       expression_op[expression_num].op = strdup($$);
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    }
    | STRING { $$ = add_quotes($1);}
    | DECIMAL { $$ = floatToString($1); 
        expression_op[expression_num].op = strdup($$);
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    } 
     | variable LSQUARE array_indexer RSQUARE {
          // 1. Llamamos a nuestra nueva función orquestadora
    $$ = legacy_access_collection_element($1, $3);
    // printf("access_collection_element result: %s\n", legacy_access_collection_element($1, $3));
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
       // $$ = add_quotes(removeParentheses($1));
        }
    | variable {
        expression_op[expression_num].op = strdup($$);
        expression_op[expression_num].num = 0; // 0 = Operando
        expression_num++;
    }
    | bool

    | TEXT '('argument_list')' { 
      FunctionSymbol* func = lookup_function($1);
              //validate_function_call($1, $3);
              char* func_call_str;
        if ($3 && strlen($3) > 0) {
            // Hay argumentos: "funcion(arg1, arg2)"
            size_t len = strlen($1) + strlen($3) + 4; // +4 para "()" y null terminator
            func_call_str = malloc(len);
            sprintf(func_call_str, "%s(%s)", $1, $3);
        } else {
            // Sin argumentos: "funcion()"
            size_t len = strlen($1) + 3; // +3 para "()" y null terminator
            func_call_str = malloc(len);
            sprintf(func_call_str, "%s()", $1);
        }
        $$ = func_call_str;
              printf("parameters: %s\n", $3);
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
         | bool
         /*| NOT condition { 
            char *temp_str = concatenateComparison("!", $2, ""); 
            $$ = concatenateComparison("",",",temp_str);
          }*/
         
         | condition logicals condition { 
             // Concatenamos las comparaciones y resultados
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
comparison:  expr EQUALC expr {    
            comparison = concatenateComparison($1,"==", $3);           
             if(strcmp($1, $3) == 0){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); } 
          }
          | expr UNEQUAL expr {
            comparison = concatenateComparison($1,"!=", $3);
            if(strcmp($1, $3) == 0){ $$ = concatenateComparison("False",",",comparison); }else{ $$ = concatenateComparison("True",",",comparison); }
             
          }
          | expr GREATERTHAN expr {
             comparison = concatenateComparison($1,">", $3);
            if(atoi($1) > atoi($3)){ $$ = concatenateComparison("True",",",comparison);}else{ $$ = concatenateComparison("False",",",comparison); }
          }
          | expr LESSTHAN expr {
             comparison = concatenateComparison($1,"<", $3);
            if(atoi($1)  < atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }
          } 
          | expr GREATERTHAN_EQUAL expr {
            comparison = concatenateComparison($1,">=", $3);
            if(atoi($1)  >= atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }      
          }
          | expr LESSTHAN_EQUAL expr {
            comparison = concatenateComparison($1,"<=", $3);
            if(atoi($1)  <= atoi($3)){ $$ = concatenateComparison("True",",",comparison); }else{ $$ = concatenateComparison("False",",",comparison); }            
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