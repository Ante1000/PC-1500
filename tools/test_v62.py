"""Test the v6.2 installer. It installs the same code as v6.1; only the RX port
default (ENTER = PB2) and the skippable TX/RX tests are new.

    python3 tools/test_v62.py                 (a mix of speeds, ports and polarities)
    python3 tools/test_v62.py 4800:2:0        (speed:port:invert; port 0 = PB0, 2 = PB2)

First the RX port answers are checked (ENTER and 2 give PB2, 0 gives PB0, and the
POKE lines carry the matching DDB mask / bit mask), then the full SEROUT/SERIN
suite of tools/test_serin.py runs on the installer.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lh5801sim import CPU, Line, load_basic  # noqa: E402

BAS = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v6.2.txt")
RUNS = sys.argv[1:] or ["4800:2:0", "9600:2:1", "4800:0:1", "2400:2:1", "1200:0:0"]

rc = 0
print("== RX port question (v6.2: default PB2)")
for answer, port in ((None, 2), (2, 2), (0, 0)):
    inputs = {"B": 4, "I": 0}
    if answer is not None:
        inputs["P"] = answer
    cpu = CPU(Line())
    env = load_basic(BAS, cpu, stop_line=360, inputs=inputs)
    si = env["SI"]
    ok = (env["BM"], env["DB"], cpu.m[si + 26], cpu.m[si + 35]) == (
        1 << port, 255 - (1 << port), 255 - (1 << port), 1 << port)
    rc |= not ok
    print("  %s  %-6s -> PB%d (BM=%d, DB=&%02X)" % ("OK  " if ok else "FAIL",
          "ENTER" if answer is None else str(answer), port, env["BM"], env["DB"]))

for run in RUNS:
    baud, port, inv = (run.split(":") + ["0", "0"])[:3]
    rc |= subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), BAS, baud, port, inv])
sys.exit(rc)
