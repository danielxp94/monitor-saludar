"""Capa de persistencia local gratuita basada en SQLite + FTS5 (Full-Text Search)."""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config_seed import (
    INITIAL_COMPETITORS_AND_ENTITIES,
    INITIAL_CRITERIA,
    INITIAL_KEYWORDS,
    INITIAL_LIMITATIONS,
    INITIAL_SITES,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("MONITOR_DB_PATH") or (DATA_DIR / "news_intelligence.db"))


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def url_hash(url: str) -> str:
    clean = (url or "").strip().split("#")[0]
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:24]


def title_fingerprint(title: str) -> str:
    import re
    from app.nlp_engine import normalize_text
    words = re.findall(r"[a-z0-9]{4,}", normalize_text(title or ""))
    return " ".join(words[:9])


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                title_fp TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT DEFAULT '',
                executive_summary TEXT DEFAULT '',
                full_text TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                author TEXT DEFAULT '',
                site_id TEXT NOT NULL,
                site_name TEXT NOT NULL,
                site_domain TEXT NOT NULL,
                published_at TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                matched_keywords_json TEXT NOT NULL,
                matched_entities_json TEXT NOT NULL,
                subcategories_json TEXT NOT NULL,
                criteria_json TEXT NOT NULL,
                primary_category TEXT DEFAULT 'Mercado & Prepagas',
                editorial_status TEXT DEFAULT 'Pendiente',
                press_notes TEXT DEFAULT '',
                sentiment_label TEXT NOT NULL,
                sentiment_score REAL NOT NULL,
                relevance_score REAL NOT NULL,
                is_osde_focus INTEGER NOT NULL DEFAULT 0,
                discovery_channel TEXT DEFAULT 'rss'
            );

            CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_articles_site ON articles(site_id);
            CREATE INDEX IF NOT EXISTS idx_articles_osde ON articles(is_osde_focus);
            CREATE INDEX IF NOT EXISTS idx_articles_title_fp ON articles(title_fp, site_id);

            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                candidates_checked INTEGER DEFAULT 0,
                articles_saved INTEGER DEFAULT 0,
                sites_scanned INTEGER DEFAULT 0,
                notes TEXT DEFAULT ''
            );
            """
        )

        # Migración automática segura para bases existentes
        existing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(articles)").fetchall()}
        migrations = [
            ("primary_category", "TEXT DEFAULT 'Mercado & Prepagas'"),
            ("editorial_status", "TEXT DEFAULT 'Pendiente'"),
            ("press_notes", "TEXT DEFAULT ''"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_def}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_editorial ON articles(editorial_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(primary_category)")

        # Sembrar configuración inicial si no existe
        now = datetime.now(timezone.utc).isoformat()
        defaults = {
            "sites": INITIAL_SITES,
            "terms": INITIAL_KEYWORDS + INITIAL_COMPETITORS_AND_ENTITIES,
            "limitations": INITIAL_LIMITATIONS,
            "criteria": INITIAL_CRITERIA,
        }
        for key, val in defaults.items():
            cur = conn.execute("SELECT 1 FROM settings WHERE key = ?", (key,)).fetchone()
            if not cur:
                conn.execute(
                    "INSERT INTO settings (key, value_json, updated_at) VALUES (?, ?, ?)",
                    (key, json.dumps(val, ensure_ascii=False), now),
                )
    conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    try:
        row = conn.execute("SELECT value_json FROM settings WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        return json.loads(row["value_json"])
    finally:
        conn.close()


def save_setting(key: str, value: Any) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False), now),
            )
    finally:
        conn.close()


def upsert_article(art: Dict[str, Any]) -> bool:
    """Inserta un artículo evitando duplicados por URL o mismo titular en el mismo medio. Devuelve True si es nuevo."""
    uh = url_hash(art["url"])
    tfp = title_fingerprint(art["title"])
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id, length(full_text) as flen FROM articles WHERE url_hash = ? OR (site_id = ? AND title_fp = ? AND title_fp != '')",
            (uh, art["site_id"], tfp),
        ).fetchone()

        if existing:
            # Si ahora tenemos texto completo más largo, enriquecer el registro existente
            new_body = art.get("full_text") or ""
            if len(new_body) > (existing["flen"] or 0) + 100:
                with conn:
                    conn.execute(
                        """
                        UPDATE articles
                        SET full_text = ?, executive_summary = ?, image_url = COALESCE(NULLIF(?, ''), image_url),
                            matched_keywords_json = ?, matched_entities_json = ?, subcategories_json = ?,
                            criteria_json = ?, primary_category = ?, sentiment_label = ?, sentiment_score = ?, relevance_score = ?,
                            is_osde_focus = ?
                        WHERE id = ?
                        """,
                        (
                            new_body,
                            art.get("executive_summary", ""),
                            art.get("image_url", ""),
                            json.dumps(art.get("matched_keywords", []), ensure_ascii=False),
                            json.dumps(art.get("matched_entities", []), ensure_ascii=False),
                            json.dumps(art.get("subcategories", []), ensure_ascii=False),
                            json.dumps(art.get("criteria", []), ensure_ascii=False),
                            art.get("primary_category", "Mercado & Prepagas"),
                            art.get("sentiment_label", "Neutro"),
                            float(art.get("sentiment_score", 0.0)),
                            float(art.get("relevance_score", 1.0)),
                            1 if art.get("is_osde_focus") else 0,
                            existing["id"],
                        ),
                    )
            return False

        with conn:
            conn.execute(
                """
                INSERT INTO articles (
                    url_hash, title_fp, url, title, summary, executive_summary, full_text,
                    image_url, author, site_id, site_name, site_domain, published_at, fetched_at,
                    matched_keywords_json, matched_entities_json, subcategories_json, criteria_json,
                    primary_category, editorial_status, press_notes,
                    sentiment_label, sentiment_score, relevance_score, is_osde_focus, discovery_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uh,
                    tfp,
                    art["url"],
                    art["title"],
                    art.get("summary", ""),
                    art.get("executive_summary", ""),
                    art.get("full_text", ""),
                    art.get("image_url", ""),
                    art.get("author", ""),
                    art["site_id"],
                    art["site_name"],
                    art["site_domain"],
                    art["published_at"],
                    art["fetched_at"],
                    json.dumps(art.get("matched_keywords", []), ensure_ascii=False),
                    json.dumps(art.get("matched_entities", []), ensure_ascii=False),
                    json.dumps(art.get("subcategories", []), ensure_ascii=False),
                    json.dumps(art.get("criteria", []), ensure_ascii=False),
                    art.get("primary_category", "Mercado & Prepagas"),
                    art.get("editorial_status", "Pendiente"),
                    art.get("press_notes", ""),
                    art.get("sentiment_label", "Neutro"),
                    float(art.get("sentiment_score", 0.0)),
                    float(art.get("relevance_score", 1.0)),
                    1 if art.get("is_osde_focus") else 0,
                    art.get("discovery_channel", "rss"),
                ),
            )
        return True
    finally:
        conn.close()


def _deserialize_row(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["matched_keywords"] = json.loads(d.pop("matched_keywords_json", "[]"))
    d["matched_entities"] = json.loads(d.pop("matched_entities_json", "[]"))
    d["subcategories"] = json.loads(d.pop("subcategories_json", "[]"))
    d["criteria"] = json.loads(d.pop("criteria_json", "[]"))
    d["is_osde_focus"] = bool(d.get("is_osde_focus", 0))
    return d


def query_articles(
    q: Optional[str] = None,
    site_id: Optional[str] = None,
    criterion: Optional[str] = None,
    term: Optional[str] = None,
    column_group: Optional[str] = None,
    sentiment: Optional[str] = None,
    primary_category: Optional[str] = None,
    editorial_status: Optional[str] = None,
    osde_only: bool = False,
    hours: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "recent",
    limit: int = 300,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        clauses = ["1=1"]
        params: List[Any] = []

        if site_id:
            clauses.append("site_id = ?")
            params.append(site_id)
        if sentiment:
            clauses.append("sentiment_label = ?")
            params.append(sentiment)
        if primary_category:
            clauses.append("primary_category = ?")
            params.append(primary_category)
        if editorial_status:
            clauses.append("editorial_status = ?")
            params.append(editorial_status)
        if osde_only:
            clauses.append("is_osde_focus = 1")
        if hours and hours > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            clauses.append("published_at >= ?")
            params.append(cutoff)
        if date_from:
            clauses.append("published_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("published_at <= ?")
            params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)
        if criterion:
            clauses.append("criteria_json LIKE ?")
            params.append(f'%"{criterion}"%')
        if term:
            clauses.append("(matched_keywords_json LIKE ? OR matched_entities_json LIKE ?)")
            params.extend([f'%"{term}"%', f'%"{term}"%'])
        if column_group == "palabras_claves":
            clauses.append("matched_keywords_json != '[]'")
        elif column_group == "personalidades_otras_prepagas":
            clauses.append("matched_entities_json != '[]'")
        if q:
            like_q = f"%{q.strip()}%"
            clauses.append("(title LIKE ? OR executive_summary LIKE ? OR full_text LIKE ? OR site_name LIKE ? OR press_notes LIKE ?)")
            params.extend([like_q, like_q, like_q, like_q, like_q])

        order_map = {
            "recent": "published_at DESC, relevance_score DESC",
            "relevance": "relevance_score DESC, published_at DESC",
            "sentiment_desc": "sentiment_score DESC, published_at DESC",
            "sentiment_asc": "sentiment_score ASC, published_at DESC",
        }
        order_clause = order_map.get(sort_by, order_map["recent"])

        sql = f"""
            SELECT * FROM articles
            WHERE {' AND '.join(clauses)}
            ORDER BY {order_clause}
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [_deserialize_row(r) for r in rows]
    finally:
        conn.close()


def reanalyze_stored_articles() -> Dict[str, int]:
    """Re-evalúa artículos almacenados con las reglas actuales de NLP y elimina falsos positivos."""
    from app.nlp_engine import analyze_article

    sites_map = {s["id"]: s for s in (get_setting("sites", INITIAL_SITES) or [])}
    terms_catalog = [t for t in (get_setting("terms", INITIAL_KEYWORDS + INITIAL_COMPETITORS_AND_ENTITIES) or []) if t.get("enabled", True)]

    conn = get_connection()
    kept = 0
    removed = 0
    try:
        rows = conn.execute("SELECT * FROM articles").fetchall()
        with conn:
            for row in rows:
                site_cfg = sites_map.get(row["site_id"], {"id": row["site_id"], "foreign_paths": [], "argentina_strict": False})
                res = analyze_article(
                    url=row["url"],
                    title=row["title"],
                    summary=row["summary"] or "",
                    body=row["full_text"] or "",
                    site_cfg=site_cfg,
                    terms_catalog=terms_catalog,
                )
                if not res.get("accepted"):
                    conn.execute("DELETE FROM articles WHERE id = ?", (row["id"],))
                    removed += 1
                    continue
                conn.execute(
                    """
                    UPDATE articles
                    SET matched_keywords_json = ?, matched_entities_json = ?, subcategories_json = ?,
                        criteria_json = ?, primary_category = ?, sentiment_label = ?, sentiment_score = ?, relevance_score = ?,
                        executive_summary = ?, is_osde_focus = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(res["matched_keywords"], ensure_ascii=False),
                        json.dumps(res["matched_entities"], ensure_ascii=False),
                        json.dumps(res["subcategories"], ensure_ascii=False),
                        json.dumps(res["criteria"], ensure_ascii=False),
                        res["primary_category"],
                        res["sentiment_label"],
                        float(res["sentiment_score"]),
                        float(res["relevance_score"]),
                        res["executive_summary"],
                        1 if res["is_osde_focus"] else 0,
                        row["id"],
                    ),
                )
                kept += 1
    finally:
        conn.close()
    return {"kept": kept, "removed": removed}


def update_article_editorial(
    article_id: int,
    editorial_status: Optional[str] = None,
    press_notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Actualiza el estado editorial ('Pendiente' | 'Aprobada' | 'Descartada') y Notas Prensa."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row:
            return None
        updates: List[str] = []
        params: List[Any] = []
        if editorial_status is not None:
            if editorial_status not in ("Pendiente", "Aprobada", "Descartada"):
                raise ValueError("Estado editorial inválido")
            updates.append("editorial_status = ?")
            params.append(editorial_status)
        if press_notes is not None:
            updates.append("press_notes = ?")
            params.append(press_notes.strip())
        if updates:
            params.append(article_id)
            with conn:
                conn.execute(f"UPDATE articles SET {', '.join(updates)} WHERE id = ?", params)
        updated = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return _deserialize_row(updated) if updated else None
    finally:
        conn.close()


def get_article_by_id(article_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return _deserialize_row(row) if row else None
    finally:
        conn.close()


def log_scan_start() -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO scan_runs (started_at, status) VALUES (?, 'running')",
                (now,),
            )
            return int(cur.lastrowid)
    finally:
        conn.close()


def log_scan_finish(
    run_id: int,
    status: str,
    candidates_checked: int,
    articles_saved: int,
    sites_scanned: int,
    notes: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE scan_runs
                SET finished_at = ?, status = ?, candidates_checked = ?,
                    articles_saved = ?, sites_scanned = ?, notes = ?
                WHERE id = ?
                """,
                (now, status, candidates_checked, articles_saved, sites_scanned, notes, run_id),
            )
    finally:
        conn.close()


def get_recent_scans(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
