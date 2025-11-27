import os
from datetime import datetime

SAVE_DIR = "scraped_txt"

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def safe_filename(name):
    return "".join(c if c.isalnum() or c in " -_." else "_" for c in name)[:100]

def ensure_directory_exists(directory=SAVE_DIR):
    if not os.path.exists(directory):
        os.makedirs(directory)

def write_text_to_file(text, filename, directory=SAVE_DIR):
    ensure_directory_exists(directory)
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return filepath

