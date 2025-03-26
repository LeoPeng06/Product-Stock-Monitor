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
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

class StockMonitor:
    def __init__(self):
        self.emailConfig = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': os.getenv('SENDER_EMAIL'),
            'sender_password': os.getenv('SENDER_PASSWORD'),
            'recipient_email': os.getenv('RECEIVER_EMAIL')
        }
        self.chromeOptions = Options()
        self.chromeOptions.add_argument('--headless')
        self.chromeOptions.add_argument('--no-sandbox')
        self.chromeOptions.add_argument('--disable-dev-shm-usage')
        self.driver = None
        
        # Initialize Chrome WebDriver
        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=self.chromeOptions)
        
        # Dictionary to store last known stock status
        self.last_status = {}

    def extractImageStatic(self, url):
        """Extract main product image from static websites"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Common selectors for product images
                selectors = [
                    'img[itemprop="image"]',
                    '.product-image img',
                    '#product-image img',
                    '.main-image img',
                    '.product-main-image img',
                    'img[alt*="product"]',
                    'img[alt*="Product"]'
                ]
                
                for selector in selectors:
                    img = soup.select_one(selector)
                    if img and img.get('src'):
                        imgUrl = img['src']
                        # Convert relative URL to absolute URL
                        if not imgUrl.startswith(('http://', 'https://')):
                            imgUrl = urljoin(url, imgUrl)
                        return imgUrl
                
                # Fallback: find first large image
                for img in soup.find_all('img'):
                    if img.get('src'):
                        imgUrl = img['src']
                        if not imgUrl.startswith(('http://', 'https://')):
                            imgUrl = urljoin(url, imgUrl)
                        # Skip small images and icons
                        if 'icon' not in imgUrl.lower() and 'logo' not in imgUrl.lower():
                            return imgUrl
                
                return None
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None

    def extractImageDynamic(self, url):
        """Extract main product image from dynamic websites"""
        try:
            if not self.driver:
                self.driver = webdriver.Chrome(service=self.service, options=self.chromeOptions)
            
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 10)
            
            # Common selectors for product images
            selectors = [
                'img[itemprop="image"]',
                '.product-image img',
                '#product-image img',
                '.main-image img',
                '.product-main-image img',
                'img[alt*="product"]',
                'img[alt*="Product"]'
            ]
            
            for selector in selectors:
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    imgUrl = element.get_attribute('src')
                    if imgUrl:
                        return imgUrl
                except:
                    continue
            
            # Fallback: find first large image
            images = self.driver.find_elements(By.TAG_NAME, 'img')
            for img in images:
                imgUrl = img.get_attribute('src')
                if imgUrl and 'icon' not in imgUrl.lower() and 'logo' not in imgUrl.lower():
                    return imgUrl
            
            return None
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def checkStockStatic(self, url, stockIndicator):
        """Check stock status for static websites"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return stockIndicator.lower() in response.text.lower()
            return False
        except Exception as e:
            print(f"Error checking stock: {e}")
            return False

    def checkStockDynamic(self, url, stockIndicator, elementSelector):
        """Check stock status for dynamic websites"""
        try:
            if not self.driver:
                self.driver = webdriver.Chrome(service=self.service, options=self.chromeOptions)
            
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 10)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, elementSelector)))
            return stockIndicator.lower() in element.text.lower()
        except Exception as e:
            print(f"Error checking stock: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def sendNotification(self, productName, url):
        """Send email notification when product is in stock"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.emailConfig['sender_email']
            msg['To'] = self.emailConfig['recipient_email']
            msg['Subject'] = f"Product In Stock Alert: {productName}"
            
            body = f"""
            The product "{productName}" is now in stock!
            URL: {url}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.emailConfig['smtp_server'], self.emailConfig['smtp_port'])
            server.starttls()
            server.login(self.emailConfig['sender_email'], self.emailConfig['sender_password'])
            server.send_message(msg)
            server.quit()
            
            print(f"Notification sent for {productName}")
        except Exception as e:
            print(f"Error sending notification: {e}")

    def monitorProduct(self, productName, url, checkInterval=300, 
                       isDynamic=False, stockIndicator="in stock", 
                       elementSelector=None):
        """
        Monitor a product's stock status
        """
        print(f"Starting to monitor {productName}")
        
        while True:
            try:
                # Check stock status
                if isDynamic:
                    isInStock = self.checkStockDynamic(url, stockIndicator, elementSelector)
                    imageUrl = self.extractImageDynamic(url)
                else:
                    isInStock = self.checkStockStatic(url, stockIndicator)
                    imageUrl = self.extractImageStatic(url)
                
                # Check if status has changed
                if productName not in self.last_status:
                    self.last_status[productName] = not isInStock
                
                if isInStock and not self.last_status[productName]:
                    self.sendNotification(productName, url)
                    self.last_status[productName] = True
                elif not isInStock:
                    self.last_status[productName] = False
                
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {productName}: {'In Stock' if isInStock else 'Out of Stock'}")
                
                # Wait before next check
                time.sleep(checkInterval)
                
            except Exception as e:
                print(f"Error monitoring {productName}: {e}")
                time.sleep(checkInterval)

    def __del__(self):
        """Cleanup Selenium driver"""
        if self.driver:
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
        monitor.monitorProduct(
            product["name"],
            product["url"],
            product["check_interval"],
            product["is_dynamic"],
            product["stock_indicator"],
            product.get("element_selector")
        )

if __name__ == "__main__":
    main() 