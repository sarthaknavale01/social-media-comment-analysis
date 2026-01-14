# utils/instagram_scraper.py
"""
Enhanced Instagram scraper using Selenium.
Features:
 - overlay cleanup
 - explicit waits (faster than blind sleeps)
 - "more comments" clicking + smart scrolling
 - optional login (more reliable for many posts)
 - returns CSV path (one comment per row)
Usage:
    scrape_instagram_comments(url, output_file="insta_comments.csv",
                              max_comments=500, headless=True,
                              instagram_username=None, instagram_password=None)
Notes:
 - Use login only for testing/demo and when you own the account or have permission.
 - Scraping may violate Instagram terms; use responsibly.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time, csv, os, sys, traceback

def _make_driver(headless=True):
    opts = Options()
    if headless:
        try:
            opts.add_argument("--headless=new")
        except:
            opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1200,900")
    opts.add_argument("--lang=en-US")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(40)
    return driver

def _safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.2)
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False

def instagram_login(driver, username, password, timeout=20, debug=False):
    """
    Performs Instagram login on the driver. Returns True if logged in.
    """
    try:
        wait = WebDriverWait(driver, timeout)
        # go to login page
        driver.get("https://www.instagram.com/accounts/login/")
        # wait for username field
        wait.until(EC.presence_of_element_located((By.NAME, "username")))
        u = driver.find_element(By.NAME, "username")
        p = driver.find_element(By.NAME, "password")
        u.clear(); u.send_keys(username)
        p.clear(); p.send_keys(password)
        # submit
        btns = driver.find_elements(By.XPATH, "//button[@type='submit']")
        if btns:
            _safe_click(driver, btns[0])
        # wait until either home or challenge appears
        time.sleep(2)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//nav")))
            if debug:
                print("[insta_login] login appears successful")
            return True
        except TimeoutException:
            # maybe login failed or needs verification
            if debug:
                print("[insta_login] login may have failed or requires verification")
            return False
    except Exception as e:
        if debug:
            print("[insta_login] exception:", e)
        return False

def scrape_instagram_comments(post_url,
                              output_file="insta_comments.csv",
                              max_comments=500,
                              headless=True,
                              instagram_username=None,
                              instagram_password=None,
                              timeout=20,
                              debug=False):
    """
    High-level function to extract comments.
    If instagram_username and instagram_password provided, will try login first.
    Returns path to CSV file (one comment per row) or raises RuntimeError.
    """
    def log(*a):
        if debug:
            print("[insta_scraper]", *a, file=sys.stderr)

    driver = None
    try:
        driver = _make_driver(headless=headless)
        wait = WebDriverWait(driver, timeout)

        # optional login
        if instagram_username and instagram_password:
            log("Attempting login...")
            ok = instagram_login(driver, instagram_username, instagram_password, timeout=timeout, debug=debug)
            if not ok:
                log("Login not successful; continuing without login (may fail for private posts).")

        # open post
        log("Opening post:", post_url)
        try:
            driver.get(post_url)
        except WebDriverException as e:
            log("Initial get failed, trying again:", e)
            time.sleep(1)
            driver.get(post_url)

        # quick overlay removal & cookie accept attempts
        try:
            time.sleep(1)
            driver.execute_script("""
                try {
                    document.querySelectorAll('div[role=\"dialog\"]').forEach(el => el.remove());
                    document.querySelectorAll('[aria-modal=\"true\"]').forEach(el => el.remove());
                } catch(e) {}
            """)
        except Exception:
            pass

        # if page shows login overlay, try to close by sending ESC
        try:
            from selenium.webdriver.common.keys import Keys
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.ESCAPE)
        except Exception:
            pass

        # wait for article or something similar
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
            log("Article found")
        except TimeoutException:
            log("Article not found quickly; continuing anyway")

        # function to try expand buttons quickly
        def click_expand_buttons():
            xps = [
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view all comments')]",
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more comments')]",
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view replies')]",
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view more')]",
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see more')]"
            ]
            for xp in xps:
                try:
                    for b in driver.find_elements(By.XPATH, xp):
                        _safe_click(driver, b)
                        time.sleep(0.4)
                        if debug: log("Clicked expand:", xp)
                except Exception:
                    pass

        # Attempt initial expands
        click_expand_buttons()

        # Collect comments efficiently: use set to avoid duplicates
        comments = []
        seen = set()

        # Short strategy:
        # - Use multiple XPaths patterns for comment text
        # - On each loop: find elements, collect new ones, click more buttons, scroll a bit
        xpath_patterns = [
            "//ul//li//div//div//div/span",   # common
            "//article//div//ul//li//div//div//div/span",
            "//div[contains(@class,'C4VMK')]/span",
            "//div[@aria-label='Comment']//span",
            "//div[contains(@data-testid,'comment')]/span",
            "//div[contains(@class, '_a9z') or contains(@class,'_a9y')]/div/span"
        ]

        loops = 0
        max_loops = 120  # safety cap
        last_count = 0
        while len(comments) < max_comments and loops < max_loops:
            loops += 1
            new_found = False
            for xp in xpath_patterns:
                try:
                    elems = driver.find_elements(By.XPATH, xp)
                    for el in elems:
                        try:
                            txt = el.text.strip()
                        except Exception:
                            txt = ""
                        if txt and txt not in seen:
                            seen.add(txt)
                            comments.append(txt)
                            new_found = True
                            if debug: log("Found:", txt[:80])
                            if len(comments) >= max_comments:
                                break
                    if len(comments) >= max_comments:
                        break
                except Exception:
                    continue

            # If none new found, try clicking more and scrolling
            if not new_found:
                click_expand_buttons()
                try:
                    driver.execute_script("window.scrollBy(0, 600);")
                except:
                    pass
                time.sleep(0.8)
            else:
                # small scroll to load more replies if available
                try:
                    driver.execute_script("window.scrollBy(0, 250);")
                except:
                    pass
                time.sleep(0.45)

            # if nothing increased for many loops, break
            if len(comments) == last_count:
                # give a couple more tries then break
                if loops > 12 and not new_found:
                    break
            else:
                last_count = len(comments)

        log("Loop finished, collected:", len(comments))

        if len(comments) == 0:
            raise RuntimeError("No comments extracted. Post may be private/login required or selectors need update.")

        # Save CSV
        uploads_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        csv_path = os.path.join(uploads_dir, output_file)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for c in comments:
                writer.writerow([c])

        log("Saved CSV:", csv_path)
        return csv_path

    except Exception as ex:
        tb = traceback.format_exc()
        if driver:
            try:
                driver.quit()
            except:
                pass
        raise RuntimeError(f"Instagram scraping failed: {ex}\n{tb}")

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
