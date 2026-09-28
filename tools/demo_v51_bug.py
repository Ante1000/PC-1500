"""Show what SERIN v51 really did: 'HELLO' arrives on PB2, but the bad
branch offset (99 F6 = back 246 bytes) lands in the RX buffer, slides over
the zeros into SEROUT, transmits one byte on PC7 and returns."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lh5801sim import CPU, Line, load_basic  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V51 = os.path.join(ROOT, "pc1500_uart_installer-v51.txt")

line = Line()
line.uart(b"HELLO", 0.01)
cpu = CPU(line)
env = load_basic(V51, cpu, stop_line=360)
trace = []
step = cpu.step


def traced():
    trace.append(cpu.p)
    step()


cpu.step = traced
c, x = cpu.call(env["SI"])
RX = env["RX"]
print("returned after %.1f ms, C=%d" % (cpu.now() * 1000, c))
print("RX buffer:", bytes(cpu.m[RX:RX + 8]).hex(" "))
inrx = [p for p in trace if RX <= p < RX + 128]
inso = [p for p in trace if env["SO"] <= p < env["SO"] + 101]
print("instructions executed inside RX buffer: %d (from &%04X)" % (len(inrx), inrx[0]))
print("instructions executed inside SEROUT:    %d" % len(inso))
print("PC7 (TX) level changes: %d  -> one byte sent from the TX buffer" % len(cpu.tx_log))
