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

    def findProductImage(self, url, isDynamic=False):
        """
        Find the main product image on a webpage.
        
        Args:
            url (str): The webpage URL to search
            isDynamic (bool): Whether the website uses dynamic loading
            
        Returns:
            str: URL of the product image, or None if not found
        """
        try:
            if isDynamic:
                return self._findImageOnDynamicSite(url)
            return self._findImageOnStaticSite(url)
        except Exception as e:
            print(f"Error finding product image: {e}")
            return None

    def _findImageOnStaticSite(self, url):
        """Find product image on a static website using BeautifulSoup"""
        response = requests.get(url)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Common locations for product images
        imageLocations = [
            'img[itemprop="image"]',
            '.product-image img',
            '#product-image img',
            '.main-image img',
            '.product-main-image img',
            'img[alt*="product"]',
            'img[alt*="Product"]'
        ]
        
        # Try each location until we find an image
        for location in imageLocations:
            image = soup.select_one(location)
            if image and image.get('src'):
                return self._makeAbsoluteUrl(url, image['src'])
        
        # If no specific product image found, look for any large image
        for image in soup.find_all('img'):
            if image.get('src'):
                imageUrl = self._makeAbsoluteUrl(url, image['src'])
                if not self._isSmallImage(imageUrl):
                    return imageUrl
        
        return None

    def _findImageOnDynamicSite(self, url):
        """Find product image on a dynamic website using Selenium"""
        try:
            if not self.browser:
                self.browser = webdriver.Chrome(service=self.browserService, options=self.browserSettings)
            
            self.browser.get(url)
            wait = WebDriverWait(self.browser, 10)
            
            # Try common image locations
            imageLocations = [
                'img[itemprop="image"]',
                '.product-image img',
                '#product-image img',
                '.main-image img',
                '.product-main-image img',
                'img[alt*="product"]',
                'img[alt*="Product"]'
            ]
            
            for location in imageLocations:
                try:
                    image = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, location)))
                    if image.get_attribute('src'):
                        return image.get_attribute('src')
                except:
                    continue
            
            # Look for any large image
            for image in self.browser.find_elements(By.TAG_NAME, 'img'):
                imageUrl = image.get_attribute('src')
                if imageUrl and not self._isSmallImage(imageUrl):
                    return imageUrl
            
            return None
        finally:
            if self.browser:
                self.browser.quit()
                self.browser = None

    def checkStockStatus(self, url, stockIndicator, isDynamic=False, elementSelector=None):
        """
        Check if a product is in stock.
        
        Args:
            url (str): The product webpage URL
            stockIndicator (str): Text that indicates the product is in stock
            isDynamic (bool): Whether the website uses dynamic loading
            elementSelector (str): CSS selector for dynamic sites
            
        Returns:
            bool: True if product is in stock, False otherwise
        """
        try:
            if isDynamic:
                return self._checkDynamicStock(url, stockIndicator, elementSelector)
            return self._checkStaticStock(url, stockIndicator)
        except Exception as e:
            print(f"Error checking stock status: {e}")
            return False

    def _checkStaticStock(self, url, stockIndicator):
        """Check stock status on a static website"""
        response = requests.get(url)
        if response.status_code == 200:
            return stockIndicator.lower() in response.text.lower()
        return False

    def _checkDynamicStock(self, url, stockIndicator, elementSelector):
        """Check stock status on a dynamic website"""
        try:
            if not self.browser:
                self.browser = webdriver.Chrome(service=self.browserService, options=self.browserSettings)
            
            self.browser.get(url)
            wait = WebDriverWait(self.browser, 10)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, elementSelector)))
            return stockIndicator.lower() in element.text.lower()
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

if __name__ == "__main__":
    main() 