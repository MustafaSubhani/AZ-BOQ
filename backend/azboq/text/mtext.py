"""MTEXT and TEXT to plain text, keeping each run's font so legacy runs can be decoded.

Fonts switch inside words and inside numbers (8\\f..;3\\f..;.\\f..;10 is 83.10), so
runs are decoded one by one and then joined, never split on a run boundary.
"""
import re
from dataclasses import dataclass

from .legacy import Decoded, decode

_SPECIAL = {"c": "Ø", "d": "°", "p": "±", "%": "%"}


@dataclass
class Run:
    text: str
    font: str | None
    charset: int | None


def _percent_codes(s: str) -> str:
    s = re.sub(r"%%(\d{3})", lambda m: chr(int(m.group(1))), s)
    s = re.sub(r"%%([cdpCDP%])", lambda m: _SPECIAL[m.group(1).lower()], s)
    return re.sub(r"%%[uUoOkK]", "", s)


def parse_runs(raw: str, base_font: str | None = None) -> list[Run]:
    runs: list[Run] = []
    stack = [(base_font, None)]
    font, charset = base_font, None
    buf: list[str] = []
    i, n = 0, len(raw)

    def flush():
        if buf:
            runs.append(Run("".join(buf), font, charset))
            buf.clear()

    while i < n:
        ch = raw[i]
        if ch == "{":
            flush()
            stack.append((font, charset))
            i += 1
            continue
        if ch == "}":
            flush()
            if len(stack) > 1:
                font, charset = stack.pop()
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            code = raw[i + 1]
            if code in "\\{}":
                buf.append(code)
                i += 2
                continue
            if code == "P":
                buf.append("\n")
                i += 2
                continue
            if code == "~":
                buf.append(" ")
                i += 2
                continue
            if code in "LlOoKkNX":
                i += 2
                continue
            if code == "U" and raw[i + 2:i + 3] == "+":
                hexpart = raw[i + 3:i + 7]
                try:
                    buf.append(chr(int(hexpart, 16)))
                    i += 7
                except ValueError:
                    i += 2
                continue
            if code == "M" and raw[i + 2:i + 3] == "+":
                i += 8
                continue
            if code == "S":
                end = raw.find(";", i)
                body = raw[i + 2:end if end != -1 else n]
                buf.append(re.sub(r"[\^#]", "/", body).replace("/ ", "/"))
                i = (end + 1) if end != -1 else n
                continue
            end = raw.find(";", i)
            if code == "f" or code == "F":
                flush()
                spec = raw[i + 2:end if end != -1 else n]
                parts = spec.split("|")
                font = parts[0] or font
                charset = None
                for p in parts[1:]:
                    if p.startswith("c") and p[1:].isdigit():
                        charset = int(p[1:])
                i = (end + 1) if end != -1 else n
                continue
            if code in "HCTQWApa":
                i = (end + 1) if end != -1 else n
                continue
            i += 2
            continue
        buf.append(ch)
        i += 1
    flush()
    for r in runs:
        r.text = _percent_codes(r.text)
    return runs


@dataclass
class TextResult:
    raw: str
    plain_raw: str
    decoded: str
    scheme: str
    confidence: float
    fonts: list[str]


def decode_mtext(raw: str, base_font: str | None = None) -> TextResult:
    runs = parse_runs(raw or "", base_font)
    pieces, schemes, conf, fonts = [], set(), 1.0, []
    for r in runs:
        d: Decoded = decode(r.text, r.font)
        pieces.append(d.text)
        if d.scheme != "unicode":
            schemes.add(d.scheme)
            conf = min(conf, d.confidence)
        if r.font and r.font not in fonts:
            fonts.append(r.font)
    plain_raw = "".join(r.text for r in runs)
    decoded = "".join(pieces)
    scheme = "unicode" if not schemes else (schemes.pop() if len(schemes) == 1 else "mixed")
    return TextResult(raw, _tidy(plain_raw), _tidy(decoded), scheme, conf, fonts)


def decode_text(raw: str, font: str | None = None) -> TextResult:
    """Single-line TEXT, ATTRIB, DIMENSION override: no inline font switches, only %% codes."""
    plain = _percent_codes(raw or "")
    d = decode(plain, font)
    return TextResult(raw or "", _tidy(plain), _tidy(d.text), d.scheme, d.confidence, [font] if font else [])


def _tidy(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s).strip()
