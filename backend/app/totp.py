"""TOTP RFC 6238 minimalista para 2FA (P8)."""

from __future__ import annotations

import base64
import hmac
import secrets
import struct
import time
from hashlib import sha1
from urllib.parse import quote


def generate_secret() -> str:
    """Gera segredo Base32 para apps autenticadores."""
    raw = secrets.token_bytes(20)
    return base64.b32encode(raw).decode().rstrip("=")


def _decode_secret(secret: str) -> bytes:
    padded = secret.strip().upper()
    padded += "=" * ((8 - len(padded) % 8) % 8)
    return base64.b32decode(padded)


def code_at(secret: str, when: int | None = None, step: int = 30, digits: int = 6) -> str:
    """Calcula o codigo TOTP para um instante."""
    when = int(time.time()) if when is None else int(when)
    counter = when // step
    msg = struct.pack(">Q", counter)
    digest = hmac.new(_decode_secret(secret), msg, sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** digits)).zfill(digits)


def verify(secret: str | None, code: str | None, *, window: int = 1) -> bool:
    """Valida codigo aceitando pequena janela de tolerancia."""
    if not secret or not code:
        return False
    clean = "".join(ch for ch in str(code) if ch.isdigit())
    if len(clean) != 6:
        return False
    now = int(time.time())
    for drift in range(-window, window + 1):
        if hmac.compare_digest(code_at(secret, now + drift * 30), clean):
            return True
    return False


def otpauth_url(*, issuer: str, username: str, secret: str) -> str:
    """Monta URL otpauth para QR/manual setup."""
    label = quote(f"{issuer}:{username}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
