import requests, time, random
from dataclasses import dataclass
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

@dataclass
class LaptopListing:
    model_id: str
    brand: str
    series: str
    model_name: str
    cpu: str
    gpu: str
    ram_gb: int
    storage_gb: int
    display_inches: float
    refresh_hz: int
    weight_kg: float
    price_inr: float
    in_stock: bool
    source_site: str
    source_url: str
    recorded_at: datetime = None

    def __post_init__(self):
        if not self.recorded_at:
            self.recorded_at = datetime.utcnow()

class BaseScraper:
    name = "Base"
    def get(self, url, **kwargs):
        time.sleep(random.uniform(1.5, 3.5))  # polite delay
        r = requests.get(url, headers=HEADERS, timeout=20, **kwargs)
        r.raise_for_status()
        return r
    def scrape(self) -> list[LaptopListing]:
        raise NotImplementedError
