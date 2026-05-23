from __future__ import annotations

import hashlib
import re
from functools import lru_cache

from config import SEARCH_PROFILE_FILE


DENVER_AREA_TERMS = (
    "denver",
    "denver metro",
    "glendale",
    "englewood",
    "lakewood",
    "littleton",
    "centennial",
    "aurora",
    "westminster",
    "arvada",
    "boulder",
    "broomfield",
    "commerce city",
    "golden",
    "thornton",
    "fort collins",
    "loveland",
    "greeley",
    "castle rock",
    "longmont",
    "colorado springs",
)

NON_DENVER_MARKET_TERMS = (
    "nashville",
    "raleigh",
    "chicago",
    "northern california",
    "southern california",
    "bay area",
    "new york",
    "boston",
    "seattle",
    "austin",
    "dallas",
    "fort worth",
    "atlanta",
    "philadelphia",
    "philly",
    "orange county",
    "memphis",
    "tampa",
    "florida",
    "texas",
    "california",
)

FOREIGN_LOCATION_TERMS = (
    "apac",
    "australia",
    "austria",
    "belgium",
    "canada",
    "copenhagen",
    "denmark",
    "emea",
    "europe",
    "france",
    "germany",
    "india",
    "london",
    "malaysia",
    "malmö",
    "netherlands",
    "portugal",
    "pakistan",
    "pune",
    "singapore",
    "sweden",
    "switzerland",
    "sydney",
    "toronto",
    "brazil",
    "colombia",
    "columbia",
    "chile",
    "chili",
    "uk",
    "vienna",
)

FOREIGN_REMOTE_US_TERMS = (
    "remote us",
    "remote u.s.",
    "remote united states",
    "us candidates",
    "u.s. candidates",
    "usa candidates",
    "eligible for us",
    "eligible for u.s.",
    "based in the us",
    "based in the u.s.",
)

GENERIC_JOB_TITLE_NOISE_EXACT = {
    "apply now",
    "didn't find what you were looking for?",
    "didn’t find what you were looking for?",
    "didn't find what you were looking for",
    "didn’t find what you were looking for",
    "see open roles",
    "open roles",
    "careers",
    "join our team",
    "complete job",
    "send your cv",
    "let's talk about you",
    "lets talk about you",
    "general application",
    "open application",
    "future openings",
    "talent pool",
    "developers.cloudflare.com",
    "cookies",
    "cookie",
}

GENERIC_CTA_PHRASES = (
    "didn't find what you were looking for",
    "didn’t find what you were looking for",
    "send your cv",
    "let's talk about you",
    "lets talk about you",
    "general application",
    "open application",
    "future openings",
    "talent pool",
)

GENERIC_JOB_TITLE_PRODUCT_EXACT = {
    "showroom",
    "windows",
    "kitchen sinks",
    "the edge estimator",
}

GENERIC_JOB_TITLE_MARKETING_EXACT = {
    "bogo",
    "sale",
    "promotion",
    "customer stories",
    "blog",
    "webinar",
}

GENERIC_JOB_TITLE_NON_JOB_EXACT = {
    "privacy policy",
    "terms",
    "login",
    "contact us",
    "product",
    "features",
    "resources",
}

SOFTWARE_ENGINEERING_ROLE_TERMS = (
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "full stack engineer",
    "fullstack engineer",
    "iOS engineer",
    "ios engineer",
    "android engineer",
    "mobile engineer",
    "devops",
    "site reliability engineer",
    "sre",
    "product manager",
    "product management",
    "growth marketing",
    "demand generation",
    "marketing manager",
    "ux designer",
    "ui designer",
    "designer ux",
)

JOB_POSTING_URL_HINTS = (
    "/careers/",
    "/jobs/",
    "/job/",
    "/openings/",
    "/positions/",
    "/greenhouse/",
    "/lever/",
    "/workable/",
    "/ashby/",
    "jobid=",
    "gh_jid=",
)

JOB_POSTING_DESCRIPTION_TERMS = (
    "responsibilities",
    "requirements",
    "qualifications",
    "benefits",
    "compensation",
    "salary",
    "posted",
    "requisition",
    "req ",
    "department",
    "team",
    "employment type",
    "full-time",
    "part-time",
    "contract",
    "location",
    "about the role",
    "what you'll do",
    "what youll do",
)

REMOTE_LOCALIZABLE_TERMS = (
    "customer success",
    "customer onboarding",
    "implementation",
    "onboarding",
    "mid-market",
    "smb",
    "construction",
    "aec",
    "contractor",
    "homebuilding",
    "field operations",
    "geospatial",
    "drone",
    "reality capture",
    "building materials",
    "building products",
    "industrial distribution",
    "manufacturing operations",
)

JOB_POSTING_TITLE_TERMS = (
    "account",
    "associate",
    "coordinator",
    "consultant",
    "designer",
    "director",
    "engineer",
    "manager",
    "rep",
    "representative",
    "sales",
    "specialist",
    "success",
    "support",
    "technician",
    "analyst",
    "estimator",
    "implementation",
    "operations",
    "project",
)

REMOTE_ANYWHERE_TERMS = (
    "remote anywhere",
    "remote from anywhere",
    "remote across the u.s.",
    "remote across the us",
    "remote within the u.s.",
    "remote within the us",
    "anywhere in the u.s.",
    "anywhere in the us",
    "anywhere in united states",
    "anywhere in the united states",
    "national remote",
    "fully remote across the u.s.",
    "fully remote across the us",
)


DEFAULT_TARGETING = {
    "role_positive": (
        "commercial sales representative",
        "commercial market sales representative",
        "market representative",
        "market sales representative",
        "design consultant",
        "design sales consultant",
        "sales consultant",
        "territory sales representative",
        "account manager",
        "client success manager",
        "project consultant",
        "product specialist",
        "showroom consultant",
        "showroom sales consultant",
        "flooring sales",
        "tile sales",
        "cabinet designer",
        "kitchen and bath designer",
        "countertop sales",
        "window and door sales",
        "glass sales",
        "glazing sales",
        "building materials sales",
        "architectural products sales",
        "architectural representative",
        "architectural sales consultant",
        "a&d representative",
        "builder sales representative",
        "dealer sales representative",
        "specification sales",
        "specifier sales",
        "trade sales representative",
        "trade representative",
        "contractor sales",
        "surface sales",
        "slab sales",
        "stone sales",
        "porcelain sales",
        "millwork sales",
        "commercial interiors sales",
        "inside sales representative",
        "sales estimator",
        "cad designer",
        "solidworks designer",
        "technical designer",
        "drafting technician",
        "cad drafter",
        "millwork designer",
        "commercial interiors designer",
        "estimator cad",
        "design sales support",
        "solar sales consultant",
        "customer onboarding specialist",
        "implementation specialist",
        "field operations consultant",
        "operations coordinator",
        "project coordinator",
        "smb account executive",
        "mid-market account executive",
        "solutions consultant",
        "associate sales engineer",
        "sales engineer solidworks",
    ),
    "role_negative": (
        "enterprise",
        "enterprise ae",
        "enterprise account executive",
        "strategic ae",
        "strategic account executive",
        "senior se",
        "senior sales engineer",
        "director",
        "vp",
        "advisory consultant",
        "sdr",
        "sales development representative",
    ),
    "industry_positive": (
        "building materials",
        "commercial interiors",
        "glass and glazing",
        "construction",
        "contractor services",
        "architectural products",
        "flooring",
        "tile",
        "cabinets",
        "countertops",
        "windows and doors",
        "kitchen and bath",
        "design-build",
        "home improvement",
        "quartz",
        "stone",
        "slab",
        "porcelain slab",
        "solid surface",
        "millwork",
        "architectural millwork",
        "finish materials",
        "fixtures",
        "lighting",
        "hardware",
        "commercial flooring",
        "residential flooring",
        "surfaces",
        "building envelope",
        "facade",
        "building products",
        "construction suppliers",
        "mep",
        "hvac",
        "plumbing supply",
        "electrical supply",
        "facilities operations",
        "industrial distribution",
        "field-service operations",
        "commercial equipment",
        "manufacturing operations",
        "logistics operations",
        "geospatial",
        "drone",
    ),
    "industry_negative": (
        "cybersecurity",
        "hr tech",
        "finance saas",
        "developer tooling",
        "pure enterprise saas",
        "generic productivity software",
    ),
    "required_positive": (
        "customer-facing",
        "customer facing",
        "consultative",
        "implementation",
        "onboarding",
        "showroom",
        "estimating",
        "estimate",
        "salesforce",
        "customer meetings",
        "workflow",
        "process improvement",
        "project coordination",
        "contractor-facing",
        "contractor facing",
        "operational support",
        "relationship-driven",
        "relationship driven",
        "training provided",
        "company vehicle",
        "mileage reimbursement",
        "car allowance",
        "base salary",
        "base pay",
        "benefits",
        "architects",
        "designers",
        "specifiers",
        "trade partners",
        "builders",
        "fabricators",
        "industry knowledge valued",
        "cross-functional collaboration",
        "field operations",
    ),
    "hard_exclusions": (
        "8+ years enterprise saas required",
        "existing enterprise book required",
        "meddic",
        "clari",
        "gong-heavy",
        "fortune-500-only",
        "heavy outbound call-center",
        "commission-only",
        "commission only",
        "door-to-door",
        "door to door",
        "own car mandatory",
        "own vehicle required",
        "must have reliable vehicle",
        "cdl",
        "warehouse-only",
        "installer-only",
        "laborer-only",
        "backend",
        "software engineer",
        "team management required",
    ),
    "locations_strong": DENVER_AREA_TERMS,
    "locations_moderate": (
        "hybrid",
        "on-site",
        "onsite",
        "local territory",
        "regional travel under 25%",
        "denver office",
        "denver showroom",
        "denver territory",
        "local branch",
        "showroom",
        "design center",
        "company vehicle",
        "branded vehicle",
        "fleet vehicle",
        "mileage reimbursement",
        "car allowance",
    ),
    "locations_negative": (
        "remote-only",
        "remote only",
        "east-coast timezone",
        "east coast timezone",
        "nationwide territory",
        "heavy travel",
        "car required",
    ),
    "sources_negative": (
        "remotejobs.org",
        "generic remote-job apis",
        "remote-first saas boards",
        "enterprise saas watchlists",
        "vc-funded startup-heavy feeds",
        "top remote jobs",
    ),
}


def profile_hash() -> str:
    return hashlib.sha256(load_profile_text().encode("utf-8")).hexdigest()[:16]


def load_profile_text() -> str:
    if not SEARCH_PROFILE_FILE.exists():
        return ""
    return SEARCH_PROFILE_FILE.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def current_targeting() -> dict[str, tuple[str, ...]]:
    text = load_profile_text()
    parsed = {key: tuple(value) for key, value in DEFAULT_TARGETING.items()}
    if not text.strip():
        return parsed

    role_positive = bullets_after(text, "Highest Priority") + bullets_after(text, "Moderate Priority")
    role_negative = bullets_after(text, "Penalize", after_heading="ROLE PRIORITY")
    industry_positive = bullets_after(text, "Tier 1") + bullets_after(text, "Tier 2")
    industry_negative = bullets_after(text, "Penalize", after_heading="INDUSTRY PRIORITY")
    required_positive = bullets_after(text, "REQUIRED POSITIVE SIGNALS")
    hard_exclusions = bullets_after(text, "HARD EXCLUSIONS")
    strong_locations = bullets_after(text, "Strong Boost")
    moderate_locations = bullets_after(text, "Moderate Boost")
    negative_locations = bullets_after(text, "Heavy Penalty")
    negative_sources = bullets_after(text, "REMOVE / DEPRIORITIZE THESE SOURCES")

    replacements = {
        "role_positive": role_positive,
        "role_negative": role_negative,
        "industry_positive": industry_positive,
        "industry_negative": industry_negative,
        "required_positive": required_positive,
        "hard_exclusions": hard_exclusions,
        "locations_strong": strong_locations,
        "locations_moderate": moderate_locations,
        "locations_negative": negative_locations,
        "sources_negative": negative_sources,
    }
    for key, values in replacements.items():
        cleaned = tuple(dedupe(clean_term(value) for value in values if clean_term(value)))
        if cleaned:
            parsed[key] = cleaned
    return parsed


def clear_targeting_cache() -> None:
    current_targeting.cache_clear()


def discovery_keywords(limit: int = 50) -> list[str]:
    targeting = current_targeting()
    candidates = list(targeting["role_positive"]) + list(targeting["industry_positive"])
    return dedupe(candidates)[:limit]


def discovery_locations() -> list[str]:
    values = ["Denver, CO", *current_targeting()["locations_strong"]]
    return dedupe(values)


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def contains_any(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase and phrase in text]


def matching_required_positive_count(text: str) -> int:
    return len(contains_any(text, current_targeting()["required_positive"]))


def is_hard_excluded(job: dict) -> tuple[bool, list[str]]:
    text = job_text(job)
    vehicle_mitigated = any(
        phrase in text
        for phrase in (
            "company vehicle",
            "company car",
            "branded vehicle",
            "fleet vehicle",
            "vehicle provided",
            "vehicle allowance",
            "mileage reimbursement",
            "mileage reimbursed",
            "travel reimbursed",
            "travel reimbursement",
            "company-paid travel",
            "company paid travel",
            "paid travel",
            "car allowance",
            "denver territory",
            "denver office",
            "denver showroom",
            "55k base",
            "65k base",
            "80k base",
        )
    )
    matches = []
    for phrase in current_targeting()["hard_exclusions"]:
        if phrase in {"own vehicle required", "own car mandatory", "must have reliable vehicle"} and vehicle_mitigated:
            continue
        if phrase and phrase in text:
            matches.append(phrase)
    return bool(matches), matches


def is_local_or_localizable(job: dict) -> bool:
    location = normalize_text(job.get("location"))
    text = job_text(job)
    targeting = current_targeting()
    if non_denver_territory_terms(job):
        return False
    if contains_any(location, FOREIGN_LOCATION_TERMS) and not re.search(r"\b(?:united states|usa|u\.s\.|us)\b", location):
        return False
    if clear_colorado_signal(job):
        return True
    if contains_any(location, targeting["locations_moderate"]):
        return True
    if job.get("remote") and not contains_any(text, targeting["locations_negative"]):
        if contains_any(text, REMOTE_LOCALIZABLE_TERMS) and matching_required_positive_count(text) >= 1:
            return True
    return False


def has_remote_anywhere_signal(job: dict) -> bool:
    return bool(contains_any(job_text(job), REMOTE_ANYWHERE_TERMS))


def clear_colorado_signal(job: dict) -> bool:
    title = normalize_text(job.get("title"))
    location = normalize_text(job.get("location"))
    description = normalize_text(job.get("raw_description"))
    title_description = f"{title} {description}"
    if contains_any(title_description, DENVER_AREA_TERMS):
        return True
    if "colorado" in title_description:
        return True
    if contains_any(title_description, ("denver office", "denver showroom", "denver territory", "front range", "colorado territory")):
        return True
    if contains_any(location, ("denver / colorado", "colorado")):
        return True
    return False


def non_denver_territory_terms(job: dict) -> list[str]:
    targeting = current_targeting()
    title_location = normalize_text(f"{job.get('title', '')} {job.get('location', '')}")

    direct_matches = contains_any(title_location, NON_DENVER_MARKET_TERMS)
    if direct_matches:
        return direct_matches
    if has_remote_anywhere_signal(job):
        return []

    description = normalize_text(job.get("raw_description"))
    context_terms = ("territory", "market", "region", "preferred", "based", "located", "must reside in", "only open to residents in")
    if not contains_any(description, context_terms):
        return []
    matches = []
    for market in NON_DENVER_MARKET_TERMS:
        if market not in description:
            continue
        if contains_any(description, context_terms):
            matches.append(market)
    abbrev_text = f"{title_location} {description}"
    if re.search(r"\b(?:atl|tx|fl)\b", abbrev_text) and contains_any(abbrev_text, context_terms):
        matches.append("state/region restriction")
    return matches


def source_penalty_applies(job: dict) -> bool:
    source_text = normalize_text(
        " ".join(str(job.get(key, "")) for key in ("source_name", "ats_source", "source_kind"))
    )
    if "remotejobs" in source_text:
        return True
    return bool(contains_any(source_text, current_targeting()["sources_negative"]))


def job_text(job: dict) -> str:
    return normalize_text(
        " ".join(
            str(job.get(key, ""))
            for key in ("title", "company", "location", "raw_description", "source_name", "ats_source", "discovery_keyword")
        )
    )


def job_page_text(job: dict) -> str:
    return normalize_text(
        " ".join(
            str(job.get(key, ""))
            for key in ("title", "url", "location", "raw_description", "source_name", "ats_source")
        )
    )


def title_looks_like_job(title: str) -> bool:
    title = normalize_text(title)
    if not title:
        return False
    if title in GENERIC_JOB_TITLE_NOISE_EXACT:
        return False
    if title in GENERIC_JOB_TITLE_PRODUCT_EXACT:
        return False
    if title in GENERIC_JOB_TITLE_MARKETING_EXACT:
        return False
    if title in GENERIC_JOB_TITLE_NON_JOB_EXACT:
        return False
    return contains_any(title, JOB_POSTING_TITLE_TERMS) or bool(re.search(r"\b[A-Za-z]{3,}\b(?:\s+[A-Za-z]{2,}){1,4}", title))


def unsupported_foreign_location_terms(job: dict) -> list[str]:
    title_location = normalize_text(f"{job.get('title', '')} {job.get('location', '')}")
    if re.search(r"\b(?:united states|usa|u\.s\.|us)\b", title_location):
        return []
    direct_matches = contains_any(title_location, FOREIGN_LOCATION_TERMS)
    if direct_matches:
        return direct_matches
    text = job_page_text(job)
    if contains_any(text, FOREIGN_REMOTE_US_TERMS):
        return []
    matches = []
    for term in FOREIGN_LOCATION_TERMS:
        if term in text:
            matches.append(term)
    return dedupe(matches)


def job_page_rejection_reasons(job: dict) -> list[str]:
    title = normalize_text(job.get("title"))
    url = normalize_text(job.get("url"))
    text = job_page_text(job)
    reasons = []

    if title in GENERIC_JOB_TITLE_NOISE_EXACT:
        reasons.append("generic_cta_not_job")
    if title in GENERIC_JOB_TITLE_PRODUCT_EXACT:
        reasons.append("product_page")
    if title in GENERIC_JOB_TITLE_MARKETING_EXACT:
        reasons.append("marketing_page")
    if title in GENERIC_JOB_TITLE_NON_JOB_EXACT:
        reasons.append("non_job_page")
    if contains_any(title, GENERIC_CTA_PHRASES) or contains_any(text, GENERIC_CTA_PHRASES):
        reasons.append("generic_cta_not_job")

    if any(part in url for part in (
        "/product/",
        "/products/",
        "/features/",
        "/resources/",
        "/blog/",
        "/customer-stories/",
        "/showroom/",
        "/windows/",
        "/kitchen-sinks/",
        "/privacy/",
        "/terms/",
        "/login/",
        "/contact/",
        "/webinars/",
    )):
        if any(part in url for part in ("/blog/", "/customer-stories/", "/webinars/")):
            reasons.append("marketing_page")
        elif any(part in url for part in ("/product/", "/products/", "/showroom/", "/windows/", "/kitchen-sinks/")):
            reasons.append("product_page")
        else:
            reasons.append("non_job_page")

    if contains_any(text, ("cookie consent", "wpconsent", "script)", "class=", "fill=", "svg", "var ", "addeventlistener", "youtube.com", "youtu.be")):
        reasons.append("cookie_script_noise")

    if contains_any(title, SOFTWARE_ENGINEERING_ROLE_TERMS) or contains_any(text, SOFTWARE_ENGINEERING_ROLE_TERMS):
        reasons.append("software_engineering_role")

    if unsupported_foreign_location_terms(job):
        reasons.append("unsupported_foreign_location")

    if "cloudflare" in text or "developers.cloudflare.com" in text:
        reasons.append("cookie_script_noise")

    return dedupe(reasons)


def likely_job_posting(job: dict) -> bool:
    title = normalize_text(job.get("title"))
    url = normalize_text(job.get("url"))
    text = job_page_text(job)
    reasons = job_page_rejection_reasons(job)
    if reasons:
        return False

    signals = 0
    if title_looks_like_job(title):
        signals += 1
    if any(hint in url for hint in JOB_POSTING_URL_HINTS):
        signals += 1
    if contains_any(text, JOB_POSTING_DESCRIPTION_TERMS):
        signals += 1
    if "apply" in text and contains_any(text, ("responsibilities", "requirements", "qualifications", "benefits")):
        signals += 1
    if contains_any(text, ("job id", "requisition", "req ", "posted", "location", "salary", "benefits", "employment type")):
        signals += 1
    return signals >= 2


def bullets_after(text: str, heading: str, after_heading: str | None = None) -> list[str]:
    search_text = text
    if after_heading:
        marker = re.search(rf"(?im)^#+\s+{re.escape(after_heading)}\s*$", text)
        if marker:
            search_text = text[marker.end() :]

    heading_match = re.search(rf"(?im)^#+\s+{re.escape(heading)}\s*$", search_text)
    if not heading_match:
        return []
    section = search_text[heading_match.end() :]
    next_heading = re.search(r"(?m)^#+\s+", section)
    if next_heading:
        section = section[: next_heading.start()]
    return [match.group(1).strip() for match in re.finditer(r"(?m)^\s*[*-]\s+(.+?)\s*$", section)]


def clean_term(value: str) -> str:
    value = value.strip().strip("`*_")
    value = re.sub(r"[“”]", '"', value)
    return normalize_text(value)


def dedupe(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
