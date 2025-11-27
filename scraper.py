import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from PIL import Image
import pytesseract
import io

from playwright.sync_api import sync_playwright

SAVE_DIR = "scraped_txt"

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def safe_filename(name):
    return "".join(c if c.isalnum() or c in " -_." else "_" for c in name)[:100]

# --------------------------------------------------------
# Playwright: Fetch a fully rendered webpage (JS-enabled)
# --------------------------------------------------------
def fetch_page_playwright(url, log_signal=None):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page.goto(url, timeout=60000, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html

    except Exception as e:
        if log_signal:
            log_signal.emit(f"[ERROR] Playwright fetch failed for {url}: {e}\n")
        else:
            print(f"[ERROR] Playwright fetch failed for {url}: {e}")
        return None

# --------------------------------------------------------
# Extract text from image (OCR)
# --------------------------------------------------------
def extract_text_from_image(img_bytes):
    try:
        image = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"OCR failed: {e}")
        return ""

# --------------------------------------------------------
# Extract all valid links
# --------------------------------------------------------
def extract_links(base_url, soup):
    links = set()
    for a in soup.find_all("a", href=True):
        url = urljoin(base_url, a["href"])
        if url.startswith("http"):
            links.add(url)
    return links

# --------------------------------------------------------
# Scrape single page using Playwright HTML
# --------------------------------------------------------
def scrape_article(url, keywords=None, ocr_images=False, log_signal=None):
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    html = fetch_page_playwright(url, log_signal)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Create filename
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "untitled"
    filename = f"{safe_filename(title)}_{get_timestamp()}.txt"
    filepath = os.path.join(SAVE_DIR, filename)

    # Extract article paragraphs
    paragraphs = soup.find_all("p")
    text_content = "\n".join(
        p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
    )

    result_text = (
        f"Title: {title}\nURL: {url}\nTimestamp: {get_timestamp()}\n\n"
        f"ARTICLE TEXT:\n{text_content}\n\n"
    )

    # OCR on images
    if ocr_images:
        img_texts = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            src = urljoin(url, src)

            try:
                img_resp = requests.get(src, timeout=10)
                img_text = extract_text_from_image(img_resp.content)
                if img_text:
                    img_texts.append(f"Image text from {src}:\n{img_text}\n")
            except Exception as e:
                warn = f"[WARNING] OCR failed for {src}: {e}\n"
                log_signal.emit(warn) if log_signal else print(warn)

        if img_texts:
            result_text += "IMAGE TEXTS:\n" + "\n".join(img_texts)

    # Save text
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result_text)

    msg = f"[INFO] Saved article text to {filepath}\n"
    log_signal.emit(msg) if log_signal else print(msg)

    return filepath

# --------------------------------------------------------
# Crawl with depth
# --------------------------------------------------------
def run_scraper(start_url, keywords=None, depth=1, ocr_images=False, log_signal=None):
    visited = set()
    to_visit = [start_url]
    total_files = 0

    for level in range(depth):
        if log_signal:
            log_signal.emit(f"[INFO] Crawl Level {level + 1}/{depth}\n")

        next_links = []

        for url in to_visit:
            if url in visited:
                continue
            visited.add(url)

            saved_file = scrape_article(
                url, keywords=keywords, ocr_images=ocr_images, log_signal=log_signal
            )

            if saved_file:
                total_files += 1

            # Fetch page HTML for link extraction
            html = fetch_page_playwright(url, log_signal)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            links = extract_links(url, soup)
            next_links.extend(list(links))

            # Safety limit
            if total_files >= 50:
                if log_signal:
                    log_signal.emit("[INFO] Page limit (50) reached.\n")
                return total_files

        to_visit = next_links

    return total_files
