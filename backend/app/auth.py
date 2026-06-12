"""Autenticação simples por senha única + token de sessão assinado (HMAC).

Evita dependências externas (JWT/itsdangerous) usando apenas a biblioteca
padrão. O token tem o formato ``base64(payload).assinatura`` onde:

* ``payload`` é um JSON com o instante de expiração (``exp``).
* ``assinatura`` é um HMAC-SHA256 do payload usando ``settings.secret_key``.

O painel envia o token no cabeçalho ``Authorization: Bearer <token>``. Os
endpoints públicos (player, WebSocket, health, login) não exigem token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

# ``auto_error=False`` para podermos retornar 401 com mensagem própria.
_bearer = HTTPBearer(auto_error=False)


def _sign(payload_b64: str) -> str:
    """Calcula a assinatura HMAC-SHA256 (hex) de um payload em base64."""
    return hmac.new(
        settings.secret_key.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()


def create_token() -> tuple[str, int]:
    """Cria um token de sessão assinado válido por ``token_ttl_hours``.

    Returns:
        tuple[str, int]: o token e o tempo de validade restante em segundos.
    """
    ttl_seconds = settings.token_ttl_hours * 3600
    exp = int(time.time()) + ttl_seconds
    payload = json.dumps({"exp": exp}, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    token = f"{payload_b64}.{_sign(payload_b64)}"
    return token, ttl_seconds


def _verify_token(token: str) -> bool:
    """Valida assinatura e expiração de um token.

    Args:
        token: token recebido do cliente.

    Returns:
        bool: True se o token for válido e não expirado.
    """
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return False
    # Comparação resistente a timing attacks.
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
    except (ValueError, json.JSONDecodeError):
        return False
    return int(payload.get("exp", 0)) > int(time.time())


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Dependência que protege rotas administrativas.

    Args:
        credentials: credenciais Bearer extraídas do cabeçalho Authorization.

    Raises:
        HTTPException: 401 quando o token está ausente ou é inválido.
    """
    if credentials is None or not _verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
