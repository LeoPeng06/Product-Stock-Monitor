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
import re

# Load environment variables
load_dotenv()

class StockMonitor:
    def __init__(self):
        # Email configuration
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.receiver_email = os.getenv('RECEIVER_EMAIL')
        
        # Chrome options for Selenium
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize Chrome WebDriver
        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        
        # Dictionary to store last known stock status
        self.last_status = {}

    def extract_image_static(self, url):
        """Extract main product image from static website"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Common image selectors for product pages
                selectors = [
                    'img[itemprop="image"]',
                    'img.product-image',
                    'img.main-image',
                    'img[data-main-image]',
                    'img[alt*="product"]',
                    'img[alt*="main"]',
                    'img[class*="product"]',
                    'img[class*="main"]',
                    'img[src*="product"]',
                    'img[src*="main"]'
                ]
                
                for selector in selectors:
                    img = soup.select_one(selector)
                    if img and img.get('src'):
                        img_url = img['src']
                        # Convert relative URLs to absolute
                        if img_url.startswith('/'):
                            from urllib.parse import urljoin
                            img_url = urljoin(url, img_url)
                        return img_url
                
                # If no specific product image found, try to get the first large image
                images = soup.find_all('img')
                for img in images:
                    if img.get('src'):
                        src = img['src']
                        # Skip small images and icons
                        if 'icon' not in src.lower() and 'logo' not in src.lower():
                            if src.startswith('/'):
                                from urllib.parse import urljoin
                                src = urljoin(url, src)
                            return src
                
                return None
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None

    def extract_image_dynamic(self, url):
        """Extract main product image from dynamic website"""
        try:
            self.driver.get(url)
            # Wait for images to load
            time.sleep(2)
            
            # Common image selectors for product pages
            selectors = [
                'img[itemprop="image"]',
                'img.product-image',
                'img.main-image',
                'img[data-main-image]',
                'img[alt*="product"]',
                'img[alt*="main"]',
                'img[class*="product"]',
                'img[class*="main"]',
                'img[src*="product"]',
                'img[src*="main"]'
            ]
            
            for selector in selectors:
                try:
                    img = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if img and img.get_attribute('src'):
                        return img.get_attribute('src')
                except:
                    continue
            
            # If no specific product image found, try to get the first large image
            images = self.driver.find_elements(By.TAG_NAME, 'img')
            for img in images:
                src = img.get_attribute('src')
                if src and 'icon' not in src.lower() and 'logo' not in src.lower():
                    return src
            
            return None
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None

    def check_stock_static(self, url, stock_indicator):
        """
        Check stock status using requests and BeautifulSoup
        Good for static websites
        """
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for stock indicator text
                stock_element = soup.find(string=lambda text: stock_indicator in text.lower() if text else False)
                return stock_element is not None
            return False
        except Exception as e:
            print(f"Error checking stock: {e}")
            return False

    def check_stock_dynamic(self, url, stock_indicator, element_selector):
        """
        Check stock status using Selenium
        Good for dynamic websites
        """
        try:
            self.driver.get(url)
            # Wait for the element to be present
            wait = WebDriverWait(self.driver, 10)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, element_selector)))
            
            # Check if stock indicator is present
            return stock_indicator.lower() in element.text.lower()
        except Exception as e:
            print(f"Error checking stock: {e}")
            return False

    def send_notification(self, product_name, url):
        """
        Send email notification when product is back in stock
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = f"Product Back in Stock: {product_name}"
            
            body = f"""
            The product '{product_name}' is now back in stock!
            
            Product URL: {url}
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Click the link above to view the product.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Create SMTP session
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            print(f"Notification sent for {product_name}")
        except Exception as e:
            print(f"Error sending notification: {e}")

    def monitor_product(self, product_name, url, check_interval=300, 
                       is_dynamic=False, stock_indicator="in stock", 
                       element_selector=None):
        """
        Monitor a product's stock status
        """
        print(f"Starting to monitor {product_name}")
        
        while True:
            try:
                # Check stock status
                if is_dynamic:
                    is_in_stock = self.check_stock_dynamic(url, stock_indicator, element_selector)
                    image_url = self.extract_image_dynamic(url)
                else:
                    is_in_stock = self.check_stock_static(url, stock_indicator)
                    image_url = self.extract_image_static(url)
                
                # Check if status has changed
                if product_name not in self.last_status:
                    self.last_status[product_name] = not is_in_stock
                
                if is_in_stock and not self.last_status[product_name]:
                    self.send_notification(product_name, url)
                    self.last_status[product_name] = True
                elif not is_in_stock:
                    self.last_status[product_name] = False
                
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {product_name}: {'In Stock' if is_in_stock else 'Out of Stock'}")
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"Error monitoring {product_name}: {e}")
                time.sleep(check_interval)

    def __del__(self):
        """
        Cleanup when the monitor is destroyed
        """
        if hasattr(self, 'driver'):
            self.driver.quit()

def main():
    # Example usage
    monitor = StockMonitor()
    
    # Example products to monitor
    products = [
        {
            "name": "Example Product 1",
            "url": "https://example.com/product1",
            "is_dynamic": False,
            "stock_indicator": "in stock",
            "check_interval": 300  # Check every 5 minutes
        },
        {
            "name": "Example Product 2",
            "url": "https://example.com/product2",
            "is_dynamic": True,
            "stock_indicator": "add to cart",
            "element_selector": "#stock-status",
            "check_interval": 300
        }
    ]
    
    # Start monitoring each product
    for product in products:
        monitor.monitor_product(
            product["name"],
            product["url"],
            product["check_interval"],
            product["is_dynamic"],
            product["stock_indicator"],
            product.get("element_selector")
        )

if __name__ == "__main__":
    main() 