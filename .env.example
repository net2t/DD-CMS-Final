# =============================================================================
# DamaDam Scraper - Environment Configuration Template
# =============================================================================
# 
# INSTRUCTIONS:
# 1. Copy this file: cp .env.example .env
# 2. Replace placeholder values with your actual credentials
# 3. NEVER commit the .env file to git
# 
# =============================================================================

# =============================================================================
# DamaDam Account Credentials
# =============================================================================

# Primary Account (Required)
# Your main DamaDam login credentials
DAMADAM_USERNAME=your_username_here
DAMADAM_PASSWORD=your_password_here

# Backup Account (Highly Recommended)
# Fallback account to prevent rate limiting and account blocking
# Leave empty if you don't have a backup account
DAMADAM_USERNAME_2=
DAMADAM_PASSWORD_2=

# =============================================================================
# Google Sheets Configuration
# =============================================================================

# Google Sheets URL (Required)
# Full URL of your Google Sheet
# Example: https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit

# Google Service Account Credentials
# Path to your credentials.json file (for local development)
GOOGLE_APPLICATION_CREDENTIALS=credentials.json

# Google Credentials JSON (for GitHub Actions only)
# Full JSON content of credentials.json file
# Leave empty for local development, set in GitHub Secrets for CI/CD
GOOGLE_CREDENTIALS_JSON=

# =============================================================================
# Scraping Configuration
# =============================================================================

# Maximum Profiles Per Run
# 0 = unlimited (scrape all available)
# Recommended: 20-50 for online mode, 0 for target mode
MAX_PROFILES_PER_RUN=0

# Batch Processing Size
# Number of profiles to process in each batch
# Recommended: 20
BATCH_SIZE=20

# Request Delays (seconds)
# Add delays between requests to avoid detection and rate limiting
MIN_DELAY=0.3
MAX_DELAY=0.5

# Page Load Timeout (seconds)
# How long to wait for pages to load before timing out
PAGE_LOAD_TIMEOUT=30

# Sheet Write Delay (seconds)
# Delay between Google Sheets API writes to avoid rate limiting
SHEET_WRITE_DELAY=1.0

# =============================================================================
# Browser Configuration (Advanced)
# =============================================================================

# ChromeDriver Path (Optional)
# Leave empty to use system ChromeDriver
# Set this if you want to use a specific ChromeDriver version
CHROMEDRIVER_PATH=

# =============================================================================
# Platform Detection (Automatic)
# =============================================================================

# GitHub Actions Detection
# Automatically set by GitHub Actions, no need to configure
# GITHUB_ACTIONS=true

# =============================================================================
# Notes
# =============================================================================
#
# • Backup Account: Highly recommended to prevent account blocking from 
#   repeated logins. The scraper will automatically switch to the backup
#   account if the primary account fails.
#
# • Rate Limiting: If you encounter Google Sheets API rate limits (429 errors),
#   increase SHEET_WRITE_DELAY to 2.0 or higher.
#
# • Browser Headless: The scraper runs in headless mode by default.
#   This cannot be changed via environment variables.
#
# • Security: NEVER commit .env file to git. It's already in .gitignore.
#
# =============================================================================
