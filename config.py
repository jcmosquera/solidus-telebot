"""
Configuration management for the Elliptic Telegram Bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
ELLIPTIC_API_KEY = os.getenv("ELLIPTIC_API_KEY")
ELLIPTIC_API_SECRET = os.getenv("ELLIPTIC_API_SECRET")
ELLIPTIC_URL = "https://aml-api.elliptic.co/v2/wallet/synchronous"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Admin Configuration
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "jcmosquera")  # Default admin

# Dashboard Configuration
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")  # Change this!
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8080"))

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "elliptic_bot.db")

# Usage Limits (Default values)
DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "10"))
DEFAULT_MONTHLY_LIMIT = int(os.getenv("DEFAULT_MONTHLY_LIMIT", "300"))

# Risk Analysis Configuration
RISK_SCORE_THRESHOLD = float(os.getenv("RISK_SCORE_THRESHOLD", "5.0"))
MAX_HOP_DISTANCE = int(os.getenv("MAX_HOP_DISTANCE", "3"))
GAMBLING_HOP_LIMIT = int(os.getenv("GAMBLING_HOP_LIMIT", "2"))
GAMBLING_CONTRIBUTION_THRESHOLD = float(os.getenv("GAMBLING_CONTRIBUTION_THRESHOLD", "3.0"))

# High-Risk Categories
HIGH_RISK_CATEGORIES = {
    "Dark Forum", "Phishing", "Dark Market - Centralised", "Dark Market - Decentralised",
    "Dark Vendor Shop", "Ponzi Scheme", "Ransomware", "Dark Service", "Activist Fundraising",
    "Child Sexual Abuse Material Vendor", "Terrorist Organisation", "OFAC Sanctioned Entity",
    "Criminal Organisation", "Extortion", "Known Criminal", "FinCEN Primary Money Laundering Concern",
    "Shielded", "Mixer", "High Transaction Fee", "Research Chemicals", "Charity", "Scam",
    "Credit Card Data Vendor", "Malware", "Political Campaign", "Reported Loss"
}

# High-Risk Countries (ISO 3166-2)
HIGH_RISK_COUNTRIES = {
    "IR",  # Iran
    "CU",  # Cuba
    "VE",  # Venezuela
    "KP",  # North Korea
    "SY",  # Syria
    "MM",  # Myanmar
    "UA-43",  # Crimea
    "UA-14",  # Donetsk
    "UA-09",  # Luhansk
    "UA-23",  # Zaporizhzhia
    "UA-65",  # Kherson
    "RU",  # Russia
}

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# API Retry Configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))  # seconds
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
