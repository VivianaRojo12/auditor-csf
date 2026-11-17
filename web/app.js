"use strict";
// Capa de presentación. Consume ÚNICAMENTE la API por HTTP (R8): nunca llama a modelos ni a la base vectorial.
const API = (window.AUDITOR_API || location.origin.replace(/:\d+$/, ":8000"));

const $ = (s) => document.querySelector(s);
const el = (t, cls, html) => { const e = document.createElement(t); if (cls) e.className = cls;
  if (html != null) e.innerHTML = html; return e; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(ruta, opciones) {
  const r = await fetch(API + ruta, opciones);
  if (!r.ok) { let d; try { d = await r.json(); } catch { d = {}; } throw new Error(d.detail || r.status); }
  return r.json();
}

// Funciones del CSF 2.0 en su orden oficial (mismas claves que servicio/csf.py).
const FUNCIONES = [["GV", "Gobernar"], ["ID", "Identificar"], ["PR", "Proteger"],
  ["DE", "Detectar"], ["RS", "Responder"], ["RC", "Recuperar"]];
const EXTENSIONES = ["pdf", "docx", "md", "markdown", "txt"];

// Archivos de demostración (los sirve web/servidor_web.py desde ejemplos/demo).
const DEMOS = [
  { ruta: "politica_ejemplo.md", titulo: "Política completa", formato: "MD",
    espera: "Seis secciones (acceso, respaldos, registros, incidentes, capacitación): recorre varias funciones." },
  { ruta: "demo/1_acceso_remoto.md", titulo: "Acceso remoto", formato: "MD",
    espera: "Brechas claras: credenciales compartidas y sesiones sin límite de tiempo." },
  { ruta: "demo/2_inyeccion.md", titulo: "Intento de inyección", formato: "MD",
    espera: "La «nota para el revisor» pide ignorar instrucciones; el guardrail debe bloquear esa sección." },
  { ruta: "demo/3_fuera_de_tema.md", titulo: "Fuera de tema", formato: "MD",
    espera: "Texto sin relación con seguridad: no debe generar hallazgos." },
  { ruta: "demo/4_respaldos.pdf", titulo: "Respaldos y recuperación", formato: "PDF",
    espera: "Lectura de PDF. Sin pruebas de restauración formales ni plan de contingencia." },
  { ruta: "demo/5_respuesta_incidentes.pdf", titulo: "Respuesta a incidentes", formato: "PDF",
    espera: "Lectura de PDF. Procedimiento más maduro: deberían aparecer controles cubiertos o parciales." },
  { ruta: "demo/6_vulnerabilidades.docx", titulo: "Vulnerabilidades y registros", formato: "DOCX",
    espera: "Lectura de DOCX. Inventario incompleto, excepciones en parches y registros de solo 7 días sin revisión." },
];

const fmtTamano = (b) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;
const fmtDuracion = (ms) => { const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

// --- Navegación ---
document.querySelectorAll(".pestana").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".pestana").forEach((x) => x.classList.remove("activa"));
  document.querySelectorAll(".vista").forEach((x) => x.classList.remove("activa"));
  b.classList.add("activa");
  $("#vista-" + b.dataset.vista).classList.add("activa");
  if (b.dataset.vista === "metricas") cargarMetricas();
  if (b.dataset.vista === "corpus") cargarCorpus();
}));

// --- Estado del servicio ---
// /health responde 503 cuando falta un componente; el cuerpo trae el detalle, así que se lee igual.
async function estado() {
  const e = $("#estado-servicio");
  let h;
  try { h = await (await fetch(API + "/health")).json(); }
  catch {
    e.textContent = "Sin conexión al servicio"; e.className = "estado mal";
    e.title = `No se pudo contactar la API en ${API}`; return;
  }
  $("#enlace-docs").href = API + "/docs";
  if (h.estado === "ok") {
    e.textContent = "Servicio en línea"; e.className = "estado ok"; e.title = "Modelos y corpus disponibles";
    return;
  }
  const comp = h.componentes || {};
  const faltan = [];
  if (!(comp.servidor_modelos && comp.servidor_modelos.disponible)) faltan.push("servidor de modelos sin conexión");
  if (!comp.corpus_indexado) faltan.push("corpus sin indexar");
  e.textContent = "Servicio incompleto" + (faltan.length ? ": " + faltan.join(" · ") : "");
  e.className = "estado aviso";
  e.title = JSON.stringify(comp, null, 1);
}

// --- Selección de archivo (clic o arrastrar) ---
let archivoElegido = null;
let auditando = false;

function elegirArchivo(archivo) {
  const info = $("#archivo-elegido");
  info.classList.remove("oculto", "error");
  const ext = (archivo.name.split(".").pop() || "").toLowerCase();
  if (!EXTENSIONES.includes(ext) || !archivo.name.includes(".")) {
    archivoElegido = null;
    info.classList.add("error");
    info.textContent = `«${archivo.name}» no es un formato admitido. Usa PDF, DOCX, Markdown o TXT.`;
  } else {
    archivoElegido = archivo;
    info.innerHTML = `Archivo listo: <strong>${esc(archivo.name)}</strong> · ${fmtTamano(archivo.size)}`;
  }
  actualizarBotones();
}

function actualizarBotones() {
  $("#btn-auditar").disabled = auditando || !archivoElegido;
  document.querySelectorAll(".demo").forEach((b) => { b.disabled = auditando; });
}

$("#archivo").addEventListener("change", () => { const f = $("#archivo").files[0]; if (f) elegirArchivo(f); });
const zona = $("#zona");
["dragenter", "dragover"].forEach((ev) => zona.addEventListener(ev, (e) => {
  e.preventDefault(); zona.classList.add("arrastrando"); }));
["dragleave", "drop"].forEach((ev) => zona.addEventListener(ev, (e) => {
  e.preventDefault(); zona.classList.remove("arrastrando"); }));
zona.addEventListener("drop", (e) => { const f = e.dataTransfer.files[0]; if (f && !auditando) elegirArchivo(f); });
// evita que soltar un archivo fuera de la zona haga que el navegador lo abra y se pierda la página
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());

$("#btn-auditar").addEventListener("click", () => auditar(archivoElegido));

function pintarDemos() {
  const cont = $("#demos");
  DEMOS.forEach((d) => {
    const b = el("button", "demo",
      `<span class="demo-cab"><span>${esc(d.titulo)}</span><span class="etiqueta">${d.formato}</span></span>
       <small>${esc(d.espera)}</small>`);
    b.addEventListener("click", async () => {
      try {
        const r = await fetch(d.ruta);
        if (!r.ok) throw new Error(`no se encontró ${d.ruta} (${r.status})`);
        const nombre = d.ruta.split("/").pop();
        auditar(new File([await r.blob()], nombre, { type: r.headers.get("Content-Type") || "" }));
      } catch (e) { mostrarError("No se pudo cargar el ejemplo: " + e.message); }
    });
    cont.appendChild(b);
  });
}

function mostrarError(msg) {
  const inf = $("#informe");
  inf.innerHTML = `<div class="bloqueada">${esc(msg)}</div>`;
  inf.classList.remove("oculto");
}

// --- Auditoría con avance por sección (POST /auditorias/stream, NDJSON) ---
let controlador = null;

async function* leerNdjson(resp) {
  const lector = resp.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { value, done } = await lector.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const linea = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (linea) yield JSON.parse(linea);
    }
  }
  if (buf.trim()) yield JSON.parse(buf);
}

async function auditar(archivo) {
  if (!archivo || auditando) return;
  auditando = true; actualizarBotones();
  $("#informe").classList.add("oculto");
  $("#ultimo-informe").classList.add("oculto");
  const prog = $("#progreso"); prog.classList.remove("oculto");
  $("#progreso-txt").textContent = `Enviando ${archivo.name}…`;
  $("#progreso-barra").style.width = "0%";
  $("#progreso-tiempo").textContent = "";
  $("#progreso-secciones").innerHTML = "";
  $("#hallazgos-vivo").innerHTML = "";
  $("#btn-cancelar").classList.remove("oculto");

  const avance = { inicio: performance.now(), total: 0, completadas: 0 };
  const reloj = setInterval(() => pintarTiempo(avance), 1000);
  controlador = new AbortController();
  const fd = new FormData(); fd.append("archivo", archivo);
  let terminado = false;
  try {
    const r = await fetch(API + "/auditorias/stream", { method: "POST", body: fd, signal: controlador.signal });
    if (!r.ok) { let d; try { d = await r.json(); } catch { d = {}; } throw new Error(d.detail || `HTTP ${r.status}`); }
    for await (const ev of leerNdjson(r)) {
      if (ev.tipo === "inicio") {
        avance.total = ev.total_secciones;
        pintarPasos(ev.secciones);
        marcarActivo(0);
        $("#progreso-txt").textContent = `Analizando ${ev.documento} · 0 de ${ev.total_secciones} secciones`;
      } else if (ev.tipo === "seccion") {
        avance.completadas = ev.completadas;
        marcarHecho(ev.completadas - 1, ev.seccion, ev.hallazgos);
        marcarActivo(ev.completadas);
        agregarHallazgosVivo(ev.hallazgos);
        $("#progreso-barra").style.width = (100 * ev.completadas / ev.total) + "%";
        $("#progreso-txt").textContent =
          `Analizando · ${ev.completadas} de ${ev.total} secciones` + (ev.completadas === ev.total ? " · armando informe…" : "");
        pintarTiempo(avance);
      } else if (ev.tipo === "fin") {
        terminado = true;
        prog.classList.add("oculto");
        pintarInforme(ev.informe);
        guardarInforme(ev.informe);
      } else if (ev.tipo === "error") {
        terminado = true;
        finalizarParcial(`El análisis se detuvo tras ${ev.completadas} de ${avance.total} secciones: ${ev.detalle}`);
      }
    }
    if (!terminado) finalizarParcial("La conexión con el servicio se cortó antes de terminar.");
  } catch (e) {
    if (e.name === "AbortError") {
      finalizarParcial(`Auditoría cancelada tras ${avance.completadas} de ${avance.total || "?"} secciones. ` +
        "Abajo quedan los hallazgos obtenidos hasta ese momento.");
    } else if (avance.total) {
      finalizarParcial("Error durante el análisis: " + e.message);
    } else {
      prog.classList.add("oculto");
      mostrarError("Error: " + e.message);
    }
  } finally {
    clearInterval(reloj);
    controlador = null; auditando = false; actualizarBotones();
  }
}

$("#btn-cancelar").addEventListener("click", () => { if (controlador) controlador.abort(); });

function finalizarParcial(msg) {
  $("#btn-cancelar").classList.add("oculto");
  $("#progreso-txt").textContent = msg;
  document.querySelectorAll("#progreso-secciones li.activo").forEach((li) => {
    li.classList.remove("activo"); li.querySelector(".icono").textContent = "–";
    li.querySelector(".detalle").textContent = "no analizada";
  });
}

function pintarTiempo(a) {
  let txt = `Transcurrido ${fmtDuracion(performance.now() - a.inicio)}`;
  if (a.completadas > 0 && a.completadas < a.total) {
    const restante = (performance.now() - a.inicio) / a.completadas * (a.total - a.completadas);
    txt += ` · quedan ~${fmtDuracion(restante)} (estimado con el ritmo actual)`;
  }
  $("#progreso-tiempo").textContent = txt;
}

function pintarPasos(secciones) {
  const ol = $("#progreso-secciones"); ol.innerHTML = "";
  secciones.forEach((s) => ol.appendChild(el("li", null,
    `<span class="icono">○</span><span>${esc(s.titulo)}</span><span class="detalle"></span>`)));
}

function marcarActivo(i) {
  const li = $("#progreso-secciones").children[i];
  if (!li) return;
  li.classList.add("activo"); li.querySelector(".icono").textContent = "◐";
  li.querySelector(".detalle").textContent = "analizando…";
}

function marcarHecho(i, s, hallazgos) {
  const li = $("#progreso-secciones").children[i];
  if (!li) return;
  li.classList.remove("activo");
  const det = li.querySelector(".detalle");
  if (s.bloqueada) {
    li.classList.add("bloqueado"); li.querySelector(".icono").textContent = "⛔";
    det.textContent = "bloqueada por los guardrails";
    return;
  }
  li.classList.add("hecho"); li.querySelector(".icono").textContent = "✓";
  const brechas = hallazgos.filter((h) => h.estado !== "cubierto").length;
  det.textContent = hallazgos.length
    ? `${hallazgos.length} hallazgo${hallazgos.length === 1 ? "" : "s"} · ${brechas} brecha${brechas === 1 ? "" : "s"}`
    : "sin hallazgos";
  if (s.cache && s.cache !== "ninguna") det.textContent += ` · caché ${s.cache}`;
}

function agregarHallazgosVivo(hallazgos) {
  const cont = $("#hallazgos-vivo");
  const brechas = hallazgos.filter((h) => h.estado !== "cubierto");
  if (!brechas.length) return;
  if (!cont.children.length) cont.appendChild(el("h4", null, "Brechas encontradas hasta ahora"));
  brechas.forEach((h) => cont.appendChild(tarjetaHallazgo(h)));
}

// --- Último informe (solo en este navegador) ---
const CLAVE_INFORME = "auditor.ultimoInforme";

function guardarInforme(inf) {
  try { localStorage.setItem(CLAVE_INFORME, JSON.stringify({ guardado: new Date().toISOString(), informe: inf })); }
  catch { /* sin almacenamiento disponible: no pasa nada */ }
}

function ofrecerUltimoInforme() {
  let dato = null;
  try { dato = JSON.parse(localStorage.getItem(CLAVE_INFORME) || "null"); } catch { dato = null; }
  if (!dato || !dato.informe) return;
  const aviso = $("#ultimo-informe");
  const fecha = new Date(dato.guardado).toLocaleString("es");
  aviso.innerHTML = `<span>Último informe: <strong>${esc(dato.informe.documento)}</strong> · ${esc(fecha)}</span>`;
  const ver = el("button", "secundario", "Ver informe");
  const quitar = el("button", "enlace", "Descartar");
  ver.onclick = () => { aviso.classList.add("oculto"); pintarInforme(dato.informe); };
  quitar.onclick = () => { try { localStorage.removeItem(CLAVE_INFORME); } catch { /* */ } aviso.classList.add("oculto"); };
  aviso.appendChild(ver); aviso.appendChild(quitar);
  aviso.classList.remove("oculto");
}

// --- Informe ---
function pintarInforme(inf) {
  const cont = $("#informe"); cont.innerHTML = "";
  const R = inf.resumen;
  cont.appendChild(el("h2", null, `Informe de auditoría — ${esc(inf.documento)}`));
  cont.appendChild(el("p", "meta-linea",
    `Traza ${esc(inf.traza_id)} · ${fmtDuracion(inf.tiempo_ms)} min · ${R.secciones_analizadas} secciones analizadas` +
    (R.secciones_bloqueadas.length ? ` · ${R.secciones_bloqueadas.length} bloqueadas` : "")));

  const cajas = el("div", "resumen-cajas");
  const dato = (n, et, alerta) => { const c = el("div", "caja" + (alerta ? " alerta" : ""));
    c.appendChild(el("div", "num", n)); c.appendChild(el("div", "et", et)); return c; };
  cajas.appendChild(dato(R.hallazgos_totales, "Hallazgos"));
  cajas.appendChild(dato(R.brechas, "Brechas"));
  cajas.appendChild(dato(R.brechas_graves, "Brechas graves", R.brechas_graves > 0));
  cajas.appendChild(dato(R.controles_citados.length, "Controles citados"));
  cont.appendChild(cajas);

  // Cobertura por función CSF: siempre las seis, aunque alguna no tenga hallazgos
  cont.appendChild(el("h3", null, "Cobertura por función del CSF 2.0"));
  cont.appendChild(el("p", "nota",
    "Indicador interno, no una calificación oficial del NIST: promedia los hallazgos de cada función " +
    "(cubierto = 1, parcial = 0.5, ausente = 0) y solo considera los controles recuperados para este documento."));
  const porCodigo = Object.fromEntries(inf.por_funcion.map((f) => [f.funcion, f]));
  const g = el("div", "funciones");
  FUNCIONES.forEach(([codigo, nombre]) => {
    const f = porCodigo[codigo];
    const d = el("div", "func" + (f ? "" : " sin-evaluar"));
    d.appendChild(el("div", "func-cab",
      `<span><strong>${codigo}</strong> · ${esc(nombre)}</span><span>${f ? Math.round(f.cobertura * 100) + "%" : "Sin evaluar"}</span>`));
    const m = el("div", "medidor"); const barra = el("div");
    if (f) {
      barra.style.width = (f.cobertura * 100) + "%";
      barra.style.background = f.cobertura >= .7 ? "var(--ok)" : f.cobertura >= .4 ? "var(--media)" : "var(--alta)";
    } else barra.style.width = "0%";
    m.appendChild(barra); d.appendChild(m);
    d.appendChild(el("small", null, f
      ? `${f.cubierto} cubiertos · ${f.parcial} parciales · ${f.ausente} ausentes`
      : "El documento no tocó controles de esta función."));
    g.appendChild(d);
  });
  cont.appendChild(g);

  // Prioridades
  if (inf.prioridades.length) {
    cont.appendChild(el("h3", null, "Prioridades de atención"));
    inf.prioridades.forEach((h) => cont.appendChild(tarjetaHallazgo(h)));
  }

  // Detalle por sección
  cont.appendChild(el("h3", "seccion-bloque", "Detalle por sección"));
  inf.secciones.forEach((s) => {
    const extra = [s.ruta || "-", s.cache !== "ninguna" ? "caché " + s.cache : "",
      s.iteraciones_agente > 1 ? "agente ×" + s.iteraciones_agente : ""].filter(Boolean).join(" · ");
    cont.appendChild(el("div", "seccion-bloque",
      `#${s.seccion} · ${esc(s.titulo)} <small class="meta-linea">[${esc(extra)}]</small>`));
    if (s.bloqueada) { cont.appendChild(el("div", "bloqueada", esc(s.mensaje || "Sección bloqueada por los guardrails."))); return; }
    const hs = inf.hallazgos.filter((h) => h.seccion === s.seccion);
    if (!hs.length) cont.appendChild(el("p", "ayuda", "Sin hallazgos en esta sección."));
    hs.forEach((h) => cont.appendChild(tarjetaHallazgo(h)));
  });

  // Retroalimentación ligada a la traza
  const retro = el("div", "retro");
  retro.appendChild(el("span", null, "¿Te fue útil este informe?"));
  const bSi = el("button", null, "Útil"); const bNo = el("button", null, "No útil");
  bSi.onclick = () => enviarRetro(inf.traza_id, true, retro);
  bNo.onclick = () => enviarRetro(inf.traza_id, false, retro);
  retro.appendChild(bSi); retro.appendChild(bNo);
  cont.appendChild(retro);
  cont.classList.remove("oculto");
}

function tarjetaHallazgo(h) {
  const estadoH = ["cubierto", "parcial", "ausente"].includes(h.estado) ? h.estado : "parcial";
  const d = el("div", "hallazgo estado-" + estadoH);
  d.appendChild(el("div", "cab",
    `<strong>${esc(h.control_id)}</strong>
     <span class="etiqueta estado-${estadoH}">${esc(h.estado)}</span>
     <span class="etiqueta grav-${esc(h.gravedad)}">gravedad ${esc(h.gravedad)}</span>
     <span class="etiqueta">función ${esc(h.funcion || "-")}</span>`));
  if (h.requisito) d.appendChild(el("p", "fuente", "<strong>Requisito del control:</strong> " + esc(h.requisito)));
  d.appendChild(el("p", null, esc(h.descripcion)));
  if (h.evidencia) d.appendChild(el("p", "evi", "“" + esc(h.evidencia) + "”"));
  if (h.recomendacion) d.appendChild(el("p", null, "<strong>Recomendación:</strong> " + esc(h.recomendacion)));
  const f = h.fuente || {};
  d.appendChild(el("div", "fuente",
    `Fuente: ${esc(f.control || h.control_id)} ${esc(f.titulo || "")}${f.puntaje != null ? " (similitud " + f.puntaje.toFixed(2) + ")" : ""}`));
  return d;
}

async function enviarRetro(traza, util, cont) {
  try { await api("/retroalimentacion", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ traza_id: traza, util }) });
    cont.innerHTML = "<span>Gracias, registramos tu retroalimentación.</span>";
  } catch (e) { cont.appendChild(el("span", null, " Error: " + esc(e.message))); }
}

// --- Consulta (función secundaria) ---
$("#btn-preguntar").addEventListener("click", preguntar);
$("#pregunta").addEventListener("keydown", (e) => { if (e.key === "Enter") preguntar(); });
async function preguntar() {
  const q = $("#pregunta").value.trim(); if (!q) return;
  const cont = $("#respuesta-consulta"); cont.classList.remove("oculto");
  cont.innerHTML = '<div class="barra-indef"></div>';
  try {
    const r = await api("/preguntas", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: q }) });
    cont.innerHTML = "";
    cont.appendChild(el("div", "hallazgo", esc(r.respuesta).replace(/\n/g, "<br>")));
    if (r.fuentes && r.fuentes.length) {
      const f = el("div", "meta-linea", "Fuentes: " + r.fuentes.map((x) => `${esc(x.control)} (${x.puntaje.toFixed(2)})`).join(" · "));
      cont.appendChild(f);
    }
  } catch (e) { cont.innerHTML = `<div class="bloqueada">Error: ${esc(e.message)}</div>`; }
}

// --- Métricas ---
$("#btn-refrescar").addEventListener("click", cargarMetricas);
async function cargarMetricas() {
  const cont = $("#metricas");
  try {
    const m = await api("/metricas");
    cont.innerHTML = "";
    const c = m.consultas;
    const cajas = el("div", "resumen-cajas");
    const dato = (n, et) => { const d = el("div", "caja"); d.appendChild(el("div", "num", n));
      d.appendChild(el("div", "et", et)); return d; };
    cajas.appendChild(dato(c.total, "Consultas"));
    cajas.appendChild(dato(c.latencia_ms.promedio + " ms", "Latencia media"));
    cajas.appendChild(dato(c.latencia_ms.p95 + " ms", "Latencia p95"));
    cajas.appendChild(dato(m.cache.tasa_aciertos != null ? Math.round(m.cache.tasa_aciertos * 100) + "%" : "—", "Aciertos de caché"));
    cajas.appendChild(dato(m.agente.iteraciones_promedio, "Iteraciones de agente"));
    cajas.appendChild(dato(m.retroalimentacion.total, "Retroalimentaciones"));
    cont.appendChild(cajas);

    cont.appendChild(el("h3", null, "Latencia por capa"));
    const t1 = el("table", "tabla"); t1.innerHTML = "<tr><th>Capa / etapa</th><th>n</th><th>promedio</th><th>p95</th><th>máx</th></tr>";
    Object.entries(m.latencia_por_capa_ms).forEach(([k, v]) =>
      t1.appendChild(el("tr", null, `<td>${esc(k)}</td><td>${v.n}</td><td>${v.promedio}</td><td>${v.p95}</td><td>${v.max}</td>`)));
    cont.appendChild(t1);

    cont.appendChild(el("h3", null, "Uso por modelo y enrutador"));
    const t2 = el("table", "tabla"); t2.innerHTML = "<tr><th>Modelo</th><th>llamadas</th><th>errores</th><th>lat. media</th></tr>";
    Object.entries(m.modelos).forEach(([k, v]) =>
      t2.appendChild(el("tr", null, `<td>${esc(k)}</td><td>${v.llamadas}</td><td>${v.errores}</td><td>${v.latencia_promedio_ms} ms</td>`)));
    cont.appendChild(t2);
    cont.appendChild(el("p", "meta-linea", "Rutas: " + esc(JSON.stringify(m.enrutador.por_ruta)) +
      " · usos de respaldo: " + m.enrutador.usos_respaldo));

    cont.appendChild(el("h3", null, "Guardrails"));
    const t3 = el("table", "tabla"); t3.innerHTML = "<tr><th>Verificación</th><th>evaluaciones</th><th>activaciones</th></tr>";
    Object.entries(m.guardrails).forEach(([k, v]) =>
      t3.appendChild(el("tr", null, `<td>${esc(k)}</td><td>${v.evaluaciones}</td><td>${v.activaciones}</td>`)));
    cont.appendChild(t3);
  } catch (e) { cont.innerHTML = `<div class="bloqueada">Error: ${esc(e.message)}</div>`; }
}

// --- Corpus ---
async function cargarCorpus() {
  const cont = $("#corpus");
  try {
    const d = await api("/documentos");
    cont.innerHTML = `<p class="meta-linea">${d.fragmentos_indexados} fragmentos indexados</p>`;
    const t = el("table", "tabla"); t.innerHTML = "<tr><th>Documento</th><th>Formato</th><th>Fragmentos</th></tr>";
    d.documentos.forEach((x) => t.appendChild(el("tr", null,
      `<td>${esc(x.nombre)}</td><td>${esc(x.formato)}</td><td>${x.fragmentos}</td>`)));
    cont.appendChild(t);
  } catch (e) { cont.innerHTML = `<div class="bloqueada">Error: ${esc(e.message)}</div>`; }
}

pintarDemos();
ofrecerUltimoInforme();
estado();
setInterval(estado, 15000);
