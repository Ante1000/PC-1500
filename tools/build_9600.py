"""Build the 9600 bps version: assemble serout_v53_9600.asm and
serin_v53_9600.asm, write their .lst listings and refresh the POKE lines
in pc1500_uart_installer-v53-9600.txt (SEROUT: 170..265, SERIN: 280..355).

    python3 tools/build_9600.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_serin import ROOT, poke_lines, update_installer, write_listing  # noqa: E402

BAS = os.path.join(ROOT, "pc1500_uart_installer-v53-9600.txt")
PARTS = [
    # source, variable, first, step, last, title, base
    ("serout_v53_9600", "SO", 170, 10, 265, "SEROUT v53 9600", "SO = RAM+&1C5"),
    ("serin_v53_9600", "SI", 280, 5, 355, "SERIN v53 9600", "SI = RAM+&22A"),
]
LIMIT = {"SO": 0x22A - 0x1C5, "SI": 0x2B0 - 0x22A}   # free bytes up to next block

if __name__ == "__main__":
    for name, var, first, step, last, title, base in PARTS:
        src = os.path.join(ROOT, name + ".asm")
        code, labels, listing, lines = poke_lines(src, var, first, step, last)
        assert len(code) <= LIMIT[var], "%s: %d bytes > %d" % (name, len(code), LIMIT[var])
        write_listing(code, labels, listing, os.path.join(ROOT, name + ".lst"), title, base)
        update_installer(BAS, lines, first, last)
        print("%s: %d bytes, labels: %s" % (title, len(code), ", ".join(
            "%s=+%d" % (k, v) for k, v in labels.items())))
