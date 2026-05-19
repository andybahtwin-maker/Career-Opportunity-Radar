from __future__ import annotations

from utils import posting_age_days


POSITIVE_SIGNALS = {
    "account executive": 6,
    "enterprise account executive": 7,
    "strategic account executive": 7,
    "sales engineer": 7,
    "solutions consultant": 7,
    "solution engineer": 6,
    "solutions engineer": 6,
    "solution consultant": 7,
    "implementation specialist": 5,
    "implementation consultant": 5,
    "technical account manager": 6,
    "engagement manager": 4,
    "construction success manager": 6,
    "customer success": 3,
    "construction": 5,
    "aec": 5,
    "lidar": 5,
    "drone": 5,
    "reality capture": 5,
    "digital twin": 4,
    "field operations": 5,
    "workflow": 4,
    "contractor": 4,
    "mapping": 3,
    "visualization": 3,
    "technical demos": 4,
    "demo": 2,
    "presentations": 3,
    "customer-facing": 4,
    "customer facing": 4,
    "remote": 3,
    "denver": 4,
    "hybrid": 2,
}

NEGATIVE_SIGNALS = {
    "sdr": -7,
    "sales development representative": -7,
    "commission only": -10,
    "door-to-door": -10,
    "door to door": -10,
    "own vehicle required": -8,
    "cold calling quota": -6,
    "insurance sales": -10,
    "canvassing": -9,
}

TITLE_NEGATIVE_SIGNALS = {
    "backend software engineer": -10,
    "software engineer": -8,
    "devops": -8,
    "product manager": -6,
    "product marketing": -7,
    "demand generation": -8,
    "procurement": -8,
    "security": -8,
    "it engineering": -8,
    "social media": -8,
}

US_FRIENDLY_LOCATION_TERMS = {
    "remote",
    "united states",
    "usa",
    "us",
    "denver",
    "austin",
    "boston",
    "chicago",
    "dallas",
    "fort worth",
    "houston",
    "los angeles",
    "new york",
    "raleigh",
    "san francisco",
}

NON_US_LOCATION_TERMS = {
    "australia",
    "austria",
    "belgium",
    "canada",
    "copenhagen",
    "emea",
    "france",
    "germany",
    "india",
    "london",
    "malmö",
    "netherlands",
    "pakistan",
    "pune",
    "singapore",
    "sweden",
    "switzerland",
    "sydney",
    "toronto",
    "uk",
    "vienna",
}


def score_job(job: dict) -> tuple[int, list[str]]:
    text = " ".join(
        str(job.get(key, ""))
        for key in ("title", "company", "location", "raw_description")
    ).lower()
    score = 0
    tags = []
    title = str(job.get("title", "")).lower()
    location = str(job.get("location", "")).lower()

    for phrase, weight in POSITIVE_SIGNALS.items():
        if phrase in text:
            score += weight
            tags.append(f"+{weight} {phrase}")

    for phrase, weight in NEGATIVE_SIGNALS.items():
        if phrase in text:
            score += weight
            tags.append(f"{weight} {phrase}")

    for phrase, weight in TITLE_NEGATIVE_SIGNALS.items():
        if phrase in title:
            score += weight
            tags.append(f"{weight} title: {phrase}")

    if job.get("remote"):
        score += 2
        tags.append("+2 remote flag")

    if location and any(term in location for term in NON_US_LOCATION_TERMS) and not any(
        term in location for term in US_FRIENDLY_LOCATION_TERMS
    ):
        score -= 8
        tags.append("-8 non-US/non-Denver location")

    category = str(job.get("company_category") or "").replace("_", " ")
    if category in {
        "construction saas",
        "contractor workflow",
        "drone reality capture",
        "reality capture",
        "aec tech",
        "aec geospatial",
        "field operations",
        "mapping visualization",
    }:
        score += 2
        tags.append(f"+2 company category: {category}")

    if int(job.get("company_priority") or 0) >= 9:
        score += 1
        tags.append("+1 priority company")

    age = posting_age_days(job.get("date_posted"), job.get("first_seen"))
    if age is None:
        tags.append("no posting date")
    elif age <= 14:
        score += 3
        tags.append("+3 fresh under 14 days")
    elif age >= 30:
        score -= 3
        tags.append("-3 older than 30 days")

    return score, tags
