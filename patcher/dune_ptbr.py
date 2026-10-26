#!/usr/bin/env python3
"""Instalador da tradução pt-BR de Dune: Imperium (Steam).

Como funciona
  1. Os textos do jogo ficam num pacote em cache em
     %USERPROFILE%\\AppData\\LocalLow\\Unity\\Dire Wolf Digital_Dune_ Imperium\\localization.
     O instalador coloca a tradução nesse pacote.
  2. Para o português aparecer em Configurações > Idiomas, um dos 12 idiomas
     do jogo (por padrão o tcheco, cs-CZ) vira "Português (Brasil)". O arquivo
     alterado é o bundle de idiomas da pasta do jogo na Steam.
  Os originais são guardados com a extensão .original para poder restaurar.

Uso
    python dune_ptbr.py                    instala (idioma novo no menu)
    python dune_ptbr.py --substituir-ingles  instala sem mexer na pasta da Steam
                                             (o "English" do jogo passa a ser português)
    python dune_ptbr.py --slot ko-KR       usa outro idioma como "vaga" no menu
    python dune_ptbr.py --restore          volta tudo ao original
    python dune_ptbr.py --status           mostra o estado atual
"""
import argparse
import glob
import os
import re
import shutil
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import UnityPy
except ImportError:
    sys.exit("Falta o UnityPy. Rode:  pip install UnityPy")

NEW_CODE = "pt-BR"
NEW_NAME = "Português (Brasil) (pt-BR)"
DEFAULT_SLOT = "cs-CZ"
LOCALES_BUNDLE = "localization-locales_assets_all.bundle"

OVERRIDE = None  # definido por --cache (usado nos testes)
GAME_DIR_OVERRIDE = None
FROZEN = getattr(sys, "frozen", False)
HERE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
EXE_DIR = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
CACHE_GLOB = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "AppData", "LocalLow", "Unity", "Dire Wolf Digital_Dune_ Imperium",
    "localization", "*", "__data",
)


# ---------------------------------------------------------------- localização
def find_translation():
    for p in (
        os.path.join(EXE_DIR, "pt_BR.txt"),  # arquivo ao lado do instalador tem prioridade
        os.path.join(HERE, "pt_BR.txt"),
        os.path.join(HERE, "..", "translation", "pt_BR.txt"),
    ):
        if os.path.isfile(p):
            return p
    sys.exit("Não encontrei o arquivo pt_BR.txt junto do instalador.")


def find_cache():
    if OVERRIDE:
        return OVERRIDE
    found = glob.glob(CACHE_GLOB)
    if not found:
        sys.exit(
            "Cache de idiomas não encontrado.\n"
            "Abra o Dune: Imperium uma vez, com internet, até o menu principal, "
            "feche o jogo e rode este instalador de novo."
        )
    return max(found, key=os.path.getmtime)


def steam_libraries():
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.append(winreg.QueryValueEx(k, "SteamPath")[0])
    except Exception:
        pass
    roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    libs = []
    for r in roots:
        libs.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            with open(vdf, encoding="utf-8", errors="replace") as f:
                libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    return libs


def find_game_dir():
    if GAME_DIR_OVERRIDE:
        return GAME_DIR_OVERRIDE
    for lib in steam_libraries():
        d = os.path.join(lib, "steamapps", "common", "Dune Imperium")
        if os.path.isfile(os.path.join(d, "DuneImperium.exe")):
            return d
    return None


def locales_bundle():
    d = find_game_dir()
    if not d:
        return None
    p = os.path.join(d, "DuneImperium_Data", "StreamingAssets", "aa", "StandaloneWindows64", LOCALES_BUNDLE)
    return p if os.path.isfile(p) else None


# ------------------------------------------------------------------- utilidades
def parse(text):
    """Lê linhas chave=valor preservando a ordem. Retorna (linhas, dict)."""
    lines = text.split("\n")
    kv = {}
    for ln in lines:
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1)
            kv[k] = v
    return lines, kv


def read_script(d):
    s = d.m_Script
    return s if isinstance(s, str) else bytes(s).decode("utf-8")


def text_assets(env):
    out = {}
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            d = obj.read()
            out[d.m_Name.lower()] = (obj, d)
    return out


def backup(path):
    b = path + ".original"
    if not os.path.exists(b):
        shutil.copy2(path, b)
        print("Backup criado:", b)
    return b


def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def merged_translation(english_text):
    """Inglês do jogo com cada linha traduzida substituída. Chaves novas ficam em inglês."""
    lines, english = parse(english_text)
    with open(find_translation(), encoding="utf-8") as f:
        _, pt = parse(f.read())
    out, used = [], 0
    for ln in lines:
        if "=" in ln and not ln.startswith("#"):
            k = ln.split("=", 1)[0]
            if pt.get(k):
                ln = f"{k}={pt[k]}"
                used += 1
        out.append(ln)
    unknown = sum(1 for k in pt if k not in english)
    print(f"Traduzidas {used} de {len(english)} linhas ({used * 100 // len(english)}%).")
    if unknown:
        print(f"Aviso: {unknown} chaves da tradução não existem mais no jogo (ignoradas).")
    return "\n".join(out)


# --------------------------------------------------------------------- instalar
def patch_texts(cache, slot_code, replace_english):
    backup_path = backup(cache)
    env = UnityPy.load(backup_path)  # sempre parte do original, nunca de um patch antigo
    assets = text_assets(env)
    if "en_us" not in assets:
        sys.exit("Idioma en_US não encontrado no pacote de textos.")
    translated = merged_translation(read_script(assets["en_us"][1]))

    if replace_english:
        obj, d = assets["en_us"]
        d.m_Script = translated
        d.save()
    else:
        old = slot_code.replace("-", "_").lower()
        new = NEW_CODE.replace("-", "_").lower()
        if old not in assets:
            sys.exit(f"Idioma {slot_code} não encontrado no pacote de textos.")
        obj, d = assets[old]
        lang, region = new.split("_")
        d.m_Name = lang + "_" + region.upper()
        d.m_Script = translated
        d.save()
        for o in env.objects:  # o container mapeia caminho -> asset
            if o.type.name == "AssetBundle":
                tt = o.read_typetree()
                tt["m_Container"] = [
                    (p.replace(f"/{old}.txt", f"/{new}.txt") if p.endswith(f"/{old}.txt") else p, v)
                    for p, v in tt["m_Container"]
                ]
                o.save_typetree(tt)
    write_atomic(cache, env.file.save(packer="lz4"))


def patch_locale(slot_code):
    path = locales_bundle()
    if not path:
        sys.exit(
            "Não encontrei a pasta do jogo na Steam.\n"
            "Use --substituir-ingles, que não precisa dela, ou informe --game-dir."
        )
    env = UnityPy.load(backup(path))
    found = False
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        tt = o.read_typetree()
        if tt.get("m_Identifier", {}).get("m_Code") == slot_code:
            tt["m_Identifier"]["m_Code"] = NEW_CODE
            tt["m_LocaleName"] = NEW_NAME
            tt["m_Name"] = NEW_NAME
            o.save_typetree(tt)
            found = True
    if not found:
        sys.exit(f"Idioma {slot_code} não encontrado no pacote de idiomas do jogo.")
    write_atomic(path, env.file.save(packer="lz4"))
    print(f"Menu de idiomas: {slot_code} agora aparece como \"{NEW_NAME}\".")


def apply(args):
    cache = find_cache()
    if args.substituir_ingles:
        restore_locale()  # garante que o menu volte ao normal
        patch_texts(cache, args.slot, replace_english=True)
        print("Pronto! No jogo, o idioma 'English' agora é português.")
    else:
        patch_texts(cache, args.slot, replace_english=False)
        patch_locale(args.slot)
        print("Pronto! Abra o jogo e escolha 'Português (Brasil)' em Configurações > Idiomas.")


def restore_locale():
    path = locales_bundle()
    if path and os.path.exists(path + ".original"):
        shutil.copy2(path + ".original", path)
        return True
    return False


def restore(args):
    cache = find_cache()
    did = False
    if os.path.exists(cache + ".original"):
        shutil.copy2(cache + ".original", cache)
        did = True
    did = restore_locale() or did
    print("Original restaurado." if did else "Nenhum backup encontrado; nada para restaurar.")


def status(args):
    cache = find_cache()
    print("Cache de textos:", cache)
    print("  backup:", "sim" if os.path.exists(cache + ".original") else "não")
    env = UnityPy.load(cache)
    assets = text_assets(env)
    print("  idiomas no pacote:", ", ".join(sorted(assets)))
    for name in ("pt_br", "en_us"):
        if name in assets:
            _, kv = parse(read_script(assets[name][1]))
            print(f"  {name}: button.play = {kv.get('button.play')}")
    lb = locales_bundle()
    print("Bundle de idiomas da Steam:", lb or "não encontrado")
    if lb:
        print("  backup:", "sim" if os.path.exists(lb + ".original") else "não")


# --------------------------------------------------------------------------- CLI
def menu():
    print("Dune: Imperium - traducao pt-BR")
    print()
    print("  1) Instalar (Portugues aparece em Configuracoes > Idiomas)")
    print("  2) Instalar substituindo o ingles (nao mexe na pasta da Steam)")
    print("  3) Restaurar o original")
    print("  4) Sair")
    print()
    return input("Escolha: ").strip()


def main():
    global OVERRIDE, GAME_DIR_OVERRIDE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--substituir-ingles", action="store_true")
    ap.add_argument("--slot", default=DEFAULT_SLOT, help="código do idioma usado como vaga (padrão: cs-CZ)")
    ap.add_argument("--cache", help="caminho do __data (avançado/testes)")
    ap.add_argument("--game-dir", help="pasta do jogo (avançado/testes)")
    a = ap.parse_args()
    OVERRIDE, GAME_DIR_OVERRIDE = a.cache, a.game_dir

    interactive = len(sys.argv) == 1 and FROZEN
    if interactive:
        choice = menu()
        if choice == "2":
            a.substituir_ingles = True
        elif choice == "3":
            a.restore = True
        elif choice != "1":
            return
    action = restore if a.restore else status if a.status else apply
    try:
        action(a)
    except SystemExit as e:  # mensagens amigáveis do sys.exit("...")
        if e.code not in (None, 0):
            print()
            print("ERRO:", e.code)
        if interactive:
            input("Pressione Enter para fechar...")
        raise
    if interactive:
        input("Pressione Enter para fechar...")


if __name__ == "__main__":
    main()
