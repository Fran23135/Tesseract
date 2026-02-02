section .data
    ClassName db "SimpleWindowClass", 0   ; Nombre de la clase de la ventana
    WindowTitle db "Ventana de Ejemplo", 0 ; Título de la ventana

section .bss
    hInstance resd 1     ; Espacio para el handle de la instancia
    hWnd resd 1          ; Espacio para el handle de la ventana
    msg resb 28          ; Estructura MSG de 28 bytes

section .text
    extern GetModuleHandleA, RegisterClassExA, CreateWindowExA, ShowWindow, UpdateWindow
    extern GetMessageA, TranslateMessage, DispatchMessageA, DefWindowProcA, ExitProcess
    global _main        ; Definir WinMain como el punto de entrada

_main:
    ; Obtener el manejador del módulo (hInstance)
    push 0                   ; NULL como parámetro para GetModuleHandle
    call GetModuleHandleA     ; Llamada a GetModuleHandleA
    mov [hInstance], eax      ; Guardar el valor de hInstance en la variable correspondiente

    ; Definir la estructura WNDCLASSEX
    sub esp, 40               ; Reservar 40 bytes para WNDCLASSEX en la pila
    mov dword [esp], 40       ; Tamaño de la estructura (cbSize)
    mov dword [esp+4], 0      ; Sin estilo (style)
    mov dword [esp+8], DefWindowProcA  ; Dirección de DefWindowProcA como lpfnWndProc
    mov dword [esp+12], 0     ; cbClsExtra
    mov dword [esp+16], 0     ; cbWndExtra
    mov eax, [hInstance]      ; Cargar hInstance
    mov dword [esp+20], eax   ; Asignar hInstance en la estructura
    mov dword [esp+24], 0     ; Sin icono (hIcon)
    mov dword [esp+28], 0     ; Sin cursor (hCursor)
    mov dword [esp+32], 5     ; Fondo blanco (hbrBackground = COLOR_WINDOW+1)
    mov dword [esp+36], ClassName  ; Nombre de la clase (lpszClassName)
    mov dword [esp+40], 0     ; Sin icono pequeño (hIconSm)

    ; Registrar la clase de ventana
    call RegisterClassExA     ; Llamada a RegisterClassExA
    test eax, eax             ; Comprobar si la clase fue registrada
    jz end_program            ; Si eax es 0, saltar a end_program

    ; Crear la ventana
    push 0                    ; dwExStyle = 0
    push ClassName            ; Nombre de la clase
    push WindowTitle          ; Título de la ventana
    push 0xCF0000             ; Estilo de ventana (WS_OVERLAPPEDWINDOW)
    push 100                  ; Posición X
    push 100                  ; Posición Y
    push 400                  ; Ancho de la ventana
    push 300                  ; Alto de la ventana
    push 0                    ; hWndParent = 0 (ventana sin padre)
    push 0                    ; Sin menú (hMenu)
    push dword [hInstance]     ; Handle de la instancia (hInstance)
    push 0                    ; Sin parámetros adicionales (lpParam)
    call CreateWindowExA       ; Llamada a CreateWindowExA
    mov [hWnd], eax            ; Guardar el handle de la ventana

    ; Mostrar la ventana
    push 1                    ; SW_SHOWNORMAL = 1
    push eax                  ; Handle de la ventana
    call ShowWindow           ; Llamada a ShowWindow

    ; Actualizar la ventana
    push eax                  ; Handle de la ventana
    call UpdateWindow         ; Llamada a UpdateWindow

    ; Bucle de mensajes
msg_loop:
    push 0                    ; Ningún handle de ventana (hWnd = 0)
    mov eax, msg              ; Cargar la dirección de msg
    push eax                  ; Poner en la pila la dirección de msg
    call GetMessageA          ; Llamada a GetMessageA
    test eax, eax             ; Comprobar si eax es 0
    jz end_program            ; Si eax es 0, salir del programa

    mov eax, msg              ; Cargar la dirección de msg
    push eax                  ; Poner en la pila la dirección de msg
    call TranslateMessage      ; Llamada a TranslateMessage

    mov eax, msg              ; Cargar la dirección de msg
    push eax                  ; Poner en la pila la dirección de msg
    call DispatchMessageA      ; Llamada a DispatchMessageA

    jmp msg_loop              ; Repetir el bucle de mensajes

end_program:
    push 0                    ; Código de salida
    call ExitProcess          ; Llamada a ExitProcess para salir del programa
