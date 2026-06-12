"""Endpoints de autenticação do painel administrativo.

Expõe ``POST /api/auth/login``: recebe a senha única do painel e, se válida,
retorna um token de sessão assinado (HMAC) com validade configurável. As demais
rotas administrativas exigem esse token via cabeçalho ``Authorization: Bearer``.
Este endpoint é público (não exige token).
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, status

from .. import schemas
from ..auth import create_token
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(data: schemas.LoginRequest) -> schemas.TokenResponse:
    """Valida a senha do painel e devolve um token de sessão.

    Args:
        data: payload contendo a senha do painel.

    Returns:
        schemas.TokenResponse: token assinado e validade em segundos.

    Raises:
        HTTPException: 401 quando a senha informada é incorreta.
    """
    # Comparação resistente a timing attacks.
    if not hmac.compare_digest(data.password, settings.admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha incorreta.",
        )
    token, expires_in = create_token()
    return schemas.TokenResponse(token=token, expires_in=expires_in)
