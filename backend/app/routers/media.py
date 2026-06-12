"""Endpoints de gerenciamento de mídias.

Suporta dois fluxos de criação:

* ``POST /api/media`` — cria mídia textual/HTML/URL (JSON).
* ``POST /api/media/upload`` — envia arquivo (imagem/vídeo) via multipart.

Após qualquer alteração, todas as telas são notificadas para recarregar.
Todas as rotas exigem autenticação (``require_auth`` no nível do roteador).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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


@router.get("", response_model=list[schemas.MediaRead])
def list_media(db: Session = Depends(get_db)) -> list[models.Media]:
    """Lista todas as mídias cadastradas."""
    return crud.list_media(db)


@router.post("", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED)
async def create_media(
    data: schemas.MediaCreate, db: Session = Depends(get_db)
) -> models.Media:
    """Cria uma mídia de texto, HTML ou URL (sem upload de arquivo)."""
    if data.type in (models.MediaType.image, models.MediaType.video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagens e vídeos devem ser enviados via /api/media/upload.",
        )
    media = crud.create_media(db, data)
    await notify_all_screens(db, reason="media-created")
    return media


@router.post(
    "/upload", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> models.Media:
    """Recebe um arquivo (imagem/vídeo), salva em disco e registra a mídia.

    O arquivo é gravado com um nome único (UUID + extensão original) dentro do
    diretório de mídia configurado, e fica acessível publicamente em ``/media``.

    Raises:
        HTTPException: extensão não suportada ou arquivo acima do limite.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in _IMAGE_EXTS:
        media_type = models.MediaType.image
    elif suffix in _VIDEO_EXTS:
        media_type = models.MediaType.video
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensão não suportada: {suffix or '(desconhecida)'}",
        )

    payload = await file.read()
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {settings.max_upload_mb} MB.",
        )

    unique_name = f"{uuid.uuid4().hex}{suffix}"
    destination = settings.media_dir / unique_name
    destination.write_bytes(payload)

    media = crud.create_uploaded_media(db, name, media_type, unique_name)
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
