"use strict";
// Capa de presentación. Consume ÚNICAMENTE la API por HTTP (R8): nunca llama a modelos ni a la base vectorial.
// Es una sola página: las secciones cambian con el hash (#/auditar, #/informe, …) sin recargar, así una
// auditoría sigue corriendo mientras se navega por el sitio.
const API = (window.AUDITOR_API || location.origin.replace(/:\d+$/, ":8000"));

// ---------------------------------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------------------------------
const $ = (s, raiz = document) => raiz.querySelector(s);
const $$ = (s, raiz = document) => [...raiz.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(ruta, opciones) {
  const r = await fetch(API + ruta, opciones);
  if (!r.ok) {
    let d = {};
    try { d = await r.json(); } catch { /* sin cuerpo JSON */ }
    const detalle = Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join("; ") : d.detail;
    throw new Error(detalle || `HTTP ${r.status}`);
  }
  return r.json();
}
const postJSON = (ruta, cuerpo) => api(ruta, { method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(cuerpo) });

function leerLocal(clave, porDefecto = null) {
  try { const v = localStorage.getItem(clave); return v == null ? porDefecto : JSON.parse(v); } catch { return porDefecto; }
}
function guardarLocal(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)); } catch { /* almacenamiento no disponible */ }
}
function borrarLocal(clave) { try { localStorage.removeItem(clave); } catch { /* */ } }

const fmtTamano = (b) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1048576).toFixed(1)} MB`;
const fmtDuracion = (ms) => { const s = Math.max(0, Math.round(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
const fmtMs = (ms) => ms == null ? "—" : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
const fmtPct = (x) => x == null ? "—" : `${Math.round(x * 100)} %`;
const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
const fmtFecha = (iso) => { try { return new Date(iso).toLocaleString("es", { dateStyle: "medium", timeStyle: "short" }); } catch { return ""; } };

function descargar(nombre, contenido, tipo) {
  const url = URL.createObjectURL(new Blob([contenido], { type: tipo }));
  const a = Object.assign(document.createElement("a"), { href: url, download: nombre });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const MICHI = {
  compu: "img/michis/michi-compu.png", lap: "img/michis/michi-lap.png", libro: "img/michis/michi-libro.png",
  ok: "img/michis/michi-ok.png", piensa: "img/michis/michi-piensa.png", festejo: "img/michis/michi-festejo.png",
  tomatoso: "img/michis/michi-tomatoso.png",
};

const FUNCIONES = [["GV", "Gobernar"], ["ID", "Identificar"], ["PR", "Proteger"], ["DE", "Detectar"],
  ["RS", "Responder"], ["RC", "Recuperar"]];
const NOMBRE_FUNCION = Object.fromEntries(FUNCIONES);
const EXTENSIONES = ["pdf", "docx", "md", "markdown", "txt"];
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
    espera: "Lectura de DOCX. Inventario incompleto, excepciones en parches y registros de solo 7 días." },
];

const PIE = `<footer class="pie"><span>Las respuestas las genera un modelo de lenguaje y pueden contener errores.
  Verifica cada hallazgo contra el control citado.</span><a href="#/creditos">Créditos</a></footer>`;

// ---------------------------------------------------------------------------------------------------
// Navegación
// ---------------------------------------------------------------------------------------------------
const vista = $("#vista");
const VISTAS = {
  auditar: vistaAuditar, informe: vistaInforme, catalogo: vistaCatalogo, practicar: vistaPracticar,
  preguntar: vistaPreguntar, sistema: vistaSistema, creditos: vistaCreditos,
};

function rutaActual() {
  const partes = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const nombre = VISTAS[partes[0]] ? partes[0] : "auditar";
  return { nombre, params: VISTAS[partes[0]] ? partes.slice(1) : [] };
}

let primeraCarga = true;
function navegar() {
  const r = rutaActual();
  $$(".menu a").forEach((a) => {
    if (a.dataset.vista === r.nombre) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  VISTAS[r.nombre](r.params);
  if (!primeraCarga) { window.scrollTo(0, 0); vista.focus({ preventScroll: true }); }
  primeraCarga = false;
}
window.addEventListener("hashchange", navegar);
const enVista = (nombre) => rutaActual().nombre === nombre;

// ---------------------------------------------------------------------------------------------------
// Avisos flotantes
// ---------------------------------------------------------------------------------------------------
function avisar(html, imagen) {
  const caja = document.createElement("div");
  caja.className = "aviso-flotante";
  caja.innerHTML = `${imagen ? `<img src="${imagen}" alt="">` : ""}<span>${html}</span>
    <button class="enlace-boton" aria-label="Cerrar aviso">Cerrar</button>`;
  $("button", caja).onclick = () => caja.remove();
  $$("a", caja).forEach((a) => a.addEventListener("click", () => caja.remove()));
  $("#avisos").appendChild(caja);
  setTimeout(() => caja.remove(), 12000);
}

// ---------------------------------------------------------------------------------------------------
// Estado del servicio
// ---------------------------------------------------------------------------------------------------
// /health responde 503 cuando falta un componente; el cuerpo trae el detalle, así que se lee igual.
let saludServicio = null;
async function revisarServicio() {
  const caja = $("#estado-servicio");
  const texto = $("span:last-child", caja);
  try {
    saludServicio = await (await fetch(API + "/health")).json();
  } catch {
    saludServicio = null;
    caja.className = "estado-servicio mal"; texto.textContent = "Sin conexión al servicio";
    caja.title = `No se pudo contactar la API en ${API}`;
    return;
  }
  if (saludServicio.estado === "ok") {
    caja.className = "estado-servicio"; texto.textContent = "Servicio en línea"; caja.title = "Modelos y corpus disponibles";
    return;
  }
  const comp = saludServicio.componentes || {};
  const faltan = [];
  if (!(comp.servidor_modelos && comp.servidor_modelos.disponible)) faltan.push("modelos sin conexión");
  if (!comp.corpus_indexado) faltan.push("corpus sin indexar");
  caja.className = "estado-servicio aviso";
  texto.textContent = "Servicio incompleto" + (faltan.length ? `: ${faltan.join(", ")}` : "");
  caja.title = texto.textContent;
}

// ---------------------------------------------------------------------------------------------------
// Auditoría (corre en segundo plano mientras se navega)
// ---------------------------------------------------------------------------------------------------
const CLAVE_INFORME = "auditor.ultimoInforme";
const A = {
  estado: "inactiva",          // inactiva | enviando | analizando | lista | cancelada | error
  documento: "", total: 0, completadas: 0, secciones: [], brechas: [], inicio: 0,
  controlador: null, mensaje: "", informe: null, avisoPendiente: false, tecnicoAbierto: false,
  tecnico: { seccion: "", ruta: "", modelo: "", exacta: 0, semantica: 0, bloqueadas: 0, iteraciones: 0, traza: "" },
};
let archivoElegido = null;
const corriendo = () => A.estado === "enviando" || A.estado === "analizando";

function ultimoInforme() {
  if (A.informe) return { informe: A.informe, guardado: null };
  return leerLocal(CLAVE_INFORME);
}

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
  if (!archivo || corriendo()) return;
  Object.assign(A, {
    estado: "enviando", documento: archivo.name, total: 0, completadas: 0, secciones: [], brechas: [],
    inicio: performance.now(), mensaje: "", informe: null, avisoPendiente: false, controlador: new AbortController(),
    tecnico: { seccion: "", ruta: "", modelo: "", exacta: 0, semantica: 0, bloqueadas: 0, iteraciones: 0, traza: "" },
  });
  archivoElegido = null;
  refrescarAuditoria();
  const fd = new FormData(); fd.append("archivo", archivo);
  let terminado = false;
  try {
    const r = await fetch(API + "/auditorias/stream", { method: "POST", body: fd, signal: A.controlador.signal });
    if (!r.ok) { let d = {}; try { d = await r.json(); } catch { /* */ } throw new Error(d.detail || `HTTP ${r.status}`); }
    for await (const ev of leerNdjson(r)) {
      if (ev.tipo === "inicio") {
        A.estado = "analizando"; A.total = ev.total_secciones; A.documento = ev.documento; A.tecnico.traza = ev.traza_id;
        A.secciones = ev.secciones.map((s) => ({ titulo: s.titulo, estado: "pendiente", detalle: "pendiente" }));
      } else if (ev.tipo === "seccion_inicio") {
        const s = A.secciones[ev.completadas];
        if (s) { s.estado = "activo"; s.detalle = "analizando…"; }
        A.tecnico.seccion = ev.titulo;
      } else if (ev.tipo === "seccion") {
        A.completadas = ev.completadas;
        registrarSeccion(A.secciones[ev.completadas - 1], ev.seccion, ev.hallazgos);
      } else if (ev.tipo === "fin") {
        terminado = true;
        terminarAuditoria(ev.informe);
      } else if (ev.tipo === "error") {
        terminado = true;
        A.estado = "error";
        A.mensaje = `El análisis se detuvo tras ${A.completadas} de ${A.total} secciones: ${ev.detalle}`;
      }
      refrescarAuditoria();
    }
    if (!terminado) { A.estado = "error"; A.mensaje = "La conexión con el servicio se cortó antes de terminar."; }
  } catch (e) {
    if (e.name === "AbortError") {
      A.estado = "cancelada";
      A.mensaje = `Auditoría cancelada tras ${A.completadas} de ${A.total || "?"} secciones.`;
    } else {
      A.estado = "error";
      A.mensaje = A.total ? `Error durante el análisis: ${e.message}` : `No se pudo iniciar la auditoría: ${e.message}`;
    }
  } finally {
    A.controlador = null;
    A.secciones.forEach((s) => { if (s.estado === "activo" || s.estado === "pendiente") { s.estado = "no"; s.detalle = "no analizada"; } });
    if (A.estado === "error" && !enVista("auditar")) {
      avisar(`La auditoría de <strong>${esc(A.documento)}</strong> falló. <a href="#/auditar">Ver detalle</a>`, MICHI.tomatoso);
    }
    refrescarAuditoria();
  }
}

function registrarSeccion(paso, s, hallazgos) {
  const t = A.tecnico;
  t.seccion = s.titulo;
  if (s.bloqueada) {
    t.bloqueadas += 1;
    if (paso) { paso.estado = "bloqueado"; paso.detalle = "bloqueada por los guardrails"; }
    return;
  }
  t.ruta = s.ruta || t.ruta; t.modelo = s.modelo || t.modelo; t.iteraciones = s.iteraciones_agente;
  if (s.cache === "exacta") t.exacta += 1;
  if (s.cache === "semantica") t.semantica += 1;
  const brechas = hallazgos.filter((h) => h.estado !== "cubierto");
  A.brechas.push(...brechas);
  if (paso) {
    paso.estado = "hecho";
    paso.detalle = hallazgos.length ? `${plural(hallazgos.length, "hallazgo", "hallazgos")}, ${plural(brechas.length, "brecha", "brechas")}` : "sin hallazgos";
    if (s.cache && s.cache !== "ninguna") paso.detalle += `, caché ${s.cache === "semantica" ? "semántica" : s.cache}`;
  }
}

function terminarAuditoria(informe) {
  A.estado = "lista"; A.informe = informe;
  guardarLocal(CLAVE_INFORME, { guardado: new Date().toISOString(), informe });
  UI_INF.abiertos.clear(); UI_INF.retro = null;
  if (enVista("auditar")) {
    location.hash = "#/informe";
  } else {
    A.avisoPendiente = true;
    avisar(`<strong>Informe listo:</strong> ${esc(informe.documento)}. <a href="#/informe">Ver informe</a>`, MICHI.ok);
  }
}

function cancelarAuditoria() { if (A.controlador) A.controlador.abort(); }
window.addEventListener("beforeunload", (e) => { if (corriendo()) { e.preventDefault(); e.returnValue = ""; } });

function refrescarAuditoria() {
  pintarRecuadro();
  if (enVista("auditar")) vistaAuditar();
}

// Recuadro del michi en la barra lateral: solo el progreso.
function pintarRecuadro() {
  const r = $("#recuadro");
  if (corriendo()) {
    const pct = A.total ? Math.round(100 * A.completadas / A.total) : 0;
    r.className = "recuadro en-curso"; r.href = "#/auditar"; r.hidden = false;
    r.setAttribute("aria-label", `Auditoría en curso: ${pct} %. Ver avance`);
    r.innerHTML = `<img class="michi trabajando" src="${MICHI.compu}" alt="">
      <span class="barra"><span style="width:${pct}%"></span></span><strong>${pct} %</strong>`;
  } else if (A.estado === "lista" && A.avisoPendiente) {
    r.className = "recuadro listo"; r.href = "#/informe"; r.hidden = false; r.removeAttribute("aria-label");
    r.innerHTML = `<img class="michi" src="${MICHI.ok}" alt=""><strong>Informe listo</strong><small>Ver informe</small>`;
  } else if (A.estado === "error" && !enVista("auditar")) {
    r.className = "recuadro con-error"; r.href = "#/auditar"; r.hidden = false; r.removeAttribute("aria-label");
    r.innerHTML = `<img class="michi" src="${MICHI.tomatoso}" alt=""><strong>La auditoría falló</strong><small>Ver detalle</small>`;
  } else {
    r.hidden = true;
  }
}

setInterval(() => {
  if (!corriendo() || !enVista("auditar")) return;
  const t = $("#tiempo-auditoria");
  if (t) t.textContent = textoTiempo();
}, 1000);

function textoTiempo() {
  const transcurrido = performance.now() - A.inicio;
  let txt = `transcurrido ${fmtDuracion(transcurrido)}`;
  if (A.completadas > 0 && A.completadas < A.total) {
    txt += `, restante aprox. ${fmtDuracion(transcurrido / A.completadas * (A.total - A.completadas))}`;
  }
  return txt;
}

// ---------------------------------------------------------------------------------------------------
// Vista: Auditar
// ---------------------------------------------------------------------------------------------------
function vistaAuditar() {
  if (A.estado === "error" || A.estado === "cancelada") pintarRecuadro();
  if (corriendo() || A.estado === "error" || A.estado === "cancelada") return pintarAvance();
  pintarCarga();
}

function pintarCarga() {
  const ultimo = leerLocal(CLAVE_INFORME);
  vista.innerHTML = `
    <div class="titulo-vista"><h1>Auditar</h1>
      <p>Revisa una política o procedimiento contra los controles del NIST SP 800-53, agrupados por las funciones del CSF 2.0.</p></div>
    ${ultimo && ultimo.informe ? `<div class="aviso-linea" id="ultimo"><span>Último informe: <strong>${esc(ultimo.informe.documento)}</strong>, ${esc(fmtFecha(ultimo.guardado))}</span>
      <a class="boton chico" href="#/informe">Ver informe</a><button class="enlace-boton" id="descartar">Descartar</button></div>` : ""}
    <section class="tarjeta" style="align-items:center">
      <input type="file" id="archivo" class="visual-oculto" accept=".pdf,.docx,.md,.markdown,.txt">
      <label for="archivo" class="zona" id="zona">
        <svg aria-hidden="true" width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#6C5CC9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>
        <strong>Arrastra aquí una política o procedimiento</strong>
        <span>o haz clic para elegirlo (PDF, DOCX, Markdown o TXT)</span>
      </label>
      <div id="archivo-listo" class="archivo-listo" aria-live="polite"></div>
    </section>
    <section style="display:flex;flex-direction:column;gap:14px">
      <h2 class="seccion-titulo" style="font-size:20px">¿Sin archivo a la mano? Prueba un ejemplo</h2>
      <div class="demos">${DEMOS.map((d, i) => `
        <button class="demo" data-demo="${i}">
          <span class="demo-cab"><strong>${esc(d.titulo)}</strong><span class="formato ${d.formato.toLowerCase()}">${d.formato}</span></span>
          <small>${esc(d.espera)}</small>
        </button>`).join("")}</div>
    </section>
    ${PIE}`;

  const descartar = $("#descartar");
  if (descartar) descartar.onclick = () => { borrarLocal(CLAVE_INFORME); $("#ultimo").remove(); };
  $("#archivo").addEventListener("change", (e) => { if (e.target.files[0]) elegirArchivo(e.target.files[0]); });
  const zona = $("#zona");
  ["dragenter", "dragover"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.add("arrastrando"); }));
  ["dragleave", "drop"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.remove("arrastrando"); }));
  zona.addEventListener("drop", (e) => { const f = e.dataTransfer.files[0]; if (f) elegirArchivo(f); });
  $$("[data-demo]").forEach((b) => b.addEventListener("click", () => cargarDemo(DEMOS[b.dataset.demo])));
  pintarArchivoElegido();
}

function elegirArchivo(archivo) {
  const ext = archivo.name.includes(".") ? archivo.name.split(".").pop().toLowerCase() : "";
  archivoElegido = EXTENSIONES.includes(ext) ? archivo : { invalido: archivo.name };
  pintarArchivoElegido();
}

function pintarArchivoElegido() {
  const caja = $("#archivo-listo");
  if (!caja) return;
  caja.classList.remove("error");
  if (!archivoElegido) { caja.innerHTML = ""; return; }
  if (archivoElegido.invalido) {
    caja.classList.add("error");
    caja.textContent = `«${archivoElegido.invalido}» no es un formato admitido. Usa PDF, DOCX, Markdown o TXT.`;
    return;
  }
  caja.innerHTML = `<span>Archivo listo: <strong>${esc(archivoElegido.name)}</strong>, ${fmtTamano(archivoElegido.size)}</span>
    <button class="boton" id="btn-auditar">Auditar documento</button>`;
  $("#btn-auditar").onclick = () => auditar(archivoElegido);
}

async function cargarDemo(d) {
  try {
    const r = await fetch(d.ruta);
    if (!r.ok) throw new Error(`no se encontró ${d.ruta} (${r.status})`);
    auditar(new File([await r.blob()], d.ruta.split("/").pop(), { type: r.headers.get("Content-Type") || "" }));
  } catch (e) { avisar(`No se pudo cargar el ejemplo: ${esc(e.message)}`, MICHI.tomatoso); }
}

function pintarAvance() {
  const pct = A.total ? Math.round(100 * A.completadas / A.total) : 0;
  const t = A.tecnico;
  const terminada = !corriendo();
  const encabezado = corriendo()
    ? `<div class="titulo-vista"><h1>Auditando</h1><p>Puedes seguir navegando: el avance queda en la barra lateral y te avisamos cuando el informe esté listo.</p></div>`
    : `<div class="titulo-vista"><h1>${A.estado === "cancelada" ? "Auditoría cancelada" : "La auditoría no terminó"}</h1></div>`;
  const ICONOS = { hecho: "✓", bloqueado: "!", no: "–", pendiente: "", activo: "" };
  vista.innerHTML = `
    ${encabezado}
    ${terminada ? `<div class="${A.estado === "error" ? "error-caja" : "aviso-naranja"}" role="alert" style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
        <img class="michi" src="${A.estado === "error" ? MICHI.tomatoso : MICHI.piensa}" alt="" width="72" height="72">
        <span style="flex-grow:1">${esc(A.mensaje)}${A.brechas.length ? " Abajo quedan las brechas que se alcanzaron a encontrar." : ""}</span>
        <button class="boton chico" id="nueva">Nueva auditoría</button></div>` : ""}
    <section class="tarjeta">
      <div class="fila-titulo" style="align-items:center">
        <div><strong style="font-size:20px">${esc(A.documento)}</strong>
          <div class="tenue">${A.total ? `Sección ${Math.min(A.completadas + (corriendo() ? 1 : 0), A.total)} de ${A.total}` : "Enviando el documento…"}${corriendo() ? `, <span id="tiempo-auditoria">${textoTiempo()}</span>` : ""}</div></div>
        ${corriendo() ? `<button class="boton chico peligro" id="cancelar">Cancelar</button>` : ""}
      </div>
      <div class="barra-progreso" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" aria-label="Avance de la auditoría"><div style="width:${pct}%"></div></div>
      <ol class="pasos">${A.secciones.map((s) => `
        <li class="${s.estado}"><span class="icono" aria-hidden="true">${ICONOS[s.estado] || ""}</span>
          <span class="nombre">${esc(s.titulo)}</span><span>${esc(s.detalle)}</span></li>`).join("")}</ol>
    </section>
    <details class="tarjeta" id="tecnico" ${A.tecnicoAbierto ? "open" : ""}>
      <summary>Detalles técnicos</summary>
      <dl class="datos-tecnicos">
        <div><dt>${corriendo() ? "Sección en curso" : "Última sección"}</dt><dd>${esc(t.seccion || "—")}</dd></div>
        <div><dt>Ruta y modelo (última sección)</dt><dd>${t.ruta ? esc(`${t.ruta}, ${t.modelo || "caché"}`) : "—"}</dd></div>
        <div><dt>Caché</dt><dd>${t.exacta} exacta, ${t.semantica} semántica</dd></div>
        <div><dt>Guardrails</dt><dd>${plural(t.bloqueadas, "sección bloqueada", "secciones bloqueadas")}</dd></div>
        <div><dt>Ciclo de agente (última sección)</dt><dd>${plural(t.iteraciones || 0, "iteración", "iteraciones")}</dd></div>
        <div><dt>Traza</dt><dd>${esc(t.traza || "—")}</dd></div>
      </dl>
      <p class="nota"><a href="#/sistema">Ver métricas del sistema</a></p>
    </details>
    ${A.brechas.length ? `<section style="display:flex;flex-direction:column;gap:12px">
      <h2 class="seccion-titulo" style="font-size:18px">Brechas encontradas hasta ahora</h2>
      ${A.brechas.map((h) => `<div class="tarjeta" style="padding:16px 20px;gap:8px">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <strong style="font-size:17px">${esc(h.control_id)}</strong>
          <span class="pastilla ${esc(h.estado)}">${esc(capital(h.estado))}</span>
          <span class="gravedad ${esc(h.gravedad)}">Gravedad ${esc(h.gravedad)}</span>
          <span class="pastilla neutra">${esc(etiquetaFuncion(h.funcion))}</span></div>
        <p style="margin:0" class="tenue">${esc(h.seccion_titulo)}: ${esc(h.descripcion)}</p></div>`).join("")}
    </section>` : ""}
    ${PIE}`;
  $("#tecnico").addEventListener("toggle", (e) => { A.tecnicoAbierto = e.target.open; });
  const cancelar = $("#cancelar"); if (cancelar) cancelar.onclick = cancelarAuditoria;
  const nueva = $("#nueva"); if (nueva) nueva.onclick = () => { A.estado = "inactiva"; pintarRecuadro(); vistaAuditar(); };
}

const capital = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
const etiquetaFuncion = (f) => f ? `${f} – ${NOMBRE_FUNCION[f] || ""}`.replace(/ – $/, "") : "—";

// ---------------------------------------------------------------------------------------------------
// Vista: Informe
// ---------------------------------------------------------------------------------------------------
const UI_INF = { estado: "todos", gravedad: "todas", funcion: "todas", abiertos: new Set(), imprimir: false, retro: null };
const PESO_GRAVEDAD = { alta: 0, media: 1, baja: 2 };
const PESO_ESTADO = { ausente: 0, parcial: 1, cubierto: 2 };

function nombreControl(h) {
  const t = (h.fuente && h.fuente.titulo) || "";
  return t.startsWith(h.control_id) ? t.slice(h.control_id.length).trim() : t;
}

function vistaInforme() {
  if (A.estado === "lista" && A.avisoPendiente) { A.avisoPendiente = false; pintarRecuadro(); }
  const dato = ultimoInforme();
  if (!dato || !dato.informe) {
    vista.innerHTML = `<div class="titulo-vista"><h1>Último informe</h1></div>
      <section class="tarjeta" style="flex-direction:row;align-items:center;gap:24px;flex-wrap:wrap">
        <img class="michi" src="${MICHI.libro}" alt="" width="140" height="140">
        <div style="display:flex;flex-direction:column;gap:10px"><strong style="font-size:20px">Todavía no hay informes</strong>
          <span class="tenue">Audita una política o prueba uno de los ejemplos.</span>
          <a class="boton" href="#/auditar" style="align-self:flex-start">Ir a Auditar</a></div>
      </section>${PIE}`;
    return;
  }
  pintarInforme(dato.informe);
}

// Orden de atención: primero las brechas (los cubiertos al final), luego por gravedad y luego ausente antes que parcial.
function hallazgosOrdenados(inf) {
  const cubierto = (h) => (h.estado === "cubierto" ? 1 : 0);
  return inf.hallazgos.map((h, i) => ({ ...h, clave: i })).sort((a, b) =>
    cubierto(a) - cubierto(b) ||
    (PESO_GRAVEDAD[a.gravedad] ?? 3) - (PESO_GRAVEDAD[b.gravedad] ?? 3) ||
    (PESO_ESTADO[a.estado] ?? 3) - (PESO_ESTADO[b.estado] ?? 3));
}

function pintarInforme(inf) {
  const R = inf.resumen;
  const porCodigo = Object.fromEntries(inf.por_funcion.map((f) => [f.funcion, f]));
  const funcionesPresentes = [...new Set(inf.hallazgos.map((h) => h.funcion).filter(Boolean))];
  const filtrados = hallazgosOrdenados(inf).filter((h) =>
    (UI_INF.estado === "todos" || h.estado === UI_INF.estado) &&
    (UI_INF.gravedad === "todas" || h.gravedad === UI_INF.gravedad) &&
    (UI_INF.funcion === "todas" || h.funcion === UI_INF.funcion));
  const chips = (grupo, opciones) => opciones.map(([v, et]) =>
    `<button class="chip" data-filtro="${grupo}" data-valor="${v}" aria-pressed="${UI_INF[grupo] === v}">${et}</button>`).join("");
  const colorCob = (c) => c >= .7 ? "var(--ok-barra)" : c >= .4 ? "var(--parcial-barra)" : "var(--mal-barra)";
  const bloqueadas = R.secciones_bloqueadas.length;

  vista.innerHTML = `
    <div class="fila-titulo">
      <div class="titulo-vista"><h1>Informe de auditoría</h1>
        <p style="color:var(--texto);font-weight:800;font-size:17px">${esc(inf.documento)}</p>
        <p class="nota">${plural(R.secciones_analizadas, "sección analizada", "secciones analizadas")}${bloqueadas ? `, ${plural(bloqueadas, "bloqueada", "bloqueadas")}` : ""}, ${fmtDuracion(inf.tiempo_ms || 0)} min, traza ${esc(inf.traza_id)}</p></div>
      <div class="grupo-chips no-imprimir">
        <button class="boton chico" id="exp-pdf">Exportar PDF</button>
        <button class="boton chico secundario" id="exp-csv">CSV</button>
        <button class="boton chico secundario" id="exp-json">JSON</button>
      </div>
    </div>

    <div class="indicadores">
      <div class="indicador"><div class="num">${R.hallazgos_totales}</div><div class="et">Hallazgos</div></div>
      <div class="indicador"><div class="num">${R.brechas}</div><div class="et">Brechas</div></div>
      <div class="indicador ${R.brechas_graves ? "alerta" : ""}"><div class="num">${R.brechas_graves}</div><div class="et">Brechas graves</div></div>
      <div class="indicador"><div class="num">${R.controles_citados.length}</div><div class="et">Controles citados</div></div>
    </div>

    <section class="tarjeta">
      <h2>Cobertura por función del CSF 2.0</h2>
      <p class="nota">Indicador interno, no una calificación oficial del NIST: promedia los hallazgos de cada función
        (cubierto = 1, parcial = 0.5, ausente = 0) y solo considera los controles recuperados para este documento.</p>
      <div class="rejilla-3">${FUNCIONES.map(([cod, nombre]) => {
        const f = porCodigo[cod];
        if (!f) return `<div class="funcion sin-evaluar"><div class="funcion-cab"><span>${cod} – ${nombre}</span><span>Sin evaluar</span></div><div class="medidor"></div></div>`;
        return `<div class="funcion evaluada"><div class="funcion-cab"><span>${cod} – ${nombre}</span><span style="color:${colorCob(f.cobertura)}">${Math.round(f.cobertura * 100)} %</span></div>
          <div class="medidor"><div style="width:${f.cobertura * 100}%;background:${colorCob(f.cobertura)}"></div></div>
          <small>${f.cubierto} cubiertos, ${f.parcial} parciales, ${f.ausente} ausentes</small></div>`;
      }).join("")}</div>
    </section>

    <section class="tarjeta">
      <h2>Hallazgos</h2>
      <div class="grupo-chips no-imprimir" style="gap:22px">
        <div class="grupo-chips" role="group" aria-label="Filtrar por estado"><span>Estado</span>${chips("estado", [["todos", "Todos"], ["ausente", "Ausente"], ["parcial", "Parcial"], ["cubierto", "Cubierto"]])}</div>
        <div class="grupo-chips" role="group" aria-label="Filtrar por gravedad"><span>Gravedad</span>${chips("gravedad", [["todas", "Todas"], ["alta", "Alta"], ["media", "Media"], ["baja", "Baja"]])}</div>
        ${funcionesPresentes.length > 1 ? `<div class="grupo-chips" role="group" aria-label="Filtrar por función"><span>Función</span>${chips("funcion", [["todas", "Todas"], ...FUNCIONES.filter(([c]) => funcionesPresentes.includes(c)).map(([c]) => [c, c])])}</div>` : ""}
      </div>
      <div class="caja-tabla"><div class="tabla-hallazgos">
        <div class="fila-h cab-tabla" aria-hidden="true"><span>CONTROL</span><span>ESTADO</span><span>GRAVEDAD</span><span>FUNCIÓN</span><span>SECCIÓN</span><span></span></div>
        ${filtrados.map((h) => {
          const abierto = UI_INF.imprimir || UI_INF.abiertos.has(h.clave);
          return `<div class="hallazgo">
            <button class="fila-h" data-hallazgo="${h.clave}" aria-expanded="${abierto}">
              <span class="ctrl"><strong>${esc(h.control_id)}</strong> <span lang="en">${esc(nombreControl(h))}</span></span>
              <span><span class="pastilla ${esc(h.estado)}">${esc(capital(h.estado))}</span></span>
              <span><span class="gravedad ${esc(h.gravedad)}">${esc(capital(h.gravedad))}</span></span>
              <span style="font-size:14px;font-weight:700">${esc(etiquetaFuncion(h.funcion))}</span>
              <span style="font-size:14px" class="tenue">${esc(h.seccion_titulo)}</span>
              <span class="flecha" aria-hidden="true">${abierto ? "−" : "+"}</span>
            </button>
            ${abierto ? `<div class="detalle-h">
              <p class="descripcion">${esc(h.descripcion)}</p>
              <div><span class="rotulo">Evidencia en tu documento</span>${h.evidencia ? `<q>${esc(h.evidencia)}</q>` : `<p class="tenue">Sin cita textual.</p>`}</div>
              <div><span class="rotulo">Requisito del control</span><p>${esc(h.requisito || "—")}</p>
                <a class="no-imprimir" href="#/catalogo/${encodeURIComponent(h.control_id)}" style="font-size:13px;font-weight:800">Ver ${esc(h.control_id)} en el catálogo</a></div>
              <div class="sugerida"><span class="rotulo">Redacción sugerida</span><p>${esc(h.recomendacion || "—")}</p></div>
            </div>` : ""}
          </div>`;
        }).join("")}
        ${filtrados.length ? "" : `<p class="vacio">${inf.hallazgos.length ? "Sin hallazgos con este filtro." : "El análisis no encontró hallazgos en este documento."}</p>`}
      </div></div>
    </section>

    <details class="tarjeta" ${UI_INF.imprimir ? "open" : ""}>
      <summary>Detalle por sección</summary>
      <ul class="lista-secciones">${inf.secciones.map((s) => `<li><strong>${esc(s.titulo)}</strong>
        <span class="tenue">${s.bloqueada ? esc(s.mensaje || "Bloqueada por los guardrails") :
          [plural(s.hallazgos, "hallazgo", "hallazgos"), s.ruta ? `ruta ${s.ruta}` : "", s.cache !== "ninguna" ? `caché ${s.cache}` : "",
           s.iteraciones_agente > 1 ? `agente ${s.iteraciones_agente} iteraciones` : ""].filter(Boolean).map(esc).join(", ")}</span></li>`).join("")}</ul>
    </details>

    <section class="tarjeta no-imprimir" id="retro">${pintarRetro(inf)}</section>
    ${PIE}`;

  $$("[data-filtro]").forEach((b) => b.onclick = () => { UI_INF[b.dataset.filtro] = b.dataset.valor; pintarInforme(inf); });
  $$("[data-hallazgo]").forEach((b) => b.onclick = () => {
    const k = Number(b.dataset.hallazgo);
    if (UI_INF.abiertos.has(k)) UI_INF.abiertos.delete(k); else UI_INF.abiertos.add(k);
    pintarInforme(inf);
    $(`[data-hallazgo="${k}"]`).focus();
  });
  $("#exp-pdf").onclick = () => {
    UI_INF.imprimir = true; pintarInforme(inf);
    window.print();
    UI_INF.imprimir = false; pintarInforme(inf);
  };
  $("#exp-csv").onclick = () => descargar(nombreArchivo(inf, "csv"), "﻿" + informeCSV(inf), "text/csv;charset=utf-8");
  $("#exp-json").onclick = () => descargar(nombreArchivo(inf, "json"), JSON.stringify(inf, null, 2), "application/json");
  activarRetro(inf);
}

const nombreArchivo = (inf, ext) => `informe_${(inf.documento || "auditoria").replace(/\.[^.]+$/, "").replace(/[^\w-]+/g, "_")}.${ext}`;

function informeCSV(inf) {
  const columnas = ["control_id", "estado", "gravedad", "funcion", "seccion", "seccion_titulo", "descripcion", "evidencia", "requisito", "recomendacion"];
  const celda = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  return [columnas.join(","), ...inf.hallazgos.map((h) => columnas.map((c) => celda(h[c])).join(","))].join("\r\n");
}

function pintarRetro() {
  if (UI_INF.retro === "enviada") return `<strong>Gracias, registramos tu opinión.</strong>`;
  return `<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <strong style="font-size:16px">¿Te fue útil este informe?</strong>
      <button class="boton chico" style="background:var(--ok-fondo);color:var(--ok-texto);border-color:var(--ok-fondo)" data-util="true">Útil</button>
      <button class="boton chico" style="background:var(--mal-fondo);color:var(--mal-texto);border-color:var(--mal-fondo)" data-util="false">No útil</button>
    </div>
    <label class="etiqueta-campo" for="comentario">Comentario (opcional)</label>
    <textarea id="comentario" class="campo" rows="2" maxlength="1000" placeholder="¿Qué hallazgo no fue correcto o qué faltó?"></textarea>
    <span id="retro-error" class="nota" style="color:var(--mal-texto)"></span>`;
}

function activarRetro(inf) {
  $$("[data-util]").forEach((b) => b.onclick = async () => {
    try {
      const comentario = ($("#comentario").value || "").trim() || null;
      await postJSON("/retroalimentacion", { traza_id: inf.traza_id, util: b.dataset.util === "true", comentario });
      UI_INF.retro = "enviada"; $("#retro").innerHTML = pintarRetro();
    } catch (e) { $("#retro-error").textContent = `No se pudo enviar: ${e.message}`; }
  });
}

// ---------------------------------------------------------------------------------------------------
// Vista: Catálogo de controles
// ---------------------------------------------------------------------------------------------------
const CAT = { controles: null, familias: null, detalles: {}, texto: "", familia: "", elegido: "AC-1" };

async function cargarCatalogo() {
  if (!CAT.controles) {
    const [c, f] = await Promise.all([api("/controles"), api("/controles/familias")]);
    CAT.controles = c.controles; CAT.familias = f.familias;
  }
}

async function vistaCatalogo(params) {
  if (params[0]) CAT.elegido = params[0].toUpperCase();
  vista.innerHTML = `<div class="titulo-vista"><h1>Catálogo de controles</h1>
    <p>Los controles del NIST SP 800-53 Rev. 5 con su texto oficial, en inglés como en el original.</p></div>
    <div id="cat-cuerpo"><p class="tenue">Cargando el catálogo…</p></div>${PIE}`;
  try { await cargarCatalogo(); } catch (e) {
    $("#cat-cuerpo").innerHTML = `<div class="error-caja">No se pudo cargar el catálogo: ${esc(e.message)}</div>`; return;
  }
  if (!enVista("catalogo")) return;
  const sel = CAT.controles.find((c) => c.id === CAT.elegido);
  if (params[0] && sel && CAT.familia && CAT.familia !== sel.familia) CAT.familia = "";
  $("#cat-cuerpo").innerHTML = `
    <div class="tarjeta" style="padding:18px 20px;gap:12px">
      <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end">
        <div style="flex:2 1 280px;display:flex;flex-direction:column;gap:6px">
          <label class="etiqueta-campo" for="buscar">Buscar por ID o nombre</label>
          <input id="buscar" class="campo" type="search" placeholder="Ej.: AC-2, remote, incident" value="${esc(CAT.texto)}"></div>
        <div style="flex:1 1 220px;display:flex;flex-direction:column;gap:6px">
          <label class="etiqueta-campo" for="familia">Familia</label>
          <select id="familia" class="campo"><option value="">Todas las familias</option>
            ${CAT.familias.map((f) => `<option value="${f.familia}" ${CAT.familia === f.familia ? "selected" : ""}>${f.familia} – ${esc(f.nombre)} (${f.controles})</option>`).join("")}
          </select></div>
      </div>
    </div>
    <div class="catalogo" style="margin-top:22px">
      <section class="lista-controles" aria-label="Resultados"><div class="cab" id="cat-conteo"></div><div class="desplazable" id="cat-lista"></div></section>
      <article class="tarjeta ficha" id="cat-ficha"></article>
    </div>`;
  $("#buscar").addEventListener("input", (e) => { CAT.texto = e.target.value; pintarListaCatalogo(); });
  $("#familia").addEventListener("change", (e) => { CAT.familia = e.target.value; pintarListaCatalogo(); });
  pintarListaCatalogo();
  pintarFicha();
}

function pintarListaCatalogo() {
  const q = CAT.texto.trim().toLowerCase();
  const lista = CAT.controles.filter((c) => (!CAT.familia || c.familia === CAT.familia) &&
    (!q || c.id.toLowerCase().includes(q) || c.nombre.toLowerCase().includes(q)));
  $("#cat-conteo").textContent = plural(lista.length, "CONTROL", "CONTROLES");
  $("#cat-lista").innerHTML = lista.length ? lista.map((c) => `
    <button data-control="${c.id}" aria-current="${c.id === CAT.elegido}"><strong>${c.id}</strong><span lang="en">${esc(c.nombre)}</span></button>`).join("")
    : `<p class="vacio">Ningún control coincide con la búsqueda.</p>`;
  $$("#cat-lista [data-control]").forEach((b) => b.onclick = () => {
    CAT.elegido = b.dataset.control;
    history.replaceState(null, "", `#/catalogo/${CAT.elegido}`);
    $$("#cat-lista [data-control]").forEach((x) => x.setAttribute("aria-current", String(x === b)));
    pintarFicha();
  });
}

async function pintarFicha() {
  const ficha = $("#cat-ficha");
  if (!ficha) return;
  const id = CAT.elegido;
  let d = CAT.detalles[id];
  if (!d) {
    ficha.innerHTML = `<p class="tenue">Cargando ${esc(id)}…</p>`;
    try { d = CAT.detalles[id] = await api(`/controles/${encodeURIComponent(id)}`); }
    catch (e) { ficha.innerHTML = `<div class="error-caja">No se encontró el control ${esc(id)}.</div>`; return; }
    if (CAT.elegido !== id || !$("#cat-ficha")) return;
  }
  ficha.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:6px">
      <h2><span class="id">${esc(d.id)}</span> <span lang="en">${esc(d.nombre)}</span></h2>
      <div class="grupo-chips"><span class="pastilla neutra">${esc(d.familia)} – ${esc(d.familia_nombre)}</span>
        <span class="pastilla neutra">Función ${esc(d.funcion)} – ${esc(d.funcion_nombre)}</span></div>
      <p class="nota">La función del CSF viene de la correspondencia hecha para este proyecto, no de un crosswalk oficial del NIST.</p>
    </div>
    <div class="texto-oficial"><span class="rotulo" style="font-size:12px;font-weight:900;color:var(--tenue);letter-spacing:.5px">TEXTO OFICIAL DEL CONTROL</span>
      <ul lang="en">${d.texto.map((t) => `<li class="n${Math.min(t.nivel, 2)}">${esc(t.linea)}</li>`).join("")}</ul>
      <span class="nota">Fuente: ${esc(d.fuente)}</span></div>
    <div class="grupo-chips">
      <a class="boton" href="#/practicar/${encodeURIComponent(d.familia)}">Practicar esta familia</a>
      <a class="boton secundario" href="#/preguntar/${encodeURIComponent(`¿Qué exige el control ${d.id}?`)}">Preguntar sobre ${esc(d.id)}</a>
    </div>`;
}

// ---------------------------------------------------------------------------------------------------
// Vista: Practicar (cuestionarios con datos oficiales y michis)
// ---------------------------------------------------------------------------------------------------
const CLAVE_PROGRESO = "auditor.progreso";
let Q = null;   // cuestionario en curso: { familia, nombre, preguntas, i, respuestas, terminado, repaso }

function progreso() { return leerLocal(CLAVE_PROGRESO, { familias: {}, cuestionarios: 0, mejor: null }); }

function michiPorPuntaje(pct) {
  if (pct >= 80) return { img: MICHI.festejo, alt: "Michi festejando con confeti", msg: "¡Excelente!", color: "var(--ok-texto)" };
  if (pct >= 40) return { img: MICHI.ok, alt: "Michi con el pulgar arriba", msg: "¡Vas muy bien!", color: "var(--parcial-texto)" };
  return { img: MICHI.tomatoso, alt: "Michi llorando", msg: "¡Vuelve a intentarlo!", color: "var(--mal-fuerte)" };
}

async function vistaPracticar(params) {
  const fam = params[0] ? params[0].toUpperCase() : null;
  if (!fam) return pintarInicioPractica();
  const clave = fam === "TODAS" ? "" : fam;
  if (!Q || Q.familia !== clave) await nuevoCuestionario(clave);
  else pintarCuestionario();
}

async function nuevoCuestionario(familia) {
  vista.innerHTML = `<div class="titulo-vista"><h1>Practicar</h1></div><p class="tenue">Preparando las preguntas…</p>`;
  try {
    const datos = await api(`/cuestionarios?n=10${familia ? `&familia=${encodeURIComponent(familia)}` : ""}`);
    Q = { familia, nombre: datos.familia_nombre, preguntas: datos.preguntas, i: 0, respuestas: [], terminado: false, repaso: false };
  } catch (e) {
    vista.innerHTML = `<div class="titulo-vista"><h1>Practicar</h1></div><div class="error-caja">No se pudo armar el cuestionario: ${esc(e.message)}</div>
      <a class="boton secundario" href="#/practicar" style="align-self:flex-start">Volver</a>`;
    return;
  }
  if (enVista("practicar")) pintarCuestionario();
}

async function pintarInicioPractica() {
  const P = progreso();
  vista.innerHTML = `
    <div class="titulo-vista"><h1>Practicar</h1>
      <p>Preguntas armadas con los datos oficiales del NIST SP 800-53: ID, nombre, familia y texto de cada control.</p></div>
    <section class="tarjeta" style="flex-direction:row;align-items:center;gap:20px;flex-wrap:wrap">
      <img class="michi" src="${MICHI.libro}" alt="Michi estudiando con un libro" width="120" height="120">
      <div style="flex:1 1 300px;display:flex;flex-direction:column;gap:4px">
        <strong style="font-size:20px">Elige un tema y responde 10 preguntas</strong>
        <span class="tenue">Al terminar verás tu puntaje y tu avance por familia. El progreso se guarda en este navegador.</span></div>
    </section>
    <div class="familias" id="familias"><p class="tenue">Cargando familias…</p></div>
    <section class="tarjeta" id="mi-progreso">${pintarMiProgreso(P)}</section>
    <div class="bandas">
      <div class="banda"><img class="michi" src="${MICHI.tomatoso}" alt=""><span><strong>0–39 %</strong><br>¡Vuelve a intentarlo!</span></div>
      <div class="banda"><img class="michi" src="${MICHI.ok}" alt=""><span><strong>40–79 %</strong><br>¡Vas muy bien!</span></div>
      <div class="banda"><img class="michi" src="${MICHI.festejo}" alt=""><span><strong>80–100 %</strong><br>¡Excelente!</span></div>
    </div>
    ${PIE}`;
  try { await cargarCatalogo(); } catch (e) {
    $("#familias").innerHTML = `<div class="error-caja">No se pudieron cargar las familias: ${esc(e.message)}</div>`; return;
  }
  if (!enVista("practicar") || !$("#familias")) return;
  $("#mi-progreso").innerHTML = pintarMiProgreso(P);   // ahora con los nombres de las familias
  activarBorrarProgreso();
  $("#familias").innerHTML = `<a class="familia todas" href="#/practicar/todas"><strong>Todas las familias</strong>
      <span>${CAT.controles.length} controles, ${CAT.familias.length} familias</span></a>` +
    CAT.familias.map((f) => {
      const p = P.familias[f.familia];
      const dominio = p && p.total ? p.aciertos / p.total : null;
      return `<a class="familia" href="#/practicar/${f.familia}"><strong>${f.familia} – ${esc(f.nombre)}</strong>
        <span>${plural(f.controles, "control", "controles")}${dominio != null ? `, dominio ${Math.round(dominio * 100)} %` : ""}</span>
        ${dominio != null ? `<span class="mini"><span style="display:block;height:100%;width:${dominio * 100}%;background:${colorDominio(dominio)}"></span></span>` : ""}</a>`;
    }).join("");
}

const colorDominio = (d) => d >= .8 ? "var(--ok-barra)" : d >= .4 ? "var(--parcial-barra)" : "var(--mal-barra)";

function pintarMiProgreso(P) {
  const filas = Object.entries(P.familias).filter(([, v]) => v.total).sort((a, b) => b[1].aciertos / b[1].total - a[1].aciertos / a[1].total);
  const nombres = CAT.familias ? Object.fromEntries(CAT.familias.map((f) => [f.familia, f.nombre])) : {};
  return `<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <img class="michi" src="${MICHI.libro}" alt="" width="64" height="64">
      <div style="display:flex;flex-direction:column;gap:2px"><h2 style="font-size:22px">Mi progreso</h2>
        <span class="nota">${P.cuestionarios ? `${plural(P.cuestionarios, "cuestionario", "cuestionarios")}${P.mejor ? `, mejor puntaje ${P.mejor.aciertos} de ${P.mejor.total}` : ""}, guardado en este navegador` : "Aún no has hecho cuestionarios."}</span></div>
    </div>
    ${filas.length ? `<div style="display:flex;flex-direction:column;gap:12px">${filas.map(([fam, v]) => {
      const d = v.aciertos / v.total;
      return `<div class="progreso-familia"><span style="font-weight:800">${fam}${nombres[fam] ? ` – ${esc(nombres[fam])}` : ""}</span>
        <div class="medidor"><div style="width:${d * 100}%;background:${colorDominio(d)}"></div></div>
        <span class="valor">${Math.round(d * 100)} % <span class="nota">(${v.aciertos}/${v.total})</span></span></div>`;
    }).join("")}</div>
    <p class="nota">El dominio de cada familia se calcula con todos tus aciertos acumulados.</p>
    <button class="enlace-boton" id="reiniciar-progreso" style="align-self:flex-start">Borrar mi progreso</button>` : ""}`;
}

function pintarCuestionario() {
  if (Q.terminado) return pintarResultado();
  const p = Q.preguntas[Q.i];
  const resp = Q.respuestas[Q.i];
  const respondida = resp != null;
  const acerto = respondida && resp === p.correcta;
  const aciertos = Q.respuestas.filter((r, i) => r === Q.preguntas[i].correcta).length;
  const errores = Q.respuestas.filter((r) => r != null).length - aciertos;
  const pct = Math.round(100 * (Q.i + (respondida ? 1 : 0)) / Q.preguntas.length);
  const michi = !respondida ? { img: MICHI.libro, alt: "Michi estudiando con un libro", txt: "Elige una respuesta" }
    : acerto ? { img: MICHI.ok, alt: "Michi con el pulgar arriba", txt: "¡Muy bien!" }
      : { img: MICHI.piensa, alt: "Michi pensativo", txt: "Piénsalo otra vez" };
  const ex = p.explicacion;
  const ultima = Q.i === Q.preguntas.length - 1;
  vista.innerHTML = `
    <div class="fila-titulo"><div class="titulo-vista"><h1>Practicar</h1></div>
      <a class="boton chico secundario" href="#/practicar">Salir del cuestionario</a></div>
    <section class="tarjeta cuestionario">
      <div class="pregunta">
        <div class="fila-titulo" style="align-items:center">
          <strong style="color:var(--morado-osc);font-size:16px">${esc(Q.nombre)}, ${Q.preguntas.length} preguntas</strong>
          <span style="font-weight:800">Aciertos ${aciertos}, errores ${errores}</span></div>
        <div style="display:flex;flex-direction:column;gap:6px">
          <span class="nota" style="font-weight:700">Pregunta ${Q.i + 1} de ${Q.preguntas.length}</span>
          <div class="barra-progreso" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" aria-label="Avance del cuestionario"><div style="width:${pct}%"></div></div></div>
        <h2>${esc(p.enunciado)}</h2>
        <div class="opciones" role="group" aria-label="Opciones">${p.opciones.map((o, i) => {
          let cls = "";
          if (respondida && i === p.correcta) cls = "correcta";
          else if (respondida && i === resp) cls = "incorrecta";
          return `<button class="opcion ${cls}" data-opcion="${i}" ${respondida ? "disabled" : ""} lang="${p.opciones_idioma}">${esc(o)}</button>`;
        }).join("")}</div>
        ${respondida ? `<div class="retro-respuesta ${acerto ? "bien" : "mal"}" role="status">
          <strong>${acerto ? "¡Correcto!" : "Casi. La respuesta es"} ${esc(ex.control)} <span lang="en">${esc(ex.nombre)}</span></strong>
          <span>Familia ${esc(ex.familia)} – ${esc(ex.familia_nombre)}.</span>
          ${ex.requisito ? `<span>Texto oficial: <q lang="en" style="font-style:italic">${esc(ex.requisito)}</q></span>` : ""}</div>
          <div class="grupo-chips">
            <button class="boton" id="siguiente">${ultima ? "Ver resultado" : "Siguiente pregunta"}</button>
            <a class="enlace-boton" style="display:inline-flex;align-items:center" href="#/catalogo/${encodeURIComponent(ex.control)}">Ver ${esc(ex.control)} en el catálogo</a></div>` : ""}
      </div>
      <figure class="michi-lado"><img class="michi" src="${michi.img}" alt="${michi.alt}"><figcaption>${michi.txt}</figcaption></figure>
    </section>
    ${PIE}`;
  $$("[data-opcion]").forEach((b) => b.onclick = () => { Q.respuestas[Q.i] = Number(b.dataset.opcion); pintarCuestionario(); $("#siguiente").focus(); });
  const sig = $("#siguiente");
  if (sig) sig.onclick = () => {
    if (ultima) { Q.terminado = true; guardarResultado(); } else { Q.i += 1; }
    pintarCuestionario();
  };
}

function guardarResultado() {
  const P = progreso();
  Q.preguntas.forEach((p, i) => {
    const fam = p.explicacion.familia;
    const f = P.familias[fam] || (P.familias[fam] = { aciertos: 0, total: 0 });
    f.total += 1; if (Q.respuestas[i] === p.correcta) f.aciertos += 1;
  });
  const aciertos = Q.respuestas.filter((r, i) => r === Q.preguntas[i].correcta).length;
  P.cuestionarios += 1;
  if (!P.mejor || aciertos / Q.preguntas.length > P.mejor.aciertos / P.mejor.total) P.mejor = { aciertos, total: Q.preguntas.length };
  guardarLocal(CLAVE_PROGRESO, P);
}

function pintarResultado() {
  const total = Q.preguntas.length;
  const aciertos = Q.respuestas.filter((r, i) => r === Q.preguntas[i].correcta).length;
  const pct = Math.round(100 * aciertos / total);
  const m = michiPorPuntaje(pct);
  const errores = Q.preguntas.map((p, i) => ({ p, r: Q.respuestas[i] })).filter((x) => x.r !== x.p.correcta);
  const mensajeExtra = pct >= 80 ? `Dominas ${esc(Q.nombre)}.` : pct >= 40 ? "Repasa tus errores para llegar al 80 %." : "Revisa el catálogo de esta familia y prueba otra vez.";
  vista.innerHTML = `
    <div class="titulo-vista"><h1>Resultado</h1></div>
    <section class="tarjeta resultado">
      <img class="michi" src="${m.img}" alt="${m.alt}">
      <div class="cifras">
        <span class="tenue" style="font-weight:800">${esc(Q.nombre)}, ${total} preguntas</span>
        <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap">
          <strong class="grande" style="color:${m.color}">${pct} %</strong><span style="font-size:20px;font-weight:800">${aciertos} de ${total}</span></div>
        <p style="margin:0;font-size:20px;font-weight:800">${m.msg} ${mensajeExtra}</p>
        <div class="grupo-chips" style="margin-top:8px">
          <button class="boton" id="repetir">Otro cuestionario de este tema</button>
          <a class="boton secundario" href="#/practicar">Elegir otro tema</a>
          ${errores.length ? `<button class="boton secundario" id="repasar" aria-expanded="${Q.repaso}">Repasar mis errores</button>` : ""}
        </div>
      </div>
    </section>
    ${Q.repaso && errores.length ? `<section class="tarjeta"><h2>Tus errores</h2><ul class="repaso">${errores.map(({ p, r }) => `
      <li><strong>${esc(p.enunciado)}</strong>
        <span>Respondiste: <span lang="${p.opciones_idioma}">${esc(p.opciones[r])}</span></span>
        <span>Correcta: <strong lang="${p.opciones_idioma}">${esc(p.opciones[p.correcta])}</strong>
          (<a href="#/catalogo/${encodeURIComponent(p.explicacion.control)}">${esc(p.explicacion.control)}</a>)</span></li>`).join("")}</ul></section>` : ""}
    <section class="tarjeta" id="mi-progreso">${pintarMiProgreso(progreso())}</section>
    ${PIE}`;
  $("#repetir").onclick = () => nuevoCuestionario(Q.familia);
  const rep = $("#repasar"); if (rep) rep.onclick = () => { Q.repaso = !Q.repaso; pintarResultado(); };
  activarBorrarProgreso();
}

function activarBorrarProgreso() {
  const b = $("#reiniciar-progreso");
  if (b) b.onclick = () => {
    if (!confirm("¿Borrar todo tu progreso de práctica en este navegador?")) return;
    borrarLocal(CLAVE_PROGRESO);
    if (enVista("practicar") && !Q?.terminado) pintarInicioPractica(); else $("#mi-progreso").innerHTML = pintarMiProgreso(progreso());
  };
}

// ---------------------------------------------------------------------------------------------------
// Vista: Preguntar
// ---------------------------------------------------------------------------------------------------
const PREG = { texto: "", cargando: false, respuesta: null, error: "" };
const IDEAS = ["¿Qué exige el control de acceso remoto?", "¿Cada cuánto se deben probar los respaldos?", "¿Qué debe incluir el manejo de incidentes?"];

function vistaPreguntar(params) {
  if (params[0] && !PREG.cargando) { PREG.texto = params[0]; PREG.respuesta = null; PREG.error = ""; }
  pintarPreguntar();
}

function pintarPreguntar() {
  const r = PREG.respuesta;
  vista.innerHTML = `
    <div class="titulo-vista"><h1>Preguntar</h1>
      <p>Pregunta sobre los controles. La respuesta solo usa los controles que encuentra en el corpus y los cita.</p></div>
    ${corriendo() ? `<div class="aviso-naranja" role="note">Hay una auditoría en curso: la respuesta tardará más, porque ambas usan el mismo modelo en tu equipo.</div>` : ""}
    <section class="tarjeta">
      <form id="form-pregunta" style="display:flex;flex-direction:column;gap:14px">
        <label class="etiqueta-campo" for="pregunta" style="font-size:15px;color:var(--texto)">Tu pregunta</label>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          <input id="pregunta" class="campo" style="flex:1 1 320px;width:auto" minlength="3" maxlength="2000" value="${esc(PREG.texto)}" placeholder="¿Qué exige el control de respuesta a incidentes?">
          <button class="boton" ${PREG.cargando ? "disabled" : ""}>Preguntar</button></div>
      </form>
      <div class="grupo-chips"><span>Ideas:</span>${IDEAS.map((t, i) => `<button class="chip" data-idea="${i}">${esc(t)}</button>`).join("")}</div>
    </section>
    ${PREG.cargando ? `<section class="tarjeta cargando" aria-live="polite">
        <img class="michi trabajando" src="${MICHI.lap}" alt="Michi trabajando en su laptop">
        <div style="display:flex;flex-direction:column;gap:6px"><strong style="font-size:20px;color:var(--morado-osc)">Buscando en los controles y redactando…</strong>
          <span class="tenue">Suele tardar entre 15 y 40 segundos.</span></div></section>` : ""}
    ${PREG.error ? `<div class="error-caja" style="display:flex;gap:14px;align-items:center"><img class="michi" src="${MICHI.tomatoso}" alt="" width="64" height="64"><span>${esc(PREG.error)}</span></div>` : ""}
    ${r ? `<section class="tarjeta">
        <div class="fila-titulo" style="align-items:center"><h2>Respuesta</h2>${r.modelo ? `<span class="nota">Modelo ${esc(r.modelo)}</span>` : ""}</div>
        ${r.bloqueada ? `<div class="aviso-naranja">${esc(r.respuesta)}</div>` : `<p class="respuesta-texto">${conCitas(r.respuesta)}</p>`}
        ${r.fuentes && r.fuentes.length ? `<div style="border-top:2px solid var(--lavanda);padding-top:14px;display:flex;flex-direction:column;gap:10px">
          <span class="rotulo" style="font-size:13px;font-weight:900;color:var(--tenue);letter-spacing:.5px">FUENTES RECUPERADAS</span>
          <div class="fuentes">${r.fuentes.map((f) => `<a class="fuente" href="#/catalogo/${encodeURIComponent(f.control)}">
            <strong>${esc(f.control)} ${f.titulo ? `<span lang="en" style="font-weight:700">${esc(String(f.titulo).replace(f.control, "").trim())}</span>` : ""}</strong>
            ${f.puntaje != null ? `<span>similitud ${Number(f.puntaje).toFixed(2)}</span>` : ""}</a>`).join("")}</div></div>` : ""}
        <p class="nota">Generada por un modelo de lenguaje: revisa el texto oficial de cada control citado antes de usarla.</p>
      </section>` : ""}
    ${PIE}`;
  $("#form-pregunta").onsubmit = (e) => { e.preventDefault(); preguntar($("#pregunta").value); };
  $$("[data-idea]").forEach((b) => b.onclick = () => preguntar(IDEAS[b.dataset.idea]));
}

function conCitas(texto) {
  return esc(texto).replace(/\[([A-Z]{2}-\d+)\]/g, (_, id) => `<a class="cita" href="#/catalogo/${id}">${id}</a>`);
}

async function preguntar(texto) {
  texto = (texto || "").trim();
  if (texto.length < 3 || PREG.cargando) return;
  Object.assign(PREG, { texto, cargando: true, respuesta: null, error: "" });
  if (enVista("preguntar")) pintarPreguntar();
  try {
    PREG.respuesta = await postJSON("/preguntas", { pregunta: texto });
  } catch (e) {
    PREG.error = `No se pudo obtener la respuesta: ${e.message}`;
  } finally {
    PREG.cargando = false;
    if (enVista("preguntar")) pintarPreguntar();
    else if (PREG.respuesta) avisar(`Tu pregunta ya tiene respuesta. <a href="#/preguntar">Verla</a>`, MICHI.lap);
  }
}

// ---------------------------------------------------------------------------------------------------
// Vista: Sistema (métricas, configuración y evaluación)
// ---------------------------------------------------------------------------------------------------
async function vistaSistema() {
  vista.innerHTML = `<div class="fila-titulo"><div class="titulo-vista"><h1>Sistema</h1>
      <p>Cómo funciona por dentro: capas, modelos y medición.</p></div>
      <button class="boton chico secundario" id="actualizar">Actualizar</button></div>
    <div id="sis-cuerpo"><p class="tenue">Cargando métricas…</p></div>${PIE}`;
  $("#actualizar").onclick = vistaSistema;
  const [m, cfg, ev, fam, salud] = await Promise.allSettled([api("/metricas"), api("/configuracion"), api("/evaluacion"),
    api("/controles/familias"), fetch(API + "/health").then((r) => r.json())]);
  if (!enVista("sistema") || !$("#sis-cuerpo")) return;
  const M = m.value, C = cfg.value, E = ev.value && ev.value.disponible ? ev.value : null;
  const totalControles = fam.value ? fam.value.familias.reduce((s, f) => s + f.controles, 0) : null;
  const fragmentos = salud.value?.componentes?.base_vectorial?.fragmentos ?? null;
  const indicador = (num, et) => `<div class="indicador"><div class="num" style="font-size:28px">${num}</div><div class="et">${et}</div></div>`;
  const tabla = (cabeceras, filas) => `<div class="caja-tabla"><table class="tabla"><thead><tr>${cabeceras.map((c) => `<th scope="col">${c}</th>`).join("")}</tr></thead>
    <tbody>${filas.length ? filas.map((f) => `<tr>${f.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${cabeceras.length}" class="tenue">Sin datos todavía.</td></tr>`}</tbody></table></div>`;
  const rutas = C ? C.modelos.rutas : {};

  $("#sis-cuerpo").innerHTML = `<div style="display:flex;flex-direction:column;gap:22px">
    ${M ? `<div class="indicadores">
      ${indicador(M.consultas.total, "Consultas")}
      ${indicador(fmtMs(M.consultas.latencia_ms.promedio), "Latencia media")}
      ${indicador(fmtMs(M.consultas.latencia_ms.p95), "Latencia p95")}
      ${indicador(fmtPct(M.cache.tasa_aciertos), "Aciertos de caché")}
      ${indicador(M.agente.iteraciones_promedio ?? "—", "Iteraciones de agente")}
      ${indicador(M.retroalimentacion.total, "Retroalimentaciones")}</div>` : `<div class="error-caja">No se pudieron leer las métricas: ${esc(m.reason?.message)}</div>`}

    <div class="rejilla-2">
      <section class="tarjeta"><h2>Configuración</h2>${C ? `<dl class="lista-datos">
        <dt>Embeddings</dt><dd>${esc(C.embeddings)}</dd>
        ${Object.entries(rutas).map(([n, r]) => `<dt>Ruta ${esc(n)}</dt><dd>${esc(r.modelo)}</dd>`).join("")}
        <dt>Respaldo</dt><dd>${esc(C.modelos.respaldo)}</dd>
        <dt>Recuperación</dt><dd>k = ${esc(C.recuperacion.k)}, umbral ${esc(C.recuperacion.umbral)}</dd>
        <dt>Corpus</dt><dd>${totalControles ? `${totalControles} controles` : "—"}${fragmentos ? `, ${fragmentos} fragmentos` : ""}</dd>
        <dt>Proveedor</dt><dd>${esc(C.proveedor_modelos)}</dd>
        <dt>Versión del corpus</dt><dd style="word-break:break-all">${esc(C.version_corpus)}</dd></dl>` : `<p class="tenue">No disponible.</p>`}
        <a href="${API}/docs" target="_blank" rel="noopener" style="font-weight:800">Documentación de la API (/docs)</a></section>

      <section class="tarjeta"><h2>Resultados de la evaluación</h2>${E ? `<dl class="lista-datos">
        <dt>Acierto@1 / @3 / @5</dt><dd>${E.rag["acierto@1"]} / ${E.rag["acierto@3"]} / ${E.rag["acierto@5"]}</dd>
        <dt>Fidelidad con RAG (0–5)</dt><dd>${E.rag.fidelidad_con_rag}${E.fidelidad_original ? ` (antes ${E.fidelidad_original.con_rag})` : ""}</dd>
        <dt>Fidelidad sin RAG</dt><dd>${E.rag.fidelidad_sin_rag}</dd>
        <dt>Citas válidas con RAG</dt><dd>${fmtPct(E.rag.citas_validas_con_rag)}</dd>
        <dt>Guardrails</dt><dd>${fmtPct(E.guardrails.bloqueos_correctos_pct)} bloqueos, ${fmtPct(E.guardrails.falsos_positivos_pct)} falsos positivos</dd>
        <dt>Enrutador</dt><dd>${fmtPct(E.enrutador.aciertos_pct)} de aciertos</dd>
        <dt>Caché</dt><dd>${fmtMs(E.cache.latencia_fria_ms)} a ${fmtMs(E.cache.latencia_caliente_ms)}</dd>
        <dt>Latencia por consulta</dt><dd>${fmtMs(E.latencia_ms.promedio)} media, ${fmtMs(E.latencia_ms.p95)} p95</dd></dl>
        <p class="nota">De la última corrida de la evaluación (${E.rag.n_casos} casos).</p>` : `<p class="tenue">Aún no hay resultados de evaluación.</p>`}</section>
    </div>

    ${M ? `<section class="tarjeta"><h2>Latencia por capa</h2>
      ${tabla(["Capa / etapa", "n", "Promedio", "p95", "Máx."], Object.entries(M.latencia_por_capa_ms).map(([k, v]) => [esc(k), v.n, fmtMs(v.promedio), fmtMs(v.p95), fmtMs(v.max)]))}</section>
    <div class="rejilla-2">
      <section class="tarjeta"><h2>Uso por modelo</h2>
        ${tabla(["Modelo", "Llamadas", "Errores", "Lat. media"], Object.entries(M.modelos).map(([k, v]) => [esc(k), v.llamadas, v.errores, fmtMs(v.latencia_promedio_ms)]))}
        <p class="nota">Rutas: ${Object.entries(M.enrutador.por_ruta || {}).map(([k, v]) => `${esc(k)} ${v}`).join(", ") || "—"}. Usos del respaldo: ${M.enrutador.usos_respaldo}.</p></section>
      <section class="tarjeta"><h2>Guardrails</h2>
        ${tabla(["Verificación", "Evaluadas", "Activadas"], Object.entries(M.guardrails).map(([k, v]) => [esc(k.replace(/_/g, " ")), v.evaluaciones, v.activaciones]))}</section>
    </div>` : ""}
  </div>`;
}

// ---------------------------------------------------------------------------------------------------
// Vista: Créditos
// ---------------------------------------------------------------------------------------------------
function vistaCreditos() {
  const imagenes = [["logo", "img/logo.png", "Logo"], ["compu", MICHI.compu, "Michi en la computadora"], ["lap", MICHI.lap, "Michi con laptop"],
    ["libro", MICHI.libro, "Michi con libro"], ["ok", MICHI.ok, "Michi con pulgar arriba"], ["piensa", MICHI.piensa, "Michi pensativo"],
    ["festejo", MICHI.festejo, "Michi festejando"], ["tomatoso", MICHI.tomatoso, "Michi llorando"]];
  vista.innerHTML = `
    <div class="titulo-vista"><h1>Créditos</h1>
      <p>De dónde viene cada parte del sitio y cómo se usa. Proyecto académico, sin fines comerciales.</p></div>
    <section class="tarjeta"><h2 style="font-size:20px">Imágenes</h2>
      <div class="creditos-imagenes">${imagenes.map(([n, src, alt]) => `<figure><img class="${n === "logo" ? "redondo" : "michi"}" src="${src}" alt="${alt}"><figcaption>${n}</figcaption></figure>`).join("")}</div>
      <ul class="lista-texto">
        <li>El logo y las ilustraciones de gatos se obtuvieron de internet y son de autoría no identificada; no son obra de la autora del proyecto.</li>
        <li>«piensa» y «libro» provienen de publicaciones de Xiaohongshu. Se retiró su marca de agua al procesarlas, lo cual no cambia su autoría.</li>
        <li>Se usan solo con fines académicos y no comerciales. Si la persona titular de alguna imagen pide su retiro, se reemplazará.</li>
        <li>Procesamiento: recorte circular del logo y eliminación del fondo de las ilustraciones con rembg, ejecutado en local.</li>
      </ul></section>
    <div class="rejilla-2">
      <section class="tarjeta"><h2 style="font-size:20px">Base de conocimiento</h2><ul class="lista-texto">
        <li><strong>NIST SP 800-53 Rev. 5:</strong> 301 controles base, de dominio público (CC0 1.0 a nivel mundial), tomados del catálogo OSCAL oficial del NIST.</li>
        <li><strong>NIST CSF 2.0:</strong> solo se usan sus seis funciones para agrupar los hallazgos.</li>
        <li>La correspondencia entre familias y funciones se hizo para este proyecto; no es un crosswalk oficial del NIST.</li></ul></section>
      <section class="tarjeta"><h2 style="font-size:20px">Documentos de ejemplo</h2>
        <p style="margin:0;font-size:15px;line-height:1.7">Las políticas y procedimientos de demostración y de evaluación son ficticios, creados para este proyecto. No pertenecen a ninguna organización real ni contienen datos personales reales.</p></section>
      <section class="tarjeta"><h2 style="font-size:20px">Herramientas y modelos</h2><ul class="lista-texto">
        <li>Modelos en local con Ollama: bge-m3 (embeddings), qwen2.5:3b y llama3.2:3b.</li>
        <li>Base vectorial Chroma, servicio con FastAPI y registros en SQLite.</li>
        <li>rembg para quitar el fondo de las imágenes.</li>
        <li>Tipografía Nunito (SIL Open Font License), incluida en el sitio para funcionar sin internet.</li></ul></section>
      <section class="tarjeta"><h2 style="font-size:20px">Uso de asistentes de IA</h2>
        <p style="margin:0;font-size:15px;line-height:1.7">Se usó un asistente de IA para generar y documentar código y para redactar borradores. Las decisiones de arquitectura, la revisión, los experimentos y el análisis de resultados son responsabilidad de la autora.</p></section>
    </div>
    <footer class="pie"><span>Las respuestas del sistema las genera un modelo de lenguaje y pueden contener errores. Verifica cada hallazgo contra el control citado.</span></footer>`;
}

// ---------------------------------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------------------------------
// Evita que soltar un archivo fuera de la zona haga que el navegador lo abra y se pierda la página.
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());

navegar();
revisarServicio();
setInterval(revisarServicio, 15000);
