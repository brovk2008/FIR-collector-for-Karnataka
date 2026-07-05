#!/usr/bin/env python3
"""
MULTIPROCESS KARNATAKA FIR SCRAPER
=================================
Runs multiple Chrome instances in parallel to speed up extraction.
Distributes police stations round-robin among workers.
Appends to CSV concurrently using a multiprocessing Lock.
"""

import os, re, csv, time, logging, base64, multiprocessing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

TARGET_YEAR = "2024"
PDF_BASE_DIR = "fir_pdfs"
CSV_FILE = "karnataka_fir_index.csv"
BASE_URL = "https://ksp.karnataka.gov.in/firsearch/en"
NUM_WORKERS = 8

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

DISTRICT_NAMES = {
    1: "Bagalkot", 2: "Ballari", 3: "Belagavi City", 4: "Belagavi Dist",
    5: "Bengaluru City", 6: "Bengaluru Dist", 7: "Bidar", 8: "Chamarajanagar",
    9: "Chickballapura", 10: "Chikkamagaluru", 11: "Chitradurga", 12: "CID",
    13: "Coastal Security Police", 14: "Dakshina Kannada", 15: "Davanagere",
    16: "Dharwad", 17: "Gadag", 18: "Hassan", 19: "Haveri",
    20: "Hubballi Dharwad City", 21: "ISD Bengaluru", 22: "K.G.F",
    23: "Kalaburagi", 24: "Kalaburagi City", 25: "Karnataka Railways",
    26: "Kodagu", 27: "Kolar", 28: "Koppal", 29: "Mandya",
    30: "Mangaluru City", 31: "Mysuru City", 32: "Mysuru Dist",
    33: "Raichur", 34: "Bengaluru South", 35: "Shivamogga", 36: "Tumakuru",
    37: "Udupi", 38: "Uttara Kannada", 39: "Vijayapur", 40: "Yadgir", 41: "Vijayanagara",
}

def sf(n):
    return re.sub(r'[<>:"/\\|?*]', '_', n).strip().rstrip('.')

def make_pdf_url(href):
    href = href.strip()
    if href.startswith('http'): return href
    if href.startswith('/'): return f"https://ksp.karnataka.gov.in{href}"
    return f"https://ksp.karnataka.gov.in/firsearch/{href}"

def setup(worker_id):
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    dl_dir = os.path.join(os.getcwd(), f"chrome_dl_worker_{worker_id}")
    os.makedirs(dl_dir, exist_ok=True)
    prefs = {
        "download.default_directory": dl_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    }
    opts.add_experimental_option("prefs", prefs)
    d = webdriver.Chrome(options=opts)
    d.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return d, dl_dir

def get_captcha(driver):
    """Get the current CAPTCHA value from the search page."""
    captcha = ""
    try:
        captcha = driver.find_element(By.CSS_SELECTOR, "input[name='random_captcha']").get_attribute("value") or ""
    except: pass
    if not captcha:
        try:
            captcha = driver.find_element(By.CSS_SELECTOR, "label.captcah-font").text.strip()
        except: pass
    return captcha

def refresh_captcha_without_reload(driver, old_captcha):
    """Attempts to refresh the captcha without a full page reload."""
    try:
        for selector in ["img[src*='captcha']", "[id*='captcha'][class*='refresh']", "img[id*='captcha']"]:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                if el.is_displayed():
                    el.click()
                    time.sleep(0.5)
                    new_c = get_captcha(driver)
                    if new_c and new_c != old_captcha:
                        return new_c
    except: pass

    try:
        for selector in ["[class*='refresh']", "[id*='refresh']", "[class*='reload']", "[id*='reload']"]:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                if el.is_displayed():
                    el.click()
                    time.sleep(0.5)
                    new_c = get_captcha(driver)
                    if new_c and new_c != old_captcha:
                        return new_c
    except: pass

    for fn in ["refreshCaptcha", "changeCaptcha", "reloadCaptcha", "change_captcha"]:
        try:
            driver.execute_script(f"if (typeof {fn} === 'function') {fn}();")
            time.sleep(0.5)
            new_c = get_captcha(driver)
            if new_c and new_c != old_captcha:
                return new_c
        except: pass

    return ""

def fill_and_submit(driver, fir_s, year):
    """Fill the form with FIR number and current captcha, then submit."""
    captcha = get_captcha(driver)
    if not captcha:
        return False
    
    try:
        Select(driver.find_element(By.NAME, "year")).select_by_value(year)
    except: pass
    
    fir_input = driver.find_element(By.NAME, "fir_num")
    fir_input.clear()
    fir_input.send_keys(fir_s)
    
    cap_input = driver.find_element(By.NAME, "captcha")
    cap_input.clear()
    cap_input.send_keys(captcha)
    
    try:
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        return True
    except:
        try:
            driver.find_element(By.XPATH, "//form//button | //button | //input[@type='submit']").click()
            return True
        except:
            return False

def get_all_stations():
    log.info("Starting master browser to gather police stations...")
    driver, _ = setup("master")
    all_stations = []
    
    try:
        for did in sorted(DISTRICT_NAMES.keys()):
            dname = DISTRICT_NAMES[did]
            log.info(f"Gathering stations for District {did}: {dname}...")
            driver.get(BASE_URL)
            try:
                dist_select = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "district_id"))
                )
                Select(dist_select).select_by_value(str(did))
                
                # Wait for stations to load (len options > 1)
                ps_select_elem = WebDriverWait(driver, 10).until(
                    lambda d: d.find_element(By.NAME, "ps_id")
                )
                WebDriverWait(driver, 10).until(
                    lambda d: len(Select(ps_select_elem).options) > 1
                )
                
                sel = Select(ps_select_elem)
                for o in sel.options:
                    sid = o.get_attribute("value")
                    sname = o.text.strip()
                    if sid and sid != "1" and "Select" not in sname:
                        all_stations.append((did, dname, sid, sname))
            except Exception as e:
                log.error(f"Error gathering stations for district {dname}: {e}")
    finally:
        driver.quit()
    return all_stations

def worker_process(worker_id, stations_chunk, csv_lock, processed_status):
    log.info(f"Worker {worker_id} started, handling {len(stations_chunk)} stations.")
    driver, dl_dir = setup(worker_id)
    
    found = pdfs = 0
    
    try:
        for idx, (did, dname, sid, sname) in enumerate(stations_chunk):
            sdir = os.path.join(PDF_BASE_DIR, sf(dname), sf(sname))
            os.makedirs(sdir, exist_ok=True)
            
            log.info(f"[Worker {worker_id}] [{idx+1}/{len(stations_chunk)}] {dname} -> {sname}")
            
            # Save search tab handle for this station
            search_tab = driver.current_window_handle
            
            consecutive_misses = 0
            for fir_i in range(1, 501):
                fir_s = str(fir_i).zfill(4)
                pdf_path = os.path.join(sdir, f"{fir_s}_{TARGET_YEAR}.pdf")
                
                # Check if we have a successful status recorded
                if (did, sid, fir_s) in processed_status:
                    status = processed_status[(did, sid, fir_s)]
                    # If it was found but the physical PDF file is missing, we re-run to download it
                    if status == "found" and not os.path.exists(pdf_path):
                        pass
                    else:
                        if status in ("found", "found_no_pdf"):
                            consecutive_misses = 0
                        elif status == "not_found":
                            consecutive_misses += 1
                        
                        if consecutive_misses >= 5:
                            break
                        continue
                
                if os.path.exists(pdf_path):
                    consecutive_misses = 0
                    continue
                
                try:
                    # Make sure we're on the search tab
                    try:
                        driver.switch_to.window(search_tab)
                    except:
                        if driver.window_handles:
                            try:
                                driver.switch_to.window(driver.window_handles[0])
                                search_tab = driver.current_window_handle
                            except:
                                pass
                    
                    # Check if district and station are currently selected
                    is_selected = False
                    try:
                        dist_val = Select(driver.find_element(By.NAME, "district_id")).first_selected_option.get_attribute("value")
                        ps_val = Select(driver.find_element(By.NAME, "ps_id")).first_selected_option.get_attribute("value")
                        if dist_val == str(did) and ps_val == sid:
                            is_selected = True
                    except:
                        pass
                    
                    captcha = ""
                    if is_selected:
                        # Try to refresh captcha without full reload
                        old_c = get_captcha(driver)
                        captcha = refresh_captcha_without_reload(driver, old_c)
                    
                    if not captcha:
                        # Reload search page and select district & station
                        driver.get(BASE_URL)
                        
                        dist_select = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, "district_id"))
                        )
                        Select(dist_select).select_by_value(str(did))
                        
                        # Wait for ps_id dropdown to populate
                        ps_select_elem = WebDriverWait(driver, 10).until(
                            lambda d: d.find_element(By.NAME, "ps_id")
                        )
                        WebDriverWait(driver, 10).until(
                            lambda d: len(Select(ps_select_elem).options) > 1
                        )
                        
                        # Select station
                        Select(ps_select_elem).select_by_value(sid)
                        search_tab = driver.current_window_handle
                    
                    # Record tabs BEFORE submitting
                    before_tabs = set(driver.window_handles)
                    
                    # Fill form and submit — this reads fresh captcha each time
                    submitted = fill_and_submit(driver, fir_s, TARGET_YEAR)
                    if not submitted:
                        log.warning(f"[Worker {worker_id}]      Submit failed, skipping")
                        continue
                    
                    # Wait for new tab to open (up to 3 seconds)
                    try:
                        WebDriverWait(driver, 3).until(
                            lambda d: len(d.window_handles) > len(before_tabs)
                        )
                    except:
                        pass
                    
                    # CHECK FOR NEW TAB (result page)
                    after_tabs = set(driver.window_handles)
                    new_tabs = after_tabs - before_tabs
                    
                    result_tab = None
                    if new_tabs:
                        result_tab = new_tabs.pop()
                        driver.switch_to.window(result_tab)
                    
                    # Wait for the results table or "no records" text to appear
                    try:
                        WebDriverWait(driver, 3).until(
                            lambda d: d.find_elements(By.CLASS_NAME, "firsearchc") or \
                                      "no records" in d.page_source.lower() or \
                                      "not found" in d.page_source.lower()
                        )
                    except:
                        pass
                    
                    html = driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                    table = soup.find("table", {"class": "firsearchc"})
                    
                    row = [did, dname, sname, sid, fir_s, TARGET_YEAR, "not_found", ""]
                    
                    if table:
                        a_tag = soup.find("a", href=re.compile(r'\.pdf'))
                        if a_tag:
                            pdf_href = a_tag['href']
                            pdf_url = make_pdf_url(pdf_href)
                            found += 1
                            
                            log.info(f"[Worker {worker_id}]      FIR #{fir_s} FOUND!")
                            
                            # Clear download folder
                            for f in os.listdir(dl_dir):
                                try: os.remove(os.path.join(dl_dir, f))
                                except: pass
                            
                            success = False
                            
                            # METHOD 1: Click "View FIR Copy" button
                            try:
                                view_btn = driver.find_element(By.CSS_SELECTOR, "a[href*='.pdf']")
                                view_btn.click()
                                
                                # Wait for PDF download (up to 8 seconds)
                                for _ in range(16):
                                    files = [f for f in os.listdir(dl_dir) if f.endswith('.pdf') and not f.endswith('.crdownload')]
                                    if files:
                                        files.sort(key=lambda f: os.path.getmtime(os.path.join(dl_dir, f)), reverse=True)
                                        src = os.path.join(dl_dir, files[0])
                                        with open(src, "rb") as f:
                                            data = f.read()
                                        if len(data) > 2000:
                                            with open(pdf_path, "wb") as f:
                                                f.write(data)
                                            pdfs += 1
                                            log.info(f"[Worker {worker_id}] ✓ FIR #{fir_s} PDF saved! ({len(data)} bytes)")
                                            success = True
                                        os.remove(src)
                                        break
                                    time.sleep(0.5)
                            except Exception as e:
                                log.warning(f"[Worker {worker_id}]      Click download failed: {e}")
                            
                            # METHOD 2: fetch from result page
                            if not success:
                                try:
                                    b64 = driver.execute_async_script("""
                                        var callback = arguments[0];
                                        try {
                                            fetch(arguments[0], {credentials: 'include'})
                                            .then(r => r.blob())
                                            .then(blob => {
                                                var reader = new FileReader();
                                                reader.onload = function() { callback(reader.result.split(',')[1]); };
                                                reader.readAsDataURL(blob);
                                            })
                                            .catch(() => callback(null));
                                        } catch(e) { callback(null); }
                                    """, pdf_url)
                                    if b64:
                                        data = base64.b64decode(b64)
                                        if len(data) > 2000:
                                            with open(pdf_path, "wb") as f:
                                                f.write(data)
                                            pdfs += 1
                                            log.info(f"[Worker {worker_id}] ✓ FIR #{fir_s} fetch saved! ({len(data)} bytes)")
                                            success = True
                                except:
                                    pass
                            
                            if success:
                                row[6] = "found"
                                row[7] = pdf_path.replace("\\", "/")
                            else:
                                row[6] = "found_no_pdf"
                    
                    # Close result tab if it was a separate tab
                    if result_tab:
                        try:
                            driver.close()
                        except:
                            pass
                        try:
                            driver.switch_to.window(search_tab)
                        except:
                            pass
                    
                    with csv_lock:
                        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                            cw = csv.writer(f)
                            cw.writerow(row)
                    
                    if row[6] in ("found", "found_no_pdf"):
                        consecutive_misses = 0
                    elif row[6] == "not_found":
                        consecutive_misses += 1
                        
                    if consecutive_misses >= 5:
                        log.warning(f"[Worker {worker_id}]      5 consecutive FIRs not found for station {sname}. Skipping remaining.")
                        break
                    
                except Exception as e:
                    log.error(f"[Worker {worker_id}] ✗ FIR #{fir_s}: {e}")
                    with csv_lock:
                        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                            cw = csv.writer(f)
                            cw.writerow([did, dname, sname, sid, fir_s, TARGET_YEAR, "error", ""])
                            
        log.info(f"Worker {worker_id} finished all assigned stations. Found: {found}, PDFs: {pdfs}")
    finally:
        driver.quit()

def run():
    log.info("="*60)
    log.info("KARNATAKA FIR SCRAPER — MULTIPROCESS EDITION")
    log.info("="*60)
    
    # Initialize CSV file with headers if it doesn't exist
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            cw = csv.writer(f)
            cw.writerow(["district_id","district","police_station","station_id","fir_number","year","status","pdf_path"])
            
    # Load previously processed records to support resume
    processed_status = {}
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    for row in reader:
                        if len(row) >= 7:
                            did_str, _, _, sid, fir_s, _, status, _ = row[:8]
                            try:
                                did = int(did_str)
                                if status != "error":
                                    processed_status[(did, sid, fir_s)] = status
                            except:
                                pass
            log.info(f"Loaded {len(processed_status)} already processed FIR records from CSV.")
        except Exception as e:
            log.error(f"Error loading CSV for resume: {e}")
            
    # Gather stations list
    all_stations = get_all_stations()
    if not all_stations:
        log.error("No stations gathered. Exiting.")
        return
        
    log.info(f"Gathered a total of {len(all_stations)} stations.")
    
    # Distribute stations round-robin among workers
    workers_stations = [[] for _ in range(NUM_WORKERS)]
    for idx, station in enumerate(all_stations):
        workers_stations[idx % NUM_WORKERS].append(station)
        
    # Lock for concurrent writing to CSV
    csv_lock = multiprocessing.Lock()
    
    # Spawn workers
    processes = []
    for i in range(NUM_WORKERS):
        p = multiprocessing.Process(target=worker_process, args=(i, workers_stations[i], csv_lock, processed_status))
        processes.append(p)
        p.start()
        log.info(f"Spawned Worker {i} Process.")
        time.sleep(2)  # Stagger startup to prevent driver race conditions
        
    # Wait for all workers to finish
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        log.warning("KeyboardInterrupt received in main process. Terminating workers...")
        for p in processes:
            p.terminate()
            
    log.info("="*60)
    log.info("MULTIPROCESS SCRAPER RUN FINISHED")
    log.info("="*60)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
