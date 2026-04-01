import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

# FIXED: Was /search/keyword (404). Correct format is catalogsearch/result/
SEARCHES = [
    ("ASUS",   "TUF",       "https://www.vijaysales.com/catalogsearch/result/?q=asus+tuf+gaming+laptop"),
    ("ASUS",   "ROG",       "https://www.vijaysales.com/catalogsearch/result/?q=asus+rog+laptop"),
    ("Lenovo", "LOQ",       "https://www.vijaysales.com/catalogsearch/result/?q=lenovo+loq+gaming"),
    ("Lenovo", "Legion",    "https://www.vijaysales.com/catalogsearch/result/?q=lenovo+legion+laptop"),
    ("HP",     "Victus",    "https://www.vijaysales.com/catalogsearch/result/?q=hp+victus+gaming"),
    ("HP",     "Omen",      "https://www.vijaysales.com/catalogsearch/result/?q=hp+omen+laptop"),
    ("Dell",   "G15",       "https://www.vijaysales.com/catalogsearch/result/?q=dell+g15+gaming"),
    ("Dell",   "Alienware", "https://www.vijaysales.com/catalogsearch/result/?q=dell+alienware"),
]

VS_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.vijaysales.com/",
}


class VijaysSalesScraper(BaseScraper):
    name = "Vijay Sales"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                resp = self.get(url, extra_headers=VS_HEADERS)
                soup = BeautifulSoup(resp.text, "lxml")

                items = (
                    soup.select(".product-item") or
                    soup.select(".item.product") or
                    soup.select("[class*='productBox']") or
                    soup.select(".product-box") or
                    soup.select("li.item")
                )

                for item in items[:6]:
                    try:
                        name_el = (
                            item.select_one(".product-item-name") or
                            item.select_one(".product-name") or
                            item.select_one("h2.product-name") or
                            item.select_one(".prdct-nm") or
                            item.select_one("strong.product-item-name")
                        )
                        price_el = (
                            item.select_one(".price") or
                            item.select_one(".special-price .price") or
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

                        link_el = item.select_one("a.product-item-link, a[href*='laptop']")
                        product_url = link_el["href"] if link_el else url

                        model_id = f"VS-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
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
                            in_stock=not bool(item.select_one("[class*='out-of-stock']")),
                            vendor_name="vijaysales.com",       # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Vijay Sales {brand} {series} error: {e}")

        return results
