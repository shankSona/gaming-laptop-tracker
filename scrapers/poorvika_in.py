import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.poorvika.com/laptop?q=asus+tuf+gaming"),
    ("ASUS",   "ROG",       "https://www.poorvika.com/laptop?q=asus+rog"),
    ("Lenovo", "LOQ",       "https://www.poorvika.com/laptop?q=lenovo+loq"),
    ("Lenovo", "Legion",    "https://www.poorvika.com/laptop?q=lenovo+legion"),
    ("HP",     "Victus",    "https://www.poorvika.com/laptop?q=hp+victus"),
    ("HP",     "Omen",      "https://www.poorvika.com/laptop?q=hp+omen"),
    ("Dell",   "G15",       "https://www.poorvika.com/laptop?q=dell+g15"),
    ("Dell",   "Alienware", "https://www.poorvika.com/laptop?q=dell+alienware"),
]

class PoorvikaScraper(BaseScraper):
    name = "Poorvika"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                items = soup.select(".product-item, .grid-item, [class*='product']")
                for item in items[:5]:
                    try:
                        name_el = item.select_one(".product-name, h2, h3, .item-title")
                        price_el = item.select_one(".price, .offer-price, [class*='price']")
                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if series.lower() not in name.lower():
                            continue
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))
                        model_id = f"PVK-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"

                        results.append(LaptopListing(
                            model_id=model_id, brand=brand, series=series,
                            model_name=name[:120],
                            cpu="See listing", gpu="See listing",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=True,
                            source_site="poorvika.com",
                            source_url=url,
                        ))
                    except Exception:
                        continue
            except Exception as e:
                print(f"Poorvika {brand} {series} error: {e}")
        return results
