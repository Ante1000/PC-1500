"""Run the SEROUT/SERIN test suite on the v6.0 installer (1200/2400/4800/9600
bps, RX on PB0 or PB2, 255-byte buffers). The installer's INPUT questions are
answered from the speed and the port of each run.

    python3 tools/test_v60.py                  (9600, 4800, 2400, 1200 on PB0 and 4800 on PB2)
    python3 tools/test_v60.py 4800:0 9600:2    (speed:port pairs, port 0 = PB0, 2 = PB2)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BAS = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v6.0.txt")
RUNS = sys.argv[1:] or ["9600:0", "4800:0", "2400:0", "1200:0", "4800:2"]
rc = 0
for run in RUNS:
    baud, _, port = run.partition(":")
    rc |= subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), BAS, baud, port or "0"])
sys.exit(rc)
