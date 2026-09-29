"""Build v6.0 (1200/2400/4800/9600 bps, RX on PB0 or PB2, 255-byte buffers):
assemble serout_v60.asm and serin_v60.asm, write their .lst listings and
refresh the POKE lines in pc1500_uart_installer-v6.0.txt (SEROUT: 170..265,
SERIN: 280..355).

The speed and the RX port are chosen by the installer's INPUT questions; the
POKE lines carry them as BASIC variables:
  SEROUT  KI (idle), KS (start bit), KB (data bit), KT (stop bit)
  SERIN   DB (DDB mask), BM (port B bit mask), KH (half bit), KB (data bit)

Memory map (RAM base A0 = &4000), the same as v55:
  &40C5  SEROUT          &4130  SERIN        &41FF  RC = RX length (1 byte)
  &4200..&42FE  RX data  &4300..&43FE  TX data      BASIC from &4400

    python3 tools/build_v60.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_serin import ROOT, poke_lines, update_installer, write_listing  # noqa: E402

BAS = os.path.join(ROOT, "pc1500_uart_installer-v6.0.txt")
PARTS = [
    # source, variable, first, step, last, title, base, load offset, free bytes
    ("serout_v60", "SO", 170, 10, 265, "SEROUT v6.0", "SO = RAM+&0C5", 0x0C5, 0x130 - 0x0C5),
    ("serin_v60", "SI", 280, 5, 355, "SERIN v6.0", "SI = RAM+&130", 0x130, 0x1FF - 0x130),
]
# operands the installer computes (offset from SO/SI -> BASIC variable)
EXPECT = {
    "SO": lambda L: {L["IDLE"] - 1: "KI", L["SDLY"] - 1: "KS", L["DLY"] - 1: "KB", L["TDLY"] - 1: "KT"},
    "SI": lambda L: {L["WH"] - 7: "DB", L["WH"] + 2: "BM", L["WL"] + 2: "BM", L["HALF"] + 4: "BM",
                     L["DLY"] + 6: "BM", L["HALF"] - 1: "KH", L["DLY"] - 1: "KB"},
}


if __name__ == "__main__":
    text = open(BAS, encoding="ascii").read()
    for name, var, first, step, last, title, base, off, limit in PARTS:
        code, labels, listing, lines = poke_lines(os.path.join(ROOT, name + ".asm"), var, first, step, last)
        assert len(code) <= limit, "%s: %d bytes > %d" % (name, len(code), limit)
        want = EXPECT[var](labels)
        got = {i: b for i, b in enumerate(code) if isinstance(b, str) and b not in ("TP", "RP", "CP")}
        assert got == want, "%s: symbolic operands %s, expected %s" % (name, got, want)
        # the REM with the address range in line 80/90
        end = "&4%03X" % (off + len(code) - 1)
        assert re.search(r"REM %s \(.*\):? +&4%03X \.\. %s" % (
            "SEROUT" if var == "SO" else "SERIN", off, end), text), "fix the %s range REM (%s)" % (var, end)
        write_listing(code, labels, listing, os.path.join(ROOT, name + ".lst"), title, base)
        update_installer(BAS, lines, first, last)
        print("%s: %d bytes, labels: %s" % (title, len(code), ", ".join(
            "%s=+%d" % (k, v) for k, v in labels.items())))
        print("  set by the installer: %s" % ", ".join("%s+%d=%s" % (var, k, v) for k, v in sorted(want.items())))
        if var == "SO":
            so_kb = labels["DLY"] - 1
        else:
            si_kb, si_bm = labels["DLY"] - 1, labels["WH"] + 2
    # the RX test identifies the installed speed and port from these bytes
    m = re.search(r"K = PEEK \(SI \+ (\d+)\) : Q = PEEK \(SI \+ (\d+)\)", text)
    assert m and (int(m.group(1)), int(m.group(2))) == (si_kb, si_bm), "fix line 562"
    m = re.search(r"IF PEEK \(SO \+ (\d+)\) <> K", text)
    assert m and int(m.group(1)) == so_kb, "fix line 576"
