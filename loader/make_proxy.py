#!/usr/bin/env python3
"""Gera um proxy da steam_api64.dll sem compilador (PE64 montado à mão).

Todos os exports da DLL original viram *forwarders* para `steam_api64_real.dll`
(a original renomeada). Apenas `SteamAPI_ISteamApps_GetAvailableGameLanguages`
tem implementação própria: devolve a lista de idiomas da Steam acrescida do
português do Brasil. É o menor "mod loader" possível para este jogo: nenhum
código do jogo é alterado, e desfazer é só restaurar a DLL original.
"""
import struct
import sys

import pefile

REAL_NAME = "steam_api64_real"
OVERRIDE = "SteamAPI_ISteamApps_GetAvailableGameLanguages"
# Idiomas que a Steam informa para o jogo + brazilian
LANGS = "english,french,italian,german,spanish,czech,japanese,polish,koreana,ukrainian,schinese,tchinese,brazilian"


def align(n, a):
    return (n + a - 1) // a * a


def build(original_path):
    pe = pefile.PE(original_path)
    names = [e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name]
    unnamed = [e for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if not e.name]
    if unnamed:
        raise SystemExit(f"{len(unnamed)} exports sem nome (por ordinal) não são suportados")
    if OVERRIDE not in names:
        raise SystemExit(f"{OVERRIDE} não existe na DLL original")
    names = sorted(set(names), key=lambda s: s.encode())
    n = len(names)

    TEXT_RVA, RDATA_RVA = 0x1000, 0x2000

    # ---- .rdata: diretório de exports + tabelas + strings
    exp_dir_size = 40
    off_funcs = exp_dir_size
    off_names = off_funcs + 4 * n
    off_ords = off_names + 4 * n
    off_strs = align(off_ords + 2 * n, 4)

    blob = bytearray()
    name_rvas, fwd_rvas = [], {}
    dll_name = b"steam_api64.dll\0"
    dll_name_off = off_strs
    blob += dll_name
    for nm in names:
        name_rvas.append(RDATA_RVA + off_strs + len(blob))
        blob += nm.encode() + b"\0"
    for nm in names:
        if nm == OVERRIDE:
            continue
        fwd_rvas[nm] = RDATA_RVA + off_strs + len(blob)
        blob += f"{REAL_NAME}.{nm}".encode() + b"\0"
    export_size = off_strs + len(blob)  # os forwarders precisam estar dentro deste intervalo
    lang_off = align(export_size, 4)
    blob += b"\0" * (lang_off - export_size)
    lang_rva = RDATA_RVA + lang_off
    blob += LANGS.encode() + b"\0"

    # ---- .text: lea rax,[rip+disp]; ret
    disp = lang_rva - (TEXT_RVA + 7)
    text = b"\x48\x8d\x05" + struct.pack("<i", disp) + b"\xc3"

    funcs = b"".join(
        struct.pack("<I", TEXT_RVA if nm == OVERRIDE else fwd_rvas[nm]) for nm in names
    )
    nms = b"".join(struct.pack("<I", r) for r in name_rvas)
    ords = b"".join(struct.pack("<H", i) for i in range(n))
    exp_dir = struct.pack(
        "<IIHHIIIIIII",
        0, 0, 0, 0,
        RDATA_RVA + dll_name_off,
        1, n, n,
        RDATA_RVA + off_funcs, RDATA_RVA + off_names, RDATA_RVA + off_ords,
    )
    rdata = bytearray(exp_dir + funcs + nms + ords)
    rdata += b"\0" * (off_strs - len(rdata))
    rdata += blob

    rdata_raw = align(len(rdata), 0x200)
    reloc_rva = RDATA_RVA + align(len(rdata), 0x1000)
    reloc = struct.pack("<IIHH", TEXT_RVA, 12, 0, 0)  # bloco vazio (só padding)
    size_of_image = reloc_rva + 0x1000

    # ---- cabeçalhos
    e_lfanew = 0x40
    dos = bytearray(0x40)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, e_lfanew)

    file_hdr = struct.pack("<HHIIIHH", 0x8664, 3, 0, 0, 0, 0xF0, 0x2022)
    opt = struct.pack(
        "<HBBIIIIIQIIHHHHHHIIIIHHQQQQII",
        0x20B, 14, 0,
        0x200,                      # SizeOfCode
        rdata_raw + 0x200,          # SizeOfInitializedData
        0,                          # SizeOfUninitializedData
        0,                          # AddressOfEntryPoint (sem DllMain)
        TEXT_RVA,                   # BaseOfCode
        0x180000000,                # ImageBase
        0x1000, 0x200,              # SectionAlignment, FileAlignment
        6, 0, 0, 0, 6, 0,           # versões
        0,                          # Win32VersionValue
        size_of_image,
        0x200,                      # SizeOfHeaders
        0,                          # CheckSum
        2,                          # Subsystem GUI
        0x0140,                     # DYNAMIC_BASE | NX_COMPAT
        0x100000, 0x1000, 0x100000, 0x1000,
        0,                          # LoaderFlags
        16,                         # NumberOfRvaAndSizes
    )
    dirs = [(0, 0)] * 16
    dirs[0] = (RDATA_RVA, export_size)
    dirs[5] = (reloc_rva, 12)
    opt += b"".join(struct.pack("<II", a, b) for a, b in dirs)

    def sect(name, vsize, rva, rawsize, rawptr, chars):
        return struct.pack("<8sIIIIIIHHI", name, vsize, rva, rawsize, rawptr, 0, 0, 0, 0, chars)

    sects = (
        sect(b".text", len(text), TEXT_RVA, 0x200, 0x200, 0x60000020)
        + sect(b".rdata", len(rdata), RDATA_RVA, rdata_raw, 0x400, 0x40000040)
        + sect(b".reloc", len(reloc), reloc_rva, 0x200, 0x400 + rdata_raw, 0x42000040)
    )
    headers = bytes(dos) + b"PE\0\0" + file_hdr + opt + sects
    out = bytearray(headers + b"\0" * (0x200 - len(headers)))
    out += text + b"\0" * (0x200 - len(text))
    out += rdata + b"\0" * (rdata_raw - len(rdata))
    out += reloc + b"\0" * (0x200 - len(reloc))
    return bytes(out), n


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data, n = build(src)
    open(dst, "wb").write(data)
    print(f"proxy gerado: {dst} ({len(data)} bytes, {n} exports)")
