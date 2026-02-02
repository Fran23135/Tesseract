%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct ast_node {
    char* type;
    char* value;
    struct ast_node* left;
    struct ast_node* right;
} ast_node;

ast_node* create_node(char* type, char* value, ast_node* left, ast_node* right);
void print_ast(ast_node* node, FILE* output, int level);
void generate_ast_file(ast_node* root);

%}

%union {
    char* str;
    int num;
    struct ast_node* node;
}

%token <str> ID
%token <num> NUM
%token PRINT ASSIGN SEMICOLON

%type <str> expression
%type <node> stmt 

%%

program:
    stmt_list
;

stmt_list:
    stmt_list stmt
    | stmt
;

stmt:
    ID ASSIGN expression SEMICOLON   { $$ = create_node("VariableDeclaration", $1, create_node("Value", $3, NULL, NULL), NULL); generate_ast_file($$); }
    | PRINT expression SEMICOLON     { $$ = create_node("CallExpression", "print", create_node("Arguments", $2, NULL, NULL), NULL); generate_ast_file($$); }
;

expression:
    ID                               { $$ = strdup($1); }
    | NUM                            { 
                                        char buffer[20]; 
                                        sprintf(buffer, "%d", $1); 
                                        $$ = strdup(buffer); 
                                      }
;

%%

ast_node* create_node(char* type, char* value, ast_node* left, ast_node* right) {
    ast_node* new_node = (ast_node*) malloc(sizeof(ast_node));
    new_node->type = strdup(type);
    new_node->value = value ? strdup(value) : NULL;
    new_node->left = left;
    new_node->right = right;
    return new_node;
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
    FILE* file = fopen("ast_output.txt", "a");
    if (file == NULL) {
        printf("Error: cannot open file ast_output.txt\n");
        return;
    }

    static int first_time = 1;
    if (first_time) {
        fprintf(file, "Program\n");
        first_time = 0;
    }

    print_ast(root, file, 1);  // Pasamos nivel 1 ya que "Program" es nivel 0
    fclose(file);
}

int main() {
    yyparse();
    return 0;
}

void yyerror(const char* s) {
    fprintf(stderr, "Error: %s\n", s);
}
