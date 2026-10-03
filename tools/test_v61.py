"""Run the SEROUT/SERIN test suite on the v6.1 installer (1200/2400/4800/9600
bps, RX on PB0 or PB2, normal or inverted polarity, 255-byte buffers). The
installer's INPUT questions are answered from the parameters of each run.

    python3 tools/test_v61.py                 (a mix of speeds, ports and polarities)
    python3 tools/test_v61.py 4800:0:1        (speed:port:invert; port 0 = PB0, 2 = PB2)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BAS = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v6.1.txt")
RUNS = sys.argv[1:] or ["4800:0:0", "9600:0:1", "4800:2:1", "2400:0:1", "1200:2:1"]
rc = 0
for run in RUNS:
    baud, port, inv = (run.split(":") + ["0", "0"])[:3]
    rc |= subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), BAS, baud, port, inv])
sys.exit(rc)
