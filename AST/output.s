section .data
    x db 0
    z db 0
    concat db "esto
    nombre db "Robert"
    sum db 6
    d db 5
    bool db True
    b db 7.40
    numero db 0
    range db 1..5
    arr db 1,2,3,4
    ars db 1,2,3
    msg1 db "esto", 0
    msg2 db "hola", 0
    msg3 db "el", 0
    msg4 db "se", 0
    msg5 db "relleno", 0
    inter db 0
    msg6 db "i", 0
    msg7 db "ejecutas", 0
    number1 db 24
    lt db 0
    tp db 0
    fb db 0
    pb db 0
    msg8 db "print", 0
    num_format db '%d', 10, 0
    str_format db '%s', 10, 0
    success_msg db 'Compilation successfully', 10, 0
    time_msg db 'Execution time: %d milliseconds', 10, 0
    start_time dd 0

section .text
    global _main
    extern _printf, _clock, _getchar

_main:
    call _clock
    mov dword [start_time], eax
    push msg1
    push str_format
    call _printf
    add esp, 8
    push 3
    push num_format
    call _printf
    add esp, 8
    push msg2
    push str_format
    call _printf
    add esp, 8
    mov al, [sum]
    movzx eax, al
    push eax
    push num_format
    call _printf
    add esp, 8
    push 2
    push num_format
    call _printf
    add esp, 8
    push msg3
    push str_format
    call _printf
    add esp, 8
    push msg4
    push str_format
    call _printf
    add esp, 8
    mov al, [b]
    movzx eax, al
    push eax
    push num_format
    call _printf
    add esp, 8
    push msg5
    push str_format
    call _printf
    add esp, 8
    mov al, [inter]
    movzx eax, al
    push eax
    push num_format
    call _printf
    add esp, 8
    push msg6
    push str_format
    call _printf
    add esp, 8
    push msg7
    push str_format
    call _printf
    add esp, 8
    mov al, [number1]
    movzx eax, al
    push eax
    push num_format
    call _printf
    add esp, 8
    mov al, [number1]
    movzx eax, al
    push eax
    push num_format
    call _printf
    add esp, 8
    push msg8
    push str_format
    call _printf
    add esp, 8
    push success_msg
    push str_format
    call _printf
    add esp, 8
    call _clock
    sub eax, [start_time]
    push eax
    push time_msg
    call _printf
    add esp, 8
    call _getchar

    ret