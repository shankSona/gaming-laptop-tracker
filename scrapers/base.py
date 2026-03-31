import requests, time, random
from dataclasses import dataclass, field
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── MINIMUM REQUIREMENTS FILTER ─────────────────────────────
MIN_REQUIREMENTS = {
    "cpu_gen":      13,       # 13th gen or newer
    "cpu_tier":     "HX",     # must be HX (not H, U, HS) for Intel
                              # for AMD, Ryzen 7000 series HX counts too
    "ram_gb":       16,
    "ram_type":     "DDR5",
    "gpu_vram_gb":  6,        # RTX 4050 6GB minimum
    "storage_gb":   512,
}

GPU_TIER_MAP = {
    # maps to numeric tier for scoring
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
    """Returns True only if laptop passes all minimum spec requirements."""
    if cpu_gen < MIN_REQUIREMENTS["cpu_gen"]:
        return False
    # For Intel: must be HX. For AMD Ryzen: HX suffix also exists (e.g. 7945HX)
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
    cpu_brand:       str    = "Intel"   # Intel / AMD
    cpu_gen:         int    = 0         # 13 / 14 / 15
    cpu_tier:        str    = "HX"      # HX / H / U / HS

    # ── GPU ───────────────────────────────────────────────────
    gpu:             str    = ""
    gpu_vram_gb:     int    = 0
    gpu_tier:        str    = ""        # RTX4050 / RTX4060 etc.

    # ── Memory & Storage ─────────────────────────────────────
    ram_gb:          int    = 16
    ram_type:        str    = "DDR5"
    ram_slots:       int    = 2         # 2 = upgradable
    storage_gb:      int    = 512
    storage_slots:   int    = 2         # 2 = room for more drives

    # ── Display ───────────────────────────────────────────────
    display_inches:  float  = 15.6
    refresh_hz:      int    = 144

    # ── Software ─────────────────────────────────────────────
    ms_office:       str    = "Unknown"  # NULL / MS365 / Home / None
    windows_version: str    = "Win11"    # Win11 / Win10 / FreeDOS

    # ── Physical ─────────────────────────────────────────────
    weight_kg:       float  = 2.5
    is_upgradable:   bool   = True       # spare RAM or M.2 slot exists

    # ── Pricing & Source ─────────────────────────────────────
    price_inr:       float  = 0.0
    in_stock:        bool   = True
    vendor_name:     str    = ""         # amazon.in / flipkart.com / croma.com etc.
    source_url:      str    = ""

    # ── Computed (auto-filled) ────────────────────────────────
    spec_score:      int    = 0
    meets_requirement: bool = False
    recorded_at:     datetime = None

    def __post_init__(self):
        if not self.recorded_at:
            self.recorded_at = datetime.utcnow()
        # Auto-compute spec score
        self.spec_score = compute_spec_score(
            self.gpu_tier, self.ram_gb, self.refresh_hz,
            self.cpu_gen, self.cpu_tier
        )
        # Auto-check requirements
        self.meets_requirement = meets_min_requirements(
            self.cpu_gen, self.cpu_tier, self.ram_gb,
            self.ram_type, self.gpu_vram_gb, self.storage_gb
        )

class BaseScraper:
    name = "Base"
    vendor_name = ""    # each subclass sets this

    def get(self, url, **kwargs):
        time.sleep(random.uniform(1.5, 3.5))
        r = requests.get(url, headers=HEADERS, timeout=20, **kwargs)
        r.raise_for_status()
        return r

    def parse_cpu_details(self, cpu_str: str):
        """Extract gen and tier from CPU string."""
        import re
        cpu_str = cpu_str.upper()
        gen = 0
        tier = "H"
        # Intel gen detection: i7-13700HX → gen 13
        m = re.search(r"I[357]-(\d{2})\d{3}", cpu_str)
        if m:
            gen = int(m.group(1))
        # AMD gen: 7745HX → gen roughly maps to release year
        m2 = re.search(r"(\d{4})(HX|H|HS|U)", cpu_str)
        if m2:
            first_digit = int(m2.group(1)[0])
            gen = 12 + (first_digit - 6)  # Ryzen 7xxx ≈ gen 13 equivalent
            tier = m2.group(2)
        # Intel tier suffix
        for t in ["HX", "HS", "H", "U", "P"]:
            if t in cpu_str:
                tier = t
                break
        return gen, tier

    def parse_gpu_details(self, gpu_str: str):
        """Extract VRAM and tier from GPU string."""
        import re
        gpu_str = gpu_str.upper()
        vram = 0
        tier = ""
        m = re.search(r"(\d+)\s*GB", gpu_str)
        if m:
            vram = int(m.group(1))
        for t in ["RTX 4090","RTX 4080","RTX 4070","RTX 4060","RTX 4050"]:
            if t.replace(" ","") in gpu_str.replace(" ",""):
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
        return "Win11"  # default assumption for new gaming laptops

    def scrape(self) -> list:
        raise NotImplementedError
