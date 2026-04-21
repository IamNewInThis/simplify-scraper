"""
Scraper para Google Shopping

Obtiene precios de múltiples retailers desde Google Shopping.
Usa playwright-stealth para evitar detección en producción.
"""

import asyncio
import re
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


# Extrae nombre, precio CLP y tienda desde el aria-label de cada tarjeta de producto.
# Formato: "<nombre>. Precio actual: CLP <precio>. <tienda> y más."
# Usamos aria-label porque es requerido por accesibilidad y Google no lo rota.
_ARIA_PRICE_RE = re.compile(
    r'^(.+?)\.\s+Precio actual:\s+CLP\s+([\d\.,]+)\.\s+(.+?)(?:\s+y más)?(?:\.\s*.*)?$',
    re.DOTALL
)

# Badges que pueden aparecer antes del nombre del retailer en el texto del panel
_PANEL_BADGES = {'más popular', 'cerca', 'mejor precio', 'más vendido', 'oferta'}


def _parse_panel_link_text(text: str) -> tuple[str, str]:
    """
    Parsea el texto de un link de panel: "<badge?>|<retailer>|CLP <precio>|..."
    Retorna (retailer, precio_str) o ("", "") si no se puede parsear.
    """
    parts = [p.strip() for p in text.split('|') if p.strip()]
    retailer = ""
    price_str = ""

    for i, part in enumerate(parts):
        if part.lower() in _PANEL_BADGES:
            continue
        if not retailer:
            retailer = part
            continue
        if part.upper().startswith('CLP'):
            price_str = part
            break

    return retailer, price_str


async def scrape_google_shopping(search_term: str) -> list[dict]:
    """
    Busca un producto en Google Shopping y extrae precios de todos los vendedores.

    Estrategia:
    1. Navega Google.cl → busca → pestaña Shopping (anti-bot con delays y stealth)
    2. Abre el panel de un producto y hace clic en "Más tiendas"
    3. Extrae retailers del panel usando jsname="uwagwf" (estable, no depende de
       clases CSS ofuscadas que Google rota frecuentemente)
    4. Si el panel falla, extrae precios del resultado principal vía aria-label

    Args:
        search_term: Término de búsqueda (ej: "Leche Soprole Entera Natural 1 L")

    Returns:
        list: [{"retailer", "nombre", "precio", "url", "encontrado"}, ...]
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--hide-scrollbars',
                '--mute-audio',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='es-CL',
            timezone_id='America/Santiago',
            geolocation={'latitude': -33.4489, 'longitude': -70.6693},
            permissions=['geolocation'],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        page = await context.new_page()

        stealth_config = Stealth()
        await page.goto("about:blank")
        stealth_config.apply_stealth_sync(page)

        try:
            # 1. Navegar a Google.cl
            print(f"[Google Shopping] Paso 1: Navegando a google.cl...")
            await page.goto("https://www.google.cl", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(random.randint(2000, 3000))

            # Simular comportamiento humano
            print(f"[Google Shopping] Simulando comportamiento natural...")
            for _ in range(random.randint(2, 4)):
                await page.mouse.move(
                    random.randint(100, 1000),
                    random.randint(100, 800),
                    steps=random.randint(10, 25)
                )
                await page.wait_for_timeout(random.randint(300, 800))
            await page.evaluate('window.scrollTo({top: 150, behavior: "smooth"})')
            await page.wait_for_timeout(random.randint(1000, 1500))

            # 2. Buscar el producto
            print(f"[Google Shopping] Paso 2: Buscando '{search_term}'...")
            search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
            await search_box.click()
            await page.wait_for_timeout(random.randint(400, 700))
            for i, char in enumerate(search_term):
                await search_box.type(char, delay=random.randint(80, 180))
                if i > 0 and i % random.randint(8, 12) == 0:
                    await page.wait_for_timeout(random.randint(200, 500))
            await page.wait_for_timeout(random.randint(1500, 2500))
            await search_box.press('Enter')
            await page.wait_for_timeout(random.randint(5000, 7000))
            await page.evaluate('window.scrollTo({top: 250, behavior: "smooth"})')
            await page.wait_for_timeout(random.randint(2000, 3000))

            # 3. Ir a la pestaña Shopping
            print(f"[Google Shopping] Paso 3: Navegando a Shopping...")
            shopping_selectors = [
                'a[href*="tbm=shop"]',
                'a:has-text("Shopping")',
                'div[role="tab"]:has-text("Shopping")',
                '[data-async-trigger="tbm_shop"]',
            ]
            shopping_button = None
            for selector in shopping_selectors:
                try:
                    shopping_button = await page.wait_for_selector(selector, timeout=8000)
                    if shopping_button:
                        print(f"[Google Shopping] ✓ Botón Shopping: {selector}")
                        break
                except Exception:
                    continue
            if not shopping_button:
                raise Exception("No se encontró el botón Shopping")

            box = await shopping_button.bounding_box()
            if box:
                await page.mouse.move(
                    box['x'] + box['width'] / 2,
                    box['y'] + box['height'] / 2,
                    steps=random.randint(5, 15)
                )
                await page.wait_for_timeout(random.randint(500, 1000))
            await shopping_button.click()
            print(f"[Google Shopping] ✓ Clic en Shopping exitoso")
            await page.wait_for_timeout(random.randint(5000, 7000))
            await page.evaluate('window.scrollTo({top: 300, behavior: "smooth"})')
            await page.wait_for_timeout(random.randint(2000, 3000))

            # Verificar CAPTCHA
            content = await page.content()
            if 'recaptcha' in content.lower() or 'captcha' in content.lower():
                print("[Google Shopping] ⚠️  CAPTCHA detectado")
                with open('/tmp/google_shopping_captcha.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                await browser.close()
                return [_error_result(page.url, "CAPTCHA")]

            # 4. Abrir panel del primer producto
            print("[Google Shopping] Paso 4: Abriendo panel del primer producto...")
            try:
                first_product = await page.wait_for_selector('[jsname="ZvZkAe"]', timeout=10000)
                if first_product:
                    box = await first_product.bounding_box()
                    if box:
                        await page.mouse.move(
                            box['x'] + box['width'] / 2,
                            box['y'] + box['height'] / 2,
                            steps=random.randint(5, 10)
                        )
                        await page.wait_for_timeout(random.randint(500, 1000))
                    await page.evaluate('(el) => el.click()', first_product)
                    print("[Google Shopping] ✓ Producto clickeado, esperando panel...")
                    await page.wait_for_timeout(random.randint(5000, 7000))
            except Exception as e:
                print(f"[Google Shopping] ⚠️  No se pudo abrir panel: {e}")

            # 5. Clic en "Más tiendas" para cargar todos los retailers
            print("[Google Shopping] Paso 5: Buscando 'Más tiendas'...")
            try:
                more_stores = await page.wait_for_selector(
                    'span:has-text("Más tiendas"), div.ZFiwCf', timeout=5000
                )
                if more_stores:
                    await page.evaluate('(el) => el.click()', more_stores)
                    print("[Google Shopping] ✓ Clic en 'Más tiendas'")
                    await page.wait_for_timeout(random.randint(3000, 5000))
                    # Scroll dentro del panel para cargar todos
                    await page.evaluate('''
                        const panel = document.querySelector('[role="dialog"]') || document.querySelector('aside');
                        if (panel) panel.scrollTop = panel.scrollHeight;
                        else window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
                    ''')
                    await page.wait_for_timeout(random.randint(2000, 3000))
            except Exception:
                print("[Google Shopping] ℹ️  Sin botón 'Más tiendas'")

            await page.screenshot(path="/tmp/google_shopping.png")
            print("[Google Shopping] Screenshot guardado en /tmp/google_shopping.png")

            # 6. Extraer retailers del panel
            # jsname="uwagwf" + role="listitem" es estable porque jsname es un
            # identificador interno de Google, no una clase CSS ofuscada rotable.
            results = await _extract_panel_results(page)

            # Fallback: extraer del resultado principal via aria-label si el panel falla
            if not results:
                print("[Google Shopping] ℹ️  Panel vacío, extrayendo de resultados principales...")
                results = await _extract_main_results(page)

            await browser.close()

            if not results:
                with open('/tmp/google_shopping_no_results.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                print("[Google Shopping] No se encontraron resultados. HTML guardado.")
                return [_error_result("", "Sin resultados")]

            print(f"\n[Google Shopping] Total vendedores: {len(results)}")
            return results

        except Exception as e:
            await browser.close()
            print(f"[Google Shopping] Error: {e}")
            import traceback
            traceback.print_exc()
            return [_error_result("", str(e))]


async def _extract_panel_results(page) -> list[dict]:
    """
    Extrae retailers del panel lateral usando jsname="uwagwf".
    Cada item tiene un link directo al producto en la tienda.
    """
    # jsname="uwagwf" identifica cada fila de retailer en el panel de precio.
    # Más estable que las clases CSS como R5K7Cb que Google rota frecuentemente.
    items = await page.query_selector_all('div[jsname="uwagwf"][role="listitem"]')
    print(f"[Google Shopping] Panel: {len(items)} retailers encontrados")

    results = []
    seen = set()

    for idx, item in enumerate(items):
        try:
            # El link tiene href al producto en la tienda y texto con retailer + precio
            link = await item.query_selector('a[href]:not([href*="google.com"])')
            if not link:
                continue

            href = await link.get_attribute('href') or ''
            text = await link.inner_text() or ''
            text_pipe = '|'.join(t.strip() for t in text.split('\n') if t.strip())

            retailer, price_str = _parse_panel_link_text(text_pipe)
            if not retailer or not price_str:
                continue

            key = retailer.lower()
            if key in seen:
                continue
            seen.add(key)

            # Extraer nombre del producto del texto (parte después del precio)
            product_name = ""
            parts = [p.strip() for p in text_pipe.split('|') if p.strip()]
            price_idx = next((i for i, p in enumerate(parts) if p.upper().startswith('CLP')), -1)
            if price_idx >= 0 and price_idx + 1 < len(parts):
                product_name = parts[price_idx + 1]

            results.append({
                "retailer": retailer,
                "nombre": product_name,
                "precio": price_str,
                "sku": "N/A",
                "url": href,
                "encontrado": True
            })
            print(f"[Google Shopping] {len(results)}. {retailer}: {price_str}")

        except Exception as e:
            print(f"[Google Shopping] Error en item {idx+1}: {e}")
            continue

    return results


async def _extract_main_results(page) -> list[dict]:
    """
    Fallback: extrae precios del resultado principal de la búsqueda vía aria-label.
    No incluye URL directa al producto en la tienda.
    """
    cards = await page.query_selector_all('[jsname="ZvZkAe"]')
    print(f"[Google Shopping] Resultados principales: {len(cards)} tarjetas")

    results = []
    seen = set()

    for idx, card in enumerate(cards[:40]):
        try:
            label = await card.get_attribute('aria-label') or ''
            m = _ARIA_PRICE_RE.match(label.strip())
            if not m:
                continue

            product_name = m.group(1).strip()
            price_str = f"CLP {m.group(2).strip()}"
            retailer = m.group(3).strip()

            if 'general' in retailer.lower() or 'precio' in retailer.lower():
                continue

            key = (retailer.lower(), m.group(2))
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "retailer": retailer,
                "nombre": product_name,
                "precio": price_str,
                "sku": "N/A",
                "url": "",
                "encontrado": True
            })
            print(f"[Google Shopping] {len(results)}. {retailer}: {price_str}")

        except Exception as e:
            print(f"[Google Shopping] Error en tarjeta {idx+1}: {e}")
            continue

    return results


def _error_result(url: str, error: str) -> dict:
    return {
        "retailer": "Google Shopping",
        "nombre": "Error",
        "precio": "N/A",
        "sku": "N/A",
        "url": url,
        "encontrado": False,
        "error": error
    }


if __name__ == "__main__":
    results = asyncio.run(scrape_google_shopping("Leche Entera Natural Soprole 1L"))
    print("\n=== Resultados de Google Shopping ===")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['retailer']}")
        print(f"   Producto: {result['nombre']}")
        print(f"   Precio: {result['precio']}")
        if result.get('url'):
            print(f"   URL: {result['url'][:80]}...")
