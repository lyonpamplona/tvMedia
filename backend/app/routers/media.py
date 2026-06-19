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
from urllib.parse import urlparse

import requests

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..config import settings
from ..database import SessionLocal, get_db
from .. import media_processing
from ..realtime import notify_all_screens

router = APIRouter(
    prefix="/api/media", tags=["media"], dependencies=[Depends(require_auth)]
)

# Extensões aceitas por tipo de upload.
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
_VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".mkv"}
_AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".oga", ".wav", ".flac"}

# Fallback de extensao por content-type quando a URL nao traz sufixo (P3).
_EXT_BY_MIME = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp", "image/svg+xml": ".svg",
    "video/mp4": ".mp4", "video/webm": ".webm", "video/ogg": ".ogg",
    "video/quicktime": ".mov", "video/x-matroska": ".mkv",
    "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/aac": ".aac",
    "audio/ogg": ".oga", "audio/wav": ".wav", "audio/x-wav": ".wav",
    "audio/flac": ".flac",
}

# Prefixos de content-type aceitos por tipo (defesa adicional além da extensão).
_IMAGE_MIME_PREFIX = "image/"
_VIDEO_MIME_PREFIX = "video/"
_AUDIO_MIME_PREFIX = "audio/"

# Tamanho do bloco de leitura/gravação no upload (1 MB), para uso de memória
# praticamente constante mesmo com vídeos grandes (ex.: Raspberry Pi 4).
_UPLOAD_CHUNK_SIZE = 1024 * 1024


def _validate_folder(db: Session, folder_id: int | None, scope: Scope) -> None:
    """Garante que a pasta informada existe e pertence ao escopo atual."""
    if folder_id is None:
        return
    folder = crud.get_folder(db, folder_id)
    if folder is None or not scope_can_access(scope, folder.company_id):
        raise HTTPException(status_code=400, detail="Pasta inexistente.")


def _process_media_in_background(media_id: int) -> None:
    """Processa (reescala/transcodifica) uma midia fora do ciclo da requisicao.

    Abre uma sessao propria de banco (a sessao da requisicao ja foi fechada).
    Nunca propaga excecoes: falhas viram status 'failed' na propria midia, para
    nao derrubar o worker em segundo plano.
    """
    db = SessionLocal()
    try:
        media = crud.get_media(db, media_id)
        if media is None or media.type not in (
            models.MediaType.image,
            models.MediaType.video,
        ):
            return
        if not media.path:
            crud.set_media_processing(db, media, status="skipped", note="Sem arquivo.")
            return
        crud.set_media_processing(db, media, status="processing")
        result = media_processing.process_media_file(
            settings.media_dir, media.path, media.type
        )
        crud.set_media_processing(
            db,
            media,
            status=result.get("status", "done"),
            note=result.get("note"),
            width=result.get("width"),
            height=result.get("height"),
            optimized_path=result.get("optimized_path"),
            poster_path=result.get("poster_path"),
        )
    except Exception as exc:  # pragma: no cover - defensivo
        try:
            media = crud.get_media(db, media_id)
            if media is not None:
                crud.set_media_processing(
                    db, media, status="failed", note=str(exc)[:480]
                )
        except Exception:
            pass
    finally:
        db.close()


async def _notify_media_processed() -> None:
    """Avisa todas as telas para recarregarem apos o processamento concluir."""
    db = SessionLocal()
    try:
        await notify_all_screens(db, reason="media-processed")
    finally:
        db.close()


def _schedule_processing(
    background_tasks: BackgroundTasks, media: models.Media
) -> None:
    """Agenda o processamento de uma midia de imagem/video, se habilitado."""
    if not settings.media_processing_enabled:
        return
    if media.type not in (models.MediaType.image, models.MediaType.video):
        return
    background_tasks.add_task(_process_media_in_background, media.id)
    background_tasks.add_task(_notify_media_processed)


@router.get("", response_model=list[schemas.MediaRead])
def list_media(
    folder_id: int | None = Query(None, description="Filtra por pasta (0 = sem pasta)."),
    tag: str | None = Query(None, description="Filtra por tag."),
    q: str | None = Query(None, description="Busca por nome."),
    limit: int | None = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[models.Media]:
    """Lista mídias da empresa em foco. Sem filtros, retorna todas dela."""
    if folder_id is None and tag is None and q is None and limit is None:
        return crud.list_media(db, company_id=scope.company_id)
    rows, _ = crud.list_media_paginated(
        db,
        limit=limit or 50,
        offset=offset,
        folder_id=folder_id,
        tag=tag,
        search=q,
        company_id=scope.company_id,
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
    scope: Scope = Depends(get_scope),
) -> schemas.Page[schemas.MediaRead]:
    """Versão paginada da listagem (total + itens da página)."""
    rows, total = crud.list_media_paginated(
        db, limit=limit, offset=offset, folder_id=folder_id, tag=tag, search=q,
        company_id=scope.company_id,
    )
    items = [schemas.MediaRead.model_validate(row) for row in rows]
    return schemas.Page[schemas.MediaRead](
        total=total, limit=limit, offset=offset, items=items
    )


@router.post("", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED)
async def create_media(
    data: schemas.MediaCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Media:
    """Cria uma mídia sem upload (texto, HTML, URL, embed, youtube)."""
    if data.type in (
        models.MediaType.image,
        models.MediaType.video,
        models.MediaType.audio,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagens, vídeos e áudios devem ser enviados via /api/media/upload.",
        )
    _validate_folder(db, data.folder_id, scope)
    media = crud.create_media(
        db,
        name=data.name,
        media_type=data.type,
        source_url=data.source_url,
        content=data.content,
        tags=data.tags,
        folder_id=data.folder_id,
        company_id=scope.write_company_id,
        expires_at=data.expires_at,
        collect_stats=data.collect_stats,
    )
    await notify_all_screens(db, reason="media-created")
    return media


@router.post("/bulk", response_model=list[schemas.MediaRead], status_code=201)
async def bulk_create_media(
    data: schemas.BulkUrlRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> list[models.Media]:
    """Importa várias mídias sem arquivo de uma só vez.

    Útil para cadastrar listas de URLs/embeds (ex.: vários vídeos do YouTube).
    Itens de imagem/vídeo (que exigem arquivo) são rejeitados.
    """
    created: list[models.Media] = []
    for item in data.items:
        if item.type in (
            models.MediaType.image,
            models.MediaType.video,
            models.MediaType.audio,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Importação em massa não aceita imagens/vídeos/áudios.",
            )
        _validate_folder(db, item.folder_id, scope)
        created.append(
            crud.create_media(
                db,
                name=item.name,
                media_type=item.type,
                source_url=item.source_url,
                content=item.content,
                tags=item.tags,
                folder_id=item.folder_id,
                company_id=scope.write_company_id,
                expires_at=item.expires_at,
                collect_stats=True,
            )
        )
    if created:
        await notify_all_screens(db, reason="media-bulk-created")
    return created


@router.post(
    "/upload", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    file: UploadFile = File(...),
    folder_id: int | None = Form(None),
    tags: str | None = Form(None),
    width: int | None = Form(None),
    height: int | None = Form(None),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
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
    elif suffix in _AUDIO_EXTS:
        media_type = models.MediaType.audio
        if content_type and not content_type.startswith(_AUDIO_MIME_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O conteúdo enviado não parece ser um áudio.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensão não suportada: {suffix or '(desconhecida)'}",
        )

    _validate_folder(db, folder_id, scope)

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
        company_id=scope.write_company_id,
        width=width,
        height=height,
    )
    _schedule_processing(background_tasks, media)
    await notify_all_screens(db, reason="media-uploaded")
    return media


@router.post("/{media_id}/file", response_model=schemas.MediaRead)
async def replace_media_file(
    media_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Media:
    """Substitui o arquivo de uma mídia de imagem/vídeo existente.

    Mantém o registro (id, nome, pasta, tags) e troca apenas o arquivo,
    apagando o antigo após gravar o novo. Valida extensão e content-type.
    """
    media = crud.get_media(db, media_id)
    if media is None or not scope_can_access(scope, media.company_id):
        raise HTTPException(status_code=404, detail="Mídia não encontrada.")
    if media.type not in (models.MediaType.image, models.MediaType.video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas mídias de imagem/vídeo possuem arquivo.",
        )
    suffix = Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "").lower()
    if media.type == models.MediaType.image:
        if suffix not in _IMAGE_EXTS:
            raise HTTPException(status_code=400, detail=f"Extensão não suportada: {suffix or '(desconhecida)'}")
        if content_type and not content_type.startswith(_IMAGE_MIME_PREFIX):
            raise HTTPException(status_code=400, detail="O conteúdo enviado não parece ser uma imagem.")
    else:
        if suffix not in _VIDEO_EXTS:
            raise HTTPException(status_code=400, detail=f"Extensão não suportada: {suffix or '(desconhecida)'}")
        if content_type and not content_type.startswith(_VIDEO_MIME_PREFIX):
            raise HTTPException(status_code=400, detail="O conteúdo enviado não parece ser um vídeo.")

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

    old_path = media.path
    old_optimized = media.optimized_path
    old_poster = media.poster_path
    media.path = unique_name
    # Invalida derivados do arquivo anterior e reenfileira o processamento.
    media.optimized_path = None
    media.poster_path = None
    media.width = None
    media.height = None
    media.processing_status = "pending"
    media.processing_note = None
    db.add(media)
    db.commit()
    db.refresh(media)
    if old_path:
        (settings.media_dir / old_path).unlink(missing_ok=True)
    if old_optimized:
        (settings.media_dir / old_optimized).unlink(missing_ok=True)
    if old_poster:
        (settings.media_dir / old_poster).unlink(missing_ok=True)
    _schedule_processing(background_tasks, media)
    await notify_all_screens(db, reason="media-file-replaced")
    return media


@router.post("/{media_id}/process", response_model=schemas.MediaRead)
async def reprocess_media(
    media_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Media:
    """Reenfileira o processamento (reescala/transcodificacao) de uma midia.

    Util para gerar versoes otimizadas de midias antigas (enviadas antes do
    recurso) ou apos instalar Pillow/ffmpeg no servidor.
    """
    media = crud.get_media(db, media_id)
    if media is None or not scope_can_access(scope, media.company_id):
        raise HTTPException(status_code=404, detail="Midia nao encontrada.")
    if media.type not in (models.MediaType.image, models.MediaType.video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas imagens e videos podem ser processados.",
        )
    media = crud.set_media_processing(db, media, status="pending", note=None)
    _schedule_processing(background_tasks, media)
    return media


@router.patch("/{media_id}", response_model=schemas.MediaRead)
async def update_media(
    media_id: int,
    data: schemas.MediaUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Media:
    """Atualiza parcialmente uma mídia existente."""
    media = crud.get_media(db, media_id)
    if media is None or not scope_can_access(scope, media.company_id):
        raise HTTPException(status_code=404, detail="Mídia não encontrada.")
    if "folder_id" in data.model_fields_set:
        _validate_folder(db, data.folder_id, scope)
    media = crud.update_media(db, media, data)
    await notify_all_screens(db, reason="media-updated")
    return media


@router.post("/bulk-tags", response_model=schemas.BulkActionResult)
async def bulk_tag_media(
    data: schemas.BulkTagRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.BulkActionResult:
    """Adiciona tags a varias midias da empresa em foco."""
    rows: list[models.Media] = []
    for media_id in data.ids:
        media = crud.get_media(db, media_id)
        if media is not None and scope_can_access(scope, media.company_id):
            rows.append(media)
    updated = crud.bulk_tag_media(db, rows, data.tags)
    if updated:
        await notify_all_screens(db, reason="media-bulk-tagged")
    return schemas.BulkActionResult(updated=updated, ids=[m.id for m in rows])


@router.delete(
    "/{media_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove uma mídia e o arquivo associado (se houver)."""
    media = crud.get_media(db, media_id)
    if media is None or not scope_can_access(scope, media.company_id):
        raise HTTPException(status_code=404, detail="Mídia não encontrada.")

    if media.path:
        file_path = settings.media_dir / media.path
        file_path.unlink(missing_ok=True)

    crud.delete_media(db, media)
    await notify_all_screens(db, reason="media-deleted")


@router.post(
    "/import-url", response_model=schemas.MediaRead, status_code=status.HTTP_201_CREATED
)
async def import_media_from_url(
    background_tasks: BackgroundTasks,
    data: schemas.MediaUrlImport,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> models.Media:
    """Baixa um arquivo (imagem/video/audio) de uma URL e registra a midia.

    O download e feito no servidor, em blocos, respeitando o limite de
    tamanho. O tipo e deduzido pela extensao da URL ou pelo content-type.
    """
    _validate_folder(db, data.folder_id, scope)
    url = data.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="A URL deve comecar com http:// ou https://.")
    suffix = Path(urlparse(url).path).suffix.lower()
    try:
        resp = requests.get(
            url, stream=True, timeout=30,
            headers={"User-Agent": "tvMedia/1.0"},
        )
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - rede
        raise HTTPException(status_code=400, detail=f"Falha ao baixar a URL: {exc}")
    try:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if suffix not in (_IMAGE_EXTS | _VIDEO_EXTS | _AUDIO_EXTS):
            suffix = _EXT_BY_MIME.get(ctype, "")
        if suffix in _IMAGE_EXTS:
            media_type = models.MediaType.image
        elif suffix in _VIDEO_EXTS:
            media_type = models.MediaType.video
        elif suffix in _AUDIO_EXTS:
            media_type = models.MediaType.audio
        else:
            raise HTTPException(status_code=400, detail="Tipo de arquivo nao suportado para download por URL.")
        unique_name = f"{uuid.uuid4().hex}{suffix}"
        destination = settings.media_dir / unique_name
        max_bytes = settings.max_upload_bytes
        written = 0
        try:
            with destination.open("wb") as buffer:
                for chunk in resp.iter_content(_UPLOAD_CHUNK_SIZE):
                    if not chunk:
                        continue
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
        resp.close()
    media = crud.create_media(
        db,
        name=data.name,
        media_type=media_type,
        path=unique_name,
        tags=data.tags,
        folder_id=data.folder_id,
        company_id=scope.write_company_id,
        expires_at=data.expires_at,
    )
    _schedule_processing(background_tasks, media)
    await notify_all_screens(db, reason="media-url-imported")
    return media


@router.post("/purge-unused", response_model=schemas.PurgeResult)
async def purge_unused_media(
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.PurgeResult:
    """Remove midias nao usadas por nenhuma playlist nem como audio de fundo.

    Apaga tambem os arquivos derivados (original, otimizado e poster).
    """
    unused = crud.list_unused_media(db, company_id=scope.company_id)
    removed: list[int] = []
    for media in unused:
        for rel in (media.path, media.optimized_path, media.poster_path):
            if rel:
                (settings.media_dir / rel).unlink(missing_ok=True)
        removed.append(media.id)
        crud.delete_media(db, media)
    if removed:
        await notify_all_screens(db, reason="media-purged")
    return schemas.PurgeResult(deleted=len(removed), ids=removed)
