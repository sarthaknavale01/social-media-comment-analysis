# utils/twitter_scraper.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time, csv, os

def scrape_twitter_replies(tweet_url, output_file="twitter_comments.csv", max_comments=300, headless=True):
    """
    Scrape replies from a PUBLIC tweet using Selenium.
    Returns: CSV file path containing scraped comments.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(40)

    try:
        driver.get(tweet_url)
    except:
        time.sleep(3)
        driver.get(tweet_url)

    time.sleep(4)

    comments = []
    seen = set()
    SCROLL_LIMIT = 60
    scrolls = 0

    while len(comments) < max_comments and scrolls < SCROLL_LIMIT:
        tweet_boxes = driver.find_elements(By.XPATH, "//article//div[@lang]")
        for box in tweet_boxes:
            text = box.text.strip()
            if text and text not in seen:
                seen.add(text)
                comments.append(text)
                if len(comments) >= max_comments:
                    break

        driver.execute_script("window.scrollBy(0, 1400);")
        time.sleep(1.5)
        scrolls += 1

    driver.quit()

    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    csv_path = os.path.join(uploads_dir, output_file)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for c in comments:
            writer.writerow([c])

    return csv_path
