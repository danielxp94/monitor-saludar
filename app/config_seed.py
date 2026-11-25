"""Configuración semilla exacta basada en la matriz de criterios del usuario."""

from typing import List, Dict, Any

INITIAL_SITES: List[Dict[str, Any]] = [
    {
        "id": "infobae",
        "name": "Infobae",
        "url": "https://www.infobae.com/",
        "domain": "infobae.com",
        "periodicity": "Diaria",
        "color": "#f97316",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.infobae.com/arc/outboundfeeds/rss/",
            "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/",
            "https://www.infobae.com/arc/outboundfeeds/rss/category/sociedad/",
            "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/",
            "https://www.infobae.com/arc/outboundfeeds/rss/category/politica/",
        ],
        "section_urls": [
            "https://www.infobae.com/salud/",
            "https://www.infobae.com/economia/",
            "https://www.infobae.com/sociedad/",
        ],
        "foreign_paths": [
            "/colombia/", "/mexico/", "/peru/", "/espana/",
            "/estados-unidos/", "/america/", "/venezuela/",
            "/republica-dominicana/", "/chile/", "/uruguay/",
            "/ecuador/", "/bolivia/", "/paraguay/", "/centroamerica/",
            "/panama/", "/costa-rica/", "/guatemala/", "/honduras/",
            "/el-salvador/", "/nicaragua/", "/cuba/", "/puerto-rico/",
            "/brasil/", "/america-latina/", "/mundo/", "/teleshow/",
            "/entretenimiento/", "/deportes/", "/tendencias/",
        ],
    },
    {
        "id": "clarin",
        "name": "Clarín",
        "url": "https://www.clarin.com/",
        "domain": "clarin.com",
        "periodicity": "Diaria",
        "color": "#dc2626",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.clarin.com/rss/lo-ultimo/",
            "https://www.clarin.com/rss/sociedad/",
            "https://www.clarin.com/rss/economia/",
            "https://www.clarin.com/rss/politica/",
            "https://www.clarin.com/rss/buena-vida/",
        ],
        "section_urls": [
            "https://www.clarin.com/sociedad/",
            "https://www.clarin.com/economia/",
        ],
        "foreign_paths": ["/mundo/", "/internacional/", "/estados-unidos/"],
    },
    {
        "id": "lanacion",
        "name": "La Nación",
        "url": "https://www.lanacion.com.ar/",
        "domain": "lanacion.com.ar",
        "periodicity": "Diaria",
        "color": "#2563eb",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml",
            "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/sociedad/?outputType=xml",
            "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml",
            "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/politica/?outputType=xml",
        ],
        "section_urls": [
            "https://www.lanacion.com.ar/sociedad/",
            "https://www.lanacion.com.ar/economia/",
        ],
        "foreign_paths": ["/el-mundo/", "/estados-unidos/"],
    },
    {
        "id": "cronista",
        "name": "El Cronista",
        "url": "https://www.cronista.com/",
        "domain": "cronista.com",
        "periodicity": "Diaria",
        "color": "#059669",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.cronista.com/files/rss/news.xml",
            "https://www.cronista.com/files/rss/economia-politica.xml",
            "https://www.cronista.com/files/rss/negocios.xml",
            "https://www.cronista.com/files/rss/informacion-gral.xml",
        ],
        "section_urls": [
            "https://www.cronista.com/negocios/",
            "https://www.cronista.com/economia-politica/",
            "https://www.cronista.com/informacion-gral/",
        ],
        "foreign_paths": ["/internacionales/", "/mexico/", "/espana/", "/colombia/", "/usa/"],
    },
    {
        "id": "tn",
        "name": "TN (Todo Noticias)",
        "url": "https://tn.com.ar/",
        "domain": "tn.com.ar",
        "periodicity": "Diaria",
        "color": "#0284c7",
        "argentina_strict": False,
        "rss_feeds": [
            "https://tn.com.ar/arc/outboundfeeds/rss/?outputType=xml",
            "https://tn.com.ar/feed/",
        ],
        "section_urls": [
            "https://tn.com.ar/salud/",
            "https://tn.com.ar/economia/",
            "https://tn.com.ar/sociedad/",
        ],
        "foreign_paths": ["/internacional/"],
    },
    {
        "id": "eldiarioar",
        "name": "elDiarioAR",
        "url": "https://www.eldiarioar.com/",
        "domain": "eldiarioar.com",
        "periodicity": "Diaria",
        "color": "#4f46e5",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.eldiarioar.com/rss/",
            "https://www.eldiarioar.com/rss/sociedad/",
        ],
        "section_urls": [
            "https://www.eldiarioar.com/sociedad/",
            "https://www.eldiarioar.com/economia/",
            "https://www.eldiarioar.com/politica/",
        ],
        "foreign_paths": ["/mundo/", "/internacional/"],
    },
    {
        "id": "lpo",
        "name": "La Política Online",
        "url": "https://www.lapoliticaonline.com/",
        "domain": "lapoliticaonline.com",
        "periodicity": "Diaria",
        "color": "#7c3aed",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.lapoliticaonline.com/files/rss/ultimasnoticias.xml",
            "https://www.lapoliticaonline.com/files/rss/politica.xml",
            "https://www.lapoliticaonline.com/files/rss/economia.xml",
        ],
        "section_urls": [
            "https://www.lapoliticaonline.com/argentina/",
        ],
        "foreign_paths": [
            "/mexico/", "/espana/", "/usa/", "/brasil/",
            "/colombia/", "/paraguay/", "/internacionales/",
        ],
    },
    {
        "id": "forbes",
        "name": "Forbes Argentina",
        "url": "https://www.forbesargentina.com/",
        "domain": "forbesargentina.com",
        "periodicity": "Diaria",
        "color": "#0f172a",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.forbesargentina.com/rss.xml",
        ],
        "section_urls": [
            "https://www.forbesargentina.com/negocios",
            "https://www.forbesargentina.com/money",
            "https://www.forbesargentina.com/innovacion",
        ],
        "foreign_paths": ["/internacional/"],
    },
    {
        "id": "wired",
        "name": "Wired en Español",
        "url": "https://es.wired.com/",
        "domain": "es.wired.com",
        "periodicity": "Diaria",
        "color": "#18181b",
        "argentina_strict": True,  # Pan-hispánico: exige mención explícita de Argentina o entidades locales
        "rss_feeds": [
            "https://es.wired.com/feed/rss",
            "https://es.wired.com/feed/biotecnologia/rss",
        ],
        "section_urls": [
            "https://es.wired.com/ciencia",
            "https://es.wired.com/biotecnologia",
        ],
        "foreign_paths": [],
    },
    {
        "id": "perfil",
        "name": "Perfil",
        "url": "https://www.perfil.com/",
        "domain": "perfil.com",
        "periodicity": "Diaria",
        "color": "#b91c1c",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.perfil.com/feed",
            "https://www.perfil.com/feed/salud",
            "https://www.perfil.com/feed/economia",
            "https://www.perfil.com/feed/politica",
            "https://www.perfil.com/feed/sociedad",
        ],
        "section_urls": [
            "https://www.perfil.com/seccion/salud",
            "https://www.perfil.com/seccion/economia",
        ],
        "foreign_paths": [
            "/noticias/internacional/", "/noticias/bloomberg/",
            "caras.perfil.com", "exitoina.perfil.com", "/celebridades/",
        ],
    },
    {
        "id": "chequeado",
        "name": "Chequeado",
        "url": "https://chequeado.com/",
        "domain": "chequeado.com",
        "periodicity": "Diaria",
        "color": "#0d9488",
        "argentina_strict": False,
        "rss_feeds": [
            "https://chequeado.com/feed/",
            "https://chequeado.com/tag/salud/feed/",
        ],
        "section_urls": [
            "https://chequeado.com/el-explicador/",
            "https://chequeado.com/ultimas-noticias/",
        ],
        "foreign_paths": [],
    },
    {
        "id": "pagina12",
        "name": "Página/12",
        "url": "https://www.pagina12.com.ar/",
        "domain": "pagina12.com.ar",
        "periodicity": "Diaria",
        "color": "#0369a1",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.pagina12.com.ar/rss/portada",
            "https://www.pagina12.com.ar/rss/secciones/sociedad/notas",
            "https://www.pagina12.com.ar/rss/secciones/economia/notas",
            "https://www.pagina12.com.ar/rss/secciones/el-pais/notas",
        ],
        "section_urls": [
            "https://www.pagina12.com.ar/secciones/sociedad",
            "https://www.pagina12.com.ar/secciones/economia",
        ],
        "foreign_paths": ["/secciones/el-mundo/"],
    },
    {
        "id": "lavoz",
        "name": "La Voz del Interior",
        "url": "https://www.lavoz.com.ar/",
        "domain": "lavoz.com.ar",
        "periodicity": "Diaria",
        "color": "#be123c",
        "argentina_strict": False,
        "rss_feeds": [
            "https://www.lavoz.com.ar/arc/outboundfeeds/rss/category/ciudadanos/?outputType=xml",
        ],
        "section_urls": [
            "https://www.lavoz.com.ar/ciudadanos/",
        ],
        "foreign_paths": ["/mundo/"],
    },
]

# Columna C: Palabras claves (15 ítems exactos de la planilla)
INITIAL_KEYWORDS: List[Dict[str, Any]] = [
    {"term": "OSDE", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": [], "context_required": False, "weight": 3.0},
    {"term": "Cristian García Sarubbi", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["Cristian Garcia Sarubbi", "García Sarubbi", "Garcia Sarubbi"], "context_required": False, "weight": 3.0},
    {"term": "Martín Pochat", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["Martin Pochat"], "context_required": False, "weight": 3.0},
    {"term": "Guido Montaruli", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["Montaruli"], "context_required": False, "weight": 3.0},
    {"term": "prepaga", "column": "palabras_claves", "subcategory": "Sector Salud", "aliases": [], "context_required": False, "weight": 2.2},
    {"term": "prepagas", "column": "palabras_claves", "subcategory": "Sector Salud", "aliases": [], "context_required": False, "weight": 2.2},
    {"term": "medicina privada", "column": "palabras_claves", "subcategory": "Sector Salud", "aliases": ["medicina prepaga"], "context_required": False, "weight": 2.4},
    {"term": "salud", "column": "palabras_claves", "subcategory": "Sector Salud", "aliases": [], "context_required": True, "weight": 1.0},
    {"term": "obras sociales", "column": "palabras_claves", "subcategory": "Sector Salud", "aliases": [], "context_required": False, "weight": 2.2},
    {"term": "obra social", "column": "palabras_claves", "subcategory": "Sector Salud", "aliases": [], "context_required": False, "weight": 2.2},
    {"term": "Bina", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["OSDE Bina", "Binaria"], "context_required": True, "weight": 2.8},
    {"term": "URG Urgencias", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["URG"], "context_required": True, "weight": 2.8},
    {"term": "Interturis", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": [], "context_required": False, "weight": 2.8},
    {"term": "Fundación OSDE", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["Fundacion OSDE"], "context_required": False, "weight": 3.0},
    {"term": "Flux", "column": "palabras_claves", "subcategory": "Grupo OSDE", "aliases": ["Flux by OSDE", "Plan Flux", "OSDE Flux"], "context_required": True, "weight": 2.8},
]

# Columna D: Personalidades o noticias sobre otras prepagas (20 ítems exactos de la planilla)
INITIAL_COMPETITORS_AND_ENTITIES: List[Dict[str, Any]] = [
    {"term": "Claudio Belocopitt", "column": "personalidades_otras_prepagas", "subcategory": "Personalidades", "aliases": ["Belocopitt"], "context_required": False, "weight": 2.8},
    {"term": "UAS", "column": "personalidades_otras_prepagas", "subcategory": "Cámaras y Entidades", "aliases": [], "context_required": True, "weight": 2.5},
    {"term": "Unión Argentina de Salud", "column": "personalidades_otras_prepagas", "subcategory": "Cámaras y Entidades", "aliases": ["Union Argentina de Salud"], "context_required": False, "weight": 2.8},
    {"term": "Hugo Magonza", "column": "personalidades_otras_prepagas", "subcategory": "Personalidades", "aliases": ["Magonza"], "context_required": False, "weight": 2.8},
    {"term": "Superintendencia de servicios de salud", "column": "personalidades_otras_prepagas", "subcategory": "Reguladores", "aliases": ["Superintendencia de Servicios de Salud", "Superintendencia de Salud"], "context_required": False, "weight": 3.0},
    {"term": "Superintendente de servicios de salud", "column": "personalidades_otras_prepagas", "subcategory": "Reguladores", "aliases": ["Superintendente de Servicios de Salud"], "context_required": False, "weight": 3.0},
    {"term": "ANEFiTS", "column": "personalidades_otras_prepagas", "subcategory": "Reguladores", "aliases": ["ANEFITS", "Agencia Nacional de Evaluación de Financiamiento de Tecnologías Sanitarias"], "context_required": False, "weight": 3.0},
    {"term": "ANMAT", "column": "personalidades_otras_prepagas", "subcategory": "Reguladores", "aliases": ["Administración Nacional de Medicamentos"], "context_required": False, "weight": 2.6},
    {"term": "Luis Fontana", "column": "personalidades_otras_prepagas", "subcategory": "Personalidades", "aliases": [], "context_required": False, "weight": 2.8},
    {"term": "Galeno", "column": "personalidades_otras_prepagas", "subcategory": "Otras Prepagas", "aliases": ["Galeno Salud"], "context_required": True, "weight": 2.5},
    {"term": "Medife", "column": "personalidades_otras_prepagas", "subcategory": "Otras Prepagas", "aliases": ["Medifé"], "context_required": False, "weight": 2.6},
    {"term": "Sancor Salud", "column": "personalidades_otras_prepagas", "subcategory": "Otras Prepagas", "aliases": ["SanCor Salud"], "context_required": False, "weight": 2.6},
    {"term": "Swiss Medical", "column": "personalidades_otras_prepagas", "subcategory": "Otras Prepagas", "aliases": ["Swiss Medical Group"], "context_required": False, "weight": 2.6},
    {"term": "Omint", "column": "personalidades_otras_prepagas", "subcategory": "Otras Prepagas", "aliases": ["Grupo Omint"], "context_required": False, "weight": 2.6},
    {"term": "Medicamentos", "column": "personalidades_otras_prepagas", "subcategory": "Prestaciones e Insumos", "aliases": ["medicamento"], "context_required": True, "weight": 1.6},
    {"term": "Cartilla", "column": "personalidades_otras_prepagas", "subcategory": "Prestaciones e Insumos", "aliases": ["cartilla médica", "cartilla de prestadores"], "context_required": True, "weight": 1.8},
    {"term": "Sanatorio", "column": "personalidades_otras_prepagas", "subcategory": "Prestaciones e Insumos", "aliases": ["sanatorios"], "context_required": True, "weight": 1.5},
    {"term": "Clínica", "column": "personalidades_otras_prepagas", "subcategory": "Prestaciones e Insumos", "aliases": ["Clinica", "clínicas", "clinicas"], "context_required": True, "weight": 1.4},
    {"term": "Hospital", "column": "personalidades_otras_prepagas", "subcategory": "Prestaciones e Insumos", "aliases": ["hospitales"], "context_required": True, "weight": 1.4},
    {"term": "Telemedicina", "column": "personalidades_otras_prepagas", "subcategory": "Prestaciones e Insumos", "aliases": ["teleconsulta", "salud digital"], "context_required": False, "weight": 2.2},
]

# Columna E: Limitaciones
INITIAL_LIMITATIONS: Dict[str, Any] = {
    "geo_scope": "Sólo Argentina",
    "periodicity": "Diaria",
    "daily_hour": "08:00",
}

# Columna F: Criterios temáticos
INITIAL_CRITERIA: List[str] = [
    "Salud",
    "Normativas de salud",
    "Resoluciones de la superintendencia",
]
