import cloudscraper
import time
import random
import requests
from dataclasses import dataclass
from datetime import datetime


# ── BROWSER HEADERS ──────────────────────────────────────────
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "DNT": "1",
}

# ── MINIMUM REQUIREMENTS FILTER ─────────────────────────────
MIN_REQUIREMENTS = {
    "cpu_gen":      13,
    "cpu_tier":     "HX",
    "ram_gb":       16,
    "ram_type":     "DDR5",
    "gpu_vram_gb":  6,
    "storage_gb":   512,
}

GPU_TIER_MAP = {
    "RTX 4050": 1, "RTX 4060": 2, "RTX 4070": 3,
    "RTX 4080": 4, "RTX 4090": 5,
}

def compute_spec_score(gpu_tier: str, ram_gb: int, refresh_hz: int, cpu_gen: int, cpu_tier: str) -> int:
    gpu_score  = GPU_TIER_MAP.get(gpu_tier, 0) * 30
    ram_score  = min(ram_gb, 64) * 2
    hz_score   = min(refresh_hz, 360) // 10
    cpu_score  = (cpu_gen - 10) * 5 if cpu_gen >= 10 else 0
    hx_bonus   = 15 if cpu_tier and "HX" in cpu_tier.upper() else 0
    return min(gpu_score + ram_score + hz_score + cpu_score + hx_bonus, 100)

def meets_min_requirements(cpu_gen: int, cpu_tier: str, ram_gb: int,
                            ram_type: str, gpu_vram_gb: int, storage_gb: int) -> bool:
    if cpu_gen < MIN_REQUIREMENTS["cpu_gen"]:
        return False
    if cpu_tier and "HX" not in cpu_tier.upper():
        return False
    if ram_gb < MIN_REQUIREMENTS["ram_gb"]:
        return False
    if ram_type and ram_type.upper() != "DDR5":
        return False
    if gpu_vram_gb < MIN_REQUIREMENTS["gpu_vram_gb"]:
        return False
    if storage_gb < MIN_REQUIREMENTS["storage_gb"]:
        return False
    return True


@dataclass
class LaptopListing:
    # ── Identity ──────────────────────────────────────────────
    model_id:        str
    brand:           str
    series:          str
    model_name:      str

    # ── CPU ───────────────────────────────────────────────────
    cpu:             str
    cpu_brand:       str    = "Intel"
    cpu_gen:         int    = 0
    cpu_tier:        str    = "HX"

    # ── GPU ───────────────────────────────────────────────────
    gpu:             str    = ""
    gpu_vram_gb:     int    = 0
    gpu_tier:        str    = ""

    # ── Memory & Storage ─────────────────────────────────────
    ram_gb:          int    = 16
    ram_type:        str    = "DDR5"
    ram_slots:       int    = 2
    storage_gb:      int    = 512
    storage_slots:   int    = 2

    # ── Display ───────────────────────────────────────────────
    display_inches:  float  = 15.6
    refresh_hz:      int    = 144

    # ── Software ─────────────────────────────────────────────
    ms_office:       str    = "Unknown"
    windows_version: str    = "Win11"

    # ── Physical ─────────────────────────────────────────────
    weight_kg:       float  = 2.5
    is_upgradable:   bool   = True

    # ── Pricing & Source ─────────────────────────────────────
    price_inr:       float  = 0.0
    in_stock:        bool   = True
    vendor_name:     str    = ""      # ← correct field name (was 'source_site' — BUG FIXED)
    source_url:      str    = ""

    # ── Computed ─────────────────────────────────────────────
    spec_score:      int    = 0
    meets_requirement: bool = False
    recorded_at:     datetime = None

    def __post_init__(self):
        if not self.recorded_at:
            self.recorded_at = datetime.utcnow()
        self.spec_score = compute_spec_score(
            self.gpu_tier, self.ram_gb, self.refresh_hz,
            self.cpu_gen, self.cpu_tier
        )
        self.meets_requirement = meets_min_requirements(
            self.cpu_gen, self.cpu_tier, self.ram_gb,
            self.ram_type, self.gpu_vram_gb, self.storage_gb
        )


class BaseScraper:
    name = "Base"
    vendor_name = ""

    def __init__(self):
        # cloudscraper mimics a real browser's TLS fingerprint + handles JS challenges
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.session.headers.update(BROWSER_HEADERS)

    def get(self, url, retries=3, extra_headers=None, **kwargs):
        headers = {**BROWSER_HEADERS, **(extra_headers or {})}
        for attempt in range(retries):
            try:
                time.sleep(random.uniform(2.0, 4.5))
                r = self.session.get(url, headers=headers, timeout=30, **kwargs)
                r.raise_for_status()
                return r
            except requests.exceptions.Timeout:
                print(f"    [TIMEOUT] {url} (attempt {attempt+1}/{retries})")
                if attempt == retries - 1:
                    raise
                time.sleep(8)
            except requests.exceptions.HTTPError as e:
                code = e.response.status_code if e.response else 0
                if code in (429, 503) and attempt < retries - 1:
                    wait = 15 * (attempt + 1)
                    print(f"    [RATE LIMIT {code}] Waiting {wait}s before retry...")
                    time.sleep(wait)
                else:
                    raise
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(5)

    def parse_cpu_details(self, cpu_str: str):
        import re
        cpu_str = cpu_str.upper()
        gen = 0
        tier = "H"
        m = re.search(r"I[357]-(\d{2})\d{3}", cpu_str)
        if m:
            gen = int(m.group(1))
        m2 = re.search(r"(\d{4})(HX|H|HS|U)", cpu_str)
        if m2:
            first_digit = int(m2.group(1)[0])
            gen = 12 + (first_digit - 6)
            tier = m2.group(2)
        for t in ["HX", "HS", "H", "U", "P"]:
            if t in cpu_str:
                tier = t
                break
        return gen, tier

    def parse_gpu_details(self, gpu_str: str):
        import re
        gpu_str = gpu_str.upper()
        vram = 0
        tier = ""
        m = re.search(r"(\d+)\s*GB", gpu_str)
        if m:
            vram = int(m.group(1))
        for t in ["RTX 4090", "RTX 4080", "RTX 4070", "RTX 4060", "RTX 4050"]:
            if t.replace(" ", "") in gpu_str.replace(" ", ""):
                tier = t
                break
        return vram, tier

    def parse_ms_office(self, text: str) -> str:
        t = text.lower()
        if "365" in t or "microsoft 365" in t:
            return "MS365"
        if "home" in t and "office" in t:
            return "Home"
        if "office" in t:
            return "Home"
        return "None"

    def parse_windows(self, text: str) -> str:
        t = text.lower()
        if "windows 11" in t or "win 11" in t:
            return "Win11"
        if "windows 10" in t or "win 10" in t:
            return "Win10"
        if "freedos" in t:
            return "FreeDOS"
        return "Win11"

    def scrape(self) -> list:
        raise NotImplementedError
