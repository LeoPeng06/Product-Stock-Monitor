# Web Scraper

A Python web scraper that demonstrates two different approaches to web scraping:
1. Using `requests` and `BeautifulSoup` for static websites
2. Using `Selenium` for dynamic websites that require JavaScript

The scraper includes a stock monitoring system that can notify you when products come back in stock.

## Prerequisites

- Python 3.7 or higher
- Chrome browser (for Selenium)
- Gmail account (for notifications)

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

3. Configure email notifications:
   - Copy the `.env.example` file to `.env`
   - Update the `.env` file with your Gmail credentials:
     - `SENDER_EMAIL`: Your Gmail address
     - `SENDER_PASSWORD`: Your Gmail app-specific password (not your regular password)
     - `RECEIVER_EMAIL`: Email address to receive notifications

   Note: For Gmail, you'll need to:
   1. Enable 2-factor authentication
   2. Generate an app-specific password
   3. Use that app-specific password in the `.env` file

## Usage

### Basic Web Scraping

The script provides two different scraping methods:

1. `scrape_with_requests()`: Uses requests and BeautifulSoup for static websites
2. `scrape_with_selenium()`: Uses Selenium for dynamic websites

To use the scraper:

1. Open `scraper.py`
2. Replace the example URL (`https://example.com`) with your target website
3. Modify the scraping logic according to your needs
4. Run the script:
```bash
python scraper.py
```

### Stock Monitoring

To monitor products for stock availability:

1. Open `stock_monitor.py`
2. Modify the `products` list in the `main()` function with your target products:
```python
products = [
    {
        "name": "Product Name",
        "url": "https://example.com/product",
        "is_dynamic": False,  # Set to True for JavaScript-heavy websites
        "stock_indicator": "in stock",  # Text to look for indicating stock
        "element_selector": "#stock-status",  # CSS selector for dynamic sites
        "check_interval": 300  # Check every 5 minutes
    }
]
```

3. Run the monitor:
```bash
python stock_monitor.py
```

The script will:
- Check the stock status at the specified interval
- Send you an email notification when a product comes back in stock
- Print status updates to the console

## Customization

- For static websites, modify the `scrape_with_requests()` function to target specific HTML elements using BeautifulSoup's methods
- For dynamic websites, modify the `scrape_with_selenium()` function to interact with the page as needed
- Adjust the `check_interval` in the stock monitor to change how frequently it checks for stock
- Modify the email notification template in the `send_notification()` method

## Note

Make sure to respect the website's robots.txt file and terms of service when scraping. Some websites may have restrictions on automated access. 