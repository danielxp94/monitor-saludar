"""Motor asíncrono de recolección multicanal (RSS directo + Secciones HTML + Búsqueda por dominio AR)."""

import asyncio
import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.database import (
    get_setting,
    log_scan_finish,
    log_scan_start,
    upsert_article,
    url_hash,
)
from app.nlp_engine import analyze_article

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.7",
}

# Estado global en memoria para mostrar progreso en tiempo real en la interfaz web
SCAN_STATE: Dict[str, Any] = {
    "is_running": False,
    "progress_pct": 0,
    "current_step": "Listo",
    "candidates_found": 0,
    "candidates_checked": 0,
    "articles_saved": 0,
    "started_at": None,
    "last_completed_at": None,
    "last_error": None,
}


def parse_any_date(raw_date: Any) -> str:
    """Normaliza cualquier formato de fecha RSS/ISO a ISO-8601 UTC."""
    if not raw_date:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(raw_date, str):
        s = raw_date.strip()
        try:
            dt = parsedate_to_datetime(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
        try:
            s_clean = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def clean_html_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def match_site_by_url_or_domain(
    target_url: str,
    source_url: str,
    sites_map_by_domain: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    for candidate in (target_url, source_url):
        if not candidate:
            continue
        host = urlparse(candidate).netloc.lower().lstrip("www.")
        for domain, cfg in sites_map_by_domain.items():
            d_clean = domain.lower().lstrip("www.")
            if host == d_clean or host.endswith("." + d_clean):
                return cfg
    return None


def _extract_jsonld_article(soup: BeautifulSoup) -> Dict[str, str]:
    """Extrae cuerpo completo, fecha, autor e imagen desde bloques JSON-LD (Arc XP, WordPress, etc.)."""
    result: Dict[str, str] = {}
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]
        expanded: List[Dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                if "@graph" in it and isinstance(it["@graph"], list):
                    expanded.extend(x for x in it["@graph"] if isinstance(x, dict))
                else:
                    expanded.append(it)

        for obj in expanded:
            otype = str(obj.get("@type", "")).lower()
            if any(t in otype for t in ("newsarticle", "article", "reportagenewsarticle", "webpage")):
                body = obj.get("articleBody") or ""
                if isinstance(body, str) and len(body) > len(result.get("body", "")):
                    result["body"] = html.unescape(body).strip()
                if not result.get("title") and isinstance(obj.get("headline"), str):
                    result["title"] = html.unescape(obj["headline"]).strip()
                if not result.get("description") and isinstance(obj.get("description"), str):
                    result["description"] = html.unescape(obj["description"]).strip()
                if not result.get("published_at"):
                    pub = obj.get("datePublished") or obj.get("dateCreated")
                    if isinstance(pub, str):
                        result["published_at"] = pub
                if not result.get("author"):
                    auth = obj.get("author")
                    if isinstance(auth, dict) and auth.get("name"):
                        result["author"] = str(auth["name"])
                    elif isinstance(auth, list) and auth:
                        names = [str(a.get("name", "")) for a in auth if isinstance(a, dict) and a.get("name")]
                        if names:
                            result["author"] = ", ".join(names[:2])
                if not result.get("image"):
                    img = obj.get("image")
                    if isinstance(img, str):
                        result["image"] = img
                    elif isinstance(img, dict) and img.get("url"):
                        result["image"] = str(img["url"])
                    elif isinstance(img, list) and img:
                        first = img[0]
                        if isinstance(first, str):
                            result["image"] = first
                        elif isinstance(first, dict) and first.get("url"):
                            result["image"] = str(first["url"])
    return result


def parse_article_html(raw_html: str, url: str) -> Dict[str, str]:
    """Extrae texto completo limpio, metadatos OpenGraph y JSON-LD desde el HTML de una nota."""
    soup = BeautifulSoup(raw_html, "html.parser")
    jld = _extract_jsonld_article(soup)

    def _meta(prop_names: List[str]) -> str:
        for p in prop_names:
            tag = soup.find("meta", attrs={"property": p}) or soup.find("meta", attrs={"name": p})
            if tag and tag.get("content"):
                return html.unescape(str(tag["content"])).strip()
        return ""

    title = jld.get("title") or _meta(["og:title", "twitter:title"]) or (
        soup.title.get_text(strip=True) if soup.title else ""
    )
    description = jld.get("description") or _meta(["og:description", "description", "twitter:description"])
    image = jld.get("image") or _meta(["og:image", "twitter:image"])
    published_raw = jld.get("published_at") or _meta([
        "article:published_time", "datePublished", "publish-date", "DC.date.issued", "parsely-pub-date"
    ])
    author = jld.get("author") or _meta(["author", "article:author", "byl"])

    # Limpiar nodos no deseados y bloques de notas relacionadas / publicidad antes de extraer párrafos
    for bad in soup.find_all(["script", "style", "nav", "footer", "aside", "form", "noscript", "iframe", "svg"]):
        bad.decompose()
    noise_pattern = re.compile(
        r"(related|recommend|te-puede-interesar|interesar|promo|banner|widget|sidebar|newsletter|more-news|read-more|also-read|mas-leidas|most-read|outbrain|taboola)",
        re.I,
    )
    for tag in list(soup.find_all(attrs={"class": noise_pattern})):
        tag.decompose()
    for tag in list(soup.find_all(attrs={"id": noise_pattern})):
        tag.decompose()

    container = (
        soup.find(attrs={"itemprop": "articleBody"})
        or soup.find("article")
        or soup.find("main")
        or soup.body
    )

    paragraphs: List[str] = []
    if container:
        for p in container.find_all("p"):
            # Ignorar párrafos que son meramente enlaces a otras notas (cards relacionados)
            if p.find_parent("a"):
                continue
            txt = re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()
            if len(txt) < 35:
                continue
            low = txt.lower()
            if any(
                junk in low
                for junk in [
                    "todos los derechos reservados",
                    "suscribite al newsletter",
                    "recibí las noticias",
                    "términos y condiciones",
                    "política de privacidad",
                    "te puede interesar",
                    "leé también",
                    "lee también",
                ]
            ):
                continue
            if txt not in paragraphs:
                paragraphs.append(txt)

    dom_body = "\n\n".join(paragraphs)
    jld_body = jld.get("body", "")
    # Preferir JSON-LD articleBody cuando está completo porque evita tarjetas relacionadas y promos del DOM
    if len(jld_body) >= 220:
        full_text = jld_body
    else:
        full_text = dom_body or jld_body

    return {
        "title": title,
        "summary": description,
        "full_text": full_text[:25000],
        "image_url": image,
        "published_at": parse_any_date(published_raw) if published_raw else "",
        "author": author[:120],
    }


async def _fetch_rss_candidates(
    client: httpx.AsyncClient,
    site_cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for rss_url in site_cfg.get("rss_feeds", []):
        try:
            resp = await client.get(rss_url, timeout=12.0, follow_redirects=True)
            if resp.status_code >= 400:
                continue
            parsed = feedparser.parse(resp.text)
            for entry in parsed.entries[:45]:
                link = (entry.get("link") or "").strip()
                title = clean_html_text(entry.get("title") or "")
                if not link or not title:
                    continue
                summary = clean_html_text(entry.get("summary") or entry.get("description") or "")
                pub = parse_any_date(entry.get("published") or entry.get("updated"))
                img = ""
                media = entry.get("media_content") or entry.get("enclosures") or []
                if isinstance(media, list) and media and isinstance(media[0], dict):
                    img = str(media[0].get("url", ""))
                is_health_feed = any(
                    seg in rss_url.lower()
                    for seg in ["/salud", "/buena-vida", "/biotecnologia", "/tag/salud"]
                )
                candidates.append(
                    {
                        "url": link,
                        "title": title,
                        "summary": summary,
                        "published_at": pub,
                        "image_url": img,
                        "site_cfg": site_cfg,
                        "channel": "rss_directo",
                        "needs_full_fetch": True,
                        "accept_health_section": is_health_feed,
                        "require_health_title": not any(
                            dom in rss_url.lower() for dom in ["perfil.com/feed/salud", "chequeado.com/tag/salud"]
                        ),
                    }
                )
        except Exception:
            continue
    return candidates


async def _fetch_section_html_candidates(
    client: httpx.AsyncClient,
    site_cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extrae enlaces de artículos directamente de portadas temáticas cuando el RSS es limitado."""
    candidates: List[Dict[str, Any]] = []
    domain = site_cfg["domain"].lower().lstrip("www.")
    seen_links: Set[str] = set()

    for sec_url in site_cfg.get("section_urls", [])[:2]:
        try:
            resp = await client.get(sec_url, timeout=12.0, follow_redirects=True)
            if resp.status_code >= 400:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = urljoin(sec_url, a_tag["href"].strip()).split("#")[0]
                parsed_u = urlparse(href)
                host = parsed_u.netloc.lower().lstrip("www.")
                if not (host == domain or host.endswith("." + domain)):
                    continue
                path = parsed_u.path or ""
                # Heurística de enlace a nota periodística (ruta profunda con guiones)
                if path.count("-") < 3 or len(path) < 28:
                    continue
                if any(
                    skip in path.lower()
                    for skip in ["/autor/", "/tag/", "/tema/", "/seccion/", "/categoria/", "/suscripciones"]
                ):
                    continue
                if href in seen_links:
                    continue
                headline = re.sub(r"\s+", " ", a_tag.get_text(" ", strip=True)).strip()
                if len(headline) < 28:
                    continue
                seen_links.add(href)
                candidates.append(
                    {
                        "url": href,
                        "title": headline,
                        "summary": "",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "image_url": "",
                        "site_cfg": site_cfg,
                        "channel": "seccion_web",
                        "needs_full_fetch": True,
                    }
                )
                if len(seen_links) >= 25:
                    break
        except Exception:
            continue
    return candidates


def _build_targeted_search_queries(
    enabled_sites: List[Dict[str, Any]],
    terms: List[Dict[str, Any]],
) -> List[Tuple[str, str]]:
    """
    Construye consultas gratuitas en Bing News RSS y Google News RSS restringidas ESTRICTAMENTE
    a los dominios de la planilla (site:dominio.com) para hallar notas específicas de OSDE,
    prepagas, personalidades y reguladores publicadas recientemente.
    """
    high_value_clusters = [
        # Cluster 1: Grupo OSDE y sus ejecutivos / marcas
        '("OSDE" OR "García Sarubbi" OR "Martín Pochat" OR "Guido Montaruli" OR "Fundación OSDE" OR "Interturis" OR "URG Urgencias")',
        # Cluster 2: Competidores y cámaras
        '("Swiss Medical" OR "Claudio Belocopitt" OR "Galeno" OR "Medifé" OR "Medife" OR "Sancor Salud" OR "Omint" OR "Unión Argentina de Salud" OR "Hugo Magonza" OR "Luis Fontana")',
        # Cluster 3: Reguladores y normativa sanitaria
        '("Superintendencia de Servicios de Salud" OR "ANMAT" OR "ANEFiTS" OR "prepagas" OR "medicina privada" OR "obras sociales")',
        # Cluster 4: Prestaciones clave y avances médicos (del script de referencia)
        '("telemedicina" OR "cartilla médica" OR "medicamentos" "salud")',
        '(alzheimer OR cáncer OR diabetes OR infarto OR acv OR "nuevo tratamiento" OR "estudio científico" OR "avance médico")',
    ]

    # Agrupar los dominios habilitados en lotes de 4 para consultas compactas y precisas
    domains = [s["domain"] for s in enabled_sites]
    domain_batches = [domains[i : i + 4] for i in range(0, len(domains), 4)]

    queries: List[Tuple[str, str, bool]] = []
    for dbatch in domain_batches:
        site_expr = "(" + " OR ".join(f"site:{d}" for d in dbatch) + ")"
        for idx, cluster in enumerate(high_value_clusters):
            is_health_adv = idx == len(high_value_clusters) - 1
            q_str = f"{site_expr} {cluster}"
            bing_url = f"https://www.bing.com/news/search?q={quote_plus(q_str)}&format=rss&cc=AR&setlang=es"
            gnews_url = f"https://news.google.com/rss/search?q={quote_plus(q_str + ' when:7d')}&hl=es-419&gl=AR&ceid=AR:es-419"
            queries.append(("bing_rss", bing_url, is_health_adv))
            queries.append(("gnews_rss", gnews_url, is_health_adv))

    # Canal general Google News Salud Argentina (filtrado estrictamente por medios autorizados)
    queries.append((
        "gnews_rss",
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNR3QwTlRFU0JtVnpMVFF4T1NnQVAB?hl=es-419&gl=AR&ceid=AR:es-419",
        True,
    ))
    return queries


async def _fetch_targeted_search_candidates(
    client: httpx.AsyncClient,
    enabled_sites: List[Dict[str, Any]],
    terms: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    sites_by_domain = {s["domain"]: s for s in enabled_sites}
    queries = _build_targeted_search_queries(enabled_sites, terms)
    candidates: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(6)

    async def _run_one(kind: str, feed_url: str, is_health_section: bool) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        async with sem:
            try:
                resp = await client.get(feed_url, timeout=12.0, follow_redirects=True)
                if resp.status_code >= 400:
                    return out
                parsed = feedparser.parse(resp.text)
                for entry in parsed.entries[:25]:
                    raw_link = (entry.get("link") or "").strip()
                    raw_title = clean_html_text(entry.get("title") or "")
                    if not raw_link or not raw_title:
                        continue

                    real_url = raw_link
                    source_href = ""
                    if kind == "bing_rss":
                        qs = parse_qs(urlparse(raw_link).query)
                        if "url" in qs and qs["url"]:
                            real_url = qs["url"][0]
                    elif kind == "gnews_rss":
                        src_obj = entry.get("source")
                        if isinstance(src_obj, dict):
                            source_href = str(src_obj.get("href") or src_obj.get("url") or "")
                        # Limpiar el sufijo " - NombreDelMedio" típico de Google News
                        if " - " in raw_title:
                            raw_title = raw_title.rsplit(" - ", 1)[0].strip()

                    matched_site = match_site_by_url_or_domain(real_url, source_href, sites_by_domain)
                    if not matched_site:
                        continue

                    summary = clean_html_text(entry.get("summary") or entry.get("description") or "")
                    # Evitar que Google News ponga solo el título repetido en el summary
                    if summary.startswith(raw_title[:30]):
                        summary = ""

                    out.append(
                        {
                            "url": real_url,
                            "title": raw_title,
                            "summary": summary,
                            "published_at": parse_any_date(entry.get("published") or entry.get("updated")),
                            "image_url": "",
                            "site_cfg": matched_site,
                            "channel": kind,
                            # Bing nos da la URL directa real del medio para extraer el artículo entero
                            "needs_full_fetch": "news.google.com" not in real_url,
                            "accept_health_section": is_health_section,
                            "require_health_title": True,
                        }
                    )
            except Exception:
                return out
        return out

    batches = await asyncio.gather(*[_run_one(k, u, h) for k, u, h in queries])
    for b in batches:
        candidates.extend(b)
    return candidates


def _quick_prefilter(title: str, summary: str, channel: str, accept_health_section: bool = False) -> bool:
    """
    Pre-filtro rápido para RSS generales (ej. portada general de Clarín/Infobae):
    evita descargar el HTML completo de notas de fútbol o espectáculo que claramente no tienen
    ninguna relación con salud, prepagas, empresas o regulación.
    Para canales ya filtrados o secciones específicas de salud, deja pasar siempre.
    """
    if channel in ("bing_rss", "gnews_rss") or accept_health_section:
        return True
    combo = f"{title} {summary}".lower()
    broad_triggers = [
        "osde", "sarubbi", "pochat", "montaruli", "prepaga", "medicina", "salud",
        "obra social", "obras sociales", "bina", "urg ", "interturis", "flux",
        "belocopitt", "uas", "magonza", "superintendencia", "anefits", "anmat",
        "fontana", "galeno", "medife", "medifé", "sancor", "swiss medical", "omint",
        "medicamento", "remedio", "farmac", "cartilla", "sanatorio", "clínica", "clinica",
        "hospital", "telemedicina", "médic", "medic", "paciente", "afiliad", "cuota",
        "pami", "ioma", "garrahan", "vacuna", "dengue", "decreto", "boletín oficial",
        "boletin oficial", "resolución", "resolucion", "discapacidad",
    ]
    return any(t in combo for t in broad_triggers)


async def run_full_scan() -> Dict[str, Any]:
    """Ejecuta un barrido completo sobre los 12 medios aplicando todos los criterios de la planilla."""
    if SCAN_STATE["is_running"]:
        return {"status": "already_running", "state": SCAN_STATE}

    SCAN_STATE.update(
        {
            "is_running": True,
            "progress_pct": 5,
            "current_step": "Cargando criterios y fuentes habilitadas...",
            "candidates_found": 0,
            "candidates_checked": 0,
            "articles_saved": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_error": None,
        }
    )
    run_id = log_scan_start()

    try:
        sites: List[Dict[str, Any]] = [
            s for s in (get_setting("sites") or []) if s.get("enabled", True)
        ]
        terms: List[Dict[str, Any]] = [
            t for t in (get_setting("terms") or []) if t.get("enabled", True)
        ]

        async with httpx.AsyncClient(headers=BROWSER_HEADERS, verify=True) as client:
            SCAN_STATE["progress_pct"] = 15
            SCAN_STATE["current_step"] = f"Consultando feeds RSS y portadas de {len(sites)} medios..."

            rss_tasks = [_fetch_rss_candidates(client, s) for s in sites]
            sec_tasks = [_fetch_section_html_candidates(client, s) for s in sites]
            search_task = _fetch_targeted_search_candidates(client, sites, terms)

            gathered = await asyncio.gather(*rss_tasks, *sec_tasks, search_task)

            raw_candidates: List[Dict[str, Any]] = []
            for group in gathered:
                raw_candidates.extend(group)

            # Deduplicar candidatos priorizando URLs directas sobre enlaces de redirección
            raw_candidates.sort(key=lambda c: (0 if c["needs_full_fetch"] else 1))
            deduped: List[Dict[str, Any]] = []
            seen_keys: Set[str] = set()
            for cand in raw_candidates:
                if not _quick_prefilter(
                    cand["title"],
                    cand["summary"],
                    cand["channel"],
                    bool(cand.get("accept_health_section", False)),
                ):
                    continue
                u_key = url_hash(cand["url"])
                t_key = f"{cand['site_cfg']['id']}::{cand['title'][:55].lower()}"
                if u_key in seen_keys or t_key in seen_keys:
                    continue
                seen_keys.add(u_key)
                seen_keys.add(t_key)
                deduped.append(cand)

            SCAN_STATE["candidates_found"] = len(deduped)
            SCAN_STATE["progress_pct"] = 42
            SCAN_STATE["current_step"] = (
                f"Extrayendo texto completo y analizando {len(deduped)} noticias candidatas..."
            )

            sem = asyncio.Semaphore(10)
            saved_count = 0
            checked_count = 0

            async def _process_candidate(cand: Dict[str, Any]) -> None:
                nonlocal saved_count, checked_count
                site_cfg = cand["site_cfg"]
                title = cand["title"]
                summary = cand["summary"]
                full_text = ""
                image_url = cand.get("image_url", "")
                author = ""
                published_at = cand["published_at"]
                final_url = cand["url"]

                if cand.get("needs_full_fetch", True):
                    async with sem:
                        try:
                            resp = await client.get(final_url, timeout=11.0, follow_redirects=True)
                            if resp.status_code < 400 and "text/html" in resp.headers.get("content-type", ""):
                                final_url = str(resp.url)
                                parsed_html = parse_article_html(resp.text, final_url)
                                if parsed_html.get("title") and len(parsed_html["title"]) > 15:
                                    title = parsed_html["title"]
                                if parsed_html.get("summary"):
                                    summary = parsed_html["summary"]
                                full_text = parsed_html.get("full_text", "")
                                if parsed_html.get("image_url"):
                                    image_url = parsed_html["image_url"]
                                if parsed_html.get("published_at"):
                                    published_at = parsed_html["published_at"]
                                if parsed_html.get("author"):
                                    author = parsed_html["author"]
                        except Exception:
                            pass

                analysis = analyze_article(
                    url=final_url,
                    title=title,
                    summary=summary,
                    body=full_text,
                    site_cfg=site_cfg,
                    terms_catalog=terms,
                    accept_health_section=bool(cand.get("accept_health_section", False)),
                    require_health_title=bool(cand.get("require_health_title", True)),
                )

                checked_count += 1
                SCAN_STATE["candidates_checked"] = checked_count
                if len(deduped) > 0:
                    SCAN_STATE["progress_pct"] = min(
                        96, 42 + int((checked_count / len(deduped)) * 54)
                    )

                if not analysis.get("accepted"):
                    return

                record = {
                    "url": final_url,
                    "title": title,
                    "summary": summary,
                    "executive_summary": analysis["executive_summary"],
                    "full_text": full_text,
                    "image_url": image_url,
                    "author": author,
                    "site_id": site_cfg["id"],
                    "site_name": site_cfg["name"],
                    "site_domain": site_cfg["domain"],
                    "published_at": published_at,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "matched_keywords": analysis["matched_keywords"],
                    "matched_entities": analysis["matched_entities"],
                    "subcategories": analysis["subcategories"],
                    "criteria": analysis["criteria"],
                    "primary_category": analysis["primary_category"],
                    "sentiment_label": analysis["sentiment_label"],
                    "sentiment_score": analysis["sentiment_score"],
                    "relevance_score": analysis["relevance_score"],
                    "is_osde_focus": analysis["is_osde_focus"],
                    "discovery_channel": cand["channel"],
                }
                if upsert_article(record):
                    saved_count += 1
                    SCAN_STATE["articles_saved"] = saved_count

            await asyncio.gather(*[_process_candidate(c) for c in deduped])

        now_iso = datetime.now(timezone.utc).isoformat()
        SCAN_STATE.update(
            {
                "is_running": False,
                "progress_pct": 100,
                "current_step": f"Completado: {saved_count} nuevas noticias relevantes indexadas",
                "last_completed_at": now_iso,
            }
        )
        log_scan_finish(
            run_id=run_id,
            status="completed",
            candidates_checked=checked_count,
            articles_saved=saved_count,
            sites_scanned=len(sites),
            notes="OK",
        )
        return dict(SCAN_STATE)

    except Exception as exc:
        err_msg = str(exc)
        SCAN_STATE.update(
            {
                "is_running": False,
                "progress_pct": 0,
                "current_step": f"Error durante el escaneo: {err_msg}",
                "last_error": err_msg,
            }
        )
        log_scan_finish(run_id, "error", SCAN_STATE["candidates_checked"], SCAN_STATE["articles_saved"], 0, err_msg)
        return dict(SCAN_STATE)
