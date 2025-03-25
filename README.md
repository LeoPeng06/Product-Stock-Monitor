# Web Scraper

A Python web scraper that demonstrates two different approaches to web scraping:
1. Using `requests` and `BeautifulSoup` for static websites
2. Using `Selenium` for dynamic websites that require JavaScript

## Prerequisites

- Python 3.7 or higher
- Chrome browser (for Selenium)

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

The script provides two different scraping methods:

1. `scrape_with_requests()`: Uses requests and BeautifulSoup for static websites
2. `scrape_with_selenium()`: Uses Selenium for dynamic websites

To use the scraper:

1. Open `scraper.py`
2. Replace the example URL (`https://example.com`) with your target website
3. Modify the scraping logic according to your needs (e.g., change the HTML elements you want to extract)
4. Run the script:
```bash
python scraper.py
```

## Customization

- For static websites, modify the `scrape_with_requests()` function to target specific HTML elements using BeautifulSoup's methods
- For dynamic websites, modify the `scrape_with_selenium()` function to interact with the page as needed (clicking buttons, filling forms, etc.)

## Note

Make sure to respect the website's robots.txt file and terms of service when scraping. Some websites may have restrictions on automated access. 