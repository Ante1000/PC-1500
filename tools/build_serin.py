"""Assemble serin_v52.asm, write serin_v52.lst and refresh the SERIN POKE
lines (270..355) in the BASIC installer.

    python3 tools/build_serin.py [installer.txt]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from asm import assemble  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "serin_v52.asm")
LST = os.path.join(ROOT, "serin_v52.lst")
BAS = os.path.join(ROOT, "pc1500_uart_installer-v52.txt")

FIRST, STEP, LAST = 280, 5, 355          # line numbers reserved for SERIN POKEs


def b2s(b):
    if isinstance(b, str):
        return b
    return "&%02X" % b if b > 9 else str(b)


def poke_lines():
    code, labels, listing = assemble(open(SRC, encoding="utf-8").read())
    lines, n = [], FIRST
    for i in range(0, len(code), 10):
        chunk = code[i:i + 10]
        lines.append("%d POKE SI+%d, %s" % (n, i, ", ".join(b2s(b) for b in chunk)))
        n += STEP
    assert n - STEP <= LAST, "SERIN too long for lines %d..%d" % (FIRST, LAST)
    return code, labels, listing, lines


def write_listing(code, labels, listing):
    out = ["; SERIN v52 - listing (adresy wzgledem SI = RAM+&22A), %d bajtow" % len(code), ";"]
    for addr, b, raw in listing:
        hexes = " ".join(b if isinstance(b, str) else "%02X" % b for b in b)
        if b:
            out.append("%02X  %-12s %s" % (addr, hexes, raw.rstrip()))
        else:
            out.append("%-16s %s" % ("", raw.rstrip()))
    open(LST, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


def update_installer(path, lines):
    old = [l.rstrip("\n") for l in open(path, encoding="ascii") if l.strip()]
    keep = [l for l in old if not (FIRST <= int(l.split(" ", 1)[0]) <= LAST)]
    new = sorted(keep + lines, key=lambda l: int(l.split(" ", 1)[0]))
    for l in new:
        assert len(l) < 80 and l.isascii(), l
    open(path, "w", encoding="ascii", newline="\n").write("\n".join(new) + "\n")


if __name__ == "__main__":
    code, labels, listing, lines = poke_lines()
    write_listing(code, labels, listing)
    update_installer(sys.argv[1] if len(sys.argv) > 1 else BAS, lines)
    print("SERIN: %d bytes, labels: %s" % (len(code), ", ".join(
        "%s=+%d" % (k, v) for k, v in labels.items())))
