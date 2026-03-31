import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

URLS = {
    "TUF": "https://www.asus.com/in/laptops/for-gaming/tuf-gaming/",
    "ROG": "https://rog.asus.com/in/laptops/",
}

class ASUSIndiaScraper(BaseScraper):
    name = "ASUS India"
    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                cards = soup.select(".product-item, [class*='product']")
                for card in cards:
                    try:
                        name_el = card.select_one("h3, .prod-name, .product-title")
                        price_el = card.select_one(".price, [class*='price']")
                        if not name_el or not price_el: continue
                        name = name_el.get_text(strip=True)
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))
                        model_id = f"ASUS-{series}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id, brand="ASUS", series=series,
                            model_name=name, cpu="See site", gpu="See site",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.2,
                            price_inr=price, in_stock=True,
                            source_site=f"asus.com/in {'(ROG)' if series=='ROG' else ''}",
                            source_url=url,
                        ))
                    except Exception: continue
            except Exception as e:
                print(f"ASUS {series} error: {e}")
        return results
