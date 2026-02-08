from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # Enter login page url below
    page.goto("")

    print("🔐 Log in manually in the opened browser")
    print("⏳ Press ENTER here AFTER login is fully complete")

    input()

    # Save session
    context.storage_state(path="session.json")
    print("session.json saved")

    browser.close()
