"""Endpoints de DataSets para widgets avancados (P5)."""

from __future__ import annotations

import csv
import io
import json
import urllib.request
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_auth, scope_can_access
from ..database import get_db
from ..realtime import notify_all_screens

router = APIRouter(
    prefix="/api/datasets",
    tags=["datasets"],
    dependencies=[Depends(require_auth)],
)

_TIMEOUT = 8
_MAX_BYTES = 1_000_000
_USER_AGENT = "tvMedia/1.0"


def _columns_from_rows(rows: list[dict]) -> list[dict]:
    """Deduz colunas preservando a primeira aparicao de cada chave."""
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(str(key))
    return [{"key": key, "label": key} for key in keys]


def _parse_csv(csv_text: str, delimiter: str = ",") -> tuple[list[dict], list[dict]]:
    """Converte CSV colado em linhas/colunas JSON."""
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
    rows = [{str(k): (v if v is not None else "") for k, v in row.items()} for row in reader]
    return rows, _columns_from_rows(rows)


def _fetch_json_rows(url: str) -> tuple[list[dict], list[dict]]:
    """Baixa JSON remoto aceitando lista direta ou objeto com chave rows/items."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL remota deve usar http(s).")
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
            payload = resp.read(_MAX_BYTES).decode("utf-8", errors="replace")
        data = json.loads(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Falha ao buscar JSON remoto.") from exc
    if isinstance(data, dict):
        data = data.get("rows") or data.get("items") or []
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON remoto deve conter uma lista.")
    rows = [item for item in data if isinstance(item, dict)]
    return rows, _columns_from_rows(rows)


def _read_dataset(dataset: models.DataSet) -> schemas.DataSetRead:
    """Serializa DataSet com campos JSON normalizados."""
    return schemas.DataSetRead.model_validate(dataset)


@router.get("", response_model=list[schemas.DataSetRead])
def list_datasets(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> list[schemas.DataSetRead]:
    """Lista DataSets do escopo atual."""
    return [
        _read_dataset(dataset)
        for dataset in crud.list_datasets(db, company_id=scope.company_id)
    ]


@router.post("", response_model=schemas.DataSetRead, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    data: schemas.DataSetCreate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.DataSetRead:
    """Cria um DataSet manual, CSV ou JSON remoto."""
    dataset = crud.create_dataset(db, data, company_id=scope.write_company_id)
    await notify_all_screens(db, reason="dataset-created")
    return _read_dataset(dataset)


@router.get("/{dataset_id}", response_model=schemas.DataSetRead)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.DataSetRead:
    """Detalha um DataSet."""
    dataset = crud.get_dataset(db, dataset_id)
    if dataset is None or not scope_can_access(scope, dataset.company_id):
        raise HTTPException(status_code=404, detail="DataSet nao encontrado.")
    return _read_dataset(dataset)


@router.patch("/{dataset_id}", response_model=schemas.DataSetRead)
async def update_dataset(
    dataset_id: int,
    data: schemas.DataSetUpdate,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.DataSetRead:
    """Atualiza um DataSet."""
    dataset = crud.get_dataset(db, dataset_id)
    if dataset is None or not scope_can_access(scope, dataset.company_id):
        raise HTTPException(status_code=404, detail="DataSet nao encontrado.")
    dataset = crud.update_dataset(db, dataset, data)
    await notify_all_screens(db, reason="dataset-updated")
    return _read_dataset(dataset)


@router.post("/{dataset_id}/import-csv", response_model=schemas.DataSetRead)
async def import_csv(
    dataset_id: int,
    data: schemas.DataSetImportCsv,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.DataSetRead:
    """Substitui linhas do DataSet a partir de CSV colado."""
    dataset = crud.get_dataset(db, dataset_id)
    if dataset is None or not scope_can_access(scope, dataset.company_id):
        raise HTTPException(status_code=404, detail="DataSet nao encontrado.")
    rows, columns = _parse_csv(data.csv_text, data.delimiter)
    dataset = crud.replace_dataset_rows(
        db, dataset, rows=rows, columns=columns, status="ok", note="CSV importado."
    )
    await notify_all_screens(db, reason="dataset-imported")
    return _read_dataset(dataset)


@router.post("/{dataset_id}/refresh", response_model=schemas.DataSetRead)
async def refresh_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> schemas.DataSetRead:
    """Atualiza DataSet do tipo JSON remoto."""
    dataset = crud.get_dataset(db, dataset_id)
    if dataset is None or not scope_can_access(scope, dataset.company_id):
        raise HTTPException(status_code=404, detail="DataSet nao encontrado.")
    if dataset.kind != "json_remote" or not dataset.source_url:
        raise HTTPException(status_code=400, detail="DataSet nao e JSON remoto.")
    try:
        rows, columns = _fetch_json_rows(dataset.source_url)
    except HTTPException as exc:
        crud.mark_dataset_refresh(db, dataset, status="failed", note=str(exc.detail))
        raise
    dataset = crud.replace_dataset_rows(
        db, dataset, rows=rows, columns=columns, status="ok", note="JSON remoto atualizado."
    )
    await notify_all_screens(db, reason="dataset-refreshed")
    return _read_dataset(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(get_scope),
) -> None:
    """Remove um DataSet."""
    dataset = crud.get_dataset(db, dataset_id)
    if dataset is None or not scope_can_access(scope, dataset.company_id):
        raise HTTPException(status_code=404, detail="DataSet nao encontrado.")
    crud.delete_dataset(db, dataset)
    await notify_all_screens(db, reason="dataset-deleted")
