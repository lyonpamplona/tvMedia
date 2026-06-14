"""Primitivas de segurança: hashing de senha e rate-limiting de login.

Usa apenas a biblioteca padrão (``hashlib``/``hmac``/``secrets``) para evitar
dependências extras e funcionar bem em hardware modesto (ex.: Raspberry Pi 4).

* Senhas são armazenadas no formato ``pbkdf2_sha256$<iter>$<salt>$<hash>``.
* O rate-limiter é em memória (janela deslizante por chave), adequado a uma
  instância única. Para múltiplas instâncias, troque por um backend
  compartilhado (ex.: Redis).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import deque

from .config import settings

_PBKDF2_ITERATIONS = 240_000
_ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """Gera o hash seguro de uma senha em texto puro.

    Args:
        password: senha em texto puro.
        iterations: número de iterações do PBKDF2.

    Returns:
        str: representação ``pbkdf2_sha256$<iter>$<salt>$<hash>``.
    """
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()
    return f"{_ALGORITHM}${iterations}${salt}${derived}"


def verify_password(password: str, stored: str) -> bool:
    """Verifica uma senha contra o hash armazenado (resistente a timing).

    Args:
        password: senha em texto puro informada no login.
        stored: hash previamente gerado por :func:`hash_password`.

    Returns:
        bool: True se a senha corresponder ao hash.
    """
    try:
        algorithm, iter_str, salt, expected = stored.split("$", 3)
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False
    try:
        iterations = int(iter_str)
    except ValueError:
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()
    return hmac.compare_digest(derived, expected)


class RateLimiter:
    """Limitador de taxa em memória por chave (janela deslizante).

    Mantém, para cada chave (ex.: IP), os instantes das tentativas recentes.
    Ao estourar ``max_attempts`` dentro de ``window_seconds``, a chave fica
    bloqueada por ``block_seconds``.
    """

    def __init__(
        self, *, max_attempts: int, window_seconds: int, block_seconds: int
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._blocked_until: dict[str, float] = {}

    def _now(self) -> float:
        return time.monotonic()

    def retry_after(self, key: str) -> int:
        """Segundos restantes de bloqueio para a chave (0 se liberada)."""
        until = self._blocked_until.get(key)
        if until is None:
            return 0
        remaining = until - self._now()
        if remaining <= 0:
            self._blocked_until.pop(key, None)
            return 0
        return int(remaining) + 1

    def is_blocked(self, key: str) -> bool:
        """True se a chave está atualmente bloqueada."""
        return self.retry_after(key) > 0

    def register_failure(self, key: str) -> None:
        """Registra uma tentativa malsucedida e bloqueia se exceder o limite."""
        now = self._now()
        bucket = self._attempts.setdefault(key, deque())
        bucket.append(now)
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_attempts:
            self._blocked_until[key] = now + self.block_seconds
            bucket.clear()

    def reset(self, key: str) -> None:
        """Limpa o histórico de uma chave (após login bem-sucedido)."""
        self._attempts.pop(key, None)
        self._blocked_until.pop(key, None)


# Limitador compartilhado para o endpoint de login, configurado por env.
login_rate_limiter = RateLimiter(
    max_attempts=settings.login_max_attempts,
    window_seconds=settings.login_window_seconds,
    block_seconds=settings.login_block_seconds,
)
