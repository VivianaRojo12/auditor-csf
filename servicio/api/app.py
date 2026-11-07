"""C1. Interfaz del servicio (API REST).

Recibe las peticiones HTTP, valida entrada y salida con esquemas y traduce cada petición en una llamada a
la orquestación. No contiene lógica de IA. Documentación OpenAPI automática en /docs.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from servicio.api.esquemas import Pregunta, Retroalimentacion
from servicio.contexto import prompts
from servicio.contexto.documentos import leer_documento
from servicio.contenedor import Contenedor
from servicio.dominio import ErrorModelo
from servicio.observabilidad.trazas import observador
from servicio.orquestacion.informe import ensamblar
from servicio.retroalimentacion.registro import TrazaInexistente

EXTENSIONES = {"pdf", "docx", "md", "markdown", "txt"}


def crear_app(contenedor: Contenedor | None = None) -> FastAPI:
    c = contenedor or Contenedor()
    app = FastAPI(title="Auditor de políticas contra NIST CSF 2.0",
                  description="Servicio en capas con embeddings y RAG que audita políticas de seguridad "
                              "contra los controles del NIST SP 800-53 Rev. 5, agrupados por las funciones "
                              "del CSF 2.0.",
                  version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=c.conf.servicio.origenes_web or ["*"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.get("/health", tags=["estado"])
    def health():
        estado_modelos = c.servidor.estado()
        base = c.base.estado()
        componentes = {
            "servidor_modelos": estado_modelos,
            "base_vectorial": base,
            "cache": {"entradas": c.cache_almacen.contar()},
            "corpus_indexado": base.get("fragmentos", 0) > 0,
        }
        ok = estado_modelos.get("disponible") and base.get("fragmentos", 0) > 0
        return JSONResponse(status_code=200 if ok else 503,
                            content={"estado": "ok" if ok else "incompleto", "componentes": componentes})

    @app.get("/configuracion", tags=["estado"])
    def configuracion():
        return {
            "proveedor_modelos": c.conf.proveedor_modelos,
            "modelos": c.conf.modelos.model_dump(),
            "embeddings": c.conf.embeddings.modelo,
            "fragmentacion": c.conf.fragmentacion,
            "recuperacion": c.conf.recuperacion,
            "agente": c.conf.agente,
            "cache": c.conf.cache,
            "enrutador": c.conf.enrutador,
            "version_corpus": c.version_corpus(),
            "huella_config": c.conf.huella(),
        }

    @app.post("/documentos", tags=["corpus"])
    async def cargar_documento(archivo: UploadFile = File(...)):
        """Agrega un documento de referencia (control o norma) a la base de conocimiento: lo fragmenta,
        genera embeddings e indexa."""
        ext = Path(archivo.filename or "").suffix.lower().lstrip(".")
        if ext not in EXTENSIONES:
            raise HTTPException(400, f"Formato no admitido: .{ext}")
        contenido = await archivo.read()
        sha = hashlib.sha256(contenido).hexdigest()
        existente = c.docs.buscar_por_hash(sha)
        if existente:
            return {"id": existente["id"], "nombre": existente["nombre"], "fragmentos": existente["fragmentos"],
                    "nota": "documento idéntico ya indexado"}
        doc_id = f"doc-{sha[:10]}"
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(contenido)
            ruta = Path(tmp.name)
        from servicio.contexto.documentos import fragmentar_texto
        from servicio.dominio import Fragmento
        doc = leer_documento(ruta, nombre=archivo.filename)
        fragmentos = []
        for i, bloque in enumerate(fragmentar_texto(doc.texto_completo, c.conf.fragmentacion["tamano"],
                                                    c.conf.fragmentacion["solapamiento"])):
            fragmentos.append(Fragmento(id=f"{doc_id}::{i}", texto=bloque,
                                        metadatos={"doc_id": doc_id, "documento": archivo.filename, "parte": i,
                                                   "control": "", "funcion": "", "titulo": archivo.filename}))
        c.contexto.indexar(fragmentos)
        c.docs.guardar_documento(doc_id, archivo.filename or doc_id, ext, sha, len(fragmentos), contenido)
        ruta.unlink(missing_ok=True)
        return {"id": doc_id, "nombre": archivo.filename, "fragmentos": len(fragmentos)}

    @app.get("/documentos", tags=["corpus"])
    def listar_documentos():
        return {"documentos": c.docs.listar_documentos(), "fragmentos_indexados": c.base.contar()}

    @app.delete("/documentos/{doc_id}", tags=["corpus"])
    def eliminar_documento(doc_id: str):
        eliminados = c.base.eliminar_documento(doc_id)
        existe = c.docs.eliminar_documento(doc_id)
        if not existe and eliminados == 0:
            raise HTTPException(404, "Documento no encontrado")
        invalidadas = c.cache.invalidar_documento(doc_id)
        c.cache.invalidar_por_version(c.version_corpus())
        return {"eliminado": doc_id, "fragmentos_eliminados": eliminados, "cache_invalidada": invalidadas}

    @app.post("/auditorias", tags=["auditoría"])
    async def auditar(archivo: UploadFile = File(...)):
        """Función principal: audita un documento de política contra los controles indexados y devuelve un
        informe de brechas por función del CSF 2.0 (no es una conversación)."""
        ext = Path(archivo.filename or "").suffix.lower().lstrip(".")
        if ext not in EXTENSIONES:
            raise HTTPException(400, f"Formato no admitido: .{ext}")
        if c.base.contar() == 0:
            raise HTTPException(503, "El corpus de controles no está indexado. Ejecuta la ingesta primero.")
        contenido = await archivo.read()
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(contenido)
            ruta = Path(tmp.name)
        traza = observador.nueva_traza()
        inicio = time.perf_counter()
        doc = leer_documento(ruta, nombre=archivo.filename)
        ruta.unlink(missing_ok=True)
        version = c.version_corpus()
        resultados = [c.orquestador.analizar_seccion(s, version) for s in doc.secciones]
        informe = ensamblar(doc.nombre, resultados, traza)
        informe["tiempo_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
        informe["traza_id"] = traza
        return informe

    @app.post("/preguntas", tags=["auditoría"])
    def preguntar(p: Pregunta = Body(...)):
        """Función secundaria: responde una pregunta sobre los controles, citando fuentes del corpus."""
        traza = observador.nueva_traza()
        from servicio.guardrails import verificaciones
        entrada = verificaciones.verificar_entrada(p.pregunta, c.conf.guardrails)
        if not entrada.aprobada:
            return {"respuesta": entrada.mensaje_seguro, "fuentes": [], "traza_id": traza, "bloqueada": True}
        rec = c.contexto.recuperar(p.pregunta)
        fuentes_texto, refs = c.contexto.armar_fuentes(rec.fragmentos)
        if not refs:
            return {"respuesta": "No encontré controles relevantes para esa pregunta en el corpus.",
                    "fuentes": [], "traza_id": traza}
        try:
            r = c.gateway.generar(
                [{"role": "system", "content": "Responde solo con la información de las fuentes y cita sus "
                  "etiquetas (F1, F2). Si no está en las fuentes, dilo. Responde en español."},
                 {"role": "user", "content": f"Pregunta: {p.pregunta}\n\nFuentes:\n{fuentes_texto}"}],
                ruta="simple", usar_respaldo=True, max_tokens=500)
        except ErrorModelo as e:
            raise HTTPException(503, f"Modelo no disponible: {e}")
        return {"respuesta": r.texto, "fuentes": refs, "modelo": r.modelo, "traza_id": traza}

    @app.post("/retroalimentacion", tags=["observabilidad"])
    def retroalimentar(r: Retroalimentacion):
        try:
            ident = c.retro.registrar(r.traza_id, r.util, r.comentario, r.origen)
        except TrazaInexistente:
            raise HTTPException(404, "La traza indicada no existe")
        return {"registrada": True, "id": ident}

    @app.get("/metricas", tags=["observabilidad"])
    def metricas():
        resumen = c.eventos.resumen_metricas()
        resumen["retroalimentacion"] = c.retro.resumen()
        return resumen

    @app.get("/trazas/{traza_id}", tags=["observabilidad"])
    def traza(traza_id: str):
        eventos = c.eventos.eventos_de_traza(traza_id)
        if not eventos:
            raise HTTPException(404, "Traza no encontrada")
        return {"traza_id": traza_id, "eventos": eventos}

    return app
