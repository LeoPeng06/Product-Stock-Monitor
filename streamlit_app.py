import streamlit as st
import pandas as pd
from stock_monitor import StockMonitor
from scrape import scrapeSite, extract_html, cleanBody, splitDomContent
import json
import os
from datetime import datetime
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure the Streamlit page with a friendly title and icon
st.set_page_config(
    page_title="Product Stock Tracker",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced custom styling for a more modern and friendly look
st.markdown("""
    <style>
    .main {
        padding: 2rem;
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .productCard {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .productCard:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    .statusInStock {
        color: #2ecc71;
        font-weight: 600;
        padding: 0.3rem 0.8rem;
        background-color: #e8f5e9;
        border-radius: 20px;
        display: inline-block;
    }
    .statusOutOfStock {
        color: #e74c3c;
        font-weight: 600;
        padding: 0.3rem 0.8rem;
        background-color: #fde8e8;
        border-radius: 20px;
        display: inline-block;
    }
    .scrapeResult {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e1e4e8;
        margin-top: 1rem;
        max-height: 400px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .productImage {
        max-width: 100%;
        height: auto;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
        padding: 0.5rem;
    }
    .stCheckbox>div>div>div {
        border-radius: 10px;
    }
    .stNumberInput>div>div>input {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

def loadImageFromUrl(url):
    """
    Load an image from a URL and return it as a PIL Image object.
    
    Args:
        url (str): The URL of the image to load
        
    Returns:
        PIL.Image: The loaded image, or None if loading fails
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        st.error(f"❌ Error loading image: {e}")
    return None

# Initialize the app's state
if 'monitor' not in st.session_state:
    st.session_state.monitor = StockMonitor()
if 'products' not in st.session_state:
    st.session_state.products = []
if 'monitoring' not in st.session_state:
    st.session_state.monitoring = False
if 'scrapeResults' not in st.session_state:
    st.session_state.scrapeResults = {}

def saveProducts():
    """Save the current list of products to a JSON file"""
    with open('products.json', 'w') as f:
        json.dump(st.session_state.products, f)

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
                    return json.loads(content)
                return []
        return []
    except json.JSONDecodeError:
        st.warning("⚠️ Error reading products.json. Starting with empty list.")
        return []
    except Exception as e:
        st.error(f"❌ Error loading products: {e}")
        return []

# Load saved products when the app starts
if not st.session_state.products:
    st.session_state.products = loadProducts()

def get_all_product_links(listing_url):
    """Scrape all product links from GameStop's search results page using Selenium."""
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # Load the page
        driver.get(listing_url)
        
        # Wait for products to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/Toys-Collectibles/Games/']")))
        
        # Give extra time for all products to load
        time.sleep(3)
        
        # Get all product links
        product_links = []
        product_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/Toys-Collectibles/Games/']")
        
        for element in product_elements:
            href = element.get_attribute('href')
            if href and href not in product_links:
                product_links.append(href)
        
        driver.quit()
        return product_links
        
    except Exception as e:
        st.error(f"Error fetching product links: {e}")
        if 'driver' in locals():
            driver.quit()
        return []

def get_product_info(url, monitor):
    """Get product name, image, and stock status from a GameStop product page using Selenium."""
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # Load the page
        driver.get(url)
        
        # Wait for product details to load
        wait = WebDriverWait(driver, 10)
        
        # Get product name
        name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/Toys-Collectibles/Games/']")))
        name = name_element.text.strip()
        
        # Get product image
        image_element = driver.find_element(By.CSS_SELECTOR, "img.product-image")
        image_url = image_element.get_attribute('src')
        
        # Check stock status based on button text
        try:
            # Look for any of the three button types
            add_to_cart_button = driver.find_element(By.CSS_SELECTOR, "button.button.is-full-width")
            button_text = add_to_cart_button.text.strip().lower()
            
            if "add to cart" in button_text:
                status = "In Stock"
            elif "preorder" in button_text:
                status = "Preorder Available"
            elif "unavailable" in button_text:
                status = "Out of Stock"
            else:
                status = "Unknown Status"
                
        except:
            status = "Status Unknown"
        
        # Get price
        try:
            price_element = driver.find_element(By.CSS_SELECTOR, "span.price")
            price = price_element.text.strip()
        except:
            price = "Price not available"
        
        driver.quit()
        
        return {
            "name": name,
            "url": url,
            "imageUrl": image_url,
            "status": status,
            "price": price
        }
        
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        return {
            "name": url,
            "url": url,
            "imageUrl": None,
            "status": f"Error: {e}",
            "price": "N/A"
        }

# Sidebar navigation and controls
with st.sidebar:
    st.title("Product Stock Tracker")
    st.markdown("---")
    
    # Mode selection
    selectedMode = st.radio(
        "Select Mode",
        ["Stock Monitor", "Web Scraper", "Bulk Product Checker"],
        format_func=lambda x: x.split()[0]
    )
    
    if selectedMode == "Stock Monitor":
        # Product addition form with better organization
        st.subheader("Add New Product")
        with st.form("addProduct"):
            productName = st.text_input("Product Name", placeholder="Enter Pokemon product name...")
            productUrl = st.text_input(
                "Product URL",
                placeholder="https://www.pokemoncenter.com/product/...",
                help="Enter the full Pokemon Center product URL"
            )
            
            # Pokemon Center is always dynamic, so we can hide this
            isDynamicSite = True
            
            # Pre-configure for Pokemon Center
            stockIndicatorText = "Add to Cart"
            elementSelector = ".add-to-cart"
            checkInterval = st.number_input(
                "Check Interval (seconds)",
                min_value=60,      # Reduced from 300 to 60 seconds minimum
                value=300,         # Default to 5 minutes instead of 10
                step=60,           # 1-minute steps instead of 5-minute steps
                help="How often to check stock status (be considerate with timing)"
            )
            
            if st.form_submit_button("Add Product"):
                if productUrl and "pokemoncenter.com" in productUrl:
                    if productName and productUrl:
                        newProduct = {
                            "name": productName,
                            "url": productUrl,
                            "isDynamic": True,  # Pokemon Center is always dynamic
                            "stockIndicator": stockIndicatorText,
                            "elementSelector": elementSelector,
                            "checkInterval": checkInterval,
                            "lastChecked": None,
                            "status": "Not Checked",
                            "imageUrl": None
                        }
                        st.session_state.products.append(newProduct)
                        saveProducts()
                        st.success("Product added successfully!")
                        st.rerun()
                else:
                    st.error("Please enter a valid Pokemon Center URL")
    
    elif selectedMode == "Web Scraper":
        st.subheader("Web Scraper")
        with st.form("scrapeUrl"):
            targetUrl = st.text_input("URL to Scrape", placeholder="https://example.com")
            useProxy = st.checkbox("Use Proxy (Bright Data)", value=True, help="Use proxy to avoid rate limiting")
            cleanText = st.checkbox("Clean Text Output", value=True, help="Remove HTML tags and clean the text")
            
            if st.form_submit_button("Start Scraping"):
                if targetUrl:
                    with st.spinner("Scraping in progress..."):
                        try:
                            if useProxy:
                                htmlContent = scrapeSite(targetUrl)
                            else:
                                response = requests.get(targetUrl)
                                htmlContent = response.text
                            
                            if cleanText:
                                bodyContent = extract_html(htmlContent)
                                if bodyContent:
                                    cleanContent = cleanBody(bodyContent)
                                    st.session_state.scrapeResults[targetUrl] = cleanContent
                                else:
                                    st.error("❌ Could not extract body content")
                            else:
                                st.session_state.scrapeResults[targetUrl] = htmlContent
                            
                            st.success("Scraping completed!")
                        except Exception as e:
                            st.error(f"Error during scraping: {str(e)}")
                else:
                    st.error("Please enter a URL to scrape")

    elif selectedMode == "Bulk Product Checker":
        st.subheader("GameStop Product Checker")
        with st.form("bulkProductForm"):
            listing_url = st.text_input(
                "GameStop Search URL",
                value="https://www.gamestop.ca/SearchResult/QuickSearch?q=pokemon+tcg",
                help="Enter a GameStop search or category URL"
            )
            submit_bulk = st.form_submit_button("Check All Products")
            if submit_bulk and listing_url:
                with st.spinner("Fetching all products..."):
                    product_links = get_all_product_links(listing_url)
                    st.session_state.bulk_products = []
                    progress_bar = st.progress(0)
                    for i, link in enumerate(product_links):
                        info = get_product_info(link, st.session_state.monitor)
                        st.session_state.bulk_products.append(info)
                        progress_bar.progress((i + 1) / len(product_links))
                    st.success(f"Found {len(st.session_state.bulk_products)} products.")

# Main content area
if selectedMode == "Stock Monitor":
    st.title("Stock Monitoring Dashboard")
    
    # Monitoring controls with better visual feedback
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.monitoring:
            if st.button("Start Monitoring", type="primary"):
                st.session_state.monitoring = True
                st.rerun()
    with col2:
        if st.session_state.monitoring:
            if st.button("Stop Monitoring", type="secondary"):
                st.session_state.monitoring = False
                st.rerun()
    
    # Display monitored products with enhanced visuals
    st.markdown("### Monitored Products")
    if not st.session_state.products:
        st.info("No products added yet. Use the sidebar form to add your first product!")
    else:
        for index, product in enumerate(st.session_state.products):
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Display product image if available
                    if isinstance(product, dict) and 'imageUrl' in product and product['imageUrl']:
                        productImage = loadImageFromUrl(product['imageUrl'])
                        if productImage:
                            st.image(productImage, caption=product['name'], use_column_width=True)
                    
                    # Display product information with enhanced styling
                    st.markdown(f"""
                        <div class="productCard">
                            <h3>{product['name']}</h3>
                            <p><a href="{product['url']}" target="_blank">{product['url']}</a></p>
                            <p>Type: {'Dynamic' if product.get('isDynamic', False) else 'Static'}</p>
                            <p>Check Interval: {product.get('checkInterval', 300)} seconds</p>
                            <p>Last Checked: {product.get('lastChecked', 'Never')}</p>
                            <p class="{'statusInStock' if product.get('status') == 'In Stock' else 'statusOutOfStock'}">
                                {product.get('status', 'Not Checked')}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("Edit", key=f"edit_{index}"):
                        st.session_state.editingProduct = index
                        st.rerun()
                
                with col3:
                    if st.button("Delete", key=f"delete_{index}"):
                        st.session_state.products.pop(index)
                        saveProducts()
                        st.rerun()
    
    # Product monitoring logic
    if st.session_state.monitoring:
        while True:
            for product in st.session_state.products:
                try:
                    # Check stock status
                    if product['isDynamic']:
                        isAvailable = st.session_state.monitor.checkStockStatus(
                            product['url'],
                            product['stockIndicator'],
                            isDynamic=True,
                            elementSelector=product['elementSelector']
                        )
                        productImageUrl = st.session_state.monitor.findProductImage(
                            product['url'],
                            isDynamic=True
                        )
                    else:
                        isAvailable = st.session_state.monitor.checkStockStatus(
                            product['url'],
                            product['stockIndicator']
                        )
                        productImageUrl = st.session_state.monitor.findProductImage(
                            product['url']
                        )
                    
                    # Update product status
                    product['lastChecked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    product['status'] = "In Stock" if isAvailable else "Out of Stock"
                    product['imageUrl'] = productImageUrl
                    
                    # Send notification if product becomes available
                    if isAvailable and product.get('lastStatus') != "In Stock":
                        st.session_state.monitor.notifyStockAvailable(product['name'], product['url'])
                    
                    product['lastStatus'] = product['status']
                    saveProducts()
                    
                except Exception as e:
                    st.error(f"❌ Error checking {product['name']}: {str(e)}")
                    product['status'] = "Error"
                    saveProducts()
            
            # Wait before next check cycle
            if st.session_state.products:  # Only try to get min interval if there are products
                min_interval = min(p['checkInterval'] for p in st.session_state.products)
                time.sleep(min_interval)
            else:
                time.sleep(60)  # Default sleep if no products are being monitored
            st.rerun()

elif selectedMode == "Web Scraper":
    st.title("Web Scraping Results")
    
    if not st.session_state.scrapeResults:
        st.info("No scraping results yet. Use the sidebar form to scrape your first URL!")
    else:
        for url, content in st.session_state.scrapeResults.items():
            with st.expander(f"Results for {url}", expanded=True):
                # Handle long content by splitting into chunks
                if len(content) > 5000:
                    contentChunks = splitDomContent(content)
                    for i, chunk in enumerate(contentChunks):
                        st.markdown(f"### Chunk {i+1}")
                        st.markdown(f"<div class='scrapeResult'>{chunk}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='scrapeResult'>{content}</div>", unsafe_allow_html=True)
                
                # Download button for results
                st.download_button(
                    label="Download Results",
                    data=content,
                    file_name=f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

elif selectedMode == "Bulk Product Checker":
    st.title("GameStop Product Availability")
    if "bulk_products" in st.session_state and st.session_state.bulk_products:
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            show_in_stock = st.checkbox("Show In Stock Only", value=False)
        with col2:
            sort_by = st.selectbox("Sort By", ["Name", "Price", "Status"])
        
        # Filter and sort products
        filtered_products = st.session_state.bulk_products
        if show_in_stock:
            filtered_products = [p for p in filtered_products if p["status"] in ["In Stock", "Preorder Available"]]
        
        if sort_by == "Name":
            filtered_products.sort(key=lambda x: x["name"])
        elif sort_by == "Price":
            filtered_products.sort(key=lambda x: x["price"])
        elif sort_by == "Status":
            filtered_products.sort(key=lambda x: x["status"])
        
        # Display products in a grid
        cols = st.columns(3)
        for i, product in enumerate(filtered_products):
            with cols[i % 3]:
                with st.container():
                    st.markdown("""
                        <style>
                        .product-card {
                            border: 1px solid #ddd;
                            border-radius: 8px;
                            padding: 10px;
                            margin-bottom: 20px;
                            background-color: white;
                        }
                        .product-card:hover {
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    if product["imageUrl"]:
                        st.image(product["imageUrl"], use_column_width=True)
                    
                    # Determine status color
                    status_color = {
                        "In Stock": "🟢",
                        "Preorder Available": "🟡",
                        "Out of Stock": "🔴",
                        "Unknown Status": "⚪"
                    }.get(product["status"], "⚪")
                    
                    st.markdown(f"""
                        <div class="product-card">
                            <h4>{product['name']}</h4>
                            <p>Price: {product['price']}</p>
                            <p>Status: {status_color} {product['status']}</p>
                            <a href="{product['url']}" target="_blank">View Product</a>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("Enter a GameStop URL and click 'Check All Products' to see availability.") 