"""
Scraper simple para Jumbo.cl

Este es un scraper básico que busca un producto en Jumbo y extrae su nombre, precio y SKU.
Usa Playwright para navegar el sitio porque Jumbo usa JavaScript para cargar contenido.
"""

import asyncio
from playwright.async_api import async_playwright


async def scrape_jumbo_product(search_term: str):
    """
    Busca un producto en Jumbo y extrae nombre, precio y SKU.
    
    Args:
        search_term: Término de búsqueda (ej: "Leche Soprole Entera Natural 1 L")
        
    Returns:
        dict: Diccionario con nombre, precio, SKU y url del producto
    """
    async with async_playwright() as p:
        # Lanzar navegador (headless=True para que no se vea la ventana)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 1. Ir directamente a la búsqueda de Jumbo
            search_url = f"https://www.jumbo.cl/busqueda?ft={search_term}"
            print(f"Navegando a búsqueda: {search_url}")
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            # Esperar a que cargue la página
            await page.wait_for_timeout(5000)
            
            # 2. Buscar el primer producto en los resultados
            # Jumbo usa selectores específicos para los productos
            try:
                # Esperar a que carguen los productos
                await page.wait_for_timeout(2000)
                
                # Buscar todos los links que podrían ser productos
                all_links = await page.query_selector_all('a[href*="/p"]')
                print(f"Se encontraron {len(all_links)} enlaces con '/p'")
                
                product_url = None
                for link in all_links:
                    url = await link.get_attribute('href')
                    print(f"Analizando link: {url}")
                    
                    # Filtrar solo URLs de productos de Jumbo (no externos)
                    if url and '/p' in url and 'jumbo.cl' in url or (url.startswith('/') and '/p' in url):
                        # Ignorar enlaces externos o publicitarios
                        if 'puntoscencosud' not in url and 'utm_' not in url:
                            if not url.startswith('http'):
                                product_url = 'https://www.jumbo.cl' + url
                            else:
                                product_url = url
                            print(f"✓ Producto válido encontrado: {product_url}")
                            break
                
                if not product_url:
                    raise Exception("No se encontró ningún producto válido")
                
                print(f"Navegando al producto: {product_url}")
                await page.goto(product_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Error buscando producto: {e}")
                await browser.close()
                return {
                    "retailer": "Jumbo",
                    "nombre": "Producto no encontrado en búsqueda",
                    "precio": "N/A",
                    "sku": "N/A",
                    "url": search_url,
                    "encontrado": False,
                    "error": str(e)
                }
            
            # 3. Extraer información del producto
            product_name = None
            product_price = None
            product_sku = None
            current_url = page.url
            
            # Extraer nombre
            try:
                # Buscar por h1 o el selector específico de Jumbo
                name_selectors = [
                    'h1.product-name',
                    'h1',
                    '[class*="product-name"]'
                ]
                for selector in name_selectors:
                    element = await page.query_selector(selector)
                    if element:
                        product_name = await element.inner_text()
                        product_name = product_name.strip()
                        if product_name:
                            print(f"Nombre encontrado: {product_name}")
                            break
            except Exception as e:
                print(f"Error extrayendo nombre: {e}")
            
            # Extraer precio (solo el precio principal, no ofertas)
            try:
                # En Jumbo, el precio principal está en un div con clase específica
                # Primero intentar el precio principal (texto más grande)
                price_element = await page.query_selector('div.sticky-product-prices div.text-3xl')
                
                if price_element:
                    # Obtener solo el texto del primer hijo (el precio, sin los spans internos)
                    price_text = await price_element.evaluate('el => el.childNodes[0]?.textContent || el.textContent')
                    price_text = price_text.strip()
                    
                    # Limpiar: extraer solo el precio con $
                    import re
                    price_match = re.search(r'\$[\d\.,]+', price_text)
                    if price_match:
                        product_price = price_match.group(0)
                        print(f"Precio encontrado: {product_price}")
                        
            except Exception as e:
                print(f"Error extrayendo precio: {e}")
            
            # Extraer SKU (Código del producto)
            try:
                # En Jumbo el código está en un span con clase product-code
                sku_element = await page.query_selector('span.product-code')
                
                if sku_element:
                    text = await sku_element.inner_text()
                    # El texto es "Código: 1589277", extraer solo el número
                    import re
                    sku_match = re.search(r'\d+', text)
                    if sku_match:
                        product_sku = sku_match.group(0)
                        print(f"SKU encontrado: {product_sku}")
                
                # Si no encontramos el código en el span, intentar desde la URL
                if not product_sku:
                    # En la URL de Jumbo viene como: /producto-nombre-CODIGO-jumbo/p
                    # Buscar patrones numéricos largos (códigos de producto)
                    url_parts = current_url.split('/')
                    for part in url_parts:
                        # Buscar partes que contengan números (posibles SKU)
                        import re
                        numbers = re.findall(r'\d{6,}', part)  # SKU suele tener 6+ dígitos
                        if numbers:
                            product_sku = numbers[0]
                            print(f"SKU extraído de URL: {product_sku}")
                            break
                
            except Exception as e:
                print(f"Error extrayendo SKU: {e}")
            
            # Cerrar navegador
            await browser.close()
            
            return {
                "retailer": "Jumbo",
                "nombre": product_name or "No encontrado",
                "precio": product_price or "No disponible",
                "sku": product_sku or "No disponible",
                "url": current_url,
                "encontrado": product_name is not None and product_price is not None
            }
            
        except Exception as e:
            await browser.close()
            return {
                "retailer": "Jumbo",
                "nombre": "Error",
                "precio": "Error",
                "sku": "Error",
                "url": "",
                "error": str(e),
                "encontrado": False
            }


# Función de prueba
if __name__ == "__main__":
    # Probar el scraper
    result = asyncio.run(scrape_jumbo_product("Leche Soprole Natural 1 Litro"))
    print("\n=== Resultado del Scraping ===")
    print(f"Nombre: {result['nombre']}")
    print(f"Precio: {result['precio']}")
    print(f"SKU: {result['sku']}")
    print(f"URL: {result['url']}")
    print(f"Encontrado: {result['encontrado']}")

