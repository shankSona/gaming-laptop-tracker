import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.poorvika.com/laptops/asus?q=tuf"),
    ("ASUS",   "ROG",       "https://www.poorvika.com/laptops/asus?q=rog"),
    ("Lenovo", "LOQ",       "https://www.poorvika.com/laptops/lenovo?q=loq"),
    ("Lenovo", "Legion",    "https://www.poorvika.com/laptops/lenovo?q=legion"),
    ("HP",     "Victus",    "https://www.poorvika.com/laptops/hp?q=victus"),
    ("HP",     "Omen",      "https://www.poorvika.com/laptops/hp?q=omen"),
    ("Dell",   "G15",       "https://www.poorvika.com/laptops/dell?q=g15"),
    ("Dell",   "Alienware", "https://www.poorvika.com/laptops/dell?q=alienware"),
]

PV_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.poorvika.com/",
}


class PoorvikaScraper(BaseScraper):
    name = "Poorvika"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                resp = self.get(url, extra_headers=PV_HEADERS)
                soup = BeautifulSoup(resp.text, "lxml")

                items = (
                    soup.select(".product-box") or
                    soup.select(".product-item") or
                    soup.select(".grid-item") or
                    soup.select("[class*='product']") or
                    soup.select(".col-product")
                )

                for item in items[:6]:
                    try:
                        name_el = (
                            item.select_one(".product-name") or
                            item.select_one("h2") or
                            item.select_one("h3") or
                            item.select_one(".item-title") or
                            item.select_one("[class*='name']") or
                            item.select_one("[class*='title']")
                        )
                        price_el = (
                            item.select_one(".offer-price") or
                            item.select_one(".price") or
                            item.select_one("[class*='offer']") or
                            item.select_one("[class*='price']")
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

                        link_el = item.select_one("a[href]")
                        product_url = url
                        if link_el:
                            href = link_el.get("href", "")
                            product_url = href if href.startswith("http") else f"https://www.poorvika.com{href}"

                        model_id = f"PVK-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
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
                            in_stock=True,
                            vendor_name="poorvika.com",         # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Poorvika {brand} {series} error: {e}")

        return results
