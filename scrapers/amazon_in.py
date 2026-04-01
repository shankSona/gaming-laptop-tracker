import re
import time
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

SEARCHES = [
    ("ASUS",   "TUF",       "https://www.amazon.in/s?k=ASUS+TUF+gaming+laptop&rh=n%3A1375424031"),
    ("ASUS",   "ROG",       "https://www.amazon.in/s?k=ASUS+ROG+gaming+laptop&rh=n%3A1375424031"),
    ("Lenovo", "LOQ",       "https://www.amazon.in/s?k=Lenovo+LOQ+gaming+laptop&rh=n%3A1375424031"),
    ("Lenovo", "Legion",    "https://www.amazon.in/s?k=Lenovo+Legion+gaming+laptop&rh=n%3A1375424031"),
    ("HP",     "Victus",    "https://www.amazon.in/s?k=HP+Victus+gaming+laptop&rh=n%3A1375424031"),
    ("HP",     "Omen",      "https://www.amazon.in/s?k=HP+Omen+gaming+laptop&rh=n%3A1375424031"),
    ("Dell",   "G15",       "https://www.amazon.in/s?k=Dell+G15+gaming+laptop&rh=n%3A1375424031"),
    ("Dell",   "Alienware", "https://www.amazon.in/s?k=Dell+Alienware+laptop&rh=n%3A1375424031"),
]

AMAZON_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.amazon.in/",
    "Sec-Fetch-Site": "same-origin",
}


class AmazonIndiaScraper(BaseScraper):
    name = "Amazon India"

    def __init__(self):
        super().__init__()
        # Warm up session: visit homepage first to get cookies
        # This significantly improves success rate vs cold requests
        try:
            self.session.get(
                "https://www.amazon.in",
                headers=BROWSER_HEADERS,
                timeout=20,
            )
            time.sleep(2)
        except Exception:
            pass  # If homepage fails, still try searches

    def scrape(self):
        results = []
        for brand, series, url in SEARCHES:
            try:
                resp = self.session.get(url, headers=AMAZON_HEADERS, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                items = soup.select('[data-component-type="s-search-result"]')
                for item in items[:6]:
                    try:
                        title_el = item.select_one("h2 span")
                        price_el = item.select_one(".a-price-whole")
                        if not title_el or not price_el:
                            continue

                        title = title_el.get_text(strip=True)
                        if series.lower() not in title.lower():
                            continue

                        price_text = price_el.get_text(strip=True).replace(",", "").replace(".", "")
                        if not price_text.isdigit():
                            continue
                        price = float(price_text)
                        if price < 30000 or price > 500000:
                            continue  # sanity check

                        asin = item.get("data-asin", "")
                        if not asin:
                            continue

                        # Check stock status
                        in_stock = not bool(
                            item.select_one('[aria-label*="Currently unavailable"]') or
                            item.select_one(".a-color-price:-soup-contains('Currently unavailable')")
                        )

                        model_id = f"AMZ-{brand[:3].upper()}-{asin}"

                        results.append(LaptopListing(
                            model_id=model_id,
                            brand=brand,
                            series=series,
                            model_name=title[:120],
                            cpu="See listing",
                            gpu="See listing",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=in_stock,
                            vendor_name="amazon.in",          # ← FIXED (was source_site=)
                            source_url=f"https://www.amazon.in/dp/{asin}",
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Amazon {brand} {series} error: {e}")

        return results
