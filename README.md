# SMACC CRM Automation (Playwright)

A Playwright-based automation script for cleaning and normalizing customer records in a web-based CRM system.

This project automates repetitive CRM maintenance tasks such as fixing missing country fields and standardizing ID information, while preserving pagination state and applying strong safety controls to protect production data.

---

## What This Automation Does

For customer records in the **Customers module** of the CRM:

* Loads customers **100 records per page**
* Iterates safely across all pages
* Skips a configurable number of initial records (resume support)
* For each customer:

  * Opens the Edit page
  * Logs **Customer Code**
  * If **Country** is empty:

    * Selects **Saudi Arabia** from autocomplete
  * Reads **VAT / Tax ID**
  * If VAT exists and ID Type is not `Other ID`:

    * Sets ID Type to **Other ID (OTH)**
    * Copies VAT into **Buyer ID / ID Number**
  * Saves changes (unless in dry-run mode)
  * Re-opens the same record to verify persistence
* Preserves pagination state using the page selector
* Stops safely at a defined record limit

---

## Safety Features

This script is designed for **production safety**:

* `DRY_RUN` mode (no saving)
* `TOTAL_LIMIT` hard cap on processed records
* `SKIP_FIRST` for resume/restart support
* Persistence verification after save
* Immediate stop on authorization errors
* Screenshots captured on fatal errors
* Session-based authentication (no credentials stored)

---

## Tech Stack

* **Python 3.10+**
* **Playwright (sync API)**
* Browser automation (Chromium)
* Session-based authentication via `session.json`

---

## Project Structure

```
smacc-crm-automation/
│
├─ src/
│  └─ update_customers.py
│
├─ README.md
├─ requirements.txt
├─ .gitignore
└─ session.json   (local only, not committed)
```

---

## Configuration Parameters

Edit these at the top of `src/update_customers.py`:

```python
TOTAL_LIMIT = 2735   # Max records to process
SKIP_FIRST = 98      # Skip first N records (resume support)
DRY_RUN = False      # True = no Save clicks
SLOW_MO_MS = 120     # Browser speed (0 = fastest)
DELAY_SECONDS = 0.0  # Optional per-record delay
```

---

## Setup Instructions

### 1️⃣ Create virtual environment (recommended)

**Windows**

```bat
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

---

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
python -m playwright install
```

---

## 🔐 Creating `session.json`

This project uses an existing authenticated browser session.

Create `session.json` **once** using a temporary script:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("<CRM_LOGIN_URL>")
    print("Log in manually, then press Enter here...")
    input()

    context.storage_state(path="session.json")
    browser.close()
```

---

## ▶️ Running the Automation

```bash
python src/update_customers.py
```

---

## 📤 Output & Logging

* Detailed timestamped logs printed to the terminal
* Screenshots saved automatically on fatal errors
* Script halts immediately if unsafe conditions are detected

---

## ⚠️ Notes & Limitations

* This automation depends on the CRM’s current HTML structure
* Selector changes may require script updates
* Always test with a low `TOTAL_LIMIT` first

---

## 📜 License

MIT License (add `LICENSE` file if required)
