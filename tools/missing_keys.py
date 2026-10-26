#!/usr/bin/env python3
"""Lista os textos do jogo que ainda não estão na tradução.

Útil depois que o jogo é atualizado: compara o inglês ORIGINAL do seu cache
(o backup __data.original) com translation/pt_BR.txt e mostra as chaves novas.

Uso:  python tools/missing_keys.py
"""
import glob
import os
import sys

import UnityPy

CACHE = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "AppData", "LocalLow", "Unity", "Dire Wolf Digital_Dune_ Imperium",
    "localization", "*", "__data",
)
HERE = os.path.dirname(os.path.abspath(__file__))
TRANSLATION = os.path.join(HERE, "..", "translation", "pt_BR.txt")


def load_kv(text):
    out = {}
    for ln in text.split("\n"):
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1)
            out[k] = v
    return out


def main():
    found = glob.glob(CACHE)
    if not found:
        sys.exit("Cache do jogo não encontrado. Abra o jogo uma vez com internet.")
    data = max(found, key=os.path.getmtime)
    source = data + ".original" if os.path.exists(data + ".original") else data
    env = UnityPy.load(source)
    english = None
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            d = obj.read()
            if d.m_Name.lower() == "en_us":
                s = d.m_Script
                english = load_kv(s if isinstance(s, str) else bytes(s).decode("utf-8"))
    if english is None:
        sys.exit("en_US não encontrado no pacote.")

    with open(TRANSLATION, encoding="utf-8") as f:
        pt = load_kv(f.read())

    missing = [k for k in english if k not in pt]
    obsolete = [k for k in pt if k not in english]
    print(f"{len(english)} chaves no jogo, {len(pt)} traduzidas.")
    print(f"{len(missing)} sem tradução, {len(obsolete)} traduzidas que não existem mais.\n")
    for k in missing:
        print(f"{k}={english[k]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
