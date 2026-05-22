from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

COMPANIES_FILE = DATA_DIR / "companies.json"
DISCOVERY_SOURCES_FILE = DATA_DIR / "discovery_sources.json"
JOBS_ARCHIVE_FILE = DATA_DIR / "jobs_archive.json"
SEARCH_PROFILE_FILE = DATA_DIR / "search_profile.md"
CANDIDATE_PROFILE_FILE = DATA_DIR / "candidate_profile.md"
DAILY_DIGEST_FILE = OUTPUT_DIR / "daily_digest.md"

HTTP_TIMEOUT_SECONDS = 20
USER_AGENT = "career-opportunity-radar/1.0 (+local personal job monitor)"

DIGEST_MIN_SCORE = 10
DIGEST_MAX_JOBS = 7
