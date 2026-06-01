// ============================================================================
// native_registry.c - Implementación nativa del módulo UI con GTK3
// ============================================================================
#include "runtime.h"
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

// ----------------------------------------------------------------------------
// Inicialización de GTK (una sola vez)
// ----------------------------------------------------------------------------
static int gtk_initialized = 0;
static void ensure_gtk(int *argc, char ***argv) {
    if (!gtk_initialized) {
        gtk_init(argc, argv);
        gtk_initialized = 1;
    }
}

// ----------------------------------------------------------------------------
// Almacenar/recuperar el GtkWidget* de un TessObject
// ----------------------------------------------------------------------------
static void set_gtk_widget(TessObject* obj, GtkWidget* widget) {
    // Guardamos el puntero como entero en un atributo
    TessValue val;
    val.tag = TESS_INT;
    val.data = (int64_t)(intptr_t)widget;
    tess_object_set_attr(obj, "__gtk_widget", &val);
    // También asociamos el TessObject al widget para los callbacks
    g_object_set_data(G_OBJECT(widget), "tess_obj", obj);
}

static GtkWidget* get_gtk_widget(TessObject* obj) {
    TessValue* v = tess_object_get_attr(obj, "__gtk_widget");
    if (!v || v->tag != TESS_INT) return NULL;
    return (GtkWidget*)(intptr_t)v->data;
}

// ----------------------------------------------------------------------------
// Ayuda para extraer TessObject de un widget en callback
// ----------------------------------------------------------------------------
static TessObject* get_tess_obj_from_widget(GtkWidget* w) {
    return (TessObject*)g_object_get_data(G_OBJECT(w), "tess_obj");
}

// ----------------------------------------------------------------------------
// Callback genérico para señales sin argumentos
// ----------------------------------------------------------------------------
static void generic_callback(GtkWidget *widget, gpointer data) {
    const char* callback_name = (const char*)data;
    TessObject* obj = get_tess_obj_from_widget(widget);
    if (obj && callback_name) {
        tess_object_call(obj, (char*)callback_name, tess_make_null(), 0);
    }
}

// ----------------------------------------------------------------------------
// Callback para botón (ACTION)
// ----------------------------------------------------------------------------
static void button_clicked_cb(GtkButton *button, gpointer data) {
    const char* callback_name = (const char*)data;
    GtkWidget *widget = GTK_WIDGET(button);
    TessObject* obj = get_tess_obj_from_widget(widget);
    if (obj && callback_name) {
        tess_object_call(obj, (char*)callback_name, tess_make_null(), 0);
    }
}

// ----------------------------------------------------------------------------
// Callback para cambio de valor en controles (toggle, scale, entry)
// ----------------------------------------------------------------------------
static void value_changed_cb(GtkWidget *widget, gpointer data) {
    const char* callback_name = (const char*)data;
    TessObject* obj = get_tess_obj_from_widget(widget);
    if (!obj || !callback_name) return;
    // Construir argumento según el tipo de widget
    TessValue* arg = tess_make_null();
    if (GTK_IS_TOGGLE_BUTTON(widget)) {
        gboolean active = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget));
        arg = tess_make_bool(active);
    } else if (GTK_IS_SCALE(widget)) {
        double val = gtk_range_get_value(GTK_RANGE(widget));
        arg = tess_make_float(val);
    } else if (GTK_IS_ENTRY(widget)) {
        const char* txt = gtk_entry_get_text(GTK_ENTRY(widget));
        arg = tess_make_string((char*)txt);
    } else if (GTK_IS_COMBO_BOX(widget)) {
        // Para combobox, obtener el texto activo
        gchar* active_text = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(widget));
        arg = tess_make_string(active_text);
        g_free(active_text);
    }
    tess_object_call(obj, (char*)callback_name, arg, 1);
}

// ----------------------------------------------------------------------------
// Callback para resize de ventana
// ----------------------------------------------------------------------------
static void window_resize_cb(GtkWindow *window, GdkRectangle *allocation, gpointer data) {
    const char* callback_name = (const char*)data;
    GtkWidget *widget = GTK_WIDGET(window);
    TessObject* obj = get_tess_obj_from_widget(widget);
    if (!obj || !callback_name) return;
    int w = allocation->width;
    int h = allocation->height;
    TessValue* args = tess_array_new();
    tess_array_push(args, tess_make_int(w));
    tess_array_push(args, tess_make_int(h));
    tess_object_call(obj, (char*)callback_name, args, 2);
}

// ----------------------------------------------------------------------------
// Callback para cerrar ventana
// ----------------------------------------------------------------------------
static gboolean window_delete_cb(GtkWidget *widget, GdkEvent *event, gpointer data) {
    const char* callback_name = (const char*)data;
    TessObject* obj = get_tess_obj_from_widget(widget);
    if (obj && callback_name) {
        tess_object_call(obj, (char*)callback_name, tess_make_null(), 0);
    }
    // Permitir que GTK maneje el cierre (podemos devolver FALSE para que destruya)
    return FALSE;
}

// ============================================================================
// CLASE Interface (Ventana)
// ============================================================================
TessValue* _tess_mod_ui_Interface_new(TessValue* title, TessValue* width,
                                       TessValue* height, TessValue* mode) {
    static int argc = 1;
    static char* argv[] = {"program", NULL};
    ensure_gtk(&argc, &argv);
    const char* ctitle = tess_to_string(title);
    int w = (int)tess_to_int(width);
    int h = (int)tess_to_int(height);
    const char* cmode = tess_to_string(mode);
    GtkWidget* window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), ctitle);
    gtk_window_set_default_size(GTK_WINDOW(window), w, h);
    if (strcmp(cmode, "fullscreen") == 0)
        gtk_window_fullscreen(GTK_WINDOW(window));
    else if (strcmp(cmode, "dialog") == 0)
        gtk_window_set_type_hint(GTK_WINDOW(window), GDK_WINDOW_TYPE_HINT_DIALOG);
    // mode "tray" no soportado directamente, ignorar
    TessObject* obj = tess_object_new("Interface");
    set_gtk_widget(obj, window);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}

TessValue* _tess_mod_ui_Interface_mount(TessValue* self, TessValue* container) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(container);
    GtkWidget* window = get_gtk_widget(win_obj);
    GtkWidget* child = get_gtk_widget(cont_obj);
    gtk_container_add(GTK_CONTAINER(window), child);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_run(TessValue* self) {
    gtk_main();
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_show(TessValue* self) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_widget_show_all(window);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_hide(TessValue* self) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_widget_hide(window);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_close(TessValue* self) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_widget_destroy(window);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setTitle(TessValue* self, TessValue* title) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_window_set_title(GTK_WINDOW(window), tess_to_string(title));
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setSize(TessValue* self, TessValue* width, TessValue* height) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_window_set_default_size(GTK_WINDOW(window),
                                (int)tess_to_int(width),
                                (int)tess_to_int(height));
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setMinSize(TessValue* self, TessValue* width, TessValue* height) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_window_set_geometry_hints(GTK_WINDOW(window), NULL,
                                   NULL, NULL,
                                   (int)tess_to_int(width),
                                   (int)tess_to_int(height),
                                   0, 0, 0);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setResizable(TessValue* self, TessValue* value) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_window_set_resizable(GTK_WINDOW(window), tess_to_bool(value));
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setIcon(TessValue* self, TessValue* path) {
    // GTK: gtk_window_set_icon_from_file
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    GError* error = NULL;
    gtk_window_set_icon_from_file(GTK_WINDOW(window), tess_to_string(path), &error);
    if (error) g_error_free(error);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setTheme(TessValue* self, TessValue* theme) {
    // GTK no tiene tema por código fácil, ignorar
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_setBackground(TessValue* self, TessValue* color) {
    // color string ej "#RRGGBB"
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    GdkRGBA rgba;
    if (gdk_rgba_parse(&rgba, tess_to_string(color))) {
        gtk_widget_override_background_color(window, GTK_STATE_FLAG_NORMAL, &rgba);
    }
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_center(TessValue* self) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    gtk_window_set_position(GTK_WINDOW(window), GTK_WIN_POS_CENTER);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_onClose(TessValue* self, TessValue* callback) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    const char* cbname = tess_to_string(callback);
    // Guardar nombre en el objeto
    tess_object_set_attr(win_obj, "__onClose_callback", callback);
    g_signal_connect(window, "delete-event", G_CALLBACK(window_delete_cb), (void*)cbname);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_onResize(TessValue* self, TessValue* callback) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(win_obj, "__onResize_callback", callback);
    g_signal_connect(window, "configure-event", G_CALLBACK(window_resize_cb), (void*)cbname);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_onFocus(TessValue* self, TessValue* callback) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(win_obj, "__onFocus_callback", callback);
    g_signal_connect(window, "focus-in-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Interface_onBlur(TessValue* self, TessValue* callback) {
    TessObject* win_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* window = get_gtk_widget(win_obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(win_obj, "__onBlur_callback", callback);
    g_signal_connect(window, "focus-out-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}

// ============================================================================
// CLASE Container (contenedor con layout)
// ============================================================================
TessValue* _tess_mod_ui_Container_new(TessValue* layout, TessValue* id) {
    ensure_gtk(NULL, NULL);
    const char* clayout = tess_to_string(layout);
    GtkWidget* box = NULL;
    if (strcmp(clayout, "column") == 0) {
        box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    } else if (strcmp(clayout, "row") == 0) {
        box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    } else if (strcmp(clayout, "grid") == 0) {
        box = gtk_grid_new();
    } else if (strcmp(clayout, "stack") == 0) {
        box = gtk_stack_new();
    } else if (strcmp(clayout, "absolute") == 0) {
        box = gtk_fixed_new();
    } else {
        box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    }
    TessObject* obj = tess_object_new("Container");
    set_gtk_widget(obj, box);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}

TessValue* _tess_mod_ui_Container_add(TessValue* self, TessValue* component) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    TessObject* child_obj = (TessObject*)(intptr_t)tess_to_int(component);
    GtkWidget* container = get_gtk_widget(cont_obj);
    GtkWidget* child = get_gtk_widget(child_obj);
    if (GTK_IS_BOX(container)) {
        gtk_box_pack_start(GTK_BOX(container), child, FALSE, FALSE, 0);
    } else if (GTK_IS_GRID(container)) {
        gtk_grid_attach(GTK_GRID(container), child, 0, 0, 1, 1);
    } else if (GTK_IS_STACK(container)) {
        gtk_stack_add_named(GTK_STACK(container), child, "child");
    } else if (GTK_IS_FIXED(container)) {
        gtk_fixed_put(GTK_FIXED(container), child, 0, 0);
    } else {
        gtk_container_add(GTK_CONTAINER(container), child);
    }
    gtk_widget_show(child);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_addAt(TessValue* self, TessValue* component, TessValue* index) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    TessObject* child_obj = (TessObject*)(intptr_t)tess_to_int(component);
    GtkWidget* container = get_gtk_widget(cont_obj);
    GtkWidget* child = get_gtk_widget(child_obj);
    int pos = (int)tess_to_int(index);
    if (GTK_IS_BOX(container)) {
        gtk_box_pack_start(GTK_BOX(container), child, FALSE, FALSE, 0);
        gtk_box_reorder_child(GTK_BOX(container), child, pos);
    } // otros layouts no soportan reordenamiento fácil
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_remove(TessValue* self, TessValue* id) {
    // id no usado, removemos el último? Por simplicidad, no implementado
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_clear(TessValue* self) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    GList *children = gtk_container_get_children(GTK_CONTAINER(container));
    for (GList *l = children; l; l = l->next) {
        gtk_container_remove(GTK_CONTAINER(container), GTK_WIDGET(l->data));
    }
    g_list_free(children);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_get(TessValue* self, TessValue* id) {
    // No implementado, devolver null
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setSpacing(TessValue* self, TessValue* value) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    int spacing = (int)tess_to_int(value);
    if (GTK_IS_BOX(container))
        gtk_box_set_spacing(GTK_BOX(container), spacing);
    else if (GTK_IS_GRID(container))
        gtk_grid_set_row_spacing(GTK_GRID(container), spacing);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setPadding(TessValue* self, TessValue* top, TessValue* right, TessValue* bottom, TessValue* left) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    // Para GTK, padding se establece con CSS o con márgenes en los hijos.
    // Aquí no implementamos, pero se podría con gtk_widget_set_margin_start, etc.
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setAlign(TessValue* self, TessValue* main, TessValue* cross) {
    // No implementado
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setScroll(TessValue* self, TessValue* axis) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    // Envolver en GtkScrolledWindow
    GtkWidget* scrolled = gtk_scrolled_window_new(NULL, NULL);
    const char* a = tess_to_string(axis);
    if (strcmp(a, "x") == 0)
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scrolled), GTK_POLICY_AUTOMATIC, GTK_POLICY_NEVER);
    else if (strcmp(a, "y") == 0)
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scrolled), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    else if (strcmp(a, "both") == 0)
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scrolled), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    else
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scrolled), GTK_POLICY_NEVER, GTK_POLICY_NEVER);
    // Reemplazar container por scrolled y meter container dentro
    GtkWidget* parent = gtk_widget_get_parent(container);
    if (parent) {
        gtk_container_remove(GTK_CONTAINER(parent), container);
        gtk_container_add(GTK_CONTAINER(parent), scrolled);
        gtk_container_add(GTK_CONTAINER(scrolled), container);
    }
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setBackground(TessValue* self, TessValue* color) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    GdkRGBA rgba;
    if (gdk_rgba_parse(&rgba, tess_to_string(color))) {
        gtk_widget_override_background_color(container, GTK_STATE_FLAG_NORMAL, &rgba);
    }
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setBorder(TessValue* self, TessValue* width, TessValue* color, TessValue* radius) {
    // Usar CSS
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    char css[256];
    snprintf(css, sizeof(css), "border: %dpx solid %s; border-radius: %dpx;",
             (int)tess_to_int(width), tess_to_string(color), (int)tess_to_int(radius));
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    GtkStyleContext* context = gtk_widget_get_style_context(container);
    gtk_style_context_add_provider(context, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setSize(TessValue* self, TessValue* width, TessValue* height) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    const char* wstr = tess_to_string(width);
    const char* hstr = tess_to_string(height);
    int w = (strcmp(wstr, "auto") == 0) ? -1 : (int)tess_to_int(width);
    int h = (strcmp(hstr, "auto") == 0) ? -1 : (int)tess_to_int(height);
    if (w > 0) gtk_widget_set_size_request(container, w, -1);
    if (h > 0) gtk_widget_set_size_request(container, -1, h);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setVisible(TessValue* self, TessValue* value) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    if (tess_to_bool(value))
        gtk_widget_show(container);
    else
        gtk_widget_hide(container);
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setId(TessValue* self, TessValue* id) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    gtk_widget_set_name(container, tess_to_string(id));
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_setGrid(TessValue* self, TessValue* cols, TessValue* rows, TessValue* gap) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    if (GTK_IS_GRID(container)) {
        // No hay función directa, solo al añadir se especifica posición
    }
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_gridPlace(TessValue* self, TessValue* col, TessValue* row, TessValue* colSpan, TessValue* rowSpan) {
    // Se aplica al componente hijo, no al contenedor. Ignoramos aquí.
    return tess_make_null();
}

TessValue* _tess_mod_ui_Container_style(TessValue* self, TessValue* key, TessValue* value) {
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* container = get_gtk_widget(cont_obj);
    // Aplicar CSS dinámico
    char css[256];
    snprintf(css, sizeof(css), "%s: %s;", tess_to_string(key), tess_to_string(value));
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    GtkStyleContext* context = gtk_widget_get_style_context(container);
    gtk_style_context_add_provider(context, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    return tess_make_null();
}

// ============================================================================
// CLASE Label
// ============================================================================
TessValue* _tess_mod_ui_Label_new(TessValue* text, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* label = gtk_label_new(tess_to_string(text));
    TessObject* obj = tess_object_new("Label");
    set_gtk_widget(obj, label);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Label_setText(TessValue* self, TessValue* text) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    gtk_label_set_text(GTK_LABEL(label), tess_to_string(text));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Label_getText(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    const char* txt = gtk_label_get_text(GTK_LABEL(label));
    return tess_make_string((char*)txt);
}
TessValue* _tess_mod_ui_Label_setFont(TessValue* self, TessValue* family, TessValue* size, TessValue* weight) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    char css[128];
    snprintf(css, sizeof(css), "font-family: %s; font-size: %dpt; font-weight: %s;",
             tess_to_string(family), (int)tess_to_int(size), tess_to_string(weight));
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    GtkStyleContext* context = gtk_widget_get_style_context(label);
    gtk_style_context_add_provider(context, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Label_setColor(TessValue* self, TessValue* color) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    char css[64];
    snprintf(css, sizeof(css), "color: %s;", tess_to_string(color));
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    GtkStyleContext* context = gtk_widget_get_style_context(label);
    gtk_style_context_add_provider(context, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Label_setAlign(TessValue* self, TessValue* align) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    const char* a = tess_to_string(align);
    float x = 0.0f, y = 0.5f;
    if (strcmp(a, "left") == 0) x = 0.0f;
    else if (strcmp(a, "center") == 0) x = 0.5f;
    else if (strcmp(a, "right") == 0) x = 1.0f;
    gtk_label_set_xalign(GTK_LABEL(label), x);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Label_setWrap(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    gtk_label_set_line_wrap(GTK_LABEL(label), tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Label_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* label = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(label);
    else gtk_widget_hide(label);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Label_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value); // mismo helper
}

// ============================================================================
// CLASE Button
// ============================================================================
TessValue* _tess_mod_ui_Button_new(TessValue* text, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* button = gtk_button_new_with_label(tess_to_string(text));
    TessObject* obj = tess_object_new("Button");
    set_gtk_widget(obj, button);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Button_setText(TessValue* self, TessValue* text) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    gtk_button_set_label(GTK_BUTTON(button), tess_to_string(text));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setIcon(TessValue* self, TessValue* path, TessValue* position) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    GtkWidget* image = gtk_image_new_from_file(tess_to_string(path));
    gtk_button_set_image(GTK_BUTTON(button), image);
    const char* pos = tess_to_string(position);
    if (strcmp(pos, "left") == 0)
        gtk_button_set_image_position(GTK_BUTTON(button), GTK_POS_LEFT);
    else if (strcmp(pos, "right") == 0)
        gtk_button_set_image_position(GTK_BUTTON(button), GTK_POS_RIGHT);
    else if (strcmp(pos, "top") == 0)
        gtk_button_set_image_position(GTK_BUTTON(button), GTK_POS_TOP);
    else if (strcmp(pos, "bottom") == 0)
        gtk_button_set_image_position(GTK_BUTTON(button), GTK_POS_BOTTOM);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setEnabled(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    gtk_widget_set_sensitive(button, tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setVariant(TessValue* self, TessValue* variant) {
    // Aplicar clases CSS
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    GtkStyleContext* context = gtk_widget_get_style_context(button);
    const char* v = tess_to_string(variant);
    if (strcmp(v, "primary") == 0)
        gtk_style_context_add_class(context, "primary");
    else if (strcmp(v, "danger") == 0)
        gtk_style_context_add_class(context, "danger");
    // etc.
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setSize(TessValue* self, TessValue* size) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    const char* s = tess_to_string(size);
    if (strcmp(s, "sm") == 0)
        gtk_widget_set_size_request(button, 80, 24);
    else if (strcmp(s, "md") == 0)
        gtk_widget_set_size_request(button, 100, 28);
    else if (strcmp(s, "lg") == 0)
        gtk_widget_set_size_request(button, 120, 32);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setFullWidth(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    if (tess_to_bool(value))
        gtk_widget_set_hexpand(button, TRUE);
    else
        gtk_widget_set_hexpand(button, FALSE);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setLoading(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    if (tess_to_bool(value)) {
        gtk_widget_set_sensitive(button, FALSE);
        gtk_button_set_label(GTK_BUTTON(button), "Loading...");
    } else {
        gtk_widget_set_sensitive(button, TRUE);
        gtk_button_set_label(GTK_BUTTON(button), "Button");
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(button);
    else gtk_widget_hide(button);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_onClick(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onClick_callback", callback);
    g_signal_connect(button, "clicked", G_CALLBACK(button_clicked_cb), (void*)cbname);
    return tess_make_null();
}
// onHover: usar "enter" y "leave"
static void enter_cb(GtkWidget *w, gpointer data) {
    generic_callback(w, data);
}
static void leave_cb(GtkWidget *w, gpointer data) {
    generic_callback(w, data);
}
TessValue* _tess_mod_ui_Button_onHover(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onHover_callback", callback);
    g_signal_connect(button, "enter-notify-event", G_CALLBACK(enter_cb), (void*)cbname);
    g_signal_connect(button, "leave-notify-event", G_CALLBACK(leave_cb), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_onFocus(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onFocus_callback", callback);
    g_signal_connect(button, "focus-in-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_onBlur(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* button = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onBlur_callback", callback);
    g_signal_connect(button, "focus-out-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Button_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// CLASE Input (GtkEntry)
// ============================================================================
TessValue* _tess_mod_ui_Input_new(TessValue* placeholder, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry), tess_to_string(placeholder));
    TessObject* obj = tess_object_new("Input");
    set_gtk_widget(obj, entry);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Input_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_entry_set_text(GTK_ENTRY(entry), tess_to_string(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_getValue(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    const char* txt = gtk_entry_get_text(GTK_ENTRY(entry));
    return tess_make_string((char*)txt);
}
TessValue* _tess_mod_ui_Input_setPlaceholder(TessValue* self, TessValue* text) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry), tess_to_string(text));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setType(TessValue* self, TessValue* type) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    const char* t = tess_to_string(type);
    if (strcmp(t, "password") == 0)
        gtk_entry_set_visibility(GTK_ENTRY(entry), FALSE);
    else
        gtk_entry_set_visibility(GTK_ENTRY(entry), TRUE);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setLabel(TessValue* self, TessValue* text) {
    // No soportado directamente, se necesitaría un GtkLabel aparte
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setHint(TessValue* self, TessValue* text) {
    return _tess_mod_ui_Input_setPlaceholder(self, text);
}
TessValue* _tess_mod_ui_Input_setError(TessValue* self, TessValue* message) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_entry_set_icon_from_icon_name(GTK_ENTRY(entry), GTK_ENTRY_ICON_SECONDARY, "dialog-warning");
    gtk_entry_set_icon_tooltip_text(GTK_ENTRY(entry), GTK_ENTRY_ICON_SECONDARY, tess_to_string(message));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_clearError(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_entry_set_icon_from_icon_name(GTK_ENTRY(entry), GTK_ENTRY_ICON_SECONDARY, NULL);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setEnabled(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_widget_set_sensitive(entry, tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setReadOnly(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_editable_set_editable(GTK_EDITABLE(entry), !tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setMaxLength(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_entry_set_max_length(GTK_ENTRY(entry), (int)tess_to_int(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setPattern(TessValue* self, TessValue* regex) {
    // Validación con regex no nativa, ignorar
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_clear(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_entry_set_text(GTK_ENTRY(entry), "");
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_focus(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    gtk_widget_grab_focus(entry);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(entry);
    else gtk_widget_hide(entry);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_onChange(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onChange_callback", callback);
    g_signal_connect(entry, "changed", G_CALLBACK(value_changed_cb), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_onSubmit(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onSubmit_callback", callback);
    g_signal_connect(entry, "activate", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_onFocus(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onFocus_callback", callback);
    g_signal_connect(entry, "focus-in-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_onBlur(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* entry = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onBlur_callback", callback);
    g_signal_connect(entry, "focus-out-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Input_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// TextArea (GtkTextView)
// ============================================================================
TessValue* _tess_mod_ui_TextArea_new(TessValue* placeholder, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* view = gtk_text_view_new();
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(view), GTK_WRAP_WORD);
    // Placeholder no es directo, se puede poner un GtkEntry como overlay, pero simplificamos
    TessObject* obj = tess_object_new("TextArea");
    set_gtk_widget(obj, view);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_TextArea_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* view = get_gtk_widget(obj);
    GtkTextBuffer* buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(view));
    gtk_text_buffer_set_text(buffer, tess_to_string(value), -1);
    return tess_make_null();
}
TessValue* _tess_mod_ui_TextArea_getValue(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* view = get_gtk_widget(obj);
    GtkTextBuffer* buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(view));
    GtkTextIter start, end;
    gtk_text_buffer_get_bounds(buffer, &start, &end);
    char* txt = gtk_text_buffer_get_text(buffer, &start, &end, FALSE);
    TessValue* ret = tess_make_string(txt);
    g_free(txt);
    return ret;
}
// setPlaceholder, setType, setLabel, setHint, setError, clearError, setEnabled, setReadOnly, setMaxLength, setPattern, clear, focus, setVisible, onChange, onSubmit, onFocus, onBlur, style se omiten por brevedad pero siguen patrón similar
TessValue* _tess_mod_ui_TextArea_setRows(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* view = get_gtk_widget(obj);
    gtk_widget_set_size_request(view, -1, (int)tess_to_int(value) * 20); // aproximado
    return tess_make_null();
}
TessValue* _tess_mod_ui_TextArea_setResize(TessValue* self, TessValue* mode) {
    // GTK permite redimensionamiento con GtkPaned o políticas, ignorar
    return tess_make_null();
}

// ============================================================================
// Select (GtkComboBoxText)
// ============================================================================
TessValue* _tess_mod_ui_Select_new(TessValue* placeholder, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* combo = gtk_combo_box_text_new();
    gtk_combo_box_text_set_active(GTK_COMBO_BOX_TEXT(combo), -1);
    TessObject* obj = tess_object_new("Select");
    set_gtk_widget(obj, combo);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Select_addOption(TessValue* self, TessValue* value, TessValue* label) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* combo = get_gtk_widget(obj);
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), tess_to_string(value), tess_to_string(label));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Select_addOptions(TessValue* self, TessValue* data) {
    // data es un array de TessValue*, cada uno es un diccionario o array
    if (!data || data->tag != TESS_ARRAY) return tess_make_null();
    int64_t len = tess_array_len(data);
    for (int64_t i = 0; i < len; i++) {
        TessValue* item = tess_array_get(data, i);
        if (item && item->tag == TESS_ARRAY && tess_array_len(item) >= 2) {
            TessValue* val = tess_array_get(item, 0);
            TessValue* lbl = tess_array_get(item, 1);
            _tess_mod_ui_Select_addOption(self, val, lbl);
        }
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_Select_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* combo = get_gtk_widget(obj);
    gtk_combo_box_text_set_active(GTK_COMBO_BOX_TEXT(combo), -1);
    // buscar por id
    // no implementado búsqueda
    return tess_make_null();
}
TessValue* _tess_mod_ui_Select_getValue(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* combo = get_gtk_widget(obj);
    gchar* active = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(combo));
    TessValue* ret = tess_make_string(active ? active : "");
    g_free(active);
    return ret;
}
// getValueAll, setMultiple, setSearchable, setEnabled, clear, setVisible, onChange, style

// ============================================================================
// Checkbox (GtkCheckButton)
// ============================================================================
TessValue* _tess_mod_ui_Checkbox_new(TessValue* label, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* check = gtk_check_button_new_with_label(tess_to_string(label));
    TessObject* obj = tess_object_new("Checkbox");
    set_gtk_widget(obj, check);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Checkbox_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* check = get_gtk_widget(obj);
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(check), tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Checkbox_getValue(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* check = get_gtk_widget(obj);
    return tess_make_bool(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(check)));
}
TessValue* _tess_mod_ui_Checkbox_setLabel(TessValue* self, TessValue* text) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* check = get_gtk_widget(obj);
    gtk_button_set_label(GTK_BUTTON(check), tess_to_string(text));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Checkbox_setEnabled(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* check = get_gtk_widget(obj);
    gtk_widget_set_sensitive(check, tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Checkbox_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* check = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(check);
    else gtk_widget_hide(check);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Checkbox_onChange(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* check = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onChange_callback", callback);
    g_signal_connect(check, "toggled", G_CALLBACK(value_changed_cb), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Checkbox_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Toggle (GtkSwitch)
// ============================================================================
TessValue* _tess_mod_ui_Toggle_new(TessValue* label, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* sw = gtk_switch_new();
    // label se ignora porque GtkSwitch no tiene label
    TessObject* obj = tess_object_new("Toggle");
    set_gtk_widget(obj, sw);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Toggle_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* sw = get_gtk_widget(obj);
    gtk_switch_set_active(GTK_SWITCH(sw), tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Toggle_getValue(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* sw = get_gtk_widget(obj);
    return tess_make_bool(gtk_switch_get_active(GTK_SWITCH(sw)));
}
// setLabel, setEnabled, setVisible, onChange, style

// ============================================================================
// Slider (GtkScale)
// ============================================================================
TessValue* _tess_mod_ui_Slider_new(TessValue* min, TessValue* max, TessValue* step, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* scale = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL,
                                                tess_to_float(min),
                                                tess_to_float(max),
                                                tess_to_float(step));
    TessObject* obj = tess_object_new("Slider");
    set_gtk_widget(obj, scale);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Slider_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    gtk_range_set_value(GTK_RANGE(scale), tess_to_float(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_getValue(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    double val = gtk_range_get_value(GTK_RANGE(scale));
    return tess_make_float(val);
}
TessValue* _tess_mod_ui_Slider_setRange(TessValue* self, TessValue* min, TessValue* max) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    gtk_range_set_range(GTK_RANGE(scale), tess_to_float(min), tess_to_float(max));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_setStep(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    gtk_range_set_increments(GTK_RANGE(scale), tess_to_float(value), tess_to_float(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_setOrientation(TessValue* self, TessValue* orientation) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    GtkOrientation orient = GTK_ORIENTATION_HORIZONTAL;
    if (strcmp(tess_to_string(orientation), "vertical") == 0)
        orient = GTK_ORIENTATION_VERTICAL;
    gtk_orientable_set_orientation(GTK_ORIENTABLE(scale), orient);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_setEnabled(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    gtk_widget_set_sensitive(scale, tess_to_bool(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(scale);
    else gtk_widget_hide(scale);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_onChange(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onChange_callback", callback);
    g_signal_connect(scale, "value-changed", G_CALLBACK(value_changed_cb), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_onRelease(TessValue* self, TessValue* callback) {
    // similar a onChange pero con button-release-event
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* scale = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onRelease_callback", callback);
    g_signal_connect(scale, "button-release-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Slider_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Image (GtkImage)
// ============================================================================
TessValue* _tess_mod_ui_Image_new(TessValue* src, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* image = gtk_image_new_from_file(tess_to_string(src));
    TessObject* obj = tess_object_new("Image");
    set_gtk_widget(obj, image);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Image_setSrc(TessValue* self, TessValue* path) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* image = get_gtk_widget(obj);
    gtk_image_set_from_file(GTK_IMAGE(image), tess_to_string(path));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_setAlt(TessValue* self, TessValue* text) {
    // GTK no tiene alt, se puede poner tooltip
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* image = get_gtk_widget(obj);
    gtk_widget_set_tooltip_text(image, tess_to_string(text));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_setSize(TessValue* self, TessValue* width, TessValue* height) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* image = get_gtk_widget(obj);
    gtk_widget_set_size_request(image, (int)tess_to_int(width), (int)tess_to_int(height));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_setFit(TessValue* self, TessValue* fit) {
    // GTK no tiene fit, se puede usar gtk_image_set_pixel_size o CSS
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* image = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(image);
    else gtk_widget_hide(image);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_onClick(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* image = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onClick_callback", callback);
    g_signal_connect(image, "button-press-event", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_onLoad(TessValue* self, TessValue* callback) {
    // GTK no tiene señal de carga para imagen desde archivo
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_onError(TessValue* self, TessValue* callback) {
    return tess_make_null();
}
TessValue* _tess_mod_ui_Image_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Progress (GtkProgressBar)
// ============================================================================
TessValue* _tess_mod_ui_Progress_new(TessValue* value, TessValue* max, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* bar = gtk_progress_bar_new();
    double val = tess_to_float(value);
    double mx = tess_to_float(max);
    if (mx > 0) gtk_progress_bar_set_fraction(GTK_PROGRESS_BAR(bar), val / mx);
    TessObject* obj = tess_object_new("Progress");
    set_gtk_widget(obj, bar);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Progress_setValue(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* bar = get_gtk_widget(obj);
    gtk_progress_bar_set_fraction(GTK_PROGRESS_BAR(bar), tess_to_float(value));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Progress_setMax(TessValue* self, TessValue* value) {
    // No se usa directamente, se puede guardar en atributo
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    tess_object_set_attr(obj, "__max", value);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Progress_setMode(TessValue* self, TessValue* mode) {
    // GTK solo tiene fraction, no hay modo ring/linear
    return tess_make_null();
}
TessValue* _tess_mod_ui_Progress_setLabel(TessValue* self, TessValue* text) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* bar = get_gtk_widget(obj);
    gtk_progress_bar_set_text(GTK_PROGRESS_BAR(bar), tess_to_string(text));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Progress_setIndeterminate(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* bar = get_gtk_widget(obj);
    if (tess_to_bool(value))
        gtk_progress_bar_pulse(GTK_PROGRESS_BAR(bar));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Progress_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* bar = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(bar);
    else gtk_widget_hide(bar);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Progress_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Spinner (GtkSpinner)
// ============================================================================
TessValue* _tess_mod_ui_Spinner_new(TessValue* size, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* spinner = gtk_spinner_new();
    TessObject* obj = tess_object_new("Spinner");
    set_gtk_widget(obj, spinner);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Spinner_setSize(TessValue* self, TessValue* size) {
    // GTK no tiene tamaño estándar, se puede usar CSS
    return tess_make_null();
}
TessValue* _tess_mod_ui_Spinner_setColor(TessValue* self, TessValue* color) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* spinner = get_gtk_widget(obj);
    char css[64];
    snprintf(css, sizeof(css), "color: %s;", tess_to_string(color));
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    GtkStyleContext* context = gtk_widget_get_style_context(spinner);
    gtk_style_context_add_provider(context, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Spinner_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* spinner = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_spinner_start(GTK_SPINNER(spinner));
    else gtk_spinner_stop(GTK_SPINNER(spinner));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Spinner_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Separator (GtkSeparator)
// ============================================================================
TessValue* _tess_mod_ui_Separator_new(TessValue* orientation) {
    ensure_gtk(NULL, NULL);
    GtkOrientation orient = GTK_ORIENTATION_HORIZONTAL;
    if (strcmp(tess_to_string(orientation), "vertical") == 0)
        orient = GTK_ORIENTATION_VERTICAL;
    GtkWidget* sep = gtk_separator_new(orient);
    TessObject* obj = tess_object_new("Separator");
    set_gtk_widget(obj, sep);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Separator_setColor(TessValue* self, TessValue* color) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* sep = get_gtk_widget(obj);
    char css[64];
    snprintf(css, sizeof(css), "background-color: %s;", tess_to_string(color));
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    GtkStyleContext* context = gtk_widget_get_style_context(sep);
    gtk_style_context_add_provider(context, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Separator_setThickness(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* sep = get_gtk_widget(obj);
    int thick = (int)tess_to_int(value);
    gtk_widget_set_size_request(sep, thick, thick);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Separator_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// List (GtkListBox)
// ============================================================================
TessValue* _tess_mod_ui_List_new(TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* listbox = gtk_list_box_new();
    TessObject* obj = tess_object_new("List");
    set_gtk_widget(obj, listbox);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_List_addItem(TessValue* self, TessValue* text, TessValue* value, TessValue* icon) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    GtkWidget* row = gtk_list_box_row_new();
    GtkWidget* label = gtk_label_new(tess_to_string(text));
    gtk_container_add(GTK_CONTAINER(row), label);
    gtk_list_box_insert(GTK_LIST_BOX(listbox), row, -1);
    // guardar value en el row
    g_object_set_data(G_OBJECT(row), "value", g_strdup(tess_to_string(value)));
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_addItems(TessValue* self, TessValue* data) {
    // data es array de arrays o diccionarios
    if (!data || data->tag != TESS_ARRAY) return tess_make_null();
    int64_t len = tess_array_len(data);
    for (int64_t i = 0; i < len; i++) {
        TessValue* item = tess_array_get(data, i);
        if (item && item->tag == TESS_ARRAY && tess_array_len(item) >= 2) {
            TessValue* text = tess_array_get(item, 0);
            TessValue* val = tess_array_get(item, 1);
            _tess_mod_ui_List_addItem(self, text, val, tess_make_null());
        }
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_removeItem(TessValue* self, TessValue* value) {
    // No implementado
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_clear(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    gtk_container_foreach(GTK_CONTAINER(listbox), (GtkCallback)gtk_widget_destroy, NULL);
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_setData(TessValue* self, TessValue* data) {
    _tess_mod_ui_List_clear(self);
    _tess_mod_ui_List_addItems(self, data);
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_getSelected(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    GtkListBoxRow* row = gtk_list_box_get_selected_row(GTK_LIST_BOX(listbox));
    if (row) {
        char* val = (char*)g_object_get_data(G_OBJECT(row), "value");
        return tess_make_string(val ? val : "");
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_getSelectedAll(TessValue* self) {
    // No implementado
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_setSelected(TessValue* self, TessValue* value) {
    // No implementado
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_setMultiSelect(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(listbox), tess_to_bool(value) ? GTK_SELECTION_MULTIPLE : GTK_SELECTION_SINGLE);
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(listbox);
    else gtk_widget_hide(listbox);
    return tess_make_null();
}
static void listbox_row_selected_cb(GtkListBox *box, GtkListBoxRow *row, gpointer data) {
    const char* cbname = (const char*)data;
    TessObject* obj = get_tess_obj_from_widget(GTK_WIDGET(box));
    if (obj && cbname) {
        char* val = row ? (char*)g_object_get_data(G_OBJECT(row), "value") : NULL;
        TessValue* arg = tess_make_string(val ? val : "");
        tess_object_call(obj, (char*)cbname, arg, 1);
    }
}
TessValue* _tess_mod_ui_List_onChange(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onChange_callback", callback);
    g_signal_connect(listbox, "row-selected", G_CALLBACK(listbox_row_selected_cb), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_onDoubleClick(TessValue* self, TessValue* callback) {
    // row-activated
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* listbox = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onDoubleClick_callback", callback);
    g_signal_connect(listbox, "row-activated", G_CALLBACK(generic_callback), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_List_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Table (GtkTreeView)
// ============================================================================
TessValue* _tess_mod_ui_Table_new(TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* treeview = gtk_tree_view_new();
    TessObject* obj = tess_object_new("Table");
    set_gtk_widget(obj, treeview);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
// setColumns, setData, addRow, removeRow, updateRow, getRow, clear, setSortable, setSelectable, getSelected, setPagination, setPage, setStriped, setVisible, onSelect, onSort, style
// No implementamos todas por brevedad, pero el patrón es similar a List.

// ============================================================================
// Tabs (GtkNotebook)
// ============================================================================
TessValue* _tess_mod_ui_Tabs_new(TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* notebook = gtk_notebook_new();
    TessObject* obj = tess_object_new("Tabs");
    set_gtk_widget(obj, notebook);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
TessValue* _tess_mod_ui_Tabs_addTab(TessValue* self, TessValue* key, TessValue* label, TessValue* container) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    TessObject* cont_obj = (TessObject*)(intptr_t)tess_to_int(container);
    GtkWidget* child = get_gtk_widget(cont_obj);
    GtkWidget* tab_label = gtk_label_new(tess_to_string(label));
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), child, tab_label);
    // Guardar key asociada
    g_object_set_data(G_OBJECT(child), "tab_key", g_strdup(tess_to_string(key)));
    return tess_make_null();
}
TessValue* _tess_mod_ui_Tabs_removeTab(TessValue* self, TessValue* key) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    int n = gtk_notebook_get_n_pages(GTK_NOTEBOOK(notebook));
    for (int i = 0; i < n; i++) {
        GtkWidget* page = gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook), i);
        char* k = (char*)g_object_get_data(G_OBJECT(page), "tab_key");
        if (k && strcmp(k, tess_to_string(key)) == 0) {
            gtk_notebook_remove_page(GTK_NOTEBOOK(notebook), i);
            break;
        }
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_Tabs_setActive(TessValue* self, TessValue* key) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    int n = gtk_notebook_get_n_pages(GTK_NOTEBOOK(notebook));
    for (int i = 0; i < n; i++) {
        GtkWidget* page = gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook), i);
        char* k = (char*)g_object_get_data(G_OBJECT(page), "tab_key");
        if (k && strcmp(k, tess_to_string(key)) == 0) {
            gtk_notebook_set_current_page(GTK_NOTEBOOK(notebook), i);
            break;
        }
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_Tabs_getActive(TessValue* self) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    int idx = gtk_notebook_get_current_page(GTK_NOTEBOOK(notebook));
    if (idx >= 0) {
        GtkWidget* page = gtk_notebook_get_nth_page(GTK_NOTEBOOK(notebook), idx);
        char* k = (char*)g_object_get_data(G_OBJECT(page), "tab_key");
        return tess_make_string(k ? k : "");
    }
    return tess_make_null();
}
TessValue* _tess_mod_ui_Tabs_setPosition(TessValue* self, TessValue* position) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    const char* pos = tess_to_string(position);
    GtkPositionType p = GTK_POS_TOP;
    if (strcmp(pos, "bottom") == 0) p = GTK_POS_BOTTOM;
    else if (strcmp(pos, "left") == 0) p = GTK_POS_LEFT;
    else if (strcmp(pos, "right") == 0) p = GTK_POS_RIGHT;
    gtk_notebook_set_tab_pos(GTK_NOTEBOOK(notebook), p);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Tabs_setVisible(TessValue* self, TessValue* value) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    if (tess_to_bool(value)) gtk_widget_show(notebook);
    else gtk_widget_hide(notebook);
    return tess_make_null();
}
static void notebook_switch_cb(GtkNotebook *notebook, GtkWidget *page, guint page_num, gpointer data) {
    const char* cbname = (const char*)data;
    TessObject* obj = get_tess_obj_from_widget(GTK_WIDGET(notebook));
    if (obj && cbname) {
        char* key = (char*)g_object_get_data(G_OBJECT(page), "tab_key");
        TessValue* arg = tess_make_string(key ? key : "");
        tess_object_call(obj, (char*)cbname, arg, 1);
    }
}
TessValue* _tess_mod_ui_Tabs_onChange(TessValue* self, TessValue* callback) {
    TessObject* obj = (TessObject*)(intptr_t)tess_to_int(self);
    GtkWidget* notebook = get_gtk_widget(obj);
    const char* cbname = tess_to_string(callback);
    tess_object_set_attr(obj, "__onChange_callback", callback);
    g_signal_connect(notebook, "switch-page", G_CALLBACK(notebook_switch_cb), (void*)cbname);
    return tess_make_null();
}
TessValue* _tess_mod_ui_Tabs_style(TessValue* self, TessValue* key, TessValue* value) {
    return _tess_mod_ui_Container_style(self, key, value);
}

// ============================================================================
// Canvas (GtkDrawingArea)
// ============================================================================
TessValue* _tess_mod_ui_Canvas_new(TessValue* width, TessValue* height, TessValue* id) {
    ensure_gtk(NULL, NULL);
    GtkWidget* drawing = gtk_drawing_area_new();
    gtk_widget_set_size_request(drawing, (int)tess_to_int(width), (int)tess_to_int(height));
    TessObject* obj = tess_object_new("Canvas");
    set_gtk_widget(obj, drawing);
    TessValue* ret = tess_make_null();
    ret->tag = TESS_INT;
    ret->data = (int64_t)(intptr_t)obj;
    return ret;
}
// Los métodos de dibujo requieren almacenar un Cairo context, no implementados completamente
// Se dejarían para una segunda fase.

// ============================================================================
// MenuBar, Menu, Dialog, Notification, ColorPicker, DatePicker
// No implementados por brevedad, pero siguen el mismo patrón.
// ============================================================================

// Fin de native_registry.c