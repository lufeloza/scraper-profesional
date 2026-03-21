"""
Web Scraper API + Panel de Control
==================================

API REST + Dashboard para monitorear scraping jobs.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import os
import json
import logging
from pathlib import Path
import threading
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Web Scraper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "scraping_resultados"
RESULTS_DIR.mkdir(exist_ok=True)

class ScrapingType(str, Enum):
    NOTICIAS = "noticias"
    ECOMMERCE = "ecommerce"
    GENERICO = "generico"

class ScrapingJob(BaseModel):
    id: str
    tipo: ScrapingType
    url: str
    estado: str = "pendiente"
    progreso: int = 0
    resultados: Optional[List[Dict]] = None
    error: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

class ScrapingConfig(BaseModel):
    url: str = Field(..., description="URL para hacer scraping")
    tipo: ScrapingType = Field(..., description="Tipo de scraping")
    max_items: int = Field(10, ge=1, le=100, description="Máximo de items a extraer")
    export_format: Optional[str] = Field(None, description="Formato de exportación: json, csv, excel")

class JobStatus(BaseModel):
    id: str
    tipo: str
    url: str
    estado: str
    progreso: int
    resultados_count: int
    error: Optional[str]
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]

jobs: Dict[str, ScrapingJob] = {}
job_lock = threading.Lock()

def generate_job_id() -> str:
    return f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

@app.get("/")
async def root():
    return FileResponse(str(BASE_DIR / "frontend" / "index.html"))

@app.get("/api/salud")
async def salud():
    return {"estado": "OK", "version": "1.0.0", "jobs_activos": len([j for j in jobs.values() if j.estado == "ejecutando"])}

@app.post("/api/scraping/ejecutar", response_model=JobStatus)
async def ejecutar_scraping(config: ScrapingConfig, background_tasks: BackgroundTasks):
    job_id = generate_job_id()
    
    job = ScrapingJob(
        id=job_id,
        tipo=config.tipo,
        url=config.url,
        estado="pendiente",
        fecha_inicio=datetime.utcnow()
    )
    
    with job_lock:
        jobs[job_id] = job
    
    background_tasks.add_task(ejecutar_scraping_task, job_id, config)
    
    return JobStatus(
        id=job.id,
        tipo=job.tipo.value,
        url=job.url,
        estado=job.estado,
        progreso=job.progreso,
        resultados_count=len(job.resultados) if job.resultados else 0,
        error=job.error,
        fecha_inicio=job.fecha_inicio.isoformat() if job.fecha_inicio else None,
        fecha_fin=job.fecha_fin.isoformat() if job.fecha_fin else None
    )

def ejecutar_scraping_task(job_id: str, config: ScrapingConfig):
    import sys
    import importlib.util
    
    scraper_path = BASE_DIR.parent / "scraper.py"
    if scraper_path.exists():
        spec = importlib.util.spec_from_file_location("scraper", str(scraper_path))
        scraper_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scraper_module)
        
        ScraperNoticias = scraper_module.ScraperNoticias
        ScraperEcommerce = scraper_module.ScraperEcommerce
        ScraperGenerico = scraper_module.ScraperGenerico
        ExportadorDatos = scraper_module.ExportadorDatos
    else:
        logger.error("No se encontró scraper.py")
        with job_lock:
            jobs[job_id].estado = "error"
            jobs[job_id].error = "Módulo scraper no encontrado"
            jobs[job_id].fecha_fin = datetime.utcnow()
        return
    from dataclasses import asdict
    
    with job_lock:
        job = jobs[job_id]
        job.estado = "ejecutando"
        job.progreso = 10
    
    try:
        if config.tipo == ScrapingType.NOTICIAS:
            scraper = ScraperNoticias()
            job.progreso = 30
            resultados = scraper.extraer_noticias(config.url, max_noticias=config.max_items)
            job.progreso = 70
            
        elif config.tipo == ScrapingType.ECOMMERCE:
            scraper = ScraperEcommerce()
            job.progreso = 30
            producto = scraper.extraer_producto(config.url)
            resultados = [asdict(producto)] if producto else []
            job.progreso = 70
            
        else:
            scraper = ScraperGenerico()
            job.progreso = 30
            resultados = [scraper.extraer_datos(config.url, config.dict() if hasattr(config, 'dict') else {})]
            job.progreso = 70
        
        with job_lock:
            job.resultados = resultados
            job.progreso = 90
        
        if config.export_format and resultados:
            try:
                if config.export_format == "json":
                    ExportadorDatos.a_json(resultados, f"scraping_{job_id}")
                elif config.export_format == "csv":
                    ExportadorDatos.a_csv(resultados, f"scraping_{job_id}")
                elif config.export_format == "excel":
                    ExportadorDatos.a_excel(resultados, f"scraping_{job_id}")
            except Exception as e:
                logger.error(f"Error exportando: {e}")
        
        with job_lock:
            job.estado = "completado"
            job.progreso = 100
            job.fecha_fin = datetime.utcnow()
            
    except Exception as e:
        with job_lock:
            job.estado = "error"
            job.error = str(e)
            job.fecha_fin = datetime.utcnow()
        logger.error(f"Error en job {job_id}: {e}")

@app.get("/api/scraping/trabajos")
async def listar_trabajos():
    return [
        JobStatus(
            id=j.id,
            tipo=j.tipo.value,
            url=j.url,
            estado=j.estado,
            progreso=j.progreso,
            resultados_count=len(j.resultados) if j.resultados else 0,
            error=j.error,
            fecha_inicio=j.fecha_inicio.isoformat() if j.fecha_inicio else None,
            fecha_fin=j.fecha_fin.isoformat() if j.fecha_fin else None
        )
        for j in sorted(jobs.values(), key=lambda x: x.fecha_inicio or datetime.min, reverse=True)[:20]
    ]

@app.get("/api/scraping/trabajos/{job_id}")
async def detalle_trabajo(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    
    return {
        "id": job.id,
        "tipo": job.tipo.value,
        "url": job.url,
        "estado": job.estado,
        "progreso": job.progreso,
        "resultados": job.resultados,
        "resultados_count": len(job.resultados) if job.resultados else 0,
        "error": job.error,
        "fecha_inicio": job.fecha_inicio.isoformat() if job.fecha_inicio else None,
        "fecha_fin": job.fecha_fin.isoformat() if job.fecha_fin else None
    }

@app.delete("/api/scraping/trabajos/{job_id}")
async def eliminar_trabajo(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Trabajo no encontrado")
    del jobs[job_id]
    return {"mensaje": "Trabajo eliminado"}

@app.get("/api/scraping/resultados")
async def listar_resultados():
    archivos = []
    for f in RESULTS_DIR.glob("*"):
        archivos.append({
            "nombre": f.name,
            "tipo": f.suffix[1:] if f.suffix else "unknown",
            "tamano": f.stat().st_size,
            "fecha": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    return sorted(archivos, key=lambda x: x["fecha"], reverse=True)

@app.get("/api/estadisticas")
async def estadisticas():
    total_jobs = len(jobs)
    jobs_completados = len([j for j in jobs.values() if j.estado == "completado"])
    jobs_activos = len([j for j in jobs.values() if j.estado == "ejecutando"])
    jobs_errores = len([j for j in jobs.values() if j.estado == "error"])
    
    total_resultados = sum(len(j.resultados) if j.resultados else 0 for j in jobs.values())
    
    return {
        "total_jobs": total_jobs,
        "jobs_completados": jobs_completados,
        "jobs_activos": jobs_activos,
        "jobs_errores": jobs_errores,
        "total_resultados": total_resultados
    }

@app.get("/api/scraping/grafico-trabajos")
async def grafico_trabajos():
    from datetime import timedelta
    
    datos = []
    for i in range(7):
        fecha = datetime.utcnow() - timedelta(days=i)
        fecha_str = fecha.strftime("%d/%m")
        
        count = len([
            j for j in jobs.values() 
            if j.fecha_inicio and j.fecha_inicio.date() == fecha.date()
        ])
        
        datos.append({
            "fecha": fecha_str,
            "trabajos": count
        })
    
    return list(reversed(datos))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
