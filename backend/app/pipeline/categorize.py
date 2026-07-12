"""Rule-based auto-categorization.

Word-boundary keyword scoring over title + description (title hits count
double). Deliberately a plain function so it can be swapped for an ML text
classifier without touching the rest of the pipeline.
"""

import re

CATEGORIES = [
    ("sports", "Sports", "⚽"),
    ("music", "Music", "🎵"),
    ("education", "Education", "🎓"),
    ("business", "Business", "💼"),
    ("cultural", "Cultural", "🎭"),
    ("religious", "Religious", "🕌"),
    ("food", "Food & Drink", "🍽️"),
    ("family", "Family & Kids", "👨‍👩‍👧"),
    ("travel", "Travel & Outdoors", "🏔️"),
    ("movies", "Movies", "🎬"),
    ("international", "International", "🌍"),
    ("other", "Other", "📌"),
]

KEYWORDS: dict[str, list[str]] = {
    "sports": [
        "cricket", "football", "futsal", "hockey", "match", "tournament",
        "marathon", "cycling", "polo", "kabaddi", "badminton", "squash",
        "psl", "league", "race", "fitness", "yoga", "gym", "boxing",
        "wrestling", "esports", "downhill", "trail race", "skate",
        "skateboard", "skateboarding", "skating", "parkour", "climbing",
        "bouldering", "swimming", "martial arts",
    ],
    "music": [
        "concert", "qawwali", "gig", "band", "dj", "music", "singer",
        "live performance", "album", "orchestra", "ghazal", "coke studio",
        "rap", "indie", "sufi night", "open mic",
    ],
    "education": [
        "workshop", "seminar", "lecture", "course", "bootcamp", "training",
        "university", "admission", "career", "hackathon", "stem",
        "science fair", "book fair", "olympiad", "webinar", "certification",
        "masterclass", "study abroad",
    ],
    "business": [
        "startup", "networking", "expo", "conference", "summit", "pitch",
        "entrepreneur", "investor", "trade", "b2b", "fintech", "tech mixer",
        "chamber of commerce", "product launch", "demo day", "awards",
    ],
    "cultural": [
        "festival", "heritage", "art", "exhibition", "theatre", "theater",
        "drama", "mushaira", "poetry", "basant", "mela", "craft",
        "gallery", "dance", "literature", "literary", "painting", "calligraphy",
    ],
    "movies": [
        "movie", "cinema", "film screening", "screening", "premiere",
        "showtime", "cineplex", "film festival", "documentary",
    ],
    "religious": [
        "eid", "milad", "ramadan", "ramzan", "iftar", "urs", "naat",
        "dars", "tableegh", "majlis", "church", "diwali", "prayer",
        "spiritual", "zikr", "seerat", "mehfil",
    ],
    "food": [
        "food festival", "food street", "tasting", "culinary", "chef",
        "bbq", "barbecue", "dessert", "iftari", "brunch", "street food",
        "food expo", "cooking",
    ],
    "family": [
        "kids", "children", "family", "carnival", "funfair", "puppet",
        "magic show", "circus", "zoo", "storytelling", "play area",
    ],
    "travel": [
        "tour", "tours", "trek", "trekking", "hike", "hiking", "camping",
        "base camp", "expedition", "safari", "trip", "road trip",
        "sightseeing", "glamping", "stargazing",
    ],
    "international": [
        "international", "world tour", "global", "embassy",
        "visiting artist", "foreign", "delegation",
    ],
}

# Precompile whole-word patterns; substring hits like "urs" in "tours" or
# "rap" in "therapy" must not count.
_PATTERNS: dict[str, list[tuple[re.Pattern, str]]] = {
    slug: [(re.compile(r"\b" + re.escape(kw) + r"\b"), kw) for kw in words]
    for slug, words in KEYWORDS.items()
}


def categorize(title: str, description: str = "") -> tuple[str, str]:
    """Return (category_slug, matched_keyword) for an event's text."""
    title_l = title.lower()
    desc_l = description.lower()
    best_slug, best_score, best_kw = "other", 0, ""
    for slug, patterns in _PATTERNS.items():
        score = 0
        first_kw = ""
        for pattern, kw in patterns:
            in_title = bool(pattern.search(title_l))
            if in_title or pattern.search(desc_l):
                score += 2 if in_title else 1
                if not first_kw:
                    first_kw = kw
        if score > best_score:
            best_slug, best_score, best_kw = slug, score, first_kw
    return best_slug, best_kw
