"""
module_loader.py
================
Cargador de librerías Tesseract desde la instalación global.

Estructura esperada en disco:
    libs/
    └── <module>/
        ├── main.tbc              ← orquestador (MAGIC "TSORCH")
        └── versions/
            └── <version>/
                ├── linker.tbc    ← bytecode del código fuente (MAGIC "TSSLK")
                ├── <module>.tmc  ← interfaz pública (MAGIC "TSMC")
                └── deps/         ← dependencias externas

Rutas de búsqueda (en orden):
    Windows:  %LOCALAPPDATA%\\Tesseract\\libs\\
              %APPDATA%\\Tesseract\\libs\\
    Linux:    ~/.local/share/tesseract/libs/
    macOS:    ~/Library/Application Support/tesseract/libs/

Resolución de linker_id → nombre en el linker:
    linker_id = "mathlib_sqrt"
    pure_name = "sqrt"         ← todo lo que está después del primer '_'
    Busca en el linker: "tess_sqrt" primero, luego "sqrt" como fallback.
    El prefijo "tess_" lo añade el tsslk_compiler a todos los símbolos.
"""

import os
import struct
from pathlib import Path


# ════════════════════════════════════════════════════════════════════════
#  EXCEPCIONES
# ════════════════════════════════════════════════════════════════════════

class ModuleError(Exception):
    pass


# ════════════════════════════════════════════════════════════════════════
#  ModuleInstance  — acceso a miembros de un módulo via dot notation
# ════════════════════════════════════════════════════════════════════════

class ModuleInstance:
    """
    Instancia de módulo. Permite acceso a variables y llamadas a métodos
    mediante dot notation desde el intérprete.
    """
    def __init__(self, module_name: str, loader: 'ModuleLoader'):
        self._name   = module_name
        self._loader = loader

    def get_member(self, member_name: str):
        return self._loader.get_export_value(self._name, member_name)

    def call_method(self, method_name: str, args: list, interpreter):
        fn = self._loader.get_function(self._name, method_name)
        return fn.call(args, interpreter)

    def __repr__(self):
        return f"<ModuleInstance '{self._name}'>"


# ════════════════════════════════════════════════════════════════════════
#  Wrapper de función enlazada desde linker.tbc
# ════════════════════════════════════════════════════════════════════════

class _LinkedFunctionWrapper:
    """
    Expone una función del linker.tbc con la misma interfaz
    .call(args, caller_interpreter) que los módulos nativos.
    """
    def __init__(self, func_name: str, isolated_interp, debug: bool = False):
        self._func_name = func_name
        self._iso       = isolated_interp
        self._debug     = debug

    def call(self, args: list, caller_interpreter):
        # Lazy import para evitar circular dependency (interpre importa module_loader)
        from interpre import FunctionContext
        if self._debug:
            print(f"  [LinkedFunc] Llamando '{self._func_name}' args={args}")
        ctx = FunctionContext(self._iso, self._func_name, args)
        return ctx.execute_function()


# ════════════════════════════════════════════════════════════════════════
#  Módulo cargado desde .tbc
# ════════════════════════════════════════════════════════════════════════

class _TbcModule:
    """
    Módulo completamente cargado: mapa público (.tmc) + intérprete aislado
    con el linker.tbc ya ejecutado.
    """
    def __init__(self, module_name: str, version: str,
                 tmc_map: dict, isolated_interp, debug: bool = False):
        self.module_name   = module_name
        self.version       = version
        self.tmc_map       = tmc_map
        self._iso          = isolated_interp
        self._debug        = debug
        self._func_cache   = {}
        self._member_aliases: dict = {}   # alias → original_name

    # ── Funciones ───────────────────────────────────────────────────────

    def get_function(self, func_name: str) -> _LinkedFunctionWrapper:
        if func_name in self._func_cache:
            return self._func_cache[func_name]

        funcs = self.tmc_map.get("functions", {})
        if func_name not in funcs:
            raise ModuleError(
                f"La función '{func_name}' no está en el módulo '{self.module_name}'."
            )

        func_info  = funcs[func_name]
        linker_id  = func_info.get("linker_id", "")
        real_name  = self._resolve_name(linker_id or func_name)

        wrapper = _LinkedFunctionWrapper(real_name, self._iso, self._debug)
        self._func_cache[func_name] = wrapper
        return wrapper

    # ── Exports (variables / constantes) ────────────────────────────────

    def get_export(self, var_name: str):
        exports = self.tmc_map.get("exports", {})
        if var_name not in exports:
            raise ModuleError(
                f"El export '{var_name}' no existe en el módulo '{self.module_name}'."
            )

        exp_info  = exports[var_name]
        linker_id = exp_info.get("linker_id", "")
        real_name = self._resolve_name(linker_id or var_name)

        # Intentar obtener de la tabla de símbolos del intérprete aislado
        iso = self._iso
        for candidate in (real_name, f"tess_{var_name}", var_name):
            try:
                return iso.symbol_table.get_value(candidate)
            except Exception:
                continue

        raise ModuleError(
            f"No se pudo obtener el valor de '{var_name}' del módulo '{self.module_name}'."
        )

    # ── Clases ──────────────────────────────────────────────────────────

    def get_classes(self) -> dict:
        """Retorna las ClassDefinition cargadas en el intérprete aislado."""
        if hasattr(self._iso, 'object_table'):
            return self._iso.object_table.class_definitions
        return {}

    # ── Resolución de nombre: linker_id → nombre real en el linker ───────

    def _resolve_name(self, linker_id: str) -> str:
        """
        Extrae el nombre puro del linker_id y busca el símbolo real
        en el intérprete aislado (tabla de funciones + tabla de símbolos).

        Convención:
          linker_id = "mathlib_sqrt"
          pure_name = "sqrt"              (todo después del primer '_')
          Busca en linker: "tess_sqrt" → "sqrt" → linker_id completo
        """
        if "_" in linker_id:
            pure_name = linker_id.split("_", 1)[1]
        else:
            pure_name = linker_id

        tess_name = f"tess_{pure_name}"

        iso = self._iso

        # Buscar en la tabla de funciones
        for candidate in (tess_name, pure_name, linker_id):
            try:
                iso.symbol_table.get_function(candidate)
                return candidate
            except Exception:
                pass

        # Buscar en la tabla de variables
        for candidate in (tess_name, pure_name, linker_id):
            try:
                iso.symbol_table.get_value(candidate)
                return candidate
            except Exception:
                pass

        # Fallback: devolver el nombre puro aunque no exista (el error llegará al llamar)
        if self._debug:
            print(f"  [ModuleLoader] WARN: no se encontró '{linker_id}' → usando '{pure_name}'")
        return pure_name


# ════════════════════════════════════════════════════════════════════════
#  Módulo nativo Python  (sin .tbc — implementado en Python puro)
# ════════════════════════════════════════════════════════════════════════

class _NativeFunctionWrapper:
    """
    Wrapper de función nativa Python con la misma interfaz .call() que
    _LinkedFunctionWrapper. La función viene del NATIVE_MODULE["functions"].
    """
    def __init__(self, fn, func_name: str):
        self._fn        = fn
        self._func_name = func_name

    def call(self, args: list, interpreter):
        return self._fn(args, interpreter)


class _NativePythonModule:
    """
    Módulo implementado en Python puro (linker_bridge.py y similares).
    Cargado desde un archivo native.py que expone NATIVE_MODULE.

    Comparte la misma interfaz que _TbcModule para que ModuleLoader
    los trate de forma idéntica.
    """
    def __init__(self, desc: dict):
        self.module_name     = desc["module"]
        self.version         = desc.get("version", "native")
        self.tmc_map         = {
            "functions": {k: {"linker_id": k} for k in desc.get("functions", {})},
            "exports":   {k: {"type": "any", "const": True, "linker_id": k}
                          for k in desc.get("exports", {})},
            "classes":   {},
        }
        self._funcs          = desc.get("functions", {})   # {name: callable(args, interp)}
        self._exports_vals   = desc.get("exports", {})     # {name: callable() → value}
        self._member_aliases: dict = {}
        self._func_cache:    dict = {}

    def get_function(self, func_name: str) -> _NativeFunctionWrapper:
        if func_name in self._func_cache:
            return self._func_cache[func_name]
        real = self._member_aliases.get(func_name, func_name)
        if real not in self._funcs:
            raise ModuleError(
                f"La función '{real}' no existe en el módulo nativo '{self.module_name}'."
            )
        w = _NativeFunctionWrapper(self._funcs[real], real)
        self._func_cache[func_name] = w
        return w

    def get_export(self, var_name: str):
        real = self._member_aliases.get(var_name, var_name)
        if real not in self._exports_vals:
            raise ModuleError(
                f"El export '{real}' no existe en el módulo nativo '{self.module_name}'."
            )
        return self._exports_vals[real]()

    def get_classes(self) -> dict:
        return {}

    def _resolve_name(self, linker_id: str) -> str:
        return linker_id




class _BinReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos  = 0

    def read(self, n: int) -> bytes:
        c = self.data[self.pos:self.pos+n]; self.pos += n; return c

    def ru8(self)  -> int:  return struct.unpack(">B", self.read(1))[0]
    def ru16(self) -> int:  return struct.unpack(">H", self.read(2))[0]
    def ri64(self) -> int:  return struct.unpack(">q", self.read(8))[0]
    def rf64(self) -> float: return struct.unpack(">d", self.read(8))[0]

    def rpstr(self) -> str:
        n = self.ru8()
        return self.read(n).decode("utf-8", errors="replace")

    def rwstr(self) -> str:
        n = self.ru16()
        return self.read(n).decode("utf-8", errors="replace")

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def rtype(self) -> str:
        """Lee un type code con payload y devuelve el nombre del tipo."""
        from tss_bytemap import (TYPE_NAMES, TYPE_ARRAY, TYPE_TUPLE,
                                  TYPE_DICT, TYPE_STRUCT)
        tc   = self.ru8()
        name = TYPE_NAMES.get(tc, "any")
        if tc == TYPE_ARRAY:
            self.ru8(); return "array"
        if tc == TYPE_TUPLE:
            cnt = self.ru8()
            for _ in range(cnt): self.ru8()
            return "tuple"
        if tc == TYPE_DICT:
            self.ru8(); self.ru8(); return "dict"
        if tc == TYPE_STRUCT:
            sname = self.rpstr(); return sname
        return name


# ════════════════════════════════════════════════════════════════════════
#  Vista pública de módulo para _inject_native_module_symbols
# ════════════════════════════════════════════════════════════════════════

class _ExportView:
    """Objeto de export compatible con la interfaz que usa interpre.py."""
    def __init__(self, value, export_type: str, is_const: bool):
        self.value       = value
        self.export_type = export_type
        self.is_const    = is_const


class _FunctionView:
    """Objeto de función compatible con la interfaz que usa interpre.py."""
    def __init__(self, wrapper: '_LinkedFunctionWrapper', params: dict):
        self._wrapper = wrapper
        self.params   = params
        self.block    = []       # vacío — es una función enlazada, no en script
        self.kind     = 'native'

    def call(self, args, interpreter):
        return self._wrapper.call(args, interpreter)


class _ModulePublicView:
    """
    Adaptador que expone un _TbcModule con la interfaz que espera
    _inject_native_module_symbols en interpre.py:
      mod.get_function(name) → objeto con .params, .block, .kind
      mod.get_export(name)   → objeto con .value, .export_type, .is_const
    """
    def __init__(self, tbc_module: '_TbcModule'):
        self._mod = tbc_module

    def get_function(self, func_name: str) -> _FunctionView:
        real  = self._mod._member_aliases.get(func_name, func_name)
        funcs = self._mod.tmc_map.get("functions", {})
        if real not in funcs:
            raise ModuleError(
                f"Función '{real}' no existe en módulo '{self._mod.module_name}'."
            )
        info    = funcs[real]
        wrapper = self._mod.get_function(real)
        return _FunctionView(wrapper, info.get("params", {}))

    def get_export(self, var_name: str) -> _ExportView:
        real    = self._mod._member_aliases.get(var_name, var_name)
        exports = self._mod.tmc_map.get("exports", {})
        if real not in exports:
            raise ModuleError(
                f"Export '{real}' no existe en módulo '{self._mod.module_name}'."
            )
        info  = exports[real]
        value = self._mod.get_export(real)
        return _ExportView(value, info.get("type", "any"), info.get("const", False))


# ════════════════════════════════════════════════════════════════════════
#  ModuleLoader  — cargador principal
# ════════════════════════════════════════════════════════════════════════

class ModuleLoader:
    """
    Carga librerías Tesseract desde la instalación global (libs/).

    Interfaz que usa interpre.py:
        is_loaded(name)               → bool
        get_function(mod, func)       → wrapper con .call(args, interp)
        get_export_value(mod, var)    → valor Python
        get_classes(mod)              → dict {name: ClassDefinition}
    """

    def __init__(self, debug: bool = False):
        self._debug   = debug
        self._modules: dict = {}    # module_name → _TbcModule
        self._aliases: dict = {}    # alias → real_module_name
        self._libs_path: Path | None = None
        self._libs_path_resolved = False

    def _resolve_alias(self, name: str) -> str:
        return self._aliases.get(name, name)

    # ════════════════════════════════════════════════════════════════════
    #  Interfaz pública (usada por interpre.py)
    # ════════════════════════════════════════════════════════════════════

    def is_loaded(self, name: str) -> bool:
        if name in self._modules or name in self._aliases:
            return True
        self._try_load(name)
        return name in self._modules

    def load(self, module_name: str):
        """Carga el módulo completo. Llamado por handle_LIB_CALL."""
        if module_name not in self._modules:
            self._ensure_loaded(module_name)

    def load_selective(self, module_name: str, functions: list):
        """
        Carga el módulo y marca qué miembros se importaron selectivamente.
        Llamado por 'from <mod> use f1, f2'.
        La carga completa es la misma — la selectividad la gestiona interpre.py.
        """
        self.load(module_name)

    def get_function(self, mod_name: str, func_name: str) -> '_LinkedFunctionWrapper':
        mod_name = self._resolve_alias(mod_name)
        self._ensure_loaded(mod_name)
        mod = self._modules[mod_name]
        # Aplicar alias de miembro si existe
        real_func = mod._member_aliases.get(func_name, func_name)
        return mod.get_function(real_func)

    def get_export_value(self, mod_name: str, var_name: str):
        mod_name = self._resolve_alias(mod_name)
        self._ensure_loaded(mod_name)
        mod = self._modules[mod_name]
        real_name = mod._member_aliases.get(var_name, var_name)
        return mod.get_export(real_name)

    def get_module(self, module_name: str) -> '_ModulePublicView':
        """
        Retorna una vista pública del módulo compatible con la interfaz que
        usa _inject_native_module_symbols en interpre.py.
        """
        module_name = self._resolve_alias(module_name)
        self._ensure_loaded(module_name)
        return _ModulePublicView(self._modules[module_name])

    def get_classes(self, mod_name: str) -> dict:
        mod_name = self._resolve_alias(mod_name)
        if mod_name not in self._modules:
            return {}
        return self._modules[mod_name].get_classes()

    # ── OOP ──────────────────────────────────────────────────────────────

    def has_class(self, class_name: str) -> bool:
        """Devuelve True si algún módulo cargado tiene esta clase."""
        for mod in self._modules.values():
            if class_name in mod.tmc_map.get("classes", {}):
                return True
            if class_name in mod.get_classes():
                return True
        return False

    def get_class_info(self, class_name: str):
        """
        Retorna (mod_name, class_definition) para una clase nativa.
        Llamado por _instantiate_native_class en interpre.py.
        """
        for mod_name, mod in self._modules.items():
            classes = mod.get_classes()
            if class_name in classes:
                return mod_name, classes[class_name]
        raise ModuleError(f"Clase '{class_name}' no encontrada en ningún módulo cargado.")

    def instantiate(self, mod_name: str, class_name: str,
                    args: list, interpreter) -> 'ModuleInstance':
        """
        Instancia una clase nativa del módulo.
        Ejecuta el constructor con los args dados.
        """
        mod_name = self._resolve_alias(mod_name)
        self._ensure_loaded(mod_name)
        mod = self._modules[mod_name]

        # Buscar el constructor en el tmc_map
        cls_info = mod.tmc_map.get("classes", {}).get(class_name, {})
        ctor     = cls_info.get("constructor")

        instance = ModuleInstance(class_name, self)
        instance._mod_name = mod_name

        if ctor:
            ctor_id   = ctor.get("linker_id", "")
            real_name = mod._resolve_name(ctor_id or f"{mod_name}_{class_name}_new")
            try:
                fn = _LinkedFunctionWrapper(real_name, mod._iso, self._debug)
                fn.call(args, interpreter)
            except Exception as e:
                if self._debug:
                    print(f"  [ModuleLoader] WARN: constructor '{class_name}' error: {e}")

        return instance

    # ── Aliases ───────────────────────────────────────────────────────────

    def apply_alias(self, module_name: str, alias: str):
        """library math al m  → m es alias de math"""
        if alias:
            self._aliases[alias] = module_name

    def apply_member_alias_inline(self, module_name: str,
                                   orig_name: str, alias: str):
        """from math use sqrt al sqr  → sqr es alias de sqrt en math"""
        module_name = self._resolve_alias(module_name)
        if module_name in self._modules and alias:
            self._modules[module_name]._member_aliases[alias] = orig_name

    def apply_member_aliases_positional(self, module_name: str,
                                         members: list, aliases: list):
        """from math use sqrt, abs al [sqr, absolute]"""
        module_name = self._resolve_alias(module_name)
        if module_name in self._modules:
            for orig, alias in zip(members, aliases):
                if alias:
                    self._modules[module_name]._member_aliases[alias] = orig

    def apply_on_aliases(self, module_name: str,
                          on_names: list, on_aliases: list):
        """Clause 'on' para mapeo de eventos/callbacks."""
        module_name = self._resolve_alias(module_name)
        if module_name in self._modules:
            for orig, alias in zip(on_names, on_aliases or []):
                if alias:
                    self._modules[module_name]._member_aliases[alias] = orig

    # ════════════════════════════════════════════════════════════════════
    #  Carga de módulo
    # ════════════════════════════════════════════════════════════════════

    def _ensure_loaded(self, module_name: str):
        if module_name not in self._modules:
            self._try_load(module_name)
        if module_name not in self._modules:
            raise ModuleError(
                f"El módulo '{module_name}' no está instalado o no pudo cargarse. "
                f"Verifica que está en {self._libs_path or 'libs/'}"
            )

    def _try_load(self, module_name: str):
        """Intenta cargar un módulo desde la ruta global. No lanza excepciones."""
        try:
            libs = self._get_libs_path()
            if libs is None:
                if self._debug:
                    print(f"[ModuleLoader] No se encontró directorio libs/")
                return
            module_dir = libs / module_name
            if not module_dir.exists():
                if self._debug:
                    print(f"[ModuleLoader] Módulo '{module_name}' no encontrado en {libs}")
                return
            self._load_module(module_name, module_dir)
        except ModuleError as e:
            if self._debug:
                print(f"[ModuleLoader] Error cargando '{module_name}': {e}")
        except Exception as e:
            if self._debug:
                import traceback
                print(f"[ModuleLoader] Error inesperado cargando '{module_name}': {e}")
                traceback.print_exc()

    def _load_module(self, module_name: str, module_dir: Path):
        """
        Pipeline de carga. Detecta automáticamente si el módulo es:
          A) Nativo Python  → version_dir/native.py  (NATIVE_MODULE descriptor)
          B) Compilado .tbc → version_dir/linker.tbc + version_dir/<mod>.tmc
        """
        main_tbc = module_dir / "main.tbc"
        if not main_tbc.exists():
            raise ModuleError(f"main.tbc no encontrado en {module_dir}")

        version = self._read_main_tbc(main_tbc)
        if self._debug:
            print(f"[ModuleLoader] '{module_name}' versión: {version}")

        version_dir = module_dir / "versions" / version
        if not version_dir.exists():
            raise ModuleError(f"Directorio de versión no encontrado: {version_dir}")

        # ── A) Módulo nativo Python (native.py) ───────────────────────────
        native_py = version_dir / "native.py"
        if native_py.exists():
            self._load_native_python(module_name, version, native_py)
            return

        # ── B) Módulo compilado (.tmc + linker.tbc) ───────────────────────
        tmc_file = version_dir / f"{module_name}.tmc"
        if not tmc_file.exists():
            raise ModuleError(f"{module_name}.tmc no encontrado en {version_dir}")

        tmc_map = self._read_tmc(tmc_file, module_name)
        if self._debug:
            print(f"[ModuleLoader] TMC: "
                  f"{len(tmc_map['functions'])} funcs, "
                  f"{len(tmc_map['exports'])} exports")

        linker_file = version_dir / "linker.tbc"
        if not linker_file.exists():
            raise ModuleError(f"linker.tbc no encontrado en {version_dir}")

        from tsslk_decoder import decode_tbc
        linker_ast = decode_tbc(str(linker_file))

        iso = self._make_isolated_interpreter(linker_ast, module_name)
        self._modules[module_name] = _TbcModule(
            module_name, version, tmc_map, iso, debug=self._debug
        )
        if self._debug:
            print(f"[ModuleLoader] '{module_name}' v{version} (.tbc) cargado OK")

    def _load_native_python(self, module_name: str, version: str, native_py: Path):
        """
        Carga un módulo nativo Python desde native.py.
        El archivo debe exponer NATIVE_MODULE = {"module":..., "functions":..., "exports":...}
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            f"_tess_native_{module_name}", str(native_py)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not hasattr(mod, "NATIVE_MODULE"):
            raise ModuleError(
                f"{native_py} no expone NATIVE_MODULE. "
                f"Agrega NATIVE_MODULE = {{...}} al archivo."
            )

        self._modules[module_name] = _NativePythonModule(mod.NATIVE_MODULE)
        if self._debug:
            desc    = mod.NATIVE_MODULE
            print(f"[ModuleLoader] '{module_name}' v{version} (native.py) cargado OK")
            print(f"  funciones: {list(desc.get('functions', {}).keys())}")
            print(f"  exports:   {list(desc.get('exports', {}).keys())}")

    # ════════════════════════════════════════════════════════════════════
    #  Parseo de main.tbc
    # ════════════════════════════════════════════════════════════════════

    def _read_main_tbc(self, path: Path) -> str:
        """
        Lee el main.tbc y retorna la versión seleccionada.

        Formato:
          MAGIC(6) + VER(1) + pstr(module_name) + pstr(version) + pstr(v_count) + ...
        """
        from tss_bytemap import MAGIC_ORCH
        data = path.read_bytes()
        r    = _BinReader(data)

        magic = r.read(6)
        if magic != MAGIC_ORCH:
            raise ModuleError(
                f"main.tbc inválido en {path}: magic {magic!r} "
                f"(esperado {MAGIC_ORCH!r})"
            )

        r.ru8()                 # VER
        _module_name = r.rpstr()  # module_name (skip)
        version      = r.rpstr()  # version seleccionada ← esto es lo que nos importa
        # v_count y el resto no se necesitan aquí

        return version

    # ════════════════════════════════════════════════════════════════════
    #  Parseo de .tmc
    # ════════════════════════════════════════════════════════════════════

    def _read_tmc(self, path: Path, module_name: str) -> dict:
        """
        Lee el .tmc y retorna el mapa público:
          {
            "functions": {fname: {linker_id, params, return_type, native}},
            "exports":   {ename: {type, const, linker_id}},
            "classes":   {cname: {constructor: {...}, methods: {...}}}
          }

        El linker_id para exports y funciones se reconstruye como
        f"{module_name}_{name}" si no está explícito en el binario.
        """
        from tss_bytemap import (MAGIC_TMC, FLAG_NATIVE, FLAG_HAS_ID,
                                  FLAG_HAS_RETURN, TMC_CLASS_HAS_CTOR,
                                  TMC_CLASS_HAS_METHODS,
                                  TYPE_FLOAT, TYPE_INT, TYPE_STRING, TYPE_BOOL,
                                  parse_type_code)

        data = path.read_bytes()
        r    = _BinReader(data)

        magic = r.read(4)
        if magic != MAGIC_TMC:
            raise ModuleError(
                f".tmc inválido en {path}: magic {magic!r} "
                f"(esperado {MAGIC_TMC!r})"
            )
        r.ru8()              # FORMAT_VER
        _mod  = r.rpstr()   # module_name
        _ver  = r.rpstr()   # version
        _desc = r.rwstr()   # description

        result = {"functions": {}, "exports": {}, "classes": {}}

        # ── Exports ──────────────────────────────────────────────────────
        ecount = r.ru16()
        for _ in range(ecount):
            ename    = r.rpstr()
            etype    = r.rtype()
            eflags   = r.ru8()
            is_const = bool(eflags & 0x01)

            # Leer y descartar el valor almacenado (no lo usamos en librerías)
            tc = parse_type_code(etype.split("<")[0].split(":")[0])
            if   tc == TYPE_FLOAT:  r.rf64()
            elif tc == TYPE_INT:    r.ri64()
            elif tc == TYPE_STRING: r.rwstr()
            elif tc == TYPE_BOOL:   r.ru8()
            else:                   r.rwstr()   # fallback wstr

            result["exports"][ename] = {
                "type":      etype,
                "const":     is_const,
                # Linker_id reconstruido por convención: module_name + _ + export_name
                "linker_id": f"{module_name}_{ename}",
            }

        # ── Functions ─────────────────────────────────────────────────────
        fcount = r.ru16()
        for _ in range(fcount):
            fname  = r.rpstr()
            pcount = r.ru8()
            params = {}
            for _ in range(pcount):
                pname = r.rpstr(); ptype = r.rtype()
                params[pname] = ptype
            flags     = r.ru8()
            is_native = bool(flags & FLAG_NATIVE)
            has_id    = bool(flags & FLAG_HAS_ID)
            has_ret   = bool(flags & FLAG_HAS_RETURN)
            fid  = r.rpstr() if has_id  else f"{module_name}_{fname}"
            ret  = r.rtype() if has_ret else ""

            result["functions"][fname] = {
                "linker_id":   fid,
                "params":      params,
                "return_type": ret,
                "native":      is_native,
            }

        # ── Classes (sección opcional) ─────────────────────────────────────
        if not r.eof():
            try:
                ccount = r.ru16()
                for _ in range(ccount):
                    cname  = r.rpstr()
                    cflags = r.ru8()
                    cls    = {"constructor": None, "methods": {}}

                    if cflags & TMC_CLASS_HAS_CTOR:
                        pcount = r.ru8()
                        cparams = {}
                        for _ in range(pcount):
                            pname = r.rpstr(); ptype = r.rtype()
                            cparams[pname] = ptype
                        cf  = r.ru8()
                        cid = r.rpstr() if cf & FLAG_HAS_ID     else f"{module_name}_{cname}_new"
                        crt = r.rtype() if cf & FLAG_HAS_RETURN else ""
                        cls["constructor"] = {
                            "linker_id": cid, "params": cparams, "return_type": crt
                        }

                    if cflags & TMC_CLASS_HAS_METHODS:
                        mcount = r.ru16()
                        for _ in range(mcount):
                            mname   = r.rpstr()
                            pcount  = r.ru8()
                            mparams = {}
                            for _ in range(pcount):
                                pname = r.rpstr(); ptype = r.rtype()
                                mparams[pname] = ptype
                            mf  = r.ru8()
                            mid = r.rpstr() if mf & FLAG_HAS_ID     else f"{module_name}_{cname}_{mname}"
                            mrt = r.rtype() if mf & FLAG_HAS_RETURN else ""
                            cls["methods"][mname] = {
                                "linker_id": mid, "params": mparams, "return_type": mrt
                            }

                    result["classes"][cname] = cls
            except Exception:
                # Sección de clases corrupta o ausente — no es fatal
                pass

        return result

    # ════════════════════════════════════════════════════════════════════
    #  Intérprete aislado para ejecutar el linker
    # ════════════════════════════════════════════════════════════════════

    def _make_isolated_interpreter(self, linker_ast: dict, module_name: str):
        """
        Crea un Interpreter aislado, ejecuta el linker AST en él y lo retorna.
        Lazy import de interpre.Interpreter para evitar import circular.
        """
        from interpre import Interpreter
        iso = Interpreter(debug_mode=self._debug)
        iso.interpret(linker_ast, source_path=f"<linker:{module_name}>")
        return iso

    # ════════════════════════════════════════════════════════════════════
    #  Localización del directorio libs/
    # ════════════════════════════════════════════════════════════════════

    def _get_libs_path(self) -> Path | None:
        """
        Localiza el directorio global de libs de Tesseract.

        Orden de búsqueda:
          Windows:  %LOCALAPPDATA%\\Tesseract\\libs
                    %APPDATA%\\Tesseract\\libs
          Linux:    ~/.local/share/tesseract/libs
          macOS:    ~/Library/Application Support/tesseract/libs

        Cachea el resultado para no re-buscar en cada llamada.
        """
        if self._libs_path_resolved:
            return self._libs_path

        self._libs_path_resolved = True
        candidates: list[Path] = []

        if os.name == "nt":   # Windows
            local   = os.environ.get("LOCALAPPDATA", "")
            roaming = os.environ.get("APPDATA", "")
            if local:   candidates.append(Path(local)   / "Tesseract" / "libs")
            if roaming: candidates.append(Path(roaming) / "Tesseract" / "libs")
        else:                  # Linux / macOS
            home = Path.home()
            candidates.append(home / ".local" / "share" / "tesseract" / "libs")
            candidates.append(home / "Library" / "Application Support" / "tesseract" / "libs")

        for p in candidates:
            if p.exists():
                self._libs_path = p
                if self._debug:
                    print(f"[ModuleLoader] libs/ encontrado en: {p}")
                return p

        if self._debug:
            print(f"[ModuleLoader] libs/ no encontrado. Buscado en:")
            for p in candidates:
                print(f"  {p}")

        self._libs_path = None
        return None