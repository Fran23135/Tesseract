%{
#include "parser.tab.h"
#include <stdio.h>
#include <stdlib.h>

%}

%%
"="               {return ASSIGN;}
"print"           {return PRINT;}
";"               {return SEMICOLON;}
   [a-zA-Z][a-zA-Z0-9]*   { yylval.str = strdup(yytext); return ID; }            
[0-9]+            { yylval.num = atoi(yytext); return NUM; }
[ \t\n]+                            /* Ignorar espacios y tabs */
. 
%%

int yywrap() {
    return 1;
}
