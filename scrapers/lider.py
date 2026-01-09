"""
Scraper para Líder (Walmart Chile)

Líder usa una estructura diferente basada en Walmart.
Los productos se buscan por código EAN o nombre.
"""

import asyncio
from playwright.async_api import async_playwright
import re


async def scrape_lider_product(search_term: str):
    """
    Busca un producto en Líder y extrae nombre, precio y SKU.
    
    Args:
        search_term: Término de búsqueda
        
    Returns:
        dict: Diccionario con nombre, precio, SKU y url del producto
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 1. Ir a búsqueda
            search_url = f"https://super.lider.cl/search?q={search_term}"
            print(f"[Líder] Navegando a: {search_url}")
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 2. Buscar primer producto
            # Líder usa enlaces diferentes, buscar por patrones de producto
            all_links = await page.query_selector_all('a[href*="/ip/"]')
            product_url = None
            
            if all_links:
                first_link = all_links[0]
                url = await first_link.get_attribute('href')
                if url:
                    if not url.startswith('http'):
                        product_url = 'https://super.lider.cl' + url
                    else:
                        product_url = url
            
            if not product_url:
                raise Exception("Producto no encontrado")
            
            print(f"[Líder] Navegando a: {product_url}")
            await page.goto(product_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            product_name = None
            product_price = None
            product_sku = None
            
            # 3. Extraer nombre (en Líder está en un h1)
            try:
                name_element = await page.query_selector('h1')
                if name_element:
                    product_name = await name_element.inner_text()
                    product_name = product_name.strip()
                    print(f"[Líder] Nombre: {product_name}")
            except Exception as e:
                print(f"[Líder] Error extrayendo nombre: {e}")
            
            # 4. Extraer precio
            try:
                # Buscar texto que contenga "El precio actual es"
                price_selectors = [
                    'span:has-text("El precio actual es") ~ *',
                    '[class*="price"]'
                ]
                
                # Buscar en todo el contenido el precio
                content = await page.content()
                price_pattern = r'El precio actual es\s*\$[\d\.,]+'
                price_match = re.search(price_pattern, content)
                
                if price_match:
                    price_text = price_match.group(0)
                    price_value = re.search(r'\$[\d\.,]+', price_text)
                    if price_value:
                        product_price = price_value.group(0)
                        print(f"[Líder] Precio: {product_price}")
            except Exception as e:
                print(f"[Líder] Error extrayendo precio: {e}")
            
            # 5. Extraer SKU/Item
            try:
                # Líder muestra "Item: 254295" en especificaciones
                content = await page.content()
                sku_pattern = r'Item\s*:\s*(\d+)'
                sku_match = re.search(sku_pattern, content)
                
                if sku_match:
                    product_sku = sku_match.group(1)
                    print(f"[Líder] SKU/Item: {product_sku}")
                else:
                    # Extraer del código EAN de la URL
                    ean_match = re.search(r'/(\d{13,14})(?:\?|$)', current_url)
                    if ean_match:
                        product_sku = ean_match.group(1)
                        print(f"[Líder] EAN extraído de URL: {product_sku}")
            except Exception as e:
                print(f"[Líder] Error extrayendo SKU: {e}")
            
            await browser.close()
            
            return {
                "retailer": "Líder",
                "nombre": product_name or "No encontrado",
                "precio": product_price or "No disponible",
                "sku": product_sku or "No disponible",
                "url": current_url,
                "encontrado": product_name is not None and product_price is not None
            }
            
        except Exception as e:
            await browser.close()
            return {
                "retailer": "Líder",
                "nombre": "Error",
                "precio": "Error",
                "sku": "Error",
                "url": "",
                "error": str(e),
                "encontrado": False
            }
