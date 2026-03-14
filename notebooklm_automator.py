import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

NOTEBOOKLM_URL = "https://notebooklm.google.com"
PROFILE_DIR = str(Path.home() / ".notebooklm_profile")
SOURCE_LIMIT = 50


def _is_logged_in(page: Page) -> bool:
    """Check if the user is logged into Google/NotebookLM."""
    try:
        # If we see a sign-in button or are redirected to accounts.google.com, not logged in
        page.wait_for_load_state("networkidle", timeout=10000)
        return "accounts.google.com" not in page.url
    except PlaywrightTimeoutError:
        return "accounts.google.com" not in page.url


def _create_new_notebook(page: Page, title: str) -> None:
    """Click 'New notebook' and optionally set a title."""
    print("Creating new notebook...")

    # Click the "New notebook" button
    new_notebook_btn = page.get_by_role("button", name="New notebook")
    new_notebook_btn.wait_for(state="visible", timeout=15000)
    new_notebook_btn.click()

    # Wait for the notebook to open (sources panel or empty state)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)

    # Try to set the notebook title if a title field is visible
    if title:
        try:
            title_input = page.get_by_placeholder("Untitled notebook")
            if title_input.is_visible():
                title_input.click()
                title_input.fill(title)
                title_input.press("Enter")
                time.sleep(1)
        except Exception:
            # Title field may not be immediately available; skip
            pass

    print(f"Notebook created. Title: {title or '(default)'}")


def _add_source_url(page: Page, url: str, index: int, total: int) -> bool:
    """Add a single YouTube URL as a source in NotebookLM."""
    try:
        # Click the "Add source" or "+" button — NotebookLM uses various labels
        # Try multiple selectors for resilience
        add_btn = None
        for selector in [
            'button[aria-label="Add source"]',
            'button:has-text("Add source")',
            'button[aria-label="Add"]',
            '[data-testid="add-source-button"]',
        ]:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    add_btn = btn
                    break
            except Exception:
                continue

        if add_btn is None:
            # Fallback: find any button with "Add" text
            add_btn = page.get_by_role("button", name="Add").first

        add_btn.click()
        time.sleep(1)

        # Select "Website" / URL option in the source type dialog
        for selector in [
            'button:has-text("Website")',
            '[aria-label="Website"]',
            'button:has-text("URL")',
            '[role="menuitem"]:has-text("Website")',
            '[role="option"]:has-text("Website")',
        ]:
            try:
                opt = page.locator(selector).first
                if opt.is_visible(timeout=2000):
                    opt.click()
                    break
            except Exception:
                continue

        time.sleep(1)

        # Find the URL input field and type the URL
        url_input = None
        for selector in [
            'input[placeholder*="URL"]',
            'input[placeholder*="url"]',
            'input[type="url"]',
            'textarea[placeholder*="URL"]',
            'input[aria-label*="URL"]',
        ]:
            try:
                inp = page.locator(selector).first
                if inp.is_visible(timeout=2000):
                    url_input = inp
                    break
            except Exception:
                continue

        if url_input is None:
            url_input = page.get_by_role("textbox").first

        url_input.click()
        url_input.fill(url)
        time.sleep(0.5)

        # Click Insert / Add / Submit button
        for selector in [
            'button:has-text("Insert")',
            'button:has-text("Add")',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ]:
            try:
                btn = page.locator(selector).last
                if btn.is_visible(timeout=2000):
                    btn.click()
                    break
            except Exception:
                continue

        # Wait for source to be processed
        time.sleep(3)
        print(f"  [{index}/{total}] Added: {url}")
        return True

    except Exception as e:
        print(f"  [{index}/{total}] FAILED: {url} — {e}")
        return False


def add_playlist_to_notebooklm(video_urls: list[str], notebook_title: str = "") -> None:
    """Open NotebookLM and add all video URLs as sources to a new notebook."""

    if len(video_urls) > SOURCE_LIMIT:
        print(
            f"Warning: Playlist has {len(video_urls)} videos but NotebookLM recommends "
            f"<= {SOURCE_LIMIT} sources per notebook. Only first {SOURCE_LIMIT} will be added."
        )
        video_urls = video_urls[:SOURCE_LIMIT]

    with sync_playwright() as p:
        print(f"Launching browser with persistent profile at: {PROFILE_DIR}")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto(NOTEBOOKLM_URL)

        if not _is_logged_in(page):
            print("\nNot logged in. Please log into your Google account in the browser window.")
            input("Press Enter here once you are logged in and see the NotebookLM homepage... ")
            page.goto(NOTEBOOKLM_URL)
            page.wait_for_load_state("networkidle", timeout=15000)

        _create_new_notebook(page, notebook_title)

        total = len(video_urls)
        added = 0
        failed = 0

        print(f"\nAdding {total} YouTube videos as sources...")
        for i, url in enumerate(video_urls, start=1):
            success = _add_source_url(page, url, i, total)
            if success:
                added += 1
            else:
                failed += 1
            # Polite delay between requests
            time.sleep(2)

        print(f"\nDone! Added {added}/{total} sources. Failed: {failed}")
        print(f"Notebook URL: {page.url}")
        print("The browser will stay open so you can review your notebook.")
        input("Press Enter to close the browser...")
        browser.close()
