"""Universal Multi-Brand and Multi-Product Domain Router.

Enables the AI agent to support diverse consumer products across the 108 brands
in the Twitter customer support ecosystem (Apple, Amazon, Uber, Spotify, Xbox, Samsung, etc.).
"""
from __future__ import annotations

import re
from typing import Dict, Any, Optional


BRAND_PROFILES: Dict[str, Dict[str, Any]] = {
    "AppleSupport": {
        "name": "Apple Support",
        "handle": "@AppleSupport",
        "category": "Consumer Electronics & OS",
        "sample_products": ["iPhone", "iPad", "MacBook", "Apple Watch", "AirPods", "iOS", "iCloud"],
        "support_url": "https://support.apple.com",
        "keywords": ["iphone", "ipad", "mac", "ios", "apple id", "itunes", "airpods", "icloud", "watchos", "macbook"],
    },
    "AmazonHelp": {
        "name": "Amazon Customer Service",
        "handle": "@AmazonHelp",
        "category": "E-Commerce, Logistics & Smart Home",
        "sample_products": ["Prime Delivery", "Kindle", "Echo / Alexa", "Fire TV", "Amazon Orders", "Refunds"],
        "support_url": "https://www.amazon.com/help",
        "keywords": ["amazon", "order", "delivery", "package", "prime", "refund", "alexa", "echo", "kindle", "firestick"],
    },
    "Uber_Support": {
        "name": "Uber Support",
        "handle": "@Uber_Support",
        "category": "Mobility & Ride-Sharing",
        "sample_products": ["Uber Rides", "Uber Eats", "Driver App", "Fare Dispute", "Lost Item"],
        "support_url": "https://help.uber.com",
        "keywords": ["uber", "driver", "ride", "trip", "fare", "eats", "cancellation", "cab", "uberx"],
    },
    "SpotifyCares": {
        "name": "Spotify Cares",
        "handle": "@SpotifyCares",
        "category": "Digital Streaming & Audio",
        "sample_products": ["Spotify Premium", "Playlists", "Offline Sync", "Family Plan", "Podcasts"],
        "support_url": "https://support.spotify.com",
        "keywords": ["spotify", "playlist", "songs", "premium", "stream", "offline", "music", "family plan"],
    },
    "XboxSupport": {
        "name": "Xbox Support",
        "handle": "@XboxSupport",
        "category": "Gaming & Cloud Services",
        "sample_products": ["Xbox Series X", "Xbox Series S", "Game Pass", "Xbox Live", "Controller"],
        "support_url": "https://support.xbox.com",
        "keywords": ["xbox", "game pass", "console", "controller", "xbox live", "multiplayer", "gamertag"],
    },
    "SamsungSupport": {
        "name": "Samsung Support",
        "handle": "@SamsungSupport",
        "category": "Smartphones, TVs & Appliances",
        "sample_products": ["Galaxy S24", "Galaxy Z Fold", "Smart TV", "Bespoke Refrigerator", "One UI"],
        "support_url": "https://www.samsung.com/support",
        "keywords": ["samsung", "galaxy", "z fold", "one ui", "smart tv", "bixby", "exynos", "snapdragon"],
    },
    "Delta": {
        "name": "Delta Air Lines",
        "handle": "@Delta",
        "category": "Aviation & Commercial Travel",
        "sample_products": ["Flight Bookings", "SkyMiles", "Baggage Tracking", "Boarding Passes", "Flight Status"],
        "support_url": "https://www.delta.com/needhelp",
        "keywords": ["delta", "flight", "boarding", "skymiles", "baggage", "gate", "terminal", "rebook", "airport"],
    },
}


class BrandRouter:
    """Detects target brand and product context from customer inquiry text."""

    @staticmethod
    def detect_brand(text: str, default_brand: str = "AppleSupport") -> Dict[str, Any]:
        """Infer which brand/product domain the inquiry belongs to."""
        lowered = text.lower()

        # Check explicit mention
        for brand_key, meta in BRAND_PROFILES.items():
            if meta["handle"].lower() in lowered:
                return {"brand_key": brand_key, **meta}

        # Check keyword matches
        scores = {}
        for brand_key, meta in BRAND_PROFILES.items():
            score = sum(1 for kw in meta["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", lowered))
            scores[brand_key] = score

        best_brand = max(scores, key=scores.get)
        if scores[best_brand] > 0:
            return {"brand_key": best_brand, **BRAND_PROFILES[best_brand]}

        return {"brand_key": default_brand, **BRAND_PROFILES[default_brand]}

    @classmethod
    def get_all_brands(cls) -> Dict[str, Dict[str, Any]]:
        """Return all supported brand profiles."""
        return BRAND_PROFILES.copy()

    @classmethod
    def get_brand_info(cls, brand_key: str) -> Dict[str, Any]:
        """Return metadata for a specific brand profile."""
        if brand_key in BRAND_PROFILES:
            return {"brand_key": brand_key, **BRAND_PROFILES[brand_key]}
        return {"brand_key": "AppleSupport", **BRAND_PROFILES["AppleSupport"]}
