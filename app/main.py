"""Servidor Web y API REST estilo NewsAPI.ai para Monitoreo de Salud y Prepagas (Argentina)."""

import asyncio
import csv
import hashlib
import hmac
import io
import os
import secrets
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.collector import SCAN_STATE, run_full_scan
from app.config_seed import (
    INITIAL_COMPETITORS_AND_ENTITIES,
    INITIAL_CRITERIA,
    INITIAL_KEYWORDS,
    INITIAL_LIMITATIONS,
    INITIAL_SITES,
)
from app.database import (
    get_article_by_id,
    get_recent_scans,
    get_setting,
    init_db,
    query_articles,
    reanalyze_stored_articles,
    save_setting,
    update_article_editorial,
)
from app.nlp_engine import cluster_articles_into_events

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
PUBLIC_READONLY = os.environ.get("PUBLIC_READONLY", "").strip().lower() in ("1", "true", "yes")
_SESSION_SECRET = (os.environ.get("SESSION_SECRET") or ADMIN_PASSWORD or secrets.token_hex(32)).encode("utf-8")
ADMIN_COOKIE_NAME = "saludar_admin"


def _make_session_token(ttl_seconds: int = 7 * 24 * 3600) -> str:
    exp = int(time.time()) + ttl_seconds
    sig = hmac.new(_SESSION_SECRET, str(exp).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def _verify_session_token(token: str) -> bool:
    if not token or "." not in token or not ADMIN_PASSWORD:
        return False
    try:
        exp_str, sig = token.split(".", 1)
        exp = int(exp_str)
        if exp < int(time.time()):
            return False
        expected = hmac.new(_SESSION_SECRET, exp_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def _is_admin_request(request: Request) -> bool:
    if not ADMIN_PASSWORD:
        return not PUBLIC_READONLY
    cookie_val = request.cookies.get(ADMIN_COOKIE_NAME, "")
    if _verify_session_token(cookie_val):
        return True
    header_pw = request.headers.get("X-Admin-Password", "")
    return bool(header_pw and hmac.compare_digest(header_pw, ADMIN_PASSWORD))


async def require_admin(request: Request) -> None:
    if not _is_admin_request(request):
        if PUBLIC_READONLY and not ADMIN_PASSWORD:
            raise HTTPException(
                status_code=403,
                detail="Instancia pública en modo solo lectura (configurá ADMIN_PASSWORD para habilitar administración).",
            )
        raise HTTPException(status_code=401, detail="Se requiere clave de administrador para modificar o escanear.")


async def _daily_scheduler_loop() -> None:
    """
    Ejecuta automáticamente el relevamiento diario ('Periodicidad: Diaria')
    y dispara un escaneo inicial si la base de datos aún está vacía.
    """
    await asyncio.sleep(1.5)
    existing = query_articles(limit=1)
    if not existing and not SCAN_STATE["is_running"]:
        asyncio.create_task(run_full_scan())

    while True:
        await asyncio.sleep(1800)  # Revisa cada 30 minutos si pasaron >= 24 horas desde el último barrido
        try:
            scans = get_recent_scans(limit=1)
            should_run = False
            if not scans:
                should_run = True
            else:
                last_str = scans[0].get("finished_at") or scans[0].get("started_at")
                if last_str:
                    last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) - last_dt >= timedelta(hours=24):
                        should_run = True
            if should_run and not SCAN_STATE["is_running"]:
                await run_full_scan()
        except Exception:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler_task = asyncio.create_task(_daily_scheduler_loop())
    yield
    scheduler_task.cancel()


app = FastAPI(
    title="SaludAR News Intelligence API",
    description=(
        "Réplica local y gratuita de NewsAPI.ai enfocada en Salud, Prepagas, Obras Sociales "
        "y Normativa Sanitaria de la República Argentina."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


class LoginPayload(BaseModel):
    password: str


@app.get("/api/auth/status")
async def api_auth_status(request: Request) -> Dict[str, Any]:
    return {
        "auth_required": bool(ADMIN_PASSWORD),
        "readonly_locked": bool(PUBLIC_READONLY and not ADMIN_PASSWORD),
        "is_admin": _is_admin_request(request),
    }


@app.post("/api/auth/login")
async def api_auth_login(payload: LoginPayload, request: Request, response: Response) -> Dict[str, Any]:
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=400, detail="No hay ADMIN_PASSWORD configurado en el servidor.")
    if not hmac.compare_digest(payload.password or "", ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Clave de administrador incorrecta.")
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=_make_session_token(),
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=is_https,
    )
    return {"ok": True, "is_admin": True}


@app.post("/api/auth/logout")
async def api_auth_logout(response: Response) -> Dict[str, Any]:
    response.delete_cookie(key=ADMIN_COOKIE_NAME)
    return {"ok": True, "is_admin": False}


@app.get("/api/articles")
async def api_list_articles(
    q: Optional[str] = Query(None, description="Búsqueda de texto libre en título y contenido"),
    site_id: Optional[str] = Query(None, description="ID del medio (ej. infobae, clarin, lanacion)"),
    criterion: Optional[str] = Query(None, description="Salud | Normativas de salud | Resoluciones de la superintendencia"),
    term: Optional[str] = Query(None, description="Palabra clave o personalidad específica"),
    column_group: Optional[str] = Query(None, description="palabras_claves | personalidades_otras_prepagas"),
    sentiment: Optional[str] = Query(None, description="Positivo | Neutro | Negativo"),
    primary_category: Optional[str] = Query(None, description="Categoría editorial Prensa OSDE"),
    editorial_status: Optional[str] = Query(None, description="Pendiente | Aprobada | Descartada"),
    osde_only: bool = Query(False, description="Filtrar exclusivamente menciones del Grupo OSDE"),
    hours: Optional[int] = Query(None, ge=1, le=720, description="Ventana horaria (ej. 24 para últimas 24 hs)"),
    date_from: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    sort_by: str = Query("recent", description="recent | relevance | sentiment_desc | sentiment_asc"),
    limit: int = Query(250, ge=1, le=1000),
) -> Dict[str, Any]:
    items = query_articles(
        q=q,
        site_id=site_id,
        criterion=criterion,
        term=term,
        column_group=column_group,
        sentiment=sentiment,
        primary_category=primary_category,
        editorial_status=editorial_status,
        osde_only=osde_only,
        hours=hours,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        limit=limit,
    )
    # Omitir full_text pesado en el listado masivo para respuesta instantánea (se pide en detalle o viene resumido)
    lightweight = []
    for it in items:
        copy_it = dict(it)
        copy_it["has_full_text"] = bool(it.get("full_text") and len(it["full_text"]) > 160)
        copy_it["word_count"] = len((it.get("full_text") or "").split())
        copy_it.pop("full_text", None)
        lightweight.append(copy_it)
    return {"count": len(lightweight), "articles": lightweight}


class EditorialUpdatePayload(BaseModel):
    editorial_status: Optional[str] = None
    press_notes: Optional[str] = None


@app.patch("/api/articles/{article_id}/editorial", dependencies=[Depends(require_admin)])
async def api_update_article_editorial(article_id: int, payload: EditorialUpdatePayload) -> Dict[str, Any]:
    try:
        updated = update_article_editorial(
            article_id=article_id,
            editorial_status=payload.editorial_status,
            press_notes=payload.press_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    updated.pop("full_text", None)
    return updated


@app.get("/api/articles/{article_id}")
async def api_get_article(article_id: int) -> Dict[str, Any]:
    art = get_article_by_id(article_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return art


@app.get("/api/events")
async def api_list_events(
    q: Optional[str] = None,
    criterion: Optional[str] = None,
    osde_only: bool = False,
    limit: int = Query(250, ge=10, le=600),
) -> Dict[str, Any]:
    articles = query_articles(q=q, criterion=criterion, osde_only=osde_only, limit=limit)
    events = cluster_articles_into_events(articles)
    # Aligerar artículos internos de cada evento
    for ev in events:
        for a in ev["articles"]:
            a.pop("full_text", None)
    return {"count": len(events), "events": events}


@app.get("/api/stats")
async def api_stats() -> Dict[str, Any]:
    articles = query_articles(limit=1000)
    events = cluster_articles_into_events(articles[:300])
    sites_cfg = get_setting("sites") or []
    scans = get_recent_scans(limit=5)

    by_site = Counter(a["site_name"] for a in articles)
    by_sentiment = Counter(a["sentiment_label"] for a in articles)
    by_primary_category = Counter(a.get("primary_category") or "Mercado & Prepagas" for a in articles)
    by_editorial_status = Counter(a.get("editorial_status") or "Pendiente" for a in articles)
    by_criteria: Counter = Counter()
    kw_counter: Counter = Counter()
    ent_counter: Counter = Counter()
    by_day: Counter = Counter()
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    last_24h_count = 0

    for a in articles:
        for c in a.get("criteria", []):
            by_criteria[c] += 1
        for k in a.get("matched_keywords", []):
            kw_counter[k] += 1
        for e in a.get("matched_entities", []):
            ent_counter[e] += 1
        pub = a.get("published_at") or ""
        if pub >= cutoff_24h:
            last_24h_count += 1
        day = pub[:10]
        if day:
            by_day[day] += 1

    multi_source_events = sum(1 for e in events if e["site_count"] > 1)
    osde_count = sum(1 for a in articles if a.get("is_osde_focus"))

    return {
        "totals": {
            "articles": len(articles),
            "last_24h": last_24h_count,
            "events": len(events),
            "multi_source_events": multi_source_events,
            "osde_mentions": osde_count,
            "approved": by_editorial_status.get("Aprobada", 0),
            "pending": by_editorial_status.get("Pendiente", 0),
            "discarded": by_editorial_status.get("Descartada", 0),
            "enabled_sites": sum(1 for s in sites_cfg if s.get("enabled", True)),
            "total_sites": len(sites_cfg),
        },
        "by_site": [{"name": k, "count": v} for k, v in by_site.most_common()],
        "by_primary_category": [{"name": k, "count": v} for k, v in by_primary_category.most_common()],
        "by_editorial_status": {
            "Pendiente": by_editorial_status.get("Pendiente", 0),
            "Aprobada": by_editorial_status.get("Aprobada", 0),
            "Descartada": by_editorial_status.get("Descartada", 0),
        },
        "by_criteria": [{"name": k, "count": v} for k, v in by_criteria.most_common()],
        "by_sentiment": {
            "Positivo": by_sentiment.get("Positivo", 0),
            "Neutro": by_sentiment.get("Neutro", 0),
            "Negativo": by_sentiment.get("Negativo", 0),
        },
        "top_keywords": [{"term": k, "count": v} for k, v in kw_counter.most_common(15)],
        "top_entities": [{"term": k, "count": v} for k, v in ent_counter.most_common(20)],
        "timeline": [
            {"date": d, "count": by_day[d]}
            for d in sorted(by_day.keys())[-14:]
        ],
        "recent_scans": scans,
        "scan_state": SCAN_STATE,
    }


@app.post("/api/scan", dependencies=[Depends(require_admin)])
async def api_trigger_scan(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    if SCAN_STATE["is_running"]:
        return {"started": False, "message": "Ya hay un escaneo en curso", "state": SCAN_STATE}
    background_tasks.add_task(run_full_scan)
    return {"started": True, "message": "Escaneo iniciado en segundo plano", "state": SCAN_STATE}


@app.get("/api/scan/status")
async def api_scan_status() -> Dict[str, Any]:
    return SCAN_STATE


@app.post("/api/reanalyze", dependencies=[Depends(require_admin)])
async def api_reanalyze() -> Dict[str, Any]:
    return reanalyze_stored_articles()


class ConfigUpdatePayload(BaseModel):
    sites: Optional[List[Dict[str, Any]]] = None
    terms: Optional[List[Dict[str, Any]]] = None
    limitations: Optional[Dict[str, Any]] = None
    criteria: Optional[List[str]] = None


@app.get("/api/config")
async def api_get_config() -> Dict[str, Any]:
    return {
        "sites": get_setting("sites", INITIAL_SITES),
        "terms": get_setting("terms", INITIAL_KEYWORDS + INITIAL_COMPETITORS_AND_ENTITIES),
        "limitations": get_setting("limitations", INITIAL_LIMITATIONS),
        "criteria": get_setting("criteria", INITIAL_CRITERIA),
    }


@app.put("/api/config", dependencies=[Depends(require_admin)])
async def api_update_config(payload: ConfigUpdatePayload) -> Dict[str, Any]:
    if payload.sites is not None:
        save_setting("sites", payload.sites)
    if payload.terms is not None:
        save_setting("terms", payload.terms)
    if payload.limitations is not None:
        save_setting("limitations", payload.limitations)
    if payload.criteria is not None:
        save_setting("criteria", payload.criteria)
    return await api_get_config()


@app.post("/api/config/reset", dependencies=[Depends(require_admin)])
async def api_reset_config() -> Dict[str, Any]:
    save_setting("sites", INITIAL_SITES)
    save_setting("terms", INITIAL_KEYWORDS + INITIAL_COMPETITORS_AND_ENTITIES)
    save_setting("limitations", INITIAL_LIMITATIONS)
    save_setting("criteria", INITIAL_CRITERIA)
    return await api_get_config()


@app.get("/api/export/csv")
async def api_export_csv(
    q: Optional[str] = None,
    site_id: Optional[str] = None,
    criterion: Optional[str] = None,
    sentiment: Optional[str] = None,
    primary_category: Optional[str] = None,
    editorial_status: Optional[str] = None,
    osde_only: bool = False,
    hours: Optional[int] = None,
):
    articles = query_articles(
        q=q,
        site_id=site_id,
        criterion=criterion,
        sentiment=sentiment,
        primary_category=primary_category,
        editorial_status=editorial_status,
        osde_only=osde_only,
        hours=hours,
        limit=1000,
    )
    output = io.StringIO()
    # BOM UTF-8 para que Microsoft Excel en español abra tildes y eñes perfectamente
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Estado",
            "Fecha Publicación",
            "Medio",
            "Categoría Prensa",
            "Título",
            "Criterios (Col F)",
            "Palabras Claves (Col C)",
            "Personalidades / Otras Prepagas (Col D)",
            "Foco OSDE",
            "Sentimiento",
            "Puntaje Relevancia",
            "Limitación",
            "Notas Prensa",
            "Resumen Ejecutivo",
            "URL",
        ]
    )
    for a in articles:
        writer.writerow(
            [
                a.get("editorial_status", "Pendiente"),
                (a.get("published_at") or "")[:19].replace("T", " "),
                a.get("site_name", ""),
                a.get("primary_category", "Mercado & Prepagas"),
                a.get("title", ""),
                ", ".join(a.get("criteria", [])),
                ", ".join(a.get("matched_keywords", [])),
                ", ".join(a.get("matched_entities", [])),
                "Sí" if a.get("is_osde_focus") else "No",
                a.get("sentiment_label", ""),
                a.get("relevance_score", ""),
                "Sólo Argentina",
                a.get("press_notes", ""),
                a.get("executive_summary") or a.get("summary") or "",
                a.get("url", ""),
            ]
        )

    output.seek(0)
    filename = f"reporte_noticias_salud_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
