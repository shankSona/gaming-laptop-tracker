import re
import json
from bs4 import BeautifulSoup
from .base import BaseScraper, LaptopListing, BROWSER_HEADERS

# HP India uses Akamai WAF which blocks data-center IPs (GitHub Actions = 403).
# We try multiple URL patterns including their JSON API as fallback.
# If all return 0, HP data will be missing until a residential IP or proxy is used.

HP_SEARCHES = [
    # (series, listing_url, fallback_api_url)
    ("Victus", "https://www.hp.com/in-en/shop/pdpproducts/v2/pl?cc=in&lc=en&segment=Consumer&productTypeId=gamingLaptop&series=Victus"),
    ("Omen",   "https://www.hp.com/in-en/shop/pdpproducts/v2/pl?cc=in&lc=en&segment=Consumer&productTypeId=gamingLaptop&series=Omen"),
]

HP_HTML_URLS = {
    "Victus": "https://www.hp.com/in-en/gaming/victus-laptop.html",
    "Omen":   "https://www.hp.com/in-en/omen/laptops.html",
}

HP_JSON_HEADERS = {
    **BROWSER_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.hp.com/in-en/shop/laptops/gaming-laptops.html",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}


class HPIndiaScraper(BaseScraper):
    name = "HP India"

    def scrape(self):
        results = []

        for series, api_url in HP_SEARCHES:
            # Try JSON API first (more reliable than HTML scraping)
            try:
                resp = self.session.get(api_url, headers=HP_JSON_HEADERS, timeout=25)
                resp.raise_for_status()
                data = resp.json()
                products = data.get("products", data.get("items", []))
                for p in products[:8]:
                    try:
                        name = p.get("name", p.get("productName", ""))
                        price = float(p.get("price", {}).get("value", 0) or
                                      p.get("salePrice", 0) or
                                      p.get("listPrice", 0))
                        if not name or price < 30000:
                            continue
                        sku = p.get("sku", p.get("partNumber", name[:10]))
                        model_id = f"HP-{series.upper()}-{re.sub(r'[^A-Z0-9]', '', sku.upper())[:15]}"
                        pdp_url = p.get("url", HP_HTML_URLS[series])
                        if pdp_url and not pdp_url.startswith("http"):
                            pdp_url = f"https://www.hp.com{pdp_url}"

                        results.append(LaptopListing(
                            model_id=model_id,
                            brand="HP",
                            series=series,
                            model_name=name[:120],
                            cpu=p.get("processor", "See site"),
                            gpu=p.get("graphics", "See site"),
                            ram_gb=int(re.search(r"(\d+)\s*GB", p.get("memory", "16GB")) .group(1) if re.search(r"(\d+)\s*GB", p.get("memory", "16GB")) else 16),
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.4,
                            price_inr=price,
                            in_stock=p.get("inStock", True),
                            vendor_name="hp.com/in",            # ← FIXED (was source_site=)
                            source_url=pdp_url,
                        ))
                    except Exception:
                        continue

                if results:
                    continue  # JSON worked, skip HTML fallback

            except Exception as e:
                print(f"HP {series} JSON API error: {e}")

            # HTML fallback
            html_url = HP_HTML_URLS[series]
            try:
                resp = self.get(html_url, extra_headers={"Referer": "https://www.hp.com/in-en/"})
                soup = BeautifulSoup(resp.text, "lxml")

                # HP product cards (may vary by page)
                cards = (
                    soup.select(".product-card") or
                    soup.select("[data-sku]") or
                    soup.select(".pv-wrapper") or
                    soup.select(".pdp-tile")
                )

                for card in cards:
                    try:
                        name_el = card.select_one(".product-name, h3, .pdp-tile-title, [class*='name']")
                        price_el = card.select_one(".price, [data-price], [class*='price']")
                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        price_text = re.sub(r"[^\d]", "", price_el.get_text())
                        if not price_text:
                            continue
                        price = float(price_text)
                        if price < 30000 or price > 500000:
                            continue

                        model_id = f"HP-{series.upper()}-{re.sub(r'[^A-Z0-9]', '', name.upper())[:15]}"
                        results.append(LaptopListing(
                            model_id=model_id,
                            brand="HP",
                            series=series,
                            model_name=name[:120],
                            cpu="See site",
                            gpu="See site",
                            ram_gb=16,
                            storage_gb=512,
                            display_inches=15.6,
                            refresh_hz=144,
                            weight_kg=2.4,
                            price_inr=price,
                            in_stock="out-of-stock" not in " ".join(card.get("class", [])),
                            vendor_name="hp.com/in",
                            source_url=html_url,
                        ))
                    except Exception:
                        continue

            except Exception as e:
                print(f"HP {series} error: {e}")

        return results
