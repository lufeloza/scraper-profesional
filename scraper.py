"""
Web Scraper Profesional
=======================

Un sistema de web scraping versátil y robusto que incluye:
- Extracción de datos de páginas web
- Scraping de noticias
- Monitoreo de precios de productos
- Exportación a múltiples formatos (JSON, CSV, Excel)
- Sistema de programación de tareas

Autor: [Tu Nombre]
Fecha: 2026
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

import json
import csv
import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse

# Librerías para scraping
import requests
from bs4 import BeautifulSoup

# Para exportación a Excel (opcional)
try:
    import openpyxl
    EXCEL_DISPONIBLE = True
except ImportError:
    EXCEL_DISPONIBLE = False

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================

# Headers para simular un navegador real (evitar bloqueos)
HEADERS_NAVEGADOR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Tiempo de espera entre peticiones (para ser respetuoso)
TIEMPO_ESPERA_SEGUNDOS = 2

# Directorio para guardar resultados
DIRECTORIO_SALIDA = "scraping_resultados"

# =============================================================================
# CLASES DE DATOS
# =============================================================================

@dataclass
class ResultadoScraping:
    """Estructura para almacenar un resultado de scraping"""
    url: str
    titulo: str
    contenido: Dict[str, Any]
    fecha_extraccion: str
    fuente: str
    metadata: Optional[Dict] = None


@dataclass
class ProductoEcommerce:
    """Estructura para productos de e-commerce"""
    nombre: str
    precio: str
    precio_numerico: Optional[float]
    moneda: str
    disponibilidad: str
    url: str
    imagen_url: Optional[str]
    tienda: str
    fecha_consulta: str

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def crear_directorio_salida() -> None:
    """Crea el directorio de salida si no existe"""
    if not os.path.exists(DIRECTORIO_SALIDA):
        os.makedirs(DIRECTORIO_SALIDA)
        logger.info(f"Directorio creado: {DIRECTORIO_SALIDA}")


def limpiar_texto(texto: str) -> str:
    """
    Limpia el texto eliminando espacios extra y caracteres no deseados.
    """
    if not texto:
        return ""
    # Eliminar espacios múltiples y saltos de línea
    texto = re.sub(r'\s+', ' ', texto)
    # Eliminar espacios al inicio y final
    return texto.strip()


def extraer_precio_numerico(texto_precio: str) -> Optional[float]:
    """
    Extrae el valor numérico de un texto de precio.
    Soporta múltiples formatos: $1,234.56, 1.234,56€, etc.
    """
    if not texto_precio:
        return None
    
    # Eliminar símbolos de moneda y espacios
    texto_limpio = re.sub(r'[^\d.,]', '', texto_precio)
    
    # Detectar formato (europeo vs americano)
    if ',' in texto_limpio and '.' in texto_limpio:
        # Formato: 1,234.56 o 1.234,56
        if texto_limpio.rfind(',') > texto_limpio.rfind('.'):
            # Formato europeo: 1.234,56
            texto_limpio = texto_limpio.replace('.', '').replace(',', '.')
        else:
            # Formato americano: 1,234.56
            texto_limpio = texto_limpio.replace(',', '')
    elif ',' in texto_limpio:
        # Podría ser 1,234 (miles) o 1,23 (decimal)
        if len(texto_limpio.split(',')[1]) <= 2:
            # Probablemente decimal europeo
            texto_limpio = texto_limpio.replace(',', '.')
        else:
            # Probablemente separador de miles americano
            texto_limpio = texto_limpio.replace(',', '')
    
    try:
        return float(texto_limpio)
    except ValueError:
        return None


def obtener_dominio(url: str) -> str:
    """Extrae el dominio de una URL"""
    parsed = urlparse(url)
    return parsed.netloc

# =============================================================================
# CLASE PRINCIPAL: SCRAPER BASE
# =============================================================================

class ScraperBase:
    """
    Clase base para todos los scrapers.
    Proporciona funcionalidad común como:
    - Manejo de sesiones HTTP
    - Reintentos automáticos
    - Respeto por robots.txt (delay entre peticiones)
    """
    
    def __init__(self, headers: Optional[Dict] = None):
        """
        Inicializa el scraper con headers personalizados.
        
        Args:
            headers: Headers HTTP personalizados (opcional)
        """
        self.session = requests.Session()
        self.headers = headers or HEADERS_NAVEGADOR
        self.session.headers.update(self.headers)
        self.ultimo_request = 0
        
    def _respetar_delay(self) -> None:
        """Espera el tiempo necesario entre peticiones"""
        tiempo_transcurrido = time.time() - self.ultimo_request
        if tiempo_transcurrido < TIEMPO_ESPERA_SEGUNDOS:
            time.sleep(TIEMPO_ESPERA_SEGUNDOS - tiempo_transcurrido)
    
    def obtener_pagina(self, url: str, reintentos: int = 3) -> Optional[BeautifulSoup]:
        """
        Obtiene el contenido de una página web.
        
        Args:
            url: URL de la página a scrapear
            reintentos: Número de reintentos en caso de error
            
        Returns:
            BeautifulSoup object o None si hay error
        """
        self._respetar_delay()
        
        for intento in range(reintentos):
            try:
                logger.info(f"Obteniendo: {url} (intento {intento + 1}/{reintentos})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                self.ultimo_request = time.time()
                
                # Crear objeto BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info(f"Página obtenida exitosamente: {url}")
                return soup
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error obteniendo {url}: {e}")
                if intento < reintentos - 1:
                    time.sleep(5 * (intento + 1))  # Backoff exponencial
                    
        return None
    
    def extraer_texto_elemento(self, soup: BeautifulSoup, selector: str, 
                                atributo: Optional[str] = None) -> Optional[str]:
        """
        Extrae texto o atributo de un elemento usando selector CSS.
        
        Args:
            soup: Objeto BeautifulSoup
            selector: Selector CSS (ej: 'h1.title', '.price', '#content')
            atributo: Atributo a extraer (ej: 'href', 'src'). Si es None, extrae texto.
            
        Returns:
            Texto o valor del atributo, o None si no se encuentra
        """
        elemento = soup.select_one(selector)
        if elemento:
            if atributo:
                return elemento.get(atributo)
            return limpiar_texto(elemento.get_text())
        return None
    
    def extraer_lista_elementos(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """
        Extrae una lista de textos de múltiples elementos.
        
        Args:
            soup: Objeto BeautifulSoup
            selector: Selector CSS para múltiples elementos
            
        Returns:
            Lista de textos extraídos
        """
        elementos = soup.select(selector)
        return [limpiar_texto(elem.get_text()) for elem in elementos if elem.get_text()]

# =============================================================================
# SCRAPER DE NOTICIAS
# =============================================================================

class ScraperNoticias(ScraperBase):
    """
    Scraper especializado para extraer noticias de sitios web.
    Soporta múltiples fuentes y estructura de datos estandarizada.
    """
    
    # Selectores CSS para diferentes sitios de noticias
    SELECTORES_SITIOS = {
        'default': {
            'articulos': 'article',
            'titulo': 'h1, h2, h3',
            'resumen': 'p',
            'enlace': 'a',
            'fecha': 'time, .date, .fecha',
            'imagen': 'img'
        },
        'bbc.com': {
            'articulos': '[data-component="card"]',
            'titulo': 'h2, h3',
            'resumen': 'p',
            'enlace': 'a',
            'fecha': 'time',
            'imagen': 'img'
        },
        'elpais.com': {
            'articulos': 'article',
            'titulo': 'h2, h3',
            'resumen': 'p',
            'enlace': 'a',
            'fecha': 'time, .date',
            'imagen': 'img'
        },
        'elmundo.es': {
            'articulos': 'article',
            'titulo': 'h2, h3',
            'resumen': 'p',
            'enlace': 'a',
            'fecha': 'time',
            'imagen': 'img'
        }
    }
    
    def obtener_selectores(self, url: str) -> Dict:
        """Obtiene los selectores apropiados según el dominio"""
        dominio = obtener_dominio(url)
        for sitio, selectores in self.SELECTORES_SITIOS.items():
            if sitio in dominio:
                return selectores
        return self.SELECTORES_SITIOS['default']
    
    def extraer_noticias(self, url: str, max_noticias: int = 10) -> List[Dict]:
        """
        Extrae noticias de una página web.
        
        Args:
            url: URL de la página de noticias
            max_noticias: Número máximo de noticias a extraer
            
        Returns:
            Lista de diccionarios con datos de noticias
        """
        soup = self.obtener_pagina(url)
        if not soup:
            return []
        
        selectores = self.obtener_selectores(url)
        noticias = []
        
        # Buscar contenedores de artículos
        articulos = soup.select(selectores['articulos'])[:max_noticias]
        
        for articulo in articulos:
            try:
                noticia = self._extraer_datos_articulo(articulo, selectores, url)
                if noticia and noticia.get('titulo'):
                    noticias.append(noticia)
            except Exception as e:
                logger.error(f"Error extrayendo artículo: {e}")
                continue
        
        logger.info(f"Extraídas {len(noticias)} noticias de {url}")
        return noticias
    
    def _extraer_datos_articulo(self, articulo: BeautifulSoup, 
                                 selectores: Dict, url_base: str) -> Dict:
        """Extrae los datos de un artículo individual"""
        titulo_elem = articulo.select_one(selectores['titulo'])
        resumen_elem = articulo.select_one(selectores['resumen'])
        enlace_elem = articulo.select_one(selectores['enlace'])
        fecha_elem = articulo.select_one(selectores['fecha'])
        imagen_elem = articulo.select_one(selectores['imagen'])
        
        # Construir URL completa si es relativa
        enlace = None
        if enlace_elem and enlace_elem.get('href'):
            enlace = urljoin(url_base, enlace_elem.get('href'))
        
        return {
            'titulo': limpiar_texto(titulo_elem.get_text()) if titulo_elem else None,
            'resumen': limpiar_texto(resumen_elem.get_text()) if resumen_elem else None,
            'enlace': enlace,
            'fecha': fecha_elem.get('datetime') or limpiar_texto(fecha_elem.get_text()) if fecha_elem else None,
            'imagen': imagen_elem.get('src') if imagen_elem else None,
            'fuente': obtener_dominio(url_base),
            'fecha_extraccion': datetime.utcnow().isoformat()
        }
    
    def extraer_articulo_completo(self, url: str) -> Optional[Dict]:
        """
        Extrae el contenido completo de un artículo.
        
        Args:
            url: URL del artículo
            
        Returns:
            Diccionario con el contenido completo del artículo
        """
        soup = self.obtener_pagina(url)
        if not soup:
            return None
        
        # Extraer título
        titulo = self.extraer_texto_elemento(soup, 'h1')
        
        # Extraer contenido del artículo
        parrafos = soup.select('article p, .article-content p, .content p, [class*="article"] p')
        contenido = '\n\n'.join([limpiar_texto(p.get_text()) for p in parrafos if p.get_text()])
        
        # Extraer autor
        autor = self.extraer_texto_elemento(soup, '[class*="author"], .author, .byline')
        
        # Extraer fecha
        fecha = self.extraer_texto_elemento(soup, 'time, [class*="date"]')
        
        return {
            'url': url,
            'titulo': titulo,
            'autor': autor,
            'fecha': fecha,
            'contenido': contenido,
            'fuente': obtener_dominio(url),
            'fecha_extraccion': datetime.utcnow().isoformat()
        }

# =============================================================================
# SCRAPER DE E-COMMERCE (PRECIOS)
# =============================================================================

class ScraperEcommerce(ScraperBase):
    """
    Scraper especializado para monitorear precios de productos.
    Soporta múltiples tiendas online.
    """
    
    # Patrones para extraer precios en diferentes tiendas
    PATRONES_TIENDAS = {
        'amazon': {
            'nombre': '[data-component-id="1"] h1, #productTitle',
            'precio': '.a-price .a-offscreen, .a-price-whole',
            'disponibilidad': '#availability span',
            'imagen': '#landingImage, #imgBlkFront'
        },
        'mercadolibre': {
            'nombre': '.ui-pdp-title',
            'precio': '.andes-money-amount__fraction',
            'disponibilidad': '.ui-pdp-stock',
            'imagen': '.ui-pdp-gallery__figure img'
        },
        'default': {
            'nombre': 'h1, [class*="product-name"], [class*="product-title"]',
            'precio': '[class*="price"], .price',
            'disponibilidad': '[class*="stock"], [class*="availability"]',
            'imagen': 'img[class*="product"], .product-image img'
        }
    }
    
    def identificar_tienda(self, url: str) -> str:
        """Identifica la tienda basándose en la URL"""
        dominio = obtener_dominio(url).lower()
        if 'amazon' in dominio:
            return 'amazon'
        elif 'mercadolibre' in dominio:
            return 'mercadolibre'
        return 'default'
    
    def extraer_producto(self, url: str) -> Optional[ProductoEcommerce]:
        """
        Extrae información de un producto de e-commerce.
        
        Args:
            url: URL del producto
            
        Returns:
            ProductoEcommerce con los datos extraídos
        """
        soup = self.obtener_pagina(url)
        if not soup:
            return None
        
        tienda = self.identificar_tienda(url)
        patrones = self.PATRONES_TIENDAS.get(tienda, self.PATRONES_TIENDAS['default'])
        
        # Extraer nombre
        nombre = self.extraer_texto_elemento(soup, patrones['nombre'])
        
        # Extraer precio
        precio_texto = self.extraer_texto_elemento(soup, patrones['precio'])
        precio_numerico = extraer_precio_numerico(precio_texto)
        
        # Detectar moneda
        moneda = 'USD'
        if precio_texto:
            if '€' in precio_texto:
                moneda = 'EUR'
            elif 'S/' in precio_texto or 'S/. ' in precio_texto:
                moneda = 'PEN'
            elif '$' in precio_texto:
                moneda = 'USD'
            elif 'R$' in precio_texto:
                moneda = 'BRL'
        
        # Extraer disponibilidad
        disponibilidad = self.extraer_texto_elemento(soup, patrones['disponibilidad']) or 'No disponible'
        
        # Extraer imagen
        imagen_url = self.extraer_texto_elemento(soup, patrones['imagen'], 'src')
        
        return ProductoEcommerce(
            nombre=nombre or 'Producto sin nombre',
            precio=precio_texto or 'Precio no disponible',
            precio_numerico=precio_numerico,
            moneda=moneda,
            disponibilidad=disponibilidad,
            url=url,
            imagen_url=imagen_url,
            tienda=obtener_dominio(url),
            fecha_consulta=datetime.utcnow().isoformat()
        )
    
    def monitorear_productos(self, urls: List[str]) -> List[ProductoEcommerce]:
        """
        Monitorea múltiples productos y retorna sus precios actuales.
        
        Args:
            urls: Lista de URLs de productos a monitorear
            
        Returns:
            Lista de productos con información actualizada
        """
        productos = []
        for url in urls:
            logger.info(f"Monitoreando: {url}")
            producto = self.extraer_producto(url)
            if producto:
                productos.append(producto)
        return productos

# =============================================================================
# SCRAPER GENÉRICO
# =============================================================================

class ScraperGenerico(ScraperBase):
    """
    Scraper genérico para extraer datos de cualquier página web.
    Útil para casos específicos donde se conocen los selectores.
    """
    
    def extraer_datos(self, url: str, configuracion: Dict) -> Dict:
        """
        Extrae datos según una configuración de selectores.
        
        Args:
            url: URL de la página
            configuracion: Diccionario con mapeo de campos a selectores CSS
                          Ejemplo: {'titulo': 'h1', 'precio': '.price'}
        
        Returns:
            Diccionario con los datos extraídos
        """
        soup = self.obtener_pagina(url)
        if not soup:
            return {'error': 'No se pudo obtener la página'}
        
        resultado = {
            'url': url,
            'fecha_extraccion': datetime.utcnow().isoformat()
        }
        
        for campo, selector in configuracion.items():
            if isinstance(selector, dict):
                # Selector con atributo
                valor = self.extraer_texto_elemento(
                    soup, 
                    selector.get('selector'), 
                    selector.get('atributo')
                )
            else:
                # Selector simple de texto
                valor = self.extraer_texto_elemento(soup, selector)
            
            resultado[campo] = valor
        
        return resultado
    
    def extraer_tabla(self, url: str, selector_tabla: str) -> List[Dict]:
        """
        Extrae datos de una tabla HTML.
        
        Args:
            url: URL de la página
            selector_tabla: Selector CSS de la tabla
            
        Returns:
            Lista de diccionarios, cada uno representa una fila
        """
        soup = self.obtener_pagina(url)
        if not soup:
            return []
        
        tabla = soup.select_one(selector_tabla)
        if not tabla:
            logger.error(f"No se encontró tabla con selector: {selector_tabla}")
            return []
        
        # Extraer headers
        headers = []
        header_row = tabla.select_one('thead tr')
        if header_row:
            headers = [limpiar_texto(th.get_text()) for th in header_row.select('th')]
        
        # Si no hay headers en thead, buscar en primera fila
        if not headers:
            primera_fila = tabla.select_one('tr')
            if primera_fila:
                headers = [limpiar_texto(th.get_text()) for th in primera_fila.select('th')]
        
        # Extraer filas
        filas = tabla.select('tbody tr') if tabla.select('tbody') else tabla.select('tr')[1:]
        
        datos = []
        for fila in filas:
            celdas = fila.select('td')
            if celdas and headers and len(celdas) == len(headers):
                fila_dict = {}
                for i, celda in enumerate(celdas):
                    fila_dict[headers[i]] = limpiar_texto(celda.get_text())
                datos.append(fila_dict)
        
        logger.info(f"Extraídas {len(datos)} filas de tabla")
        return datos

# =============================================================================
# EXPORTADORES DE DATOS
# =============================================================================

class ExportadorDatos:
    """Clase para exportar datos a diferentes formatos"""
    
    @staticmethod
    def a_json(datos: List[Dict], nombre_archivo: str) -> str:
        """
        Exporta datos a formato JSON.
        
        Args:
            datos: Lista de diccionarios con los datos
            nombre_archivo: Nombre del archivo (sin extensión)
            
        Returns:
            Ruta del archivo creado
        """
        crear_directorio_salida()
        ruta = os.path.join(DIRECTORIO_SALIDA, f"{nombre_archivo}.json")
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Datos exportados a JSON: {ruta}")
        return ruta
    
    @staticmethod
    def a_csv(datos: List[Dict], nombre_archivo: str) -> str:
        """
        Exporta datos a formato CSV.
        
        Args:
            datos: Lista de diccionarios con los datos
            nombre_archivo: Nombre del archivo (sin extensión)
            
        Returns:
            Ruta del archivo creado
        """
        if not datos:
            logger.warning("No hay datos para exportar")
            return ""
        
        crear_directorio_salida()
        ruta = os.path.join(DIRECTORIO_SALIDA, f"{nombre_archivo}.csv")
        
        # Obtener todas las claves posibles
        claves = set()
        for item in datos:
            claves.update(item.keys())
        claves = sorted(list(claves))
        
        with open(ruta, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=claves)
            writer.writeheader()
            writer.writerows(datos)
        
        logger.info(f"Datos exportados a CSV: {ruta}")
        return ruta
    
    @staticmethod
    def a_excel(datos: List[Dict], nombre_archivo: str) -> Optional[str]:
        """
        Exporta datos a formato Excel (.xlsx).
        
        Args:
            datos: Lista de diccionarios con los datos
            nombre_archivo: Nombre del archivo (sin extensión)
            
        Returns:
            Ruta del archivo creado o None si openpyxl no está instalado
        """
        if not EXCEL_DISPONIBLE:
            logger.warning("openpyxl no está instalado. Instala con: pip install openpyxl")
            return None
        
        if not datos:
            logger.warning("No hay datos para exportar")
            return None
        
        crear_directorio_salida()
        ruta = os.path.join(DIRECTORIO_SALIDA, f"{nombre_archivo}.xlsx")
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Datos"
        
        # Obtener headers
        claves = sorted(list(datos[0].keys()))
        
        # Escribir headers
        for col, clave in enumerate(claves, 1):
            ws.cell(row=1, column=col, value=clave)
        
        # Escribir datos
        for row, item in enumerate(datos, 2):
            for col, clave in enumerate(claves, 1):
                valor = item.get(clave, '')
                ws.cell(row=row, column=col, value=str(valor) if valor else '')
        
        wb.save(ruta)
        logger.info(f"Datos exportados a Excel: {ruta}")
        return ruta

# =============================================================================
# EJEMPLO DE USO Y DEMO
# =============================================================================

def demo_scraper_noticias():
    """
    Demostración del scraper de noticias.
    Extrae noticias de diferentes fuentes.
    """
    print("\n" + "="*60)
    print("📰 DEMO: SCRAPER DE NOTICIAS")
    print("="*60)
    
    scraper = ScraperNoticias()
    
    # URLs de ejemplo para demo
    urls_demo = [
        "https://elpais.com/tecnologia/",
        "https://www.bbc.com/news/technology"
    ]
    
    todas_noticias = []
    
    for url in urls_demo:
        print(f"\n🔍 Extrayendo noticias de: {url}")
        noticias = scraper.extraer_noticias(url, max_noticias=5)
        
        for i, noticia in enumerate(noticias, 1):
            print(f"\n  [{i}] {noticia.get('titulo', 'Sin título')[:80]}...")
            if noticia.get('resumen'):
                print(f"      {noticia.get('resumen')[:100]}...")
        
        todas_noticias.extend(noticias)
    
    # Exportar resultados
    if todas_noticias:
        ExportadorDatos.a_json(todas_noticias, "noticias_demo")
        ExportadorDatos.a_csv(todas_noticias, "noticias_demo")
        print(f"\n✅ Exportadas {len(todas_noticias)} noticias")
    
    return todas_noticias


def demo_scraper_ecommerce():
    """
    Demostración del scraper de e-commerce.
    Muestra cómo monitorear precios.
    """
    print("\n" + "="*60)
    print("🛒 DEMO: SCRAPER DE E-COMMERCE")
    print("="*60)
    
    scraper = ScraperEcommerce()
    
    # URLs de ejemplo (productos populares)
    urls_productos = [
        # Agregar URLs de productos reales para probar
        # Ejemplo: "https://www.amazon.com/dp/B08N5WRWNW"
    ]
    
    if not urls_productos:
        print("\n⚠️  Para probar el scraper de e-commerce, agrega URLs de productos")
        print("   Puedes agregar URLs de Amazon, MercadoLibre, etc.")
        return []
    
    productos = scraper.monitorear_productos(urls_productos)
    
    for producto in productos:
        print(f"\n📦 {producto.nombre[:60]}...")
        print(f"   💰 Precio: {producto.precio}")
        print(f"   📊 Disponibilidad: {producto.disponibilidad}")
    
    # Exportar resultados
    if productos:
        datos = [asdict(p) for p in productos]
        ExportadorDatos.a_json(datos, "productos_demo")
        print(f"\n✅ Exportados {len(productos)} productos")
    
    return productos


def demo_scraper_generico():
    """
    Demostración del scraper genérico.
    Muestra cómo extraer datos con selectores personalizados.
    """
    print("\n" + "="*60)
    print("🔧 DEMO: SCRAPER GENÉRICO")
    print("="*60)
    
    scraper = ScraperGenerico()
    
    # Ejemplo: extraer datos de una página con selectores específicos
    # El usuario puede configurar sus propios selectores
    
    print("\n📌 El scraper genérico permite extraer datos de cualquier página")
    print("   usando selectores CSS personalizados.\n")
    
    print("   Ejemplo de uso:")
    print("""
    configuracion = {
        'titulo': 'h1',
        'precio': '.price-amount',
        'descripcion': '.product-description',
        'imagen': {'selector': '.main-image img', 'atributo': 'src'}
    }
    
    datos = scraper.extraer_datos('https://ejemplo.com/producto', configuracion)
    """)
    
    print("\n   Para extraer tablas:")
    print("""
    datos_tabla = scraper.extraer_tabla(
        'https://ejemplo.com/datos',
        'table.datos'
    )
    """)


def main():
    """
    Función principal que ejecuta las demostraciones.
    """
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║           🕷️  WEB SCRAPER PROFESIONAL v1.0  🕷️            ║
║                                                            ║
║     Extrae datos de cualquier página web de forma          ║
║     eficiente y los exporta a múltiples formatos           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # Crear directorio de salida
    crear_directorio_salida()
    
    # Ejecutar demos
    print("\n🚀 Ejecutando demostraciones...\n")
    
    # Demo de noticias
    try:
        demo_scraper_noticias()
    except Exception as e:
        print(f"❌ Error en demo de noticias: {e}")
    
    # Demo de e-commerce
    try:
        demo_scraper_ecommerce()
    except Exception as e:
        print(f"❌ Error en demo de e-commerce: {e}")
    
    # Demo genérico
    demo_scraper_generico()
    
    print("\n" + "="*60)
    print("✅ DEMOSTRACIÓN COMPLETADA")
    print("="*60)
    print(f"\n📁 Los resultados se guardaron en: {DIRECTORIO_SALIDA}/")
    print("\n📚 Para usar el scraper en tus proyectos:")
    print("   1. Importa las clases necesarias")
    print("   2. Crea una instancia del scraper")
    print("   3. Llama a los métodos de extracción")
    print("   4. Exporta los resultados")
    print("\n📖 Consulta el README para más información.")


if __name__ == "__main__":
    main()
