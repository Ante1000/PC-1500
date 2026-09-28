"""Assemble serin_v52.asm, write serin_v52.lst and refresh the SERIN POKE
lines (280..355) in the BASIC installer.

    python3 tools/build_serin.py [installer.txt]

The helpers are also used by tools/build_9600.py.
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


def poke_lines(src=SRC, var="SI", first=FIRST, step=STEP, last=LAST):
    code, labels, listing = assemble(open(src, encoding="utf-8").read())
    lines, n = [], first
    for i in range(0, len(code), 10):
        chunk = code[i:i + 10]
        lines.append("%d POKE %s+%d, %s" % (n, var, i, ", ".join(b2s(b) for b in chunk)))
        n += step
    assert n - step <= last, "%s too long for lines %d..%d" % (src, first, last)
    return code, labels, listing, lines


def write_listing(code, labels, listing, lst=LST, title="SERIN v52", base="SI = RAM+&22A"):
    out = ["; %s - listing (adresy wzgledem %s), %d bajtow" % (title, base, len(code)), ";"]
    for addr, b, raw in listing:
        hexes = " ".join(x if isinstance(x, str) else "%02X" % x for x in b)
        if b:
            out.append("%02X  %-12s %s" % (addr, hexes, raw.rstrip()))
        else:
            out.append("%-16s %s" % ("", raw.rstrip()))
    open(lst, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


def update_installer(path, lines, first=FIRST, last=LAST):
    old = [l.rstrip("\n") for l in open(path, encoding="ascii") if l.strip()]
    keep = [l for l in old if not (first <= int(l.split(" ", 1)[0]) <= last)]
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
