// SaludAR / Prensa OSDE - Frontend Application (100% Free & Local)

let currentTab = "articles";
let activeTermFilter = "";
let cachedConfig = null;
let cachedStats = null;
let cachedPortalArticles = [];
let siteColorMap = {};
let authState = { auth_required: false, is_admin: true, readonly_locked: false };

const CATEGORY_COLORS = {
  "OSDE & Ecosistema": "bg-[#004a80] text-white",
  "OSDE Institucional & Unidades": "bg-[#004a80] text-white",
  "Competencia & Sector Prepagas": "bg-[#b91c1c] text-white",
  "Normativa & Regulaciones": "bg-[#6b21a8] text-white",
  "Economía & Costos": "bg-[#ca8a04] text-white",
  "Experiencia del Paciente & Reclamos": "bg-[#dc2626] text-white",
  "Gremiales & Recursos Humanos": "bg-[#991b1b] text-white",
  "Coberturas & PMO": "bg-[#0284c7] text-white",
  "Industria Farmacéutica & Insumos": "bg-[#7c3aed] text-white",
  "Prestadores & Servicios": "bg-[#2563eb] text-white",
  "Tecnología & Salud Digital": "bg-[#0f766e] text-white",
  "Salud Pública & Epidemiología": "bg-[#ea580c] text-white",
  "Salud Positiva, Bienestar & Avances": "bg-[#16a34a] text-white",
  "Mercado & Prepagas": "bg-[#475569] text-white",
};

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => el.classList.add("hidden"), 3500);
}

function formatDateAR(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("es-AR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso.slice(0, 16);
  }
}

function categoryBadge(cat, clickable = true) {
  const label = cat || "Mercado & Prepagas";
  const cls = CATEGORY_COLORS[label] || "bg-slate-600 text-white";
  if (!clickable) {
    return `<span class="px-2 py-0.5 rounded text-[11px] font-semibold ${cls}">${escapeHtml(label)}</span>`;
  }
  return `<button onclick="filterByPrimaryCat('${escapeHtml(label)}')" title="Filtrar por categoría" class="px-2 py-0.5 rounded text-[11px] font-semibold ${cls} hover:opacity-90 transition">${escapeHtml(label)}</button>`;
}

function editorialBadge(status) {
  if (status === "Aprobada") {
    return `<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">Aprobada</span>`;
  }
  if (status === "Descartada") {
    return `<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-200 text-slate-600">Descartada</span>`;
  }
  return `<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">Pendiente</span>`;
}

function channelBadge(channel) {
  const map = {
    rss_directo: { label: "RSS Directo", cls: "bg-slate-100 text-slate-600" },
    bing_rss: { label: "Bing AR", cls: "bg-blue-50 text-blue-700" },
    gnews_rss: { label: "Google News AR", cls: "bg-teal-50 text-teal-700" },
    seccion_web: { label: "Portada Web", cls: "bg-purple-50 text-purple-700" },
  };
  const info = map[channel] || { label: channel || "RSS", cls: "bg-slate-100 text-slate-600" };
  return `<span class="px-2 py-0.5 rounded text-[11px] font-medium ${info.cls}">${escapeHtml(info.label)}</span>`;
}

function sentimentBadge(label, score) {
  const s = typeof score === "number" ? ` (${score > 0 ? "+" : ""}${score})` : "";
  if (label === "Positivo") {
    return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Positivo${s}</span>`;
  }
  if (label === "Negativo") {
    return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">Negativo${s}</span>`;
  }
  return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">Neutro${s}</span>`;
}

function criterionBadge(c) {
  if (c === "Resoluciones de la superintendencia") {
    return `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">${escapeHtml(c)}</span>`;
  }
  if (c === "Normativas de salud") {
    return `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">${escapeHtml(c)}</span>`;
  }
  return `<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-sky-50 text-sky-700">${escapeHtml(c)}</span>`;
}

function switchTab(tab) {
  currentTab = tab;
  ["articles", "portal", "events", "analytics", "config"].forEach((t) => {
    const el = document.getElementById("tab-" + t);
    el.className =
      t === tab
        ? "px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-sky-50 text-[#004a80]"
        : "px-3.5 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100";
  });
  document.getElementById("filter-bar-articles").classList.toggle("hidden", tab !== "articles");
  document.getElementById("filter-bar-portal").classList.toggle("hidden", tab !== "portal");
  document.getElementById("filter-bar-events").classList.toggle("hidden", tab !== "events");
  loadCurrentTab();
}

function resetAndGoArticles() {
  resetFilters(false);
  switchTab("articles");
}

function quickFilterOsde() {
  resetFilters(false);
  document.getElementById("f-osde").checked = true;
  switchTab("articles");
}

function quickFilterSentiment(sent) {
  resetFilters(false);
  document.getElementById("f-sentiment").value = sent;
  switchTab("articles");
}

function filterByPrimaryCat(cat) {
  document.getElementById("f-primary-cat").value = cat;
  switchTab("articles");
}

function filterByTerm(term) {
  activeTermFilter = term;
  document.getElementById("active-term-label").textContent = term;
  document.getElementById("active-term-chip").classList.remove("hidden");
  switchTab("articles");
}

function filterBySite(siteName) {
  if (!cachedConfig) return;
  const found = (cachedConfig.sites || []).find((s) => s.name === siteName);
  if (found) {
    document.getElementById("f-site").value = found.id;
    switchTab("articles");
  }
}

function clearTermFilter() {
  activeTermFilter = "";
  document.getElementById("active-term-chip").classList.add("hidden");
  loadCurrentTab();
}

function resetFilters(reload = true) {
  document.getElementById("f-q").value = "";
  document.getElementById("f-site").value = "";
  document.getElementById("f-primary-cat").value = "";
  document.getElementById("f-criterion").value = "";
  document.getElementById("f-hours").value = "";
  document.getElementById("f-editorial").value = "";
  document.getElementById("f-sentiment").value = "";
  document.getElementById("f-sort").value = "recent";
  document.getElementById("f-group").value = "";
  document.getElementById("f-osde").checked = false;
  activeTermFilter = "";
  document.getElementById("active-term-chip").classList.add("hidden");
  if (reload) loadCurrentTab();
}

function updateExportLink() {
  const params = new URLSearchParams();
  const q = document.getElementById("f-q").value.trim();
  const site = document.getElementById("f-site").value;
  const pcat = document.getElementById("f-primary-cat").value;
  const criterion = document.getElementById("f-criterion").value;
  const edStatus = document.getElementById("f-editorial").value;
  const sentiment = document.getElementById("f-sentiment").value;
  const hours = document.getElementById("f-hours").value;
  const osde = document.getElementById("f-osde").checked;
  if (q) params.set("q", q);
  if (site) params.set("site_id", site);
  if (pcat) params.set("primary_category", pcat);
  if (criterion) params.set("criterion", criterion);
  if (edStatus) params.set("editorial_status", edStatus);
  if (sentiment) params.set("sentiment", sentiment);
  if (hours) params.set("hours", hours);
  if (osde) params.set("osde_only", "true");
  const qs = params.toString();
  document.getElementById("btn-export-csv").href = "/api/export/csv" + (qs ? "?" + qs : "");
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    cachedStats = data;
    const totals = data.totals || {};
    document.getElementById("stat-total").textContent = totals.articles ?? 0;
    document.getElementById("stat-24h").textContent = `${totals.last_24h ?? 0} en últimas 24 hs`;
    document.getElementById("stat-events").textContent = totals.events ?? 0;
    document.getElementById("stat-multi-events").textContent = `${totals.multi_source_events ?? 0} multi-medio`;
    document.getElementById("stat-osde").textContent = totals.osde_mentions ?? 0;
    document.getElementById("stat-approved").textContent = totals.approved ?? 0;
    document.getElementById("stat-pending").textContent = `${totals.pending ?? 0} pendientes`;
    document.getElementById("portal-count-badge").textContent = totals.approved ?? 0;
    document.getElementById("stat-sites").textContent = `${totals.enabled_sites ?? 0}/${totals.total_sites ?? 0}`;

    const sent = data.by_sentiment || {};
    const pos = sent.Positivo || 0;
    const neu = sent.Neutro || 0;
    const neg = sent.Negativo || 0;
    const sum = Math.max(pos + neu + neg, 1);
    document.getElementById("stat-pos").textContent = pos;
    document.getElementById("stat-neu").textContent = neu;
    document.getElementById("stat-neg").textContent = neg;
    document.getElementById("bar-pos").style.width = `${(pos / sum) * 100}%`;
    document.getElementById("bar-neu").style.width = `${(neu / sum) * 100}%`;
    document.getElementById("bar-neg").style.width = `${(neg / sum) * 100}%`;

    const lastScan = data.recent_scans && data.recent_scans[0];
    document.getElementById("stat-last-scan").textContent = lastScan
      ? formatDateAR(lastScan.finished_at || lastScan.started_at)
      : "Pendiente";

    if (currentTab === "analytics") renderAnalytics();
  } catch (e) {
    console.error("Error cargando estadísticas:", e);
  }
}

async function loadConfigFilters() {
  try {
    const res = await fetch("/api/config");
    const cfg = await res.json();
    cachedConfig = cfg;
    siteColorMap = {};
    const siteSelect = document.getElementById("f-site");
    const currentVal = siteSelect.value;
    siteSelect.innerHTML = `<option value="">Todos los medios (${(cfg.sites || []).length})</option>`;
    (cfg.sites || []).forEach((s) => {
      siteColorMap[s.id] = s.color || "#0284c7";
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name;
      siteSelect.appendChild(opt);
    });
    siteSelect.value = currentVal;
  } catch (e) {
    console.error("Error cargando config:", e);
  }
}

async function setEditorialStatus(articleId, status, fromModal = false) {
  const res = await fetch(`/api/articles/${articleId}/editorial`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ editorial_status: status }),
  });
  if (!res.ok) return;
  showToast(`Nota #${articleId} marcada como "${status}"`);
  await loadStats();
  if (fromModal) {
    await openArticleModal(articleId);
  }
  if (currentTab === "articles") loadArticles();
  else if (currentTab === "portal") loadPortal();
}

async function savePressNotes(articleId) {
  const input = document.getElementById("modal-press-notes");
  if (!input) return;
  const res = await fetch(`/api/articles/${articleId}/editorial`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ press_notes: input.value }),
  });
  if (res.ok) {
    showToast("Notas de Prensa guardadas");
    if (currentTab === "articles") loadArticles();
    else if (currentTab === "portal") loadPortal();
  }
}

async function loadArticles() {
  updateExportLink();
  const area = document.getElementById("content-area");
  area.innerHTML = '<div class="bg-white p-6 rounded-xl border border-slate-200 text-sm text-slate-500">Cargando noticias...</div>';

  const params = new URLSearchParams();
  const q = document.getElementById("f-q").value.trim();
  const site = document.getElementById("f-site").value;
  const pcat = document.getElementById("f-primary-cat").value;
  const criterion = document.getElementById("f-criterion").value;
  const hours = document.getElementById("f-hours").value;
  const edStatus = document.getElementById("f-editorial").value;
  const sentiment = document.getElementById("f-sentiment").value;
  const sortBy = document.getElementById("f-sort").value;
  const group = document.getElementById("f-group").value;
  const osdeOnly = document.getElementById("f-osde").checked;

  if (q) params.set("q", q);
  if (site) params.set("site_id", site);
  if (pcat) params.set("primary_category", pcat);
  if (criterion) params.set("criterion", criterion);
  if (hours) params.set("hours", hours);
  if (edStatus) params.set("editorial_status", edStatus);
  if (sentiment) params.set("sentiment", sentiment);
  if (sortBy) params.set("sort_by", sortBy);
  if (group) params.set("column_group", group);
  if (osdeOnly) params.set("osde_only", "true");
  if (activeTermFilter) params.set("term", activeTermFilter);
  params.set("limit", "250");

  const res = await fetch("/api/articles?" + params.toString());
  const data = await res.json();
  const items = data.articles || [];
  document.getElementById("result-counter").textContent = `${items.length} noticias mostradas`;

  if (!items.length) {
    area.innerHTML = `
      <div class="bg-white p-10 rounded-xl border border-slate-200 text-center space-y-2">
        <p class="text-slate-700 font-medium">No hay noticias que coincidan con estos filtros.</p>
        <p class="text-xs text-slate-500">Probá limpiar los filtros o ejecutar un nuevo escaneo.</p>
      </div>`;
    return;
  }

  area.innerHTML = items
    .map((a) => {
      const dotColor = siteColorMap[a.site_id] || "#0284c7";
      const kwList = Array.isArray(a.matched_keywords) ? a.matched_keywords : [];
      const entList = Array.isArray(a.matched_entities) ? a.matched_entities : [];
      const critList = Array.isArray(a.criteria) ? a.criteria : [];
      const summary = a.executive_summary || a.summary || "";
      const edStatus = a.editorial_status || "Pendiente";

      return `
      <article class="bg-white p-4 sm:p-5 rounded-xl border ${edStatus === "Aprobada" ? "border-emerald-300 bg-emerald-50/15" : edStatus === "Descartada" ? "border-slate-200 opacity-65" : "border-slate-200"} hover:border-sky-300 transition shadow-xs flex flex-col sm:flex-row gap-4">
        ${
          a.image_url
            ? `<div class="sm:w-40 sm:h-28 shrink-0 rounded-lg overflow-hidden bg-slate-100 border border-slate-200">
                 <img src="${escapeHtml(a.image_url)}" alt="" loading="lazy" onerror="this.parentElement.style.display='none'" class="w-full h-full object-cover" />
               </div>`
            : ""
        }
        <div class="flex-1 min-w-0 space-y-2">
          <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div class="flex flex-wrap items-center gap-1.5 text-slate-500">
              ${categoryBadge(a.primary_category)}
              <span class="inline-flex items-center gap-1 font-semibold text-slate-800 ml-1">
                <span class="w-2 h-2 rounded-full" style="background:${escapeHtml(dotColor)}"></span>
                ${escapeHtml(a.site_name)}
              </span>
              <span>•</span>
              <span>${escapeHtml(formatDateAR(a.published_at))}</span>
              ${channelBadge(a.discovery_channel)}
              ${editorialBadge(edStatus)}
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
              ${sentimentBadge(a.sentiment_label, a.sentiment_score)}
              ${critList.map(criterionBadge).join("")}
            </div>
          </div>

          <h3 class="text-base font-bold text-slate-900 leading-snug">
            <button onclick="openArticleModal(${a.id})" class="text-left hover:text-[#004a80] transition">
              ${escapeHtml(a.title)}
            </button>
          </h3>

          ${summary ? `<p class="text-sm text-slate-600 line-clamp-2">${escapeHtml(summary)}</p>` : ""}
          ${a.press_notes ? `<p class="text-xs text-emerald-900 bg-emerald-50 border border-emerald-200 rounded-lg px-2.5 py-1.5"><strong>Nota Prensa:</strong> ${escapeHtml(a.press_notes)}</p>` : ""}

          <div class="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div class="flex flex-wrap gap-1.5">
              ${kwList
                .map(
                  (t) =>
                    `<button onclick="filterByTerm('${escapeHtml(t)}')" class="px-2 py-0.5 bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200 rounded text-xs font-medium transition">${escapeHtml(t)}</button>`
                )
                .join("")}
              ${entList
                .map(
                  (t) =>
                    `<button onclick="filterByTerm('${escapeHtml(t)}')" class="px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded text-xs font-medium transition">${escapeHtml(t)}</button>`
                )
                .join("")}
            </div>

            <div class="flex flex-wrap items-center gap-2 text-xs shrink-0">
              <div class="inline-flex rounded-lg border border-slate-200 overflow-hidden bg-slate-50">
                <button onclick="setEditorialStatus(${a.id}, 'Aprobada')" title="Aprobar para Portal Publicadas" class="px-2 py-1 ${edStatus === "Aprobada" ? "bg-emerald-600 text-white font-bold" : "text-emerald-700 hover:bg-emerald-100"}">Aprobar</button>
                <button onclick="setEditorialStatus(${a.id}, 'Pendiente')" title="Marcar como pendiente" class="px-2 py-1 border-x border-slate-200 ${edStatus === "Pendiente" ? "bg-amber-100 text-amber-900 font-bold" : "text-slate-600 hover:bg-slate-200"}">Pend.</button>
                <button onclick="setEditorialStatus(${a.id}, 'Descartada')" title="Descartar nota" class="px-2 py-1 ${edStatus === "Descartada" ? "bg-slate-600 text-white font-bold" : "text-slate-600 hover:bg-rose-100 hover:text-rose-700"}">Descartar</button>
              </div>
              <button onclick="openArticleModal(${a.id})" class="font-semibold text-[#004a80] hover:underline">Leer / Notas</button>
              <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener" class="font-medium text-slate-500 hover:text-slate-900">Fuente &#8599;</a>
            </div>
          </div>
        </div>
      </article>`;
    })
    .join("");
}

async function loadPortal() {
  const area = document.getElementById("content-area");
  area.innerHTML = '<div class="bg-white p-6 rounded-xl border border-slate-200 text-sm text-slate-500">Cargando Portal Publicadas...</div>';
  const q = (document.getElementById("p-q").value || "").trim();
  const params = new URLSearchParams({ editorial_status: "Aprobada", limit: "300" });
  if (q) params.set("q", q);

  const res = await fetch("/api/articles?" + params.toString());
  const data = await res.json();
  const items = data.articles || [];
  cachedPortalArticles = items;
  document.getElementById("result-counter").textContent = `${items.length} notas aprobadas en Portal`;

  if (!items.length) {
    area.innerHTML = `
      <div class="bg-white p-10 rounded-xl border border-slate-200 text-center space-y-2">
        <p class="text-slate-700 font-semibold">Todavía no hay noticias marcadas como "Aprobada".</p>
        <p class="text-xs text-slate-500">En la pestaña <strong>Noticias</strong>, hacé clic en <strong>Aprobar</strong> en cualquier nota para publicarla automáticamente en este portal.</p>
      </div>`;
    return;
  }

  area.innerHTML = items
    .map((a) => `
      <div class="bg-white p-4 rounded-xl border border-slate-200 hover:shadow-md transition space-y-2">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2">
            ${categoryBadge(a.primary_category, false)}
            <span class="px-2 py-0.5 rounded bg-sky-50 text-sky-800 text-xs font-semibold">${escapeHtml(a.site_name)}</span>
          </div>
          <div class="flex items-center gap-2 text-xs text-slate-500">
            <span>${escapeHtml(formatDateAR(a.published_at))}</span>
            <button onclick="setEditorialStatus(${a.id}, 'Pendiente')" class="text-rose-600 hover:underline">Quitar del portal</button>
          </div>
        </div>
        <h3 class="text-base font-bold text-slate-900">
          <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener" class="hover:text-[#004a80]">${escapeHtml(a.title)}</a>
        </h3>
        ${a.press_notes ? `<p class="text-sm text-slate-700 bg-slate-50 border-l-4 border-[#004a80] px-3 py-2">${escapeHtml(a.press_notes)}</p>` : ""}
        <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
          <span><strong>Criterio:</strong> ${escapeHtml((a.matched_keywords || []).concat(a.matched_entities || []).join(", ") || (a.criteria || []).join(", "))}</span>
          <div class="flex items-center gap-3">
            <button onclick="openArticleModal(${a.id})" class="text-[#004a80] font-semibold hover:underline">Editar nota</button>
            <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener" class="px-2.5 py-1 rounded border border-sky-600 text-sky-700 hover:bg-sky-50 font-medium">Leer nota completa &#8599;</a>
          </div>
        </div>
      </div>
    `)
    .join("");
}

async function copyPortalBriefing() {
  if (!cachedPortalArticles.length) {
    showToast("No hay noticias aprobadas para copiar");
    return;
  }
  const lines = ["*RESUMEN PRENSA SALUD / OSDE*", ""];
  cachedPortalArticles.forEach((a, idx) => {
    lines.push(`${idx + 1}. [${a.primary_category || "Salud"}] *${a.title}* (${a.site_name})`);
    if (a.press_notes) lines.push(`   Nota: ${a.press_notes}`);
    lines.push(`   ${a.url}`);
  });
  await navigator.clipboard.writeText(lines.join("\n"));
  showToast("Resumen copiado al portapapeles");
}

async function loadEvents() {
  const area = document.getElementById("content-area");
  area.innerHTML = '<div class="bg-white p-6 rounded-xl border border-slate-200 text-sm text-slate-500">Agrupando noticias por similitud temática (TF-IDF)...</div>';

  const params = new URLSearchParams();
  const q = document.getElementById("e-q").value.trim();
  const criterion = document.getElementById("e-criterion").value;
  const osdeOnly = document.getElementById("e-osde").checked;
  const multiOnly = document.getElementById("e-multi").checked;
  if (q) params.set("q", q);
  if (criterion) params.set("criterion", criterion);
  if (osdeOnly) params.set("osde_only", "true");
  params.set("limit", "300");

  const res = await fetch("/api/events?" + params.toString());
  const data = await res.json();
  let events = data.events || [];
  if (multiOnly) {
    events = events.filter((ev) => (ev.site_count || 1) > 1);
  }
  document.getElementById("result-counter").textContent = `${events.length} eventos`;

  if (!events.length) {
    area.innerHTML = '<div class="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500">No se encontraron eventos con estos filtros.</div>';
    return;
  }

  area.innerHTML = events
    .map((ev) => {
      const multi = (ev.site_count || 1) > 1;
      const kwList = ev.matched_keywords || [];
      const entList = ev.matched_entities || [];
      const critList = ev.criteria || [];
      const arts = ev.articles || [];

      return `
      <div class="bg-white p-5 rounded-xl border ${multi ? "border-indigo-200 shadow-sm" : "border-slate-200"} space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${multi ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-700"}">
              ${ev.article_count} ${ev.article_count === 1 ? "nota" : "notas"} • ${ev.site_count} ${ev.site_count === 1 ? "medio" : "medios"}
            </span>
            ${ev.is_osde_focus ? `<span class="px-2 py-0.5 rounded-full bg-[#004a80] text-white text-[11px] font-bold">Foco OSDE</span>` : ""}
            ${(ev.sites || []).map((s) => `<span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs font-medium">${escapeHtml(s)}</span>`).join("")}
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            ${sentimentBadge(ev.sentiment_label, ev.sentiment_score)}
            ${critList.map(criterionBadge).join("")}
            <span class="text-xs text-slate-400 ml-1">${escapeHtml(formatDateAR(ev.latest_published_at))}</span>
          </div>
        </div>

        <div>
          <h3 class="text-base font-bold text-slate-900">${escapeHtml(ev.title)}</h3>
          ${ev.summary ? `<p class="text-sm text-slate-600 mt-1 line-clamp-3">${escapeHtml(ev.summary)}</p>` : ""}
        </div>

        <div class="flex flex-wrap gap-1.5">
          ${kwList.map((t) => `<button onclick="filterByTerm('${escapeHtml(t)}')" class="px-2 py-0.5 bg-sky-50 text-sky-800 border border-sky-200 rounded text-xs">${escapeHtml(t)}</button>`).join("")}
          ${entList.map((t) => `<button onclick="filterByTerm('${escapeHtml(t)}')" class="px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 rounded text-xs">${escapeHtml(t)}</button>`).join("")}
        </div>

        <div class="pl-3 border-l-2 border-indigo-200 space-y-1.5 pt-1">
          ${arts
            .map(
              (a) => `
              <div class="flex flex-wrap items-center justify-between gap-2 text-sm py-0.5">
                <div class="min-w-0 flex-1">
                  <span class="font-semibold text-slate-700">${escapeHtml(a.site_name)}:</span>
                  <button onclick="openArticleModal(${a.id})" class="text-left text-sky-700 hover:underline">${escapeHtml(a.title)}</button>
                </div>
                <div class="flex items-center gap-2 text-xs shrink-0">
                  <span class="text-slate-400">${escapeHtml(formatDateAR(a.published_at))}</span>
                  <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener" class="text-slate-500 hover:text-slate-900">&#8599;</a>
                </div>
              </div>`
            )
            .join("")}
        </div>
      </div>`;
    })
    .join("");
}

function renderAnalytics() {
  const area = document.getElementById("content-area");
  document.getElementById("result-counter").textContent = "Panel analítico";
  if (!cachedStats) {
    area.innerHTML = '<div class="bg-white p-6 rounded-xl border border-slate-200 text-sm text-slate-500">Cargando analítica...</div>';
    return;
  }
  const st = cachedStats;
  const bySite = st.by_site || [];
  const maxSite = Math.max(...bySite.map((x) => x.count), 1);
  const byCat = st.by_primary_category || [];
  const maxCat = Math.max(...byCat.map((x) => x.count), 1);
  const topKw = st.top_keywords || [];
  const maxKw = Math.max(...topKw.map((x) => x.count), 1);
  const topEnt = st.top_entities || [];
  const maxEnt = Math.max(...topEnt.map((x) => x.count), 1);
  const timeline = st.timeline || [];
  const maxDay = Math.max(...timeline.map((x) => x.count), 1);

  area.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3 lg:col-span-2">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-slate-900">Evolución diaria de noticias (últimos días)</h3>
          <span class="text-xs text-slate-500">${timeline.length} fechas registradas</span>
        </div>
        ${
          timeline.length
            ? `<div class="h-44 flex items-end gap-2 pt-4 border-b border-slate-200 pb-1">
                ${timeline
                  .map((d) => {
                    const pct = Math.max(8, Math.round((d.count / maxDay) * 100));
                    return `
                      <div class="flex-1 flex flex-col items-center justify-end h-full group">
                        <span class="text-[11px] font-bold text-slate-700 mb-1">${d.count}</span>
                        <div class="w-full max-w-[42px] bg-[#004a80] group-hover:bg-sky-600 rounded-t-md transition-all" style="height:${pct}%"></div>
                        <span class="text-[10px] text-slate-500 mt-1.5 truncate">${escapeHtml(d.date.slice(5))}</span>
                      </div>`;
                  })
                  .join("")}
              </div>`
            : `<p class="text-sm text-slate-500">Sin datos temporales todavía.</p>`
        }
      </div>

      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3">
        <h3 class="font-bold text-slate-900">Categorías Prensa OSDE (click para filtrar)</h3>
        <div class="space-y-2">
          ${byCat
            .map(
              (c) => `
              <button onclick="filterByPrimaryCat('${escapeHtml(c.name)}')" class="w-full text-left group">
                <div class="flex justify-between text-xs mb-1">
                  <span class="font-medium text-slate-700 group-hover:text-[#004a80]">${escapeHtml(c.name)}</span>
                  <span class="font-bold text-slate-900">${c.count}</span>
                </div>
                <div class="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div class="h-full bg-[#004a80] rounded-full" style="width:${(c.count / maxCat) * 100}%"></div>
                </div>
              </button>`
            )
            .join("")}
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3">
        <h3 class="font-bold text-slate-900">Cobertura por Medio (click para filtrar)</h3>
        <div class="space-y-2">
          ${bySite
            .map(
              (s) => `
              <button onclick="filterBySite('${escapeHtml(s.name)}')" class="w-full text-left group">
                <div class="flex justify-between text-xs mb-1">
                  <span class="font-medium text-slate-700 group-hover:text-sky-700">${escapeHtml(s.name)}</span>
                  <span class="font-bold text-slate-900">${s.count}</span>
                </div>
                <div class="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div class="h-full bg-sky-600 rounded-full" style="width:${(s.count / maxSite) * 100}%"></div>
                </div>
              </button>`
            )
            .join("")}
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3">
        <h3 class="font-bold text-slate-900">Top Palabras Claves (Columna C)</h3>
        <div class="space-y-2">
          ${topKw
            .map(
              (k) => `
              <button onclick="filterByTerm('${escapeHtml(k.term)}')" class="w-full text-left group">
                <div class="flex justify-between text-xs mb-1">
                  <span class="font-medium text-slate-700 group-hover:text-sky-700">${escapeHtml(k.term)}</span>
                  <span class="font-bold text-slate-900">${k.count}</span>
                </div>
                <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div class="h-full bg-cyan-600 rounded-full" style="width:${(k.count / maxKw) * 100}%"></div>
                </div>
              </button>`
            )
            .join("")}
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3">
        <h3 class="font-bold text-slate-900">Top Personalidades y Otras Prepagas (Columna D)</h3>
        <div class="space-y-2">
          ${topEnt
            .map(
              (e) => `
              <button onclick="filterByTerm('${escapeHtml(e.term)}')" class="w-full text-left group">
                <div class="flex justify-between text-xs mb-1">
                  <span class="font-medium text-slate-700 group-hover:text-amber-700">${escapeHtml(e.term)}</span>
                  <span class="font-bold text-slate-900">${e.count}</span>
                </div>
                <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div class="h-full bg-amber-500 rounded-full" style="width:${(e.count / maxEnt) * 100}%"></div>
                </div>
              </button>`
            )
            .join("")}
        </div>
      </div>
    </div>`;
}

async function loadConfig() {
  const area = document.getElementById("content-area");
  document.getElementById("result-counter").textContent = "Configuración y matriz";
  const res = await fetch("/api/config");
  const cfg = await res.json();
  cachedConfig = cfg;

  const sites = cfg.sites || [];
  const terms = cfg.terms || [];
  const kwTerms = terms.filter((t) => t.column === "palabras_claves");
  const entTerms = terms.filter((t) => t.column !== "palabras_claves");
  const lim = cfg.limitations || {};
  const scans = (cachedStats && cachedStats.recent_scans) || [];

  area.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-slate-900">Sitios a consultar (${sites.length})</h3>
          <span class="text-xs text-slate-500">Periodicidad: ${escapeHtml(lim.periodicity || "Diaria")}</span>
        </div>
        <div class="divide-y divide-slate-100 max-h-96 overflow-y-auto">
          ${sites
            .map(
              (s, idx) => `
              <div class="py-2 flex items-center justify-between gap-2 text-sm">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:${escapeHtml(s.color || "#0284c7")}"></span>
                    <span class="font-semibold text-slate-800">${escapeHtml(s.name)}</span>
                  </div>
                  <a href="${escapeHtml(s.url)}" target="_blank" class="text-xs text-sky-700 hover:underline truncate block">${escapeHtml(s.url)}</a>
                </div>
                <label class="inline-flex items-center gap-1.5 text-xs cursor-pointer shrink-0">
                  <input type="checkbox" ${s.enabled !== false ? "checked" : ""} onchange="toggleSite(${idx}, this.checked)" class="rounded text-sky-600" />
                  <span>Activo</span>
                </label>
              </div>`
            )
            .join("")}
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-slate-900">Palabras claves y Personalidades</h3>
          <button onclick="resetConfigDefaults()" class="text-xs px-2.5 py-1 rounded border border-slate-300 hover:bg-slate-50 text-slate-700">
            Restaurar planilla original
          </button>
        </div>

        <form onsubmit="addNewTerm(event)" class="flex flex-wrap gap-2">
          <input id="new-term-text" type="text" required placeholder="Nuevo término o personalidad..." class="flex-1 min-w-[180px] px-3 py-1.5 border border-slate-300 rounded-lg text-sm" />
          <select id="new-term-col" class="px-2.5 py-1.5 border border-slate-300 rounded-lg text-sm bg-white">
            <option value="palabras_claves">Palabras claves (Col C)</option>
            <option value="personalidades_otras_prepagas">Personalidades / Prepagas (Col D)</option>
          </select>
          <button type="submit" class="px-3.5 py-1.5 bg-[#004a80] hover:bg-sky-900 text-white text-sm font-medium rounded-lg">Agregar</button>
        </form>

        <div>
          <p class="text-xs font-semibold text-slate-500 uppercase mb-1.5">Palabras claves (${kwTerms.length})</p>
          <div class="flex flex-wrap gap-1.5">
            ${kwTerms
              .map(
                (t) => `
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${t.enabled !== false ? "bg-sky-50 text-sky-800 border-sky-200" : "bg-slate-100 text-slate-400 border-slate-200 line-through"}">
                  <button onclick="filterByTerm('${escapeHtml(t.term)}')" class="hover:underline">${escapeHtml(t.term)}</button>
                  <button onclick="toggleTerm('${escapeHtml(t.term)}')" title="Activar/desactivar" class="text-slate-400 hover:text-slate-700 font-bold ml-0.5">&#8635;</button>
                </span>`
              )
              .join("")}
          </div>
        </div>

        <div>
          <p class="text-xs font-semibold text-slate-500 uppercase mb-1.5">Personalidades y otras prepagas (${entTerms.length})</p>
          <div class="flex flex-wrap gap-1.5">
            ${entTerms
              .map(
                (t) => `
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${t.enabled !== false ? "bg-amber-50 text-amber-800 border-amber-200" : "bg-slate-100 text-slate-400 border-slate-200 line-through"}">
                  <button onclick="filterByTerm('${escapeHtml(t.term)}')" class="hover:underline">${escapeHtml(t.term)}</button>
                  <button onclick="toggleTerm('${escapeHtml(t.term)}')" title="Activar/desactivar" class="text-slate-400 hover:text-slate-700 font-bold ml-0.5">&#8635;</button>
                </span>`
              )
              .join("")}
          </div>
        </div>

        <div class="pt-2 border-t border-slate-100 text-xs text-slate-600 space-y-1">
          <p><strong>Limitaciones:</strong> ${escapeHtml(lim.geo_scope || "Sólo Argentina")} • Periodicidad ${escapeHtml(lim.periodicity || "Diaria")}</p>
          <p><strong>Criterios:</strong> ${(cfg.criteria || []).map(escapeHtml).join(" • ")}</p>
        </div>
      </div>

      <div class="bg-white p-5 rounded-xl border border-slate-200 space-y-3 lg:col-span-2">
        <h3 class="font-bold text-slate-900">Historial de barridos recientes</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="text-slate-500 border-b border-slate-200">
              <tr>
                <th class="py-2 pr-3">#</th>
                <th class="py-2 pr-3">Inicio</th>
                <th class="py-2 pr-3">Fin</th>
                <th class="py-2 pr-3">Estado</th>
                <th class="py-2 pr-3">Candidatas</th>
                <th class="py-2 pr-3">Guardadas</th>
                <th class="py-2">Medios</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${
                scans.length
                  ? scans
                      .map(
                        (sc) => `
                      <tr>
                        <td class="py-2 pr-3 font-mono">${sc.id}</td>
                        <td class="py-2 pr-3">${escapeHtml(formatDateAR(sc.started_at))}</td>
                        <td class="py-2 pr-3">${sc.finished_at ? escapeHtml(formatDateAR(sc.finished_at)) : "-"}</td>
                        <td class="py-2 pr-3"><span class="px-2 py-0.5 rounded bg-slate-100 font-medium">${escapeHtml(sc.status)}</span></td>
                        <td class="py-2 pr-3">${sc.candidates_checked ?? 0}</td>
                        <td class="py-2 pr-3 font-semibold text-sky-700">${sc.articles_saved ?? 0}</td>
                        <td class="py-2">${sc.sites_scanned ?? 0}</td>
                      </tr>`
                      )
                      .join("")
                  : `<tr><td colspan="7" class="py-3 text-slate-500">Sin barridos registrados aún.</td></tr>`
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}

async function toggleSite(idx, enabled) {
  if (!cachedConfig) return;
  cachedConfig.sites[idx].enabled = enabled;
  await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sites: cachedConfig.sites }),
  });
  showToast("Configuración de medio actualizada");
  loadStats();
}

async function toggleTerm(termName) {
  if (!cachedConfig) return;
  const item = (cachedConfig.terms || []).find((t) => t.term === termName);
  if (!item) return;
  item.enabled = item.enabled === false ? true : false;
  await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms: cachedConfig.terms }),
  });
  showToast(`Término "${termName}" actualizado`);
  loadConfig();
}

async function addNewTerm(e) {
  e.preventDefault();
  if (!cachedConfig) return;
  const term = document.getElementById("new-term-text").value.trim();
  const column = document.getElementById("new-term-col").value;
  if (!term) return;
  cachedConfig.terms.push({
    term,
    column,
    subcategory: column === "palabras_claves" ? "Personalizado" : "Entidad personalizada",
    aliases: [],
    context_required: false,
    weight: 2.5,
    enabled: true,
  });
  await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms: cachedConfig.terms }),
  });
  showToast(`Término "${term}" agregado`);
  loadConfig();
}

async function resetConfigDefaults() {
  const res = await fetch("/api/config/reset", { method: "POST" });
  cachedConfig = await res.json();
  showToast("Configuración restaurada a la planilla original");
  loadConfigFilters();
  loadConfig();
}

async function openArticleModal(articleId) {
  const modal = document.getElementById("article-modal");
  const body = document.getElementById("modal-body");
  const topMeta = document.getElementById("modal-meta-top");
  const bottomMeta = document.getElementById("modal-meta-bottom");
  const extLink = document.getElementById("modal-external-link");

  modal.classList.remove("hidden");
  topMeta.innerHTML = `<span class="text-slate-500">Cargando artículo #${articleId}...</span>`;
  body.innerHTML = `<div class="py-10 text-center text-sm text-slate-500">Cargando contenido completo...</div>`;

  const res = await fetch(`/api/articles/${articleId}`);
  if (!res.ok) {
    body.innerHTML = `<p class="text-rose-600 text-sm">No se pudo cargar el artículo.</p>`;
    return;
  }
  const a = await res.json();
  const edStatus = a.editorial_status || "Pendiente";

  topMeta.innerHTML = `
    ${categoryBadge(a.primary_category, false)}
    <span class="font-bold text-slate-900">${escapeHtml(a.site_name)}</span>
    <span class="text-slate-400">•</span>
    <span class="text-slate-500">${escapeHtml(formatDateAR(a.published_at))}</span>
    ${sentimentBadge(a.sentiment_label, a.sentiment_score)}
  `;
  extLink.href = a.url;
  bottomMeta.textContent = `${a.author ? "Autor: " + a.author + " • " : ""}Relevancia: ${a.relevance_score ?? 0} • Canal: ${a.discovery_channel || "rss"}`;

  const paragraphs = (a.full_text || a.executive_summary || a.summary || "")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  body.innerHTML = `
    <h2 class="text-xl font-bold text-slate-900 leading-snug">${escapeHtml(a.title)}</h2>

    <!-- Editorial Curation Box -->
    <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-xs font-bold uppercase text-slate-600">Curación Prensa (${escapeHtml(edStatus)})</span>
        <div class="inline-flex rounded-lg border border-slate-300 overflow-hidden text-xs bg-white">
          <button onclick="setEditorialStatus(${a.id}, 'Aprobada', true)" class="px-3 py-1 ${edStatus === "Aprobada" ? "bg-emerald-600 text-white font-bold" : "text-emerald-700 hover:bg-emerald-50"}">Aprobar (Publicar)</button>
          <button onclick="setEditorialStatus(${a.id}, 'Pendiente', true)" class="px-3 py-1 border-x border-slate-300 ${edStatus === "Pendiente" ? "bg-amber-100 text-amber-900 font-bold" : "text-slate-600 hover:bg-slate-100"}">Pendiente</button>
          <button onclick="setEditorialStatus(${a.id}, 'Descartada', true)" class="px-3 py-1 ${edStatus === "Descartada" ? "bg-slate-600 text-white font-bold" : "text-slate-600 hover:bg-rose-50 hover:text-rose-700"}">Descartar</button>
        </div>
      </div>
      <div class="flex gap-2">
        <input id="modal-press-notes" type="text" value="${escapeHtml(a.press_notes || "")}" placeholder="Agregar Notas Prensa (ej. impacto en afiliados, seguimiento)..." class="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white" />
        <button onclick="savePressNotes(${a.id})" class="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg">Guardar nota</button>
      </div>
    </div>

    ${
      a.image_url
        ? `<img src="${escapeHtml(a.image_url)}" alt="" onerror="this.style.display='none'" class="w-full max-h-72 object-cover rounded-xl border border-slate-200" />`
        : ""
    }
    ${
      a.executive_summary
        ? `<div class="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-sm text-sky-950">
             <span class="text-xs font-bold uppercase text-sky-700 block mb-1">Resumen ejecutivo automático</span>
             ${escapeHtml(a.executive_summary)}
           </div>`
        : ""
    }
    <div class="flex flex-wrap gap-1.5">
      ${(a.criteria || []).map(criterionBadge).join("")}
      ${(a.matched_keywords || []).map((t) => `<span class="px-2 py-0.5 bg-sky-50 text-sky-800 border border-sky-200 rounded text-xs font-medium">${escapeHtml(t)}</span>`).join("")}
      ${(a.matched_entities || []).map((t) => `<span class="px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 rounded text-xs font-medium">${escapeHtml(t)}</span>`).join("")}
    </div>
    <div class="prose prose-sm max-w-none text-slate-700 space-y-3 leading-relaxed border-t border-slate-100 pt-4">
      ${
        paragraphs.length
          ? paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join("")
          : `<p class="text-slate-500 italic">Este medio no entregó cuerpo completo vía web; usá "Abrir en medio original" para leer la nota completa.</p>`
      }
    </div>
  `;
}

function closeModal() {
  document.getElementById("article-modal").classList.add("hidden");
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

function loadCurrentTab() {
  if (currentTab === "articles") loadArticles();
  else if (currentTab === "portal") loadPortal();
  else if (currentTab === "events") loadEvents();
  else if (currentTab === "analytics") renderAnalytics();
  else loadConfig();
}

async function triggerScan() {
  const btn = document.getElementById("btn-scan");
  btn.disabled = true;
  btn.textContent = "Iniciando...";
  await fetch("/api/scan", { method: "POST" });
  pollScanStatus();
}

async function triggerReanalyze() {
  const btn = document.getElementById("btn-reanalyze");
  btn.disabled = true;
  btn.textContent = "Depurando...";
  try {
    const res = await fetch("/api/reanalyze", { method: "POST" });
    const data = await res.json();
    showToast(`Base depurada y recategorizada: ${data.kept} relevantes, ${data.removed} descartadas.`);
    await loadStats();
    loadCurrentTab();
  } finally {
    btn.disabled = false;
    btn.textContent = "Depurar base";
  }
}

let wasRunning = false;
async function pollScanStatus() {
  try {
    const res = await fetch("/api/scan/status");
    const st = await res.json();
    const badge = document.getElementById("scan-status-badge");
    const btn = document.getElementById("btn-scan");
    const wrap = document.getElementById("scan-progress-wrap");
    const bar = document.getElementById("scan-progress-bar");
    const stepText = document.getElementById("scan-step-text");
    const countersText = document.getElementById("scan-counters-text");

    if (st.is_running) {
      wasRunning = true;
      badge.textContent = `Escaneando ${st.progress_pct || 0}%`;
      badge.className = "text-xs px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 font-semibold";
      btn.disabled = true;
      btn.textContent = "Escaneando...";
      wrap.classList.remove("hidden");
      bar.style.width = `${st.progress_pct || 5}%`;
      stepText.textContent = st.current_step || "Escaneando medios...";
      countersText.textContent = `${st.progress_pct || 0}% • ${st.candidates_checked || 0}/${st.candidates_found || 0} analizadas • +${st.articles_saved || 0} nuevas`;
      setTimeout(pollScanStatus, 2000);
    } else {
      wrap.classList.add("hidden");
      badge.textContent = "Listo";
      badge.className = "text-xs px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-medium";
      btn.disabled = false;
      btn.textContent = "Escanear ahora";
      if (wasRunning) {
        wasRunning = false;
        showToast(st.current_step || "Escaneo completado");
        await loadStats();
        loadCurrentTab();
      }
    }
  } catch (e) {
    console.error(e);
  }
}

async function checkAuthStatus() {
  try {
    const res = await fetch("/api/auth/status");
    if (res.ok) {
      authState = await res.json();
      updateAuthUI();
    }
  } catch (e) {
    console.error("Error al consultar auth:", e);
  }
}

function updateAuthUI() {
  const icon = document.getElementById("auth-status-icon");
  const text = document.getElementById("auth-status-text");
  const btn = document.getElementById("btn-admin-auth");
  if (!icon || !text) return;

  if (!authState.auth_required) {
    btn.classList.add("hidden");
    return;
  }
  btn.classList.remove("hidden");

  if (authState.is_admin) {
    icon.textContent = "🔓";
    text.textContent = "Admin (Salir)";
    btn.className = "px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-sm font-medium rounded-lg transition border border-emerald-300 flex items-center gap-1.5";
  } else {
    icon.textContent = "🔒";
    text.textContent = "Ingresar";
    btn.className = "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition border border-slate-300 flex items-center gap-1.5";
  }

  // Deshabilitar o esconder controles de admin si es solo lectura
  document.querySelectorAll(".admin-only").forEach(el => {
    if (!authState.is_admin) {
      el.classList.add("opacity-50", "pointer-events-none");
    } else {
      el.classList.remove("opacity-50", "pointer-events-none");
    }
  });
}

function toggleAuthModal() {
  if (authState.is_admin && authState.auth_required) {
    if (confirm("¿Deseas cerrar la sesión de administración?")) {
      handleLogout();
    }
    return;
  }
  const modal = document.getElementById("login-modal");
  modal.classList.toggle("hidden");
  if (!modal.classList.contains("hidden")) {
    document.getElementById("admin-pass-input").value = "";
    document.getElementById("admin-pass-input").focus();
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const pass = document.getElementById("admin-pass-input").value.trim();
  if (!pass) return;
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pass }),
    });
    if (res.ok) {
      showToast("Sesión de administrador iniciada.");
      document.getElementById("login-modal").classList.add("hidden");
      await checkAuthStatus();
      loadCurrentTab();
    } else {
      const err = await res.json();
      showToast(err.detail || "Clave incorrecta.");
    }
  } catch (err) {
    showToast("Error de conexión al autenticar.");
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    showToast("Sesión cerrada. Modo lectura activado.");
    await checkAuthStatus();
    loadCurrentTab();
  } catch (e) {
    console.error(e);
  }
}

(async function init() {
  await checkAuthStatus();
  await loadConfigFilters();
  await loadStats();
  loadCurrentTab();
  pollScanStatus();
})();
