# Web Scraper Profesional

Sistema modular de extracción de datos de páginas web.

## 🎯 Para qué sirve

- Extraer datos de cualquier sitio web
- Monitoreo de precios de competidores
- Generación de bases de datos de leads
- Extracción de noticias y contenidos

## ✨ Características

| Tipo | Descripción |
|------|-------------|
| **Scraper de Noticias** | Extrae artículos de medios digitales |
| **Scraper E-commerce** | Monitorea precios y disponibilidad |
| **Scraper Genérico** | Configurable con selectores CSS personalizados |
| **Exportación** | JSON, CSV y Excel |
| **Rate Limiting** | Respetuoso con servidores |

## 🛠️ Stack

- Python 3.9+
- BeautifulSoup4
- Requests
- openpyxl (Excel)

## 🚀 Cómo ejecutarlo

```bash
cd scraper-profesional
pip install -r requirements.txt
python scraper.py
```

Los resultados se guardan en `scraping_resultados/`

## 📦 Uso en tu proyecto

```python
from scraper import ScraperNoticias, ExportadorDatos

# Extraer noticias
scraper = ScraperNoticias()
noticias = scraper.extraer_noticias("https://elpais.com/tecnologia/", max_noticias=10)

# Exportar a Excel
ExportadorDatos.a_excel(noticias, "mis_noticias")
```

```python
from scraper import ScraperEcommerce

# Extraer producto
scraper = ScraperEcommerce()
producto = scraper.extraer_producto("https://amazon.com/dp/...")
print(f"Precio: {producto.precio}")
```

## 📁 Estructura
```
scraper-profesional/
├── scraper.py           # Código principal
├── scraping_resultados/ # Resultados
├── requirements.txt
└── README.md
```

---

**リストラブル y fácil de extender.** Puedo adaptarlo a tus necesidades específicas.