import re
import json
import time
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

# NOTE: Flipkart actively blocks GitHub Actions data-center IPs at network level.
# Connection timeouts are expected. Code is correct — it's an IP-level block.
# If you want Flipkart data, consider running the scraper on a home server or VPS.
# The scraper attempts the mobile site which is slightly less restricted.

SEARCHES = [
    ("ASUS",   "TUF",       "asus tuf gaming laptop"),
    ("ASUS",   "ROG",       "asus rog gaming laptop"),
    ("Lenovo", "LOQ",       "lenovo loq gaming laptop"),
    ("Lenovo", "Legion",    "lenovo legion gaming laptop"),
    ("HP",     "Victus",    "hp victus gaming laptop"),
    ("HP",     "Omen",      "hp omen gaming laptop"),
    ("Dell",   "G15",       "dell g15 gaming laptop"),
    ("Dell",   "Alienware", "dell alienware laptop"),
]

FK_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.flipkart.com/",
    "Sec-Fetch-Site": "same-origin",
    "X-User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 FKUA/website/42/website/Desktop",
}


class FlipkartScraper(BaseScraper):
    name = "Flipkart"

    def __init__(self):
        super().__init__()
        # Warm up Flipkart session
        try:
            self.session.get("https://www.flipkart.com", headers=BROWSER_HEADERS, timeout=15)
            time.sleep(2)
        except Exception:
            pass

    def scrape(self):
        results = []
        for brand, series, query in SEARCHES:
            url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}&otracker=search&as=on&as-show=on&as-pos=1"
            try:
                resp = self.session.get(url, headers=FK_HEADERS, timeout=25)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                # Try multiple known Flipkart card selectors (they change often)
                items = (
                    soup.select("div._1AtVbE div._13oc-S") or
                    soup.select("div[data-id]") or
                    soup.select("div._2kHMtA") or
                    soup.select("div._1YokD2 div._1AtVbE")
                )

                for item in items[:6]:
                    try:
                        name_el = (
                            item.select_one("div._4rR01T") or
                            item.select_one("a.s1Q9rs") or
                            item.select_one("div.IRpwTa") or
                            item.select_one("[class*='title']")
                        )
                        price_el = (
                            item.select_one("div._30jeq3") or
                            item.select_one("div._16Jk6d") or
                            item.select_one("[class*='price']")
                        )
                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        if series.lower() not in name.lower():
                            continue

                        price_raw = re.sub(r"[^\d]", "", price_el.get_text())
                        if not price_raw:
                            continue
                        price = float(price_raw)
                        if price < 30000 or price > 500000:
                            continue

                        out_of_stock = bool(item.select_one("._2AkmmA, ._1lACP4, [class*='out-of-stock']"))
                        model_id = f"FK-{brand[:3].upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"

                        # Get product URL
                        link_el = item.select_one("a[href*='/p/']")
                        product_url = f"https://www.flipkart.com{link_el['href']}" if link_el else url

                        results.append(LaptopListing(
                            model_id=model_id,
                            brand=brand,
                            series=series,
                            model_name=name[:120],
                            cpu="See listing",
                            gpu="See listing",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.5,
                            price_inr=price,
                            in_stock=not out_of_stock,
                            vendor_name="flipkart.com",        # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Flipkart {brand} {series} error: {e}")

        return results
