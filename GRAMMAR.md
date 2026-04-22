# Lux Grammar (Draft)

PEG-style grammar. Not yet formal enough for parser generation, but precise enough to argue about.

## Notation

```
'literal'     exact string
UPPER         token class (from lexer)
lower         grammar rule
a b           sequence
a | b         ordered choice
a?            optional
a*            zero or more
a+            one or more
(a b)         grouping
```

## Lexical Grammar

### Keywords

```
fn let pub struct enum match if else return
inout sink contain import as type trait impl
for in while break continue true false
can test catch spawn
```

### Reserved (for future use)

```
async await yield effect handle with do
macro comptime where
```

### Tokens

```
IDENT       = [a-zA-Z_][a-zA-Z0-9_]*
INT         = [0-9][0-9_]*
FLOAT       = [0-9][0-9_]* '.' [0-9][0-9_]*
STRING      = '"' (interp | escape | [^"\\{])* '"'
interp      = '{' expr '}'
CHAR        = '\'' (escape | [^'\\]) '\''
escape      = '\\' [nrt\\'"0{]

COMMENT     = '//' [^\n]*
DOC_COMMENT = '///' [^\n]*
```

### Operators and Punctuation

```
+  -  *  /  %  ++
== != < > <= >=
&& || !
|> ? ??
= += -= *= /=
-> =>
. :: : ; ,
( ) [ ] { }
```

## Syntax Grammar

### Top Level

```
program     = item*
item        = fn_def | struct_def | enum_def | type_alias
            | import | trait_def | impl_block | test_def
```

### Imports

```
import      = 'import' path ('.' '{' ident_list '}')? ('as' IDENT)?
path        = IDENT ('.' IDENT)*
ident_list  = IDENT (',' IDENT)* ','?
```

### Functions

```
fn_def      = 'pub'? 'fn' IDENT generics? '(' params? ')' return_type? can_clause? block

params      = param (',' param)* ','?
param       = passing? IDENT ':' type
passing     = 'let' | 'inout' | 'sink'

return_type = '->' type
can_clause  = 'can' effect_list
effect_list = IDENT (',' IDENT)*

generics    = '<' generic_param (',' generic_param)* '>'
generic_param = IDENT (':' type_bound)?
type_bound  = IDENT ('+' IDENT)*
```

### Types

```
type        = type_name generics_args?
            | fn_type
            | tuple_type
            | '(' type ')'

type_name   = path
generics_args = '<' type (',' type)* '>'

fn_type     = 'fn' '(' type_list? ')' return_type? can_clause?
type_list   = type (',' type)*

tuple_type  = '(' type ',' type (',' type)* ')'
```

### Structs

```
struct_def  = 'pub'? 'struct' IDENT generics? '{' field_list? '}'
field_list  = field (',' field)* ','?
field       = 'pub'? IDENT ':' type
```

### Enums

```
enum_def    = 'pub'? 'enum' IDENT generics? '{' variant_list? '}'
variant_list = variant (',' variant)* ','?
variant     = IDENT variant_data?
variant_data = '(' type_list ')' | '{' field_list '}'
```

### Traits

```
trait_def   = 'pub'? 'trait' IDENT generics? '{' trait_item* '}'
trait_item  = fn_sig ';' | fn_def    // signature-only or default impl

fn_sig      = 'fn' IDENT generics? '(' params? ')' return_type? can_clause?

impl_block  = 'impl' generics? IDENT generics_args? 'for' type '{' fn_def* '}'
```

### Tests

```
test_def    = 'test' STRING can_clause? block
```

### Subscripts

```
subscript   = 'subscript' IDENT '[' params ']' '(' passing 'self' ':' type ')' return_type? block
```

### Statements

```
block       = '{' statement* expr? '}'

statement   = let_stmt
            | assign_stmt
            | expr_stmt
            | return_stmt
            | if_stmt
            | match_stmt
            | for_stmt
            | while_stmt
            | contain_stmt

let_stmt    = 'let' pattern (':' type)? '=' expr ';'
assign_stmt = place assign_op expr ';'
assign_op   = '=' | '+=' | '-=' | '*=' | '/='
expr_stmt   = expr ';'
return_stmt = 'return' expr? ';'
for_stmt    = 'for' pattern 'in' expr block
while_stmt  = 'while' expr block
```

### Expressions

```
expr        = pipeline

pipeline    = coalesce ('|>' pipeline_stage)*
pipeline_stage = IDENT ('(' args? ')')? '?'?
              | field_projection

coalesce    = logical_or ('??' (logical_or | block))?

logical_or  = logical_and ('||' logical_and)*
logical_and = comparison ('&&' comparison)*
comparison  = concat (comp_op concat)?
comp_op     = '==' | '!=' | '<' | '>' | '<=' | '>='

concat      = addition ('++' addition)*
addition    = multiplication (('+' | '-') multiplication)*
multiplication = unary (('*' | '/' | '%') unary)*

unary       = ('-' | '!') unary | postfix
postfix     = primary (call | index | field | try)*

call        = '(' args? ')'
index       = '[' expr ']'
field       = '.' IDENT
try         = '?'

primary     = INT | FLOAT | STRING | CHAR | 'true' | 'false'
            | IDENT
            | path
            | struct_literal
            | closure
            | field_projection
            | if_expr
            | match_expr
            | catch_expr
            | spawn_expr
            | block
            | '(' expr ')'

args        = arg (',' arg)* ','?
arg         = (IDENT ':')? expr

struct_literal = type_name '{' field_init_list? '}'
field_init_list = field_init (',' field_init)* ','?
field_init  = IDENT ':' expr | IDENT   // shorthand: name == value

closure     = '|' params? '|' expr
            | '|' params? '|' block

// .field in closure position: sugar for |it| it.field
// .field op .field in closure position: sugar for |it| it.field op it.field
field_projection = '.' IDENT (operator '.' IDENT)*
```

### Pattern Matching

```
if_expr     = 'if' expr block ('else' (if_expr | block))?

match_expr  = 'match' expr '{' match_arm+ '}'
match_arm   = pattern '=>' (expr ',') | (block)

pattern     = '_'
            | IDENT
            | literal_pattern
            | IDENT '(' pattern_list? ')'     // enum variant
            | IDENT '{' field_pattern_list? '}' // struct pattern
            | pattern '|' pattern              // or-pattern

pattern_list = pattern (',' pattern)*
field_pattern_list = field_pattern (',' field_pattern)*
field_pattern = IDENT ':' pattern | IDENT
```

### Error Handling

```
catch_expr  = 'catch' expr '{' catch_arm+ '}'
catch_arm   = 'Ok' '(' pattern ')' '=>' expr ','
            | 'Err' '(' pattern ')' '=>' expr ','
```

### Concurrency

```
spawn_expr  = 'spawn' expr
```

### Effect Containment

```
contain_stmt = 'contain' effect_list block
```

## Precedence (highest to lowest)

1. Field access (`.`), indexing (`[]`), function call (`()`)
2. Try (`?`)
3. Unary (`-`, `!`)
4. Multiplicative (`*`, `/`, `%`)
5. Additive (`+`, `-`)
6. String concatenation (`++`)
7. Comparison (`==`, `!=`, `<`, `>`, `<=`, `>=`)
8. Logical AND (`&&`)
9. Logical OR (`||`)
10. Nil coalescing (`??`)
11. Pipeline (`|>`)
12. Assignment (`=`, `+=`, etc.)

## Notes

- No semicolons after blocks (if/match/for/while/test that end with `}`)
- Trailing commas allowed everywhere
- The last expression in a block is the block's value (implicit return)
- `?` propagates Fail effects (early return on error/none)
- `??` provides a fallback for Option values
- `can` in function signatures declares effects; the compiler infers effects at call sites
- `++` for string concatenation, not `+` (strings are not numbers)
- String interpolation uses `{expr}` inside double-quoted strings
- `.field` in closure position is sugar for `|it| it.field`
- `test` blocks are top-level items, not functions (no `fn` keyword needed)
- `contain` absorbs effects: code inside can perform the listed effects, but the boundary is pure from outside
- `spawn` creates a concurrent task; requires `can Async` in the enclosing function
- Imports use `.` not `::` for path separators (reads as English: `import std.collections.Map`)
