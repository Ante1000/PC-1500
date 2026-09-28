"""Run the SEROUT/SERIN test suite on the 9600 bps installer (v53).

    python3 tools/test_9600.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BAS = os.path.join(os.path.dirname(HERE), "pc1500_uart_installer-v53-9600.txt")
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, "test_serin.py"), BAS, "9600"]))
