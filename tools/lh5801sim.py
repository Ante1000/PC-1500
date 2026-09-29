"""Minimal LH5801 (Sharp PC-1500) simulator for testing the bit-banged UART.

Instruction semantics and cycle counts follow MAME's lh5801 core
(src/devices/cpu/lh5801/5801tbl.hxx).  An alternative timing table
('guide') uses the values from the LH5801 instruction summary
(ROR/SHR 9, ROL 8 cycles, shifts change only C, not Z) so we can check
sensitivity to cycle counts and flag behaviour.

ME1 I/O: LH5811 at &F000.. ; &F00D = DDB, &F00F = port B (RX input on
PB2 = CMT-IN, or on another bit with rx_bit, e.g. PB0/PB1 for v56; the other
pins read 1). As in the LH5811 TRM (and MAME's lh5810), a port B bit whose DDB
bit is 1 (output) reads back the OPB latch, not the pin, so SERIN only sees
the line after it has made its bit an input. DDB starts at &FF (all outputs,
latch 0) - the worst case; the PC-1500 ROM itself always keeps DDB = &00.
&F008 = port C (PC7 = TX out).
"""
import bisect
import re

CLOCK_HZ = 1_300_000


class Line:
    """Logic level on the RX input (PB2 or PB0) as a function of time (seconds)."""

    def __init__(self, idle=1):
        self.t = [0.0]
        self.v = [idle]

    def add(self, t, v):
        if self.v[-1] != v:
            self.t.append(t)
            self.v.append(v)

    def level(self, t):
        i = bisect.bisect_right(self.t, t) - 1
        return self.v[max(i, 0)]

    def uart(self, data, t0, baud=4800.0, gap=0.0, stop_bits=1.0):
        """Append 8N1 frames starting at t0; returns end time."""
        bt = 1.0 / baud
        t = t0
        for b in data:
            self.add(t, 0)                      # start bit
            for i in range(8):
                self.add(t + (1 + i) * bt, (b >> i) & 1)
            self.add(t + 9 * bt, 1)             # stop bit
            t += (9 + stop_bits) * bt + gap
        return t


class Halt(Exception):
    pass


class CPU:
    def __init__(self, line, timing="mame", read_offset=3, rx_bit=2):
        self.m = bytearray(0x10000)
        self.line = line
        self.a = 0
        self.x = self.y = self.u = 0
        self.p = 0
        self.s = 0x784F
        self.c = self.z = 0
        self.ie = 1
        self.cyc = 0
        self.ddb = 0xFF
        self.opb = 0x00                  # port B output latch
        self.pc_port = 0xFF
        self.timing = timing
        self.read_offset = read_offset   # cycles before instr end when ME1 is read
        self.rx_bit = rx_bit             # port B bit carrying the RX line
        self.cur_len = 0
        self.tx_log = []                 # (time, level) of PC7 writes

    # --- helpers -------------------------------------------------------
    def now(self):
        return self.cyc / CLOCK_HZ

    def io_read(self, addr):
        if addr == 0xF00F:
            t = (self.cyc + self.cur_len - self.read_offset) / CLOCK_HZ
            pins = (0xFF ^ 1 << self.rx_bit) | self.line.level(t) << self.rx_bit
            return (self.opb & self.ddb) | (pins & ~self.ddb & 0xFF)
        if addr == 0xF00D:
            return self.ddb
        if addr == 0xF008:
            return self.pc_port
        raise RuntimeError("io read %04X" % addr)

    def io_write(self, addr, v):
        if addr == 0xF00D:
            self.ddb = v
        elif addr == 0xF00F:
            self.opb = v
        elif addr == 0xF008:
            self.pc_port = v
            self.tx_log.append((self.now(), v >> 7 & 1))
        else:
            raise RuntimeError("io write %04X" % addr)

    def fetch(self):
        b = self.m[self.p]
        self.p = (self.p + 1) & 0xFFFF
        return b

    def fetch16(self):
        h = self.fetch()
        return h << 8 | self.fetch()

    def add_generic(self, l, r, carry):
        res = l + r + carry
        self.c = 1 if res & 0x100 else 0
        self.z = 1 if not (res & 0xFF) else 0
        return res & 0xFF

    def setz(self, v):
        self.z = 1 if v == 0 else 0

    @property
    def xl(self):
        return self.x & 0xFF

    @property
    def xh(self):
        return self.x >> 8

    def run(self, max_seconds=120.0):
        limit = int(max_seconds * CLOCK_HZ)
        while True:
            if self.cyc > limit:
                raise RuntimeError("timeout (hang) at P=%04X" % self.p)
            self.step()

    # --- one instruction ----------------------------------------------
    def step(self):
        op = self.fetch()
        g = self.timing == "guide"
        if op == 0xFD:
            op2 = self.fetch()
            if op2 == 0xBE:          # RIE
                self.ie = 0; n = 8
            elif op2 == 0x81:        # SIE
                self.ie = 1; n = 8
            elif op2 in (0x59, 0x5B, 0x5D, 0x5F):   # ANI/ORI/BII/ADI #(Y),i
                n = 17 if op2 != 0x5D else 14
                self.cur_len = n
                i = self.fetch()
                v = self.io_read(self.y)
                if op2 == 0x59:
                    v &= i; self.setz(v); self.io_write(self.y, v)
                elif op2 == 0x5B:
                    v |= i; self.setz(v); self.io_write(self.y, v)
                elif op2 == 0x5D:
                    self.setz(v & i)
                else:
                    v = self.add_generic(v, i, 0); self.io_write(self.y, v)
            elif op2 == 0x15:        # LDA #(Y)
                n = 10; self.cur_len = n
                self.a = self.io_read(self.y); self.setz(self.a)
            elif op2 == 0x62:        # DEC UH
                n = 9
                uh = self.add_generic(self.u >> 8, 0xFF, 0)
                self.u = uh << 8 | (self.u & 0xFF)
            elif op2 == 0x60:        # INC UH
                n = 9
                uh = self.add_generic(self.u >> 8, 1, 0)
                self.u = uh << 8 | (self.u & 0xFF)
            else:
                raise RuntimeError("FD %02X at %04X" % (op2, self.p - 2))
            self.cyc += n
            return
        n = None
        if op == 0x00:   # SBC XL
            self.a = self.add_generic(self.a, self.xl ^ 0xFF, self.c); n = 6
        elif op == 0x04: self.a = self.xl; self.setz(self.a); n = 5
        elif op == 0x84: self.a = self.xh; self.setz(self.a); n = 5
        elif op == 0x0A: self.x = (self.x & 0xFF00) | self.a; n = 5
        elif op == 0x08: self.x = self.a << 8 | self.xl; n = 5
        elif op == 0x0E: self.m[self.x] = self.a; n = 6
        elif op == 0x28: self.u = self.a << 8 | (self.u & 0xFF); n = 5
        elif op == 0x38: n = 5
        elif op == 0x41: self.m[self.x] = self.a; self.x = (self.x + 1) & 0xFFFF; n = 6
        elif op == 0x45:
            self.a = self.m[self.x]; self.setz(self.a); self.x = (self.x + 1) & 0xFFFF; n = 6
        elif op == 0x44: self.x = (self.x + 1) & 0xFFFF; n = 5
        elif op == 0x54: self.y = (self.y + 1) & 0xFFFF; n = 5
        elif op == 0x48: self.x = self.fetch() << 8 | self.xl; n = 6
        elif op == 0x4A: self.x = (self.x & 0xFF00) | self.fetch(); n = 6
        elif op == 0x58: self.y = self.fetch() << 8 | (self.y & 0xFF); n = 6
        elif op == 0x5A: self.y = (self.y & 0xFF00) | self.fetch(); n = 6
        elif op == 0x68: self.u = self.fetch() << 8 | (self.u & 0xFF); n = 6
        elif op == 0x6A: self.u = (self.u & 0xFF00) | self.fetch(); n = 6
        elif op == 0x62:  # DEC UL
            ul = self.add_generic(self.u & 0xFF, 0xFF, 0)
            self.u = (self.u & 0xFF00) | ul; n = 5
        elif op == 0x88:  # LOP UL,e
            e = self.fetch(); n = 8
            ul = self.u & 0xFF
            self.u = (self.u & 0xFF00) | ((ul - 1) & 0xFF)
            if ul:
                self.p = (self.p - e) & 0xFFFF; n += 3
        elif op in (0x81, 0x83, 0x89, 0x8B, 0x8E, 0x91, 0x93, 0x99, 0x9B, 0x9E):
            e = self.fetch()
            cond = {0x81: not self.c, 0x83: self.c, 0x89: not self.z, 0x8B: self.z,
                    0x8E: True, 0x91: not self.c, 0x93: self.c, 0x99: not self.z,
                    0x9B: self.z, 0x9E: True}[op]
            n = {0x8E: 5, 0x9E: 6}.get(op, 8)
            if cond:
                n += 3
                if op & 0x10:
                    self.p = (self.p - e) & 0xFFFF
                else:
                    self.p = (self.p + e) & 0xFFFF
        elif op == 0x9A:  # RTN
            self.p = self.m[(self.s + 1) & 0xFFFF] << 8 | self.m[(self.s + 2) & 0xFFFF]
            self.s = (self.s + 2) & 0xFFFF; n = 11
            if self.p == 0xFFFF:
                self.cyc += n
                raise Halt()
        elif op == 0xA5: self.a = self.m[self.fetch16()]; self.setz(self.a); n = 12
        elif op == 0xAE: self.m[self.fetch16()] = self.a; n = 12
        elif op == 0xB3: self.a = self.add_generic(self.a, self.fetch(), self.c); n = 7
        elif op == 0xB5: self.a = self.fetch(); self.setz(self.a); n = 6
        elif op == 0xB7: self.add_generic(self.a, self.fetch() ^ 0xFF, 1); n = 7
        elif op == 0xB9: self.a &= self.fetch(); self.setz(self.a); n = 7
        elif op == 0xBF: self.setz(self.a & self.fetch()); n = 7
        elif op == 0xD1:  # ROR
            nv = self.a
            self.a = ((self.c << 8) | nv) >> 1
            self.c = nv & 1; n = 9 if g else 6
            if not g: self.setz(self.a)
        elif op == 0xD5:  # SHR
            nv = self.a
            self.a = nv >> 1; self.c = nv & 1; n = 9 if g else 6
            if not g: self.setz(self.a)
        elif op == 0xDB:  # ROL
            nv = self.a
            self.a = ((nv << 1) | self.c) & 0xFF
            self.c = nv >> 7; n = 8 if g else 6
            if not g: self.setz(self.a)
        elif op == 0xDD: self.a = self.add_generic(self.a, 1, 0); n = 5
        elif op == 0xDF: self.a = self.add_generic(self.a, 0xFF, 0); n = 5
        elif op == 0xF9: self.c = 0; n = 4
        elif op == 0xFB: self.c = 1; n = 4
        else:
            raise RuntimeError("opcode %02X at %04X" % (op, self.p - 1))
        self.cyc += n

    def call(self, addr, xval=None, max_seconds=120.0):
        """Emulate BASIC CALL addr[,var]. Returns (C flag, X) after RTN."""
        if xval is not None:
            self.x = xval & 0xFFFF
        else:
            self.x = 0xC871          # CHECK_AT_END leaves a ROM return address in X
        self.s = 0x784F
        self.m[0x784E] = 0xFF        # sentinel return address &FFFF
        self.m[0x784F] = 0xFF
        self.s = 0x784D
        self.p = addr
        try:
            self.run(max_seconds)
        except Halt:
            return self.c, self.x


# --- tiny BASIC loader: evaluates assignments, POKE, INPUT and IF -------
def basic_eval(expr, env):
    e = expr.strip()
    e = re.sub(r"&([0-9A-Fa-f]+)", lambda mm: str(int(mm.group(1), 16)), e)
    e = re.sub(r"PEEK\s*30819", "64", e)                  # PEEK &7863 -> &40
    e = re.sub(r"INT\s*\(", "int(", e).replace("<>", "!=")
    return int(eval(e, {"int": int}, dict(env)))


def basic_cond(expr, env):
    """IF condition: = <> < > <= >= combined with AND / OR."""
    e = re.sub(r"(?<![<>!=])=(?!=)", "==", expr.replace("<>", "!="))
    e = re.sub(r"\bAND\b", " and ", re.sub(r"\bOR\b", " or ", e))
    return bool(basic_eval(e, env))


class BasicJump(Exception):
    """The installer took a GOTO/END before the POKE lines (e.g. bad input)."""


def run_statements(stmts, env, cpu, inputs, num):
    """Execute statements of one line; returns False to skip the rest of it."""
    for stmt in stmts:
        s = stmt.strip()
        if s.startswith("REM"):
            return False
        if s.startswith("IF "):
            m = re.match(r"^IF\s+(.+?)\s*(?:THEN\s+|(?=LET\s|PRINT|BEEP|GOTO|END))(.*)$", s)
            assert m, (num, s)
            try:
                ok = basic_cond(m.group(1), env)
            except Exception:
                return False          # unknown values (e.g. PEEK of BASIC pointers)
            if not ok:
                return False          # false condition: rest of the line is skipped
            s = m.group(2).strip()
        if re.match(r"^(GOTO|END)\b|^\d+$", s):
            raise BasicJump("line %s: %s" % (num, s))
        if s.startswith("INPUT"):
            var = re.split(r"[;,]", s)[-1].strip()
            if inputs is None or var not in inputs:
                return False          # ENTER alone: variable unchanged, rest of line skipped
            env[var] = inputs[var]
            continue
        if s.startswith("POKE "):
            args = split_args(s[5:])
            addr = basic_eval(args[0], env)
            for i, a in enumerate(args[1:]):
                v = basic_eval(a, env)
                assert 0 <= v <= 255, (num, a, v)
                cpu.m[addr + i] = v
            continue
        m = re.match(r"^(?:LET\s+)?([A-Z][A-Z0-9]?)\s*=\s*(.+)$", s)
        if m:
            try:
                env[m.group(1)] = basic_eval(m.group(2), env)
            except Exception:
                pass
    return True


def load_basic(path, cpu, stop_line=None, inputs=None):
    """Run the installer lines below stop_line (straight through, no jumps).
    inputs: values typed at INPUT prompts, {var: value}; a missing var means
    ENTER alone (the PC-1500 ROM then keeps the variable and skips the rest
    of the line)."""
    env = {}
    for raw in open(path, encoding="ascii"):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        num, _, body = raw.partition(" ")
        if stop_line is not None and int(num) >= stop_line:
            break
        run_statements(split_statements(body), env, cpu, inputs, num)
    return env


def split_statements(body):
    out, cur, q = [], "", False
    for ch in body:
        if ch == '"':
            q = not q
        if ch == ":" and not q:
            out.append(cur); cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def split_args(s):
    out, cur, depth = [], "", 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    out.append(cur)
    return out
