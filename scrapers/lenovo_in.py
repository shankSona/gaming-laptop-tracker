import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

# Lenovo India uses a JS-heavy storefront (React/commercetools).
# These URLs are the closest to static product listings they offer.

URLS = {
    "LOQ":    "https://www.lenovo.com/in/en/laptops/loq-laptops/c/loq-laptops",
    "Legion": "https://www.lenovo.com/in/en/laptops/legion-laptops/c/legion-laptops",
}

LENOVO_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.lenovo.com/in/en/",
    "Sec-Fetch-Site": "same-origin",
}


class LenovoIndiaScraper(BaseScraper):
    name = "Lenovo India"

    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                resp = self.get(url, extra_headers=LENOVO_HEADERS)
                soup = BeautifulSoup(resp.text, "lxml")

                # Try to find products in embedded JSON (Next.js / SSR data)
                json_found = self._try_json(soup, series, url, results)
                if json_found:
                    continue

                # HTML card fallback
                cards = (
                    soup.select(".product-item") or
                    soup.select("[data-product-id]") or
                    soup.select(".bx-product-card") or
                    soup.select("[class*='ProductTile']") or
                    soup.select(".product-tile")
                )

                for card in cards:
                    try:
                        name_el = (
                            card.select_one(".product-title") or
                            card.select_one("h3") or
                            card.select_one(".item-title") or
                            card.select_one("[class*='title']")
                        )
                        price_el = (
                            card.select_one(".price") or
                            card.select_one(".product-price") or
                            card.select_one("[class*='price']")
                        )
                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        price_text = re.sub(r"[^\d]", "", price_el.get_text())
                        if not price_text:
                            continue
                        price = float(price_text)
                        if price < 40000 or price > 500000:
                            continue

                        link_el = card.select_one("a[href]")
                        product_url = url
                        if link_el:
                            href = link_el.get("href", "")
                            product_url = href if href.startswith("http") else f"https://www.lenovo.com{href}"

                        model_id = f"LEN-{series.upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id,
                            brand="Lenovo",
                            series=series,
                            model_name=name[:120],
                            cpu="See site",
                            gpu="See site",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.4,
                            price_inr=price,
                            in_stock=bool(card.select_one("[class*='add-to-cart'], [class*='cart']")),
                            vendor_name="lenovo.com/in",        # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Lenovo {series} error: {e}")

        return results

    def _try_json(self, soup, series, url, results) -> bool:
        """Try to extract products from embedded JSON (SSR/Next.js)."""
        import json
        found = False
        for script in soup.select("script[type='application/json'], script#__NEXT_DATA__"):
            try:
                data = json.loads(script.string or "")
                # Walk the JSON looking for product lists
                products = self._find_products(data)
                for p in products[:10]:
                    try:
                        name = p.get("name", p.get("title", ""))
                        price = float(
                            p.get("price", {}).get("value", 0) or
                            p.get("salePrice", 0) or
                            p.get("currentPrice", 0) or 0
                        )
                        if not name or price < 40000:
                            continue
                        model_id = f"LEN-{series.upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id, brand="Lenovo", series=series,
                            model_name=name[:120], cpu="See site", gpu="See site",
                            ram_gb=16, storage_gb=512, display_inches=15.6,
                            refresh_hz=144, weight_kg=2.4, price_inr=price,
                            in_stock=True, vendor_name="lenovo.com/in", source_url=url,
                        ))
                        found = True
                    except Exception:
                        continue
            except Exception:
                continue
        return found

    def _find_products(self, data, depth=0):
        if depth > 6:
            return []
        if isinstance(data, list):
            if data and isinstance(data[0], dict) and any(k in data[0] for k in ("name", "title", "price")):
                return data
            for item in data:
                result = self._find_products(item, depth + 1)
                if result:
                    return result
        elif isinstance(data, dict):
            for key in ("products", "items", "results", "data"):
                if key in data:
                    result = self._find_products(data[key], depth + 1)
                    if result:
                        return result
        return []
