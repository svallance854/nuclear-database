"""Configuration settings for nuclear database ingestion scripts."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "nuclear.db"))

# USAspending API (no key required for public endpoints)
USASPENDING_API_BASE = "https://api.usaspending.gov/api/v2"

# Nuclear-relevant NAICS codes
NUCLEAR_NAICS_CODES = [
    "221113",  # Nuclear Electric Power Generation
    "541330",  # Engineering Services
    "562211",  # Hazardous Waste Treatment and Disposal
    "541715",  # R&D in Physical, Engineering, and Life Sciences
    "237130",  # Power and Communication Line Construction
]

# Agencies of interest
NUCLEAR_AGENCIES = ["DOE", "NRC", "DOD"]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Scheduler
SCHEDULER_INTERVAL_HOURS = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "168"))  # weekly

# Notifications
NOTIFY_METHOD = os.getenv("NOTIFY_METHOD", "log")  # "log", "email", or "slack"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL_FROM = os.getenv("NOTIFY_EMAIL_FROM", "")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")  # comma-separated
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# API server
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5000"))
API_KEY = os.getenv("API_KEY", "")

# NRC ADAMS public search
ADAMS_SEARCH_URL = "https://adams.nrc.gov/wba/services/search/advanced/nrc"
