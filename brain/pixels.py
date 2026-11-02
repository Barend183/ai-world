"""Turns the AI's pixel art into a PNG, so it can look at its own drawings next to real photos."""
import struct
import zlib


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def png(rows, palette, scale=6, background="#efe6d6"):
    width = max(len(r) for r in rows)
    bg = _hex(background)
    lines = []
    for row in rows:
        px = b"".join(bytes(_hex(palette[ch]) if ch in palette else bg) * scale for ch in row.ljust(width, "."))
        lines += [b"\x00" + px] * scale
    raw = b"".join(lines)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    head = struct.pack(">IIBBBBB", width * scale, len(rows) * scale, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def render_creation(sp):
    """A picture of a creation exactly as the world draws it (drawn shapes too), via Node.js.
    Returns PNG bytes, or None when Node.js isn't installed."""
    import json
    import os
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        return None
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.js")
    done = subprocess.run([node, script], input=json.dumps(sp).encode(), capture_output=True, timeout=60)
    return done.stdout if done.returncode == 0 and done.stdout[:4] == b"\x89PNG" else None
