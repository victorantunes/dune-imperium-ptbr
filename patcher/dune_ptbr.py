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
import struct
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crcfix  # noqa: E402

CRC_MARKER = b"FRGE"

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


def bundle_header(data):
    """Cabeçalho UnityFS: (versão do formato, versão da Unity, flags)."""
    sig_end = data.index(bytes([0]))
    i = sig_end + 1 + 4
    pv_end = data.index(bytes([0]), i)
    uv_end = data.index(bytes([0]), pv_end + 1)
    flags = struct.unpack(">I", data[uv_end + 1 + 16: uv_end + 1 + 20])[0]
    return data[:sig_end], data[pv_end + 1:uv_end], flags


def save_like_original(env, original_path):
    """Regrava o bundle mantendo compressão/flags do original e confere o cabeçalho.

    O Unity 6 recusa bundles com flags diferentes (ex.: packer 'lz4' perde o
    preenchimento de bloco e o jogo fica em loop de erro). Por isso a gravação
    usa o packer 'original' e abortamos se o cabeçalho não for idêntico.
    """
    data = env.file.save(packer="original")
    with open(original_path, "rb") as f:
        ref = f.read(256)
    if bundle_header(data) != bundle_header(ref):
        sys.exit("O bundle gerado tem cabeçalho diferente do original; abortado para não quebrar o jogo.")
    return data


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
        # Mantém o nome/código do idioma da "vaga": o jogo só lista códigos que
        # ele conhece, então o texto é trocado sem renomear nada.
        old = slot_code.replace("-", "_").lower()
        if old not in assets:
            sys.exit(f"Idioma {slot_code} não encontrado no pacote de textos.")
        obj, d = assets[old]
        d.m_Script = translated
        d.save()
    write_atomic(cache, save_like_original(env, backup_path))



def patch_texts_add_pt(cache):
    """Acrescenta um TextAsset 'pt_BR' ao pacote de textos (sem alterar nenhum idioma)."""
    import copy
    backup_path = backup(cache)
    env = UnityPy.load(backup_path)
    assets = text_assets(env)
    if "en_us" not in assets:
        sys.exit("Idioma en_US não encontrado no pacote de textos.")
    translated = merged_translation(read_script(assets["en_us"][1]))
    if "pt_br" in assets:
        obj, _ = assets["pt_br"]
        tt = obj.read_typetree()
        tt["m_Script"] = translated
        obj.save_typetree(tt)
    else:
        src, _ = assets["en_us"]
        sf = src.assets_file
        new = copy.copy(src)
        new.path_id = max(sf.objects) + 1 if sf.objects else 1
        tt = src.read_typetree()
        tt["m_Name"] = "pt_BR"
        tt["m_Script"] = translated
        new.save_typetree(tt)
        sf.objects[new.path_id] = new
        for o in env.objects:
            if o.type.name == "AssetBundle":
                bt = o.read_typetree()
                size = len(bt["m_PreloadTable"])
                bt["m_PreloadTable"].append({"m_FileID": 0, "m_PathID": new.path_id})
                bt["m_Container"].append((
                    "assets/editor/localization/pt_br.txt",
                    {"preloadIndex": size, "preloadSize": 1, "asset": {"m_FileID": 0, "m_PathID": new.path_id}},
                ))
                o.save_typetree(bt)
    write_atomic(cache, save_like_original(env, backup_path))
    print("Texto pt_BR adicionado ao pacote de idiomas (os outros idiomas ficam intactos).")


def patch_locale(slot_code):
    path = locales_bundle()
    if not path:
        sys.exit(
            "Não encontrei a pasta do jogo na Steam.\n"
            "Use --substituir-ingles, que não precisa dela, ou informe --game-dir."
        )
    backup_path = backup(path)
    env = UnityPy.load(backup_path)
    found = False
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        tt = o.read_typetree()
        if tt.get("m_Identifier", {}).get("m_Code") == slot_code:
            tt["m_LocaleName"] = NEW_NAME
            tt["m_Name"] = NEW_NAME
            tt["m_CustomFormatCultureCode"] = CRC_MARKER.decode("ascii")  # campo sem efeito (usado no ajuste de CRC)
            o.save_typetree(tt)
            found = True
    if not found:
        sys.exit(f"Idioma {slot_code} não encontrado no pacote de idiomas do jogo.")
    # O catálogo do Addressables guarda o CRC32 do bundle original e o jogo recusa
    # qualquer arquivo diferente (loop de erro). Ajustamos 4 bytes inertes para
    # que o CRC do bundle alterado seja idêntico ao do original.
    with open(backup_path, "rb") as f:
        target = crcfix.crc_of_bundle(f.read())
    data = crcfix.fix_crc(save_like_original(env, backup_path), target, CRC_MARKER)
    write_atomic(path, data)
    print(f"Menu de idiomas: {slot_code} agora aparece como \"{NEW_NAME}\".")


def apply(args):
    cache = find_cache()
    if args.usar_vaga:
        # Experimental: usa a vaga de outro idioma (o rótulo no menu NÃO muda; veja o README).
        patch_texts(cache, args.slot, replace_english=False)
        patch_locale(args.slot)
        print(f"Pronto! Escolha o idioma da vaga {args.slot} em Configurações > Idiomas.")
    elif args.substituir_ingles:
        # Modo simples, sem mod loader: o idioma "English" passa a ser português.
        restore_locale()
        restore_loader()
        patch_texts(cache, args.slot, replace_english=True)
        print("Pronto! No jogo, o idioma 'English' agora é português (o rótulo no menu continua 'English').")
    else:
        # Padrão: mod loader + novo idioma "Português (Brasil)" na lista.
        restore_locale()
        patch_texts_add_pt(cache)
        install_loader()
        game = find_game_dir()
        with open(os.path.join(game, "dune_loader.ini"), "w") as f:
            f.write("hook=1" + chr(10))
        print("Pronto! Abra o jogo: 'Português (Brasil)' aparece em Configurações > Idiomas (logo após English).")


def restore_locale():
    path = locales_bundle()
    if path and os.path.exists(path + ".original"):
        shutil.copy2(path + ".original", path)
        return True
    return False


# ------------------------------------------------------------------ mod loader
def steam_api_paths():
    d = find_game_dir()
    if not d:
        return None, None
    base = os.path.join(d, "DuneImperium_Data", "Plugins", "x86_64")
    # A original fica na raiz do jogo: o Windows resolve os forwarders do proxy
    # procurando na pasta do executável (e não na pasta da DLL que repassa).
    return os.path.join(base, "steam_api64.dll"), os.path.join(d, "steam_api64_real.dll")


def is_proxy(path):
    with open(path, "rb") as f:
        return b"steam_api64_real." in f.read()


def install_loader():
    """Instala o proxy da steam_api64.dll (veja loader/make_proxy.py)."""
    sys.path.insert(0, os.path.join(HERE, "..", "loader"))
    sys.path.insert(0, os.path.join(HERE, "loader"))
    import make_proxy

    api, real = steam_api_paths()
    if not api or not os.path.isfile(api):
        sys.exit("Não encontrei a steam_api64.dll do jogo.")
    if not is_proxy(api):
        # a original (nova ou atualizada pela Steam) vira a "real"
        os.replace(api, real)
        print("Original guardada como steam_api64_real.dll")
    elif not os.path.isfile(real):
        sys.exit("Proxy instalado, mas steam_api64_real.dll sumiu; rode 'Verificar integridade' na Steam.")
    try:
        import build_loader  # compila loader/src/loader.c (precisa do Zig)
        tmp_dll = api + ".new"
        n = build_loader.build(real, tmp_dll)
        os.replace(tmp_dll, api)
        print(f"Mod loader compilado e instalado ({n} exports repassados à steam_api64_real.dll).")
    except (ImportError, SystemExit) as e:
        print("Aviso: não foi possível compilar o loader completo; usando o proxy simples.", e)
        data, n = make_proxy.build(real)
        write_atomic(api, data)
        print(f"Proxy simples instalado ({n} exports repassados à steam_api64_real.dll).")


def restore_loader():
    api, real = steam_api_paths()
    if api and real and os.path.isfile(real):
        os.replace(real, api)
        return True
    return False


def restore(args):
    cache = find_cache()
    did = restore_loader()
    gd = find_game_dir()
    if gd:
        for fn in ("dune_loader.ini", "dune_loader.log", "dune_hook.txt", "dune_probe.txt", "dune_diag.txt"):
            fp = os.path.join(gd, fn)
            if os.path.exists(fp):
                os.remove(fp)
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
    for name in ("cs_cz", "en_us"):
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
    print("  1) Instalar (o idioma English do jogo passa a ser portugues)")
    print("  2) Restaurar o original")
    print("  3) Sair")
    print()
    return input("Escolha: ").strip()


def main():
    global OVERRIDE, GAME_DIR_OVERRIDE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--substituir-ingles", action="store_true", help="modo simples, sem mod loader: troca o texto do idioma English")
    ap.add_argument("--usar-vaga", action="store_true", help="experimental: usa a vaga de outro idioma (altera a pasta da Steam)")
    ap.add_argument("--loader", action="store_true", help="experimental: instala só o proxy da steam_api64.dll (mod loader)")
    ap.add_argument("--slot", default=DEFAULT_SLOT, help="código do idioma usado como vaga (padrão: cs-CZ)")
    ap.add_argument("--cache", help="caminho do __data (avançado/testes)")
    ap.add_argument("--game-dir", help="pasta do jogo (avançado/testes)")
    a = ap.parse_args()
    OVERRIDE, GAME_DIR_OVERRIDE = a.cache, a.game_dir

    interactive = len(sys.argv) == 1 and FROZEN
    if interactive:
        choice = menu()
        if choice == "2":
            a.restore = True
        elif choice != "1":
            return
    action = (restore if a.restore else status if a.status
              else (lambda _a: install_loader()) if a.loader else apply)
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
