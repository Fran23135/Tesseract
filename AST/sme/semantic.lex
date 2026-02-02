%{
#include "semantic.tab.h"   
#include <string.h>
extern char *removeQuotes(char* str);
//   /-?[0-9]+(\.[0-9]+)? { yylval.dval = atoi(yytext); return decimal; }
extern char* get_var(char *name);
extern char* removeParentheses(char* str);
extern void yyerror(const char *s);

int indent_level = 0;
int indent_stack[100];
int stack_top = 0;
int pending_dedent = 0;
int current_indent_type = 0;
extern int use_indent;
static int dedent_queue = 0;
/*void process_string(const char *input) {
    char result[512]; // Buffer para el resultado
    char var_name[128];
    char *var_value;
    int i, j = 0;

    int len = strlen(input);

    // Quitar comillas inicial y final si existen
    if (len > 1 && input[0] == '"' && input[len - 1] == '"') {
        input++;
        len -= 2;
    }

    for (i = 0; i < len; i++) {
        // Si encuentra #(
        if (input[i] == '#' && input[i + 1] == '(') {
            i += 2; // Saltar #(
            int k = 0;

            // Extraer el nombre de la variable (mínimo una letra)
            if ((input[i] >= 'a' && input[i] <= 'z') || (input[i] >= 'A' && input[i] <= 'Z')) {
                while (input[i] != ')' && k < sizeof(var_name) - 1) {
                    var_name[k++] = input[i++];
                }
                var_name[k] = '\0';

                // Obtener el valor usando get_var()
                var_value = get_var(var_name);

                if (var_value) {
                    // Concatenar el valor en el resultado
                    j += sprintf(&result[j], "%s", var_value);
                }
            }
        } else {
            // Copiar el carácter al resultado
            result[j++] = input[i];
        }
    }

    result[j] = '\0';

    // Asignar el resultado formateado a yylval.sval
    yylval.sval = strdup(result);
}*/
%}
%x COMMENT
%option yylineno
%%
 {

    if (dedent_queue > 0) {
        dedent_queue--;
        return DEDENT;
    }
 }
<<EOF>>   {
              // Al final del archivo, si todavía estamos indentados,
              // emitimos todos los DEDENTs necesarios para cerrar los bloques.
               if (dedent_queue > 0) {
               dedent_queue--;
               return DEDENT;
              }             
              if (use_indent && indent_level > 0) {
                  indent_level = 0; // Forzar el regreso al nivel 0
                  dedent_queue = stack_top; // Poner todos los niveles en la cola
                  stack_top = 0;
                  // Devolvemos el primer DEDENT, el resto se manejará en yylex()
                  if (dedent_queue > 0) {
                      dedent_queue--;
                      return DEDENT;
                  }
              }
              return 0; // Retorna 0 para indicar el fin de archivo (EOF)
          }


\n[ \t]*  {
          /*  if (use_indent) {
            return NEWLINE;
             }*/
             
                 // Reiniciar el nivel de indentación
                if (use_indent) {
                    int new_level = 0;
                    
                     //new_level = 0; 
                    for (int i = 0; i < yyleng; i++) {
                        if (yytext[i] == ' ') new_level++;
                        else if (yytext[i] == '\t') new_level += 4; // o el tamaño de tu tab
                         
                        
                        printf("Nivel de indentacion detectado: %d\n", indent_level);
                     
                    }
                    
                    
                    if (new_level > indent_level) {
                        // INDENT: Aumentó el nivel de indentación
                        indent_stack[stack_top++] = indent_level;
                        indent_level = new_level;
                        return INDENT;
                         
                    } else if (new_level < indent_level) {
                        // DEDENT: Disminuyó el nivel de indentación
                        // Calculamos cuántos DEDENTs necesitamos emitir
                        while (new_level < indent_level) {
                           printf("Nivel de indentacion actual: %d, nuevo nivel: %d\n", indent_level, new_level);
                            if (stack_top > 0) {
                                indent_level = indent_stack[--stack_top];
                                dedent_queue++;
                            } else {
                                yyerror("Error de des-indentacion inconsistente.");
                                exit(1);
                            }
                        }
                        if (new_level != indent_level) {
                           yyerror("Error de indentacion: nivel invalido.");
                           exit(1);
                        }
                        // Devolvemos el primer DEDENT, el resto queda en la cola
                        if (dedent_queue > 0) {
                           dedent_queue--;
                           return DEDENT;
                        }
                        return NEWLINE; // Retornamos NEWLINE para indicar un cambio de línea
                    }
                       
                } 
                // Si use_indent es falso, simplemente ignoramos los espacios.
                
            }


"//"[^\n]* ;
"/*"           { BEGIN(COMMENT); }   // 1. Al encontrar "/*", entra en el estado COMMENT.

<COMMENT>"*/" { BEGIN(INITIAL); }   // 2. Dentro de COMMENT, si encuentra "*/", vuelve al estado normal (INITIAL).
<COMMENT>.|\n  ;      
"["         { return LSQUARE;}
"("         { return '('; }
")"         { return ')'; }
"()"        { return PARENS; } 
"for"       { return FOR; }
"in"        { return IN; }
">"         { return GREATERTHAN; }
"<"         { return LESSTHAN; }
"=="        { return EQUALC; } 
"!="        { return UNEQUAL; }
">="        { return GREATERTHAN_EQUAL; }
"<="        { return LESSTHAN_EQUAL; }
".."        { return RANGE;}
"..<"       { return RANGE_SEMI_OPEN; }
"||"        { return OR;}
"&&"        { return AND;}
"]"         { return RSQUARE;}
"[]"        { return SQUARES_L_R;}
"print"     { return PRINT; }
"var"       { return VAR; }
"read"      { return READ; }
"+"         { return PLUS; }
"-"         { return MINUS; }
"*"         { return TIMES; }
"/"         { return DIVIDE; }
"%"         { return MOD; }
"="         { return EQUAL; }
"++"        { return INCREMENT; }
"--"        { return DECREMENT; }
";"         { return SEMICOLON; }
"{"         { return startRace; } 
"}"         { return endRace; }
"."         { return DOT; }
","         { return COM; }
":"         { return COLON; }
"?"         { return QUESTION_MARK; }
"#"         { return SHARP; }
"import"    { return IM; }
"import Math" { return IM_Math; }
"PI"        { return PI; }
"function"  { return FUNCTION; }
"struct"    { return STRUCT; }
"func"      { return FUNC; }
"string"    { return TSTRING; }
"int"       { return TINT; }
"float"     { return TFLOAT; }
"bool"      { return TBOOL; }
"void"      { return TVOID; }
"Equation"  { return EQUATION; }
"while"     { return WHILE;}
"perform"   { return PERFORM; }
"if"        {return IF;}
"else"      {return ELSE;}
"else if"   {return ELSE_IF;} 
"switch"    { return SWITCH; }
"case"      { return CASE; }
"default"   { return DEFAULT; }
"break"     {return BREAK;} 
"return"    {return RETURN;} 
".Insert(" { return INSERTVALUE; }
"main"          { return MAIN; }
"True"          { return TRUE; }
"False"         { return FALSE; }
".type"         { return DOTYPE; }
".append("      { return APPEND; }
".lenght"       { return LENGHT; }

[0-9]+\.[0-9]+ { yylval.fval = atof(yytext); return DECIMAL; }
[0-9]+      { yylval.ival = atoi(yytext); return NUMBER; }


\"[^\"]*#\([a-zA-Z][^)]*\)[^\"]*\" {
               //  process_string(removeQuotes(yytext));
                 yylval.sval = strdup(yytext); // Pasamos el string completo, con comillas
                 return STRING_WITH_VARS;
} 
\"[^\"]*\"|\'[^\']*\'  { yylval.sval = strdup(yytext + 1);
              yylval.sval[strlen(yylval.sval)-1] = '\0';
              return STRING;       
              }



[a-zA-Z][a-zA-Z0-9]*   { yylval.sval = strdup(yytext);
                         return TEXT; }

[ \t\n\r]     /* ignore whitespace */

.         { fprintf(stderr, "Error Léxico: Carácter inesperado '%s' en la línea %d\n", yytext, yylineno); }  /* ignore everything else */



%%

int yywrap() {
   return 1;
}
