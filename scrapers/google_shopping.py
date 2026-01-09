"""
Scraper para Google Shopping

Obtiene precios de múltiples retailers desde Google Shopping.
Usa técnicas anti-detección para evitar CAPTCHAs.
"""

import asyncio
from playwright.async_api import async_playwright
import re
import random


async def scrape_google_shopping(search_term: str):
    """
    Busca un producto en Google Shopping y extrae precios de todos los vendedores.
    
    Estrategia anti-detección:
    - Inicia en Google.cl (no directo a Shopping)
    - Simula búsqueda humana
    - User agent real
    - Delays aleatorios
    - Movimientos de mouse
    
    Args:
        search_term: Término de búsqueda (ej: "Leche Soprole Entera Natural 1 L")
        
    Returns:
        list: Lista de diccionarios con información de cada vendedor
    """
    async with async_playwright() as p:
        # Usar headless=False para evitar detección (luego configurar XVFB en producción)
        browser = await p.chromium.launch(
            headless=False,  # Cambiar a True con XVFB en producción
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='es-CL',
            timezone_id='America/Santiago',
            geolocation={'latitude': -33.4489, 'longitude': -70.6693},  # Santiago, Chile
            permissions=['geolocation']
        )
        
        page = await context.new_page()
        
        # Scripts anti-detección
        await page.add_init_script("""
            // Eliminar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Agregar plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Agregar languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-CL', 'es', 'en']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Permisos
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        try:
            # 1. Ir primero a Google.cl (comportamiento humano)
            print(f"[Google Shopping] Paso 1: Navegando a google.cl...")
            await page.goto("https://www.google.cl", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))  # Esperar más tiempo
            
            # 2. Simular movimiento de mouse
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await page.wait_for_timeout(random.randint(1000, 2000))  # Más tiempo
            
            # 3. Buscar el producto en el cuadro de búsqueda
            print(f"[Google Shopping] Paso 2: Buscando '{search_term}'...")
            search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
            
            # Escribir con delays naturales más lentos (simular tipeo humano)
            for char in search_term:
                await search_box.type(char, delay=random.randint(100, 250))  # Más lento
            
            await page.wait_for_timeout(random.randint(1000, 2000))  # Más tiempo antes de Enter
            
            # 4. Presionar Enter
            await search_box.press('Enter')
            await page.wait_for_timeout(random.randint(4000, 6000))  # Mucho más tiempo de espera
            
            # 4.5. Scroll suave (comportamiento humano)
            await page.evaluate('window.scrollTo({top: 200, behavior: "smooth"})')
            await page.wait_for_timeout(random.randint(1500, 2500))
            
            # 5. Buscar y hacer clic en la pestaña "Shopping"
            print(f"[Google Shopping] Paso 3: Navegando a Shopping...")
            try:
                # Intentar varios selectores para el botón de Shopping
                shopping_selectors = [
                    'a[href*="tbm=shop"]',  # Enlace directo a Shopping
                    'a:has-text("Shopping")',  # Texto visible "Shopping"
                    'div[role="tab"]:has-text("Shopping")',  # Tab de Shopping  
                    'a.YyVfkd:has-text("Shopping")',  # Clase específica
                    '[data-async-trigger="tbm_shop"]',  # Trigger async
                ]
                
                shopping_button = None
                for selector in shopping_selectors:
                    try:
                        shopping_button = await page.wait_for_selector(selector, timeout=8000)
                        if shopping_button:
                            print(f"[Google Shopping] ✓ Botón Shopping encontrado con selector: {selector}")
                            break
                    except:
                        continue
                
                if not shopping_button:
                    raise Exception("No se encontró el botón Shopping en ningún selector")
                
                # Mover mouse al botón (comportamiento humano)
                    box = await shopping_button.bounding_box()
                    if box:
                        await page.mouse.move(
                            box['x'] + box['width']/2, 
                            box['y'] + box['height']/2,
                            steps=random.randint(5, 15)
                        )
                        await page.wait_for_timeout(random.randint(500, 1000))
                
                # Hacer clic en el botón Shopping
                await shopping_button.click()
                print(f"[Google Shopping] ✓ Clic en Shopping exitoso")
                await page.wait_for_timeout(random.randint(5000, 7000))
                
                # Scroll suave después del clic
                await page.evaluate('window.scrollTo({top: 300, behavior: "smooth"})')
                await page.wait_for_timeout(random.randint(2000, 3000))
                    
            except Exception as e:
                print(f"[Google Shopping] ❌ Error fatal: No se puede acceder a Shopping - {e}")
                # NO HACER FALLBACK A URL DIRECTA - causa CAPTCHA
                raise Exception(f"No se puede acceder a Shopping: {e}")
            
            # 6. Hacer clic en el primer producto para ver todos los vendedores
            print("[Google Shopping] Paso 4: Haciendo clic en el primer producto...")
            try:
                # Buscar el primer producto usando los selectores correctos
                first_product = await page.wait_for_selector('div.njFjte[jsname="ZvZkAe"]', timeout=10000)
                
                if first_product:
                    # Mover mouse al producto (comportamiento humano)
                    box = await first_product.bounding_box()
                    if box:
                        await page.mouse.move(
                            box['x'] + box['width']/2,
                            box['y'] + box['height']/2,
                            steps=random.randint(5, 10)
                        )
                        await page.wait_for_timeout(random.randint(500, 1000))
                    
                    # Hacer clic usando JavaScript (más confiable cuando hay elementos encima)
                    await page.evaluate('(element) => element.click()', first_product)
                    print("[Google Shopping] ✓ Producto clickeado, esperando panel lateral...")
                    
                    # Esperar a que se abra el panel lateral con todos los vendedores
                    await page.wait_for_timeout(random.randint(5000, 7000))
                    
                    # Scroll en el panel lateral para cargar más vendedores
                    # El panel puede tener su propio scroll, intentar múltiples estrategias
                    await page.evaluate('''
                        // Intentar scrollear el panel lateral si existe
                        const panel = document.querySelector('[role="dialog"]') || document.querySelector('aside');
                        if (panel) {
                            panel.scrollTop = 1000;
                        } else {
                            window.scrollTo({top: 800, behavior: "smooth"});
                        }
                    ''')
                    await page.wait_for_timeout(random.randint(2000, 3000))
                    
                    # Scroll adicional para cargar más vendedores
                    await page.evaluate('''
                        const panel = document.querySelector('[role="dialog"]') || document.querySelector('aside');
                        if (panel) {
                            panel.scrollTop = 2000;
                        } else {
                            window.scrollTo({top: 1500, behavior: "smooth"});
                        }
                    ''')
                    await page.wait_for_timeout(random.randint(1500, 2500))
                else:
                    print("[Google Shopping] ⚠️  No se encontró el primer producto")
                    
            except Exception as e:
                print(f"[Google Shopping] Error haciendo clic en producto: {e}")
            
            # 7. Guardar screenshot para debug
            await page.screenshot(path="/tmp/google_shopping.png")
            print("[Google Shopping] Screenshot guardado en /tmp/google_shopping.png")
            
            # 8. Verificar si hay CAPTCHA
            content = await page.content()
            if 'recaptcha' in content.lower() or 'captcha' in content.lower():
                print("[Google Shopping] ⚠️  CAPTCHA detectado - Google está bloqueando")
                with open('/tmp/google_shopping_captcha.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                await browser.close()
                return [{
                    "retailer": "Google Shopping",
                    "nombre": "CAPTCHA detectado - Google bloqueó la solicitud",
                    "precio": "N/A",
                    "sku": "N/A",
                    "url": page.url,
                    "encontrado": False,
                    "error": "CAPTCHA"
                }]
            
            results = []
            
            # 9. Extraer todos los vendedores del panel lateral
            print(f"[Google Shopping] Paso 5: Extrayendo vendedores del panel lateral...")
            # Selector correcto basado en el HTML real de Google Shopping
            # Cada vendedor está en un div con role="listitem" y clase R5K7Cb
            product_items = await page.query_selector_all('div.R5K7Cb[role="listitem"]')
            
            print(f"[Google Shopping] Encontrados {len(product_items)} productos")
            
            if len(product_items) == 0:
                # Intentar obtener el HTML completo para ver la estructura
                content = await page.content()
                print(f"[Google Shopping] No se encontraron productos con el selector")
                print(f"[Google Shopping] Guardando HTML para análisis...")
                with open('/tmp/google_shopping.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                print("[Google Shopping] HTML guardado en /tmp/google_shopping.html")
            
            for idx, item in enumerate(product_items[:20]):  # Máximo 20 vendedores
                try:
                    product_name = None
                    product_price = None
                    retailer_name = None
                    product_url = None
                    
                    # Extraer nombre del vendedor/retailer (div.hP4iBf.gUf0b.uWvFpd)
                    retailer_element = await item.query_selector('div.hP4iBf.gUf0b.uWvFpd')
                    if retailer_element:
                        retailer_name = await retailer_element.inner_text()
                        retailer_name = retailer_name.strip()
                    
                    # Extraer precio (div.GBgquf.JIep9e > span con aria-label)
                    price_element = await item.query_selector('div.GBgquf.JIep9e span[aria-label]')
                    if price_element:
                        aria_label = await price_element.get_attribute('aria-label')
                        if aria_label:
                            # Extraer el precio del aria-label (ej: "Precio actual: CLP 1,150")
                            price_match = re.search(r'CLP\s*([\d\.,]+)', aria_label)
                            if price_match:
                                product_price = f"${price_match.group(1)}"
                    
                    # Si no encontramos precio con aria-label, intentar con el texto
                    if not product_price:
                        price_element = await item.query_selector('div.GBgquf.JIep9e')
                        if price_element:
                            price_text = await price_element.inner_text()
                            price_match = re.search(r'CLP\s*([\d\.,]+)', price_text)
                            if price_match:
                                product_price = f"${price_match.group(1)}"
                    
                    # Extraer nombre del producto (div.Rp8BL.CpcIhb.y1FcZd.rYkzq)
                    name_element = await item.query_selector('div.Rp8BL.CpcIhb.y1FcZd.rYkzq')
                    if name_element:
                        product_name = await name_element.inner_text()
                        product_name = product_name.strip()
                    
                    # Extraer URL del producto (enlace principal con clase P9159d)
                    link_element = await item.query_selector('a.P9159d[href]')
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href:
                            # Google Shopping usa URLs de redirección, extraer la URL real
                            if 'url=' in href:
                                from urllib.parse import unquote
                                url_match = re.search(r'url=([^&]+)', href)
                                if url_match:
                                    product_url = unquote(url_match.group(1))
                            else:
                                product_url = href
                    
                    if product_name and product_price and retailer_name:
                        results.append({
                            "retailer": retailer_name,
                            "nombre": product_name,
                            "precio": product_price,
                            "sku": "N/A",  # Google Shopping no muestra SKU
                            "url": product_url or "",
                            "encontrado": True
                        })
                        print(f"[Google Shopping] {idx+1}. {retailer_name}: {product_price} - {product_name[:50]}...")
                    
                except Exception as e:
                    print(f"[Google Shopping] Error procesando item {idx+1}: {e}")
                    continue
            
            await browser.close()
            
            if len(results) == 0:
                return [{
                    "retailer": "Google Shopping",
                    "nombre": "No se encontraron resultados",
                    "precio": "N/A",
                    "sku": "N/A",
                    "url": page.url,
                    "encontrado": False
                }]
            
            print(f"\n[Google Shopping] Total de vendedores encontrados: {len(results)}")
            return results
            
        except Exception as e:
            await browser.close()
            print(f"[Google Shopping] Error: {e}")
            import traceback
            traceback.print_exc()
            return [{
                "retailer": "Google Shopping",
                "nombre": "Error",
                "precio": "Error",
                "sku": "Error",
                "url": "",
                "error": str(e),
                "encontrado": False
            }]


# Función de prueba
if __name__ == "__main__":
    results = asyncio.run(scrape_google_shopping("Leche Entera Natural Soprole 1L"))
    print("\n=== Resultados de Google Shopping ===")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['retailer']}")
        print(f"   Producto: {result['nombre']}")
        print(f"   Precio: {result['precio']}")
        if result['url']:
            print(f"   URL: {result['url'][:80]}...")
