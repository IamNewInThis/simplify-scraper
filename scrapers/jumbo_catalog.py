"""
Scraper para catálogo de Jumbo

Obtiene lista de productos de una marca o categoría desde Jumbo.cl
Usa la URL de búsqueda directa para evitar detección.
"""

import asyncio
from playwright.async_api import async_playwright


async def scrape_jumbo_catalog(search_term: str):
    """
    Busca productos en Jumbo.cl por marca o categoría.

    Usa la URL de búsqueda directa: https://www.jumbo.cl/busqueda?ft={term}

    Args:
        search_term: Término de búsqueda (ej: "Soprole", "Cereales")

    Returns:
        dict: Estado del scraping y lista de productos encontrados
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # 1. Ir directamente a la búsqueda de Jumbo
            search_url = f"https://www.jumbo.cl/busqueda?ft={search_term}"
            print(f"[Jumbo] Navegando a: {search_url}")
            await page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Esperar a que carguen los productos
            await page.wait_for_timeout(3000)

            # 2. Guardar screenshot para verificar
            await page.screenshot(path="/tmp/jumbo_search_results.png")
            print(f"[Jumbo] Screenshot guardado en /tmp/jumbo_search_results.png")

            # 3. Guardar HTML para análisis
            content = await page.content()
            with open('/tmp/jumbo_search.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[Jumbo] HTML guardado en /tmp/jumbo_search.html")

            # 4. Contar productos encontrados (por ahora solo contamos)
            # Los productos en Jumbo están en elementos con clase específica
            product_links = await page.query_selector_all('a[href*="/p"]')

            # Filtrar solo links válidos de productos
            valid_products = []
            for link in product_links:
                href = await link.get_attribute('href')
                if href and '/p' in href and 'puntoscencosud' not in href and 'utm_' not in href:
                    if href not in [p['url'] for p in valid_products]:
                        valid_products.append({'url': href})

            print(f"[Jumbo] Encontrados {len(valid_products)} productos")

            await browser.close()

            return {
                "status": "success",
                "brand": search_term,
                "message": f"Búsqueda completada. {len(valid_products)} productos encontrados.",
                "product_count": len(valid_products),
                "search_url": search_url
            }

        except Exception as e:
            print(f"[Jumbo] Error: {e}")
            await page.screenshot(path="/tmp/jumbo_error.png")
            await browser.close()

            import traceback
            traceback.print_exc()

            return {
                "status": "error",
                "brand": search_term,
                "message": str(e),
                "product_count": 0
            }


# Función de prueba
if __name__ == "__main__":
    result = asyncio.run(scrape_jumbo_catalog("Soprole"))
    print("\n=== Resultado del scraping de Jumbo ===")
    print(f"Estado: {result['status']}")
    print(f"Marca: {result['brand']}")
    print(f"Productos: {result['product_count']}")
    print(f"Mensaje: {result['message']}")
