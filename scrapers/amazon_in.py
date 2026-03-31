import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing

# Search URLs — Amazon India gaming laptops by brand
SEARCHES = [
    ("ASUS", "TUF",      "https://www.amazon.in/s?k=ASUS+TUF+gaming+laptop&rh=n%3A1375424031"),
    ("ASUS", "ROG",      "https://www.amazon.in/s?k=ASUS+ROG+gaming+laptop"),
    ("Lenovo","LOQ",     "https://www.amazon.in/s?k=Lenovo+LOQ+gaming+laptop"),
    ("Lenovo","Legion",  "https://www.amazon.in/s?k=Lenovo+Legion+laptop"),
    ("HP",   "Victus",   "https://www.amazon.in/s?k=HP+Victus+gaming+laptop"),
    ("HP",   "Omen",     "https://www.amazon.in/s?k=HP+Omen+laptop"),
    ("Dell", "G15",      "https://www.amazon.in/s?k=Dell+G15+gaming+laptop"),
    ("Dell", "Alienware","https://www.amazon.in/s?k=Dell+Alienware+laptop"),
]

class AmazonIndiaScraper(BaseScraper):
    name = "Amazon India"

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                soup = BeautifulSoup(self.get(url).text, "lxml")
                items = soup.select('[data-component-type="s-search-result"]')
                for item in items[:5]:  # top 5 per search
                    try:
                        title_el = item.select_one("h2 span")
                        price_el = item.select_one(".a-price-whole")
                        if not title_el or not price_el: continue

                        title = title_el.get_text(strip=True)
                        # Filter only target series
                        if series.lower() not in title.lower(): continue

                        price = float(price_el.get_text(strip=True).replace(",",""))
                        in_stock = not bool(item.select_one(".a-color-price"))
                        asin = item.get("data-asin","")
                        model_id = f"AMZ-{brand[:3].upper()}-{asin}"

                        results.append(LaptopListing(
                            model_id=model_id, brand=brand, series=series,
                            model_name=title[:120],
                            cpu="See listing", gpu="See listing",
                            ram_gb=16, storage_gb=512,
                            display_inches=15.6, refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price, in_stock=in_stock,
                            source_site="amazon.in",
                            source_url=f"https://amazon.in/dp/{asin}",
                        ))
                    except Exception: continue
            except Exception as e:
                print(f"Amazon {brand} {series} error: {e}")
        return results
