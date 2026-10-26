/*
 * Mod loader mínimo para Dune: Imperium (Windows x64, Unity IL2CPP).
 *
 * Funciona como proxy da steam_api64.dll: os exports são repassados à DLL
 * original (steam_api64_real.dll, veja steam_api64.def gerado por
 * build_loader.py) e o DllMain inicia uma thread que usa a API IL2CPP exportada
 * pela GameAssembly.dll.
 *
 * Modos (arquivo dune_loader.ini ao lado do .exe do jogo, opcional):
 *   probe=1   grava dune_probe.txt com classes/métodos/campos do jogo
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>

static const char *LANGS =
    "english,french,italian,german,spanish,czech,japanese,polish,koreana,"
    "ukrainian,schinese,tchinese,brazilian";

__declspec(dllexport) const char *SteamAPI_ISteamApps_GetAvailableGameLanguages(void *self) {
    (void)self;
    return LANGS;
}

/* ------------------------------------------------------------------ IL2CPP */
typedef void *(*t_domain_get)(void);
typedef void **(*t_domain_get_assemblies)(void *, size_t *);
typedef void *(*t_assembly_get_image)(void *);
typedef const char *(*t_image_get_name)(void *);
typedef size_t (*t_image_get_class_count)(void *);
typedef void *(*t_image_get_class)(void *, size_t);
typedef const char *(*t_class_get_name)(void *);
typedef const char *(*t_class_get_namespace)(void *);
typedef void *(*t_class_get_methods)(void *, void **);
typedef const char *(*t_method_get_name)(void *);
typedef uint32_t (*t_method_get_param_count)(void *);
typedef void *(*t_class_get_fields)(void *, void **);
typedef const char *(*t_field_get_name)(void *);
typedef void *(*t_thread_attach)(void *);

static char g_dir[MAX_PATH];

static void path_in_game_dir(char *out, size_t n, const char *file) {
    snprintf(out, n, "%s\\%s", g_dir, file);
}

static void log_line(const char *fmt, const char *arg) {
    char p[MAX_PATH];
    path_in_game_dir(p, sizeof p, "dune_loader.log");
    FILE *f = fopen(p, "a");
    if (!f) return;
    fprintf(f, fmt, arg);
    fputc('\n', f);
    fclose(f);
}

static int ini_flag(const char *key) {
    char p[MAX_PATH];
    path_in_game_dir(p, sizeof p, "dune_loader.ini");
    FILE *f = fopen(p, "r");
    if (!f) return 0;
    char line[256];
    int v = 0;
    size_t kl = strlen(key);
    while (fgets(line, sizeof line, f)) {
        if (strncmp(line, key, kl) == 0 && line[kl] == '=') v = atoi(line + kl + 1);
    }
    fclose(f);
    return v;
}

static int skip_image(const char *n) {
    return !strcmp(n, "mscorlib.dll") || !strncmp(n, "System", 6) || !strncmp(n, "Mono", 4) ||
           !strncmp(n, "UnityEngine", 11) || !strncmp(n, "netstandard", 11) ||
           !strncmp(n, "Newtonsoft", 10) || !strncmp(n, "Unity.TextMeshPro", 17) ||
           !strncmp(n, "Unity.Burst", 11) || !strncmp(n, "Unity.Mathematics", 17);
}

static void run_probe(HMODULE ga) {
    t_domain_get domain_get = (t_domain_get)GetProcAddress(ga, "il2cpp_domain_get");
    t_domain_get_assemblies get_asms = (t_domain_get_assemblies)GetProcAddress(ga, "il2cpp_domain_get_assemblies");
    t_assembly_get_image asm_img = (t_assembly_get_image)GetProcAddress(ga, "il2cpp_assembly_get_image");
    t_image_get_name img_name = (t_image_get_name)GetProcAddress(ga, "il2cpp_image_get_name");
    t_image_get_class_count img_cc = (t_image_get_class_count)GetProcAddress(ga, "il2cpp_image_get_class_count");
    t_image_get_class img_class = (t_image_get_class)GetProcAddress(ga, "il2cpp_image_get_class");
    t_class_get_name cls_name = (t_class_get_name)GetProcAddress(ga, "il2cpp_class_get_name");
    t_class_get_namespace cls_ns = (t_class_get_namespace)GetProcAddress(ga, "il2cpp_class_get_namespace");
    t_class_get_methods cls_methods = (t_class_get_methods)GetProcAddress(ga, "il2cpp_class_get_methods");
    t_method_get_name m_name = (t_method_get_name)GetProcAddress(ga, "il2cpp_method_get_name");
    t_method_get_param_count m_pc = (t_method_get_param_count)GetProcAddress(ga, "il2cpp_method_get_param_count");
    t_class_get_fields cls_fields = (t_class_get_fields)GetProcAddress(ga, "il2cpp_class_get_fields");
    t_field_get_name f_name = (t_field_get_name)GetProcAddress(ga, "il2cpp_field_get_name");
    t_thread_attach thread_attach = (t_thread_attach)GetProcAddress(ga, "il2cpp_thread_attach");
    if (!domain_get || !get_asms || !asm_img || !img_name || !img_cc || !img_class || !cls_name || !cls_ns ||
        !cls_methods || !m_name || !m_pc || !cls_fields || !f_name || !thread_attach) {
        log_line("probe: API IL2CPP incompleta%s", "");
        return;
    }
    void *dom = domain_get();
    thread_attach(dom);
    size_t n = 0;
    void **asms = get_asms(dom, &n);
    char p[MAX_PATH];
    path_in_game_dir(p, sizeof p, "dune_probe.txt");
    FILE *out = fopen(p, "w");
    if (!out) return;
    fprintf(out, "# assemblies: %u\n", (unsigned)n);
    for (size_t a = 0; a < n; a++) {
        void *img = asm_img(asms[a]);
        const char *iname = img_name(img);
        fprintf(out, "ASSEMBLY %s classes=%u%s\n", iname, (unsigned)img_cc(img), skip_image(iname) ? " (ignorada)" : "");
    }
    for (size_t a = 0; a < n; a++) {
        void *img = asm_img(asms[a]);
        const char *iname = img_name(img);
        if (skip_image(iname)) continue;
        size_t cc = img_cc(img);
        for (size_t c = 0; c < cc; c++) {
            void *k = img_class(img, c);
            fprintf(out, "CLASS %s | %s.%s\n", iname, cls_ns(k), cls_name(k));
            void *it = NULL, *m;
            while ((m = cls_methods(k, &it)) != NULL) fprintf(out, "  M %s/%u\n", m_name(m), (unsigned)m_pc(m));
            it = NULL;
            void *fl;
            while ((fl = cls_fields(k, &it)) != NULL) fprintf(out, "  F %s\n", f_name(fl));
        }
        fflush(out);
    }
    fclose(out);
    log_line("probe: concluído%s", "");
}


/* ------------------------------------------------------------- diagnóstico */
typedef void *(*t_class_from_name)(void *, const char *, const char *);
typedef void *(*t_class_get_method_from_name)(void *, const char *, int);
typedef void *(*t_runtime_invoke)(void *, void *, void **, void **);
typedef uint16_t *(*t_string_chars)(void *);
typedef int32_t (*t_string_length)(void *);
typedef int (*t_method_is_instance)(void *);
typedef void (*t_field_static_get_value)(void *, void *);

static void *find_image(HMODULE ga, const char *name) {
    t_domain_get domain_get = (t_domain_get)GetProcAddress(ga, "il2cpp_domain_get");
    t_domain_get_assemblies get_asms = (t_domain_get_assemblies)GetProcAddress(ga, "il2cpp_domain_get_assemblies");
    t_assembly_get_image asm_img = (t_assembly_get_image)GetProcAddress(ga, "il2cpp_assembly_get_image");
    t_image_get_name img_name = (t_image_get_name)GetProcAddress(ga, "il2cpp_image_get_name");
    size_t n = 0;
    void **asms = get_asms(domain_get(), &n);
    for (size_t i = 0; i < n; i++) {
        void *img = asm_img(asms[i]);
        if (!strcmp(img_name(img), name)) return img;
    }
    return NULL;
}

static void utf8_of_string(HMODULE ga, void *str, char *out, size_t n) {
    t_string_chars chars = (t_string_chars)GetProcAddress(ga, "il2cpp_string_chars");
    t_string_length len = (t_string_length)GetProcAddress(ga, "il2cpp_string_length");
    out[0] = 0;
    if (!str) return;
    int w = WideCharToMultiByte(CP_UTF8, 0, (LPCWCH)chars(str), len(str), out, (int)n - 1, NULL, NULL);
    out[w > 0 ? w : 0] = 0;
}

static void run_diag(HMODULE ga) {
    t_domain_get domain_get = (t_domain_get)GetProcAddress(ga, "il2cpp_domain_get");
    t_thread_attach thread_attach = (t_thread_attach)GetProcAddress(ga, "il2cpp_thread_attach");
    t_class_from_name from_name = (t_class_from_name)GetProcAddress(ga, "il2cpp_class_from_name");
    t_class_get_method_from_name get_method = (t_class_get_method_from_name)GetProcAddress(ga, "il2cpp_class_get_method_from_name");
    t_runtime_invoke invoke = (t_runtime_invoke)GetProcAddress(ga, "il2cpp_runtime_invoke");
    t_method_is_instance is_inst = (t_method_is_instance)GetProcAddress(ga, "il2cpp_method_is_instance");
    t_class_get_fields cls_fields = (t_class_get_fields)GetProcAddress(ga, "il2cpp_class_get_fields");
    t_field_get_name f_name = (t_field_get_name)GetProcAddress(ga, "il2cpp_field_get_name");
    t_field_static_get_value sget = (t_field_static_get_value)GetProcAddress(ga, "il2cpp_field_static_get_value");
    thread_attach(domain_get());

    char p[MAX_PATH];
    path_in_game_dir(p, sizeof p, "dune_diag.txt");
    FILE *out = fopen(p, "w");
    if (!out) return;

    void *img = find_image(ga, "core-localization.dll");
    fprintf(out, "image core-localization: %p\n", img);
    if (!img) { fclose(out); return; }

    /* enum localization.Locale */
    void *kEnum = from_name(img, "", "Locale");
    fprintf(out, "enum Locale class: %p\n", kEnum);
    if (kEnum) {
        void *it = NULL, *fl;
        while ((fl = cls_fields(kEnum, &it)) != NULL) {
            const char *nm = f_name(fl);
            if (!strcmp(nm, "value__")) continue;
            int v = -1;
            sget(fl, &v);
            fprintf(out, "ENUM %s = %d\n", nm, v);
        }
    }

    /* TextLocalization.GetNameForLocale */
    void *kTL = from_name(img, "localization", "TextLocalization");
    fprintf(out, "TextLocalization: %p\n", kTL);
    void *mName = kTL ? get_method(kTL, "GetNameForLocale", 1) : NULL;
    fprintf(out, "GetNameForLocale: %p instance=%d\n", mName, mName ? is_inst(mName) : -1);
    if (mName && !is_inst(mName)) {
        for (int v = 0; v < 64; v++) {
            int x = v;
            void *args[1] = { &x };
            void *exc = NULL;
            void *r = invoke(mName, NULL, args, &exc);
            char buf[256];
            utf8_of_string(ga, exc ? NULL : r, buf, sizeof buf);
            if (buf[0]) fprintf(out, "NAME[%d] = %s\n", v, buf);
        }
    }
    fclose(out);
    log_line("diag: concluído%s", "");
}


/* ------------------------------------------------- hooks (thread principal) */
typedef void *(*t_object_get_class)(void *);
typedef void *(*t_class_get_field_from_name)(void *, const char *);
typedef void (*t_field_get_value)(void *, void *, void *);
typedef void *(*t_object_unbox)(void *);

static struct {
    HMODULE ga;
    t_class_from_name from_name;
    t_class_get_method_from_name get_method;
    t_runtime_invoke invoke;
    t_object_get_class obj_class;
    t_class_get_field_from_name get_field;
    t_field_get_value field_get;
    t_object_unbox unbox;
    t_class_get_name cls_name;
} A;

static FILE *g_diag;
static void dlog(const char *fmt, ...) {
    if (!g_diag) {
        char p[MAX_PATH];
        path_in_game_dir(p, sizeof p, "dune_hook.txt");
        g_diag = fopen(p, "a");
        if (!g_diag) return;
    }
    va_list ap;
    va_start(ap, fmt);
    vfprintf(g_diag, fmt, ap);
    va_end(ap);
    fputc('\n', g_diag);
    fflush(g_diag);
}

static void *call(void *klass, const char *name, int argc, void *obj, void **args) {
    void *m = A.get_method(klass, name, argc);
    if (!m) { dlog("  (método %s/%d não encontrado)", name, argc); return NULL; }
    void *exc = NULL;
    void *r = A.invoke(m, obj, args, &exc);
    if (exc) { dlog("  (exceção em %s)", name); return NULL; }
    return r;
}

static int unbox_int(void *boxed) { return boxed ? *(int *)A.unbox(boxed) : -1; }

static void str_of(void *s, char *buf, size_t n) { utf8_of_string(A.ga, s, buf, n); }

static void inspect_dropdown(void *thiz) {
    void *k = A.obj_class(thiz);
    dlog("LocaleDropdown instância %p classe %s", thiz, A.cls_name(k));
    void *f = A.get_field(k, "localeDropdown");
    void *dd = NULL;
    if (f) A.field_get(thiz, f, &dd);
    dlog("  localeDropdown = %p", dd);
    if (!dd) return;
    void *dk = A.obj_class(dd);
    dlog("  tipo do dropdown: %s", A.cls_name(dk));
    void *list = call(dk, "get_options", 0, dd, NULL);
    if (!list) return;
    void *lk = A.obj_class(list);
    int count = unbox_int(call(lk, "get_Count", 0, list, NULL));
    dlog("  opções: %d", count);
    for (int i = 0; i < count; i++) {
        void *args[1] = { &i };
        void *opt = call(lk, "get_Item", 1, list, args);
        if (!opt) continue;
        void *ok = A.obj_class(opt);
        char buf[256];
        str_of(call(ok, "get_text", 0, opt, NULL), buf, sizeof buf);
        dlog("    [%d] %s", i, buf);
    }
    int val = unbox_int(call(dk, "get_value", 0, dd, NULL));
    dlog("  valor selecionado: %d", val);
}


/* ------------------------------------------------ adicionar o idioma pt-BR */
typedef void *(*t_string_new)(const char *);
typedef void *(*t_method_get_param)(void *, uint32_t);
typedef const char *(*t_type_get_name)(void *);

static void *find_method_by_param(void *klass, const char *name, const char *ptype) {
    t_class_get_methods cm = (t_class_get_methods)GetProcAddress(A.ga, "il2cpp_class_get_methods");
    t_method_get_name mn = (t_method_get_name)GetProcAddress(A.ga, "il2cpp_method_get_name");
    t_method_get_param_count pc = (t_method_get_param_count)GetProcAddress(A.ga, "il2cpp_method_get_param_count");
    t_method_get_param gp = (t_method_get_param)GetProcAddress(A.ga, "il2cpp_method_get_param");
    t_type_get_name tn = (t_type_get_name)GetProcAddress(A.ga, "il2cpp_type_get_name");
    void *it = NULL, *m;
    while ((m = cm(klass, &it)) != NULL) {
        if (strcmp(mn(m), name) || pc(m) != 1) continue;
        const char *t = tn(gp(m, 0));
        dlog("  overload %s(%s)", name, t ? t : "?");
        if (t && !strcmp(t, ptype)) return m;
    }
    return NULL;
}

static int g_pt_added;

static void log_locales(void *prov, void *pk) {
    void *list = call(pk, "get_Locales", 0, prov, NULL);
    if (!list) return;
    void *lk = A.obj_class(list);
    int n = unbox_int(call(lk, "get_Count", 0, list, NULL));
    dlog("  AvailableLocales: %d", n);
    for (int i = 0; i < n; i++) {
        void *args[1] = { &i };
        void *loc = call(lk, "get_Item", 1, list, args);
        void *lck = A.obj_class(loc);
        void *id = call(lck, "get_Identifier", 0, loc, NULL);
        char buf[128] = "?";
        if (id) str_of(call(A.obj_class(id), "get_Code", 0, id, NULL), buf, sizeof buf);
        dlog("    locale[%d] %s", i, buf);
    }
}

static void ensure_pt_locale(void) {
    if (g_pt_added) return;
    g_pt_added = 1;
    t_string_new snew = (t_string_new)GetProcAddress(A.ga, "il2cpp_string_new");
    void *img = find_image(A.ga, "Unity.Localization.dll");
    void *kLS = img ? A.from_name(img, "UnityEngine.Localization.Settings", "LocalizationSettings") : NULL;
    void *kLoc = img ? A.from_name(img, "UnityEngine.Localization", "Locale") : NULL;
    dlog("ensure_pt_locale: img=%p LocalizationSettings=%p Locale=%p", img, kLS, kLoc);
    if (!kLS || !kLoc) return;
    void *prov = call(kLS, "get_AvailableLocales", 0, NULL, NULL);
    if (!prov) { dlog("  sem provider"); return; }
    void *pk = A.obj_class(prov);
    dlog("  provider classe %s", A.cls_name(pk));
    log_locales(prov, pk);
    void *mCreate = find_method_by_param(kLoc, "CreateLocale", "System.String");
    dlog("  CreateLocale(string) = %p", mCreate);
    if (!mCreate) return;
    void *args[1] = { snew("pt-BR") };
    void *exc = NULL;
    void *loc = A.invoke(mCreate, NULL, args, &exc);
    dlog("  novo Locale = %p exc=%p", loc, exc);
    if (!loc || exc) return;
    void *a2[1] = { loc };
    call(pk, "AddLocale", 1, prov, a2);
    log_locales(prov, pk);
}


static const char *PT_LABEL = "Portugu\xC3\xAAs (Brasil)";
static int g_opt_added_logged;

static void add_pt_option(void *thiz) {
    void *k = A.obj_class(thiz);
    void *f = A.get_field(k, "localeDropdown");
    void *dd = NULL;
    if (f) A.field_get(thiz, f, &dd);
    if (!dd) return;
    void *dk = A.obj_class(dd);
    void *list = call(dk, "get_options", 0, dd, NULL);
    if (!list) return;
    void *lk = A.obj_class(list);
    int count = unbox_int(call(lk, "get_Count", 0, list, NULL));
    if (count != 12) { if (count != 13) dlog("add_pt_option: %d opções (esperado 12)", count); return; }
    void *last = NULL;
    { int i = count - 1; void *args[1] = { &i }; last = call(lk, "get_Item", 1, list, args); }
    if (!last) return;
    void *ok = A.obj_class(last);
    t_string_new snew = (t_string_new)GetProcAddress(A.ga, "il2cpp_string_new");
    typedef void *(*t_object_new)(void *);
    t_object_new onew = (t_object_new)GetProcAddress(A.ga, "il2cpp_object_new");
    void *ctor = find_method_by_param(ok, ".ctor", "System.String");
    if (!ctor) { dlog("add_pt_option: construtor OptionData(string) não achado"); return; }
    void *opt = onew(ok);
    void *cargs[1] = { snew(PT_LABEL) };
    void *exc = NULL;
    A.invoke(ctor, opt, cargs, &exc);
    if (exc) { dlog("add_pt_option: exceção no construtor"); return; }
    void *aargs[1] = { opt };
    call(lk, "Add", 1, list, aargs);
    int n2 = unbox_int(call(lk, "get_Count", 0, list, NULL));
    if (!g_opt_added_logged++) dlog("add_pt_option: agora %d opções", n2);
}


/* ------------------------------------------------------ inspetor de objetos */
typedef void *(*t_class_get_parent)(void *);
typedef void *(*t_field_get_type)(void *);
typedef size_t (*t_field_get_offset)(void *);
typedef int (*t_field_get_flags)(void *);
typedef uint32_t (*t_array_length)(void *);

static void print_value(const char *tn, uint64_t v, void *fieldobj_unused) {
    (void)fieldobj_unused;
    if (!strcmp(tn, "System.String")) {
        char buf[200];
        str_of((void *)(uintptr_t)v, buf, sizeof buf);
        dlog("      = \"%s\"", buf);
    } else if (strstr(tn, "[]") && v) {
        t_array_length al = (t_array_length)GetProcAddress(A.ga, "il2cpp_array_length");
        dlog("      = array len=%u (%p)", (unsigned)al((void *)(uintptr_t)v), (void *)(uintptr_t)v);
    } else if (strstr(tn, "List`1") && v) {
        void *o = (void *)(uintptr_t)v;
        int n = unbox_int(call(A.obj_class(o), "get_Count", 0, o, NULL));
        dlog("      = List count=%d (%p)", n, o);
    } else if (strstr(tn, "Dictionary") && v) {
        void *o = (void *)(uintptr_t)v;
        int n = unbox_int(call(A.obj_class(o), "get_Count", 0, o, NULL));
        dlog("      = Dictionary count=%d (%p)", n, o);
    } else {
        dlog("      = 0x%llx", (unsigned long long)v);
    }
}

static void dump_class_fields(void *obj, void *klass, int want_static) {
    t_class_get_parent par = (t_class_get_parent)GetProcAddress(A.ga, "il2cpp_class_get_parent");
    t_class_get_fields cf = (t_class_get_fields)GetProcAddress(A.ga, "il2cpp_class_get_fields");
    t_field_get_name fn = (t_field_get_name)GetProcAddress(A.ga, "il2cpp_field_get_name");
    t_field_get_type ft = (t_field_get_type)GetProcAddress(A.ga, "il2cpp_field_get_type");
    t_field_get_offset fo = (t_field_get_offset)GetProcAddress(A.ga, "il2cpp_field_get_offset");
    t_field_get_flags ff = (t_field_get_flags)GetProcAddress(A.ga, "il2cpp_field_get_flags");
    t_type_get_name tn = (t_type_get_name)GetProcAddress(A.ga, "il2cpp_type_get_name");
    t_field_static_get_value sget = (t_field_static_get_value)GetProcAddress(A.ga, "il2cpp_field_static_get_value");
    for (void *k = klass; k; k = par(k)) {
        const char *cn = A.cls_name(k);
        if (!strcmp(cn, "Object") || !strcmp(cn, "MonoBehaviour") || !strcmp(cn, "Behaviour") || !strcmp(cn, "Component")) break;
        dlog("  [classe %s]", cn);
        void *it = NULL, *fl;
        while ((fl = cf(k, &it)) != NULL) {
            int is_static = (ff(fl) & 0x10) != 0;
            if (is_static != want_static) continue;
            const char *type = tn(ft(fl));
            uint64_t v = 0;
            if (is_static) sget(fl, &v);
            else if (obj) v = *(uint64_t *)((char *)obj + fo(fl));
            dlog("    %s %s", type, fn(fl));
            print_value(type, v, NULL);
        }
    }
}

static void dump_object(void *obj, const char *label) {
    if (!obj) return;
    dlog("DUMP %s (%p)", label, obj);
    dump_class_fields(obj, A.obj_class(obj), 0);
    dump_class_fields(NULL, A.obj_class(obj), 1);
}

static void dump_statics_of(const char *image, const char *ns, const char *name) {
    void *img = find_image(A.ga, image);
    void *k = img ? A.from_name(img, ns, name) : NULL;
    dlog("DUMP estáticos de %s.%s (%p)", ns, name, k);
    if (k) dump_class_fields(NULL, k, 1);
}


/* ------------------------------------------- lista de idiomas suportados */
typedef void *(*t_array_new)(void *, uint32_t);
typedef void *(*t_class_get_element_class)(void *);
static int g_supported_done;
#define PT_BR_ENUM 3   /* localization.Locale.pt_BR */
#define PT_BR_INDEX 1  /* posição na lista (logo depois do inglês) */


static void rename_pt_label(void) {
    void *img = find_image(A.ga, "core-localization.dll");
    void *k = img ? A.from_name(img, "localization", "TextLocalization") : NULL;
    void *f = k ? A.get_field(k, "localeNames") : NULL;
    t_field_static_get_value sget = (t_field_static_get_value)GetProcAddress(A.ga, "il2cpp_field_static_get_value");
    t_string_new snew = (t_string_new)GetProcAddress(A.ga, "il2cpp_string_new");
    void *dict = NULL;
    if (f) sget(f, &dict);
    dlog("rename_pt_label: dict=%p", dict);
    if (!dict) return;
    int key = PT_BR_ENUM;
    void *args[2] = { &key, snew(PT_LABEL) };
    void *exc = NULL;
    void *m = A.get_method(A.obj_class(dict), "set_Item", 2);
    if (m) A.invoke(m, dict, args, &exc);
    dlog("  rótulo pt_BR definido (exc=%p)", exc);
}

static void patch_supported_locales(void) {
    if (g_supported_done) return;
    g_supported_done = 1;
    rename_pt_label();
    void *img = find_image(A.ga, "boardgames.dll");
    void *k = img ? A.from_name(img, "boardgames.utils", "DBGConstants") : NULL;
    dlog("DBGConstants: img=%p classe=%p", img, k);
    if (!k) return;
    dump_class_fields(NULL, k, 1);
    t_method_is_instance is_inst = (t_method_is_instance)GetProcAddress(A.ga, "il2cpp_method_is_instance");
    void *mGet = A.get_method(k, "get_SupportedLocales", 0);
    void *mSet = A.get_method(k, "set_SupportedLocales", 1);
    dlog("  get=%p set=%p instância=%d", mGet, mSet, mGet ? is_inst(mGet) : -1);
    if (!mGet || is_inst(mGet)) return;
    void *exc = NULL;
    void *coll = A.invoke(mGet, NULL, NULL, &exc);
    if (!coll || exc) { dlog("  getter falhou"); return; }
    void *ck = A.obj_class(coll);
    const char *cn = A.cls_name(ck);
    dlog("  coleção: %s (%p)", cn, coll);
    if (strstr(cn, "List")) {
        int n = unbox_int(call(ck, "get_Count", 0, coll, NULL));
        int have = 0;
        for (int i = 0; i < n; i++) {
            void *args[1] = { &i };
            int v = unbox_int(call(ck, "get_Item", 1, coll, args));
            dlog("    [%d] = %d", i, v);
            if (v == PT_BR_ENUM) have = 1;
        }
        if (!have) {
            int idx = PT_BR_INDEX < n ? PT_BR_INDEX : n, val = PT_BR_ENUM;
            void *args[2] = { &idx, &val };
            call(ck, "Insert", 2, coll, args);
            int n2 = unbox_int(call(ck, "get_Count", 0, coll, NULL));
            dlog("  pt_BR inserido na posição %d (agora %d itens)", idx, n2);
        }
    } else if (strstr(cn, "[]")) {
        t_array_length al = (t_array_length)GetProcAddress(A.ga, "il2cpp_array_length");
        t_array_new anew = (t_array_new)GetProcAddress(A.ga, "il2cpp_array_new");
        t_class_get_element_class ec = (t_class_get_element_class)GetProcAddress(A.ga, "il2cpp_class_get_element_class");
        uint32_t n = al(coll);
        int *src = (int *)((char *)coll + 0x20);
        int have = 0;
        for (uint32_t i = 0; i < n; i++) { dlog("    [%u] = %d", i, src[i]); if (src[i] == PT_BR_ENUM) have = 1; }
        if (!have && mSet) {
            void *arr = anew(ec(ck), n + 1);
            int *dst = (int *)((char *)arr + 0x20);
            uint32_t at = PT_BR_INDEX < n ? PT_BR_INDEX : n, j = 0;
            for (uint32_t i = 0; i <= n; i++) dst[i] = (i == at) ? PT_BR_ENUM : src[j++];
            void *sargs[1] = { arr };
            void *e2 = NULL;
            A.invoke(mSet, NULL, sargs, &e2);
            dlog("  pt_BR inserido no array na posição %u (exc=%p)", at, e2);
        }
    }
}

static void (*orig_OnEnable)(void *, const void *);
static void (*orig_ChangeLocale)(void *, void *, const void *);
static int g_dumped;
static void (*orig_SetLocale)(void *, void *, const void *);
static void (*orig_Start)(void *, const void *);
static int g_hits;

static void detour_OnEnable(void *thiz, const void *mi) {
    ensure_pt_locale();
    patch_supported_locales();
    if (g_hits++ < 4) dlog("== OnEnable");
    orig_OnEnable(thiz, mi);
    add_pt_option(thiz);
}
static void detour_Start(void *thiz, const void *mi) {
    ensure_pt_locale();
    patch_supported_locales();
    if (g_hits++ < 4) dlog("== Start");
    orig_Start(thiz, mi);
    add_pt_option(thiz);
}
static void detour_ChangeLocale(void *thiz, void *a1, const void *mi) {
    dlog("== Event_ChangeLocale arg=%u", (unsigned)(uintptr_t)a1);
    if (!(g_dumped & 1)) {
        g_dumped |= 1;
        dump_object(thiz, "LocaleSetting");
        dump_statics_of("core-localization.dll", "localization", "TextLocalization");
        dump_statics_of("core-localization-bridge.dll", "localization.bridge", "UnityLocalizationUtil");
        dump_statics_of("core-localization-bridge.dll", "localization.bridge", "LocaleSetting");
        dump_statics_of("dbg-client.dll", "boardgames.menus.behaviours", "LocaleDropdown");
    }
    orig_ChangeLocale(thiz, a1, mi);
}
static void detour_SetLocale(void *thiz, void *a1, const void *mi) {
    dlog("== Event_SetLocale arg=%u", (unsigned)(uintptr_t)a1);
    if (!(g_dumped & 2)) { g_dumped |= 2; dump_object(thiz, "LocaleDropdown"); }
    orig_SetLocale(thiz, a1, mi);
}

static void patch_method(void *minfo, void *detour, void **orig_out) {
    void **slot = (void **)minfo;           /* MethodInfo.methodPointer */
    *orig_out = slot[0];
    DWORD old;
    VirtualProtect(slot, 16, PAGE_READWRITE, &old);
    if (slot[1] == slot[0]) slot[1] = detour; /* virtualMethodPointer */
    slot[0] = detour;
    VirtualProtect(slot, 16, old, &old);
}

static void install_hooks(HMODULE ga) {
    A.ga = ga;
    A.from_name = (t_class_from_name)GetProcAddress(ga, "il2cpp_class_from_name");
    A.get_method = (t_class_get_method_from_name)GetProcAddress(ga, "il2cpp_class_get_method_from_name");
    A.invoke = (t_runtime_invoke)GetProcAddress(ga, "il2cpp_runtime_invoke");
    A.obj_class = (t_object_get_class)GetProcAddress(ga, "il2cpp_object_get_class");
    A.get_field = (t_class_get_field_from_name)GetProcAddress(ga, "il2cpp_class_get_field_from_name");
    A.field_get = (t_field_get_value)GetProcAddress(ga, "il2cpp_field_get_value");
    A.unbox = (t_object_unbox)GetProcAddress(ga, "il2cpp_object_unbox");
    A.cls_name = (t_class_get_name)GetProcAddress(ga, "il2cpp_class_get_name");
    t_thread_attach attach = (t_thread_attach)GetProcAddress(ga, "il2cpp_thread_attach");
    t_domain_get dget = (t_domain_get)GetProcAddress(ga, "il2cpp_domain_get");
    attach(dget());
    void *img = find_image(ga, "dbg-client.dll");
    void *k = img ? A.from_name(img, "boardgames.menus.behaviours", "LocaleDropdown") : NULL;
    dlog("hooks: imagem=%p classe=%p", img, k);
    if (!k) return;
    void *mEnable = A.get_method(k, "OnEnable", 0);
    void *mStart = A.get_method(k, "Start", 0);
    dlog("hooks: OnEnable=%p Start=%p", mEnable, mStart);
    if (mEnable) patch_method(mEnable, (void *)detour_OnEnable, (void **)&orig_OnEnable);
    if (mStart) patch_method(mStart, (void *)detour_Start, (void **)&orig_Start);
    void *mSet = A.get_method(k, "Event_SetLocale", 1);
    if (mSet) patch_method(mSet, (void *)detour_SetLocale, (void **)&orig_SetLocale);
    void *imgb = find_image(ga, "core-localization-bridge.dll");
    void *kLS = imgb ? A.from_name(imgb, "localization.bridge", "LocaleSetting") : NULL;
    void *mChg = kLS ? A.get_method(kLS, "Event_ChangeLocale", 1) : NULL;
    dlog("hooks: LocaleSetting=%p Event_ChangeLocale=%p", kLS, mChg);
    if (mChg) patch_method(mChg, (void *)detour_ChangeLocale, (void **)&orig_ChangeLocale);
    dlog("hooks instalados");
}

static DWORD WINAPI worker(LPVOID unused) {
    (void)unused;
    HMODULE ga = NULL;
    for (int i = 0; i < 600 && !ga; i++) {  /* até 60 s */
        ga = GetModuleHandleA("GameAssembly.dll");
        if (!ga) Sleep(100);
    }
    if (!ga) {
        log_line("GameAssembly.dll não carregou%s", "");
        return 0;
    }
    log_line("GameAssembly.dll encontrada%s", "");
    if (ini_flag("hook")) {
        /* instala assim que o runtime e a classe existirem (antes de o menu abrir) */
        t_domain_get dget = (t_domain_get)GetProcAddress(ga, "il2cpp_domain_get");
        for (int i = 0; i < 1200; i++) {
            void *dom = dget();
            if (dom) {
                A.ga = ga;
                A.from_name = (t_class_from_name)GetProcAddress(ga, "il2cpp_class_from_name");
                t_thread_attach attach = (t_thread_attach)GetProcAddress(ga, "il2cpp_thread_attach");
                attach(dom);
                void *img = find_image(ga, "dbg-client.dll");
                if (img && A.from_name(img, "boardgames.menus.behaviours", "LocaleDropdown")) break;
            }
            Sleep(100);
        }
        install_hooks(ga);
    }
    Sleep(25000); /* deixa o jogo inicializar */
    if (ini_flag("probe")) run_probe(ga);
    if (ini_flag("diag")) run_diag(ga);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        GetModuleFileNameA(NULL, g_dir, MAX_PATH);
        char *s = strrchr(g_dir, '\\');
        if (s) *s = 0;
        HANDLE t = CreateThread(NULL, 0, worker, NULL, 0, NULL);
        if (t) CloseHandle(t);
    }
    return TRUE;
}
