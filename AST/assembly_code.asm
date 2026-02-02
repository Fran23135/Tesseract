section .data
    output db 'Value: ', 0
    x db 0
    z db 0

section .text
global _start
_start:
    mov al, 3
    mov [x], al
    mov al, NULL
    mov [z], al
    ; Imprimir el mensaje
    mov eax, 4
    mov ebx, 1
    mov ecx, output
    mov edx, 8
    int 0x80
    ; Imprimir el valor de la variable
    mov al, ["hola"]
    mov eax, 4
    mov ebx, 1
    mov edx, 1
    int 0x80
    ; Imprimir el mensaje
    mov eax, 4
    mov ebx, 1
    mov ecx, output
    mov edx, 8
    int 0x80
    ; Imprimir el valor de la variable
    mov al, [25]
    mov eax, 4
    mov ebx, 1
    mov edx, 1
    int 0x80
    ; Imprimir el mensaje
    mov eax, 4
    mov ebx, 1
    mov ecx, output
    mov edx, 8
    int 0x80
    ; Imprimir el valor de la variable
    mov al, [x]
    mov eax, 4
    mov ebx, 1
    mov edx, 1
    int 0x80
    ; Imprimir el mensaje
    mov eax, 4
    mov ebx, 1
    mov ecx, output
    mov edx, 8
    int 0x80
    ; Imprimir el valor de la variable
    mov al, [3.14]
    mov eax, 4
    mov ebx, 1
    mov edx, 1
    int 0x80
    ; Imprimir el mensaje
    mov eax, 4
    mov ebx, 1
    mov ecx, output
    mov edx, 8
    int 0x80
    ; Imprimir el valor de la variable
    mov al, [z]
    mov eax, 4
    mov ebx, 1
    mov edx, 1
    int 0x80
    mov eax, 1
    xor ebx, ebx
    int 0x80
