"""Run the SEROUT/SERIN test suite on the v56 installers (9600 bps,
255-byte buffers, RX on PB0 or PB1).

    python3 tools/test_v56.py [PB0|PB1]      (default: both)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PINS = sys.argv[1:] or ["PB0", "PB1"]
rc = 0
for pin in PINS:
    bas = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v56-9600-%s.txt" % pin)
    rc |= subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), bas, "9600", pin[2]])
sys.exit(rc)
