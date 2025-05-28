import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime
import os
from dotenv import load_dotenv
from urllib.parse import urljoin
import json

# Load environment variables for email configuration
load_dotenv()

class StockMonitor:
    """
    A class to monitor product stock status across different websites.
    Supports both static and dynamic websites, with email notifications
    when products become available.
    """
    
    def __init__(self):
        """Initialize the stock monitor with email and browser settings"""
        # Email configuration for notifications
        self.emailSettings = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': os.getenv('SENDER_EMAIL'),
            'sender_password': os.getenv('SENDER_PASSWORD'),
            'recipient_email': os.getenv('RECEIVER_EMAIL')
        }
        
        # Browser settings for web scraping
        self.browserSettings = Options()
        self.browserSettings.add_argument('--headless')  # Run browser in background
        self.browserSettings.add_argument('--no-sandbox')
        self.browserSettings.add_argument('--disable-dev-shm-usage')
        self.browser = None
        
        # Initialize web browser
        self.browserService = Service(ChromeDriverManager().install())
        self.browser = webdriver.Chrome(service=self.browserService, options=self.browserSettings)
        
        # Track product stock history
        self.productStockHistory = {}

    def findProductImage(self, url, isDynamic=True):
        """
        Find the main product image on Pokemon Center.
        
        Args:
            url (str): The webpage URL to search
            isDynamic (bool): Whether the website uses dynamic loading
            
        Returns:
            str: URL of the product image, or None if not found
        """
        try:
            if not self.browser:
                self.browser = webdriver.Chrome(service=self.browserService, options=self.browserSettings)
            
            self.browser.get(url)
            wait = WebDriverWait(self.browser, 10)
            
            # Pokemon Center specific image selectors
            image_selectors = [
                ".product-gallery__image img",  # Main product image
                ".product-gallery__featured-image img",  # Featured image
                ".product__image img",  # Alternative image location
                "[data-testid='product-image'] img"  # Test ID selector
            ]
            
            for selector in image_selectors:
                try:
                    image = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    image_url = image.get_attribute('src')
                    if image_url and not self._isSmallImage(image_url):
                        return image_url
                except:
                    continue
            
            return None
        
        except Exception as e:
            print(f"Error finding Pokemon Center product image: {e}")
            return None
        finally:
            if self.browser:
                self.browser.quit()
                self.browser = None

    def checkStockStatus(self, url, stockIndicator, isDynamic=False, elementSelector=None):
        """
        Check if a product is in stock on Pokemon Center.
        
        Args:
            url (str): The product webpage URL
            stockIndicator (str): Text that indicates the product is in stock
            isDynamic (bool): Whether the website uses dynamic loading
            elementSelector (str): CSS selector for dynamic sites
            
        Returns:
            bool: True if product is in stock, False otherwise
        """
        try:
            if not self.browser:
                self.browser = webdriver.Chrome(service=self.browserService, options=self.browserSettings)
            
            self.browser.get(url)
            wait = WebDriverWait(self.browser, 10)
            
            # Pokemon Center specific selectors
            stock_selectors = [
                ".add-to-cart",  # Main add to cart button
                "button[data-testid='add-to-cart']",  # Alternative button selector
                ".product-details__add-to-cart"  # Another possible location
            ]
            
            for selector in stock_selectors:
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    button_text = element.text.lower()
                    # Check if the button indicates the item is in stock
                    if "add to cart" in button_text and "out of stock" not in button_text:
                        return True
                except:
                    continue
            
            # Check for out of stock indicators
            out_of_stock_selectors = [
                ".out-of-stock",
                ".product-details__out-of-stock",
                "[data-testid='out-of-stock']"
            ]
            
            for selector in out_of_stock_selectors:
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if element.is_displayed():
                        return False
                except:
                    continue
            
            return False  # Default to out of stock if we can't determine status
        
        except Exception as e:
            print(f"Error checking Pokemon Center stock: {e}")
            return False
        finally:
            if self.browser:
                self.browser.quit()
                self.browser = None

    def notifyStockAvailable(self, productName, url):
        """
        Send an email notification when a product becomes available.
        
        Args:
            productName (str): Name of the product
            url (str): URL of the product
        """
        try:
            email = MIMEMultipart()
            email['From'] = self.emailSettings['sender_email']
            email['To'] = self.emailSettings['recipient_email']
            email['Subject'] = f"Product Available: {productName}"
            
            message = f"""
            Great news! The product "{productName}" is now available!
            You can find it here: {url}
            """
            
            email.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(self.emailSettings['smtp_server'], self.emailSettings['smtp_port']) as server:
                server.starttls()
                server.login(self.emailSettings['sender_email'], self.emailSettings['sender_password'])
                server.send_message(email)
            
            print(f"Notification sent for {productName}")
        except Exception as e:
            print(f"Error sending notification: {e}")

    def startMonitoring(self, productName, url, checkInterval=300, 
                       isDynamic=False, stockIndicator="in stock", 
                       elementSelector=None):
        """
        Start monitoring a product's stock status.
        
        Args:
            productName (str): Name of the product to monitor
            url (str): URL of the product page
            checkInterval (int): How often to check (in seconds)
            isDynamic (bool): Whether the website uses dynamic loading
            stockIndicator (str): Text that indicates the product is in stock
            elementSelector (str): CSS selector for dynamic sites
        """
        print(f"Starting to monitor {productName}")
        
        while True:
            try:
                # Check current stock status
                isAvailable = self.checkStockStatus(url, stockIndicator, isDynamic, elementSelector)
                productImage = self.findProductImage(url, isDynamic)
                
                # Update stock history
                if productName not in self.productStockHistory:
                    self.productStockHistory[productName] = not isAvailable
                
                # Send notification if product just became available
                if isAvailable and not self.productStockHistory[productName]:
                    self.notifyStockAvailable(productName, url)
                    self.productStockHistory[productName] = True
                elif not isAvailable:
                    self.productStockHistory[productName] = False
                
                # Log current status
                status = "Available" if isAvailable else "Out of Stock"
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {productName}: {status}")
                
                # Wait before next check
                time.sleep(checkInterval)
                
            except Exception as e:
                print(f"Error monitoring {productName}: {e}")
                time.sleep(checkInterval)

    def _makeAbsoluteUrl(self, baseUrl, relativeUrl):
        """Convert a relative URL to an absolute URL"""
        if not relativeUrl.startswith(('http://', 'https://')):
            return urljoin(baseUrl, relativeUrl)
        return relativeUrl

    def _isSmallImage(self, url):
        """Check if an image URL likely points to a small image or icon"""
        return any(term in url.lower() for term in ['icon', 'logo', 'thumb', 'small'])

    def __del__(self):
        """Clean up browser resources when the monitor is destroyed"""
        if self.browser:
            self.browser.quit()

def main():
    """Example usage of the StockMonitor class"""
    monitor = StockMonitor()
    
    # Example products to monitor
    products = [
        {
            "name": "Example Product 1",
            "url": "https://example.com/product1",
            "isDynamic": False,
            "stockIndicator": "in stock",
            "checkInterval": 300  # Check every 5 minutes
        },
        {
            "name": "Example Product 2",
            "url": "https://example.com/product2",
            "isDynamic": True,
            "stockIndicator": "add to cart",
            "elementSelector": "#stock-status",
            "checkInterval": 300
        }
    ]
    
    # Start monitoring each product
    for product in products:
        monitor.startMonitoring(
            product["name"],
            product["url"],
            product["checkInterval"],
            product["isDynamic"],
            product["stockIndicator"],
            product.get("elementSelector")
        )

def loadProducts():
    """
    Load products from the JSON file.
    
    Returns:
        list: List of products, or empty list if file is empty or invalid
    """
    try:
        if os.path.exists('products.json'):
            with open('products.json', 'r') as f:
                content = f.read().strip()
                if content:
                    products = json.loads(content)
                    # Validate that products is a list and each item is a dictionary
                    if isinstance(products, list):
                        validated_products = []
                        for p in products:
                            if isinstance(p, dict) and 'name' in p:
                                validated_products.append(p)
                            else:
                                print(f"Skipping invalid product entry: {p}")
                        return validated_products
                    return []
        return []
    except json.JSONDecodeError:
        print("Error reading products.json. Starting with empty list.")
        return []
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

if __name__ == "__main__":
    main() 