from __future__ import annotations

from realism import evaluate_job
from targeting import (
    contains_any,
    current_targeting,
    is_hard_excluded,
    is_local_or_localizable,
    job_text,
    matching_required_positive_count,
    source_penalty_applies,
)
from utils import posting_age_days


POSITIVE_SIGNALS = {
    "account manager": 7,
    "commercial sales representative": 8,
    "commercial market sales representative": 9,
    "market representative": 7,
    "market sales representative": 8,
    "design consultant": 9,
    "sales consultant": 7,
    "design sales consultant": 9,
    "territory sales representative": 8,
    "project consultant": 7,
    "product specialist": 6,
    "showroom consultant": 6,
    "showroom sales consultant": 9,
    "flooring sales": 9,
    "tile sales": 9,
    "cabinet designer": 10,
    "kitchen and bath designer": 10,
    "countertop sales": 9,
    "window and door sales": 9,
    "glass sales": 9,
    "glazing sales": 9,
    "building materials sales": 8,
    "architectural products sales": 9,
    "a&d representative": 9,
    "architectural representative": 9,
    "architectural sales consultant": 9,
    "builder sales representative": 8,
    "dealer sales representative": 8,
    "specification sales": 8,
    "specifier sales": 8,
    "trade sales representative": 8,
    "trade representative": 8,
    "contractor sales": 8,
    "inside sales representative": 6,
    "commercial interiors sales": 8,
    "sales estimator": 8,
    "surface sales": 8,
    "slab sales": 8,
    "stone sales": 8,
    "porcelain sales": 8,
    "millwork sales": 8,
    "cad designer": 7,
    "solidworks designer": 6,
    "technical designer": 6,
    "drafting technician": 6,
    "cad drafter": 6,
    "millwork designer": 8,
    "commercial interiors designer": 8,
    "estimator cad": 7,
    "design sales support": 7,
    "sales engineer solidworks": 5,
    "solar sales consultant": 5,
    "customer onboarding specialist": 7,
    "implementation specialist": 7,
    "field operations consultant": 7,
    "operations coordinator": 6,
    "project coordinator": 6,
    "smb account executive": 2,
    "mid-market account executive": 1,
    "solutions consultant": 1,
    "associate sales engineer": 1,
    "construction": 5,
    "aec": 5,
    "building materials": 6,
    "commercial interiors": 6,
    "showroom": 6,
    "flooring": 6,
    "tile": 6,
    "cabinet": 6,
    "countertop": 6,
    "window": 5,
    "glass": 5,
    "glazing": 5,
    "kitchen and bath": 7,
    "home improvement": 5,
    "architectural products": 6,
    "building products": 6,
    "quartz": 5,
    "stone": 4,
    "slab": 5,
    "porcelain slab": 6,
    "solid surface": 5,
    "millwork": 6,
    "architectural millwork": 7,
    "finish materials": 6,
    "fixtures": 4,
    "lighting": 4,
    "hardware": 3,
    "commercial flooring": 6,
    "residential flooring": 5,
    "surfaces": 5,
    "building envelope": 5,
    "facade": 5,
    "industrial distribution": 6,
    "facilities operations": 5,
    "lidar": 5,
    "drone": 5,
    "reality capture": 5,
    "digital twin": 4,
    "field operations": 5,
    "workflow": 4,
    "contractor": 4,
    "trade sales": 5,
    "company vehicle": 9,
    "branded vehicle": 8,
    "fleet vehicle": 8,
    "mileage reimbursement": 7,
    "car allowance": 7,
    "design center": 6,
    "local branch": 5,
    "denver office": 8,
    "denver showroom": 9,
    "denver territory": 9,
    "aia": 4,
    "iida": 4,
    "idcec": 4,
    "architects": 5,
    "designers": 4,
    "specifiers": 5,
    "trade partners": 5,
    "builders": 4,
    "installers": 3,
    "fabricators": 4,
    "customer meetings": 5,
    "customer tracking": 4,
    "homeowner-facing": 5,
    "homeowner facing": 5,
    "architect-facing": 5,
    "architect facing": 5,
    "estimating": 5,
    "estimate": 3,
    "training provided": 5,
    "base salary": 5,
    "base + bonus": 6,
    "base and bonus": 6,
    "base plus bonus": 6,
    "base pay": 5,
    "salary range": 4,
    "hourly": 4,
    "plus commission": 4,
    "hourly + commission": 5,
    "benefits": 4,
    "paid training": 5,
    "actively hiring": 5,
    "urgently hiring": 5,
    "mapping": 3,
    "visualization": 3,
    "technical demos": 4,
    "demo": 1,
    "presentations": 1,
    "customer-facing": 4,
    "customer facing": 4,
    "onboarding": 4,
    "consultative": 4,
    "relationship-driven": 4,
    "relationship driven": 4,
    "denver": 8,
    "hybrid": 2,
    "on-site": 3,
    "onsite": 3,
}

NEGATIVE_SIGNALS = {
    "sdr": -7,
    "sales development representative": -7,
    "commission only": -10,
    "door-to-door": -10,
    "door to door": -10,
    "own vehicle required": -8,
    "own car mandatory": -10,
    "must have reliable vehicle": -10,
    "cold calling quota": -6,
    "insurance sales": -10,
    "canvassing": -9,
    "cdl": -10,
    "warehouse-only": -9,
    "installer-only": -9,
    "laborer-only": -9,
    "nationwide territory": -8,
    "heavy travel": -8,
    "meddic": -6,
    "clari": -5,
    "gong": -4,
    "enterprise book": -8,
    "enterprise-only": -10,
    "fortune 500": -8,
    "fortune-500": -8,
    "heavy outbound": -8,
    "call-center": -8,
    "requires 5+ years saas": -10,
    "5+ years saas": -10,
    "8+ years": -12,
    "draw only": -12,
    "draw-only": -12,
    "unlimited earning potential": -9,
}

TITLE_NEGATIVE_SIGNALS = {
    "enterprise": -14,
    "enterprise account executive": -28,
    "strategic account executive": -28,
    "senior strategic": -30,
    "senior strategic customer success manager": -34,
    "enterprise customer success": -24,
    "large enterprise": -20,
    "senior sales engineer": -24,
    "senior solutions engineer": -24,
    "director": -28,
    "head of": -28,
    "advisory": -22,
    "principal": -22,
    "vp": -28,
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
    text = job_text(job)
    score = 0
    tags = []
    title = str(job.get("title", "")).lower()
    location = str(job.get("location", "")).lower()
    targeting = current_targeting()

    hard_excluded, exclusions = is_hard_excluded(job)
    if hard_excluded:
        score -= 40
        tags.append("-40 hard exclusion: " + ", ".join(exclusions[:3]))

    for phrase, weight in POSITIVE_SIGNALS.items():
        if phrase in text:
            score += weight
            tags.append(f"+{weight} {phrase}")

    for phrase in targeting["role_positive"]:
        if phrase in title:
            weight = 4 if phrase in {"solutions consultant", "associate sales engineer"} else 6
            score += weight
            tags.append(f"+{weight} profile target title: {phrase}")
        elif phrase in text:
            weight = 2 if phrase in {"solutions consultant", "associate sales engineer"} else 3
            score += weight
            tags.append(f"+{weight} profile target term: {phrase}")

    for phrase in targeting["industry_positive"]:
        if phrase in text:
            score += 5
            tags.append(f"+5 profile industry: {phrase}")

    for phrase, weight in NEGATIVE_SIGNALS.items():
        if phrase in text:
            score += weight
            tags.append(f"{weight} {phrase}")

    for phrase in targeting["role_negative"]:
        if phrase in title:
            score -= 12
            tags.append(f"-12 profile penalized title: {phrase}")
        elif phrase in text:
            score -= 6
            tags.append(f"-6 profile penalized term: {phrase}")

    for phrase in targeting["industry_negative"]:
        if phrase in text:
            score -= 6
            tags.append(f"-6 profile penalized industry: {phrase}")

    for phrase, weight in TITLE_NEGATIVE_SIGNALS.items():
        if phrase in title:
            score += weight
            tags.append(f"{weight} title: {phrase}")

    realism = evaluate_job(job)
    if job.get("remote") and not realism["physical_industry_software_signal"] and not realism["side_cash_signal"]:
        score -= 16
        tags.append("-16 generic remote flag")

    if source_penalty_applies(job) and not realism["physical_industry_software_signal"] and not realism["side_cash_signal"]:
        score -= 12
        tags.append("-12 remote/generic source penalty")

    score += int(realism["realism_score_delta"])
    delta = int(realism["realism_score_delta"])
    sign = "+" if delta >= 0 else ""
    tags.append(f"{sign}{delta} practical fit: {realism['practical_fit']}")
    tags.append(f"domain barrier: {realism['domain_barrier']}")
    tags.append(f"transferability score: {realism['transferability_score']}")
    tags.append(f"hireability score: {realism['hireability_score']}")
    for note in realism["realism_notes"][:3]:
        tags.append(note)
    if realism["non_denver_territory_signal"]:
        score -= 55
        tags.append("-55 non-Denver territory")
    if realism["seniority_stretch_signal"]:
        score -= 18
        tags.append("-18 senior/enterprise stretch")
    if realism["denver_metro_signal"]:
        score += 18
        tags.append("+18 Denver metro realism")
    if realism["base_pay_signal"]:
        score += 8
        tags.append("+8 base/stable pay structure")
    else:
        score -= 5
        tags.append("-5 unclear compensation")
    if realism["vehicle_support_signal"]:
        score += 8
        tags.append("+8 vehicle/travel support")
    if realism["physical_industry_software_signal"] and realism["practical_fit_label"] in {"Strong Construction Tech Fit", "Remote Physical-Industry Stretch", "Realistic Stretch"}:
        score += 10
        tags.append("+10 physical-industry software context")
    if realism["remote_only_signal"] and realism["physical_industry_software_signal"]:
        score -= 12
        tags.append("-12 remote physical-industry secondary lane")
    if realism["remote_saas_signal"] and not realism["physical_industry_software_signal"] and realism["practical_fit_label"] in {"Remote Stretch", "Semantic Match Only"}:
        score -= 30
        tags.append("-30 generic remote SaaS stretch")
    elif realism["remote_only_signal"] and realism["practical_fit_label"] == "Remote Stretch":
        score -= 10
        tags.append("-10 generic remote stretch")
    if realism["side_cash_signal"] and "side-cash pay under $15/hr" in realism["realism_notes"]:
        score -= 14
        tags.append("-14 side-cash pay under $15/hr")

    required_matches = matching_required_positive_count(text)
    if required_matches >= 2:
        score += 8
        tags.append("+8 required positives >=2")
    elif required_matches == 1:
        score += 2
        tags.append("+2 required positive")
    else:
        score -= 8
        tags.append("-8 missing required positives")

    if is_local_or_localizable(job) or realism["physical_industry_software_signal"] or realism["side_cash_signal"]:
        score += 8
        tags.append("+8 local/localizable or secondary lane")
    else:
        score -= 10
        tags.append("-10 not local/localizable")

    strong_locations = contains_any(location, targeting["locations_strong"])
    if strong_locations:
        score += 18
        tags.append("+18 target metro: " + ", ".join(strong_locations[:3]))

    moderate_locations = contains_any(text, targeting["locations_moderate"])
    if moderate_locations:
        score += 8
        tags.append("+8 local work pattern: " + ", ".join(moderate_locations[:3]))

    negative_locations = contains_any(text, targeting["locations_negative"])
    if negative_locations:
        score -= 8
        tags.append("-8 location penalty: " + ", ".join(negative_locations[:3]))

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
        "building materials",
        "commercial interiors",
        "contractor services",
        "facilities operations",
        "industrial distribution",
        "glass and glazing",
        "flooring",
        "tile",
        "cabinets",
        "countertops",
        "windows and doors",
        "kitchen and bath",
        "home improvement",
        "construction suppliers",
        "mep",
        "hvac",
        "plumbing supply",
        "electrical supply",
        "solar home improvement",
    }:
        category_boost = 8 if category in {"building materials", "commercial interiors", "contractor services", "facilities operations", "industrial distribution", "glass and glazing", "flooring", "tile", "cabinets", "countertops", "windows and doors", "kitchen and bath", "home improvement", "construction suppliers", "mep", "hvac", "plumbing supply", "electrical supply", "solar home improvement"} else 2
        score += category_boost
        tags.append(f"+{category_boost} company category: {category}")

    if int(job.get("company_priority") or 0) >= 9:
        score += 1
        tags.append("+1 priority company")

    age = posting_age_days(job.get("date_posted"), job.get("first_seen"))
    if age is None:
        tags.append("no posting date")
    elif age <= 7:
        score += 6
        tags.append("+6 fresh under 7 days")
    elif age <= 14:
        score += 3
        tags.append("+3 fresh under 14 days")
    elif age >= 30:
        score -= 3
        tags.append("-3 older than 30 days")

    return score, tags
