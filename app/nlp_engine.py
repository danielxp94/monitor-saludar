"""Motor local y gratuito de NLP: Entidades, Filtro 'Sólo Argentina', Criterios, Sentimiento y Clustering."""

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Set, Tuple


def strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def normalize_text(text: str) -> str:
    return strip_accents(text or "").lower()


# Indicadores geográficos explícitos de Argentina
ARGENTINA_POSITIVE_MARKERS = [
    "argentina", "argentino", "argentinos", "argentina", "buenos aires", "caba",
    "porteño", "porteña", "conurbano", "pba", "cordoba", "rosario", "mendoza",
    "santa fe", "tucuman", "neuquen", "salta", "entre rios", "misiones", "chaco",
    "corrientes", "san juan", "jujuy", "rio negro", "chubut", "santa cruz",
    "tierra del fuego", "la pampa", "catamarca", "la rioja", "san luis", "formosa",
    "santiago del estero", "osde", "swiss medical", "galeno", "medife", "omint",
    "sancor salud", "anmat", "anefits", "pami", "ioma", "garrahan", "posadas",
    "superintendencia de servicios de salud", "union argentina de salud",
    "belocopitt", "magonza", "lugones", "milei", "kicillof", "macri", "conicet",
    "ministerio de salud de la nacion", "boletin oficial", "pesos", "afip", "arca",
]

# Marcadores fuertes de que una nota es puramente extranjera si no menciona Argentina
FOREIGN_COUNTRIES_AND_AGENCIES = [
    # Países y territorios extranjeros
    "espana", "mexico", "colombia", "peru", "chile", "uruguay", "venezuela",
    "republica dominicana", "ecuador", "bolivia", "paraguay", "cuba", "panama",
    "costa rica", "guatemala", "puerto rico", "honduras", "el salvador", "nicaragua",
    "estados unidos", "ee.uu", "eeuu", "canada", "reino unido", "gran bretana",
    "inglaterra", "francia", "alemania", "italia", "portugal", "suiza", "suecia",
    "noruega", "dinamarca", "paises bajos", "holanda", "belgica", "irlanda",
    "israel", "gaza", "palestina", "ucrania", "rusia", "polonia", "iran", "irak",
    "china", "japon", "corea del sur", "india", "australia", "nueva zelanda",
    "sudafrica", "egipto", "marruecos", "turquia",
    # Gentilicios y ciudades extranjeras
    "espanol", "espanola", "mexicano", "mexicana", "colombiano", "colombiana",
    "peruano", "peruana", "chileno", "chilena", "panameno", "panamena",
    "dominicano", "dominicana", "ecuatoriano", "ecuatoriana", "venezolano", "venezolana",
    "estadounidense", "estadounidenses", "britanico", "britanica",
    "madrid", "barcelona", "bogota", "medellin", "cdmx", "tijuana", "cancun",
    "lima", "santiago de chile", "santo domingo", "quito", "guayaquil",
    "montevideo", "asuncion", "caracas", "ciudad de panama", "nueva york",
    "washington", "california", "miami", "londres", "paris", "roma", "berlin", "tokio",
    # Ministerios y organismos sanitarios extranjeros
    "minsa", "imss", "issste", "cofepris", "invima", "medicare", "medicaid",
    "gofundme", "nhs", "fonasa", "isapre", "isapres", "eps en colombia",
    "sanidad espanola", "seguridad social espanola", "reforma a la salud de petro",
    "indotel", "fda de estados unidos", "en wall street",
]

FOREIGN_HEADLINE_REGEXES = [
    (term, re.compile(r"\b" + re.escape(term) + r"\b"))
    for term in FOREIGN_COUNTRIES_AND_AGENCIES
]

# Contexto sanitario para desambiguar términos amplios ("salud", "hospital", "clínica", "cartilla", "flux", "bina")
HEALTHCARE_CONTEXT_WORDS = [
    "salud", "medic", "prepaga", "obra social", "obras sociales", "paciente",
    "tratamiento", "enfermedad", "clinica", "sanatorio", "hospital", "farmac",
    "remedio", "medicamento", "receta", "cobertura", "afiliad", "cuota",
    "prestador", "prestacion", "odontolog", "psicolog", "cirugia", "terapia",
    "vacuna", "anmat", "superintendencia", "ministerio de salud", "pami", "ioma",
    "osde", "swiss medical", "galeno", "medife", "omint", "sancor", "ambulancia",
    "emergencia", "urgencia", "diagnostico", "oncolog", "pediatr", "guardia",
    "residente", "profesionales de la salud", "sistema sanitario", "sanitaria",
    "sanitario", "epidemiolog", "dengue", "virus", "biotecnolog", "telemedicina",
    "cartilla", "pmo", "discapacidad", "reintegro", "coseguro", "copago",
]

# Patrones de exclusión en titular del script de referencia (lifestyle, clima, deportes, ciudades/países extranjeros)
EXCLUDED_TITLE_PATTERNS = [
    # Lifestyle / Comida / Fitness
    "receta", "dieta", "ejercicios para", "rutina de", "horoscopo", "signo del zodiaco",
    "desayuno saludable", "perder peso", "adelgazar", "quemar grasa", "quemar mas grasa",
    "bajar la panza", "truco casero", "infusion", "te de", "licuado", "batido",
    "comer sardinas", "prepararlas", "prepararlo", "black forest labs",
    # Clima y pronósticos
    "clima", "estado del tiempo", "prediccion del clima", "pronostico del tiempo",
    "temperaturas que predominaran",
    # Países, ciudades y organismos extranjeros (Filtro "Sólo Argentina")
    "mexico", "mexicano", "mexicana", "tijuana", "cancun", "puerto vallarta", "unam",
    "colombia", "colombiano", "colombiana",
    "espana", "espanol", "espanola", "torrevieja", "benidorm", "coslada", "cadiz",
    "chile", "chileno", "chilena",
    "peru", "peruano", "peruana",
    "guatemala", "republica dominicana",
    "estados unidos", "estadounidense", "estadounidenses", "medicare", "gofundme",
    # Deportes
    "futbol", "gol de", "var", "liguilla", "liga mx", "pumas", "chivas", "america",
    "arquero", "delantero", "defensor", "mediocampista", "dt", "entrenador", "director tecnico",
    "torneo", "campeonato", "libertadores", "sudamericana", "champions", "premier league", "la liga",
    "partido", "estadio", "cancha", "fichaje", "traspaso", "clasico", "seleccion",
    "boca", "river", "racing", "independiente", "san lorenzo", "messi", "scaloni",
    "simeone", "atletico de madrid", "real madrid", "barcelona", "cuti romero",
    "tenis", "rugby", "basquet", "nba", "formula 1", "colapinto",
    # Astronomía, tecnología ajena y portadas índice
    "sistema solar", "estela", "jefe de ia", "meta", "violencia politica", "anibal gordon",
    "phil knight", "nike", "noticias de salud hoy",
]

EXCLUDED_TITLE_REGEXES = [
    re.compile(r"(?:^|\s)" + re.escape(p) + r"(?:\s|$)") for p in EXCLUDED_TITLE_PATTERNS
]

REGEX_SALUD_TITULO = re.compile(
    r"salud|medic|clinic|hospital|sanatorio|enfermedad|paciente|tratamiento|diagnostic|"
    r"estudio clinico|estudio medico|estudio cientifico|alzheimer|cancer|diabetes|infarto|"
    r"acv|cardiac|angioplastia|analisis de sangre|biopsia|vacuna|virus|covid|dengue|"
    r"sarampion|prepaga|obra social|farmacia|farmaco|laboratorio|anmat|terapia|cirugia|"
    r"sintoma|cerebro|corazon|oncolog|trasplante|vitamina",
    re.I,
)

# Contexto policial / accidentes viales / deportes / mascotas que genera ruido cuando solo aparece "hospital" o "salud"
NON_HEALTH_NOISE_HEADLINE = [
    "choque", "chocaron", "volco", "atropello", "motociclista", "apuñalo",
    "balearon", "tiroteo", "asesinaron", "homicidio", "robo", "ladron",
    "delincuente", "detuvieron", "femicidio", "incendio en una casa",
    "parte medico de boca", "parte medico de river", "lesion de messi",
    "eliminatorias", "copa libertadores", "torneo apertura", "torneo clausura",
    "gran hermano", "horoscopo", "adiestrador canino", "llevar al perro",
    "llevar al gato", "mascotas", "aspirantes a cabo", "inscripcion para aspirantes",
    "premio fundacion medife", "fundacion medife filba",
]

SUPERINTENDENCIA_MARKERS = [
    "superintendencia de servicios de salud",
    "superintendente de servicios de salud",
    "superintendencia de salud",
    "sss",
    "desregulacion de obras sociales",
    "registro nacional de agentes del seguro",
    "fondo solidario de redistribucion",
    "agente del seguro de salud",
]

NORMATIVA_MARKERS = [
    "resolucion", "resoluciones", "decreto", "dnu", "boletin oficial",
    "disposicion", "normativa", "reglamentacion", "reglamento", "ley ",
    "proyecto de ley", "amparo", "fallo judicial", "corte suprema", "justicia ordeno",
    "cautelar", "medida cautelar", "anmat prohibio", "anmat aprobo", "anmat autorizo",
    "anefits", "ministerio de salud", "programa medico obligatorio", "pmo",
    "receta electronica", "intimacion", "multa", "sancion", "homologacion",
    "desregulacion",
]

POSITIVE_WORDS = [
    "inversion", "innovacion", "acuerdo", "alianza", "mejora", "apertura",
    "inauguro", "inauguracion", "avance", "exitoso", "exito", "beneficio",
    "descuento", "crecimiento", "ampliacion", "aprobo", "autorizo", "incorporacion",
    "tecnologia", "modernizacion", "prevencion", "gratuito", "premio", "distincion",
    "recuperacion", "nuevo centro", "nueva sede", "capacitacion", "solidaridad",
]

NEGATIVE_WORDS = [
    "aumento", "aumentos", "suba", "subas", "crisis", "reclamo", "reclamos",
    "denuncia", "denuncias", "conflicto", "paro", "medida de fuerza", "prohibio",
    "retiro del mercado", "alerta", "escasez", "faltante", "desabastecimiento",
    "deuda", "recorte", "ajuste", "baja de afiliados", "cierre", "quiebra",
    "irregularidades", "fraude", "estafa", "multa", "intimacion", "amparo",
    "cautelar", "judicializacion", "demora", "quejas", "inflacion", "desfinanciamiento",
    "epidemia", "brote", "muerte", "fallecio", "grave",
]

SPANISH_STOPWORDS: Set[str] = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "pero",
    "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "tambien", "me", "hasta", "hay", "donde", "quien",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra",
    "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mi", "antes", "algunos",
    "que", "unos", "yo", "otro", "otras", "otra", "el", "tanto", "esa", "estos",
    "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar",
    "estas", "algunas", "algo", "nosotros", "mi", "mis", "tu", "te", "ti",
    "fue", "son", "ser", "era", "han", "ha", "sido", "tiene", "tienen", " tras",
    "segun", "cada", "asi", "parte", "puede", "pueden", "nuevo", "nueva", "nuevos",
    "nuevas", "anos", "ano", "dia", "dias", "mes", "meses", "hoy", "ayer", "semana",
}


def check_argentina_only(
    url: str,
    title: str,
    summary: str,
    body: str,
    site_cfg: Dict[str, Any],
) -> Tuple[bool, str]:
    """Valida la limitación 'Sólo Argentina' para descartar notas internacionales."""
    url_lower = (url or "").lower()
    norm_head = normalize_text(f"{title} {summary}")
    norm_full = normalize_text(f"{title} {summary} {(body or '')[:2000]}")

    has_ar_head = any(
        re.search(r"\b" + re.escape(m) + r"\b", norm_head)
        for m in ARGENTINA_POSITIVE_MARKERS
    )
    has_ar_full = has_ar_head or any(
        re.search(r"\b" + re.escape(m) + r"\b", norm_full)
        for m in ARGENTINA_POSITIVE_MARKERS
    )

    # 1. Revisar rutas extranjeras explícitas en la URL (ej. infobae.com/panama/, infobae.com/colombia/)
    for fpath in site_cfg.get("foreign_paths", []):
        if fpath.lower() in url_lower and not has_ar_head:
            return False, f"Ruta internacional excluida ({fpath})"

    # 1b. Detección universal de rutas de ediciones extranjeras en URLs aunque no estén listadas en el medio
    universal_foreign_slugs = [
        "/panama/", "/mexico/", "/colombia/", "/peru/", "/espana/",
        "/republica-dominicana/", "/estados-unidos/", "/venezuela/",
        "/ecuador/", "/bolivia/", "/costa-rica/", "/guatemala/",
        "/chile/", "/uruguay/", "/paraguay/", "/america-latina/",
    ]
    for slug in universal_foreign_slugs:
        if slug in url_lower and not has_ar_head:
            return False, f"Sección internacional excluida ({slug})"

    # 2. Si el titular/bajada menciona un país, ciudad o ente sanitario extranjero y no menciona Argentina
    for term, rx in FOREIGN_HEADLINE_REGEXES:
        if rx.search(norm_head) and not has_ar_head:
            return False, f"Nota internacional detectada ({term})"
    if re.search(r"\bbrasil\b", norm_head) and not has_ar_head and "viaj" not in norm_head:
        return False, "Nota internacional detectada (brasil)"

    # 2b. Si los primeros párrafos de la nota son de agencia/contexto extranjero (ej. HealthDay News EE.UU.) sin referencia a Argentina
    lead_body = norm_full[:900]
    if ("healthday news" in lead_body or "europa press" in lead_body) and not has_ar_full:
        return False, "Cable internacional sindicado sin referencia a Argentina"
    if not has_ar_full:
        for term, rx in FOREIGN_HEADLINE_REGEXES:
            if rx.search(lead_body):
                return False, f"Contexto geográfico extranjero en desarrollo ({term})"

    # 3. Para medios pan-hispánicos (ej. es.wired.com), exigir mención explícita de Argentina
    if site_cfg.get("argentina_strict", False) and not has_ar_full:
        return False, "Medio regional sin referencia explícita a Argentina"

    return True, "Argentina"


def _has_healthcare_context(norm_text: str, min_hits: int = 2) -> bool:
    hits = 0
    for w in HEALTHCARE_CONTEXT_WORDS:
        if w in norm_text:
            hits += 1
            if hits >= min_hits:
                return True
    return False


def classify_primary_category(
    matched_terms: List[str],
    title: str,
    norm_full: str,
    es_salud_general: bool = False,
) -> str:
    """Jerarquía de 13 categorías editoriales alineadas a Prensa OSDE."""
    m_norm = {normalize_text(m) for m in matched_terms if m}
    t_norm = re.sub(r"[^a-z0-9\s]", " ", normalize_text(title))

    def has_any_term(candidates: List[str]) -> bool:
        return any(normalize_text(c) in m_norm for c in candidates)

    def text_has_any(phrases: List[str]) -> bool:
        return any(normalize_text(p) in t_norm or normalize_text(p) in norm_full for p in phrases)

    # 1. OSDE & Ecosistema (Máxima prioridad)
    if has_any_term([
        "osde", "bina", "urg urgencias", "interturis", "fundacion osde", "flux",
        "martin pochat", "cristian garcia sarubbi", "guido montaruli",
        "osde neo", "plan 210", "plan 310", "plan 410", "cartilla",
    ]) or re.search(r"\bosde\b", t_norm):
        return "OSDE & Ecosistema"

    # 2. OSDE Institucional & Unidades
    if text_has_any(["binaria", "binaria seguros", "premio osde", "auditorio osde", "carrera osde"]):
        return "OSDE Institucional & Unidades"

    # 3. Competencia & Sector Prepagas
    if has_any_term([
        "swiss medical", "galeno", "medicus", "medife", "omint", "sancor salud",
        "hospital italiano", "medicina privada", "prepaga", "prepagas",
        "obras sociales", "obra social", "claudio belocopitt", "hugo magonza",
        "luis fontana", "uas", "union argentina de salud",
    ]):
        return "Competencia & Sector Prepagas"

    # 4. Normativa & Regulaciones
    if has_any_term([
        "superintendencia de servicios de salud", "superintendente de servicios de salud",
        "anmat", "anefits",
    ]) or re.search(r"\b(resolucion|normativa|amparo|cautelar|dnu|desregulacion|boletin oficial)\b", t_norm):
        return "Normativa & Regulaciones"

    # 5. Economía & Costos
    if re.search(r"\b(aumento|cuotas|copago|copagos|arancel|honorarios|inflacion)\b", t_norm) or text_has_any([
        "aumento de prepagas", "aumento de cuota", "cuota de las prepagas"
    ]):
        return "Economía & Costos"

    # 6. Experiencia del Paciente & Reclamos
    if text_has_any([
        "defensa del consumidor", "defensa al consumidor", "coprec", "mala praxis",
        "abandono de persona", "demora en turnos", "falta de profesionales", "fuga de medicos",
    ]):
        return "Experiencia del Paciente & Reclamos"

    # 7. Gremiales & Recursos Humanos
    if text_has_any([
        "paro de medicos", "paro de sanidad", "conflicto gremial", "fatsa",
        "paritarias", "sindicato de sanidad", "hector daer", "medicos residentes",
        "retencion de tareas", "medida de fuerza",
    ]):
        return "Gremiales & Recursos Humanos"

    # 8. Coberturas & PMO
    if text_has_any([
        "programa medico obligatorio", "epof", "enfermedades poco frecuentes",
        "certificado de discapacidad", "reproduccion asistida", "fertilidad",
        "ley de salud mental", "salud mental",
    ]) or re.search(r"\b(pmo|cud|discapacidad)\b", t_norm):
        return "Coberturas & PMO"

    # 9. Industria Farmacéutica & Insumos
    if text_has_any([
        "cilfa", "caeme", "industria farmaceutica", "importacion de insumos",
        "insumos medicos", "droguerias", "escasez de medicamentos", "laboratorios",
    ]):
        return "Industria Farmacéutica & Insumos"

    # 10. Prestadores & Servicios
    if has_any_term(["clinica", "sanatorio", "hospital"]) or text_has_any([
        "receta electronica", "colegio medico", "profesionales de la salud", "prestadores"
    ]):
        return "Prestadores & Servicios"

    # 11. Tecnología & Salud Digital
    if has_any_term(["telemedicina"]) or text_has_any([
        "credencial digital", "turnos online", "portal del paciente", "salud digital",
        "healthtech", "startup de salud", "biotecnologia",
    ]):
        return "Tecnología & Salud Digital"

    # 12. Salud Pública & Epidemiología
    if re.search(r"\b(covid|dengue|vacuna|vacunacion|brote|epidemia|virus|sarampion|oms)\b", t_norm):
        return "Salud Pública & Epidemiología"

    # 13. Salud Positiva, Bienestar & Avances
    if re.search(
        r"\b(alzheimer|cancer|diabetes|infarto|acv|cardiaco|angioplastia|diagnostico|"
        r"analisis de sangre|biopsia|nuevo tratamiento|avance contra|cura para|como prevenir|"
        r"mejorar la salud|calidad de vida|estudio cientifico|ensayo clinico|inmunoterapia|"
        r"terapia genica|celulas madre|medicina preventiva|longevidad)\b",
        t_norm,
    ):
        return "Salud Positiva, Bienestar & Avances"

    return "Salud Positiva, Bienestar & Avances" if es_salud_general else "Mercado & Prepagas"


def analyze_article(
    url: str,
    title: str,
    summary: str,
    body: str,
    site_cfg: Dict[str, Any],
    terms_catalog: List[Dict[str, Any]],
    accept_health_section: bool = False,
    require_health_title: bool = True,
) -> Dict[str, Any]:
    """
    Evalúa relevancia, Limitación ('Sólo Argentina'), Palabras claves (Col C),
    Personalidades/Otras Prepagas (Col D), Criterios (Col F), Sentimiento, Resumen y Categoría Prensa.
    """
    is_ar, ar_reason = check_argentina_only(url, title, summary, body, site_cfg)
    if not is_ar:
        return {"accepted": False, "reason": ar_reason}

    full_text = f"{title}\n{summary}\n{body or ''}"
    norm_title = normalize_text(title)
    norm_title_clean = re.sub(r"[^a-z0-9\s]", " ", norm_title)
    norm_title_clean = re.sub(r"\s+", " ", norm_title_clean).strip()
    url_low = (url or "").lower()

    # Descartar portadas de tags/temas o subdominios de farándula/celebridades
    if any(p in url_low for p in ["/tags/", "/tag/", "/tema/", "/temas/", "caras.perfil.com", "exitoina.perfil.com", "/celebridades/", "/mascotas/", "/horoscopo/", "/astrologia/"]):
        return {"accepted": False, "reason": "Página índice de etiquetas o sección de farándula/mascotas"}
    if re.match(r"^(ultimas noticias de|noticias de)\b", norm_title_clean):
        return {"accepted": False, "reason": "Portada índice de tema"}

    # Excluir titulares de lifestyle/clima/deportes/extranjeros salvo mención explícita de OSDE o prepagas argentinas
    if any(rx.search(norm_title_clean) for rx in EXCLUDED_TITLE_REGEXES):
        if not re.search(r"\b(osde|prepaga|prepagas|anmat|superintendencia)\b", norm_title_clean):
            return {"accepted": False, "reason": "Titular descartado por patrón de exclusión (deportes/clima/lifestyle/extranjero)"}

    norm_lead = normalize_text(f"{title} {summary}")
    norm_full = normalize_text(full_text)

    # Buscar coincidencias exactas por límites de palabra en todo el catálogo
    matched_keywords: List[str] = []
    matched_entities: List[str] = []
    matched_subcategories: Set[str] = set()
    relevance_score = 0.0
    strong_entity_hit = False

    has_health_ctx = _has_healthcare_context(norm_full, min_hits=2)
    has_lead_health_ctx = _has_healthcare_context(norm_lead, min_hits=1)

    for item in terms_catalog:
        if not item.get("enabled", True):
            continue
        canonical = item["term"]
        variants = [canonical] + list(item.get("aliases", []))
        needs_ctx = bool(item.get("context_required", False))
        weight = float(item.get("weight", 1.5))

        found_in_title = False
        found_in_body = False

        for variant in variants:
            norm_v = normalize_text(variant)
            if not norm_v:
                continue
            pattern = r"\b" + re.escape(norm_v) + r"\b"
            if re.search(pattern, norm_lead):
                found_in_title = True
                break
            elif re.search(pattern, norm_full):
                found_in_body = True

        if not (found_in_title or found_in_body):
            continue

        # Reglas especiales de desambiguación para evitar falsos positivos
        norm_canon = normalize_text(canonical)
        if norm_canon in ("bina", "flux"):
            # Exigir contexto OSDE o salud/prepaga explícito
            if not re.search(r"\b(osde|prepaga|prepagas|salud|medicina|plan)\b", norm_full):
                continue
        elif norm_canon == "uas":
            # Exigir mayúsculas 'UAS' en texto original + contexto salud (no 'drones UAS')
            if not re.search(r"\bUAS\b", full_text) or not has_health_ctx:
                continue
        elif norm_canon == "medife":
            # Evitar el premio literario "Fundación Medifé Filba" cuando no habla del sistema de salud
            if ("filba" in norm_full or "premio fundacion medife" in norm_full) and not re.search(
                r"\b(prepaga|prepagas|obra social|obras sociales|afiliad|cobertura|cuota|cartilla|clinica|sanatorio)\b",
                norm_full,
            ):
                continue
        elif norm_canon == "salud":
            # Evitar "salud financiera", "salud económica", "¡salud!"
            if re.search(r"salud (financiera|economica|fiscal|cambiaria|democratica)", norm_full) and not _has_healthcare_context(norm_full, min_hits=3):
                continue
            if not _has_healthcare_context(norm_full, min_hits=3):
                continue
        elif norm_canon == "cartilla":
            if not re.search(r"\b(medica|prestadores|prepaga|obra social|salud|osde|afiliad)\b", norm_full):
                continue
        elif needs_ctx and not has_health_ctx:
            continue

        # Acumular puntaje (mayor peso si aparece en titular/bajada)
        hit_score = weight * (2.0 if found_in_title else 1.0)
        relevance_score += hit_score
        if weight >= 2.2:
            strong_entity_hit = True

        if item["column"] == "palabras_claves":
            matched_keywords.append(canonical)
        else:
            matched_entities.append(canonical)
        matched_subcategories.add(item.get("subcategory", "General"))

    direct_health_accepted = False
    if not matched_keywords and not matched_entities:
        if accept_health_section and (not require_health_title or REGEX_SALUD_TITULO.search(norm_title_clean)):
            direct_health_accepted = True
            matched_keywords.append("salud")
            matched_subcategories.add("Salud Positiva & Avances")
            relevance_score = max(relevance_score, 2.5)
        else:
            return {"accepted": False, "reason": "Sin coincidencias con las palabras clave o personalidades"}

    # Descartar secciones ajenas a salud humana (ej. /mascotas/, /horoscopo/) salvo mención explícita de prepaga/regulador
    url_low = (url or "").lower()
    if any(p in url_low for p in ["/mascotas/", "/horoscopo/", "/astrologia/"]) and not strong_entity_hit:
        return {"accepted": False, "reason": "Sección no sanitaria (mascotas/horóscopo)"}

    # Filtro anti-ruido (ej. choques de tránsito, policiales, mascotas o lesiones deportivas donde solo dice "fue llevado al hospital")
    weak_generic_only = (
        not direct_health_accepted
        and not strong_entity_hit
        and set(normalize_text(x) for x in (matched_keywords + matched_entities)).issubset(
            {"salud", "hospital", "clinica", "sanatorio", "medicamentos", "cartilla"}
        )
    )
    if weak_generic_only:
        if any(noise in norm_lead for noise in NON_HEALTH_NOISE_HEADLINE):
            return {"accepted": False, "reason": "Descartada por contexto policial/vial/deportivo/mascotas no sanitario"}
        if not has_lead_health_ctx or relevance_score < 2.4:
            return {"accepted": False, "reason": "Mención tangencial sin foco principal en salud"}

    # Clasificación en los 3 Criterios de la Columna F:
    # 1) "Salud"
    # 2) "Normativas de salud"
    # 3) "Resoluciones de la superintendencia"
    criteria: List[str] = []

    has_sss = (
        "Superintendencia de servicios de salud" in matched_entities
        or "Superintendente de servicios de salud" in matched_entities
        or any(
            (
                re.search(r"\bsss\b", norm_full) and has_health_ctx
                if m == "sss"
                else m in norm_full
            )
            for m in SUPERINTENDENCIA_MARKERS
        )
    )
    has_normativa = (
        "ANEFiTS" in matched_entities
        or "ANMAT" in matched_entities
        or any(m in norm_lead or m in norm_full[:1800] for m in NORMATIVA_MARKERS)
    )

    if has_sss and (
        has_normativa
        or any(w in norm_full for w in ["resolucion", "decreto", "dispuso", "oficializo", "padron", "obras sociales", "prepagas"])
    ):
        criteria.append("Resoluciones de la superintendencia")

    if has_normativa or "Resoluciones de la superintendencia" in criteria:
        criteria.append("Normativas de salud")

    # Criterio base sectorial
    if "Salud" not in criteria:
        criteria.append("Salud")

    # Análisis de sentimiento local (-1.0 a +1.0)
    pos_hits = sum(1 for w in POSITIVE_WORDS if re.search(r"\b" + re.escape(w), norm_full[:2500]))
    neg_hits = sum(1 for w in NEGATIVE_WORDS if re.search(r"\b" + re.escape(w), norm_full[:2500]))
    # Doble peso en el titular
    pos_hits += sum(1 for w in POSITIVE_WORDS if re.search(r"\b" + re.escape(w), norm_title))
    neg_hits += sum(1 for w in NEGATIVE_WORDS if re.search(r"\b" + re.escape(w), norm_title))

    total_polar = pos_hits + neg_hits
    if total_polar == 0:
        sentiment_score = 0.0
        sentiment_label = "Neutro"
    else:
        sentiment_score = round((pos_hits - neg_hits) / max(total_polar, 3), 2)
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        if sentiment_score >= 0.22:
            sentiment_label = "Positivo"
        elif sentiment_score <= -0.22:
            sentiment_label = "Negativo"
        else:
            sentiment_label = "Neutro"

    # Resumen ejecutivo extractivo si tenemos cuerpo completo
    exec_summary = generate_extractive_summary(title, summary, body, matched_keywords + matched_entities)

    osde_related = any(
        t in matched_keywords
        for t in [
            "OSDE", "Cristian García Sarubbi", "Martín Pochat", "Guido Montaruli",
            "Bina", "URG Urgencias", "Interturis", "Fundación OSDE", "Flux",
        ]
    )

    primary_category = classify_primary_category(
        matched_keywords + matched_entities,
        title,
        norm_full,
        es_salud_general=direct_health_accepted,
    )

    return {
        "accepted": True,
        "matched_keywords": matched_keywords,
        "matched_entities": matched_entities,
        "subcategories": sorted(matched_subcategories),
        "criteria": criteria,
        "primary_category": primary_category,
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "relevance_score": round(relevance_score, 2),
        "executive_summary": exec_summary,
        "is_osde_focus": osde_related,
    }


def generate_extractive_summary(
    title: str,
    rss_summary: str,
    body: str,
    matched_terms: List[str],
) -> str:
    """Genera un resumen limpio de 2 a 3 oraciones priorizando entidades detectadas."""
    clean_rss = re.sub(r"<[^>]+>", " ", rss_summary or "").strip()
    clean_rss = re.sub(r"\s+", " ", clean_rss)
    if not body or len(body.strip()) < 220:
        return clean_rss[:420] if clean_rss else title

    sentences = re.split(r"(?<=[\.\!\?])\s+", body.strip())
    valid_sentences = [
        s.strip()
        for s in sentences
        if 45 <= len(s.strip()) <= 340
        and not any(skip in s.lower() for skip in ["suscribite", "leé también", "lee también", "seguinos en", "cookies", "copyright"])
    ]
    if not valid_sentences:
        return clean_rss[:420] if clean_rss else body[:380]

    norm_terms = [normalize_text(t) for t in matched_terms if t]
    scored: List[Tuple[float, int, str]] = []
    for idx, sent in enumerate(valid_sentences[:18]):
        ns = normalize_text(sent)
        position_bonus = 2.0 if idx == 0 else (1.2 if idx <= 2 else 0.5)
        term_bonus = sum(1.8 for nt in norm_terms if nt and nt in ns)
        scored.append((position_bonus + term_bonus, idx, sent))

    scored.sort(key=lambda x: (-x[0], x[1]))
    top = sorted(scored[:2], key=lambda x: x[1])
    result = " ".join(s for _, _, s in top)
    return result[:520]


# ==============================================================================
# CLUSTERING DE EVENTOS (Estilo NewsAPI.ai / Event Registry - 100% Python puro)
# ==============================================================================

def _tokenize_for_clustering(text: str) -> List[str]:
    norm = normalize_text(text)
    words = re.findall(r"[a-z0-9]{3,}", norm)
    filtered = [w for w in words if w not in SPANISH_STOPWORDS]
    # Agregar bigramas adyacentes para capturar nombres propios y frases ("swiss_medical", "boletin_oficial")
    bigrams = [f"{filtered[i]}_{filtered[i+1]}" for i in range(len(filtered) - 1)]
    return filtered + bigrams


def cluster_articles_into_events(
    articles: List[Dict[str, Any]],
    similarity_threshold: float = 0.28,
) -> List[Dict[str, Any]]:
    """
    Agrupa artículos recientes que cubren el mismo hecho noticioso usando vectores TF-IDF
    y similitud de coseno (sin requerir librerías externas pesadas ni APIs pagas).
    """
    if not articles:
        return []

    n_docs = len(articles)
    tokenized_docs: List[Counter] = []
    df: Counter = Counter()

    for art in articles:
        # El título y las entidades pesan doble para que distintos diarios coincidan en el hecho
        entities_str = " ".join((art.get("matched_keywords") or []) + (art.get("matched_entities") or []))
        combo = f"{art.get('title', '')} {art.get('title', '')} {entities_str} {entities_str} {(art.get('executive_summary') or art.get('summary') or '')[:300]}"
        tokens = _tokenize_for_clustering(combo)
        counts = Counter(tokens)
        tokenized_docs.append(counts)
        for tok in counts.keys():
            df[tok] += 1

    # Construir vectores TF-IDF normalizados (norma L2 = 1)
    vectors: List[Dict[str, float]] = []
    for counts in tokenized_docs:
        vec: Dict[str, float] = {}
        norm_sq = 0.0
        for tok, tf in counts.items():
            idf = math.log((1.0 + n_docs) / (1.0 + df[tok])) + 1.0
            val = (1.0 + math.log(tf)) * idf
            vec[tok] = val
            norm_sq += val * val
        inv_norm = 1.0 / math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        for tok in vec:
            vec[tok] *= inv_norm
        vectors.append(vec)

    # Clustering aglomerativo greedy sobre artículos ordenados por relevancia/fecha
    assigned = [-1] * n_docs
    clusters: List[List[int]] = []

    for i in range(n_docs):
        if assigned[i] != -1:
            continue
        current_cluster = [i]
        assigned[i] = len(clusters)
        vec_i = vectors[i]

        for j in range(i + 1, n_docs):
            if assigned[j] != -1:
                continue
            vec_j = vectors[j]
            # Producto punto rápido sobre claves comunes
            if len(vec_i) < len(vec_j):
                sim = sum(v * vec_j.get(k, 0.0) for k, v in vec_i.items())
            else:
                sim = sum(v * vec_i.get(k, 0.0) for k, v in vec_j.items())

            if sim >= similarity_threshold:
                assigned[j] = len(clusters)
                current_cluster.append(j)

        clusters.append(current_cluster)

    event_objects: List[Dict[str, Any]] = []
    for cid, member_indices in enumerate(clusters):
        members = [articles[idx] for idx in member_indices]
        # Elegir artículo cabecera (el de mayor relevancia o texto más completo)
        lead = max(
            members,
            key=lambda a: (a.get("relevance_score", 0.0), len(a.get("full_text") or "")),
        )
        unique_sites = list(dict.fromkeys(m.get("site_name", "") for m in members))
        all_kw = list(dict.fromkeys(k for m in members for k in (m.get("matched_keywords") or [])))
        all_ent = list(dict.fromkeys(e for m in members for e in (m.get("matched_entities") or [])))
        all_crit = list(dict.fromkeys(c for m in members for c in (m.get("criteria") or [])))
        avg_sent = round(
            sum(float(m.get("sentiment_score", 0.0)) for m in members) / len(members), 2
        )
        sent_label = (
            "Positivo" if avg_sent >= 0.2 else ("Negativo" if avg_sent <= -0.2 else "Neutro")
        )
        latest_pub = max((m.get("published_at") or "") for m in members)

        event_objects.append(
            {
                "event_id": f"evt-{lead.get('id', cid)}",
                "title": lead.get("title", ""),
                "summary": lead.get("executive_summary") or lead.get("summary") or "",
                "article_count": len(members),
                "site_count": len(unique_sites),
                "sites": unique_sites,
                "matched_keywords": all_kw,
                "matched_entities": all_ent,
                "criteria": all_crit,
                "sentiment_score": avg_sent,
                "sentiment_label": sent_label,
                "latest_published_at": latest_pub,
                "is_osde_focus": any(m.get("is_osde_focus") for m in members),
                "articles": members,
            }
        )

    # Ordenar primero los eventos multi-medio y luego por relevancia/fecha
    event_objects.sort(
        key=lambda e: (e["site_count"] > 1, e["site_count"], e["article_count"], e["latest_published_at"]),
        reverse=True,
    )
    return event_objects
