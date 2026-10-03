"""Shared helpers for the build scripts (tools/build_v60.py, tools/build_v61.py):
assemble a source, turn the code into BASIC POKE lines, write the .lst listing
and replace the POKE lines in an installer.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from asm import assemble  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def b2s(b):
    if isinstance(b, str):
        return b
    return "&%02X" % b if b > 9 else str(b)


def poke_lines(src, var, first, step, last):
    code, labels, listing = assemble(open(src, encoding="utf-8").read())
    lines, n = [], first
    for i in range(0, len(code), 10):
        chunk = code[i:i + 10]
        lines.append("%d POKE %s+%d, %s" % (n, var, i, ", ".join(b2s(b) for b in chunk)))
        n += step
    assert n - step <= last, "%s too long for lines %d..%d" % (src, first, last)
    return code, labels, listing, lines


def write_listing(code, labels, listing, lst, title, base):
    out = ["; %s - listing (adresy wzgledem %s), %d bajtow" % (title, base, len(code)), ";"]
    for addr, b, raw in listing:
        hexes = " ".join(x if isinstance(x, str) else "%02X" % x for x in b)
        if b:
            out.append("%02X  %-12s %s" % (addr, hexes, raw.rstrip()))
        else:
            out.append("%-16s %s" % ("", raw.rstrip()))
    open(lst, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


def update_installer(path, lines, first, last):
    old = [l.rstrip("\n") for l in open(path, encoding="ascii") if l.strip()]
    keep = [l for l in old if not (first <= int(l.split(" ", 1)[0]) <= last)]
    new = sorted(keep + lines, key=lambda l: int(l.split(" ", 1)[0]))
    for l in new:
        assert len(l) < 80 and l.isascii(), l
    open(path, "w", encoding="ascii", newline="\n").write("\n".join(new) + "\n")

