"""Tiny two-pass assembler for the SERIN routine (LH5801 subset).

Each source line: [LABEL:] MNEMONIC [OPERANDS] [; comment]
Symbolic byte operands (RH, RL, R1, CN) are kept symbolic so they can be
emitted as BASIC variables in the POKE lines.
"""
import re

SYMS = ("RH", "RL", "R1", "CN", "TH", "TL", "RP", "CP", "TP", "NP")

# (mnemonic, operand-pattern) -> (opcode bytes, kind)
# kind: None | 'imm' | 'abs' | 'rel+' | 'rel-'
TABLE = {
    ("RIE", ""): ([0xFD, 0xBE], None),
    ("LDA", "XH"): ([0x84], None),
    ("LDA", "XL"): ([0x04], None),
    ("STA", "XL"): ([0x0A], None),
    ("BZR+", "L"): ([0x89], "rel+"),
    ("BZS+", "L"): ([0x8B], "rel+"),
    ("BCH+", "L"): ([0x8E], "rel+"),
    ("BZR-", "L"): ([0x99], "rel-"),
    ("BCH-", "L"): ([0x9E], "rel-"),
    ("LOP", "UL,L"): ([0x88], "rel-"),
    ("BII", "A,i"): ([0xBF], "imm"),
    ("LDI", "A,i"): ([0xB5], "imm"),
    ("ADI", "A,i"): ([0xB3], "imm"),
    ("LDI", "XH,i"): ([0x48], "imm"),
    ("LDI", "XL,i"): ([0x4A], "imm"),
    ("LDI", "YH,i"): ([0x58], "imm"),
    ("LDI", "YL,i"): ([0x5A], "imm"),
    ("LDI", "UH,i"): ([0x68], "imm"),
    ("LDI", "UL,i"): ([0x6A], "imm"),
    ("STA", "(RX)"): ([0xAE, "RH", "RL"], None),
    ("STA", "(ab)"): ([0xAE], "abs"),
    ("LDA", "(ab)"): ([0xA5], "abs"),
    ("STA", "XH"): ([0x08], None),
    ("LDA", "(RX)"): ([0xA5, "RH", "RL"], None),
    ("ANI", "#(Y),i"): ([0xFD, 0x59], "imm"),
    ("BII", "#(Y),i"): ([0xFD, 0x5D], "imm"),
    ("INC", "Y"): ([0x54], None),
    ("DEC", "UH"): ([0xFD, 0x62], None),
    ("DEC", "A"): ([0xDF], None),
    ("SEC", ""): ([0xFB], None),
    ("REC", ""): ([0xF9], None),
    ("ROR", ""): ([0xD1], None),
    ("SIN", "X"): ([0x41], None),
    ("RTN", ""): ([0x9A], None),
    ("NOP", ""): ([0x38], None),
    ("SHR", ""): ([0xD5], None),
    ("LIN", "X"): ([0x45], None),
    ("STA", "UH"): ([0x28], None),
    ("BCS+", "L"): ([0x83], "rel+"),
    ("ORI", "#(Y),i"): ([0xFD, 0x5B], "imm"),
}


def parse_num(s):
    s = s.strip()
    if s in SYMS:
        return s
    if s.startswith("&"):
        return int(s[1:], 16)
    return int(s)


def classify(mn, ops):
    """Return (key, operand-string-for-imm/label)."""
    if mn in ("BZR+", "BZS+", "BCS+", "BCH+", "BZR-", "BCH-"):
        return (mn, "L"), ops
    if mn == "LOP":
        reg, lab = ops.split(",")
        assert reg == "UL"
        return (mn, "UL,L"), lab
    if ops in ("", "XH", "XL", "Y", "UH", "A", "X", "(RX)"):
        return (mn, ops), None
    m = re.match(r"^\(([^,()]+),([^,()]+)\)$", ops)      # (hi,lo) absolute address
    if m:
        return (mn, "(ab)"), (m.group(1), m.group(2))
    m = re.match(r"^(#\(Y\)|A|XH|XL|YH|YL|UH|UL),(.+)$", ops)
    if m:
        return (mn, m.group(1) + ",i"), m.group(2)
    raise ValueError((mn, ops))


def assemble(src):
    lines = []
    for raw in src.strip("\n").split("\n"):
        code, _, comment = raw.partition(";")
        label = None
        m = re.match(r"^(\w+):\s*(.*)$", code.strip())
        if m:
            label, code = m.group(1), m.group(2)
        code = code.strip()
        if not code:
            lines.append((label, None, None, comment.strip(), raw))
            continue
        parts = code.split(None, 1)
        mn = parts[0]
        ops = parts[1].replace(" ", "") if len(parts) > 1 else ""
        key, arg = classify(mn, ops)
        lines.append((label, key, arg, comment.strip(), raw))
    # pass 1: addresses
    addr, labels, sizes = 0, {}, []
    for label, key, arg, _, _ in lines:
        if label:
            labels[label] = addr
        if key is None:
            sizes.append(0)
            continue
        opc, kind = TABLE[key]
        n = len(opc) + {None: 0, "abs": 2}.get(kind, 1)
        sizes.append(n)
        addr += n
    # pass 2: bytes
    out, listing, addr = [], [], 0
    for (label, key, arg, comment, raw), n in zip(lines, sizes):
        if key is None:
            listing.append((addr, [], raw))
            continue
        opc, kind = TABLE[key]
        b = list(opc)
        if kind == "imm":
            b.append(parse_num(arg))
        elif kind == "abs":
            b.extend(parse_num(x) for x in arg)
        elif kind in ("rel+", "rel-"):
            target = labels[arg]
            nxt = addr + n
            d = target - nxt if kind == "rel+" else nxt - target
            assert 0 <= d <= 255, (raw, d)
            b.append(d)
        out.extend(b)
        listing.append((addr, b, raw))
        addr += n
    return out, labels, listing
