import sys
import os
import tempfile
import subprocess
import time
import psutil  # pip install psutil

# Importar los módulos directamente
import astAjson
import interpre
import module_loader
import native_registry

# =============================================================================
# Rutas base (funciona tanto como .py como .exe de PyInstaller)
# =============================================================================

if getattr(sys, 'frozen', False):
    BASE_DIR     = os.path.dirname(sys.executable)
    INTERNAL_DIR = sys._MEIPASS          # archivos empaquetados dentro del bundle
else:
    BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
    INTERNAL_DIR = BASE_DIR


# =============================================================================
# Utilidades de tiempo / memoria
# =============================================================================

def format_time(seconds):
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1_000:.2f} ms"
    else:
        return f"{seconds:.6f} s"


def get_process_memory():
    try:
        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        return None


# =============================================================================
# Resolver la ruta al runtime C pre-compilado
# =============================================================================

def resolve_runtime_lib(user_provided: str | None, target_platform: str | None) -> str:
    """
    Resuelve la ruta al objeto runtime C (.o pre-compilado o .c fuente).

    Prioridad:
      1. --runtime <ruta>  proporcionado por el usuario  →  se usa tal cual.
      2. .o pre-compilado por plataforma (buscado en INTERNAL_DIR y BASE_DIR).
      3. tess_runtime.c como fallback (zig/clang compilará en el momento).
    """
    if user_provided:
        return user_provided

    # Determinar plataforma si no se indicó
    if target_platform is None:
        if sys.platform == "win32":
            plat = "win32"
        elif sys.platform == "darwin":
            plat = "mac"
        else:
            plat = "linux"
    else:
        plat = target_platform

    obj_name = {
        "win32": "tess_runtime_win.o",
        "linux": "tess_runtime_linux.o",
        "unix":  "tess_runtime_linux.o",
        "mac":   "tess_runtime_mac.o",
    }.get(plat, "tess_runtime_linux.o")

    # Buscar .o empaquetado
    for search_dir in (INTERNAL_DIR, BASE_DIR):
        candidate = os.path.join(search_dir, obj_name)
        if os.path.exists(candidate):
            return candidate

    # Fallback: .c fuente (zig/clang lo compilará on-the-fly)
    for search_dir in (INTERNAL_DIR, BASE_DIR):
        candidate = os.path.join(search_dir, "tess_runtime.c")
        if os.path.exists(candidate):
            print(f"[native] ADVERTENCIA: no se encontró '{obj_name}', "
                  f"se usará el fuente C '{candidate}'")
            return candidate

    raise FileNotFoundError(
        f"No se encontró '{obj_name}' ni 'tess_runtime.c' "
        f"en '{INTERNAL_DIR}' ni en '{BASE_DIR}'"
    )


# =============================================================================
# Parseo de argumentos
# =============================================================================

# Flags consumidos por compiler_portable (NO se reenvían a compiler.exe)
_OWN_FLAGS = {
    '--debug', '--d', '-d',
    '--target',
    '-o',
    '--runtime',
    '--win32', '--linux', '--mac', '--unix',
    '--ir',
    '--pretty',
    '--no-zig',
    '-html',
}
_COMPILER_ALLOWED = {'-indent', '-i', '-block', '-b'}
def parse_args(argv):
    """
    Devuelve:
      debug_mode, source_file, target, output_name, runtime_lib_user,
      target_platform, ir_only, pretty, use_zig, compiler_flags
    """
    debug_mode      = False
    source_file     = None
    target          = 'interp'
    output_name     = None
    runtime_lib_user = None       # None = auto-detect en resolve_runtime_lib
    target_platform = None
    ir_only         = False
    pretty          = False
    use_zig         = True
    html_mode       = False
    compiler_flags  = []
    i = 1
    while i < len(argv):
        arg = argv[i]

        if arg in ('--debug', '--d', '-d'):
            debug_mode = True

        elif arg == '--target':
            i += 1
            if i < len(argv):
                target = argv[i].lower()
                if target not in ('interp', 'native', 'web'):
                    print(f"Error: --target debe ser 'interp', 'native' o 'web' "
                          f"(recibido: '{target}')")
                    sys.exit(1)

        elif arg == '-o':
            i += 1
            if i < len(argv):
                output_name = argv[i]

        elif arg == '--runtime':
            i += 1
            if i < len(argv):
                runtime_lib_user = argv[i]

        elif arg == '--win32':
            target_platform = 'win32'
        elif arg == '--linux':
            target_platform = 'linux'
        elif arg == '--unix':
            target_platform = 'unix'
        elif arg == '--mac':
            target_platform = 'mac'

        elif arg == '--ir':
            ir_only = True
        elif arg == '--pretty':
            pretty = True
        elif arg == '--no-zig':
            use_zig = False
        elif arg == '-html':
            html_mode = True    
        elif arg.startswith('-'):
            if arg in _COMPILER_ALLOWED:
                # Flag válido para compiler.exe → reenviar
                compiler_flags.append(arg)
            elif arg in _OWN_FLAGS:
                # Flag propio de compiler_portable llegó fuera de lugar
                # (p.ej. --target sin valor, o duplicado)
                print(f"Error: '{arg}' es un flag de compiler_portable y no fue procesado correctamente.")
                sys.exit(1)
            else:
                print(f"Error: flag desconocido: '{arg}'")
                print(f"  Flags de compiler.exe permitidos : {sorted(_COMPILER_ALLOWED)}")
                print(f"  Flags de compiler_portable       : {sorted(_OWN_FLAGS)}")
                sys.exit(1)
        else:
            if source_file is None:
                source_file = arg

        i += 1

    return (debug_mode, source_file, target, output_name, runtime_lib_user,
            target_platform, ir_only, pretty, use_zig, html_mode, compiler_flags)

# =============================================================================
# Backend: Intérprete
# =============================================================================

def run_interpreter(json_path, debug_mode, _log):
    _log("\n[3/3] Ejecutando intérprete...")
    _log("-" * 70)
    inicio = time.perf_counter()
    try:
        interpre.debug_mode_g = debug_mode
        sys.argv = ['interpre.py', json_path]
        interpre.main()
        return time.perf_counter() - inicio, None
    except Exception as e:
        t = time.perf_counter() - inicio
        print(f"\n❌ Error en intérprete: {e}")
        return t, e


# =============================================================================
# Backend: Nativo (tesscodegen → .ll → binario)
# =============================================================================

def run_native(json_path, output_name, runtime_lib, target_platform,
               ir_only, use_zig, debug_mode, _log):
    """
    Invoca tesscodegen para producir .ll y, opcionalmente, el binario final.

    Nomenclatura de archivos:
      - El .ll se genera como  <output_name>.ll  (sin .exe)
      - El ejecutable lleva .exe automáticamente en win32 (tesscodegen lo añade)
    El runtime_lib puede ser un .o pre-compilado o un .c fuente.
    """
    import tesscodegen

    if output_name is None:
        output_name = 'output'

    # Quitar .exe si el usuario ya lo puso; tesscodegen lo reañade en win32
    if output_name.lower().endswith('.exe'):
        output_name = output_name[:-4]

    _log(f"\n[3/3] Backend nativo (tesscodegen)  →  salida: {output_name}")
    _log(f"      Runtime lib: {runtime_lib}")
    _log("-" * 70)
    inicio = time.perf_counter()

    try:
        if ir_only:
            ll_out = output_name + '.ll'
            tesscodegen.compile_to_file(json_path, ll_out, debug=debug_mode)
            print(f"[native] IR escrito en: {ll_out}")
        else:
            tesscodegen.compile_to_binary(
                ast_path        = json_path,
                output_path     = output_name,
                runtime_lib     = runtime_lib,
                debug           = debug_mode,
                target_platform = target_platform,
                use_zig         = use_zig,
            )
        return time.perf_counter() - inicio, None
    except Exception as e:
        t = time.perf_counter() - inicio
        print(f"\n❌ Error en backend nativo: {e}")
        return t, e


# =============================================================================
# Backend: Web (tessruntimeweb → WebIR → node runtimeweb.js → .js)
# =============================================================================

def run_web(json_path, output_name, pretty, html_mode, debug_mode, _log):
    """
    1. tessruntimeweb.py  →  <base>.webir.json
    2. node runtimeweb.js →  <base>.js
    """
    import tessruntimeweb

    if output_name is None:
        output_name = 'output'

    base_name  = output_name[:-3] if output_name.lower().endswith('.js') else output_name
    webir_path = base_name + '.webir.json'
    js_path    = base_name + '.js'

    _log(f"\n[3a/3] tessruntimeweb  →  {webir_path}")
    _log("-" * 70)
    inicio = time.perf_counter()

    try:
        tessruntimeweb.emit_webir_file(json_path, webir_path, debug=debug_mode)
    except Exception as e:
        t = time.perf_counter() - inicio
        print(f"\n❌ Error en tessruntimeweb: {e}")
        return t, e

    _log(f"\n[3b/3] runtimeweb.js   →  {js_path}")

    # Localizar runtimeweb.js (empaquetado en INTERNAL_DIR o junto al ejecutable)
    runtimeweb_js = None
    for search_dir in (INTERNAL_DIR, BASE_DIR):
        candidate = os.path.join(search_dir, 'runtimeweb.js')
        if os.path.exists(candidate):
            runtimeweb_js = candidate
            break

    if runtimeweb_js is None:
        t = time.perf_counter() - inicio
        print(f"❌ No se encontró 'runtimeweb.js' en '{INTERNAL_DIR}' ni en '{BASE_DIR}'")
        return t, FileNotFoundError("runtimeweb.js")

    node_cmd = ['node', runtimeweb_js, webir_path, '-o', js_path]
    if pretty:
        node_cmd.append('--pretty')
    if html_mode:
        node_cmd.append('-html')    

    res = subprocess.run(node_cmd, capture_output=True, text=True)
    t = time.perf_counter() - inicio

    if res.returncode != 0:
        print("❌ ERROR EN runtimeweb.js")
        print("=" * 70)
        if res.stdout:
            print("SALIDA ESTÁNDAR:")
            print(res.stdout)
        if res.stderr:
            print("\nSALIDA DE ERROR:")
            print(res.stderr)
        print("=" * 70)
        return t, RuntimeError(f"runtimeweb.js falló (código {res.returncode})")

    print(f"[web] JavaScript generado: {js_path}")
    if res.stdout:
        print(res.stdout)
    return t, None


# =============================================================================
# Main
# =============================================================================

USAGE = """\
Uso: compiler_portable.exe [--target interp|native|web] [opciones] archivo.txt

  Targets:
    interp   (default)  Ejecuta con el intérprete Python
    native              Compila a binario nativo via LLVM
    web                 Transpila a JavaScript

  Opciones globales:
    --debug / -d        Modo debug (muestra tiempos y traza interna)
    -indent / -block    Flags para el parser C (compiler.exe)

  --target native:
    -o <nombre>         Nombre del ejecutable (sin extensión; .exe se añade en Windows)
    --runtime <ruta>    Ruta al runtime C (.o pre-compilado o .c fuente)
                        Por defecto busca tess_runtime_<plat>.o junto al ejecutable
    --win32             Compilar para Windows x64 (cross-compilation con zig)
    --linux             Compilar para Linux x64
    --mac               Compilar para macOS x64
    --unix              Compilar para Unix genérico
    --ir                Solo generar el .ll (LLVM IR), no enlazar
    --no-zig            Usar clang en lugar de zig cc

  --target web:
    -o <nombre>         Nombre del archivo .js de salida
    --pretty            WebIR JSON indentado (útil para depuración)
    -html               Generar __tessRead con input HTML (en vez de window.prompt)

Ejemplos:
    compiler_portable.exe programa.tess
    compiler_portable.exe --target native -o miapp programa.tess
    compiler_portable.exe --target native --win32 -o miapp programa.tess
    compiler_portable.exe --target web -o salida programa.tess
    compiler_portable.exe --target native --ir -o prueba programa.tess
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    if len(sys.argv) < 2:
        print(USAGE)
        return

    (debug_mode, source_file, target, output_name, runtime_lib_user,
     target_platform, ir_only, pretty, use_zig, html_mode, compiler_flags) = parse_args(sys.argv)

    def _log(msg):
        if debug_mode:
            print(msg)

    _log(f"DEBUG: sys.argv        = {sys.argv}")
    _log(f"DEBUG: target          = {target}")
    _log(f"DEBUG: source_file     = {source_file}")
    _log(f"DEBUG: output_name     = {output_name}")
    _log(f"DEBUG: runtime_lib_user= {runtime_lib_user}")
    _log(f"DEBUG: target_platform = {target_platform}")
    _log(f"DEBUG: ir_only         = {ir_only}")
    _log(f"DEBUG: pretty          = {pretty}")
    _log(f"DEBUG: use_zig         = {use_zig}")
    _log(f"DEBUG: compiler_flags  = {compiler_flags}")
    _log(f"DEBUG: BASE_DIR        = {BASE_DIR}")
    _log(f"DEBUG: INTERNAL_DIR    = {INTERNAL_DIR}")
    _log(f"DEBUG: html_mode       = {html_mode}")

    if source_file is None:
        print("Error: no se especificó archivo fuente.")
        sys.exit(1)
    if not os.path.exists(source_file):
        print(f"Error: El archivo '{source_file}' no existe.")
        sys.exit(1)

    # Resolver runtime lib (solo necesario para target native)
    runtime_lib = None
    if target == 'native':
        try:
            runtime_lib = resolve_runtime_lib(runtime_lib_user, target_platform)
            _log(f"DEBUG: runtime_lib resuelto = {runtime_lib}")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)

    # =========================================================================
    # INICIO MEDICIÓN
    # =========================================================================
    inicio_absoluto = time.perf_counter()
    memoria_inicial = get_process_memory()

    _log("=" * 70)
    _log(f"COMPILADOR TESSERACT  [target: {target}]")
    _log("=" * 70)
    _log(f"Archivo fuente: {source_file}")
    _log(f"Tamaño: {os.path.getsize(source_file)} bytes")
    _log("-" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        txt_path  = os.path.join(temp_dir, 'ast_output.txt')
        json_path = os.path.join(temp_dir, 'ast_output.json')

        # =====================================================================
        # PASO 1: Parser (compiler.exe)
        # =====================================================================
        _log("\n[1/3] Ejecutando parser (compiler.exe)...")
        inicio_compiler = time.perf_counter()

        compiler_exe = None
        for search_dir in (BASE_DIR, INTERNAL_DIR):
            for name in ('compiler.exe', 'compiler'):
                candidate = os.path.join(search_dir, name)
                if os.path.exists(candidate):
                    compiler_exe = candidate
                    break
            if compiler_exe:
                break

        if not compiler_exe:
            print(f"❌ No se encontró compiler.exe en '{BASE_DIR}' ni en '{INTERNAL_DIR}'")
            sys.exit(1)

        compiler_cmd = [compiler_exe] + compiler_flags + [source_file, txt_path]
        result = subprocess.run(compiler_cmd, capture_output=True, text=True)
        _log(result)

        tiempo_compiler = time.perf_counter() - inicio_compiler

        if result.returncode != 0:
            print("❌ ERROR EN COMPILER.EXE")
            print("=" * 70)
            if result.stdout:
                print("SALIDA ESTÁNDAR:")
                print(result.stdout)
            if result.stderr:
                print("\nSALIDA DE ERROR:")
                print(result.stderr)
            print("=" * 70)
            print("\n⛔ Ejecución detenida debido a errores en el parser")
            sys.exit(1)

        if not os.path.exists(txt_path):
            print("❌ El parser no generó archivo AST")
            return

        tamaño_ast = os.path.getsize(txt_path)
        _log(f"✓ Completado en {format_time(tiempo_compiler)}")
        _log(f"  AST generado: {tamaño_ast} bytes")

        # =====================================================================
        # PASO 2: AST → JSON
        # =====================================================================
        _log("\n[2/3] Convirtiendo AST a JSON...")
        inicio_json = time.perf_counter()

        try:
            sys.argv = ['astAjson.py', txt_path, json_path]
            astAjson.main()
            tiempo_json = time.perf_counter() - inicio_json

            if not os.path.exists(json_path):
                print("❌ No se generó el archivo JSON")
                return

            _log(f"✓ Completado en {format_time(tiempo_json)}")
            _log(f"  JSON generado: {os.path.getsize(json_path)} bytes")

        except Exception as e:
            print(f"❌ Error en conversión JSON: {e}")
            return

        # =====================================================================
        # PASO 3: Backend según --target
        # =====================================================================
        if target == 'interp':
            tiempo_backend, error_backend = run_interpreter(json_path, debug_mode, _log)

        elif target == 'native':
            tiempo_backend, error_backend = run_native(
                json_path, output_name, runtime_lib, target_platform,
                ir_only, use_zig, debug_mode, _log,
            )

        elif target == 'web':
            tiempo_backend, error_backend = run_web(
                json_path, output_name, pretty, html_mode, debug_mode, _log,
            )

    # =========================================================================
    # FIN MEDICIÓN
    # =========================================================================
    fin_absoluto  = time.perf_counter()
    tiempo_total  = fin_absoluto - inicio_absoluto
    memoria_final = get_process_memory()

    # =========================================================================
    # REPORTE (solo en --debug)
    # =========================================================================
    _log("\n" + "=" * 70)
    _log("REPORTE DE RENDIMIENTO")
    _log("=" * 70)

    backend_label = {
        'interp': 'Intérprete',
        'native': 'Codegen nativo',
        'web':    'Codegen web',
    }.get(target, 'Backend')

    _log("\n📊 TIEMPOS POR FASE:")
    _log(f"   Parser (C/C++):         {format_time(tiempo_compiler):>15}")
    _log(f"   Conversión JSON:        {format_time(tiempo_json):>15}")
    _log(f"   {backend_label + ':':24}{format_time(tiempo_backend):>15}")
    _log("-" * 70)
    _log(f"   TOTAL:                  {format_time(tiempo_total):>15}")

    if tiempo_total > 0:
        pct_c = tiempo_compiler / tiempo_total * 100
        pct_j = tiempo_json     / tiempo_total * 100
        pct_b = tiempo_backend  / tiempo_total * 100

        _log("\n📈 DISTRIBUCIÓN:")
        _log(f"   Parser:        {pct_c:>5.1f}%  {'█' * int(pct_c / 2)}")
        _log(f"   JSON:          {pct_j:>5.1f}%  {'█' * int(pct_j / 2)}")
        _log(f"   {backend_label + ':':15}{pct_b:>5.1f}%  {'█' * int(pct_b / 2)}")

    if memoria_inicial and memoria_final:
        _log(f"\n💾 MEMORIA: {memoria_inicial:.1f} MB → {memoria_final:.1f} MB "
             f"(Δ {memoria_final - memoria_inicial:+.1f} MB)")

    _log("\n" + "=" * 70)

    if error_backend:
        sys.exit(1)


if __name__ == "__main__":
    main()