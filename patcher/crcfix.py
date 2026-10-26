"""Faz um bundle UnityFS alterado manter o mesmo CRC32 do original.

O catálogo do Addressables guarda o CRC32 dos dados DESCOMPRIMIDOS de cada
bundle e o jogo recusa arquivos que não batem. Como o CRC32 é linear, dá para
reservar 4 bytes inertes e calcular os valores que fazem o CRC voltar ao alvo.
"""
import struct
import zlib

import lz4.block

_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if _c & 1 else _c >> 1
    _TABLE.append(_c)
_TOP = {t >> 24: i for i, t in enumerate(_TABLE)}


def parse_bundle(raw):
    """Lê um UnityFS (versão 8, bloco+diretório combinados). Retorna dict."""
    sig_end = raw.index(bytes([0]))
    i = sig_end + 1 + 4
    pv = raw.index(bytes([0]), i)
    uv = raw.index(bytes([0]), pv + 1)
    head = raw[:uv + 1]
    size, cs, us, flags = struct.unpack(">qIII", raw[uv + 1:uv + 21])
    pos = uv + 21
    if flags & 0x200:
        pos = (pos + 15) // 16 * 16
    if not flags & 0x40:
        raise ValueError("formato de bundle não suportado (bloco/diretório separados)")
    ct = flags & 0x3F
    comp = raw[pos:pos + cs]
    info = lz4.block.decompress(comp, uncompressed_size=us) if ct in (2, 3) else comp
    n = struct.unpack(">I", info[16:20])[0]
    blocks = [struct.unpack(">IIH", info[20 + 10 * k:30 + 10 * k]) for k in range(n)]
    rest = info[20 + 10 * n:]
    q = pos + cs
    if flags & 0x200:
        q = (q + 15) // 16 * 16
    data = b""
    for u, c, f in blocks:
        seg = raw[q:q + c]
        q += c
        data += lz4.block.decompress(seg, uncompressed_size=u) if f & 0x3F in (2, 3) else seg
    return {"head": head, "flags": flags, "hash": info[:16], "rest": rest, "blocks": blocks, "data": data}


def build_bundle(b, data):
    """Remonta o bundle com `data` (descomprimido) em um único bloco LZ4HC."""
    flags = b["flags"]
    f_block = b["blocks"][0][2]
    comp = lz4.block.compress(data, mode="high_compression", compression=12, store_size=False)
    info = b["hash"] + struct.pack(">I", 1) + struct.pack(">IIH", len(data), len(comp), f_block) + b["rest"]
    info_c = lz4.block.compress(info, mode="high_compression", compression=12, store_size=False)
    out = b"" + b["head"]
    hdr_len = len(out) + 20
    pad1 = (-hdr_len) % 16 if flags & 0x200 else 0
    body_start = hdr_len + pad1 + len(info_c)
    pad2 = (-body_start) % 16 if flags & 0x200 else 0
    total = body_start + pad2 + len(comp)
    out += struct.pack(">qIII", total, len(info_c), len(info), flags)
    out += bytes(pad1) + info_c + bytes(pad2) + comp
    return out


def forge(data, pos, target):
    """Devolve 4 bytes que, colocados em data[pos:pos+4], fazem crc32(data)==target."""
    c = 0xFFFFFFFF
    for byte in data[:pos]:
        c = _TABLE[(c ^ byte) & 0xFF] ^ (c >> 8)
    f = target ^ 0xFFFFFFFF
    for byte in reversed(data[pos + 4:]):  # desfaz o sufixo
        i = _TOP[f >> 24]
        f = (((f ^ _TABLE[i]) << 8) & 0xFFFFFFFF) | (i ^ byte)
    idx = []
    s = f
    for _ in range(4):  # desfaz os 4 bytes desconhecidos (low bytes = 0)
        i = _TOP[s >> 24]
        idx.append(i)
        s = ((s ^ _TABLE[i]) << 8) & 0xFFFFFFFF
    x = c ^ s  # os low bytes desconhecidos
    # idx está na ordem inversa (último byte primeiro)
    idx.reverse()
    out = bytearray()
    state = c
    for j in range(4):
        b = (state ^ idx[j]) & 0xFF
        out.append(b)
        state = _TABLE[(state ^ b) & 0xFF] ^ (state >> 8)
    if state != f:
        raise ValueError("falha ao calcular os bytes de ajuste do CRC")
    return bytes(out)


def crc_of_bundle(raw):
    return zlib.crc32(parse_bundle(raw)["data"]) & 0xFFFFFFFF


def fix_crc(new_raw, target_crc, marker):
    """Ajusta `new_raw` para que o CRC dos dados descomprimidos seja `target_crc`.

    `marker`: 4 bytes únicos gravados pelo patcher em um campo sem efeito.
    """
    b = parse_bundle(new_raw)
    data = b["data"]
    pos = data.find(marker)
    if pos < 0 or data.find(marker, pos + 1) >= 0:
        raise ValueError("marcador de ajuste não encontrado (ou duplicado)")
    patched = data[:pos] + forge(data, pos, target_crc) + data[pos + 4:]
    out = build_bundle(b, patched)
    if crc_of_bundle(out) != target_crc:
        raise ValueError("o CRC final não bateu com o alvo")
    return out
