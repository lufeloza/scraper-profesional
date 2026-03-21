"""
Tests para la API del Web Scraper
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

class TestSalud:
    def test_salud(self):
        r = client.get("/api/salud")
        assert r.status_code == 200
        data = r.json()
        assert data["estado"] == "OK"
        assert "version" in data

class TestEstadisticas:
    def test_estadisticas(self):
        r = client.get("/api/estadisticas")
        assert r.status_code == 200
        data = r.json()
        assert "total_jobs" in data
        assert "jobs_completados" in data
        assert "jobs_activos" in data
        assert "jobs_errores" in data
        assert "total_resultados" in data

class TestGrafico:
    def test_grafico_trabajos(self):
        r = client.get("/api/scraping/grafico-trabajos")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 7

class TestScraping:
    def test_ejecutar_scraping_noticias(self):
        r = client.post(
            "/api/scraping/ejecutar",
            json={
                "url": "https://elpais.com/tecnologia/",
                "tipo": "noticias",
                "max_items": 5,
                "export_format": None
            }
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tipo"] == "noticias"
        assert data["estado"] == "pendiente"
        assert "id" in data
        assert "progreso" in data

    def test_ejecutar_scraping_ecommerce(self):
        r = client.post(
            "/api/scraping/ejecutar",
            json={
                "url": "https://www.amazon.com",
                "tipo": "ecommerce",
                "max_items": 1,
                "export_format": None
            }
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tipo"] == "ecommerce"

    def test_ejecutar_scraping_sin_url(self):
        r = client.post(
            "/api/scraping/ejecutar",
            json={
                "url": "",
                "tipo": "noticias",
                "max_items": 5
            }
        )
        assert r.status_code == 200
        assert r.json()["estado"] == "pendiente"

    def test_listar_trabajos(self):
        r = client.get("/api/scraping/trabajos")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

class TestTrabajosDetalle:
    def test_trabajo_no_existe(self):
        r = client.get("/api/scraping/trabajos/job_inexistente")
        assert r.status_code == 404

    def test_eliminar_trabajo_no_existe(self):
        r = client.delete("/api/scraping/trabajos/job_inexistente")
        assert r.status_code == 404

class TestResultados:
    def test_listar_resultados(self):
        r = client.get("/api/scraping/resultados")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
