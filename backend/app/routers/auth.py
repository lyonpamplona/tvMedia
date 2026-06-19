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

from .. import crud, models, schemas, security, totp
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

    if user.totp_enabled and not totp.verify(user.totp_secret, data.totp_code):
        security.login_rate_limiter.register_failure(key)
        crud.record_audit(
            db,
            actor=username,
            action="login_2fa_required",
            entity_type="user",
            entity_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código 2FA obrigatório ou inválido.",
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
        two_factor_required=user.totp_enabled,
    )


@router.get("/me", response_model=schemas.UserRead)
def me(user: models.User = Depends(get_current_user)) -> models.User:
    """Retorna os dados do usuário autenticado."""
    return user


@router.post("/2fa/setup", response_model=schemas.TotpSetupRead)
def setup_2fa(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.TotpSetupRead:
    """Gera segredo TOTP para o usuario autenticado."""
    secret = totp.generate_secret()
    crud.set_user_totp_secret(db, user, secret)
    return schemas.TotpSetupRead(
        secret=secret,
        otpauth_url=totp.otpauth_url(issuer="tvMedia", username=user.username, secret=secret),
    )


@router.post("/2fa/enable", response_model=schemas.UserRead)
def enable_2fa(
    data: schemas.TotpVerifyRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.User:
    """Ativa 2FA apos confirmar um codigo do app autenticador."""
    if not totp.verify(user.totp_secret, data.code):
        raise HTTPException(status_code=400, detail="Código 2FA inválido.")
    return crud.enable_user_totp(db, user)


@router.post("/2fa/disable", response_model=schemas.UserRead)
def disable_2fa(
    data: schemas.TotpDisableRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.User:
    """Desativa 2FA confirmando senha atual."""
    if not security.verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")
    return crud.disable_user_totp(db, user)


@router.get("/api-tokens", response_model=list[schemas.ApiTokenRead])
def list_api_tokens(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[models.ApiToken]:
    """Lista tokens de API pessoais."""
    return crud.list_api_tokens(db, user)


@router.post("/api-tokens", response_model=schemas.ApiTokenCreated, status_code=201)
def create_api_token(
    data: schemas.ApiTokenCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ApiTokenCreated:
    """Cria token de API pessoal; o segredo e exibido uma unica vez."""
    row, token = crud.create_api_token(db, user, data)
    base = schemas.ApiTokenRead.model_validate(row)
    return schemas.ApiTokenCreated(**base.model_dump(), token=token)


@router.delete("/api-tokens/{token_id}", response_model=schemas.ApiTokenRead)
def revoke_api_token(
    token_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.ApiToken:
    """Revoga token de API pessoal."""
    row = crud.get_api_token(db, token_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Token não encontrado.")
    return crud.revoke_api_token(db, row)


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
