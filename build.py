"""
build.py — Script de construcción del compilador portátil Tesseract
=====================================================================
Pasos que ejecuta:
  1. Pre-compila tess_runtime.c a objetos .o para cada plataforma destino
     usando zig cc (cross-compilation). Para Android genera .so.
  2. Invoca PyInstaller con compiler_portable.spec para generar el .exe.
  3. Para Android, genera una carpeta 'compiler_android' lista para Termux.

Uso:
    python build.py                    # Solo la plataforma actual
    python build.py --all-platforms    # Todos los targets (win/linux/mac/android)
    python build.py --platforms android  # Solo Android
    python build.py --no-pyinstaller   # Solo precompila los .o/.so
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

# =============================================================================
# Configuración — rutas por carpeta
# =============================================================================

NATIVE_DIR = "TesseractNative"   # tesscodegen.py, tessruntime.py, tess_runtime.c
WEB_DIR    = "TesseractWeb"      # tessruntimeweb.py, runtimeweb.js

RUNTIME_C    = os.path.join(NATIVE_DIR, "runtime.c")
RUNTIME_OBJS = {
    "win32":   os.path.join(NATIVE_DIR, "tess_runtime_win.o"),
    "linux":   os.path.join(NATIVE_DIR, "tess_runtime_linux.o"),
    "mac":     os.path.join(NATIVE_DIR, "tess_runtime_mac.o"),
    "android": os.path.join(NATIVE_DIR, "libtess_runtime.so"),   # shared library
}

ZIG_TARGETS = {
    "win32":   "x86_64-windows-gnu",
    "linux":   "x86_64-linux-gnu",
    "mac":     "x86_64-macos",
    "android": "aarch64-linux-musl",   # o arm-linux-androideabi para 32-bit
}

# =============================================================================
# Helpers
# =============================================================================

def find_zig() -> str:
    zig = shutil.which("zig")
    if not zig:
        raise RuntimeError(
            "No se encontró 'zig' en el PATH.\n"
            "Instálalo desde https://ziglang.org/download y añádelo al PATH."
        )
    return zig


def compile_runtime(zig: str, platform: str) -> str:
    """Compila tess_runtime.c a un .o (o .so para Android) dentro de TesseractNative/."""
    c_src = RUNTIME_C
    out_file = RUNTIME_OBJS[platform]
    zig_target = ZIG_TARGETS[platform]

    if not os.path.exists(c_src):
        print(f"❌ No se encontró '{c_src}'")
        sys.exit(1)

    # Construir comando según plataforma
    if platform == "android":
        cmd = [
            zig, "cc",
            "-target", zig_target,
            "-O2",
            "-shared",
            "-fPIC",
            c_src,
            "-o", out_file,
        ]
    else:
        cmd = [
            zig, "cc",
            "-target", zig_target,
            "-O2",
            "-c",
            c_src,
            "-o", out_file,
        ]

    print(f"[build] Compilando runtime para '{platform}': {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Error compilando para {platform}:\n{res.stderr}")
        sys.exit(1)
    print(f"[build] ✓ {out_file} ({os.path.getsize(out_file):,} bytes)")
    return out_file

# Módulos tkinter que PyInstaller no detecta automáticamente en Windows
_TKINTER_HIDDEN = [
    "tkinter",
    "_tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.filedialog",
    "tkinter.simpledialog",
    "tkinter.colorchooser",
    "tkinter.font",
    "tkinter.scrolledtext",
    "tkinter.constants",
    "tkinter.dnd",
    "tkinter.commondialog",
]

def patch_spec_for_tkinter(spec_path: str) -> None:
    """
    Parchea compiler_portable.spec para que PyInstaller incluya
    tkinter, _tkinter y los archivos TCL/TK en el build de Windows.

    Es idempotente: si ya fue parcheado anteriormente no hace nada.
    """
    MARKER = "# [build.py] tkinter patch aplicado"

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER in content:
        print("[build] ℹ️  El spec ya tiene el patch de tkinter, omitiendo.")
        return

    # ------------------------------------------------------------------
    # 1. Inyectar hiddenimports de tkinter
    # ------------------------------------------------------------------
    def inject_hidden(m: re.Match) -> str:
        # Extraer los imports existentes (puede ser lista multilínea)
        inner = m.group(2)
        existing = [
            x.strip().strip("'\"")
            for x in re.split(r",\s*", inner)
            if x.strip().strip("'\"")
        ]
        to_add = [x for x in _TKINTER_HIDDEN if x not in existing]
        combined = existing + to_add
        formatted = ", ".join(f"'{x}'" for x in combined)
        return f"{m.group(1)}{formatted}{m.group(3)}"

    new_content, n = re.subn(
        r"(hiddenimports\s*=\s*\[)(.*?)(\])",
        inject_hidden,
        content,
        flags=re.DOTALL,
    )

    if n == 0:
        print("⚠️  No se encontró 'hiddenimports' en el spec. "
              "Asegúrate de que Analysis() exista en el spec.")

    # ------------------------------------------------------------------
    # 2. Inyectar cabecera con collect_data_files y collect_dynamic_libs
    #    para los archivos TCL/TK y _tkinter.pyd (Windows)
    # ------------------------------------------------------------------
    header = (
        f"{MARKER}\n"
        "# Recolecta los archivos de datos de TCL/TK y el .pyd de _tkinter\n"
        "import sys as _sys\n"
        "from PyInstaller.utils.hooks import (\n"
        "    collect_data_files as _cdf,\n"
        "    collect_dynamic_libs as _cdl,\n"
        ")\n"
        "_tk_datas    = _cdf('tkinter')          # archivos .tcl, .tk, etc.\n"
        "_tk_binaries = _cdl('_tkinter')         # _tkinter.pyd + tcl/tk DLLs (Windows)\n\n"
    )
    new_content = header + new_content

    # ------------------------------------------------------------------
    # 3. Fusionar _tk_datas en datas=[] y _tk_binaries en binaries=[]
    # ------------------------------------------------------------------
    def inject_list(var_name: str, extra: str, text: str) -> str:
        """Agrega `*extra` a la lista `var_name=[...]` del spec."""
        pattern = rf"({var_name}\s*=\s*\[)(.*?)(\])"

        def replacer(m: re.Match) -> str:
            inner = m.group(2).strip()
            if inner:
                return f"{m.group(1)}{inner}, *{extra}{m.group(3)}"
            return f"{m.group(1)}*{extra}{m.group(3)}"

        result, count = re.subn(pattern, replacer, text, flags=re.DOTALL)
        if count == 0:
            print(f"⚠️  No se encontró '{var_name}=[]' en el spec. "
                  f"Los {extra} no serán incluidos automáticamente.")
        return result

    new_content = inject_list("datas",    "_tk_datas",    new_content)
    new_content = inject_list("binaries", "_tk_binaries", new_content)

    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[build] ✓ Spec parcheado con tkinter "
          f"({len(_TKINTER_HIDDEN)} hidden imports + datos TCL/TK + binarios _tkinter)")
def run_pyinstaller():
    """Lanza PyInstaller y copia la carpeta tkinter a _internal."""
    spec = "compiler_portable.spec"
    if not os.path.exists(spec):
        print(f"❌ No se encontró {spec}")
        sys.exit(1)

    print("\n[build] Ejecutando PyInstaller...")
    res = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", spec],
        check=False,
    )
    if res.returncode != 0:
        print("❌ PyInstaller falló.")
        sys.exit(res.returncode)
    print("[build] ✓ Empaquetado completado → dist/compiler_portable/")

    # Copiar la carpeta tkinter de Python directo a _internal
    if sys.platform == "win32":
        import tkinter as _tk
        tk_src = os.path.dirname(_tk.__file__)
        tk_dst = os.path.join("dist", "compiler_portable", "_internal", "tkinter")
        if os.path.exists(tk_dst):
            shutil.rmtree(tk_dst)
        shutil.copytree(tk_src, tk_dst)
        print(f"[build] ✓ tkinter copiado: {tk_src} → {tk_dst}")
def package_for_android():
    """Crea una carpeta 'compiler_android' lista para copiar a Termux."""
    output_dir = "compiler_android"
    print(f"\n[build] Preparando empaquetado para Android en '{output_dir}/'")

    # Crear estructura de directorios
    os.makedirs(output_dir, exist_ok=True)
    native_out = os.path.join(output_dir, "TesseractNative")
    web_out = os.path.join(output_dir, "TesseractWeb")
    os.makedirs(native_out, exist_ok=True)
    os.makedirs(web_out, exist_ok=True)

        # 6. Copiar el binario del parser (compiler) para Android
    compiler_src = os.path.join(os.path.dirname(__file__), "compiler")
    if os.path.exists(compiler_src):
        compiler_dst = os.path.join(output_dir, "compiler")
        shutil.copy2(compiler_src, compiler_dst)
        os.chmod(compiler_dst, 0o755)   # ejecutable en Termux
        print(f"   Copiado {compiler_src} -> {compiler_dst}")
    else:
        print(f"   ⚠️ No se encontró 'compiler' en el directorio actual. El parser no funcionará.")

    # 1. Copiar el .so compilado
    so_src = RUNTIME_OBJS["android"]
    so_dst = os.path.join(native_out, "libtess_runtime.so")
    if not os.path.exists(so_src):
        print(f"❌ No se encontró {so_src}. Ejecuta antes --platforms android")
        sys.exit(1)
    shutil.copy2(so_src, so_dst)
    print(f"   Copiado {so_src} -> {so_dst}")
    # 2. Copiar scripts Python necesarios (todos los .py del directorio actual excepto build.py)
    for file in os.listdir("."):
        if file.endswith(".py") and file != "build.py":
            shutil.copy2(file, output_dir)
            print(f"   Copiado {file}")

    # 3. Copiar archivos de TesseractNative (excepto .c, .o, .so)
    for file in os.listdir(NATIVE_DIR):
        src = os.path.join(NATIVE_DIR, file)
        dst = os.path.join(native_out, file)
        if os.path.isfile(src) and not file.endswith((".c", ".o", ".so")):
            shutil.copy2(src, dst)
            print(f"   Copiado {src} -> {dst}")

    # 4. Copiar archivos de TesseractWeb
    for file in os.listdir(WEB_DIR):
        src = os.path.join(WEB_DIR, file)
        dst = os.path.join(web_out, file)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            print(f"   Copiado {src} -> {dst}")

    # 5. Crear script run.sh para Termux
    run_script = os.path.join(output_dir, "run.sh")
    with open(run_script, "w", encoding="utf-8") as f:
        f.write("#!/data/data/com.termux/files/usr/bin/bash\n")
        f.write("# Lanzador del compilador en Termux\n")
        f.write('cd "$(dirname "$0")"\n')
        f.write('export LD_LIBRARY_PATH="$PWD/TesseractNative:$LD_LIBRARY_PATH"\n')
        f.write('python compiler_portable.py "$@"\n')
        f.write("export PATH=\"$PWD:$PATH\"\n")   # <-- aquí el nombre correcto
    os.chmod(run_script, 0o755)
    print(f"   Creado {run_script} (ejecutable)")

    print(f"\n✅ Empaquetado listo en '{output_dir}/'")
    print("   Para usar en Termux:")
    print("   1. Copia toda la carpeta a tu dispositivo (adb, scp, etc.)")
    print("   2. En Termux: cd compiler_android && chmod +x run.sh && ./run.sh")


# =============================================================================
# Main
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description="Build script de Tesseract Portable")
    ap.add_argument("--all-platforms",  action="store_true",
                    help="Pre-compila el runtime para Windows, Linux, macOS y Android")
    ap.add_argument("--no-pyinstaller", action="store_true",
                    help="Solo precompila los .o/.so, no ejecuta PyInstaller")
    ap.add_argument("--platforms",      nargs="+",
                    choices=list(RUNTIME_OBJS.keys()),
                    help="Plataformas específicas a compilar (win32, linux, mac, android)")
    args = ap.parse_args()

    # Verificar que existen las carpetas
    for folder in (NATIVE_DIR, WEB_DIR):
        if not os.path.isdir(folder):
            print(f"❌ No se encontró la carpeta '{folder}' en el directorio actual.")
            sys.exit(1)

    # Verificar que existe el fuente C
    if not os.path.exists(RUNTIME_C):
        print(f"❌ No se encontró '{RUNTIME_C}'")
        sys.exit(1)

    # Verificar que existe runtimeweb.js
    runtimeweb = os.path.join(WEB_DIR, "runtimeweb.js")
    if not os.path.exists(runtimeweb):
        print(f"❌ No se encontró '{runtimeweb}'")
        sys.exit(1)

    zig = find_zig()

    # Decidir qué plataformas compilar
    if args.all_platforms:
        platforms = list(RUNTIME_OBJS.keys())
    elif args.platforms:
        platforms = args.platforms
    else:
        if sys.platform == "win32":
            platforms = ["win32"]
        elif sys.platform == "darwin":
            platforms = ["mac"]
        else:
            platforms = ["linux"]

    print(f"[build] Plataformas objetivo: {', '.join(platforms)}")
    print(f"[build] Native dir: {NATIVE_DIR}")
    print(f"[build] Web dir:    {WEB_DIR}\n")

    # Compilar runtimes
    for plat in platforms:
        compile_runtime(zig, plat)

    # Si Android está entre las plataformas, generar empaquetado específico
    if "android" in platforms:
        package_for_android()
        # Si solo se pidió Android, no ejecutar PyInstaller
        if set(platforms) == {"android"} and not args.no_pyinstaller:
            print("\n[build] Nota: Para Android no se ejecuta PyInstaller. Se ha creado 'compiler_android/'")
            return

    # PyInstaller solo para win/linux/mac (no para Android)
    if not args.no_pyinstaller:
        run_pyinstaller()


if __name__ == "__main__":
    main()