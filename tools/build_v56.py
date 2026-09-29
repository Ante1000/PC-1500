"""Build v56 (9600 bps, 255-byte buffers, RX on PB0 or PB1): assemble
serout_v55.asm (unchanged) and the SERIN source of each variant, write the
.lst listings and refresh the POKE lines (SEROUT: 170..265, SERIN: 280..355)
in the installers:

  RX on PB0 (pin 9):  serin_v56.asm      -> pc1500_uart_installer-v56-9600-PB0.txt
  RX on PB1 (pin 39): serin_v56_pb1.asm  -> pc1500_uart_installer-v56-9600-PB1.txt

Memory map (RAM base A0 = &4000), the same as v55:
  &40C5  SEROUT          &4130  SERIN        &41FF  RC = RX length (1 byte)
  &4200..&42FE  RX data  &4300..&43FE  TX data      BASIC from &4400

    python3 tools/build_v56.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_serin import ROOT, poke_lines, update_installer, write_listing  # noqa: E402

SEROUT = ("serout_v55", "SO", 170, 10, 265, "SEROUT v55 9600", "SO = RAM+&0C5", 0x130 - 0x0C5)
VARIANTS = [
    # installer, SERIN source, listing title, port B bit of the RX input
    ("pc1500_uart_installer-v56-9600-PB0.txt", "serin_v56", "SERIN v56 9600 PB0", 0),
    ("pc1500_uart_installer-v56-9600-PB1.txt", "serin_v56_pb1", "SERIN v56 9600 PB1", 1),
]


def build(bas, part):
    name, var, first, step, last, title, base, limit = part
    code, labels, listing, lines = poke_lines(os.path.join(ROOT, name + ".asm"), var, first, step, last)
    assert len(code) <= limit, "%s: %d bytes > %d" % (name, len(code), limit)
    write_listing(code, labels, listing, os.path.join(ROOT, name + ".lst"), title, base)
    update_installer(bas, lines, first, last)
    print("%s: %d bytes, labels: %s" % (title, len(code), ", ".join(
        "%s=+%d" % (k, v) for k, v in labels.items())))
    return code, labels


if __name__ == "__main__":
    for installer, serin, title, bit in VARIANTS:
        bas = os.path.join(ROOT, installer)
        print(installer)
        build(bas, SEROUT)
        code, labels = build(bas, (serin, "SI", 280, 5, 355, title, "SI = RAM+&130", 0x1FF - 0x130))
        assert code[labels["WH"] - 7] == 0xFF ^ 1 << bit, "ANI mask (DDB) does not match PB%d" % bit
        # the RX test checks the bit-loop constant (line 570) and the input bit mask (line 575)
        text = open(bas, encoding="ascii").read()
        m = re.search(r"PEEK \(SI \+ (\d+)\) <> 5", text)
        assert m and int(m.group(1)) == labels["BIT"] + 1, "fix the SI+n check in line 570"
        m = re.search(r"PEEK \(SI \+ (\d+)\) <> %d " % (1 << bit), text)
        assert m and int(m.group(1)) == labels["WH"] + 2 and code[int(m.group(1))] == 1 << bit, \
            "fix the SI+n check in line 575"
