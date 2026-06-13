"""Endpoints multi-tenant: gestao de empresas, branding e templates.

Divididos em tres roteadores:

* ``router`` (``/api/companies``) — CRUD de empresas e estatisticas. Restrito
  ao super administrador (gere todo o parque de empresas/clientes).
* ``branding_router`` (``/api/branding``) — marca da empresa em foco (nome,
  logo e cor), consumida pelo painel apos o login por qualquer usuario.
* ``templates_router`` (``/api/templates``) — catalogo de templates de tela
  (cenarios prontos) usados no assistente de criacao de telas.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import Scope, get_scope, require_super_admin
from ..config import settings
from ..database import get_db

router = APIRouter(
    prefix="/api/companies",
    tags=["companies"],
    dependencies=[Depends(require_super_admin)],
)
branding_router = APIRouter(tags=["branding"])
templates_router = APIRouter(tags=["templates"])

# Extensoes de imagem aceitas para o logo da empresa.
_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}

# Catalogo estatico de templates de tela (cenarios prontos por empresa).
_TEMPLATES: list[dict] = [
    {"key": "blank", "name": "Tela cheia", "zones": 1,
     "description": "Uma unica zona ocupando 100% da tela."},
    {"key": "restaurante", "name": "Restaurante", "zones": 2,
     "description": "Cardapio em destaque com rodape de promocoes."},
    {"key": "recepcao", "name": "Recepcao", "zones": 3,
     "description": "Destaque principal, coluna de avisos e relogio/clima."},
    {"key": "varejo", "name": "Varejo", "zones": 2,
     "description": "Vitrine principal com faixa de ofertas no rodape."},
]


def _to_stats(db: Session, company: models.Company) -> schemas.CompanyStats:
    """Monta a representacao de empresa com contadores agregados."""
    counts = crud.company_stats(db, company)
    base = schemas.CompanyRead.model_validate(company).model_dump()
    return schemas.CompanyStats(**base, **counts)


@router.get("", response_model=list[schemas.CompanyStats])
def list_companies(db: Session = Depends(get_db)) -> list[schemas.CompanyStats]:
    """Lista todas as empresas com seus contadores (super admin)."""
    return [_to_stats(db, company) for company in crud.list_companies(db)]


@router.post("", response_model=schemas.CompanyRead, status_code=201)
def create_company(
    data: schemas.CompanyCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_super_admin),
) -> models.Company:
    """Cria uma empresa e, opcionalmente, seu usuario administrador inicial."""
    company = crud.create_company(
        db, name=data.name, primary_color=data.primary_color
    )
    if data.admin_username and data.admin_password:
        if crud.get_user_by_username(db, data.admin_username) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nome de usuario do administrador ja existe.",
            )
        crud.create_user(
            db,
            schemas.UserCreate(
                username=data.admin_username,
                password=data.admin_password,
                role=models.UserRole.admin,
            ),
            company_id=company.id,
        )
    crud.record_audit(
        db,
        actor=actor.username,
        action="create_company",
        entity_type="company",
        entity_id=company.id,
        detail=company.name,
        company_id=company.id,
    )
    return company


@router.get("/{company_id}", response_model=schemas.CompanyStats)
def get_company(
    company_id: int, db: Session = Depends(get_db)
) -> schemas.CompanyStats:
    """Detalha uma empresa com contadores."""
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    return _to_stats(db, company)


@router.patch("/{company_id}", response_model=schemas.CompanyRead)
def update_company(
    company_id: int,
    data: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
) -> models.Company:
    """Atualiza nome, cor ou estado (ativa/inativa) de uma empresa."""
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    return crud.update_company(db, company, data)


@router.delete(
    "/{company_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_super_admin),
) -> None:
    """Remove uma empresa e, em cascata, todo o seu conteudo.

    Impede remover a ultima empresa restante (evita deixar o sistema sem
    empresa padrao).
    """
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    if crud.count_companies(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel remover a unica empresa existente.",
        )
    name = company.name
    crud.delete_company(db, company)
    crud.record_audit(
        db,
        actor=actor.username,
        action="delete_company",
        entity_type="company",
        entity_id=company_id,
        detail=name,
    )


@router.post("/{company_id}/logo", response_model=schemas.CompanyRead)
async def upload_company_logo(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> models.Company:
    """Envia (ou substitui) o logo de uma empresa."""
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _LOGO_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de logo nao suportado (use PNG, JPG, WEBP ou SVG).",
        )
    branding_dir = settings.media_dir / "branding"
    branding_dir.mkdir(parents=True, exist_ok=True)
    filename = f"logo_{company_id}_{uuid.uuid4().hex}{suffix}"
    target = branding_dir / filename
    with target.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return crud.set_company_logo(db, company, f"branding/{filename}")


@branding_router.get("/api/branding", response_model=schemas.BrandingRead)
def get_branding(
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope)
) -> schemas.BrandingRead:
    """Marca da empresa em foco (apos o login), para o cabecalho do painel.

    Para super admin sem empresa selecionada, devolve uma marca neutra.
    """
    company_id = scope.company_id if scope.company_id is not None else scope.user.company_id
    if company_id is None:
        return schemas.BrandingRead()
    company = crud.get_company(db, company_id)
    if company is None:
        return schemas.BrandingRead()
    logo_url = f"/media/{company.logo_path}" if company.logo_path else None
    return schemas.BrandingRead(
        company_id=company.id,
        company_name=company.name,
        logo_url=logo_url,
        primary_color=company.primary_color,
    )


@templates_router.get("/api/templates", response_model=list[schemas.TemplateInfo])
def list_templates(scope: Scope = Depends(get_scope)) -> list[schemas.TemplateInfo]:
    """Lista os templates de tela disponiveis (cenarios prontos)."""
    return [schemas.TemplateInfo(**tpl) for tpl in _TEMPLATES]
