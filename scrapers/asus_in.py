import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

URLS = {
    "TUF": "https://www.asus.com/in/laptops/for-gaming/tuf-gaming/",
    # FIXED: was /in/laptops/ (404). Correct URL is /in/laptops/all-series/
    "ROG": "https://rog.asus.com/in/laptops/all-series/",
}

ASUS_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.asus.com/in/",
}


class ASUSIndiaScraper(BaseScraper):
    name = "ASUS India"

    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                resp = self.get(url, extra_headers=ASUS_HEADERS)
                soup = BeautifulSoup(resp.text, "lxml")

                # ASUS uses multiple possible card class names
                cards = (
                    soup.select(".product-item") or
                    soup.select("[class*='ProductItem']") or
                    soup.select(".rog-product-card") or
                    soup.select("[class*='product-card']") or
                    soup.select("li.product")
                )

                for card in cards:
                    try:
                        name_el = (
                            card.select_one("h3") or
                            card.select_one(".prod-name") or
                            card.select_one(".product-title") or
                            card.select_one("[class*='title']") or
                            card.select_one("[class*='name']")
                        )
                        price_el = (
                            card.select_one(".price") or
                            card.select_one("[class*='price']") or
                            card.select_one("[class*='Price']")
                        )
                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        if not name or len(name) < 5:
                            continue

                        price_text = re.sub(r"[^\d]", "", price_el.get_text())
                        if not price_text:
                            continue
                        price = float(price_text)
                        if price < 30000 or price > 600000:
                            continue

                        # Get product link
                        link_el = card.select_one("a[href]")
                        product_url = url
                        if link_el:
                            href = link_el.get("href", "")
                            product_url = href if href.startswith("http") else f"https://rog.asus.com{href}"

                        model_id = f"ASUS-{series}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id,
                            brand="ASUS",
                            series=series,
                            model_name=name[:120],
                            cpu="See site",
                            gpu="See site",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.2,
                            price_inr=price,
                            in_stock=True,
                            vendor_name="asus.com/in",          # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"ASUS {series} error: {e}")

        return results
