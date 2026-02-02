
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

/* Line 1676 of yacc.c  */
#line 2126 "semantic.y"

    int ival;
    char *sval;
    char **arrval;
    float fval;
    struct ast_node* node;



/* Line 1676 of yacc.c  */
#line 138 "semantic.tab.h"
} YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define yystype YYSTYPE /* obsolescent; will be withdrawn */
# define YYSTYPE_IS_DECLARED 1
#endif

extern YYSTYPE yylval;


