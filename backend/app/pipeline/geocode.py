"""Geocoding for the normalization layer.

v1 resolves against a curated gazetteer of known venues and localities in the
launch city (Islamabad/Rawalpindi). Unknown addresses fall back to sector-level
matching, then to the city centroid. A real geocoding API (Google/Nominatim)
can be slotted into `geocode()` later — callers only see (lat, lng).
"""

CITY_CENTROIDS = {
    "islamabad": (33.6844, 73.0479),
    "rawalpindi": (33.5651, 73.0169),
    "lahore": (31.5204, 74.3587),
    "karachi": (24.8607, 67.0011),
}

# Known venues in the launch market. name (lowercased substring) -> (lat, lng)
VENUES = {
    "pakistan national council of the arts": (33.7101, 73.0777),
    "pnca": (33.7101, 73.0777),
    "lok virsa": (33.6935, 73.0806),
    "pakistan monument": (33.6936, 73.0666),
    "faisal mosque": (33.7295, 73.0372),
    "jinnah convention centre": (33.7167, 73.1004),
    "jinnah convention center": (33.7167, 73.1004),
    "pak-china friendship centre": (33.7220, 73.1032),
    "pak china friendship centre": (33.7220, 73.1032),
    "pak-china friendship center": (33.7220, 73.1032),
    "f-9 park": (33.7047, 73.0250),
    "fatima jinnah park": (33.7047, 73.0250),
    "centaurus": (33.7078, 73.0501),
    "serena hotel": (33.7222, 73.0937),
    "marriott hotel": (33.7266, 73.0862),
    "liberty parade ground": (33.6980, 73.0755),
    "jinnah stadium": (33.6520, 73.0754),
    "pakistan sports complex": (33.6522, 73.0779),
    "liaquat gymnasium": (33.6530, 73.0790),
    "daman-e-koh": (33.7476, 73.0568),
    "monal": (33.7515, 73.0575),
    "saidpur village": (33.7368, 73.0679),
    "shakarparian": (33.6906, 73.0724),
    "rawal lake": (33.6970, 73.1235),
    "quaid-i-azam university": (33.7463, 73.1385),
    "qau": (33.7463, 73.1385),
    "nust": (33.6425, 72.9910),
    "comsats": (33.6512, 73.1565),
    "air university": (33.7167, 73.0995),
    "fast nuces": (33.6570, 73.0169),
    "iiui": (33.6631, 73.0269),
    "islamabad club": (33.7130, 73.1120),
    "kuch khaas": (33.7280, 73.0800),
    "gallery 6": (33.7245, 73.0745),
    "tanzara gallery": (33.7290, 73.0870),
    "d-chowk": (33.7296, 73.0940),
    "convention centre": (33.7167, 73.1004),
    "expo centre": (33.6640, 73.0810),
    "golra sharif": (33.7050, 72.9450),
    "bari imam": (33.7480, 73.1180),
    "faizabad": (33.6614, 73.0855),
    "army museum": (33.5885, 73.0470),
    "ayub park": (33.5716, 73.0672),
    "arts council rawalpindi": (33.6007, 73.0679),
    "rawalpindi cricket stadium": (33.6503, 73.0817),
    "pindi cricket stadium": (33.6503, 73.0817),
}

# Sector-level fallback (Islamabad grid).
SECTORS = {
    "f-5": (33.7245, 73.0837), "f-6": (33.7276, 73.0745), "f-7": (33.7203, 73.0564),
    "f-8": (33.7100, 73.0394), "f-10": (33.6957, 73.0121), "f-11": (33.6845, 72.9902),
    "g-5": (33.7167, 73.0980), "g-6": (33.7180, 73.0790), "g-7": (33.7080, 73.0680),
    "g-8": (33.6990, 73.0480), "g-9": (33.6900, 73.0330), "g-10": (33.6790, 73.0140),
    "g-11": (33.6690, 72.9980), "g-13": (33.6520, 72.9640),
    "i-8": (33.6680, 73.0740), "i-9": (33.6600, 73.0530), "i-10": (33.6480, 73.0350),
    "e-7": (33.7350, 73.0550), "e-9": (33.7130, 73.0180), "e-11": (33.7000, 72.9780),
    "blue area": (33.7150, 73.0650), "dha": (33.5300, 73.1560), "bahria town": (33.5450, 73.1050),
    "saddar": (33.5980, 73.0530), "gulberg greens": (33.6100, 73.1550),
}


def geocode(venue_name: str, address: str, city: str) -> tuple[float | None, float | None, bool]:
    """Resolve (lat, lng, exact) for a venue/address. `exact` is False when we
    only matched at sector or city granularity."""
    text = f"{venue_name} {address}".lower()
    for key, coords in VENUES.items():
        if key in text:
            return coords[0], coords[1], True
    for key, coords in SECTORS.items():
        if key in text:
            return coords[0], coords[1], False
    centroid = CITY_CENTROIDS.get(city.strip().lower())
    if centroid:
        return centroid[0], centroid[1], False
    return None, None, False
