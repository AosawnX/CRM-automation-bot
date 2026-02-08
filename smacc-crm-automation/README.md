# SMACC CRM Automation (Playwright)

Automates customer record cleanup in SMACC (Customers module) using Playwright.

## What it does

For each customer record (paged 100 per page):

- Opens the customer edit form
- Logs Customer Code
- If **Country** is empty, selects **Saudi Arabia** from the autocomplete
- Reads **VAT / Tax ID**
- If VAT is not empty and ID Type is not already **Other ID**
  - Sets ID Type to **Other ID** (`OTH`)
  - Copies VAT into **Buyer ID / ID Number**
- Saves changes (unless `DRY_RUN=True`)
- Re-opens the same record to verify persistence (safety check)
- Keeps pagination stable using the `#ddlPages` page selector

## Safety first

This script changes production data. Use these controls:

- `DRY_RUN=True` to simulate without saving
- `TOTAL_LIMIT` to cap how many records are touched
- `SKIP_FIRST` to resume from a specific offset

## Prerequisites

- Python 3.10+
- A valid `session.json` Playwright storage state (login session)
- Playwright browsers installed

## Setup

### 1) Create a virtual environment (recommended)

**Windows (PowerShell):**
```bash
python -m venv .venv
.venv\Scripts\activate

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install
