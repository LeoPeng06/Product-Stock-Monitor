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

# Set page config
st.set_page_config(
    pageTitle="Web Scraper & Stock Monitor",
    pageIcon="🌐",
    layout="wide",
    initialSidebarState="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    .productCard {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .statusInStock {
        color: #00b894;
    }
    .statusOutOfStock {
        color: #d63031;
    }
    .scrapeResult {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #e1e4e8;
        margin-top: 1rem;
        max-height: 400px;
        overflow-y: auto;
    }
    .productImage {
        max-width: 100%;
        height: auto;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

def loadImageFromUrl(url):
    """Load image from URL and return PIL Image object"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Error loading image: {e}")
    return None

# Initialize session state
if 'monitor' not in st.session_state:
    st.session_state.monitor = StockMonitor()
if 'products' not in st.session_state:
    st.session_state.products = []
if 'monitoring' not in st.session_state:
    st.session_state.monitoring = False
if 'scrapeResults' not in st.session_state:
    st.session_state.scrapeResults = {}

def saveProducts():
    """Save products to a JSON file"""
    with open('products.json', 'w') as f:
        json.dump(st.session_state.products, f)

def loadProducts():
    """Load products from JSON file"""
    try:
        if os.path.exists('products.json'):
            with open('products.json', 'r') as f:
                content = f.read().strip()  # Read and remove whitespace
                if content:  # Check if file is not empty
                    return json.loads(content)
                return []  # Return empty list if file is empty
        return []  # Return empty list if file doesn't exist
    except json.JSONDecodeError:
        print("Error reading products.json. Starting with empty list.")
        return []  # Return empty list if JSON is invalid
    except Exception as e:
        print(f"Error loading products: {e}")
        return []  # Return empty list for any other error

# Load saved products
if not st.session_state.products:
    st.session_state.products = loadProducts()

# Sidebar
with st.sidebar:
    st.title("🌐 Web Scraper & Stock Monitor")
    st.markdown("---")
    
    # Tab selection
    tab = st.radio("Select Mode", ["Stock Monitor", "Web Scraper"])
    
    if tab == "Stock Monitor":
        # Add new product form
        st.subheader("Add New Product")
        with st.form("addProduct"):
            name = st.text_input("Product Name")
            url = st.text_input("Product URL")
            isDynamic = st.checkbox("Is Dynamic Website?")
            stockIndicator = st.text_input("Stock Indicator Text", "in stock")
            elementSelector = st.text_input("Element Selector (for dynamic sites)", "#stock-status")
            checkInterval = st.number_input("Check Interval (seconds)", min_value=60, value=300, step=60)
            
            if st.form_submit_button("Add Product"):
                if name and url:
                    newProduct = {
                        "name": name,
                        "url": url,
                        "isDynamic": isDynamic,
                        "stockIndicator": stockIndicator,
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
    
    else:  # Web Scraper tab
        st.subheader("Web Scraper")
        with st.form("scrapeUrl"):
            url = st.text_input("URL to Scrape")
            useProxy = st.checkbox("Use Proxy (Bright Data)", value=True)
            cleanText = st.checkbox("Clean Text Output", value=True)
            
            if st.form_submit_button("Scrape"):
                if url:
                    with st.spinner("Scraping in progress..."):
                        try:
                            if useProxy:
                                html = scrapeSite(url)
                            else:
                                response = requests.get(url)
                                html = response.text
                            
                            if cleanText:
                                bodyContent = extract_html(html)
                                if bodyContent:
                                    cleanContent = cleanBody(bodyContent)
                                    st.session_state.scrapeResults[url] = cleanContent
                                else:
                                    st.error("Could not extract body content")
                            else:
                                st.session_state.scrapeResults[url] = html
                            
                            st.success("Scraping completed!")
                        except Exception as e:
                            st.error(f"Error during scraping: {str(e)}")

# Main content
if tab == "Stock Monitor":
    st.title("Stock Monitoring Dashboard")
    
    # Control buttons
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
    
    # Products display
    st.markdown("### Monitored Products")
    if not st.session_state.products:
        st.info("No products added yet. Add products using the sidebar form.")
    else:
        for i, product in enumerate(st.session_state.products):
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Get product image
                    if product.get('imageUrl'):
                        image = loadImageFromUrl(product['imageUrl'])
                        if image:
                            st.image(image, caption=product['name'], use_column_width=True)
                    
                    st.markdown(f"""
                        <div class="productCard">
                            <h3>{product['name']}</h3>
                            <p>URL: {product['url']}</p>
                            <p>Type: {'Dynamic' if product['isDynamic'] else 'Static'}</p>
                            <p>Check Interval: {product['checkInterval']} seconds</p>
                            <p>Last Checked: {product['lastChecked'] or 'Never'}</p>
                            <p class="{'statusInStock' if product['status'] == 'In Stock' else 'statusOutOfStock'}">
                                Status: {product['status']}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("Edit", key=f"edit_{i}"):
                        st.session_state.editingProduct = i
                        st.rerun()
                
                with col3:
                    if st.button("Delete", key=f"delete_{i}"):
                        st.session_state.products.pop(i)
                        saveProducts()
                        st.rerun()
    
    # Monitoring logic
    if st.session_state.monitoring:
        while True:
            for product in st.session_state.products:
                try:
                    if product['isDynamic']:
                        isInStock = st.session_state.monitor.checkStockDynamic(
                            product['url'],
                            product['stockIndicator'],
                            product['elementSelector']
                        )
                        imageUrl = st.session_state.monitor.extractImageDynamic(product['url'])
                    else:
                        isInStock = st.session_state.monitor.checkStockStatic(
                            product['url'],
                            product['stockIndicator']
                        )
                        imageUrl = st.session_state.monitor.extractImageStatic(product['url'])
                    
                    product['lastChecked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    product['status'] = "In Stock" if isInStock else "Out of Stock"
                    product['imageUrl'] = imageUrl
                    
                    if isInStock and product.get('lastStatus') != "In Stock":
                        st.session_state.monitor.sendNotification(product['name'], product['url'])
                    
                    product['lastStatus'] = product['status']
                    saveProducts()
                    
                except Exception as e:
                    st.error(f"Error checking {product['name']}: {str(e)}")
                    product['status'] = "Error"
                    saveProducts()
            
            time.sleep(min(p['checkInterval'] for p in st.session_state.products))
            st.rerun()

else:  # Web Scraper tab
    st.title("Web Scraping Results")
    
    if not st.session_state.scrapeResults:
        st.info("No scraping results yet. Use the sidebar form to scrape a URL.")
    else:
        for url, content in st.session_state.scrapeResults.items():
            with st.expander(f"Results for {url}", expanded=True):
                # Split content if it's too long
                if len(content) > 5000:
                    contentChunks = splitDomContent(content)
                    for i, chunk in enumerate(contentChunks):
                        st.markdown(f"### Chunk {i+1}")
                        st.markdown(f"<div class='scrapeResult'>{chunk}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='scrapeResult'>{content}</div>", unsafe_allow_html=True)
                
                # Add download button
                st.download_button(
                    label=f"Download Results for {url}",
                    data=content,
                    file_name=f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                ) 