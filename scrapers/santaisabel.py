"""
Scraper para Santa Isabel

Santa Isabel usa la misma plataforma que Jumbo (Cencosud)
por lo que la estructura HTML es muy similar.
"""

import asyncio
from playwright.async_api import async_playwright
import re


async def scrape_santaisabel_product(search_term: str):
    """
    Busca un producto en Santa Isabel y extrae nombre, precio y SKU.
    
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
            search_url = f"https://www.santaisabel.cl/busqueda?ft={search_term}"
            print(f"[Santa Isabel] Navegando a: {search_url}")
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 2. Buscar primer producto válido
            all_links = await page.query_selector_all('a[href*="/p"]')
            product_url = None
            
            for link in all_links:
                url = await link.get_attribute('href')
                if url and '/p' in url and 'santaisabel.cl' in url or (url.startswith('/') and '/p' in url):
                    if 'puntoscencosud' not in url and 'utm_' not in url:
                        if not url.startswith('http'):
                            product_url = 'https://www.santaisabel.cl' + url
                        else:
                            product_url = url
                        break
            
            if not product_url:
                raise Exception("Producto no encontrado")
            
            print(f"[Santa Isabel] Navegando a: {product_url}")
            await page.goto(product_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            product_name = None
            product_price = None
            product_sku = None
            
            # 3. Extraer nombre
            try:
                name_element = await page.query_selector('h1.product-name, h1')
                if name_element:
                    product_name = await name_element.inner_text()
                    product_name = product_name.strip()
                    print(f"[Santa Isabel] Nombre: {product_name}")
            except Exception as e:
                print(f"[Santa Isabel] Error extrayendo nombre: {e}")
            
            # 4. Extraer precio
            try:
                price_element = await page.query_selector('div.sticky-product-prices div.text-3xl')
                if price_element:
                    price_text = await price_element.evaluate('el => el.childNodes[0]?.textContent || el.textContent')
                    price_match = re.search(r'\$[\d\.,]+', price_text.strip())
                    if price_match:
                        product_price = price_match.group(0)
                        print(f"[Santa Isabel] Precio: {product_price}")
            except Exception as e:
                print(f"[Santa Isabel] Error extrayendo precio: {e}")
            
            # 5. Extraer SKU
            try:
                sku_element = await page.query_selector('span.product-code')
                if sku_element:
                    text = await sku_element.inner_text()
                    sku_match = re.search(r'\d+', text)
                    if sku_match:
                        product_sku = sku_match.group(0)
                        print(f"[Santa Isabel] SKU: {product_sku}")
            except Exception as e:
                print(f"[Santa Isabel] Error extrayendo SKU: {e}")
            
            await browser.close()
            
            return {
                "retailer": "Santa Isabel",
                "nombre": product_name or "No encontrado",
                "precio": product_price or "No disponible",
                "sku": product_sku or "No disponible",
                "url": current_url,
                "encontrado": product_name is not None and product_price is not None
            }
            
        except Exception as e:
            await browser.close()
            return {
                "retailer": "Santa Isabel",
                "nombre": "Error",
                "precio": "Error",
                "sku": "Error",
                "url": "",
                "error": str(e),
                "encontrado": False
            }
