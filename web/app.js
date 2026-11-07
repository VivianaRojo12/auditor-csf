"use strict";
// Capa de presentación. Consume ÚNICAMENTE la API por HTTP (R8): nunca llama a modelos ni a la base vectorial.
const API = (window.SENTINELA_API || location.origin.replace(/:\d+$/, ":8000"));

const $ = (s) => document.querySelector(s);
const el = (t, cls, html) => { const e = document.createElement(t); if (cls) e.className = cls;
  if (html != null) e.innerHTML = html; return e; };
const esc = (s) => (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

async function api(ruta, opciones) {
  const r = await fetch(API + ruta, opciones);
  if (!r.ok) { let d; try { d = await r.json(); } catch { d = {}; } throw new Error(d.detail || r.status); }
  return r.json();
}

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
async function estado() {
  const e = $("#estado-servicio");
  try {
    const h = await api("/health");
    const ok = h.estado === "ok";
    e.textContent = ok ? "Servicio en línea" : "Servicio incompleto";
    e.className = "estado " + (ok ? "ok" : "mal");
    $("#enlace-docs").href = API + "/docs";
  } catch { e.textContent = "Sin conexión al servicio"; e.className = "estado mal"; }
}

// --- Auditoría ---
$("#archivo").addEventListener("change", () => { $("#btn-auditar").disabled = !$("#archivo").files.length; });
$("#btn-auditar").addEventListener("click", () => auditar($("#archivo").files[0]));
$("#btn-ejemplo").addEventListener("click", async () => {
  const r = await fetch("politica_ejemplo.md"); const t = await r.text();
  auditar(new File([t], "politica_ejemplo.md", { type: "text/markdown" }));
});

async function auditar(archivo) {
  if (!archivo) return;
  $("#informe").classList.add("oculto");
  $("#progreso").classList.remove("oculto");
  $("#progreso-txt").textContent = `Analizando ${archivo.name}… (puede tardar según el equipo)`;
  const fd = new FormData(); fd.append("archivo", archivo);
  try {
    const inf = await api("/auditorias", { method: "POST", body: fd });
    pintarInforme(inf);
  } catch (e) { $("#informe").innerHTML = `<div class="bloqueada">Error: ${esc(e.message)}</div>`;
    $("#informe").classList.remove("oculto"); }
  finally { $("#progreso").classList.add("oculto"); }
}

function pintarInforme(inf) {
  const cont = $("#informe"); cont.innerHTML = "";
  const R = inf.resumen;
  cont.appendChild(el("h2", null, `Informe de auditoría — ${esc(inf.documento)}`));
  cont.appendChild(el("p", "meta-linea",
    `Traza ${inf.traza_id} · ${inf.tiempo_ms} ms · ${R.secciones_analizadas} secciones analizadas`));

  const cajas = el("div", "resumen-cajas");
  const dato = (n, et, alerta) => { const c = el("div", "caja" + (alerta ? " alerta" : ""));
    c.appendChild(el("div", "num", n)); c.appendChild(el("div", "et", et)); return c; };
  cajas.appendChild(dato(R.hallazgos_totales, "Hallazgos"));
  cajas.appendChild(dato(R.brechas, "Brechas"));
  cajas.appendChild(dato(R.brechas_graves, "Brechas graves", R.brechas_graves > 0));
  cajas.appendChild(dato(R.controles_citados.length, "Controles citados"));
  cont.appendChild(cajas);

  // Cobertura por función CSF
  if (inf.por_funcion.length) {
    cont.appendChild(el("h3", null, "Cobertura por función del CSF 2.0"));
    const g = el("div", "funciones");
    inf.por_funcion.forEach((f) => {
      const d = el("div", "func");
      d.appendChild(el("div", "func-cab",
        `<span><strong>${f.funcion}</strong> · ${esc(f.nombre)}</span><span>${Math.round(f.cobertura * 100)}%</span>`));
      const m = el("div", "medidor"); const barra = el("div");
      barra.style.width = (f.cobertura * 100) + "%";
      barra.style.background = f.cobertura >= .7 ? "var(--ok)" : f.cobertura >= .4 ? "var(--media)" : "var(--alta)";
      m.appendChild(barra); d.appendChild(m);
      d.appendChild(el("small", null,
        `${f.cubierto} cubiertos · ${f.parcial} parciales · ${f.ausente} ausentes`));
      g.appendChild(d);
    });
    cont.appendChild(g);
  }

  // Prioridades
  if (inf.prioridades.length) {
    cont.appendChild(el("h3", null, "Prioridades de atención"));
    inf.prioridades.forEach((h) => cont.appendChild(tarjetaHallazgo(h)));
  }

  // Detalle por sección
  cont.appendChild(el("h3", "seccion-bloque", "Detalle por sección"));
  inf.secciones.forEach((s) => {
    cont.appendChild(el("div", "seccion-bloque",
      `#${s.seccion} · ${esc(s.titulo)} <small style="color:var(--tenue);font-size:.75rem">
       [${esc(s.ruta || "-")}${s.cache !== "ninguna" ? " · caché " + s.cache : ""}${s.iteraciones_agente > 1 ? " · agente ×" + s.iteraciones_agente : ""}]</small>`));
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
  const d = el("div", "hallazgo " + (h.gravedad || "media"));
  d.appendChild(el("div", "cab",
    `<strong>${esc(h.control_id)}</strong>
     <span class="etiqueta estado-${esc(h.estado)}">${esc(h.estado)}</span>
     <span class="etiqueta">gravedad ${esc(h.gravedad)}</span>
     <span class="etiqueta">función ${esc(h.funcion || "-")}</span>`));
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
    cont.appendChild(el("p", "meta-linea", "Rutas: " + JSON.stringify(m.enrutador.por_ruta) +
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

estado();
setInterval(estado, 15000);
