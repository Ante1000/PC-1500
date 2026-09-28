"""Build v55 (9600 bps, 255-byte buffers): assemble serout_v55.asm and
serin_v55.asm, write their .lst listings and refresh the POKE lines in
pc1500_uart_installer-v55-9600.txt (SEROUT: 170..265, SERIN: 280..355).

Memory map (RAM base A0 = &4000):
  &40C5  SEROUT          &4130  SERIN        &41FF  RC = RX length (1 byte)
  &4200..&42FE  RX data  &4300..&43FE  TX data      BASIC from &4400

    python3 tools/build_v55.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_serin import ROOT, poke_lines, update_installer, write_listing  # noqa: E402

BAS = os.path.join(ROOT, "pc1500_uart_installer-v55-9600.txt")
PARTS = [
    # source, variable, first, step, last, title, base, free bytes
    ("serout_v55", "SO", 170, 10, 265, "SEROUT v55 9600", "SO = RAM+&0C5", 0x130 - 0x0C5),
    ("serin_v55", "SI", 280, 5, 355, "SERIN v55 9600", "SI = RAM+&130", 0x1FF - 0x130),
]

if __name__ == "__main__":
    for name, var, first, step, last, title, base, limit in PARTS:
        src = os.path.join(ROOT, name + ".asm")
        code, labels, listing, lines = poke_lines(src, var, first, step, last)
        assert len(code) <= limit, "%s: %d bytes > %d" % (name, len(code), limit)
        write_listing(code, labels, listing, os.path.join(ROOT, name + ".lst"), title, base)
        update_installer(BAS, lines, first, last)
        print("%s: %d bytes, labels: %s" % (title, len(code), ", ".join(
            "%s=+%d" % (k, v) for k, v in labels.items())))
        if var == "SI":   # the RX test checks the bit-loop constant at SI+BIT+1
            text = open(BAS, encoding="ascii").read()
            m = re.search(r"PEEK \(SI \+ (\d+)\) <> 5", text)
            assert m and int(m.group(1)) == labels["BIT"] + 1, "fix the SI+n check in line 570"
