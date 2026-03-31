import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

TARGET_SERIES = ["victus", "omen"]

URLS = {
    "victus": "https://www.hp.com/in-en/shop/laptops/gaming-laptops/victus-laptops.html",
    "omen":   "https://www.hp.com/in-en/shop/laptops/gaming-laptops/omen-laptops.html",
}

class HPIndiaScraper(BaseScraper):
    name = "HP India"

    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                # HP uses product cards with class 'product-card'
                cards = soup.select(".product-card, [data-sku]")
                for card in cards:
                    try:
                        name_el = card.select_one(".product-name, h3")
                        price_el = card.select_one(".price, [data-price]")
                        if not name_el or not price_el: continue

                        name = name_el.get_text(strip=True)
                        price_text = price_el.get_text(strip=True)
                        price = float(re.sub(r"[^\d.]", "", price_text))

                        in_stock = "out-of-stock" not in card.get("class", [])
                        model_id = f"HP-{series.upper()}-{re.sub(r'[^A-Z0-9]','',name.upper())[:15]}"

                        results.append(LaptopListing(
                            model_id=model_id,
                            brand="HP", series=series.capitalize(),
                            model_name=name,
                            cpu=self._extract(card, "processor"),
                            gpu=self._extract(card, "graphics"),
                            ram_gb=self._extract_num(card, "memory"),
                            storage_gb=self._extract_num(card, "storage"),
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.4,
                            price_inr=price, in_stock=in_stock,
                            source_site="hp.com/in",
                            source_url=url,
                        ))
                    except Exception: continue
            except Exception as e:
                print(f"HP {series} error: {e}")
        return results

    def _extract(self, card, keyword):
        el = card.find(string=re.compile(keyword, re.I))
        return el.strip() if el else "See site"

    def _extract_num(self, card, keyword):
        el = card.find(string=re.compile(keyword, re.I))
        if el:
            nums = re.findall(r"\d+", el)
            return int(nums[0]) if nums else 0
        return 0
