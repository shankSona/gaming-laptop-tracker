import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.flipkart.com/search?q=asus+tuf+gaming+laptop&otracker=search"),
    ("ASUS",   "ROG",       "https://www.flipkart.com/search?q=asus+rog+gaming+laptop"),
    ("Lenovo", "LOQ",       "https://www.flipkart.com/search?q=lenovo+loq+gaming+laptop"),
    ("Lenovo", "Legion",    "https://www.flipkart.com/search?q=lenovo+legion+laptop"),
    ("HP",     "Victus",    "https://www.flipkart.com/search?q=hp+victus+gaming+laptop"),
    ("HP",     "Omen",      "https://www.flipkart.com/search?q=hp+omen+laptop"),
    ("Dell",   "G15",       "https://www.flipkart.com/search?q=dell+g15+gaming+laptop"),
    ("Dell",   "Alienware", "https://www.flipkart.com/search?q=dell+alienware+laptop"),
]

class FlipkartScraper(BaseScraper):
    name = "Flipkart"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                # Flipkart product containers
                items = soup.select("div[data-id], ._1AtVbE")
                for item in items[:5]:
                    try:
                        name_el = item.select_one("._4rR01T, .s1Q9rs, .IRpwTa")
                        price_el = item.select_one("._30jeq3, ._16Jk6d")
                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if series.lower() not in name.lower():
                            continue
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))
                        out_of_stock = bool(item.select_one("._2AkmmA, ._1lACP4"))
                        pid = item.get("data-id", name[:10])
                        model_id = f"FK-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"

                        results.append(LaptopListing(
                            model_id=model_id, brand=brand, series=series,
                            model_name=name[:120],
                            cpu="See listing", gpu="See listing",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=not out_of_stock,
                            source_site="flipkart.com",
                            source_url=url,
                        ))
                    except Exception:
                        continue
            except Exception as e:
                print(f"Flipkart {brand} {series} error: {e}")
        return results
