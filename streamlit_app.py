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

# Sidebar navigation and controls
with st.sidebar:
    st.title("Product Stock Tracker")
    st.markdown("---")
    
    # Mode selection
    selectedMode = st.radio(
        "Select Mode",
        ["Stock Monitor", "Web Scraper"],
        format_func=lambda x: x.split()[0]
    )
    
    if selectedMode == "Stock Monitor":
        # Product addition form with better organization
        st.subheader("Add New Product")
        with st.form("addProduct"):
            productName = st.text_input("Product Name", placeholder="Enter product name...")
            productUrl = st.text_input("Product URL", placeholder="https://example.com/product")
            isDynamicSite = st.checkbox("Is this a dynamic website? (e.g., React, Vue)")
            stockIndicatorText = st.text_input(
                "Stock Indicator Text",
                value="in stock",
                help="Text that indicates the product is in stock"
            )
            elementSelector = st.text_input(
                "Element Selector (for dynamic sites)",
                value="#stock-status",
                help="CSS selector to find the stock status element"
            )
            checkInterval = st.number_input(
                "Check Interval (seconds)",
                min_value=60,
                value=300,
                step=60,
                help="How often to check the product's stock status"
            )
            
            if st.form_submit_button("Add Product"):
                if productName and productUrl:
                    newProduct = {
                        "name": productName,
                        "url": productUrl,
                        "isDynamic": isDynamicSite,
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
                    st.error("Please fill in both product name and URL")
    
    else:  # Web Scraper mode
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
                    if product.get('imageUrl'):
                        productImage = loadImageFromUrl(product['imageUrl'])
                        if productImage:
                            st.image(productImage, caption=product['name'], use_column_width=True)
                    
                    # Display product information with enhanced styling
                    st.markdown(f"""
                        <div class="productCard">
                            <h3>{product['name']}</h3>
                            <p><a href="{product['url']}" target="_blank">{product['url']}</a></p>
                            <p>Type: {'Dynamic' if product['isDynamic'] else 'Static'}</p>
                            <p>Check Interval: {product['checkInterval']} seconds</p>
                            <p>Last Checked: {product['lastChecked'] or 'Never'}</p>
                            <p class="{'statusInStock' if product['status'] == 'In Stock' else 'statusOutOfStock'}">
                                {product['status']}
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
            time.sleep(min(p['checkInterval'] for p in st.session_state.products))
            st.rerun()

else:  # Web Scraper mode
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