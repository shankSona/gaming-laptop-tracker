import re
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

# Dell India uses React — most product data is JS-rendered.
# requests+BeautifulSoup will get the page shell but rarely product cards.
# These URLs are the closest to static content Dell exposes.

URLS = {
    "G15":       "https://www.dell.com/en-in/shop/gaming/sr/laptops/gaming",
    "Alienware": "https://www.dell.com/en-in/shop/alienware/sr/alienware",
}

DELL_HEADERS = {
    **BROWSER_HEADERS,
    "Referer": "https://www.dell.com/en-in/",
    "Sec-Fetch-Site": "same-origin",
}


class DellIndiaScraper(BaseScraper):
    name = "Dell India"

    def scrape(self):
        results = []
        for series, url in URLS.items():
            try:
                resp = self.get(url, extra_headers=DELL_HEADERS)
                soup = BeautifulSoup(resp.text, "lxml")

                # Dell product cards — try multiple selectors
                cards = (
                    soup.select(".ps-top-wrapper") or
                    soup.select(".product-card") or
                    soup.select("[data-testid='product-card']") or
                    soup.select(".stack") or
                    soup.select("article.product")
                )

                for card in cards:
                    try:
                        name_el = (
                            card.select_one(".ps-name") or
                            card.select_one("h3") or
                            card.select_one("[class*='name']") or
                            card.select_one("[class*='title']")
                        )
                        price_el = (
                            card.select_one(".ps-price") or
                            card.select_one(".price") or
                            card.select_one("[class*='price']")
                        )
                        if not name_el or not price_el:
                            continue

                        name = name_el.get_text(strip=True)
                        price_text = re.sub(r"[^\d]", "", price_el.get_text())
                        if not price_text:
                            continue
                        price = float(price_text)
                        if price < 50000 or price > 700000:
                            continue

                        link_el = card.select_one("a[href*='/p/']")
                        product_url = url
                        if link_el:
                            href = link_el.get("href", "")
                            product_url = href if href.startswith("http") else f"https://www.dell.com{href}"

                        model_id = f"DEL-{series[:3].upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:12]}"
                        results.append(LaptopListing(
                            model_id=model_id,
                            brand="Dell",
                            series=series,
                            model_name=name[:120],
                            cpu="See site",
                            gpu="See site",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=120,
                            weight_kg=2.8,
                            price_inr=price,
                            in_stock=True,
                            vendor_name="dell.com/in",          # ← FIXED (was source_site=)
                            source_url=product_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"Dell {series} error: {e}")

        return results
