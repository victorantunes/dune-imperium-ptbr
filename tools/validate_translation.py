#!/usr/bin/env python3
"""Valida translation/pt_BR.txt contra o inglês original do jogo.

Confere que cada chave existe no jogo e que as tags/marcadores (<b>, <sprite ...>,
[name], {0} ...) são idênticos ao original. Use antes de abrir um Pull Request.

Uso:  python tools/validate_translation.py
"""
import glob
import os
import re
import sys

import UnityPy

CACHE = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "AppData", "LocalLow", "Unity", "Dire Wolf Digital_Dune_ Imperium",
    "localization", "*", "__data",
)
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = re.compile(r"<[^>]+>|\{[^}]*\}|\[[^\]]*\]")


def load_kv(text):
    out = {}
    for ln in text.split("\n"):
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1)
            out[k] = v
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    found = glob.glob(CACHE)
    if not found:
        sys.exit("Cache do jogo não encontrado. Abra o jogo uma vez com internet.")
    data = max(found, key=os.path.getmtime)
    source = data + ".original" if os.path.exists(data + ".original") else data
    english = None
    for obj in UnityPy.load(source).objects:
        if obj.type.name == "TextAsset":
            d = obj.read()
            if d.m_Name.lower() == "en_us":
                s = d.m_Script
                english = load_kv(s if isinstance(s, str) else bytes(s).decode("utf-8"))
    with open(os.path.join(HERE, "..", "translation", "pt_BR.txt"), encoding="utf-8") as f:
        pt = load_kv(f.read())
    bad = [k for k in pt if k not in english or sorted(TOKEN.findall(english[k])) != sorted(TOKEN.findall(pt[k]))]
    print(f"{len(pt)} chaves traduzidas, {len(bad)} com problema.")
    for k in bad[:50]:
        print(" -", k, "(chave inexistente)" if k not in english else "(tags diferentes do original)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
