#!/usr/bin/env python3
"""Compila o loader (loader/src/loader.c) como proxy da steam_api64.dll.

Requer o compilador Zig (pip install ziglang). Uso:
    python loader/build_loader.py <steam_api64 original> <saida.dll>
"""
import os
import subprocess
import sys
import tempfile

import pefile

OVERRIDE = {"SteamAPI_ISteamApps_GetAvailableGameLanguages"}  # implementado em loader.c
HERE = os.path.dirname(os.path.abspath(__file__))


def build(original, out_dll):
    pe = pefile.PE(original)
    names = sorted({e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name})
    lines = ["LIBRARY steam_api64", "EXPORTS"]
    lines += [f"    {n} = steam_api64_real.{n}" for n in names if n not in OVERRIDE]
    with tempfile.TemporaryDirectory() as tmp:
        deffile = os.path.join(tmp, "steam_api64.def")
        with open(deffile, "w") as f:
            f.write("\n".join(lines) + "\n")
        cmd = [
            sys.executable, "-m", "ziglang", "cc", "-target", "x86_64-windows-gnu", "-shared", "-O2",
            "-o", out_dll, os.path.join(HERE, "src", "loader.c"), deffile,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("falha ao compilar o loader:\n" + r.stderr[-2000:])
    return len(names)


if __name__ == "__main__":
    n = build(sys.argv[1], sys.argv[2])
    print(f"loader compilado: {sys.argv[2]} ({n} exports)")
