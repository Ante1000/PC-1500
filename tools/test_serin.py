"""Test SERIN/SEROUT from a BASIC installer on the LH5801 simulator.

    python3 tools/test_serin.py [installer.txt] [baud] [rx_bit] [invert]
    (default: pc1500_uart_installer-v6.1.txt, 4800, RX on PB0; see
     tools/test_v60.py and tools/test_v61.py)

v6.0/v6.1 ask for the speed, the RX port (and v6.1 the polarity) at INPUT
prompts: the answers (B = 1/2/4/9, P = rx_bit, I = invert) are derived from
[baud], [rx_bit] and [invert]. With invert = 1 the simulated pins carry the
inverted line (mark = low) and PC7 is read back inverted.

The installer's POKE lines are evaluated (A0=&4000). SERIN is CALLed with a
simulated 8N1 signal on PB<rx_bit> (the other port B pins read 1, so reading
the wrong bit fails every test); SEROUT's PC7 output is decoded by a model of
an ideal PC UART receiver. Every scenario runs with two cycle tables (MAME
core and the LH5801 manual, where shifts do not change the Z flag).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lh5801sim import CPU, Line, load_basic  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "pc1500_uart_installer-v6.1.txt")
BAUD = float(sys.argv[2]) if len(sys.argv) > 2 else 4800.0
RXBIT = int(sys.argv[3]) if len(sys.argv) > 3 else 0   # port B bit of the RX input
INV = int(sys.argv[4]) if len(sys.argv) > 4 else 0     # 1: inverted line polarity (v6.1)
INPUTS = {"B": {1200: 1, 2400: 2, 4800: 4, 9600: 9}.get(int(BAUD)), "P": RXBIT, "I": INV}
STACK = (0x784E, 0x784F)            # return address pushed by the test harness
fails = 0


def check(name, cond, info=""):
    global fails
    fails += not cond
    print(("  OK   " if cond else "  FAIL ") + name + ("   " + info if info else ""))


def rnd(n, seed):
    random.seed(seed)
    return bytes(random.randrange(256) for _ in range(n))


def machine(line, timing, ro=3):
    cpu = CPU(line, timing=timing, read_offset=ro, rx_bit=RXBIT, rx_invert=INV)
    for a in range(0x10000):
        cpu.m[a] = (a * 7 + 3) & 0xFF                  # random-ish RAM
    env = load_basic(BAS, cpu, stop_line=360, inputs=INPUTS)
    return cpu, env


# v55 layout: page-aligned 255-byte buffers, 1-byte RX length at RC = RX-1;
# older layout: length byte at RX+0, data RX+1..RX+127, TX 128 bytes.
BIG = "RC" in machine(Line(), "mame")[1]
RXCAP = 255 if BIG else 127
NEW_SEROUT = BAUD == 9600 or BIG  # v53+ SEROUT: N=0 -> 1, raises PC7 itself
TXCAP = 255 if BIG else (128 if NEW_SEROUT else 127)


# ----------------------------------------------------------------- SERIN
def rx(data=b"", t0=0.01, baud=None, gap=0.0, var=None, timing="mame",
       ro=3, line=None, stop_bits=1.0):
    if line is None:
        line = Line()
        if data:
            line.uart(data, t0, baud=baud or BAUD, gap=gap, stop_bits=stop_bits)
    cpu, env = machine(line, timing, ro)
    RX = env["RX"]
    before = bytes(cpu.m)
    c, x = cpu.call(env["SI"], xval=var, max_seconds=40)
    if BIG:
        RC = env["RC"]
        n, data = cpu.m[RC], RX
        allowed = lambda a: RX <= a < RX + RXCAP or a == RC
    else:
        n, data = cpu.m[RX], RX + 1
        allowed = lambda a: RX <= a < RX + 128
    bad = [a for a in range(0x10000) if cpu.m[a] != before[a]
           and not allowed(a) and a not in STACK]
    assert not bad, "memory outside RX written: %s" % [hex(a) for a in bad[:8]]
    assert n <= RXCAP
    assert cpu.ddb == 0xFF ^ 1 << RXBIT, "DDB=%02X: only PB%d may become an input" % (
        cpu.ddb, RXBIT)
    return dict(n=n, got=bytes(cpu.m[data:data + n]), c=c, x=x, t=cpu.now())


def serin_suite(timing):
    print("== SERIN @ %d bps, cycle table: %s" % (BAUD, timing))
    bad = [b for b in range(256) if rx(bytes([b]), timing=timing)["got"] != bytes([b])]
    check("all 256 byte values", not bad, str(bad[:8]))
    r = rx(b"A", timing=timing)
    check("CALL SI, 1 char: length=1, exit ~0.5 s after it",
          r["n"] == 1 and r["c"] == 1 and r["x"] == 1 and 0.45 < r["t"] < 0.6, "t=%.3f s" % r["t"])
    r = rx(b"HELLO WORLD\r\n", timing=timing)
    check("string sent back-to-back", r["got"] == b"HELLO WORLD\r\n", repr(r["got"]))
    d = rnd(RXCAP, 1)
    check("%d random bytes back-to-back" % RXCAP, rx(d, timing=timing)["got"] == d)
    d = rnd(RXCAP + 73, 2)
    r = rx(d, timing=timing)
    tcap = 0.01 + RXCAP * 10 / BAUD
    check("%d bytes -> first %d, exit right after the last one" % (len(d), RXCAP),
          r["got"] == d[:RXCAP] and r["t"] < tcap + 0.005 and r["x"] == RXCAP, "t=%.3f s" % r["t"])
    r = rx(b"HELLO", var=3, timing=timing)
    check("CALL SI,M (M=3): 'HEL', immediate exit, M:=3",
          r["got"] == b"HEL" and r["x"] == 3 and r["c"] == 1 and r["t"] < 0.01 + 35 / BAUD,
          "t=%.4f s" % r["t"])
    r = rx(b"HI", var=5, timing=timing)
    check("CALL SI,M (M=5), 2 sent: 2 chars, M:=2", r["got"] == b"HI" and r["x"] == 2)
    r = rx(b"XYZ", var=1, timing=timing)
    check("CALL SI,M (M=1)", r["got"] == b"X" and r["x"] == 1)
    if BIG:
        for m, want in ((128, 128), (254, 254), (255, 255), (0, 255), (256, 255), (300, 255),
                        (0xFFFF, 255)):
            r = rx(rnd(300, m), var=m, timing=timing)
            check("CALL SI,M (M=%d) -> %d chars, M:=%d" % (m, want, want),
                  r["n"] == want and r["x"] == want and r["got"] == rnd(300, m)[:want])
    else:
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
    ln = Line(idle=0); ln.add(1.0, 1); ln.uart(b"OK", 1.5, baud=BAUD)
    check("line 0 at start, then idle, then data", rx(line=ln, timing=timing)["got"] == b"OK")
    ln = Line(); ln.add(0.2, 0); ln.add(0.2 + 20e-6, 1); ln.uart(b"Q", 0.3, baud=BAUD)
    check("20 us glitch ignored", rx(line=ln, timing=timing)["got"] == b"Q")
    for pct in (-2.0, -1.0, 1.0, 2.0):
        d = rnd(100, int(pct * 10) + 50)
        check("100 bytes, sender %+.0f%% (%d bps)" % (pct, BAUD * (1 + pct / 100)),
              rx(d, baud=BAUD * (1 + pct / 100), timing=timing)["got"] == d)
    random.seed(7)
    ok = 0
    for _ in range(40):
        d = bytes(random.randrange(256) for _ in range(random.randrange(1, 30)))
        r = rx(d, gap=random.choice([0, 0, 1e-4, 1e-3, 0.05, 0.3]), timing=timing,
               stop_bits=random.choice([1.0, 1.5, 2.0]), ro=random.choice([1, 3, 6]),
               t0=random.uniform(0.001, 2))
        ok += r["got"] == d
    check("40 random packets (gaps, 1-2 stop bits)", ok == 40, "%d/40" % ok)
    lo = hi = 0
    for p in range(0, 100, 5):
        if rx(rnd(60, p), baud=BAUD * (1 - p / 1000), timing=timing)["got"] != rnd(60, p):
            break
        lo = p
    for p in range(0, 100, 5):
        if rx(rnd(60, p), baud=BAUD * (1 + p / 1000), timing=timing)["got"] != rnd(60, p):
            break
        hi = p
    print("  info: sender speed tolerance -%.1f%% .. +%.1f%%" % (lo / 10, hi / 10))


# ---------------------------------------------------------------- SEROUT
def tx(data, var=None, timing="mame"):
    """CALL SO[,var] with data in the TX buffer; returns (C, X, transitions)."""
    cpu, env = machine(Line(), timing)
    # new SEROUT must put PC7 to mark itself: start from space (low, or high if inverted)
    cpu.pc_port = (0x7F | INV << 7) if NEW_SEROUT else 0xFF
    TX = env["TX"]
    cpu.m[TX:TX + len(data)] = data
    before = bytes(cpu.m)
    c, x = cpu.call(env["SO"], xval=var, max_seconds=5)
    bad = [a for a in range(0x10000) if cpu.m[a] != before[a] and a not in STACK
           and not (env["SO"] + 99 <= a <= env["SO"] + 100 and not NEW_SEROUT)]
    assert not bad, "SEROUT wrote memory: %s" % [hex(a) for a in bad[:8]]
    tr = []
    lvl = 0 if NEW_SEROUT else 1
    for t, v in cpu.tx_log:
        v ^= INV                                     # PC7 pin -> logical level
        if v != lvl:
            tr.append((t, v)); lvl = v
    return c, x, tr, cpu.now()


def level_at(tr, t, init):
    v = init
    for tt, vv in tr:
        if tt > t:
            break
        v = vv
    return v


def decode(tr, f=1.0, init=1):
    """Ideal receiver: falling edge -> sample in the middle of each bit."""
    T = 1 / (BAUD * f)
    out, t = [], None
    starts = [tt for tt, v in tr if v == 0]
    if not starts:
        return b"", False
    t = starts[0]
    frame_ok = True
    while True:
        out.append(sum(level_at(tr, t + (1.5 + k) * T, init) << k for k in range(8)))
        frame_ok &= level_at(tr, t + 9.5 * T, init) == 1
        nxt = [s for s in starts if s > t + 9.5 * T]
        if not nxt:
            break
        t = nxt[0]
    return bytes(out), frame_ok


def edge_stats(tr):
    """Max deviation of data edges from the ideal bit grid and min stop length."""
    T = 1 / BAUD
    starts = []
    for t, v in tr:
        if v == 0 and (not starts or t > starts[-1] + 9.5 * T):
            starts.append(t)
    err = 0.0
    for s in starts:
        for t, v in tr:
            if s < t < s + 9.5 * T:
                err = max(err, abs((t - s) / T - round((t - s) / T)))
    stop = min([(b - a) / T - 9 for a, b in zip(starts, starts[1:])] or [9])
    return err, stop


def serout_suite(timing):
    print("== SEROUT @ %d bps, cycle table: %s" % (BAUD, timing))
    init = 0 if NEW_SEROUT else 1
    c, x, tr, t = tx(b"HELLO", var=5, timing=timing)
    got, fr = decode(tr, init=init)
    check("CALL SO,N (N=5) sends 'HELLO', N unchanged (C=0)", got == b"HELLO" and fr and c == 0, repr(got))
    c, x, tr, t = tx(b"HELLO", timing=timing)
    check("CALL SO sends 1 char", decode(tr, init=init)[0] == b"H")
    for seed in (1, 2):
        d = rnd(TXCAP, seed)
        c, x, tr, t = tx(d, var=len(d), timing=timing)
        got, fr = decode(tr, init=init)
        check("%d random bytes" % len(d), got == d and fr)
    d = bytes(range(256))
    good = decode(tx(d[:128], var=128, timing=timing)[2], init=init)[0] == d[:128] and \
        decode(tx(d[128:], var=128, timing=timing)[2], init=init)[0] == d[128:]
    check("all 256 byte values", good)
    if BIG:
        c, x, tr, t = tx(b"AB", var=0, timing=timing)
        check("CALL SO,N (N=0) -> 1 char", decode(tr, init=init)[0] == b"A")
        c, x, tr, t = tx(rnd(255, 9), var=200, timing=timing)
        check("CALL SO,N (N=200) -> 200 chars", decode(tr, init=init)[0] == rnd(255, 9)[:200])
        for n in (256, 300):
            c, x, tr, t = tx(rnd(255, n), var=n, timing=timing)
            check("CALL SO,N (N=%d) -> 255 chars" % n, decode(tr, init=init)[0] == rnd(255, n))
        c, x, tr, t = tx(b"XY", var=0xFFFF, timing=timing)
        check("CALL SO,N (N=65535, XH>=&80 = like no variable) -> 1 char",
              decode(tr, init=init)[0] == b"X")
        first = tr[0]
        check("PC7 raised to idle >= 1 bit before the first start bit",
              first[1] == 1 and tr[1][1] == 0 and (tr[1][0] - first[0]) * BAUD >= 1.0,
              "%.2f bit" % ((tr[1][0] - first[0]) * BAUD))
    elif NEW_SEROUT:
        c, x, tr, t = tx(b"AB", var=0, timing=timing)
        check("CALL SO,N (N=0) -> 1 char", decode(tr, init=init)[0] == b"A")
        c, x, tr, t = tx(rnd(128, 9), var=200, timing=timing)
        check("CALL SO,N (N=200) -> 128 chars", decode(tr, init=init)[0] == rnd(128, 9))
        c, x, tr, t = tx(b"XY", var=300, timing=timing)
        check("CALL SO,N (N>255, XH<>0 = like no variable) -> 1 char",
              decode(tr, init=init)[0] == b"X")
        first = tr[0]
        check("PC7 raised to idle >= 1 bit before the first start bit",
              first[1] == 1 and tr[1][1] == 0 and (tr[1][0] - first[0]) * BAUD >= 1.0,
              "%.2f bit" % ((tr[1][0] - first[0]) * BAUD))
    c, x, tr, t = tx(rnd(100, 5), var=100, timing=timing)
    err, stop = edge_stats(tr)
    check("edges within 0.25 bit of ideal grid, stop bit >= 1 bit", err < 0.25 and stop >= 1.0,
          "max edge error %.3f bit, min stop %.2f bit" % (err, stop))
    lo = hi = 0
    for p in range(0, 100, 5):
        if decode(tr, 1 - p / 1000, init) != (rnd(100, 5), True):
            break
        lo = p
    for p in range(0, 100, 5):
        if decode(tr, 1 + p / 1000, init) != (rnd(100, 5), True):
            break
        hi = p
    check("PC receiver may be off by +-2%", lo >= 20 and hi >= 20,
          "tolerance -%.1f%% .. +%.1f%%" % (lo / 10, hi / 10))


if __name__ == "__main__":
    print("installer: %s, %d bps, RX on PB%d%s" % (os.path.basename(BAS), BAUD, RXBIT,
                                                  ", inverted" if INV else ""))
    for tb in ("mame", "guide"):
        serout_suite(tb)
    for tb in ("mame", "guide"):
        serin_suite(tb)
    print("FAILURES: %d" % fails)
    sys.exit(1 if fails else 0)
