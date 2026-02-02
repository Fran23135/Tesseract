section .data
    format db "%d", 0,10 ; formato para imprimir enteros

section .bss
    num resd 1  ; espacio para almacenar el número

section .text
    extern _printf, _getchar   ; función printf de la librería C estándar
    global _main     ; punto de entrada

_main:
    ; Inicializar el contador
    mov dword [num], 1

for_loop:
    ; Comparar si num <= 3
    mov eax, [num]
    cmp eax, 4
    jge end_loop  ; salir si num >= 4

    ; Imprimir el número
    push eax            ; poner el número en la pila
    push format         ; poner el formato en la pila
    call _printf        ; llamar a printf
    add esp, 8          ; limpiar la pila
    ; Incrementar el contador
    inc dword [num]
    jmp for_loop        ; repetir el ciclo
    
end_loop:
    ; Terminar el programa
    call _getchar
    ret
