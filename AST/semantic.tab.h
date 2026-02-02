
/* A Bison parser, made by GNU Bison 2.4.1.  */

/* Skeleton interface for Bison's Yacc-like parsers in C
   
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

/* Line 1676 of yacc.c  */
#line 2992 "semantic.y"

    int ival;
    char *sval;
    char **arrval;
    float fval;
    struct ast_node* node;



/* Line 1676 of yacc.c  */
#line 142 "semantic.tab.h"
} YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define yystype YYSTYPE /* obsolescent; will be withdrawn */
# define YYSTYPE_IS_DECLARED 1
#endif

extern YYSTYPE yylval;


