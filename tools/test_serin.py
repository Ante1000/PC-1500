"""Test SERIN v52 from the BASIC installer on the LH5801 simulator.

    python3 tools/test_serin.py [installer.txt]

The installer's POKE lines are evaluated (A0=&4000), SERIN is CALLed with a
simulated 4800 bps 8N1 signal on PB2, and RX / the CALL variable are checked.
Every scenario is run with two cycle tables (MAME core and LH5801 manual).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lh5801sim import CPU, Line, load_basic  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "pc1500_uart_installer-v52.txt")
STACK = (0x784E, 0x784F)            # return address pushed by the test harness
fails = 0


def rx(data=b"", t0=0.01, baud=4800.0, gap=0.0, var=None, timing="mame",
       ro=3, line=None, stop_bits=1.0):
    if line is None:
        line = Line()
        if data:
            line.uart(data, t0, baud=baud, gap=gap, stop_bits=stop_bits)
    cpu = CPU(line, timing=timing, read_offset=ro)
    for a in range(0x10000):
        cpu.m[a] = (a * 7 + 3) & 0xFF                  # random-ish RAM
    env = load_basic(BAS, cpu, stop_line=360)
    RX = env["RX"]
    before = bytes(cpu.m)
    c, x = cpu.call(env["SI"], xval=var, max_seconds=40)
    n = cpu.m[RX]
    bad = [a for a in range(0x10000) if cpu.m[a] != before[a]
           and not RX <= a < RX + 128 and a not in STACK]
    assert not bad, "memory outside RX written: %s" % [hex(a) for a in bad[:8]]
    assert n <= 127
    return dict(n=n, got=bytes(cpu.m[RX + 1:RX + 1 + n]), c=c, x=x, t=cpu.now())


def check(name, cond, info=""):
    global fails
    fails += not cond
    print(("  OK   " if cond else "  FAIL ") + name + ("   " + info if info else ""))


def rnd(n, seed):
    random.seed(seed)
    return bytes(random.randrange(256) for _ in range(n))


def suite(timing):
    print("== cycle table: %s" % timing)
    bad = [b for b in range(256) if rx(bytes([b]), timing=timing)["got"] != bytes([b])]
    check("all 256 byte values", not bad, str(bad[:8]))
    r = rx(b"A", timing=timing)
    check("CALL SI, 1 char: RX(0)=1, exit ~0.5 s after it",
          r["n"] == 1 and r["c"] == 1 and r["x"] == 1 and 0.45 < r["t"] < 0.6, "t=%.3f s" % r["t"])
    r = rx(b"HELLO WORLD\r\n", timing=timing)
    check("string sent back-to-back", r["got"] == b"HELLO WORLD\r\n", repr(r["got"]))
    d = rnd(127, 1)
    check("127 random bytes back-to-back", rx(d, timing=timing)["got"] == d)
    d = rnd(200, 2)
    r = rx(d, timing=timing)
    t127 = 0.01 + 127 * 10 / 4800
    check("200 bytes -> first 127, exit right after the 127th",
          r["got"] == d[:127] and r["t"] < t127 + 0.005, "t=%.3f s" % r["t"])
    r = rx(b"HELLO", var=3, timing=timing)
    check("CALL SI,M (M=3): 'HEL', immediate exit, M:=3",
          r["got"] == b"HEL" and r["x"] == 3 and r["c"] == 1 and r["t"] < 0.02, "t=%.4f s" % r["t"])
    r = rx(b"HI", var=5, timing=timing)
    check("CALL SI,M (M=5), 2 sent: 2 chars, M:=2", r["got"] == b"HI" and r["x"] == 2)
    r = rx(b"XYZ", var=1, timing=timing)
    check("CALL SI,M (M=1)", r["got"] == b"X" and r["x"] == 1)
    for m in (0, 127, 128, 255, 300, 0xFFFF):
        check("CALL SI,M (M=%d) -> max 127" % m, rx(rnd(180, m), var=m, timing=timing)["n"] == 127)
    r = rx(b"", timing=timing)
    check("no data: 0 chars after ~30 s, M:=0", r["n"] == 0 and r["x"] == 0 and 28 < r["t"] < 32,
          "t=%.2f s" % r["t"])
    check("first char at 29 s -> received", rx(b"K", t0=29.0, timing=timing)["got"] == b"K")
    check("first char at 31 s -> timeout", rx(b"K", t0=31.0, timing=timing)["n"] == 0)
    check("gaps of 400 ms -> 3 chars", rx(b"ABC", gap=0.4, timing=timing)["got"] == b"ABC")
    check("gaps of 600 ms -> 1 char", rx(b"ABC", gap=0.6, timing=timing)["got"] == b"A")
    r = rx(line=Line(idle=0), timing=timing)
    check("line stuck at 0 -> 0 chars after ~30 s", r["n"] == 0 and 28 < r["t"] < 32)
    ln = Line(idle=0); ln.add(1.0, 1); ln.uart(b"OK", 1.5)
    check("line 0 at start, then idle, then data", rx(line=ln, timing=timing)["got"] == b"OK")
    ln = Line(); ln.add(0.2, 0); ln.add(0.2 + 20e-6, 1); ln.uart(b"Q", 0.3)
    check("20 us glitch ignored", rx(line=ln, timing=timing)["got"] == b"Q")
    for pct in (-2.0, -1.0, 1.0, 2.0):
        d = rnd(100, int(pct * 10) + 50)
        check("100 bytes, sender %+.0f%% (%d bps)" % (pct, 4800 * (1 + pct / 100)),
              rx(d, baud=4800 * (1 + pct / 100), timing=timing)["got"] == d)
    random.seed(7)
    ok = 0
    for _ in range(40):
        d = bytes(random.randrange(256) for _ in range(random.randrange(1, 30)))
        r = rx(d, gap=random.choice([0, 0, 1e-4, 1e-3, 0.05, 0.3]), timing=timing,
               stop_bits=random.choice([1.0, 1.5, 2.0]), ro=random.choice([1, 3, 6]),
               t0=random.uniform(0.001, 2))
        ok += r["got"] == d
    check("40 random packets (gaps, 1-2 stop bits)", ok == 40, "%d/40" % ok)
    # informational: sender speed range that still works (same as SERIN v47)
    lo = hi = 0
    for p in range(0, 100, 5):
        if rx(rnd(60, p), baud=4800 * (1 - p / 1000), timing=timing)["got"] != rnd(60, p):
            break
        lo = p
    for p in range(0, 100, 5):
        if rx(rnd(60, p), baud=4800 * (1 + p / 1000), timing=timing)["got"] != rnd(60, p):
            break
        hi = p
    print("  info: sender speed tolerance -%.1f%% .. +%.1f%%" % (lo / 10, hi / 10))


def serout_check():
    cpu = CPU(Line())
    env = load_basic(BAS, cpu, stop_line=270)
    cpu.m[env["TX"]:env["TX"] + 5] = b"HELLO"
    cpu.call(env["SO"], xval=5, max_seconds=5)
    ev, bit = cpu.tx_log, 1 / 4800

    def lv(t):
        v = 1
        for tt, vv in ev:
            if tt > t:
                break
            v = vv
        return v
    out, t = [], ev[0][0]
    while True:
        out.append(sum(lv(t + (1.5 + k) * bit) << k for k in range(8)))
        nxt = [tt for (tt, v) in ev if v == 0 and tt > t + 9.5 * bit and lv(tt - 1e-9) == 1]
        if not nxt:
            break
        t = nxt[0]
    check("SEROUT (unchanged) sends 'HELLO' on PC7", bytes(out) == b"HELLO", repr(bytes(out)))


serout_check()
for tb in ("mame", "guide"):
    suite(tb)
print("FAILURES: %d" % fails)
sys.exit(1 if fails else 0)
