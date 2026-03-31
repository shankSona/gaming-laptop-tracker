import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

URLS = {
    "G15":       "https://www.dell.com/en-in/cat/laptops/gaming-laptops",
    "Alienware": "https://www.dell.com/en-in/cat/laptops/alienware-laptops",
}

class DellIndiaScraper(BaseScraper):
    name = "Dell India"
    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                cards = soup.select(".ps-top-wrapper, .product-card")
                for card in cards:
                    try:
                        name_el = card.select_one(".ps-name, h3")
                        price_el = card.select_one(".ps-price, .price")
                        if not name_el or not price_el: continue
                        name = name_el.get_text(strip=True)
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))
                        model_id = f"DEL-{series[:3].upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id, brand="Dell", series=series,
                            model_name=name, cpu="See site", gpu="See site",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=120,
                            weight_kg=2.8,
                            price_inr=price, in_stock=True,
                            source_site="dell.com/in", source_url=url,
                        ))
                    except Exception: continue
            except Exception as e:
                print(f"Dell {series} error: {e}")
        return results
