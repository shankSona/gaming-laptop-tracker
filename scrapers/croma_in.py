import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.croma.com/searchB?q=asus+tuf+gaming+laptop&sortBy=&sortOrder="),
    ("ASUS",   "ROG",       "https://www.croma.com/searchB?q=asus+rog+laptop&sortBy=&sortOrder="),
    ("Lenovo", "LOQ",       "https://www.croma.com/searchB?q=lenovo+loq+gaming&sortBy=&sortOrder="),
    ("Lenovo", "Legion",    "https://www.croma.com/searchB?q=lenovo+legion+laptop&sortBy=&sortOrder="),
    ("HP",     "Victus",    "https://www.croma.com/searchB?q=hp+victus+gaming+laptop&sortBy=&sortOrder="),
    ("HP",     "Omen",      "https://www.croma.com/searchB?q=hp+omen+laptop&sortBy=&sortOrder="),
    ("Dell",   "G15",       "https://www.croma.com/searchB?q=dell+g15+gaming&sortBy=&sortOrder="),
    ("Dell",   "Alienware", "https://www.croma.com/searchB?q=dell+alienware&sortBy=&sortOrder="),
]

CROMA_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.croma.com/",
}


class CromaScraper(BaseScraper):
    name = "Croma"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                resp = self.get(url, extra_headers=CROMA_HEADERS)
                soup = BeautifulSoup(resp.text, "lxml")

                # Croma uses React — try to find SSR JSON first
                json_found = self._try_ssr_json(soup, brand, series, url, results)
                if json_found:
                    continue

                # HTML fallback with updated selectors
                items = (
                    soup.select("li.product-item") or
                    soup.select("[class*='product-item']") or
                    soup.select("div.plp-card-details-container") or
                    soup.select("[class*='plp-card']") or
                    soup.select("[class*='ProductCard']")
                )

                for item in items[:6]:
                    try:
                        name_el = (
                            item.select_one("h3.product-title") or
                            item.select_one(".product-name") or
                            item.select_one("h3") or
                            item.select_one("[class*='title']") or
                            item.select_one("[class*='name']")
                        )
                        price_el = (
                            item.select_one("[class*='amount']") or
                            item.select_one("[class*='price']") or
                            item.select_one(".pdp-price")
                        )
                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        if series.lower() not in name.lower():
                            continue

                        price_text = re.sub(r"[^\d]", "", price_el.get_text())
                        if not price_text:
                            continue
                        price = float(price_text)
                        if price < 30000 or price > 500000:
                            continue

                        link_el = item.select_one("a[href*='laptop']")
                        product_url = url
                        if link_el:
                            href = link_el.get("href", "")
                            product_url = href if href.startswith("http") else f"https://www.croma.com{href}"

                        out_of_stock = bool(item.select_one("[class*='out-of-stock'], [class*='unavailable']"))
                        model_id = f"CRM-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"

                        results.append(LaptopListing(
                            model_id=model_id,
                            brand=brand,
                            series=series,
                            model_name=name[:120],
                            cpu="See listing",
                            gpu="See listing",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=not out_of_stock,
                            vendor_name="croma.com",            # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Croma {brand} {series} error: {e}")

        return results

    def _try_ssr_json(self, soup, brand, series, url, results) -> bool:
        import json
        for script in soup.select("script"):
            text = script.string or ""
            if "products" not in text and "price" not in text:
                continue
            try:
                # Look for JSON blobs embedded in script tags
                matches = re.findall(r'\{["\']products["\']:\s*\[.*?\]\}', text, re.DOTALL)
                for match in matches[:2]:
                    data = json.loads(match)
                    for p in data.get("products", [])[:8]:
                        name = p.get("name", p.get("productName", ""))
                        price = float(p.get("offerPrice", p.get("price", 0)))
                        if not name or price < 30000:
                            continue
                        if series.lower() not in name.lower():
                            continue
                        model_id = f"CRM-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id, brand=brand, series=series,
                            model_name=name[:120], cpu="See listing", gpu="See listing",
                            ram_gb=16, storage_gb=512, display_inches=15.6,
                            refresh_hz=144, weight_kg=2.5, price_inr=price,
                            in_stock=True, vendor_name="croma.com", source_url=url,
                        ))
                        return True
            except Exception:
                continue
        return False
