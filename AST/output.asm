section .data
    msg1 db 'hola', 10, 0             ; Mensaje "hola" con salto de línea
    msg2 db '%d', 10, 0                ; Formato para imprimir números con salto de línea
    x db 0                             ; Variable x inicializada
    z db 0                             ; Variable z inicializada

section .text
    global _main                       ; Punto de entrada
    extern _printf                     ; Declaración de printf

_main:
    mov byte [x], 3            ; Asigna 3 a x
    mov byte [z], 0            ; Asigna NULL a z
    push hola             ; Apila el mensaje 'hola'
    call _printf               ; Llama a printf
    add esp, 4                 ; Limpia la pila
    push 25             ; Apila el número 25
    push msg2                  ; Apila el formato
    call _printf               ; Llama a printf
    add esp, 8                 ; Limpia la pila
    mov al, [x]       ; Carga el valor de x en AL
    movzx eax, al               ; Extiende AL a EAX
    push eax                   ; Apila el valor de x
    push msg2                  ; Apila el formato
    call _printf               ; Llama a printf
    add esp, 8                 ; Limpia la pila
    mov al, [z]       ; Carga el valor de z en AL
    movzx eax, al               ; Extiende AL a EAX
    push eax                   ; Apila el valor de z
    push msg2                  ; Apila el formato
    call _printf               ; Llama a printf
    add esp, 8                 ; Limpia la pila
    ret
