"""Endpoints de gerenciamento de mídias.

Fluxos de criação:

* ``POST /api/media`` — mídia textual/HTML/URL/embed/youtube (JSON).
* ``POST /api/media/upload`` — arquivo (imagem/vídeo) via multipart, com
  validação de extensão e de content-type e gravação em blocos.
* ``POST /api/media/bulk`` — importação em massa de itens sem arquivo.

Listagem com filtros opcionais (pasta, tag, busca) e paginação, mantendo
compatibilidade: sem parâmetros, retorna a lista completa. Após alterações,
todas as telas são notificadas. Todas as rotas exigem autenticação.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import require_auth
from ..config import settings
from ..database import get_db
from ..realtime import notify_all_screens

router = APIRouter(
    prefix="/api/media", tags=["media"], dependencies=[Depends(require_auth)]
)

# Extensões aceitas por tipo de upload.
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
_VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".mkv"}

# Prefixos de content-type aceitos por tipo (defesa adicional além da extensão).
_IMAGE_MIME_PREFIX = "image/"
_VIDEO_MIME_PREFIX = "video/"

# Tamanho do bloco de leitura/gravação no upload (1 MB), para uso de memória
# praticamente constante mesmo com vídeos grandes (ex.: Raspberry Pi 4).
_UPLOAD_CHUNK_SIZE = 1024 * 1024


def _validate_folder(db: Session, folder_id: int | None) -> None:
    """Garante que a pasta informada existe (quando informada)."""
    if folder_id is not None and crud.get_folder(db, folder_id) is None:
        raise HTTPException(status_code=400, detail="Pasta inexistente.")


@router.get("", response_model=list[schemas.MediaRead])
def list_media(
    folder_id: int | None = Query(None, description="Filtra por pasta (0 = sem pasta)."),
    tag: str | None = Query(None, description="Filtra por tag."),
    q: str | None = Query(None, description="Busca por nome."),
    limit: int | None = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[models.Media]:
    """Lista mídias. Sem filtros/paginação, retorna todas (compatível)."""
    if folder_id is None and tag is None and q is None and limit is None:
        return crud.list_media(db)
    rows, _ = crud.list_media_paginated(
        db,
        limit=limit or 50,
        offset=offset,
        folder_id=folder_id,
        tag=tag,
        search=q,
    )
    return rows


@router.get("/page", response_model=schemas.Page[schemas.MediaRead])
def list_media_page(
    folder_id: int | None = Query(None),
    tag: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> schemas.Page[schemas.MediaRead]:
    """Versão paginada da listagem (total + itens da página)."""
    rows, total = crud.list_media_paginated(
        db, limit=limit, offset=offset, folder_id=folder_id, tag=tag, search=q
    )
    items = [schemas.MediaRead.model_validate(row) for row in rows]
    return schemas.Page[schemas.MediaRead](
        total=total, limit=limit, offset=offset, items=items
    )


@router.post("", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED)
async def create_media(
    data: schemas.MediaCreate, db: Session = Depends(get_db)
) -> models.Media:
    """Cria uma mídia sem upload (texto, HTML, URL, embed, youtube)."""
    if data.type in (models.MediaType.image, models.MediaType.video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagens e vídeos devem ser enviados via /api/media/upload.",
        )
    _validate_folder(db, data.folder_id)
    media = crud.create_media(
        db,
        name=data.name,
        media_type=data.type,
        source_url=data.source_url,
        content=data.content,
        tags=data.tags,
        folder_id=data.folder_id,
    )
    await notify_all_screens(db, reason="media-created")
    return media


@router.post("/bulk", response_model=list[schemas.MediaRead], status_code=201)
async def bulk_create_media(
    data: schemas.BulkUrlRequest, db: Session = Depends(get_db)
) -> list[models.Media]:
    """Importa várias mídias sem arquivo de uma só vez.

    Útil para cadastrar listas de URLs/embeds (ex.: vários vídeos do YouTube).
    Itens de imagem/vídeo (que exigem arquivo) são rejeitados.
    """
    created: list[models.Media] = []
    for item in data.items:
        if item.type in (models.MediaType.image, models.MediaType.video):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Importação em massa não aceita imagens/vídeos.",
            )
        _validate_folder(db, item.folder_id)
        created.append(
            crud.create_media(
                db,
                name=item.name,
                media_type=item.type,
                source_url=item.source_url,
                content=item.content,
                tags=item.tags,
                folder_id=item.folder_id,
            )
        )
    if created:
        await notify_all_screens(db, reason="media-bulk-created")
    return created


@router.post(
    "/upload", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    name: str = Form(...),
    file: UploadFile = File(...),
    folder_id: int | None = Form(None),
    tags: str | None = Form(None),
    db: Session = Depends(get_db),
) -> models.Media:
    """Recebe um arquivo (imagem/vídeo), valida, salva e registra a mídia.

    Valida tanto a extensão quanto o content-type informado pelo cliente, e
    grava em blocos para manter o uso de memória baixo.

    Raises:
        HTTPException: extensão/tipo não suportados ou arquivo acima do limite.
    """
    suffix = Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "").lower()
    if suffix in _IMAGE_EXTS:
        media_type = models.MediaType.image
        if content_type and not content_type.startswith(_IMAGE_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O conteúdo enviado não parece ser uma imagem.",
            )
    elif suffix in _VIDEO_EXTS:
        media_type = models.MediaType.video
        if content_type and not content_type.startswith(_VIDEO_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O conteúdo enviado não parece ser um vídeo.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensão não suportada: {suffix or '(desconhecida)'}",
        )

    _validate_folder(db, folder_id)

    unique_name = f"{uuid.uuid4().hex}{suffix}"
    destination = settings.media_dir / unique_name
    max_bytes = settings.max_upload_bytes
    written = 0
    try:
        with destination.open("wb") as buffer:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Arquivo excede o limite de {settings.max_upload_mb} MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    tag_list = (
        [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    )
    media = crud.create_media(
        db,
        name=name,
        media_type=media_type,
        path=unique_name,
        tags=tag_list,
        folder_id=folder_id,
    )
    await notify_all_screens(db, reason="media-uploaded")
    return media


@router.patch("/{media_id}", response_model=schemas.MediaRead)
async def update_media(
    media_id: int, data: schemas.MediaUpdate, db: Session = Depends(get_db)
) -> models.Media:
    """Atualiza parcialmente uma mídia existente."""
    media = crud.get_media(db, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Mídia não encontrada.")
    if "folder_id" in data.model_fields_set:
        _validate_folder(db, data.folder_id)
    media = crud.update_media(db, media, data)
    await notify_all_screens(db, reason="media-updated")
    return media


@router.delete(
    "/{media_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_media(media_id: int, db: Session = Depends(get_db)) -> None:
    """Remove uma mídia e o arquivo associado (se houver)."""
    media = crud.get_media(db, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Mídia não encontrada.")

    if media.path:
        file_path = settings.media_dir / media.path
        file_path.unlink(missing_ok=True)

    crud.delete_media(db, media)
    await notify_all_screens(db, reason="media-deleted")
