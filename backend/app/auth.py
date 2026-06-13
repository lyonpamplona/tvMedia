"""Autenticação por usuário + token de sessão assinado (HMAC), com papéis.

O token tem o formato ``base64(payload).assinatura`` onde o ``payload`` contém:

* ``sub`` — ID do usuário.
* ``ver`` — versão do token do usuário (permite revogação em massa).
* ``exp`` — instante de expiração (epoch).

A assinatura é um HMAC-SHA256 do payload usando ``settings.secret_key``.
Incrementar ``User.token_version`` invalida todos os tokens daquele usuário.

Dependências úteis para os roteadores:

* :func:`get_current_user` — exige um token válido e devolve o usuário.
* :func:`require_auth` — alias de :func:`get_current_user` (compatibilidade).
* :func:`require_role` — fábrica de dependência que exige um papel mínimo.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

# ``auto_error=False`` para retornarmos 401 com mensagem própria.
_bearer = HTTPBearer(auto_error=False)

# Hierarquia de papéis: índice maior = mais permissões.
_ROLE_ORDER: dict[models.UserRole, int] = {
    models.UserRole.viewer: 0,
    models.UserRole.editor: 1,
    models.UserRole.admin: 2,
}


def _sign(payload_b64: str) -> str:
    """Calcula a assinatura HMAC-SHA256 (hex) de um payload em base64."""
    return hmac.new(
        settings.secret_key.encode(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()


def create_token(user: models.User) -> tuple[str, int]:
    """Cria um token de sessão assinado para um usuário.

    Args:
        user: usuário autenticado.

    Returns:
        tuple[str, int]: o token e a validade restante em segundos.
    """
    ttl_seconds = settings.token_ttl_hours * 3600
    exp = int(time.time()) + ttl_seconds
    payload = json.dumps(
        {"sub": user.id, "ver": user.token_version, "exp": exp},
        separators=(",", ":"),
    )
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    token = f"{payload_b64}.{_sign(payload_b64)}"
    return token, ttl_seconds


def _decode_token(token: str) -> dict | None:
    """Valida assinatura e expiração e devolve o payload (ou ``None``)."""
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) <= int(time.time()):
        return None
    return payload


def _unauthorized(detail: str = "Não autenticado.") -> HTTPException:
    """Monta uma exceção 401 padronizada."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    """Dependência que valida o token e retorna o usuário autenticado.

    Raises:
        HTTPException: 401 se o token estiver ausente, inválido, expirado,
            revogado, ou se o usuário estiver inativo/inexistente.
    """
    if credentials is None:
        raise _unauthorized()
    payload = _decode_token(credentials.credentials)
    if payload is None:
        raise _unauthorized()
    user = db.get(models.User, int(payload.get("sub", 0)))
    if user is None or not user.is_active:
        raise _unauthorized()
    if int(payload.get("ver", -1)) != user.token_version:
        raise _unauthorized("Sessão revogada.")
    return user


# Alias histórico: muitos roteadores usam ``Depends(require_auth)``.
require_auth = get_current_user


def require_role(minimum: models.UserRole):
    """Fábrica de dependência que exige um papel mínimo.

    Args:
        minimum: papel mínimo necessário (viewer < editor < admin).

    Returns:
        Callable: dependência FastAPI que devolve o usuário se autorizado.
    """

    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if _ROLE_ORDER[user.role] < _ROLE_ORDER[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação.",
            )
        return user

    return dependency


require_admin = require_role(models.UserRole.admin)
require_editor = require_role(models.UserRole.editor)


# --------------------------------------------------------------------------- #
# Multi-tenant (escopo por empresa)
# --------------------------------------------------------------------------- #
@dataclass
class Scope:
    """Escopo de empresa resolvido para a requisição atual.

    Atributos:
        user: usuário autenticado.
        company_id: empresa em foco. ``None`` significa "todas as empresas"
            (apenas super admin sem empresa selecionada) e, em listagens,
            desativa o filtro por empresa.
        is_super_admin: se o usuário é super administrador.
    """

    user: models.User
    company_id: int | None
    is_super_admin: bool

    @property
    def write_company_id(self) -> int | None:
        """Empresa usada ao criar conteúdo.

        Para super admin sem empresa selecionada, recai sobre a empresa do
        próprio usuário (a "Matriz"), evitando criar conteúdo órfão.
        """
        if self.company_id is not None:
            return self.company_id
        return self.user.company_id


def get_scope(
    user: models.User = Depends(get_current_user),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
) -> Scope:
    """Resolve o escopo de empresa da requisição.

    * Usuário comum: travado na própria empresa (``user.company_id``).
    * Super admin: pode personificar uma empresa via cabeçalho
      ``X-Company-Id``; sem o cabeçalho, enxerga todas as empresas.
    """
    if user.is_super_admin:
        if x_company_id:
            try:
                return Scope(user=user, company_id=int(x_company_id), is_super_admin=True)
            except (TypeError, ValueError):
                pass
        return Scope(user=user, company_id=None, is_super_admin=True)
    return Scope(user=user, company_id=user.company_id, is_super_admin=False)


def require_super_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """Dependência que exige um super administrador (gestão de empresas)."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o super administrador pode executar esta operação.",
        )
    return user
