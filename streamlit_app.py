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
    page_title="Web Scraper & Stock Monitor",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
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
    .product-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-in-stock {
        color: #00b894;
    }
    .status-out-of-stock {
        color: #d63031;
    }
    .scrape-result {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #e1e4e8;
        margin-top: 1rem;
        max-height: 400px;
        overflow-y: auto;
    }
    .product-image {
        max-width: 100%;
        height: auto;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

def load_image_from_url(url):
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
if 'scrape_results' not in st.session_state:
    st.session_state.scrape_results = {}

def save_products():
    """Save products to a JSON file"""
    with open('products.json', 'w') as f:
        json.dump(st.session_state.products, f)

def load_products():
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
    st.session_state.products = load_products()

# Sidebar
with st.sidebar:
    st.title("🌐 Web Scraper & Stock Monitor")
    st.markdown("---")
    
    # Tab selection
    tab = st.radio("Select Mode", ["Stock Monitor", "Web Scraper"])
    
    if tab == "Stock Monitor":
        # Add new product form
        st.subheader("Add New Product")
        with st.form("add_product"):
            name = st.text_input("Product Name")
            url = st.text_input("Product URL")
            is_dynamic = st.checkbox("Is Dynamic Website?")
            stock_indicator = st.text_input("Stock Indicator Text", "in stock")
            element_selector = st.text_input("Element Selector (for dynamic sites)", "#stock-status")
            check_interval = st.number_input("Check Interval (seconds)", min_value=60, value=300, step=60)
            
            if st.form_submit_button("Add Product"):
                if name and url:
                    new_product = {
                        "name": name,
                        "url": url,
                        "is_dynamic": is_dynamic,
                        "stock_indicator": stock_indicator,
                        "element_selector": element_selector,
                        "check_interval": check_interval,
                        "last_checked": None,
                        "status": "Not Checked",
                        "image_url": None
                    }
                    st.session_state.products.append(new_product)
                    save_products()
                    st.success("Product added successfully!")
                    st.rerun()
    
    else:  # Web Scraper tab
        st.subheader("Web Scraper")
        with st.form("scrape_url"):
            url = st.text_input("URL to Scrape")
            use_proxy = st.checkbox("Use Proxy (Bright Data)", value=True)
            clean_text = st.checkbox("Clean Text Output", value=True)
            
            if st.form_submit_button("Scrape"):
                if url:
                    with st.spinner("Scraping in progress..."):
                        try:
                            if use_proxy:
                                html = scrapeSite(url)
                            else:
                                response = requests.get(url)
                                html = response.text
                            
                            if clean_text:
                                body_content = extract_html(html)
                                if body_content:
                                    clean_content = cleanBody(body_content)
                                    st.session_state.scrape_results[url] = clean_content
                                else:
                                    st.error("Could not extract body content")
                            else:
                                st.session_state.scrape_results[url] = html
                            
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
                    image_html = ""
                    if product.get('image_url'):
                        image = load_image_from_url(product['image_url'])
                        if image:
                            st.image(image, caption=product['name'], use_column_width=True)
                    
                    st.markdown(f"""
                        <div class="product-card">
                            <h3>{product['name']}</h3>
                            <p>URL: {product['url']}</p>
                            <p>Type: {'Dynamic' if product['is_dynamic'] else 'Static'}</p>
                            <p>Check Interval: {product['check_interval']} seconds</p>
                            <p>Last Checked: {product['last_checked'] or 'Never'}</p>
                            <p class="{'status-in-stock' if product['status'] == 'In Stock' else 'status-out-of-stock'}">
                                Status: {product['status']}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("Edit", key=f"edit_{i}"):
                        st.session_state.editing_product = i
                        st.rerun()
                
                with col3:
                    if st.button("Delete", key=f"delete_{i}"):
                        st.session_state.products.pop(i)
                        save_products()
                        st.rerun()
    
    # Monitoring logic
    if st.session_state.monitoring:
        while True:
            for product in st.session_state.products:
                try:
                    if product['is_dynamic']:
                        is_in_stock = st.session_state.monitor.check_stock_dynamic(
                            product['url'],
                            product['stock_indicator'],
                            product['element_selector']
                        )
                        image_url = st.session_state.monitor.extract_image_dynamic(product['url'])
                    else:
                        is_in_stock = st.session_state.monitor.check_stock_static(
                            product['url'],
                            product['stock_indicator']
                        )
                        image_url = st.session_state.monitor.extract_image_static(product['url'])
                    
                    product['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    product['status'] = "In Stock" if is_in_stock else "Out of Stock"
                    product['image_url'] = image_url
                    
                    if is_in_stock and product.get('last_status') != "In Stock":
                        st.session_state.monitor.send_notification(product['name'], product['url'])
                    
                    product['last_status'] = product['status']
                    save_products()
                    
                except Exception as e:
                    st.error(f"Error checking {product['name']}: {str(e)}")
                    product['status'] = "Error"
                    save_products()
            
            time.sleep(min(p['check_interval'] for p in st.session_state.products))
            st.rerun()

else:  # Web Scraper tab
    st.title("Web Scraping Results")
    
    if not st.session_state.scrape_results:
        st.info("No scraping results yet. Use the sidebar form to scrape a URL.")
    else:
        for url, content in st.session_state.scrape_results.items():
            with st.expander(f"Results for {url}", expanded=True):
                # Split content if it's too long
                if len(content) > 5000:
                    content_chunks = splitDomContent(content)
                    for i, chunk in enumerate(content_chunks):
                        st.markdown(f"### Chunk {i+1}")
                        st.markdown(f"<div class='scrape-result'>{chunk}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='scrape-result'>{content}</div>", unsafe_allow_html=True)
                
                # Add download button
                st.download_button(
                    label=f"Download Results for {url}",
                    data=content,
                    file_name=f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                ) 