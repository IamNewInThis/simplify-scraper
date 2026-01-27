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
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            # Cerrar banner de cookies si aparece
            print("[Jumbo] Verificando banner de cookies...")
            try:
                cookie_btn = await page.wait_for_selector(
                    'button:has-text("Aceptar"), button:has-text("Acepto"), #onetrust-accept-btn-handler',
                    timeout=3000
                )
                if cookie_btn:
                    await cookie_btn.click()
                    print("[Jumbo] Banner de cookies cerrado")
                    await page.wait_for_timeout(1000)
            except:
                print("[Jumbo] No se encontró banner de cookies")

            # Esperar a que aparezcan los productos
            print("[Jumbo] Esperando a que carguen los productos...")
            try:
                await page.wait_for_selector('[data-cnstrc-item-name]', timeout=15000)
            except:
                # Si no aparecen con el selector, esperar un poco más
                await page.wait_for_timeout(5000)

            # 2. Guardar screenshot para verificar
            await page.screenshot(path="/tmp/jumbo_search_results.png")
            print(f"[Jumbo] Screenshot guardado en /tmp/jumbo_search_results.png")

            # 3. Guardar HTML para análisis
            content = await page.content()
            with open('/tmp/jumbo_search.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[Jumbo] HTML guardado en /tmp/jumbo_search.html")

            # 4. Extraer productos usando los atributos data-cnstrc-*
            # Jumbo usa estos atributos para datos de productos
            product_cards = await page.query_selector_all('[data-cnstrc-item-name]')

            valid_products = []
            seen_ids = set()

            for card in product_cards:
                item_id = await card.get_attribute('data-cnstrc-item-id')

                # Evitar duplicados
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)

                    # Extraer datos del producto
                    name = await card.get_attribute('data-cnstrc-item-name')
                    price = await card.get_attribute('data-cnstrc-item-price')

                    # Obtener URL del producto
                    link = await card.query_selector('a[href*="/p"]')
                    url = await link.get_attribute('href') if link else None

                    # Obtener imagen
                    img = await card.query_selector('img')
                    image_url = await img.get_attribute('src') if img else None

                    valid_products.append({
                        'name': name,
                        'jumbo_id': item_id,
                        'price': int(price) if price else None,
                        'url': f"https://www.jumbo.cl{url}" if url and not url.startswith('http') else url,
                        'image_url': image_url
                    })

            print(f"[Jumbo] Encontrados {len(valid_products)} productos")

            await browser.close()

            return {
                "status": "success",
                "brand": search_term,
                "message": f"Búsqueda completada. {len(valid_products)} productos encontrados.",
                "product_count": len(valid_products),
                "products": valid_products,
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
    print(f"Productos encontrados: {result['product_count']}")
    print(f"Mensaje: {result['message']}")

    if result.get('products'):
        print("\n=== Lista de productos ===")
        for i, product in enumerate(result['products'], 1):
            print(f"\n{i}. {product['name']}")
            print(f"   ID Jumbo: {product['jumbo_id']}")
            print(f"   Precio: ${product['price']}")
            print(f"   URL: {product['url']}")
