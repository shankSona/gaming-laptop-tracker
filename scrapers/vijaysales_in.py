import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.vijaysales.com/search/asus-tuf-gaming-laptop"),
    ("ASUS",   "ROG",       "https://www.vijaysales.com/search/asus-rog-laptop"),
    ("Lenovo", "LOQ",       "https://www.vijaysales.com/search/lenovo-loq-gaming"),
    ("Lenovo", "Legion",    "https://www.vijaysales.com/search/lenovo-legion-laptop"),
    ("HP",     "Victus",    "https://www.vijaysales.com/search/hp-victus-gaming"),
    ("HP",     "Omen",      "https://www.vijaysales.com/search/hp-omen-laptop"),
    ("Dell",   "G15",       "https://www.vijaysales.com/search/dell-g15-gaming"),
    ("Dell",   "Alienware", "https://www.vijaysales.com/search/dell-alienware"),
]

class VijaysSalesScraper(BaseScraper):
    name = "Vijay Sales"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                items = soup.select(".product-box, .product-item, [class*='productBox']")
                for item in items[:5]:
                    try:
                        name_el = item.select_one(".product-name, h3, .prdct-nm")
                        price_el = item.select_one(".price, .special-price, [class*='price']")
                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if series.lower() not in name.lower():
                            continue
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))
                        model_id = f"VS-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"

                        results.append(LaptopListing(
                            model_id=model_id, brand=brand, series=series,
                            model_name=name[:120],
                            cpu="See listing", gpu="See listing",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=True,
                            source_site="vijaysales.com",
                            source_url=url,
                        ))
                    except Exception:
                        continue
            except Exception as e:
                print(f"Vijay Sales {brand} {series} error: {e}")
        return results
