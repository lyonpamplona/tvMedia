"""Endpoints de autenticação do painel administrativo.

Fluxo baseado em usuário com token de sessão assinado (HMAC):

* ``POST /api/auth/login`` — valida usuário/senha e devolve um token. Mantém
  compatibilidade com o fluxo antigo: se ``username`` for omitido, assume o
  administrador padrão ``admin``. Protegido por rate-limit por IP.
* ``GET /api/auth/me`` — dados do usuário autenticado.
* ``POST /api/auth/change-password`` — troca a própria senha (revoga sessões).
* ``POST /api/auth/logout`` — revoga todas as sessões do usuário.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas, security
from ..auth import create_token, get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_key(request: Request) -> str:
    """Deriva a chave de rate-limit a partir do IP do cliente."""
    if request.client and request.client.host:
        return request.client.host
    return "desconhecido"


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    data: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)
) -> schemas.TokenResponse:
    """Valida as credenciais e devolve um token de sessão.

    Args:
        data: usuário (opcional) e senha do painel.
        request: requisição atual (para rate-limit por IP).
        db: sessão de banco.

    Returns:
        schemas.TokenResponse: token assinado, validade, usuário e papel.

    Raises:
        HTTPException: 429 quando há tentativas em excesso; 401 para
            credenciais inválidas.
    """
    key = _client_key(request)
    retry_after = security.login_rate_limiter.retry_after(key)
    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente em instantes.",
            headers={"Retry-After": str(retry_after)},
        )

    username = (data.username or "admin").strip()
    user = crud.get_user_by_username(db, username)
    valid = (
        user is not None
        and user.is_active
        and security.verify_password(data.password, user.password_hash)
    )
    if not valid or user is None:
        security.login_rate_limiter.register_failure(key)
        crud.record_audit(
            db,
            actor=username,
            action="login_failed",
            entity_type="user",
            entity_id=getattr(user, "id", None),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
        )

    security.login_rate_limiter.reset(key)
    crud.touch_last_login(db, user)
    crud.record_audit(
        db, actor=user.username, action="login", entity_type="user", entity_id=user.id
    )
    token, expires_in = create_token(user)
    company = crud.get_company(db, user.company_id) if user.company_id else None
    return schemas.TokenResponse(
        token=token,
        expires_in=expires_in,
        username=user.username,
        role=user.role,
        is_super_admin=user.is_super_admin,
        company_id=user.company_id,
        company_name=company.name if company else None,
    )


@router.get("/me", response_model=schemas.UserRead)
def me(user: models.User = Depends(get_current_user)) -> models.User:
    """Retorna os dados do usuário autenticado."""
    return user


@router.post("/change-password", response_model=schemas.TokenResponse)
def change_password(
    data: schemas.ChangePasswordRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.TokenResponse:
    """Troca a senha do usuário autenticado e devolve um novo token.

    Trocar a senha revoga as sessões antigas; por isso um novo token é
    emitido para que o cliente atual permaneça logado.

    Raises:
        HTTPException: 400 quando a senha atual não confere.
    """
    if not security.verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta."
        )
    crud.set_password(db, user, data.new_password)
    crud.record_audit(
        db,
        actor=user.username,
        action="change_password",
        entity_type="user",
        entity_id=user.id,
    )
    token, expires_in = create_token(user)
    return schemas.TokenResponse(
        token=token, expires_in=expires_in, username=user.username, role=user.role
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """Revoga todas as sessões ativas do usuário (logout global)."""
    crud.revoke_user_tokens(db, user)
    crud.record_audit(
        db, actor=user.username, action="logout", entity_type="user", entity_id=user.id
    )
