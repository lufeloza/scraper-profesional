import asyncio
from scraper import demo_scraper_noticias, demo_scraper_ecommerce

async def main():
    print("🚀 Iniciando pruebas del Scraper Profesional Asíncrono...")
    noticias = await demo_scraper_noticias()
    # Para probar productos, descomenta la siguiente línea y añade URLs en scraper_config.json
    # productos = await demo_scraper_ecommerce()
    print("\n✅ Pruebas finalizadas con éxito.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
