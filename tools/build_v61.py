"""Build v6.1 (1200/2400/4800/9600 bps, RX on PB0 or PB2, normal or inverted
line polarity, 255-byte buffers): assemble serout_v61.asm and serin_v61.asm,
write their .lst listings and refresh the POKE lines in
pc1500_uart_installer-v6.1.txt (SEROUT: 170..265, SERIN: 280..355).

The installer's INPUT questions set BASIC variables that the POKE lines carry:
  speed     SEROUT KI, KS, KB, KT      SERIN KH, KB
  RX port   SERIN  DB (DDB mask), BM (port B bit mask)
  polarity  SEROUT OM/VM (write mark), OS/VS (write space) to PC7
            SERIN  FM, FS, RM (branch opcodes: forward if mark / space, back if mark)

Memory map (RAM base A0 = &4000), the same as v6.0:
  &40C5  SEROUT          &4130  SERIN        &41FF  RC = RX length (1 byte)
  &4200..&42FE  RX data  &4300..&43FE  TX data      BASIC from &4400

    python3 tools/build_v61.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_common import ROOT, poke_lines, update_installer, write_listing  # noqa: E402

BAS = os.path.join(ROOT, "pc1500_uart_installer-v6.1.txt")
PARTS = [
    # source, variable, first, step, last, title, base, load offset, free bytes
    ("serout_v61", "SO", 170, 10, 265, "SEROUT v6.1", "SO = RAM+&0C5", 0x0C5, 0x130 - 0x0C5),
    ("serin_v61", "SI", 280, 5, 355, "SERIN v6.1", "SI = RAM+&130", 0x130, 0x1FF - 0x130),
]


def mark(p):
    return {p + 1: "OM", p + 2: "VM"}      # MARK #(Y) at p: FD OM VM


def space(p):
    return {p + 1: "OS", p + 2: "VS"}      # SPACE #(Y) at p: FD OS VS


# operands the installer computes (offset from SO/SI -> BASIC variable)
EXPECT = {
    "SO": lambda L: {L["IDLE"] - 1: "KI", L["SDLY"] - 1: "KS", L["DLY"] - 1: "KB", L["TDLY"] - 1: "KT",
                     **mark(L["IDLE"] - 5), **space(L["CHAR"] + 1), **space(L["OUT"] + 3),
                     **mark(L["ONE"]), **mark(L["TDLY"] - 5)},
    "SI": lambda L: {L["WH"] - 7: "DB", L["WH"] + 2: "BM", L["WL"] + 2: "BM", L["HALF"] + 4: "BM",
                     L["DLY"] + 6: "BM", L["HALF"] - 1: "KH", L["DLY"] - 1: "KB",
                     L["WH"] + 3: "FM", L["WL"] + 3: "FS", L["HALF"] + 5: "RM", L["DLY"] + 8: "FM"},
}


if __name__ == "__main__":
    text = open(BAS, encoding="ascii").read()
    for name, var, first, step, last, title, base, off, limit in PARTS:
        code, labels, listing, lines = poke_lines(os.path.join(ROOT, name + ".asm"), var, first, step, last)
        assert len(code) <= limit, "%s: %d bytes > %d" % (name, len(code), limit)
        want = EXPECT[var](labels)
        got = {i: b for i, b in enumerate(code) if isinstance(b, str) and b not in ("TP", "RP", "CP")}
        assert got == want, "%s: symbolic operands %s, expected %s" % (name, got, want)
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
            si_kb, si_bm, si_fm = labels["DLY"] - 1, labels["WH"] + 2, labels["WH"] + 3
    # the RX test identifies the installed speed, port and polarity from these bytes
    m = re.search(r"K = PEEK \(SI \+ (\d+)\) : Q = PEEK \(SI \+ (\d+)\)", text)
    assert m and (int(m.group(1)), int(m.group(2))) == (si_kb, si_bm), "fix line 562"
    m = re.search(r"IF PEEK \(SO \+ (\d+)\) <> K", text)
    assert m and int(m.group(1)) == so_kb, "fix line 576"
    m = re.search(r"IF PEEK \(SI \+ (\d+)\) = &8B THEN", text)
    assert m and int(m.group(1)) == si_fm, "fix line 579"
