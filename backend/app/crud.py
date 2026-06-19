"""Camada de acesso a dados (CRUD) sobre os modelos ORM.

Funções puras de banco, independentes do HTTP, para facilitar testes. Inclui:
mídia (com pastas, tags, busca e paginação), playlists, telas/zonas/
agendamentos, usuários, auditoria e eventos de reprodução (proof-of-play).
"""

from __future__ import annotations

import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas, security


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _tags_to_csv(tags: list[str] | None) -> str | None:
    """Converte uma lista de tags em CSV normalizado (ou None)."""
    if not tags:
        return None
    cleaned = [t.strip() for t in tags if t and t.strip()]
    return ",".join(dict.fromkeys(cleaned)) or None


def _split_csv_tags(value: str | None) -> list[str]:
    """Converte CSV de tags armazenado no banco em lista limpa."""
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def _ints_to_json(ids: list[int] | None) -> str | None:
    """Serializa IDs inteiros de forma estável para campos Text."""
    if not ids:
        return None
    cleaned = [int(value) for value in dict.fromkeys(ids)]
    return json.dumps(cleaned, separators=(",", ":"))


def _json_to_ints(value: str | None) -> list[int]:
    """Lê IDs serializados como JSON (fallback CSV)."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [int(item) for item in parsed]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return [int(part) for part in value.split(",") if part.strip().isdigit()]


def _dict_to_json(value: dict | None) -> str | None:
    """Serializa payload JSON opcional."""
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _list_to_json(value: list | None) -> str | None:
    """Serializa listas JSON opcionais."""
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------- #
# Empresas (multi-tenant)
# --------------------------------------------------------------------------- #
def get_company(db: Session, company_id: int) -> models.Company | None:
    """Busca uma empresa por ID."""
    return db.get(models.Company, company_id)


def get_company_by_slug(db: Session, slug: str) -> models.Company | None:
    """Busca uma empresa pelo slug."""
    return db.scalar(select(models.Company).where(models.Company.slug == slug))


def list_companies(db: Session) -> list[models.Company]:
    """Lista todas as empresas ordenadas por nome."""
    return list(db.scalars(select(models.Company).order_by(models.Company.name)))


def count_companies(db: Session) -> int:
    """Total de empresas cadastradas."""
    return int(db.scalar(select(func.count()).select_from(models.Company)) or 0)


def create_company(
    db: Session, *, name: str, primary_color: str | None = None
) -> models.Company:
    """Cria uma empresa (tenant)."""
    company = models.Company(name=name, primary_color=primary_color)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(
    db: Session, company: models.Company, data: schemas.CompanyUpdate
) -> models.Company:
    """Atualiza nome/cor/estado de uma empresa."""
    if data.name is not None:
        company.name = data.name
    if "primary_color" in data.model_fields_set:
        company.primary_color = data.primary_color
    if "emergency_message" in data.model_fields_set:
        company.emergency_message = data.emergency_message
    if data.emergency_active is not None:
        company.emergency_active = data.emergency_active
    if data.is_active is not None:
        company.is_active = data.is_active
    db.commit()
    db.refresh(company)
    return company


def set_company_logo(
    db: Session, company: models.Company, logo_path: str | None
) -> models.Company:
    """Define (ou limpa) o caminho do logo da empresa."""
    company.logo_path = logo_path
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company: models.Company) -> None:
    """Remove uma empresa e, em cascata, seus dados."""
    db.delete(company)
    db.commit()


def company_stats(db: Session, company: models.Company) -> dict[str, int]:
    """Conta os principais recursos de uma empresa (para o super admin)."""
    def _count(model) -> int:
        return int(
            db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.company_id == company.id)
            )
            or 0
        )

    return {
        "users": _count(models.User),
        "screens": _count(models.Screen),
        "media": _count(models.Media),
        "playlists": _count(models.Playlist),
    }


def seed_default_company(db: Session) -> models.Company:
    """Garante a existencia de uma empresa padrao 'Matriz'.

    Returns:
        models.Company: a empresa padrao (criada ou ja existente).
    """
    existing = db.scalar(select(models.Company).order_by(models.Company.id))
    if existing is not None:
        return existing
    company = models.Company(name="Matriz", primary_color="#7aa2f7")
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def backfill_company(db: Session, company_id: int) -> None:
    """Atribui a empresa padrao a todos os registros orfaos (sem empresa).

    Migracao idempotente: roda a cada startup e so afeta linhas com
    ``company_id`` nulo (instalacoes pre-multi-tenant).
    """
    for model in (
        models.User,
        models.MediaFolder,
        models.PlaylistFolder,
        models.Media,
        models.Playlist,
        models.Screen,
    ):
        rows = list(db.scalars(select(model).where(model.company_id.is_(None))))
        for row in rows:
            row.company_id = company_id
        if rows:
            db.commit()


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #
def count_users(db: Session) -> int:
    """Retorna o total de usuários cadastrados."""
    return int(db.scalar(select(func.count()).select_from(models.User)) or 0)


def get_user(db: Session, user_id: int) -> models.User | None:
    """Busca um usuário por ID."""
    return db.get(models.User, user_id)


def get_user_by_username(db: Session, username: str) -> models.User | None:
    """Busca um usuário pelo nome de usuário (case-insensitive)."""
    return db.scalar(
        select(models.User).where(func.lower(models.User.username) == username.lower())
    )


def list_users(db: Session, *, company_id: int | None = None) -> list[models.User]:
    """Lista usuários (opcionalmente de uma única empresa) ordenados por nome."""
    stmt = select(models.User)
    if company_id is not None:
        stmt = stmt.where(models.User.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.User.username)))


def create_user(
    db: Session,
    data: schemas.UserCreate,
    *,
    company_id: int | None = None,
    is_super_admin: bool = False,
) -> models.User:
    """Cria um usuário com a senha já convertida em hash, vinculado a uma empresa."""
    user = models.User(
        username=data.username,
        password_hash=security.hash_password(data.password),
        role=data.role,
        company_id=company_id,
        is_super_admin=is_super_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session, user: models.User, data: schemas.UserUpdate
) -> models.User:
    """Atualiza papel/estado/senha de um usuário.

    Trocar a senha incrementa ``token_version`` para revogar sessões ativas.
    """
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        user.password_hash = security.hash_password(data.password)
        user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def set_user_totp_secret(db: Session, user: models.User, secret: str | None) -> models.User:
    """Define segredo TOTP em setup pendente."""
    user.totp_secret = secret
    if secret is None:
        user.totp_enabled = False
    db.commit()
    db.refresh(user)
    return user


def enable_user_totp(db: Session, user: models.User) -> models.User:
    """Ativa 2FA e revoga sessões antigas."""
    user.totp_enabled = True
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def disable_user_totp(db: Session, user: models.User) -> models.User:
    """Desativa 2FA e remove segredo."""
    user.totp_enabled = False
    user.totp_secret = None
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, user: models.User, new_password: str) -> models.User:
    """Define uma nova senha e revoga as sessões existentes do usuário."""
    user.password_hash = security.hash_password(new_password)
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def revoke_user_tokens(db: Session, user: models.User) -> models.User:
    """Invalida todos os tokens do usuário (logout global)."""
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def touch_last_login(db: Session, user: models.User) -> None:
    """Registra o instante do último login bem-sucedido."""
    user.last_login = datetime.now(timezone.utc)
    db.commit()


def _api_token_hash(token: str) -> str:
    """Hash SHA-256 de token API."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_api_token(
    db: Session, user: models.User, data: schemas.ApiTokenCreate
) -> tuple[models.ApiToken, str]:
    """Cria token de API e devolve o segredo uma unica vez."""
    raw = "tvma_" + secrets.token_urlsafe(32)
    scopes = ",".join(dict.fromkeys(s.strip() for s in data.scopes if s and s.strip())) or "read"
    row = models.ApiToken(
        name=data.name,
        token_hash=_api_token_hash(raw),
        prefix=raw[:12],
        scopes=scopes,
        user_id=user.id,
        company_id=user.company_id,
        expires_at=data.expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, raw


def list_api_tokens(db: Session, user: models.User) -> list[models.ApiToken]:
    """Lista tokens pessoais do usuario."""
    stmt = select(models.ApiToken).where(models.ApiToken.user_id == user.id)
    return list(db.scalars(stmt.order_by(models.ApiToken.created_at.desc())))


def get_api_token(db: Session, token_id: int) -> models.ApiToken | None:
    """Busca token de API por ID."""
    return db.get(models.ApiToken, token_id)


def get_api_token_by_secret(db: Session, token: str) -> models.ApiToken | None:
    """Busca token pelo segredo recebido no Authorization Bearer."""
    return db.scalar(select(models.ApiToken).where(models.ApiToken.token_hash == _api_token_hash(token)))


def touch_api_token(db: Session, row: models.ApiToken) -> None:
    """Atualiza ultimo uso do token."""
    row.last_used_at = datetime.now(timezone.utc)
    db.commit()


def revoke_api_token(db: Session, row: models.ApiToken) -> models.ApiToken:
    """Revoga token de API."""
    row.is_active = False
    db.commit()
    db.refresh(row)
    return row


def delete_user(db: Session, user: models.User) -> None:
    """Remove um usuário."""
    db.delete(user)
    db.commit()


def seed_admin(db: Session) -> models.User | None:
    """Cria o administrador inicial a partir de ``ADMIN_PASSWORD`` se vazio.

    Returns:
        models.User | None: o admin criado, ou None se já havia usuários.
    """
    if count_users(db) > 0:
        return None
    from .config import settings

    company = seed_default_company(db)
    admin = models.User(
        username="admin",
        password_hash=security.hash_password(settings.admin_password),
        role=models.UserRole.admin,
        company_id=company.id,
        is_super_admin=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


# --------------------------------------------------------------------------- #
# Auditoria
# --------------------------------------------------------------------------- #
def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    detail: str | None = None,
    company_id: int | None = None,
) -> models.AuditLog:
    """Registra uma ação administrativa na trilha de auditoria."""
    entry = models.AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        company_id=company_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_audit(db: Session, *, limit: int = 100, offset: int = 0) -> tuple[list[models.AuditLog], int]:
    """Lista registros de auditoria (mais recentes primeiro) com total."""
    total = int(db.scalar(select(func.count()).select_from(models.AuditLog)) or 0)
    rows = list(
        db.scalars(
            select(models.AuditLog)
            .order_by(models.AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return rows, total


# --------------------------------------------------------------------------- #
# Pastas de mídia
# --------------------------------------------------------------------------- #
def list_folders(db: Session, *, company_id: int | None = None) -> list[models.MediaFolder]:
    """Lista pastas de mídia (opcionalmente de uma empresa) ordenadas por nome."""
    stmt = select(models.MediaFolder)
    if company_id is not None:
        stmt = stmt.where(models.MediaFolder.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.MediaFolder.name)))


def get_folder(db: Session, folder_id: int) -> models.MediaFolder | None:
    """Busca uma pasta por ID."""
    return db.get(models.MediaFolder, folder_id)


def create_folder(
    db: Session, data: schemas.FolderCreate, *, company_id: int | None = None
) -> models.MediaFolder:
    """Cria uma pasta de mídia."""
    folder = models.MediaFolder(
        name=data.name, parent_id=data.parent_id, company_id=company_id
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def update_folder(
    db: Session, folder: models.MediaFolder, data: schemas.FolderUpdate
) -> models.MediaFolder:
    """Atualiza nome/pai de uma pasta."""
    if data.name is not None:
        folder.name = data.name
    if data.parent_id is not None or "parent_id" in data.model_fields_set:
        folder.parent_id = data.parent_id
    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(db: Session, folder: models.MediaFolder) -> None:
    """Remove uma pasta (mídias dentro dela ficam sem pasta)."""
    db.delete(folder)
    db.commit()


# --------------------------------------------------------------------------- #
# Pastas de playlists
# --------------------------------------------------------------------------- #
def list_playlist_folders(
    db: Session, *, company_id: int | None = None
) -> list[models.PlaylistFolder]:
    """Lista pastas de playlists (opcionalmente de uma empresa)."""
    stmt = select(models.PlaylistFolder)
    if company_id is not None:
        stmt = stmt.where(models.PlaylistFolder.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.PlaylistFolder.name)))


def get_playlist_folder(
    db: Session, folder_id: int
) -> models.PlaylistFolder | None:
    """Busca uma pasta de playlist por ID."""
    return db.get(models.PlaylistFolder, folder_id)


def create_playlist_folder(
    db: Session, data: schemas.FolderCreate, *, company_id: int | None = None
) -> models.PlaylistFolder:
    """Cria uma pasta para organizar playlists."""
    folder = models.PlaylistFolder(
        name=data.name, parent_id=data.parent_id, company_id=company_id
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def update_playlist_folder(
    db: Session, folder: models.PlaylistFolder, data: schemas.FolderUpdate
) -> models.PlaylistFolder:
    """Atualiza nome/pai de uma pasta de playlist."""
    if data.name is not None:
        folder.name = data.name
    if data.parent_id is not None or "parent_id" in data.model_fields_set:
        folder.parent_id = data.parent_id
    db.commit()
    db.refresh(folder)
    return folder


def delete_playlist_folder(db: Session, folder: models.PlaylistFolder) -> None:
    """Remove uma pasta de playlist (playlists ficam sem pasta)."""
    db.delete(folder)
    db.commit()


# --------------------------------------------------------------------------- #
# Media
# --------------------------------------------------------------------------- #
def get_media(db: Session, media_id: int) -> models.Media | None:
    """Busca uma mídia por ID."""
    return db.get(models.Media, media_id)


def list_media(db: Session, *, company_id: int | None = None) -> list[models.Media]:
    """Lista mídias (opcionalmente de uma empresa), mais recentes primeiro."""
    stmt = select(models.Media)
    if company_id is not None:
        stmt = stmt.where(models.Media.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.Media.created_at.desc())))


def list_media_paginated(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    folder_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
    company_id: int | None = None,
) -> tuple[list[models.Media], int]:
    """Lista mídias com filtros opcionais e paginação.

    Args:
        limit: tamanho da página.
        offset: deslocamento.
        folder_id: filtra por pasta (use 0 para 'sem pasta').
        tag: filtra por tag (correspondência parcial em CSV).
        search: filtra por nome (correspondência parcial, case-insensitive).

    Returns:
        tuple[list[Media], int]: itens da página e total filtrado.
    """
    conditions = []
    if company_id is not None:
        conditions.append(models.Media.company_id == company_id)
    if folder_id is not None:
        if folder_id == 0:
            conditions.append(models.Media.folder_id.is_(None))
        else:
            conditions.append(models.Media.folder_id == folder_id)
    if tag:
        conditions.append(models.Media.tags.ilike(f"%{tag}%"))
    if search:
        conditions.append(models.Media.name.ilike(f"%{search}%"))

    base = select(models.Media)
    count_stmt = select(func.count()).select_from(models.Media)
    for cond in conditions:
        base = base.where(cond)
        count_stmt = count_stmt.where(cond)

    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            base.order_by(models.Media.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return rows, total


def create_media(
    db: Session,
    *,
    name: str,
    media_type: models.MediaType,
    path: str | None = None,
    source_url: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
    folder_id: int | None = None,
    company_id: int | None = None,
    width: int | None = None,
    height: int | None = None,
    processing_status: str | None = None,
    expires_at: datetime | None = None,
    collect_stats: bool = True,
) -> models.Media:
    """Cria uma mídia.

    Args:
        name: nome amigável.
        media_type: tipo da mídia.
        path: caminho relativo do arquivo enviado (imagens/vídeos).
        source_url: URL de origem (tipo 'url').
        content: conteúdo textual/HTML.
        tags: tags livres.
        folder_id: pasta opcional.

    Returns:
        models.Media: a mídia criada.
    """
    if processing_status is None:
        processing_status = (
            "pending"
            if media_type in (models.MediaType.image, models.MediaType.video)
            else "skipped"
        )
    media = models.Media(
        name=name,
        type=media_type,
        path=path,
        source_url=source_url,
        content=content,
        tags=_tags_to_csv(tags),
        folder_id=folder_id,
        company_id=company_id,
        width=width,
        height=height,
        processing_status=processing_status,
        expires_at=expires_at,
        collect_stats=collect_stats,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def set_media_processing(
    db: Session,
    media: models.Media,
    *,
    status: str,
    note: str | None = None,
    width: int | None = None,
    height: int | None = None,
    optimized_path: str | None = None,
    poster_path: str | None = None,
) -> models.Media:
    """Atualiza os campos de processamento server-side de uma midia.

    Apenas ``status`` e ``note`` sao sempre gravados; dimensoes e caminhos
    derivados sao atualizados somente quando informados (nao-None).
    """
    media.processing_status = status
    media.processing_note = note
    if width is not None:
        media.width = width
    if height is not None:
        media.height = height
    if optimized_path is not None:
        media.optimized_path = optimized_path
    if poster_path is not None:
        media.poster_path = poster_path
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def update_media(
    db: Session, media: models.Media, data: schemas.MediaUpdate
) -> models.Media:
    """Atualiza campos editaveis de uma mídia (parcial)."""
    if data.name is not None:
        media.name = data.name
    if "source_url" in data.model_fields_set:
        media.source_url = data.source_url
    if "content" in data.model_fields_set:
        media.content = data.content
    if data.tags is not None:
        media.tags = _tags_to_csv(data.tags)
    if "folder_id" in data.model_fields_set:
        media.folder_id = data.folder_id
    if "expires_at" in data.model_fields_set:
        media.expires_at = data.expires_at
    if data.collect_stats is not None:
        media.collect_stats = data.collect_stats
    db.commit()
    db.refresh(media)
    return media


def delete_media(db: Session, media: models.Media) -> None:
    """Remove uma mídia (e seus itens de playlist em cascata)."""
    db.delete(media)
    db.commit()


# --------------------------------------------------------------------------- #
# DataSets (P5)
# --------------------------------------------------------------------------- #
def list_datasets(
    db: Session, *, company_id: int | None = None
) -> list[models.DataSet]:
    """Lista DataSets do escopo atual."""
    stmt = select(models.DataSet).order_by(models.DataSet.name)
    if company_id is not None:
        stmt = stmt.where(models.DataSet.company_id == company_id)
    return list(db.scalars(stmt))


def get_dataset(db: Session, dataset_id: int) -> models.DataSet | None:
    """Busca um DataSet por ID."""
    return db.get(models.DataSet, dataset_id)


def create_dataset(
    db: Session, data: schemas.DataSetCreate, *, company_id: int | None = None
) -> models.DataSet:
    """Cria uma fonte de dados para widgets P5."""
    dataset = models.DataSet(
        name=data.name,
        kind=data.kind,
        source_url=data.source_url,
        columns=_list_to_json(data.columns),
        rows=_list_to_json(data.rows),
        fallback_rows=_list_to_json(data.fallback_rows),
        expires_at=data.expires_at,
        company_id=company_id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def update_dataset(
    db: Session, dataset: models.DataSet, data: schemas.DataSetUpdate
) -> models.DataSet:
    """Atualiza campos editaveis de um DataSet."""
    if data.name is not None:
        dataset.name = data.name
    if data.kind is not None:
        dataset.kind = data.kind
    if "source_url" in data.model_fields_set:
        dataset.source_url = data.source_url
    if "columns" in data.model_fields_set:
        dataset.columns = _list_to_json(data.columns)
    if "rows" in data.model_fields_set:
        dataset.rows = _list_to_json(data.rows)
    if "fallback_rows" in data.model_fields_set:
        dataset.fallback_rows = _list_to_json(data.fallback_rows)
    if "expires_at" in data.model_fields_set:
        dataset.expires_at = data.expires_at
    db.commit()
    db.refresh(dataset)
    return dataset


def replace_dataset_rows(
    db: Session,
    dataset: models.DataSet,
    *,
    rows: list[dict],
    columns: list[dict] | None = None,
    status: str = "ok",
    note: str | None = None,
) -> models.DataSet:
    """Substitui linhas/colunas e registra status da atualizacao."""
    dataset.rows = _list_to_json(rows)
    if columns is not None:
        dataset.columns = _list_to_json(columns)
    dataset.refresh_status = status
    dataset.refresh_note = note
    dataset.last_refresh_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dataset)
    return dataset


def mark_dataset_refresh(
    db: Session, dataset: models.DataSet, *, status: str, note: str | None = None
) -> models.DataSet:
    """Registra status de refresh sem alterar as linhas."""
    dataset.refresh_status = status
    dataset.refresh_note = note
    dataset.last_refresh_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, dataset: models.DataSet) -> None:
    """Remove um DataSet."""
    db.delete(dataset)
    db.commit()


# --------------------------------------------------------------------------- #
# Playlists
# --------------------------------------------------------------------------- #
def _playlist_query():
    """Query base de playlist com itens e mídias pré-carregados."""
    return select(models.Playlist).options(
        selectinload(models.Playlist.items).selectinload(models.PlaylistItem.media)
    )


def get_playlist(db: Session, playlist_id: int) -> models.Playlist | None:
    """Busca uma playlist por ID com itens carregados."""
    return db.scalar(_playlist_query().where(models.Playlist.id == playlist_id))


def list_playlists(
    db: Session,
    *,
    company_id: int | None = None,
    folder_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
) -> list[models.Playlist]:
    """Lista playlists com filtros opcionais e itens carregados."""
    stmt = _playlist_query()
    if company_id is not None:
        stmt = stmt.where(models.Playlist.company_id == company_id)
    if folder_id is not None:
        if folder_id == 0:
            stmt = stmt.where(models.Playlist.folder_id.is_(None))
        else:
            stmt = stmt.where(models.Playlist.folder_id == folder_id)
    if tag:
        stmt = stmt.where(models.Playlist.tags.ilike(f"%{tag}%"))
    if search:
        stmt = stmt.where(models.Playlist.name.ilike(f"%{search}%"))
    return list(db.scalars(stmt.order_by(models.Playlist.name)))


def list_playlists_paginated(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    company_id: int | None = None,
    folder_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
) -> tuple[list[models.Playlist], int]:
    """Lista playlists com paginação, filtros e total."""
    count_stmt = select(func.count()).select_from(models.Playlist)
    base = _playlist_query()
    conditions = []
    if company_id is not None:
        conditions.append(models.Playlist.company_id == company_id)
    if folder_id is not None:
        if folder_id == 0:
            conditions.append(models.Playlist.folder_id.is_(None))
        else:
            conditions.append(models.Playlist.folder_id == folder_id)
    if tag:
        conditions.append(models.Playlist.tags.ilike(f"%{tag}%"))
    if search:
        conditions.append(models.Playlist.name.ilike(f"%{search}%"))
    for cond in conditions:
        count_stmt = count_stmt.where(cond)
        base = base.where(cond)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            base.order_by(models.Playlist.name).limit(limit).offset(offset)
        )
    )
    return rows, total


def create_playlist(
    db: Session, data: schemas.PlaylistCreate, *, company_id: int | None = None
) -> models.Playlist:
    """Cria uma playlist vazia."""
    playlist = models.Playlist(
        name=data.name,
        tags=_tags_to_csv(data.tags),
        folder_id=data.folder_id,
        company_id=company_id,
    )
    db.add(playlist)
    db.commit()
    return get_playlist(db, playlist.id)


def update_playlist(
    db: Session, playlist: models.Playlist, data: schemas.PlaylistUpdate
) -> models.Playlist:
    """Atualiza uma playlist."""
    if data.name is not None:
        playlist.name = data.name
    if data.tags is not None:
        playlist.tags = _tags_to_csv(data.tags)
    if "folder_id" in data.model_fields_set:
        playlist.folder_id = data.folder_id
    db.commit()
    return get_playlist(db, playlist.id)


def bulk_tag_media(db: Session, media: list[models.Media], tags: list[str]) -> int:
    """Adiciona tags a várias mídias preservando as existentes."""
    cleaned = [t.strip() for t in tags if t and t.strip()]
    if not cleaned:
        return 0
    changed = 0
    for item in media:
        existing = _tags_to_csv(_split_csv_tags(item.tags) + cleaned)
        if item.tags != existing:
            item.tags = existing
            changed += 1
    if changed:
        db.commit()
    return changed


def bulk_tag_playlists(
    db: Session, playlists: list[models.Playlist], tags: list[str]
) -> int:
    """Adiciona tags a várias playlists preservando as existentes."""
    cleaned = [t.strip() for t in tags if t and t.strip()]
    if not cleaned:
        return 0
    changed = 0
    for playlist in playlists:
        existing = _tags_to_csv(_split_csv_tags(playlist.tags) + cleaned)
        if playlist.tags != existing:
            playlist.tags = existing
            changed += 1
    if changed:
        db.commit()
    return changed


def delete_playlist(db: Session, playlist: models.Playlist) -> None:
    """Remove uma playlist e seus itens."""
    db.delete(playlist)
    db.commit()


def _next_position(playlist: models.Playlist) -> int:
    """Calcula a próxima posição livre ao final da playlist."""
    if not playlist.items:
        return 0
    return max(item.position for item in playlist.items) + 1


def add_playlist_item(
    db: Session, playlist: models.Playlist, data: schemas.PlaylistItemCreate
) -> models.Playlist:
    """Adiciona um item de mídia a uma playlist."""
    position = data.position if data.position is not None else _next_position(playlist)
    item = models.PlaylistItem(
        playlist_id=playlist.id,
        media_id=data.media_id,
        position=position,
        duration=data.duration,
        fit=data.fit,
        focal=data.focal,
        transition=data.transition,
        muted=data.muted,
        play_full=data.play_full,
        start_at=data.start_at,
        end_at=data.end_at,
        max_plays_per_hour=data.max_plays_per_hour,
    )
    db.add(item)
    db.commit()
    return get_playlist(db, playlist.id)


def update_playlist_item(
    db: Session, item: models.PlaylistItem, data: schemas.PlaylistItemUpdate
) -> models.Playlist:
    """Atualiza um item de playlist (parcial)."""
    if data.duration is not None:
        item.duration = data.duration
    if data.position is not None:
        item.position = data.position
    if data.fit is not None:
        item.fit = data.fit
    if data.focal is not None:
        item.focal = data.focal
    if data.transition is not None:
        item.transition = data.transition
    if data.muted is not None:
        item.muted = data.muted
    if data.play_full is not None:
        item.play_full = data.play_full
    if "start_at" in data.model_fields_set:
        item.start_at = data.start_at
    if "end_at" in data.model_fields_set:
        item.end_at = data.end_at
    if "max_plays_per_hour" in data.model_fields_set:
        item.max_plays_per_hour = data.max_plays_per_hour
    db.commit()
    return get_playlist(db, item.playlist_id)


def remove_playlist_item(db: Session, item: models.PlaylistItem) -> models.Playlist:
    """Remove um item de uma playlist."""
    playlist_id = item.playlist_id
    db.delete(item)
    db.commit()
    return get_playlist(db, playlist_id)


def get_playlist_item(db: Session, item_id: int) -> models.PlaylistItem | None:
    """Busca um item de playlist por ID."""
    return db.get(models.PlaylistItem, item_id)


def reorder_items(
    db: Session, playlist: models.Playlist, item_ids: list[int]
) -> models.Playlist:
    """Reordena os itens de uma playlist conforme a sequência de IDs."""
    order = {item_id: index for index, item_id in enumerate(item_ids)}
    for item in playlist.items:
        if item.id in order:
            item.position = order[item.id]
    db.commit()
    return get_playlist(db, playlist.id)


# --------------------------------------------------------------------------- #
# Telas, zonas e agendamentos
# --------------------------------------------------------------------------- #
def _screen_query():
    """Query base de tela com zonas e agendamentos pré-carregados."""
    return select(models.Screen).options(
        selectinload(models.Screen.zones).selectinload(models.Zone.schedules),
        selectinload(models.Screen.overlays),
    )


def get_screen(db: Session, screen_id: int) -> models.Screen | None:
    """Busca uma tela por ID."""
    return db.scalar(_screen_query().where(models.Screen.id == screen_id))


def get_screen_by_slug(db: Session, slug: str) -> models.Screen | None:
    """Busca uma tela pelo slug público."""
    return db.scalar(_screen_query().where(models.Screen.slug == slug))


def get_screen_by_code(db: Session, code: str) -> models.Screen | None:
    """Busca uma tela pelo código de emparelhamento (6 dígitos)."""
    return db.scalar(_screen_query().where(models.Screen.pair_code == code))


def _template_zones(
    template: str | None, default_playlist_id: int | None
) -> list[dict]:
    """Geometria das zonas para um template de tela (cenários prontos)."""
    full = [
        {"name": "Principal", "x": 0.0, "y": 0.0, "width": 100.0, "height": 100.0,
         "z_index": 0, "default_playlist_id": default_playlist_id},
    ]
    if not template or template == "blank":
        return full
    if template == "restaurante":
        return [
            {"name": "Cardapio", "x": 0.0, "y": 0.0, "width": 100.0, "height": 82.0,
             "z_index": 0, "default_playlist_id": default_playlist_id},
            {"name": "Promocoes (rodape)", "x": 0.0, "y": 82.0, "width": 100.0,
             "height": 18.0, "z_index": 1, "default_playlist_id": None},
        ]
    if template == "recepcao":
        return [
            {"name": "Destaque", "x": 0.0, "y": 0.0, "width": 72.0, "height": 100.0,
             "z_index": 0, "default_playlist_id": default_playlist_id},
            {"name": "Avisos", "x": 72.0, "y": 0.0, "width": 28.0, "height": 86.0,
             "z_index": 1, "default_playlist_id": None},
            {"name": "Relogio/Clima", "x": 72.0, "y": 86.0, "width": 28.0,
             "height": 14.0, "z_index": 2, "default_playlist_id": None},
        ]
    if template == "varejo":
        return [
            {"name": "Vitrine", "x": 0.0, "y": 0.0, "width": 100.0, "height": 76.0,
             "z_index": 0, "default_playlist_id": default_playlist_id},
            {"name": "Ofertas (rodape)", "x": 0.0, "y": 76.0, "width": 100.0,
             "height": 24.0, "z_index": 1, "default_playlist_id": None},
        ]
    return full


def list_screens(db: Session, *, company_id: int | None = None) -> list[models.Screen]:
    """Lista telas (opcionalmente de uma empresa)."""
    stmt = _screen_query()
    if company_id is not None:
        stmt = stmt.where(models.Screen.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.Screen.name)))


def create_screen(
    db: Session, data: schemas.ScreenCreate, *, company_id: int | None = None
) -> models.Screen:
    """Cria uma tela, aplicando um template de layout quando informado."""
    screen = models.Screen(
        name=data.name,
        timezone=data.timezone,
        company_id=company_id,
        sync_group=data.sync_group,
        tags=_tags_to_csv(data.tags),
        location_label=data.location_label,
        latitude=data.latitude,
        longitude=data.longitude,
        resolution=data.resolution,
        orientation=data.orientation or "landscape",
        size_inches=data.size_inches,
        publish_status=data.publish_status,
        publish_at=data.publish_at,
        layout_locked=data.layout_locked,
        collect_stats=data.collect_stats,
        published_at=datetime.now(timezone.utc) if data.publish_status == "published" else None,
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)
    for zone_def in _template_zones(data.template, data.default_playlist_id):
        db.add(models.Zone(screen_id=screen.id, **zone_def))
    db.commit()
    return get_screen(db, screen.id)


def update_screen(
    db: Session, screen: models.Screen, data: schemas.ScreenUpdate
) -> models.Screen:
    """Atualiza nome/fuso de uma tela."""
    if data.name is not None:
        screen.name = data.name
    if data.timezone is not None:
        screen.timezone = data.timezone
    if "sync_group" in data.model_fields_set:
        screen.sync_group = data.sync_group
    if data.tags is not None:
        screen.tags = _tags_to_csv(data.tags)
    if "location_label" in data.model_fields_set:
        screen.location_label = data.location_label
    if "latitude" in data.model_fields_set:
        screen.latitude = data.latitude
    if "longitude" in data.model_fields_set:
        screen.longitude = data.longitude
    if "resolution" in data.model_fields_set:
        screen.resolution = data.resolution
    if "orientation" in data.model_fields_set and data.orientation:
        screen.orientation = data.orientation
    if "size_inches" in data.model_fields_set:
        screen.size_inches = data.size_inches
    if "background_audio_id" in data.model_fields_set:
        screen.background_audio_id = data.background_audio_id
    if data.publish_status is not None:
        screen.publish_status = data.publish_status
        if data.publish_status == "published" and screen.published_at is None:
            screen.published_at = datetime.now(timezone.utc)
    if "publish_at" in data.model_fields_set:
        screen.publish_at = data.publish_at
    if data.layout_locked is not None:
        screen.layout_locked = data.layout_locked
    if data.collect_stats is not None:
        screen.collect_stats = data.collect_stats
    for _theme_field in (
        "theme_bg",
        "theme_text",
        "theme_accent",
        "theme_ticker_bg",
        "theme_ticker_text",
    ):
        if _theme_field in data.model_fields_set:
            setattr(screen, _theme_field, getattr(data, _theme_field))
    db.commit()
    return get_screen(db, screen.id)


def publish_screen(
    db: Session, screen: models.Screen, *, publish_at: datetime | None = None
) -> models.Screen:
    """Publica uma tela agora ou agenda publicacao futura."""
    screen.publish_status = "published" if publish_at is None else "draft"
    screen.publish_at = publish_at
    if publish_at is None:
        screen.published_at = datetime.now(timezone.utc)
    db.commit()
    return get_screen(db, screen.id)


def set_screen_layout_lock(
    db: Session, screen: models.Screen, *, locked: bool
) -> models.Screen:
    """Liga/desliga a trava de layout de uma tela."""
    screen.layout_locked = locked
    db.commit()
    return get_screen(db, screen.id)


# --------------------------------------------------------------------------- #
# P4: grupos de telas, comandos e alertas
# --------------------------------------------------------------------------- #
def get_screen_group(db: Session, group_id: int) -> models.ScreenGroup | None:
    """Busca um grupo de telas por ID."""
    return db.get(models.ScreenGroup, group_id)


def list_screen_groups(
    db: Session, *, company_id: int | None = None
) -> list[models.ScreenGroup]:
    """Lista grupos de telas."""
    stmt = select(models.ScreenGroup)
    if company_id is not None:
        stmt = stmt.where(models.ScreenGroup.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.ScreenGroup.name)))


def create_screen_group(
    db: Session, data: schemas.ScreenGroupCreate, *, company_id: int | None = None
) -> models.ScreenGroup:
    """Cria um grupo de telas estático ou dinâmico."""
    group = models.ScreenGroup(
        name=data.name,
        mode=data.mode,
        screen_ids=_ints_to_json(data.screen_ids),
        tags=_tags_to_csv(data.tags),
        sync_group=data.sync_group,
        company_id=company_id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_screen_group(
    db: Session, group: models.ScreenGroup, data: schemas.ScreenGroupUpdate
) -> models.ScreenGroup:
    """Atualiza um grupo de telas."""
    if data.name is not None:
        group.name = data.name
    if data.mode is not None:
        group.mode = data.mode
    if data.screen_ids is not None:
        group.screen_ids = _ints_to_json(data.screen_ids)
    if data.tags is not None:
        group.tags = _tags_to_csv(data.tags)
    if "sync_group" in data.model_fields_set:
        group.sync_group = data.sync_group
    db.commit()
    db.refresh(group)
    return group


def delete_screen_group(db: Session, group: models.ScreenGroup) -> None:
    """Remove um grupo de telas."""
    db.delete(group)
    db.commit()


def resolve_group_screens(
    db: Session, group: models.ScreenGroup
) -> list[models.Screen]:
    """Resolve as telas pertencentes a um grupo estático ou dinâmico."""
    stmt = select(models.Screen)
    if group.company_id is not None:
        stmt = stmt.where(models.Screen.company_id == group.company_id)
    if group.mode == "dynamic":
        tags = _split_csv_tags(group.tags)
        for tag in tags:
            stmt = stmt.where(models.Screen.tags.ilike(f"%{tag}%"))
        return list(db.scalars(stmt.order_by(models.Screen.name)))
    ids = _json_to_ints(group.screen_ids)
    if not ids:
        return []
    stmt = stmt.where(models.Screen.id.in_(ids))
    return list(db.scalars(stmt.order_by(models.Screen.name)))


def screen_group_count(db: Session, group: models.ScreenGroup) -> int:
    """Conta telas resolvidas de um grupo."""
    return len(resolve_group_screens(db, group))


def group_names_for_screen(
    db: Session, screen: models.Screen, groups: list[models.ScreenGroup] | None = None
) -> list[str]:
    """Lista grupos aos quais uma tela pertence."""
    groups = groups if groups is not None else list_screen_groups(db, company_id=screen.company_id)
    names: list[str] = []
    screen_tags = set(_split_csv_tags(screen.tags))
    for group in groups:
        if group.mode == "dynamic":
            tags = set(_split_csv_tags(group.tags))
            if tags and tags.issubset(screen_tags):
                names.append(group.name)
        elif screen.id in _json_to_ints(group.screen_ids):
            names.append(group.name)
    return names


# --------------------------------------------------------------------------- #
# P6: campanhas e limites de exibicao
# --------------------------------------------------------------------------- #
def list_campaigns(
    db: Session, *, company_id: int | None = None
) -> list[models.Campaign]:
    """Lista campanhas do escopo atual."""
    stmt = select(models.Campaign)
    if company_id is not None:
        stmt = stmt.where(models.Campaign.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.Campaign.priority.desc(), models.Campaign.name)))


def get_campaign(db: Session, campaign_id: int) -> models.Campaign | None:
    """Busca campanha por ID."""
    return db.get(models.Campaign, campaign_id)


def create_campaign(
    db: Session, data: schemas.CampaignCreate, *, company_id: int | None = None
) -> models.Campaign:
    """Cria campanha P6."""
    campaign = models.Campaign(
        name=data.name,
        playlist_id=data.playlist_id,
        mode=data.mode,
        screen_ids=_ints_to_json(data.screen_ids),
        screen_group_ids=_ints_to_json(data.screen_group_ids),
        zone_ids=_ints_to_json(data.zone_ids),
        start_at=data.start_at,
        end_at=data.end_at,
        priority=data.priority,
        enabled=data.enabled,
        max_plays_per_hour=data.max_plays_per_hour,
        company_id=company_id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def update_campaign(
    db: Session, campaign: models.Campaign, data: schemas.CampaignUpdate
) -> models.Campaign:
    """Atualiza campanha P6."""
    if data.name is not None:
        campaign.name = data.name
    if data.playlist_id is not None:
        campaign.playlist_id = data.playlist_id
    if data.mode is not None:
        campaign.mode = data.mode
    if data.screen_ids is not None:
        campaign.screen_ids = _ints_to_json(data.screen_ids)
    if data.screen_group_ids is not None:
        campaign.screen_group_ids = _ints_to_json(data.screen_group_ids)
    if data.zone_ids is not None:
        campaign.zone_ids = _ints_to_json(data.zone_ids)
    if "start_at" in data.model_fields_set:
        campaign.start_at = data.start_at
    if "end_at" in data.model_fields_set:
        campaign.end_at = data.end_at
    if data.priority is not None:
        campaign.priority = data.priority
    if data.enabled is not None:
        campaign.enabled = data.enabled
    if "max_plays_per_hour" in data.model_fields_set:
        campaign.max_plays_per_hour = data.max_plays_per_hour
    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(db: Session, campaign: models.Campaign) -> None:
    """Remove campanha."""
    db.delete(campaign)
    db.commit()


def play_count_since(
    db: Session, *, screen_slug: str, media_id: int, since: datetime
) -> int:
    """Conta exibicoes de uma midia em uma tela desde um instante."""
    stmt = select(func.count()).select_from(models.PlayEvent).where(
        models.PlayEvent.screen_slug == screen_slug,
        models.PlayEvent.media_id == media_id,
        models.PlayEvent.played_at >= since,
    )
    return int(db.scalar(stmt) or 0)


def create_player_command(
    db: Session,
    screen: models.Screen,
    data: schemas.PlayerCommandCreate,
    *,
    requested_by: str | None = None,
) -> models.PlayerCommand:
    """Cria um comando enfileirado para uma tela."""
    command = models.PlayerCommand(
        screen_id=screen.id,
        company_id=screen.company_id,
        command_type=data.command_type,
        payload=_dict_to_json(data.payload),
        requested_by=requested_by,
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def get_player_command(db: Session, command_id: int) -> models.PlayerCommand | None:
    """Busca um comando por ID."""
    return db.get(models.PlayerCommand, command_id)


def list_player_commands(
    db: Session,
    *,
    screen_id: int | None = None,
    company_id: int | None = None,
    limit: int = 100,
) -> list[models.PlayerCommand]:
    """Lista comandos recentes."""
    stmt = select(models.PlayerCommand)
    if screen_id is not None:
        stmt = stmt.where(models.PlayerCommand.screen_id == screen_id)
    if company_id is not None:
        stmt = stmt.where(models.PlayerCommand.company_id == company_id)
    return list(
        db.scalars(stmt.order_by(models.PlayerCommand.created_at.desc()).limit(limit))
    )


def mark_command_sent(db: Session, command: models.PlayerCommand) -> models.PlayerCommand:
    """Marca um comando como enviado ao player."""
    command.status = "sent"
    command.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(command)
    return command


def complete_player_command(
    db: Session,
    command: models.PlayerCommand,
    *,
    status: str,
    result: str | None = None,
    result_path: str | None = None,
) -> models.PlayerCommand:
    """Registra o resultado de um comando."""
    command.status = status
    command.result = result
    command.result_path = result_path
    command.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(command)
    return command


def open_command_count(db: Session, screen_id: int) -> int:
    """Conta comandos ainda não finalizados de uma tela."""
    return int(
        db.scalar(
            select(func.count())
            .select_from(models.PlayerCommand)
            .where(
                models.PlayerCommand.screen_id == screen_id,
                models.PlayerCommand.status.in_(("queued", "sent")),
            )
        )
        or 0
    )


def get_offline_alert(db: Session, screen_id: int) -> models.OfflineAlert | None:
    """Busca o estado de alerta offline de uma tela."""
    return db.scalar(
        select(models.OfflineAlert).where(models.OfflineAlert.screen_id == screen_id)
    )


def set_offline_alert_state(
    db: Session, screen: models.Screen, *, is_offline: bool, alerted: bool = False
) -> models.OfflineAlert:
    """Atualiza o estado de alerta offline de uma tela."""
    alert = get_offline_alert(db, screen.id)
    if alert is None:
        alert = models.OfflineAlert(screen_id=screen.id, company_id=screen.company_id)
        db.add(alert)
    alert.is_offline = is_offline
    if alerted:
        alert.last_alert_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


def delete_screen(db: Session, screen: models.Screen) -> None:
    """Remove uma tela e suas zonas/agendamentos."""
    db.delete(screen)
    db.commit()


def touch_screen_seen(db: Session, screen: models.Screen) -> None:
    """Atualiza o ``last_seen`` da tela (heartbeat do player)."""
    screen.last_seen = datetime.now(timezone.utc)
    db.commit()


def get_zone(db: Session, zone_id: int) -> models.Zone | None:
    """Busca uma zona por ID com agendamentos carregados."""
    return db.scalar(
        select(models.Zone)
        .options(selectinload(models.Zone.schedules))
        .where(models.Zone.id == zone_id)
    )


def create_zone(
    db: Session, screen: models.Screen, data: schemas.ZoneCreate
) -> models.Zone:
    """Cria uma zona em uma tela."""
    zone = models.Zone(screen_id=screen.id, **data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def update_zone(db: Session, zone: models.Zone, data: schemas.ZoneUpdate) -> models.Zone:
    """Atualiza uma zona (parcial)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone


def delete_zone(db: Session, zone: models.Zone) -> None:
    """Remove uma zona e seus agendamentos."""
    db.delete(zone)
    db.commit()


def get_overlay(db: Session, overlay_id: int) -> models.Overlay | None:
    """Busca um overlay por ID."""
    return db.scalar(select(models.Overlay).where(models.Overlay.id == overlay_id))


def create_overlay(
    db: Session, screen: models.Screen, data: schemas.OverlayCreate
) -> models.Overlay:
    """Cria um overlay (HUD) vinculado a uma tela."""
    overlay = models.Overlay(screen_id=screen.id, **data.model_dump())
    db.add(overlay)
    db.commit()
    db.refresh(overlay)
    return overlay


def update_overlay(
    db: Session, overlay: models.Overlay, data: schemas.OverlayUpdate
) -> models.Overlay:
    """Atualiza campos de um overlay (apenas os enviados)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(overlay, field, value)
    db.commit()
    db.refresh(overlay)
    return overlay


def delete_overlay(db: Session, overlay: models.Overlay) -> None:
    """Remove um overlay de uma tela."""
    db.delete(overlay)
    db.commit()


def get_schedule(db: Session, schedule_id: int) -> models.Schedule | None:
    """Busca um agendamento por ID."""
    return db.get(models.Schedule, schedule_id)


def create_schedule(
    db: Session, zone: models.Zone, data: schemas.ScheduleCreate
) -> models.Schedule:
    """Cria um agendamento para uma zona."""
    schedule = models.Schedule(zone_id=zone.id, **data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(
    db: Session, schedule: models.Schedule, data: schemas.ScheduleUpdate
) -> models.Schedule:
    """Atualiza um agendamento (parcial)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: models.Schedule) -> None:
    """Remove um agendamento."""
    db.delete(schedule)
    db.commit()


def resolve_active_playlist_id(zone: models.Zone, now: datetime) -> int | None:
    """Resolve qual playlist deve tocar em uma zona em um dado instante.

    Avalia os agendamentos por dia da semana, faixa de horário e, quando
    definida, faixa de datas (campanhas). Em sobreposição, vence a maior
    ``priority``. Sem agendamento ativo, usa ``default_playlist_id``.

    Args:
        zone: zona com agendamentos carregados.
        now: instante de referência (timezone-aware, no fuso da tela).

    Returns:
        int | None: ID da playlist ativa, ou None se não houver.
    """
    minute_of_day = now.hour * 60 + now.minute
    weekday = now.weekday()  # 0=segunda … 6=domingo
    today = now.date()

    best: models.Schedule | None = None
    for schedule in zone.schedules:
        days = {
            int(part)
            for part in schedule.days_of_week.split(",")
            if part.strip().isdigit()
        }
        if weekday not in days:
            continue
        if not (schedule.start_minute <= minute_of_day < schedule.end_minute):
            continue
        if schedule.start_date is not None and today < schedule.start_date:
            continue
        if schedule.end_date is not None and today > schedule.end_date:
            continue
        if best is None or schedule.priority > best.priority:
            best = schedule

    if best is not None:
        return best.playlist_id
    return zone.default_playlist_id


# --------------------------------------------------------------------------- #
# Proof-of-play (eventos de reprodução)
# --------------------------------------------------------------------------- #
def record_play_events(
    db: Session,
    *,
    screen_slug: str,
    events: list[schemas.PlayEventCreate],
    company_id: int | None = None,
) -> int:
    """Persiste um lote de eventos de reprodução reportados pelo player.

    Returns:
        int: quantidade de eventos gravados.
    """
    screen = get_screen_by_slug(db, screen_slug)
    if screen is not None and not getattr(screen, "collect_stats", True):
        return 0
    media_cache: dict[int, bool] = {}
    filtered: list[schemas.PlayEventCreate] = []
    for event in events:
        if event.media_id is not None:
            if event.media_id not in media_cache:
                media = get_media(db, event.media_id)
                media_cache[event.media_id] = bool(
                    media is None or getattr(media, "collect_stats", True)
                )
            if not media_cache[event.media_id]:
                continue
        filtered.append(event)
    rows = [
        models.PlayEvent(
            screen_slug=screen_slug,
            company_id=company_id,
            zone_id=event.zone_id,
            media_id=event.media_id,
            media_name=event.media_name,
            media_type=event.media_type,
            duration_seconds=event.duration_seconds,
        )
        for event in filtered
    ]
    if rows:
        db.add_all(rows)
        db.commit()
    return len(rows)


def proof_of_play(
    db: Session,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    screen_slug: str | None = None,
    company_id: int | None = None,
    limit: int = 100,
) -> list[schemas.ProofOfPlayRow]:
    """Agrega eventos de reprodução por mídia (contagem e tempo total).

    Quando ``company_id`` é informado, considera apenas os eventos daquela
    empresa (segmentação multiempresa do proof-of-play).
    """
    stmt = select(
        models.PlayEvent.media_id,
        models.PlayEvent.media_name,
        func.count().label("plays"),
        func.coalesce(func.sum(models.PlayEvent.duration_seconds), 0).label("secs"),
    )
    if since is not None:
        stmt = stmt.where(models.PlayEvent.played_at >= since)
    if until is not None:
        stmt = stmt.where(models.PlayEvent.played_at <= until)
    if screen_slug is not None:
        stmt = stmt.where(models.PlayEvent.screen_slug == screen_slug)
    if company_id is not None:
        stmt = stmt.where(models.PlayEvent.company_id == company_id)
    stmt = (
        stmt.group_by(models.PlayEvent.media_id, models.PlayEvent.media_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        schemas.ProofOfPlayRow(
            media_id=row[0],
            media_name=row[1] or "(sem nome)",
            plays=int(row[2]),
            total_seconds=int(row[3]),
        )
        for row in rows
    ]


def proof_of_play_details(
    db: Session,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    screen_slug: str | None = None,
    company_id: int | None = None,
    limit: int = 5000,
) -> list[schemas.ProofOfPlayDetailRow]:
    """Lista eventos detalhados para exportacao CSV/BI."""
    stmt = select(models.PlayEvent)
    if since is not None:
        stmt = stmt.where(models.PlayEvent.played_at >= since)
    if until is not None:
        stmt = stmt.where(models.PlayEvent.played_at <= until)
    if screen_slug is not None:
        stmt = stmt.where(models.PlayEvent.screen_slug == screen_slug)
    if company_id is not None:
        stmt = stmt.where(models.PlayEvent.company_id == company_id)
    rows = list(db.scalars(stmt.order_by(models.PlayEvent.played_at.desc()).limit(limit)))
    return [
        schemas.ProofOfPlayDetailRow(
            played_at=row.played_at,
            screen_slug=row.screen_slug,
            zone_id=row.zone_id,
            media_id=row.media_id,
            media_name=row.media_name,
            media_type=row.media_type,
            duration_seconds=row.duration_seconds,
        )
        for row in rows
    ]


def proof_of_play_summary(
    db: Session,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    screen_slug: str | None = None,
    company_id: int | None = None,
) -> schemas.ProofOfPlaySummary:
    """Resumo executivo do proof-of-play."""
    stmt = select(
        func.count().label("plays"),
        func.coalesce(func.sum(models.PlayEvent.duration_seconds), 0).label("secs"),
        func.count(func.distinct(models.PlayEvent.media_id)).label("media"),
        func.count(func.distinct(models.PlayEvent.screen_slug)).label("screens"),
    ).select_from(models.PlayEvent)
    if since is not None:
        stmt = stmt.where(models.PlayEvent.played_at >= since)
    if until is not None:
        stmt = stmt.where(models.PlayEvent.played_at <= until)
    if screen_slug is not None:
        stmt = stmt.where(models.PlayEvent.screen_slug == screen_slug)
    if company_id is not None:
        stmt = stmt.where(models.PlayEvent.company_id == company_id)
    row = db.execute(stmt).one()
    return schemas.ProofOfPlaySummary(
        total_plays=int(row[0] or 0),
        total_seconds=int(row[1] or 0),
        unique_media=int(row[2] or 0),
        unique_screens=int(row[3] or 0),
    )


def list_report_schedules(
    db: Session, *, company_id: int | None = None
) -> list[models.ReportSchedule]:
    """Lista relatorios agendados."""
    stmt = select(models.ReportSchedule)
    if company_id is not None:
        stmt = stmt.where(models.ReportSchedule.company_id == company_id)
    return list(db.scalars(stmt.order_by(models.ReportSchedule.name)))


def get_report_schedule(db: Session, schedule_id: int) -> models.ReportSchedule | None:
    """Busca relatorio agendado."""
    return db.get(models.ReportSchedule, schedule_id)


def create_report_schedule(
    db: Session, data: schemas.ReportScheduleCreate, *, company_id: int | None = None
) -> models.ReportSchedule:
    """Cria relatorio agendado."""
    row = models.ReportSchedule(
        name=data.name,
        recipients=data.recipients,
        frequency=data.frequency,
        hour=data.hour,
        days=data.days,
        screen_slug=data.screen_slug,
        enabled=data.enabled,
        company_id=company_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_report_schedule(
    db: Session, row: models.ReportSchedule, data: schemas.ReportScheduleUpdate
) -> models.ReportSchedule:
    """Atualiza relatorio agendado."""
    for field in ("name", "recipients", "frequency", "hour", "days", "screen_slug", "enabled"):
        if field in data.model_fields_set:
            setattr(row, field, getattr(data, field))
    db.commit()
    db.refresh(row)
    return row


def mark_report_sent(db: Session, row: models.ReportSchedule, when: datetime) -> None:
    """Registra envio de relatorio."""
    row.last_sent_at = when
    db.commit()


def delete_report_schedule(db: Session, row: models.ReportSchedule) -> None:
    """Remove relatorio agendado."""
    db.delete(row)
    db.commit()


def purge_play_events(db: Session, *, older_than_days: int) -> int:
    """Remove eventos de reprodução mais antigos que ``older_than_days``."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    result = db.execute(
        delete(models.PlayEvent).where(models.PlayEvent.played_at < cutoff)
    )
    db.commit()
    return int(result.rowcount or 0)


# --------------------------------------------------------------------------- #
# P3: biblioteca (busca por nome+tipo e limpeza de nao utilizadas)
# --------------------------------------------------------------------------- #
def find_media_by_name_type(
    db: Session, *, name: str, media_type: models.MediaType, company_id: int | None = None
) -> models.Media | None:
    """Busca a primeira midia com mesmo nome e tipo (usado no import de playlist)."""
    stmt = select(models.Media).where(
        models.Media.name == name, models.Media.type == media_type
    )
    if company_id is not None:
        stmt = stmt.where(models.Media.company_id == company_id)
    return db.scalars(stmt).first()


def list_unused_media(
    db: Session, *, company_id: int | None = None
) -> list[models.Media]:
    """Lista midias nao referenciadas por nenhum item de playlist nem como
    audio de fundo de telas (candidatas a limpeza)."""
    used_ids = set(db.scalars(select(models.PlaylistItem.media_id)).all())
    used_ids.update(
        x
        for x in db.scalars(select(models.Screen.background_audio_id)).all()
        if x is not None
    )
    stmt = select(models.Media)
    if company_id is not None:
        stmt = stmt.where(models.Media.company_id == company_id)
    rows = list(db.scalars(stmt))
    return [m for m in rows if m.id not in used_ids]
