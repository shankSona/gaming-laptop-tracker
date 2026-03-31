import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

URLS = {
    "LOQ":    "https://www.lenovo.com/in/en/laptops/loq-laptops/",
    "Legion": "https://www.lenovo.com/in/en/laptops/legion-laptops/",
}

class LenovoIndiaScraper(BaseScraper):
    name = "Lenovo India"

    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                cards = soup.select(".product-item, [data-product-id]")
                for card in cards:
                    try:
                        name_el = card.select_one(".product-title, h3, .item-title")
                        price_el = card.select_one(".price, .product-price")
                        if not name_el or not price_el: continue

                        name = name_el.get_text(strip=True)
                        price = float(re.sub(r"[^\d.]", "", price_el.get_text()))

                        model_id = f"LEN-{series.upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:12]}"
                        in_stock = bool(card.select_one(".add-to-cart, .btn-cart"))

                        results.append(LaptopListing(
                            model_id=model_id, brand="Lenovo", series=series,
                            model_name=name,
                            cpu="See site", gpu="See site",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.4,
                            price_inr=price, in_stock=in_stock,
                            source_site="lenovo.com/in",
                            source_url=url,
                        ))
                    except Exception: continue
            except Exception as e:
                print(f"Lenovo {series} error: {e}")
        return results
