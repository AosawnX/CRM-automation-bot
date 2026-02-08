from playwright.sync_api import sync_playwright
from datetime import datetime
import os

# ===================== CONFIG =====================
TOTAL_LIMIT = 2735
SKIP_FIRST = 1950
DRY_RUN = False

# Speed controls
SLOW_MO_MS = 0        # 0 = fastest, 80-150 = watchable, 300+ = slow
DELAY_SECONDS = 0.0     # extra sleep after each record (set 0 for fast)
VERBOSE_LOGS = True     # set False to reduce logs
# =================================================

SESSION_FILE = "session.json"
CUSTOMERS_URL = ""

processed = 0


def log(msg):
    if not VERBOSE_LOGS:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def is_unauthorized(page):
    content = page.locator("body").inner_text().lower()
    return (
        "unauthorized access" in content or
        "attempted to perform an unauthorized operation" in content
    )


def wait_until_enabled(page, css_id, timeout_ms=10000):
    log(f"Waiting for field #{css_id} to become enabled")
    page.wait_for_function(
        """(id) => {
            const el = document.getElementById(id);
            return el && !el.disabled;
        }""",
        arg=css_id,
        timeout=timeout_ms
    )
    log(f"Field #{css_id} is now enabled")


def goto_list(page):
    log("Navigating to Customers list (module=4)")
    page.goto(CUSTOMERS_URL, wait_until="domcontentloaded")

    current = page.url.lower()
    log(f"Current URL: {page.url}")

    if "login.aspx" in current:
        page.screenshot(path="NOT_LOGGED_IN.png", full_page=True)
        raise RuntimeError("Redirected to login. Session is invalid or expired.")

    page.wait_for_selector("a.EditDetailsPageListIcon", timeout=30000)
    log("Customers list loaded. Edit icons detected.")


def ensure_100_per_page_once(page):
    page.wait_for_selector("#ddlPageCount", timeout=30000)
    current = page.input_value("#ddlPageCount").strip()
    log(f"Page size (current): {current}")

    if current != "100":
        log("Setting page size to 100")
        page.select_option("#ddlPageCount", value="100")
        
        page.wait_for_selector("a.EditDetailsPageListIcon", timeout=30000)
        log("Page size set to 100 and list refreshed")
    else:
        log("Page size already 100")


def get_current_page_num(page):
    page.wait_for_selector("#ddlPages", timeout=30000)
    val = page.input_value("#ddlPages").strip()
    try:
        return int(val)
    except Exception:
        return 1


def get_max_page_num(page):
    page.wait_for_selector("#ddlPages", timeout=30000)
    options = page.locator("#ddlPages option")
    n = options.count()
    if n == 0:
        return 1
    last_val = options.nth(n - 1).get_attribute("value") or "1"
    try:
        return int(last_val)
    except Exception:
        return 1


def go_to_page(page, page_num: int):
    page.wait_for_selector("#ddlPages", timeout=30000)
    max_page = get_max_page_num(page)

    if page_num > max_page:
        log(f"Reached end of dataset. Requested page {page_num} > max {max_page}")
        return False

    log(f"Switching to page {page_num} via #ddlPages")
    page.select_option("#ddlPages", value=str(page_num))

    
    page.wait_for_function(
        """(target) => {
            const ddl = document.querySelector("#ddlPages");
            return ddl && ddl.value === String(target);
        }""",
        arg=page_num,
        timeout=30000
    )

    page.wait_for_selector("a.EditDetailsPageListIcon", timeout=30000)

    now = get_current_page_num(page)
    log(f"Now on page {now}")
    return now == page_num


def back_to_list(page, desired_page: int):
    log(f"Returning to Customers list (keep page={desired_page})")

    try:
        page.go_back(wait_until="domcontentloaded")
    except Exception:
        pass

    if "customerspage.aspx" not in page.url.lower():
        log("Not on list after go_back, loading list URL.")
        goto_list(page)
        ensure_100_per_page_once(page)

    page.wait_for_selector("#ddlPages", timeout=30000)
    current_page = get_current_page_num(page)
    log(f"List page after return: {current_page}")

    if current_page != desired_page:
        log(f"Page reset detected. Forcing back to page {desired_page}")
        ok = go_to_page(page, desired_page)
        if not ok:
            page.screenshot(path="BACK_TO_LIST_FAILED.png", full_page=True)
            raise RuntimeError(f"Failed to force list to page {desired_page}")

    log("Returned to list with correct page preserved")


def set_country_saudi_if_empty(page, tag=""):
    page.wait_for_selector("#cpBulk_cpForm_CountryName", timeout=20000)
    country = page.input_value("#cpBulk_cpForm_CountryName").strip()
    log(f"Country (current): {country or '<EMPTY>'}")

    if country:
        return False

    log("Country is empty. Selecting Saudi Arabia (from autocomplete)")

    country_input = page.locator("#cpBulk_cpForm_CountryName").first
    country_input.click()
    country_input.fill("Saudi")

    
    page.wait_for_timeout(600)

    page.wait_for_selector("ul.ui-autocomplete li", timeout=15000)

    
    page.wait_for_timeout(600)

    option = page.locator("ul.ui-autocomplete li:has-text('Saudi Arabia')").first
    if option.count() == 0:
        page.screenshot(path=f"COUNTRY_AUTOCOMPLETE_NOT_FOUND{('_'+str(tag)) if tag else ''}.png", full_page=True)
        raise RuntimeError("Saudi Arabia not found in country autocomplete list")

    option.click()


    page.wait_for_timeout(300)
    country_input.press("Tab")
    page.wait_for_timeout(500)

    country_after = page.input_value("#cpBulk_cpForm_CountryName").strip()
    log(f"Country (after): {country_after or '<EMPTY>'}")
    return True


def click_save(page, tag):
    log("Clicking Save button")
    save_btn = page.locator(
        "button:has-text('Save'), input[type='submit'][value*='Save'], input[type='button'][value*='Save']"
    ).first

    if save_btn.count() == 0:
        page.screenshot(path=f"SAVE_NOT_FOUND_{tag}.png", full_page=True)
        raise RuntimeError("Save button not found")

    save_btn.click()
    
    page.wait_for_timeout(150)  
    if is_unauthorized(page):
        page.screenshot(path=f"UNAUTHORIZED_AFTER_SAVE_{tag}.png", full_page=True)
        raise RuntimeError("Unauthorized after save attempt")


with sync_playwright() as p:
    if not os.path.exists(SESSION_FILE):
        raise RuntimeError("session.json missing. Create it first.")

    log("Launching browser")
    browser = p.chromium.launch(headless=False, slow_mo=SLOW_MO_MS)

    context = browser.new_context(storage_state=SESSION_FILE)
    page = context.new_page()

    goto_list(page)
    ensure_100_per_page_once(page)

    index_in_page = 0
    global_index = 0
    current_page = get_current_page_num(page)

    while processed < TOTAL_LIMIT:
        try:
            # Page boundary
            if index_in_page >= 100:
                current_page += 1
                ok = go_to_page(page, current_page)
                if not ok:
                    break
                index_in_page = 0

            edit_links = page.locator("a.EditDetailsPageListIcon")
            count = edit_links.count()

            if count == 0:
                log("No editable records on this page")
                break

            if index_in_page >= count:
                current_page += 1
                ok = go_to_page(page, current_page)
                if not ok:
                    break
                index_in_page = 0
                continue

            # Global skip
            if global_index < SKIP_FIRST:
                log(f"Skipping record {global_index + 1}/{SKIP_FIRST} (no edit)")
                global_index += 1
                index_in_page += 1
                continue

            log(
                f"Processing global_seen={global_index + 1} "
                f"processed={processed + 1}/{TOTAL_LIMIT} "
                f"page={current_page} page_index={index_in_page + 1}"
            )

            log("Clicking Edit icon")
            edit_links.nth(index_in_page).click()
            page.wait_for_selector("#cpBulk_cpForm_CustomerCode", timeout=20000)

            if is_unauthorized(page):
                page.screenshot(path=f"UNAUTHORIZED_{processed+1}.png", full_page=True)
                raise RuntimeError("Unauthorized access on edit page")

            customer_code = page.input_value("#cpBulk_cpForm_CustomerCode").strip()
            log(f"Customer Code: {customer_code or '<EMPTY>'}")

            country_changed = set_country_saudi_if_empty(page, tag=processed + 1)

            page.wait_for_selector("#cpBulk_cpForm_VATNumber", timeout=20000)
            vat = page.input_value("#cpBulk_cpForm_VATNumber").strip()
            log(f"Read VAT value: {'EMPTY' if not vat else vat}")

            id_label = ""
            try:
                id_label = page.locator("select#OtherBuyerID option:checked").inner_text().strip()
            except Exception:
                pass
            log(f"Current ID Type: {id_label or '<not selected>'}")

            
            if not vat:
                log("VAT empty. Skipping ID update.")
                if not DRY_RUN and country_changed:
                    click_save(page, processed + 1)
                back_to_list(page, current_page)

                processed += 1
                global_index += 1
                index_in_page += 1
                if DELAY_SECONDS > 0:
                    page.wait_for_timeout(int(DELAY_SECONDS * 1000))
                continue

            
            if id_label == "Other ID":
                log("ID Type already 'Other ID'. Skipping ID change.")
                if not DRY_RUN and country_changed:
                    click_save(page, processed + 1)
                back_to_list(page, current_page)

                processed += 1
                global_index += 1
                index_in_page += 1
                if DELAY_SECONDS > 0:
                    page.wait_for_timeout(int(DELAY_SECONDS * 1000))
                continue

            
            log("Updating ID Type to 'Other ID'")
            page.select_option("select#OtherBuyerID", value="OTH")

            wait_until_enabled(page, "BuyerIDValue", timeout_ms=15000)

            log("Copying VAT to Buyer ID field")
            page.locator("#BuyerIDValue").first.fill(vat)

            if DRY_RUN:
                log("DRY RUN enabled. Save skipped.")
            else:
                click_save(page, processed + 1)

                
                log("Re-opening record to confirm persistence")
                back_to_list(page, current_page)
                page.wait_for_selector("a.EditDetailsPageListIcon", timeout=30000)
                page.locator("a.EditDetailsPageListIcon").nth(index_in_page).click()
                page.wait_for_selector("#BuyerIDValue", timeout=20000)

                re_buyer_id = page.input_value("#BuyerIDValue").strip()
                if re_buyer_id != vat:
                    page.screenshot(path=f"VERIFY_FAILED_{processed+1}.png", full_page=True)
                    raise RuntimeError("Persistence verification failed after re-open")

            log("Record done")
            back_to_list(page, current_page)

            processed += 1
            global_index += 1
            index_in_page += 1
            if DELAY_SECONDS > 0:
                page.wait_for_timeout(int(DELAY_SECONDS * 1000))

        except Exception as e:
            page.screenshot(path="FATAL_ERROR.png", full_page=True)
            log(f"FATAL ERROR: {e}")
            log("Automation stopped to protect PROD")
            raise

    log(f"Test complete. Records processed: {processed}")
    browser.close()


