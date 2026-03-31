import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.croma.com/searchB?q=asus+tuf+gaming+laptop"),
    ("ASUS",   "ROG",       "https://www.croma.com/searchB?q=asus+rog+laptop"),
    ("Lenovo", "LOQ",       "https://www.croma.com/searchB?q=lenovo+loq+gaming"),
    ("Lenovo", "Legion",    "https://www.croma.com/searchB?q=lenovo+legion+laptop"),
    ("HP",     "Victus",    "https://www.croma.com/searchB?q=hp+victus+gaming+laptop"),
    ("HP",     "Omen",      "https://www.croma.com/searchB?q=hp+omen+laptop"),
    ("Dell",   "G15",       "https://www.croma.com/searchB?q=dell+g15+gaming"),
    ("Dell",   "Alienware", "https://www.croma.com/searchB?q=dell+alienware"),
]

class CromaScraper(BaseScraper):
    name = "Croma"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                items = soup.select("li.product-item, [class*='product']")
                for item in items[:5]:
                    try:
                        name_el = item.select_one("h3.product-title, .product-name, h2")
                        price_el = item.select_one("[class*='amount'], [class*='price']")
                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if series.lower() not in name.lower():
                            continue
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))
                        out_of_stock = bool(item.select_one("[class*='out-of-stock'], [class*='unavailable']"))
                        model_id = f"CRM-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"

                        results.append(LaptopListing(
                            model_id=model_id, brand=brand, series=series,
                            model_name=name[:120],
                            cpu="See listing", gpu="See listing",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=not out_of_stock,
                            source_site="croma.com",
                            source_url=url,
                        ))
                    except Exception:
                        continue
            except Exception as e:
                print(f"Croma {brand} {series} error: {e}")
        return results
