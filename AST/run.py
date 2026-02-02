# interpreter.py

def interpret_intermediate_code(input_file, output_file):
    asm_code = []
    data_section = []
    main_code = []
    variables = {}
    msg_count = 0

    # Leer el archivo de código intermedio
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()

            if parts[0] == "assign":
                var_name = parts[1]
                value = parts[2]
                variables[var_name] = value

                if value == "NULL":
                    data_section.append(f"    {var_name} db 0")
                else:
                    data_section.append(f"    {var_name} db {value}")

            elif parts[0] == "call" and parts[1] == "print":
                value = parts[2].strip('"')

                if value in variables:
                    main_code.append(f"    mov al, [{value}]")
                    main_code.append("    movzx eax, al")
                    main_code.append("    push eax")
                    main_code.append("    push num_format")
                else:
                    try:
                        num_value = int(value)
                        main_code.append(f"    push {num_value}")
                        main_code.append("    push num_format")
                    except ValueError:
                        msg_count += 1
                        msg_var = f"msg{msg_count}"
                        data_section.append(f'    {msg_var} db "{value}", 0')
                        main_code.append(f"    push {msg_var}")
                        main_code.append("    push str_format")

                main_code.append("    call _printf")
                main_code.append("    add esp, 8")

    asm_code.append("section .data")
    asm_code.extend(data_section)
    asm_code.append("    num_format db '%d', 10, 0")
    asm_code.append("    str_format db '%s', 10, 0")
    asm_code.append("    success_msg db 'Compilation successfully', 10, 0")
    asm_code.append("    time_msg db 'Execution time: %d milliseconds', 10, 0")
    asm_code.append("    start_time dd 0")

    asm_code.append("\nsection .text")
    asm_code.append("    global _main")
    asm_code.append("    extern _printf, _clock, _getchar")  # Incluir getchar
    asm_code.append("\n_main:")

    asm_code.append("    call _clock")
    asm_code.append("    mov dword [start_time], eax")

    asm_code.extend(main_code)

    asm_code.append("    push success_msg")
    asm_code.append("    push str_format")
    asm_code.append("    call _printf")
    asm_code.append("    add esp, 8")

    asm_code.append("    call _clock")
    asm_code.append("    sub eax, [start_time]")
    asm_code.append("    push eax")
    asm_code.append("    push time_msg")
    asm_code.append("    call _printf")
    asm_code.append("    add esp, 8")

    asm_code.append("    call _getchar")  # Esperar a que el usuario presione una tecla

    asm_code.append("\n    ret")

    with open(output_file, 'w') as f:
        f.write('\n'.join(asm_code))

if __name__ == "__main__":
    input_filename = "intermediate_code.txt"
    output_filename = "output.s"
    interpret_intermediate_code(input_filename, output_filename)
    print(f"Código ensamblador generado en '{output_filename}'")
