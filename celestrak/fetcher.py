"""
Fetch real space debris from CelesTrak API.
Falls back to mock data if offline.
"""
import json
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

__all__ = ["DebrisFetcher", "DebrisObject"]


@dataclass
class DebrisObject:
    """Real space debris metadata."""
    norad_id: str          # NORAD catalog ID
    name: str              # Object name
    object_type: str       # DEBRIS, PAYLOAD, ROCKET BODY, etc.
    country: str           # Launch country
    launch_date: str       # YYYY-MM-DD
    
    def to_dict(self) -> dict:
        return asdict(self)


class DebrisFetcher:
    """
    Fetch and cache CelesTrak debris data.
    
    Usage:
        fetcher = DebrisFetcher(use_mock=True)  # Offline mode
        debris = fetcher.get_random()
        print(debris.norad_id, debris.name)
    """
    
    CACHE_FILE = Path("debris_cache.json")
    CACHE_DURATION = 86400  # 24 hours
    
    # CelesTrak GP endpoints
    CELESTRAK_URLS = {
        "debris": "https://celestrak.org/NORAD/elements/gp.php?GROUP=debris&FORMAT=json",
        "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json",
    }
    
    def __init__(self, use_mock: bool = False):
        """
        Args:
            use_mock: If True, use offline mock data instead of API
        """
        self.use_mock = use_mock
        self._debris_pool: List[DebrisObject] = []
        self._load_or_fetch()
    
    def _load_or_fetch(self):
        """Load cache or fetch fresh data."""
        if self.use_mock:
            self._debris_pool = self._generate_mock_debris()
            return
        
        # Try cache first
        if self.CACHE_FILE.exists():
            cache_age = time.time() - self.CACHE_FILE.stat().st_mtime
            if cache_age < self.CACHE_DURATION:
                try:
                    with open(self.CACHE_FILE) as f:
                        data = json.load(f)
                        self._debris_pool = [DebrisObject(**d) for d in data]
                        print(f"[CelesTrak] Loaded {len(self._debris_pool)} objects from cache")
                        return
                except Exception as e:
                    print(f"[CelesTrak] Cache read failed: {e}")
        
        # Fetch from API
        try:
            self._fetch_from_api()
        except Exception as e:
            print(f"[CelesTrak] API fetch failed: {e}, using mock data")
            self._debris_pool = self._generate_mock_debris()
    
    def _fetch_from_api(self):
        """Fetch from CelesTrak (requires network)."""
        import urllib.request
        
        all_objects = []
        for category, url in self.CELESTRAK_URLS.items():
            print(f"[CelesTrak] Fetching {category}...")
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read())
                
                for obj in data:
                    debris = DebrisObject(
                        norad_id=str(obj.get("NORAD_CAT_ID", "00000")),
                        name=obj.get("OBJECT_NAME", "UNKNOWN"),
                        object_type=obj.get("OBJECT_TYPE", "DEBRIS"),
                        country=obj.get("COUNTRY", "UNK"),
                        launch_date=obj.get("LAUNCH_DATE", "1957-10-04")
                    )
                    all_objects.append(debris)
        
        self._debris_pool = all_objects
        
        # Cache it
        with open(self.CACHE_FILE, "w") as f:
            json.dump([d.to_dict() for d in all_objects], f)
        
        print(f"[CelesTrak] Cached {len(all_objects)} objects")
    
    def _generate_mock_debris(self) -> List[DebrisObject]:
        """Generate mock debris for offline testing."""
        mock_data = []
        
        # Real-ish NORAD IDs and names
        templates = [
            ("25544", "ISS (ZARYA)", "PAYLOAD", "ISS", "1998-11-20"),
            ("43226", "STARLINK-1007", "PAYLOAD", "US", "2018-02-22"),
            ("16908", "SL-16 R/B", "ROCKET BODY", "CIS", "1986-06-19"),
            ("40115", "FENGYUN 1C DEB", "DEBRIS", "PRC", "2007-01-11"),
            ("25400", "COSMOS 2251 DEB", "DEBRIS", "CIS", "2009-02-10"),
            ("37820", "H-2A R/B", "ROCKET BODY", "JPN", "2011-09-17"),
            ("33320", "IRIDIUM 33 DEB", "DEBRIS", "US", "2009-02-10"),
            ("20625", "DELTA 2 R/B", "ROCKET BODY", "US", "1990-05-24"),
        ]
        
        # Generate 500 mock objects
        for i in range(500):
            template = random.choice(templates)
            norad_base = int(template[0])
            mock = DebrisObject(
                norad_id=str(norad_base + i),
                name=f"{template[1]}-{i}",
                object_type=template[2],
                country=template[3],
                launch_date=template[4]
            )
            mock_data.append(mock)
        
        print(f"[CelesTrak] Generated {len(mock_data)} mock objects")
        return mock_data
    
    def get_random(self) -> Optional[DebrisObject]:
        """Get random debris for asteroid assignment."""
        if not self._debris_pool:
            return None
        return random.choice(self._debris_pool)
    
    def get_by_norad(self, norad_id: str) -> Optional[DebrisObject]:
        """Look up specific debris by NORAD ID."""
        for debris in self._debris_pool:
            if debris.norad_id == norad_id:
                return debris
        return None
    
    @property
    def count(self) -> int:
        """Total debris objects available."""
        return len(self._debris_pool)
