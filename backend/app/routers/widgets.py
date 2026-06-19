"""Proxy de widgets dinamicos (noticias via RSS) para o player.

O player roda sem autenticacao e, por restricao de CORS, nao consegue buscar
feeds RSS de outros dominios diretamente no navegador. Este roteador busca os
feeds no servidor e devolve um JSON normalizado de manchetes. O widget de clima
e obtido client-side (open-meteo, sem chave), portanto nao precisa de proxy.

A rota e publica (como o /api/display/{slug}) para que o player possa consumi-la
sem token. So aceita esquemas http/https e impoe timeout e limite de tamanho.
"""

from __future__ import annotations

import csv
import io
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db

router = APIRouter(prefix="/api/widgets", tags=["widgets"])

_TIMEOUT = 6
_USER_AGENT = "tvMedia/1.0"
_MAX_PER_FEED = 15
_MAX_BYTES = 1_000_000
_MAX_FEEDS = 6


def _fetch(url: str) -> str:
    """Baixa o conteudo de um feed com timeout e limite de bytes."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
        raw = resp.read(_MAX_BYTES)
    return raw.decode("utf-8", errors="replace")


def _clean(text: str | None) -> str:
    """Normaliza espacos em branco de um texto."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def _json_list(value: str | None) -> list:
    """Le uma lista JSON armazenada no banco."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _is_expired(value) -> bool:
    """Indica se um datetime opcional ja passou."""
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > value


def _parse_feed(xml_text: str) -> list[dict]:
    """Extrai titulos/links de um feed RSS 2.0 ou Atom (tolerante a namespaces)."""
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for node in root.iter():
        tag = node.tag.lower()
        if not (tag.endswith("item") or tag.endswith("entry")):
            continue
        title = None
        link = None
        for child in node:
            ctag = child.tag.lower()
            if ctag.endswith("title") and title is None:
                title = child.text
            elif ctag.endswith("link") and link is None:
                link = child.text or child.attrib.get("href")
        if title:
            items.append({"title": _clean(title), "link": _clean(link)})
        if len(items) >= _MAX_PER_FEED:
            break
    return items


@router.get("/news")
def news(
    feeds: str = Query("", description="URLs de feeds RSS separadas por virgula."),
    limit: int = Query(20, ge=1, le=60),
) -> dict:
    """Agrega manchetes de um ou mais feeds RSS/Atom (uso publico pelo player)."""
    urls = [u.strip() for u in feeds.split(",") if u.strip()]
    headlines: list[dict] = []
    for url in urls[:_MAX_FEEDS]:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        try:
            xml_text = _fetch(url)
        except Exception:  # noqa: BLE001
            continue
        for item in _parse_feed(xml_text):
            item["source"] = parsed.netloc
            headlines.append(item)
    return {"items": headlines[:limit]}



@router.get("/rates")
def rates(
    pairs: str = Query(
        "USD-BRL,EUR-BRL",
        description="Pares de moedas separados por virgula, ex.: USD-BRL,EUR-BRL.",
    ),
) -> dict:
    """Cotacoes de moedas (proxy server-side, sem chave) para o player.

    Usa open.er-api.com (gratuito, sem token). Agrupa por moeda base para
    minimizar requisicoes. Rota publica, como os demais widgets.
    """
    wanted: list[tuple[str, str]] = []
    for token in pairs.split(","):
        token = token.strip().upper()
        if "-" in token:
            base, quote = token.split("-", 1)
            base, quote = base.strip(), quote.strip()
            if base and quote:
                wanted.append((base, quote))
    wanted = wanted[:12]
    bases: dict[str, set[str]] = {}
    for base, quote in wanted:
        bases.setdefault(base, set()).add(quote)
    out: list[dict] = []
    for base, quotes in bases.items():
        try:
            raw = _fetch("https://open.er-api.com/v6/latest/" + base)
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        rates_map = data.get("rates") or {}
        updated = data.get("time_last_update_utc")
        for quote in quotes:
            value = rates_map.get(quote)
            if value is not None:
                out.append(
                    {
                        "pair": base + "-" + quote,
                        "base": base,
                        "quote": quote,
                        "rate": value,
                        "updated": updated,
                    }
                )
    order = {b + "-" + q: i for i, (b, q) in enumerate(wanted)}
    out.sort(key=lambda r: order.get(r["pair"], 999))
    return {"items": out}


@router.get("/stocks")
def stocks(
    symbols: str = Query(
        "AAPL.US,MSFT.US",
        description="Simbolos separados por virgula no formato aceito pelo Stooq.",
    ),
) -> dict:
    """Cotacoes simples de acoes/indices via Stooq CSV (sem chave)."""
    wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()][:12]
    if not wanted:
        return {"items": []}
    url = "https://stooq.com/q/l/?s=" + ",".join(wanted) + "&f=sd2t2ohlcv&h&e=csv"
    try:
        raw = _fetch(url)
    except Exception:  # noqa: BLE001
        return {"items": []}
    rows = csv.DictReader(io.StringIO(raw))
    items: list[dict] = []
    for row in rows:
        symbol = (row.get("Symbol") or "").upper()
        close = row.get("Close")
        if not symbol or close in (None, "", "N/D"):
            continue
        items.append(
            {
                "symbol": symbol,
                "date": row.get("Date"),
                "time": row.get("Time"),
                "open": row.get("Open"),
                "high": row.get("High"),
                "low": row.get("Low"),
                "close": close,
                "volume": row.get("Volume"),
            }
        )
    order = {symbol: idx for idx, symbol in enumerate(wanted)}
    items.sort(key=lambda item: order.get(item["symbol"], 999))
    return {"items": items}


@router.get("/datasets/{dataset_id}")
def dataset_widget(dataset_id: int, db: Session = Depends(get_db)) -> dict:
    """Entrega DataSet ao player, com fallback se estiver expirado."""
    dataset = crud.get_dataset(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="DataSet nao encontrado.")
    stale = _is_expired(dataset.expires_at)
    rows = _json_list(dataset.fallback_rows if stale else dataset.rows)
    if stale and not rows:
        rows = _json_list(dataset.rows)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "columns": _json_list(dataset.columns),
        "rows": rows,
        "stale": stale,
        "refresh_status": dataset.refresh_status,
        "refresh_note": dataset.refresh_note,
    }
