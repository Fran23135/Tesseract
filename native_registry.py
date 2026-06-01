import math as _math
import sys
import tkinter as _tk
from tkinter import ttk as _ttk
from tkinter import messagebox as _msgbox
from tkinter import filedialog as _filedialog
from tkinter import colorchooser as _colorchooser
from tkinter import simpledialog as _simpledialog
from tkinter import font as _tkfont

# ==============================================================================
# Estado global
# ==============================================================================
_current_interpreter = None
_ui_state = {"root": None}

# ==============================================================================
# Helpers internos
# ==============================================================================

def _invoke_callback(callback, *extra_args):
    """Invoca un callback del lenguaje (string con nombre de función)."""
    if _current_interpreter is None or not callback:
        return
    try:
        call_node = {
            "FunctionCall": {
                "function": callback,
                "paramenters": {"value": ""}
            }
        }
        _current_interpreter.execute_node(call_node)
    except Exception as e:
        print(f"[ui] Error en callback '{callback}': {e}")

def _opt(args, i, default=None, convert=None):
    if len(args) > i:
        val = args[i]
        if convert is not None:
            try:
                return convert(val)
            except (ValueError, TypeError):
                return default
        return val
    return default

_CURSOR_MAP = {
    "pointer":   "hand2",
    "default":   "arrow",
    "text":      "xterm",
    "grab":      "fleur",
    "crosshair": "crosshair",
}

def _apply_style(widget, key, value):
    """Aplica una clave de estilo directamente al widget tkinter."""
    try:
        if key in ("width",):
            widget.configure(width=int(value))
        elif key in ("height",):
            widget.configure(height=int(value))
        elif key == "background":
            widget.configure(bg=value)
        elif key == "color":
            widget.configure(fg=value)
        elif key == "opacity":
            pass  # por widget no soportado en tkinter
        elif key == "fontSize":
            pass  # manejado por setFont
        elif key == "cursor":
            widget.configure(cursor=_CURSOR_MAP.get(str(value), str(value)))
        elif key == "borderRadius":
            pass  # no soportado nativo en tkinter
        elif key in ("margin", "marginTop", "marginBottom",
                     "marginLeft", "marginRight"):
            pass
        elif key in ("padding", "paddingTop", "paddingBottom",
                     "paddingLeft", "paddingRight"):
            widget.configure(padx=int(value), pady=int(value))
        elif key == "zIndex":
            widget.lift() if int(value) > 0 else widget.lower()
        elif key == "overflow":
            pass
    except Exception:
        pass

def _parse_size(value):
    """Convierte "auto", "100%", o int a algo útil para tkinter."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.endswith("%"):
        return value  # se ignora en pack/place si no aplica
    return None


# ==============================================================================
# _UIInterface — Ventana raíz
# ==============================================================================
class _UIInterface:
    def __init__(self, title="Ventana", width=800, height=600, mode="window"):
        root = _tk.Tk()
        root.title(str(title))
        if mode == "fullscreen":
            root.attributes("-fullscreen", True)
        else:
            root.geometry(f"{int(width)}x{int(height)}")
        self._root   = root
        self._mode   = mode
        self._container = None
        _ui_state["root"] = root

    def mount(self, container):
     self._container = container
     container._build(self._root)
     self._root.update_idletasks()
     # No reconstruyas los hijos, ya se construyeron en _build

    def run(self):
        self._root.mainloop()

    def show(self):
        self._root.deiconify()

    def hide(self):
        self._root.withdraw()

    def close(self):
        self._root.destroy()

    def setTitle(self, title):
        self._root.title(str(title))

    def setSize(self, width, height):
        self._root.geometry(f"{int(width)}x{int(height)}")

    def setMinSize(self, width, height):
        self._root.minsize(int(width), int(height))

    def setResizable(self, value):
        b = bool(value)
        self._root.resizable(b, b)

    def setIcon(self, path):
        try:
            self._root.iconbitmap(str(path))
        except Exception:
            pass

    def setTheme(self, theme):
        # tkinter no tiene soporte de tema nativo universal
        if theme == "dark":
            try:
                self._root.configure(bg="#1e1e1e")
            except Exception:
                pass

    def setBackground(self, color):
        self._root.configure(bg=str(color))

    def center(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        ww = self._root.winfo_width()
        wh = self._root.winfo_height()
        x  = (sw - ww) // 2
        y  = (sh - wh) // 2
        self._root.geometry(f"+{x}+{y}")

    def onClose(self, callback):
        self._root.protocol("WM_DELETE_WINDOW",
                            lambda: _invoke_callback(callback))

    def onResize(self, callback):
        self._root.bind("<Configure>",
                        lambda e: _invoke_callback(callback))

    def onFocus(self, callback):
        self._root.bind("<FocusIn>",
                        lambda e: _invoke_callback(callback))

    def onBlur(self, callback):
        self._root.bind("<FocusOut>",
                        lambda e: _invoke_callback(callback))


# ==============================================================================
# _UIContainer — Contenedor universal de layout
# ==============================================================================
class _UIContainer:
    def __init__(self, layout="column", id=None):
        self._layout       = layout
        self._id           = id
        self._widget       = None
        self._inner        = None   # frame interior (para scroll)
        self._children     = []
        self._spacing      = 0
        self._padding      = (0, 0, 0, 0)   # top right bottom left
        self._bg           = None
        self._scroll       = "none"
        self._grid_cols    = 1
        self._grid_rows    = 1
        self._grid_gap     = 0
        self._align_main   = "start"
        self._align_cross  = "start"
        # posición dentro de un padre grid
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent_widget):
        print(f"[Container] Construyendo {len(self._children)} hijos: {self._children}")
        kw = {}
        if self._bg:
            kw["bg"] = self._bg

        if self._scroll != "none":
            outer  = _tk.Frame(parent_widget, **kw)
            canvas = _tk.Canvas(outer, **kw, highlightthickness=0)
            inner  = _tk.Frame(canvas, **kw)

            if self._scroll in ("y", "both"):
                vsb = _tk.Scrollbar(outer, orient="vertical",
                                    command=canvas.yview)
                vsb.pack(side="right", fill="y")
                canvas.configure(yscrollcommand=vsb.set)
            if self._scroll in ("x", "both"):
                hsb = _tk.Scrollbar(outer, orient="horizontal",
                                    command=canvas.xview)
                hsb.pack(side="bottom", fill="x")
                canvas.configure(xscrollcommand=hsb.set)

            canvas.pack(side="left", fill="both", expand=True)
            win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _on_inner_configure(e):
                canvas.configure(scrollregion=canvas.bbox("all"))
            inner.bind("<Configure>", _on_inner_configure)

            def _on_canvas_configure(e):
                canvas.itemconfig(win_id, width=e.width)
            canvas.bind("<Configure>", _on_canvas_configure)

            self._widget = outer
            self._inner  = inner
        else:
            frame = _tk.Frame(parent_widget, **kw)
            self._widget = frame
            self._inner  = frame
            self._widget.pack(fill="both", expand=True)

        # Configurar grid si aplica
        if self._layout == "grid":
            for c in range(self._grid_cols):
                self._inner.columnconfigure(c, weight=1)
            for r in range(self._grid_rows):
                self._inner.rowconfigure(r, weight=1)

        # Construir hijos ya registrados
        for child in self._children:
            self._build_child(child)

    def _build_child(self, child):
     
     print(f"Construyendo hijo: {child}")
     child._build(self._inner)
     w = child._widget
     if w is None:
        print("ERROR: widget del hijo es None en _UIContainer._build_child") 
        return

     top, right, bottom, left = self._padding
     gap = self._spacing

     if self._layout == "column":
        pack_opts = {'side': 'top', 'fill': 'x', 'expand': True,
                     'padx': (left, right), 'pady': (0, gap)}
        w.pack(**pack_opts)
        child._pack_opts = pack_opts   # Guardar para setVisible
     elif self._layout == "row":
        pack_opts = {'side': 'left', 'fill': 'y', 'expand': True,
                     'padx': (0, gap), 'pady': (top, bottom)}
        w.pack(**pack_opts)
        child._pack_opts = pack_opts
     elif self._layout == "grid":
        w.grid(
            column=child._grid_col,
            row=child._grid_row,
            columnspan=child._grid_colspan,
            rowspan=child._grid_rowspan,
            padx=self._grid_gap // 2,
            pady=self._grid_gap // 2,
            sticky="nsew",
        )
        child._grid_opts = True  # marcador
     elif self._layout == "stack":
        w.place(relx=0, rely=0, relwidth=1, relheight=1)
        child._place_opts = True
     elif self._layout == "absolute":
        pass

     # Aplicar visibilidad inicial si el hijo tiene flag _visible = False
     if hasattr(child, '_visible') and not child._visible:
        if self._layout == "column" or self._layout == "row":
            w.pack_forget()
        elif self._layout == "grid":
            w.grid_remove()
        elif self._layout == "stack":
            w.place_forget()
    def add(self, component):
        print(f"[Container] add llamado con {component} (tipo {type(component)})")
        self._children.append(component)
        if self._widget is not None:
            self._build_child(component)

    def addAt(self, component, index):
        self._children.insert(int(index), component)
        if self._widget is not None:
            self._build_child(component)

    def remove(self, id):
        for i, child in enumerate(self._children):
            if getattr(child, "_id", None) == id:
                if child._widget:
                    child._widget.destroy()
                self._children.pop(i)
                return

    def clear(self):
        for child in self._children:
            if child._widget:
                child._widget.destroy()
        self._children = []

    def get(self, id):
        for child in self._children:
            if getattr(child, "_id", None) == id:
                return child
        return None

    def setSpacing(self, value):
        self._spacing = int(value)

    def setPadding(self, top, right, bottom, left):
        self._padding = (int(top), int(right), int(bottom), int(left))
        if self._inner:
            self._inner.configure(padx=int(right), pady=int(top))

    def setAlign(self, main, cross):
        self._align_main  = main
        self._align_cross = cross

    def setScroll(self, axis):
        self._scroll = axis

    def setBackground(self, color):
        self._bg = color
        if self._widget:
            self._widget.configure(bg=color)
        if self._inner and self._inner is not self._widget:
            self._inner.configure(bg=color)

    def setBorder(self, width, color, radius):
        if self._widget:
            self._widget.configure(
                bd=int(width),
                relief="solid",
                highlightbackground=color,
                highlightthickness=int(width),
            )

    def setSize(self, width, height):
        if self._widget:
            w = _parse_size(width)
            h = _parse_size(height)
            if isinstance(w, int):
                self._widget.configure(width=w)
            if isinstance(h, int):
                self._widget.configure(height=h)

    def setVisible(self, value):
     if not hasattr(self, '_widget') or self._widget is None:
        self._visible = bool(value)
        return
     if value:
        opts = getattr(self, '_pack_opts', None)
        if opts is not None:
            self._widget.pack(**opts)
        else:
            # Fallback si no hay opciones guardadas
            self._widget.pack(side="top", fill="x", expand=True)
        self._widget.master.update_idletasks()
     else:
        # Guardar opciones actuales antes de ocultar
        self._pack_opts = self._widget.pack_info()
        self._widget.pack_forget()
     self._visible = bool(value)

    def setId(self, id):
        self._id = id

    def setGrid(self, cols, rows, gap):
        self._grid_cols = int(cols)
        self._grid_rows = int(rows)
        self._grid_gap  = int(gap)
        if self._inner:
            for c in range(int(cols)):
                self._inner.columnconfigure(c, weight=1)
            for r in range(int(rows)):
                self._inner.rowconfigure(r, weight=1)

    def gridPlace(self, col, row, colspan, rowspan):
        self._grid_col     = int(col)
        self._grid_row     = int(row)
        self._grid_colspan = int(colspan)
        self._grid_rowspan = int(rowspan)

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UILabel
# ==============================================================================
class _UILabel:
    def __init__(self, text="", id=None):
        self._text   = str(text)
        self._id     = id
        self._widget = None
        self._font   = ("TkDefaultFont", 12, "normal")
        self._color  = None
        self._align  = "left"
        self._wrap   = False
        self._visible = True
        self._pending_size = None      # (width, height)
        self._pending_bg = None
        # grid placement
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        if parent is None:
            raise RuntimeError("No se puede construir Label sin padre")
        # Mapear align a anchor válido para Tkinter
        anchor_map = {"left": "w", "center": "center", "right": "e"}
        anchor_val = anchor_map.get(self._align, "w")
        kw = {"text": self._text, "anchor": anchor_val,
              "justify": self._align, "font": self._font}
        if self._color:
            kw["fg"] = self._color
        if self._wrap:
            kw["wraplength"] = 400
        self._widget = _tk.Label(parent, **kw)
        # Aplicar propiedades pendientes
        if self._pending_size:
            w, h = self._pending_size
            self._widget.config(width=int(w), height=int(h))
        if self._pending_bg:
            self._widget.config(bg=self._pending_bg)
        # Si debe estar oculto, lo ocultamos después de que el contenedor lo empaquete
        parent.after_idle(self._apply_initial_visibility)

    def _apply_initial_visibility(self):
        if not self._visible and self._widget:
            self._widget.pack_forget()

    def setText(self, text):
        self._text = str(text)
        if self._widget:
            self._widget.configure(text=self._text)

    def getText(self):
        return self._text

    def setFont(self, family, size, weight):
        tk_weight = "bold" if weight == "bold" else "normal"
        self._font = (str(family), int(size), tk_weight)
        if self._widget:
            self._widget.configure(font=self._font)

    def setColor(self, color):
        self._color = color
        if self._widget:
            self._widget.configure(fg=color)

    def setAlign(self, align):
        self._align = align
        anchor_map = {"left": "w", "center": "center", "right": "e"}
        if self._widget:
            self._widget.configure(anchor=anchor_map.get(align, "w"),
                                   justify=align)

    def setWrap(self, value):
        self._wrap = bool(value)
        if self._widget:
            self._widget.configure(wraplength=400 if value else 0)

    def setSize(self, width, height):
        self._pending_size = (int(width), int(height))
        if self._widget:
            self._widget.config(width=int(width), height=int(height))

    def setBackground(self, color):
        self._pending_bg = color
        if self._widget:
            self._widget.config(bg=color)

    def setVisible(self, value):
        self._visible = bool(value)
        if self._widget is None:
            return
        if value:
            if self._widget.winfo_ismapped():
                return
            opts = getattr(self, '_pack_opts', None)
            if opts is None:
                opts = {'side': 'top', 'fill': 'x', 'expand': False}
            self._widget.pack(**opts)
        else:
            if self._widget.winfo_ismapped():
                self._pack_opts = self._widget.pack_info()
                self._widget.pack_forget()

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)
# ==============================================================================
# _UIButton
# ==============================================================================
class _UIButton:
    def __init__(self, text="", id=None):
        self._text      = str(text)
        self._id        = id
        self._widget    = None
        self._enabled   = True
        self._loading   = False
        self._variant   = "primary"
        self._size      = "md"
        self._full      = False
        self._icon      = None
        self._icon_pos  = "left"
        
        # grid placement
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1
        

    def _get_variant_colors(self):
        variants = {
            "primary":   ("#0066cc", "white"),
            "secondary": ("#6c757d", "white"),
            "danger":    ("#dc3545", "white"),
            "ghost":     ("#f0f0f0", "#333333"),
            "link":      ("white",   "#0066cc"),
            "outline":   ("white",   "#0066cc"),
        }
        return variants.get(self._variant, ("#0066cc", "white"))

    def _get_size_font(self):
        return {"sm": 9, "md": 11, "lg": 14}.get(self._size, 11)

    def _build(self, parent):
        bg, fg  = self._get_variant_colors()
        fsize   = self._get_size_font()
        relief  = "flat" if self._variant in ("ghost", "link") else "raised"
        if self._variant == "outline":
            relief = "groove"
        kw = {
            "text":    self._text,
            "bg":      bg,
            "fg":      fg,
            "font":    ("TkDefaultFont", fsize),
            "relief":  relief,
            "bd":      1,
            "state":   "normal" if self._enabled else "disabled",
            "cursor":  "hand2",
        }
        if self._full:
            kw["width"] = 100
        self._widget = _tk.Button(parent, **kw)
        if hasattr(self, '_on_click') and self._on_click:
            cb = self._on_click
            self._widget.configure(command=lambda: _invoke_callback(cb))

    def setText(self, text):
        self._text = str(text)
        if self._widget:
            self._widget.configure(text=self._text)

    def setIcon(self, path, position="left"):
        self._icon     = path
        self._icon_pos = position
        # En tkinter se puede usar PhotoImage; por ahora solo almacenamos

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setVariant(self, variant):
        self._variant = variant
        if self._widget:
            bg, fg = self._get_variant_colors()
            self._widget.configure(bg=bg, fg=fg)

    def setSize(self, size):
        self._size = size
        if self._widget:
            self._widget.configure(font=("TkDefaultFont", self._get_size_font()))

    def setFullWidth(self, value):
        self._full = bool(value)
        if self._widget and value:
            self._widget.pack(fill="x")

    def setLoading(self, value):
        self._loading = bool(value)
        if self._widget:
            self._widget.configure(
                state="disabled" if value else ("normal" if self._enabled else "disabled"),
                text="..." if value else self._text,
            )

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack()
            else:
                self._widget.pack_forget()

    def onClick(self, callback):
        if self._widget:
            self._widget.configure(command=lambda: _invoke_callback(callback))
        self._on_click = callback

    def onHover(self, callback):
        if self._widget:
            self._widget.bind("<Enter>", lambda e: _invoke_callback(callback))

    def onFocus(self, callback):
        if self._widget:
            self._widget.bind("<FocusIn>", lambda e: _invoke_callback(callback))

    def onBlur(self, callback):
        if self._widget:
            self._widget.bind("<FocusOut>", lambda e: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UIInput
# ==============================================================================
class _UIInput:
    def __init__(self, placeholder="", id=None):
        self._placeholder = str(placeholder)
        self._id          = id
        self._widget      = None
        self._frame       = None   # contenedor con label/hint/error
        self._label_w     = None
        self._hint_w      = None
        self._error_w     = None
        self._var         = None
        self._type        = "text"
        self._enabled     = True
        self._readonly    = False
        self._maxlen      = None
        self._label_text  = ""
        self._hint_text   = ""
        # grid placement
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._frame = _tk.Frame(parent)
        self._frame.pack(fill="x")

        if self._label_text:
            self._label_w = _tk.Label(self._frame, text=self._label_text,
                                      anchor="w")
            self._label_w.pack(fill="x")

        self._var = _tk.StringVar()
        show = "*" if self._type == "password" else ""
        kw   = {
            "textvariable": self._var,
            "show":         show,
            "state":        "normal" if self._enabled else "disabled",
        }
        if self._maxlen:
            kw["validate"]    = "key"
            kw["validatecommand"] = (self._frame.register(
                lambda v: len(v) <= self._maxlen), "%P")

        self._widget = _tk.Entry(self._frame, **kw)
        self._widget.pack(fill="x")

        # Placeholder simulado
        if self._placeholder:
            self._widget.insert(0, self._placeholder)
            self._widget.configure(fg="grey")
            self._widget.bind("<FocusIn>",  self._on_focus_placeholder)
            self._widget.bind("<FocusOut>", self._on_blur_placeholder)

        if self._hint_text:
            self._hint_w = _tk.Label(self._frame, text=self._hint_text,
                                     fg="grey", anchor="w", font=("TkDefaultFont", 9))
            self._hint_w.pack(fill="x")

        self._widget_parent = parent

    def _on_focus_placeholder(self, e):
        if self._widget.get() == self._placeholder:
            self._widget.delete(0, "end")
            self._widget.configure(fg="black")

    def _on_blur_placeholder(self, e):
        if not self._widget.get():
            self._widget.insert(0, self._placeholder)
            self._widget.configure(fg="grey")

    def setValue(self, value):
        if self._var:
            self._var.set(str(value))

    def getValue(self):
        if self._var:
            v = self._var.get()
            if v == self._placeholder:
                return ""
            return v
        return ""

    def setPlaceholder(self, text):
        self._placeholder = str(text)

    def setType(self, type_):
        self._type = type_
        if self._widget:
            self._widget.configure(show="*" if type_ == "password" else "")

    def setLabel(self, text):
        self._label_text = str(text)
        if self._label_w:
            self._label_w.configure(text=text)
        elif self._frame:
            self._label_w = _tk.Label(self._frame, text=text, anchor="w")
            self._label_w.pack(fill="x")

    def setHint(self, text):
        self._hint_text = str(text)
        if self._hint_w:
            self._hint_w.configure(text=text)
        elif self._frame:
            self._hint_w = _tk.Label(self._frame, text=text, fg="grey",
                                     anchor="w", font=("TkDefaultFont", 9))
            self._hint_w.pack(fill="x")

    def setError(self, message):
        if self._widget:
            self._widget.configure(highlightbackground="red",
                                   highlightthickness=1)
        if self._frame:
            if self._error_w:
                self._error_w.configure(text=message)
            else:
                self._error_w = _tk.Label(self._frame, text=message,
                                          fg="red", anchor="w",
                                          font=("TkDefaultFont", 9))
                self._error_w.pack(fill="x")

    def clearError(self):
        if self._widget:
            self._widget.configure(highlightthickness=0)
        if self._error_w:
            self._error_w.destroy()
            self._error_w = None

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setReadOnly(self, value):
        self._readonly = bool(value)
        if self._widget:
            self._widget.configure(state="readonly" if value else "normal")

    def setMaxLength(self, value):
        self._maxlen = int(value)

    def setPattern(self, regex):
        pass  # validación regex — se puede implementar vía validatecommand

    def clear(self):
        if self._var:
            self._var.set("")

    def focus(self):
        if self._widget:
            self._widget.focus_set()

    def setVisible(self, value):
        if self._frame:
            if value:
                self._frame.pack(fill="x")
            else:
                self._frame.pack_forget()

    def onChange(self, callback):
        if self._var:
            self._var.trace_add("write",
                                lambda *_: _invoke_callback(callback))

    def onSubmit(self, callback):
        if self._widget:
            self._widget.bind("<Return>",
                              lambda e: _invoke_callback(callback))

    def onFocus(self, callback):
        if self._widget:
            self._widget.bind("<FocusIn>",
                              lambda e: _invoke_callback(callback))

    def onBlur(self, callback):
        if self._widget:
            self._widget.bind("<FocusOut>",
                              lambda e: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UITextArea (extiende _UIInput)
# ==============================================================================
class _UITextArea(_UIInput):
    def __init__(self, placeholder="", id=None):
        super().__init__(placeholder, id)
        self._rows   = 5
        self._resize = "both"

    def _build(self, parent):
        self._frame = _tk.Frame(parent)
        self._frame.pack(fill="x")

        if self._label_text:
            self._label_w = _tk.Label(self._frame, text=self._label_text,
                                      anchor="w")
            self._label_w.pack(fill="x")

        self._widget = _tk.Text(self._frame, height=self._rows,
                                state="normal" if self._enabled else "disabled",
                                wrap="word")
        self._widget.pack(fill="both", expand=True)

        if self._hint_text:
            self._hint_w = _tk.Label(self._frame, text=self._hint_text,
                                     fg="grey", anchor="w",
                                     font=("TkDefaultFont", 9))
            self._hint_w.pack(fill="x")

    def getValue(self):
        if self._widget and isinstance(self._widget, _tk.Text):
            return self._widget.get("1.0", "end-1c")
        return ""

    def setValue(self, value):
        if self._widget and isinstance(self._widget, _tk.Text):
            self._widget.delete("1.0", "end")
            self._widget.insert("1.0", str(value))

    def setRows(self, value):
        self._rows = int(value)
        if self._widget:
            self._widget.configure(height=int(value))

    def setResize(self, mode):
        self._resize = mode
        # Tkinter Text no soporta resize CSS; ignorado en este runtime

    def onChange(self, callback):
        if self._widget and isinstance(self._widget, _tk.Text):
            self._widget.bind("<<Modified>>",
                              lambda e: _invoke_callback(callback))

    def clear(self):
        if self._widget and isinstance(self._widget, _tk.Text):
            self._widget.delete("1.0", "end")


# ==============================================================================
# _UISelect
# ==============================================================================
class _UISelect:
    def __init__(self, placeholder="", id=None):
        self._placeholder = str(placeholder)
        self._id          = id
        self._widget      = None
        self._var         = None
        self._options     = []   # [(value, label), ...]
        self._multiple    = False
        self._searchable  = False
        self._enabled     = True
        # grid placement
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var    = _tk.StringVar()
        labels       = [lbl for _, lbl in self._options]
        self._widget = _ttk.Combobox(parent, textvariable=self._var,
                                     values=labels,
                                     state="readonly" if not self._searchable
                                     else "normal")
        if self._placeholder:
            self._widget.set(self._placeholder)
        self._widget.pack(fill="x")

    def addOption(self, value, label):
        self._options.append((str(value), str(label)))
        if self._widget:
            self._widget.configure(values=[lbl for _, lbl in self._options])

    def addOptions(self, data):
        for item in data:
            self._options.append((str(item["value"]), str(item["label"])))
        if self._widget:
            self._widget.configure(values=[lbl for _, lbl in self._options])

    def setValue(self, value):
        for val, lbl in self._options:
            if val == str(value):
                if self._var:
                    self._var.set(lbl)
                return

    def getValue(self):
        if not self._var:
            return ""
        label = self._var.get()
        for val, lbl in self._options:
            if lbl == label:
                return val
        return ""

    def getValueAll(self):
        return [self.getValue()]

    def setMultiple(self, value):
        self._multiple = bool(value)

    def setSearchable(self, value):
        self._searchable = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "readonly")

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="disabled" if not value else
                                   ("normal" if self._searchable else "readonly"))

    def clear(self):
        self._options = []
        if self._widget:
            self._widget.configure(values=[])

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(fill="x")
            else:
                self._widget.pack_forget()

    def onChange(self, callback):
        if self._widget:
            self._widget.bind("<<ComboboxSelected>>",
                              lambda e: _invoke_callback(callback))

    def style(self, key, value):
        pass  # ttk no soporta configure directo fácilmente


# ==============================================================================
# _UICheckbox
# ==============================================================================
class _UICheckbox:
    def __init__(self, label="", id=None):
        self._label   = str(label)
        self._id      = id
        self._widget  = None
        self._var     = None
        self._enabled = True
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var    = _tk.BooleanVar()
        self._widget = _tk.Checkbutton(parent, text=self._label,
                                       variable=self._var,
                                       state="normal" if self._enabled else "disabled")
        self._widget.pack(anchor="w")

    def setValue(self, value):
        if self._var:
            self._var.set(bool(value))

    def getValue(self):
        return bool(self._var.get()) if self._var else False

    def setLabel(self, text):
        self._label = str(text)
        if self._widget:
            self._widget.configure(text=text)

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(anchor="w")
            else:
                self._widget.pack_forget()

    def onChange(self, callback):
        if self._var:
            self._var.trace_add("write",
                                lambda *_: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UIRadio
# ==============================================================================
class _UIRadio:
    def __init__(self, name="", id=None):
        self._name    = str(name)
        self._id      = id
        self._frame   = None
        self._var     = None
        self._options = []   # [(value, label), ...]
        self._buttons = []
        self._layout  = "column"
        self._enabled = True
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var   = _tk.StringVar()
        self._frame = _tk.Frame(parent)
        side = "left" if self._layout == "row" else "top"
        self._frame.pack(fill="x")
        for val, lbl in self._options:
            rb = _tk.Radiobutton(self._frame, text=lbl, variable=self._var,
                                 value=val,
                                 state="normal" if self._enabled else "disabled")
            rb.pack(side=side, anchor="w")
            self._buttons.append(rb)

    def addOption(self, value, label):
        self._options.append((str(value), str(label)))
        if self._frame and self._var:
            side = "left" if self._layout == "row" else "top"
            rb   = _tk.Radiobutton(self._frame, text=str(label),
                                   variable=self._var, value=str(value))
            rb.pack(side=side, anchor="w")
            self._buttons.append(rb)

    def setValue(self, value):
        if self._var:
            self._var.set(str(value))

    def getValue(self):
        return self._var.get() if self._var else ""

    def setLayout(self, layout):
        self._layout = layout

    def setEnabled(self, value):
        self._enabled = bool(value)
        for rb in self._buttons:
            rb.configure(state="normal" if value else "disabled")

    def setVisible(self, value):
        if self._frame:
            if value:
                self._frame.pack(fill="x")
            else:
                self._frame.pack_forget()

    def onChange(self, callback):
        if self._var:
            self._var.trace_add("write",
                                lambda *_: _invoke_callback(callback))

    def style(self, key, value):
        if self._frame:
            _apply_style(self._frame, key, value)


# ==============================================================================
# _UIToggle
# ==============================================================================
class _UIToggle:
    def __init__(self, label="", id=None):
        self._label   = str(label)
        self._id      = id
        self._widget  = None
        self._var     = None
        self._enabled = True
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var    = _tk.BooleanVar()
        # Tkinter no tiene un Toggle nativo; usamos Checkbutton con estilo
        self._widget = _tk.Checkbutton(parent, text=self._label,
                                       variable=self._var,
                                       indicatoron=False,
                                       selectcolor="#0066cc",
                                       bg="#cccccc",
                                       relief="flat",
                                       state="normal" if self._enabled else "disabled")
        self._widget.pack(anchor="w")

    def setValue(self, value):
        if self._var:
            self._var.set(bool(value))

    def getValue(self):
        return bool(self._var.get()) if self._var else False

    def setLabel(self, text):
        self._label = str(text)
        if self._widget:
            self._widget.configure(text=text)

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(anchor="w")
            else:
                self._widget.pack_forget()

    def onChange(self, callback):
        if self._var:
            self._var.trace_add("write",
                                lambda *_: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UISlider
# ==============================================================================
class _UISlider:
    def __init__(self, min_=0, max_=100, step=1, id=None):
        self._min         = float(min_)
        self._max         = float(max_)
        self._step        = float(step)
        self._id          = id
        self._widget      = None
        self._var         = None
        self._orientation = "horizontal"
        self._enabled     = True
        self._on_release  = None
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var    = _tk.DoubleVar(value=self._min)
        orient       = "horizontal" if self._orientation == "horizontal" else "vertical"
        self._widget = _tk.Scale(parent,
                                 from_=self._min, to=self._max,
                                 resolution=self._step,
                                 orient=orient,
                                 variable=self._var,
                                 state="normal" if self._enabled else "disabled")
        self._widget.pack(fill="x")
        if self._on_release:
            self._widget.bind("<ButtonRelease-1>",
                              lambda e: _invoke_callback(self._on_release))

    def setValue(self, value):
        if self._var:
            self._var.set(float(value))

    def getValue(self):
        return self._var.get() if self._var else self._min

    def setRange(self, min_, max_):
        self._min = float(min_)
        self._max = float(max_)
        if self._widget:
            self._widget.configure(from_=self._min, to=self._max)

    def setStep(self, value):
        self._step = float(value)
        if self._widget:
            self._widget.configure(resolution=float(value))

    def setOrientation(self, orientation):
        self._orientation = orientation
        if self._widget:
            self._widget.configure(orient=orientation)

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(fill="x")
            else:
                self._widget.pack_forget()

    def onChange(self, callback):
        if self._widget:
            self._widget.configure(command=lambda v: _invoke_callback(callback))

    def onRelease(self, callback):
        self._on_release = callback
        if self._widget:
            self._widget.bind("<ButtonRelease-1>",
                              lambda e: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UIImage
# ==============================================================================
class _UIImage:
    def __init__(self, src="", id=None):
        self._src     = str(src)
        self._id      = id
        self._widget  = None
        self._photo   = None
        self._alt     = ""
        self._w       = 0
        self._h       = 0
        self._fit     = "contain"
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._widget = _tk.Label(parent)
        self._widget.pack()
        self._load_image()

    def _load_image(self):
        if not self._src or not self._widget:
            return
        try:
            self._photo = _tk.PhotoImage(file=self._src)
            self._widget.configure(image=self._photo)
        except Exception:
            if self._alt:
                self._widget.configure(text=self._alt)

    def setSrc(self, path):
        self._src = str(path)
        self._load_image()

    def setAlt(self, text):
        self._alt = str(text)

    def setSize(self, width, height):
        self._w = int(width)
        self._h = int(height)
        if self._widget:
            self._widget.configure(width=int(width), height=int(height))

    def setFit(self, fit):
        self._fit = fit

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack()
            else:
                self._widget.pack_forget()

    def onClick(self, callback):
        if self._widget:
            self._widget.bind("<Button-1>",
                              lambda e: _invoke_callback(callback))

    def onLoad(self, callback):
        self._on_load = callback

    def onError(self, callback):
        self._on_error = callback

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UIProgress
# ==============================================================================
class _UIProgress:
    def __init__(self, value=0, max_=100, id=None):
        self._value         = float(value)
        self._max           = float(max_)
        self._id            = id
        self._widget        = None
        self._var           = None
        self._mode          = "bar"
        self._label_text    = ""
        self._indeterminate = False
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var    = _tk.DoubleVar(value=self._value)
        self._widget = _ttk.Progressbar(parent,
                                        variable=self._var,
                                        maximum=self._max,
                                        mode="indeterminate" if self._indeterminate
                                        else "determinate",
                                        orient="horizontal")
        self._widget.pack(fill="x")
        if self._indeterminate:
            self._widget.start()

    def setValue(self, value):
        self._value = float(value)
        if self._var:
            self._var.set(float(value))

    def setMax(self, value):
        self._max = float(value)
        if self._widget:
            self._widget.configure(maximum=float(value))

    def setMode(self, mode):
        self._mode = mode
        if self._widget:
            orient = "horizontal"
            self._widget.configure(orient=orient)

    def setLabel(self, text):
        self._label_text = str(text)

    def setIndeterminate(self, value):
        self._indeterminate = bool(value)
        if self._widget:
            if value:
                self._widget.configure(mode="indeterminate")
                self._widget.start()
            else:
                self._widget.stop()
                self._widget.configure(mode="determinate")

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(fill="x")
            else:
                self._widget.pack_forget()

    def style(self, key, value):
        pass  # ttk no permite configure directo


# ==============================================================================
# _UISpinner
# ==============================================================================
class _UISpinner:
    def __init__(self, size="md", id=None):
        self._size   = size
        self._id     = id
        self._widget = None
        self._color  = "#0066cc"
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        sz = {"sm": 16, "md": 24, "lg": 40}.get(self._size, 24)
        self._widget = _ttk.Progressbar(parent, mode="indeterminate",
                                        length=sz, orient="horizontal")
        self._widget.pack()
        self._widget.start()

    def setSize(self, size):
        self._size = size

    def setColor(self, color):
        self._color = color

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack()
                self._widget.start()
            else:
                self._widget.stop()
                self._widget.pack_forget()

    def style(self, key, value):
        pass


# ==============================================================================
# _UISeparator
# ==============================================================================
class _UISeparator:
    def __init__(self, orientation="horizontal"):
        self._orientation = orientation
        self._widget      = None
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        orient = "horizontal" if self._orientation == "horizontal" else "vertical"
        self._widget = _ttk.Separator(parent, orient=orient)
        if orient == "horizontal":
            self._widget.pack(fill="x", pady=4)
        else:
            self._widget.pack(fill="y", padx=4, side="left")

    def setColor(self, color):
        pass  # ttk Separator no permite color directo

    def setThickness(self, value):
        pass

    def style(self, key, value):
        pass


# ==============================================================================
# _UIList
# ==============================================================================
class _UIList:
    def __init__(self, id=None):
        self._id          = id
        self._widget      = None
        self._frame       = None
        self._scrollbar   = None
        self._items       = []   # [(text, value, icon), ...]
        self._multiselect = False
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._frame     = _tk.Frame(parent)
        self._scrollbar = _tk.Scrollbar(self._frame)
        self._scrollbar.pack(side="right", fill="y")
        select_mode = "multiple" if self._multiselect else "browse"
        self._widget = _tk.Listbox(self._frame,
                                   yscrollcommand=self._scrollbar.set,
                                   selectmode=select_mode)
        self._widget.pack(side="left", fill="both", expand=True)
        self._scrollbar.configure(command=self._widget.yview)
        self._frame.pack(fill="both", expand=True)
        for text, _, _ in self._items:
            self._widget.insert("end", text)

    def addItem(self, text, value, icon=None):
        self._items.append((str(text), str(value), icon))
        if self._widget:
            self._widget.insert("end", str(text))

    def addItems(self, data):
        for item in data:
            self.addItem(item["text"], item["value"], item.get("icon"))

    def removeItem(self, value):
        for i, (t, v, ic) in enumerate(self._items):
            if v == str(value):
                self._items.pop(i)
                if self._widget:
                    self._widget.delete(i)
                return

    def clear(self):
        self._items = []
        if self._widget:
            self._widget.delete(0, "end")

    def setData(self, data):
        self.clear()
        self.addItems(data)

    def getSelected(self):
        if not self._widget:
            return ""
        sel = self._widget.curselection()
        if sel:
            return self._items[sel[0]][1]
        return ""

    def getSelectedAll(self):
        if not self._widget:
            return []
        return [self._items[i][1] for i in self._widget.curselection()]

    def setSelected(self, value):
        for i, (t, v, ic) in enumerate(self._items):
            if v == str(value):
                if self._widget:
                    self._widget.selection_clear(0, "end")
                    self._widget.selection_set(i)
                return

    def setMultiSelect(self, value):
        self._multiselect = bool(value)
        if self._widget:
            self._widget.configure(
                selectmode="multiple" if value else "browse")

    def setVisible(self, value):
        if self._frame:
            if value:
                self._frame.pack(fill="both", expand=True)
            else:
                self._frame.pack_forget()

    def onChange(self, callback):
        if self._widget:
            self._widget.bind("<<ListboxSelect>>",
                              lambda e: _invoke_callback(callback))

    def onDoubleClick(self, callback):
        if self._widget:
            self._widget.bind("<Double-Button-1>",
                              lambda e: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UITable
# ==============================================================================
class _UITable:
    def __init__(self, id=None):
        self._id        = id
        self._widget    = None
        self._frame     = None
        self._columns   = []   # [{key, label, width?, sortable?, type?}, ...]
        self._data      = []   # [dict, ...]
        self._sortable  = False
        self._selectable= False
        self._striped   = False
        self._page_size = 0
        self._page      = 0
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._frame  = _tk.Frame(parent)
        cols         = [c["key"] for c in self._columns]
        self._widget = _ttk.Treeview(self._frame, columns=cols,
                                     show="headings",
                                     selectmode="browse" if self._selectable
                                     else "none")
        for col in self._columns:
            key   = col["key"]
            label = col.get("label", key)
            width = col.get("width", 120)
            self._widget.heading(key, text=label,
                                 command=(lambda k=key: self._sort_column(k))
                                 if self._sortable else None)
            self._widget.column(key, width=int(width))

        vsb = _ttk.Scrollbar(self._frame, orient="vertical",
                             command=self._widget.yview)
        hsb = _ttk.Scrollbar(self._frame, orient="horizontal",
                             command=self._widget.xview)
        self._widget.configure(yscrollcommand=vsb.set,
                               xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._widget.pack(fill="both", expand=True)
        self._frame.pack(fill="both", expand=True)
        self._refresh()

    def _refresh(self):
        if not self._widget:
            return
        self._widget.delete(*self._widget.get_children())
        data = self._data
        if self._page_size > 0:
            start = self._page * self._page_size
            data  = data[start:start + self._page_size]
        for i, row in enumerate(data):
            vals = [row.get(c["key"], "") for c in self._columns]
            tag  = "even" if i % 2 == 0 else "odd"
            self._widget.insert("", "end", iid=str(i), values=vals, tags=(tag,))
        if self._striped:
            self._widget.tag_configure("even", background="#f9f9f9")
            self._widget.tag_configure("odd",  background="#ffffff")

    def _sort_column(self, key):
        self._data.sort(key=lambda r: r.get(key, ""))
        self._refresh()

    def setColumns(self, columns):
        self._columns = columns

    def setData(self, data):
        self._data = list(data)
        self._refresh()

    def addRow(self, row):
        self._data.append(dict(row))
        self._refresh()

    def removeRow(self, index):
        if 0 <= int(index) < len(self._data):
            self._data.pop(int(index))
            self._refresh()

    def updateRow(self, index, row):
        if 0 <= int(index) < len(self._data):
            self._data[int(index)] = dict(row)
            self._refresh()

    def getRow(self, index):
        if 0 <= int(index) < len(self._data):
            return self._data[int(index)]
        return {}

    def clear(self):
        self._data = []
        self._refresh()

    def setSortable(self, value):
        self._sortable = bool(value)

    def setSelectable(self, value):
        self._selectable = bool(value)
        if self._widget:
            self._widget.configure(
                selectmode="browse" if value else "none")

    def getSelected(self):
        if not self._widget:
            return []
        sel = self._widget.selection()
        return [int(s) for s in sel]

    def setPagination(self, page_size):
        self._page_size = int(page_size)
        self._refresh()

    def setPage(self, page):
        self._page = int(page)
        self._refresh()

    def setStriped(self, value):
        self._striped = bool(value)
        self._refresh()

    def setVisible(self, value):
        if self._frame:
            if value:
                self._frame.pack(fill="both", expand=True)
            else:
                self._frame.pack_forget()

    def onSelect(self, callback):
        if self._widget:
            self._widget.bind("<<TreeviewSelect>>",
                              lambda e: _invoke_callback(callback))

    def onSort(self, callback):
        self._on_sort = callback

    def style(self, key, value):
        pass


# ==============================================================================
# _UITabs
# ==============================================================================
class _UITabs:
    def __init__(self, id=None):
        self._id       = id
        self._widget   = None
        self._tabs     = {}   # {key: (label, container)}
        self._position = "top"
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._widget = _ttk.Notebook(parent)
        self._widget.pack(fill="both", expand=True)
        for key, (label, container) in self._tabs.items():
            container._build(self._widget)
            w = container._widget if container._widget else _tk.Frame(self._widget)
            self._widget.add(w, text=str(label))

    def addTab(self, key, label, container):
        self._tabs[str(key)] = (str(label), container)
        if self._widget:
            container._build(self._widget)
            w = container._widget if container._widget else _tk.Frame(self._widget)
            self._widget.add(w, text=str(label))

    def removeTab(self, key):
        if str(key) in self._tabs and self._widget:
            tabs_list = list(self._tabs.keys())
            if str(key) in tabs_list:
                idx = tabs_list.index(str(key))
                self._widget.forget(idx)
        self._tabs.pop(str(key), None)

    def setActive(self, key):
        if self._widget:
            tabs_list = list(self._tabs.keys())
            if str(key) in tabs_list:
                self._widget.select(tabs_list.index(str(key)))

    def getActive(self):
        if not self._widget:
            return ""
        idx   = self._widget.index(self._widget.select())
        keys  = list(self._tabs.keys())
        return keys[idx] if idx < len(keys) else ""

    def setPosition(self, position):
        self._position = position

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(fill="both", expand=True)
            else:
                self._widget.pack_forget()

    def onChange(self, callback):
        if self._widget:
            self._widget.bind("<<NotebookTabChanged>>",
                              lambda e: _invoke_callback(callback))

    def style(self, key, value):
        pass


# ==============================================================================
# _UICanvas
# ==============================================================================
class _UICanvas:
    def __init__(self, width=400, height=300, id=None):
        self._w      = int(width)
        self._h      = int(height)
        self._id     = id
        self._widget = None
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._widget = _tk.Canvas(parent, width=self._w, height=self._h,
                                  bg="white", highlightthickness=0)
        self._widget.pack()

    def clear(self):
        if self._widget:
            self._widget.delete("all")

    def setBackground(self, color):
        if self._widget:
            self._widget.configure(bg=color)

    def drawLine(self, x1, y1, x2, y2, color, width):
        if self._widget:
            self._widget.create_line(
                float(x1), float(y1), float(x2), float(y2),
                fill=color, width=float(width))

    def drawRect(self, x, y, w, h, color, fill):
        if self._widget:
            fc = color if bool(fill) else ""
            oc = color
            self._widget.create_rectangle(
                float(x), float(y), float(x)+float(w), float(y)+float(h),
                fill=fc, outline=oc)

    def drawCircle(self, cx, cy, r, color, fill):
        if self._widget:
            fc = color if bool(fill) else ""
            oc = color
            self._widget.create_oval(
                float(cx)-float(r), float(cy)-float(r),
                float(cx)+float(r), float(cy)+float(r),
                fill=fc, outline=oc)

    def drawPolygon(self, points, color, fill):
        if self._widget:
            flat = []
            for p in points:
                flat.extend([float(p["x"]), float(p["y"])])
            fc = color if bool(fill) else ""
            self._widget.create_polygon(flat, fill=fc, outline=color)

    def drawText(self, text, x, y, family, size, color):
        if self._widget:
            self._widget.create_text(
                float(x), float(y),
                text=str(text),
                font=(str(family), int(size)),
                fill=color)

    def drawImage(self, src, x, y, w, h):
        if self._widget:
            try:
                img   = _tk.PhotoImage(file=str(src))
                # guardar referencia para evitar GC
                if not hasattr(self, "_images"):
                    self._images = []
                self._images.append(img)
                self._widget.create_image(float(x), float(y),
                                          image=img, anchor="nw")
            except Exception:
                pass

    def redraw(self):
        if self._widget:
            self._widget.update_idletasks()

    def onClick(self, callback):
        if self._widget:
            self._widget.bind("<Button-1>",
                              lambda e: _invoke_callback(callback))

    def onMouseMove(self, callback):
        if self._widget:
            self._widget.bind("<Motion>",
                              lambda e: _invoke_callback(callback))

    def onMouseDown(self, callback):
        if self._widget:
            self._widget.bind("<ButtonPress>",
                              lambda e: _invoke_callback(callback))

    def onMouseUp(self, callback):
        if self._widget:
            self._widget.bind("<ButtonRelease>",
                              lambda e: _invoke_callback(callback))

    def onKeyDown(self, callback):
        if self._widget:
            self._widget.bind("<KeyPress>",
                              lambda e: _invoke_callback(callback))
            self._widget.focus_set()

    def onKeyUp(self, callback):
        if self._widget:
            self._widget.bind("<KeyRelease>",
                              lambda e: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# _UIDialog
# ==============================================================================
class _UIDialog:
    def __init__(self, title="", id=None):
        self._title     = str(title)
        self._id        = id
        self._win       = None
        self._container = None
        self._closable  = True
        self._blocking  = True
        self._w         = 400
        self._h         = 300

    def setTitle(self, text):
        self._title = str(text)
        if self._win:
            self._win.title(str(text))

    def mount(self, container):
        self._container = container

    def setSize(self, width, height):
        self._w = int(width)
        self._h = int(height)
        if self._win:
            self._win.geometry(f"{int(width)}x{int(height)}")

    def show(self):
        root = _ui_state.get("root")
        if root is None:
            return
        self._win = _tk.Toplevel(root)
        self._win.title(self._title)
        self._win.geometry(f"{self._w}x{self._h}")
        if not self._closable:
            self._win.protocol("WM_DELETE_WINDOW", lambda: None)
        if self._blocking:
            self._win.grab_set()
        if self._container:
            self._container._build(self._win)
            if self._container._widget:
                self._container._widget.pack(fill="both", expand=True)

    def hide(self):
        if self._win:
            self._win.withdraw()

    def setClosable(self, value):
        self._closable = bool(value)
        if self._win:
            self._win.protocol("WM_DELETE_WINDOW",
                               self._win.destroy if value else (lambda: None))

    def setBlocking(self, value):
        self._blocking = bool(value)
        if self._win:
            if value:
                self._win.grab_set()
            else:
                self._win.grab_release()

    def onClose(self, callback):
        if self._win:
            self._win.protocol("WM_DELETE_WINDOW",
                               lambda: _invoke_callback(callback))

    def style(self, key, value):
        if self._win:
            _apply_style(self._win, key, value)


# ==============================================================================
# _UINotification
# ==============================================================================
class _UINotification:
    def __init__(self, message="", type_="info", duration=3000):
        self._message  = str(message)
        self._type     = str(type_)
        self._duration = int(duration)
        self._win      = None
        self._position = "top-right"
        self._action_label    = None
        self._action_callback = None

    def _type_colors(self):
        return {
            "info":    ("#d1ecf1", "#0c5460"),
            "success": ("#d4edda", "#155724"),
            "warning": ("#fff3cd", "#856404"),
            "error":   ("#f8d7da", "#721c24"),
        }.get(self._type, ("#d1ecf1", "#0c5460"))

    def show(self):
        root = _ui_state.get("root")
        if root is None:
            return
        bg, fg = self._type_colors()
        self._win = _tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.configure(bg=bg)
        self._win.attributes("-topmost", True)

        lbl = _tk.Label(self._win, text=self._message, bg=bg, fg=fg,
                        font=("TkDefaultFont", 11), padx=12, pady=8)
        lbl.pack()

        if self._action_label and self._action_callback:
            btn = _tk.Button(self._win, text=self._action_label, bg=bg, fg=fg,
                             relief="flat", font=("TkDefaultFont", 10, "underline"),
                             command=lambda: _invoke_callback(self._action_callback))
            btn.pack()

        self._win.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ww = self._win.winfo_width()
        wh = self._win.winfo_height()
        pos_map = {
            "top-left":       (10, 10),
            "top-center":     ((sw - ww) // 2, 10),
            "top-right":      (sw - ww - 10, 10),
            "bottom-left":    (10, sh - wh - 10),
            "bottom-center":  ((sw - ww) // 2, sh - wh - 10),
            "bottom-right":   (sw - ww - 10, sh - wh - 10),
        }
        x, y = pos_map.get(self._position, (sw - ww - 10, 10))
        self._win.geometry(f"+{x}+{y}")

        if self._duration > 0:
            self._win.after(self._duration, self.hide)

    def hide(self):
        if self._win:
            self._win.destroy()
            self._win = None

    def setMessage(self, text):
        self._message = str(text)

    def setType(self, type_):
        self._type = str(type_)

    def setDuration(self, value):
        self._duration = int(value)

    def setPosition(self, position):
        self._position = position

    def setAction(self, label, callback):
        self._action_label    = str(label)
        self._action_callback = callback

    def onDismiss(self, callback):
        self._on_dismiss = callback


# ==============================================================================
# _UIMenuBar + _UIMenu
# ==============================================================================
class _UIMenu:
    def __init__(self, label=""):
        self._label    = str(label)
        self._tk_menu  = None
        self._enabled  = True
        self._icon     = None
        self._items    = []

    def _build(self, parent_menu):
        self._tk_menu = _tk.Menu(parent_menu, tearoff=0)
        for item in self._items:
            if item["type"] == "separator":
                self._tk_menu.add_separator()
            elif item["type"] == "item":
                cb  = item["callback"]
                kw  = {"label": item["label"],
                       "command": lambda c=cb: _invoke_callback(c)}
                if item.get("shortcut"):
                    kw["accelerator"] = item["shortcut"]
                self._tk_menu.add_command(**kw)
            elif item["type"] == "submenu":
                item["menu"]._build(self._tk_menu)
                self._tk_menu.add_cascade(label=item["menu"]._label,
                                          menu=item["menu"]._tk_menu)
        if not self._enabled:
            pass  # se deshabilita en el padre

    def addItem(self, label, callback, shortcut=None):
        self._items.append({"type": "item", "label": str(label),
                            "callback": callback, "shortcut": shortcut})
        if self._tk_menu:
            kw = {"label": str(label),
                  "command": lambda c=callback: _invoke_callback(c)}
            if shortcut:
                kw["accelerator"] = shortcut
            self._tk_menu.add_command(**kw)

    def addSeparator(self):
        self._items.append({"type": "separator"})
        if self._tk_menu:
            self._tk_menu.add_separator()

    def addSubMenu(self, menu):
        self._items.append({"type": "submenu", "menu": menu})
        if self._tk_menu:
            menu._build(self._tk_menu)
            self._tk_menu.add_cascade(label=menu._label, menu=menu._tk_menu)

    def setEnabled(self, value):
        self._enabled = bool(value)

    def setIcon(self, path):
        self._icon = str(path)


class _UIMenuBar:
    def __init__(self, id=None):
        self._id      = id
        self._widget  = None
        self._menus   = []

    def _build(self, parent):
        root = _ui_state.get("root")
        if root is None:
            return
        self._widget = _tk.Menu(root)
        root.configure(menu=self._widget)
        for menu in self._menus:
            menu._build(self._widget)
            self._widget.add_cascade(label=menu._label,
                                     menu=menu._tk_menu)

    def addMenu(self, menu):
        self._menus.append(menu)
        if self._widget:
            menu._build(self._widget)
            self._widget.add_cascade(label=menu._label, menu=menu._tk_menu)

    def setVisible(self, value):
        root = _ui_state.get("root")
        if root:
            if value:
                root.configure(menu=self._widget)
            else:
                root.configure(menu="")


# ==============================================================================
# _UIColorPicker
# ==============================================================================
class _UIColorPicker:
    def __init__(self, id=None):
        self._id      = id
        self._value   = "#000000"
        self._format  = "hex"
        self._enabled = True
        self._widget  = None
        self._frame   = None
        self._swatch  = None
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._frame  = _tk.Frame(parent)
        self._swatch = _tk.Label(self._frame, bg=self._value,
                                 width=4, relief="raised", cursor="hand2")
        self._swatch.pack(side="left")
        self._widget = _tk.Button(self._frame, text="Elegir color",
                                  state="normal" if self._enabled else "disabled",
                                  command=self._open_picker)
        self._widget.pack(side="left")
        self._frame.pack()

    def _open_picker(self):
        result = _colorchooser.askcolor(color=self._value)
        if result and result[1]:
            self._value = result[1]
            if self._swatch:
                self._swatch.configure(bg=self._value)
            if hasattr(self, "_on_change"):
                _invoke_callback(self._on_change)

    def setValue(self, color):
        self._value = str(color)
        if self._swatch:
            self._swatch.configure(bg=color)

    def getValue(self):
        return self._value

    def setFormat(self, format_):
        self._format = format_

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setVisible(self, value):
        if self._frame:
            if value:
                self._frame.pack()
            else:
                self._frame.pack_forget()

    def onChange(self, callback):
        self._on_change = callback

    def style(self, key, value):
        if self._frame:
            _apply_style(self._frame, key, value)


# ==============================================================================
# _UIDatePicker
# ==============================================================================
class _UIDatePicker:
    def __init__(self, id=None):
        self._id      = id
        self._value   = ""
        self._min     = ""
        self._max     = ""
        self._format  = "YYYY-MM-DD"
        self._enabled = True
        self._widget  = None
        self._var     = None
        self._grid_col     = 0
        self._grid_row     = 0
        self._grid_colspan = 1
        self._grid_rowspan = 1

    def _build(self, parent):
        self._var    = _tk.StringVar(value=self._value)
        self._widget = _tk.Entry(parent, textvariable=self._var,
                                 state="normal" if self._enabled else "disabled")
        self._widget.pack(fill="x")
        # Placeholder hint
        lbl = _tk.Label(parent, text=f"Formato: {self._format}",
                        fg="grey", font=("TkDefaultFont", 8))
        lbl.pack()

    def setValue(self, date):
        self._value = str(date)
        if self._var:
            self._var.set(str(date))

    def getValue(self):
        return self._var.get() if self._var else self._value

    def setMin(self, date):
        self._min = str(date)

    def setMax(self, date):
        self._max = str(date)

    def setFormat(self, format_):
        self._format = format_

    def setEnabled(self, value):
        self._enabled = bool(value)
        if self._widget:
            self._widget.configure(state="normal" if value else "disabled")

    def setVisible(self, value):
        if self._widget:
            if value:
                self._widget.pack(fill="x")
            else:
                self._widget.pack_forget()

    def onChange(self, callback):
        if self._var:
            self._var.trace_add("write",
                                lambda *_: _invoke_callback(callback))

    def style(self, key, value):
        if self._widget:
            _apply_style(self._widget, key, value)


# ==============================================================================
# Wrappers nativos — patrón:  args[0] = self (instancia Python), args[1..] = params
# ==============================================================================

def _make_ctor(cls):
    def ctor(args):
        return cls(*args)
    return ctor

def _make_method(method_name):
    def method(args):
        self  = args[0]
        rest  = args[1:]
        fn    = getattr(self, method_name)
        return fn(*rest)
    return method

# Constructor helpers
def _ui_Interface_new(args):
    title  = _opt(args, 0, "Ventana", str)
    width  = _opt(args, 1, 800, int)
    height = _opt(args, 2, 600, int)
    mode   = _opt(args, 3, "window", str)
    return _UIInterface(title, width, height, mode)

def _ui_Container_new(args):
    layout = _opt(args, 0, "column", str)
    id_    = _opt(args, 1, None,     str)
    return _UIContainer(layout, id_)

def _ui_Label_new(args):
    text = _opt(args, 0, "", str)
    id_  = _opt(args, 1, None, str)
    return _UILabel(text, id_)

def _ui_Button_new(args):
    text = _opt(args, 0, "", str)
    id_  = _opt(args, 1, None, str)
    return _UIButton(text, id_)

def _ui_Input_new(args):
    ph  = _opt(args, 0, "", str)
    id_ = _opt(args, 1, None, str)
    return _UIInput(ph, id_)

def _ui_TextArea_new(args):
    ph  = _opt(args, 0, "", str)
    id_ = _opt(args, 1, None, str)
    return _UITextArea(ph, id_)

def _ui_Select_new(args):
    ph  = _opt(args, 0, "", str)
    id_ = _opt(args, 1, None, str)
    return _UISelect(ph, id_)

def _ui_Checkbox_new(args):
    label = _opt(args, 0, "", str)
    id_   = _opt(args, 1, None, str)
    return _UICheckbox(label, id_)

def _ui_Radio_new(args):
    name = _opt(args, 0, "", str)
    id_  = _opt(args, 1, None, str)
    return _UIRadio(name, id_)

def _ui_Toggle_new(args):
    label = _opt(args, 0, "", str)
    id_   = _opt(args, 1, None, str)
    return _UIToggle(label, id_)

def _ui_Slider_new(args):
    min_  = _opt(args, 0, 0,   float)
    max_  = _opt(args, 1, 100, float)
    step  = _opt(args, 2, 1,   float)
    id_   = _opt(args, 3, None, str)
    return _UISlider(min_, max_, step, id_)

def _ui_Image_new(args):
    src = _opt(args, 0, "", str)
    id_ = _opt(args, 1, None, str)
    return _UIImage(src, id_)

def _ui_Progress_new(args):
    value = _opt(args, 0, 0,   float)
    max_  = _opt(args, 1, 100, float)
    id_   = _opt(args, 2, None, str)
    return _UIProgress(value, max_, id_)

def _ui_Spinner_new(args):
    size = _opt(args, 0, "md", str)
    id_  = _opt(args, 1, None, str)
    return _UISpinner(size, id_)

def _ui_Separator_new(args):
    orientation = _opt(args, 0, "horizontal", str)
    return _UISeparator(orientation)

def _ui_List_new(args):
    id_ = _opt(args, 0, None, str)
    return _UIList(id_)

def _ui_Table_new(args):
    id_ = _opt(args, 0, None, str)
    return _UITable(id_)

def _ui_Tabs_new(args):
    id_ = _opt(args, 0, None, str)
    return _UITabs(id_)

def _ui_Canvas_new(args):
    width  = _opt(args, 0, 400, int)
    height = _opt(args, 1, 300, int)
    id_    = _opt(args, 2, None, str)
    return _UICanvas(width, height, id_)

def _ui_MenuBar_new(args):
    id_ = _opt(args, 0, None, str)
    return _UIMenuBar(id_)

def _ui_Menu_new(args):
    label = _opt(args, 0, "", str)
    return _UIMenu(label)

def _ui_Dialog_new(args):
    title = _opt(args, 0, "", str)
    id_   = _opt(args, 1, None, str)
    return _UIDialog(title, id_)

def _ui_Notification_new(args):
    message  = _opt(args, 0, "", str)
    type_    = _opt(args, 1, "info", str)
    duration = _opt(args, 2, 3000, int)
    return _UINotification(message, type_, duration)

def _ui_ColorPicker_new(args):
    id_ = _opt(args, 0, None, str)
    return _UIColorPicker(id_)

def _ui_DatePicker_new(args):
    id_ = _opt(args, 0, None, str)
    return _UIDatePicker(id_)

# Generador genérico de wrapper para método
def _m(method_name):
    """Genera una función nativa que llama self.method_name(*args[1:])."""
    def wrapper(args):
        obj  = args[0]
        rest = args[1:]
        return getattr(obj, method_name)(*rest)
    wrapper.__name__ = f"_method_{method_name}"
    return wrapper


# ==============================================================================
# _NATIVE_REGISTRY
# ==============================================================================
_NATIVE_REGISTRY = {
    # --------------------------------------------------------------------------
    # math (se mantiene)
    # --------------------------------------------------------------------------
    "math_sqrt":  lambda args: _math.sqrt(float(args[0])),
    "math_abs":   lambda args: abs(args[0]),
    "math_pow":   lambda args: _math.pow(float(args[0]), float(args[1])),
    "math_floor": lambda args: int(_math.floor(float(args[0]))),
    "math_ceil":  lambda args: int(_math.ceil(float(args[0]))),
    "math_round": lambda args: round(float(args[0])),
    "math_log":   lambda args: _math.log(float(args[0])),
    "math_log2":  lambda args: _math.log2(float(args[0])),
    "math_sin":   lambda args: _math.sin(float(args[0])),
    "math_cos":   lambda args: _math.cos(float(args[0])),
    "math_tan":   lambda args: _math.tan(float(args[0])),

    # --------------------------------------------------------------------------
    # ui — constructores
    # --------------------------------------------------------------------------
    "ui_Interface_new":    _ui_Interface_new,
    "ui_Container_new":    _ui_Container_new,
    "ui_Label_new":        _ui_Label_new,
    "ui_Button_new":       _ui_Button_new,
    "ui_Input_new":        _ui_Input_new,
    "ui_TextArea_new":     _ui_TextArea_new,
    "ui_Select_new":       _ui_Select_new,
    "ui_Checkbox_new":     _ui_Checkbox_new,
    "ui_Radio_new":        _ui_Radio_new,
    "ui_Toggle_new":       _ui_Toggle_new,
    "ui_Slider_new":       _ui_Slider_new,
    "ui_Image_new":        _ui_Image_new,
    "ui_Progress_new":     _ui_Progress_new,
    "ui_Spinner_new":      _ui_Spinner_new,
    "ui_Separator_new":    _ui_Separator_new,
    "ui_List_new":         _ui_List_new,
    "ui_Table_new":        _ui_Table_new,
    "ui_Tabs_new":         _ui_Tabs_new,
    "ui_Canvas_new":       _ui_Canvas_new,
    "ui_MenuBar_new":      _ui_MenuBar_new,
    "ui_Menu_new":         _ui_Menu_new,
    "ui_Dialog_new":       _ui_Dialog_new,
    "ui_Notification_new": _ui_Notification_new,
    "ui_ColorPicker_new":  _ui_ColorPicker_new,
    "ui_DatePicker_new":   _ui_DatePicker_new,

    # --------------------------------------------------------------------------
    # ui — Interface métodos
    # --------------------------------------------------------------------------
    "ui_Interface_mount":       _m("mount"),
    "ui_Interface_run":         _m("run"),
    "ui_Interface_show":        _m("show"),
    "ui_Interface_hide":        _m("hide"),
    "ui_Interface_close":       _m("close"),
    "ui_Interface_setTitle":    _m("setTitle"),
    "ui_Interface_setSize":     _m("setSize"),
    "ui_Interface_setMinSize":  _m("setMinSize"),
    "ui_Interface_setResizable":_m("setResizable"),
    "ui_Interface_setIcon":     _m("setIcon"),
    "ui_Interface_setTheme":    _m("setTheme"),
    "ui_Interface_setBackground":_m("setBackground"),
    "ui_Interface_center":      _m("center"),
    "ui_Interface_onClose":     _m("onClose"),
    "ui_Interface_onResize":    _m("onResize"),
    "ui_Interface_onFocus":     _m("onFocus"),
    "ui_Interface_onBlur":      _m("onBlur"),

    # --------------------------------------------------------------------------
    # ui — Container métodos
    # --------------------------------------------------------------------------
    "ui_Container_add":          _m("add"),
    "ui_Container_addAt":        _m("addAt"),
    "ui_Container_remove":       _m("remove"),
    "ui_Container_clear":        _m("clear"),
    "ui_Container_get":          _m("get"),
    "ui_Container_setSpacing":   _m("setSpacing"),
    "ui_Container_setPadding":   _m("setPadding"),
    "ui_Container_setAlign":     _m("setAlign"),
    "ui_Container_setScroll":    _m("setScroll"),
    "ui_Container_setBackground":_m("setBackground"),
    "ui_Container_setBorder":    _m("setBorder"),
    "ui_Container_setSize":      _m("setSize"),
    "ui_Container_setVisible":   _m("setVisible"),
    "ui_Container_setId":        _m("setId"),
    "ui_Container_setGrid":      _m("setGrid"),
    "ui_Container_gridPlace":    _m("gridPlace"),
    "ui_Container_style":        _m("style"),

    # --------------------------------------------------------------------------
    # ui — Label métodos
    # --------------------------------------------------------------------------
    "ui_Label_setText":   _m("setText"),
    "ui_Label_getText":   _m("getText"),
    "ui_Label_setFont":   _m("setFont"),
    "ui_Label_setSize":   _m("setSize"),
    "ui_Label_setColor":  _m("setColor"),
    "ui_Label_setAlign":  _m("setAlign"),
    "ui_Label_setWrap":   _m("setWrap"),
    "ui_Label_setVisible":_m("setVisible"),
    "ui_Label_style":     _m("style"),

    # --------------------------------------------------------------------------
    # ui — Button métodos
    # --------------------------------------------------------------------------
    "ui_Button_setText":     _m("setText"),
    "ui_Button_setIcon":     _m("setIcon"),
    "ui_Button_setEnabled":  _m("setEnabled"),
    "ui_Button_setVariant":  _m("setVariant"),
    "ui_Button_setSize":     _m("setSize"),
    "ui_Button_setFullWidth":_m("setFullWidth"),
    "ui_Button_setLoading":  _m("setLoading"),
    "ui_Button_setVisible":  _m("setVisible"),
    "ui_Button_onClick":     _m("onClick"),
    "ui_Button_onHover":     _m("onHover"),
    "ui_Button_onFocus":     _m("onFocus"),
    "ui_Button_onBlur":      _m("onBlur"),
    "ui_Button_style":       _m("style"),

    # --------------------------------------------------------------------------
    # ui — Input métodos
    # --------------------------------------------------------------------------
    "ui_Input_setValue":     _m("setValue"),
    "ui_Input_getValue":     _m("getValue"),
    "ui_Input_setPlaceholder":_m("setPlaceholder"),
    "ui_Input_setType":      _m("setType"),
    "ui_Input_setLabel":     _m("setLabel"),
    "ui_Input_setHint":      _m("setHint"),
    "ui_Input_setError":     _m("setError"),
    "ui_Input_clearError":   _m("clearError"),
    "ui_Input_setEnabled":   _m("setEnabled"),
    "ui_Input_setReadOnly":  _m("setReadOnly"),
    "ui_Input_setMaxLength": _m("setMaxLength"),
    "ui_Input_setPattern":   _m("setPattern"),
    "ui_Input_clear":        _m("clear"),
    "ui_Input_focus":        _m("focus"),
    "ui_Input_setVisible":   _m("setVisible"),
    "ui_Input_onChange":     _m("onChange"),
    "ui_Input_onSubmit":     _m("onSubmit"),
    "ui_Input_onFocus":      _m("onFocus"),
    "ui_Input_onBlur":       _m("onBlur"),
    "ui_Input_style":        _m("style"),

    # --------------------------------------------------------------------------
    # ui — TextArea métodos (hereda Input + propios)
    # --------------------------------------------------------------------------
    "ui_TextArea_setValue":     _m("setValue"),
    "ui_TextArea_getValue":     _m("getValue"),
    "ui_TextArea_setPlaceholder":_m("setPlaceholder"),
    "ui_TextArea_setType":      _m("setType"),
    "ui_TextArea_setLabel":     _m("setLabel"),
    "ui_TextArea_setHint":      _m("setHint"),
    "ui_TextArea_setError":     _m("setError"),
    "ui_TextArea_clearError":   _m("clearError"),
    "ui_TextArea_setEnabled":   _m("setEnabled"),
    "ui_TextArea_setReadOnly":  _m("setReadOnly"),
    "ui_TextArea_setMaxLength": _m("setMaxLength"),
    "ui_TextArea_setPattern":   _m("setPattern"),
    "ui_TextArea_clear":        _m("clear"),
    "ui_TextArea_focus":        _m("focus"),
    "ui_TextArea_setVisible":   _m("setVisible"),
    "ui_TextArea_onChange":     _m("onChange"),
    "ui_TextArea_onSubmit":     _m("onSubmit"),
    "ui_TextArea_onFocus":      _m("onFocus"),
    "ui_TextArea_onBlur":       _m("onBlur"),
    "ui_TextArea_style":        _m("style"),
    "ui_TextArea_setRows":      _m("setRows"),
    "ui_TextArea_setResize":    _m("setResize"),

    # --------------------------------------------------------------------------
    # ui — Select métodos
    # --------------------------------------------------------------------------
    "ui_Select_addOption":   _m("addOption"),
    "ui_Select_addOptions":  _m("addOptions"),
    "ui_Select_setValue":    _m("setValue"),
    "ui_Select_getValue":    _m("getValue"),
    "ui_Select_getValueAll": _m("getValueAll"),
    "ui_Select_setMultiple": _m("setMultiple"),
    "ui_Select_setSearchable":_m("setSearchable"),
    "ui_Select_setEnabled":  _m("setEnabled"),
    "ui_Select_clear":       _m("clear"),
    "ui_Select_setVisible":  _m("setVisible"),
    "ui_Select_onChange":    _m("onChange"),
    "ui_Select_style":       _m("style"),

    # --------------------------------------------------------------------------
    # ui — Checkbox métodos
    # --------------------------------------------------------------------------
    "ui_Checkbox_setValue":  _m("setValue"),
    "ui_Checkbox_getValue":  _m("getValue"),
    "ui_Checkbox_setLabel":  _m("setLabel"),
    "ui_Checkbox_setEnabled":_m("setEnabled"),
    "ui_Checkbox_setVisible":_m("setVisible"),
    "ui_Checkbox_onChange":  _m("onChange"),
    "ui_Checkbox_style":     _m("style"),

    # --------------------------------------------------------------------------
    # ui — Radio métodos
    # --------------------------------------------------------------------------
    "ui_Radio_addOption":   _m("addOption"),
    "ui_Radio_setValue":    _m("setValue"),
    "ui_Radio_getValue":    _m("getValue"),
    "ui_Radio_setLayout":   _m("setLayout"),
    "ui_Radio_setEnabled":  _m("setEnabled"),
    "ui_Radio_setVisible":  _m("setVisible"),
    "ui_Radio_onChange":    _m("onChange"),
    "ui_Radio_style":       _m("style"),

    # --------------------------------------------------------------------------
    # ui — Toggle métodos
    # --------------------------------------------------------------------------
    "ui_Toggle_setValue":  _m("setValue"),
    "ui_Toggle_getValue":  _m("getValue"),
    "ui_Toggle_setLabel":  _m("setLabel"),
    "ui_Toggle_setEnabled":_m("setEnabled"),
    "ui_Toggle_setVisible":_m("setVisible"),
    "ui_Toggle_onChange":  _m("onChange"),
    "ui_Toggle_style":     _m("style"),

    # --------------------------------------------------------------------------
    # ui — Slider métodos
    # --------------------------------------------------------------------------
    "ui_Slider_setValue":      _m("setValue"),
    "ui_Slider_getValue":      _m("getValue"),
    "ui_Slider_setRange":      _m("setRange"),
    "ui_Slider_setStep":       _m("setStep"),
    "ui_Slider_setOrientation":_m("setOrientation"),
    "ui_Slider_setEnabled":    _m("setEnabled"),
    "ui_Slider_setVisible":    _m("setVisible"),
    "ui_Slider_onChange":      _m("onChange"),
    "ui_Slider_onRelease":     _m("onRelease"),
    "ui_Slider_style":         _m("style"),

    # --------------------------------------------------------------------------
    # ui — Image métodos
    # --------------------------------------------------------------------------
    "ui_Image_setSrc":     _m("setSrc"),
    "ui_Image_setAlt":     _m("setAlt"),
    "ui_Image_setSize":    _m("setSize"),
    "ui_Image_setFit":     _m("setFit"),
    "ui_Image_setVisible": _m("setVisible"),
    "ui_Image_onClick":    _m("onClick"),
    "ui_Image_onLoad":     _m("onLoad"),
    "ui_Image_onError":    _m("onError"),
    "ui_Image_style":      _m("style"),

    # --------------------------------------------------------------------------
    # ui — Progress métodos
    # --------------------------------------------------------------------------
    "ui_Progress_setValue":        _m("setValue"),
    "ui_Progress_setMax":          _m("setMax"),
    "ui_Progress_setMode":         _m("setMode"),
    "ui_Progress_setLabel":        _m("setLabel"),
    "ui_Progress_setIndeterminate":_m("setIndeterminate"),
    "ui_Progress_setVisible":      _m("setVisible"),
    "ui_Progress_style":           _m("style"),

    # --------------------------------------------------------------------------
    # ui — Spinner métodos
    # --------------------------------------------------------------------------
    "ui_Spinner_setSize":    _m("setSize"),
    "ui_Spinner_setColor":   _m("setColor"),
    "ui_Spinner_setVisible": _m("setVisible"),
    "ui_Spinner_style":      _m("style"),

    # --------------------------------------------------------------------------
    # ui — Separator métodos
    # --------------------------------------------------------------------------
    "ui_Separator_setColor":     _m("setColor"),
    "ui_Separator_setThickness": _m("setThickness"),
    "ui_Separator_style":        _m("style"),

    # --------------------------------------------------------------------------
    # ui — List métodos
    # --------------------------------------------------------------------------
    "ui_List_addItem":       _m("addItem"),
    "ui_List_addItems":      _m("addItems"),
    "ui_List_removeItem":    _m("removeItem"),
    "ui_List_clear":         _m("clear"),
    "ui_List_setData":       _m("setData"),
    "ui_List_getSelected":   _m("getSelected"),
    "ui_List_getSelectedAll":_m("getSelectedAll"),
    "ui_List_setSelected":   _m("setSelected"),
    "ui_List_setMultiSelect":_m("setMultiSelect"),
    "ui_List_setVisible":    _m("setVisible"),
    "ui_List_onChange":      _m("onChange"),
    "ui_List_onDoubleClick": _m("onDoubleClick"),
    "ui_List_style":         _m("style"),

    # --------------------------------------------------------------------------
    # ui — Table métodos
    # --------------------------------------------------------------------------
    "ui_Table_setColumns":   _m("setColumns"),
    "ui_Table_setData":      _m("setData"),
    "ui_Table_addRow":       _m("addRow"),
    "ui_Table_removeRow":    _m("removeRow"),
    "ui_Table_updateRow":    _m("updateRow"),
    "ui_Table_getRow":       _m("getRow"),
    "ui_Table_clear":        _m("clear"),
    "ui_Table_setSortable":  _m("setSortable"),
    "ui_Table_setSelectable":_m("setSelectable"),
    "ui_Table_getSelected":  _m("getSelected"),
    "ui_Table_setPagination":_m("setPagination"),
    "ui_Table_setPage":      _m("setPage"),
    "ui_Table_setStriped":   _m("setStriped"),
    "ui_Table_setVisible":   _m("setVisible"),
    "ui_Table_onSelect":     _m("onSelect"),
    "ui_Table_onSort":       _m("onSort"),
    "ui_Table_style":        _m("style"),

    # --------------------------------------------------------------------------
    # ui — Tabs métodos
    # --------------------------------------------------------------------------
    "ui_Tabs_addTab":     _m("addTab"),
    "ui_Tabs_removeTab":  _m("removeTab"),
    "ui_Tabs_setActive":  _m("setActive"),
    "ui_Tabs_getActive":  _m("getActive"),
    "ui_Tabs_setPosition":_m("setPosition"),
    "ui_Tabs_setVisible": _m("setVisible"),
    "ui_Tabs_onChange":   _m("onChange"),
    "ui_Tabs_style":      _m("style"),

    # --------------------------------------------------------------------------
    # ui — Canvas métodos
    # --------------------------------------------------------------------------
    "ui_Canvas_clear":        _m("clear"),
    "ui_Canvas_setBackground":_m("setBackground"),
    "ui_Canvas_drawLine":     _m("drawLine"),
    "ui_Canvas_drawRect":     _m("drawRect"),
    "ui_Canvas_drawCircle":   _m("drawCircle"),
    "ui_Canvas_drawPolygon":  _m("drawPolygon"),
    "ui_Canvas_drawText":     _m("drawText"),
    "ui_Canvas_drawImage":    _m("drawImage"),
    "ui_Canvas_redraw":       _m("redraw"),
    "ui_Canvas_onClick":      _m("onClick"),
    "ui_Canvas_onMouseMove":  _m("onMouseMove"),
    "ui_Canvas_onMouseDown":  _m("onMouseDown"),
    "ui_Canvas_onMouseUp":    _m("onMouseUp"),
    "ui_Canvas_onKeyDown":    _m("onKeyDown"),
    "ui_Canvas_onKeyUp":      _m("onKeyUp"),
    "ui_Canvas_style":        _m("style"),

    # --------------------------------------------------------------------------
    # ui — MenuBar métodos
    # --------------------------------------------------------------------------
    "ui_MenuBar_addMenu":    _m("addMenu"),
    "ui_MenuBar_setVisible": _m("setVisible"),

    # --------------------------------------------------------------------------
    # ui — Menu métodos
    # --------------------------------------------------------------------------
    "ui_Menu_addItem":    _m("addItem"),
    "ui_Menu_addSeparator":_m("addSeparator"),
    "ui_Menu_addSubMenu": _m("addSubMenu"),
    "ui_Menu_setEnabled": _m("setEnabled"),
    "ui_Menu_setIcon":    _m("setIcon"),

    # --------------------------------------------------------------------------
    # ui — Dialog métodos
    # --------------------------------------------------------------------------
    "ui_Dialog_setTitle":    _m("setTitle"),
    "ui_Dialog_mount":       _m("mount"),
    "ui_Dialog_setSize":     _m("setSize"),
    "ui_Dialog_show":        _m("show"),
    "ui_Dialog_hide":        _m("hide"),
    "ui_Dialog_setClosable": _m("setClosable"),
    "ui_Dialog_setBlocking": _m("setBlocking"),
    "ui_Dialog_onClose":     _m("onClose"),
    "ui_Dialog_style":       _m("style"),

    # --------------------------------------------------------------------------
    # ui — Notification métodos
    # --------------------------------------------------------------------------
    "ui_Notification_show":        _m("show"),
    "ui_Notification_hide":        _m("hide"),
    "ui_Notification_setMessage":  _m("setMessage"),
    "ui_Notification_setType":     _m("setType"),
    "ui_Notification_setDuration": _m("setDuration"),
    "ui_Notification_setPosition": _m("setPosition"),
    "ui_Notification_setAction":   _m("setAction"),
    "ui_Notification_onDismiss":   _m("onDismiss"),

    # --------------------------------------------------------------------------
    # ui — ColorPicker métodos
    # --------------------------------------------------------------------------
    "ui_ColorPicker_setValue":  _m("setValue"),
    "ui_ColorPicker_getValue":  _m("getValue"),
    "ui_ColorPicker_setFormat": _m("setFormat"),
    "ui_ColorPicker_setEnabled":_m("setEnabled"),
    "ui_ColorPicker_setVisible":_m("setVisible"),
    "ui_ColorPicker_onChange":  _m("onChange"),
    "ui_ColorPicker_style":     _m("style"),

    # --------------------------------------------------------------------------
    # ui — DatePicker métodos
    # --------------------------------------------------------------------------
    "ui_DatePicker_setValue":  _m("setValue"),
    "ui_DatePicker_getValue":  _m("getValue"),
    "ui_DatePicker_setMin":    _m("setMin"),
    "ui_DatePicker_setMax":    _m("setMax"),
    "ui_DatePicker_setFormat": _m("setFormat"),
    "ui_DatePicker_setEnabled":_m("setEnabled"),
    "ui_DatePicker_setVisible":_m("setVisible"),
    "ui_DatePicker_onChange":  _m("onChange"),
    "ui_DatePicker_style":     _m("style"),
}
