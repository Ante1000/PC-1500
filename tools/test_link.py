"""Check the framing used by pc1500_uart_link-v1.0.txt on the LH5801 simulator.

    python3 tools/test_link.py [baud ...]      (default: 1200 2400 4800 9600)

The sender puts PL = INT(baud/64) NUL bytes (about 150 ms) in front of the
text and CR LF and sends everything with one CALL SO,N. The receiver may be
busy in BASIC when the burst starts and enter CALL SI at any moment during the
NULs (even in the middle of a frame). It must still get the text intact once
the leading NULs are skipped (the BASIC program finds the first non-NUL byte
by binary search). Every case runs with both polarities and both cycle tables.

The receiver gets the link program's RX settings: first-char timeout POKE
SI+32,1 (~1.7 s). To keep the run short the inter-char timeout (SI+105) is
cut to ~33 ms here; it only decides when SERIN returns after the last byte.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lh5801sim import CPU, Line, load_basic  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INST = os.path.join(ROOT, "pc1500_uart_installer-v6.1.txt")
BAUDS = [int(b) for b in sys.argv[1:]] or [1200, 2400, 4800, 9600]
fails = 0


def check(name, cond, info=""):
    global fails
    fails += not cond
    print(("  OK   " if cond else "  FAIL ") + name + ("   " + info if info else ""))


def machine(line, baud, inv, timing):
    cpu = CPU(line, timing=timing, read_offset=3, rx_bit=0, rx_invert=inv)
    for a in range(0x10000):
        cpu.m[a] = (a * 7 + 3) & 0xFF
    inputs = {"B": {1200: 1, 2400: 2, 4800: 4, 9600: 9}[baud], "P": 0, "I": inv}
    return cpu, load_basic(INST, cpu, stop_line=360, inputs=inputs)


def send(payload, baud, inv, timing):
    """SEROUT output as logical levels (1 = mark): [(t, level), ...]."""
    cpu, env = machine(Line(), baud, inv, timing)
    cpu.pc_port = 0x7F if inv else 0xFF              # PC7 idle (mark)
    cpu.m[env["TX"]:env["TX"] + len(payload)] = payload
    cpu.call(env["SO"], xval=len(payload), max_seconds=5)
    return [(t, v ^ inv) for t, v in cpu.tx_log]


def level_at(tr, t):
    v = 1
    for tt, vv in tr:
        if tt > t:
            break
        v = vv
    return v


def shifted(tr, d):
    """The line as seen by a receiver that enters CALL SI d seconds after the sender's CALL SO."""
    ln = Line(idle=level_at(tr, d))
    for t, v in tr:
        if t > d:
            ln.add(t - d, v)
    return ln


def receive(line, baud, inv, timing):
    cpu, env = machine(line, baud, inv, timing)
    si = env["SI"]
    assert cpu.m[si + 32] == 18 and cpu.m[si + 105] == 77, "timeout operands moved"
    cpu.m[si + 32] = 1                               # as RX mode of the link program
    cpu.m[si + 105] = 5                              # faster test (see docstring)
    cpu.call(si, max_seconds=5)
    n = cpu.m[env["RC"]]
    return bytes(cpu.m[env["RX"]:env["RX"] + n])


def skip_nuls(d):
    """Same binary search as lines 530-545 of the BASIC program."""
    u, w = 0, len(d)
    while u < w:
        i = (u + w) // 2
        if d[i] == 0:
            u = i + 1
        else:
            w = i
    return d[u:]


def start_of_byte(tr, k):
    """Start bit of byte k, k <= number of leading NULs (a NUL frame has one falling edge)."""
    prev, n = 1, 0
    for t, v in tr:
        if prev == 1 and v == 0:
            if n == k:
                return t
            n += 1
        prev = v
    return None


for baud in BAUDS:
    pl = baud // 64
    for text in (b"583", b"HELLO FROM PC-1500A, 0123456789 abcdef!"):
        payload = b"\0" * pl + text + b"\r\n"
        for inv in (0, 1):
            for timing in ("mame", "guide"):
                tr = send(payload, baud, inv, timing)
                frame = 10.0 / baud
                t_text = start_of_byte(tr, pl)  # start bit of the 1st text byte
                # the receiver must be polling before the last NUL's stop bit ends
                last = t_text - 2 * frame
                ds = [-0.02, 0.0] + [last * k / 24 for k in range(1, 25)]
                bad = [d for d in ds
                       if skip_nuls(receive(shifted(tr, d), baud, inv, timing)) != text + b"\r\n"]
                check("%4d bps, %2d+%d bytes, %s, %-5s: entry -20 ms .. %.0f ms into the NULs"
                      % (baud, pl, len(text) + 2, "inv" if inv else "TTL", timing, last * 1000),
                      not bad, "bad entries (ms): %s" % [round(d * 1000, 2) for d in bad[:6]])
print("FAILURES: %d" % fails)
sys.exit(1 if fails else 0)
