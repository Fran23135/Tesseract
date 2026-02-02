import subprocess
import tempfile
import os
import sys

# --- CONFIGURACIÓN ---
# Cambia 'parser.exe' por el nombre real de tu ejecutable del parser.
# Si tu parser también es un script de Python, usa ['python', 'parser.py']
PARSER_CMD = ['compiler.exe'] 
# ---------------------

def run_command(command, step_name):
    """Ejecuta un comando y reporta si falla."""
    print(f"--- PASO: {step_name} ---")
    try:
        # Usamos subprocess.run para ejecutar el comando
        # check=True asegura que si el comando falla (código de salida != 0), se lance una excepción
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(result.stdout) # Muestra la salida estándar del subproceso
        if result.stderr:
            print(f"Salida de error del subproceso:\n{result.stderr}")
        print(f"--- ÉXITO: {step_name} completado. ---\n")
        return True
    except FileNotFoundError:
        print(f"*** ERROR: No se encontró el ejecutable '{command[0]}'. Asegúrate de que esté en la misma carpeta o en el PATH del sistema. ***")
        return False
    except subprocess.CalledProcessError as e:
        # Esta excepción se captura si el subproceso devuelve un código de error
        print(f"*** ERROR durante '{step_name}'. El subproceso falló. ***")
        print(f"Comando ejecutado: {' '.join(e.cmd)}")
        print(f"Código de salida: {e.returncode}")
        print(f"Salida estándar (stdout):\n{e.stdout}")
        print(f"Salida de error (stderr):\n{e.stderr}")
        return False
    except Exception as e:
        print(f"*** Ocurrió un error inesperado durante '{step_name}': {e} ***")
        return False
def run_interactive_command(command, step_name):
    """Ejecuta un comando interactivo, permitiendo la entrada del usuario."""
    print(f"--- PASO: {step_name} ---")
    try:
        # La diferencia clave: no capturamos la salida, dejamos que fluya directamente.
        # Esto permite que input() en el subproceso funcione.
        result = subprocess.run(command, check=True, text=True, encoding='utf-8', errors='replace')
        print(f"--- ÉXITO: {step_name} completado. ---\n")
        return True
    except FileNotFoundError:
        print(f"*** ERROR: No se encontró el ejecutable '{command[0]}'. Asegúrate de que esté en la misma carpeta. ***")
        return False
    except subprocess.CalledProcessError as e:
        print(f"*** ERROR durante '{step_name}'. El subproceso falló. ***")
        print(f"Salida de error (stderr):\n{e.stderr}")
        return False
def main():
    # 1. Verificar que se haya pasado un archivo de código fuente como argumento
    if len(sys.argv) < 2:
        print("Uso: python main.py <ruta_al_archivo_de_codigo>")
        sys.exit(1)
    
    source_file = sys.argv[1]
    if not os.path.exists(source_file):
        print(f"Error: El archivo de código fuente '{source_file}' no existe.")
        sys.exit(1)

    # 2. Crear un directorio temporal seguro que se limpiará automáticamente
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📦 Usando directorio temporal: {temp_dir}\n")

        # 3. Definir las rutas de los archivos intermedios dentro del directorio temporal
        txt_ast_path = os.path.join(temp_dir, 'ast_output.txt')
        json_ast_path = os.path.join(temp_dir, 'ast_output.json')

        # === PASO 1: Ejecutar el Parser (semantic.y compilado) ===
        # Este comando ejecutará: parser.exe <tu_codigo.txt> <ruta_temporal_ast.txt>
        parser_full_cmd = PARSER_CMD + [source_file, txt_ast_path]
        if not run_command(parser_full_cmd, "Generando AST (.txt)"):
            return # Detener si falla

        # === PASO 2: Convertir el AST de TXT a JSON ===
        # Este comando ejecutará: python astAjson.py <ruta_temporal_ast.txt> <ruta_temporal_ast.json>
        converter_cmd = ['python', 'astAjson.py', txt_ast_path, json_ast_path]
        if not run_command(converter_cmd, "Convirtiendo AST a JSON"):
            return # Detener si falla

        # === PASO 3: Ejecutar el Intérprete con el archivo JSON ===
        # Este comando ejecutará: python interpre.py <ruta_temporal_ast.json>
        interpreter_cmd = ['python', 'interpre.py', json_ast_path]
        if not run_interactive_command(interpreter_cmd, "Ejecutando el intérprete"): # <-- ¡ESTE ES EL CAMBIO!
         return # Detener si falla
            
    print("✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    main()