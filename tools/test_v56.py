"""Run the SEROUT/SERIN test suite on the v56 installer (9600 bps,
255-byte buffers, RX on PB0).

    python3 tools/test_v56.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BAS = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v56-9600-PB0.txt")
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), BAS, "9600", "0"]))
