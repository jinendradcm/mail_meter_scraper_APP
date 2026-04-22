import pandas as pd
import json
import asyncio
import os
import time
from playwright.async_api import async_playwright

BASE_URL = "https://mailmeteor.com/tools/email-finder"
MAX_RETRIES = 3

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# Column Detection
# -----------------------------
def detect_columns(df):
    name_candidates = []
    domain_candidates = []

    for col in df.columns:
        col_lower = col.lower().strip()

        # --- Heuristic 1: column name matching ---
        if any(k in col_lower for k in ["name", "full", "person", "contact"]):
            name_candidates.append(col)

        if any(k in col_lower for k in ["domain", "website", "company", "url"]):
            domain_candidates.append(col)

    # --- Heuristic 2: fallback using data pattern ---
    if not name_candidates or not domain_candidates:
        for col in df.columns:
            sample_values = df[col].dropna().astype(str).head(10)

            name_score = 0
            domain_score = 0

            for val in sample_values:
                val = val.strip()

                # Name pattern: contains space, no digits
                if " " in val and not any(c.isdigit() for c in val):
                    name_score += 1

                # Domain pattern: contains dot, no spaces
                if "." in val and " " not in val:
                    domain_score += 1

            if name_score >= 5:
                name_candidates.append(col)

            if domain_score >= 5:
                domain_candidates.append(col)

    if not name_candidates or not domain_candidates:
        raise Exception(f"Could not detect columns automatically. Columns found: {df.columns.tolist()}")

    return name_candidates[0], domain_candidates[0]

# -----------------------------
# Playwright helpers
# -----------------------------
async def open_clean_page(page):
    url = f"{BASE_URL}?r={int(time.time()*1000)}"
    print("Opening:", url)

    await page.goto(url, wait_until="domcontentloaded", timeout=30000)

    # fallback reload
    if page.url == "about:blank":
        print("Retrying page load...")
        await page.goto(url, wait_until="domcontentloaded")

    await page.wait_for_selector("#fullName", timeout=15000)
    await page.wait_for_selector("#domain", timeout=15000)

async def run_search(page, name, domain):
    # clear inputs fully
    await page.fill("#fullName", "")
    await page.fill("#domain", "")

    await page.click("#fullName")
    await page.keyboard.type(name, delay=1)

    await page.click("#domain")
    await page.keyboard.type(domain, delay=1)

    # click FIND EMAIL button and wait for response
    try:
        async with page.expect_response(lambda r: "email-finder" in r.url or "api" in r.url, timeout=20000):
            await page.click("form#email-finder-form button[type='submit']")
    except:
        # Fallback if response listener misses it
        await page.click("form#email-finder-form button[type='submit']")

    await page.wait_for_selector("div.email-result-card", timeout=20000)

async def extract_email(page):
    try:
        email = await page.locator("span.email-finder__text.text-secondary").inner_text()
        if "@" in email:
            return email
    except:
        pass
    return None

# -----------------------------
# New Extraction Helpers
# -----------------------------
async def get_state(page):
    try:
        card = page.locator("div.email-result-card").first
        
        title = ""
        try:
            title = (await card.locator("h5 span").inner_text()).strip().lower()
        except:
            title = ""

        if "no results found" in title:
            return "NOT_FOUND"

        if "searching" in title:
            return "SEARCHING"

        try:
            email_text = (await card.locator("span.email-finder__text.text-secondary").inner_text()).strip()
            if "@" in email_text:
                return "FOUND"
        except:
            pass

        return "UNKNOWN"
    except:
        return "UNKNOWN"

async def extract_email_data(page):
    card = page.locator("div.email-result-card").first

    found_name = None
    email = None
    status = None

    try:
        found_name = (await card.locator("h5 span").inner_text()).strip()
        if found_name.lower() in ["searching...", "no results found"]:
            found_name = None
    except:
        pass

    try:
        email_text = (await card.locator("span.email-finder__text.text-secondary").inner_text()).strip()
        if "@" in email_text:
            email = email_text
    except:
        pass

    try:
        # User snippet used div.chip
        status_text = (await card.locator("div.chip").inner_text()).strip()
        if status_text:
            status = status_text.lower()
    except:
        # Fallback to my previous badge/success logic if chip not found
        try:
            status = await page.locator("div.email-result-card .badge, div.email-result-card .text-success").first.inner_text()
        except:
            status = "Unknown"

    return found_name, email, status.strip() if status else "Unknown"

# -----------------------------
# Scrape one
# -----------------------------
async def scrape_one(page, name, domain, worker_id):
    result = {
        "input_name": name,
        "input_domain": domain,
        "url": BASE_URL,
        "found_name": None,
        "email": None,
        "status": None,
        "error": None
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[Worker-{worker_id}] TRY {attempt}/{MAX_RETRIES} -> {name} | {domain}")

            # HARD RESET PAGE EVERY ATTEMPT
            await open_clean_page(page)

            # Submit search
            await run_search(page, name, domain)

            # Wait max 12 seconds for FOUND/NOT_FOUND
            for _ in range(40):  # 40 * 0.3 = 12 sec
                state = await get_state(page)

                if state == "FOUND":
                    found_name, email, status = await extract_email_data(page)

                    result["found_name"] = found_name
                    result["email"] = email
                    result["status"] = status
                    result["error"] = None

                    return result

                if state == "NOT_FOUND":
                    print(f"[Worker-{worker_id}] NOT FOUND -> forcing retry")
                    break

                await asyncio.sleep(0.3)

        except Exception as e:
            print(f"[Worker-{worker_id}] ERROR attempt {attempt}: {str(e)}")

        await asyncio.sleep(0.4)

    result["error"] = f"NOT FOUND after {MAX_RETRIES} retries"
    return result

# -----------------------------
# MAIN (generator for FastAPI)
# -----------------------------
async def run_main(file_path, workers, tabs, log_callback=None):

    yield {"type": "log", "data": "Loading file..."}

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, encoding="latin1")
    else:
        df = pd.read_excel(file_path)

    name_col, domain_col = detect_columns(df)
    yield {"type": "log", "data": f"{name_col}, {domain_col}"}

    queue = asyncio.Queue()
    output = []
    lock = asyncio.Lock()

    total = 0
    for i, row in df.iterrows():
        name = str(row[name_col]).strip()
        domain = str(row[domain_col]).strip()

        if name and domain and name.lower() != "nan":
            await queue.put((i, name, domain))
            total += 1

    yield {"type": "log", "data": f"Queued {total}"}

    progress = {
        "total": total,
        "processed": 0,
        "success": 0,
        "failed": 0
    }

    # Initialize output files
    csv_path = os.path.join(OUTPUT_DIR, "output.csv")
    json_path = os.path.join(OUTPUT_DIR, "output.json")
    
    # Write CSV header immediately
    cols = ["input_name", "input_domain", "url", "found_name", "email", "status", "error"]
    pd.DataFrame(columns=cols).to_csv(csv_path, index=False)
    
    # Write empty JSON array
    with open(json_path, "w") as f:
        json.dump([], f)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        async def worker_group(worker_id):
            context = await browser.new_context()
            pages = [await context.new_page() for _ in range(tabs)]

            async def tab_runner(page, tab_id):
                while True:
                    item = await queue.get()

                    if item is None:
                        queue.task_done()
                        break

                    idx, name, domain = item

                    # ✅ SEND LOG TO UI
                    prefix = f"[W{worker_id}-T{tab_id}] {name} | {domain}"

                    result = await scrape_one(page, name, domain, f"W{worker_id}-T{tab_id}")

                    # 🔥 LOG RESULT
                    if log_callback:
                        if result["email"]:
                            await log_callback(f"{prefix} → FOUND: {result['email']}")
                        else:
                            await log_callback(f"{prefix} → NOT FOUND")

                    async with lock:
                        output.append(result)
                        progress["processed"] += 1

                        if result["email"]:
                            progress["success"] += 1
                        else:
                            progress["failed"] += 1
                        
                        # 🔥 LIVELY WRITING (CSV)
                        try:
                            # Append to CSV
                            res_df = pd.DataFrame([result])
                            res_df[cols].to_csv(csv_path, mode='a', header=False, index=False)
                            
                            # Update JSON (Full rewrite for valid JSON structure, or just wait for end)
                            # To keep it "lively" and stay valid JSON, we rewrite it. 
                            # If performance is an issue for huge files, we can switch to JSONL.
                            with open(json_path, "a") as f:
                                f.write(json.dumps(result) + "\n")
                        except Exception as fe:
                            print(f"Error writing to file: {fe}")

                    queue.task_done()
            await asyncio.gather(*[
                asyncio.create_task(tab_runner(page, i+1))
                for i, page in enumerate(pages)
            ])

            await context.close()

        workers_tasks = [
            asyncio.create_task(worker_group(i+1))
            for i in range(workers)
        ]

        # progress loop
        while progress["processed"] < total:
            yield {"type": "progress", "data": progress}
            await asyncio.sleep(1)

        await queue.join()

        # stop workers
        for _ in range(workers * tabs):
            await queue.put(None)

        await asyncio.gather(*workers_tasks)

        await browser.close()

    # Final yield
    yield {"type": "done", "data": {"csv": csv_path, "json": json_path}}