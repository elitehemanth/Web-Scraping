# Web-Scraping
This project is an open-source web-scraping application built entirely in Python, designed to make collecting and understanding website data as simple as possible. It offers a 
clean interface with dedicated tabs for scraping, reviewing logs, managing settings, browsing saved text files, searching keywords, and generating AI-powered summaries. 
The scraper relies on BeautifulSoup4 to pull text from any URL the user provides, and all extracted data is stored as .txt files for full transparency and portability. 
A configurable crawl-depth system lets the user decide how deeply the scraper should explore a site’s internal pages, while the dashboard displays real-time progress throughout
the process. When deeper insight is needed, the AI Summary tab sends the scraped text as a JSON request to an LLM server running through LM Studio, or any compatible model. 
The server returns a structured summary, turning raw web content into something clear and digestible. The project aims to make web scraping efficient, accessible, and
expandable for anyone who wants to work with web data.
<hr>
<img width="896" height="635" alt="dashboard" src="https://github.com/user-attachments/assets/f3e2c71d-279c-4793-a4a5-3f4ce0120d98" />
<hr>

<img width="896" height="635" alt="Ai summary" src="https://github.com/user-attachments/assets/ca13d3d2-d442-4195-a62e-49a797e52e87" />
<hr>

# install requirements
pip install -r requirements.txt

# Run the application 
python main.py

# NOT MY STYLE
