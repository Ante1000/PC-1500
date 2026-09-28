"""Run the SEROUT/SERIN test suite on the v55 installer (9600 bps, 256-byte buffers).

    python3 tools/test_v55.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BAS = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v55-9600.txt")
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), BAS, "9600"]))
